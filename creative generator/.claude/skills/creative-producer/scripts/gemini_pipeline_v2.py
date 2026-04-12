#!/usr/bin/env python3
"""Gemini Creative Pipeline v2 — Strategist-Led, Persona-Based, Logo-Aware.

Key upgrades over ``gemini_pipeline.py``:

1. STRATEGIST STEP
   A single "Creative Strategist" call analyzes brand + reviews + winner ads
   and outputs N diverse creative concepts (persona-targeted) as a JSON array.
   This produces more strategic coherence across the batch than generating
   concepts in isolation.

2. STRUCTURED ENGLISH PROMPT FORMAT
   All prompts fed into the image model follow:
     [Key visual] [Text overlay concept] [Secondary text / CTA] [Typography]
   Written as continuous English prose, with German text content quoted.

3. LOGO AS TRANSPARENT PNG INPUT
   branding/logo_white.png or logo_dark.png (chosen based on concept mood) is
   passed as an extra ``inline_data`` image. Gemini integrates it natively
   instead of trying to render the "ora" wordmark.

4. PERSONA-BASED VARIATION
   The Strategist picks diverse personas (Schwitzer, Rueckenschmerz-Geplagte,
   Paar, Performance-Optimierer, Mutter, Qualitaetsbewusster, Wiederkaeufer,
   Schlafloser) so every creative targets ONE specific segment with a
   tailored hook.

Architecture per batch::

    Step 1  STRATEGIST       -> 1  call  -> N concepts (JSON array)
    Step 2  PROMPT ENGINEER  -> N  calls -> structured English prompt each
    Step 3  IMAGE GENERATION -> N  calls -> final PNG each

Usage::

    python3 gemini_pipeline_v2.py --count 3
    python3 gemini_pipeline_v2.py --count 6 --personas "Der Schwitzer,Das Paar"
"""

import argparse
import atexit
import base64
import glob
import io
import json
import os
import random
import re
import signal
import sys
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

# Reuse the helpers already proven in main.py / gemini_pipeline.py
from main import (
    SupabaseClient,
    init_supabase,
    load_config,
    encode_image,
    acquire_process_lock,
    release_process_lock,
    PROJECT_ROOT,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEXT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

FORMATS = ["4:5", "9:16", "1:1"]
PRODUCT_IMAGES = [
    "products/images/ora-ultra-matratze/0.jpg",
    "products/images/ora-ultra-matratze/1.jpg",
]
WINNERS_DIR = os.path.join(PROJECT_ROOT, "winners", "assets")
CREATIVES_DIR = os.path.join(PROJECT_ROOT, "creatives")
BRANDING_DIR = os.path.join(PROJECT_ROOT, "branding")
REVIEWS_DIR = os.path.join(PROJECT_ROOT, "reviews")

LOGO_WHITE_PATH = os.path.join(BRANDING_DIR, "logo_white.png")
LOGO_DARK_PATH = os.path.join(BRANDING_DIR, "logo_dark.png")

MAX_WORKERS = 3                 # respect Gemini rate limits
TEXT_MAX_RETRIES = 3
IMAGE_MAX_RETRIES = 3
TEXT_TIMEOUT = 120
IMAGE_TIMEOUT = 240

DEFAULT_PERSONAS = [
    "Der Schwitzer",
    "Der Rueckenschmerz-Geplagte",
    "Das Paar",
    "Der Performance-Optimierer",
    "Die Mutter",
    "Der Qualitaetsbewusste",
    "Der Wiederkaeufer",
    "Der Schlaflose",
]

PERSONA_DESCRIPTIONS = {
    "Der Schwitzer": "can't sleep due to heat / night sweats, wakes up sticky",
    "Der Rueckenschmerz-Geplagte": "chronic back pain sufferer, wakes up stiff",
    "Das Paar": "couple, partners disturb each other at night (motion, heat)",
    "Der Performance-Optimierer": "athlete or high-performer optimizing recovery",
    "Die Mutter": "tired parent, broken sleep, desperate for recovery",
    "Der Qualitaetsbewusste": "premium buyer, wants the best, Swiss quality driven",
    "Der Wiederkaeufer": "existing happy customer buying a second mattress",
    "Der Schlaflose": "insomniac who lies awake for hours every night",
}


# ---------------------------------------------------------------------------
# Gemini primitives
# ---------------------------------------------------------------------------

def _gemini_text_call(api_key, parts, max_retries=TEXT_MAX_RETRIES, temperature=0.9,
                     max_output_tokens=4096):
    """Call Gemini text model and return the response text."""
    url = GEMINI_URL.format(model=TEXT_MODEL)
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "maxOutputTokens": max_output_tokens,
        },
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=TEXT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"    Warning: empty candidates (attempt {attempt + 1})")
                continue
            parts_out = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts_out).strip()
            if text:
                return text
            finish = candidates[0].get("finishReason", "")
            print(f"    Warning: no text in response (finish={finish})")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 8 * (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"    HTTP {status}: {e}")
            if attempt < max_retries - 1:
                time.sleep(4)
                continue
        except Exception as e:
            print(f"    Text call error: {e}")
            if attempt < max_retries - 1:
                time.sleep(4)
                continue
    return None


