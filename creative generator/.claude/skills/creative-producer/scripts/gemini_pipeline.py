#!/usr/bin/env python3
"""Gemini 3-Step Creative Pipeline with Visual References.

This pipeline replaces the PIL-compositing approach. Instead of stitching
headlines onto Gemini backgrounds, we pass 2-3 REAL high-performing Ora Sleep
ads as visual references along with the product image to Gemini's image
generation model. Gemini learns the style from examples — not from text.

Architecture (per creative):
    Step 1 — CONCEPT      (Gemini text)  -> headline/subline/cta/layout
    Step 2 — AD PROMPT    (Gemini text)  -> detailed image-gen prompt
    Step 3 — IMAGE        (Gemini image) -> final PNG

Usage:
    python3 gemini_pipeline.py --count 6
    python3 gemini_pipeline.py --count 12 --angle mix
    python3 gemini_pipeline.py --count 3 --angle "Problem/Pain"
"""

import argparse
import atexit
import base64
import glob
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

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

# Reuse the helpers already proven in main.py
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

MAX_WORKERS = 3                 # respect Gemini rate limits
TEXT_MAX_RETRIES = 3
IMAGE_MAX_RETRIES = 3
TEXT_TIMEOUT = 90
IMAGE_TIMEOUT = 240


# ---------------------------------------------------------------------------
# Gemini primitives
# ---------------------------------------------------------------------------

