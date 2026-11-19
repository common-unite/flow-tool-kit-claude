"""The form-type rules, counted times, and the one place they are written into plan.json.

plan.json is the source of truth: a person (or Claude in chat) writes the design, and `normalize` fills in what the
rules decide so nobody types it by hand: each page's Estimated_Time__c counted from its questions, the form-type row's
template switches, the banner's layout and placement, the forward button label, section spacing, the Style Editor
tokens, rich text scaled to the form's Text size, and the five parts of an address row on a standard address field
(MailingAddress and the like), without which the package draws no address. It is idempotent: a second run changes nothing.

A value the user chose on purpose is listed in plan["keep"] (a Form Template field API name, "banner.layout",
"banner.placement", "Estimated_Time__c" or "Button_Label__c") and is never changed.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys

from . import conditions, tokens

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_shared" / "lib"))
import addressparts  # noqa: E402  the address rule, one copy for every skill

LONG_KINDS = ("application", "grant")
FORM_KINDS = ("survey", "application", "grant", "registration", "intake", "release", "request", "feedback", "other")
PAGE_MARGIN_TOP = "slds-m-top_xx-large"   # 48px outside the frame plus its own 20px: frames sit 68px apart
PAGE_MARGIN_BOTTOM = "slds-m-bottom_none"  # a bottom margin lands inside a framed section, under its last field
DEFAULT_STYLE = {"brand": "#0b5cab", "heading_color": "#032d60", "accent": "#fe9339", "background": "#f3f3f3",
                 "font": "Arial", "font_css": "Arial, Helvetica, sans-serif", "heading_font_css": "Arial, Helvetica, sans-serif",
                 "Corner radius": "8px"}
FONT_SIZE = re.compile(r"font-size:\s*(\d+(?:\.\d+)?)px")


# ---------------------------------------------------------------- reading the plan
def pages(plan: dict) -> list:
    return plan.get("pages") or []


def kind(plan: dict) -> str:
    return (plan.get("form_kind") or "other").lower()


def style(plan: dict) -> dict:
    """The plan's style with defaults: a plan from a brief with no brand kit still draws in a neutral palette."""
    s = {**DEFAULT_STYLE, **(plan.get("style") or {})}
    if (plan.get("style") or {}).get("font") and not (plan.get("style") or {}).get("font_css"):
        s["font_css"] = f"'{s['font']}', Arial, sans-serif"
    if (plan.get("style") or {}).get("heading_font") and not (plan.get("style") or {}).get("heading_font_css"):
        s["heading_font_css"] = f"'{s['heading_font']}', Georgia, serif"
    s["form_style"] = {**tokens.DEFAULT_FORM_STYLE, **(s.get("form_style") or {})}
    s.setdefault("advanced", {"font-family-heading": s["heading_font_css"], "line-height": "1.875"})
    return s


def text_scale(plan: dict) -> float:
    return tokens.percent(style(plan)["form_style"].get("Text size", "100%"))


def radius_px(plan: dict) -> int:
    return int(float(str(style(plan).get("Corner radius", "8px")).rstrip("px") or 8))


def kept(plan: dict, key: str) -> bool:
    return key in (plan.get("keep") or [])


def load_ir(plan: dict, base: pathlib.Path | None):
    """The source's ir.json (form-migrate) when the plan names one and it is there; None for a brief or a missing file."""
    path = (plan.get("source") or {}).get("ir")
    if not path or base is None:
        return None
    file = (base / path) if not pathlib.Path(path).is_absolute() else pathlib.Path(path)
    return json.loads(file.read_text()) if file.exists() else None


# ---------------------------------------------------------------- counted time
def words(markup: str | None) -> int:
    return len(html.unescape(re.sub(r"<[^>]+>", " ", markup or "")).split())


def is_address_part(field: dict) -> bool:
    """An Address component is one row (variant Address) plus its bound parts, which draw and count as nothing."""
    return field.get("control") == "Address" and field.get("variant") != "Address"


def field_seconds(field: dict, in_matrix: bool = False) -> float:
    """A matrix row about 5 seconds, a checkbox 3, a picklist 6, short text or a number about 11, long text 55."""
    c, v = field.get("control"), field.get("variant")
    if in_matrix:
        return 5
    if c == "Address":
        return 25 if v == "Address" else 0
    if c == "Checkbox":
        return 3 + (words(field.get("attestation_text") or field.get("help")) / 4 if v == "attestation" else 0)
    if c == "Picklist":
        return 6
    if c == "MultiPicklist":
        return 8
    if c == "TextArea":
        return 55
    if c in ("FileUpload", "ImageUpload"):
        return 30
    if c == "SignaturePad":
        return 15
    if c == "Repeater":
        return 2 * 11 * len((field.get("repeater") or {}).get("columns") or [])
    return 11


