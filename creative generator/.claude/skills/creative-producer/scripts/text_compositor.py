#!/usr/bin/env python3
"""Text Compositor — Renders text overlays onto Gemini-generated images via PIL.

Gemini generates ONLY the background/scene/product (no text). This module then
composites all text elements (headlines, CTAs, prices, badges, etc.) as crisp,
programmatically-rendered layers using Pillow.

Usage:
    from text_compositor import composite_text
    final_bytes = composite_text(image_bytes, ad_prompt)
"""

import io
import math
import os
import textwrap
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
FONTS_DIR = os.path.join(PROJECT_ROOT, "branding", "fonts")

# ---------------------------------------------------------------------------
# Font mapping
# ---------------------------------------------------------------------------

FONT_MAP = {
    "sans": "Jost-Regular.ttf",
    "sans_regular": "Jost-Regular.ttf",
    "sans_medium": "Jost-Medium.ttf",
    "sans_semibold": "Jost-SemiBold.ttf",
    "sans_bold": "Jost-Bold.ttf",
    "regular": "Jost-Regular.ttf",
    "medium": "Jost-Medium.ttf",
    "semibold": "Jost-SemiBold.ttf",
    "bold": "Jost-Bold.ttf",
}

# Weight-based fallback when font_family doesn't match but font_weight does
WEIGHT_MAP = {
    "regular": "Jost-Regular.ttf",
    "normal": "Jost-Regular.ttf",
    "medium": "Jost-Medium.ttf",
    "semibold": "Jost-SemiBold.ttf",
    "bold": "Jost-Bold.ttf",
    "extra_bold": "Jost-Bold.ttf",
}

# ---------------------------------------------------------------------------
# Font size presets (relative to canvas height)
# ---------------------------------------------------------------------------

SIZE_PRESETS = {
    "xs": 0.018,
    "sm": 0.024,
    "md": 0.032,
    "lg": 0.042,
    "xl": 0.055,
    "xxl": 0.070,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def _resolve_font(font_family: str, font_weight: str, font_size_px: int) -> ImageFont.FreeTypeFont:
    """Resolve font family + weight to a loaded PIL font object."""
    # Try font_family directly
    filename = FONT_MAP.get(font_family)
    # Fallback to weight
    if not filename:
        filename = WEIGHT_MAP.get(font_weight, "Jost-Regular.ttf")

    cache_key = (filename, font_size_px)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font_path = os.path.join(FONTS_DIR, filename)
    if not os.path.exists(font_path):
        # Ultimate fallback
        font_path = os.path.join(FONTS_DIR, "Jost-Regular.ttf")

    try:
        font = ImageFont.truetype(font_path, font_size_px)
    except Exception:
        font = ImageFont.load_default()

    _font_cache[cache_key] = font
    return font


def _compute_font_size_px(size_key: str, canvas_height: int) -> int:
    """Convert a size preset string to pixel size relative to canvas."""
    ratio = SIZE_PRESETS.get(size_key, SIZE_PRESETS["md"])
    return max(16, int(canvas_height * ratio))


def _get_region_brightness(img: Image.Image, x: int, y: int, w: int, h: int) -> float:
    """Average perceived brightness (0-255) of a region."""
    x = max(0, x)
    y = max(0, y)
    w = min(w, img.width - x)
    h = min(h, img.height - y)
    if w <= 0 or h <= 0:
        return 128.0
    region = img.crop((x, y, x + w, y + h)).convert("RGB")
    pixels = list(region.getdata())
    if not pixels:
        return 128.0
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)
    return 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b


def _auto_text_color(img: Image.Image, x: int, y: int, w: int, h: int) -> str:
    """Return white or dark text color based on background brightness."""
    brightness = _get_region_brightness(img, x, y, w, h)
    return "#FFFFFF" if brightness < 140 else "#1A1A2E"


def _parse_color(color_str: str) -> Tuple[int, int, int, int]:
    """Parse hex color string to RGBA tuple."""
    if not color_str:
        return (255, 255, 255, 255)
    color_str = color_str.strip().lstrip("#")
    if len(color_str) == 6:
        r, g, b = int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)
        return (r, g, b, 255)
    elif len(color_str) == 8:
        r, g, b, a = (
            int(color_str[0:2], 16),
            int(color_str[2:4], 16),
            int(color_str[4:6], 16),
            int(color_str[6:8], 16),
        )
        return (r, g, b, a)
    return (255, 255, 255, 255)


