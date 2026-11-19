"""Turn a Form Template export (see ``extract.py``) into the shared IR.

Every section form is normalized to one shape first, whichever of the three
sources it lives in, so the IR never learns which one it was. Each IR field
also carries ``target`` (the Salesforce object and field it writes today) and
``component`` (where its form lives), because a clean-up or redesign decides
reuse and placement from exactly those two facts.

Each page section keeps what the package draws for it (``Component_Type__c``):
a Field Set, Repeater or Table keeps its form, a Flow its flow, a Lightning Web
Component its component name and Display Text its text, so a redesign never
mistakes a repeater for a set of single questions. Section show and hide rules
(``Conditional_Logic__c`` on the section, the page rule's shape) become
condition trees, a mapped component's Submission Field Map becomes each field's
``submission_landing``, and the header form, banners, header tags and logo
become ``form.branding``.
"""

from __future__ import annotations

import json
import re

from ... import conditions as conditions_module
from ... import ir

STAR = "*__"

_TYPE_MAP = {
    "string": "text", "textarea": "textarea", "email": "email", "phone": "tel", "url": "url",
    "double": "number", "int": "number", "long": "number", "percent": "number", "currency": "number",
    "date": "date", "datetime": "datetime", "time": "time", "boolean": "checkbox",
    "picklist": "select", "multipicklist": "choice-group", "reference": "select",
    "base64": "file", "encryptedstring": "text", "id": "hidden",
}
_VALIDATION = {"email": "email", "phone": "phone", "date": "date", "datetime": "datetime",
               "double": "number", "percent": "number", "currency": "currency",
               "int": "integer", "long": "integer", "boolean": "checkbox", "multipicklist": "checkbox"}
_CHOICE_DISPLAYS = ("radio", "visual", "button", "checkboxgroup", "pill", "card", "toggle")

# Component_Type__c values (Form_Template_Page_Section__c), and the formula
# checkboxes that mirror them on exports read before the picklist existed.
SECTION_TYPES = ir.SECTION_COMPONENT_TYPES
_FORM_TYPES = ("Field Set", "Repeater", "Table")
_TYPE_FLAGS = (("isRepeater__c", "Repeater"), ("isTable__c", "Table"), ("isFlow__c", "Flow"),
               ("isFieldSet__c", "Field Set"))

# Repeater and Table action settings, as formTemplatePageSection passes them on.
_ACTIONS = {
    "new": {"enabled": "Enable_New_Action__c", "label": "New_Action_Button_Label__c",
            "modal_title": "Table_New_Action_Modal_Title__c", "modal_subtitle": "Table_New_Action_Modal_Subtitle__c"},
    "edit": {"enabled": "Enable_Edit_Action__c", "label": "Edit_Action_Button_Label__c",
             "modal_title": "Edit_Action_Modal_Title__c", "modal_subtitle": "Edit_Action_Modal_Subtitle__c"},
    "clone": {"enabled": "Enable_Clone_Action__c", "label": "Clone_Action_Button_Label__c",
              "modal_title": "Table_Clone_Action_Modal_Title__c", "modal_subtitle": "Table_Clone_Action_Modal_Subtitle__c"},
    "delete": {"enabled": "Enable_Delete_Action__c", "label": "Delete_Action_Button_Label__c",
               "modal_title": "Table_Delete_Action_Modal_Title__c", "modal_subtitle": "Table_Delete_Action_Modal_Subtitle__c",
               "modal_body": "Table_Delete_Action_Modal_Body__c"},
}
_TABLE_SETTINGS = ("Table_Display_Row_Numbers__c", "Table_Hide_Column_Headers__c", "Table_Hide_Footer__c",
                   "Table_Prevent_Column_Resize__c", "Table_Disable_Row_Action_Indicators__c", "Table_Row_Style__c")
_REPEATER_SETTINGS = ("Repeater_Hide_Divider__c", "Repeater_Record_Spacing__c")
_SUBMISSION_MAP = "Submission_Field_Map__c"
_IMG_SRC = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)


class ExportError(ValueError):
    """Raised when an export file is not a Form Template export."""


def _get(node: dict, namespace: str, key: str, default=None):
    for candidate in (namespace + key, STAR + key, key):
        if isinstance(node, dict) and candidate in node and node[candidate] not in (None, ""):
            return node[candidate]
    return default


def _fold(name: str, namespace: str) -> str:
    name = (name or "").strip()
    return namespace + name[len(STAR):] if name.startswith(STAR) else name


def _json(value):
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value)
    except ValueError:
        return None


