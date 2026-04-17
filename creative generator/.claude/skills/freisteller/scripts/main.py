#!/usr/bin/env python3
"""
freisteller — Background removal for product images via FAL BiRefNet.

Usage:
  python3 .claude/skills/freisteller/scripts/main.py <path>         # single image
  python3 .claude/skills/freisteller/scripts/main.py <folder>       # all images in folder
  python3 .claude/skills/freisteller/scripts/main.py img.jpg -o out.png  # custom output

Reads FAL_KEY from .env in the creative-generator root or ai-visuals root.
Output: *_cutout.png (RGBA) next to the original.

Cost: ~$0.01 per image via fal-ai/birefnet.
"""

import os
import sys
from pathlib import Path

import fal_client
import requests


# ---------------------------------------------------------------------------
# FAL key discovery — check creative-generator .env first, then ai-visuals
# ---------------------------------------------------------------------------

def find_fal_key():
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    script_dir = Path(__file__).resolve().parent
    for up in range(6):
        d = script_dir
        for _ in range(up):
            d = d.parent
        env_file = d / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("FAL_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    # Also check ai-visuals
    ai_visuals_env = script_dir.parents[3] / ".." / "ai-visuals" / ".env"
    if ai_visuals_env.exists():
        for line in ai_visuals_env.read_text().splitlines():
            if line.strip().startswith("FAL_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("Error: FAL_KEY not found. Add it to .env")


# ---------------------------------------------------------------------------
# Background removal via BiRefNet
# ---------------------------------------------------------------------------

def remove_background(image_path: Path, output_path: Path) -> bool:
    """Upload image to FAL BiRefNet and save the result as RGBA PNG."""
    print(f"  ↑ Uploading {image_path.name}...", end=" ", flush=True)
    try:
        image_url = fal_client.upload_file(str(image_path))
    except Exception as e:
        print(f"✗ upload failed: {e}")
        return False
    print("✓")

    print(f"  ⚙ Running BiRefNet...", end=" ", flush=True)
    try:
        result = fal_client.run(
            "fal-ai/birefnet",
            arguments={
                "image_url": image_url,
                "model": "General Use (Heavy)",
                "operating_resolution": "1024x1024",
                "output_format": "png",
            },
        )
    except Exception as e:
        print(f"✗ BiRefNet failed: {e}")
        return False

    # Extract result URL
    img_result = result.get("image") or {}
    result_url = img_result.get("url") if isinstance(img_result, dict) else None
    if not result_url:
        print(f"✗ No image in response")
        return False
    print("✓")

    # Download result
    print(f"  ↓ Downloading {output_path.name}...", end=" ", flush=True)
    try:
        resp = requests.get(result_url, timeout=60)
        resp.raise_for_status()
        output_path.write_bytes(resp.content)
        size_kb = len(resp.content) / 1024
        print(f"✓ ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"✗ download failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    fal_key = find_fal_key()
    os.environ["FAL_KEY"] = fal_key

    target = Path(sys.argv[1])
    custom_output = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            custom_output = Path(sys.argv[idx + 1])

    # Collect images
    if target.is_dir():
        images = sorted(
            f for f in target.iterdir()
            if f.suffix.lower() in SUPPORTED and "_cutout" not in f.stem
        )
    elif target.is_file() and target.suffix.lower() in SUPPORTED:
        images = [target]
    else:
        sys.exit(f"Error: {target} is not a supported image file or directory")

    if not images:
        sys.exit(f"No images found in {target}")

    print(f"Freisteller — {len(images)} image(s) to process")
    print()

    ok = 0
    fail = 0
    for img in images:
        if custom_output and len(images) == 1:
            out = custom_output
        else:
            out = img.parent / f"{img.stem}_cutout.png"

        print(f"→ {img.name}")
        if out.exists():
            print(f"  (skip — {out.name} already exists)")
            ok += 1
            continue

        if remove_background(img, out):
            ok += 1
        else:
            fail += 1
        print()

    print(f"Done. {ok} ok, {fail} failed.")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
