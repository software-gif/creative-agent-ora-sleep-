# AI Visuals for Brands with Claude Code

Generate photorealistic AI model imagery and video for your brand using Claude Code and the FAL API.

---

## Folder structure

All outputs save under your brand folder. Multiple brands can coexist in the same project.

```
brands/
  [brand-name]/
    brand-identity/
      visual-guidelines.md
      products.json
      product-images/
    models/
      [model-name]/
        headshot.png
        fullbody.png
        model-spec.json
    styled/
      [output-name]/
        [output-name]_v1.png
        style-spec.json
    clothing-shoot/
      [output-name]/
        shoot_v1.png
        shoot-spec.json
    ugc/
      [output-name]/
        ugc-image_v1.png
        ugc-video.mp4
        ugc-spec.json
    product-ugc/
      [output-name]/
        product-ugc-image_v1.png
        product-ugc-video.mp4
        product-ugc-spec.json
    packshots/
      [output-name]/
        [output-name]_v1.png
        packshot-spec.json
        product-references/
    product-shots/
      [output-name]/
        [output-name]_v1.png
        product-shot-spec.json
    model-product-shoot/
      [output-name]/
        [output-name]_v1.png
        model-product-shoot-spec.json
    static-ads/
      [output-name]/
        [output-name]_v1.png
        static-ad-spec.json
    reformat/
      [output-name]/
        [output-name]_v1.png
        reformat-spec.json
    motion/
      [output-name]/
        [output-name]_v1.mp4
        add-motion-spec.json
```

---

## Skills

| Command | What it does |
|---------|-------------|
| `/brand` | Crawl a brand website — extracts visual guidelines and downloads product images |
| `/model` | Create a model — generates a matched headshot and full-body casting digital |
| `/style` | Style a model — places a product/garment onto a generated model |
| `/clothing-shoot` | Place a styled model into a location environment |
| `/ugc` | UGC selfie image, optionally continued into a talking-head video |
| `/product-ugc` | UGC selfie of a model holding a product, optionally continued into video |
| `/packshot` | Clean commercial packshot — studio product photography |
| `/product-shoot` | Lifestyle product shot using a composition reference image |
| `/model-product-shoot` | Editorial shot of a model interacting with a product |
| `/static-ads` | Generate on-brand static ad variations from a winning format reference |
| `/reformat` | Reformat an existing image to different aspect ratios |
| `/add-motion` | Animate a still image into a short video clip |

---

## Documentation

- `course-outline.md` is the canonical reference for everything about this course — structure, branding, IDE setup, lesson notes, conventions, build status. Update it there, not in memory.
- Do not save project information to the memory system. Memory is for user preferences and feedback only.

---

## Conventions

- Always open Claude Code from the project root
- File names: lowercase, hyphens, no spaces — `energy-gels-dark.png` not `Energy Gels Dark.png`
- Output versioning: reruns always increment — `_v1`, `_v2`, `_v3` — previous outputs are never overwritten
- FAL key goes in `.env` at the project root: `FAL_KEY=your_key_here`