def _section_wrapper(text: str, namespace: str) -> dict:
    parsed = _json(text)
    if parsed is None:
        return {"status": "blank" if not (text or "").strip() else "unparseable"}
    if not isinstance(parsed, dict):
        return {"status": "unparseable"}
    if "formSelectionMode" not in parsed:
        return {"status": "legacy_raw", "config": parsed}
    return {"status": "parsed", "mode": parsed.get("formSelectionMode") or "",
            "form_name": _fold(parsed.get("formQualifiedApiName") or "", namespace),
            "object": _fold(parsed.get("object") or "", namespace),
            "config": _json(parsed.get("formJsonConfig"))}


def _relationship_name(node: dict, namespace: str, key: str) -> str:
    related = _get(node, namespace, key)
    return related.get("QualifiedApiName") or "" if isinstance(related, dict) else ""


def _normalize_runtime(config: dict, namespace: str) -> dict:
    """Runtime/record JSON (sections__r / fields__r) -> the common shape."""
    form_object = _fold(_get(config, namespace, "ObjectApiName__c") or "", namespace)
    if not form_object:
        form_object_rel = _get(config, namespace, "Form_Object__r") or {}
        form_object = _fold(_relationship_name(form_object_rel, namespace, "Object__r"), namespace)
    sections = []
    for raw_section in _get(config, namespace, "sections__r") or []:
        fields = []
        for raw_field in _get(raw_section, namespace, "fields__r") or []:
            extra = _json(_get(raw_field, namespace, "config__c")) or {}
            field_name = _relationship_name(raw_field, namespace, "fieldName__r") \
                or _get(raw_field, namespace, "fieldName__c") or ""
            field_object = _relationship_name(raw_field, namespace, "Object__r") or form_object
            fields.append({
                "position": _get(raw_field, namespace, "position__c", 0),
                "field": _fold(field_name, namespace), "object": _fold(field_object, namespace),
                "label_override": _get(raw_field, namespace, "customLabel__c") or _get(extra, namespace, "customLabel__c") or "",
                "display_type": _get(raw_field, namespace, "displayType__c") or _get(extra, namespace, "displayType__c") or "",
                "required": bool(_get(raw_field, namespace, "required__c", False)),
                "read_only": bool(_get(raw_field, namespace, "readOnly__c", False)),
                "condition_id": _get(raw_field, namespace, "conditionalLogic__c") or "",
            })
        sections.append({"title": _get(raw_section, namespace, "title__c") or "",
                         "position": _get(raw_section, namespace, "position__c", 0),
                         "condition_id": _get(raw_section, namespace, "conditionalLogic__c") or "",
                         **_section_extras(raw_section, namespace), "fields": fields})
    logic = {}
    for raw_logic in _get(config, namespace, "conditionalLogic__r") or []:
        logic[raw_logic.get("Id") or raw_logic.get("QualifiedApiName") or str(len(logic))] = {
            "label": raw_logic.get("Label") or "",
            "condition_type": _get(raw_logic, namespace, "conditionType__c") or "AND",
            "display_type": _get(raw_logic, namespace, "displayType__c") or "",
            "conditions": [{
                "position": _get(c, namespace, "position__c", 0),
                "field": _fold(_relationship_name(c, namespace, "fieldName__r") or _get(c, namespace, "fieldName__c") or "", namespace),
                "object": _fold(_relationship_name(c, namespace, "Object__r") or form_object, namespace),
                "operation": _get(c, namespace, "operation__c") or "",
                "value": _get(c, namespace, "value__c"),
            } for c in _get(raw_logic, namespace, "conditions__r") or []],
        }
    return {"object": form_object, "sections": sections, "logic": logic,
            "submission_map": _get(config, namespace, _SUBMISSION_MAP)}


def _section_extras(raw_section: dict, namespace: str) -> dict:
    """A component section's type, banner settings, image asset and rich text.

    Read from the same keys in both shapes: a ``sections__r`` entry in record
    or inline JSON, or a ``Form_Section__mdt`` row's ``config__c``.
    """
    return {"section_type": _get(raw_section, namespace, "sectionType__c") or "",
            "banner": _json(_get(raw_section, namespace, "Banner__c")),
            "image_asset": _get(raw_section, namespace, "contentAssetName__c") or "",
            "rich_text": _get(raw_section, namespace, "richText__c") or ""}


