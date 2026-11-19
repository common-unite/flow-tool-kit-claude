"""The required-flag check: every placed question keeps the source's required flag, or the person confirmed the change.

form-migrate reads whether the source requires each question (``ir.json`` ``fields[].required``: true or false, absent
when the source does not say). The plan keeps it exactly (references/decisions.md). A plan field whose ``required``
differs is a change only the person can confirm, so it is asked in ``questions`` until the answer is recorded on the
field as ``required_change``, the person's reason in a few words:

    {"source_id": "q4", "label": "Date of birth", "required": false,
     "required_change": "the person keeps it optional: some volunteers never give it"}

A source field in ``dropped`` is already decided. ``problems(plan, ir)`` returns (errors, warnings).
"""
from __future__ import annotations

import json
import re

from . import conditions, sensitive


def word(required: bool) -> str:
    return "required" if required else "optional"


def problems(plan: dict, ir: dict | None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if not ir:
        return errors, warnings
    placed = conditions.by_source_id(plan)
    dropped = {d.get("source_id") for d in plan.get("dropped") or []}
    asked = json.dumps(plan.get("questions") or [])
    for source in ir.get("fields") or []:
        wanted = source.get("required")
        field = placed.get(source.get("id"))
        if not isinstance(wanted, bool) or field is None or source.get("id") in dropped:
            continue  # the source does not say, or the source-field check reports a question neither placed nor dropped
        if bool(field.get("required")) == wanted or str(field.get("required_change") or "").strip():
            continue
        where = (f"source field {source['id']} ({sensitive.shown(source)!r}) is {word(wanted)} in the source and "
                 f"{word(not wanted)} in the plan")
        if re.search(rf"(?<!\w){re.escape(source['id'])}(?!\w)", asked):
            warnings.append(f"{where}: the person's answer is still open; record it as required_change on the field")
        else:
            errors.append(f"{where}: keep the source's flag, or ask the person in a question naming {source['id']} "
                          "and record the answer as required_change on the field")
    return errors, warnings
