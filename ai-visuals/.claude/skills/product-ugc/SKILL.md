---
name: product-ugc
description: Run when the user wants to create product UGC content, a UGC selfie of a model holding a product, creator-to-camera content featuring a product, or use the /product-ugc command. Takes a model (styled or unstyled) and a product image, generates an ultra-realistic iPhone selfie of the model holding the product, then optionally continues into a UGC video via Veo 3.1 at 1080p. Assumes the user has completed both the model/style and product workflows. Output saved under the active brand folder.
---

# Product UGC

Two-stage workflow:
1. **Product UGC image** — ultra-realistic iPhone selfie of the model holding a product at 9:16 2K
2. **Product UGC video** — talking-head video from the selfie at 9:16 1080p via Veo 3.1

**Prerequisite:** This workflow assumes the user has already created a model (via `/model`) and has product images set up (via `/brand`). If they also want branded outfit styling, they should have run `/style` first.

Output saved to `./brands/[brand-name]/product-ugc/[output-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Select a model

Ask: "Would you like to use a **styled** model (specific outfit applied) or an **unstyled** model (plain casting neutral wardrobe)?"

**If styled:** list available outputs from `./brands/[brand-name]/styled/`:
```
Available styled models:
  • jade-cloudmerino-tshirt
  • marcus-techsilk-shorts
```
Read `brands/[brand-name]/styled/[name]/style-spec.json` to get `model_dir`.

**If unstyled:** list available models from `./brands/[brand-name]/models/`:
```
Available models:
  • jade
  • marcus-02
```

If neither folder has completed outputs:
> "No models found for [brand]. Use `/model` to create one first. If you want a specific outfit, also run `/style`."

---

## Step 3 — Select the product to hold

Ask: "Which product should the model be holding? I'll look for it in your brand's product images."

Check `./brands/[brand-name]/brand-identity/product-images/` for a matching image. Show what was found:
```
Found:
  ✓ cloudmerino-66-t-shirt.jpg

Not found:
  ✗ rippy-cap — searching brand site...
```

**If not found in product-images:**
1. Check `brands/[brand-name]/brand-identity/products.json` for the product URL
2. Try to download the product image from the brand site:
   ```bash
   curl -L "[product-image-url]" -o "brands/[brand-name]/brand-identity/product-images/[slug].jpg"
   ```
3. If that fails, ask the user to either drop the image in `product-images/` or paste the image URL directly

---

## Step 4 — Collect variables

Ask for all in one message:

**Variable 1 — Action:**
"What is the model doing? (e.g. standing, sitting at a café, walking down a street, leaning against a wall)"

**Variable 2 — Location:**
"Where are they? Describe the environment. (e.g. a busy urban high street with bokeh traffic, a sunlit café terrace in Paris, a graffiti-covered alley at golden hour)"

**Variable 3 — Outfit** *(unstyled models only):*
"What are they wearing? Describe the full outfit. (e.g. a black oversized hoodie, dark jeans, white sneakers)"

Skip Variable 3 for styled models — the outfit is locked to the styled image (Image 3).

---

## Step 5 — Name the output

Derive a slug from the model name, product name, and a short location descriptor:
- `jade-cloudmerino-paris-cafe`
- `marcus-rippy-cap-urban-walk`

Ask the user to confirm or rename.

---

## Step 6 — Write product-ugc-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/product-ugc/[output-name]/
  product-ugc-spec.json
```

**product-ugc-spec.json — styled model:**
```json
{
  "output_name": "jade-cloudmerino-paris-cafe",
  "brand": "[brand-name]",
  "model_type": "styled",
  "model_dir": "brands/[brand-name]/models/jade",
  "styled_dir": "brands/[brand-name]/styled/jade-cloudmerino-tshirt",
  "product_image": "brands/[brand-name]/brand-identity/product-images/cloudmerino-66-t-shirt.jpg",
  "action": "sitting at an outdoor café table, leaning slightly forward",
  "location": "A sunlit café terrace in Paris, warm afternoon light, blurred street and pedestrians behind",
  "outfit": "must perfectly match image 3"
}
```

