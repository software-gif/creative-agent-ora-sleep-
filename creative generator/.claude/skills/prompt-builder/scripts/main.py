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
    "Warmes, helles Schlafzimmer mit Holzmöbeln im natürlichen Stil, Ora Matratze sichtbar mit 'ora' Schriftzug an der Seite, weiches Morgenlicht",
    "Frau streckt sich glücklich nach dem Aufwachen auf Ora Matratze, Morgenlicht fällt durch Vorhänge, warme Farbtöne",
    "Person schläft friedlich auf Ora Matratze, kuschelige Bettwäsche, warme Farbtöne, ruhige Atmosphäre",
    "Clean Product Shot: Matratze auf Holzbettgestell, minimalistischer Raum, helle Wände, professionelle Beleuchtung",
    "Paar im Bett, entspannte Atmosphäre, gemütliches Licht, warme Ausstrahlung, beide zufrieden",
    "Dunkles, stimmungsvolles Schlafzimmer, Person schläft tief, dramatische Beleuchtung, Premium-Atmosphäre",
]

FONTS = ["sans_bold", "sans_modern", "serif_elegant"]


def load_configs():
    """Load all config files."""
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    guidelines_path = os.path.join(PROJECT_ROOT, "branding", "brand_guidelines.json")
    angles_path = os.path.join(PROJECT_ROOT, "angles", "angles.json")

    for p, name in [(brand_path, "brand.json"), (angles_path, "angles.json")]:
        if not os.path.exists(p):
            print(f"Error: {name} not found at {p}")
            sys.exit(1)

    with open(brand_path) as f:
        brand = json.load(f)

    # Guidelines are optional — use defaults if missing
    guidelines = {}
    if os.path.exists(guidelines_path):
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


CTA_VARIANTS = [
    "Jetzt testen", "Mehr erfahren", "Jetzt entdecken", "Jetzt bestellen",
    "Kostenlos testen", "Jetzt upgraden", "Schlaf verbessern",
    "Jetzt sichern", "Gratis testen",
]

TRUST_SIGNAL_VARIANTS = [
    "Swiss Made | Testsieger 2026",
    "4.5 ★ auf Trustpilot | 237 Bewertungen",
    "Swiss Made | 108 zufriedene Kunden",
    "Testsieger 2026 | Kostenlose Lieferung",
    "Swiss Made Qualität | 60 Nächte testen",
    "237 Trustpilot Bewertungen | 4.5 ★",
]


