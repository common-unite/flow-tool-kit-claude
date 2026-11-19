"""Check a parsed form against a project's ``force-app`` metadata.

Answers the questions a consultant would otherwise answer by hand:

* Does every object and field the connector writes still exist?
* Does every form field appear on both the alias export and the rendered form?
* Is any mapping's source label ambiguous - the connector displays sources by
  label, and labels repeat across sections ("City" exists twice on an address
  pair), so a label alone does not identify a field.
* Is anything conditional but never mapped, or mapped but never visible?
* **Did the source adapter actually see what it is reporting on?**

Standard fields are reported as *unverified* rather than missing. A source
retrieval only contains standard fields that were customized, so treating an
absent ``FirstName`` as a broken mapping would be wrong.

The coverage check exists because every other check reads a list, and an empty
list has three incompatible meanings - the platform has no such concept, the
adapter parsed it and found none, or nobody captured it. Only the coverage block
tells them apart, and only one of the three is safe to act on. A check that runs
over a ``not_captured`` aspect and reports "no problems found" is worse than no
check at all: it converts a hole into a clean bill of health.
"""

from __future__ import annotations

import os

# Custom and namespaced fields end in __c; anything else is a standard field
# whose absence from source proves nothing.
_CUSTOM_SUFFIX = "__c"

_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

# Which coverage aspect each check depends on. A check whose aspect was never
# captured is SKIPPED and reported as skipped, never silently passed.
_CHECK_REQUIRES = {
    "objects": "connector",
    "target-fields": "connector",
    "source-labels": "connector",
    "alias-form-agreement": "fields",
    "condition-coverage": "conditions",
}


def load_org_metadata(force_app_path: str) -> dict[str, set[str]]:
    """Map object API name to the field API names present in source."""
    objects_root = os.path.join(force_app_path, "main", "default", "objects")
    if not os.path.isdir(objects_root):
        objects_root = force_app_path

    metadata: dict[str, set[str]] = {}
    if not os.path.isdir(objects_root):
        return metadata

    for object_name in os.listdir(objects_root):
        fields_dir = os.path.join(objects_root, object_name, "fields")
        if not os.path.isdir(fields_dir):
            metadata.setdefault(object_name, set())
            continue
        metadata[object_name] = {
            entry.replace(".field-meta.xml", "")
            for entry in os.listdir(fields_dir)
            if entry.endswith(".field-meta.xml")
        }
    return metadata


def load_org_metadata_from_org(document: dict, org: str | None = None) -> dict[str, set[str]]:
    """The same map as ``load_org_metadata``, read live for the objects the IR targets.

    Uses the Salesforce CLI (``org`` alias, or the default org). An object the
    org does not have is left out, so the object check reports it. Standard
    fields are real here, unlike in retrieved source.
    """
    from . import schema as schema_module

    metadata: dict[str, set[str]] = {}
    objects = sorted({node.get("sobject") for node in document["connector"]["nodes"] if node.get("sobject")})
    for sobject in objects:
        try:
            fields = schema_module.load_object_fields_from_org(sobject, org)
        except schema_module.OrgUnavailable:
            continue
        metadata[sobject] = {name for name in fields if not name.startswith("label:")}
    return metadata


