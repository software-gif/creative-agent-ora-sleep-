#!/usr/bin/env python3
"""
generate-product-ugc.py — Product UGC image and video pipeline.

Two modes:
  --image   Generate a product UGC selfie (model holding product, 9:16 2K via nano-banana-2/edit)
  --video   Generate a UGC video from the selfie (9:16 1080p via Veo 3.1 Fast)

Image reference order (important):
  Image 1 — product being held
  Image 2 — headshot (identity)
  Image 3 — styled body (outfit, styled models only)

Usage (run from project root):
  python3 skills/references/generate-product-ugc.py brands/[brand]/product-ugc/[output-name] --image
  python3 skills/references/generate-product-ugc.py brands/[brand]/product-ugc/[output-name] --video

Reads product-ugc-spec.json from the output folder.

Outputs:
  product-ugc-image_v1.png  (auto-incremented on each run)
  product-ugc-video.mp4

Pricing:
  Image: $0.12 @ 2K
  Video: ~$0.26 per 5s at 1080p (scales with duration)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import fal_client
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

IMAGE_MODEL = "fal-ai/nano-banana-2/edit"
VIDEO_MODEL = "fal-ai/veo3.1/fast/image-to-video"


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
# Prompt
# ---------------------------------------------------------------------------

IMAGE_PROMPT_TEMPLATE = """Produce a photorealistic UGC-style iPhone front-camera selfie. Ensure the individual's appearance is a perfect 1:1 match with the person in Image 2. They are {action}. High angle shot — the model is holding the phone out at arm's length high above them, looking up into the lens. In their other hand they are holding the product prominently toward the camera. One hand holds the phone outstretched, the other holds the product clearly in frame at all times. The product must be rendered with absolute precision, including all labels and branding text. Candid, relaxed, and neutral expression, looking directly into the camera lens.

--- Instructions ---

Image references: The product held must perfectly match image 1 (including all visible text). Subject likeness must perfectly match image 2.

Environment: {location}

Outfit: {outfit}

Lighting: Natural, indirect, creating soft catchlights in the eyes.

Framing & Composition: A compact facial close-up focusing on the head and neckline. Maintain a very narrow margin at the top, cropping the frame around the upper hair boundary.

Style: Authentic mobile sensor quality. Focus on high-frequency skin textures: ensure the complexion looks dewy with distinct pore visibility and fine vellus hairs. Apply a natural, shallow-focus background blur.

