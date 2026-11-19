"""The data dictionary: FieldDefinition and EntityParticle per object, joined
with every Flow Tool Kit reference, then a verdict and a documentation check
per custom field.

The verdict answers one question, whether Flow Tool Kit references the field:
Active (referenced or mapped in a Form Template, page section, Form Component,
mapping or Flow Tool Kit flow, with the places listed) or Unreferenced (no
reference in any of them). No record is ever counted or read, and Apex,
reports, page layouts and other general metadata are left to Setup's Where is
this used?.

The governance columns are Salesforce's own (Description, Security
Classification, Compliance Group, Business Status), so the dictionary reads
the same as Setup.
"""

from __future__ import annotations

import re

from . import TEMPLATE_OBJECT
from . import flows, sweep, walk
from .orgreads import ocutil
from .queries import options_of

val, records, ran, failed = ocutil.val, ocutil.records, ocutil.ran, ocutil.failed

# Surface -> rollup bucket.
BUCKETS = {
    "Section Form": "sections", "Header Form": "sections", "Footer Form": "sections", "Table Form": "sections",
    "Page Rule": "rules", "Section Rule": "rules", "Payment Rule": "rules",
    walk.MAPPING_SURFACE: "mappings", "Source Mapping": "mappings", "Source Config": "mappings",
    "Nullable": "mappings",
    "Prefill Values": "prefill", "Prefill Template": "prefill",
    "URL Parameter": "url",
    "Merge Token": "merge", "Email Template": "merge",
    "Flow Screen Form": "flows", "Flow Element": "flows", "Flow Formula": "flows", "Flow Action": "flows",
}
BUCKET_ORDER = ["sections", "rules", "mappings", "prefill", "url", "merge", "flows"]

ACTIVE = "Active"
UNREFERENCED = "Unreferenced"
VERDICTS = [ACTIVE, UNREFERENCED]
_ISSUE_NUMBER = re.compile(r"(?<![\w&])#\d+\b")
HELP_LIMIT = 255
EM_DASH = chr(0x2014)


def is_managed(name, own_namespace=""):
    """``ns__Name__c`` (three ``__`` parts) is a field an installed package owns:
    an admin cannot delete it or rewrite its description. A field with the org's
    own namespace (a packaging or namespaced development org) is the org's."""
    parts = name.split("__")
    return len(parts) >= 3 and parts[0] != own_namespace


def org_namespace(raw):
    return val((records(raw, "org") or [{}])[0], "NamespacePrefix") or ""


# ---- references ----------------------------------------------------------------------------------------------------

_ENTITY_ID = re.compile(r"^01I[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$")


def entity_names(raw):
    """15-character entity Id -> object API name, from the ``entities`` read."""
    return {(val(r, "DurableId") or "")[:15]: val(r, "QualifiedApiName") for r in records(raw, "entities")}


def references_of(raw):
    """(template references, flow references, coverage). Some stored configs
    name a custom object by its entity Id (01I...); those are given the
    object's name once the ``entities`` read has run."""
    options = options_of(raw)
    references, coverage, resolve = sweep.sweep(raw)
    flow_references = flows.scan_all(raw, options, resolve, coverage)
    names_by_id = entity_names(raw)
    for ref in references + flow_references:
        if _ENTITY_ID.match(ref["object"]) and ref["object"][:15] in names_by_id:
            ref["object"] = names_by_id[ref["object"][:15]]
    return references, flow_references, coverage


def unresolved_entities(raw):
    analysis = analyze(raw)
    return sorted({r["object"][:15] for r in analysis["references"] + analysis["flow_references"]
                   if _ENTITY_ID.match(r["object"])})


def _resolvable(ref):
    obj = ref["object"]
    return ref["field"] and not ref["is_path"] and obj and "." not in obj and "__r" not in obj


def referenced_objects(raw):
    analysis = analyze(raw)
    return {r["object"] for r in analysis["references"] + analysis["flow_references"] if _resolvable(r)}