def validate(document: dict, org_metadata: dict[str, set[str]] | None) -> list[dict]:
    """Run every applicable check and return findings sorted by severity.

    A check is applicable only when the IR's coverage says its input was
    actually read. Checks whose input was never captured are reported as skipped
    so the gap survives into the discovery report instead of disappearing.

    ``org_metadata`` of ``None`` means no org and no project metadata was read:
    the object and field checks are then reported as skipped, never passed.
    """
    coverage = (document.get("source") or {}).get("coverage") or {}
    findings: list[dict] = list(_check_coverage(document, coverage))
    if org_metadata is None:
        org_metadata = {}
        if document["connector"]["nodes"]:
            findings.append(_finding(
                "warning", "objects",
                "SKIPPED: no org and no project metadata was read, so the objects and "
                "fields the connector writes are not checked. Connect an org or "
                "retrieve the metadata, then run again."))
        skip_org_checks = True
    else:
        skip_org_checks = False

    for check, runner in (
        ("objects", lambda: _check_objects(document, org_metadata)),
        ("target-fields", lambda: _check_target_fields(document, org_metadata)),
        ("source-labels", lambda: _check_source_labels(document)),
        ("alias-form-agreement", lambda: _check_alias_form_agreement(document)),
        ("condition-coverage", lambda: _check_condition_coverage(document)),
    ):
        if skip_org_checks and check in ("objects", "target-fields"):
            continue
        aspect = _CHECK_REQUIRES[check]
        state = coverage.get(aspect, "unknown")
        if state in ("not_captured", "unknown"):
            findings.append(
                _finding(
                    "warning",
                    check,
                    f"SKIPPED: this check reads {aspect}, which the "
                    f"{document.get('source', {}).get('platform', 'source')} "
                    f"adapter reports as {state}. A clean result here would be "
                    "meaningless, so no result is given.",
                    aspect=aspect,
                    coverage=state,
                )
            )
            continue
        if state == "none_exist":
            continue
        findings.extend(runner())

    findings.sort(key=lambda item: (_SEVERITY_ORDER.get(item["severity"], 9), item["check"]))
    return findings


def _check_coverage(document, coverage) -> list[dict]:
    """Report what this source could and could not see, before anything else.

    This is the first thing a reader of the discovery report should meet: it
    frames every finding that follows as either a fact about the form or a
    limit of how the form was read.
    """
    platform = (document.get("source") or {}).get("platform", "unknown")
    findings = []

    holes = sorted(
        aspect for aspect, state in coverage.items()
        if state in ("not_captured", "unknown")
    )
    if holes:
        findings.append(
            _finding(
                "error",
                "coverage",
                f"The {platform} source did not capture: {', '.join(holes)}. "
                "These are HOLES, not absences - anything downstream treating "
                "them as empty is drawing a conclusion from missing evidence.",
                aspects=holes,
            )
        )

    hand = sorted(
        aspect for aspect, state in coverage.items() if state == "hand_authored"
    )
    if hand:
        findings.append(
            _finding(
                "info",
                "coverage",
                f"Hand-authored (a person, not a parser, is the source of these "
                f"claims): {', '.join(hand)}. Verify against the live form "
                "before building; there is no export to re-check.",
                aspects=hand,
            )
        )

    if coverage.get("connector") == "none_exist":
        findings.append(
            _finding(
                "info",
                "coverage",
                f"{platform} has no Salesforce connector to read, so this IR "
                "carries no target mappings by design. Every mapping decision "
                "moves to new-mapping-flow discovery and becomes a client "
                "question rather than a derived fact.",
            )
        )
    return findings


def _finding(severity: str, check: str, message: str, **extra) -> dict:
    return {"severity": severity, "check": check, "message": message, **extra}


def _check_objects(document, org_metadata) -> list[dict]:
    findings = []
    for node in document["connector"]["nodes"]:
        sobject = node["sobject"]
        if sobject and sobject not in org_metadata:
            findings.append(
                _finding(
                    "error",
                    "object-exists",
                    f"Node {node['order_path']} targets {sobject}, which is not in "
                    "this project's metadata.",
                    order_path=node["order_path"],
                )
            )
    return findings


def _check_target_fields(document, org_metadata) -> list[dict]:
    findings = []
    unverified = []
    for entry in document["connector"]["declared_target_fields"]:
        sobject, _, field = entry.partition(".")
        if not field:
            continue
        if sobject not in org_metadata:
            continue  # Already reported by the object check.
        if field in org_metadata[sobject]:
            continue
        if field.endswith(_CUSTOM_SUFFIX):
            findings.append(
                _finding(
                    "error",
                    "field-exists",
                    f"{entry} is mapped by the connector but does not exist in this "
                    "project's metadata.",
                    field=entry,
                )
            )
        else:
            unverified.append(entry)

    if unverified:
        findings.append(
            _finding(
                "info",
                "field-exists",
                f"{len(unverified)} standard field(s) could not be verified against "
                "source, which only contains customized standard fields: "
                + ", ".join(sorted(unverified)),
            )
        )
    return findings


