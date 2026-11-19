"""The one table from a plan field to the package keys that draw it, shared by every builder.

buildtemplate.py (local sections, extended and shared components) and any other script that writes component JSON
call package_keys(), so a design cannot be translated two ways. A second translator is how a drawing and a build drift
apart: a hidden label drops out of what a screen reader announces, a consent's wording lands in 255-character help text under the box, a
shared component offers an answer the form did not. Keys come back unprefixed (`labelVariant__c`); the caller adds the
namespace placeholder.

Labels, help text and placeholders are Text(255) on a form field. Longer wording goes whole into the package's long
twins (customLabelLong__c, helpTextLong__c, placeholderLong__c), which every reader takes first with the short field as
the fallback. An org whose Flow Tool Kit has no long twins gets the old 255-character cut.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "_shared" / "lib"))
import addressparts  # noqa: E402  the address rule, one copy for every skill

N = "FlowToolKit__"
STAR = "*__"

# The control's variant is stored in one of these keys (the design system README's "Maps to" for each control).
VARIANT_KEY = {"Picklist": "picklistType__c", "MultiPicklist": "picklistType__c", "Checkbox": "booleanType__c",
               "NumberInput": "numberType__c", "TextInput": "stringType__c", "TextArea": "stringType__c",
               "FileUpload": "longTextType__c", "ImageUpload": "richTextType__c", "SignaturePad": "richTextType__c",
               "Lookup": "referenceFieldOverrideType__c"}
# Variants that are the field type itself, with no package key (an Email field draws as email).
TYPE_VARIANTS = {"FormattedInput", "DateInput", "Address", "Repeater"}
# A form field's Text(255) wording and the long twin the package reads first (Form_Component_Field__c; the renderer's
# longTextValue and the server's applyLongTextFallback take the twin, else the short field).
LONG_TEXT = {"customLabel__c": "customLabelLong__c", "helpText__c": "helpTextLong__c", "placeholder__c": "placeholderLong__c"}
SHORT_LIMIT = 255


def _paragraph(text: str) -> str:
    return text if text.lstrip().startswith("<") else f"<p>{text}</p>"


def package_keys(field: dict, long_text: bool = True, cut: list | None = None) -> dict:
    """Package keys for one plan field, beyond name, position, widths and required.

    long_text: the org has the long twins (the default), so wording past 255 characters goes whole into them. False: an
    older org, where it is cut at 255 as before, and each cut key is added to `cut`."""
    control, variant = field.get("control") or "", field.get("variant") or ""
    keys: dict = {}
    if control == "Address":
        keys["addressFieldType__c"] = variant
    if field.get("label"):
        # The Address row's label names the whole address for screen readers, the "is required" message and the
        # read-only view; on screen its address section's header shows it (address_title)
        keys["customLabel__c"] = field["label"]
    key = VARIANT_KEY.get(control)
    # A Lookup's customSearch variant exists only in Flow screens; on a Form Template the standard lookup draws.
    if key and variant and variant != "standard" and control not in TYPE_VARIANTS and not (control == "Lookup" and variant == "customSearch"):
        keys[key] = variant
    if variant == "attestation":
        # The design draws the statement inside the card and no label above it. Help text is capped at 255 characters
        # and renders under the card, so the statement goes in Label_Rich_Text__c, with the label as the card's bold
        # first line, and the label above the card is hidden.
        keys["booleanType__c"] = "attestation"
        keys["labelVariant__c"] = "none"
        statement = field.get("attestation_text") or field.get("help")
        if statement:
            title = f"<p><strong>{field['label']}</strong></p>" if field.get("label") else ""
            keys["Label_Rich_Text__c"] = title + _paragraph(statement)
        if field.get("attestation_text") and field.get("help"):
            keys["helpText__c"] = field["help"]
            keys["helpTextDisplay__c"] = field.get("helpTextDisplay") or "Below Field"
    elif field.get("help"):
        keys["helpText__c"] = field["help"]
        keys["helpTextDisplay__c"] = field.get("helpTextDisplay") or "Below Field"
    if field.get("label_hidden") and variant != "attestation":
        # label-hidden hides the label on screen but keeps it for screen readers. The consent card above keeps none:
        # its statement inside the card is the label.
        keys["labelVariant__c"] = "label-hidden"
    if control == "MultiPicklist":
        keys["picklistColumnsSize__c"] = f"size_1-of-{int(field.get('columns') or 1)}"
    values = [str(o.get("value", o.get("label"))) if isinstance(o, dict) else str(o) for o in field.get("options") or []]
    if values and (control in ("Picklist", "MultiPicklist") or "Yes_No_Question" in (field.get("field") or "")):
        # The form shows only the planned options, in the plan's order: a field (a packaged one, or a new one several
        # forms share) holds more values than one form offers. A value the record type lacks is skipped by the package,
        # which the build reports (picklists.py)
        keys["picklistOptionOverrides__c"] = ";".join(values)
    for name, value in (field.get("config") or {}).items():
        if name.endswith("__c") or name.endswith("__r"):
            keys[name.replace(N, "").replace(STAR, "")] = value
    descriptions = option_settings(field, keys.get("picklistOptionSettings__c"))
    if descriptions:
        keys["picklistOptionSettings__c"] = descriptions
    return fit_long_text(keys, long_text, cut)


def fit_long_text(keys: dict, long_text: bool = True, cut: list | None = None) -> dict:
    """Wording past 255 characters in a Text(255) key moves whole into its long twin, and the short key is left out (a
    save would otherwise copy the short value over the twin). Without the twins it is cut at 255, as before."""
    for short, long in LONG_TEXT.items():
        value = keys.get(short)
        if not isinstance(value, str) or len(value) <= SHORT_LIMIT:
            continue
        if long_text:
            keys[long] = keys.pop(short)
        else:
            keys[short] = value[:SHORT_LIMIT]
            if cut is not None:
                cut.append(short)
    return keys


def option_settings(field: dict, existing: str | None = None) -> str | None:
    """A choice's planned label ({value, label} in options, when it differs from the value) and its explanation, only
    when the source form or the review supplied one (plan key option_descriptions, {stored value: text}), written into
    the package's per-option settings JSON ({value: {label, description, score, icon}}). Any icon already there is kept."""
    supplied = {value: text for value, text in (field.get("option_descriptions") or {}).items() if text and str(text).strip()}
    labels = {str(o.get("value")): str(o["label"]) for o in field.get("options") or []
              if isinstance(o, dict) and o.get("value") is not None and o.get("label") and o.get("label") != o.get("value")}
    if not supplied and not labels:
        return None
    try:
        settings = json.loads(existing) if existing else {}
    except ValueError:
        settings = {}
    for value, label in labels.items():
        settings.setdefault(value, {})["label"] = label
    for value, text in supplied.items():
        settings.setdefault(value, {})["description"] = str(text).strip()
    return json.dumps(settings)


