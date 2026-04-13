---
name: packshot
description: Run when the user wants to generate a packshot, clean product image, ghost mannequin shot, flat-lay, or studio product photography, or use the /packshot command. Analyses product reference images using Claude, generates a tailored staging prompt, then renders a clean commercial packshot via Nano Banana 2. Output saved under the active brand folder.
---

# Packshots

Three-step workflow:
1. **Claude analyses** the product reference images and generates a tailored staging prompt
2. **Append** a fixed render specification snippet to Claude's output
3. **Generate** the packshot via Nano Banana 2 using the combined prompt + product reference images

Output saved to `./brands/[brand-name]/packshots/[output-name]/`.

---

## Step 1 — Select brand

Scan `./brands/` for subfolders that contain a `brand-identity/visual-guidelines.md` file.

- **One brand found:** use it automatically and confirm: "Using brand: [name]"
- **Multiple brands found:** list them and ask which to use
- **None found:** tell the user to run `/brand` first

---

## Step 2 — Ask for product description and output name

Ask in one message:

**Product description:** "Give me a brief product description — e.g. `skincare bottle`, `running cap`, `hooded sweatshirt`. One short phrase is enough."

**Output name:** Derive a slug from the product description (e.g. `skincare-bottle`, `rippy-cap`, `mothtech-hoodie`). Confirm with the user or let them rename it.

---

## Step 3 — Create reference folder and collect product images

Create the reference folder first, then tell the user:
```bash
mkdir -p brands/[brand-name]/packshots/[output-name]/product-references
```

Tell the user:
> "Drop your product reference images into:
> `brands/[brand-name]/packshots/[output-name]/product-references/`
>
> These are the images Claude and Nano Banana will use to understand the product. More angles = better result. Let me know when you've added them."

Wait for the user to confirm before proceeding.

Once confirmed, list the images found:
```
Found 3 product reference image(s):
  • front.jpg
  • back.jpg
  • detail.jpg
```

If the folder is empty, ask again.

---

## Step 4 — Ask for aspect ratio

Ask: "What aspect ratio do you want? Default is `3:4`. Other options: `1:1`, `4:5`, `2:3`, `4:3`, `16:9`"

Use `3:4` if the user doesn't specify.

---

## Step 5 — Run Claude analysis (Step 1 of the packshot workflow)

Read all images from `brands/[brand-name]/packshots/[output-name]/product-references/` using the Read tool.

Then run the following analysis prompt with all product reference images attached. Replace `Variable 1` with the product description the user gave:

---

*Analysis prompt to run internally:*

"Act as a specialist in commercial product imaging. You have been provided with an image containing [Variable 1]. Conduct a deep visual audit of this item only.

Phase A: Staging Logic Selection Choose the single most effective framing archetype from the following options to best showcase the specific item:
1. Produce a high-end commercial ghost-mannequin packshot, showing the item in a three-dimensional, hollow-body floating state.
2. Produce a clean, professional top-down flat-lay packshot, oriented with surgical precision for e-commerce.
3. Produce a stylized streetwear-inspired folded packshot, emphasizing the item's texture and silhouette in a relaxed studio setting.

Phase B: Text Extraction and Mapping If the item features any inscriptions, logos, or branding, transcribe them exactly. Output this data using the header " Product Typography and Alignment Syntax:" followed by a line-by-line breakdown of every visible string, preserving original capitalisation, spelling, and stating their placement hierarchy and positioning on the product.

Phase C: Structural and Material Narrative Compose an intricate, jargon-free description of the item's physical properties. Emphasize the tactile nature of the materials (e.g., dense-knit fleece, technical weather-resistant nylon, brushed jersey), the specific hardware details (industrial zippers, aglet-tipped cords), and the architectural cut of the garment. Do not reference the background, environment, or any human figure.

Output Format: Present the exact sentence from the chosen staging snippet in Phase A, followed by a line break. Then, Present the extracted text from Phase B, followed by a line break. Then, include the header "--- Physical Characteristics ---" followed by your material description from Phase C."

---

Capture this output. This is the **Step 1 result**.

---

## Step 6 — Append the render specification (Step 2 of the packshot workflow)

