"""Show/hide rules as plan.json writes them, and what the canvas says about each one.

A rule is the structured shape the build reads (references/plan-format.md, `condition`):

    {"label": "Volunteering chosen", "show_when": "<source text>", "object": "Form_Submission__c", "mode": "showWhen",
     "type": "OR", "conditions": [{"field": "Interest__c", "operator": "==", "value": "Volunteering", "source_id": "q7"}]}

`type` is AND, OR or CUSTOM (then `custom` holds the logic, "(1 OR 2) AND 3"). One condition per allowed value.
"""
from __future__ import annotations

POSITIVE = ("==", "INCLUDES", "TRUE", "CONTAINS", "NOTBLANK")
NEGATIVE = ("!=", "EXCLUDES", "FALSE", "BLANK")
NO_VALUE = ("TRUE", "FALSE", "BLANK", "NOTBLANK")
OPERATORS = ("==", "!=", "CONTAINS", "INCLUDES", "EXCLUDES", "<", ">", "<=", ">=") + NO_VALUE
LABEL_MAX = 40


def options_of(field: dict) -> list[dict]:
    """A field's choices as [{"label", "value"}], whether the plan wrote strings or objects."""
    out = []
    for option in field.get("options") or []:
        if isinstance(option, dict):
            value = option.get("value", option.get("label"))
            out.append({"label": option.get("label", value), "value": value})
        else:
            out.append({"label": option, "value": option})
    return out


def iter_fields(plan: dict):
    """Every field on every page: (page, section, field)."""
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            for field in section.get("fields") or []:
                yield page, section, field


def by_source_id(plan: dict) -> dict:
    """The first plan field (or repeater column) placed from each source question, by its source id."""
    found = {}
    for _, _, field in iter_fields(plan):
        if field.get("source_id"):
            found.setdefault(field["source_id"], field)
        for column in (field.get("repeater") or {}).get("columns") or []:
            if column.get("source_id"):
                found.setdefault(column["source_id"], column)
    return found


def field_index(plan: dict) -> dict:
    """Controlling fields by API name and by source id, so a rule can name its question in plain words."""
    index = {}
    for _, _, field in iter_fields(plan):
        for key in (field.get("field"), field.get("source_id")):
            if key:
                index.setdefault(key, field)
    return index


def iter_rules(plan: dict):
    """Every rule in the plan: (where, rule). Page, section, field and component rules all count."""
    for p, page in enumerate(plan.get("pages") or [], 1):
        if page.get("condition"):
            yield f"page {p}", page["condition"]
        for s, section in enumerate(page.get("sections") or [], 1):
            if section.get("condition"):
                yield f"page {p} section {s}", section["condition"]
            for field in section.get("fields") or []:
                for key in ("condition", "component_rule"):
                    if field.get(key):
                        yield f"page {p} section {s} field {field.get('label', '')!r}", field[key]


def _short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3].rsplit(" ", 1)[0] + "..."


def _value_label(controller: dict | None, value) -> str:
    for option in options_of(controller or {}):
        if str(option["value"]) == str(value):
            return str(option["label"])
    if str(value).lower() == "true":
        return "checked"
    if str(value).lower() == "false":
        return "not checked"
    return str(value)


def describe(rule: dict | None, index: dict) -> str:
    """'Shows when "Interest" is "Volunteering" or "Mentoring"', the tag the canvas puts above a governed field or section."""
    if not rule:
        return ""
    groups: dict[tuple, list] = {}
    for c in rule.get("conditions") or []:
        negative = c.get("operator") in NEGATIVE
        groups.setdefault((c.get("field") or c.get("source_id"), negative), []).append(c)
    joiner = " and " if rule.get("type") == "AND" else " or "
    parts = []
    for (key, negative), conds in groups.items():
        controller = index.get(key) or index.get(conds[0].get("source_id"))
        label = _short((controller or {}).get("label") or key or "a question", 60)
        values = [f"“{_short(_value_label(controller, c.get('value')), 40)}”" for c in conds]
        if negative:
            said = f"is not {values[0]}" if len(values) == 1 else "is none of " + ", ".join(values)
        else:
            said = "is " + joiner.join(values)
        parts.append(f"“{label}” {said}")
    if not parts:
        return "Shows when a rule is met"
    if rule.get("type") == "CUSTOM" and rule.get("custom"):
        return "Shows when " + "; ".join(f"({n}) {p}" for n, p in enumerate(parts, 1)) + f"; logic {rule['custom']}"
    return "Shows when " + (joiner + "when ").join(parts)


def alternatives(rule: dict | None):
    """(controlling field, [values]) when a rule shows its content for some answers to one question; None otherwise.

    Sections shown by different answers to one question are alternatives: a respondent sees one set, so only the
    longest set counts toward the time to complete."""
    if not rule:
        return None
    conds = rule.get("conditions") or []
    fields = {c.get("field") or c.get("source_id") for c in conds}
    if len(fields) != 1 or not conds or any(c.get("operator") not in ("==", "INCLUDES") for c in conds):
        return None
    if len(conds) > 1 and rule.get("type") != "OR":
        return None
    return fields.pop(), [str(c.get("value")) for c in conds]


def rule_problems(where: str, rule: dict) -> list[str]:
    """What the build refuses: no label, a label over 40 characters, a condition without its field, operator or value."""
    problems = []
    label = rule.get("label")
    if not label:
        problems.append(f"{where}: rule has no label (Form Builder lists rules by it; name the purpose, such as 'Volunteering chosen')")
    elif len(label) > LABEL_MAX:
        problems.append(f"{where}: rule label {label!r} is over {LABEL_MAX} characters")
    elif "__c" in label:
        problems.append(f"{where}: rule label {label!r} is an API name; name the purpose in plain words")
    if rule.get("type") not in ("AND", "OR", "CUSTOM"):
        problems.append(f"{where}: rule type must be AND, OR or CUSTOM")
    if rule.get("type") == "CUSTOM" and not rule.get("custom"):
        problems.append(f"{where}: a CUSTOM rule needs its logic in 'custom', such as '(1 OR 2) AND 3'")
    conds = rule.get("conditions") or []
    if not conds:
        problems.append(f"{where}: rule has no conditions")
    for n, c in enumerate(conds, 1):
        missing = [k for k in ("field", "operator") if not c.get(k)]
        if c.get("value") is None and c.get("operator") not in NO_VALUE:
            missing.append("value")
        if missing:
            problems.append(f"{where}: condition {n} is missing {', '.join(missing)}")
        if c.get("operator") and c["operator"] not in OPERATORS:
            problems.append(f"{where}: condition {n} operator {c['operator']!r} is not one the package evaluates ({', '.join(OPERATORS)})")
        if " | " in str(c.get("value", "")) or " & " in str(c.get("value", "")):
            problems.append(f"{where}: condition {n} value {c.get('value')!r} holds a second question; give it its own condition")
    return problems