def _check_source_labels(document) -> list[dict]:
    """The connector shows sources by label, and labels are not unique."""
    label_index: dict[str, list[str]] = {}
    for field in document["fields"]:
        label = (field["label"] or "").strip()
        if label:
            label_index.setdefault(label, []).append(field["id"])

    findings = []
    for node in document["connector"]["nodes"]:
        for mapping in node["mappings"]:
            if mapping["source_kind"] != "form_field":
                continue
            label = (mapping["source_value"] or "").strip()
            if not label:
                findings.append(
                    _finding(
                        "warning",
                        "source-label",
                        f"Node {node['order_path']} maps {mapping['target_field_label']} "
                        "from a form field with a blank label - identify it before "
                        "building the mapping.",
                        order_path=node["order_path"],
                    )
                )
                continue

            matches = label_index.get(label, [])
            if not matches:
                findings.append(
                    _finding(
                        "error",
                        "source-label",
                        f"Node {node['order_path']} maps {mapping['target_field_label']} "
                        f"from \"{label}\", which matches no field on the form.",
                        order_path=node["order_path"],
                    )
                )
            elif len(matches) > 1:
                findings.append(
                    _finding(
                        "warning",
                        "source-label",
                        f"Node {node['order_path']} maps {mapping['target_field_label']} "
                        f"from \"{label}\", which is ambiguous - {len(matches)} fields "
                        f"share that label ({', '.join(matches)}). Confirm which one.",
                        order_path=node["order_path"],
                        candidates=matches,
                    )
                )
    return findings


def _check_alias_form_agreement(document) -> list[dict]:
    """A field on one input but not the other is a signal in either direction."""
    missing = [
        field["id"]
        for field in document["fields"]
        if not field["present_in_rendered_form"]
    ]
    if not missing:
        return []
    return [
        _finding(
            "info",
            "alias-form-agreement",
            f"{len(missing)} alias field(s) have no matching input in the rendered "
            "form - usually calculated or display-only fields: "
            + ", ".join(sorted(missing)[:15])
            + ("…" if len(missing) > 15 else ""),
        )
    ]


def _check_condition_coverage(document) -> list[dict]:
    """Conditional-but-unmapped and unresolved references."""
    findings = []
    for condition in document["conditions"]:
        if condition["unresolved_references"]:
            findings.append(
                _finding(
                    "error",
                    "condition-references",
                    f"Condition on {condition['element_id']} references "
                    f"{', '.join(condition['unresolved_references'])}, which resolve "
                    "to nothing in the alias export.",
                    element_id=condition["element_id"],
                )
            )

    mapped_labels = {
        (mapping["source_value"] or "").strip()
        for node in document["connector"]["nodes"]
        for mapping in node["mappings"]
        if mapping["source_kind"] == "form_field"
    }
    formula_tokens = {
        token["token"]
        for node in document["connector"]["nodes"]
        for mapping in node["mappings"]
        for token in mapping["formula_tokens"]
    }
    for node in document["connector"]["nodes"]:
        for token in node["skip_if_tokens"]:
            formula_tokens.add(token["token"])

    controlling = {
        reference
        for condition in document["conditions"]
        for reference in condition["references"]
    }
    fields_by_id = {field["id"]: field for field in document["fields"]}
    option_parent = {
        option["id"]: field["id"]
        for field in document["fields"]
        for option in field["options"]
    }

    # Several options can share a parent field, so collapse to the field.
    unmapped_controllers: dict[str, str] = {}
    for reference in sorted(controlling):
        field_id = option_parent.get(reference, reference)
        field = fields_by_id.get(field_id)
        if field is None:
            continue
        label = (field["label"] or "").strip()
        if field_id in formula_tokens or reference in formula_tokens:
            continue
        if label and label in mapped_labels:
            continue
        unmapped_controllers[field_id] = f"{field_id} ({label or 'no label'})"

    if unmapped_controllers:
        findings.append(
            _finding(
                "info",
                "condition-coverage",
                f"{len(unmapped_controllers)} field(s) drive conditional visibility but "
                "are never mapped to Salesforce - decide whether the rebuild still "
                "needs them as staging fields: "
                + ", ".join(sorted(unmapped_controllers.values())),
            )
        )
    return findings
