"""The artboards, drawn from plan.json with the real FlowToolKit Forms components.

Each board is {"name", "title", "w", "h", "tree"}: the element tree (nodes.py) and the frame it sits in on the canvas.
Heights are estimates sized to the canvas cap (an artboard is at most 8000px tall): a page that would be taller is split
at section boundaries into numbered parts, never clipped. A height measured on a real render (design/measured-heights.json,
written by check_render.cjs) wins over the estimate.
"""
from __future__ import annotations

import html
import math
import re

from . import conditions, letterhead, planrules
from .nodes import BRAND, el, esc, raw

CAP = 8000
BUDGET = CAP - 200
SCALE = 0.95 * 1.35  # estimates at text and inputs 150%, spacing 125%, line height 1.875
FORM_WIDTH = 1100
STAGES_WIDTH = 1440  # the vertical indicator card (300) beside a page card as wide as a single-card form
FIELD_LABELS, INPUT_TEXT = "#353535", "#181818"


class Ctx:
    """One plan, ready to draw: its style, its images' canvas urls and its question index."""

    def __init__(self, plan: dict, images: dict | None = None, slug: str = "form", ir: dict | None = None):
        self.plan, self.slug, self.ir = plan, slug, ir
        self.style = planrules.style(plan)
        self.images = images or {}
        self.index = conditions.field_index(plan)
        self.components = {c.get("key"): c for c in plan.get("components") or []}
        self.template = plan.get("template") or {}
        self.long = planrules.is_long(plan)
        self.pages = planrules.pages(plan)
        self.multipage = len(self.pages) > 1
        self.title = self.template.get("Name") or "Untitled form"

    def image(self, *keys):
        return next((self.images[k] for k in keys if self.images.get(k)), None)


# ---------------------------------------------------------------- shared page parts
def page_css(style: dict) -> str:
    return (f"body{{margin:0;background:{style['background']};font-family:{style['font_css']};color:{INPUT_TEXT}}}"
            f"a{{color:{style['brand']}}}a:hover{{color:{style['heading_color']}}}"
            f".form-card{{background:#ffffff;border-radius:{style['Corner radius']};box-shadow:0 2px 6px rgba(33,50,58,.14);overflow:hidden}}"
            ".form-body{padding:16px 40px 8px;display:flex;flex-direction:column;gap:8px}"
            ".intro{margin:0;font-size:14px;line-height:1.5;color:#353535}"
            ".fd-tag{display:inline-flex;align-items:center;gap:6px;margin:0 0 6px;padding:2px 10px;border-radius:999px;background:#353535;"
            "color:#ffffff;font-size:11px;font-weight:600;letter-spacing:.02em}"
            ".fd-component{margin:0 0 -2px;font-size:12px;color:#444444}"
            ".fd-gate{border:2px dashed #353535;border-radius:10px;padding:10px 10px 4px}")


def form_style(ctx: Ctx, *children) -> dict:
    fs = ctx.style["form_style"]
    pct = lambda v: str(v).rstrip("%")
    return el("FTK.FormStyle", {"brand": BRAND, "fieldLabels": FIELD_LABELS, "inputText": INPUT_TEXT, "cornerRadius": planrules.radius_px(ctx.plan),
                                "font": ctx.style["font_css"], "borders": fs.get("Borders"), "borderThickness": pct(fs.get("Border thickness", "100")),
                                "textSize": pct(fs.get("Text size", "100")), "fieldSpacing": pct(fs.get("Field spacing", "100")),
                                "inputSize": pct(fs.get("Input size", "100")), "advanced": ctx.style["advanced"]}, *children)


def frame(width: int, height: int, *children, pad: str = "32px 40px 24px") -> dict:
    return el("div", {"style": f"width: {width}px; min-height: {height}px; box-sizing: border-box; padding: {pad}; display: flex; "
                               "flex-direction: column; gap: 16px"}, *children)


def tag(text: str) -> dict:
    return raw(f'<div class="fd-tag"><span aria-hidden="true">&#8627;</span>{esc(text)}</div>')


def source_line(ctx: Ctx, extra: str = "") -> dict:
    src = ctx.plan.get("source") or {}
    platform = src.get("platform") or "brief"
    if platform == "brief":
        what = "Source: described in the request (brief mode), no source form"
        return raw(f'<p style="margin: 0; font-size: 13px; color: #353535">{esc(what)}{esc(extra)}</p>')
    name = src.get("form_name") or ctx.title
    ident = f" {src['form_id']}" if src.get("form_id") else ""
    label = f"{name} · {platform}{ident}"
    url = src.get("url")
    link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>' if url else esc(label + " (captured file in sources/)")
    return raw(f'<p style="margin: 0; font-size: 13px; color: #353535">Source: {link}{esc(extra)}</p>')


def banner(ctx: Ctx) -> dict:
    b = ctx.template.get("banner") or {}
    image = ctx.image("banner") if b.get("image", True) is not False else None
    logo = ctx.image("logo")
    assets = ctx.plan.get("assets") or {}
    scrim = ctx.style["brand"] if ctx.multipage else ctx.style.get("slate", ctx.style["heading_color"])
    return el("FTK.Banner", {
        "layout": b.get("layout") or planrules.banner_layout(ctx.plan), "placement": b.get("placement") or planrules.banner_placement(ctx.plan),
        "height": b.get("height") or "small", "title": f"<p>{esc(b.get('title') or ctx.title)}</p>",
        "subtitle": f"<p>{esc(planrules.with_time(b.get('subtitle') or '', ctx.plan))}</p>" if b.get("subtitle") else None,
        "tags": planrules.with_time(b["tags"] if isinstance(b.get("tags"), str) else "; ".join(b.get("tags") or []), ctx.plan) or None,
        "image": image, "imageAlt": (b.get("imageAlt") or assets.get("banner_alt") or "") if image else None,
        "backgroundColor": BRAND, "scrimColor": b.get("scrimColor") or scrim, "tagColor": b.get("tagColor") or ctx.style["accent"],
        "logo": logo, "logoAlt": (b.get("logoAlt") or assets.get("logo_alt") or "") if logo else None,
        "logoShape": (b.get("logoShape") or "circle") if logo else None})


