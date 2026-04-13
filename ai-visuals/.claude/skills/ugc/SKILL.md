---
name: ugc
description: Run when the user wants to create UGC content, a UGC-style selfie, a talking-head video, creator-to-camera content, or use the /ugc command. Takes a model (styled or unstyled), generates an ultra-realistic iPhone selfie image, then optionally continues into a UGC video using Veo 3.1 Fast at 1080p. Output saved under the active brand folder.
---

# UGC

Two-stage workflow:
1. **UGC image** — ultra-realistic iPhone front-camera selfie at 9:16 2K
2. **UGC video** — talking-head video from the selfie at 9:16 1080p via Veo 3.1 Fast

Output saved to `./brands/[brand-name]/ugc/[output-name]/`.

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

## Step 3 — Collect variables

Ask for all in one message:

**Variable 1 — Action:**
"What is the model doing? (e.g. standing, sitting at a café, walking down a street, leaning against a wall)"

**Variable 2 — Location:**
"Where are they? Describe the environment in detail. (e.g. a busy urban high street with bokeh traffic in the background, a sunlit café terrace in Paris, a graffiti-covered alley at golden hour)"

**Variable 3 — Outfit** *(unstyled models only):*
"What are they wearing? Describe the full outfit. (e.g. a black oversized hoodie, dark jeans, white sneakers)"

Skip Variable 3 for styled models — outfit is locked to the styled image.

---

## Step 4 — Name the output

Derive a slug from the model name and a short descriptor:
- `jade-paris-cafe`
- `marcus-urban-walk`
- `hero-golden-hour`

Ask the user to confirm or rename.

---

## Step 5 — Write ugc-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/ugc/[output-name]/
  ugc-spec.json
```

**ugc-spec.json — styled model:**
```json
{
  "output_name": "jade-paris-cafe",
  "brand": "[brand-name]",
  "model_type": "styled",
  "model_dir": "brands/[brand-name]/models/jade",
  "styled_dir": "brands/[brand-name]/styled/jade-cloudmerino-tshirt",
  "action": "sitting at an outdoor café table, leaning slightly forward",
  "location": "A sunlit café terrace in Paris, warm afternoon light, blurred street and pedestrians behind",
  "outfit": "must perfectly match image 2"
}
```

**ugc-spec.json — unstyled model:**
```json
{
  "output_name": "marcus-urban-walk",
  "brand": "[brand-name]",
  "model_type": "unstyled",
  "model_dir": "brands/[brand-name]/models/marcus",
  "styled_dir": null,
  "action": "walking down a street, mid-stride",
  "location": "Busy urban high street, motion-blurred cars and shop fronts in background",
  "outfit": "A black oversized hoodie, dark jeans, white sneakers"
}
```

---

## Step 6 — Generate image

Run from the project root:

```bash
python3 skills/references/generate-ugc.py brands/[brand-name]/ugc/[output-name] --image
```

Reference images passed in order:
- Image 1: `brands/[brand-name]/models/[name]/headshot.png` — identity
- Image 2 (styled only): `brands/[brand-name]/styled/[name]/[name]_v{n}.png` — outfit (script auto-detects the latest version)

Cost: ~$0.12

---

## Step 7 — Review and decide

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/ugc/[output-name]/[output-name]_v1.png`

Ask: "Happy with this image? You can:
- **Continue** — pick a version to use for the video, then move to Step 8
- **Regenerate** — run again to get another version
- **Adjust** — change the action, location, or outfit and regenerate"

If more than one version exists when the user is ready to continue, ask which they want to use for the video.

**To regenerate:**
```bash
python3 skills/references/generate-ugc.py brands/[brand-name]/ugc/[output-name] --image
```

---

## Step 8 — Video: collect inputs

Once the user is happy with the image, ask:

**Script:** "What should they say in the video? Paste the script."

**Voice and delivery notes:** "Any notes on accent, tone, pace, or energy? (e.g. 'Australian accent, upbeat and conversational', 'calm and authoritative, slight American accent')"

**Duration:** "How long? Options: **4s, 6s, or 8s** (Veo 3.1 Fast only supports these three values)"

---

## Step 9 — Update ugc-spec.json with video inputs

Add video fields to the existing spec:

```json
{
  ...existing fields...,
  "script": "I've been obsessed with this tee all summer. It's the CloudMerino 66 from Satisfy — lightweight, breathable, and it just feels incredible.",
  "voice_notes": "Australian accent, relaxed and genuine, like talking to a friend. Not salesy.",
  "duration": "8"
}
```

---

## Step 10 — Generate video

Run from the project root:

```bash
python3 skills/references/generate-ugc.py brands/[brand-name]/ugc/[output-name] --video
```

Uploads `ugc-image.png` to FAL, combines script + voice notes as the prompt, calls Veo 3.1 Fast at 9:16 1080p.

Cost: ~$0.60 for 4s · ~$0.90 for 6s · ~$1.20 for 8s at 1080p with audio.

---

## Step 11 — Present the result

Tell the user the exact path where the video was saved, e.g.:
`brands/[brand-name]/ugc/[output-name]/[output-name]-video.mp4`

Ask: "Happy with the video? Or would you like to regenerate, adjust the script, or change the delivery notes?"


**To regenerate video:**
```bash
python3 skills/references/generate-ugc.py brands/[brand-name]/ugc/[output-name] --video
```

**To run image + video together:**
```bash
python3 skills/references/generate-ugc.py brands/[brand-name]/ugc/[output-name] --image --video
```

---

## Notes

- Each brand has its own `ugc/` subfolder — multiple brands can run independent UGC workflows in the same project
- UGC image is always 9:16 to match the video format
- `generate_audio: true` is set — Veo 3.1 Fast generates audio alongside the video
- Duration is locked to 4, 6, or 8 seconds — Veo 3.1 Fast does not support other values
- The face in the video is driven by the UGC image. A strong, well-lit selfie = more consistent video output
- If the video doesn't match the script delivery, regenerate — Veo output varies by seed
