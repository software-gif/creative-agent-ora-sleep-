---
name: model
description: Run when the user wants to create a model, generate a character, or use the /model command. Collects model characteristics, generates a headshot and full-body casting digital via FAL API, and saves both under the active brand folder. The output is a matched headshot + full body pair — a complete model "digital" ready for styling and shoot workflows.
---

# Model

Generates a matched headshot + full-body casting digital for a brand model character.

Two images are produced:
1. **Headshot** — tight casting portrait, straight-on, clinical flash lighting
2. **Full body** — full-length casting digital using the headshot as a face reference

Both saved to `./brands/[brand-name]/models/[model-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first to set up their brand

---

## Step 2 — Collect characteristics

Ask the user for all of the following in one grouped message. Tell them to skip anything that doesn't apply (e.g. facial hair for a female model).

```
I need a few details to build your model. Fill in what applies:

DEMOGRAPHICS
Age:
Sex:
Ethnicity:

PHYSICAL FEATURES
Skin tone:
Face shape:
Jawline:
Cheekbones:
Cheeks:
Eye shape:
Eye colour:
Eyebrows:
Nose:
Lips:
Freckles:
Facial hair:

HAIR
Colour:
Style:

BUILD
Height:
Body type:

AESTHETIC NOTES
Tone:        (e.g. Natural, editorial, high fashion, athletic, commercial)
Expression:  (leave blank for neutral — the default)
```

Confirm back the full characteristics list before proceeding. Ask if they want to change anything.

---

## Step 3 — Name the model

Ask: "What would you like to name this model? This becomes the folder name — e.g. `jade`, `marcus-02`, `hero-female`."

Slug the name: lowercase, hyphens, no spaces or special characters.

---

## Step 4 — Write model-spec.json

Create the folder and write the spec:

```
brands/[brand-name]/models/[model-name]/
  model-spec.json
  characteristics.md
```

**model-spec.json format:**
```json
{
  "model_name": "[model-name]",
  "brand": "[brand-name]",
  "characteristics": "Age: 23\nSex: Female\nEthnicity: Asian\nSkin tone: Slightly olive, slight freckles\nFace shape: Oval\nJawline: Defined\nCheekbones: Prominent, high\nCheeks: Natural, strong and defined\nEye shape: Almond\nEye colour: Green\nEyebrows: Natural, medium thickness\nNose: Small, straight, lightly rounded tip\nLips: Plump, natural finish\nFreckles: Lightly scattered on nose and cheeks\nFacial hair: None\nHair colour: Light brown\nHair style: Mid-length, slight waves, centre part\nHeight: Average\nBody type: Slim\nTone: Natural, high fashion"
}
```

Format the characteristics as a flat newline-separated key: value list. Include only fields the user provided — omit blanks.

**characteristics.md** — a readable reference copy:
```markdown
# [Model Name] — Characteristics

## Demographics
Age: 23
Sex: Female
Ethnicity: Asian

## Physical features
Skin tone: Slightly olive, slight freckles
Face shape: Oval
...

## Hair
Colour: Light brown
Style: Mid-length, slight waves, centre part

## Build
Height: Average
Body type: Slim

## Aesthetic
Tone: Natural, high fashion
```

---

## Step 5 — Generate

Run from the project root:

```bash
python3 skills/references/generate-model.py brands/[brand-name]/models/[model-name]
```

This runs two FAL API calls in sequence:
1. Headshot — text-to-image at 2K, 3:4
2. Full body — image-reference edit at 2K, 3:4, using the headshot as face reference

Cost: ~$0.24 total (2 × $0.12 at 2K).

---

## Step 6 — Present the results

Once generation completes:
- Tell the user the exact save paths, e.g.:
  - `brands/[brand-name]/models/[model-name]/headshot.png`
  - `brands/[brand-name]/models/[model-name]/fullbody.png`
- Ask: "Happy with this model? Or would you like to regenerate or tweak the characteristics?"

Once the user is happy, suggest the next step:

> "Your model is ready. When you're ready to place clothing on them, run `/style` to dress the model in a product from your brand."

---

## Regeneration and iteration

**Regenerate both images (same characteristics):**
```bash
python3 skills/references/generate-model.py brands/[brand-name]/models/[model-name]
```
Overwrites `headshot.png` and `fullbody.png`.

**Tweak characteristics and regenerate:**
1. Ask which characteristics to change
2. Update `model-spec.json` and `characteristics.md`
3. Re-run the script

**Regenerate full body only (keep headshot):**
Not supported directly — the full body uses the headshot as face reference, so both regenerate together for a consistent match. The headshot step is fast (~15 seconds).

---

## Notes

- Each brand has its own `models/` subfolder — multiple brands can have separate model rosters in the same project
- Models within a brand can be reused across all styling and shoot workflows for that brand
- Multiple models per brand are fine: `brands/[brand]/models/jade/`, `brands/[brand]/models/marcus/`
- If the script fails with a FAL API error, check `.env` has a valid `FAL_KEY`
