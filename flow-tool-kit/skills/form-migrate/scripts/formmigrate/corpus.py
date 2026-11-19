"""Merge several forms into one IR so staging fields are named across all of them.

The rule this implements is already doctrine and previously had no code:

    Name org-canonical fields only after batch-parsing every form in the org.
    Naming from one form bakes that form's vocabulary into fields every future
    form must live with.

Run per-form and ten surveys asking "How satisfied are you?" produce ten
near-duplicate staging fields, because each Field Plan only ever sees its own
form. Merged first, that question is proposed ONCE and every form binds to it.

Two questions are the same when their normalized label AND their type family
match. Option sets are deliberately NOT part of the identity test, because the
interesting case is the one where they differ: the same question asked with
different choices on different forms is a real inconsistency somebody should
decide about, and folding it silently into one field is how a picklist ends up
with the union of two committees' vocabularies.
"""

from __future__ import annotations

import re

from . import ir

_WORD_RE = re.compile(r"[a-z0-9]+")

# Wording that varies without changing what a question asks.
_NOISE = {
    "please", "your", "you", "the", "a", "an", "of", "is", "are", "do", "does",
    "did", "in", "to", "for", "and", "or", "this", "that", "we", "us", "our",
    "choose", "all", "apply", "select", "up", "three", "optional",
}


def normalize_label(label: str) -> str:
    """A comparable form of a question's text."""
    words = [word for word in _WORD_RE.findall((label or "").lower())
             if word not in _NOISE]
    return " ".join(words)


def _family(field: dict) -> str:
    """Coarse type family, so a rating and a picklist never merge."""
    input_type = (field.get("input_type") or "").lower()
    if input_type in ("choice-group", "select", "multiselect"):
        return "multi" if "checkbox" in (field.get("validation") or []) else "choice"
    if input_type in ("rating", "scale"):
        return input_type
    if input_type in ("textarea",):
        return "longtext"
    return input_type or "text"


def merge(documents: dict[str, dict], platform: str = "corpus") -> dict:
    """Combine several IR documents into one, collapsing repeated questions.

    ``documents`` maps a form name to its IR. The merged document is a normal IR
    that ``fieldplan``, ``validate`` and ``workbook`` all read unchanged; each
    field gains ``forms`` (every form asking it) and ``variants`` (the differing
    option sets, when they differ).
    """
    if not documents:
        raise ValueError("A corpus needs at least one document.")

    coverage_states: dict[str, set[str]] = {}
    merged_fields: dict[str, dict] = {}
    order: list[str] = []
    findings: list[dict] = []
    section_paths: list[str] = []
    images: list[str] = []

    for form_name, document in documents.items():
        for aspect, state in ((document.get("source") or {}).get("coverage") or {}).items():
            coverage_states.setdefault(aspect, set()).add(state)
        section_paths.extend(
            f"{form_name}/{path}" for path in document["form"].get("section_paths", [])
        )
        images.extend(document.get("images") or [])
        findings.extend(
            {**finding, "form": form_name} for finding in document.get("findings", [])
        )

        for field in document.get("fields", []):
            key = (normalize_label(field.get("label", "")), _family(field))
            option_labels = tuple(option["label"] for option in field.get("options", []))

            if key not in merged_fields:
                entry = dict(field)
                entry["forms"] = [form_name]
                entry["variants"] = []
                entry["section_path"] = form_name
                entry["corpus_key"] = " | ".join(key)
                merged_fields[key] = entry
                order.append(key)
                continue

            entry = merged_fields[key]
            entry["forms"].append(form_name)
            # Required anywhere means the staging field must accept it, but the
            # per-form requirement is a component setting, not a field one.
            entry["required"] = entry.get("required") or field.get("required")

            existing = tuple(option["label"] for option in entry.get("options", []))
            if option_labels and option_labels != existing:
                entry["variants"].append(
                    {"form": form_name, "options": list(option_labels)}
                )

    document = ir.new_document(
        platform=platform,
        form_name=f"{len(documents)} forms",
        coverage={
            # The corpus is only as trustworthy as its weakest member: if ANY
            # form failed to capture an aspect, the merged view has a hole there.
            aspect: _worst(states) for aspect, states in coverage_states.items()
        },
    )
    document["source"]["forms"] = list(documents)
    document["form"]["section_paths"] = section_paths
    document["fields"] = [merged_fields[key] for key in order]
    document["structure"] = [
        {"id": name, "tag": "form", "layout": [], "parent_id": None,
         "has_condition": False}
        for name in documents
    ]
    document["images"] = sorted(set(images))
    document["findings"] = findings + _corpus_findings(document["fields"], documents)
    return ir.finalize(document)


