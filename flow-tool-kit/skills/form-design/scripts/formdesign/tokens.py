"""Style Editor values to the saved --ftk- tokens, so plan.json carries exactly what the canvas draws.

The Form Template keeps the package's default theme. A brand is applied as Style Editor values (the Basic tab) and a few
Advanced section tokens, never as a new Form Theme, so an admin can still change it in the Style Editor afterwards.
"""
from __future__ import annotations

# Style Editor Basic label to the token it saves
FORM_STYLE_TOKENS = {
    "Brand": "--ftk-color-primary", "Brand text": "--ftk-color-on-primary", "Input text": "--ftk-color-text",
    "Field labels": "--ftk-color-label", "Choice text": "--ftk-color-option", "Form background": "--ftk-color-background",
    "Card background": "--ftk-color-surface", "Input background": "--ftk-color-control-surface", "Borders": "--ftk-color-border",
    "Border thickness": "--ftk-border-scale", "Corner radius": "--ftk-radius-medium", "Input size": "--ftk-control-scale",
    "Text size": "--ftk-font-scale", "Field spacing": "--ftk-spacing-scale", "Label weight": "--ftk-font-weight-label",
    "Font": "--ftk-font-family",
}
SCALE_LABELS = {"Border thickness", "Input size", "Text size", "Field spacing"}

# Inputs people can find: a darker border at 150%, text and inputs 150%, spacing 125% (house rules, form-house-rules.md)
DEFAULT_FORM_STYLE = {"Borders": "#8A8A8A", "Border thickness": "150%", "Text size": "150%", "Field spacing": "125%", "Input size": "150%"}


class TokenError(ValueError):
    pass


def scale_value(label: str, value) -> str:
    """Scales save as plain multipliers ("1.5"); the editor shows percents ("150%")."""
    if label not in SCALE_LABELS:
        return str(value)
    number = float(str(value).rstrip("%"))
    if str(value).endswith("%") or number > 10:
        number /= 100
    return f"{number:g}"


def percent(value) -> float:
    """150%, "150", 1.5 -> 1.5."""
    number = float(str(value).rstrip("%"))
    return number / 100 if str(value).endswith("%") or number > 10 else number


def style_tokens(form_style: dict, advanced: dict | None = None) -> dict:
    tokens = {}
    for label, value in form_style.items():
        if label not in FORM_STYLE_TOKENS:
            raise TokenError(f"style.form_style {label!r} is not a Style Editor Basic value ({', '.join(FORM_STYLE_TOKENS)})")
        tokens[FORM_STYLE_TOKENS[label]] = scale_value(label, value)
    for name, value in (advanced or {}).items():
        tokens[name if name.startswith("--ftk-") else "--ftk-" + name.lstrip("-")] = value
    return tokens


def section_tokens(brand: str, label_color: str = "#353535") -> dict:
    """Section frames in the brand: title, border and a 2px border width. These are the Advanced section tokens, because
    the Basic Borders color would recolor every input too."""
    return {"--ftk-section-border-color": brand, "--ftk-section-border-width": "2px", "--ftk-header-title-color": brand,
            "--ftk-header-subtitle-color": label_color}