def _build_text_overlays(angle, product, brand, headline, hook, benefits, font, primary_color, creative_type, style):
    """Build diverse text overlays based on angle and creative type.

    Not every creative needs all elements. Vary what's shown for diversity.
    """
    overlays = []
    is_dark_bg = primary_color.startswith("#1") or primary_color.startswith("#2") or primary_color.startswith("#0") or primary_color.startswith("#3")
    text_color = "#FFFFFF" if is_dark_bg else "#272727"

    # Angle-specific high-performing headline patterns (mixed in ~40% of the time)
    angle_type = angle.get("type", "")
    used_hook = False
    if random.random() < 0.4:
        headline_hooks = {
            "Problem/Pain": [
                "Schlechter Schlaf? War gestern.",
                "Rückenschmerzen nach dem Aufstehen?",
                "Jede Nacht dasselbe Problem.",
            ],
            "Benefit": [
                "Schlaf, der dein Leben verändert.",
                "Erholt aufwachen. Besser leben.",
                "Ab der ersten Nacht besser schlafen.",
            ],
            "Proof": [
                "93% spüren mehr Energie.",
                "4.5 Sterne auf Trustpilot.",
                "108 Kunden, eine Meinung.",
            ],
            "Offer": [
                "Testsieger zum besten Preis.",
                "Jetzt ab CHF 899.",
                "Schweizer Qualität zum besten Preis.",
            ],
            "Story": [
                "Schlaf, made in Switzerland.",
                "Einmal Ora, immer Ora.",
            ],
            "Education": [
                "Was passiert nach 7h auf der richtigen Matratze?",
                "Ocean Cool Technologie erklärt.",
            ],
            "Curiosity": [
                "3 Matratzen-Mythen, die dich Schlaf kosten.",
                "Was deine Matratze dir verschweigt.",
            ],
        }
        alt_headlines = headline_hooks.get(angle_type, [])
        if alt_headlines:
            headline = random.choice(alt_headlines)
            used_hook = True

    # Cap headline length — max ~60 chars to prevent 7-line monsters
    if len(headline) > 60:
        # Shorten to first sentence or clause
        for sep in [". ", " — ", " – ", ", "]:
            if sep in headline[:55]:
                headline = headline[:headline.index(sep, 0, 55) + len(sep)].rstrip(", —–")
                break

    # 1. HEADLINE — always present (the main hook)
    overlays.append({
        "role": "headline",
        "content": headline,
        "position": {"x": "center", "y": "upper_third"},
        "style": {
            "font_family": font,
            "font_weight": "bold",
            "font_size": "xl",
            "color": text_color,
            "text_transform": random.choice(["none", "uppercase"]),
            "text_align": "center",
        },
    })

    # 1b. SUBHEADLINE — ~50% of the time, positioned ABOVE the headline
    # Subheadline must NEVER be the same as the headline
    add_subheadline = random.random() < 0.5
    if add_subheadline:
        subheadline_variants = {
            "Problem/Pain": ["Das kennt jeder.", "Kommt dir das bekannt vor?"],
            "Benefit": ["Dein Tag beginnt mit einer Nacht auf Ora.", "Das Ora Versprechen."],
            "Proof": ["Das sagen unsere Kunden.", "Echte Ergebnisse."],
            "Offer": ["Nur für kurze Zeit.", "Das Ora Angebot."],
            "Story": ["So geht Schlaf.", "Echte Kunden, echte Geschichten."],
            "Education": ["Wusstest du das?", "Schlaf-Wissenschaft."],
            "Curiosity": ["Überraschende Fakten.", "Das wissen die wenigsten."],
        }
        sub_options = subheadline_variants.get(angle_type, ["Schlaf neu erleben."])
        # Filter out any subheadline that matches the headline
        sub_options = [s for s in sub_options if s.lower().rstrip(".") not in headline.lower()]
        if sub_options:
            overlays.append({
                "role": "subheadline",
                "content": random.choice(sub_options),
                "position": {"x": "center", "y": "upper_quarter", "above_headline": True},
                "style": {
                    "font_family": "sans_medium",
                    "font_weight": "medium",
                    "font_size": "sm",
                    "color": text_color,
                    "text_transform": "none",
                    "text_align": "center",
                },
            })

    # Randomly decide which additional elements to add (for diversity)
    add_cta = random.random() < 0.7
    add_trust = random.random() < 0.6
    add_price = angle["type"] == "Offer" or random.random() < 0.3
    add_benefits = creative_type == "product_static" and random.random() < 0.4

    # 2. CTA BUTTON — Ora Sleep warm gold/orange
    if add_cta:
        overlays.append({
            "role": "cta",
            "content": random.choice(CTA_VARIANTS),
            "position": {"x": "center", "y": "lower_third"},
            "style": {
                "font_family": "sans_bold",
                "font_weight": "bold",
                "font_size": "md",
                "color": "#1A1A2E",
                "background_color": "#E8A838",
                "text_transform": "uppercase",
                "text_align": "center",
            },
        })

    # 3. PRICE (for Offer angles or randomly)
    if add_price:
        price_text = f"ab CHF {int(product.get('price_from', 899))}"
        if product.get('compare_at_price'):
            price_text = f"ab CHF {int(product['price_from'])} statt CHF {int(product['compare_at_price'])}"
        overlays.append({
            "role": "price",
            "content": price_text,
            "position": {"x": "center"},
            "style": {
                "font_family": "sans_bold",
                "font_weight": "bold",
                "font_size": "lg",
                "color": text_color,
                "text_align": "center",
            },
        })

    # 4. TRUST SIGNALS (bottom area)
    if add_trust:
        overlays.append({
            "role": "trust_signals",
            "content": random.choice(TRUST_SIGNAL_VARIANTS),
            "position": {"x": "center", "y": "bottom_safe"},
            "style": {
                "font_family": "sans",
                "font_weight": "regular",
                "font_size": "xs",
                "color": "auto",
                "text_align": "center",
            },
        })

    # 5. BENEFITS LIST (for product_static)
    if add_benefits and benefits:
        benefit_text = ";".join(benefits[:3])
        overlays.append({
            "role": "benefit_list",
            "content": benefit_text,
            "position": {"x": "left", "y": "lower_quarter"},
            "style": {
                "font_family": "sans_medium",
                "font_weight": "medium",
                "font_size": "sm",
                "color": text_color,
                "text_align": "left",
            },
        })

    # 6. TRUST BAR — 4-icon bar at the very bottom (~60% of creatives)
    add_trust_bar = random.random() < 0.6
    if add_trust_bar:
        overlays.append({
            "role": "trust_bar",
            "content": "Kostenlose Lieferung;200 Nächte testen;10 Jahre Garantie;Swiss Made",
            "position": {"x": "center", "y": "bottom"},
            "style": {
                "font_family": "sans",
                "font_weight": "regular",
                "font_size": "xs",
                "color": "#FFFFFF",
                "text_align": "center",
            },
        })

    return overlays