# Worst-first: a hole anywhere in the corpus is a hole in the corpus.
_COVERAGE_RANK = ("unknown", "not_captured", "none_exist", "hand_authored", "parsed")


def _worst(states: set[str]) -> str:
    for state in _COVERAGE_RANK:
        if state in states:
            return state
    return "unknown"


def _corpus_findings(fields: list[dict], documents: dict) -> list[dict]:
    """Report what the merge revealed that no single form could show."""
    findings = []

    shared = [field for field in fields if len(field["forms"]) > 1]
    if shared:
        findings.append(
            {
                "source": "corpus",
                "message": f"{len(shared)} question(s) appear on more than one "
                f"form and collapse to one staging field each. These are the "
                "org-canonical candidates: name them for the ROLE, not for the "
                "form you happened to read first.",
            }
        )
    for field in shared:
        findings.append(
            {
                "source": "corpus",
                "message": f'"{field["label"]}" is asked by '
                f"{len(field['forms'])} forms: {', '.join(field['forms'])}.",
            }
        )

    for field in fields:
        if not field.get("variants"):
            continue
        findings.append(
            {
                "source": "corpus",
                "message": f'"{field["label"]}" is asked with DIFFERENT option '
                f"sets across forms ({len(field['variants']) + 1} variants). One "
                "staging field cannot hold both cleanly. Decide whether these are "
                "genuinely the same question before merging them.",
                "variants": [field.get("options", [])] + field["variants"],
            }
        )

    total = sum(len(document.get("fields", [])) for document in documents.values())
    findings.append(
        {
            "source": "corpus",
            "message": f"{total} question(s) across {len(documents)} form(s) "
            f"reduced to {len(fields)} distinct staging field(s) "
            f"({total - len(fields)} duplicates collapsed).",
        }
    )
    return findings


# Packaged generic-slot families, and the question shape each one holds.
#
# The scale batteries are FIXED-scale: the renderer draws their packaged scale
# and ignores option overrides, so they fit ONLY when the question genuinely
# asks for that scale. A question with its own end labels ("Very difficult ..
# Very easy") is NOT an agreement question and must not be parked in one.
_SLOT_FAMILIES = {
    "text": "Text_Question_",
    "longtext": "Long_Text_Question_",
    "number": "Number_Question_",
    "boolean": "Boolean_Question_",
    "agreement": "Agreement_Question_",
    "satisfaction": "Satisfaction_Question_",
    "frequency": "Frequency_Question_",
    "scale": "Scale_Question_",
    "rating": "Rating_",
}

# The packaged scale batteries are FIXED-scale: the renderer draws the value set
# below and ignores option overrides. A question matches one ONLY when its own
# anchors say the same thing, or the battery silently replaces the wording the
# form author chose. Sourced from the field metadata, not guessed.
#
#   Agreement_Question_1-10  Strongly Disagree .. Strongly Agree
#   Satisfaction_Question_1-5  Very Dissatisfied .. Very Satisfied
#   Frequency_Question_1-5     Never .. Always
#   Scale_Question_1-3         0 .. 10          (the NPS shape)
#   Rating_1-5                 1 .. 5
_BATTERY_ENDS = {
    "agreement": (("strongly disagree", "strongly agree"), ("disagree", "agree")),
    "satisfaction": (("very dissatisfied", "very satisfied"),
                     ("dissatisfied", "satisfied")),
    "frequency": (("never", "always"),),
}

# A 0-10 scale is what Scale_Question holds, whatever its anchors say: the
# anchors ride along as prepend/append rather than being part of the value set.
_SCALE_MAX = 10

# When a family runs out of packaged slots, the overflow field still has to be
# created with the shape the question actually needs.
_OVERFLOW_TYPE = {
    "longtext": "LongTextArea",
    "text": "Text",
    "number": "Number",
    "boolean": "Checkbox",
    "agreement": "Picklist",
    "rating": "Number",
}