def section_parts(section: dict) -> list[dict]:
    """A section's inner parts in render order: its own text block first, then its fields.

    The design draws the section text above the field grid; the package lines it up only when it is its own
    richTextSection, so a text block and fields never share one inner section. An address draws only in its own
    addressSection (shared lib addressparts.py), so each address in a section of other fields becomes its own part, in
    its place among them. `inner_sections` in the plan wins."""
    explicit = section.get("inner_sections")
    if explicit:
        return explicit
    fields = section.get("fields") or []
    text = section.get("rich_text")
    # Form Builder lists inner sections by Label, so an untitled part is named after its section.
    name = section.get("label") or section.get("Header_Title__c") or section.get("Title__c")
    parts = []
    if text:
        # frame clean: without it the package indents a JSON richTextSection 8px left of the fields below it
        parts.append({"type": "richTextSection", "rich_text": text, "variant": section.get("rich_text_variant") or "default", "frame": "clean",
                      "label": f"{name}: intro" if name else None})
    if fields or not text:
        runs = addressparts.groups(fields) or [("fields", [])]
        for n, (kind, run) in enumerate(runs):
            first = n == 0
            row = next((f for f in run if addressparts.plan_variant(f) == "Address"), {}) if kind == "address" else {}
            label = (None if section.get("inner_title") else name) if first else (row.get("label") or (f"{name}, part {n + 1}" if name else None))
            title = section.get("inner_title") if first else None
            if not title and address_title(section, row):
                title = row["label"]
            parts.append({"title": title, "label": label, "fields": run,
                          "type": addressparts.SECTION_TYPE if kind == "address" else section.get("inner_type"),
                          "likert_mode": section.get("likert_mode") or section.get("Likert_Mode__c"), "likert_scale": section.get("likert_scale")})
    return parts


