"""One letterhead for the organization's Lightning Email Templates, drawn on the canvas before anything is built:
logo on the brand color, the banner photo, a 16px body, one button, an address footer.

An email in plan.json (emails.confirmation, emails.saved, emails.resume):

    {"name": "Volunteer_Confirmation", "subject": "We received your application, {{FlowToolKit__Contact1_First_Name__c}}",
     "heading": "Thank you for applying", "body": ["<p>...</p>", ...], "button": {"label": "Visit our site", "url": "https://..."}}

Merge fields are written {{Field__c}}. In the template they become Lightning merges on the Form Submission
({{{FlowToolKit__Form_Submission__c.Field__c}}}); on the canvas they show the plan's sample values. Lightning templates
cannot follow a relationship (Form_Template__r.Name), so the copy uses direct Form Submission fields only.
"""
from __future__ import annotations

import html as _html
import re

OBJ = "FlowToolKit__Form_Submission__c"
RESUME_LINK = "{{FlowToolKit__Internal_Resume_Link__c}}"
MERGE = re.compile(r"\{\{(\w+__c)\}\}")
BODY_P = 'style="margin: 0 0 16px; font-size: 16px; line-height: 1.6; color: #212529"'


def merge_lightning(text: str) -> str:
    """{{Field__c}} -> {{{FlowToolKit__Form_Submission__c.Field__c}}}, for the template that is deployed."""
    return MERGE.sub(lambda m: "{{{" + OBJ + "." + m.group(1) + "}}}", text)


def merge_sample(text: str, sample: dict) -> str:
    """{{Field__c}} -> its sample value, for the canvas; an unknown field shows as [Field label]."""
    def value(m):
        name = m.group(1)
        if name in sample:
            return _html.escape(str(sample[name]))
        words = re.sub(r"^FlowToolKit__|__c$", "", name).replace("_", " ")
        return f"[{words}]"
    return MERGE.sub(value, text)


def body_html(paragraphs: list) -> str:
    out = []
    for p in paragraphs:
        p = p.strip()
        out.append(p if p.startswith("<") else f"<p {BODY_P}>{_html.escape(p)}</p>")
    return "".join(out)


def html(email: dict, images: dict, letterhead: dict, style: dict) -> str:
    """The whole email as table markup that renders in mail clients. images: {"logo": url, "banner": url}; a missing
    image is left out, never drawn with an empty src."""
    button = email.get("button") or {}
    lh = {"org": "", "tagline": "", "address": "", "email": "", "site": "", "site_label": "", **(letterhead or {})}
    brand, heading = style["brand"], style.get("heading_color", style["brand"])
    cream = style.get("background", "#f3f3f3")
    body_font, heading_font = style["font_css"], style["heading_font_css"]
    radius = style.get("button_radius", "4px")
    logo = (f'<td style="padding-right: 14px"><img src="{images["logo"]}" width="52" height="52" alt="{_html.escape(lh.get("logo_alt") or lh["org"])}" '
            f'style="display: block; border-radius: 26px; background: #ffffff"/></td>') if images.get("logo") else ""
    banner = (f'<tr><td><img src="{images["banner"]}" width="600" alt="{_html.escape(lh.get("banner_alt") or "")}" style="display: block; '
              f'width: 100%; height: 200px; object-fit: cover"/></td></tr>') if images.get("banner") else ""
    action = (f'<tr><td style="padding: 8px 32px 32px"><a href="{_html.escape(button.get("url", ""))}" style="display: inline-block; padding: 12px 28px; '
              f'border-radius: {radius}; background: {brand}; color: #ffffff; font-family: {body_font}; font-size: 16px; font-weight: 600; '
              f'text-decoration: none">{_html.escape(button.get("label", ""))}</a></td></tr>') if button.get("label") else ""
    contact = " &#160;|&#160; ".join(x for x in (
        _html.escape(lh["address"]),
        f'<a href="mailto:{_html.escape(lh["email"])}" style="color: #ffffff">{_html.escape(lh["email"])}</a>' if lh["email"] else "",
        f'<a href="{_html.escape(lh["site"])}" style="color: #ffffff">{_html.escape(lh["site_label"] or lh["site"])}</a>' if lh["site"] else "") if x)
    return (f'<html><body style="margin: 0; padding: 0; background: {cream}">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: {cream}"><tr><td align="center" style="padding: 24px 12px">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background: #ffffff; border-radius: 8px; overflow: hidden">'
            f'<tr><td style="background: {brand}; padding: 18px 32px"><table role="presentation" cellpadding="0" cellspacing="0"><tr>{logo}'
            f'<td style="font-family: {heading_font}; font-size: 20px; font-weight: 600; color: #ffffff">{_html.escape(lh["org"])}</td></tr></table></td></tr>'
            f'{banner}'
            f'<tr><td style="padding: 32px 32px 8px; font-family: {body_font}">'
            f'<h1 style="margin: 0 0 20px; font-family: {heading_font}; font-size: 24px; line-height: 1.3; font-weight: 600; color: {heading}">{_html.escape(email.get("heading", ""))}</h1>'
            f'{body_html(email.get("body") or [])}</td></tr>{action}'
            f'<tr><td style="padding: 20px 32px; background: {heading}; font-family: {body_font}; font-size: 14px; line-height: 1.6; color: #ffffff">'
            f'{_html.escape(lh["tagline"])}{"<br/>" if lh["tagline"] and contact else ""}{contact}</td></tr>'
            f'</table></td></tr></table></body></html>')


def inner_body(markup: str) -> str:
    return markup.split("<body", 1)[1].split(">", 1)[1].rsplit("</body>", 1)[0]
