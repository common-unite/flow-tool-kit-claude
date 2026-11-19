"""Write the Field Plan as a mappings file a reviewer edits, in CSV or JSON.

The reviewer is usually the org's admin, so each row leads with what they
recognise (the question as it appears on the form) and only then shows where it
lands. Both formats carry the same rows; pick whichever the reviewer will edit:
a spreadsheet opens the CSV, any text editor or a script reads the JSON.

The **Field ID** is the join key that carries edits back in
(``decisions.read_edits``), so it is a first-class column and the file says not
to change it. The old connector records mapping sources by label, and labels
repeat across sections, so a row without an id is ambiguous on any form with
two addresses.
"""

from __future__ import annotations

import csv
import io
import json

# Reviewer columns come FIRST so they are what a spreadsheet opens on.
EDITABLE_COLUMNS = ["Decision", "Your Field Name", "Your Notes"]

COLUMNS = [
    *EDITABLE_COLUMNS,
    "Form Name", "Section Path", "Field ID", "Field Label",
    "Form Submission Field Name", "Form Submission Field Label",
    "Built On", "Reaches Target By", "Verify In Org",
    "Origin", "Target Object", "Target Field",
    "Disposition", "Confidence", "Sensitive", "Notes",
]

HOW_TO = (
    "Fill in only the first three columns. Decision: OK approves the row as "
    "proposed, SKIP leaves the question out. Your Field Name: a different API "
    "name to use instead. Your Notes: anything else. Leave a row blank if you "
    "have no opinion; blank means not reviewed. Do not change Field ID: it is how "
    "your answers are matched back."
)

# Plain-English disposition wording. The internal keys never reach the reviewer.
DISPOSITION_LABEL = {
    "skipped": "Excluded by you",
    "create_formula": "Create formula field",
    "extend_packaged": "Add the missing values to the packaged picklist",
    "reuse_packaged": "Use existing field",
    "keep_target": "Keep: already saved here",
    "create_org_canonical": "Create field (shared by every form in the org)",
    "create_form_specific": "Create field for this form",
    "ask_client": "Needs your decision",
    "not_mapped": "Not saved to Salesforce today",
    "folded": "Folded into one date question",
}

_PLACEMENT_LABEL = {
    "form_submission": "Form Submission form",
    "existing": "Its current form",
    "edition_unknown": "Depends on the edition",
}

_CONVERSION_LABEL = {
    "submission_field_maps": "Form Template Mapping (Apply Submission Field Maps)",
    "transform": "Transform row in the conversion flow",
    "existing": "Already saved there",
}


def _built_on(proposal) -> str:
    if proposal.placement == "source_object":
        return f"{proposal.component_object} form, mapped to Form Submission"
    if proposal.placement == "edition_unknown":
        return f"{_PLACEMENT_LABEL['edition_unknown']} ({proposal.component_object} form if paid)"
    return _PLACEMENT_LABEL.get(proposal.placement, proposal.placement)


def rows(form_name: str, proposals, decisions=None) -> list[dict]:
    """One dict per proposal, keyed by ``COLUMNS``."""
    decisions = decisions or {}
    out = []
    for proposal in proposals:
        decision = decisions.get(proposal.field_id, {})
        target_objects = sorted({t.split(".", 1)[0] for t in proposal.targets})
        target_fields = sorted({t.split(".", 1)[1] for t in proposal.targets if "." in t})
        out.append(
            {
                "Decision": decision.get("verdict_as_written", ""),
                "Your Field Name": decision.get("field_name", ""),
                "Your Notes": decision.get("note", ""),
                "Form Name": form_name,
                "Section Path": proposal.section_path,
                "Field ID": proposal.field_id,
                "Field Label": proposal.label,
                "Form Submission Field Name": proposal.staging_field or "",
                "Form Submission Field Label": proposal.staging_label or "",
                "Built On": _built_on(proposal),
                "Reaches Target By": _CONVERSION_LABEL.get(proposal.conversion, proposal.conversion),
                "Verify In Org": "Yes" if proposal.verify else "",
                "Origin": proposal.origin,
                "Target Object": ", ".join(target_objects),
                "Target Field": ", ".join(target_fields),
                "Disposition": DISPOSITION_LABEL.get(proposal.disposition, proposal.disposition),
                "Confidence": proposal.confidence,
                "Sensitive": getattr(proposal, "sensitive", ""),
                "Notes": " ".join([proposal.evidence, *proposal.notes]).strip(),
            }
        )
    return out


def to_csv(form_name: str, proposals, decisions=None) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows(form_name, proposals, decisions))
    return buffer.getvalue()


def to_json(form_name: str, proposals, decisions=None, summary=None) -> str:
    """The same rows as JSON, with the how-to and the counts on top."""
    return json.dumps(
        {
            "form_name": form_name,
            "how_to_edit": HOW_TO,
            "editable_columns": EDITABLE_COLUMNS,
            "summary": summary or {},
            "rows": rows(form_name, proposals, decisions),
        },
        indent=2,
        ensure_ascii=False,
    )