def _normalize_cmt(form: dict, namespace: str) -> dict:
    sections = []
    for raw_section in form["sections"]:
        extra_section = _json(raw_section.get("config")) or {}
        fields = []
        for raw_field in raw_section["fields"]:
            extra = _json(raw_field.get("config")) or {}
            fields.append({
                "position": raw_field.get("position") or 0, "field": raw_field["field"],
                "object": raw_field.get("object") or form["object"],
                "label_override": _get(extra, namespace, "customLabel__c") or "",
                "display_type": _get(extra, namespace, "displayType__c") or "",
                "required": raw_field.get("required", False), "read_only": raw_field.get("read_only", False),
                "condition_id": raw_field.get("condition_id") or "",
            })
        sections.append({"title": _get(extra_section, namespace, "title__c") or "",
                         "position": raw_section.get("position") or 0,
                         "condition_id": raw_section.get("condition_id") or "",
                         **_section_extras(extra_section, namespace), "fields": fields})
    # A metadata form carries its Submission Field Map in Form__mdt.config__c,
    # which the package merges into the form root it renders from.
    submission_map = form.get("submission_field_map") or _get(_json(form.get("config")) or {}, namespace, _SUBMISSION_MAP)
    return {"object": form["object"], "sections": sections, "logic": form.get("logic") or {},
            "submission_map": submission_map}


def _cmt_form(export: dict, name: str):
    """A metadata form by name, with or without the package namespace."""
    namespace = export["namespace"]
    forms = export.get("cmt_forms") or {}
    bare = name[len(namespace):] if name.startswith(namespace) else name
    for candidate in (name, bare, namespace + bare):
        if candidate in forms:
            return forms[candidate]
    return None


def _named_form(name: str, export: dict, components_by_version: dict):
    """(kind, label, normalized form, error) for a form named outright.

    Used for the template's header form, which names its form directly rather
    than through a section wrapper.
    """
    namespace = export["namespace"]
    if name.endswith("_v0"):
        component = components_by_version.get(name)
        if component is None:
            return None, name, None, f"record component {name!r} not found"
        config = _json(_get(component, namespace, "FormConfigJSON__c")) or {}
        form = _normalize_runtime(config, namespace)
        form["submission_map"] = _get(component, namespace, _SUBMISSION_MAP) or form["submission_map"]
        return "Record", _get(component, namespace, "Label__c") or component.get("Name") or name, form, None
    found = _cmt_form(export, name)
    if found is None:
        return None, name, None, f"metadata form {name!r} not found"
    return "Metadata", found.get("label") or name, _normalize_cmt(found, namespace), None


def _resolve_section(section: dict, export: dict, components_by_version: dict):
    """(kind, name, normalized form, stale inline JSON?) for one page section.

    Mirrors FormTemplate_Utility.sectionFormConfig / jsonSectionConfig /
    recordComponentName exactly, so the IR shows what the package draws:
    a ``_v0`` name is a record component, ``component`` mode or a bare name
    is a metadata form, anything else is inline JSON.
    """
    namespace = export["namespace"]
    raw_text = _get(section, namespace, "FormConfigJSON__c") or ""
    wrapper = _section_wrapper(raw_text, namespace)
    if wrapper["status"] == "unparseable":
        return None, "FormConfigJSON__c does not parse", None, False
    mode = wrapper.get("mode") or ""
    mirror = _fold(_get(section, namespace, "FormQualifiedApiName__c") or "", namespace)
    picked = wrapper.get("form_name") if mode == "component" and wrapper.get("form_name") else mirror
    stale = mode == "component" and wrapper.get("config") is not None

    record_name = None
    if not (mode != "component" and (raw_text.strip() or not picked)) and picked.endswith("_v0"):
        record_name = picked
    if record_name:
        component = components_by_version.get(record_name)
        if component is None:
            return None, f"record component {record_name!r} not found", None, stale
        config = _json(_get(component, namespace, "FormConfigJSON__c")) or {}
        label = _get(component, namespace, "Label__c") or component.get("Name") or record_name
        form = _normalize_runtime(config, namespace)
        # The record's own field is what the package reads; the root key is a fallback.
        form["submission_map"] = _get(component, namespace, _SUBMISSION_MAP) or form["submission_map"]
        return "Record", label, form, stale

    if mode == "component" or (not raw_text.strip() and mirror):
        name = wrapper.get("form_name") or mirror
        if not name or name.endswith("_v0"):
            return None, "section has no form", None, stale
        form = _cmt_form(export, name)
        if form is None:
            return None, f"metadata form {name!r} not found", None, stale
        return "Metadata", form.get("label") or name, _normalize_cmt(form, namespace), stale

    config = wrapper.get("config") if wrapper["status"] == "parsed" else wrapper.get("config")
    if not config:
        return None, "section has no form", None, False
    return "JSON", "", _normalize_runtime(config, namespace), False


def _input_type(describe_entry: dict | None, display_type: str) -> tuple[str, list[str]]:
    sf_type = (describe_entry or {}).get("type", "")
    input_type = _TYPE_MAP.get(sf_type, "text")
    if sf_type == "picklist" and any(word in (display_type or "").lower() for word in _CHOICE_DISPLAYS):
        input_type = "choice-group"
    validation = [_VALIDATION[sf_type]] if sf_type in _VALIDATION else []
    return input_type, validation