def address_title(section: dict, row: dict) -> bool:
    """Whether an address's own section shows its row's label as a header. The package draws an editable address with
    its label hidden and names it by its section header, as Form Builder's New Address section does, so the label goes
    there; not when the section's own header already says the same words."""
    label = str(row.get("label") or "").strip()
    header = str(section.get("Header_Title__c") or "").strip() if section.get("Show_Header__c") is not False else ""
    return bool(label) and label.casefold() != header.casefold()


def address_problems(section: dict, where: str) -> list[str]:
    """What stops the package drawing an address in this section, part by part (shared lib addressparts.py)."""
    return [p for n, part in enumerate(section_parts(section))
            for p in addressparts.section_problems(part.get("fields") or [], part.get("type"), f"{where}, inner section {n + 1}")]


def submission_map(mapping: dict | None) -> str | None:
    """The plan's form_template_mapping as the package's Submission Field Map.

    The plan writes {apply_to, fields: {component field: Form Submission field}}; the package stores
    {"lookupField": "<Form Submission lookup>" or "ALL", "fields": {Form Submission field: component field}}, keyed by
    the Form Submission field (one mapping per Form Submission field; one component field may feed several)."""
    if not mapping or not mapping.get("fields"):
        return None
    apply_to = str(mapping.get("apply_to") or "all").strip()
    lookup = "ALL" if apply_to.lower().startswith("all") else apply_to.replace(N, STAR)
    fields: dict = {}
    for source, targets in mapping["fields"].items():
        for target in (targets if isinstance(targets, list) else [targets]):
            if target:
                fields[str(target).replace(N, STAR)] = source
    return json.dumps({"lookupField": lookup, "fields": fields})


FEATURE_TAGS = {"Address": "Address", "SignaturePad": "Signature", "FileUpload": "File Upload", "ImageUpload": "Image Upload",
                "Repeater": "Repeater", "MultiPicklist": "Multi-select", "DateInput": "Dates", "NumberInput": "Amounts", "Lookup": "Lookup"}


def feature_tags(fields: list, has_rule: bool = False, has_text: bool = False) -> list:
    """Filing tags for what a component holds: features that cut across folders (Address, Signature, Conditional Logic),
    never the object."""
    tags = []
    for f in fields or []:
        tag = FEATURE_TAGS.get(f.get("control") or "")
        if f.get("variant") == "attestation" or "Consent" in (f.get("label") or ""):
            tag = "Consent"
        if tag and tag not in tags:
            tags.append(tag)
    if has_rule or any(f.get("condition") for f in fields or []):
        tags.append("Conditional Logic")
    if has_text:
        tags.append("Instructions")
    return tags


def filing(folder: str, kind: str, fields: list, has_rule: bool = False, has_text: bool = False, workstream: str = "") -> dict:
    """Folder and Tags for a built component: the folder given, and tags for the workstream, the kind (Shared component or
    Template section) and the features it holds, comma separated as Form Builder shows them."""
    tags = [t for t in [workstream, kind] if t] + feature_tags(fields, has_rule, has_text)
    return {"Folder__c": folder, "Tags__c": ", ".join(dict.fromkeys(tags))}
