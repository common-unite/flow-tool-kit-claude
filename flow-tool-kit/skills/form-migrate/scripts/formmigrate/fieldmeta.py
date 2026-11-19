"""Emit Salesforce field metadata for the new staging fields a Field Plan needs.

The migrator decides each new field's API name, type, and (for picklists) value
set. This turns those decisions into deployable ``.field-meta.xml`` so the
form that renders them, and the flows that convert them, have somewhere to write.

Subscriber-side only: these are custom fields added to the packaged
``FlowToolKit__Form_Submission__c`` object, so they carry no namespace in a
subscriber org.

Every field ships with its description, written for the admin who audits it in
Setup (``_shared/standards/documentation.md``): what the question captures and,
when it maps somewhere, where the answer is copied. Form Submission fields are
respondent-facing, so no inline help text is written; the label is the question
as the respondent reads it when it fits in 40 characters.
"""

from __future__ import annotations

import html
import os

# New staging picklists are unrestricted so the org's admins can add values
# without a deploy. (Packaged picklists are restricted, but a subscriber org can
# still add values to them; see decisions.extend_packaged.)
_PICKLIST_RESTRICTED = False

# Salesforce text default; long free text uses a LongTextArea instead.
_TEXT_LENGTH = 255
_LONGTEXT_LENGTH = 32768
_LONGTEXT_LINES = 6


def _picklist_values(values: list[str]) -> str:
    rows = "\n".join(
        f"""            <value>
                <fullName>{html.escape(v, quote=True)}</fullName>
                <default>false</default>
                <label>{html.escape(v, quote=True)}</label>
            </value>"""
        for v in values
    )
    return f"""    <valueSet>
        <restricted>{str(_PICKLIST_RESTRICTED).lower()}</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
{rows}
        </valueSetDefinition>
    </valueSet>"""


def _body_for_type(field_type: str, values: list[str]) -> tuple[str, str]:
    """Return (salesforce type element, extra body) for a proposed type."""
    kind = (field_type or "Text").split()[0]

    if kind in ("Picklist", "MultiselectPicklist"):
        extra = _picklist_values(values)
        if kind == "MultiselectPicklist":
            extra += "\n    <visibleLines>4</visibleLines>"
        return kind, extra
    if kind == "Checkbox":
        return "Checkbox", "    <defaultValue>false</defaultValue>"
    if kind == "Number":
        return "Number", "    <precision>18</precision>\n    <scale>0</scale>"
    if kind == "Currency":
        return "Currency", "    <precision>18</precision>\n    <scale>2</scale>"
    if kind == "Date":
        return "Date", ""
    if kind in ("Email",):
        return "Email", ""
    if kind == "Phone":
        return "Phone", ""
    if kind == "Address":
        # A compound Address field is a single field of type Address.
        return "Address", ""
    if kind == "TextArea":
        return "TextArea", ""
    if field_type.startswith("Formula"):
        # Formula body is deliberately left as a TODO - the expression depends
        # on the target org's rollup fields, which a human verifies first.
        return_type = "Checkbox" if "Checkbox" in field_type else "Text"
        return (
            "Text" if return_type == "Text" else "Checkbox",
            f"    <!-- TODO formula: verify the source field on the Account "
            f"lookup exists, then author the formula. Placeholder as {return_type}. -->",
        )
    if kind == "LongTextArea":
        return "LongTextArea", (
            f"    <length>{_LONGTEXT_LENGTH}</length>\n"
            f"    <visibleLines>{_LONGTEXT_LINES}</visibleLines>"
        )
    return "Text", f"    <length>{_TEXT_LENGTH}</length>"


def render_field(api_name: str, label: str, field_type: str,
                 values: list[str] | None = None, description: str = "") -> str:
    """Render one ``.field-meta.xml``."""
    local = api_name.replace("FlowToolKit__", "").replace("__c", "")
    sf_type, extra = _body_for_type(field_type, values or [])
    # The question as the respondent reads it, when it fits. A longer question
    # would be clipped mid-phrase ("What type of program are you applyin"), so
    # the label then comes from the field's own name ("Program Type").
    label = (label or "").strip()
    if not label or len(label) > 40:
        label = local.replace("_", " ")[:40]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">',
        f"    <fullName>{local}__c</fullName>",
        f"    <label>{html.escape(label[:40], quote=False)}</label>",
        f"    <type>{sf_type}</type>",
    ]
    if description:
        lines.insert(4, f"    <description>{html.escape(description, quote=False)}</description>")
    if sf_type not in ("Address",):
        lines.append("    <required>false</required>")
    if extra:
        lines.append(extra)
    lines.append("</CustomField>")
    return "\n".join(lines) + "\n"


def describe(proposal) -> str:
    """The field description, summary first: what it captures, then where it goes."""
    question = (proposal.label or proposal.staging_label or "").strip()
    if question:
        text = f"Answer to the form question: {question}" + ("" if question[-1] in ".?!:" else ".")
    else:
        text = "Answer to an unlabelled form question."
    if proposal.targets:
        targets = ", ".join(t.replace(".", "'s ", 1) for t in sorted(set(proposal.targets)))
        text += f" Copied to the {targets} when the submission converts."
    if proposal.proposed_type in ("Picklist", "MultiselectPicklist") and proposal.proposed_values:
        text += " Values match the form's choices."
    return text[:1000]


def emit(proposals, out_dir: str, *, dispositions=("create_form_specific",
         "create_org_canonical", "create_formula"), skip_types=("Address",)) -> list[str]:
    """Write a field file per creatable proposal; return the paths written.

    Compound Address fields are skipped by default: one Address field replaces a
    block, and it is emitted once elsewhere, not once per part.
    """
    os.makedirs(out_dir, exist_ok=True)
    written = []
    claimed: dict[str, object] = {}
    collisions: list[str] = []

    for proposal in proposals:
        if proposal.disposition not in dispositions:
            continue
        name = proposal.staging_field
        if not name:
            continue
        if proposal.proposed_type in skip_types:
            continue

        owner = claimed.get(name)
        if owner is not None:
            # Two proposals may legitimately share a field only when they are
            # parts of one thing (an address block). Two DIFFERENT questions
            # landing on one name is a collision, and skipping the second is the
            # most expensive silent failure in this package: two questions merge
            # into one field, and the file count quietly disagrees with the plan.
            if owner.label != proposal.label:
                collisions.append(
                    f"{name} is claimed by both '{owner.label}' "
                    f"({owner.field_id}) and '{proposal.label}' "
                    f"({proposal.field_id})"
                )
            continue

        claimed[name] = proposal
        local = name.replace("FlowToolKit__", "").replace("__c", "")
        path = os.path.join(out_dir, f"{local}__c.field-meta.xml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                render_field(
                    name, proposal.label or proposal.staging_label or "", proposal.proposed_type or "Text",
                    proposal.proposed_values,
                    description=describe(proposal),
                )
            )
        written.append(path)

    if collisions:
        raise ValueError(
            "Field name collisions -- distinct questions were assigned the same "
            "API name, so writing them would merge two questions into one field:"
            + "".join(f"\n  - {entry}" for entry in collisions)
            + "\n\nRun fieldplan.deduplicate_names(proposals, schema) before emit."
        )
    return written