#!/usr/bin/env python3
"""Gemini Creative Pipeline v3 — Strategist + Concept Designer + Variants.

Upgrade over ``gemini_pipeline_v2.py``:

1. SPLIT CONCEPT GENERATION INTO TWO STEPS
   v2 flow: Strategist (N concepts) -> Prompt Engineer -> Image
   v3 flow: Strategist (N SEEDS) -> Concept Designer (N full docs)
            -> Prompt Engineer (N x V variants) -> Image (N x V)

   The Strategist is now lightweight and only identifies which directions
   to pursue. The Concept Designer expands each seed into a full ad concept
   document (headline, subline, CTA, composition, palette, elements).

2. ``--variants N`` FLAG
   Each concept document is rendered V times with a different variant
   direction (composition, color treatment, style intensity, typography
   emphasis). Total creatives = count x variants.

3. METADATA + PARALLELISM
   Batch-level ``strategist_seeds.json`` / ``concept_documents.json``,
   per-creative ``*_meta.json``, ThreadPoolExecutor(max_workers=3) for
   Steps 2-4.

Usage::

    python3 gemini_pipeline_v3.py --count 4 --variants 3   # 12 creatives
    python3 gemini_pipeline_v3.py --count 6                 # 6 creatives, 1 variant each
    python3 gemini_pipeline_v3.py --count 3 --variants 2    # 6 creatives
    python3 gemini_pipeline_v3.py --count 4 --variants 3 --personas "Der Schwitzer,Das Paar"
"""

import argparse
import atexit
import base64
import json
import os
import random
import re
import signal
import sys
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Make sibling imports work regardless of where the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    SupabaseClient,
    init_supabase,
    load_config,
    encode_image,
    acquire_process_lock,
    release_process_lock,
    PROJECT_ROOT,
)