def _apply_text_transform(text: str, transform: str) -> str:
    """Apply CSS-like text transforms."""
    if transform == "uppercase":
        return text.upper()
    elif transform == "lowercase":
        return text.lower()
    elif transform == "capitalize":
        return text.title()
    return text


def _word_wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = words[0]

    for word in words[1:]:
        test_line = current_line + " " + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def _resolve_y_position(y_key: str, canvas_h: int, block_h: int, margin_y: int) -> int:
    """Convert named vertical position to pixel y coordinate."""
    positions = {
        "top": margin_y,
        "upper_third": int(canvas_h * 0.12),
        "upper_quarter": int(canvas_h * 0.10),
        "center": (canvas_h - block_h) // 2,
        "lower_third": int(canvas_h * 0.62),
        "lower_quarter": int(canvas_h * 0.70),
        "bottom": canvas_h - block_h - margin_y,
        "bottom_safe": canvas_h - block_h - int(margin_y * 2.5),
    }
    if isinstance(y_key, (int, float)):
        return int(y_key)
    return positions.get(y_key, positions["center"])


def _resolve_x_position(x_key: str, canvas_w: int, block_w: int, margin_x: int) -> int:
    """Convert named horizontal position to pixel x coordinate."""
    positions = {
        "left": margin_x,
        "center": (canvas_w - block_w) // 2,
        "right": canvas_w - block_w - margin_x,
    }
    if isinstance(x_key, (int, float)):
        return int(x_key)
    return positions.get(x_key, positions["center"])


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    shadow_offset: int = 1,
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 40),
    stroke_width: int = 0,
    stroke_fill: Optional[Tuple[int, int, int, int]] = None,
):
    """Draw text with subtle shadow and optional stroke for readability."""
    x, y = position
    # Shadow
    if shadow_offset > 0:
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=shadow_color,
        )
    # Stroke (outline) for extra contrast on busy backgrounds
    if stroke_width > 0 and stroke_fill:
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
    else:
        draw.text((x, y), text, font=font, fill=fill)


def _draw_rounded_rect(
    draw: ImageDraw.Draw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, int, int, int],
):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    radius = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


# ---------------------------------------------------------------------------
# Overlay renderers  (one per role)
# ---------------------------------------------------------------------------

