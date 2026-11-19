"""Round-trip the mappings file: read a reviewed CSV or JSON back in.

The mappings file is regenerated on every run, so a reviewer's edits have to
survive that. They are lifted out into ``decisions.json``, keyed by source field
id, and re-applied on each regeneration - the same pattern
``name-overrides.json`` uses, for the same reason.

**Field ID is the join key**, which is why the file tells reviewers not to edit
it. Everything else can be reordered or reformatted by a spreadsheet app or an
editor without consequence.

Reviewers write one of:

* ``OK``   - approve the proposal as it stands
* ``SKIP`` - do not stage this field at all
* a name in *Your Field Name* - use that API name instead

Blank means "not reviewed", which is deliberately distinct from approved. A
mappings file nobody has looked at must not read as accepted.
"""

from __future__ import annotations

import csv
import json
import os

DECISION_COLUMNS = ["Decision", "Your Field Name", "Your Notes"]

_KEY_COLUMN = "Field ID"
_DECISIONS_FILE = "decisions.json"

# Reviewers will not type exactly what we ask. Accept the obvious variants.
_APPROVE = {
    "ok", "y", "yes", "approve", "approved", "confirm", "confirmed", "x", "✓",
    "valid", "use this field", "use", "correct", "good", "keep", "looks good",
}
_SKIP = {
    "skip", "n", "no", "bypass", "exclude", "ignore", "drop", "not needed",
    "remove", "delete", "n/a", "na",
}


def read_edits(path: str) -> dict[str, dict]:
    """Extract reviewer decisions from an edited mappings file, CSV or JSON."""
    if path.lower().endswith(".json"):
        return read_json(path)
    return read_csv(path)


def read_csv(path: str) -> dict[str, dict]:
    """Extract reviewer decisions from an edited mappings CSV.

    Uses ``utf-8-sig`` because spreadsheet apps often write a byte order mark,
    and ``newline=""`` because some write CR line endings - both silently
    corrupt the first column header otherwise, which is the join key.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return _from_rows(csv.DictReader(handle))


def read_json(path: str) -> dict[str, dict]:
    """Extract reviewer decisions from an edited ``mappings.json``.

    Accepts the file ``mappings.to_json`` writes (``{"rows": [...]}``) or a bare
    list of rows, so edits from any tool that keeps the column names come back.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return _from_rows(data.get("rows", []) if isinstance(data, dict) else data)


def _from_rows(rows) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        field_id = str(row.get(_KEY_COLUMN) or "").strip()
        if not field_id:
            continue

        verdict = str(row.get("Decision") or "").strip()
        override = str(row.get("Your Field Name") or "").strip()
        note = str(row.get("Your Notes") or "").strip()
        if not (verdict or override or note):
            continue

        lowered = verdict.lower()
        if lowered in _SKIP:
            action = "skip"
        elif lowered in _APPROVE:
            action = "approve"
        elif verdict:
            action = "unrecognized"
        else:
            action = "approve" if override else "note"

        found[field_id] = {
            "action": action,
            "verdict_as_written": verdict,
            "field_name": override,
            "note": note,
        }
    return found


def load(form_dir: str) -> dict[str, dict]:
    path = os.path.join(form_dir, _DECISIONS_FILE)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle).get("decisions", {})


def save(form_dir: str, decisions: dict[str, dict]) -> str:
    """Persist decisions so regenerating the mappings file cannot lose them."""
    path = os.path.join(form_dir, _DECISIONS_FILE)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "_comment": (
                    "Reviewer decisions from the mappings file, keyed by "
                    "source field id so they survive regeneration."
                ),
                "decisions": decisions,
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )
    return path