def _gemini_text_call(api_key, parts, max_retries=TEXT_MAX_RETRIES, temperature=0.9):
    """Call Gemini text model and return the response text."""
    url = GEMINI_URL.format(model=TEXT_MODEL)
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "maxOutputTokens": 2048,
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
                import time
                time.sleep(wait)
                continue
            print(f"    HTTP {status}: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(4)
                continue
        except Exception as e:
            print(f"    Text call error: {e}")
            if attempt < max_retries - 1:
                import time
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
            # No image — log text for debugging
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
                import time
                time.sleep(wait)
                continue
            print(f"    HTTP {status}: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(5)
                continue
        except Exception as e:
            print(f"    Image call error: {e}")
            if attempt < max_retries - 1:
                import time
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
# Brand + angle context
# ---------------------------------------------------------------------------

def load_brand_context():
    """Load brand.json + brand_guidelines.json and compress to a text block."""
    with open(os.path.join(PROJECT_ROOT, "branding", "brand.json")) as f:
        brand = json.load(f)
    try:
        with open(os.path.join(PROJECT_ROOT, "branding", "brand_guidelines.json")) as f:
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


def load_angles():
    with open(os.path.join(PROJECT_ROOT, "angles", "angles.json")) as f:
        return json.load(f)["angles"]


def pick_visual_references(k=3, angle_type=None):
    """Pick k random real-ad references from winners/assets/.

    angle_type is currently unused for selection (random is fine for v1), but
    kept so we can add type-aware selection later without changing callers.
    """
    all_refs = sorted(glob.glob(os.path.join(WINNERS_DIR, "*.jpg")))
    all_refs += sorted(glob.glob(os.path.join(WINNERS_DIR, "*.jpeg")))
    all_refs += sorted(glob.glob(os.path.join(WINNERS_DIR, "*.png")))
    if not all_refs:
        print(f"  Warning: no reference ads in {WINNERS_DIR}")
        return []
    k = min(k, len(all_refs))
    return random.sample(all_refs, k)


def infer_target_emotion(angle):
    """Heuristic mapping from angle type to target emotion."""
    t = angle.get("type", "")
    mapping = {
        "Problem/Pain": "relief, validation, hope",
        "Benefit": "excitement, aspiration, comfort",
        "Proof": "trust, credibility, reassurance",
        "Story": "connection, authenticity, warmth",
        "Curiosity": "intrigue, surprise, pattern-interrupt",
        "Education": "enlightenment, authority, clarity",
        "Offer": "urgency, value, action",
    }
    return mapping.get(t, "trust and comfort")


# ---------------------------------------------------------------------------
# Step 1 — Concept generation
# ---------------------------------------------------------------------------

STEP1_SYSTEM = """You are a senior creative director for Ora Sleep, a Swiss mattress brand.

BRAND CONTEXT:
{brand_context}

CREATIVE BRIEF:
- Angle: {angle_name} ({angle_type})
- Target emotion: {target_emotion}
- Key message: {key_message}
- Data points: {data_points}
- Health claims guardrail: NEVER promise cures. Only report customer feedback.
  Use "49% unserer Kunden berichten..." not "heilt Rückenschmerzen".

The product image is attached. Study the visual reference ads carefully — these are
high-performing real Ora Sleep ads that define the brand's visual language. Your concept
MUST match their quality, layout style, typography approach, and visual direction.

Generate a static ad concept with this EXACT structure (German copy, no English):

Headline: <bold, impactful, max 8 words, German>
Subline: <small supporting line above or below headline, max 10 words, German>
Call-to-action: <2-4 words, German>
Visual Composition:
  Product placement: <where and how the product appears>
  Layout suggestion: <describe the specific layout>
  Background / environment: <specific background description>
  Style & mood: <photography style, mood, emotional tone>
  Color palette: <3-5 specific colors with hex codes>
  Additional elements: <badges, trust signals, data points>

Output ONLY the concept in this format. No preamble, no explanation."""


def step1_concept(api_key, brand_context, angle, product_image_path, ref_paths):
    """Step 1: generate a structured ad concept."""
    hook = random.choice(angle.get("hook_variants", [""])) if angle.get("hook_variants") else ""
    headline_hint = random.choice(angle.get("headline_variants", [""])) if angle.get("headline_variants") else ""
    key_message = hook or headline_hint

    prompt_text = STEP1_SYSTEM.format(
        brand_context=brand_context,
        angle_name=angle["name"],
        angle_type=angle.get("type", "Benefit"),
        target_emotion=infer_target_emotion(angle),
        key_message=key_message,
        data_points=angle.get("data_point", ""),
    )

    parts = [{"text": prompt_text}]

    # Product image
    pp = _image_part(product_image_path)
    if pp:
        parts.append({"text": "\n\nPRODUCT IMAGE (the mattress to feature):"})
        parts.append(pp)

    # Visual references
    if ref_paths:
        parts.append({"text": "\n\nVISUAL REFERENCE ADS (real high-performing Ora Sleep ads — match their style):"})
        for rp in ref_paths:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    parts.append({"text": "\n\nNow produce the concept."})

    return _gemini_text_call(api_key, parts, temperature=0.95)


# ---------------------------------------------------------------------------
# Step 2 — Ad prompt generation
# ---------------------------------------------------------------------------

STEP2_SYSTEM = """You are an expert at writing prompts for Gemini image generation
to produce professional Meta advertisements.

Given this ad concept:

{concept_output}

And studying the visual reference ads attached (these are real high-performing ads from
the same brand), write a SINGLE detailed image-generation prompt that will produce a
static ad matching the concept and visual style of the references.

Requirements:
- Format: {format} aspect ratio
- Must include the product from the attached product image, clearly visible
- Must render all text: headline, subline, CTA — in correct German spelling
- Must match the visual style of the reference ads (typography, layout, color treatment,
  photography style)
- Text must be perfectly readable and correctly spelled in German (use Umlaute: ä ö ü ß)
- No AI artifacts, no distorted anatomy, no gibberish text
- Photorealistic quality, professional ad production value

Output ONLY the final image generation prompt. No preamble, no explanation, no markdown
headings, no lists. Plain natural language prompt ready to feed into Gemini."""


def step2_ad_prompt(api_key, concept_output, fmt, product_image_path, ref_paths):
    """Step 2: transform concept into a detailed image-gen prompt."""
    prompt_text = STEP2_SYSTEM.format(concept_output=concept_output, format=fmt)
    parts = [{"text": prompt_text}]

    pp = _image_part(product_image_path)
    if pp:
        parts.append({"text": "\n\nPRODUCT IMAGE:"})
        parts.append(pp)

    if ref_paths:
        parts.append({"text": "\n\nVISUAL REFERENCE ADS:"})
        for rp in ref_paths:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    parts.append({"text": "\n\nWrite the image generation prompt now."})
    return _gemini_text_call(api_key, parts, temperature=0.8)


# ---------------------------------------------------------------------------
# Step 3 — Image generation
# ---------------------------------------------------------------------------

def step3_image(api_key, image_prompt, fmt, product_image_path, ref_paths):
    """Step 3: generate the final ad image."""
    parts = []

    # Intro text orienting the model
    parts.append({"text": (
        "You are generating a professional static advertisement for Ora Sleep, a Swiss "
        "mattress brand. Follow the detailed prompt below exactly. The attached product "
        "image shows the exact mattress to feature. The attached reference ads define the "
        "brand's visual language — match their production quality, typography style, "
        "layout approach, and overall polish. Render all German text with correct "
        "spelling and Umlaute.\n\n"
    )})

    # Product image (keep first so the model anchors on it)
    pp = _image_part(product_image_path)
    if pp:
        parts.append({"text": "PRODUCT IMAGE (use this exact mattress):\n"})
        parts.append(pp)

    # Reference ads (use 2-3)
    use_refs = ref_paths[: min(3, len(ref_paths))]
    if use_refs:
        parts.append({"text": "\nREFERENCE ADS (match this style and quality):\n"})
        for rp in use_refs:
            ip = _image_part(rp)
            if ip:
                parts.append(ip)

    # The detailed prompt from step 2
    parts.append({"text": f"\nIMAGE PROMPT:\n{image_prompt}\n\nGenerate the final advertisement image now."})

    aspect_map = {"4:5": "4:5", "9:16": "9:16", "1:1": "1:1", "16:9": "16:9"}
    aspect = aspect_map.get(fmt, "4:5")

    return _gemini_image_call(api_key, parts, aspect)


# ---------------------------------------------------------------------------
# Concept parsing (lightweight — only for DB fields)
# ---------------------------------------------------------------------------

def parse_headline(concept_text):
    if not concept_text:
        return ""
    m = re.search(r"^\s*Headline\s*:\s*(.+)$", concept_text, re.MULTILINE | re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"').strip("*")
    return ""


def slugify(s):
    s = (s or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "creative"


# ---------------------------------------------------------------------------
# Single creative pipeline
# ---------------------------------------------------------------------------

def produce_one(
    api_key, sb, brand_id, batch_id, index, total,
    angle, fmt, product_image_rel, ref_paths, brand_context, creative_id
):
    """Run the 3-step pipeline for a single creative."""
    prefix = f"[{index}/{total}]"
    angle_name = angle["name"]
    angle_type = angle.get("type", "")
    print(f"\n{prefix} {angle_name} ({angle_type}) - {fmt} - {os.path.basename(product_image_rel)}")
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

    # Step 1 — Concept
    print(f"{prefix}   Step 1: Concept...")
    concept = step1_concept(api_key, brand_context, angle, product_abs, ref_paths)
    if not concept:
        print(f"{prefix}   FAILED at Step 1 (concept)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None
    headline = parse_headline(concept)
    print(f"{prefix}   Concept OK (headline: {headline[:60]!r})")

    # Step 2 — Ad prompt
    print(f"{prefix}   Step 2: Prompt...")
    image_prompt = step2_ad_prompt(api_key, concept, fmt, product_abs, ref_paths)
    if not image_prompt:
        print(f"{prefix}   FAILED at Step 2 (ad prompt)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None
    print(f"{prefix}   Prompt OK ({len(image_prompt)} chars)")

    # Step 3 — Image
    print(f"{prefix}   Step 3: Image...")
    image_data, mime_type = step3_image(api_key, image_prompt, fmt, product_abs, ref_paths)
    if not image_data:
        print(f"{prefix}   FAILED at Step 3 (image gen)")
        if creative_id:
            try:
                sb.update_creative(creative_id, {"status": "failed"})
            except Exception:
                pass
        return None

    # Decode + persist locally
    image_bytes = base64.standard_b64decode(image_data)
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    ext = ext_map.get(mime_type, "png")

    fmt_slug = fmt.replace(":", "x")
    filename = f"{index:03d}_{slugify(angle_name)}_{fmt_slug}.{ext}"

    local_dir = os.path.join(CREATIVES_DIR, str(batch_id))
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    # Save concept + prompt alongside for debugging
    meta_path = os.path.join(local_dir, f"{index:03d}_{slugify(angle_name)}_meta.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "index": index,
                "angle": angle_name,
                "angle_type": angle_type,
                "format": fmt,
                "product_image": product_image_rel,
                "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
                "concept": concept,
                "image_prompt": image_prompt,
                "headline": headline,
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
        "angle": angle_name,
        "angle_type": angle_type,
        "format": fmt,
        "product_image": product_image_rel,
        "headline": headline,
        "concept": concept,
        "image_prompt": image_prompt,
        "ref_paths": [os.path.relpath(r, PROJECT_ROOT) for r in ref_paths],
    }


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def pick_angles(all_angles, count, angle_filter):
    """Pick angles for a batch. angle_filter: None / 'mix' / exact name / type."""
    if angle_filter and angle_filter.lower() != "mix":
        # Exact name match
        exact = [a for a in all_angles if a["name"].lower() == angle_filter.lower()]
        if exact:
            return [exact[0]] * count
        # Type match
        by_type = [a for a in all_angles if a.get("type", "").lower() == angle_filter.lower()]
        if by_type:
            return [by_type[i % len(by_type)] for i in range(count)]
        print(f"Warning: angle filter '{angle_filter}' matched nothing. Using mix.")
    # Mix: rotate through shuffled angles
    pool = list(all_angles)
    random.shuffle(pool)
    return [pool[i % len(pool)] for i in range(count)]


def pick_format(index):
    """Equal distribution across formats."""
    return FORMATS[index % len(FORMATS)]


def pick_product_image(index):
    return PRODUCT_IMAGES[index % len(PRODUCT_IMAGES)]


def run_batch(api_key, sb, brand_id, count, angle_filter):
    batch_id = str(uuid.uuid4())
    print(f"Batch ID: {batch_id}")
    print(f"Count: {count}  |  Angle filter: {angle_filter or 'mix'}")
    print(f"Workers: {MAX_WORKERS}")

    brand_context, brand_json, guidelines = load_brand_context()
    all_angles = load_angles()
    picked_angles = pick_angles(all_angles, count, angle_filter)

    # Build jobs
    jobs = []
    for i in range(count):
        angle = picked_angles[i]
        fmt = pick_format(i)
        product_image = pick_product_image(i)
        refs = pick_visual_references(k=3, angle_type=angle.get("type"))
        jobs.append({
            "index": i + 1,
            "angle": angle,
            "format": fmt,
            "product_image": product_image,
            "refs": refs,
        })

    # Insert placeholder rows (best effort — non-fatal if it fails)
    creative_ids = []
    for j in jobs:
        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": j["angle"]["name"],
            "sub_angle": j["angle"].get("type", ""),
            "variant": 1,
            "format": j["format"],
            "hook_text": "",
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

    # Local dir + seed manifest
    local_dir = os.path.join(CREATIVES_DIR, batch_id)
    os.makedirs(local_dir, exist_ok=True)

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "batch_id": batch_id,
        "brand_id": brand_id,
        "pipeline": "gemini-3-step-visual-refs",
        "text_model": TEXT_MODEL,
        "image_model": IMAGE_MODEL,
        "total": count,
        "angle_filter": angle_filter or "mix",
        "successful": 0,
        "failed": 0,
        "ads": [],
    }

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for j, cid in zip(jobs, creative_ids):
            fut = executor.submit(
                produce_one,
                api_key, sb, brand_id, batch_id,
                j["index"], count,
                j["angle"], j["format"], j["product_image"], j["refs"],
                brand_context, cid,
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
        description="Gemini 3-Step Creative Pipeline with Visual References"
    )
    parser.add_argument("--count", type=int, default=6, help="Number of creatives (default: 6)")
    parser.add_argument(
        "--angle",
        default="mix",
        help="'mix' (default), exact angle name, or angle type (e.g. 'Problem/Pain')",
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

    run_batch(api_key, sb, brand_id, args.count, args.angle)


if __name__ == "__main__":
    main()
