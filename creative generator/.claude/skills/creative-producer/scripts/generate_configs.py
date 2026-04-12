#!/usr/bin/env python3
"""Config Generator — Produces diverse pipeline configs for batch_pipeline.py.

Generates randomized but aesthetically coherent configs by combining:
- Angles from angles.json (headlines, data points, hooks)
- Brand data from brand.json (products, trust signals, prices)
- Diverse visual treatments (backgrounds, overlays, typography styles)

Usage:
    python3 generate_configs.py --count 12 --output creatives/pipeline_configs.json
    python3 generate_configs.py --count 24 --output configs.json --seed 42
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

# ---------------------------------------------------------------------------
# Visual palette constants
# ---------------------------------------------------------------------------

ORA_COLORS = [
    "#2D3748",  # dark blue-gray (Ora primary)
    "#1A202C",  # navy
    "#2D2D2D",  # charcoal
    "#F5F0EB",  # warm cream
    "#FFFFFF",  # white
    "#1A1A2E",  # deep navy
    "#272727",  # Ora brand dark
    "#E8D5C4",  # warm beige (lifestyle)
    "#1E3A5F",  # ocean blue
    "#3A3A5C",  # slate
    "#F4EDE4",  # off-white warm
    "#0F1419",  # almost black
]

ORA_DARK_COLORS = ["#2D3748", "#1A202C", "#2D2D2D", "#1A1A2E", "#272727", "#1E3A5F", "#0F1419"]
ORA_LIGHT_COLORS = ["#F5F0EB", "#FFFFFF", "#E8D5C4", "#F4EDE4"]

GRADIENTS = [
    # Dark gradients
    {"color": "#2D3748", "gradient_to": "#1A202C", "direction": "top_to_bottom"},
    {"color": "#1A1A2E", "gradient_to": "#2D3748", "direction": "top_to_bottom"},
    {"color": "#2D2D2D", "gradient_to": "#1A1A2E", "direction": "diagonal"},
    {"color": "#1A202C", "gradient_to": "#2D3748", "direction": "bottom_to_top"},
    {"color": "#272727", "gradient_to": "#0F1419", "direction": "top_to_bottom"},
    {"color": "#1E3A5F", "gradient_to": "#0F1419", "direction": "diagonal"},
    # Light gradients
    {"color": "#F5F0EB", "gradient_to": "#FFFFFF", "direction": "top_to_bottom"},
    {"color": "#FFFFFF", "gradient_to": "#F5F0EB", "direction": "top_to_bottom"},
    {"color": "#E8D5C4", "gradient_to": "#F4EDE4", "direction": "top_to_bottom"},
    {"color": "#F4EDE4", "gradient_to": "#E8D5C4", "direction": "diagonal"},
    # Dark-to-warm accent
    {"color": "#1A1A2E", "gradient_to": "#3A3A5C", "direction": "top_to_bottom"},
]

# Product images categorized
LIFESTYLE_IMAGES = [
    "products/images/ora-ultra-matratze/0.jpg",  # couple
    "products/images/ora-ultra-matratze/1.jpg",  # woman sleeping
    "products/images/ora-ultra-matratze/6.png",  # lifestyle
    "products/images/ora-ultra-matratze/7.png",  # lifestyle
]

# These images already have text/labels baked in — ONLY use as full-bleed background, NOT as overlay
PRODUCT_INFO_IMAGES = [
    "products/images/ora-ultra-matratze/2.png",   # layer diagram (dark, has text)
    "products/images/ora-ultra-matratze/3.png",   # OraVital design (light, has text)
    "products/images/ora-ultra-matratze/5.png",   # hand on foam + testimonial (has text)
    "products/images/ora-ultra-matratze/9.jpg",   # layer + badges (has text)
]

# Clean product/lifestyle images that work as overlays on color/gradient backgrounds
OVERLAY_IMAGES = [
    "products/images/ora-ultra-matratze/0.jpg",   # couple on mattress (studio shot, the HERO)
    "products/images/ora-ultra-matratze/1.jpg",   # woman sleeping in bedroom
]

# CTA variants
CTAS = [
    "Jetzt entdecken",
    "Jetzt testen",
    "Mehr erfahren",
    "Jetzt bestellen",
    "Kostenlos testen",
    "200 Nächte testen",
    "Jetzt Angebot sichern",
    "Jetzt upgraden",
]

CTA_COLORS = [
    "#E8A838",  # golden amber (default)
    "#FFFFFF",  # white
    "#3C619E",  # slate blue
    "#06D6A0",  # mint green
    "#F77F00",  # amber orange
]

# Subheadline templates by angle type
SUBHEADLINES_BY_TYPE = {
    "Benefit": [
        "Das sagen unsere Kunden.",
        "Besser schlafen ab Nacht 1.",
        "Spürbar mehr Lebensqualität.",
        "Laut Kundenumfrage.",
    ],
    "Problem/Pain": [
        "Kennst du das?",
        "Das muss nicht sein.",
        "Es gibt eine Lösung.",
        "Schluss damit.",
    ],
    "Proof": [
        "Echte Zahlen. Echte Kunden.",
        "Das sagen 108 Kunden.",
        "Zahlen lügen nicht.",
        "Unsere Kunden bestätigen:",
    ],
    "Story": [
        "Echte Kundenstimme.",
        "So war es bei mir.",
        "Eine wahre Geschichte.",
        "Kundenerfahrung.",
    ],
    "Curiosity": [
        "Die Wahrheit über Matratzen.",
        "Was du wissen solltest.",
        "Überraschende Fakten.",
    ],
    "Education": [
        "Schlafwissen.",
        "Die Wissenschaft dahinter.",
        "Gut zu wissen.",
    ],
    "Offer": [
        "Nur für kurze Zeit.",
        "Limitiertes Angebot.",
        "Jetzt sparen.",
        "Exklusiv online.",
    ],
}

TRUST_SIGNALS = [
    "Swiss Made | Testsieger 2026",
    "Testsieger 2026 | 200 Nächte testen",
    "Kostenlose Lieferung | 10 Jahre Garantie",
    "Swiss Made | Kostenlose Lieferung",
    "108 zufriedene Kunden | Swiss Made",
    "200 Nächte testen | Gratis Rückgabe",
]

TRUST_BAR_ITEMS = [
    ["Kostenlose Lieferung", "200 Nächte testen", "10 Jahre Garantie", "Swiss Made"],
    ["Swiss Made", "Testsieger 2026", "200 Nächte testen", "Gratis Versand"],
    ["10 Jahre Garantie", "Kostenlose Lieferung", "Swiss Made", "200 Nächte"],
]

PRICES = [
    "ab CHF 899",
    "ab CHF 899 statt CHF 2.091",
    "CHF 899",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_angles(path: str) -> list:
    """Load angles from angles.json."""
    if not os.path.exists(path):
        print(f"Warning: angles.json not found at {path}")
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("angles", [])


def load_brand(path: str) -> dict:
    """Load brand data from brand.json."""
    if not os.path.exists(path):
        print(f"Warning: brand.json not found at {path}")
        return {}
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Config generation
# ---------------------------------------------------------------------------

def _pick_format(rng: random.Random) -> str:
    """Pick a format with weighted distribution: 4:5 (40%), 9:16 (40%), 1:1 (20%)."""
    return rng.choices(["4:5", "9:16", "1:1"], weights=[40, 40, 20], k=1)[0]


def _pick_background(rng: random.Random) -> dict:
    """Pick a background config: color (30%), gradient (30%), photo (40%)."""
    mode = rng.choices(["color", "gradient", "photo"], weights=[30, 30, 40], k=1)[0]

    if mode == "color":
        color = rng.choice(ORA_COLORS)
        return {"mode": "color", "color": color}

    elif mode == "gradient":
        grad = rng.choice(GRADIENTS)
        return {
            "mode": "gradient",
            "color": grad["color"],
            "gradient_to": grad["gradient_to"],
            "gradient_direction": grad["direction"],
        }

    else:  # photo — use lifestyle images (clean photos without baked-in text)
        photo = rng.choice(LIFESTYLE_IMAGES)
        return {
            "mode": "photo",
            "photo_path": photo,
        }


def _pick_product_overlay(rng: random.Random, bg_mode: str, bg_config: dict) -> dict:
    """Pick product overlay config. Disabled for lifestyle photo backgrounds 75% of time."""
    # For photo backgrounds with lifestyle images, often skip overlay
    if bg_mode == "photo":
        photo_path = bg_config.get("photo_path", "")
        is_lifestyle = any(lf in photo_path for lf in ["0.jpg", "1.jpg", "6.png", "7.png"])
        if is_lifestyle:
            # Lifestyle photos usually don't need product overlay
            if rng.random() < 0.75:
                return {"enabled": False}

    # For color/gradient backgrounds, ALWAYS enable overlay (otherwise empty canvas)
    # For photo backgrounds, 60% chance
    if bg_mode == "photo" and rng.random() > 0.60:
        return {"enabled": False}

    image_path = rng.choice(OVERLAY_IMAGES)
    scale = round(rng.uniform(0.65, 0.85), 2)
    # center_bottom looks more polished (product sits on the bottom, text on top)
    position = rng.choices(["center_bottom", "center"], weights=[70, 30], k=1)[0]

    # Rounded rect mask for photo-on-color — always use it for visual polish
    mask = "none"
    if bg_mode in ("color", "gradient"):
        mask = "rounded_rect"

    return {
        "enabled": True,
        "image_path": image_path,
        "position": position,
        "scale": scale,
        "mask": mask,
        "shadow": True,
    }


def _pick_gradient_overlay(rng: random.Random, bg_mode: str, has_text_top: bool) -> dict:
    """Pick gradient overlay config for text readability."""
    if bg_mode == "photo":
        # Always add gradient overlay for photo backgrounds
        enabled = True
    else:
        # 50% for color/gradient backgrounds
        enabled = rng.random() < 0.50

    if not enabled:
        return {"enabled": False}

    # Type based on where text appears
    if has_text_top:
        grad_type = rng.choice(["top", "both", "both"])  # 67% both when text on top
    else:
        grad_type = rng.choice(["top", "both"])

    opacity = round(rng.uniform(0.35, 0.60), 2)

    return {
        "enabled": True,
        "type": grad_type,
        "opacity": opacity,
    }


def _pick_text(rng: random.Random, angle: dict) -> dict:
    """Build text config from an angle entry."""
    angle_type = angle.get("type", "Benefit")
    headline_variants = angle.get("headline_variants", ["Besserer Schlaf"])
    hook_variants = angle.get("hook_variants", [])
    data_point = angle.get("data_point", "")

    # Headline: pick from angle variants
    headline = rng.choice(headline_variants)

    # Subheadline: type-appropriate
    subheadline_pool = SUBHEADLINES_BY_TYPE.get(angle_type, SUBHEADLINES_BY_TYPE["Benefit"])
    subheadline = rng.choice(subheadline_pool)

    # Headline style
    headline_style = rng.choices(
        ["bold", "uppercase", "bold"],  # bold most common
        weights=[50, 20, 30], k=1
    )[0]

    # Data point: extract number and label if available
    data_number = None
    data_label = None
    if data_point and rng.random() < 0.50:
        # Try to extract a percentage or number from the data point
        import re
        number_match = re.search(r'(\d+%)', data_point)
        if number_match:
            data_number = number_match.group(1)
            # Use part of the data point as label
            data_label = data_point.split(",")[0]
            # Remove the number from the label to avoid duplication
            data_label = data_label.replace(data_number, "").strip()
            if data_label.startswith("der ") or data_label.startswith("von "):
                pass  # keep as-is
            elif not data_label:
                data_label = "unserer Kunden berichten"

    # CTA
    cta = rng.choice(CTAS)
    cta_color = rng.choice(CTA_COLORS)

    # Price: 40% of the time
    price = rng.choice(PRICES) if rng.random() < 0.40 else None

    # Trust signal: 60% of the time
    trust_signal = rng.choice(TRUST_SIGNALS) if rng.random() < 0.60 else None

    text_config = {
        "subheadline": subheadline,
        "headline": headline,
        "headline_style": headline_style,
        "cta": cta,
        "cta_color": cta_color,
    }

    if data_number:
        text_config["data_number"] = data_number
    if data_label:
        text_config["data_label"] = data_label
    if price:
        text_config["price"] = price
    if trust_signal:
        text_config["trust_signal"] = trust_signal

    return text_config


def _pick_logo(rng: random.Random) -> dict:
    """Logo config: visible 70% of time."""
    if rng.random() > 0.70:
        return {"visible": False}

    position = rng.choices(
        ["top_center", "top_left", "top_right"],
        weights=[50, 30, 20], k=1
    )[0]

    return {"visible": True, "position": position}


def _pick_trust_bar(rng: random.Random) -> dict:
    """Trust bar config: visible 50% of time."""
    if rng.random() > 0.50:
        return {"visible": False}

    items = rng.choice(TRUST_BAR_ITEMS)
    return {"visible": True, "items": items}


def _determine_creative_type(bg_mode: str, overlay_enabled: bool, has_data: bool) -> str:
    """Infer creative type from config properties."""
    if has_data:
        return "data_driven"
    if bg_mode == "photo" and not overlay_enabled:
        return "lifestyle"
    return "product_static"


def generate_single_config(rng: random.Random, angle: dict) -> dict:
    """Generate a single pipeline config + meta from an angle."""
    fmt = _pick_format(rng)
    bg_config = _pick_background(rng)
    bg_mode = bg_config["mode"]

    product_overlay = _pick_product_overlay(rng, bg_mode, bg_config)
    overlay_enabled = product_overlay.get("enabled", False)

    text_config = _pick_text(rng, angle)
    has_data = "data_number" in text_config

    # Gradient overlay: needs to know if text is at top
    gradient_overlay = _pick_gradient_overlay(rng, bg_mode, has_text_top=True)

    logo = _pick_logo(rng)
    trust_bar = _pick_trust_bar(rng)

    creative_type = _determine_creative_type(bg_mode, overlay_enabled, has_data)

    # Determine hook_text from headline or hook_variants
    hook_variants = angle.get("hook_variants", [])
    hook_text = text_config.get("headline", "")
    if hook_variants and rng.random() < 0.40:
        hook_text = rng.choice(hook_variants)

    pipeline_config = {
        "format": fmt,
        "background": bg_config,
        "product_overlay": product_overlay,
        "gradient_overlay": gradient_overlay,
        "text": text_config,
        "logo": logo,
        "trust_bar": trust_bar,
    }

    # Creative style based on background approach
    if bg_mode == "photo":
        creative_style = "lifestyle" if not overlay_enabled else "on_brand"
    elif bg_mode in ("color", "gradient") and not overlay_enabled:
        creative_style = "minimal"
    else:
        creative_style = "on_brand"

    meta = {
        "angle": angle.get("name", "Unknown"),
        "sub_angle": angle.get("type", "Benefit"),
        "hook_text": hook_text,
        "format": fmt,
        "creative_style": creative_style,
        "creative_type": creative_type,
    }

    return {
        "pipeline_config": pipeline_config,
        "meta": meta,
    }


def generate_configs(count: int, angles: list, seed: int = None) -> list:
    """Generate a diverse set of pipeline configs.

    Ensures diversity by:
    - Cycling through all angles before repeating
    - Tracking used formats/backgrounds to avoid clusters
    """
    rng = random.Random(seed)

    if not angles:
        print("Error: No angles available — cannot generate configs")
        sys.exit(1)

    configs = []
    angle_pool = list(angles)
    rng.shuffle(angle_pool)
    angle_idx = 0

    # Track diversity metrics
    format_counts = {"4:5": 0, "9:16": 0, "1:1": 0}
    bg_mode_counts = {"color": 0, "gradient": 0, "photo": 0}

    for i in range(count):
        # Cycle through angles
        if angle_idx >= len(angle_pool):
            angle_pool = list(angles)
            rng.shuffle(angle_pool)
            angle_idx = 0

        angle = angle_pool[angle_idx]
        angle_idx += 1

        config = generate_single_config(rng, angle)

        # Track diversity
        fmt = config["pipeline_config"]["format"]
        bg_mode = config["pipeline_config"]["background"]["mode"]
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        bg_mode_counts[bg_mode] = bg_mode_counts.get(bg_mode, 0) + 1

        configs.append(config)

    return configs, format_counts, bg_mode_counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate diverse pipeline configs for batch_pipeline.py"
    )
    parser.add_argument(
        "--count", type=int, default=12,
        help="Number of configs to generate (default: 12)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output JSON file path (relative to project root or absolute)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility (optional)"
    )
    args = parser.parse_args()

    # Load data sources
    angles_path = os.path.join(PROJECT_ROOT, "angles", "angles.json")
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")

    angles = load_angles(angles_path)
    brand = load_brand(brand_path)

    if not angles:
        print("Error: No angles loaded. Ensure angles/angles.json exists.")
        sys.exit(1)

    print(f"Loaded {len(angles)} angles from {angles_path}")
    print(f"Brand: {brand.get('name', 'Unknown')}")
    print(f"Generating {args.count} configs...")

    if args.seed is not None:
        print(f"Seed: {args.seed}")

    # Generate
    configs, fmt_counts, bg_counts = generate_configs(args.count, angles, args.seed)

    # Resolve output path
    output_path = args.output
    if not os.path.isabs(output_path):
        output_path = os.path.join(PROJECT_ROOT, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\nGenerated {len(configs)} configs -> {output_path}")
    print(f"\nFormat distribution:")
    for fmt, cnt in sorted(fmt_counts.items()):
        pct = cnt / len(configs) * 100
        print(f"  {fmt}: {cnt} ({pct:.0f}%)")
    print(f"\nBackground distribution:")
    for mode, cnt in sorted(bg_counts.items()):
        pct = cnt / len(configs) * 100
        print(f"  {mode}: {cnt} ({pct:.0f}%)")

    # Count unique angles used
    used_angles = set()
    for c in configs:
        used_angles.add(c["meta"]["angle"])
    print(f"\nAngles used: {len(used_angles)} of {len(angles)}")

    # Count creative types
    type_counts = {}
    for c in configs:
        ct = c["meta"]["creative_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1
    print(f"\nCreative types:")
    for ct, cnt in sorted(type_counts.items()):
        print(f"  {ct}: {cnt}")


if __name__ == "__main__":
    main()
