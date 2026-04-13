#!/usr/bin/env python3
"""
generate-ugc.py — UGC image and video pipeline.

Two modes:
  --image   Generate a UGC-style selfie photo (9:16 2K via nano-banana-2/edit)
  --video   Generate a UGC talking-head video from the selfie (9:16 1080p via Veo 3.1 Fast)

Usage (run from project root):
  python3 skills/references/generate-ugc.py ugc/[output-name] --image
  python3 skills/references/generate-ugc.py ugc/[output-name] --video

Reads ugc-spec.json from the output folder.

Outputs:
  ugc/[output-name]/ugc-image.png
  ugc/[output-name]/ugc-video.mp4

Pricing:
  Image: $0.12 @ 2K
  Video: $0.60 for 4s · $0.90 for 6s · $1.20 for 8s at 1080p with audio (Veo 3.1 Fast)
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
# Prompts
# ---------------------------------------------------------------------------

IMAGE_PROMPT_TEMPLATE = """Produce a photorealistic UGC-style iPhone front-camera selfie. Ensure the individual's appearance is a perfect 1:1 match with the person in Image 1. They are {action}. Candid, relaxed, and neutral expression, looking directly into the camera lens.

--- Instructions ---

Image references: Subject likeness must perfectly match image 1.

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
    model_type   = spec.get("model_type", "unstyled")   # "styled" or "unstyled"
    model_dir    = Path(spec["model_dir"])
    styled_dir   = spec.get("styled_dir")
    action       = spec.get("action", "")
    location     = spec.get("location", "")
    outfit       = spec.get("outfit", "must perfectly match image 1")

    headshot = model_dir / "headshot.png"
    if not headshot.exists():
        sys.exit(f"Error: headshot not found: {headshot}")

    prompt = IMAGE_PROMPT_TEMPLATE.format(
        action=action,
        location=location,
        outfit=outfit,
    )
    (output_dir / "image-prompt.txt").write_text(prompt)

    print(f"\n{output_dir.name} — UGC image")
    print("Uploading reference images...")

    image_urls = [_upload(headshot, "headshot (Image 1 — identity)")]

    if model_type == "styled" and styled_dir:
        styled_base = Path(styled_dir)
        folder_name = styled_base.name
        version = 1
        while (styled_base / f"{folder_name}_v{version + 1}.png").exists():
            version += 1
        styled_path = styled_base / f"{folder_name}_v{version}.png"
        if not styled_path.exists():
            sys.exit(f"Error: styled image not found: {styled_path}")
        image_urls.append(_upload(styled_path, f"styled body: {styled_path.name} (Image 2 — outfit)"))

    print("\nGenerating UGC image...")
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

    script        = spec.get("script", "")
    voice_notes   = spec.get("voice_notes", "")
    duration      = str(spec.get("duration", "8"))
    output_name   = spec.get("output_name", output_dir.name)

    if duration not in {"4", "6", "8"}:
        sys.exit(f"Error: duration must be 4, 6, or 8 seconds (Veo 3.1 requirement), got '{duration}'.")

    # Build video prompt from action, script and voice notes
    action        = spec.get("action", "")
    video_prompt_parts = []
    if action:
        video_prompt_parts.append(f"Action: {action}")
    if script:
        video_prompt_parts.append(f"Script: {script}")
    if voice_notes:
        video_prompt_parts.append(f"Voice and delivery: {voice_notes}")
    video_prompt = " ".join(video_prompt_parts)

    (output_dir / "video-prompt.txt").write_text(video_prompt)

    print(f"\n{output_name} — UGC video")
    print("Uploading UGC image to FAL storage...")
    image_url = _upload(image_path, "ugc-image.png")

    veo_duration = f"{duration}s" if not str(duration).endswith("s") else duration
    print(f"\nGenerating {duration}s video at 1080p 9:16 (Veo 3.1 Fast)...")
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

    image_base = image_path.stem
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
    parser = argparse.ArgumentParser(description="UGC image and video pipeline.")
    parser.add_argument("output_dir", help="Path to the UGC output folder (e.g. ugc/jade-urban-walk)")
    parser.add_argument("--image", action="store_true", help="Generate the UGC selfie image")
    parser.add_argument("--video", action="store_true", help="Generate the UGC video from ugc-image.png")
    args = parser.parse_args()

    if not args.image and not args.video:
        sys.exit("Error: specify --image or --video (or both).")

    output_dir = Path(args.output_dir)
    spec_path  = output_dir / "ugc-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: ugc-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    check_fal_key()

    if args.image:
        generate_image(output_dir, spec)

    if args.video:
        generate_video(output_dir, spec)


if __name__ == "__main__":
    main()
