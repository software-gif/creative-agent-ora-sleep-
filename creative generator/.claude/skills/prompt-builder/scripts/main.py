#!/usr/bin/env python3
"""Prompt Builder — Dynamic creative prompt generator based on Andromeda diversification."""

import argparse
import json
import os
import random
import sys
import uuid
from itertools import cycle

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

FORMAT_RESOLUTIONS = {
    "4:5": {"width": 1440, "height": 1800},
    "9:16": {"width": 1080, "height": 1920},
    "1:1": {"width": 1440, "height": 1440},
}

FORMAT_WEIGHTS = {"4:5": 4, "9:16": 4, "1:1": 2}

LAYOUT_TYPES = [
    "three_zone_vertical", "centered_hero", "split_composition",
    "diagonal_splash", "full_bleed_lifestyle",
]

BG_TYPES_PRODUCT = ["solid_color", "gradient", "texture"]
BG_TYPES_LIFESTYLE = ["photo_scene", "blurred_lifestyle"]

LIFESTYLE_SCENES = [
    "Gemütliches Schlafzimmer, warmes Licht, weiche Bettwäsche, Person schläft friedlich",
    "Modernes Schlafzimmer, Morgenlicht fällt durch Vorhänge, aufgewachte Person streckt sich zufrieden",
    "Minimalistisches Schlafzimmer im Schweizer Stil, saubere Linien, Holzakzente, Matratze im Fokus",
    "Dunkles Schlafzimmer bei Nacht, Monlicht, ruhige Atmosphäre, tiefer Schlaf",
    "Helles Schlafzimmer am Morgen, Kaffeetasse auf Nachttisch, Person sitzt lächelnd im Bett",
    "Paar im Bett, beide schlafen ruhig ohne sich gegenseitig zu stören",
]

FONTS = ["sans_bold", "sans_modern", "serif_elegant"]


def load_configs():
    """Load all config files."""
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    guidelines_path = os.path.join(PROJECT_ROOT, "branding", "brand_guidelines.json")
    angles_path = os.path.join(PROJECT_ROOT, "angles", "angles.json")

    for p, name in [(brand_path, "brand.json"), (guidelines_path, "brand_guidelines.json"), (angles_path, "angles.json")]:
        if not os.path.exists(p):
            print(f"Error: {name} not found at {p}")
            sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)
    with open(guidelines_path) as f:
        guidelines = json.load(f)
    with open(angles_path) as f:
        angles_data = json.load(f)

    return brand, guidelines, angles_data


def find_product(brand, handle):
    """Find product by handle."""
    for p in brand["products"]:
        if p["handle"] == handle:
            return p
    print(f"Error: Product '{handle}' not found. Available: {[p['handle'] for p in brand['products']]}")
    sys.exit(1)


def pick_formats(count, fmt):
    """Pick formats based on distribution."""
    if fmt != "mix":
        return [fmt] * count

    pool = []
    for f, w in FORMAT_WEIGHTS.items():
        pool.extend([f] * w)

    formats = []
    for i in range(count):
        formats.append(pool[i % len(pool)])
    random.shuffle(formats)
    return formats


def pick_angles(angles_list, count, angle_filter):
    """Pick angles with rotation (no repeats until all used)."""
    if angle_filter and angle_filter != "mix":
        matching = [a for a in angles_list if a["type"] == angle_filter or a["id"] == angle_filter]
        if not matching:
            matching = [a for a in angles_list if angle_filter.lower() in a["name"].lower()]
        if not matching:
            print(f"Warning: Angle '{angle_filter}' not found. Using all angles.")
            matching = angles_list
        pool = matching
    else:
        pool = angles_list

    picked = []
    shuffled = list(pool)
    random.shuffle(shuffled)
    angle_cycle = cycle(shuffled)
    for _ in range(count):
        picked.append(next(angle_cycle))
    return picked


def pick_types(count, type_filter):
    """Pick creative types."""
    if type_filter != "mix":
        return [type_filter] * count

    types = []
    for i in range(count):
        types.append("lifestyle" if random.random() < 0.4 else "product_static")
    return types


def pick_styles(count, style_filter):
    """Pick on_brand / off_brand mix."""
    if style_filter != "mix":
        return [style_filter] * count

    styles = []
    for i in range(count):
        styles.append("off_brand" if random.random() < 0.3 else "on_brand")
    return styles


