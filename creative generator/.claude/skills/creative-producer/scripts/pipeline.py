#!/usr/bin/env python3
"""Multi-Pass Creative Production Pipeline for Ora Sleep Meta Ads.

Replaces single-pass Gemini approach with a 5-step compositing pipeline
that produces professional-quality static ads at real Meta ad resolutions.

Pipeline Passes:
    1. BACKGROUND   — Solid color, gradient, or real product photo as full-bleed
    2. PRODUCT PHOTO — Composite real Ora product photo onto the background
    3. GRADIENT OVERLAY — Semi-transparent gradient for text readability
    4. TYPOGRAPHY   — Headlines, subheadlines, CTAs, prices, data points
    5. BRAND ELEMENTS — Logo, trust bar, badges

Usage:
    from pipeline import run_pipeline
    png_bytes = run_pipeline(config, project_root)
"""

import io
import math
import os
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Real Meta ad sizes (1080px wide)
FORMAT_SIZES = {
    "4:5":  (1080, 1350),
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
}

# Font file names (Jost family)
FONT_FILES = {
    "regular":  "Jost-Regular.ttf",
    "medium":   "Jost-Medium.ttf",
    "semibold": "Jost-SemiBold.ttf",
    "bold":     "Jost-Bold.ttf",
}

# Trust bar short labels for narrow formats (progressive shortening)
TRUST_SHORT = {
    "Kostenlose Lieferung": "Gratis Versand",
    "Kostenlose Lieferung & Retoure": "Gratis Versand",
    "200 Nächte testen":    "200 Nächte",
    "200 Nächte Probeschlafen": "200 Nächte",
    "10 Jahre Garantie":    "10J Garantie",
    "Gratis Versand":       "Versand",
    "200 Nächte":           "200 N.",
    "10J Garantie":         "10 Jahre",
    "Testsieger 2026":      "Testsieger",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def _hex(color: str) -> tuple:
    """Parse '#RRGGBB' hex string to (R, G, B) tuple."""
    color = color.lstrip("#")
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))


def _hex_rgba(color: str, alpha: int = 255) -> tuple:
    """Parse hex color and return (R, G, B, A)."""
    r, g, b = _hex(color)
    return (r, g, b, alpha)


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB tuples. t in [0, 1]."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _brightness(color: tuple) -> float:
    """Perceived brightness (ITU-R BT.601) from an RGB tuple."""
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def _region_brightness(img: Image.Image, x: int, y: int, w: int, h: int) -> float:
    """Average perceived brightness of a rectangular region."""
    # Clamp to image bounds
    x2 = min(x + w, img.width)
    y2 = min(y + h, img.height)
    x = max(0, x)
    y = max(0, y)
    if x2 <= x or y2 <= y:
        return 128.0
    region = img.crop((x, y, x2, y2)).convert("RGB")
    pixels = list(region.getdata())
    if not pixels:
        return 128.0
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)
    return 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b


