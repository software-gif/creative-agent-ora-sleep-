---
name: brand
description: Run when the user wants to set up their brand, add their brand to the project, or provides a website URL for brand onboarding. Crawls the brand's website, extracts visual guidelines and product images, and saves everything to /brands/[brand-name]/ so all subsequent creative workflows are personalised to their brand from the start. Multiple brands can be set up and run side-by-side in the same project.
---

# Brand Setup

One-time setup workflow. Run this when a student provides their brand's website URL and wants to get started.

The output is two things:
1. `brand-identity/visual-guidelines.md` — brand colours, typography, photography style, packaging, ad creative style, and a ready-to-use prompt modifier
2. `brand-identity/products.json` + `product-images/` folder — product manifest and images downloaded from the brand's website

Identity files save to `./brands/[brand-name]/brand-identity/`. Product images save to `./brands/[brand-name]/product-images/`.

---

## Step 1 — Research the brand

Use WebFetch to load the brand's homepage first. Then run targeted searches to fill in what the site doesn't show directly. Work through all three stages before writing anything.

### Stage A — Live site audit

Fetch the brand URL. Read it before any external searches — this gives you a baseline impression that external sources can then sharpen.

- **Language and voice:** Read the hero headline, About page, and 3–4 product descriptions. What are the 5 adjectives that most precisely describe how this brand sounds? Not generic words like "clean" or "premium" — be specific.
- **Photography on site:** What is the lighting quality — hard or soft, natural or studio? How is it colour graded — warm, cool, neutral, heavy contrast, matte? What's the typical composition and subject matter?
- **Type in use:** What weight and style is the headline set in? How is body copy treated — tight or loose leading, all-caps, distinctive spacing or capitalization?
- **Colour in use:** Which colour leads, which is accent? What colours are used for backgrounds and for CTAs specifically?
- **Layout feel:** Does the site breathe (airy, generous whitespace) or pack information tightly? Is it grid-structured or more organic?
- **Packaging:** Look at every product page. Describe the physical packaging — shape, material, finish (matte/gloss/soft-touch), label placement, any translucency or texture details.

### Stage B — Web research

Run targeted searches to fill in what the site doesn't tell you directly:

- `"[Brand] font"`, `"[Brand] typeface"`, `"what font does [Brand] use"` — you need exact names, not descriptions
- `"[Brand] hex codes"`, `"[Brand] brand colors"`, `"[Brand] color palette"` — get the actual hex values
- `"[Brand] design agency"`, `"[Brand] branding case study"`, `"[Brand] rebrand"` — knowing who built the identity often unlocks precise language about it
- `"[Brand] brand guidelines"`, `"[Brand] press kit"`, `"[Brand] style guide"`, `"[Brand] media kit"` — these occasionally surface publicly
- **Meta Ad Library** — search the brand name and note the creative formats and visual treatment they're currently running
- `"[Brand] founding story"`, `"[Brand] brand story"`, `"[Brand] mission"` — needed for voice and copy direction

### Stage C — Market context

Identify 2–3 direct competitors. For each, note one specific visual or positioning choice that sets this brand apart from them. One sentence per competitor is enough — this shapes how the prompt modifier frames the brand's distinctiveness.

---

## Step 2 — Write visual-guidelines.md

Create the brand-identity folder first:
```bash
mkdir -p ./brands/[brand-name]/brand-identity
```

Save the research as `./brands/[brand-name]/brand-identity/visual-guidelines.md`.

Use this exact structure:

