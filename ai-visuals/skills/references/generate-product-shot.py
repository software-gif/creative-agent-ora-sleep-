#!/usr/bin/env python3
"""
generate-product-shot.py — Product shot pipeline.

Substitutes a product into a composition reference image, optionally
adopting the lighting from a third reference.

Image reference order (important):
  Image 1 — composition reference (framing, environment, pose)
  Image 2 — product image (the product to place)
  Image 3 — lighting reference (optional)

Usage (run from project root):
  python3 skills/references/generate-product-shot.py brands/[brand]/product-shots/[output-name]

Reads product-shot-spec.json from the output folder.

Output: product-shot_v1.png, product-shot_v2.png, ... (auto-incremented)

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

EDIT_MODEL = "fal-ai/nano-banana-2/edit"


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
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 skills/references/generate-product-shot.py brands/[brand]/product-shots/[output-name]")

    output_dir = Path(sys.argv[1])
    spec_path  = output_dir / "product-shot-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: product-shot-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    output_name           = spec.get("output_name", output_dir.name)
    composition_reference = Path(spec["composition_reference"])
    product_image         = Path(spec["product_image"])
    lighting_reference    = Path(spec["lighting_reference"]) if spec.get("lighting_reference") else None
    additional_notes      = spec.get("additional_notes", "").strip()
    aspect_ratio          = spec.get("aspect_ratio", "3:4")

    # Build prompt
    base = (
        "Regenerate image 1 by substituting its primary subject with the exact product shown in image 2. "
        "Preserve everything that makes image 1 compelling: the camera angle and perspective exactly "
        "(low angle, eye level, overhead — whatever is shown), the lighting quality and direction, "
        "the background, colour grade, depth of field, mood, and overall atmosphere. "
        "The product from image 2 must match in form, proportions, and branding exactly — "
        "do not distort its shape to fit the reference product's silhouette. "
        "Only the subject changes. Everything else stays."
    )
    if lighting_reference:
        base += " Adopt the lighting and tonal atmosphere of image 3."
    prompt = base

    if additional_notes:
        prompt += f" {additional_notes}"

    # Validate paths
    for label, path in [
        ("composition reference", composition_reference),
        ("product image",         product_image),
    ]:
        if not path.exists():
            sys.exit(f"Error: {label} not found: {path}")

    if lighting_reference and not lighting_reference.exists():
        sys.exit(f"Error: lighting reference not found: {lighting_reference}")

    check_fal_key()

    (output_dir / "shot-prompt.txt").write_text(prompt)

    print(f"\n{output_name} — product shot")
    print("Uploading reference images...")

    image_urls = [
        _upload(composition_reference, f"composition reference (Image 1): {composition_reference.name}"),
        _upload(product_image,         f"product image (Image 2): {product_image.name}"),
    ]
    if lighting_reference:
        image_urls.append(_upload(lighting_reference, f"lighting reference (Image 3): {lighting_reference.name}"))

    print("\nGenerating product shot...")
    result = fal_client.run(
        EDIT_MODEL,
        arguments={
            "prompt":           prompt,
            "aspect_ratio":     aspect_ratio,
            "num_images":       1,
            "output_format":    "png",
            "resolution":       "2K",
            "safety_tolerance": "4",
            "image_urls":       image_urls,
            "limit_generations": True,
        },
    )

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
