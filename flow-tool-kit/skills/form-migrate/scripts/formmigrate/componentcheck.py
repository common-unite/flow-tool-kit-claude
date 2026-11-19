"""Check that every field a built form component references actually exists.

This closes the one failure in the migration relay that is completely silent.
The FlowToolKit render engine treats an unknown ``fieldName__c`` as a skip with a
console warning, never a fatal error, so a component built against a staging
field that was never deployed renders as **a working form quietly missing that
question**. Nothing in the deploy, the cache reset, or the preview says so; you
find out when a submission arrives with a blank you cannot explain.

It is checkable, so it should be checked. A reference resolves when it is:

* a field present in ``force-app`` on the component's object, or
* an approved proposal in the Field Plan (deployed later in the same release), or
* a standard field every object has.

The reverse direction matters too. A Field Plan entry that NO component
references is a field about to be created for nothing, which is how a staging
object accretes columns nobody can account for a year later.

Reads a hand-authored component JSON, or a CMT ``.md-meta.xml`` exported by
``pull-form``. Both end up as the same reference list.
"""

from __future__ import annotations

import json
import os
import re

from . import schema as schema_module

# The renderer rewrites `*__` to the package namespace, and does it blindly, so
# a reference may arrive in either form.
_NAMESPACE = "FlowToolKit__"
_STAR = "*__"

# Standard fields every object carries; never defined in force-app.
_STANDARD_FIELDS = {
    "Id", "Name", "OwnerId", "CreatedById", "CreatedDate", "LastModifiedById",
    "LastModifiedDate", "RecordTypeId", "CurrencyIsoCode",
}

# Pull one field's config out of an exported CMT record file.
_CMT_VALUE_RE = re.compile(
    r"<field>(?P<field>[^<]+)</field>\s*<value[^>]*>(?P<value>.*?)</value>",
    re.S,
)

_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _finding(severity: str, check: str, message: str, **extra) -> dict:
    return {"severity": severity, "check": check, "message": message, **extra}


def _normalize(api_name: str) -> str:
    """Reduce a reference to a comparable API name."""
    name = (api_name or "").strip()
    if name.startswith(_STAR):
        name = _NAMESPACE + name[len(_STAR) :]
    return name


def _local(api_name: str) -> str:
    """API name without the package namespace, for cross-namespace comparison."""
    return _normalize(api_name).replace(_NAMESPACE, "")