_TOKEN = re.compile(r"\s*(\(|\)|AND|OR|NOT|\d+)\s*", re.IGNORECASE)


def _custom_logic(text: str, refs: dict[int, dict]) -> dict:
    """'1 AND (2 OR NOT 3)' -> a condition tree over the numbered refs."""
    tokens = [t.upper() for t in _TOKEN.findall(text or "")]
    position = 0

    def peek():
        return tokens[position] if position < len(tokens) else None

    def take():
        nonlocal position
        position += 1
        return tokens[position - 1]

    def primary():
        token = take()
        if token == "(":
            node = expression()
            take()
            return node
        if token == "NOT":
            return conditions_module.negate(primary())
        if token is None or not token.isdigit() or int(token) not in refs:
            raise conditions_module.ConditionSyntaxError(f"custom logic {text!r}: bad token {token!r}")
        return refs[int(token)]

    def chain(operator, lower, build):
        operands = [lower()]
        while peek() == operator:
            take()
            operands.append(lower())
        return operands[0] if len(operands) == 1 else build(operands)

    def term():
        return chain("AND", primary, conditions_module.all_of)

    def expression():
        return chain("OR", term, conditions_module.any_of)

    tree = expression()
    if position != len(tokens):
        raise conditions_module.ConditionSyntaxError(f"custom logic {text!r}: trailing tokens")
    return tree


def _condition_tree(items, condition_type, custom, hide, make_ref):
    refs = {int(item.get("position") or index + 1): make_ref(item) for index, item in enumerate(items)}
    ordered = [refs[key] for key in sorted(refs)]
    kind = (condition_type or "AND").upper()
    if kind == "CUSTOM" and custom:
        tree = _custom_logic(custom, refs)
    elif len(ordered) == 1:
        tree = ordered[0]
    else:
        tree = conditions_module.any_of(ordered) if kind == "OR" else conditions_module.all_of(ordered)
    return conditions_module.negate(tree) if hide else tree


def _component_type(section: dict, namespace: str) -> tuple[str, str]:
    """(Component_Type__c, where it came from) for one page section.

    The picklist is required and defaults to Field Set. An export read before
    the picklist existed still has the formula checkboxes, so those decide next.
    """
    value = _get(section, namespace, "Component_Type__c")
    if value:
        return value, "Component_Type__c"
    for flag, kind in _TYPE_FLAGS:
        if _get(section, namespace, flag):
            return kind, flag
    if _get(section, namespace, "lwcComponentName__c"):
        return "Lightning Web Component", "lwcComponentName__c"
    return "Field Set", "default"


def _present(section: dict, namespace: str, keys) -> dict:
    """The named section settings that hold a value, keyed without the namespace."""
    found = {}
    for key in keys:
        value = _get(section, namespace, key)
        if value not in (None, ""):
            found[key] = value
    return found


def _actions(section: dict, namespace: str, component_type: str) -> dict:
    actions = {}
    for action, keys in _ACTIONS.items():
        entry = {"enabled": bool(_get(section, namespace, keys["enabled"], False))}
        for role, key in keys.items():
            if role == "enabled" or (component_type != "Table" and key.startswith("Table_")):
                continue
            value = _get(section, namespace, key)
            if value not in (None, ""):
                entry[role] = value
        actions[action] = entry
    return actions


