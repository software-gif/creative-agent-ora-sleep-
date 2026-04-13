#!/usr/bin/env python3
"""
generate-style.py — Clothing-on-model styling pipeline.

Places product clothing onto a generated model using three reference images:
1. Face reference  (models/[name]/headshot.png)
2. Body reference  (models/[name]/fullbody.png)
3. Product reference(s)  (brands/[brand]/product-images/[product].jpg)

Usage (run from project root):
  python3 skills/references/generate-style.py styled/[output-name]

Reads style-spec.json from the output folder, uploads all reference images
to FAL storage, and calls fal-ai/nano-banana-2/edit.

Output: styled/[output-name]/styled_v1.png

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

STYLE_PROMPT_WITH_PRODUCT = """Generate a full body casting image in-studio, for a luxury lookbook image. Synthesise the provided Product Reference Image onto the exact Body Reference Image while strictly maintaining the facial features and character likeness of the Face Reference Image.

The generated image should be an ultra realistic fashion styling photograph where the output model looks identical to the Face & Body Reference Images and the clothing and accessories worn by the subject match exactly that of the Wardrobe Reference Image.

--- Reference Images ---

1. Face Reference Image: Source of facial features.
2. Body Reference Image: Source of body proportions. Disregard the fashion worn in this image.
3. Product Reference Image: Source of truth for what the model should be wearing, including accessories. Ensure clothing fabric, colour, fit, cut, any labels are matched.

--- Instructions ---

Lighting and Background: Preserve the identical lighting, background, and colour grading from the Face & Body Reference Images. Do not add any other stylistic features such as vignettes.

Framing: Identical to body reference image. Straight-on full body shot framed from just below the feet to above the head. Small margin of negative space below the feet and above the head. No cropping of feet or head.

Pose: Identical to body reference image. Shoulders square to camera, relaxed casting stance, shoulders square to camera with arms naturally by side, neutral expression, looking directly into camera."""

STYLE_PROMPT_NOTES_ONLY = """Generate a full body casting image in-studio, for a luxury lookbook image. Dress the model from the Body Reference Image in the outfit described in the Styling Instructions below, while strictly maintaining the facial features and character likeness of the Face Reference Image.

--- Reference Images ---

1. Face Reference Image: Source of facial features.
2. Body Reference Image: Source of body proportions. Disregard the fashion worn in this image.

--- Instructions ---

Lighting and Background: Preserve the identical lighting, background, and colour grading from the Face & Body Reference Images. Do not add any other stylistic features such as vignettes.

Framing: Identical to body reference image. Straight-on full body shot framed from just below the feet to above the head. Small margin of negative space below the feet and above the head. No cropping of feet or head.

Pose: Identical to body reference image. Shoulders square to camera, relaxed casting stance, shoulders square to camera with arms naturally by side, neutral expression, looking directly into camera."""


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
        sys.exit("Usage: python3 skills/references/generate-style.py styled/[output-name]")

    output_dir = Path(sys.argv[1])
    spec_path  = output_dir / "style-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: style-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    model_name    = spec.get("model_name", output_dir.name)
    model_dir     = Path(spec["model_dir"])
    product_images = [Path(p) for p in spec.get("product_images", [])]
    notes         = spec.get("notes", "").strip()

    if not product_images and not notes:
        sys.exit("Error: style-spec.json must have either product_images or notes (or both).")

    face_ref = model_dir / "headshot.png"
    body_ref = model_dir / "fullbody.png"

    for p in [face_ref, body_ref]:
        if not p.exists():
            sys.exit(f"Error: reference image not found: {p}\nRun the /model skill first.")

    for p in product_images:
        if not p.exists():
            sys.exit(f"Error: product image not found: {p}")

    check_fal_key()

    print(f"\n{model_name} — styling")
    print("Uploading reference images...")

    image_urls = []
    image_urls.append(_upload(face_ref,  "face reference (headshot)"))
    image_urls.append(_upload(body_ref,  "body reference (full body)"))
    for i, prod_path in enumerate(product_images, start=1):
        label = f"product reference {i}: {prod_path.name}" if len(product_images) > 1 else f"product reference: {prod_path.name}"
        image_urls.append(_upload(prod_path, label))

    if product_images:
        prompt = STYLE_PROMPT_WITH_PRODUCT
    else:
        prompt = STYLE_PROMPT_NOTES_ONLY
    if notes:
        prompt += f"\n\n--- Styling Instructions ---\n\n{notes}"

    print("\nGenerating styled image...")
    result = fal_client.run(
        EDIT_MODEL,
        arguments={
            "prompt": prompt,
            "aspect_ratio": "3:4",
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

    base_name = output_dir.name
    version = 1
    while (output_dir / f"{base_name}_v{version}.png").exists():
        version += 1
    out_path = output_dir / f"{base_name}_v{version}.png"
    _download(images[0]["url"], out_path)

    print(f"  ✓ {out_path.name}")
    print(f"\nDone. Output → {out_path}")


if __name__ == "__main__":
    main()
