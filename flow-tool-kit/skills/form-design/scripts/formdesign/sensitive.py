"""The sensitive-information check: every question form-migrate marked sensitive is asked about, then decided.

form-migrate marks a question that collects a government identifier, an account number, health information, a
password, or a date of birth with the person's name (``ir.json`` ``fields[].sensitive``). The plan carries the mark on
the field it becomes, as ``"sensitive": {"category": ..., "answer": ...}``, and the decision only the person can make
is asked in ``questions`` until it is answered:

    not collected   the field leaves the form: it goes in ``dropped`` with the reason, never stays on a page
    encrypted       an encrypted field that only the people who need it can read, kept out of emails, PDFs, prefill
    ordinary        an ordinary field, on the person's word (a warning stays, so a reviewer sees it)

A source field in ``dropped`` is already decided. ``problems(plan, ir)`` returns (errors, warnings). Messages name a
date asked as Month, Day and Year by the one question it is (``sensitive.question``), never by its first part.
"""
from __future__ import annotations

import json
import re

from . import conditions

ANSWERS = ("not collected", "encrypted", "ordinary")


def shown(source: dict) -> str:
    """How a source question reads in a message: a date asked in parts by its date (form-migrate's question), else
    its label."""
    return (source.get("sensitive") or {}).get("question") or source.get("label") or ""


def problems(plan: dict, ir: dict | None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if not ir:
        return errors, warnings
    placed = conditions.by_source_id(plan)
    dropped = {d.get("source_id") for d in plan.get("dropped") or []}
    asked = json.dumps(plan.get("questions") or [])
    for source in ir.get("fields") or []:
        mark = source.get("sensitive")
        if not mark or source.get("id") in dropped:
            continue
        field = placed.get(source.get("id"))
        if field is None:
            continue  # the source-field check reports a question that is neither placed nor dropped
        where = f"source field {source['id']} ({shown(source)!r})"
        kind = mark.get("kind") or mark.get("category") or "sensitive information"
        carried = field.get("sensitive")
        if not isinstance(carried, dict):
            errors.append(f"{where} collects {kind}: carry it onto the plan field as sensitive "
                          "{category, answer} and ask the person whether to collect it at all and how to store it")
            continue
        answer = str(carried.get("answer") or "").strip().lower()
        if not answer:
            if not re.search(rf"(?<!\w){re.escape(source['id'])}(?!\w)", asked):
                errors.append(f"{where} collects {kind} and nobody was asked: add a question naming {source['id']} "
                              "(collect it at all? an encrypted field with restricted access, or not stored?)")
            else:
                warnings.append(f"{where} collects {kind}: the person's answer is still open")
        elif answer not in ANSWERS:
            errors.append(f"{where}: sensitive.answer {answer!r} is not one of {', '.join(ANSWERS)}")
        elif answer == "not collected":
            errors.append(f"{where}: the answer is not collected, so it goes in dropped with that reason, not on the form")
        elif answer == "ordinary":
            warnings.append(f"{where} collects {kind} in an ordinary field, on the person's answer: everyone who reads "
                            "the submission sees it; keep it out of emails, PDFs and prefill")
    return errors, warnings