Negative Prompts: No visible hands holding a phone, no visible phone, no visible mirrors, no studio lighting or over-processed look."""


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
# Image generation
# ---------------------------------------------------------------------------

def generate_image(output_dir: Path, spec: dict) -> None:
    model_type    = spec.get("model_type", "unstyled")
    model_dir     = Path(spec["model_dir"])
    styled_dir    = spec.get("styled_dir")
    product_image = Path(spec["product_image"])
    action        = spec.get("action", "")
    location      = spec.get("location", "")
    outfit        = spec.get("outfit", "must perfectly match image 3")

    headshot = model_dir / "headshot.png"

    for label, path in [
        ("product image", product_image),
        ("headshot",      headshot),
    ]:
        if not path.exists():
            sys.exit(f"Error: {label} not found: {path}")

    prompt = IMAGE_PROMPT_TEMPLATE.format(
        action=action,
        location=location,
        outfit=outfit,
    )
    (output_dir / "image-prompt.txt").write_text(prompt)

    print(f"\n{output_dir.name} — product UGC image")
    print("Uploading reference images...")

    # Order: product first (Image 1), headshot second (Image 2), styled body third if present (Image 3)
    image_urls = [
        _upload(product_image, f"product: {product_image.name} (Image 1)"),
        _upload(headshot,      "headshot (Image 2 — identity)"),
    ]

    if model_type == "styled" and styled_dir:
        # Find the latest styled version — uses output folder name as base filename
        styled_base = Path(styled_dir)
        folder_name = styled_base.name
        version = 1
        while (styled_base / f"{folder_name}_v{version + 1}.png").exists():
            version += 1
        styled_path = styled_base / f"{folder_name}_v{version}.png"
        if not styled_path.exists():
            sys.exit(f"Error: styled image not found: {styled_path}")
        image_urls.append(_upload(styled_path, f"styled body: {styled_path.name} (Image 3 — outfit)"))

    print("\nGenerating product UGC image...")
    result = fal_client.run(
        IMAGE_MODEL,
        arguments={
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "num_images": 1,
            "output_format": "png",
            "resolution": "2K",
            "safety_tolerance": "4",
            "image_urls": image_urls,
            "limit_generations": True,
        },
    )

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned from FAL.")

    output_name = spec.get("output_name", output_dir.name)
    version = 1
    while (output_dir / f"{output_name}_v{version}.png").exists():
        version += 1
    out_path = output_dir / f"{output_name}_v{version}.png"
    _download(images[0]["url"], out_path)
    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

def generate_video(output_dir: Path, spec: dict) -> None:
    output_name = spec.get("output_name", output_dir.name)
    chosen = spec.get("video_image_version")
    if chosen:
        image_path = output_dir / f"{output_name}_v{chosen}.png"
    else:
        version = 1
        while (output_dir / f"{output_name}_v{version + 1}.png").exists():
            version += 1
        image_path = output_dir / f"{output_name}_v{version}.png"

    if not image_path.exists():
        sys.exit(f"Error: no image found in {output_dir}. Run --image first.")

    script      = spec.get("script", "")
    voice_notes = spec.get("voice_notes", "")
    duration    = str(spec.get("duration", "8"))
    output_name = spec.get("output_name", output_dir.name)

    if duration not in {"4", "6", "8"}:
        sys.exit(f"Error: duration must be 4, 6, or 8 seconds (Veo 3.1 requirement), got '{duration}'.")

    action        = spec.get("action", "")
    video_prompt_parts = []
    if action:
        video_prompt_parts.append(f"Action: {action}")
    if script:
        video_prompt_parts.append(f"Script: {script}")
    if voice_notes:
        video_prompt_parts.append(f"Voice and delivery: {voice_notes}")
    video_prompt_parts.append(
        "The model may move naturally throughout the shot, but must maintain a firm grip on both "
        "the outstretched arm holding the camera and the product in their other hand at all times — "
        "the product must remain clearly visible and in frame from start to finish."
    )
    video_prompt = " ".join(video_prompt_parts)

    (output_dir / "video-prompt.txt").write_text(video_prompt)

    print(f"\n{output_name} — product UGC video")
    print(f"Using image: {image_path.name}")
    image_url = _upload(image_path, image_path.name)

    veo_duration = f"{duration}s" if not str(duration).endswith("s") else duration
    print(f"\nGenerating {duration}s video at 1080p 9:16 (Veo 3.1)...")
    result = fal_client.run(
        VIDEO_MODEL,
        arguments={
            "prompt": video_prompt,
            "image_url": image_url,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "duration": veo_duration,
            "generate_audio": True,
        },
    )

    video = result.get("video", {})
    video_url = video.get("url") if isinstance(video, dict) else None
    if not video_url:
        sys.exit("Error: no video returned from FAL.")

    # Name video after the source image + run number
    image_base = image_path.stem  # e.g. sofia-magnesium-yoga-studio_v1
    run = 1
    while (output_dir / f"{image_base}-run{run}.mp4").exists():
        run += 1
    out_path = output_dir / f"{image_base}-run{run}.mp4"
    print("  Downloading video...", end=" ", flush=True)
    _download(video_url, out_path)
    print("✓")
    print(f"\nDone. Output → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Product UGC image and video pipeline.")
    parser.add_argument("output_dir", help="Path to the output folder (e.g. brands/[brand]/product-ugc/jade-paris-tshirt)")
    parser.add_argument("--image", action="store_true", help="Generate the product UGC selfie image")
    parser.add_argument("--video", action="store_true", help="Generate the UGC video")
    args = parser.parse_args()

    if not args.image and not args.video:
        sys.exit("Error: specify --image or --video (or both).")

    output_dir = Path(args.output_dir)
    spec_path  = output_dir / "product-ugc-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: product-ugc-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    check_fal_key()

    if args.image:
        generate_image(output_dir, spec)

    if args.video:
        generate_video(output_dir, spec)


if __name__ == "__main__":
    main()
