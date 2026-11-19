"""Parsers for every shape a field reference is stored in.

Every walker emits the same reference shape, and a caller reports what it
could not parse to the coverage list: an empty result must never read as a
clean bill of health.

Two conditional-logic dialects are matched separately:

* the Form Builder dialect: ``conditionalLogic__r[].conditions__r[].fieldName__c``,
  matched by ``walk_config`` like any other field key;
* the page, section and payment dialect: ``conditions[].fieldApiName``,
  matched by ``parse_rule``.
"""

from __future__ import annotations

import json

from . import NAMESPACE, SUBMISSION_OBJECT
from .names import fold_star, is_path, merge_tokens, split_durable, strip_key

# Config JSON keys that hold a field API name, and the role each plays.
# Section-level Alternative_Field__c (a Likert score target) shares its key
# with the field-level related-field override; both matter, one matcher.
FIELD_KEYS = {
    "fieldName__c": "input field",
    "Alternative_Field__c": "related-field override / score target",
    "minDateFieldName__c": "min-date bound",
    "maxDateFieldName__c": "max-date bound",
    "columnClassFieldReference__c": "column class driver",
    "columnIconNameFieldReference__c": "column icon driver",
    "columnUrlLabelOverrideFieldReference__c": "column URL label driver",
    "imageOverrideFieldApiName__c": "section image driver",
    "fieldApiName": "rule operand",  # page and design-block dialect inside a config
}

OBJECT_KEYS = {"Object__c", "Alternative_Object__c", "ObjectApiName__c"}

# The Form Builder's Form Template Mapping tab saves this key on the form root
# (record component JSON, metadata form config) and on Form_Component__c.
MAP_KEY = "Submission_Field_Map__c"
ALL_LOOKUPS = "ALL"
MAPPING_SURFACE = "Form Template Mapping"


def reference(obj, field, surface, role, template=None, page=None, section=None,
              component_type="", component_key="", component_label="", snippet="",
              component_path=""):
    """One place a field is used. Template, page and section are row dicts."""
    template, page, section = template or {}, page or {}, section or {}
    return {
        "object": fold_star(obj or ""),
        "field": fold_star(field or ""),
        "surface": surface,
        "role": role,
        "template_id": template.get("Id", ""),
        "template_name": template.get("Name", ""),
        "page_id": page.get("Id", ""),
        "page_label": page.get("label") or page.get("Name", ""),
        "section_id": section.get("Id", ""),
        "section_title": section.get("title") or section.get("Name", ""),
        "component_type": component_type,
        "component_key": component_key,
        "component_label": component_label,
        "component_path": component_path,
        "snippet": (snippet or "")[:120],
        "is_path": is_path(field or ""),
    }


def parse_submission_map(value):
    """A Form Template Mapping, as (lookup field or None, [(submission field, target field)]).

    Stored as JSON text or an object: ``{"lookupField": "FlowToolKit__Account__c"
    or "ALL", "fields": {"<Form Submission field>": "<the form's own field>"}}``.
    Returns None for blank, unreadable or empty maps.
    """
    parsed = value
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("fields"), dict):
        return None
    pairs = [(fold_star(sub), fold_star(target)) for sub, target in parsed["fields"].items()
             if sub and isinstance(target, str) and target.strip()]
    if not pairs:
        return None
    lookup = parsed.get("lookupField")
    lookup = fold_star(lookup) if isinstance(lookup, str) and lookup and lookup != ALL_LOOKUPS else None
    return lookup, pairs


def emit_mapping(mapping, form_object, emit):
    """Both sides of a Form Template Mapping: the Form Submission field that keeps
    the answer and the form's own field it comes from, each naming the other."""
    lookup, pairs = mapping
    target_object = fold_star(form_object or "")
    for submission_field, target_field in pairs:
        emit(SUBMISSION_OBJECT, submission_field, "keeps a mapped answer",
             f"mapped from {target_object}.{target_field}", MAPPING_SURFACE)
        emit(target_object, target_field, "mapped to Form Submission",
             f"mapped to {submission_field}", MAPPING_SURFACE)
    if lookup:
        emit(SUBMISSION_OBJECT, lookup, "mapping lookup",
             f"applies to the {target_object} this lookup names", MAPPING_SURFACE)