# ---------------------------------------------------------------- fields and sections
def field_options(field: dict) -> list:
    return [{"label": o["label"], "value": o["value"]} for o in conditions.options_of(field)]


def control_node(f: dict, hide_label: bool = False) -> dict | None:
    c, v = f.get("control"), f.get("variant") or "standard"
    label = f.get("label") or ""
    common = {"label": label, "required": True if f.get("required") else None}
    if f.get("help") and v != "attestation":
        common.update({"helpText": f["help"], "helpTextDisplay": f.get("helpTextDisplay") or "Below Field"})
    if hide_label or f.get("label_hidden"):
        common["labelHidden"] = True
    cfg = f.get("config") or {}
    if c == "TextInput":
        return el("FTK.TextInput", common)
    if c == "FormattedInput":
        return el("FTK.FormattedInput", {"type": v, "phoneMask": "(xxx) xxx-xxxx" if v == "phone" else None, **common})
    if c == "Picklist":
        return el("FTK.Picklist", {"variant": v, "options": field_options(f), "placeholder": "Select an option" if v == "standard" else None, **common})
    if c == "MultiPicklist":
        return el("FTK.MultiPicklist", {"variant": v, "options": field_options(f), "columns": 1, **common})
    if c == "Checkbox" and v == "attestation":
        text = re.sub(r'<a [^>]*href="https?://([^"]+)"[^>]*>([^<]+)</a>', r"\2 (\1)", f.get("attestation_text") or f.get("help") or "")
        return el("FTK.Checkbox", {"variant": "attestation", "label": label, "labelHidden": True, "attestationTitle": label,
                                   "attestationText": html.unescape(re.sub(r"<[^>]+>", " ", text)).strip() or None, "required": common.get("required")})
    if c == "Checkbox":  # standard is the package default, the toggle
        return el("FTK.Checkbox", {"variant": None if v == "standard" else v, **common})
    if c == "NumberInput":
        extra = {"format": "currency", "variant": "standard"} if v == "currency" else {"variant": v, "min": 0}
        return el("FTK.NumberInput", {**extra, **common})
    if c == "TextArea":
        return el("FTK.TextArea", {"maxLength": int(cfg.get("maxLength", 2000)), **common})
    if c == "Repeater":
        r = f.get("repeater") or {}
        cols = [{"field": col.get("source_id") or col.get("field") or f"c{n}", "label": col.get("label"), "type": col.get("type", "text"),
                 "options": [o["label"] for o in conditions.options_of(col)] or None, "required": bool(col.get("required")),
                 "widths": col.get("widths") or [6, 6, 12]} for n, col in enumerate(r.get("columns") or [])]
        return el("FTK.Repeater", {"columns": cols, "min": 1, "max": int(r.get("max", 10)), "newButtonLabel": r.get("newButtonLabel") or "Add",
                                   "recordTitle": r.get("recordTitle") or "", "allowDelete": True})
    if c == "Address":
        return el("FTK.Address", {"showLookup": True, **common})
    if c == "DateInput":
        return el("FTK.DateInput", {"type": "date", **common})
    if c == "SignaturePad":
        return el("FTK.SignaturePad", common)
    if c == "ImageUpload":
        return el("FTK.ImageUpload", common)  # drawn empty, the state the live form opens in
    if c == "FileUpload":
        return el("FTK.FileUpload", {"acceptedFormats": cfg.get("acceptedFormats__c", ".pdf,.png,.jpg"), **common})
    if c == "Lookup":
        obj = cfg.get("objectLabel") or cfg.get("referenceTo") or "Record"
        return el("FTK.Lookup", {"variant": "customSearch" if cfg.get("enableCustomLookup__c") else "standard", "objectLabel": obj,
                                 "objectIcon": cfg.get("objectIcon") or "standard:record", "placeholder": f"Search {obj}...", **common})
    if c == "RichTextInput":
        return el("FTK.RichTextInput", common)
    return None


def gap_card(f: dict) -> dict:
    return raw(f'<div style="border: 2px dashed #b3261e; border-radius: 8px; padding: 12px; color: #b3261e; font-size: 14px">'
               f'Gap: {esc(f.get("label"))} ({esc(f.get("control"))}). Not drawn as working; listed in the plan\'s gaps.</div>')


def field_node(f: dict, ctx: Ctx, section_rule, hide_label: bool) -> dict | None:
    if planrules.is_address_part(f):
        return None  # the Address row draws the whole component
    w = f.get("widths") or [12, 12, 12]
    inner = control_node(f, hide_label) if f.get("status") != "gap" else None
    inner = inner or gap_card(f)
    own = f.get("condition") or f.get("component_rule")
    badge = tag(conditions.describe(own, ctx.index)) if own and own != section_rule else None
    return el("FTK.Column", {"large": w[0], "medium": w[1], "small": w[2]}, badge, inner)


def hides_label(section: dict) -> bool:
    """One field under the section's own text: the text is the long label, so the field's label is hidden. A plain
    checkbox keeps its label, which is the option beside the box."""
    shown = [f for f in section.get("fields") or [] if not planrules.is_address_part(f)]
    return bool(section.get("rich_text")) and len(shown) == 1 and shown[0].get("control") != "Checkbox"


SHAPE_WORDS = {"metadata": "Metadata component", "record": "Record component", "json": "JSON on this section"}