```
# [Brand Name] — Visual Guidelines

## Brand identity
**Name:** [Brand name as styled — e.g. all-caps, lowercase, etc.]
**Tagline:** [if there is one]
**Design agency:** [if known]
**Positioning:** [One sentence: who it's for, what it does, how it sounds]
**Voice:** [5 precise adjectives, comma-separated]
**What sets it apart:** [One sentence per closest competitor — what visually or positionally distinguishes this brand from each]

## Colour palette
- **Primary:** [name] — #XXXXXX
- **Secondary:** [name] — #XXXXXX
- **Accent:** [name] — #XXXXXX
- **Background:** [description] — #XXXXXX (list all backgrounds the brand uses)
- **CTA / button:** [fill colour #XXXXXX] / [text colour #XXXXXX] — [button style: shape, radius, weight]

## Typography
- **Headline:** [typeface name] — [weight range, e.g. 400–900]
- **Body / UI:** [typeface name] — [style, e.g. monospaced, regular]
- **Treatment:** [distinctive choices — all-caps, tight tracking, loose leading, etc.]

## Photography style
- **Lighting:** [quality and source — hard or soft, natural or studio, direction if consistent]
- **Colour grade:** [temperature, saturation, contrast, any film quality — be specific: "matte, dusty-warm midtones" not just "warm"]
- **Composition:** [typical framing, subject placement, negative space]
- **What appears in frame:** [subjects, body language, props, styling — what is and isn't present]
- **Surfaces and backgrounds:** [materials, textures, settings — e.g. bare earth, white cyclorama, concrete]
- **Overall mood:** [5 adjectives that describe the feeling of the imagery]

## Packaging & product
- **Physical form:** [shape, size, material, finish — matte/gloss/soft-touch]
- **Label and logo placement:** [where branding sits — stealth, chest hit, internal, etc.]
- **Distinctive visual features:** [anything that makes the packaging or product immediately recognisable]
- **Product system:** [how the range is unified visually — shared palette, naming system, material language, etc.]

## Ad formats & creative style
- **Formats:** [what formats they run — Instagram feed, Stories, editorial, OOH, etc.]
- **Text on image:** [how copy is used — sparingly, typeface, colour, placement, scale]
- **Photo vs illustration:** [photography only, or mixed — and what kind]
- **UGC:** [whether creator content appears in paid creative, and how it's treated]
- **Pricing and offers:** [how pricing, shipping, and discounts are presented — or deliberately not presented]

## Prompt modifier
[A single paragraph, 50–75 words. Written to open any image generation prompt — this is what gets pasted directly into creative workflows. Must lock in: exact hex values, precise lighting direction, colour grade description, surfaces and backgrounds, mood in 3 adjectives, any hard visual rules. The image model reads this first — it needs to be specific enough to constrain the output, not just describe it.]
```

---

## Step 3 — Product images

### 3a — Preview what's available

Before downloading anything, fetch the brand's product list. For Shopify brands, try:
```
[brand-url]/products.json?sort_by=best-selling&limit=20
```
Or use WebFetch on the brand's shop/collections page and extract product names from the HTML.

Present the list to the user:
```
Found 20 products on [brand]. Here are the top best sellers:

  1. Linea Jacket — Tobacco
  2. Cowboy Denim — Carbon
  3. Everyday Pleats — Olive
  ...

Which of these would you like to download? You can:
  • Say "all" to download all 20
  • List specific numbers or names
  • Skip this and add images manually (see below)
```

### 3b — Create the product-images folder

Create a clean, empty folder ready for images:
```bash
mkdir -p ./brands/[brand-name]/brand-identity/product-images
```

If the folder already exists and has files in it, warn the user before proceeding — don't overwrite without confirmation.

Tell the user:
> "Your product images folder is ready at:
> `brands/[brand-name]/brand-identity/product-images/`
>
> You can also add images here manually at any time — just drop them in and name them clearly (e.g. `linea-jacket-tobacco.jpg`, `cowboy-denim-carbon.png`). Use lowercase, hyphens, no spaces."

### 3c — Download or wait

**If the user wants to download from the site:**

Run the scraper from inside `brand-identity/` so both `product-images/` and `products.json` land in the right place:
```bash
cd ./brands/[brand-name]/brand-identity && python3 ../../../skills/references/brand.py --scrape [brand-url]
```

This saves:
- Product images → `./brands/[brand-name]/brand-identity/product-images/`
- Product manifest → `./brands/[brand-name]/brand-identity/products.json`

**If the scraper fails** (non-Shopify site, heavy JS rendering):
Tell the user and fall back to manual: ask them to drop images into `brand-identity/product-images/` and confirm when done. Then write `brand-identity/products.json` by hand from the filenames present.

**If the user wants to add images manually:**
Tell them the folder is ready, remind them to name files clearly (lowercase, hyphens), and wait for them to confirm when done. Then scan the folder and write `brand-identity/products.json` from what's there.

---

## Step 4 — Report back

When both files are saved, give the student a short summary:

1. Brand name as detected
2. Key visual identity in 2–3 sentences (colours, photography style, mood)
3. Number of product images downloaded
4. The prompt modifier, quoted in full — this is the most useful thing for them to see immediately

Then tell them: they're ready to start creating. Point them to the next lesson.

---

## Notes

- Use the brand name as it appears on the site for the folder name — slug it (lowercase, hyphens, no spaces): `satisfy-running`, `glossier`, `their-brand`
- If the brand URL redirects, follow the redirect — fetch the final URL
- If a page fails to load, note it and continue with what you have
- Hex values matter — don't approximate. If you can't find exact values from the site or web research, say so in the guidelines rather than guess
- The prompt modifier is the most important output. Draft it last, after all the research is done
