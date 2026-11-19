"""The intermediate representation every source adapter produces.

The IR is the contract. A source adapter's only job is to emit one of these;
everything downstream - the Field Plan, the validator, the client questions, the
workbook, and the `build-form-component` skill that authors the rebuild - reads
the IR and never touches a source file.

Key ordering is stable so two runs over the same inputs diff cleanly: a
regenerated IR that shuffles its keys is useless for spotting what a form
actually changed between exports.

## Coverage is part of the contract, not a nicety

Sources differ in what they can even see. FormAssembly publishes its connector,
so the object graph is *parsed*. A Google Form has no connector and never had
one, so it is *none_exist*. A form somebody screenshotted in a hurry may have
had conditional logic nobody wrote down, which is *not_captured*.

Those three produce an identical-looking IR - an empty list - and exactly one of
them is safe. ``coverage`` is what tells them apart, and ``validate.py`` reads it
to decide whether an empty list is a fact or a hole. An adapter that leaves
coverage unset gets ``unknown``, which is reported, because silence must never
read as completeness.
"""

from __future__ import annotations

import json
import re

from . import conditions as conditions_module

# Bump when a change would make an older ir.json misread rather than merely
# lack a key. Consumers should refuse a major they do not know.
SCHEMA_VERSION = "2.0"

# Tokens inside %%...%% in formulas and skip conditions.
_TOKEN_RE = re.compile(r"%%([A-Za-z0-9_]+)%%")

# What an adapter may claim about each aspect of a form.
#
#   parsed         read from a machine-readable source; trustworthy
#   hand_authored  transcribed by a human from screenshots or a PDF
#   none_exist     the platform has no such concept (a Google Form's connector)
#   not_captured   it exists, nobody captured it - an ACKNOWLEDGED HOLE
#   unknown        the adapter did not say; treated as not_captured, and flagged
COVERAGE_STATES = ("parsed", "hand_authored", "none_exist", "not_captured", "unknown")

# Every aspect an adapter is expected to declare.
COVERAGE_ASPECTS = (
    "structure",       # section/page tree
    "fields",          # the questions themselves
    "options",         # picklist/checkbox choices
    "validation",      # required flags, type constraints
    "conditions",      # conditional visibility
    "connector",       # the Salesforce mapping spec, if the platform has one
    "images",          # banners and inline art
    "custom_scripts",  # injected JavaScript
)

# Aspects with no honest "none_exist": every form has fields and a structure.
_MUST_EXIST = ("structure", "fields")


def new_document(
    platform: str,
    form_id: str = "",
    connector_id: str = "",
    form_name: str = "",
    source_url: str = "",
    coverage: dict | None = None,
) -> dict:
    """Start a contract-valid, empty IR for one form.

    Adapters fill the lists; ``finalize`` orders and checks them. Building the
    skeleton here rather than in each adapter is what keeps a new source from
    quietly omitting a key that downstream indexes without a ``.get``.
    """
    declared = dict(coverage or {})
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "platform": platform,
            "form_id": form_id,
            "form_name": form_name,
            "source_url": source_url,
            "connector_id": connector_id,
            "coverage": {
                aspect: declared.get(aspect, "unknown") for aspect in COVERAGE_ASPECTS
            },
        },
        "form": {
            "form_id": form_id,
            "connector_id": connector_id,
            "section_paths": [],
        },
        "fields": [],
        "structure": [],
        "conditions": [],
        "dependent_picklists": [],
        "connector": {
            "nodes": [],
            "options": {},
            "declared_target_fields": [],
            "branches": [],
        },
        "images": [],
        "custom_scripts": [],
        "findings": [],
    }


def finalize(document: dict, resolver=None) -> dict:
    """Order keys, derive what can be derived, and record contract violations.

    Called by every adapter as its last step. Deriving branch analysis and
    reference resolution HERE rather than per-adapter means a new source gets
    both for free and cannot get them subtly wrong.
    """
    connector = document.setdefault("connector", {})
    connector.setdefault("nodes", [])
    connector["options"] = dict(sorted((connector.get("options") or {}).items()))
    connector["declared_target_fields"] = sorted(
        set(connector.get("declared_target_fields") or [])
    )
    connector["branches"] = analyze_branches(connector["nodes"])

    for entry in document.get("conditions", []):
        tree = entry.get("tree")
        if not tree:
            continue
        entry["references"] = conditions_module.references(tree)
        entry["unresolved_references"] = [
            reference
            for reference in entry["references"]
            if resolver is None or resolver.resolve(reference) is None
        ]
        entry.setdefault("reads_as", conditions_module.describe(tree, resolver))

    document["findings"] = list(document.get("findings", [])) + [
        {"source": "contract", "message": message}
        for message in validate_document(document)
    ]
    return document