from gemini_pipeline_v2 import (  # noqa: E402
    load_brand_context,
    load_pain_points_summary,
    pick_visual_references,
    _gemini_text_call,
    _gemini_image_call,
    _image_part,
    _pick_logo_path,
    slugify,
    DEFAULT_PERSONAS,
    PERSONA_DESCRIPTIONS,
    FORMATS,
    PRODUCT_IMAGES,
    CREATIVES_DIR,
    TEXT_MODEL,
    IMAGE_MODEL,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAX_WORKERS = 3  # respect Gemini rate limits

# Variant directions — applied in a round-robin to each concept so that V
# variants of one concept are visually distinguishable while still sharing
# the same headline / subline / CTA / core idea.
VARIANT_DIRECTIONS = [
    {
        "keyword": "editorial",
        "direction": (
            "conservative / editorial / wide composition — product prominent "
            "in center, clean negative space at top for headline, balanced "
            "typography with serif or refined sans-serif, warm neutral palette, "
            "magazine-quality lighting"
        ),
    },
    {
        "keyword": "dramatic",
        "direction": (
            "bold / dramatic / close composition — tighter framing, stronger "
            "color contrast, saturated hero color, headline pushes against "
            "product with heavy bold sans-serif, cinematic lighting with "
            "directional shadow"
        ),
    },
    {
        "keyword": "minimal",
        "direction": (
            "minimal / airy / asymmetric — lots of negative space, off-center "
            "composition, smaller product, headline dominates with large "
            "typography, muted cool palette, soft diffused lighting"
        ),
    },
    {
        "keyword": "vibrant",
        "direction": (
            "vibrant / playful / split-layout — split or diagonal composition "
            "with a bold accent block of color behind the product, medium-weight "
            "sans-serif headline, punchy contrasting palette, bright even light"
        ),
    },
    {
        "keyword": "moody",
        "direction": (
            "moody / data-driven / dark — dark environment, product lit from "
            "the side, big data point ('72%', '4.5*') as dominant typographic "
            "element, small supporting headline, deep cool palette"
        ),
    },
]


# ---------------------------------------------------------------------------
# Step 1 — STRATEGIST (N lightweight seeds)
# ---------------------------------------------------------------------------

STRATEGIST_SEEDS_PROMPT = """You are a senior Creative Strategist for Ora Sleep, a Swiss premium mattress brand. Your job: analyze the brand's existing winning ads and identify {count} diverse creative directions (seeds) that will drive high ROAS and low CPM on Meta.

BRAND CONTEXT:
{brand_context}

TOP CUSTOMER PAIN POINTS (from reviews):
{pain_points_summary}

KEY DATA POINTS WE CAN USE:
- NPS 8.6 (108 customer survey)
- 4.5 stars on Trustpilot (237 reviews)
- 93% report more energy
- 72% report better temperature regulation
- 60% fall asleep in under 10 minutes
- 49% report significant back pain improvement
- 8 customers: back pain completely gone
- Testsieger 2026 (test winner)
- Swiss Made, 10 year warranty, 200 night trial

HEALTH CLAIMS GUARDRAIL:
NEVER promise cures or medical outcomes. Only report customer feedback ("49% unserer Kunden berichten...", "Laut Kundenumfrage..."). No "heilt", "garantiert", "medizinisch".

TARGET PERSONAS (pick {count} diverse ones from this list):
{persona_list}

The visual reference ads attached are real high-performing Ora Sleep ads. Study them for tone and direction.

You are NOT writing full concepts. You are writing lightweight SEEDS that describe WHICH direction each creative should take. A downstream Concept Designer will expand each seed into a full ad concept document.

Output exactly {count} seeds. For each seed output this JSON object:

{{
  "concept_number": 1,
  "persona": "...one from the list above...",
  "angle": "Problem/Pain | Benefit | Proof | Offer | Story | Education | Curiosity",
  "core_idea": "One sentence in English describing the creative direction and its emotional hook",
  "target_emotion": "short phrase, e.g. 'frustration -> relief', 'confidence', 'calm trust'",
  "key_data_point": "Optional data point to feature (e.g. '72% report better temperature regulation'). Use '' if none.",
  "format_recommendation": "4:5 | 9:16 | 1:1"
}}

Output ONLY a JSON array of {count} seeds. No preamble, no markdown fences."""


def run_strategist_seeds(api_key, brand_context, pain_points_summary, ref_paths,
                         count, personas):
    """Single strategist call that produces N lightweight seeds."""
    persona_list = "\n".join(
        f"- {p} ({PERSONA_DESCRIPTIONS.get(p, '')})".rstrip() for p in personas
    )

    prompt_text = STRATEGIST_SEEDS_PROMPT.format(
        count=count,
        brand_context=brand_context,
        pain_points_summary=pain_points_summary,
        persona_list=persona_list,
    )

    parts = [{"text": prompt_text}]

    if ref_paths:
        parts.append({"text": "\n\nVISUAL REFERENCE ADS (real high-performing Ora Sleep ads):"})
        for rp in ref_paths:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    parts.append({"text": "\n\nNow output the JSON array of seeds."})

    raw = _gemini_text_call(
        api_key, parts, temperature=0.95, max_output_tokens=4096
    )
    if not raw:
        return None
    return _parse_json_array(raw, expected=count)


def _parse_json_array(raw, expected):
    """Tolerant JSON-array parser (handles markdown fences, preamble, etc.)."""
    text = raw.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("concepts", "seeds", "items", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
    except Exception:
        pass

    match = re.search(r"\[\s*\{.*\}\s*\]", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            print(f"    Warning: JSON array substring parse failed: {e}")

    print(f"    ERROR: could not parse JSON array. First 500 chars:\n{text[:500]}")
    return None


# ---------------------------------------------------------------------------
# Step 2 — CONCEPT DESIGNER (1 call per seed; returns full ad concept doc)
# ---------------------------------------------------------------------------

CONCEPT_DESIGNER_PROMPT = """Objective: Create a static ad concept that combines visual composition (layout, art direction, style, elements) with copywriting (headline, tagline, supporting text). The product picture must be integrated and remain clearly visible.

CONCEPT SEED:
{seed_json}

BRAND CONTEXT:
{brand_context}

PAIN POINTS & CUSTOMER VOICE:
{pain_points}

The visual reference ads attached are real high-performing Ora Sleep ads. Study them for tone of copywriting and visual direction.

Generate a full ad concept with this exact structure:

Headline: <Main headline in German, bold impactful, max 8 words>
Subline: <Supporting subline in German, clarifies value or benefit, max 12 words>
Call-to-action: <German CTA, 2-4 words, clear and motivating>
Visual Composition:
  Product placement: <Where and how prominently the product appears>
  Layout suggestion: <Describe the layout including where text and graphic elements go>
  Background / environment: <Specific background description>
  Style & mood: <Photography/illustration approach, emotional tone>
  Color palette: <3-5 specific colors with hex codes>
  Additional elements: <Badges, trust signals, data points, graphic accents>

HEALTH CLAIMS GUARDRAIL: Never promise cures. Only report customer feedback.

Output ONLY the concept in this format. No preamble."""


def run_concept_designer(api_key, seed, brand_context, pain_points_summary, ref_paths):
    """Expand one seed into a full ad concept document (plain text block)."""
    prompt_text = CONCEPT_DESIGNER_PROMPT.format(
        seed_json=json.dumps(seed, ensure_ascii=False, indent=2),
        brand_context=brand_context,
        pain_points=pain_points_summary,
    )

    parts = [{"text": prompt_text}]

    if ref_paths:
        parts.append({"text": "\n\nVISUAL REFERENCE ADS (real high-performing Ora Sleep ads):"})
        for rp in ref_paths:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    parts.append({"text": "\n\nNow output the full concept document."})

    return _gemini_text_call(
        api_key, parts, temperature=0.9, max_output_tokens=2048
    )


# ---------------------------------------------------------------------------
# Concept document parser — used to derive angle/persona metadata for DB rows
# ---------------------------------------------------------------------------

def parse_concept_document(doc):
    """Pull Headline / Subline / CTA / color palette / mood from a concept doc.

    The Concept Designer outputs loosely structured text — this is best-effort
    parsing for DB persistence. The raw doc is preserved verbatim in metadata.
    """
    if not doc:
        return {}

    out = {
        "headline_de": "",
        "subline_de": "",
        "cta_de": "",
        "product_placement": "",
        "layout": "",
        "background": "",
        "mood": "",
        "color_palette": [],
        "additional_elements": "",
    }

    # Line-based extraction
    def _find(regex, flags=re.IGNORECASE):
        m = re.search(regex, doc, flags=flags)
        return m.group(1).strip() if m else ""

    out["headline_de"] = _find(r"Headline\s*:\s*(.+)")
    out["subline_de"] = _find(r"Subline\s*:\s*(.+)")
    out["cta_de"] = _find(r"Call[- ]to[- ]action\s*:\s*(.+)")
    out["product_placement"] = _find(r"Product placement\s*:\s*(.+)")
    out["layout"] = _find(r"Layout suggestion\s*:\s*(.+)")
    out["background"] = _find(r"Background(?:\s*/\s*environment)?\s*:\s*(.+)")
    out["mood"] = _find(r"Style\s*(?:&|and)?\s*mood\s*:\s*(.+)")
    palette_line = _find(r"Color palette\s*:\s*(.+)")
    out["additional_elements"] = _find(r"Additional elements\s*:\s*(.+)")

    if palette_line:
        hexes = re.findall(r"#[0-9a-fA-F]{6}", palette_line)
        out["color_palette"] = hexes

    # Clean-up: strip quotes / angle brackets / trailing punctuation
    for key in ("headline_de", "subline_de", "cta_de"):
        v = out[key]
        v = v.strip().strip("<>\"'").strip()
        out[key] = v

    return out


# ---------------------------------------------------------------------------
# Step 3 — PROMPT ENGINEER (v2 structure + variant awareness)
# ---------------------------------------------------------------------------

PROMPT_ENGINEER_V3 = """You are an expert prompt writer for Gemini image generation. Transform this ad concept into a structured English prompt for a static Meta ad.

AD CONCEPT DOCUMENT:
{concept_document}

VARIANT DIRECTION ({variant_index}/{total_variants}):
{variant_direction}

The visual reference ads attached are real high-performing ads from the same brand. Match their quality and visual language.

PROMPT STRUCTURE (required):
[Key visual description] [Text overlay concept with exact quoted German text] [Secondary text/CTA] [Typography specifications]

RULES:
- Write as continuous prose, no bullet points
- English prose EXCEPT for German text content (headline, subline, CTA exactly as specified in the concept)
- Apply the variant direction to differentiate this variant from others
- Specify negative space for text placement
- Do NOT mention logos (logo is attached separately)
- Do NOT describe the product in detail (product image is attached)
- Format: {format} aspect ratio

Output ONLY the final prompt paragraph. No preamble."""


def run_prompt_engineer_v3(api_key, concept_document, variant_index,
                           total_variants, variant_direction, fmt, ref_paths):
    """Turn (concept doc + variant direction) into a structured English prompt."""
    prompt_text = PROMPT_ENGINEER_V3.format(
        concept_document=concept_document,
        variant_index=variant_index,
        total_variants=total_variants,
        variant_direction=variant_direction,
        format=fmt,
    )

    parts = [{"text": prompt_text}]

    if ref_paths:
        parts.append({"text": "\n\nVISUAL REFERENCE ADS (match style and quality):"})
        for rp in ref_paths:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    parts.append({"text": "\n\nWrite the final structured prompt paragraph now."})
    return _gemini_text_call(api_key, parts, temperature=0.8, max_output_tokens=2048)


# ---------------------------------------------------------------------------
# Step 4 — IMAGE GENERATION (identical plumbing to v2)
# ---------------------------------------------------------------------------

def run_image_generation_v3(api_key, structured_prompt, parsed_concept, fmt,
                            product_image_path, ref_paths):
    """Call the image model with product + refs + logo + structured prompt."""
    parts = []

    # Product first
    pp = _image_part(product_image_path)
    if pp:
        parts.append(pp)
        parts.append({"text": "Product image to feature in the ad, kept clearly visible."})

    # Reference ads (2-3)
    use_refs = ref_paths[: min(3, len(ref_paths))]
    for rp in use_refs:
        ip = _image_part(rp)
        if ip:
            parts.append(ip)
    if use_refs:
        parts.append({
            "text": (
                "Real high-performing ads from the same brand. Match this visual "
                "language and quality exactly."
            )
        })

    # Logo PNG (reuse v2's picker)
    logo_concept_shape = {
        "mood": parsed_concept.get("mood", ""),
        "color_palette": parsed_concept.get("color_palette", []),
    }
    logo_path, _ = _pick_logo_path(logo_concept_shape)
    if logo_path:
        lp = _image_part(logo_path)
        if lp:
            parts.append(lp)
            parts.append({
                "text": (
                    "Transparent logo PNG — integrate it subtly at the top of the ad, "
                    "small and clean. Do not distort it, do not render the word 'ora' "
                    "manually as text, use this PNG as-is."
                )
            })

    logo_hint = (
        " A transparent logo PNG is attached — integrate it subtly at the top of the "
        "ad (centered or top-left), sized small."
    )
    parts.append({"text": structured_prompt.strip() + logo_hint})

    aspect_map = {"4:5": "4:5", "9:16": "9:16", "1:1": "1:1", "16:9": "16:9"}
    aspect = aspect_map.get(fmt, "4:5")

    return _gemini_image_call(api_key, parts, aspect)


# ---------------------------------------------------------------------------
# Creative-type heuristic
# ---------------------------------------------------------------------------

def infer_creative_type(concept_document, parsed):
    """Return 'lifestyle' or 'product_static' from concept language."""
    text = (concept_document or "").lower()
    lifestyle_markers = (
        "bedroom", "schlafzimmer", "person", "couple", "paar", "woman",
        "frau", "man ", "mann", "lying", "sleeping", "bett",
    )
    if any(m in text for m in lifestyle_markers):
        return "lifestyle"
    return "product_static"


# ---------------------------------------------------------------------------
# Per-variant production (Steps 3 + 4 + upload)
# ---------------------------------------------------------------------------

def produce_variant(api_key, sb, brand_id, batch_id, global_index, total,
                    concept_index, variant_index, total_variants,
                    seed, concept_document, parsed, variant_entry,
                    product_image_rel, ref_paths, fmt, creative_id):
    """Prompt-engineer + image-gen + upload for a single variant."""
    prefix = f"[{global_index}/{total}]"
    persona = seed.get("persona", "Unknown")
    angle = seed.get("angle", "Benefit")
    headline = parsed.get("headline_de", "") or seed.get("core_idea", "")
    variant_keyword = variant_entry["keyword"]
    variant_direction = variant_entry["direction"]

    print(f"\n{prefix} concept={concept_index} variant={variant_index}/{total_variants}"
          f" [{variant_keyword}] {persona} | {angle} | {fmt}")
    print(f"{prefix}   headline: {headline!r}")
    print(f"{prefix}   refs: {', '.join(os.path.basename(r) for r in ref_paths)}")

    product_abs = os.path.join(PROJECT_ROOT, product_image_rel)
    if not os.path.exists(product_abs):
        print(f"{prefix}   ERROR: product image not found: {product_abs}")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None

    # Step 3 — Prompt Engineer
    print(f"{prefix}   Step 3: Prompt Engineer ({variant_keyword})...")
    structured_prompt = run_prompt_engineer_v3(
        api_key, concept_document, variant_index, total_variants,
        variant_direction, fmt, ref_paths,
    )
    if not structured_prompt:
        print(f"{prefix}   FAILED at Step 3 (prompt engineer)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None
    print(f"{prefix}   Prompt OK ({len(structured_prompt)} chars)")

    # Step 4 — Image Generation
    print(f"{prefix}   Step 4: Image...")
    image_data, mime_type = run_image_generation_v3(
        api_key, structured_prompt, parsed, fmt, product_abs, ref_paths,
    )
    if not image_data:
        print(f"{prefix}   FAILED at Step 4 (image gen)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None

    image_bytes = base64.standard_b64decode(image_data)
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    ext = ext_map.get(mime_type, "png")

    fmt_slug = fmt.replace(":", "x")
    filename = (
        f"{global_index:03d}_c{concept_index:02d}_v{variant_index}_"
        f"{slugify(persona)}_{slugify(angle)}_{variant_keyword}_{fmt_slug}.{ext}"
    )

    local_dir = os.path.join(CREATIVES_DIR, str(batch_id))
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    # Per-creative metadata
    meta_path = os.path.join(
        local_dir,
        f"{global_index:03d}_c{concept_index:02d}_v{variant_index}_meta.json",
    )
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "global_index": global_index,
                "concept_index": concept_index,
                "variant_index": variant_index,
                "total_variants": total_variants,
                "variant_keyword": variant_keyword,
                "variant_direction": variant_direction,
                "persona": persona,
                "angle": angle,
                "format": fmt,
                "product_image": product_image_rel,
                "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
                "concept_seed": seed,
                "concept_document": concept_document,
                "parsed_concept": parsed,
                "structured_prompt": structured_prompt,
                "headline": parsed.get("headline_de", ""),
                "subline": parsed.get("subline_de", ""),
                "cta": parsed.get("cta_de", ""),
                "filename": filename,
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"{prefix}   Warning: failed to write meta: {e}")

    # Upload to Supabase Storage
    storage_path = f"{brand_id}/{batch_id}/{filename}"
    content_type = mime_type or "image/png"
    image_url = None
    try:
        sb.upload_file("creatives", storage_path, image_bytes, content_type)
        image_url = sb.get_public_url("creatives", storage_path)
        print(f"{prefix}   Uploaded: {storage_path} ({len(image_bytes) / 1024:.0f} KB)")
    except Exception as e:
        print(f"{prefix}   Upload failed: {e}")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None

    # Update DB row
    if creative_id:
        try:
            sb.update_creative(creative_id, {
                "status": "done",
                "storage_path": storage_path,
                "image_url": image_url,
                "hook_text": parsed.get("headline_de", "") or headline,
            })
        except Exception as e:
            print(f"{prefix}   Warning: DB update failed: {e}")

    print(f"{prefix}   DONE!")

    return {
        "global_index": global_index,
        "concept_index": concept_index,
        "variant_index": variant_index,
        "variant_keyword": variant_keyword,
        "filename": filename,
        "local_path": local_path,
        "storage_path": storage_path,
        "image_url": image_url,
        "persona": persona,
        "angle": angle,
        "format": fmt,
        "product_image": product_image_rel,
        "headline": parsed.get("headline_de", ""),
        "subline": parsed.get("subline_de", ""),
        "cta": parsed.get("cta_de", ""),
        "seed": seed,
        "concept_document": concept_document,
        "structured_prompt": structured_prompt,
        "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
    }


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def pick_product_image(index):
    return PRODUCT_IMAGES[index % len(PRODUCT_IMAGES)]


def run_batch(api_key, sb, brand_id, count, variants, personas_filter,
              max_workers=MAX_WORKERS, output_dir=None):
    batch_id = str(uuid.uuid4())
    total_creatives = count * variants
    print(f"Batch ID: {batch_id}")
    print(f"Concepts: {count}  |  Variants: {variants}  |  Total: {total_creatives}")
    print(f"Workers: {max_workers}")

    brand_context, _brand_json, _guidelines = load_brand_context()
    pain_points_summary = load_pain_points_summary()

    # Persona pool
    if personas_filter:
        personas = [p.strip() for p in personas_filter.split(",") if p.strip()]
        if not personas:
            personas = list(DEFAULT_PERSONAS)
    else:
        personas = list(DEFAULT_PERSONAS)
    print(f"Persona pool: {', '.join(personas)}")

    # Shared strategist refs (same as v2)
    strategist_refs = pick_visual_references(k=5)
    print(f"Strategist refs: {[os.path.basename(r) for r in strategist_refs]}")

    # -------- Step 1: STRATEGIST --------
    print(f"\nStep 1: STRATEGIST — {count} seeds...")
    seeds = run_strategist_seeds(
        api_key, brand_context, pain_points_summary,
        strategist_refs, count, personas,
    )
    if not seeds:
        print("FATAL: strategist returned no seeds, aborting batch")
        return None

    if len(seeds) > count:
        seeds = seeds[:count]
    elif len(seeds) < count:
        print(f"Warning: strategist returned {len(seeds)} seeds, expected {count}")

    print(f"Strategist OK — {len(seeds)} seeds:")
    for i, s in enumerate(seeds, 1):
        print(f"  {i}. [{s.get('persona')}] {s.get('angle')} — "
              f"{(s.get('core_idea') or '')[:80]}")

    local_dir = output_dir or os.path.join(CREATIVES_DIR, batch_id)
    os.makedirs(local_dir, exist_ok=True)

    seeds_path = os.path.join(local_dir, "strategist_seeds.json")
    try:
        with open(seeds_path, "w", encoding="utf-8") as f:
            json.dump(seeds, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  Warning: failed to write strategist seeds dump: {e}")

    # -------- Step 2: CONCEPT DESIGNER (parallel, one call per seed) --------
    print(f"\nStep 2: CONCEPT DESIGNER — expanding {len(seeds)} seeds...")
    concept_documents = [None] * len(seeds)
    parsed_concepts = [None] * len(seeds)
    designer_refs_per_seed = [pick_visual_references(k=3) for _ in seeds]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, seed in enumerate(seeds):
            fut = executor.submit(
                run_concept_designer,
                api_key, seed, brand_context, pain_points_summary,
                designer_refs_per_seed[i],
            )
            futures[fut] = i

        for fut in as_completed(futures):
            i = futures[fut]
            try:
                doc = fut.result()
            except Exception as e:
                print(f"  [concept {i + 1}] EXCEPTION: {e}")
                traceback.print_exc()
                doc = None
            if not doc:
                print(f"  [concept {i + 1}] FAILED — no concept document")
                continue
            concept_documents[i] = doc
            parsed_concepts[i] = parse_concept_document(doc)
            headline = parsed_concepts[i].get("headline_de", "")
            print(f"  [concept {i + 1}] OK — headline: {headline!r}")

    # Persist concept documents
    concept_docs_path = os.path.join(local_dir, "concept_documents.json")
    try:
        with open(concept_docs_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "concept_index": i + 1,
                        "seed": seeds[i],
                        "concept_document": concept_documents[i],
                        "parsed": parsed_concepts[i],
                    }
                    for i in range(len(seeds))
                ],
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception as e:
        print(f"  Warning: failed to write concept_documents.json: {e}")

    # -------- Build variant jobs --------
    jobs = []
    global_index = 0
    for concept_idx, seed in enumerate(seeds):
        concept_document = concept_documents[concept_idx]
        if not concept_document:
            # Skip — failed concept designer step
            continue
        parsed = parsed_concepts[concept_idx] or {}

        fmt = seed.get("format_recommendation") or FORMATS[concept_idx % len(FORMATS)]
        if fmt not in FORMATS:
            fmt = FORMATS[concept_idx % len(FORMATS)]

        for v in range(variants):
            global_index += 1
            variant_entry = VARIANT_DIRECTIONS[v % len(VARIANT_DIRECTIONS)]
            jobs.append({
                "global_index": global_index,
                "concept_index": concept_idx + 1,
                "variant_index": v + 1,
                "total_variants": variants,
                "seed": seed,
                "concept_document": concept_document,
                "parsed": parsed,
                "variant_entry": variant_entry,
                "format": fmt,
                "product_image": pick_product_image(global_index - 1),
                "refs": pick_visual_references(k=3),
            })

    effective_total = len(jobs)
    print(f"\nBuilt {effective_total} variant jobs "
          f"(expected {total_creatives}, dropped {total_creatives - effective_total} due to failed concepts)")

    # -------- Insert placeholder rows in Supabase --------
    creative_ids = []
    for j in jobs:
        seed = j["seed"]
        parsed = j["parsed"]
        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": seed.get("angle", "Benefit"),
            "sub_angle": seed.get("persona", "Unknown"),
            "variant": j["variant_index"],
            "format": j["format"],
            "hook_text": parsed.get("headline_de", "") or seed.get("core_idea", ""),
            "creative_style": j["variant_entry"]["keyword"],
            "creative_type": infer_creative_type(j["concept_document"], parsed),
            "status": "generating",
            "is_saved": False,
        }
        try:
            inserted = sb.insert_creative(row)
            creative_ids.append(inserted["id"])
        except Exception as e:
            print(f"  Warning: placeholder insert failed for [{j['global_index']}]: {e}")
            creative_ids.append(None)

    print(f"Inserted {sum(1 for c in creative_ids if c)} / {len(jobs)} placeholders")

    # -------- Manifest skeleton --------
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "batch_id": batch_id,
        "brand_id": brand_id,
        "pipeline": "gemini-v3-strategist-designer-variants",
        "text_model": TEXT_MODEL,
        "image_model": IMAGE_MODEL,
        "count": count,
        "variants": variants,
        "total": effective_total,
        "personas": personas,
        "strategist_refs": [os.path.relpath(r, PROJECT_ROOT) for r in strategist_refs],
        "seeds": seeds,
        "concept_documents": [
            {
                "concept_index": i + 1,
                "seed": seeds[i],
                "concept_document": concept_documents[i],
                "parsed": parsed_concepts[i],
            }
            for i in range(len(seeds))
        ],
        "successful": 0,
        "failed": 0,
        "ads": [],
    }

    # -------- Steps 3 + 4 in parallel per variant --------
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for j, cid in zip(jobs, creative_ids):
            fut = executor.submit(
                produce_variant,
                api_key, sb, brand_id, batch_id,
                j["global_index"], effective_total,
                j["concept_index"], j["variant_index"], j["total_variants"],
                j["seed"], j["concept_document"], j["parsed"], j["variant_entry"],
                j["product_image"], j["refs"], j["format"], cid,
            )
            futures[fut] = j["global_index"]

        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"[{idx}] EXCEPTION: {e}")
                traceback.print_exc()
                res = None
            if res:
                results.append(res)
                manifest["successful"] += 1
            else:
                manifest["failed"] += 1

    results.sort(key=lambda r: r["global_index"])
    manifest["ads"] = results

    manifest_path = os.path.join(local_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"DONE: {manifest['successful']} succeeded, {manifest['failed']} failed")
    print(f"Batch: {batch_id}")
    print(f"Local: {local_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"{'=' * 60}")

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gemini Creative Pipeline v3 — Strategist + Concept Designer + Variants"
    )
    parser.add_argument("--count", type=int, default=3,
                        help="Number of concept seeds (default: 3)")
    parser.add_argument("--variants", type=int, default=1,
                        help="Variants per concept (default: 1). Total creatives = count * variants.")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help=f"Parallel worker threads (default: {MAX_WORKERS})")
    parser.add_argument(
        "--personas",
        default=None,
        help=(
            "Optional comma-separated persona list to constrain the strategist. "
            "Defaults to the full pool."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Local output directory (default: creatives/<batch_id>)",
    )
    parser.add_argument("--brand-id", default=None,
                        help="Brand UUID (auto-detected if omitted)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.count <= 0:
        print("Error: --count must be > 0")
        sys.exit(1)
    if args.variants <= 0:
        print("Error: --variants must be > 0")
        sys.exit(1)
    if args.workers <= 0:
        print("Error: --workers must be > 0")
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)

    acquire_process_lock()
    atexit.register(release_process_lock)

    def handle_signal(sig, frame):
        print(f"\nInterrupted (signal {sig}) — cleaning up...")
        release_process_lock()
        sys.exit(1)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    api_key = load_config()
    sb = init_supabase()

    if args.brand_id:
        try:
            uuid.UUID(args.brand_id)
        except ValueError:
            print(f"Error: --brand-id must be a valid UUID, got: {args.brand_id}")
            sys.exit(1)
        brand_id = args.brand_id
    else:
        env_brand = os.getenv("BRAND_ID")
        if env_brand:
            try:
                uuid.UUID(env_brand)
                brand_id = env_brand
                print(f"Using BRAND_ID from env: {brand_id}")
            except ValueError:
                brand_id = sb.get_single_brand_id()
                print(f"Auto-detected brand: {brand_id}")
        else:
            brand_id = sb.get_single_brand_id()
            print(f"Auto-detected brand: {brand_id}")

    run_batch(
        api_key, sb, brand_id,
        count=args.count,
        variants=args.variants,
        personas_filter=args.personas,
        max_workers=args.workers,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