def apply(proposals, decisions: dict[str, dict]) -> list[dict]:
    """Apply reviewer decisions to the Field Plan. Returns what was applied.

    Beyond the spreadsheet's own OK/SKIP, decisions.json may carry richer actions
    that a reviewer expressed in prose and a human interpreted:

    * ``formula``   - stage as a formula field, usually reading the Account lookup
    * ``extend_packaged`` - a packaged picklist is the right field but lacks some
      values; add them to the packaged picklist in this org (a subscriber can add
      values to a restricted packaged picklist, and map them to their
      controlling values when it is dependent) instead of creating a new field
    * ``approve`` may carry a ``type`` to force the field shape
    """
    applied = []
    for proposal in proposals:
        decision = decisions.get(proposal.field_id)
        if not decision:
            continue

        action = decision["action"]

        if action == "formula":
            proposal.disposition = "create_formula"
            proposal.staging_field = decision.get("field_name") or proposal.staging_field
            proposal.staging_label = (decision.get("field_name") or "").replace("__c", "")
            proposal.proposed_type = decision.get("type", "Formula (Checkbox)")
            proposal.confidence = "confirmed"
            proposal.evidence = (
                "The reviewer asked for a formula field reading the Account lookup rather "
                "than a stored value."
            )
            proposal.notes.append(decision.get("note", ""))
            applied.append({**decision, "field_id": proposal.field_id, "applied": True})
            continue

        if action == "extend_packaged":
            proposal.disposition = "extend_packaged"
            proposal.staging_field = decision.get("field_name") or proposal.staging_field
            proposal.confidence = "confirmed"
            missing = decision.get("values") or []
            proposal.evidence = (
                "The packaged picklist is the right field; add the missing values "
                "to it in this org"
                + (f" ({', '.join(missing)})" if missing else "")
                + ". A subscriber can add values to a restricted packaged picklist; "
                "for a dependent picklist, also map each new value to its "
                "controlling values."
            )
            if decision.get("note"):
                proposal.notes.append(decision["note"])
            applied.append({**decision, "field_id": proposal.field_id, "applied": True})
            continue

        if action == "unrecognized":
            proposal.notes.append(
                f"Reviewer wrote \"{decision['verdict_as_written']}\" in the "
                "Decision column, which is not OK or SKIP. Left unapplied - "
                "confirm what was meant."
            )
            applied.append({**decision, "field_id": proposal.field_id, "applied": False})
            continue

        if decision["action"] == "skip":
            proposal.disposition = "skipped"
            proposal.staging_field = None
            proposal.staging_label = None
            proposal.confidence = "confirmed"
            proposal.evidence = "Excluded by the reviewer."
        else:
            if decision["field_name"]:
                proposal.notes.append(
                    f"Renamed from {proposal.staging_field} by the reviewer."
                )
                proposal.staging_field = decision["field_name"]
            if decision.get("type"):
                proposal.proposed_type = decision["type"]
            if action == "approve":
                proposal.confidence = "confirmed"
                if proposal.disposition in ("ask_client", "not_mapped"):
                    # An approved question is no longer a question.
                    proposal.disposition = (
                        "reuse_packaged"
                        if (proposal.staging_field or "").startswith("FlowToolKit__")
                        else "create_form_specific"
                    )

        if decision["note"]:
            proposal.notes.append(f"Reviewer note: {decision['note']}")

        applied.append({**decision, "field_id": proposal.field_id, "applied": True})
    return applied


def summarize(proposals, decisions: dict[str, dict]) -> dict[str, int]:
    """How much of the mappings file has actually been reviewed."""
    reviewable = [p for p in proposals if p.disposition != "not_mapped"]
    return {
        "rows_total": len(proposals),
        "rows_needing_decision": sum(
            1 for p in reviewable if p.disposition == "ask_client"
        ),
        "rows_reviewed": len(decisions),
        "approved": sum(1 for d in decisions.values() if d["action"] == "approve"),
        "skipped": sum(1 for d in decisions.values() if d["action"] == "skip"),
        "unrecognized": sum(
            1 for d in decisions.values() if d["action"] == "unrecognized"
        ),
    }