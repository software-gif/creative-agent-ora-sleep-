---
name: product-shoot
description: Run when the user wants to create a product shot, lifestyle product image, or place a product into a scene using reference images, or use the /product-shoot command. Takes a composition reference image, a product image, and an optional lighting reference, then generates a photorealistic product shot via Nano Banana 2. Output saved under the active brand folder.
---

# Product Shots

Places a product into a composition reference image, optionally matching the lighting and tonal atmosphere of a third reference.

Three inputs drive the output:
1. **Composition reference** (required) — sets the framing, environment, and scene
2. **Product image** (required) — the product to place into the scene
3. **Lighting reference** (optional) — sets the lighting quality, direction, and tonal mood

Output saved to `./brands/[brand-name]/product-shoot/[output-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Create reference folders

Create the shared reference folders if they don't exist:
```bash
mkdir -p brands/[brand-name]/product-shoot/composition-references
mkdir -p brands/[brand-name]/product-shoot/lighting-references
```

Tell the user what this skill needs and where to put things. Lead with the explanation — do NOT mention folder contents or whether folders are empty before explaining what they're for. Be clear — they may not know what "composition reference" means:

> "To generate your product shot I need two things from you (a third is optional):
>
> **1. Composition reference** (required)
> A photo that shows the kind of scene, framing, and environment you want — e.g. a hand holding a product, an overhead flat-lay on marble, a bottle leaning against a wall. The product in the reference photo doesn't matter — I'll swap it out for yours. Save it to:
> `brands/[brand-name]/product-shoot/composition-references/`
>
> **2. Product image** (required)
> I'll pull this from your brand's product images folder — just tell me which product you want to shoot.
>
> **3. Lighting reference** (optional)
> A photo whose lighting mood you want to match — e.g. a moody dark studio shot, a soft natural window light image. If you skip this, I'll use the lighting from your composition reference as-is. Save it to:
> `brands/[brand-name]/product-shoot/lighting-references/`
>
> Name your files clearly — e.g. `hand-hold-concrete.jpg`, `moody-dark-studio.jpg`. Drop them in and let me know when ready."

After delivering this message, check what's already in each folder. If either has files, follow up with what's already available so the user knows they can reuse them:
```bash
ls brands/[brand-name]/product-shoot/composition-references/
ls brands/[brand-name]/product-shoot/lighting-references/
```

---

## Step 3 — Select composition reference

Show available composition references:
```
Composition references:
  1. hand-hold-dark-bg.jpg
  2. overhead-marble.jpg
  3. hero-leaning-wall.jpg
```

Ask: "Which composition reference would you like to use? (number or name)"

If the folder is empty, tell the user:
> "No composition references found. Drop at least one image into `brands/[brand-name]/product-shoot/composition-references/` and let me know."

Wait for confirmation before proceeding.

---

## Step 4 — Select product

Ask: "Which product would you like to shoot?"

Check `brands/[brand-name]/brand-identity/product-images/` for a match. Show what was found:
```
Found:
  ✓ hey-bud-face-tint.jpg

Not found:
  ✗ [product name] — not in product images
```

**If not found:**
1. Check `brands/[brand-name]/brand-identity/products.json` for the product URL
2. Try to download the product image:
   ```bash
   curl -L "[product-image-url]" -o "brands/[brand-name]/brand-identity/product-images/[slug].jpg"
   ```
3. If that fails, ask the user to drop the image into `brand-identity/product-images/` and confirm.

---

## Step 5 — Select lighting reference (optional)

Show available lighting references:
```
Lighting references:
  1. talgh-soft-wrap.jpg
  2. moody-dark-studio.jpg

