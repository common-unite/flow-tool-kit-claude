"""A choice field's planned options against what the form will offer: the org's values for the record type it uses.

What the package does with a picklist on a form (flowFormField):

- It reads the field's values for one record type (the submission's, else the person's default). On Form Submission,
  a new submission takes the record type named Default when the org has it, the one this module compares with.
- `picklistOptionOverrides__c` (values separated by ;) shows only those values, in that order. A value the record type
  does not offer is skipped without a word; when none of them is offered, the override is ignored and every value
  shows.
- `picklistOptionSettings__c` ({value: {label, description, ...}}) relabels a value.

So the build writes the plan's options as the override and their labels as settings (fieldmap.package_keys), then
this module says what the form will really show: a planned value the field or record type lacks (a value to add in
Setup) and, through the round trip, every value missing, extra or labelled differently. Standard library only.
"""
from __future__ import annotations

import json

N = "FlowToolKit__"
MASTER = "012000000000000AAA"
CHOICE_CONTROLS = ("Picklist", "MultiPicklist")


def planned(field: dict) -> list[tuple[str, str | None]]:
    """The plan's options as (value, label or None): an option is a value, or {value, label}."""
    out = []
    for option in field.get("options") or []:
        if isinstance(option, dict):
            value = option.get("value", option.get("label"))
            label = option.get("label")
            out.append((str(value), str(label) if label is not None and label != value else None))
        else:
            out.append((str(option), None))
    return out


def is_choice(field: dict) -> bool:
    return field.get("control") in CHOICE_CONTROLS and bool(field.get("options"))


def record_type(org, obj: str, wanted: str | None = None) -> tuple[str, str, str | None]:
    """(record type Id, its name, a note) for the form's picklist values on obj: the plan's intake.record_type when the
    object has it, else on Form Submission the record type named Default (what the package gives a new submission),
    else the running user's default for the object, else the master values."""
    try:
        info = org.rest("GET", f"/ui-api/object-info/{obj}") or {}
    except Exception as error:  # noqa: BLE001 - the values are then read as the master's
        return MASTER, "Master", f"the record types of {obj} could not be read ({str(error)[:120]}), so the master values were used"
    infos = info.get("recordTypeInfos") or {}

    def named(name):
        return next((rid for rid, r in infos.items() if r.get("name") == name and r.get("available", True)), None)

    note = None
    chosen = named(wanted) if wanted else None
    if wanted and not chosen:
        note = f"intake.record_type {wanted!r} is not a record type of {obj} this user can use"
    if not chosen and obj.endswith("Form_Submission__c"):
        chosen = named("Default")
    chosen = chosen or info.get("defaultRecordTypeId") or MASTER
    return chosen, (infos.get(chosen) or {}).get("name") or "Master", note


def org_options(org, obj: str, field: str, record_type_id: str) -> list[tuple[str, str]] | None:
    """The field's (value, label) for the record type, in the org's order; None when they cannot be read."""
    try:
        data = org.rest("GET", f"/ui-api/object-info/{obj}/picklist-values/{record_type_id}/{field}") or {}
    except Exception:  # noqa: BLE001
        return None
    return [(str(v.get("value")), str(v.get("label"))) for v in data.get("values") or []]


def gap(options: list, offered: list) -> dict | None:
    """What the planned options lack in the org: missing values, and the ones the org has under another value (the
    plan wrote a label). None when every planned value is offered."""
    values = {v for v, _ in offered}
    by_label = {label: value for value, label in offered}
    missing = [v for v, _ in options if v not in values]
    if not missing:
        return None
    return {"missing": missing, "stored_as": {v: by_label[v] for v in missing if v in by_label},
            "shows_all": not any(v in values for v, _ in options)}


def keys_of(field: dict) -> tuple[str, dict]:
    """(override, settings) from a built field, whatever its key prefix."""
    override, settings = "", {}
    for key, value in field.items():
        if key.endswith("picklistOptionOverrides__c") and value:
            override = str(value)
        elif key.endswith("picklistOptionSettings__c") and value:
            try:
                settings = json.loads(value) if isinstance(value, str) else dict(value)
            except ValueError:
                settings = {}
    return override, settings


def rendered(field: dict, offered: list) -> list[tuple[str, str]]:
    """The options the package draws for a built field: the override's values the record type offers, in its order
    (every value when it names none of them), each with its settings label or the org's own."""
    override, settings = keys_of(field)
    labels = dict(offered)
    chosen = [v for v in override.split(";") if v and v in labels]
    shown = chosen or [v for v, _ in offered]
    return [(v, str((settings.get(v) or {}).get("label") or labels[v])) for v in shown]


def differences(options: list, shown: list, offered: list) -> list[tuple[str, str, str]]:
    """(what, plan, form) for each difference between the planned options and what the form draws."""
    rows = []
    shown_values = [v for v, _ in shown]
    labels = dict(offered)
    missing = [v for v, _ in options if v not in shown_values]
    extra = [v for v in shown_values if v not in {v for v, _ in options}]
    if missing:
        rows.append(("options missing", ", ".join(missing), "not offered"))
    if extra:
        rows.append(("options extra", "not planned", ", ".join(extra)))
    have = dict(shown)
    for value, label in options:
        want = label or labels.get(value) or value
        if value in have and have[value] != want:
            rows.append((f"option {value} label", want, have[value]))
    order = [v for v in shown_values if v in {v for v, _ in options}]
    if not missing and not extra and order != [v for v, _ in options]:
        rows.append(("options order", ", ".join(v for v, _ in options), ", ".join(order)))
    return rows