def component_note(section: dict, ctx: Ctx) -> dict | None:
    comp = ctx.components.get(section.get("component")) or {}
    name = comp.get("name") or (comp.get("catalog_match") or {}).get("name")
    text = {"reuse": f"Reuses {name}", "extend": f"Extends {name} with {len(comp.get('add_fields') or [])} field(s)",
            "shared-new": f"New shared component{': ' + name if name else ''}",
            "flow-section": f"Flow Section, built by build-flow-section{': ' + str(section.get('FlowApiName__c')) if section.get('FlowApiName__c') else ''}",
            "custom-lwc": f"Custom LWC section, built by build-custom-lwc{': ' + str(section.get('lwcComponentName__c')) if section.get('lwcComponentName__c') else ''}",
            }.get(comp.get("decision"))
    shape = comp.get("shape") or (comp.get("catalog_match") or {}).get("shape") or (comp.get("catalog_match") or {}).get("kind")
    if shape in SHAPE_WORDS and comp.get("decision") != "update":
        if comp.get("decision") == "form-only":
            text = None if shape == "json" else f"{SHAPE_WORDS[shape]}, this form only"
        else:
            text = (text + " · " if text else "") + SHAPE_WORDS[shape].lower()
    if comp.get("object") and comp.get("object") not in ("Form_Submission__c", "FlowToolKit__Form_Submission__c") and comp.get("form_template_mapping"):
        text = (text + " · " if text else "") + f"on {comp['object']}, mapped to Form Submission"
    if comp.get("decision") == "update":  # a change every other user of the component sees: a dark tag, not a quiet note
        n = len((comp.get("usage") or {}).get("consumers") or [])
        return tag(f"Updates shared component {name}, reaches {n} templates and components")
    return raw(f'<p class="fd-component">{esc(text)}</p>') if text else None


def placeholder_section(section: dict, ctx: Ctx) -> list:
    comp = ctx.components.get(section.get("component")) or {}
    flow = section.get("Component_Type__c") == "Flow"
    name = section.get("FlowApiName__c") if flow else section.get("lwcComponentName__c")
    what = comp.get("what_it_does") or comp.get("reason") or ""
    kind = "Flow Section" if flow else "Custom Lightning Web Component"
    builder = "build-flow-section" if flow else "build-custom-lwc"
    return [el("FTK.Column", {"large": 12, "medium": 12, "small": 12},
               raw(f'<div style="border: 2px dashed #6b6b6b; border-radius: 8px; padding: 16px; font-size: 15px; line-height: 1.5; color: #353535">'
                   f'<strong>{esc(kind)}: {esc(name or "to be named")}</strong><br>{esc(what)}<br>'
                   f'<span style="font-size: 13px">Drawn as a placeholder; {builder} builds it after the template.</span></div>'))]


def payment_node(ctx: Ctx) -> dict | None:
    """The payment step as a marked placeholder after the last page's sections: the package takes payment after the form,
    so the canvas shows only that it is required, and when."""
    payment = ctx.plan.get("payment")
    if not isinstance(payment, dict) or payment.get("required") is False:
        return None
    rule = payment.get("condition")
    when = conditions.describe(rule, ctx.index).replace("Shows when", "Required when") if rule else "Required on every submission"
    card = raw(f'<div style="border: 2px dashed #6b6b6b; border-radius: 8px; padding: 16px; font-size: 15px; line-height: 1.5; color: #353535">'
               f'<strong>Payment</strong><br>{esc(when)}.<br><span style="font-size: 13px">Drawn as a placeholder: the package takes payment after '
               f'the form (Payment Required{", Payment Conditions" if rule else ""} on the template); the payment page itself is not part of this design.</span></div>')
    return el("div", {}, tag(when) if rule else None, card)


def section_body(section: dict, fields: list, ctx: Ctx) -> list:
    rule = section.get("condition")
    hide = hides_label(section)
    body = []
    if section.get("rich_text"):
        body.append(el("FTK.Column", {"large": 12, "medium": 12, "small": 12},
                       el("FTK.RichText", {"variant": section.get("rich_text_variant") or "default",
                                           "html": planrules.display_markup(section["rich_text"], ctx.plan)})))
    if section.get("Component_Type__c") in ("Flow", "Lightning Web Component"):
        return body + placeholder_section(section, ctx)
    if section.get("inner_type") == "likertSection" and fields:
        ranking = section.get("matrix") == "ranking"
        mode = "Number" if ranking or section.get("Likert_Mode__c") == "Number" else "Picklist"
        scale = [str(i) for i in range(1, len(fields) + 1)] if ranking else [o["label"] for o in conditions.options_of(fields[0])]
        matrix = el("FTK.LikertMatrix", {"mode": mode, "label": section.get("Header_Title__c") or "", "scale": scale,
                                         "rows": [{"id": f.get("source_id") or f.get("field"), "label": f.get("label"), "required": bool(f.get("required"))} for f in fields]})
        if section.get("Survey_Section__c"):
            matrix = el("FTK.SurveyScope", {}, el("FTK.SurveyQuestion", {"active": True, "section": True, "total": 1,
                                                                          "required": True if any(f.get("required") for f in fields) else None}, matrix))
        return body + [el("FTK.Column", {"large": 12, "medium": 12, "small": 12}, matrix)]
    items = [(f, field_node(f, ctx, rule, hide)) for f in fields]
    items = [(f, n) for f, n in items if n]
    if section.get("Survey_Section__c"):
        cards = [el("FTK.SurveyQuestion", {"position": i, "total": len(items), "active": True, "required": True if f.get("required") else None}, n)
                 for i, (f, n) in enumerate(items, 1)]
        return body + [el("FTK.Column", {"large": 12, "medium": 12, "small": 12}, el("FTK.SurveyScope", {}, cards))]
    return body + [n for _, n in items]


