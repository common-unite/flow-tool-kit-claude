"""Colour contrast as WCAG 2 measures it, and the nearest shade of a colour that passes.

    import contrast
    contrast.ratio("#2e844a", "#ffffff")         # 4.65
    contrast.darken_to("#7fc8a9")                # the same hue, darkened until it reaches 4.5:1 on white
    contrast.nearest_passing("#f2c14e", "#ffffff", contrast.LARGE_TEXT)

WCAG AA asks 4.5:1 for body text and the text on a button (BODY_TEXT), and 3:1 for large text: 24px, or 18.66px bold
(LARGE_TEXT). brand-kit darkens a brand colour to 4.5:1 with ``darken_to``; form-design reports each colour pair of a
plan with ``ratio`` and suggests ``nearest_passing``. Python 3 standard library only.
"""
from __future__ import annotations

import colorsys
import re

BODY_TEXT = 4.5   # WCAG AA, body text and button text
LARGE_TEXT = 3.0  # WCAG AA, large text (24px, or 18.66px bold)
MIN_CONTRAST = BODY_TEXT
HEXCOLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex(value) -> str:
    """#abc, abc, #aabbcc or aabbcc as #aabbcc; ValueError for anything else."""
    value = (value or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", value):
        value = "#" + "".join(c * 2 for c in value.lstrip("#"))
    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        value = "#" + value
    if not HEXCOLOR.match(value):
        raise ValueError(f"not a color: {value!r} (use #rrggbb)")
    return value.lower()


def is_color(value) -> bool:
    try:
        normalize_hex(value if isinstance(value, str) else "")
        return True
    except ValueError:
        return False


def luminance(hex_color: str) -> float:
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    hex_color = normalize_hex(hex_color)
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a: str, b: str = "#ffffff") -> float:
    """The contrast ratio of two colours, 1 to 21."""
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def _with_lightness(h: float, lightness: float, s: float) -> str:
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h, lightness, s))


def darken_to(hex_color: str, against: str = "#ffffff", minimum: float = MIN_CONTRAST) -> str:
    """The same hue, darkened step by step until it reaches the contrast; the colour itself when it already does."""
    hex_color = normalize_hex(hex_color)
    if ratio(hex_color, against) >= minimum:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    while lightness > 0:
        lightness = max(0.0, lightness - 0.01)
        candidate = _with_lightness(h, lightness, s)
        if ratio(candidate, against) >= minimum:
            return candidate
    return "#000000"


def nearest_passing(hex_color: str, against: str, minimum: float = MIN_CONTRAST) -> str:
    """The shade of the same hue closest in lightness that reaches the contrast against a fixed colour, darker or
    lighter, whichever needs the smaller step; the colour itself when it already passes."""
    hex_color = normalize_hex(hex_color)
    if ratio(hex_color, against) >= minimum:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    for step in range(1, 101):
        for candidate_l in (lightness - step / 100, lightness + step / 100):
            if 0.0 <= candidate_l <= 1.0:
                candidate = _with_lightness(h, candidate_l, s)
                if ratio(candidate, against) >= minimum:
                    return candidate
    return "#000000" if ratio("#000000", against) >= ratio("#ffffff", against) else "#ffffff"
