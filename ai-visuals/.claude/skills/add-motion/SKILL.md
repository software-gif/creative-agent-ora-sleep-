---
name: add-motion
description: Run when the user wants to add motion to an image, animate a still image, or create a short video clip from a photo using the /add-motion command. Uses Kling 3.0 Pro. Handles product images, start/end frames, and optional audio. Does NOT cover voiceovers or UGC — use the /ugc or /product-ugc skills for those.
---

# Add Motion

Animates a still image into a short video clip using Kling 3.0 Pro.

**This skill covers:** product shots, packshots, clothing shoot outputs, styled images, or any still you want to bring to life.

**This skill does not cover:**
- Voiceovers or talking-head content — use `/ugc` or `/product-ugc` for that
- Long-form video — clips are 3–12 seconds

Output saved to `./brands/[brand-name]/motion/[output-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Select the source image

Ask: "Which image would you like to add motion to?"

**If it's a previously generated image**, ask them to point you to it. Suggest checking these folders:
```
brands/[brand-name]/product-shoot/
brands/[brand-name]/packshots/
brands/[brand-name]/styled/
brands/[brand-name]/clothing-shoot/
brands/[brand-name]/ugc/
```

**If it's an external image they want to upload**, create the uploads folder and tell them where to put it:
```bash
mkdir -p brands/[brand-name]/motion/uploads
```
> "Drop your image into `brands/[brand-name]/motion/uploads/` and let me know the filename."

Wait for confirmation before continuing.

---

## Step 3 — Describe the motion

Ask: "Describe the motion you'd like added. Be specific — direction, speed, camera movement, subject behaviour. Examples:
- 'Slow upward drift with a subtle parallax depth effect'
- 'The product rotates 90 degrees clockwise, slow and smooth'
- 'Camera slowly pulls back from the subject, slight lens breathing'"

---

## Step 4 — Start frame and end frame

**First time running this skill**, explain before asking:

> "Kling animates from a start frame to an end frame.
>
> - **Start frame only** — Kling has full creative control over how the motion evolves. Good for natural, organic movement.
> - **Start + end frame** — you define exactly where the motion lands. Useful when you need a precise final state (e.g. a product landing in a specific position).
>
> The source image you've selected will be the start frame. Do you also have an end frame you'd like to provide?"

If the user provides an end frame, ask where it's saved (same process as Step 2 — existing file or upload to `motion/uploads/`).

If no end frame, note it and continue.

---

## Step 5 — Analyse image for products

Read the source image using the Read tool.

**Determine whether the image contains a product** (packshot, product-in-hand, product on a surface, product being held, etc.). If the image is clearly people-only with no product visible (e.g. someone applying cream with no product in frame), skip this step.

**If a product is present:**

1. Confirm with the user: "I can see what looks like [product description] in the image. Is this correct? And which product is it — I'll look it up in your brand's product images."

2. Once confirmed, locate the product in `brands/[brand-name]/brand-identity/product-images/`. If the file is there, use it. If not, check `brands/[brand-name]/brand-identity/products.json` for the product URL, then try to scrape additional images from the product page:
   ```bash
   # Try fetching the product page directly via WebFetch
   # Look for multiple product image URLs in the HTML/JSON
   # Download them to brands/[brand-name]/brand-identity/product-images/
   ```

3. Aim for **at least 2 product images** from different angles. If only one is available:
   > "I can only find one image of this product. Do you have another angle you can add to `brands/[brand-name]/brand-identity/product-images/`? More angles help Kling maintain accurate product rendering throughout the animation."

   Wait for them to add more, or proceed with one if they can't provide another.

4. These product images become **Element1, Element2, ...** — they're passed to Kling so it can maintain product accuracy through the motion.

---

## Step 6 — Duration and audio

Ask in one message:

**Duration:** "How long should the clip be? (3–12 seconds)"

**Audio:** "Would you like Kling to generate ambient audio for the clip? Note: this is environmental/atmospheric sound — not voiceover. (+$0.056/sec)"

---

## Step 7 — Name the output

Derive a slug from the source image name and a short motion descriptor:
- `hey-bud-tint-rotate`
- `ren-jacket-parallax`
- `mutimer-hero-drift`

Ask the user to confirm or rename.

---

## Step 8 — Write add-motion-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/motion/[output-name]/
  add-motion-spec.json
```

**With end frame and product images:**
```json
{
  "output_name": "hey-bud-tint-rotate",
  "brand": "[brand-name]",
  "source_image": "brands/[brand-name]/product-shoot/hey-bud-tint-hand-hold/product-shot_v1.png",
  "end_image": "brands/[brand-name]/motion/uploads/hey-bud-end-frame.jpg",
  "motion_description": "The product rotates 90 degrees clockwise, slow and smooth, light catching the label.",
  "has_product": true,
  "product_name": "Hey Bud Acne Face Tint",
  "product_images": [
    "brands/[brand-name]/brand-identity/product-images/hey-bud-face-tint.jpg",
    "brands/[brand-name]/brand-identity/product-images/hey-bud-face-tint-side.jpg"
  ],
  "duration": 5,
  "generate_audio": false,
  "aspect_ratio": "9:16"
}
```

**Without end frame or product:**
```json
{
  "output_name": "ren-jacket-parallax",
  "brand": "[brand-name]",
  "source_image": "brands/[brand-name]/clothing-shoot/ren-garage/shoot_v1.png",
  "end_image": null,
  "motion_description": "Slow camera pull-back with subtle parallax depth. Slight lens breathing.",
  "has_product": false,
  "product_name": null,
  "product_images": [],
  "duration": 6,
  "generate_audio": true,
  "aspect_ratio": "4:5"
}
```

**Aspect ratio** — detect from the source image dimensions and match automatically. Default to `9:16` if unsure. Ask the user if the image is ambiguous.

---

## Step 9 — Generate

Run from the project root:

```bash
python3 skills/references/generate-motion.py brands/[brand-name]/motion/[output-name]
```

The script:
- Uploads the start frame (and end frame if provided) to FAL
- Uploads product images as Element1, Element2, ... and appends `@Element` references to the prompt
- Calls Kling 3.0 Pro with all inputs
- Downloads the output video

Cost: `duration × $0.112` (audio off) or `duration × $0.168` (audio on)

---

## Step 10 — Present the result

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/motion/[output-name]/[output-name]_v1.mp4`

Ask: "Happy with this? Or would you like to regenerate, adjust the motion description, or add an end frame?"

**To regenerate (same spec):**
```bash
python3 skills/references/generate-motion.py brands/[brand-name]/motion/[output-name]
```

**To adjust motion or add an end frame:** update `add-motion-spec.json` and re-run.

---

## Notes

- Kling 3.0 Pro accepts durations 3–15s — this skill caps the suggestion at 12s for cost and practical reasons
- The `elements` array gives Kling reference images for maintaining product accuracy. More angles = better fidelity through rotation and movement
- End frames give you precise control over the motion arc. Without one, Kling interprets the motion description creatively
- Audio generated by Kling is ambient/environmental — it is not voiceover. For talking-head audio, use `/ugc`
- Each brand has its own `motion/` subfolder — multiple brands can run independent motion workflows in the same project
