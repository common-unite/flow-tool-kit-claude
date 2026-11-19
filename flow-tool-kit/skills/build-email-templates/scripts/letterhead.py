"""One letterhead for an organization's Lightning Email Templates: the brand bar with the logo, an optional banner photo,
a 16px body, one button and an address footer, as table markup that renders in mail clients.

The same markup is drawn on form-design's review canvas, so what the person reviewed is what is deployed. Keep html()
in step with form-design's letterhead (shared/needs/build-email-templates.md in the plugin repository proposes one shared copy).

Merge fields are written {{Field__c}} in plan.json. In the template they become Lightning merges:
    {{Field__c}}              -> {{{FlowToolKit__Form_Submission__c.Field__c}}}   (a Form Submission field, direct only)
    {{Name}}                  -> {{{FlowToolKit__Form_Submission__c.Name}}}       (the submission number)
    {{Recipient.FirstName}}   -> {{{Recipient.FirstName}}}                        (the Contact or Lead the email renders against)
A relationship ({{Form_Template__r.Name}}) is refused: a Lightning template cannot follow one, and the render fails.
"""
from __future__ import annotations

import html as _html
import re

SUBMISSION = "FlowToolKit__Form_Submission__c"
RESUME_LINK_FIELD = "FlowToolKit__Internal_Resume_Link__c"
RESUME_LINK = "{{" + RESUME_LINK_FIELD + "}}"
MERGE = re.compile(r"\{\{\s*([A-Za-z][A-Za-z0-9_.]*)\s*\}\}")
GLOBAL_PREFIXES = ("Recipient.", "Organization.", "Sender.")
BODY_P = 'style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #212529"'

DEFAULT_STYLE = {"brand": "#0b5cab", "heading_color": "#032d60", "accent": "#fe9339", "background": "#f3f3f3",
                 "font": "Arial", "font_css": "Arial, Helvetica, sans-serif", "heading_font_css": "Arial, Helvetica, sans-serif",
                 "Corner radius": "8px"}


class MergeError(ValueError):
    pass


def merges(text: str) -> list:
    """Every merge name in the text, in order, as written ({{X}} -> X)."""
    return [m.group(1) for m in MERGE.finditer(text or "")]


def lightning_token(name: str) -> str:
    if name.startswith(GLOBAL_PREFIXES):
        return "{{{" + name + "}}}"
    if "." in name:
        raise MergeError(f"{{{{{name}}}}} follows a relationship; a Lightning template can merge only direct Form Submission "
                         "fields (copy the value onto the submission, or write the words into the email)")
    return "{{{" + SUBMISSION + "." + name + "}}}"


def merge_lightning(text: str) -> str:
    """{{Field__c}} -> {{{FlowToolKit__Form_Submission__c.Field__c}}}, for the template that is deployed."""
    return MERGE.sub(lambda m: lightning_token(m.group(1)), text or "")


def label_for(name: str) -> str:
    words = re.sub(r"^FlowToolKit__|__c$", "", name.split(".")[-1]).replace("_", " ")
    return words.strip() or name


def merge_sample(text: str, sample: dict) -> str:
    """{{Field__c}} -> its sample value, for the preview; an unknown field shows as [Field label]."""
    def value(m):
        name = m.group(1)
        if name in (sample or {}):
            return _html.escape(str(sample[name]))
        return f"[{_html.escape(label_for(name))}]"
    return MERGE.sub(value, text or "")


def body_html(paragraphs: list) -> str:
    out = []
    for p in paragraphs or []:
        p = str(p).strip()
        if not p:
            continue
        out.append(p if p.startswith("<") else f"<p {BODY_P}>{_html.escape(p)}</p>")
    return "".join(out)


def html(email: dict, images: dict, letterhead: dict, style: dict) -> str:
    """The whole email. images: {"logo": url, "banner": url}; a missing image is left out, never drawn with an empty src."""
    button = email.get("button") or {}
    lh = {"org": "", "tagline": "", "address": "", "email": "", "site": "", "site_label": "", **(letterhead or {})}
    style = {**DEFAULT_STYLE, **(style or {})}
    brand, heading = style["brand"], style.get("heading_color") or style["brand"]
    cream = style.get("background", "#f3f3f3")
    body_font, heading_font = style["font_css"], style["heading_font_css"]
    radius = style.get("button_radius") or style.get("Corner radius") or "4px"
    images = images or {}
    logo = (f'<td style="padding-right: 14px"><img src="{_html.escape(images["logo"])}" width="52" height="52" '
            f'alt="{_html.escape(lh.get("logo_alt") or lh["org"])}" style="display: block; border-radius: 26px; background: #ffffff"/></td>'
            ) if images.get("logo") else ""
    banner = (f'<tr><td><img src="{_html.escape(images["banner"])}" width="600" alt="{_html.escape(lh.get("banner_alt") or "")}" '
              f'style="display: block; width: 100%; height: 200px; object-fit: cover"/></td></tr>') if images.get("banner") else ""
    action = (f'<tr><td style="padding: 8px 32px 32px"><a href="{_html.escape(button.get("url", ""))}" style="display: inline-block; '
              f'padding: 12px 28px; border-radius: {radius}; background: {brand}; color: #ffffff; font-family: {body_font}; font-size: 16px; '
              f'font-weight: 600; text-decoration: none">{_html.escape(button.get("label", ""))}</a></td></tr>') if button.get("label") else ""
    contact = " &#160;|&#160; ".join(x for x in (
        _html.escape(lh["address"]),
        f'<a href="mailto:{_html.escape(lh["email"])}" style="color: #ffffff">{_html.escape(lh["email"])}</a>' if lh["email"] else "",
        f'<a href="{_html.escape(lh["site"])}" style="color: #ffffff">{_html.escape(lh["site_label"] or lh["site"])}</a>' if lh["site"] else ""
    ) if x)
    return (f'<html><body style="margin: 0; padding: 0; background: {cream}">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: {cream}"><tr>'
            f'<td align="center" style="padding: 24px 12px">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; '
            f'background: #ffffff; border-radius: 8px; overflow: hidden">'
            f'<tr><td style="background: {brand}; padding: 18px 32px"><table role="presentation" cellpadding="0" cellspacing="0"><tr>{logo}'
            f'<td style="font-family: {heading_font}; font-size: 20px; font-weight: 600; color: #ffffff">{_html.escape(lh["org"])}</td>'
            f'</tr></table></td></tr>'
            f'{banner}'
            f'<tr><td style="padding: 32px 32px 8px; font-family: {body_font}">'
            f'<h1 style="margin: 0 0 20px; font-family: {heading_font}; font-size: 24px; line-height: 1.3; font-weight: 600; '
            f'color: {heading}">{_html.escape(email.get("heading", ""))}</h1>'
            f'{body_html(email.get("body") or [])}</td></tr>{action}'
            f'<tr><td style="padding: 20px 32px; background: {heading}; font-family: {body_font}; font-size: 14px; line-height: 1.6; '
            f'color: #ffffff">{_html.escape(lh["tagline"])}{"<br/>" if lh["tagline"] and contact else ""}{contact}</td></tr>'
            f'</table></td></tr></table></body></html>')


def inner_body(markup: str) -> str:
    return markup.split("<body", 1)[1].split(">", 1)[1].rsplit("</body>", 1)[0]


# ---- contrast (WCAG 2): white text sits on the brand bar, the button and the footer ----

def _channel(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", h):
        raise ValueError(f"not a #rrggbb color: {hex_color!r}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
