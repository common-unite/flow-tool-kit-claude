"""Clean up proposed staging field names.

Two layers, deliberately separated.

**Mechanical** rules are the ones a machine should always get right: camelCase
that lost its word boundaries, initialisms flattened to title case, abbreviations
nobody should have to expand mentally, and UI phrasing that describes a widget
rather than the data ("check all that apply").

**Judgment** renames are the rest, and they cannot be automated honestly. A name
built from question text truncates mid-sentence, and a name mirrored from the
target inherits whatever was wrong with the target. Those live in a per-form
overrides file so a human decision survives regeneration instead of being
silently reapplied or silently lost.
"""

from __future__ import annotations

import json
import os
import re

# Initialisms that should never be title-cased into a word.
_INITIALISMS = {
    "sms": "SMS", "id": "ID", "url": "URL", "zip": "ZIP", "faq": "FAQ",
    "ein": "EIN", "usa": "USA", "ssn": "SSN", "dob": "DOB",
}

# Abbreviations expanded, per the house rule against shortened names.
_ABBREVIATIONS = {
    "app": "Application", "apps": "Applications", "num": "Number",
    "addr": "Address", "info": "Information", "org": "Organization",
    "amt": "Amount", "qty": "Quantity", "desc": "Description",
}

# Phrasing that describes the input widget rather than the data it holds.
_UI_NOISE = re.compile(
    r"\b(multi[\s_]?select|check\s+all\s+that\s+apply|select\s+all|"
    r"choose\s+one|if\s+applicable|please\s+specify)\b",
    re.I,
)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _split_camel(token: str) -> list[str]:
    """`ContactFound` -> ['Contact', 'Found']; leaves ALLCAPS intact."""
    if token.isupper():
        return [token]
    return _CAMEL_BOUNDARY.sub(" ", token).split()


def clean_name(api_name: str) -> str:
    """Apply every mechanical rule to a proposed API name."""
    if not api_name:
        return api_name
    suffix = "__c" if api_name.endswith("__c") else ""
    stem = api_name[: -len(suffix)] if suffix else api_name

    stem = _UI_NOISE.sub(" ", stem.replace("_", " "))

    words: list[str] = []
    for raw in stem.split():
        for part in _split_camel(raw):
            lowered = part.lower()
            if lowered in _INITIALISMS:
                words.append(_INITIALISMS[lowered])
            elif lowered in _ABBREVIATIONS:
                words.append(_ABBREVIATIONS[lowered])
            else:
                words.append(part.capitalize())

    return "_".join(words) + suffix


def load_overrides(form_dir: str) -> dict[str, str]:
    """Read the per-form judgment renames, if any."""
    path = os.path.join(form_dir, "name-overrides.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle).get("renames", {})


def apply(proposals, overrides: dict[str, str] | None = None) -> list[dict]:
    """Clean names in place and report what changed and why."""
    overrides = overrides or {}
    changes = []

    for proposal in proposals:
        if not proposal.staging_field or not proposal.disposition.startswith("create"):
            continue
        original = proposal.staging_field

        mechanical = clean_name(original)
        if mechanical != original:
            proposal.staging_field = mechanical

        override = overrides.get(proposal.field_id)
        if override:
            proposal.staging_field = override

        if proposal.staging_field != original:
            reason = "reviewed for readability" if override else "name cleanup"
            proposal.notes.append(
                f"Renamed from {original} ({reason}). The staging field and its "
                "target still share a type and value set; only the name differs, "
                "and the pair is recorded in this workbook."
            )
            changes.append(
                {
                    "field_id": proposal.field_id,
                    "label": proposal.label,
                    "from": original,
                    "to": proposal.staging_field,
                    "kind": "judgment" if override else "mechanical",
                }
            )

    return changes