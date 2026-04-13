#!/usr/bin/env python3
"""
generate-reformat.py — Content format multiplier.

Reformats an existing image to a new aspect ratio using Nano Banana,
recomposing the layout intelligently while preserving all design elements:
composition, typography, product placement, colors, and visual hierarchy.

Usage (run from project root):
  python3 skills/references/generate-reformat.py [source-image-path] [aspect-ratio]

Example:
  python3 skills/references/generate-reformat.py \\
    brands/puresport/static-ads/iMessage-energy-gel/iMessage-energy-gel-var-1_v1.png \\
    9:16

Output is saved to the same folder as the source image, with the aspect ratio
appended to the filename:
  iMessage-energy-gel-var-1_v1.png  →  iMessage-energy-gel-var-1_9x16_v1.png

Auto-increments if the output already exists.

Always reformat from the original source — not from a previously reformatted version.

Pricing: $0.12 @ 2K
"""

import os
import re
import sys
from pathlib import Path

import fal_client
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EDIT_MODEL = "fal-ai/nano-banana-2/edit"

REFORMAT_PROMPT = (
    "Recreate this image exactly in the new aspect ratio. "
    "Preserve all design elements without exception: text, typography, colors, "
    "product imagery, backgrounds, layout structure, and visual hierarchy. "
    "Recompose the layout intelligently to suit the new format — do not crop, "
    "letterbox, stretch, or omit any element. "
    "Keep all text and key visual elements within the central safe zone of the frame, "
    "clear of the outer 10% on all edges. "
    "The result should look like a natively designed version for this format, "
    "not a mechanical adaptation of the original."
)


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


def _derive_output_path(source: Path, aspect_ratio: str) -> Path:
    """
    Derive the output path from the source image path and target aspect ratio.

    Examples:
      iMessage-energy-gel-var-1_v1.png + 9:16  →  iMessage-energy-gel-var-1_9x16_v1.png
      packshot_v3.png + 1:1                    →  packshot_1x1_v1.png
    """
    ratio_slug = aspect_ratio.replace(":", "x")

    # Strip any existing _vN suffix to get the clean base name
    stem_base = re.sub(r"_v\d+$", "", source.stem)

    base    = f"{stem_base}_{ratio_slug}"
    version = 1
    while (source.parent / f"{base}_v{version}.png").exists():
        version += 1

    return source.parent / f"{base}_v{version}.png"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        sys.exit(
            "Usage: python3 skills/references/generate-reformat.py "
            "[source-image-path] [aspect-ratio]"
        )

    source_path  = Path(sys.argv[1])
    aspect_ratio = sys.argv[2]

    if not source_path.exists():
        sys.exit(f"Error: source image not found: {source_path}")

    valid_ratios = {"1:1", "3:4", "4:5", "9:16", "16:9", "4:3", "2:3"}
    if aspect_ratio not in valid_ratios:
        print(f"Warning: '{aspect_ratio}' is not a recognised ratio. Proceeding anyway.")

    check_fal_key()

    out_path = _derive_output_path(source_path, aspect_ratio)

    print(f"\n{source_path.name}  →  {aspect_ratio}")
    image_url = _upload(source_path, source_path.name)

    print(f"\nGenerating {aspect_ratio} version...")
    result = fal_client.run(
        EDIT_MODEL,
        arguments={
            "prompt":            REFORMAT_PROMPT,
            "aspect_ratio":      aspect_ratio,
            "num_images":        1,
            "output_format":     "png",
            "resolution":        "2K",
            "safety_tolerance":  "4",
            "image_urls":        [image_url],
            "limit_generations": True,
        },
    )

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned from FAL.")

    _download(images[0]["url"], out_path)

    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