def section_node(section: dict, fields: list, ctx: Ctx, continued: bool = False) -> dict:
    title = section.get("Header_Title__c")
    if continued and title:
        title = f"{title} (continued)"
    body = section_body({**section, "rich_text": None} if continued else section, fields, ctx)
    frame_name = section.get("Section_Frame__c") or ("box" if title else "clean")
    if title:
        node = el("FTK.Section", {"title": title, "subtitle": "" if continued else section.get("Header_Subtitle__c") or "",
                                  "icon": section.get("Header_Icon_Name__c") or "utility:form", "frame": frame_name,
                                  "headerStyle": section.get("Header_Style__c") or "outlined", "titleColor": BRAND, "borderColor": BRAND,
                                  "borderSize": 2, "iconColor": BRAND}, body)
    else:
        node = el("FTK.Section", {"frame": frame_name, "showHeader": False, "borderColor": BRAND, "borderSize": 2}, body)
    note = None if continued else component_note(section, ctx)
    if section.get("condition"):
        node = el("div", {"class": "fd-gate"}, tag(conditions.describe(section["condition"], ctx.index)), node)
    return el("div", {}, note, node) if note else node


# ---------------------------------------------------------------- heights
def field_height(f: dict) -> int:
    c, v = f.get("control"), f.get("variant")
    n = len(conditions.options_of(f))
    if f.get("status") == "gap":
        return 90
    if c == "Repeater":
        cols = (f.get("repeater") or {}).get("columns") or []
        return 120 + 70 * math.ceil(sum((col.get("widths") or [6])[0] for col in cols) / 12)
    if c == "Address":
        return 250 if v == "Address" else 0
    if c == "TextArea":
        return 150
    if c == "FileUpload":
        return 130
    if c == "ImageUpload":
        return 150
    if c == "SignaturePad":
        return 260
    if c == "Checkbox":
        return 130 if v == "attestation" else 44
    if c == "MultiPicklist":
        return 50 + n * 30
    if c == "Picklist" and v in ("surveybuttons", "radio", "radiolist"):
        return 50 + n * 46
    if c == "Picklist" and v == "separatedbuttons":
        return 80 if n <= 4 else 120
    return 76 + (22 if f.get("help") else 0) + (28 if f.get("condition") else 0)