def _slot_family(field: dict) -> str | None:
    """Which packaged slot family a question can legitimately reuse."""
    family = _family(field)
    if family == "longtext":
        return "longtext"
    if family in ("text", "email", "tel", "url"):
        return "text"
    if family == "rating":
        return "rating"
    if family == "scale":
        scale = field.get("scale") or {}
        low = str(scale.get("low_label") or "").strip().lower()
        high = str(scale.get("high_label") or "").strip().lower()

        # A battery matches only when the question's own anchors say what the
        # packaged value set says. Anything looser and the fixed scale replaces
        # wording the form author chose, which looks right in config and renders
        # the wrong question.
        for battery, pairs in _BATTERY_ENDS.items():
            for start, end in pairs:
                if low.startswith(start) and high.endswith(end):
                    return battery

        # A 0-10 range is exactly what Scale_Question holds. Its anchors are not
        # part of the value set, so they survive as prepend/append.
        if scale.get("max") == _SCALE_MAX:
            return "scale"

        # Everything else is a scale with bespoke anchors. It belongs in a NUMBER
        # slot rather than a bespoke picklist: a 1-to-5 rating stored as a
        # picklist is a number pretending to be a category and cannot be
        # averaged, charted or trended without conversion first.
        return "number"
    return None


def shape_census(fields: list[dict], schema) -> dict:
    """Compare what the corpus needs against the packaged slots available.

    This is the question a per-form plan can never answer: ten forms each
    needing three text slots is thirty proposals form-by-form, but only ten
    slots exist and they are reused across forms. Counting once, across the
    whole corpus, is the only way to see whether the packaged inventory fits.
    """
    # Demand is the BUSIEST SINGLE FORM, not the corpus total: slots are
    # exclusive per form, and every form reuses the same slot numbers for its
    # own questions. Summing across forms invents a shortage that does not exist.
    per_form: dict[str, dict[str, int]] = {}
    needed: dict[str, list[dict]] = {}
    unmatched: list[dict] = []
    for field in fields:
        family = _slot_family(field)
        if family is None:
            unmatched.append(field)
            continue
        needed.setdefault(family, []).append(field)
        for form in field.get("forms") or ["_"]:
            per_form.setdefault(form, {})
            per_form[form][family] = per_form[form].get(family, 0) + 1

    available = {}
    for family, prefix in _SLOT_FAMILIES.items():
        available[family] = sorted(
            entry.local_name for entry in schema.mappable()
            if entry.local_name.startswith(prefix)
        )

    report = {"families": {}, "unmatched": unmatched, "per_form": per_form}
    for family in sorted(set(needed) | set(available)):
        peak = max((counts.get(family, 0) for counts in per_form.values()), default=0)
        busiest = max(
            (form for form in per_form if per_form[form].get(family, 0) == peak),
            default="",
        ) if peak else ""
        have = len(available.get(family, []))
        report["families"][family] = {
            "needed": peak,
            "corpus_total": len(needed.get(family, [])),
            "busiest_form": busiest,
            "available": have,
            "shortfall": max(0, peak - have),
            "questions": [entry["label"] for entry in needed.get(family, [])],
            "slots": available.get(family, []),
        }
    return report


def census_findings(report: dict) -> list[dict]:
    """Turn a shape census into findings a reviewer can act on."""
    findings = []
    for family, entry in sorted(report["families"].items()):
        if not entry["needed"]:
            continue
        if entry["shortfall"]:
            findings.append({
                "source": "corpus",
                "message": f"'{entry['busiest_form']}' alone needs "
                f"{entry['needed']} {family} slot(s) but the package ships only "
                f"{entry['available']}. {entry['shortfall']} custom field(s) are "
                "unavoidable -- slots are exclusive within one form.",
            })
        else:
            findings.append({
                "source": "corpus",
                "message": f"{entry['corpus_total']} {family} question(s) across "
                f"the corpus fit {entry['available']} packaged slot(s): the "
                f"busiest single form ('{entry['busiest_form']}') needs only "
                f"{entry['needed']}, and every other form reuses the same slots "
                "for its own questions. Reuse them; create nothing.",
            })
    if report["unmatched"]:
        findings.append({
            "source": "corpus",
            "message": f"{len(report['unmatched'])} question(s) match no packaged "
            "generic slot and need their own field. Scales carrying their own end "
            "labels are the common case: a FIXED packaged battery would replace "
            "that wording with its own, which looks correct in config and renders "
            "the wrong scale.",
        })
    return findings