def _number(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def parse_submission_map(raw, namespace: str):
    """A Submission Field Map as ``{"lookup_field", "fields"}``, or None.

    Mirrors SubmissionFieldMapping.parse: the JSON is keyed by Form Submission
    field (``{"lookupField": "ALL" or a lookup, "fields": {submission: source}}``)
    and stores the namespace as ``*__``. Blank sources are skipped.
    """
    if isinstance(raw, str):
        raw = _json(raw.replace(STAR, namespace))
    elif isinstance(raw, dict):
        raw = _json(json.dumps(raw).replace(STAR, namespace))
    if not isinstance(raw, dict) or not isinstance(raw.get("fields"), dict):
        return None
    fields = {submission: source for submission, source in sorted(raw["fields"].items())
              if submission and isinstance(source, str) and source.strip()}
    if not fields:
        return None
    lookup = raw.get("lookupField") if isinstance(raw.get("lookupField"), str) else ""
    return {"lookup_field": lookup, "fields": fields}


def _html_images(text) -> list[str]:
    return _IMG_SRC.findall(text) if isinstance(text, str) else []


def _literal(value) -> bool:
    """True for an image or logo reference, False for a merge field that names one."""
    return isinstance(value, str) and bool(value.strip()) and "{{" not in value


def _banners(form: dict, where: str, images: list[str]) -> list[dict]:
    """Banner sections of a normalized form, recording their literal images."""
    found = []
    for inner in sorted(form["sections"], key=lambda s: s["position"] or 0):
        if inner.get("image_asset"):
            images.append(inner["image_asset"])
        images.extend(_html_images(inner.get("rich_text")))
        if inner.get("section_type") != "bannerSection":
            continue
        settings = inner.get("banner") or {}
        found.append({"where": " > ".join(part for part in (where, inner["title"]) if part),
                      "settings": settings})
        for key in ("image", "logo"):
            if _literal(settings.get(key)):
                images.append(settings[key])
    return found


def build(export: dict) -> dict:
    """Assemble a Form Template export into an IR document."""
    if "template" not in export or "namespace" not in export:
        raise ExportError("Not a Form Template export: run extract.py first.")
    namespace = export["namespace"]
    template = export["template"]
    describes = export.get("describes") or {}
    findings: list[dict] = []
    images: list[str] = []
    banners: list[dict] = []
    content_blocks: list[dict] = []
    submission_object = namespace + "Form_Submission__c"

    components_by_version = {_fold(_get(c, namespace, "VersionId__c") or "", namespace): c
                             for c in export.get("components") or [] if _get(c, namespace, "VersionId__c")}

    pages = sorted(export.get("pages") or [], key=lambda p: _get(p, namespace, "Position__c", 0) or 0)
    sections_by_page: dict[str, list[dict]] = {}
    for section in export.get("sections") or []:
        sections_by_page.setdefault(_get(section, namespace, "Form_Template_Page__c"), []).append(section)

    fields, structure, conditions = [], [], []
    option_labels: dict[str, tuple[str, str]] = {}
    field_labels: dict[str, str] = {}
    targets: dict[str, list[tuple[str, str]]] = {}
    landings: list[tuple[str, str, str]] = []
    kinds = {"Metadata": 0, "Record": 0, "JSON": 0}
    section_types = {kind: 0 for kind in SECTION_TYPES}
    used_ids: set[str] = set()

    def describe_entry(obj, field):
        return (describes.get(obj) or {}).get(field)

    def rule_ref(obj, field, operation, value):
        entry = describe_entry(obj, field)
        field_label = (entry or {}).get("label") or field
        text = f"{operation} {value}".strip() if value not in (None, "") else operation
        reference = f"{obj}.{field}::{text}"
        option_labels[reference] = (text, field_label)
        return conditions_module.ref(reference)

    def template_rule(raw, element_id, tag, label) -> bool:
        """A page or page-section rule (Conditional_Logic__c JSON) as a condition tree."""
        rule = _json(raw)
        if not (isinstance(rule, dict) and rule.get("conditions")):
            return False
        rule_object = _fold(rule.get("objectApiName") or submission_object, namespace)
        try:
            tree = _condition_tree(
                rule["conditions"], rule.get("conditionType"), rule.get("customLogic"),
                rule.get("ruleMode") == "hideWhen",
                lambda c: rule_ref(rule_object, _fold(c.get("fieldApiName") or "", namespace),
                                   c.get("operator") or "", c.get("value")))
        except conditions_module.ConditionSyntaxError as error:
            findings.append({"source": "adapter", "message": f"{label} rule not read: {error}"})
            return True
        conditions.append({"element_id": element_id, "governs": "section", "tag": tag,
                           "expression": json.dumps(rule, ensure_ascii=False), "tree": tree,
                           "references": [], "unresolved_references": []})
        return True

    for page in pages:
        page_id = page["Id"]
        page_label = _get(page, namespace, "Page_Label__c") or page.get("Name") or page_id
        page_node = {"id": page_id, "tag": "page", "label": page_label, "layout": [], "parent_id": None,
                     "has_condition": False}
        structure.append(page_node)
        page_node["has_condition"] = template_rule(_get(page, namespace, "Conditional_Logic__c"),
                                                   page_id, "page", f"Page {page_label!r}")
        if _literal(_get(page, namespace, "Form_Banner_Image__c")):
            images.append(_get(page, namespace, "Form_Banner_Image__c"))
        for key in ("Page_Title__c", "Details__c", "Page_Footer__c", "Header_Text__c"):
            images.extend(_html_images(_get(page, namespace, key)))

        page_sections = sorted(sections_by_page.get(page_id, []), key=lambda s: _get(s, namespace, "Position__c", 0) or 0)
        for section in page_sections:
            section_id = section["Id"]
            section_title = _get(section, namespace, "Header_Title__c") or _get(section, namespace, "Title__c") \
                or section.get("Name") or section_id
            where = f"{page_label} > {section_title}"
            component_type, type_source = _component_type(section, namespace)
            if component_type not in SECTION_TYPES:
                findings.append({"source": "adapter", "message": f"{where}: Component Type {component_type!r} "
                                 "is not one the package draws; check the section in the org"})
            else:
                section_types[component_type] += 1
            details = {"component_type": component_type, "component_type_source": type_source}
            details.update({key: value for key, value in (
                ("section_tag", _get(section, namespace, "Section_Tag__c")),
                ("message_variant", _get(section, namespace, "Message_Variant__c")),
            ) if value not in (None, "")})
            node = {"id": section_id, "tag": "section", "label": section_title, "layout": [],
                    "parent_id": page_id, "has_condition": False, "section": details}
            if component_type in ("Repeater", "Table"):
                node["repeat"] = True
                node["repeat_label"] = section_title
            structure.append(node)
            node["has_condition"] = template_rule(_get(section, namespace, "Conditional_Logic__c"),
                                                  section_id, "page-section", where)
            text = _get(section, namespace, "Component_Section_Text__c") or ""
            images.extend(_html_images(text))
            images.extend(_html_images(_get(section, namespace, "Header_Text__c")))
            if _literal(_get(section, namespace, "Form_Banner_Image__c")):
                images.append(_get(section, namespace, "Form_Banner_Image__c"))

            if component_type == "Display Text":
                details["text"] = text
                if text:
                    content_blocks.append({"section": where, "title": section_title, "text": text})
                else:
                    findings.append({"source": "adapter", "message": f"{where}: Display Text section has no text"})
                continue
            if text:
                details["intro_text"] = text
                content_blocks.append({"section": where, "title": section_title, "text": text})
            if component_type == "Flow":
                details["flow_api_name"] = _get(section, namespace, "FlowApiName__c") or ""
                if not details["flow_api_name"]:
                    findings.append({"source": "adapter", "message": f"{where}: Flow section names no flow (FlowApiName__c)"})
                continue
            if component_type == "Lightning Web Component":
                details["lwc_component_name"] = _get(section, namespace, "lwcComponentName__c") or ""
                if not details["lwc_component_name"]:
                    findings.append({"source": "adapter", "message": f"{where}: Lightning Web Component section "
                                     "names no component (lwcComponentName__c)"})
                continue

            if component_type in ("Repeater", "Table"):
                details["min"] = _number(_get(section, namespace, "Min__c"))
                details["max"] = _number(_get(section, namespace, "Max__c"))
                details["actions"] = _actions(section, namespace, component_type)
                details["settings"] = _present(section, namespace,
                                               _TABLE_SETTINGS if component_type == "Table" else _REPEATER_SETTINGS)
                if component_type == "Table":
                    details["alternate_form"] = _fold(_get(section, namespace, "Alternate_FormQualifiedApiName__c") or "", namespace)
                    details["bulk_form"] = _fold(_get(section, namespace, "Bulk_FormQualifiedApiName__c") or "", namespace)
                    legacy = _get(section, namespace, "Edit_FormQualifiedApiName__c")
                    if legacy:
                        details["legacy_edit_form"] = _fold(legacy, namespace)

            kind, name, form, stale = _resolve_section(section, export, components_by_version)
            raw_text = _get(section, namespace, "FormConfigJSON__c") or ""
            wrapper = _section_wrapper(raw_text, namespace)
            details["form"] = {"kind": kind, "name": name if form is not None else "",
                               "qualified_api_name": _fold(_get(section, namespace, "FormQualifiedApiName__c") or "", namespace)
                               or wrapper.get("form_name") or "",
                               "selection_mode": wrapper.get("mode") or ""}
            if kind == "JSON" and form is not None:
                details["form"]["inline_config"] = wrapper.get("config")
            if stale:
                findings.append({"source": "adapter", "message": f"{where}: inline JSON "
                                 "is left over and ignored by the package (component mode draws the named form); "
                                 "clear it during clean-up"})
            if form is None:
                message = f"{component_type} section has no form" if name == "section has no form" else name
                findings.append({"source": "adapter", "message": f"{where}: {message}"})
                continue
            kinds[kind] += 1
            logic = form["logic"]
            banners.extend(_banners(form, where, images))

            submission_map = None
            if form.get("submission_map"):
                if form["object"] == submission_object:
                    findings.append({"source": "adapter", "message": f"{where}: the form is on Form Submission, "
                                     "so the package ignores its Submission Field Map; clear it during clean-up"})
                else:
                    submission_map = parse_submission_map(form["submission_map"], namespace)
                    if submission_map is None:
                        findings.append({"source": "adapter", "message": f"{where}: Submission Field Map does not "
                                         "parse or maps nothing; check it on the Form Template Mapping tab"})
            if submission_map:
                details["submission_field_map"] = {"object": form["object"], **submission_map}
                for landing_field, source_field in submission_map["fields"].items():
                    landings.append((landing_field, form["object"], source_field))
            landing_by_source: dict[str, list[str]] = {}
            for landing_field, source_field in (submission_map or {}).get("fields", {}).items():
                landing_by_source.setdefault(source_field, []).append(landing_field)

            def logic_condition(condition_id, element_id, governs):
                entry = logic.get(condition_id)
                if not entry:
                    return
                try:
                    tree = _condition_tree(
                        entry["conditions"], entry.get("condition_type"), entry.get("custom_logic"),
                        "hide" in (entry.get("display_type") or "").lower(),
                        lambda c: rule_ref(c.get("object") or form["object"], c["field"], c.get("operation") or "", c.get("value")))
                except conditions_module.ConditionSyntaxError as error:
                    findings.append({"source": "adapter", "message": f"{entry.get('label')}: {error}"})
                    return
                conditions.append({"element_id": element_id, "governs": governs, "tag": "component",
                                   "expression": entry.get("label") or condition_id, "tree": tree,
                                   "references": [], "unresolved_references": []})

            for inner_index, inner in enumerate(sorted(form["sections"], key=lambda s: s["position"] or 0)):
                inner_id = f"{section_id}/{inner_index + 1}"
                if inner["title"] or inner["condition_id"]:
                    inner_node = {"id": inner_id, "tag": "component-section", "label": inner["title"],
                                  "layout": [], "parent_id": section_id, "has_condition": bool(inner["condition_id"])}
                    if inner.get("section_type"):
                        inner_node["section_type"] = inner["section_type"]
                    structure.append(inner_node)
                    logic_condition(inner["condition_id"], inner_id, "section")
                path = " > ".join(part for part in (page_label, section_title, inner["title"]) if part)
                for raw in sorted(inner["fields"], key=lambda f: f["position"] or 0):
                    if not raw["field"] or raw["field"].startswith("01I") or "." in raw["field"]:
                        findings.append({"source": "adapter", "message": f"{path}: field {raw['field']!r} "
                                         "is an unresolved id or a path; check it in the org"})
                        continue
                    entry = describe_entry(raw["object"], raw["field"])
                    if entry is None:
                        findings.append({"source": "adapter", "message": f"{path}: {raw['object']}.{raw['field']} "
                                         "is not in the org describe (deleted, renamed or no access)"})
                    label = raw["label_override"] or (entry or {}).get("label") or raw["field"]
                    input_type, validation = _input_type(entry, raw["display_type"])
                    field_id = f"{raw['object']}.{raw['field']}"
                    if field_id in used_ids:
                        field_id = f"{section_id}/{field_id}"
                    used_ids.add(field_id)
                    field_labels[field_id] = label
                    options = [{"id": f"{field_id}::{value}", "label": value} for value in (entry or {}).get("picklist") or []]
                    for option in options:
                        option_labels[option["id"]] = (option["label"], label)
                    field = {
                        "id": field_id, "label": label, "section_path": path, "section_id": inner_id,
                        "input_type": input_type, "tag": "input", "required": raw["required"],
                        "validation": validation, "default_value": None, "present_in_rendered_form": True,
                        "options": options, "read_only": raw["read_only"],
                        "target": {"object": raw["object"], "field": raw["field"]},
                        "component": {"kind": kind, "name": name, "section_record_id": section_id,
                                      "component_type": component_type},
                    }
                    if component_type in ("Repeater", "Table"):
                        field["repeat_section"] = section_id
                    if raw["object"] == form["object"] and landing_by_source.get(raw["field"]):
                        field["submission_landing"] = sorted(landing_by_source[raw["field"]])
                    fields.append(field)
                    targets.setdefault(raw["object"], []).append((raw["field"], label))
                    logic_condition(raw["condition_id"], field_id, "field")

    branding, header_ok = _branding(template, export, components_by_version, images, findings)
    branding["banners"] = branding.pop("header_banners") + banners

    unread_rules = any("not read" in f["message"] or "custom logic" in f["message"] for f in findings)
    document = ir.new_document(
        platform="formtemplate", form_id=template["Id"], form_name=template.get("Name") or "",
        coverage={"structure": "parsed", "fields": "parsed", "options": "parsed", "validation": "parsed",
                  "conditions": "not_captured" if unread_rules else "parsed",
                  "connector": "parsed", "images": "parsed" if header_ok else "not_captured",
                  "custom_scripts": "none_exist"})
    document["source"]["extracted_on"] = export.get("extracted_on", "")
    document["source"]["org"] = export.get("org", "")
    document["form"]["section_paths"] = [n["label"] for n in structure if n["tag"] == "page"]
    document["form"]["template"] = {key: value for key, value in sorted(template.items())
                                    if key != "attributes" and value not in (None, "", False)}
    document["form"]["component_sources"] = kinds
    document["form"]["section_types"] = {kind: count for kind, count in section_types.items() if count}
    document["form"]["branding"] = branding
    document["form"]["content_blocks"] = content_blocks
    document["fields"] = fields
    document["structure"] = structure
    document["conditions"] = conditions
    document["images"] = list(dict.fromkeys(images))
    nodes = [{
        "node_id": obj, "order_path": str(index + 1), "action": "template", "sobject": obj,
        "parent_node_id": None, "comment": "Written by the existing Form Template", "skip_if": None,
        "skip_if_tokens": [], "lookup": None,
        "mappings": [{"target_field_label": field, "source_kind": "form_field", "source_value": label,
                      "source_node_path": None, "formula_tokens": []} for field, label in pairs],
    } for index, (obj, pairs) in enumerate(sorted(targets.items()))]
    if landings:
        nodes.append({
            "node_id": f"{submission_object}#submission_field_maps", "order_path": str(len(nodes) + 1),
            "action": "submission_field_map", "sobject": submission_object, "parent_node_id": None,
            "comment": "Landed on Form Submission by the components' Submission Field Maps",
            "skip_if": None, "skip_if_tokens": [], "lookup": None,
            "mappings": [{"target_field_label": landing, "source_kind": "submission_field_map",
                          "source_value": f"{obj}.{source}", "source_node_path": None, "formula_tokens": []}
                         for landing, obj, source in sorted(set(landings))],
        })
    document["connector"]["nodes"] = nodes
    document["connector"]["declared_target_fields"] = (
        [f"{obj}.{field}" for obj, pairs in targets.items() for field, _ in pairs]
        + [f"{submission_object}.{landing}" for landing, _, _ in landings])
    if export.get("undescribable_objects"):
        findings.append({"source": "extract", "message": "Objects the org would not describe: "
                         + ", ".join(export["undescribable_objects"])})
    document["findings"] = findings
    for field_id, label in field_labels.items():
        option_labels.setdefault(field_id, (label, label))
    resolver = conditions_module.LabelResolver(field_labels, option_labels)
    return ir.finalize(document, resolver=resolver)


def _branding(template: dict, export: dict, components_by_version: dict, images: list[str],
              findings: list[dict]) -> tuple[dict, bool]:
    """The template's header form, header tags, logo and banner image.

    Returns the branding and whether the header form it names was in the export.
    The logo shown when Logo Override is blank is the org default from Global
    Styles, which lives outside the template and is reported, not read.
    """
    namespace = export["namespace"]
    tags = _get(template, namespace, "Header_Tags__c") or ""
    branding = {
        "header_tags": [tag.strip() for tag in tags.split(";") if tag.strip()],
        "banner_image": _get(template, namespace, "Form_Banner_Image__c") or "",
        "logo_override": _get(template, namespace, "Logo_Override__c") or "",
        "logo_alt_text_override": _get(template, namespace, "Logo_Alt_Text_Override__c") or "",
        "header_form": None, "header_banners": [],
    }
    for key in ("banner_image", "logo_override"):
        if _literal(branding[key]):
            images.append(branding[key])
    for key in ("Template_Header_Text__c", "Template_Footer_Text__c", "Confirmation_Page_Message__c"):
        images.extend(_html_images(_get(template, namespace, key)))
    if not any(key.endswith("Logo_Override__c") for key in template):
        findings.append({"source": "adapter", "message": "The export has no Logo Override fields (Flow Tool Kit "
                         "before 5.4): a banner's logo comes from its own settings or the org default"})
    elif not branding["logo_override"]:
        findings.append({"source": "adapter", "message": "No Logo Override: the banner shows the org default "
                         "logo from the Form Builder's Global Styles tab, which is not part of the template"})

    header_ok = True
    name = _fold(_get(template, namespace, "FormQualifiedApiName_Header__c") or "", namespace)
    if name:
        kind, label, form, error = _named_form(name, export, components_by_version)
        branding["header_form"] = {"name": name, "kind": kind or "", "label": label if form else "",
                                   "found": form is not None}
        if form is None:
            header_ok = False
            findings.append({"source": "adapter", "message": f"Header form: {error}; its banner was not read"})
        else:
            branding["header_form"]["section_types"] = [inner.get("section_type") or "" for inner in
                                                        sorted(form["sections"], key=lambda s: s["position"] or 0)]
            branding["header_banners"] = _banners(form, "Header", images)
    return branding, header_ok


def build_from_file(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return build(json.load(handle))