**product-ugc-spec.json — unstyled model:**
```json
{
  "output_name": "marcus-rippy-cap-urban-walk",
  "brand": "[brand-name]",
  "model_type": "unstyled",
  "model_dir": "brands/[brand-name]/models/marcus",
  "styled_dir": null,
  "product_image": "brands/[brand-name]/brand-identity/product-images/rippy-air-trail-cap.jpg",
  "action": "walking down a street, mid-stride",
  "location": "Busy urban high street, motion-blurred cars and shop fronts in background",
  "outfit": "A black oversized hoodie, dark jeans, white sneakers"
}
```

---

## Step 7 — Generate image

Run from the project root:

```bash
python3 skills/references/generate-product-ugc.py brands/[brand-name]/product-ugc/[output-name] --image
```

**Reference images passed in order:**
- Image 1: product image — what the model is holding
- Image 2: `brands/[brand-name]/models/[name]/headshot.png` — identity
- Image 3 (styled only): `brands/[brand-name]/styled/[name]/[name]_v{n}.png` — outfit (script auto-detects the latest version)

Cost: ~$0.12

---

## Step 8 — Review and decide

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/product-ugc/[output-name]/[output-name]_v1.png`

Ask: "Happy with this image? You can:
- **Continue** — pick a version to use for the video, then move on
- **Regenerate** — run again to get another version
- **Adjust** — change the action, location, outfit, or product and regenerate"

If more than one version exists when the user is ready to continue, ask which they want to use for the video.

**To regenerate:**
```bash
python3 skills/references/generate-product-ugc.py brands/[brand-name]/product-ugc/[output-name] --image
```

**To adjust variables:** update `product-ugc-spec.json` and re-run.

---

## Step 9 — Video: collect inputs

Once the user is happy with the image, ask:

**Script:** "What should they say in the video? Paste the script."

**Voice and delivery notes:** "Any notes on accent, tone, pace, or energy? (e.g. 'Australian accent, upbeat and conversational', 'calm and authoritative, slight American accent')"

**Duration:** "How long? Options: **4s, 6s, or 8s** (Veo 3.1 only supports these three values)"

---

## Step 10 — Update product-ugc-spec.json with video inputs

Add video fields and the chosen image version:

```json
{
  ...existing fields...,
  "video_image_version": 2,
  "script": "This cap is everything. The Rippy Air Trail from Satisfy — lightweight, breathable, and it just works for everything.",
  "voice_notes": "Australian accent, relaxed and genuine. Not salesy.",
  "duration": "8"
}
```

`video_image_version` tells the script which versioned image to use. If not set, it uses the latest.

---

## Step 11 — Generate video

Run from the project root:

```bash
python3 skills/references/generate-product-ugc.py brands/[brand-name]/product-ugc/[output-name] --video
```

Uploads the chosen image to FAL, combines script + voice notes as the prompt, calls Veo 3.1 at 9:16 1080p for the requested duration.

Cost: ~$0.60 for 4s · ~$0.90 for 6s · ~$1.20 for 8s at 1080p with audio.

---

## Step 12 — Present the result

Tell the user the exact path where the video was saved, e.g.:
`brands/[brand-name]/product-ugc/[output-name]/[output-name]-video.mp4`

Ask: "Happy with the video? Or would you like to regenerate, adjust the script, or change the delivery notes?"

**To regenerate video:**
```bash
python3 skills/references/generate-product-ugc.py brands/[brand-name]/product-ugc/[output-name] --video
```

**To run image + video in one go:**
```bash
python3 skills/references/generate-product-ugc.py brands/[brand-name]/product-ugc/[output-name] --image --video
```

---

## Notes

- Each brand has its own `product-ugc/` subfolder — multiple brands can run independent product UGC workflows in the same project
- Image reference order matters: product (Image 1) → headshot (Image 2) → styled body (Image 3). The script handles this automatically.
- Product rendering precision depends on the quality of the product image — clean, well-lit packshots produce the best hold renders
- If the product in the output looks inaccurate or labels are wrong, regenerate — product fidelity varies with image complexity
- Audio is generated automatically by Veo 3.1 — no separate flag needed
- Video duration is locked to 4s, 6s, or 8s — these are the only values Veo 3.1 supports. Always default to 1080p.
