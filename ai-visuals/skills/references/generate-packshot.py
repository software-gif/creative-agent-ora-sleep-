#!/usr/bin/env python3
"""
generate-packshot.py — Packshot generation pipeline.

Generates a clean commercial product packshot using product reference images
and a pre-built prompt (produced by Claude in Step 1+2 of the packshot skill).

Usage (run from project root):
  python3 skills/references/generate-packshot.py brands/[brand]/packshots/[output-name]

Reads packshot-spec.json from the output folder.

Output: packshot_v1.png, packshot_v2.png, ... (auto-incremented)

Pricing: $0.12 @ 2K
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

EDIT_MODEL  = "fal-ai/nano-banana-2/edit"
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


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


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
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 skills/references/generate-packshot.py brands/[brand]/packshots/[output-name]")

    output_dir = Path(sys.argv[1])
    spec_path  = output_dir / "packshot-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: packshot-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    prompt         = spec.get("prompt", "")
    product_images = [Path(p) for p in spec.get("product_images", [])]
    aspect_ratio   = spec.get("aspect_ratio", "3:4")
    output_name    = spec.get("output_name", output_dir.name)

    if not prompt:
        sys.exit("Error: packshot-spec.json has no prompt. Run the packshot skill first to generate it.")

    if not product_images:
        sys.exit("Error: packshot-spec.json has no product_images.")

    for p in product_images:
        if not p.exists():
            sys.exit(f"Error: product image not found: {p}")

    check_fal_key()

    print(f"\n{output_name} — packshot")
    print("Uploading product reference images...")

    image_urls = []
    for i, img_path in enumerate(product_images, start=1):
        image_urls.append(_upload(img_path, f"product reference {i}: {img_path.name}"))

    model    = EDIT_MODEL if image_urls else TXT2IMG_MODEL
    payload  = {
        "prompt":           prompt,
        "aspect_ratio":     aspect_ratio,
        "num_images":       1,
        "output_format":    "png",
        "resolution":       "2K",
        "safety_tolerance": "4",
        "limit_generations": True,
    }
    if image_urls:
        payload["image_urls"] = image_urls

    print("\nGenerating packshot...")
    result = fal_client.run(model, arguments=payload)

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned from FAL.")

    base = output_name
    version = 1
    while (output_dir / f"{base}_v{version}.png").exists():
        version += 1
    out_path = output_dir / f"{base}_v{version}.png"
    _download(images[0]["url"], out_path)

    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