def build_prompt(angle, product, brand, guidelines, fmt, creative_type, style, variant):
    """Build a single creative-producer compatible JSON prompt."""
    colors = guidelines.get("colors", {})
    resolution = FORMAT_RESOLUTIONS[fmt]

    # Pick headline and hook from angle
    headline = random.choice(angle.get("headline_variants", [angle["name"]]))
    hook = random.choice(angle.get("hook_variants", [""]))

    # Pick benefits from product
    benefits = random.sample(product.get("benefits", [])[:6], min(3, len(product.get("benefits", []))))

    # Determine background
    is_lifestyle = creative_type == "lifestyle"
    if is_lifestyle:
        bg_type = random.choice(BG_TYPES_LIFESTYLE)
        scene = random.choice(LIFESTYLE_SCENES)
    else:
        bg_type = random.choice(BG_TYPES_PRODUCT)
        scene = None

    # Color palette based on style
    if style == "off_brand":
        palette = [
            random.choice(["#1A1A2E", "#16213E", "#0F3460", "#533483", "#2C3333", "#395B64"]),
            random.choice(["#E94560", "#F77F00", "#FCBF49", "#06D6A0", "#118AB2", "#EF476F"]),
            "#FFFFFF",
        ]
        primary_color = palette[0]
        accent_color = palette[1]
    else:
        primary_color = colors.get("primary", "#272727")
        accent_color = colors.get("accent", "#3C619E")
        palette = [primary_color, colors.get("secondary", "#F2F2F2"), accent_color, "#FFFFFF"]

    # Logo visibility (diverse: sometimes yes, sometimes no)
    show_logo = random.random() > 0.3

    # Font choice
    font = random.choice(FONTS)

    # Product image
    product_image = f"products/images/{product['handle']}/0.jpg"

    # Scene type
    scene_type = "negative" if angle["type"] == "Problem/Pain" and random.random() < 0.4 else "positive"

    prompt = {
        "prompt": {
            "meta": {
                "angle": angle["type"],
                "sub_angle": angle["name"],
                "hook_text": hook,
                "variant": variant,
                "scene_type": scene_type,
                "format": fmt,
                "resolution": resolution,
            },
            "canvas": {
                "background": {
                    "type": bg_type,
                    "primary_color": primary_color,
                    "secondary_color": palette[1] if len(palette) > 1 else None,
                    "gradient_direction": random.choice(["top_to_bottom", "radial", "diagonal"]) if bg_type == "gradient" else None,
                    "scene_description": scene if is_lifestyle else None,
                    "texture_description": None,
                    "opacity": 1.0,
                },
                "lighting": {
                    "type": "soft_natural" if is_lifestyle else "studio",
                    "direction": random.choice(["frontal", "top_left", "ambient"]),
                    "warmth": "warm",
                    "intensity": "medium",
                    "shadows": "subtle",
                },
                "color_mood": {
                    "palette": palette,
                    "mood": f"{angle['type']} — {angle['name']}",
                    "saturation": "natural" if style == "on_brand" else "vibrant",
                    "contrast": "high" if style == "off_brand" else "medium",
                },
            },
            "layout": {
                "type": random.choice(LAYOUT_TYPES[:3]) if not is_lifestyle else "full_bleed_lifestyle",
                "zones": {
                    "top": {"height_percent": 25, "content": "headline", "background": None},
                    "middle": {"height_percent": 45, "content": "lifestyle_scene" if is_lifestyle else "product_hero"},
                    "bottom": {"height_percent": 30, "content": "cta_price"},
                },
                "margins": {"outer": "medium", "inner_gap": "normal"},
                "alignment": "center",
            },
            "product": {
                "source_image": product_image,
                "display_mode": "single_hero",
                "position": {"x": "center", "y": "center"},
                "scale": random.choice([0.45, 0.5, 0.55, 0.6]),
                "rotation": random.choice([0, 0, 0, -5, 5]),
                "perspective": random.choice(["straight_on", "slight_angle"]),
                "shadow": {"type": "drop_shadow", "intensity": "medium", "direction": "below"},
                "surface": None,
                "decorative_elements": [],
            },
            "text_overlays": [
                {
                    "role": "headline",
                    "content": headline,
                    "position": {"x": "center", "y": "upper_third"},
                    "style": {
                        "font_family": font,
                        "font_weight": "bold",
                        "font_size": random.choice(["xl", "xxl"]),
                        "color": "#FFFFFF" if primary_color.startswith("#1") or primary_color.startswith("#2") or primary_color.startswith("#0") else primary_color,
                        "letter_spacing": "normal",
                        "text_transform": random.choice(["none", "uppercase"]),
                        "line_height": 1.2,
                        "max_width_percent": 85,
                        "text_align": "center",
                    },
                    "decoration": {"background": None, "shadow": "subtle"},
                    "emphasis_words": [],
                    "emphasis_style": {},
                },
            ],
            "visual_elements": {
                "badges": [],
                "dividers": [],
                "icons": ["checkmark"] * len(benefits),
                "shapes": [],
            },
            "brand_elements": {
                "logo": {
                    "visible": show_logo,
                    "position": "top_center",
                    "size": "medium",
                    "color_mode": "auto",
                },
                "brand_colors_usage": f"{'Off-brand experimentell' if style == 'off_brand' else 'On-brand Ora Sleep Farben'}",
                "trust_signals": brand.get("trust_signals", [])[:2],
            },
            "generation_instructions": {
                "style_reference": f"{'Experimentelles' if style == 'off_brand' else 'Clean, Swiss'} {'Lifestyle' if is_lifestyle else 'Product'} Ad. Angle: {angle['name']}. Format: {fmt}. {'Mutige Farben und Layouts.' if style == 'off_brand' else 'Minimalistisch, professionell.'}",
                "must_include": [
                    f"Headline: \"{headline}\"",
                    f"{'Lifestyle Szene' if is_lifestyle else f'Produkt: {product[\"name\"]}'}"
                ] + [f"Benefit: {b}" for b in benefits],
                "must_avoid": [
                    "Health claims (heilt, garantiert, medizinisch bewiesen)",
                    "Any brand logo text — composited in post-processing" if show_logo else "",
                    "More than one product",
                    "Cluttered backgrounds",
                    "AI artifacts",
                ],
                "quality_notes": "4K quality, no watermarks, photorealistic. German text correctly spelled.",
                "text_rendering_notes": "Clean typography, no overlapping text. All text in German.",
            },
        },
        "product_image": product_image,
        "creative_style": style,
        "creative_type": creative_type,
        "season": "evergreen",
    }

    return prompt