def build_prompt(angle, product, brand, guidelines, fmt, creative_type, style, variant):
    """Build a single creative-producer compatible JSON prompt."""
    # Extract colors — handle both old flat structure and new nested structure
    colors_raw = guidelines.get("colors", {})
    colors = colors_raw.get("website_palette", colors_raw)
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
        primary_color = colors.get("dark", colors.get("primary", "#272727"))
        accent_color = colors.get("navy", colors.get("accent", "#3C619E"))
        secondary_color = colors.get("light_gray", colors.get("secondary", "#F2F2F2"))
        palette = [primary_color, secondary_color, accent_color, "#FFFFFF"]

    # Logo visibility (diverse: sometimes yes, sometimes no)
    show_logo = random.random() > 0.3

    # Font choice
    font = random.choice(FONTS)

    # Product image — rotate through all available images
    img_dir = os.path.join(PROJECT_ROOT, "products", "images", product['handle'])
    if os.path.isdir(img_dir):
        available_images = sorted([f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    else:
        available_images = ["0.jpg"]
    product_image = f"products/images/{product['handle']}/{random.choice(available_images)}"

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
            "text_overlays": _build_text_overlays(
                angle=angle,
                product=product,
                brand=brand,
                headline=headline,
                hook=hook,
                benefits=benefits,
                font=font,
                primary_color=primary_color,
                creative_type=creative_type,
                style=style,
            ),
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
                    "Lifestyle Szene mit Schlafzimmer-Setting" if is_lifestyle else f"Product: {product['name']} mattress clearly visible",
                    "Clean space in top area for text overlay",
                    "Clean space in bottom area for CTA/trust signals",
                ],
                "must_avoid": [
                    "ANY text, words, letters, numbers, labels, or typography in the image",
                    "Any brand logo or wordmark — composited in post-processing",
                    "More than one product",
                    "Cluttered backgrounds",
                    "AI artifacts, distorted faces, extra limbs",
                ],
                "quality_notes": "4K quality, no watermarks, photorealistic. Clean, professional advertising photography.",
                "text_rendering_notes": "DO NOT render any text in the image. Text will be added in post-processing.",
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
