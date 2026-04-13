#!/usr/bin/env python3
"""
generate-model.py — Character creation pipeline.

Generates a headshot then a full-body casting digital for a model character,
using the characteristics saved in model-spec.json.

Usage (run from project root):
  python3 skills/references/generate-model.py models/[model-name]

Step 1: text-to-image headshot  →  fal-ai/nano-banana-2
Step 2: image-reference full body  →  fal-ai/nano-banana-2/edit  (headshot as face reference)

Outputs saved to models/[model-name]/
  headshot.png
  fullbody.png

Pricing: $0.12/image @ 2K  ·  total ~$0.24 per character
"""

import json
import os
import sys
import time
from pathlib import Path

import fal_client
import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TXT2IMG_MODEL = "fal-ai/nano-banana-2"
EDIT_MODEL    = "fal-ai/nano-banana-2/edit"


def _load_env_file() -> None:
    """Load FAL_KEY from .env — searches cwd and up to 4 parent directories."""
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

HEADSHOT_PROMPT = """High-fidelity agency casting portrait, oriented straight-on with shoulders squared to the lens.

Subject Characteristics: {characteristics}

Wardrobe: (If female) Sleek, tight-fitting microfiber crop tank in a neutral tone. (If male) Sleek, tight-fitting microfiber tank top in a neutral tone.

Skin & Facial Detail: Aim for a completely bare-faced appearance with zero cosmetics. Focus on high-frequency epidermal textures: clearly defined pores, natural freckling, minor skin imperfections, and slight blemishes. Do not allow for airbrushing or skin-smoothing filters. Maintain authentic facial asymmetry and the subtle creasing or texture beneath the eyes. Brows and lashes should be groomed but entirely natural. No artificial hair luster or "glam" styling.

Composition & Stance: A tight vertical headshot cropped just above the cranium and below the chin line. The model should maintain an upright, straight-backed posture with shoulders squared perfectly to the lens and no head tilt. The neck should appear elongated and tension-free. Maintain a neutral, authoritative, and steady facial expression—no smiling. Eyes must be locked directly onto the camera lens. Keep clothing out of the frame.

Studio Lighting: Utilize a sharp, honest "on-camera flash" aesthetic or a slight off-axis frontal strobe. The lighting must be unforgiving, highlighting every skin detail. Cast faint, minimal shadows directly onto the backdrop behind the subject. Allow for "hot" specular highlights on the bridge of the nose, forehead, and cheekbones, mimicking a raw flash photograph. Avoid all cinematic, soft-box, or "beauty" lighting setups. No rim lighting or halos.

Environment: A seamless, bright light-grey studio wall. The backdrop must be devoid of all patterns, textures, vignettes, or room corners. It should look like a professional, clinical casting environment with no props or distractions.

Technical Camera Specs: Render as a high-resolution full-frame mirrorless or DSLR portrait. Use a focal length between 75mm and 85mm. Set the aperture to f/8 to ensure total edge-to-edge sharpness from the tip of the nose to the ears. Aspect ratio 3:4. Incorporate a trace amount of realistic sensor grain to avoid a digitally "perfect" look. Zero depth-of-field blur on the subject.

Color Science: Neutral 5750k-5800k daylight white balance. No artistic color grading or heavy saturation. Skin tones must be rendered naturally. Strictly prohibit the use of filmic filters, lens flares, halation, or bokeh.

Final Mandate: The resulting image must pass as an unedited "digital" for a top-tier modeling agency (like IMG). It should look like a raw file for a casting director, not a commercial campaign. Absolutely no CGI artifacts, plasticized features, or uncanny facial symmetry."""