def _load_font(fonts_dir: str, weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a Jost font at the given pixel size, with caching."""
    cache_key = (weight, size)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    filename = FONT_FILES.get(weight, FONT_FILES["regular"])
    path = os.path.join(fonts_dir, filename)

    if os.path.exists(path):
        font = ImageFont.truetype(path, size)
    else:
        # Fallback to default if font file is missing
        print(f"  Warning: Font not found: {path}, using default")
        font = ImageFont.load_default()

    _font_cache[cache_key] = font
    return font


def _smooth_ease(t: float) -> float:
    """Smooth ease-in-out curve for gradient transitions. t in [0, 1]."""
    # Hermite interpolation (smoothstep)
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    if not words:
        return []

    lines = []
    current_line = words[0]

    for word in words[1:]:
        test = current_line + " " + word
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def _text_color_for_bg(img: Image.Image, x: int, y: int, w: int, h: int) -> tuple:
    """Choose white or dark text based on background brightness at position."""
    brightness = _region_brightness(img, x, y, w, h)
    if brightness < 128:
        return (255, 255, 255, 255)  # White text on dark bg
    else:
        return (26, 26, 46, 255)  # #1A1A2E dark text on light bg


# ---------------------------------------------------------------------------
# Pass 1: Background
# ---------------------------------------------------------------------------

def _pass_background(config: dict, project_root: str) -> Image.Image:
    """Create the base canvas with the specified background.

    Modes:
        color    — Solid fill with a single hex color.
        gradient — Pixel-by-pixel linear gradient between two colors.
        photo    — Load a real photo, center-crop to fill the canvas.
        gemini   — Use pre-generated Gemini image bytes as background.
    """
    fmt = config.get("format", "4:5")
    canvas_w, canvas_h = FORMAT_SIZES.get(fmt, FORMAT_SIZES["4:5"])

    bg = config.get("background", {})
    mode = bg.get("mode", "color")

    if mode == "color":
        color = _hex(bg.get("color", "#2D3748"))
        img = Image.new("RGBA", (canvas_w, canvas_h), color + (255,))

    elif mode == "gradient":
        color_from = _hex(bg.get("color", "#2D3748"))
        color_to = _hex(bg.get("gradient_to", "#1A202C"))
        direction = bg.get("gradient_direction", "top_to_bottom")

        img = Image.new("RGBA", (canvas_w, canvas_h))
        pixels = img.load()

        for y in range(canvas_h):
            for x in range(canvas_w):
                if direction == "top_to_bottom":
                    t = y / max(canvas_h - 1, 1)
                elif direction == "left_to_right":
                    t = x / max(canvas_w - 1, 1)
                elif direction == "diagonal":
                    t = (x / max(canvas_w - 1, 1) + y / max(canvas_h - 1, 1)) / 2.0
                elif direction == "bottom_to_top":
                    t = 1.0 - y / max(canvas_h - 1, 1)
                else:
                    t = y / max(canvas_h - 1, 1)

                t = _smooth_ease(t)
                r, g, b = _lerp_color(color_from, color_to, t)
                pixels[x, y] = (r, g, b, 255)

    elif mode == "photo":
        photo_path = os.path.join(project_root, bg.get("photo_path", ""))
        if not os.path.exists(photo_path):
            print(f"  Warning: Background photo not found: {photo_path}")
            img = Image.new("RGBA", (canvas_w, canvas_h), (45, 55, 72, 255))
        else:
            photo = Image.open(photo_path).convert("RGBA")
            # Center-crop to fill the canvas while maintaining aspect ratio
            ph_w, ph_h = photo.size
            canvas_ratio = canvas_w / canvas_h
            photo_ratio = ph_w / ph_h

            if photo_ratio > canvas_ratio:
                # Photo is wider — crop sides
                new_h = ph_h
                new_w = int(ph_h * canvas_ratio)
                left = (ph_w - new_w) // 2
                photo = photo.crop((left, 0, left + new_w, new_h))
            else:
                # Photo is taller — crop top/bottom
                new_w = ph_w
                new_h = int(ph_w / canvas_ratio)
                top = (ph_h - new_h) // 2
                photo = photo.crop((0, top, new_w, top + new_h))

            img = photo.resize((canvas_w, canvas_h), Image.LANCZOS)

    elif mode == "gemini":
        gemini_bytes = bg.get("gemini_bytes")
        if gemini_bytes:
            img = Image.open(io.BytesIO(gemini_bytes)).convert("RGBA")
            img = img.resize((canvas_w, canvas_h), Image.LANCZOS)
        else:
            print("  Warning: gemini mode but no gemini_bytes provided, falling back to solid")
            img = Image.new("RGBA", (canvas_w, canvas_h), (45, 55, 72, 255))

    else:
        print(f"  Warning: Unknown background mode '{mode}', falling back to solid")
        img = Image.new("RGBA", (canvas_w, canvas_h), (45, 55, 72, 255))

    return img


# ---------------------------------------------------------------------------
# Pass 2: Product Photo Overlay
# ---------------------------------------------------------------------------

def _pass_product_overlay(img: Image.Image, config: dict, project_root: str) -> Image.Image:
    """Composite a product photo onto the canvas.

    Supports scaling, positioning, rounded-rect masking, and drop shadows.
    """
    overlay_cfg = config.get("product_overlay", {})
    if not overlay_cfg.get("enabled", False):
        return img

    image_path = os.path.join(project_root, overlay_cfg.get("image_path", ""))
    if not os.path.exists(image_path):
        print(f"  Warning: Product image not found: {image_path}")
        return img

    canvas_w, canvas_h = img.size
    product = Image.open(image_path).convert("RGBA")

    # Scale product to config.scale of canvas width, maintaining aspect ratio
    scale = overlay_cfg.get("scale", 0.65)
    target_w = int(canvas_w * scale)
    ratio = product.height / product.width
    target_h = int(target_w * ratio)

    # Constrain product height based on text elements that need space
    # Reserve: top area (headline + subheadline + logo) + bottom area (CTA + price + trust signal + trust bar)
    text_cfg = config.get("text", {})
    has_subheadline = bool(text_cfg.get("subheadline"))
    has_cta = bool(text_cfg.get("cta"))
    has_price = bool(text_cfg.get("price"))
    has_trust_signal = bool(text_cfg.get("trust_signal"))
    trust_bar_visible = config.get("trust_bar", {}).get("visible", False)
    logo_visible = config.get("logo", {}).get("visible", False)

    # Reserve top space: logo (3%) + subheadline (4%) + headline (14%) ≈ 21%
    reserve_top = int(canvas_h * 0.22)
    if has_subheadline:
        reserve_top += int(canvas_h * 0.03)

    # Reserve bottom space: CTA (6%) + price (4%) + trust signal (3%) + trust bar (8%) + padding
    reserve_bottom = int(canvas_h * 0.02)  # Base padding
    if has_cta:
        reserve_bottom += int(canvas_h * 0.07)
    if has_price:
        reserve_bottom += int(canvas_h * 0.05)
    if has_trust_signal:
        reserve_bottom += int(canvas_h * 0.035)
    if trust_bar_visible:
        reserve_bottom += int(canvas_h * 0.08)

    available_h = canvas_h - reserve_top - reserve_bottom
    if target_h > available_h:
        # Scale down to fit
        new_target_h = available_h
        new_target_w = int(new_target_h / ratio)
        # But don't make it too narrow either
        if new_target_w < int(canvas_w * 0.4):
            new_target_w = int(canvas_w * 0.4)
            new_target_h = int(new_target_w * ratio)
        target_w, target_h = new_target_w, new_target_h

    product = product.resize((target_w, target_h), Image.LANCZOS)

    # Apply rounded rectangle mask if requested
    mask_mode = overlay_cfg.get("mask", "none")
    if mask_mode == "rounded_rect":
        radius = int(target_w * 0.03)
        mask = Image.new("L", (target_w, target_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (target_w - 1, target_h - 1)],
            radius=radius,
            fill=255
        )
        # Apply mask to product alpha channel
        product_r, product_g, product_b, product_a = product.split()
        # Combine existing alpha with the rounded mask
        from PIL import ImageChops
        combined_alpha = ImageChops.multiply(product_a, mask)
        product = Image.merge("RGBA", (product_r, product_g, product_b, combined_alpha))

    # Calculate position — product sits in the usable area between top and bottom reserves
    position = overlay_cfg.get("position", "center")
    px = (canvas_w - target_w) // 2  # Always center horizontally

    # Available vertical area for product
    usable_start = reserve_top
    usable_end = canvas_h - reserve_bottom
    usable_h = usable_end - usable_start

    if position == "center_bottom":
        # Push product to bottom of usable area
        py = usable_end - target_h
    elif position == "center":
        # Center within usable area
        py = usable_start + (usable_h - target_h) // 2
    elif position == "bottom_left":
        px = int(canvas_w * 0.05)
        py = usable_end - target_h
    elif position == "bottom_right":
        px = canvas_w - target_w - int(canvas_w * 0.05)
        py = usable_end - target_h
    else:
        py = usable_start + (usable_h - target_h) // 2

    # Safety clamp
    if py < usable_start:
        py = usable_start
    if py + target_h > usable_end:
        py = usable_end - target_h

    # Drop shadow (rendered BEFORE the product)
    if overlay_cfg.get("shadow", False):
        shadow_offset_x = 4
        shadow_offset_y = 8
        shadow_opacity = int(255 * 0.40)
        shadow_blur = 15

        # Create shadow: same shape, filled with black at reduced opacity
        shadow = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        # Use the product alpha as shape reference
        _, _, _, product_alpha = product.split()
        shadow_fill = Image.new("RGBA", (target_w, target_h), (0, 0, 0, shadow_opacity))
        shadow.paste(shadow_fill, mask=product_alpha)

        # Expand shadow canvas for blur padding
        padding = shadow_blur * 3
        shadow_canvas = Image.new("RGBA",
                                  (target_w + padding * 2, target_h + padding * 2),
                                  (0, 0, 0, 0))
        shadow_canvas.paste(shadow, (padding, padding))

        # Blur the shadow
        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur))

        # Paste shadow onto main image
        shadow_x = px + shadow_offset_x - padding
        shadow_y = py + shadow_offset_y - padding
        img.paste(shadow_canvas, (shadow_x, shadow_y), shadow_canvas)

    # Paste the product
    img.paste(product, (px, py), product)

    # Store the product region in config so typography pass can avoid collisions
    config["_product_region"] = {
        "top": py,
        "bottom": py + target_h,
        "left": px,
        "right": px + target_w,
    }

    return img


# ---------------------------------------------------------------------------
# Pass 3: Gradient Overlay (for text readability)
# ---------------------------------------------------------------------------

def _pass_gradient_overlay(img: Image.Image, config: dict) -> Image.Image:
    """Apply semi-transparent dark gradient overlays for text readability.

    This is CRITICAL for photo backgrounds. Instead of ugly text strokes,
    Ora uses smooth gradient overlays so text is always legible.

    Types:
        top    — Dark gradient from top, fading at ~40% height
        bottom — Dark gradient from bottom, fading at ~60% height
        both   — Top and bottom gradients combined
        full   — Very light full-canvas tint
    """
    grad_cfg = config.get("gradient_overlay", {})
    if not grad_cfg.get("enabled", False):
        return img

    canvas_w, canvas_h = img.size
    grad_type = grad_cfg.get("type", "top")
    opacity = grad_cfg.get("opacity", 0.5)

    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    pixels = overlay.load()

    if grad_type in ("top", "both"):
        fade_end = 0.40  # Gradient fades out at 40% of canvas height
        for y in range(int(canvas_h * fade_end)):
            t = y / (canvas_h * fade_end)
            # Alpha goes from full opacity at top to 0 at fade_end
            alpha = int(255 * opacity * (1.0 - _smooth_ease(t)))
            for x in range(canvas_w):
                r, g, b, a = pixels[x, y]
                # Combine with any existing alpha (for "both" mode)
                pixels[x, y] = (0, 0, 0, max(a, alpha))

    if grad_type in ("bottom", "both"):
        fade_start = 0.60  # Gradient begins at 60% of canvas height
        for y in range(int(canvas_h * fade_start), canvas_h):
            t = (y - canvas_h * fade_start) / (canvas_h * (1.0 - fade_start))
            # Alpha goes from 0 at fade_start to full opacity at bottom
            alpha = int(255 * opacity * _smooth_ease(t))
            for x in range(canvas_w):
                r, g, b, a = pixels[x, y]
                pixels[x, y] = (0, 0, 0, max(a, alpha))

    if grad_type == "full":
        # Very light full-canvas tint
        tint_alpha = int(255 * opacity * 0.3)
        overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, tint_alpha))

    img = Image.alpha_composite(img, overlay)
    return img


# ---------------------------------------------------------------------------
# Pass 4: Typography
# ---------------------------------------------------------------------------

def _pass_typography(img: Image.Image, config: dict, project_root: str) -> Image.Image:
    """Render all text elements onto the canvas.

    CRITICAL RULES:
        - NO stroke/outline on ANY text (amateur look)
        - Shadows: offset 1px, opacity 25-35% MAX (barely visible)
        - Clean anti-aliased font rendering

    Elements rendered top-to-bottom:
        1. Subheadline  (~12% from top, Jost-Regular, small, 70% opacity)
        2. Headline     (~15-20% from top, Jost-Bold, large)
        3. Data Point   (big number + small label)
        4. CTA Button   (rounded pill, ~65-70% from top)
        5. Price        (below CTA)
        6. Trust Signal (~88% from top, very small, 80% opacity)
    """
    text_cfg = config.get("text", {})
    if not text_cfg:
        return img

    fonts_dir = os.path.join(project_root, "branding", "fonts")
    canvas_w, canvas_h = img.size

    # Create a text layer for alpha compositing
    text_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    # Margin for text content
    margin_x = int(canvas_w * 0.08)
    max_text_w = canvas_w - margin_x * 2

    # Get product overlay region if present (set by _pass_product_overlay)
    product_region = config.get("_product_region")
    product_top = product_region["top"] if product_region else None
    product_bottom = product_region["bottom"] if product_region else None

    # ----- 1. Subheadline -----
    subheadline = text_cfg.get("subheadline")
    # Reserve space for logo at the top
    logo_visible = config.get("logo", {}).get("visible", False)
    logo_reserve = int(canvas_h * 0.095) if logo_visible else int(canvas_h * 0.06)
    subheadline_y_end = logo_reserve

    if subheadline:
        font_size = int(canvas_h * 0.025)
        font = _load_font(fonts_dir, "regular", font_size)
        y_pos = max(int(canvas_h * 0.12), logo_reserve + int(canvas_h * 0.015))

        # Center subheadline to match typical Ora ad style
        sub_bbox = font.getbbox(subheadline)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]
        sub_x = (canvas_w - sub_w) // 2

        text_color = _text_color_for_bg(img, sub_x, y_pos, sub_w, font_size * 2)
        # 70% opacity
        text_color = (text_color[0], text_color[1], text_color[2], int(255 * 0.70))

        # Subtle shadow
        shadow_color = (0, 0, 0, int(255 * 0.25))
        draw.text((sub_x + 1, y_pos + 1), subheadline, font=font, fill=shadow_color)
        draw.text((sub_x, y_pos), subheadline, font=font, fill=text_color)

        subheadline_y_end = y_pos + sub_h + int(canvas_h * 0.01)

    # ----- 2. Headline -----
    headline = text_cfg.get("headline")
    if headline:
        style = text_cfg.get("headline_style", "bold")
        font_weight = "bold"
        if style == "italic":
            font_weight = "medium"  # No italic Jost, use medium as stand-in

        # Apply uppercase if requested (before wrapping so width calc is correct)
        if style == "uppercase":
            headline = headline.upper()

        # Start with default size, shrink if the wrapped block is too tall
        font_size = int(canvas_h * 0.055)
        # Headline starts after subheadline (or after logo reserve if no subheadline)
        headline_y_start = max(int(canvas_h * 0.17), subheadline_y_end + int(canvas_h * 0.005))
        if product_top is not None:
            available_h = product_top - headline_y_start - int(canvas_h * 0.02)
            max_headline_h = max(int(canvas_h * 0.12), available_h)
        else:
            max_headline_h = int(canvas_h * 0.28)  # Max 28% of canvas for headline
        min_font_size = int(canvas_h * 0.028)

        all_lines = []
        while font_size >= min_font_size:
            font = _load_font(fonts_dir, font_weight, font_size)
            # Handle explicit line breaks
            raw_lines = headline.split("\\n") if "\\n" in headline else headline.split("\n")
            all_lines = []
            for raw_line in raw_lines:
                wrapped = _wrap_text(raw_line.strip(), font, max_text_w)
                all_lines.extend(wrapped)

            # Check total height
            line_spacing = int(font_size * 1.25)
            block_h = len(all_lines) * line_spacing

            # Check if any line is still wider than max_text_w
            max_line_w = 0
            for line in all_lines:
                bbox = font.getbbox(line)
                lw = bbox[2] - bbox[0]
                if lw > max_line_w:
                    max_line_w = lw

            if block_h <= max_headline_h and max_line_w <= max_text_w:
                break
            font_size = int(font_size * 0.9)

        font = _load_font(fonts_dir, font_weight, font_size)
        line_spacing = int(font_size * 1.25)
        y_pos = headline_y_start

        for i, line in enumerate(all_lines):
            ly = y_pos + i * line_spacing
            # Center each line individually
            line_bbox = font.getbbox(line)
            line_w = line_bbox[2] - line_bbox[0]
            line_x = (canvas_w - line_w) // 2
            text_color = _text_color_for_bg(img, line_x, ly, line_w, font_size)
            text_color = (text_color[0], text_color[1], text_color[2], 255)

            # Subtle shadow
            shadow_color = (0, 0, 0, int(255 * 0.30))
            draw.text((line_x + 1, ly + 1), line, font=font, fill=shadow_color)
            draw.text((line_x, ly), line, font=font, fill=text_color)

        # Track where headline ends for positioning subsequent elements
        headline_end_y = y_pos + len(all_lines) * line_spacing
    else:
        headline_end_y = int(canvas_h * 0.25)

    # ----- 3. Data Point (big number + label) -----
    # Skip data point if product overlay is active OR background is a photo
    # (both would cause visual collision with the data point)
    product_overlay_active = config.get("product_overlay", {}).get("enabled", False)
    bg_is_photo = config.get("background", {}).get("mode") == "photo"
    data_number = text_cfg.get("data_number")
    data_label = text_cfg.get("data_label")
    data_end_y = headline_end_y

    if data_number and not product_overlay_active and not bg_is_photo:
        number_font_size = int(canvas_h * 0.12)
        number_font = _load_font(fonts_dir, "bold", number_font_size)

        label_font_size = int(canvas_h * 0.025)
        label_font = _load_font(fonts_dir, "regular", label_font_size)

        y_pos = headline_end_y + int(canvas_h * 0.03)

        # Measure the number width for positioning the label beside it
        num_bbox = number_font.getbbox(data_number)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]

        # Center the data point block horizontally
        if data_label:
            # Wrap label text to fit remaining space
            label_max_w = max_text_w - num_w - int(canvas_w * 0.03)
            label_lines = _wrap_text(data_label, label_font, max(label_max_w, int(canvas_w * 0.3)))
        else:
            label_lines = []

        # Position number
        block_x = margin_x
        text_color = _text_color_for_bg(img, block_x, y_pos, num_w, num_h)
        text_color = (text_color[0], text_color[1], text_color[2], 255)

        shadow_color = (0, 0, 0, int(255 * 0.30))
        draw.text((block_x + 1, y_pos + 1), data_number, font=number_font, fill=shadow_color)
        draw.text((block_x, y_pos), data_number, font=number_font, fill=text_color)

        # Position label to the right of the number, vertically centered
        if label_lines:
            label_x = block_x + num_w + int(canvas_w * 0.02)
            total_label_h = len(label_lines) * int(label_font_size * 1.3)
            label_start_y = y_pos + (num_h - total_label_h) // 2 + int(num_h * 0.15)

            label_color = _text_color_for_bg(img, label_x, label_start_y, label_max_w, total_label_h)
            label_color = (label_color[0], label_color[1], label_color[2], int(255 * 0.85))

            for j, lline in enumerate(label_lines):
                ly = label_start_y + j * int(label_font_size * 1.3)
                shadow_c = (0, 0, 0, int(255 * 0.25))
                draw.text((label_x + 1, ly + 1), lline, font=label_font, fill=shadow_c)
                draw.text((label_x, ly), lline, font=label_font, fill=label_color)

        data_end_y = y_pos + num_h + int(canvas_h * 0.02)

    # ----- 4. CTA Button -----
    cta_text = text_cfg.get("cta")
    cta_end_y = data_end_y

    if cta_text:
        cta_font_size = int(canvas_h * 0.028)
        cta_font = _load_font(fonts_dir, "semibold", cta_font_size)

        cta_color_hex = text_cfg.get("cta_color", "#E8A838")
        cta_bg_color = _hex_rgba(cta_color_hex, 255)

        # Measure CTA text
        cta_bbox = cta_font.getbbox(cta_text)
        cta_text_w = cta_bbox[2] - cta_bbox[0]
        cta_text_h = cta_bbox[3] - cta_bbox[1]

        # Button dimensions with padding
        btn_pad_x = int(canvas_w * 0.06)
        btn_pad_y = int(canvas_h * 0.015)
        btn_w = cta_text_w + btn_pad_x * 2
        btn_h = cta_text_h + btn_pad_y * 2

        # Position: centered horizontally
        trust_bar_visible = config.get("trust_bar", {}).get("visible", False)
        bg_is_photo = config.get("background", {}).get("mode") == "photo"
        has_price_el = bool(text_cfg.get("price"))
        has_ts_el = bool(text_cfg.get("trust_signal"))

        if product_bottom is not None:
            # Product overlay exists → place CTA below the product
            btn_y = product_bottom + int(canvas_h * 0.025)
            max_btn_y = canvas_h - btn_h - (int(canvas_h * 0.10) if trust_bar_visible else int(canvas_h * 0.04))
            if btn_y > max_btn_y:
                btn_y = max_btn_y
        elif bg_is_photo:
            # Full-bleed photo background → place CTA near the bottom
            # Reserve extra space if price/trust signal are below the CTA
            extra_space = 0
            if has_price_el:
                extra_space += int(canvas_h * 0.05)
            if has_ts_el:
                extra_space += int(canvas_h * 0.035)
            if trust_bar_visible:
                btn_y = canvas_h - btn_h - int(canvas_h * 0.10) - extra_space
            else:
                btn_y = canvas_h - btn_h - int(canvas_h * 0.06) - extra_space
        else:
            btn_y = int(canvas_h * 0.67)
            if data_end_y > btn_y - btn_h:
                btn_y = data_end_y + int(canvas_h * 0.04)

        btn_x = (canvas_w - btn_w) // 2

        # Determine text color on CTA button
        cta_bg_brightness = _brightness(_hex(cta_color_hex))
        if cta_bg_brightness > 150:
            cta_text_color = (26, 26, 46, 255)  # Dark text
        else:
            cta_text_color = (255, 255, 255, 255)  # White text

        # Draw pill-shaped button
        pill_radius = btn_h // 2
        draw.rounded_rectangle(
            [(btn_x, btn_y), (btn_x + btn_w, btn_y + btn_h)],
            radius=pill_radius,
            fill=cta_bg_color
        )

        # Draw CTA text centered in button
        text_x = btn_x + (btn_w - cta_text_w) // 2
        text_y = btn_y + (btn_h - cta_text_h) // 2 - int(cta_bbox[1] * 0.5)
        draw.text((text_x, text_y), cta_text, font=cta_font, fill=cta_text_color)

        cta_end_y = btn_y + btn_h

    # ----- 5. Price -----
    price = text_cfg.get("price")
    price_end_y = cta_end_y
    if price:
        price_font_size = int(canvas_h * 0.032)
        price_font = _load_font(fonts_dir, "bold", price_font_size)

        price_y = cta_end_y + int(canvas_h * 0.02)

        # Center horizontally
        price_bbox = price_font.getbbox(price)
        price_w = price_bbox[2] - price_bbox[0]
        price_h = price_bbox[3] - price_bbox[1]
        price_x = (canvas_w - price_w) // 2

        text_color = _text_color_for_bg(img, price_x, price_y, price_w, price_font_size)
        text_color = (text_color[0], text_color[1], text_color[2], 255)

        shadow_c = (0, 0, 0, int(255 * 0.30))
        draw.text((price_x + 1, price_y + 1), price, font=price_font, fill=shadow_c)
        draw.text((price_x, price_y), price, font=price_font, fill=text_color)

        price_end_y = price_y + price_h

    # ----- 6. Trust Signal -----
    trust_signal = text_cfg.get("trust_signal")
    if trust_signal:
        ts_font_size = int(canvas_h * 0.018)
        ts_font = _load_font(fonts_dir, "regular", ts_font_size)

        # If trust bar is visible, move trust signal higher to avoid overlap
        trust_bar_visible = config.get("trust_bar", {}).get("visible", False)
        if trust_bar_visible:
            ts_y = int(canvas_h * 0.82)
        else:
            ts_y = int(canvas_h * 0.88)

        # If price/CTA was pushed down by product, place trust signal below
        if price_end_y > ts_y - ts_font_size:
            ts_y = price_end_y + int(canvas_h * 0.015)
            # Don't go into trust bar
            if trust_bar_visible and ts_y > canvas_h - int(canvas_h * 0.09):
                ts_y = canvas_h - int(canvas_h * 0.10)

        # Center horizontally
        ts_bbox = ts_font.getbbox(trust_signal)
        ts_w = ts_bbox[2] - ts_bbox[0]
        ts_x = (canvas_w - ts_w) // 2

        text_color = _text_color_for_bg(img, ts_x, ts_y, ts_w, ts_font_size)
        text_color = (text_color[0], text_color[1], text_color[2], int(255 * 0.80))

        shadow_c = (0, 0, 0, int(255 * 0.25))
        draw.text((ts_x + 1, ts_y + 1), trust_signal, font=ts_font, fill=shadow_c)
        draw.text((ts_x, ts_y), trust_signal, font=ts_font, fill=text_color)

    # Composite the text layer onto the main image
    img = Image.alpha_composite(img, text_layer)
    return img


# ---------------------------------------------------------------------------
# Pass 5: Brand Elements (Logo + Trust Bar)
# ---------------------------------------------------------------------------

def _pass_brand_elements(img: Image.Image, config: dict, project_root: str) -> Image.Image:
    """Render logo and trust bar onto the canvas.

    Logo: Automatically selects dark or white variant based on background
          brightness at the logo position.

    Trust Bar: Full-width semi-transparent dark strip at the very bottom
               with 4 evenly-spaced items and subtle separators.
    """
    canvas_w, canvas_h = img.size
    branding_dir = os.path.join(project_root, "branding")
    fonts_dir = os.path.join(branding_dir, "fonts")

    # ----- Logo -----
    logo_cfg = config.get("logo", {})
    if logo_cfg.get("visible", False):
        logo_dark_path = os.path.join(branding_dir, "logo_dark.png")
        logo_white_path = os.path.join(branding_dir, "logo_white.png")

        if os.path.exists(logo_dark_path):
            logo_scale = 0.18
            margin_x = int(canvas_w * 0.04)
            margin_y = int(canvas_h * 0.03)

            # Load temporary to get aspect ratio
            logo_tmp = Image.open(logo_dark_path).convert("RGBA")
            logo_ratio = logo_tmp.height / logo_tmp.width
            logo_w = int(canvas_w * logo_scale)
            logo_h = int(logo_w * logo_ratio)

            # Calculate position
            position = logo_cfg.get("position", "top_center")
            pos_map = {
                "top_left":      (margin_x, margin_y),
                "top_center":    ((canvas_w - logo_w) // 2, margin_y),
                "top_right":     (canvas_w - logo_w - margin_x, margin_y),
                "bottom_center": ((canvas_w - logo_w) // 2, canvas_h - logo_h - margin_y),
                "bottom_right":  (canvas_w - logo_w - margin_x, canvas_h - logo_h - margin_y),
            }
            lx, ly = pos_map.get(position, pos_map["top_center"])

            # Auto-detect logo variant based on background brightness
            brightness = _region_brightness(img, lx, ly, logo_w, logo_h)
            if brightness > 160:
                chosen_path = logo_dark_path
            else:
                chosen_path = logo_white_path if os.path.exists(logo_white_path) else logo_dark_path

            logo = Image.open(chosen_path).convert("RGBA")
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            img.paste(logo, (lx, ly), logo)
        else:
            print(f"  Warning: Logo not found at {logo_dark_path}")

    # ----- Trust Bar -----
    trust_cfg = config.get("trust_bar", {})
    if trust_cfg.get("visible", False):
        items = trust_cfg.get("items", [
            "Kostenlose Lieferung", "200 Nächte testen",
            "10 Jahre Garantie", "Swiss Made"
        ])

        bar_height = int(canvas_h * 0.07)
        bar_y = canvas_h - bar_height

        # Semi-transparent black background (fully opaque for readability)
        bar_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        bar_draw = ImageDraw.Draw(bar_layer)
        bar_draw.rectangle(
            [(0, bar_y), (canvas_w, canvas_h)],
            fill=(0, 0, 0, 220)
        )

        # Determine font size — try to fit all items
        col_width = canvas_w // len(items)
        max_item_w = int(col_width * 0.90)

        # Start with default font size and shrink if needed
        font_size = int(bar_height * 0.30)
        min_font_size = int(bar_height * 0.20)

        def _fits(display_items, font):
            for item in display_items:
                bbox = font.getbbox(item)
                if (bbox[2] - bbox[0]) > max_item_w:
                    return False
            return True

        def _shorten_item(item):
            """Apply progressive shortening: Full → Short → Shorter."""
            short = TRUST_SHORT.get(item, item)
            # Apply shortening chain (max 2 levels)
            shorter = TRUST_SHORT.get(short, short)
            return shorter

        # Start with original items
        display_items = list(items)
        font = _load_font(fonts_dir, "regular", font_size)

        # Step 1: Try with original items
        if not _fits(display_items, font):
            # Step 2: Apply short labels
            display_items = [_shorten_item(item) for item in items]

        # Step 3: Shrink font until it fits (down to minimum)
        while not _fits(display_items, font) and font_size > min_font_size:
            font_size = int(font_size * 0.92)
            font = _load_font(fonts_dir, "regular", font_size)

        # Step 4: If still doesn't fit, truncate text with ellipsis
        for idx, item in enumerate(display_items):
            bbox = font.getbbox(item)
            while (bbox[2] - bbox[0]) > max_item_w and len(item) > 3:
                item = item[:-1]
                bbox = font.getbbox(item + "…")
            if item != display_items[idx]:
                display_items[idx] = item.rstrip() + "…" if item != display_items[idx] else item

        # Render items evenly spaced
        text_color = (255, 255, 255, int(255 * 0.80))
        separator_color = (255, 255, 255, int(255 * 0.25))

        for i, item in enumerate(display_items):
            # Calculate horizontal center of this column
            col_center_x = int((i + 0.5) * col_width)
            bbox = font.getbbox(item)
            item_w = bbox[2] - bbox[0]
            item_h = bbox[3] - bbox[1]
            text_x = col_center_x - item_w // 2
            text_y = bar_y + (bar_height - item_h) // 2 - int(bbox[1] * 0.5)

            bar_draw.text((text_x, text_y), item, font=font, fill=text_color)

            # Draw 1px separator line between columns (not after the last)
            if i < len(display_items) - 1:
                sep_x = (i + 1) * col_width
                bar_draw.line(
                    [(sep_x, bar_y + int(bar_height * 0.2)),
                     (sep_x, bar_y + int(bar_height * 0.8))],
                    fill=separator_color,
                    width=1
                )

        img = Image.alpha_composite(img, bar_layer)

    return img


# ---------------------------------------------------------------------------
# Main Pipeline Entry Point
# ---------------------------------------------------------------------------

def run_pipeline(config: dict, project_root: str) -> bytes:
    """Run the full 5-pass creative production pipeline.

    Args:
        config:       Pipeline configuration dict (see module docstring for schema).
        project_root: Absolute path to the creative generator project root.

    Returns:
        Final composited image as PNG bytes.
    """
    fmt = config.get("format", "4:5")
    canvas_w, canvas_h = FORMAT_SIZES.get(fmt, FORMAT_SIZES["4:5"])
    print(f"Pipeline: {fmt} ({canvas_w}x{canvas_h})")

    # Pass 1: Background
    print("  Pass 1: Background...")
    img = _pass_background(config, project_root)

    # Pass 2: Product Photo Overlay
    print("  Pass 2: Product overlay...")
    img = _pass_product_overlay(img, config, project_root)

    # Pass 3: Gradient Overlay
    print("  Pass 3: Gradient overlay...")
    img = _pass_gradient_overlay(img, config)

    # Pass 4: Typography
    print("  Pass 4: Typography...")
    img = _pass_typography(img, config, project_root)

    # Pass 5: Brand Elements
    print("  Pass 5: Brand elements...")
    img = _pass_brand_elements(img, config, project_root)

    # Export as PNG bytes
    print("  Exporting PNG...")
    buf = io.BytesIO()
    # Flatten RGBA to RGB for final output (no transparency needed in ads)
    final = Image.new("RGB", img.size, (255, 255, 255))
    final.paste(img, mask=img.split()[3])
    final.save(buf, format="PNG", optimize=True)

    png_bytes = buf.getvalue()
    print(f"  Done: {len(png_bytes) / 1024:.0f} KB")
    return png_bytes


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Generate a test creative with a hardcoded config and save to disk."""

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

    test_config = {
        "format": "4:5",
        "background": {
            "mode": "gradient",
            "color": "#2D3748",
            "gradient_to": "#1A202C",
            "gradient_direction": "top_to_bottom",
        },
        "product_overlay": {
            "enabled": True,
            "image_path": "products/images/ora-ultra-matratze/0.jpg",
            "position": "center",
            "scale": 0.65,
            "mask": "rounded_rect",
            "shadow": True,
        },
        "gradient_overlay": {
            "enabled": True,
            "type": "both",
            "opacity": 0.5,
        },
        "text": {
            "subheadline": "Das sagen unsere Kunden.",
            "headline": "Schlaf, der dein\nLeben verändert.",
            "headline_style": "bold",
            "data_number": "93%",
            "data_label": "unserer Kunden spüren mehr Energie",
            "cta": "Jetzt entdecken",
            "cta_color": "#E8A838",
            "price": "ab CHF 899",
            "trust_signal": "Swiss Made | Testsieger 2026",
        },
        "logo": {
            "visible": True,
            "position": "top_center",
        },
        "trust_bar": {
            "visible": True,
            "items": [
                "Kostenlose Lieferung",
                "200 Nächte testen",
                "10 Jahre Garantie",
                "Swiss Made",
            ],
        },
    }

    print("=" * 60)
    print("Pipeline Test — Ora Sleep Creative Generator")
    print("=" * 60)

    result_bytes = run_pipeline(test_config, PROJECT_ROOT)

    output_path = os.path.join(PROJECT_ROOT, "test_pipeline_output.png")
    with open(output_path, "wb") as f:
        f.write(result_bytes)

    print(f"\nSaved test output: {output_path}")
    print(f"File size: {len(result_bytes) / 1024:.1f} KB")