def _render_headline(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
) -> int:
    """Render headline text. Returns y_end (bottom of rendered block)."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")
    transform = style.get("text_transform", "none")
    content = _apply_text_transform(content, transform)

    size_key = style.get("font_size", "xl")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_bold"),
        style.get("font_weight", "bold"),
        font_px,
    )

    max_text_w = canvas_w - margin_x * 2
    lines = _word_wrap(content, font, max_text_w, draw)

    # Auto-shrink if headline takes up too much vertical space (max ~35% of canvas)
    max_headline_h = int(canvas_h * 0.35)
    line_height = int(font_px * 1.25)
    block_h = line_height * len(lines)
    while block_h > max_headline_h and font_px > 24:
        font_px = int(font_px * 0.85)
        font = _resolve_font(
            style.get("font_family", "sans_bold"),
            style.get("font_weight", "bold"),
            font_px,
        )
        lines = _word_wrap(content, font, max_text_w, draw)
        line_height = int(font_px * 1.25)
        block_h = line_height * len(lines)

    y_start = _resolve_y_position(pos.get("y", "upper_third"), canvas_h, block_h, margin_y)
    # Push headline down if logo is occupying the top
    logo_offset = pos.get("_logo_offset", 0)
    if logo_offset > 0:
        y_start = max(y_start, logo_offset)
    align = style.get("text_align", "center")

    # Determine color
    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        fill = _parse_color(color_str)
    else:
        fill = _parse_color(_auto_text_color(img, margin_x, y_start, max_text_w, block_h))

    shadow_offset = max(1, font_px // 60)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        if align == "center":
            lx = (canvas_w - line_w) // 2
        elif align == "right":
            lx = canvas_w - line_w - margin_x
        else:
            lx = margin_x
        ly = y_start + i * line_height

        _draw_text_with_shadow(
            draw, (lx, ly), line, font, fill,
            shadow_offset=shadow_offset,
            shadow_color=(0, 0, 0, 35),
            stroke_width=0,
            stroke_fill=None,
        )

    return y_start + block_h


def _render_subheadline(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render subheadline. Supports above_headline positioning or auto-stacks below."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")
    transform = style.get("text_transform", "none")
    content = _apply_text_transform(content, transform)

    size_key = style.get("font_size", "md")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_medium"),
        style.get("font_weight", "medium"),
        font_px,
    )

    max_text_w = canvas_w - margin_x * 2
    lines = _word_wrap(content, font, max_text_w, draw)
    line_height = int(font_px * 1.3)
    block_h = line_height * len(lines)

    # Check if subheadline should render ABOVE the headline
    above_headline = pos.get("above_headline", False)
    y_key = pos.get("y", None)

    if above_headline or y_key == "upper_quarter":
        # Position above the headline area, but below logo if present
        # Logo reserve is ~10% so subheadline starts at 10%
        y_start = int(canvas_h * 0.10)
    elif y_key:
        y_start = _resolve_y_position(y_key, canvas_h, block_h, margin_y)
    else:
        # Auto-position below previous element
        y_start = prev_y_end + int(canvas_h * 0.02)

    align = style.get("text_align", "center")

    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        fill = _parse_color(color_str)
    else:
        fill = _parse_color(_auto_text_color(img, margin_x, y_start, max_text_w, block_h))

    shadow_offset = max(1, font_px // 60)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        if align == "center":
            lx = (canvas_w - line_w) // 2
        elif align == "right":
            lx = canvas_w - line_w - margin_x
        else:
            lx = margin_x
        ly = y_start + i * line_height

        _draw_text_with_shadow(
            draw, (lx, ly), line, font, fill,
            shadow_offset=shadow_offset,
            shadow_color=(0, 0, 0, 30),
            stroke_width=0,
            stroke_fill=None,
        )

    return y_start + block_h


def _render_cta(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render CTA button (rounded rect + centered text)."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")
    transform = style.get("text_transform", "uppercase")
    content = _apply_text_transform(content, transform)

    size_key = style.get("font_size", "md")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_bold"),
        style.get("font_weight", "bold"),
        font_px,
    )

    # Measure text
    bbox = draw.textbbox((0, 0), content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x = int(font_px * 1.8)
    pad_y = int(font_px * 0.7)
    btn_w = text_w + pad_x * 2
    btn_h = text_h + pad_y * 2
    btn_radius = btn_h // 2  # Pill shape

    y_key = pos.get("y", None)
    if y_key:
        btn_y = _resolve_y_position(y_key, canvas_h, btn_h, margin_y)
    else:
        btn_y = prev_y_end + int(canvas_h * 0.03)

    x_key = pos.get("x", "center")
    btn_x = _resolve_x_position(x_key, canvas_w, btn_w, margin_x)

    # Button background color — default to Ora Sleep warm gold/orange
    bg_color_str = style.get("background_color", "")
    if bg_color_str and bg_color_str.lower() != "auto":
        bg_fill = _parse_color(bg_color_str)
    else:
        # Default to Ora Sleep warm gold/orange CTA
        bg_fill = (232, 168, 56, 240)  # #E8A838

    # Check if button bg has enough contrast with image bg — if not, flip
    img_brightness = _get_region_brightness(img, btn_x, btn_y, btn_w, btn_h)
    bg_brightness = 0.299 * bg_fill[0] + 0.587 * bg_fill[1] + 0.114 * bg_fill[2]
    contrast = abs(img_brightness - bg_brightness)
    if contrast < 60:
        # Not enough contrast — flip the button color
        bg_fill = (255, 255, 255, 240) if bg_brightness < 140 else (232, 168, 56, 240)
        bg_brightness = 0.299 * bg_fill[0] + 0.587 * bg_fill[1] + 0.114 * bg_fill[2]

    # Text color — dark text on gold/bright button, white on dark button
    text_fill = (255, 255, 255, 255) if bg_brightness < 140 else (26, 26, 46, 255)

    # Draw button
    _draw_rounded_rect(draw, (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), btn_radius, bg_fill)

    # Center text inside button
    text_x = btn_x + (btn_w - text_w) // 2
    text_y = btn_y + (btn_h - text_h) // 2 - int(font_px * 0.05)  # slight optical lift
    draw.text((text_x, text_y), content, font=font, fill=text_fill)

    return btn_y + btn_h


def _render_price(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render price display with CHF formatting."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")

    # Ensure CHF prefix if not present and content looks like a number
    if content and not content.startswith("CHF") and not content.startswith("ab "):
        try:
            float(content.replace("'", "").replace(",", "."))
            content = f"CHF {content}"
        except ValueError:
            pass

    size_key = style.get("font_size", "lg")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_bold"),
        style.get("font_weight", "bold"),
        font_px,
    )

    bbox = draw.textbbox((0, 0), content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    y_key = pos.get("y", None)
    if y_key:
        ty = _resolve_y_position(y_key, canvas_h, text_h, margin_y)
    else:
        ty = prev_y_end + int(canvas_h * 0.02)

    x_key = pos.get("x", "center")
    tx = _resolve_x_position(x_key, canvas_w, text_w, margin_x)

    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        fill = _parse_color(color_str)
    else:
        fill = _parse_color(_auto_text_color(img, tx, ty, text_w, text_h))

    shadow_offset = max(1, font_px // 60)

    _draw_text_with_shadow(
        draw, (tx, ty), content, font, fill,
        shadow_offset=shadow_offset,
        shadow_color=(0, 0, 0, 40),
        stroke_width=0,
        stroke_fill=None,
    )

    return ty + text_h


def _render_badge(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    badge_index: int = 0,
    prev_y_end: int = 0,
) -> int:
    """Render a pill-shaped badge (e.g. 'Testsieger 2026', 'Swiss Made')."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")
    transform = style.get("text_transform", "uppercase")
    content = _apply_text_transform(content, transform)

    size_key = style.get("font_size", "sm")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_semibold"),
        style.get("font_weight", "semibold"),
        font_px,
    )

    bbox = draw.textbbox((0, 0), content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x = int(font_px * 1.2)
    pad_y = int(font_px * 0.45)
    pill_w = text_w + pad_x * 2
    pill_h = text_h + pad_y * 2
    pill_radius = pill_h // 2

    # Stack multiple badges horizontally with spacing
    y_key = pos.get("y", None)
    if y_key:
        pill_y = _resolve_y_position(y_key, canvas_h, pill_h, margin_y)
    else:
        pill_y = prev_y_end + int(canvas_h * 0.02)

    x_key = pos.get("x", "center")
    pill_x = _resolve_x_position(x_key, canvas_w, pill_w, margin_x)

    # Badge background
    bg_color_str = style.get("background_color", "")
    if bg_color_str:
        bg_fill = _parse_color(bg_color_str)
    else:
        # Semi-transparent dark pill by default
        bg_brightness = _get_region_brightness(img, pill_x, pill_y, pill_w, pill_h)
        if bg_brightness < 140:
            bg_fill = (255, 255, 255, 50)
        else:
            bg_fill = (26, 26, 46, 180)

    _draw_rounded_rect(draw, (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h), pill_radius, bg_fill)

    # Badge text
    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        text_fill = _parse_color(color_str)
    else:
        bg_lum = 0.299 * bg_fill[0] + 0.587 * bg_fill[1] + 0.114 * bg_fill[2]
        text_fill = (255, 255, 255, 255) if bg_lum < 140 else (26, 26, 46, 255)

    text_x = pill_x + (pill_w - text_w) // 2
    text_y = pill_y + (pill_h - text_h) // 2
    draw.text((text_x, text_y), content, font=font, fill=text_fill)

    return pill_y + pill_h


def _render_trust_signals(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render small trust signal text at the bottom."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")

    size_key = style.get("font_size", "xs")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans"),
        style.get("font_weight", "regular"),
        font_px,
    )

    max_text_w = canvas_w - margin_x * 2
    lines = _word_wrap(content, font, max_text_w, draw)
    line_height = int(font_px * 1.3)
    block_h = line_height * len(lines)

    y_key = pos.get("y", "bottom_safe")
    y_start = _resolve_y_position(y_key, canvas_h, block_h, margin_y)
    align = style.get("text_align", "center")

    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        fill = _parse_color(color_str)
    else:
        fill = _parse_color(_auto_text_color(img, margin_x, y_start, max_text_w, block_h))
    # Make trust signals slightly translucent
    fill = (fill[0], fill[1], fill[2], min(fill[3], 200))

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        if align == "center":
            lx = (canvas_w - line_w) // 2
        elif align == "right":
            lx = canvas_w - line_w - margin_x
        else:
            lx = margin_x
        ly = y_start + i * line_height

        _draw_text_with_shadow(
            draw, (lx, ly), line, font, fill,
            shadow_offset=0,
            shadow_color=(0, 0, 0, 0),
            stroke_width=0,
            stroke_fill=None,
        )

    return y_start + block_h


