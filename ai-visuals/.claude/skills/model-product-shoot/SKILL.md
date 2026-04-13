---
name: model-product-shoot
description: Run when the user wants to create a lifestyle or editorial shot of a model interacting with or holding a product — not a selfie or UGC format. Takes a reference image showing the desired scene style, a product image, and a styled model. Composites all three into a single campaign-quality image using Nano Banana 2. Output saved under the active brand folder.
---

# Model Product Shoot

Places a styled model and a product into a reference scene. The reference image drives the composition, framing, and lighting — the model and product are swapped in while preserving everything else.

Four images passed to Nano Banana in this order:
1. **Reference image** — composition, framing, lighting
2. **Product image** — the product to feature
3. **Model headshot** — model identity reference
4. **Styled model image** — clothing and body reference

Output saved to `./brands/[brand-name]/model-product-shoot/[output-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Create reference folder and collect reference image

Create the shared composition references folder:
```bash
mkdir -p brands/[brand-name]/model-product-shoot/composition-references
```

List any images already in the folder. If empty, tell the user:

> "I need a **reference image** — this is a photo showing the kind of scene, framing, and lighting you want. It could be a model holding a product on a track, applying something post-workout, or any lifestyle scene that fits the vibe. The model and product in the reference don't matter — I'll swap them out.
>
> Drop it into:
> `brands/[brand-name]/model-product-shoot/composition-references/`
>
> Name it clearly — e.g. `track-hold.jpg`, `postrun-apply.jpg`. Let me know when it's in."

If images are already present, list them and ask which to use.

Wait for the user to confirm before proceeding.

---

## Step 3 — Select product

Ask: "Which product should the model be holding or interacting with?"

Check `brands/[brand-name]/brand-identity/product-images/` for a match. Show what was found:
```
Found:
  ✓ freeze-roll-on.jpg

Not found:
  ✗ [product name] — not in product images
```

**If not found:**
1. Check `brands/[brand-name]/brand-identity/products.json` for the product and its image URL
2. Try to download it:
   ```bash
   curl -L "[product-image-url]" -o "brands/[brand-name]/brand-identity/product-images/[slug].jpg"
   ```
3. If the download fails or the product isn't in products.json, create a product upload folder and ask the user:
   ```bash
   mkdir -p brands/[brand-name]/model-product-shoot/product-uploads
   ```
   > "I couldn't find that product image. Drop it into:
   > `brands/[brand-name]/model-product-shoot/product-uploads/`
   > and let me know when it's in."

---

## Step 4 — Select model and styled image

Scan `brands/[brand-name]/models/` for subfolders containing `headshot.png` and `fullbody.png`.

Present available models:
```
Available models:
  • sofia
  • marcus
```

Ask: "Which model would you like to feature?"

Then scan `brands/[brand-name]/styled/` for output folders that reference the selected model. List the styled outputs found:
```
Styled outputs for sofia:
  • sofia-allblack-athletic (sofia-allblack-athletic_v1.png)
  • sofia-puresport-cap (sofia-puresport-cap_v2.png)
```

Ask: "Which styled outfit would you like to use?"

Use the most recent versioned file (highest version number, or the unversioned file if only one exists).

If no styled outputs exist for the selected model, tell the user:
> "No styled outputs found for [model]. Run `/style` first to dress the model."

---

## Step 5 — Aspect ratio

Ask: "What aspect ratio? Default is `3:4`. Other options: `1:1`, `4:5`, `2:3`, `9:16`, `16:9`."

Use `3:4` if the user doesn't specify.

---

## Step 6 — Name the output

Derive a slug from the model name, product, and reference:
- `sofia-rollerbottle-track`
- `marcus-creatine-postrun`

Ask the user to confirm or rename.

---

## Step 7 — Write model-product-shoot-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/model-product-shoot/[output-name]/
  model-product-shoot-spec.json
```

```json
{
  "output_name": "sofia-rollerbottle-track",
  "brand": "puresport",
  "product_name": "Freeze Roll On",
  "product_image": "brands/puresport/brand-identity/product-images/freeze-roll-on.jpg",
  "composition_reference": "brands/puresport/model-product-shoot/composition-references/track-hold.jpg",
  "model_name": "sofia",
  "model_headshot": "brands/puresport/models/sofia/headshot.png",
  "styled_image": "brands/puresport/styled/sofia-allblack-athletic/sofia-allblack-athletic_v1.png",
  "aspect_ratio": "3:4"
}
```

---

## Step 8 — Generate

Run from the project root:

```bash
python3 skills/references/generate-model-product-shoot.py brands/[brand-name]/model-product-shoot/[output-name]
```

Uploads images in order: composition reference → product → headshot → styled image.

Calls `fal-ai/nano-banana-2/edit` at 2K in the chosen aspect ratio.

Cost: ~.12 per image.

---

## Step 9 — Present the result

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/model-product-shoot/[output-name]/[output-name]_v1.png`

Ask: "Happy with this? Or would you like to regenerate, swap the reference, or try a different product?"

Once the user is happy, suggest the next step:

> "Great shot. If you'd like to animate this into a short video clip, run `/add-motion`."

**To regenerate (same spec):**
```bash
python3 skills/references/generate-model-product-shoot.py brands/[brand-name]/model-product-shoot/[output-name]
```
Each run saves as the next version — `[output-name]_v1.png`, `[output-name]_v2.png`, etc. Previous outputs are never overwritten.

**To try a different reference:** update `composition_reference` in the spec and re-run.
**To swap the product:** update `product_image` and `product_name` and re-run.
**To change the outfit:** update `styled_image` and re-run.

---

## Notes

- Image order matters: composition → product → headshot → styled model. The script handles this automatically.
- The reference image is the strongest driver of the output — choose it based on the scene and energy you want, not the product or model in it
- Multiple brands have their own `model-product-shoot/` subfolder — independent workflows can run side by side
- Composition references are shared across all outputs for that brand — reuse them freely