def assign_slots(fields: list[dict], schema) -> dict[str, dict]:
    """Allocate packaged generic slots to the questions that can reuse them.

    The Field Plan matches questions to fields by LABEL, which can never find a
    generic slot: no question is worded like "Agreement Question 3". Generic
    slots are matched by SHAPE, and only the corpus knows how many of each shape
    exist in total, so allocation belongs here.

    Without this step every survey question proposes a brand-new field, which is
    the anti-pattern the staging-field doctrine calls the number one mistake in
    a client build: a per-form schema on an object designed as a generic landing
    pad.

    Allocation is in document order and stops at the packaged supply. Overflow
    is returned too, marked, so the shortfall is visible rather than silent.
    """
    available = {}
    for family, prefix in _SLOT_FAMILIES.items():
        available[family] = sorted(
            (entry for entry in schema.mappable()
             if entry.local_name.startswith(prefix)),
            key=lambda entry: _slot_number(entry.local_name),
        )

    # Slots are exclusive PER FORM, not across the corpus. A submission record
    # belongs to one form, and the per-form wording lives on the component's
    # customLabel, so Agreement_Question_1 can be "My workload is sustainable"
    # on one survey and "The board meets effectively" on another with no
    # collision -- they are different records.
    #
    # Allocating globally instead is the error this comment exists to prevent:
    # it turns a comfortable fit into a fabricated shortage. On a ten-survey
    # corpus it reported 12 long-text questions competing for 5 slots and
    # invented 7 custom fields, when the busiest single survey needed 2.
    taken: dict[str, set[int]] = {}          # form -> slot indexes already used
    assignments: dict[str, dict] = {}

    for field in fields:
        family = _slot_family(field)
        if family is None:
            continue
        pool = available.get(family) or []
        forms = field.get("forms") or [field.get("section_path") or "_"]

        # A question shared by several forms needs one slot free in ALL of them.
        index = 0
        while any(index in taken.get(f"{form}:{family}", set()) for form in forms):
            index += 1

        if index >= len(pool):
            assignments[field["id"]] = {
                "family": family,
                "slot": None,
                "overflow": True,
                "reason": f"No {family} slot left ({len(pool)} exist) for "
                f"{', '.join(forms)}. This question needs a custom field.",
            }
            for form in forms:
                taken.setdefault(f"{form}:{family}", set()).add(index)
            continue

        slot = pool[index]
        for form in forms:
            taken.setdefault(f"{form}:{family}", set()).add(index)
        assignments[field["id"]] = {
            "family": family,
            "slot": slot.api_name,
            "slot_label": slot.label,
            "overflow": False,
            "reason": f"Reuses the packaged {slot.local_name} slot. The question "
            "wording lives on the form component, never on the field, so other "
            "forms reuse the same slot for their own question.",
        }
    return assignments


def _slot_number(local_name: str) -> tuple:
    """Sort Text_Question_10 after Text_Question_9, not before Text_Question_1.

    The digits are followed by the ``__c`` suffix, so anchoring them to the end
    of the string matches nothing: every slot scores 0, the sort falls back to
    alphabetical, and ``Agreement_Question_10__c`` gets handed out first. The
    plan still works, but it reads as scrambled and a reviewer rightly stops
    trusting it.
    """
    match = re.search(r"(\d+)(?:__c)?$", local_name)
    return (int(match.group(1)) if match else 0, local_name)


def apply_slots(proposals, assignments: dict[str, dict]) -> None:
    """Rewrite proposals in place to reuse an assigned slot."""
    for proposal in proposals:
        assignment = assignments.get(proposal.field_id)
        if not assignment:
            continue
        if assignment["overflow"]:
            # Overflow still has to be created with the RIGHT shape. Falling
            # through to the generic text default stages a paragraph answer in
            # Text(255), which truncates silently at save time -- the answer is
            # simply shorter than what the respondent typed, and nothing errors.
            shape = _OVERFLOW_TYPE.get(assignment["family"])
            if shape and proposal.proposed_type in ("", "Text"):
                proposal.proposed_type = shape
            proposal.notes.append(assignment["reason"])
            continue
        proposal.disposition = "reuse_packaged"
        proposal.staging_field = assignment["slot"]
        proposal.staging_label = assignment.get("slot_label")
        proposal.confidence = "high"
        proposal.evidence = assignment["reason"]
        proposal.proposed_type = ""
        proposal.proposed_values = []


def per_form_index(fields: list[dict]) -> dict[str, list[str]]:
    """Which staging questions each form needs, for building components later."""
    index: dict[str, list[str]] = {}
    for field in fields:
        for form_name in field["forms"]:
            index.setdefault(form_name, []).append(field["id"])
    return index