def _render_benefit_list(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render a benefit list with checkmark bullets."""
    style = overlay.get("style", {})
    pos = overlay.get("position", {})
    content = overlay.get("content", "")

    # Content can be a string with newlines or a semicolon-separated list
    if isinstance(content, list):
        items = content
    elif "\n" in content:
        items = [line.strip() for line in content.split("\n") if line.strip()]
    elif ";" in content:
        items = [item.strip() for item in content.split(";") if item.strip()]
    else:
        items = [content]

    size_key = style.get("font_size", "sm")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans_medium"),
        style.get("font_weight", "medium"),
        font_px,
    )

    checkmark = "\u2713 "  # Unicode checkmark
    # Truncate items that are too long for the canvas
    max_item_w = canvas_w - margin_x * 2 - int(canvas_w * 0.1)
    truncated_items = []
    for item in items:
        full_text = checkmark + item
        bbox = draw.textbbox((0, 0), full_text, font=font)
        if (bbox[2] - bbox[0]) > max_item_w and len(item) > 30:
            item = item[:27] + "..."
        truncated_items.append(item)
    items = truncated_items

    # Limit to max 3 benefits to prevent overflow
    items = items[:3]

    line_height = int(font_px * 1.6)
    block_h = line_height * len(items)

    y_key = pos.get("y", None)
    if y_key:
        y_start = _resolve_y_position(y_key, canvas_h, block_h, margin_y)
    else:
        y_start = prev_y_end + int(canvas_h * 0.025)

    x_key = pos.get("x", "left")
    align = style.get("text_align", "left")

    color_str = style.get("color")
    if color_str and color_str.lower() != "auto":
        fill = _parse_color(color_str)
    else:
        fill = _parse_color(_auto_text_color(img, margin_x, y_start, canvas_w - margin_x * 2, block_h))

    shadow_offset = max(1, font_px // 60)
    is_light_text = (fill[0] + fill[1] + fill[2]) > 384

    # Draw semi-transparent background rectangle behind the entire benefit list
    bg_pad_x = int(margin_x * 0.5)
    bg_pad_y = int(font_px * 0.5)
    bg_x0 = margin_x - bg_pad_x
    bg_y0 = y_start - bg_pad_y
    bg_x1 = canvas_w - margin_x + bg_pad_x
    bg_y1 = y_start + block_h + bg_pad_y
    if is_light_text:
        bg_rect_fill = (0, 0, 0, 120)  # dark semi-transparent for light text
    else:
        bg_rect_fill = (255, 255, 255, 140)  # light semi-transparent for dark text
    _draw_rounded_rect(draw, (bg_x0, bg_y0, bg_x1, bg_y1), int(font_px * 0.4), bg_rect_fill)

    # Checkmark color — slightly accented
    check_fill = (100, 220, 120, 255) if is_light_text else (40, 160, 80, 255)

    for i, item in enumerate(items):
        item_text = checkmark + item
        ly = y_start + i * line_height

        bbox = draw.textbbox((0, 0), item_text, font=font)
        item_w = bbox[2] - bbox[0]

        if align == "center":
            lx = (canvas_w - item_w) // 2
        elif align == "right":
            lx = canvas_w - item_w - margin_x
        else:
            lx = margin_x + int(canvas_w * 0.05)

        # Draw checkmark in accent color
        check_bbox = draw.textbbox((0, 0), checkmark, font=font)
        check_w = check_bbox[2] - check_bbox[0]

        _draw_text_with_shadow(
            draw, (lx, ly), checkmark, font, check_fill,
            shadow_offset=shadow_offset,
            shadow_color=(0, 0, 0, 30),
            stroke_width=0,
            stroke_fill=None,
        )
        _draw_text_with_shadow(
            draw, (lx + check_w, ly), item, font, fill,
            shadow_offset=shadow_offset,
            shadow_color=(0, 0, 0, 30),
            stroke_width=0,
            stroke_fill=None,
        )

    return y_start + block_h


def _render_trust_bar(
    img: Image.Image,
    draw: ImageDraw.Draw,
    overlay: dict,
    canvas_w: int,
    canvas_h: int,
    margin_x: int,
    margin_y: int,
    prev_y_end: int = 0,
) -> int:
    """Render a 4-column trust bar at the very bottom of the image.

    Content should be a semicolon-separated list of trust items, e.g.:
    "Kostenlose Lieferung;200 Nächte testen;10 Jahre Garantie;Swiss Made"
    """
    style = overlay.get("style", {})
    content = overlay.get("content", "")

    # Parse items from semicolon-separated string
    if isinstance(content, list):
        items = content
    elif ";" in content:
        items = [item.strip() for item in content.split(";") if item.strip()]
    else:
        items = [content]

    size_key = style.get("font_size", "xs")
    font_px = _compute_font_size_px(size_key, canvas_h)
    font = _resolve_font(
        style.get("font_family", "sans"),
        style.get("font_weight", "regular"),
        font_px,
    )

    # Bar dimensions — full width, ~8% of canvas height at the very bottom
    bar_h = int(canvas_h * 0.08)
    bar_y = canvas_h - bar_h

    # Draw semi-transparent dark background strip
    bg_fill = (0, 0, 0, 160)
    draw.rectangle((0, bar_y, canvas_w, canvas_h), fill=bg_fill)

    # Text color — white on dark bar
    text_fill = (255, 255, 255, 220)

    # Evenly space items across the bar width
    num_items = len(items)
    if num_items == 0:
        return bar_y + bar_h

    col_w = canvas_w // num_items

    # Try emoji prefixes for each known item, fall back to plain text
    emoji_map = {
        "lieferung": "\U0001F69A ",   # truck
        "retoure": "\U0001F69A ",     # truck
        "nächte": "\U0001F319 ",      # moon
        "testen": "\U0001F319 ",      # moon
        "probeschlafen": "\U0001F319 ",
        "garantie": "\U0001F6E1\uFE0F ",  # shield
        "swiss": "\U0001F1E8\U0001F1ED ",  # Swiss flag
    }

    # Short labels for narrow formats (9:16 etc.)
    short_labels = {
        "kostenlose lieferung": "Gratis Versand",
        "kostenlose lieferung & retoure": "Gratis Versand",
        "200 nächte testen": "200 Nächte",
        "200 nächte probeschlafen": "200 Nächte",
        "10 jahre garantie": "10J Garantie",
        "swiss made": "Swiss Made",
    }

    for i, item in enumerate(items):
        display_text = item

        # Measure and shorten if too wide for column
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_w = bbox[2] - bbox[0]
        if text_w > col_w - 20:
            short = short_labels.get(item.lower(), item)
            display_text = short
            bbox = draw.textbbox((0, 0), display_text, font=font)
            text_w = bbox[2] - bbox[0]

        text_h = bbox[3] - bbox[1]
        tx = i * col_w + (col_w - text_w) // 2
        ty = bar_y + (bar_h - text_h) // 2

        draw.text((tx, ty), display_text, font=font, fill=text_fill)

    # Draw subtle separator lines between columns
    sep_fill = (255, 255, 255, 60)
    for i in range(1, num_items):
        sep_x = i * col_w
        draw.line(
            [(sep_x, bar_y + int(bar_h * 0.2)), (sep_x, bar_y + int(bar_h * 0.8))],
            fill=sep_fill,
            width=1,
        )

    return bar_y + bar_h


# ---------------------------------------------------------------------------
# Role dispatcher
# ---------------------------------------------------------------------------

ROLE_RENDERERS = {
    "headline": _render_headline,
    "subheadline": _render_subheadline,
    "cta": _render_cta,
    "price": _render_price,
    "badge": _render_badge,
    "trust_signals": _render_trust_signals,
    "trust_signal": _render_trust_signals,
    "benefit_list": _render_benefit_list,
    "benefits": _render_benefit_list,
    "trust_bar": _render_trust_bar,
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def composite_text(image_bytes: bytes, ad_prompt: dict) -> bytes:
    """Takes raw Gemini image + ad prompt JSON, returns image with text overlaid.

    Args:
        image_bytes: PNG/JPEG image bytes from Gemini (no text on it).
        ad_prompt: The full ad prompt dict containing ``text_overlays`` list.

    Returns:
        PNG image bytes with all text overlays composited.
    """
    if not HAS_PIL:
        print("  Warning: PIL not installed, skipping text compositing")
        return image_bytes

    overlays = ad_prompt.get("text_overlays", [])
    if not overlays:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        print(f"  Warning: Could not open image for text compositing: {e}")
        return image_bytes

    canvas_w, canvas_h = img.size

    # Create a transparent overlay layer for text (allows alpha blending)
    text_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    margin_x = int(canvas_w * 0.06)
    margin_y = int(canvas_h * 0.04)

    # Check if logo is visible — if so, reserve space at the top
    logo_visible = ad_prompt.get("brand_elements", {}).get("logo", {}).get("visible", False)
    logo_reserve_y = int(canvas_h * 0.10) if logo_visible else 0

    # Calculate total overlay height to detect overflow
    # Count non-trust-signal overlays to limit stacking
    main_overlays = [o for o in overlays if o.get("role", "").lower() not in ("trust_signals", "trust_signal", "trust_bar", "subheadline")]
    max_main_overlays = 3  # headline + max 2 more (CTA, price OR benefits — not all)
    if len(main_overlays) > max_main_overlays:
        # Keep headline, CTA, and one of price/benefits — drop the rest
        kept = []
        has_headline = False
        has_cta = False
        has_extra = False
        for o in overlays:
            role = o.get("role", "").lower()
            if role == "headline" and not has_headline:
                kept.append(o)
                has_headline = True
            elif role == "cta" and not has_cta:
                kept.append(o)
                has_cta = True
            elif role in ("price",) and not has_extra:
                kept.append(o)
                has_extra = True
            elif role in ("trust_signals", "trust_signal", "trust_bar", "subheadline"):
                kept.append(o)
        overlays = kept

    # Track vertical cursor for auto-stacking overlays
    prev_y_end = logo_reserve_y
    badge_index = 0
    overlay_count = 0

    for overlay in overlays:
        role = overlay.get("role", "").lower().strip()
        renderer = ROLE_RENDERERS.get(role)

        if not renderer:
            print(f"  Warning: Unknown text overlay role '{role}', skipping")
            continue

        try:
            if role == "badge":
                prev_y_end = renderer(
                    img, draw, overlay, canvas_w, canvas_h,
                    margin_x, margin_y,
                    badge_index=badge_index,
                    prev_y_end=prev_y_end,
                )
                badge_index += 1
            elif role == "headline":
                # Offset headline down if logo is taking top space
                if logo_reserve_y > 0:
                    pos = overlay.get("position", {})
                    y_key = pos.get("y", "upper_third")
                    if y_key in ("upper_third", "upper_quarter", "top"):
                        overlay = dict(overlay)
                        overlay["position"] = dict(pos)
                        overlay["position"]["_logo_offset"] = logo_reserve_y
                prev_y_end = renderer(
                    img, draw, overlay, canvas_w, canvas_h,
                    margin_x, margin_y,
                )
            else:
                prev_y_end = renderer(
                    img, draw, overlay, canvas_w, canvas_h,
                    margin_x, margin_y,
                    prev_y_end=prev_y_end,
                )
            overlay_count += 1
        except Exception as e:
            print(f"  Warning: Failed to render '{role}' overlay: {e}")
            continue

    # Composite text layer onto original image
    img = Image.alpha_composite(img, text_layer)

    # Export as PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    print(f"  Text composited: {overlay_count} overlay(s) on {canvas_w}x{canvas_h} canvas")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CLI test helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json
    import sys as _sys

    if len(_sys.argv) < 3:
        print("Usage: python text_compositor.py <image_path> <prompt_json_path> [output_path]")
        print("  Composites text overlays onto an image for testing.")
        _sys.exit(1)

    img_path = _sys.argv[1]
    prompt_path = _sys.argv[2]
    out_path = _sys.argv[3] if len(_sys.argv) > 3 else "composited_output.png"

    with open(img_path, "rb") as f:
        raw_bytes = f.read()
    with open(prompt_path, "r") as f:
        prompt_data = _json.load(f)

    result = composite_text(raw_bytes, prompt_data)
    with open(out_path, "wb") as f:
        f.write(result)
    print(f"Output saved to: {out_path}")
