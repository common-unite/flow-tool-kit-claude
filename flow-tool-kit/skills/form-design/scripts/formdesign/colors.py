"""The plan's colours measured against WCAG AA where the form draws them, before anything is drawn.

`problems(plan)` returns (errors, warnings). Each pair is a text colour on the colour behind it, as the package draws
it: the button text on the brand, links in the brand on the card, headings, field labels and typed values, and the
banner's white text on its fill or scrim. Body text and buttons need 4.5:1 and fall short as an error; large text
(headings, the banner title) needs 3:1 and falls short as a warning. Each message gives the measured ratio and the
nearest shade of the plan's own colour that passes. The arithmetic is the shared lib's contrast.py, the same brand-kit
uses to darken a brand colour.
"""
from __future__ import annotations

import pathlib
import sys

from . import planrules

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_shared" / "lib"))
import contrast  # noqa: E402  one copy for every skill (shared lib)

WHITE = "#ffffff"
BODY, LARGE = "body", "large"
NEED = {BODY: contrast.BODY_TEXT, LARGE: contrast.LARGE_TEXT}


def pairs(plan: dict) -> list[dict]:
    """Every text colour on its background the plan sets: {use, text, on, size, change}, where change names the plan
    colour a fix should move (text or on)."""
    s = planrules.style(plan)
    # The Style Editor values as normalize writes them into styleTokens: the run's defaults, then the plan's own
    fs = {"Brand": s["brand"], "Field labels": "#353535", "Input text": "#181818", **s["form_style"]}
    brand, card = fs["Brand"], fs.get("Card background") or WHITE
    out = [
        {"use": "button text (Brand text) on the brand: buttons, checked boxes and selected options", "size": BODY,
         "text": ("form_style Brand text", fs.get("Brand text") or WHITE), "on": ("style.brand", brand), "change": "on"},
        {"use": "links in the brand on the card", "size": BODY,
         "text": ("style.brand", brand), "on": ("form_style Card background", card), "change": "text"},
        {"use": "headings (style.heading_color) on the card", "size": LARGE,
         "text": ("style.heading_color", s["heading_color"]), "on": ("form_style Card background", card), "change": "text"},
        {"use": "field labels on the card", "size": BODY,
         "text": ("form_style Field labels", fs["Field labels"]), "on": ("form_style Card background", card), "change": "text"},
        {"use": "typed answers on the input", "size": BODY,
         "text": ("form_style Input text", fs["Input text"]), "on": ("form_style Input background", fs.get("Input background") or WHITE),
         "change": "text"},
    ]
    banner = {**(plan.get("banner") or {}), **((plan.get("template") or {}).get("banner") or {})}
    layout = banner.get("layout") or banner.get("shape") or planrules.banner_layout(plan)
    if layout in ("overlay", "split", "hero"):
        photo = layout != "split" and banner.get("image", True) is not False
        if photo:
            # The drawing's scrim: the plan's, else the brand on a multi-page form, else the slate or heading colour
            if banner.get("scrimColor"):
                behind = ("template.banner.scrimColor", banner["scrimColor"])
            elif len(planrules.pages(plan)) > 1:
                behind = ("style.brand", brand)
            else:
                behind = ("style.slate", s["slate"]) if s.get("slate") else ("style.heading_color", s["heading_color"])
            where = "on its scrim (measured solid; the photo shows through it, so check the drawn banner as well)"
        else:
            behind = ("template.banner.backgroundColor" if banner.get("backgroundColor") else "style.brand", banner.get("backgroundColor") or brand)
            where = "on its fill"
        out.append({"use": f"the banner title, white {where}", "size": LARGE, "text": ("banner text", WHITE), "on": behind, "change": "on"})
        if banner.get("subtitle"):
            out.append({"use": f"the banner subtitle, white {where}", "size": BODY, "text": ("banner text", WHITE), "on": behind, "change": "on"})
    return out


def problems(plan: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    seen = set()
    for pair in pairs(plan):
        (text_name, text), (on_name, on) = pair["text"], pair["on"]
        if not (contrast.is_color(text) and contrast.is_color(on)):
            bad = text_name if not contrast.is_color(text) else on_name
            value = text if bad == text_name else on
            if (bad, value) not in seen:
                seen.add((bad, value))
                warnings.append(f"{bad} {value!r} is not a #rrggbb colour, so its contrast was not measured")
            continue
        need = NEED[pair["size"]]
        measured = contrast.ratio(text, on)
        if measured >= need:
            continue
        name, own, against = (on_name, on, text) if pair["change"] == "on" else (text_name, text, on)
        fixed = contrast.nearest_passing(own, against, need)
        kind = "body text and buttons" if pair["size"] == BODY else "large text"
        message = (f"contrast: {pair['use']}: {contrast.normalize_hex(text)} on {contrast.normalize_hex(on)} measures "
                   f"{measured:.2f}:1; WCAG AA needs {need:g}:1 for {kind}. {fixed} ({contrast.ratio(fixed, against):.2f}:1) is the "
                   f"nearest passing shade of {name} {contrast.normalize_hex(own)}")
        (errors if pair["size"] == BODY else warnings).append(message)
    return errors, warnings