def main():
    parser = argparse.ArgumentParser(description="Prompt Builder — Dynamic creative prompt generator")
    parser.add_argument("--product", required=True, help="Product handle from brand.json")
    parser.add_argument("--angle", default="mix", help="Angle ID, type, or 'mix' for diverse batch")
    parser.add_argument("--count", type=int, default=6, help="Number of creatives (default: 6)")
    parser.add_argument("--format", default="mix", choices=["4:5", "9:16", "1:1", "mix"], help="Ad format or 'mix'")
    parser.add_argument("--style", default="mix", choices=["on_brand", "off_brand", "mix"], help="Creative style")
    parser.add_argument("--type", default="mix", choices=["product_static", "lifestyle", "mix"], help="Creative type")
    parser.add_argument("--output", default=None, help="Output path for prompts JSON")
    args = parser.parse_args()

    brand, guidelines, angles_data = load_configs()
    product = find_product(brand, args.product)
    angles_list = angles_data.get("angles", [])

    if not angles_list:
        print("Error: No angles found in angles.json")
        sys.exit(1)

    # Pick diverse combinations
    formats = pick_formats(args.count, args.format)
    angles = pick_angles(angles_list, args.count, args.angle)
    types = pick_types(args.count, args.type)
    styles = pick_styles(args.count, args.style)

    print(f"Prompt Builder")
    print(f"  Product: {product['name']}")
    print(f"  Count: {args.count}")
    print(f"  Angles: {len(set(a['id'] for a in angles))} unique")
    print(f"  Formats: {dict((f, formats.count(f)) for f in set(formats))}")
    print(f"  Types: {dict((t, types.count(t)) for t in set(types))}")
    print(f"  Styles: {dict((s, styles.count(s)) for s in set(styles))}")

    # Build prompts
    prompts = []
    for i in range(args.count):
        prompt = build_prompt(
            angle=angles[i],
            product=product,
            brand=brand,
            guidelines=guidelines,
            fmt=formats[i],
            creative_type=types[i],
            style=styles[i],
            variant=i + 1,
        )
        prompts.append(prompt)

    # Diversity check
    unique_angles = len(set(a["id"] for a in angles))
    unique_formats = len(set(formats))
    has_lifestyle = "lifestyle" in types

    print(f"\n  Diversity Check:")
    print(f"    Angles: {unique_angles} {'✓' if unique_angles >= min(3, args.count) else '⚠️ wenig Diversity'}")
    print(f"    Formats: {unique_formats} {'✓' if unique_formats >= min(2, args.count) else '⚠️ wenig Diversity'}")
    print(f"    Lifestyle: {'✓' if has_lifestyle else '⚠️ kein Lifestyle'}")

    # Save
    batch_id = str(uuid.uuid4())[:8]
    output_path = args.output or os.path.join(PROJECT_ROOT, "creatives", f"batch_{batch_id}_prompts.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved: {output_path}")
    print(f"\n  Run creative-producer:")
    print(f"  python3 .claude/skills/creative-producer/scripts/main.py --prompts-file {os.path.relpath(output_path, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