def rollup(references):
    """(object, field) -> bucket counts, for references that name one field."""
    counts = {}
    for ref in references:
        if not _resolvable(ref):
            continue
        buckets = counts.setdefault((ref["object"], ref["field"]), {bucket: 0 for bucket in BUCKET_ORDER})
        buckets[BUCKETS[ref["surface"]]] += 1
    return counts


def surfaces_of(references):
    """(object, field) -> the surface names that use it, in the order first met
    (``Section Form``, ``Form Template Mapping``, ``Flow Action``): the
    dictionary names each surface, since a bucket such as Mappings joins several."""
    found = {}
    for ref in references:
        if _resolvable(ref):
            found.setdefault((ref["object"], ref["field"]), {})[ref["surface"]] = True
    return {key: list(names) for key, names in found.items()}


def used_in(references, flow_references):
    """(object, field) -> the template and flow names that use it, and its mapped partners."""
    places, partners = {}, {}
    for ref in references:
        if not _resolvable(ref):
            continue
        key = (ref["object"], ref["field"])
        name = ref["template_name"] or (f"{ref['component_label']} (form)" if ref["component_label"] else "")
        if name:
            places.setdefault(key, []).append(name)
        if ref["surface"] == walk.MAPPING_SURFACE and ref["snippet"].startswith(("mapped from ", "mapped to ")):
            partner = ref["snippet"].split(" ", 2)[2]
            partners.setdefault(key, []).append(f"{partner} ({ref['component_label']})" if ref["component_label"]
                                                else partner)
    for ref in flow_references:
        if _resolvable(ref):
            places.setdefault((ref["object"], ref["field"]), []).append(f"{ref['flow_label']} (flow)")
    unique = lambda items: list(dict.fromkeys(items))  # noqa: E731
    return ({k: unique(v) for k, v in places.items()}, {k: unique(v) for k, v in partners.items()})


# ---- field definitions ---------------------------------------------------------------------------------------------

def field_table(raw, sobject):
    """Field -> attributes, or None when the object's fields could not be read."""
    if not ran(raw, "fields:" + sobject) or failed(raw, "fields:" + sobject):
        return None
    own = org_namespace(raw)
    definitions = {val(r, "QualifiedApiName"): r for r in records(raw, "fields:" + sobject)}
    particles = {val(r, "QualifiedApiName"): r for r in records(raw, "particles:" + sobject)}
    fields = {}
    # EntityParticle also lists the parts of compound fields (BillingCity,
    # FirstName), which FieldDefinition leaves out
    for name in set(definitions) | set(particles):
        if not name:
            continue
        definition, particle = definitions.get(name) or {}, particles.get(name) or {}
        fields[name] = {
            "label": val(particle, "Label") or val(definition, "Label") or "",
            "type": val(definition, "DataType") or val(particle, "DataType") or "",
            "description": val(definition, "Description") or "",
            "help_text": val(particle, "InlineHelpText") or "",
            "security": val(definition, "SecurityClassification") or "",
            "compliance": val(definition, "ComplianceGroup") or "",
            "status": val(definition, "BusinessStatus") or "",
            "is_custom": name.endswith("__c"),
            "is_managed": is_managed(name, own),
            # Object.00N... for custom fields, Object.Name for standard: either
            # tail is a valid Object Manager FieldsAndRelationships path
            "setup_token": (val(definition, "DurableId") or "").split(".", 1)[-1] or name,
        }
    return fields


# ---- verdicts and documentation ------------------------------------------------------------------------------------

def verdict(reference_count):
    """Active when a Form Template, page section, Form Component, mapping or Flow
    Tool Kit flow references the field; Unreferenced otherwise. Never based on
    records, and never on general metadata."""
    return ACTIVE if reference_count else UNREFERENCED


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s]