def section_seconds(section: dict) -> float:
    matrix = section.get("inner_type") == "likertSection"
    own = section.get("condition")
    # A follow-up a field's own rule reveals ("Please specify") is rarely shown, so it is not counted
    seconds = sum(field_seconds(f, matrix) for f in section.get("fields") or [] if not (f.get("condition") and f.get("condition") != own))
    return seconds + words(section.get("rich_text")) / 4  # reading at about 240 words a minute


def branch_seconds(sections: list) -> float:
    """One path through these sections: unconditional ones add up; sections shown by different answers to one question
    are alternatives, so only the longest answer's set counts."""
    base, branches = 15.0, {}  # about 15 seconds a page to read its header and move on
    for section in sections:
        seconds = section_seconds(section)
        alt = conditions.alternatives(section.get("condition"))
        if not alt:
            base += seconds
            continue
        controller, values = alt
        for value in values:
            branches.setdefault(controller, {}).setdefault(value, 0)
            branches[controller][value] += seconds
    return base + sum(max(v.values()) for v in branches.values())


def page_minutes(page: dict) -> int:
    return max(1, round(branch_seconds(page.get("sections") or []) / 60))


def form_seconds(plan: dict) -> float:
    sections = [s for p in pages(plan) for s in p.get("sections") or []]
    return branch_seconds(sections) + 15 * (len(pages(plan)) - 1)


def form_minutes(plan: dict) -> int:
    """The pages' Estimated_Time__c added up, as the form-type rules count "long"."""
    return sum(page_minutes(p) for p in pages(plan))


