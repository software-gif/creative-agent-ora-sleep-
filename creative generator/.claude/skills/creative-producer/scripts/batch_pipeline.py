#!/usr/bin/env python3
"""Batch Pipeline — Generates multiple creatives via the compositing pipeline
and uploads them to Supabase.

This is the pipeline equivalent of main.py. Most creatives are generated purely
locally (color, gradient, photo backgrounds) in ~1-2 seconds each. Only configs
with background.mode == "gemini" require an API call.

Usage:
    python3 batch_pipeline.py --configs-file creatives/pipeline_configs.json
    python3 batch_pipeline.py --configs-file configs.json --brand-id <uuid>
"""

import argparse
import atexit
import base64
import io
import json
import os
import re
import signal
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: 'python-dotenv' not installed. Run: pip3 install python-dotenv")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

# Add scripts dir to path so we can import sibling modules
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from pipeline import run_pipeline
from main import (
    SupabaseClient,
    init_supabase,
    acquire_process_lock,
    release_process_lock,
    load_config as load_gemini_config,
    build_gemini_prompt,
    call_gemini,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    """Convert a string to ASCII-safe slug."""
    s = s.lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _load_env():
    """Load .env file from project root."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ---------------------------------------------------------------------------
# Single creative generation
# ---------------------------------------------------------------------------

def generate_single_creative(
    sb: SupabaseClient,
    brand_id: str,
    batch_id: str,
    entry: dict,
    index: int,
    creative_id: str,
    api_key: str = None,
) -> dict:
    """Generate a single creative via the pipeline, upload to Supabase.

    Args:
        sb:          Supabase client.
        brand_id:    Brand UUID.
        batch_id:    Batch UUID for grouping.
        entry:       Dict with "pipeline_config" and "meta" keys.
        index:       1-based index for logging/filenames.
        creative_id: Pre-inserted Supabase row ID.
        api_key:     Gemini API key (only needed for gemini background mode).

    Returns:
        Manifest entry dict on success, None on failure.
    """
    pipeline_config = entry["pipeline_config"]
    meta = entry["meta"]
    bg_mode = pipeline_config.get("background", {}).get("mode", "color")

    angle = meta.get("angle", "Unknown")
    sub_angle = meta.get("sub_angle", "Unknown")
    fmt = meta.get("format", pipeline_config.get("format", "4:5"))
    hook_text = meta.get("hook_text", "")

    print(f"\n[{index}] {angle} > {sub_angle} ({fmt}, bg={bg_mode})")

    try:
        # --- If Gemini background, generate it first ---
        if bg_mode == "gemini":
            if not api_key:
                print(f"  ERROR: Gemini background requested but no API key available")
                sb.update_creative(creative_id, {"status": "failed"})
                return None

            gemini_prompt_cfg = pipeline_config.get("background", {}).get("gemini_prompt")
            product_image_path = pipeline_config.get("background", {}).get("product_image", "")
            img_path = os.path.join(PROJECT_ROOT, product_image_path) if product_image_path else ""

            if gemini_prompt_cfg:
                print(f"  Generating Gemini background...")
                payload = build_gemini_prompt(gemini_prompt_cfg, img_path)
                image_data, mime_type = call_gemini(api_key, payload)

                if not image_data:
                    print(f"  FAILED: No Gemini image generated")
                    sb.update_creative(creative_id, {"status": "failed"})
                    return None

                gemini_bytes = base64.standard_b64decode(image_data)
                pipeline_config["background"]["gemini_bytes"] = gemini_bytes
                print(f"  Gemini background ready ({len(gemini_bytes) / 1024:.0f} KB)")
            else:
                print(f"  ERROR: gemini mode but no gemini_prompt in config")
                sb.update_creative(creative_id, {"status": "failed"})
                return None

        # --- Run the pipeline ---
        png_bytes = run_pipeline(pipeline_config, PROJECT_ROOT)

        if not png_bytes:
            print(f"  FAILED: Pipeline returned no data")
            sb.update_creative(creative_id, {"status": "failed"})
            return None

        # --- Build filename ---
        angle_slug = _slugify(angle)
        sub_slug = _slugify(sub_angle)
        fmt_slug = fmt.replace(":", "x")
        filename = f"{index:03d}_{angle_slug}_{sub_slug}_{fmt_slug}.png"

        # --- Upload to Supabase Storage ---
        storage_path = f"{brand_id}/{batch_id}/{filename}"
        try:
            sb.upload_file("creatives", storage_path, png_bytes, "image/png")
            image_url = sb.get_public_url("creatives", storage_path)
            print(f"  Uploaded: {storage_path} ({len(png_bytes) / 1024:.0f} KB)")
        except Exception as e:
            print(f"  Upload failed: {e}")
            sb.update_creative(creative_id, {"status": "failed"})
            return None

        # --- Update DB entry ---
        sb.update_creative(creative_id, {
            "status": "done",
            "storage_path": storage_path,
            "image_url": image_url,
        })
        print(f"  Creative updated: image live!")

        # --- Save locally ---
        local_dir = os.path.join(PROJECT_ROOT, "creatives", str(batch_id))
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        with open(local_path, "wb") as f:
            f.write(png_bytes)

        return {
            "index": index,
            "filename": filename,
            "storage_path": storage_path,
            "image_url": image_url,
            "angle": angle,
            "sub_angle": sub_angle,
            "format": fmt,
            "hook_text": hook_text,
            "background_mode": bg_mode,
        }

    except Exception as e:
        print(f"  ERROR generating creative [{index}]: {e}")
        try:
            sb.update_creative(creative_id, {"status": "failed"})
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_batch(sb: SupabaseClient, brand_id: str, entries: list, api_key: str = None) -> dict:
    """Generate all creatives, splitting between fast (local) and slow (Gemini) pools.

    Non-Gemini configs run with 8 parallel workers.
    Gemini configs run with 3 parallel workers (API rate limiting).
    """
    batch_id = str(uuid.uuid4())
    print(f"\nBatch ID: {batch_id}")
    print(f"Total configs: {len(entries)}")

    # --- Separate Gemini vs non-Gemini configs ---
    gemini_entries = []
    local_entries = []

    for i, entry in enumerate(entries, 1):
        bg_mode = entry.get("pipeline_config", {}).get("background", {}).get("mode", "color")
        if bg_mode == "gemini":
            gemini_entries.append((i, entry))
        else:
            local_entries.append((i, entry))

    print(f"  Local (fast): {len(local_entries)}")
    print(f"  Gemini (slow): {len(gemini_entries)}")

    # --- Insert ALL placeholders into Supabase ---
    creative_ids = {}  # index -> creative_id
    for i, entry in enumerate(entries, 1):
        meta = entry.get("meta", {})
        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": meta.get("angle", "Unknown"),
            "sub_angle": meta.get("sub_angle", "Unknown"),
            "format": meta.get("format", entry.get("pipeline_config", {}).get("format", "4:5")),
            "hook_text": meta.get("hook_text", ""),
            "status": "generating",
            "is_saved": False,
            "creative_style": meta.get("creative_style", "pipeline"),
            "creative_type": meta.get("creative_type", "product_static"),
        }
        try:
            inserted = sb.insert_creative(row)
            creative_ids[i] = inserted["id"]
            print(f"  Placeholder [{i}]: {meta.get('angle', '?')} > {meta.get('sub_angle', '?')}")
        except Exception as e:
            print(f"  Error inserting placeholder [{i}]: {e}")
            creative_ids[i] = None

    print(f"\nAll {len(entries)} placeholders inserted into Supabase")

    # --- Build manifest ---
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "batch_id": batch_id,
        "brand_id": brand_id,
        "total_configs": len(entries),
        "local_count": len(local_entries),
        "gemini_count": len(gemini_entries),
        "successful": 0,
        "failed": 0,
        "ads": [],
    }

    # --- Process local (fast) configs first ---
    if local_entries:
        print(f"\n{'='*60}")
        print(f"PHASE 1: Local pipeline ({len(local_entries)} creatives, 8 workers)")
        print(f"{'='*60}")

        max_workers = min(8, len(local_entries))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for idx, entry in local_entries:
                cid = creative_ids.get(idx)
                if cid is None:
                    manifest["failed"] += 1
                    continue
                future = executor.submit(
                    generate_single_creative,
                    sb, brand_id, batch_id, entry, idx, cid, None,
                )
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    if result:
                        manifest["successful"] += 1
                        manifest["ads"].append(result)
                    else:
                        manifest["failed"] += 1
                except Exception as e:
                    print(f"  Error in creative {idx}: {e}")
                    manifest["failed"] += 1

    # --- Process Gemini configs ---
    if gemini_entries:
        print(f"\n{'='*60}")
        print(f"PHASE 2: Gemini pipeline ({len(gemini_entries)} creatives, 3 workers)")
        print(f"{'='*60}")

        if not api_key:
            print("  WARNING: No Gemini API key — skipping all Gemini configs")
            manifest["failed"] += len(gemini_entries)
        else:
            max_workers = min(3, len(gemini_entries))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for idx, entry in gemini_entries:
                    cid = creative_ids.get(idx)
                    if cid is None:
                        manifest["failed"] += 1
                        continue
                    future = executor.submit(
                        generate_single_creative,
                        sb, brand_id, batch_id, entry, idx, cid, api_key,
                    )
                    futures[future] = idx

                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        if result:
                            manifest["successful"] += 1
                            manifest["ads"].append(result)
                        else:
                            manifest["failed"] += 1
                    except Exception as e:
                        print(f"  Error in creative {idx}: {e}")
                        manifest["failed"] += 1

    # Sort manifest ads by index
    manifest["ads"].sort(key=lambda a: a["index"])

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch Pipeline — Generate multiple creatives via compositing pipeline + Supabase"
    )
    parser.add_argument(
        "--configs-file", required=True,
        help="Path to JSON file with array of pipeline configs (each with pipeline_config + meta)"
    )
    parser.add_argument(
        "--brand-id", default=None,
        help="Brand UUID (auto-detected from Supabase if omitted)"
    )
    args = parser.parse_args()

    # Prevent concurrent runs
    acquire_process_lock()
    atexit.register(release_process_lock)

    def handle_signal(sig, frame):
        print(f"\nInterrupted (signal {sig}) — cleaning up...")
        release_process_lock()
        sys.exit(1)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Load environment
    _load_env()
    sb = init_supabase()

    # Auto-detect brand if not provided
    if args.brand_id:
        try:
            uuid.UUID(args.brand_id)
        except ValueError:
            print(f"Error: --brand-id must be a valid UUID, got: {args.brand_id}")
            sys.exit(1)
        brand_id = args.brand_id
    else:
        brand_id = sb.get_single_brand_id()
        print(f"Auto-detected brand: {brand_id}")

    # Load configs
    configs_path = args.configs_file
    if not os.path.isabs(configs_path):
        configs_path = os.path.join(PROJECT_ROOT, configs_path)

    if not os.path.exists(configs_path):
        print(f"Error: Configs file not found: {configs_path}")
        sys.exit(1)

    with open(configs_path) as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        entries = [entries]

    print(f"Loaded {len(entries)} pipeline configs from {configs_path}")
    print(f"Brand: {brand_id}")

    # Check if any configs need Gemini
    has_gemini = any(
        e.get("pipeline_config", {}).get("background", {}).get("mode") == "gemini"
        for e in entries
    )

    api_key = None
    if has_gemini:
        try:
            api_key = load_gemini_config()
            print(f"Gemini API key loaded (needed for {sum(1 for e in entries if e.get('pipeline_config', {}).get('background', {}).get('mode') == 'gemini')} configs)")
        except SystemExit:
            print("WARNING: Gemini API key not available — Gemini backgrounds will fail")

    # Run batch
    t_start = time.time()
    manifest = run_batch(sb, brand_id, entries, api_key)
    elapsed = time.time() - t_start

    # Save manifest locally
    batch_dir = os.path.join(PROJECT_ROOT, "creatives", manifest["batch_id"])
    os.makedirs(batch_dir, exist_ok=True)
    manifest_path = os.path.join(batch_dir, "manifest.json")

    manifest["elapsed_seconds"] = round(elapsed, 1)

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total:     {manifest['total_configs']}")
    print(f"  Success:   {manifest['successful']}")
    print(f"  Failed:    {manifest['failed']}")
    print(f"  Time:      {elapsed:.1f}s ({elapsed / max(manifest['total_configs'], 1):.1f}s avg)")
    print(f"  Batch ID:  {manifest['batch_id']}")
    print(f"  Manifest:  {manifest_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
