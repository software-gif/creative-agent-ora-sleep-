#!/usr/bin/env python3
"""
generate-clothing-shoot.py — Clothing shoot pipeline.

Places a styled model into a location environment using three reference images:
1. Environment reference  (user-provided location/lighting reference)
2. Styled image           (styled/[name]/[name]_v{n}.png — latest version auto-detected)
3. Face reference         (models/[name]/headshot.png)

Usage (run from project root):
  python3 skills/references/generate-clothing-shoot.py clothing-shoot/[output-name]

Reads shoot-spec.json from the output folder and calls fal-ai/nano-banana-2/edit.

Output: clothing-shoot/[output-name]/shoot_v1.png

Pricing: $0.12/image @ 2K
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
# Prompt
# ---------------------------------------------------------------------------

SHOOT_PROMPT = """Generate a photorealistic, campaign-ready fashion photography image by synthesising the provided reference images.

--- Reference Images ---

1. Environment & Lighting (Location Reference Image): Use this exact location, perspective, and depth of field. Analyse the exact lighting setup (shadow mapping, colour temperature, directional light, ambient bounce) and apply it to the subject.

2. Styling & Body (Styled Image): Maintain the exact proportions of the subject. Recreate the precise clothing items and accessories, layering, fabric textures and labels with zero deviation.

3. Identity (Face Reference Image): Ensure perfect character consistency.

--- Instructions ---

Pose / Model's Actions: The subject must be dynamically posed, interacting naturally with the spatial elements or props of the location. Use physical tension, dramatic body angles, and asymmetrical posing to highlight the movement of the outfit and the mood of the environment. No generic, stiff, overly dynamic, hyper-editorial, or obscured poses. {pose_direction}

Technical: Do not simply composite the subject. Analyse the layout of the location and ground the subject organically within the environment. Render at editorial-tier fashion campaign quality. Highly detailed, photorealistic, cinematic lighting, focus on the subject."""


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
        sys.exit("Usage: python3 skills/references/generate-clothing-shoot.py clothing-shoot/[output-name]")

    output_dir = Path(sys.argv[1])
    spec_path  = output_dir / "shoot-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: shoot-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    output_name    = spec.get("output_name", output_dir.name)
    styled_dir     = Path(spec["styled_dir"])
    model_dir      = Path(spec["model_dir"])
    env_reference  = Path(spec["env_reference"])
    pose_direction = spec.get("pose_direction", "")
    aspect_ratio   = spec.get("aspect_ratio", "4:5")

    folder_name  = styled_dir.name
    sv = 1
    while (styled_dir / f"{folder_name}_v{sv + 1}.png").exists():
        sv += 1
    styled_image = styled_dir / f"{folder_name}_v{sv}.png"
    face_ref     = model_dir  / "headshot.png"

    for label, path in [
        ("environment reference", env_reference),
        ("styled image",          styled_image),
        ("face reference",        face_ref),
    ]:
        if not path.exists():
            sys.exit(f"Error: {label} not found: {path}")

    check_fal_key()

    print(f"\n{output_name}")
    print("Uploading reference images...")

    image_urls = [
        _upload(env_reference, "environment reference"),
        _upload(styled_image,  "styled image"),
        _upload(face_ref,      "face reference (headshot)"),
    ]

    prompt = SHOOT_PROMPT.format(pose_direction=pose_direction)
    (output_dir / "shoot-prompt.txt").write_text(prompt)

    print("\nGenerating shoot image...")
    result = fal_client.run(
        EDIT_MODEL,
        arguments={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
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

    version = 1
    while (output_dir / f"shoot_v{version}.png").exists():
        version += 1
    out_path = output_dir / f"shoot_v{version}.png"
    _download(images[0]["url"], out_path)

    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