def walk_config(config, default_object, emit):
    """Recursive walk of a form config tree. Matches every field key, every
    merge token and every Form Template Mapping, tracking the object as it
    narrows. ``emit(obj, field, role, snippet, surface=None)``; surface None
    means the caller's own surface (the form)."""

    def descend(node, current_object):
        if isinstance(node, list):
            for item in node:
                descend(item, current_object)
            return
        if not isinstance(node, dict):
            return
        node_object = current_object
        for key, value in node.items():
            bare_key = strip_key(key)
            if bare_key in OBJECT_KEYS and isinstance(value, str) and value.strip():
                candidate = split_durable(value)[1] if "." not in value else value.split(".")[0]
                node_object = fold_star(candidate)
            elif bare_key == "Object__r" and isinstance(value, dict) and value.get("QualifiedApiName"):
                # metadata-shaped configs (inline JSON in flows) carry the object as a relationship
                node_object = fold_star(value["QualifiedApiName"])
            elif bare_key == "Form_Object__r" and isinstance(value, dict):
                inner = value.get(NAMESPACE + "Object__r") or value.get("*__Object__r") or {}
                if isinstance(inner, dict) and inner.get("QualifiedApiName"):
                    node_object = fold_star(inner["QualifiedApiName"])
        for key, value in node.items():
            bare_key = strip_key(key)
            if bare_key == MAP_KEY:
                mapping = parse_submission_map(value)
                if mapping:
                    emit_mapping(mapping, node_object, emit)
            elif bare_key in FIELD_KEYS and isinstance(value, str) and value.strip():
                override = None
                if bare_key == "Alternative_Field__c":
                    override_raw = node.get(NAMESPACE + "Alternative_Object__c") or node.get("*__Alternative_Object__c")
                    if isinstance(override_raw, str) and override_raw.strip():
                        override = fold_star(split_durable(override_raw)[1])
                obj, field = split_durable(value, override or node_object)
                emit(obj or node_object, field, FIELD_KEYS[bare_key], "")
            elif isinstance(value, str) and "{{" in value:
                for token_object, token in merge_tokens(value):
                    emit(token_object or node_object, token, "merge token", value)
            elif isinstance(value, (dict, list)):
                descend(value, node_object)

    descend(config, fold_star(default_object or SUBMISSION_OBJECT))


def parse_section_wrapper(config_text):
    """The FormConfigJSON__c wrapper on a page section, in every shape it has had:
    ``{formSelectionMode, ...}``, older raw Form Builder JSON, or unreadable."""
    if not (config_text or "").strip():
        return {"status": "blank"}
    try:
        parsed = json.loads(config_text)
    except (json.JSONDecodeError, ValueError):
        return {"status": "unparseable"}
    if not isinstance(parsed, dict):
        return {"status": "unparseable"}
    if "formSelectionMode" not in parsed:
        return {"status": "legacy_raw", "config": parsed,
                "object": parsed.get(NAMESPACE + "ObjectApiName__c") or parsed.get("*__ObjectApiName__c")}
    mode = parsed.get("formSelectionMode") or ""
    inner = None
    inner_raw = parsed.get("formJsonConfig")
    if isinstance(inner_raw, str) and inner_raw.strip():
        try:
            inner = json.loads(inner_raw)
        except (json.JSONDecodeError, ValueError):
            return {"status": "unparseable"}
    elif isinstance(inner_raw, dict):
        inner = inner_raw
    return {"status": "parsed", "mode": mode, "object": parsed.get("object"),
            "form_name": parsed.get("formQualifiedApiName"), "config": inner}


def parse_rule(rule_text_or_dict, default_object=SUBMISSION_OBJECT):
    """A page, section or payment rule: ``{"objectApiName", "ruleMode",
    "conditions": [{"fieldApiName", "operator", "value"}]}``.

    Returns None for blank, ``{"status": "unparseable"}``, or
    ``{"status": "parsed", "object", "hits": [(field, snippet)]}``.
    """
    rule = rule_text_or_dict
    if isinstance(rule, str):
        if not rule.strip():
            return None
        try:
            rule = json.loads(rule)
        except (json.JSONDecodeError, ValueError):
            return {"status": "unparseable"}
    if not isinstance(rule, dict):
        return {"status": "unparseable"}
    obj = fold_star(rule.get("objectApiName") or default_object)
    hits = []
    for condition in rule.get("conditions") or []:
        if not isinstance(condition, dict):
            continue
        field = condition.get("fieldApiName")
        if field:
            snippet = (f"{rule.get('ruleMode', 'showWhen')}: {condition.get('operator', '')} "
                       f"{condition.get('value', '')}").strip()
            hits.append((field, snippet))
    return {"status": "parsed", "object": obj, "hits": hits}


def parse_url_mapping(text):
    """``[{"field": "FlowToolKit__Email__c", "param": "pv1"}]`` as [(field, param)], or None."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(parsed, list):
        return None
    return [(row.get("field"), row.get("param")) for row in parsed
            if isinstance(row, dict) and row.get("field")]


def parse_nullable(text):
    """Nullable Fields: a comma list of names, or an object-keyed map ``{"Contact": ["Email"]}``."""
    text = (text or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return [(None, part.strip()) for part in text.split(",") if part.strip()]
    if isinstance(parsed, dict):
        return [(obj, field) for obj, fields in parsed.items()
                for field in (fields if isinstance(fields, list) else [fields])]
    if isinstance(parsed, list):
        return [(None, field) for field in parsed if isinstance(field, str)]
    return []


def parse_prefill_mapping(text, source_object):
    """A source prefill mapping, stored on the source record.

    Keys are Form Submission fields (the targets); values are a source path
    string or ``{"source": path, "live": bool}``.
    """
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    rows = []
    for target, value in parsed.items():
        if isinstance(value, dict):
            path, live = value.get("source"), bool(value.get("live"))
        else:
            path, live = value, False
        rows.append({"target": target, "path": path or "", "live": live,
                     "source_object": source_object})
    return rows
