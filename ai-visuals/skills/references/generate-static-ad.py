#!/usr/bin/env python3
"""
generate-static-ad.py — Static ad generation.

Passes the variation prompt and product reference images directly to Nano Banana.
Product images are Images 1, 2, ... — the prompt describes the full ad layout,
composition, copy, and safe zone constraints.

Usage (run from project root):
  python3 skills/references/generate-static-ad.py brands/[brand]/static-ads/[output-name] [variation-slug]

Example:
  python3 skills/references/generate-static-ad.py brands/puresport/static-ads/calling-tongkat-ali var-1

Reads static-ad-spec.json from the output folder.

Output: [output-name]-[slug]_v1.png, [output-name]-[slug]_v2.png, ... (auto-incremented)

Cost: ~$0.12 per image
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

EDIT_MODEL    = "fal-ai/nano-banana-2/edit"
TXT2IMG_MODEL = "fal-ai/nano-banana-2"


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
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        sys.exit(
            "Usage: python3 skills/references/generate-static-ad.py "
            "brands/[brand]/static-ads/[output-name] [variation-slug]"
        )

    output_dir = Path(sys.argv[1])
    slug       = sys.argv[2]
    spec_path  = output_dir / "static-ad-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: static-ad-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    output_name    = spec.get("output_name", output_dir.name)
    product_images = [Path(p) for p in spec.get("product_images", [])]
    aspect_ratio   = spec.get("aspect_ratio", "3:4")

    # Find the requested variation
    variations = spec.get("variations", [])
    variation  = next((v for v in variations if v.get("slug") == slug), None)
    if variation is None:
        available = [v.get("slug") for v in variations]
        sys.exit(
            f"Error: variation '{slug}' not found in static-ad-spec.json. "
            f"Available: {available}"
        )

    prompt = variation.get("prompt", "").strip()
    if not prompt:
        sys.exit(f"Error: variation '{slug}' has no prompt.")

    for p in product_images:
        if not p.exists():
            sys.exit(f"Error: product image not found: {p}")

    check_fal_key()

    print(f"\n{output_name} — {slug}")

    # Build image list — reference ad first (if present), then product images
    reference_path = spec.get("reference_image")
    image_urls = []
    print("Uploading images...")
    if reference_path:
        ref = Path(reference_path)
        if not ref.exists():
            sys.exit(f"Error: reference_image not found: {ref}")
        image_urls.append(_upload(ref, f"Image 1: reference ad ({ref.name})"))
    if product_images:
        for i, img_path in enumerate(product_images, start=len(image_urls) + 1):
            image_urls.append(_upload(img_path, f"Image {i}: {img_path.name}"))

    # Choose model
    model = EDIT_MODEL if image_urls else TXT2IMG_MODEL
    print(f"\nGenerating {aspect_ratio} ad...")

    result = fal_client.run(
        model,
        arguments={
            "prompt":            prompt,
            "aspect_ratio":      aspect_ratio,
            "num_images":        1,
            "output_format":     "png",
            "resolution":        "2K",
            "safety_tolerance":  "4",
            **({"image_urls": image_urls} if image_urls else {}),
            "limit_generations": True,
        },
    )

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: No image returned from FAL.")

    # Save output (auto-increment version)
    base    = f"{output_name}-{slug}"
    version = 1
    while (output_dir / f"{base}_v{version}.png").exists():
        version += 1
    out_path = output_dir / f"{base}_v{version}.png"
    _download(images[0]["url"], out_path)

    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