def minutes_range(seconds: float) -> str:
    m = seconds / 60
    if m < 2:
        return "1 to 2 minutes"
    if m < 10:
        return f"{int(m)} to {int(m) + 2} minutes"
    lo = 5 * int(m // 5)
    return f"{lo} to {lo + 5} minutes"


def with_time(text: str | None, plan: dict) -> str:
    """'10 minutes' or 'about 40 minutes' in a banner subtitle or tag becomes the counted range."""
    return re.sub(r"(?:about |around )?\d+(?:\s*(?:to|-)\s*\d+)?\s*(?:minutes|mins|min)\b",
                  lambda _: minutes_range(form_seconds(plan)), text or "", flags=re.I)


# ---------------------------------------------------------------- the form-type rules
def form_row(plan: dict) -> int:
    """The row of the form-type rules table (_shared/standards/form-type-rules.md) this form follows.

    1 survey, one page; 2 survey, two or more pages; 3 simple single page; 4 two pages; 5 three or more pages, not long;
    6 long: an application or grant with three or more pages, or any form with three or more pages and about 10 minutes
    or more. plan["stages"] (true or false) is the user's own choice and wins."""
    n = len(pages(plan))
    stages = plan.get("stages")
    if stages is True:
        return 6
    long_form = n >= 3 and (kind(plan) in LONG_KINDS or form_minutes(plan) >= 10)
    if long_form and stages is not False:
        return 6
    if kind(plan) == "survey":
        return 1 if n == 1 else 2
    return 3 if n == 1 else 4 if n == 2 else 5


def is_long(plan: dict) -> bool:
    return form_row(plan) == 6


def button_position(plan: dict) -> str:
    """A Footer bar on one or two pages; Docked on three or more, where pages are long and the bar should stay in reach."""
    return "Docked" if len(pages(plan)) > 2 else "Footer"


def submit_default(plan: dict) -> str:
    return {"survey": "Submit Survey", "application": "Submit Application", "grant": "Submit Application",
            "registration": "Submit Registration"}.get(kind(plan), "Submit")


def sends_confirmation(plan: dict) -> bool:
    return bool((plan.get("emails") or {}).get("confirmation"))


def template_settings(plan: dict) -> dict:
    """What the form-type row sets on the Form Template. Values listed in plan["keep"] are left alone by normalize."""
    template = plan.get("template") or {}
    long_form = is_long(plan)
    n = len(pages(plan))
    save = long_form or bool(template.get("Allow_Save_Progress__c") and kept(plan, "Allow_Save_Progress__c"))
    out = {
        "Stages_Mode__c": long_form,
        "Allow_Save_Progress__c": save,
        "Enable_Review_Screen__c": long_form,
        # The Save Progress email serves ordinary pages only; stages mode sends its own resume link from a button
        "Send_Save_Progress_Email__c": save and not long_form,
        "Attach_PDF_Confirmation__c": long_form and sends_confirmation(plan),
        "Buttons_Position__c": button_position(plan),
        "Button_Alignment__c": "center" if long_form else "spread",
        "Hide_Stage_Indicator__c": n <= 2 and not long_form,
    }
    if long_form:
        out["Stage_Indicator_Type__c"] = "vertical"
        out["Stage_Mode_Layout__c"] = "Display Template Header"
    elif n > 2:
        out["Stage_Indicator_Type__c"] = "base"  # base shows on phones, where path hides
    return out


def banner_layout(plan: dict) -> str:
    return "compact" if len(pages(plan)) == 1 else "overlay"


def banner_placement(plan: dict) -> str:
    """header only beside the vertical indicator (stages mode); any other form sits flush on the card, square bottom corners."""
    return "header" if is_long(plan) else "singleCardHeader"


# ---------------------------------------------------------------- normalize
class Changes(list):
    def set(self, obj: dict, key: str, value, path: str):
        if obj.get(key) != value:
            self.append(f"{path}: {json.dumps(obj.get(key))} -> {json.dumps(value)}")
            obj[key] = value

    def drop(self, obj: dict, key: str, path: str):
        if key in obj:
            self.append(f"{path}: {json.dumps(obj[key])} -> (removed)")
            del obj[key]


def scale_markup(markup: str, factor: float) -> str:
    if not markup or factor == 1:
        return markup
    return FONT_SIZE.sub(lambda m: f"font-size: {round(float(m.group(1)) * factor, 2):g}px", markup)


def rich_text_targets(plan: dict):
    """Every stored rich text a respondent reads: section text and the confirmation message."""
    for page in pages(plan):
        for section in page.get("sections") or []:
            if section.get("rich_text"):
                yield section, "rich_text"
    template = plan.get("template") or {}
    if template.get("Confirmation_Page_Message__c"):
        yield template, "Confirmation_Page_Message__c"


def normalize(plan: dict, base: pathlib.Path | None = None) -> list[str]:
    """Write the rule-decided values into the plan in place. Returns what changed, one line each."""
    ch = Changes()
    long_form = is_long(plan)
    multipage = len(pages(plan)) > 1
    template = plan.setdefault("template", {})

    for p, page in enumerate(pages(plan)):
        where = f"pages[{p}]"
        if not kept(plan, "Estimated_Time__c"):
            ch.set(page, "Estimated_Time__c", page_minutes(page), f"{where}.Estimated_Time__c")
        if multipage and not long_form and p < len(pages(plan)) - 1 and not kept(plan, "Button_Label__c"):
            if page.get("Button_Label__c") in (None, "", "Next"):
                ch.set(page, "Button_Label__c", "Continue", f"{where}.Button_Label__c")
        for s, section in enumerate(page.get("sections") or []):
            here = f"{where}.sections[{s}]"
            titled = bool(section.get("Header_Title__c"))
            filled, lines = addressparts.completed(section.get("fields") or [])
            if lines:
                section["fields"] = filled
                ch += [f"{here}.fields: {line}" for line in lines]
            fields = section.get("fields") or []
            admin = section.get("Header_Title__c") or (fields[0].get("label") if fields else None) or "Text block"
            if not section.get("Title__c"):
                ch.set(section, "Title__c", admin[:80], f"{here}.Title__c")
            if not titled:
                ch.set(section, "Show_Header__c", False, f"{here}.Show_Header__c")
            if not section.get("Section_Frame__c"):
                ch.set(section, "Section_Frame__c", "box" if titled else "clean", f"{here}.Section_Frame__c")
            if titled and not section.get("Header_Style__c"):
                ch.set(section, "Header_Style__c", "outlined", f"{here}.Header_Style__c")
            if not section.get("Top_Margin__c"):
                ch.set(section, "Top_Margin__c", PAGE_MARGIN_TOP, f"{here}.Top_Margin__c")
            if not section.get("Bottom_Margin__c"):
                ch.set(section, "Bottom_Margin__c", PAGE_MARGIN_BOTTOM, f"{here}.Bottom_Margin__c")

    ch.set(plan, "form_type", "long" if long_form else "short", "form_type")
    if not template.get("Submit_Button_Label__c"):
        ch.set(template, "Submit_Button_Label__c", submit_default(plan), "template.Submit_Button_Label__c")
    settings = template_settings(plan)
    for key, value in settings.items():
        if not kept(plan, key):
            ch.set(template, key, value, f"template.{key}")
    for key in ("Stage_Indicator_Type__c", "Stage_Mode_Layout__c"):
        if key not in settings and not kept(plan, key):
            ch.drop(template, key, f"template.{key}")

    emails = plan.get("emails") or {}
    if emails.get("confirmation", {}).get("name"):
        ch.set(template, "Email_Template_Name_Confirmation__c", emails["confirmation"]["name"], "template.Email_Template_Name_Confirmation__c")
        ch.set(template, "Send_Confirmation__c", True, "template.Send_Confirmation__c")
        if not template.get("Recipients_Confirmation_Email__c"):
            ch.set(template, "Recipients_Confirmation_Email__c", "Email", "template.Recipients_Confirmation_Email__c")
    if emails.get("saved", {}).get("name") and template.get("Send_Save_Progress_Email__c"):
        ch.set(template, "Email_Template_Name_Saved__c", emails["saved"]["name"], "template.Email_Template_Name_Saved__c")
    if emails.get("resume", {}).get("name") and template.get("Stages_Mode__c"):
        ch.set(template, "Email_Template_Name_Resume_Form__c", emails["resume"]["name"], "template.Email_Template_Name_Resume_Form__c")

    banner = template.setdefault("banner", {})
    if not kept(plan, "banner.layout") and banner.get("layout") != "split":
        ch.set(banner, "layout", banner_layout(plan), "template.banner.layout")
    if not kept(plan, "banner.placement"):
        ch.set(banner, "placement", banner_placement(plan), "template.banner.placement")
    if not banner.get("height"):
        ch.set(banner, "height", "small", "template.banner.height")
    if not banner.get("title") and template.get("Name"):
        ch.set(banner, "title", template["Name"], "template.banner.title")
    for key in ("subtitle", "tags"):
        if banner.get(key) and with_time(banner[key], plan) != banner[key]:
            ch.set(banner, key, with_time(banner[key], plan), f"template.banner.{key}")
    assets = plan.get("assets") or {}
    for key, asset in (("imageAsset", assets.get("banner")), ("logoAsset", assets.get("logo"))):
        if asset and not banner.get(key):
            ch.set(banner, key, asset, f"template.banner.{key}")

    s = style(plan)
    form_style = {"Brand": s["brand"], "Field labels": "#353535", "Input text": "#181818", "Corner radius": s["Corner radius"],
                  "Font": s["font_css"], **s["form_style"]}
    ch.set(plan, "styleTokens", {**tokens.style_tokens(form_style, s["advanced"]), **tokens.section_tokens(s["brand"])}, "styleTokens")

    # Stored rich text is scaled by the form's Text size: the package's font scale reaches labels and inputs but not an
    # inline size, so 16px is stored as 24px at 150%. The canvas divides it back. rich_text_scale records what is stored.
    target = text_scale(plan)
    stored = float(plan.get("rich_text_scale") or 1)
    if abs(target - stored) > 1e-9:
        for obj, key in rich_text_targets(plan):
            obj[key] = scale_markup(obj[key], target / stored)
        ch.set(plan, "rich_text_scale", target, "rich_text_scale")

    ir = load_ir(plan, base)
    if ir:
        used = {f.get("source_id") for _, _, f in conditions.iter_fields(plan)}
        used |= {c.get("source_id") for _, _, f in conditions.iter_fields(plan) for c in (f.get("repeater") or {}).get("columns") or []}
        dropped = plan.setdefault("dropped", [])
        explained = {d.get("source_id") for d in dropped}
        for f in ir.get("fields") or []:
            if f.get("id") in used or f.get("id") in explained:
                continue
            if f.get("input_type") == "hidden" or f.get("present_in_rendered_form") is False:
                dropped.append({"source_id": f["id"], "label": f.get("label") or "", "reason": "hidden field in the source (platform plumbing)"})
                ch.append(f"dropped: + {f['id']} (hidden in the source)")
    return ch


def display_markup(markup: str | None, plan: dict) -> str:
    """Stored rich text at the size the canvas draws it: the stored sizes divided by rich_text_scale."""
    stored = float(plan.get("rich_text_scale") or 1)
    return scale_markup(markup or "", 1 / stored) if stored != 1 else (markup or "")