def documentation_gaps(sobject, field, meta):
    """What the plugin's documentation standard asks of this field and it lacks.
    Only fields the org owns: a package documents its own fields."""
    if not meta.get("is_custom") or meta.get("is_managed"):
        return []
    gaps = []
    description, help_text = meta.get("description") or "", meta.get("help_text") or ""
    if not description.strip():
        gaps.append("no description")
    if sobject == TEMPLATE_OBJECT:
        if not help_text.strip():
            gaps.append("no help text (a Form Template field needs two sentences)")
        elif len(_sentences(help_text)) < 2:
            gaps.append("help text is one sentence (a Form Template field needs two)")
    if len(help_text) > HELP_LIMIT:
        gaps.append(f"help text over {HELP_LIMIT} characters")
    for label, text in (("description", description), ("help text", help_text)):
        if _ISSUE_NUMBER.search(text):
            gaps.append(f"{label} cites an issue number")
        if EM_DASH in text:
            gaps.append(f"{label} has an em-dash")
    return gaps


# ---- the whole analysis --------------------------------------------------------------------------------------------

_CACHE = {}


def analyze(raw):
    """Everything the report needs, from a finished (or partial) raw.json.
    Cached per raw.json revision: ``queries.store`` bumps ``_rev``."""
    key = (id(raw), raw.get("_rev"))
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = _analyze(raw)
    return _CACHE[key]


def _analyze(raw):
    options = options_of(raw)
    references, flow_references, coverage = references_of(raw)
    counts = rollup(references + flow_references)
    places, partners = used_in(references, flow_references)
    surfaces = surfaces_of(references + flow_references)
    audit_objects = list(options["objects"])
    objects = sorted(set(audit_objects) | {obj for obj, _ in counts})

    tables = {}
    for sobject in objects:
        table = field_table(raw, sobject)
        if table is None:
            if sobject in audit_objects or ran(raw, "fields:" + sobject):
                coverage.append({"store": f"Fields of {sobject}", "status": "missing",
                                 "detail": "the field definitions could not be read"})
            table = {}
        tables[sobject] = table

    rows = []
    for sobject in objects:
        table = tables[sobject]
        names = set(table) | {field for obj, field in counts if obj == sobject}
        for field in sorted(names):
            meta = table.get(field)
            buckets = counts.get((sobject, field), {b: 0 for b in BUCKET_ORDER})
            total = sum(buckets.values())
            is_audit = sobject in audit_objects
            if meta is None:  # referenced but not a field the org knows: a typo or a deleted field
                meta = {"label": "", "type": "", "description": "", "help_text": "", "security": "",
                        "compliance": "", "status": "", "is_custom": field.endswith("__c"),
                        "is_managed": is_managed(field, org_namespace(raw)), "setup_token": "", "missing": True}
                if not table:
                    meta["missing"] = False  # the object's fields were not read; nothing to say
            if total == 0 and not (is_audit and meta.get("is_custom")):
                continue  # other objects' fields earn a row only by being used
            row = {
                "object": sobject, "field": field, "meta": meta, "buckets": buckets, "total_refs": total,
                "surfaces": surfaces.get((sobject, field), []),
                "used_in": places.get((sobject, field), []),
                "mapped_with": partners.get((sobject, field), []),
                "verdict": "",
                "documentation": documentation_gaps(sobject, field, meta),
            }
            if meta.get("missing"):
                row["documentation"] = ["not a field on this object (renamed, deleted or misspelled)"]
            elif meta.get("is_custom"):
                row["verdict"] = verdict(total)
            rows.append(row)

    return {"options": options, "references": references, "flow_references": flow_references,
            "coverage": coverage, "rows": rows, "audit_objects": audit_objects}


def focus(analysis, template):
    """The audit narrowed to one Form Template (by Name or Id): the fields it
    uses, where it uses them, and the flows that touch those same fields.
    Verdicts stay org-wide, because a field another template uses is not unused.
    None when no template matches."""
    wanted = (template or "").strip().lower()
    refs = [r for r in analysis["references"]
            if wanted and (r["template_name"].lower() == wanted or r["template_id"][:15].lower() == wanted[:15])]
    if not refs:
        return None
    keys = {(r["object"], r["field"]) for r in refs}
    return dict(analysis, references=refs,
                flow_references=[r for r in analysis["flow_references"] if (r["object"], r["field"]) in keys],
                rows=[row for row in analysis["rows"] if (row["object"], row["field"]) in keys],
                focus=refs[0]["template_name"])