Take the Step 1 result and append the following block verbatim — no modifications:

```
Material & Identity Fidelity: Every aspect of the item—its morphology, dimensions, material weight, color saturation, and surface pattern—must be a 1:1 match with the provided source image. Any graphics, hallmarks, or text must be replicated with extreme precision in font, spacing, and positional coordinates.

Illumination Profile: Primary lighting is provided by a high-output, evenly diffused softbox array at a 5600k daylight temperature, specifically tuned to lift shadows without losing depth. The environment should be illuminated by a secondary neutral #f9f9f9 light source to ensure a consistent, non-vignetted, clinical grey backdrop without gradients.

Render Specs: High-resolution 4k master. Capture every individual fiber, stitch line, and microscopic material texture with edge-to-edge optical clarity.

Strict Negative Constraints: No creative interpretation of the original product. Do not render studio hardware, light stands, or power cords. Exclude all human elements, including hands, skin, or mannequins. No props, no dust, and no digital artifacts.
```

This is the **full combined prompt** (Step 1 + Step 2).

---

## Step 7 — Write packshot-spec.json

Create the spec file at `brands/[brand-name]/packshots/[output-name]/packshot-spec.json`:

```json
{
  "output_name": "[output-name]",
  "brand": "[brand-name]",
  "product_description": "skincare bottle",
  "aspect_ratio": "3:4",
  "product_images": [
    "brands/[brand-name]/packshots/[output-name]/product-references/front.jpg",
    "brands/[brand-name]/packshots/[output-name]/product-references/back.jpg"
  ],
  "prompt": "[full combined prompt from Steps 1+2]"
}
```

List all images found in `product-references/` in the `product_images` array.

---

## Step 8 — Generate

Run from the project root:

```bash
python3 skills/references/generate-packshot.py brands/[brand-name]/packshots/[output-name]
```

Uploads all product reference images to FAL storage, then calls `fal-ai/nano-banana-2/edit` at 2K in the specified aspect ratio using the combined prompt.

Cost: ~$0.12 per image.

---

## Step 9 — Present the result

Tell the user the exact path where the file was saved, e.g.:
`brands/[brand-name]/packshots/[output-name]/[output-name]_v1.png`

Ask: "Happy with this? Or would you like to regenerate, change the aspect ratio, or try a different staging approach?"

**If the user is not happy**, before regenerating, ask:

> "To improve the result, it helps to have more product reference images — different angles, close-ups, and shots in varying lighting give Nano Banana more to work with.
>
> You currently have [N] image(s) in:
> `brands/[brand-name]/packshots/[output-name]/product-references/`
>
> If you can add any of the following, drop them in and let me know:
> - **Additional angles** — side, back, three-quarter
> - **Close-ups** — label detail, texture, hardware
> - **Different lighting** — a shot in natural light if you only have studio, or vice versa
>
> Or I can regenerate now with what we have — sometimes a second pass gives a better result regardless."

Once the user confirms (with or without new images), re-run the analysis (Steps 5–6) to update the prompt if new images were added, then regenerate.

Once the user is happy, suggest the next step:

> "Clean shot. If you'd like to place this product into a lifestyle scene or styled environment, run `/product-shoot`."

**To regenerate (same prompt):**
```bash
python3 skills/references/generate-packshot.py brands/[brand-name]/packshots/[output-name]
```
Saves as the next version — does not overwrite previous outputs.

**To try a different staging approach:** re-run the Claude analysis (Step 5), update `packshot-spec.json` with the new prompt, then regenerate.

**To change aspect ratio:** update `aspect_ratio` in `packshot-spec.json` and re-run.

---

## Notes

- Claude does the prompt engineering internally — no external API call needed for Step 1
- More product reference images = better material and text fidelity. Minimum 1, ideal 3–5 from different angles
- Ghost mannequin, flat-lay, and folded are the three staging options — Claude picks the best fit based on the product type
- If branding or text on the product comes out wrong, regenerate — Nano Banana 2's text rendering varies
- Each brand has its own `packshots/` subfolder — multiple brands can run independent packshot workflows in the same project
