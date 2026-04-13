---
name: reformat
description: Run when the user wants to reformat or resize an existing image to a different aspect ratio, or use the /reformat command. Takes a source image and one or more target aspect ratios, then regenerates each version via Nano Banana — preserving composition, typography, product placement, and visual hierarchy. Works on any output from any skill. Output saved alongside the source image.
---

# Content Format Multiplier

Reformats an existing image to one or more new aspect ratios, recomposing the layout intelligently rather than cropping or letterboxing.

Output saved to the same folder as the source image.

---

## Step 1 — Get source image

Ask:

> "Drop the image you want to reformat into the chat, or give me the path."

If the user drops an image into the chat, ask:

> "And what's the folder path to save the output to? Or drop it into the project folder and give me the path."

Wait until you have a resolvable file path.

---

## Step 2 — Select target aspect ratio(s)

Ask:

> "Which aspect ratio(s) do you want? Options: `1:1`, `3:4`, `4:5`, `9:16`, `16:9`, `4:3`, `2:3`."

Multiple ratios can be given at once. Each is generated in sequence.

---

## Step 3 — Generate

For each target aspect ratio, run:

```bash
python3 skills/references/generate-reformat.py [source-image-path] [aspect-ratio]
```

e.g.:
```bash
python3 skills/references/generate-reformat.py brands/puresport/static-ads/iMessage-energy-gel/iMessage-energy-gel-var-1_v1.png 9:16
```

Run sequentially. Always reformat from the original source — not from a previously reformatted version.

The script saves the output to the same folder as the source, with the ratio appended to the filename:
- `iMessage-energy-gel-var-1_v1.png` → `iMessage-energy-gel-var-1_9x16_v1.png`

Cost: ~$0.12 per image.

---

## Step 4 — Present results

Tell the user the paths for all reformatted files:

```
Reformatted:
  ✓ brands/puresport/static-ads/iMessage-energy-gel/iMessage-energy-gel-var-1_9x16_v1.png
  ✓ brands/puresport/static-ads/iMessage-energy-gel/iMessage-energy-gel-var-1_1x1_v1.png
```

Ask: "Happy with these? Or would you like to regenerate any?"

**To regenerate:** re-run the script. Output auto-increments — previous versions are not overwritten.

---

## Notes

- Always reformat from the primary output — not from another reformatted version. Each ratio is derived independently from the same source.
- The script recomposes intelligently — it does not crop, letterbox, or distort. All text and key elements are kept within the central safe zone of the new frame.
- Works on any output from any skill: static ads, packshots, product shots, styled images, UGC frames.
- If results are off, try regenerating — Nano Banana varies run to run. A second pass often improves composition quality.
