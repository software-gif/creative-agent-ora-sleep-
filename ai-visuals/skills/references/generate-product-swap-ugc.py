#!/usr/bin/env python3
"""
generate-product-swap-ugc.py — Product swap + motion transfer pipeline.

Stage 1: Swap the product in the source UGC still (Nano Banana 2/edit)
Stage 2: Transfer motion from the original UGC video to the swapped image (Kling Motion Control v2.6 Standard)

Usage (run from project root):
  python3 skills/references/generate-product-swap-ugc.py brands/[brand]/multiply-ugc/[output-name]
  python3 skills/references/generate-product-swap-ugc.py brands/[brand]/multiply-ugc/[output-name] --swap-only
  python3 skills/references/generate-product-swap-ugc.py brands/[brand]/multiply-ugc/[output-name] --motion-only

Reads multiply-ugc-spec.json from the output folder (expects "product_image" field).
"""

import json
import os
import sys
from pathlib import Path

import fal_client
import requests


SWAP_MODEL   = "fal-ai/nano-banana-2/edit"
MOTION_MODEL = "fal-ai/kling-video/v2.6/standard/motion-control"

SWAP_PROMPT = (
    "Replace the product/item being held in the person's hand in Image 1 with the "
    "product shown in Image 2. Keep the person, pose, background, lighting, and "
    "everything else in the scene exactly the same. Only the held product changes."
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


def _upload(path: Path, label: str) -> str:
    print(f"  Uploading {label}...", end=" ", flush=True)
    url = fal_client.upload_file(str(path))
    print("✓")
    return url


def _download(url: str, dest: Path) -> None:
    with requests.get(url, timeout=(30, 600), stream=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _next_version(output_dir: Path, stem: str, ext: str) -> Path:
    version = 1
    while (output_dir / f"{stem}_v{version}{ext}").exists():
        version += 1
    return output_dir / f"{stem}_v{version}{ext}"


def stage1_swap(output_dir: Path, spec: dict) -> Path:
    source_image  = Path(spec["source_ugc_image"])
    product_image = Path(spec["product_image"])

    if not source_image.exists():
        sys.exit(f"Error: source UGC image not found: {source_image}")
    if not product_image.exists():
        sys.exit(f"Error: product image not found: {product_image}")

    print("\nStage 1 — Product swap (Nano Banana 2)")
    print("Uploading reference images...")

    image_urls = [
        _upload(source_image, f"source UGC still (Image 1): {source_image.name}"),
        _upload(product_image, f"product image (Image 2): {product_image.name}"),
    ]

    print("\nSwapping product...")
    result = fal_client.run(
        SWAP_MODEL,
        arguments={
            "prompt":            SWAP_PROMPT,
            "aspect_ratio":      "9:16",
            "num_images":        1,
            "output_format":     "png",
            "resolution":        "2K",
            "safety_tolerance":  "4",
            "image_urls":        image_urls,
            "limit_generations": True,
        },
    )

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned from Nano Banana 2.")

    output_name = spec.get("output_name", output_dir.name)
    out_path = _next_version(output_dir, f"{output_name}-swap", ".png")
    _download(images[0]["url"], out_path)
    print(f"  ✓ {out_path.name}")

    return out_path


def stage2_motion(output_dir: Path, spec: dict, swap_image: Path) -> None:
    source_video = Path(spec["source_ugc_video"])
    output_name  = spec.get("output_name", output_dir.name)

    if not source_video.exists():
        sys.exit(f"Error: source UGC video not found: {source_video}")

    print("\nStage 2 — Motion transfer (Kling Motion Control v2.6 Standard)")
    print("Uploading files...")

    image_url = _upload(swap_image, f"swapped image: {swap_image.name}")
    video_url = _upload(source_video, f"source UGC video: {source_video.name}")

    print("\nTransferring motion...")
    result = fal_client.run(
        MOTION_MODEL,
        arguments={
            "image_url":             image_url,
            "video_url":             video_url,
            "character_orientation": "video",
            "keep_original_sound":   True,
        },
    )

    video = result.get("video", {})
    video_url_out = video.get("url") if isinstance(video, dict) else None
    if not video_url_out:
        sys.exit("Error: no video returned from Kling Motion Control.")

    out_path = _next_version(output_dir, output_name, ".mp4")
    print("  Downloading video...", end=" ", flush=True)
    _download(video_url_out, out_path)
    print("✓")
    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Product swap UGC — product swap + motion transfer.")
    parser.add_argument("output_dir", help="Path to the multiply-ugc output folder")
    parser.add_argument("--swap-only", action="store_true",
                        help="Run product swap only — skip motion transfer")
    parser.add_argument("--motion-only", action="store_true",
                        help="Skip swap — use the latest existing swap image and re-run motion transfer only")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    spec_path  = output_dir / "multiply-ugc-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: multiply-ugc-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    check_fal_key()

    output_name = spec.get("output_name", output_dir.name)
    print(f"\n{output_name} — Product Swap UGC")

    if args.swap_only:
        stage1_swap(output_dir, spec)
    elif args.motion_only:
        version = 1
        while (output_dir / f"{output_name}-swap_v{version + 1}.png").exists():
            version += 1
        swap_image = output_dir / f"{output_name}-swap_v{version}.png"
        if not swap_image.exists():
            sys.exit(f"Error: no swap image found in {output_dir}. Run without --motion-only first.")
        print(f"Using existing swap image: {swap_image.name}")
        stage2_motion(output_dir, spec, swap_image)
    else:
        swap_image = stage1_swap(output_dir, spec)
        stage2_motion(output_dir, spec, swap_image)


if __name__ == "__main__":
    main()