def _gemini_image_call(api_key, parts, aspect_ratio, max_retries=IMAGE_MAX_RETRIES):
    """Call Gemini image model and return (base64_data, mime_type)."""
    url = GEMINI_URL.format(model=IMAGE_MODEL)
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 0.85,
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": "2K",
            },
        },
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=IMAGE_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"    Warning: no candidates (attempt {attempt + 1})")
                continue
            parts_out = candidates[0].get("content", {}).get("parts", [])
            for part in parts_out:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    mime = inline.get("mimeType") or inline.get("mime_type", "image/png")
                    return inline["data"], mime
            for part in parts_out:
                if "text" in part:
                    print(f"    Gemini text fallback: {part['text'][:300]}")
            finish = candidates[0].get("finishReason", "")
            if finish:
                print(f"    Finish reason: {finish}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"    HTTP {status}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
        except Exception as e:
            print(f"    Image call error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
    return None, None


def _image_part(image_path):
    """Build an inline_data part for a local image file."""
    data, mime = encode_image(image_path)
    if data is None:
        return None
    return {"inline_data": {"mime_type": mime, "data": data}}


# ---------------------------------------------------------------------------
# Context loading (brand + reviews + refs)
# ---------------------------------------------------------------------------

def load_brand_context():
    """Load brand.json + brand_guidelines.json and compress to a text block."""
    with open(os.path.join(BRANDING_DIR, "brand.json")) as f:
        brand = json.load(f)
    try:
        with open(os.path.join(BRANDING_DIR, "brand_guidelines.json")) as f:
            guidelines = json.load(f)
    except FileNotFoundError:
        guidelines = {}

    product = brand["products"][0]  # Ora Ultra Matratze
    benefits = "\n".join(f"  - {b}" for b in product["benefits"])
    trust = ", ".join(brand.get("trust_signals", []))

    tov = guidelines.get("tone_of_voice", {})
    tone_spectrum = "\n".join(f"  - {s}" for s in tov.get("spectrum", []))

    diversity_principles = "\n".join(
        f"  - {p}" for p in guidelines.get("diversity_rules", {}).get("principles", [])
    )

    ctx = f"""Brand: {brand['name']} ({brand['tagline']})
Market: {brand['target_market']}, Language: German (du-form)
Category: {brand['category']}
Currency: {brand['currency']}

PRODUCT: {product['name']}
Price: from CHF {product['price_from']:.0f} (compare at CHF {product.get('compare_at_price', 0):.0f})
Rating: {product.get('rating', 'n/a')} / {product.get('reviews_count', 0)} reviews
Benefits:
{benefits}

Trust Signals: {trust}
Trustpilot: {brand.get('social_proof', {}).get('trustpilot_rating', 'n/a')} stars, {brand.get('social_proof', {}).get('trustpilot_reviews', 0)} reviews

TONE OF VOICE:
{tone_spectrum}

DIVERSITY PRINCIPLES (Andromeda Strategy):
{diversity_principles}
"""
    return ctx.strip(), brand, guidelines


def load_pain_points_summary(max_chars=2500):
    """Summarize customer reviews into a pain-points / wins block for the strategist.

    Pulls from ``reviews/trustpilot/summary.json`` if present, else tries
    ``reviews_raw.json``, else returns a static fallback summary.
    """
    summary_path = os.path.join(REVIEWS_DIR, "trustpilot", "summary.json")
    raw_path = os.path.join(REVIEWS_DIR, "trustpilot", "reviews_raw.json")

    if os.path.exists(summary_path):
        try:
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
            text = json.dumps(summary, ensure_ascii=False, indent=2)
            if len(text) <= max_chars:
                return text
            return text[:max_chars] + "\n... (truncated)"
        except Exception as e:
            print(f"  Warning: failed to read review summary: {e}")

    if os.path.exists(raw_path):
        try:
            with open(raw_path, encoding="utf-8") as f:
                reviews = json.load(f)
            if isinstance(reviews, dict):
                reviews = reviews.get("reviews", [])
            quotes = []
            for r in reviews[:20]:
                body = r.get("body") or r.get("text") or r.get("review") or ""
                rating = r.get("rating") or r.get("stars") or ""
                if body:
                    snippet = body.strip().replace("\n", " ")[:240]
                    quotes.append(f"- ({rating}*) {snippet}")
            joined = "\n".join(quotes)
            if len(joined) > max_chars:
                joined = joined[:max_chars] + "\n... (truncated)"
            return joined or "(no reviews available)"
        except Exception as e:
            print(f"  Warning: failed to read raw reviews: {e}")

    return (
        "- Many customers report chronic back / neck pain before switching\n"
        "- Heat build-up and night sweats common with previous mattresses\n"
        "- Couples disturbed by partner motion and temperature\n"
        "- Parents exhausted by broken sleep\n"
        "- Premium buyers care about Swiss Made, 10 year warranty, trial\n"
        "- Happy customers frequently mention morning energy improvement"
    )


def pick_visual_references(k=3):
    """Pick k random real-ad references from winners/assets/."""
    all_refs = sorted(glob.glob(os.path.join(WINNERS_DIR, "*.jpg")))
    all_refs += sorted(glob.glob(os.path.join(WINNERS_DIR, "*.jpeg")))
    all_refs += sorted(glob.glob(os.path.join(WINNERS_DIR, "*.png")))
    if not all_refs:
        print(f"  Warning: no reference ads in {WINNERS_DIR}")
        return []
    k = min(k, len(all_refs))
    return random.sample(all_refs, k)


# ---------------------------------------------------------------------------
# Step 1 — STRATEGIST (1 call, N concepts)
# ---------------------------------------------------------------------------

STRATEGIST_PROMPT = """You are a senior Creative Strategist for Ora Sleep, a Swiss premium mattress brand. Your job: analyze the brand's existing winning ads and generate {count} new creative concepts that will drive high ROAS and low CPM on Meta.

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

The visual reference ads attached are real high-performing Ora Sleep ads. Study their layout patterns, typography, color treatments, and compositional style — your concepts MUST match their quality.

Generate exactly {count} creative concepts. For each concept output this JSON object:

{{
  "concept_number": 1,
  "persona": "...",
  "angle": "Problem/Pain | Benefit | Proof | Offer | Story | Education | Curiosity",
  "hook": "The emotional/intellectual hook",
  "headline_de": "Main headline in German (max 8 words, bold and punchy)",
  "subline_de": "Supporting line in German (max 12 words)",
  "cta_de": "Call to action in German (2-4 words)",
  "visual_direction": "Lifestyle scene description (English)",
  "mood": "warm/cool/dramatic/editorial/minimal/etc",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "format_recommendation": "4:5 | 9:16 | 1:1",
  "product_placement": "Where the product appears in the scene"
}}

Output ONLY a JSON array of {count} concepts. No preamble, no markdown fences."""


def run_strategist(api_key, brand_context, pain_points_summary, ref_paths, count, personas):
    """Single strategist call producing N concepts as a JSON array."""
    persona_list = "\n".join(
        f"- {p} ({PERSONA_DESCRIPTIONS.get(p, '')})".rstrip() for p in personas
    )

    prompt_text = STRATEGIST_PROMPT.format(
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

    parts.append({"text": "\n\nNow output the JSON array."})

    raw = _gemini_text_call(
        api_key, parts, temperature=0.95, max_output_tokens=8192
    )
    if not raw:
        return None

    return _parse_strategist_json(raw, expected=count)


def _parse_strategist_json(raw, expected):
    """Be tolerant of markdown fences, leading preamble, etc."""
    text = raw.strip()

    # Strip markdown fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # First attempt: direct JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "concepts" in parsed:
            return parsed["concepts"]
    except Exception:
        pass

    # Fallback: pull the first JSON array substring
    match = re.search(r"\[\s*\{.*\}\s*\]", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            print(f"    Warning: JSON array substring parse failed: {e}")

    print(f"    ERROR: could not parse strategist output. First 500 chars:\n{text[:500]}")
    return None


# ---------------------------------------------------------------------------
# Step 2 — PROMPT ENGINEER (structured English prompt)
# ---------------------------------------------------------------------------

PROMPT_ENGINEER_SYSTEM = """You are an expert prompt writer for AI image generation models (specifically Gemini / nano banana). Transform this creative concept into a single, structured English prompt that will produce a high-performing static ad.

CONCEPT:
{concept_json}

The visual reference ads attached are real high-performing ads from the same brand — study their typography, layout, color treatments, and style. Your prompt MUST produce output that matches their quality and visual language.

PROMPT STRUCTURE (required):
[Key visual description] [Text overlay concept] [Secondary text/CTA] [Typography]

RULES:
- Write as continuous prose, no bullet points or headers
- Entirely in English EXCEPT the German text content (headline, subline, CTA)
- Describe composition, lighting, mood with cinematic precision
- Specify negative space for text placement
- Include exact German text quoted: "{headline_de}", "{subline_de}", "{cta_de}"
- Do NOT mention logos in the prompt (logo is added separately)
- Do NOT describe the product in detail (product image is attached)
- Describe where the product appears and how prominent it is
- Specify typography (serif/sans-serif, weight, style)
- Format: {format} aspect ratio

Output ONLY the final prompt paragraph. No preamble, no labels, no explanation."""


def run_prompt_engineer(api_key, concept, fmt, ref_paths):
    """Turn one concept dict into a single structured English prompt paragraph."""
    concept_json = json.dumps(concept, ensure_ascii=False, indent=2)
    prompt_text = PROMPT_ENGINEER_SYSTEM.format(
        concept_json=concept_json,
        headline_de=concept.get("headline_de", ""),
        subline_de=concept.get("subline_de", ""),
        cta_de=concept.get("cta_de", ""),
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
# Step 3 — IMAGE GENERATION (with logo PNG)
# ---------------------------------------------------------------------------

DARK_MOODS = {"warm", "dramatic", "editorial", "moody", "cinematic", "sunset", "night"}


def _pick_logo_path(concept):
    """Pick white or dark logo based on concept mood / background brightness hints."""
    mood = (concept.get("mood") or "").lower()
    palette = [c.lower() for c in concept.get("color_palette", [])]

    # If any dark hex is present or mood is dark -> use white logo
    def _is_dark_hex(h):
        if not isinstance(h, str) or not h.startswith("#") or len(h) < 7:
            return False
        try:
            r = int(h[1:3], 16)
            g = int(h[3:5], 16)
            b = int(h[5:7], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) < 128
        except Exception:
            return False

    has_dark = any(_is_dark_hex(c) for c in palette)
    dark_mood = any(tok in mood for tok in DARK_MOODS)

    if has_dark or dark_mood:
        if os.path.exists(LOGO_WHITE_PATH):
            return LOGO_WHITE_PATH, "white"
    if os.path.exists(LOGO_DARK_PATH):
        return LOGO_DARK_PATH, "dark"
    if os.path.exists(LOGO_WHITE_PATH):
        return LOGO_WHITE_PATH, "white"
    return None, None


def run_image_generation(api_key, structured_prompt, concept, fmt,
                         product_image_path, ref_paths):
    """Build the image-model call with product + refs + logo and return (data, mime)."""
    parts = []

    # Product image first
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

    # Logo PNG
    logo_path, logo_mode = _pick_logo_path(concept)
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

    # Final structured prompt + logo hint
    logo_hint = (
        " A transparent logo PNG is attached — integrate it subtly at the top of the "
        "ad (centered or top-left), sized small."
    )
    parts.append({"text": structured_prompt.strip() + logo_hint})

    aspect_map = {"4:5": "4:5", "9:16": "9:16", "1:1": "1:1", "16:9": "16:9"}
    aspect = aspect_map.get(fmt, "4:5")

    return _gemini_image_call(api_key, parts, aspect)


# ---------------------------------------------------------------------------
# Per-creative pipeline
# ---------------------------------------------------------------------------

def slugify(s):
    s = (s or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "creative"


def produce_one(api_key, sb, brand_id, batch_id, index, total, concept,
                product_image_rel, ref_paths, creative_id):
    """Run Prompt Engineer + Image Generation for a single concept."""
    prefix = f"[{index}/{total}]"
    persona = concept.get("persona", "Unknown")
    angle = concept.get("angle", "Benefit")
    headline = concept.get("headline_de", "")
    fmt = concept.get("format_recommendation") or FORMATS[index % len(FORMATS)]
    if fmt not in FORMATS:
        fmt = "4:5"

    print(f"\n{prefix} {persona} | {angle} | {fmt}")
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

    # Step 2 — Prompt Engineer
    print(f"{prefix}   Step 2: Prompt Engineer...")
    structured_prompt = run_prompt_engineer(api_key, concept, fmt, ref_paths)
    if not structured_prompt:
        print(f"{prefix}   FAILED at Step 2 (prompt engineer)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None
    print(f"{prefix}   Prompt OK ({len(structured_prompt)} chars)")

    # Step 3 — Image Generation
    print(f"{prefix}   Step 3: Image...")
    image_data, mime_type = run_image_generation(
        api_key, structured_prompt, concept, fmt, product_abs, ref_paths
    )
    if not image_data:
        print(f"{prefix}   FAILED at Step 3 (image gen)")
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
    filename = f"{index:03d}_{slugify(persona)}_{slugify(angle)}_{fmt_slug}.{ext}"

    local_dir = os.path.join(CREATIVES_DIR, str(batch_id))
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    # Save per-creative debug meta
    meta_path = os.path.join(local_dir, f"{index:03d}_{slugify(persona)}_meta.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "index": index,
                "persona": persona,
                "angle": angle,
                "format": fmt,
                "product_image": product_image_rel,
                "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
                "concept": concept,
                "structured_prompt": structured_prompt,
                "headline": headline,
                "subline": concept.get("subline_de", ""),
                "cta": concept.get("cta_de", ""),
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
                "hook_text": headline,
            })
        except Exception as e:
            print(f"{prefix}   Warning: DB update failed: {e}")

    print(f"{prefix}   DONE!")

    return {
        "index": index,
        "filename": filename,
        "local_path": local_path,
        "storage_path": storage_path,
        "image_url": image_url,
        "persona": persona,
        "angle": angle,
        "format": fmt,
        "product_image": product_image_rel,
        "headline": headline,
        "subline": concept.get("subline_de", ""),
        "cta": concept.get("cta_de", ""),
        "concept": concept,
        "structured_prompt": structured_prompt,
        "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
    }


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def pick_product_image(index):
    return PRODUCT_IMAGES[index % len(PRODUCT_IMAGES)]


def run_batch(api_key, sb, brand_id, count, personas_filter, output_dir=None):
    batch_id = str(uuid.uuid4())
    print(f"Batch ID: {batch_id}")
    print(f"Count: {count}  |  Workers: {MAX_WORKERS}")

    brand_context, brand_json, guidelines = load_brand_context()
    pain_points_summary = load_pain_points_summary()

    # Pick personas
    if personas_filter:
        personas = [p.strip() for p in personas_filter.split(",") if p.strip()]
        if not personas:
            personas = DEFAULT_PERSONAS
    else:
        personas = list(DEFAULT_PERSONAS)
    print(f"Persona pool: {', '.join(personas)}")

    # Shared strategist refs — top 5
    strategist_refs = pick_visual_references(k=5)
    print(f"Strategist refs: {[os.path.basename(r) for r in strategist_refs]}")

    # Step 1 — STRATEGIST
    print(f"\nStep 1: STRATEGIST ({count} concepts)...")
    concepts = run_strategist(
        api_key, brand_context, pain_points_summary,
        strategist_refs, count, personas,
    )
    if not concepts:
        print("FATAL: strategist returned no concepts, aborting batch")
        return None

    # Clamp to requested count
    if len(concepts) > count:
        concepts = concepts[:count]
    elif len(concepts) < count:
        print(f"Warning: strategist returned {len(concepts)} concepts, expected {count}")

    print(f"Strategist OK — {len(concepts)} concepts:")
    for i, c in enumerate(concepts, 1):
        print(f"  {i}. [{c.get('persona')}] {c.get('headline_de')!r} ({c.get('angle')})")

    # Build jobs with per-concept refs
    jobs = []
    for i, concept in enumerate(concepts):
        fmt = concept.get("format_recommendation") or FORMATS[i % len(FORMATS)]
        if fmt not in FORMATS:
            fmt = FORMATS[i % len(FORMATS)]
        jobs.append({
            "index": i + 1,
            "concept": concept,
            "format": fmt,
            "product_image": pick_product_image(i),
            "refs": pick_visual_references(k=3),
        })

    # Insert placeholder rows
    creative_ids = []
    for j in jobs:
        concept = j["concept"]
        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": concept.get("persona", "Unknown"),
            "sub_angle": concept.get("angle", ""),
            "variant": 1,
            "format": j["format"],
            "hook_text": concept.get("headline_de", ""),
            "status": "generating",
            "is_saved": False,
        }
        try:
            inserted = sb.insert_creative(row)
            creative_ids.append(inserted["id"])
        except Exception as e:
            print(f"  Warning: placeholder insert failed for [{j['index']}]: {e}")
            creative_ids.append(None)

    print(f"Inserted {sum(1 for c in creative_ids if c)} / {len(jobs)} placeholders")

    # Output dir + seed manifest
    local_dir = output_dir or os.path.join(CREATIVES_DIR, batch_id)
    os.makedirs(local_dir, exist_ok=True)

    # Dump strategist output up front for debugging
    strategist_path = os.path.join(local_dir, "strategist_concepts.json")
    try:
        with open(strategist_path, "w", encoding="utf-8") as f:
            json.dump(concepts, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  Warning: failed to write strategist dump: {e}")

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "batch_id": batch_id,
        "brand_id": brand_id,
        "pipeline": "gemini-v2-strategist-personas",
        "text_model": TEXT_MODEL,
        "image_model": IMAGE_MODEL,
        "total": len(jobs),
        "personas": personas,
        "strategist_refs": [os.path.relpath(r, PROJECT_ROOT) for r in strategist_refs],
        "concepts": concepts,
        "successful": 0,
        "failed": 0,
        "ads": [],
    }

    # Step 2 + 3 per concept in parallel
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for j, cid in zip(jobs, creative_ids):
            fut = executor.submit(
                produce_one,
                api_key, sb, brand_id, batch_id,
                j["index"], len(jobs),
                j["concept"], j["product_image"], j["refs"], cid,
            )
            futures[fut] = j["index"]

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

    # Stable ordering
    results.sort(key=lambda r: r["index"])
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
        description="Gemini Creative Pipeline v2 — Strategist-Led + Personas + Logo PNG"
    )
    parser.add_argument("--count", type=int, default=3, help="Number of creatives (default: 3)")
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
    parser.add_argument("--brand-id", default=None, help="Brand UUID (auto-detected if omitted)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.count <= 0:
        print("Error: --count must be > 0")
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

    run_batch(api_key, sb, brand_id, args.count, args.personas, args.output_dir)


if __name__ == "__main__":
    main()
