---
name: clothing-shoot
description: Run when the user wants to place a styled model into a location, create a fashion campaign image, shoot a model in an environment, or use the /clothing-shoot command. Takes a styled model image and an environment reference image, then generates a campaign-quality fashion photograph with the model grounded in that location. Output saved under the active brand folder.
---

# Clothing Shoot

Places a styled model into a location environment. Produces a campaign-quality fashion photograph with the model grounded in the scene.

Three reference images drive the output:
1. **Environment reference** — location, lighting, perspective, depth of field
2. **Styled image** — the model's outfit and proportions
3. **Face reference** — identity consistency (headshot)

Output saved to `./brands/[brand-name]/clothing-shoot/[output-name]/shoot_v1.png`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Select a styled model

Scan `./brands/[brand-name]/styled/` for subfolders containing a versioned image matching `[folder-name]_v1.png` (e.g. `jade-cloudmerino-tshirt_v1.png`). The script auto-detects the latest version.

Present available options:
```
Available styled models:
  • jade-cloudmerino-tshirt
  • marcus-techsilk-shorts
  • hero-female-mothtech-jacket
```

Ask: "Which styled model would you like to use for this shoot?"

If no styled outputs exist:
> "No styled models found for [brand]. Use `/model` to create a model first, then `/style` to dress them."

Once selected, read `brands/[brand-name]/styled/[name]/style-spec.json` to get `model_dir` for the face reference.

---

## Step 3 — Get the environment reference image

At the start of every clothing-shoot session, create the environment references folder if it doesn't exist:
```bash
mkdir -p brands/[brand-name]/clothing-shoot/environment-references
```

Then list what's in it:
```bash
ls brands/[brand-name]/clothing-shoot/environment-references/
```

**If images are present**, show them and ask which to use:
```
Environment references available:
  1. jazz-room.jpg
  2. concrete-alley.jpg
  3. rooftop-golden-hour.jpg

Which would you like to use? (number or name)
```

**If the folder is empty**, tell the user:
> "Drop your environment reference images into `brands/[brand-name]/clothing-shoot/environment-references/` — then let me know and I'll continue."

Wait for confirmation before proceeding. Do not generate without a saved reference image.

---

## Step 4 — Get pose direction

Ask: "How should the model be posed or what should they be doing in this scene? Be specific — the more direction you give, the better the pose will suit the environment."

Examples:
- `Walking through the space, mid-stride, looking slightly off-camera`
- `Leaning against the wall, arms crossed, direct gaze`
- `Caught mid-turn, one hand in pocket, looking back over shoulder`

This is required — don't proceed without it.

---

## Step 5 — Aspect ratio

Ask: "What aspect ratio do you want? Options: `1:1`, `4:5`, `3:4`, `2:3`, `9:16`, `16:9`, `3:2`"

Default to `4:5` if the user isn't sure.

---

## Step 6 — Name the output

Derive a slug from the styled model name and a short environment descriptor:
- `jade-cloudmerino-urban-alley`
- `marcus-techsilk-rooftop`
- `hero-female-mothtech-forest-trail`

Ask the user to confirm or rename.

---

## Step 7 — Write shoot-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/clothing-shoot/[output-name]/
  shoot-spec.json
  env-reference.jpg  (if downloaded)
```

**shoot-spec.json format:**
```json
{
  "brand": "[brand-name]",
  "output_name": "jade-cloudmerino-urban-alley",
  "styled_dir": "brands/[brand-name]/styled/jade-cloudmerino-tshirt",
  "model_dir": "brands/[brand-name]/models/jade",
  "env_reference": "brands/[brand-name]/clothing-shoot/jade-cloudmerino-urban-alley/env-reference.jpg",
  "pose_direction": "Walking through the space, mid-stride, looking slightly off-camera",
  "aspect_ratio": "4:5",
  "output_dir": "brands/[brand-name]/clothing-shoot/jade-cloudmerino-urban-alley"
}
```

`model_dir` is pulled from the styled output's `style-spec.json` — no need to ask the user.

---

## Step 8 — Generate

Run from the project root:

```bash
python3 skills/references/generate-clothing-shoot.py brands/[brand-name]/clothing-shoot/[output-name]
```

Uploads environment, styled image, and face reference to FAL storage in that order, then calls `fal-ai/nano-banana-2/edit` at 2K in the specified aspect ratio.

Cost: ~$0.12 per image.

---

## Step 9 — Present the result

Once complete, tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/clothing-shoot/[output-name]/shoot_v1.png`

Ask: "Happy with this? Or would you like to regenerate, adjust the pose, or try a different environment?"

Once the user is happy, suggest the next step:

> "Looking good. If you'd like to bring this image to life, run `/add-motion` to animate it into a short video clip."

**To regenerate (same spec):**
```bash
python3 skills/references/generate-clothing-shoot.py brands/[brand-name]/clothing-shoot/[output-name]
```
Saves as the next version — does not overwrite previous outputs.

**To adjust pose:** update `pose_direction` in `shoot-spec.json` and re-run.

**To try a different environment:** replace the env-reference image, update the path in `shoot-spec.json` if needed, re-run.

**To use a different styled model in the same environment:** update `styled_dir` and `model_dir` in `shoot-spec.json`, re-run.

---

## Notes

- Each brand has its own `clothing-shoot/` subfolder — multiple brands can run independent shoot workflows in the same project
- Reference image order matters: environment → styled → face. The script handles this automatically.
- A strong, clearly lit environment reference produces significantly better results than a vague one
- If the model appears floating or unnaturally placed, regenerate — organic placement varies by scene complexity
