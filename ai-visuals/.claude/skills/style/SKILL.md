---
name: style
description: Run when the user wants to style a model, place clothing on a model, dress a model in a product, or use the /style command. Takes a generated model (headshot + full body) and a product image from the brand folder, then synthesises the clothing onto the model using FAL API. Output saved under the active brand folder.
---

# Style

Places product clothing onto a generated model. Produces a full-body studio image with the model wearing the specified product.

Output saved to `./brands/[brand-name]/styled/[output-name]/[output-name]_v1.png`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Select a model

Scan `./brands/[brand-name]/models/` for subfolders containing both `headshot.png` and `fullbody.png`.

Present available models:
```
Available models:
  • jade
  • marcus-02
  • hero-female
```

Ask: "Which model would you like to style?"

If no complete models exist, tell the user:
> "No models found for [brand]. Use `/model` to create one first."

---

## Step 3 — Select product(s)

Ask: "Which product(s) would you like to place on the model?"

The user may specify:
- **Brand products** — match against `./brands/[brand-name]/brand-identity/product-images/`
- **Non-brand items** — accessories, shoes, or styling the brand doesn't sell (e.g. "brown loafers", "white socks"). These have no product image. Capture them in `notes` — they will be included in the generation prompt.

Show what was found:
```
Found in brands/[brand-name]/brand-identity/product-images/:
  ✓ linea-jacket-tobacco.png
  ✓ cowboy-denim-carbon.png
  ✗ dusty brown loafers — no product image, will be added as a styling note
```

**For brand products not found in the folder:**
Ask the user to either:
- Drop the image into `brands/[brand-name]/brand-identity/product-images/` and confirm
- Paste an image URL — download it:
  ```bash
  curl -L "[url]" -o "brands/[brand-name]/brand-identity/product-images/[slug].jpg"
  ```

**For non-brand items (shoes, socks, belts, etc.):**
No image needed. Describe them precisely in `notes` — the script appends notes to the generation prompt. Be specific: colour, material, style (e.g. "dusty brown suede loafers, minimal sole, no branding").

---

## Step 4 — Check for a complete outfit

If the selected product(s) don't form a complete outfit (e.g. only a top, only a jacket), ask:

> "The [product] only covers the [top/bottom/half]. What should the model wear for the rest? You can:
> - Name another product from the brand folder
> - Describe the styling (e.g. 'neutral grey tailored trousers', 'dusty brown loafers') — no image needed
> - Leave it to the model to fill in neutrally"

If the user describes styling rather than providing a product image, write it to `notes` in the spec — it will be passed directly into the generation prompt. If they provide an additional product image, add it to `product_images`.

---

## Step 5 — Name the output

Derive a slug from the model name and product name(s):
- `jade-cloudmerino-tshirt`
- `marcus-techsilk-shorts`
- `hero-female-mothtech-jacket`

Ask the user to confirm or rename.

---

## Step 6 — Write style-spec.json

Create the output folder and write the spec:

```
brands/[brand-name]/styled/[output-name]/
  style-spec.json
```

**style-spec.json format:**
```json
{
  "brand": "[brand-name]",
  "model_name": "jade",
  "model_dir": "brands/[brand-name]/models/jade",
  "product_names": ["CloudMerino 66 T-Shirt"],
  "product_images": [
    "brands/[brand-name]/brand-identity/product-images/cloudmerino-66-t-shirt.jpg"
  ],
  "output_dir": "brands/[brand-name]/styled/jade-cloudmerino-tshirt",
  "notes": "Dusty brown suede loafers, minimal sole, no branding."
}
```

`notes` is appended to the generation prompt as additional styling instructions. Use it for any items that don't have a product reference image — shoes, socks, belts, jewellery, styling details (e.g. jacket zipped vs open), or garment fit notes. Leave empty if not needed.

---

## Step 7 — Generate

Run from the project root:

```bash
python3 skills/references/generate-style.py brands/[brand-name]/styled/[output-name]
```

Uploads face reference, body reference, then product reference(s) to FAL storage and calls `fal-ai/nano-banana-2/edit` at 2K, 3:4.

Cost: ~$0.12 per image.

---

## Step 8 — Present the result

Once complete, tell the user the exact path where the file was saved using the actual versioned filename, e.g.:
`brands/[brand-name]/styled/[output-name]/[output-name]_v1.png`

Ask: "Happy with this? Or would you like to regenerate or try a different product?"

Once the user is happy, suggest next steps:

> "Your styled model is ready. From here you can:
> - Run `/clothing-shoot` to place them into a location or campaign environment
> - Run `/ugc` to generate a selfie and talking-head video
> - Run `/product-ugc` to generate a selfie of them holding a product"

**To regenerate (same spec):**
```bash
python3 skills/references/generate-style.py brands/[brand-name]/styled/[output-name]
```
Saves as the next version — does not overwrite previous outputs.

**To try a different product on the same model:** update `style-spec.json` and re-run.

---

## Notes

- Each brand has its own `styled/` subfolder — multiple brands can run independent styling workflows in the same project
- Reference image order matters: face → body → product. The script handles this automatically.
- Multiple product images are supported for multi-piece outfits — add them all to `product_images`
- If body proportions look wrong or the body is cropped, regenerate — this is prompt adherence variance