def validate_document(document: dict) -> list[str]:
    """Contract violations in an adapter's output. Empty means conforming.

    This checks SHAPE, not truth - that the adapter declared what it saw and
    produced trees downstream can read. Whether the parse was *right* is what
    the source-specific sanity checks in the SKILL are for.
    """
    problems: list[str] = []

    major = str(document.get("schema_version", "")).split(".")[0]
    if major != SCHEMA_VERSION.split(".")[0]:
        problems.append(
            f"schema_version {document.get('schema_version')!r} is not compatible "
            f"with {SCHEMA_VERSION}."
        )

    source = document.get("source") or {}
    if not source.get("platform"):
        problems.append("source.platform is empty; every IR must name its adapter.")

    coverage = source.get("coverage") or {}
    for aspect in COVERAGE_ASPECTS:
        state = coverage.get(aspect, "unknown")
        if state not in COVERAGE_STATES:
            problems.append(f"coverage.{aspect} is {state!r}, not one of {COVERAGE_STATES}.")
        elif state == "unknown":
            problems.append(
                f"coverage.{aspect} was not declared. An undeclared aspect is "
                "treated as NOT CAPTURED, never as complete."
            )
        elif state == "not_captured":
            problems.append(
                f"coverage.{aspect} is not_captured - an acknowledged hole. "
                "Anything downstream reading it is reading an absence, not a fact."
            )
        elif state == "none_exist" and aspect in _MUST_EXIST:
            problems.append(
                f"coverage.{aspect} claims none_exist, but every form has {aspect}."
            )

    # An empty list is only trustworthy when coverage says the source was read.
    for aspect, key in (("conditions", "conditions"), ("fields", "fields")):
        if not document.get(key) and coverage.get(aspect) in ("parsed", "hand_authored"):
            problems.append(
                f"coverage.{aspect} claims {coverage.get(aspect)} but {key} is empty - "
                "either the source genuinely has none, or the adapter missed them."
            )

    for index, entry in enumerate(document.get("conditions", [])):
        tree = entry.get("tree")
        if tree:
            problems.extend(
                conditions_module.validate_tree(tree, f"conditions[{index}].tree")
            )

    return problems


def analyze_branches(nodes: list[dict]) -> list[dict]:
    """Report mirrored branches so the rebuild plans one pipeline, not two.

    A connector that carries a prefilled path and a not-prefilled path
    duplicates most of its mappings across both. In FlowToolKit the difference
    is source injection, so the duplicate work collapses.

    Operates on IR nodes rather than any source's model, so every
    connector-bearing platform gets this analysis without reimplementing it.
    """
    branches: dict[str, list[dict]] = {}
    for node in nodes:
        root = (node.get("order_path") or "").split(".")[0]
        branches.setdefault(root, []).append(node)

    signatures = {
        root: {
            (node.get("sobject"), mapping.get("target_field_label"))
            for node in grouped
            for mapping in node.get("mappings", [])
        }
        for root, grouped in branches.items()
    }

    analysis = []
    roots = sorted(signatures)
    for index, root in enumerate(roots):
        entry = {
            "root": root,
            "node_paths": [node.get("order_path") for node in branches[root]],
            "mapping_count": len(signatures[root]),
            "overlaps": [],
        }
        for other in roots[index + 1 :]:
            shared = signatures[root] & signatures[other]
            if not shared:
                continue
            smaller = min(len(signatures[root]), len(signatures[other])) or 1
            entry["overlaps"].append(
                {
                    "with_root": other,
                    "shared_mappings": len(shared),
                    "overlap_ratio": round(len(shared) / smaller, 3),
                }
            )
        analysis.append(entry)
    return analysis


def resolve_tokens(text: str | None, resolver) -> list[dict]:
    """Resolve %%token%% references so a formula reads in business language."""
    if not text:
        return []
    resolved = []
    for token in dict.fromkeys(_TOKEN_RE.findall(text)):
        found = resolver.resolve(token) if resolver else None
        resolved.append(
            {
                "token": token,
                "kind": found["kind"] if found else "unknown",
                "reads_as": resolver.describe(token) if found else None,
            }
        )
    return resolved


_ID_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def derive_field_id(label: str, used: set[str]) -> str:
    """A stable, readable field id from a question's label.

    Shared because any source whose questions are identified by their text
    rather than by a platform id needs exactly this, and two implementations
    would drift into producing different ids for the same form.
    """
    stem = _ID_CLEAN_RE.sub("_", (label or "").lower()).strip("_")[:48] or "field"
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def to_json(document: dict) -> str:
    """Serialize the IR with stable ordering and readable indentation."""
    return json.dumps(document, indent=2, ensure_ascii=False)


def load(path: str) -> dict:
    """Read an ir.json from disk."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
