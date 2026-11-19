"""Find the questions that collect sensitive information, whatever the source.

A government identifier, a bank or card number, a health detail, a password, or a date of birth on a form that also
asks who the person is: each one, saved on a submission record, is readable by everyone who can read that record,
travels in confirmation emails and PDFs, and on a public (guest) form is typed by people nobody has verified. The
first decision is whether to collect it at all; the second is how to store it (an encrypted field with restricted
access, or not stored). This module only finds and marks them; ``questions.py`` asks, and form-design carries the
answer into the plan.

``mark(document)`` sets ``fields[].sensitive`` = ``{"category", "kind", "matched"}`` on each such question and adds
one finding (source ``sensitive``). It reads the label, the help text and the field id, and is safe to run twice.

A date asked as Month, Day and Year (``dateparts.py``) is one question: the first part carries the mark, with
``parts`` (the three ids) and ``question`` (how it reads, "Date of Birth (asked as Month, Day and Year)"), and the
other two carry none. A trio is a date of birth only when its context says so (a "Date of Birth:" text block, a
"Birth Month" label); any other trio is an ordinary date.
"""

from __future__ import annotations

import re

# category -> (what to call it, the pattern). Order matters: the first match names the category.
CATEGORIES = [
    ("password", "a password or security answer", re.compile(
        r"\bpass(word|code|phrase)\b|\bsecurity (question|answer)\b|\bmother'?s maiden name\b|\bpin( number| code)?\b",
        re.I)),
    ("government_id", "a government identifier", re.compile(
        r"\bsocial security\b|\bssn\b|\bsocial insurance (number|no)\b|\btax(payer)? (id|identification)\b|\btin\b|"
        r"\bitin\b|\bein\b|\bemployer identification\b|\bpassport\b|\bdriver'?s?'? licen[cs]e (number|no|#)|"
        r"\blicen[cs]e (number|no|#)|\bnational (id|identity|insurance)\b|\balien (registration )?(number|no)\b|"
        r"\bvisa (number|no)\b|\bgovernment[- ]issued id\b|\bstate id\b|\bid card number\b", re.I)),
    ("financial_account", "a bank or card account", re.compile(
        r"\bbank account\b|\baccount (number|no|#)|\brouting (number|no)\b|\biban\b|\bsort code\b|"
        r"\b(credit|debit) card\b|\bcard (number|no)\b|\bcvv\b|\bcvc\b|\bcard security code\b", re.I)),
    ("health", "health information", re.compile(
        r"\bdiagnos|\bmedical (condition|history|record|information)|\bhealth (condition|information|history|"
        r"insurance|issue)|\bmedications?\b|\bdisabilit|\ballerg|\bhiv\b|\bmental health\b|\bpregnan|\bmedicaid\b|"
        r"\bmedicare\b|\binsurance (member )?(id|number)\b|\bimmuni[sz]ation|\bvaccinat", re.I)),
]

_BIRTHDATE = re.compile(r"\bdate of birth\b|\bbirth\s*date\b|\bbirthday\b|\bdob\b", re.I)
_IDENTITY = re.compile(r"\b(first|last|full|legal|given|family|sur)\s*name\b|^name$|\bname of (the )?applicant\b", re.I)

KINDS = {category: kind for category, kind, _ in CATEGORIES}
KINDS["birthdate"] = "a date of birth with the person's name"


def classify(entry: dict, identity_on_form: bool = False) -> dict | None:
    """``{"category", "kind", "matched"}`` for a sensitive question, else None."""
    text = " ".join(str(entry.get(key) or "") for key in ("label", "help_text"))
    words = f"{text} {str(entry.get('id') or '').replace('_', ' ')}"
    if (entry.get("input_type") or "") == "password":
        return {"category": "password", "kind": KINDS["password"], "matched": "a password box"}
    for category, kind, pattern in CATEGORIES:
        found = pattern.search(words)
        if found:
            return {"category": category, "kind": kind, "matched": found.group(0)}
    found = _BIRTHDATE.search(words)
    if found and identity_on_form:
        return {"category": "birthdate", "kind": KINDS["birthdate"], "matched": found.group(0)}
    return None


def shown(entry: dict) -> str:
    """How a marked question reads in findings and questions: a date asked in parts by its date, else its label."""
    return (entry.get("sensitive") or {}).get("question") or entry.get("label") or ""


def _mark_date_parts(document: dict, identity: bool) -> None:
    """One mark per date asked as Month, Day and Year, on its first part (see the module docstring)."""
    from . import dateparts

    by_id = {f.get("id"): f for f in document.get("fields") or []}
    for group in dateparts.groups(document):
        parts = [by_id[i] for i in group.ids]
        found = next((p["sensitive"] for p in parts if p.get("sensitive")), None)
        if found is None and group.birth and identity:
            found = {"category": "birthdate", "kind": KINDS["birthdate"], "matched": group.context}
        for part in parts:
            part.pop("sensitive", None)
        if found:
            parts[0]["sensitive"] = {**found, "parts": group.ids, "question": group.question}


def mark(document: dict) -> list[dict]:
    """Mark each sensitive question in place and refresh the one ``sensitive`` finding. Returns the marked fields."""
    fields = document.get("fields") or []
    identity = any(_IDENTITY.search((f.get("label") or "").strip()) for f in fields)
    for entry in fields:
        found = classify(entry, identity)
        if found:
            entry["sensitive"] = found
        else:
            entry.pop("sensitive", None)
    _mark_date_parts(document, identity)
    marked = [entry for entry in fields if entry.get("sensitive")]
    findings = [f for f in document.get("findings") or [] if f.get("source") != "sensitive"]
    if marked:
        findings.append({
            "source": "sensitive",
            "message": f"{len(marked)} question(s) collect sensitive information: "
            + "; ".join(f"{f['id']} \"{shown(f)}\" ({f['sensitive']['kind']})" for f in marked[:8])
            + ". Decide with the person whether to collect each at all and how to store it (questions.md); "
            "on a public (guest) form, prefer not collecting it.",
        })
    document["findings"] = findings
    return marked