def collect_references(config: dict) -> list[dict]:
    """Every field reference in a component config, with where it came from.

    Walks the whole structure rather than the documented shape on purpose:
    references live on fields, and again inside conditional-logic conditions,
    and a config that nests differently than expected must not silently
    contribute zero references.
    """
    found: list[dict] = []

    def walk(node, path: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if isinstance(value, str) and key.endswith("fieldName__c"):
                found.append(
                    {
                        "field": value,
                        "path": f"{path}.{key}" if path else key,
                        "context": "condition" if "conditions" in path else "field",
                        "component": node.get("QualifiedApiName", ""),
                    }
                )
            else:
                walk(value, f"{path}.{key}" if path else key)

    walk(config, "")
    return found


def load_config(path: str) -> dict:
    """Read a component config from JSON, or from an exported CMT record file."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        raw = handle.read()

    if path.endswith(".json"):
        return json.loads(raw)

    # A CMT record file stores the real config in a config__c custom field, and
    # the discrete columns are only a filterable mirror. Reading the columns and
    # ignoring config__c would miss every reference.
    merged: dict = {}
    for match in _CMT_VALUE_RE.finditer(raw):
        field = match.group("field").strip()
        value = match.group("value").strip()
        if field.endswith("config__c"):
            try:
                merged.setdefault("configs", []).append(json.loads(value))
            except json.JSONDecodeError:
                merged.setdefault("unparsed_config", []).append(value[:200])
        elif field.endswith("fieldName__c"):
            merged.setdefault("fields", []).append({field: value})
    return merged


def check(
    config: dict,
    force_app: str,
    object_name: str = "FlowToolKit__Form_Submission__c",
    proposals=None,
) -> list[dict]:
    """Report every unresolvable reference, and every unused planned field."""
    references = collect_references(config)
    findings: list[dict] = []

    if not references:
        findings.append(
            _finding(
                "warning",
                "no-references",
                "No fieldName__c references were found in this config. Either it "
                "is display-only, or it was read in a shape this check does not "
                "recognise -- confirm before treating a clean result as a pass.",
            )
        )

    existing = schema_module.load_object_fields(force_app, object_name)
    if not existing:
        findings.append(
            _finding(
                "warning",
                "no-metadata",
                f"No fields found for {object_name} under {force_app}. Every "
                "reference below is unverifiable, not verified.",
                object_name=object_name,
            )
        )

    existing_local = {_local(name) for name in existing if not name.startswith("label:")}
    planned = {
        _local(proposal.staging_field): proposal
        for proposal in (proposals or [])
        if getattr(proposal, "staging_field", None)
        and str(proposal.disposition).startswith("create")
    }

    referenced_locals: set[str] = set()
    for reference in references:
        local = _local(reference["field"])
        referenced_locals.add(local)

        if local in _STANDARD_FIELDS or local in existing_local:
            continue
        if local in planned:
            findings.append(
                _finding(
                    "info",
                    "field-planned",
                    f"{reference['field']} does not exist yet but is an approved "
                    "Field Plan proposal. It MUST be deployed before this "
                    "component is, or the question renders as nothing.",
                    field=reference["field"],
                    path=reference["path"],
                )
            )
            continue

        findings.append(
            _finding(
                "error",
                "field-missing",
                f"{reference['field']} is referenced by the component but exists "
                f"neither in {object_name} nor in the Field Plan. The renderer "
                "SKIPS unknown fields with only a console warning, so this "
                "question will silently not appear.",
                field=reference["field"],
                path=reference["path"],
                context=reference["context"],
            )
        )

    for local, proposal in sorted(planned.items()):
        if local in referenced_locals:
            continue
        findings.append(
            _finding(
                "warning",
                "field-unused",
                f"{proposal.staging_field} is planned for creation but no "
                f"component references it. Either a question was dropped during "
                "the build, or this field is not needed.",
                field=proposal.staging_field,
                label=proposal.label,
            )
        )

    findings.sort(key=lambda item: (_SEVERITY_ORDER.get(item["severity"], 9), item["check"]))
    return findings


def check_file(
    config_path: str,
    force_app: str,
    object_name: str = "FlowToolKit__Form_Submission__c",
    proposals=None,
) -> list[dict]:
    """Load a config from disk and check it."""
    return check(load_config(config_path), force_app, object_name, proposals)


def check_directory(
    directory: str,
    force_app: str,
    object_name: str = "FlowToolKit__Form_Submission__c",
    proposals=None,
) -> dict[str, list[dict]]:
    """Check every component config in a directory, keyed by file name.

    Proposals are checked against the UNION of every config, so a field used by
    one component in a multi-component form is not reported unused by the rest.
    """
    paths = [
        os.path.join(directory, entry)
        for entry in sorted(os.listdir(directory))
        if entry.endswith((".json", ".md-meta.xml"))
    ]
    merged_references: set[str] = set()
    results: dict[str, list[dict]] = {}

    for path in paths:
        config = load_config(path)
        merged_references.update(
            _local(reference["field"]) for reference in collect_references(config)
        )
        # Proposals MUST be passed through, or a not-yet-deployed planned field
        # reports as a hard error in every file. Only the unused check is
        # per-directory: a field used by one component is not unused just
        # because the other nine do not reference it.
        results[os.path.basename(path)] = [
            finding
            for finding in check(config, force_app, object_name, proposals)
            if finding["check"] != "field-unused"
        ]

    for proposal in proposals or []:
        name = getattr(proposal, "staging_field", None)
        if not name or not str(proposal.disposition).startswith("create"):
            continue
        if _local(name) in merged_references:
            continue
        results.setdefault("_unused", []).append(
            _finding(
                "warning",
                "field-unused",
                f"{name} is planned for creation but NO component in {directory} "
                "references it. Either a question was dropped during the build, "
                "or this field is not needed.",
                field=name,
                label=proposal.label,
            )
        )
    return results