def section_height(section: dict, fields: list) -> int:
    if section.get("Component_Type__c") in ("Flow", "Lightning Web Component"):
        body = 160
    elif section.get("inner_type") == "likertSection":
        body = 70 + sum(46 + 22 * (len(f.get("label") or "") // 40) for f in fields) + (110 if section.get("Survey_Section__c") else 0)
    elif section.get("Survey_Section__c"):
        body = sum(field_height(f) + 110 for f in fields if not planrules.is_address_part(f))
    else:
        rows, row, used = [], [], 0
        for f in fields:
            if planrules.is_address_part(f):
                continue
            w = (f.get("widths") or [12])[0]
            if used + w > 12:
                rows.append(row)
                row, used = [], 0
            row.append(f)
            used += w
        if row:
            rows.append(row)
        body = sum(max(field_height(f) for f in r) for r in rows)
    rich = section.get("rich_text")
    if rich:
        blocks = [b for b in re.split(r"</div>|</p>|</li>", rich) if b.strip()]
        lines = sum(max(1, math.ceil(len(html.unescape(re.sub(r"<[^>]+>", "", b))) / 125)) for b in blocks)
        body += int((40 + 24 * lines + 14 * rich.count("<p")) * 1.15)
    head = 96 if section.get("Header_Title__c") else 8
    gate = 50 if section.get("condition") else 0
    note = 24 if section.get("component") else 0
    return head + body + gate + note + (44 if (section.get("Section_Frame__c") or "box") != "clean" else 8)


def split_section(section: dict, room: float) -> list:
    """A section taller than a part is split between its fields, its title repeated with "(continued)"."""
    fields = section.get("fields") or []
    if section_height(section, fields) + 20 <= room or len(fields) < 2:
        return [(section, fields, False)]
    pieces, cur = [], []
    for f in fields:
        if cur and section_height(section, cur + [f]) + 20 > room:
            pieces.append((section, cur, bool(pieces)))
            cur = []
        cur.append(f)
    pieces.append((section, cur, bool(pieces)))
    return pieces


def page_chunks(ctx: Ctx, page: dict) -> list:
    """The page's sections in artboard-sized parts: [(pieces, height)], balanced, each under the cap. The first part carries the
    banner, indicator and any page heading; the last the button bar."""
    header = page.get("header") or {}
    head_h = 64 + 230 + (110 if header.get("title") else 0) + (70 if len(ctx.pages) > 2 and not ctx.long else 0)
    cont_h, foot_h = 124, 140
    limit = BUDGET / SCALE
    pieces = [(piece, section_height(piece[0], piece[1]) + 20) for s in page.get("sections") or [] for piece in split_section(s, limit - cont_h - foot_h)]
    total = head_h + sum(h for _, h in pieces) + foot_h
    parts = [([p for p, _ in pieces], total)]
    for n in range(max(1, math.ceil(total / limit)), len(pieces) + 2):
        target, parts, cur, h = total / n, [], [], head_h
        for piece, sh in pieces:
            if cur and h + sh / 2 > target and len(parts) < n - 1:
                parts.append((cur, h))
                cur, h = [], cont_h
            cur.append(piece)
            h += sh
        parts.append((cur, h + foot_h))
        if all(height <= limit for _, height in parts) or n > len(pieces):
            break
    return [(p, max(400, int(math.ceil(h * SCALE / 20) * 20))) for p, h in parts]


# ---------------------------------------------------------------- boards
def part_name(base: str, n: int) -> str:
    return f"{base}.dc.html" if n == 1 else f"{base}-part{n}.dc.html"


def stage_labels(ctx: Ctx) -> list:
    return [p.get("Page_Label__c") or f"Page {i}" for i, p in enumerate(ctx.pages, 1)]


def buttons(ctx: Ctx, index: int, last: bool) -> dict:
    position = planrules.button_position(ctx.plan)
    submit = ctx.template.get("Submit_Button_Label__c") or planrules.submit_default(ctx.plan)
    if ctx.long:  # inside a step the package shows Return, Save Progress, Mark Complete; the review step submits
        return el("FTK.Buttons", {"position": position, "alignment": "center", "saveProgress": True, "backLabel": "Return",
                                  "nextLabel": "Mark Complete", "submitLabel": submit})
    labels = stage_labels(ctx)
    page = ctx.pages[index]
    return el("FTK.Buttons", {"position": position, "alignment": "spread",
                              "backLabel": labels[index - 1] if ctx.multipage and index > 0 else None,
                              "nextLabel": None if last else (page.get("Button_Label__c") or "Continue"),
                              "lastPage": True if last else None, "submitLabel": submit})


def stage_rail(ctx: Ctx, current: str) -> dict:
    return el("div", {"class": "form-card", "style": "width: 300px; flex: none; padding: 24px 16px; box-sizing: border-box"},
              el("FTK.StageIndicator", {"type": "vertical", "stages": stage_labels(ctx) + ["Review"], "current": current}))


def page_boards(ctx: Ctx, index: int) -> list:
    page = ctx.pages[index]
    labels = stage_labels(ctx)
    chunks = page_chunks(ctx, page)
    width = STAGES_WIDTH if ctx.long else FORM_WIDTH
    boards = []
    for n, (pieces, height) in enumerate(chunks, 1):
        first, final = n == 1, n == len(chunks)
        last_page = index == len(ctx.pages) - 1 and final and not ctx.long
        header = page.get("header") or {}
        heading = el("FTK.PageHeader", {"headerStyle": header.get("style") or "classic", "title": header["title"],
                                        "subtitle": header.get("subtitle") or page.get("Description__c") or "", "icon": header.get("icon") or "utility:info",
                                        "titleColor": BRAND, "iconColor": BRAND}) if first and header.get("title") else None
        sections = [section_node(s, fields, ctx, continued) for s, fields, continued in pieces]
        pay = payment_node(ctx) if final and index == len(ctx.pages) - 1 and not ctx.long else None  # stages: on the review screen
        if pay:
            sections.append(pay)
            height += 220
        bar = buttons(ctx, index, last_page) if final else None
        notes = []
        if ctx.multipage:
            notes.append(f" · page {index + 1} of {len(ctx.pages)}")
        if ctx.long:
            notes.append(f" · stages mode, step {index + 1}")
        if len(chunks) > 1:
            notes.append(f" · part {n} of {len(chunks)}")
        line = source_line(ctx, "".join(notes))
        body = el("div", {"class": "form-body"}, heading, sections)
        if ctx.long:
            top = el("div", {"class": "form-card"}, banner(ctx)) if first else None
            card = el("div", {"class": "form-card", "style": "flex: 1; min-width: 0"}, body, bar)
            inner = [line, top, el("div", {"style": "display: flex; gap: 24px; align-items: flex-start"}, stage_rail(ctx, labels[index]), card)]
        else:
            indicator = (el("div", {"style": "padding: 16px 40px 0"}, el("FTK.StageIndicator", {"type": "base", "stages": labels, "current": labels[index]}))
                         if first and len(ctx.pages) > 2 else None)
            inner = [line, el("div", {"class": "form-card"}, banner(ctx) if first else None, indicator, body, bar)]
        title = f"{page.get('Page_Label__c') or ctx.title}" + (f" (page {index + 1} of {len(ctx.pages)})" if ctx.multipage else "")
        base = f"{ctx.slug}-p{index + 1}" if ctx.multipage else ctx.slug
        boards.append({"name": part_name(base, n), "title": title + (f" (part {n} of {len(chunks)})" if len(chunks) > 1 else ""),
                       "w": width, "h": height, "tree": form_style(ctx, frame(width, height, inner)), "interactive": True})
    return boards


def stages_board(ctx: Ctx) -> dict:
    stages = []
    for page in ctx.pages:
        titled = [{"title": s["Header_Title__c"], "description": s.get("Header_Subtitle__c") or ""} for s in page.get("sections") or [] if s.get("Header_Title__c")]
        stages.append({"title": page.get("Page_Label__c"), "description": page.get("Description__c") or "", "status": "todo",
                       "hasStarted": False, "progress": 0, "time": planrules.page_minutes(page), "startLabel": page.get("Button_Label__c") or "Start",
                       "substeps": titled if len(titled) >= 2 else []})  # the accordion lists sections only when two or more are titled
    height = int(math.ceil((520 + 170 * len(stages) + 44 * sum(len(s["substeps"]) for s in stages)) / 20) * 20)
    height = min(max(height, 1200), CAP)
    subtitle = f"{len(ctx.pages)} steps, {planrules.minutes_range(planrules.form_seconds(ctx.plan))}. Save your progress and come back any time."
    tree = form_style(ctx, frame(FORM_WIDTH, height, source_line(ctx, " · stages mode with Save Progress"),
                                 el("div", {"class": "form-card"}, banner(ctx),
                                    el("div", {"class": "form-body"}, el("FTK.StagesOverview", {"title": ctx.title, "subtitle": subtitle, "stages": stages})))))
    return {"name": f"{ctx.slug}-stages.dc.html", "title": "Stages overview (start screen)", "w": FORM_WIDTH, "h": height, "tree": tree}


def review_type(f: dict) -> str:
    c, v = f.get("control"), f.get("variant")
    return {"NumberInput": "currency" if v == "currency" else "double", "DateInput": "date", "FileUpload": "fileupload",
            "Checkbox": "boolean", "MultiPicklist": "multipicklist"}.get(c) or ("tel" if c == "FormattedInput" and v == "phone" else "string")


def review_boards(ctx: Ctx) -> list:
    """The review screen that closes a stages form: every page's questions by section, answers empty, then the real submit."""
    rows = []
    for page in ctx.pages:
        sections = []
        for s in page.get("sections") or []:
            fields = [{"label": f.get("label"), "value": "", "type": review_type(f)} for f in s.get("fields") or [] if not planrules.is_address_part(f)]
            if fields:
                sections.append({"title": s.get("Header_Title__c") or "", "showHeader": bool(s.get("Header_Title__c")), "fields": fields})
        if sections:
            rows.append({"label": page.get("Page_Label__c"), "sections": sections})
    page_h = lambda p: 44 + 56 * len(p["sections"]) + 30 * sum(len(s["fields"]) for s in p["sections"])
    chunks, cur, h = [], [], 520
    for p in rows:
        if cur and h + page_h(p) > BUDGET:
            chunks.append((cur, h))
            cur, h = [], 260
        cur.append(p)
        h += page_h(p)
    chunks.append((cur, h))
    submit = ctx.template.get("Submit_Button_Label__c") or planrules.submit_default(ctx.plan)
    out = []
    for n, (pages, height) in enumerate(chunks, 1):
        final = n == len(chunks)
        height = int(math.ceil(height / 20) * 20)
        bar = el("FTK.Buttons", {"position": planrules.button_position(ctx.plan), "alignment": "center", "saveProgress": True, "backLabel": "Return",
                                 "lastPage": True, "submitLabel": submit}) if final else None
        pay = payment_node(ctx) if final else None
        if pay:
            height += 220
        card = el("div", {"class": "form-card", "style": "flex: 1; min-width: 0"},
                  el("div", {"class": "form-body"}, el("FTK.ReviewPage", {"title": "Review", "subtitle": "Check your answers, then submit. Edit opens that section.",
                                                                          "pages": pages}), pay), bar)
        note = f" · review screen, the last step" + (f" · part {n} of {len(chunks)}" if len(chunks) > 1 else "")
        tree = form_style(ctx, frame(STAGES_WIDTH, height, source_line(ctx, note), el("div", {"class": "form-card"}, banner(ctx)) if n == 1 else None,
                                     el("div", {"style": "display: flex; gap: 24px; align-items: flex-start"}, stage_rail(ctx, "Review"), card)))
        out.append({"name": part_name(f"{ctx.slug}-review", n), "title": "Review (last step)" + (f" (part {n} of {len(chunks)})" if len(chunks) > 1 else ""),
                    "w": STAGES_WIDTH, "h": height, "tree": tree, "interactive": True})
    return out


def source_boards(ctx: Ctx, screenshot_url: str | None, screenshot_size: tuple) -> list:
    """The original form beside its redesign: its screenshot (an uploaded canvas image) cut into windows under the cap, or the
    source's questions in order. None for a brief, which has no source to show."""
    src = ctx.plan.get("source") or {}
    if (src.get("platform") or "brief") == "brief":
        return []
    fields = [f for f in (ctx.ir or {}).get("fields") or [] if f.get("present_in_rendered_form", True) and f.get("input_type") != "hidden" and f.get("label")]
    url = src.get("url")
    link = f' · <a href="{esc(url)}" target="_blank" rel="noopener">open the source form</a>' if url else ""
    head = (f'<h1 style="margin: 0; font-size: 36px; font-weight: 600">Original form: {esc(ctx.title)}</h1>'
            f'<p style="margin: 0; font-size: 15px">{esc(src.get("platform"))} {esc(src.get("form_id") or "")} · {len(fields)} questions{link}</p>')
    parts = []
    if screenshot_url and screenshot_size[0]:
        w, h = screenshot_size
        shown = int(h * 1000 / w)
        window = BUDGET - 260
        count = max(1, math.ceil(shown / window))
        for n in range(1, count + 1):
            win = min(window, shown - (n - 1) * window)
            parts.append((head + (f'<p style="margin: 0; font-size: 13px">Part {n} of {count}</p>' if count > 1 else "")
                          + f'<div style="width: 1000px; height: {win}px; overflow: hidden; border: 1px solid #d9d9d9; background: #ffffff">'
                          f'<img src="{esc(screenshot_url)}" alt="{esc(ctx.title)}, the source form" style="display: block; width: 1000px; height: auto; '
                          f'margin-top: -{(n - 1) * window}px"></div>', win + 260))
    elif fields:
        rows = [f'<tr style="border-bottom: 1px solid #e5e5e5"><td style="padding: 6px 8px; width: 70%">{esc(" ".join(str(f["label"]).split()))}'
                f'{" *" if f.get("required") else ""}</td><td style="padding: 6px 8px">{esc(f.get("input_type") or f.get("tag") or "")}'
                f'{(" · " + str(len(f["options"])) + " options") if f.get("options") else ""}</td></tr>' for f in fields]
        per = (BUDGET - 320) // 40
        chunks = [rows[i:i + per] for i in range(0, len(rows), per)]
        for n, chunk in enumerate(chunks, 1):
            note = "No screenshot of the source yet: its questions in order, * required." + (f" Part {n} of {len(chunks)}." if len(chunks) > 1 else "")
            parts.append((head + f'<p style="margin: 0; font-size: 13px">{note}</p><table style="width: 100%; border-collapse: collapse; font-size: 14px">'
                          + "".join(chunk) + "</table>", 320 + 40 * len(chunk)))
    else:
        parts.append((head + '<p style="margin: 0; font-size: 14px">No screenshot or question list captured; open the source with the link above.</p>', 400))
    out = []
    for n, (inner, h) in enumerate(parts, 1):
        h = int(math.ceil(h / 20) * 20)
        tree = el("div", {"style": f"width: 1100px; min-height: {h}px; box-sizing: border-box; padding: 40px 50px; display: flex; flex-direction: column; "
                                   f"gap: 14px; background: #ffffff; color: #353535; font-family: {ctx.style['font_css']}"}, raw(inner))
        out.append({"name": part_name(f"{ctx.slug}-source", n), "title": f"Original form: {ctx.title}" + (f" (part {n} of {len(parts)})" if len(parts) > 1 else ""),
                    "w": 1100, "h": h, "tree": tree})
    return out


def form_boards(ctx: Ctx, screenshot_url: str | None = None, screenshot_size: tuple = (0, 0)) -> list:
    """One form's boards in canvas order: the source, the stages start screen (long forms), each page, the review."""
    out = source_boards(ctx, screenshot_url, screenshot_size)
    if ctx.long:
        out.append(stages_board(ctx))
    for i in range(len(ctx.pages)):
        out += page_boards(ctx, i)
    if ctx.long:
        out += review_boards(ctx)
    return out


def sample_message(markup: str, plan: dict) -> str:
    sample = (plan.get("emails") or {}).get("sample_merge") or {}
    return re.sub(r"\{\{(\w+)\}\}", lambda m: esc(sample.get(m.group(1), m.group(0))), markup or "")


def confirmations_board(ctxs: list) -> dict:
    ctx0 = ctxs[0]

    def card_h(markup):
        blocks = [html.unescape(re.sub(r"<[^>]+>", "", b[1])) for b in re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>", markup or "", re.S)] or [markup or ""]
        return 260 + sum(36 * max(1, math.ceil(len(b) / 50)) + 24 for b in blocks)
    rows = [ctxs[i:i + 3] for i in range(0, len(ctxs), 3)]
    h = int(math.ceil((96 + sum(max(card_h(c.template.get("Confirmation_Page_Message__c")) for c in row) + 32 for row in rows)) / 20) * 20)
    h = min(max(h, 800), CAP)
    cards = [el("div", {"style": "display: flex; flex-direction: column; gap: 8px"},
                raw(f'<h2 style="margin: 0; font-family: {esc(c.style["heading_font_css"])}; font-size: 28px; color: {c.style["heading_color"]}; font-weight: 400">'
                    f'{esc(c.title)}</h2>'),
                el("div", {"class": "form-card", "style": "padding: 8px"},
                   el("FTK.ConfirmationPage", {"message": sample_message(planrules.display_markup(c.template.get("Confirmation_Page_Message__c"), c.plan), c.plan)})))
             for c in ctxs]
    tree = form_style(ctx0, el("div", {"style": f"width: 1800px; min-height: {h}px; box-sizing: border-box; padding: 48px; display: grid; "
                                                "grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px; align-content: start"}, cards))
    return {"name": "Confirmations.dc.html", "title": "Confirmation messages", "w": 1800, "h": h, "tree": tree}


EMAIL_USES = (("confirmation", "Confirmation email (Email_Template_Name_Confirmation__c)"),
              ("saved", "Save Progress email (Email_Template_Name_Saved__c)"),
              ("resume", "Resume link email, stages button (Email_Template_Name_Resume_Form__c)"))


def email_boards(ctxs: list, images: dict) -> list:
    cards = []
    for c in ctxs:
        emails = c.plan.get("emails") or {}
        sample = emails.get("sample_merge") or {}
        for key, use in EMAIL_USES:
            email = emails.get(key)
            if not email:
                continue
            body = letterhead.inner_body(letterhead.html(email, {"logo": images.get("logo"), "banner": images.get("banner")}, emails.get("letterhead") or {},
                                                         {**c.style, "button_radius": c.style.get("Corner radius", "4px")}))
            cards.append(raw(f'<div style="display: flex; flex-direction: column; gap: 8px"><h2 style="margin: 0; font-size: 24px; font-weight: 400; '
                             f'color: {c.style["heading_color"]}">{esc(c.title)}</h2><p style="margin: 0; font-size: 14px; color: #353535">{esc(use)} · '
                             f'<strong>{esc(email.get("name", ""))}</strong> · Subject: {letterhead.merge_sample(esc(email.get("subject", "")), sample)}</p>'
                             f'<div style="background: {c.style["background"]}; border-radius: 8px">{letterhead.merge_sample(body, sample)}</div></div>'))
    if not cards:
        return []
    per = 3 * ((BUDGET - 100) // 1350)
    chunks = [cards[i:i + per] for i in range(0, len(cards), per)]
    out = []
    for n, chunk in enumerate(chunks, 1):
        rows = math.ceil(len(chunk) / 3)
        h = 1400 if rows == 1 else 1350 * rows
        tree = el("div", {"style": f"width: 2100px; min-height: {h}px; box-sizing: border-box; padding: 48px; display: grid; "
                                   "grid-template-columns: repeat(3, 640px); gap: 40px 34px; align-content: start"}, chunk)
        out.append({"name": part_name("Emails", n), "title": "Email templates (Lightning, on Form Submission)" + (f" (part {n} of {len(chunks)})" if len(chunks) > 1 else ""),
                    "w": 2100, "h": h, "tree": tree})
    return out


AUDIT_COLUMNS = ["Form", "Source ID", "Label", "Control", "Object", "Field", "Component", "Placement", "Status", "Page", "Section"]


def audit_rows(ctx: Ctx) -> list:
    rows = []
    for page in ctx.pages:
        for s in page.get("sections") or []:
            comp = ctx.components.get(s.get("component")) or {}
            comp_text = f"{comp.get('decision', '')} {comp.get('name') or ''}".strip() + (f" ({comp['shape']})" if comp.get("shape") else "")
            for f in s.get("fields") or []:  # Address parts are listed too: each lands on its own field
                base =[ctx.title, f.get("source_id") or "", f.get("label") or "", f"{f.get('control')} · {f.get('variant') or 'standard'}",
                        f.get("object") or "Form_Submission__c", f.get("field") or "", comp_text, f.get("placement") or "", f.get("status") or "",
                        page.get("Page_Label__c") or "", s.get("Header_Title__c") or "(follows the section above)"]
                cols = (f.get("repeater") or {}).get("columns")
                if cols:
                    for col in cols:
                        rows.append([base[0], col.get("source_id") or "", col.get("label") or "", f"Repeater column · {col.get('type', 'text')}",
                                     col.get("object") or base[4], col.get("field") or "", comp_text, base[7], base[8], base[9], base[10]])
                else:
                    rows.append(base)
    return rows


def audit_boards(rows: list, style: dict, form_count: int) -> list:
    per = (BUDGET - 260) // 38
    chunks = [rows[i:i + per] for i in range(0, len(rows), per)] or [[]]
    out = []
    shown = [0, 1, 2, 3, 5, 6, 8, 9]
    for n, chunk in enumerate(chunks, 1):
        h = int(math.ceil((260 + len(chunk) * 38) / 20) * 20)
        bg = {"gap": "#fde2e2", "verify": "#fff8c4"}
        head = "".join(f'<th style="padding: 6px 8px">{esc(AUDIT_COLUMNS[i])}</th>' for i in shown)
        body = "".join(f'<tr style="background: {bg.get(r[8], "#ffffff")}; border-bottom: 1px solid #e5e5e5">'
                       + "".join(f'<td style="padding: 5px 8px">{esc(r[i])}</td>' for i in shown) + "</tr>" for r in chunk)
        part = f" (part {n} of {len(chunks)})" if len(chunks) > 1 else ""
        markup = (f'<h1 style="margin: 0; font-size: 44px; color: {style["heading_color"]}; font-weight: 400">Field audit: where every answer lands{part}</h1>'
                  f'<p style="margin: 0; font-size: 14px">{len(rows)} fields across {form_count} form(s). Yellow: verify (a proposed new field or an '
                  f'unconfirmed setting). Red: a gap the package cannot do yet. The same rows are in field-audit.csv.</p>'
                  f'<table style="width: 100%; border-collapse: collapse; font-size: 12px"><thead><tr style="background: #353535; color: #ffffff; '
                  f'text-align: left">{head}</tr></thead><tbody>{body}</tbody></table>')
        tree = el("div", {"style": f"width: 1800px; min-height: {h}px; box-sizing: border-box; padding: 48px; display: flex; flex-direction: column; "
                                   f"gap: 16px; background: #ffffff; color: #353535; font-family: {style['font_css']}"}, raw(markup))
        out.append({"name": part_name("FieldAudit", n), "title": "Field audit" + part, "w": 1800, "h": h, "tree": tree})
    return out


def brand_board(ctx: Ctx) -> dict | None:
    """The brand as chosen: logo, colors with their roles, fonts and buttons, tone and general copy. Only what was picked."""
    board = ctx.plan.get("brand_board")
    if not board:
        return None
    s = ctx.style
    swatches = "".join(f'<div style="display: flex; flex-direction: column; gap: 6px"><div style="width: 180px; height: 96px; background: {esc(color)}; '
                       f'border: 1px solid #d9d9d9"></div><strong style="font-size: 14px">{esc(name)}</strong><span style="font-size: 13px">{esc(color)} · '
                       f'{esc(role)}</span></div>' for name, color, role in board.get("swatches") or
                       [("Brand", s["brand"], "buttons, frames"), ("Heading", s["heading_color"], "titles"), ("Accent", s["accent"], "tags"),
                        ("Background", s["background"], "page")])
    logo = ctx.image("logo")
    logo_html = f'<img src="{esc(logo)}" alt="{esc(board.get("logo_alt", "Logo"))}" style="height: 120px">' if logo else \
        '<div style="width: 120px; height: 120px; border: 2px dashed #8a8a8a; display: flex; align-items: center; justify-content: center; font-size: 13px">logo: upload pending</div>'
    copy = "".join(f'<p style="margin: 0; font-size: 16px; line-height: 1.6; max-width: 1200px">{esc(p)}</p>' for p in board.get("copy") or [])
    markup = (f'<div style="display: flex; align-items: center; gap: 28px">{logo_html}<div><h1 style="margin: 0; font-family: {esc(s["heading_font_css"])}; '
              f'font-size: 56px; color: {s["heading_color"]}">{esc(board.get("headline") or ctx.title)}</h1><p style="margin: 0; font-size: 16px">'
              f'{esc(board.get("source_line") or "")}</p></div></div>'
              f'<h2 style="margin: 0; font-size: 32px; color: {s["heading_color"]}">Colors</h2><div style="display: flex; gap: 24px; flex-wrap: wrap">{swatches}</div>'
              f'<h2 style="margin: 0; font-size: 32px; color: {s["heading_color"]}">Type and tone</h2>'
              f'<p style="margin: 0; font-family: {esc(s["heading_font_css"])}; font-size: 40px">{esc(s.get("heading_font", "Heading"))}</p>'
              f'<p style="margin: 0; font-size: 18px">{esc(s.get("font", "Body"))}: body text, labels and help.</p>'
              f'<p style="margin: 0; font-size: 16px; line-height: 1.6">{esc(board.get("tone") or "")}</p>'
              + (f'<h2 style="margin: 0; font-size: 32px; color: {s["heading_color"]}">General copy</h2>{copy}' if copy else ""))
    tree = el("div", {"style": f"width: 1600px; min-height: 1800px; box-sizing: border-box; padding: 56px; display: flex; flex-direction: column; gap: 32px; "
                               f"background: {s['background']}; color: #353535; font-family: {s['font_css']}"}, raw(markup))
    return {"name": "Main.dc.html", "title": "Brand: selected assets, copy and tone", "w": 1600, "h": 1800, "tree": tree}


def design_notes(ctx: Ctx) -> str | None:
    lines = [f"- {n}" for n in ctx.plan.get("notes") or []]
    for where, rule in conditions.iter_rules(ctx.plan):
        lines.append(f"- {where}: {conditions.describe(rule, ctx.index)}")
    payment = ctx.plan.get("payment")
    if isinstance(payment, dict) and payment.get("required") is not False:
        rule = payment.get("condition")
        lines.append("- Payment: " + (conditions.describe(rule, ctx.index).replace("Shows when", "required when") if rule else "required on every submission")
                     + "; guests need Read on Payment Conditions and every field the rule reads")
    for p in ctx.plan.get("url_parameters") or []:
        target = ctx.index.get(p.get("field")) or {}
        lines.append(f"- URL parameter {p.get('param')} fills {target.get('label') or p.get('field')} ({p.get('field')}); guests need Edit on it")
    lines += [f"- Ask: {q.get('ask')}" for q in ctx.plan.get("questions") or []]
    lines += [f"- Gap: {g.get('feature')}: {g.get('needed')}" for g in ctx.plan.get("gaps") or []]
    return "\n".join(["Design notes"] + lines) if lines else None