FULLBODY_PROMPT = """High-fidelity full-body agency casting digital. Maintain 1:1 facial identity, bone structure, and anatomical alignment with the provided Face Reference Image.

Subject Characteristics: {characteristics}

Face & Skin Matching: Replicate the high-end aesthetic and flawless natural grooming from the reference. Mirror all facial features exactly: natural brows, lashes, and lip pigmentation. Ensure high-frequency skin detail with visible pores, freckles, and minor blemishes. Maintain the subtle under-eye texture and natural facial asymmetry. Do not allow for skin smoothing or "perfecting" filters. No dramatic hair luster; no extra glam.

Environment & Technicals: Match the reference environment precisely—a bright, light-gray seamless paper wall with no texture, patterns, vignettes, or visible room corners. Background must feel like a clinical casting studio. Render as a full-frame DSLR or mirrorless shot. Use a 70mm to 85mm equivalent lens with an aperture of f/8 to ensure the entire body, from face to feet, remains sharp. Aspect ratio 3:4 vertical. Incorporate subtle realistic sensor noise. Neutral daylight 5800k white balance with no stylized grading. Natural skin tones only; no film filters, glow, or bokeh.

Stance & Composition: Strictly framed straight-on full-body shot, captured from just beneath the feet to slightly above the head. Ensure a small margin of negative space at the top and bottom; do not crop the feet or the head. Subject stands in a relaxed casting posture, shoulders perfectly square to the camera, arms resting naturally at the sides. Neutral, steady expression with eyes looking directly into the lens.

Styling & Wardrobe: Torso must match the source portrait exactly. (If female): Minimalist, form-fitting microfiber neutral-toned crop tank. Tailored matching neutral form-fitting shorts with a 1-inch inseam. Barefoot. (If male): Minimalist, form-fitting microfiber neutral-toned tank top. Tailored matching neutral form-fitting shorts with a 5-inch inseam. Barefoot.

General Rules: The final output must look like a raw, unretouched "digital" for a top-tier agency casting director. No CGI appearance, no plastic-perfect features, and no artificial facial symmetry."""


# ---------------------------------------------------------------------------
# FAL helpers
# ---------------------------------------------------------------------------

def _call_txt2img(prompt: str) -> dict:
    return fal_client.run(
        TXT2IMG_MODEL,
        arguments={
            "prompt": prompt,
            "aspect_ratio": "3:4",
            "num_images": 1,
            "output_format": "png",
            "resolution": "2K",
            "safety_tolerance": "4",
            "limit_generations": True,
        },
    )


def _call_edit(prompt: str, image_url: str) -> dict:
    return fal_client.run(
        EDIT_MODEL,
        arguments={
            "prompt": prompt,
            "aspect_ratio": "3:4",
            "num_images": 1,
            "output_format": "png",
            "resolution": "2K",
            "safety_tolerance": "4",
            "image_urls": [image_url],
            "limit_generations": True,
        },
    )


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 skills/references/generate-model.py models/[model-name]")

    model_dir = Path(sys.argv[1])
    spec_path = model_dir / "model-spec.json"

    if not spec_path.exists():
        sys.exit(f"Error: model-spec.json not found at {spec_path}")

    with open(spec_path) as f:
        spec = json.load(f)

    model_name      = spec.get("model_name", model_dir.name)
    characteristics = spec.get("characteristics", "").strip()

    if not characteristics:
        sys.exit("Error: model-spec.json has no characteristics.")

    check_fal_key()

    headshot_path = model_dir / "headshot.png"
    fullbody_path = model_dir / "fullbody.png"

    headshot_prompt = HEADSHOT_PROMPT.format(characteristics=characteristics)
    fullbody_prompt = FULLBODY_PROMPT.format(characteristics=characteristics)

    # Save prompts for reference
    (model_dir / "headshot-prompt.txt").write_text(headshot_prompt)
    (model_dir / "fullbody-prompt.txt").write_text(fullbody_prompt)

    # Step 1 — Headshot
    print(f"\n{model_name}")
    print("Step 1/2 — Generating headshot...")
    result = _call_txt2img(headshot_prompt)
    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned for headshot.")

    _download(images[0]["url"], headshot_path)
    print(f"  ✓ headshot.png")

    time.sleep(0.5)

    # Step 2 — Upload headshot, generate full body
    print("Step 2/2 — Uploading headshot reference...")
    headshot_url = fal_client.upload_file(str(headshot_path))
    print(f"  ✓ uploaded")

    print("         Generating full body...")
    result = _call_edit(fullbody_prompt, headshot_url)
    images = result.get("images", [])
    if not images or not images[0].get("url"):
        sys.exit("Error: no image returned for full body.")

    _download(images[0]["url"], fullbody_path)
    print(f"  ✓ fullbody.png")

    print(f"\nDone. Outputs → {model_dir}/")
    print(f"  {model_dir}/headshot.png")
    print(f"  {model_dir}/fullbody.png")


if __name__ == "__main__":
    main()
