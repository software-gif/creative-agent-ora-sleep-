#!/usr/bin/env python3
"""
generate-motion.py — Add motion to an image using Kling 3.0 Pro.

Usage (run from project root):
  python3 skills/references/generate-motion.py brands/[brand]/motion/[output-name]

Reads add-motion-spec.json from the output folder.

Output: motion_v1.mp4, motion_v2.mp4, ... (auto-incremented)

Pricing:
  Audio off: $0.112/sec  (5s = ~$0.56)
  Audio on:  $0.168/sec  (5s = ~$0.84)
"""

import json
import os
import sys
from pathlib import Path

import fal_client
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VIDEO_MODEL = "fal-ai/kling-video/v3/pro/image-to-video"


def _load_env_file() -> None:
    if os.environ.get("FAL_KEY"):
        return
    search = Path.cwd()
    for _ in range(5):
        env_file = search / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val
            return
        parent = search.parent
        if parent == search:
            break
        search = parent


_load_env_file()
FAL_KEY = os.environ.get("FAL_KEY", "")


def check_fal_key() -> None:
    if not FAL_KEY:
        sys.exit("Error: FAL_KEY not found. Add it to .env at the project root.")
    os.environ["FAL_KEY"] = FAL_KEY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(path: Path, label: str) -> str:
    print(f"  Uploading {label}...", end=" ", flush=True)
    url = fal_client.upload_file(str(path))
    print("✓")
    return url


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 skills/references/generate-motion.py brands/[brand]/motion/[output-name]")

    output_dir = Path(sys.argv[1])
    spec_path  = output_dir / "add-motion-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: add-motion-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    output_name       = spec.get("output_name", output_dir.name)
    source_image      = Path(spec["source_image"])
    end_image         = Path(spec["end_image"]) if spec.get("end_image") else None
    motion_description = spec.get("motion_description", "")
    product_images    = [Path(p) for p in spec.get("product_images", [])]
    duration          = int(spec.get("duration", 5))
    generate_audio    = bool(spec.get("generate_audio", False))
    aspect_ratio      = spec.get("aspect_ratio", "9:16")

    if not source_image.exists():
        sys.exit(f"Error: source image not found: {source_image}")
    if end_image and not end_image.exists():
        sys.exit(f"Error: end frame not found: {end_image}")
    for p in product_images:
        if not p.exists():
            sys.exit(f"Error: product image not found: {p}")

    if not 3 <= duration <= 15:
        sys.exit(f"Error: duration must be 3–15 seconds, got {duration}.")

    check_fal_key()

    print(f"\n{output_name} — add motion")
    print("Uploading images...")

    start_url = _upload(source_image, f"start frame: {source_image.name}")
    end_url   = _upload(end_image, f"end frame: {end_image.name}") if end_image else None

    # Build elements from product images (Element1, Element2, ...)
    elements = []
    if product_images:
        print("Uploading product reference images...")
        for i, prod_path in enumerate(product_images, start=1):
            prod_url = _upload(prod_path, f"product reference (Element{i}): {prod_path.name}")
            elements.append({"frontal_image_url": prod_url, "reference_image_urls": [prod_url], "name": f"Element{i}"})

    # Build prompt — append element references if product images present
    prompt = motion_description
    if elements:
        element_refs = " ".join(f"@Element{i+1}" for i in range(len(elements)))
        prompt += f" Maintain the exact product appearance shown in {element_refs} — preserve all labels, branding, and physical details throughout."

    (output_dir / "motion-prompt.txt").write_text(prompt)

    # Estimate cost
    rate = 0.168 if generate_audio else 0.112
    cost = duration * rate
    print(f"\nGenerating {duration}s video at {aspect_ratio} ({'audio on' if generate_audio else 'audio off'}) — est. ${cost:.2f}")

    payload = {
        "start_image_url": start_url,
        "prompt":          prompt,
        "duration":        duration,
        "aspect_ratio":    aspect_ratio,
        "generate_audio":  generate_audio,
        "cfg_scale":       0.5,
    }
    if end_url:
        payload["end_image_url"] = end_url
    if elements:
        payload["elements"] = elements

    result = fal_client.run(VIDEO_MODEL, arguments=payload)

    video = result.get("video", {})
    video_url = video.get("url") if isinstance(video, dict) else None
    if not video_url:
        sys.exit("Error: no video returned from Kling.")

    version = 1
    while (output_dir / f"motion_v{version}.mp4").exists():
        version += 1
    out_path = output_dir / f"motion_v{version}.mp4"

    print("  Downloading video...", end=" ", flush=True)
    _download(video_url, out_path)
    print("✓")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