(or skip to use the composition reference's existing lighting)
```

Ask: "Would you like to apply a lighting reference? Pick one from the list, or say 'skip' to use the composition reference's lighting as-is."

If the folder is empty, skip this step and note that no lighting reference will be used.

---

## Step 6 — Additional notes

Ask: "Any specific requests? e.g. 'add a slight shadow under the product', 'keep the background muted', 'match the product orientation to the original'. Leave blank to skip."

These get appended to the prompt.

---

## Step 7 — Aspect ratio

Ask: "What aspect ratio? Default is `3:4`. Other options: `1:1`, `4:5`, `2:3`, `4:3`, `16:9`, `9:16`."

Use `3:4` if the user doesn't specify.

---

## Step 8 — Name the output

Derive a slug from the product name and composition reference:
- `hey-bud-tint-hand-hold`
- `mutimer-jacket-overhead-marble`
- `brand-hero-leaning-wall`

Ask the user to confirm or rename.

---

## Step 9 — Write product-shot-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/product-shoot/[output-name]/
  product-shot-spec.json
```

**With lighting reference:**
```json
{
  "output_name": "hey-bud-tint-hand-hold",
  "brand": "[brand-name]",
  "product_name": "Hey Bud Acne Face Tint",
  "product_image": "brands/[brand-name]/brand-identity/product-images/hey-bud-face-tint.jpg",
  "composition_reference": "brands/[brand-name]/product-shoot/composition-references/hand-hold-dark-bg.jpg",
  "lighting_reference": "brands/[brand-name]/product-shoot/lighting-references/talgh-soft-wrap.jpg",
  "additional_notes": "Add a slight shadow beneath the product.",
  "aspect_ratio": "3:4"
}
```

**Without lighting reference:**
```json
{
  "output_name": "hey-bud-tint-hand-hold",
  "brand": "[brand-name]",
  "product_name": "Hey Bud Acne Face Tint",
  "product_image": "brands/[brand-name]/brand-identity/product-images/hey-bud-face-tint.jpg",
  "composition_reference": "brands/[brand-name]/product-shoot/composition-references/hand-hold-dark-bg.jpg",
  "lighting_reference": null,
  "additional_notes": "",
  "aspect_ratio": "3:4"
}
```

---

## Step 10 — Generate

Run from the project root:

```bash
python3 skills/references/generate-product-shot.py brands/[brand-name]/product-shoot/[output-name]
```

**Prompt used (with lighting reference):**
> "Regenerate image 1 by substituting its primary subject with the exact product shown in image 2. Preserve everything that makes image 1 compelling: the camera angle and perspective exactly (low angle, eye level, overhead — whatever is shown), the lighting quality and direction, the background, colour grade, depth of field, mood, and overall atmosphere. The product from image 2 must match in form, proportions, and branding exactly — do not distort its shape to fit the reference product's silhouette. Only the subject changes. Everything else stays. Adopt the lighting and tonal atmosphere of image 3."

**Prompt used (without lighting reference):**
> "Regenerate image 1 by substituting its primary subject with the exact product shown in image 2. Preserve everything that makes image 1 compelling: the camera angle and perspective exactly (low angle, eye level, overhead — whatever is shown), the lighting quality and direction, the background, colour grade, depth of field, mood, and overall atmosphere. The product from image 2 must match in form, proportions, and branding exactly — do not distort its shape to fit the reference product's silhouette. Only the subject changes. Everything else stays."

Additional notes are appended to either prompt if provided.

Image order passed to Nano Banana: composition reference → product image → lighting reference (if present).

Cost: ~$0.12 per image.

---

## Step 11 — Present the result

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/product-shoot/[output-name]/[output-name]_v1.png`

Ask: "Happy with this? Or would you like to regenerate, try a different composition, or swap the lighting reference?"

Once the user is happy, suggest the next step:

> "Great shot. If you'd like to animate this into a short video clip, run `/add-motion`."

**To regenerate (same spec):**
```bash
python3 skills/references/generate-product-shot.py brands/[brand-name]/product-shoot/[output-name]
```
Saves as the next version — does not overwrite.

**To try a different composition:** update `composition_reference` in `product-shot-spec.json` and re-run.

**To add or change lighting:** update `lighting_reference` and re-run.

**To adjust the prompt:** update `additional_notes` and re-run.

---

## Notes

- Composition references and lighting references live in shared folders at `brands/[brand-name]/product-shoot/` — they can be reused across multiple product shots without re-uploading
- The composition reference drives the entire scene — choose it based on the framing and environment you want, regardless of what product is in it
- A strong lighting reference from a brand like Aesop, Talgh, or Byredo will pull the tonal atmosphere of that aesthetic into the output
- Each brand has its own `product-shoot/` subfolder — multiple brands can run independent product shot workflows in the same project
