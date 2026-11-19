#!/usr/bin/env python3
"""Merge repeated sections across an org's Form Templates into one shared component. Optional: run only when asked.

Every new section starts as JSON on the section. When the same questions turn up on several templates later, this
script groups them (org-catalog's repeated-sections finding, never a second measure), shows what each group's members
share and where they differ, and, for the groups the person says yes to, builds one shared component and repoints each
member section at it. Each section keeps its own title, header and rules; a form's questions never change silently.

Commands, in the order a consolidation runs them:
    queries   --catalog catalog.json | --conversion consolidation.json --for roundtrip|cleanup
              the SOQL each step reads (for a Salesforce connector in chat)
    snapshot  --catalog catalog.json --target-org <org-alias> | --rows rows.json  --out snapshot.json
              read the member sections and one-off record components
    plan      --catalog catalog.json --snapshot snapshot.json [answers] --out consolidation.json   the dry run
              answers: --merge g1|all  --add g1:<field>  --separate <section Id>  --join <section Id>
                       --base g1=<section Id>  --name g1=<Name>  --shape g1=record|metadata  --describe g1=<text>
    confirm   consolidation.json        record that the person approved this exact dry run
    build     consolidation.json [--out <customMetadata folder>] [--plan plan.json ...]
              writes components/<Name>.json, create.apex (record) or the metadata files (metadata), repoint.apex
              and rollback.apex
    roundtrip consolidation.json --target-org <org-alias> | --rows rows.json   every template still asks the same
              questions, except the changes the person approved
    cleanup   consolidation.json --target-org <org-alias> | --rows rows.json   the separate, later step: remove the old
              JSON kept on repointed sections, and list one-off record components nothing uses any more

Nothing here changes the org by itself: creating, repointing and cleaning up are Apex files the person approves.
Python 3 standard library only.

Exit codes: 0 done; 1 an error; 2 the dry run found a problem; 3 not confirmed, changed after it was confirmed, or the
round trip has not passed; 4 files in the project would change (rerun with --overwrite once the person agrees);
5 the round trip found a difference.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import html
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
from xml.sax.saxutils import escape

NS = "FlowToolKit__"
STAR = "*__"
HERE = pathlib.Path(__file__).resolve().parent
PROMOTE_AT = 2  # templates: a section on two or more templates is worth one shared component
MAX_AGE_HOURS = 24
SHAPES = ("record", "metadata")
NON_FORM_TYPES = {"Flow", "Lightning Web Component", "LightningWebComponent", "Display Text", "DisplayText"}
SECTION_NAME_COLUMNS = ["FormQualifiedApiName__c", "Alternate_FormQualifiedApiName__c", "Bulk_FormQualifiedApiName__c",
                        "Edit_FormQualifiedApiName__c"]
SECTION_COLUMNS = ["Id", "LastModifiedDate", f"{NS}Title__c", f"{NS}Header_Title__c", f"{NS}Component_Type__c",
                   f"{NS}FormConfigJSON__c", f"{NS}FormQualifiedApiName__c", f"{NS}Form_Component__c"]
COMPONENT_COLUMNS = ["Id", "LastModifiedDate", f"{NS}QualifiedApiName__c", f"{NS}Label__c", f"{NS}ObjectApiName__c",
                     f"{NS}FormConfigJSON__c", f"{NS}Version__c", f"{NS}Active__c", "RecordType.DeveloperName"]
METADATA_TYPES = ("Form", "Form_Section", "Form_Field", "Form_Conditional_Logic", "Form_Conditional_Logic_Condition")
RECORD_REF = re.compile(r"^(\w+)_v0$")
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$")
DROPPED = {"Id", "_Id", "attributes", "Version__c", "VersionId__c", "SystemModstamp__c", "Form_Managers__c"}


class ConsolidateError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


# ---- small helpers -----------------------------------------------------------------------------------------------------

def local(key):
    """A JSON key without the package prefix or its *__ placeholder."""
    key = str(key)
    for prefix in (STAR, NS):
        if key.startswith(prefix):
            return key[len(prefix):]
    return key


def get(node, name, default=None):
    if not isinstance(node, dict):
        return default
    for key, value in node.items():
        if local(key) == name:
            return value
    return default


def bare(name):
    return local(str(name or "").replace(STAR, NS))


def col(row, path, default=None):
    """Read 'A.B' from a query row, nested or flattened, with or without the package prefix on each part."""
    if not isinstance(row, dict):
        return default
    for key, value in row.items():
        if bare(key).lower() == bare(path).lower() or key.lower() == path.lower():
            return value
    head, _, rest = path.partition(".")
    if rest:
        for key, value in row.items():
            if bare(key).lower() == bare(head).lower() and isinstance(value, dict):
                return col(value, rest, default)
    return default


def parse_json(text):
    if isinstance(text, (dict, list)):
        return text
    if not text or not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def plain(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))
    return re.sub(r"\s+", " ", text).strip()


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp():
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConsolidateError(f"cannot read {path}: {error}")


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def soql_list(values):
    return ", ".join("'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'" for v in sorted(set(values)))


def apex_str(value):
    """An Apex string expression for any text, split so no single literal is very long."""
    if value is None:
        return "null"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n")
    parts = [text[i:i + 2000] for i in range(0, len(text), 2000)] or [""]
    return "\n    + ".join(f"'{p}'" for p in parts)


def catalog_age_hours(catalog, now=None):
    taken = catalog.get("taken_at")
    if not taken:
        return None
    when = datetime.datetime.fromisoformat(taken.replace("Z", "+00:00"))
    return ((now or now_utc()) - when).total_seconds() / 3600


def shared_name(title, taken):
    """A purpose name from the section's title (In case of emergency -> In_Case_Of_Emergency), not taken in the org."""
    words = re.findall(r"[A-Za-z0-9]+", plain(title))
    name = "_".join(w[:1].upper() + w[1:] for w in words) or "Shared_Section"
    if name[0].isdigit():
        name = "S_" + name
    name = name[:36].rstrip("_")
    candidate, n = name, 2
    while candidate.lower() in taken:
        candidate = f"{name[:33]}_{n}"
        n += 1
    return candidate


# ---- reading a page section the way the package does -------------------------------------------------------------------

def section_source(row):
    """What a page section draws: {kind: json|record|metadata|none, design, name, object, wrapper}."""
    if (col(row, "Component_Type__c") or "") in NON_FORM_TYPES:
        return {"kind": "none"}
    raw = (col(row, "FormConfigJSON__c") or "").strip()
    column = col(row, "FormQualifiedApiName__c")
    wrapper = parse_json(raw) if raw else None
    wrapper = wrapper if isinstance(wrapper, dict) else None
    mode = (wrapper or {}).get("formSelectionMode")
    obj = (wrapper or {}).get("object")
    if raw and mode == "component":
        name = wrapper.get("formQualifiedApiName") or column
    elif raw:
        inner = wrapper.get("formJsonConfig") if wrapper and "formSelectionMode" in wrapper else raw
        design = parse_json(inner)
        return {"kind": "json", "design": design if isinstance(design, dict) else None, "object": obj, "wrapper": wrapper}
    else:
        name = column
    if not name:
        return {"kind": "none"}
    return {"kind": "record" if RECORD_REF.match(name) else "metadata", "name": name, "object": obj, "wrapper": wrapper}


def latest_record_design(rows, name):
    """The newest active Record Component version of a record component, as its stored JSON root."""
    name = RECORD_REF.sub(r"\1", name or "")
    found = [r for r in rows if col(r, "QualifiedApiName__c") == name and col(r, "RecordType.DeveloperName") == "Record_Component"]
    found.sort(key=lambda r: (bool(col(r, "Active__c", True)), float(col(r, "Version__c") or 0)), reverse=True)
    return found[0] if found else None


# ---- what a design asks ------------------------------------------------------------------------------------------------

def rules_by_name(design):
    out = {}
    for rule in get(design, "conditionalLogic__r") or []:
        conditions = sorted((bare(get(c, "fieldName__c") or "").lower(), str(get(c, "operation__c") or ""),
                             str(get(c, "value__c") if get(c, "value__c") is not None else ""))
                            for c in get(rule, "conditions__r") or [])
        out[rule.get("QualifiedApiName")] = {"type": get(rule, "conditionType__c") or "AND", "logic": get(rule, "customLogic__c") or "",
                                             "conditions": conditions}
    return out


def rule_text(rule, display):
    if not rule:
        return ""
    joined = f" {rule['type']} ".join(f"{f} {op} {v}".strip() for f, op, v in rule["conditions"]) or "(no conditions)"
    return f"{(display or 'SHOW').upper()} when {joined}" + (f" [{rule['logic']}]" if rule.get("logic") else "")


def choices(field):
    parts = []
    overrides = get(field, "picklistOptionOverrides__c")
    if overrides:
        parts.append("options " + ";".join(v.strip() for v in str(overrides).split(";") if v.strip()))
    settings = parse_json(get(field, "picklistOptionSettings__c"))
    if isinstance(settings, dict) and settings:
        parts.append("labels " + "; ".join(f"{k}={(v or {}).get('label', '')}" for k, v in sorted(settings.items()) if isinstance(v, dict)))
    if get(field, "booleanPicklistTypeOverride__c") not in (None, "", "default"):
        parts.append("answers " + str(get(field, "booleanPicklistTypeOverride__c")))
    presets = parse_json(get(field, "numberPresets__c"))
    if isinstance(presets, dict) and presets.get("options"):
        parts.append("presets " + ", ".join(str(o.get("label") or o.get("value")) for o in presets["options"] if isinstance(o, dict)))
    return " | ".join(parts)


def field_label(field, obj, index):
    custom = plain(get(field, "customLabelLong__c") or get(field, "customLabel__c") or get(field, "Label_Rich_Text__c") or "")
    if custom:
        return custom
    entry = ((index or {}).get(obj) or {}).get("fields") or {}
    name = str(get(field, "fieldName__c") or "").replace(STAR, NS)
    return plain((entry.get(name) or entry.get(bare(name)) or {}).get("label") or bare(name))


def questions(design, default_object=None, index=None):
    """Every question a design asks, in order: field key, label, required, choices and the rule that shows it."""
    if not isinstance(design, dict):
        return []
    root_obj = str(get(design, "ObjectApiName__c") or default_object or NS + "Form_Submission__c").replace(STAR, NS)
    rules = rules_by_name(design)
    out = []
    for section in sorted(get(design, "sections__r") or [], key=lambda s: float(get(s, "position__c") or 0)):
        section_rule = rule_text(rules.get(get(section, "conditionalLogic__c")), get(section, "displayType__c"))
        for field in sorted(get(section, "fields__r") or [], key=lambda f: float(get(f, "position__c") or 0)):
            name = str(get(field, "fieldName__c") or "").replace(STAR, NS)
            if not name or name.lower() == "id":
                continue
            obj = str(get(field, "Object__c") or root_obj).replace(STAR, NS)
            rule = rule_text(rules.get(get(field, "conditionalLogic__c")), get(field, "displayType__c"))
            out.append({"key": f"{bare(obj).lower()}.{bare(name).lower()}", "field": name, "object": obj,
                        "label": field_label(field, obj, index), "required": bool(get(field, "required__c")),
                        "choices": choices(field), "rule": " / ".join(r for r in (section_rule, rule) if r)})
    return out


def mapping_of(design):
    value = get(design, "Submission_Field_Map__c") if isinstance(design, dict) else None
    parsed = parse_json(value) if isinstance(value, str) else value
    return json.dumps(parsed, sort_keys=True) if parsed else ""


def differences(member, shared, member_map="", shared_map=""):
    """What would change for a member section if it showed the shared component."""
    have = {q["key"]: q for q in member}
    want = {q["key"]: q for q in shared}
    out = {"loses": [q["label"] for q in member if q["key"] not in want],
           "gains": [q["label"] for q in shared if q["key"] not in have],
           "relabels": [], "required": [], "choices": [], "rules": [], "mapping": []}
    for key, q in have.items():
        s = want.get(key)
        if not s:
            continue
        if q["label"].lower() != s["label"].lower():
            out["relabels"].append(f"'{q['label']}' would read '{s['label']}'")
        if q["required"] != s["required"]:
            out["required"].append(f"{q['label']} would be {'required' if s['required'] else 'optional'}")
        if q["choices"] != s["choices"]:
            out["choices"].append(f"{q['label']}: {q['choices'] or 'its own choices'} would be {s['choices'] or 'its own choices'}")
        if q["rule"] != s["rule"]:
            out["rules"].append(f"{q['label']}: {q['rule'] or 'always shown'} would be {s['rule'] or 'always shown'}")
    if member_map != shared_map:
        out["mapping"].append("its Form Template Mapping differs from the shared component's")
    return out


OTHER_CHANGES = ("relabels", "required", "choices", "rules", "mapping")


def signature(qs):
    return [[q["key"], q["label"].lower(), q["required"], q["choices"], q["rule"]] for q in qs]


# ---- grouping: org-catalog's finding -----------------------------------------------------------------------------------

def sibling(name, marker):
    """The scripts folder of another skill of this plugin that holds marker, whether its folder is <name> or
    <plugin name>:<name> (_shared/lib/siblings.py), or None when it is not installed."""
    if str(HERE.parent / "_shared" / "lib") not in sys.path:
        sys.path.insert(0, str(HERE.parent / "_shared" / "lib"))
    try:
        import siblings
    except ImportError:
        return None
    try:
        return pathlib.Path(siblings.find(str(HERE.parent), name, subdir="scripts", markers=[marker]))
    except siblings.NotFound:
        return None


def load_org_catalog(path=None):
    """org-catalog's scripts (its repeated-sections finding and section measure), from the org-catalog skill of this
    plugin (its folder is org-catalog or <plugin name>:org-catalog; _shared/lib/siblings.py finds either)."""
    if path:
        folder = pathlib.Path(path)
    else:
        folder = sibling("org-catalog", "ocbuild.py")
        if folder is None:  # no org-catalog (chat): the catalog's own groups are used
            return None
    if not (folder / "ocbuild.py").is_file():
        return None
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location("ftk_ocbuild", folder / "ocbuild.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - an org-catalog that cannot load leaves the catalog's own groups
        return None


def template_sections(catalog):
    """{section Id: where} for every template section in the catalog."""
    out = {}
    for template in catalog.get("templates") or []:
        for page in template.get("pages") or []:
            for section in page.get("sections") or []:
                out[section.get("id")] = {"template_id": template.get("id"), "template": template.get("name"),
                                          "page": page.get("position"), "position": section.get("position"),
                                          "section": section.get("title"), "section_id": section.get("id"),
                                          "source": section.get("source"), "component": section.get("component"),
                                          "object": section.get("object"), "fields": section.get("fields") or []}
    return out


def one_off_records(catalog):
    """Record components placed in exactly one template section and nowhere else: a section's own questions, built as
    a record. They join the sections that ask the same questions."""
    by_place = {(s["template_id"], s["page"], s["position"]): s for s in template_sections(catalog).values()}
    out = []
    for component in catalog.get("components") or []:
        if component.get("kind") != "record" or component.get("packaged") or component.get("used_by_components"):
            continue
        places = component.get("used_in") or []
        if len(places) != 1 or places[0].get("role") != "section" or not places[0].get("template_id"):
            continue
        where = by_place.get((places[0]["template_id"], places[0].get("page"), places[0].get("position")))
        if where:
            out.append(dict(where, object=component.get("object") or where.get("object"), fields=component.get("fields") or [],
                            kind="record", component=component["name"]))
    return out


def twins_of(catalog):
    return {obj: entry.get("twins") or [] for obj, entry in (catalog.get("fields_index") or {}).items()}


def find_groups(catalog, oc=None, promote_at=PROMOTE_AT):
    """Groups of sections that ask the same questions on promote_at templates or more, and warnings."""
    warnings = []
    sections = template_sections(catalog)
    one_offs = one_off_records(catalog)
    groups = catalog.get("repeated_sections") or []
    if one_offs and oc is not None:
        pool = [dict(s, kind="json") for s in sections.values() if s["source"] == "custom" and s["fields"]] + one_offs
        groups = oc.repeated_sections(pool, twins_of(catalog))
    elif one_offs:
        warnings.append("org-catalog is not beside this skill, so one-off record components ("
                        + ", ".join(sorted(o["component"] for o in one_offs)) + ") were not compared; only the catalog's "
                        "repeated JSON sections are grouped. Install the whole Flow Tool Kit plugin to include them")
    kinds = {o["section_id"]: o for o in one_offs}
    out = []
    for group in groups:
        members = []
        for m in group.get("sections") or []:
            where = sections.get(m.get("section_id")) or {}
            one_off = kinds.get(m.get("section_id"))
            members.append({"section_id": m.get("section_id"), "template_id": m.get("template_id"), "template": m.get("template"),
                            "page": m.get("page"), "position": m.get("position"), "title": m.get("section") or where.get("section"),
                            "kind": "record" if one_off else "json", "component": (one_off or {}).get("component"),
                            "exact": m.get("exact"), "by_field": m.get("by_field")})
        templates = len({m["template_id"] for m in members})
        if templates < promote_at:
            continue
        out.append({"title": group.get("title"), "object": group.get("object"), "templates": templates,
                    "fields": group.get("fields") or [], "members": members})
    out.sort(key=lambda g: (-g["templates"], str(g["title"])))
    for n, group in enumerate(out, 1):
        group["id"] = f"g{n}"
    return out, warnings


# ---- the org: Salesforce CLI, or rows a connector returned ------------------------------------------------------------

def run_sf(args):
    try:
        proc = subprocess.run(["sf"] + args + ["--json"], capture_output=True, text=True)
    except FileNotFoundError:
        raise ConsolidateError("The Salesforce CLI (sf) is not installed or not on the PATH. Sign in with it, or in chat run "
                               "the queries through the Salesforce connector (consolidate.py queries) and pass --rows.")
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError:
        data = {}
    if not data:
        raise ConsolidateError((proc.stderr or out or "sf returned nothing").strip()[:600])
    if data.get("status", 1) != 0:
        raise ConsolidateError(str(data.get("message") or data.get("name") or "sf failed").strip())
    return data.get("result") or {}


def strip_attributes(node):
    if isinstance(node, dict):
        return {k: strip_attributes(v) for k, v in node.items() if k != "attributes"}
    if isinstance(node, list):
        return [strip_attributes(v) for v in node]
    return node


def read_rows(queries, target_org=None, rows_file=None, sf=run_sf):
    """{key: rows} for each query: from the CLI, or from a file of rows a connector returned (saved under each key)."""
    if rows_file:
        given = load_json(rows_file)
        missing = [q["key"] for q in queries if q["key"] not in given and not q.get("optional")]
        if missing:
            raise ConsolidateError(f"{rows_file} has no rows for: {', '.join(missing)} (run each query and save its rows under its key)")
        return {q["key"]: strip_attributes(given.get(q["key"]) or []) for q in queries}
    out = {}
    for q in queries:
        args = ["data", "query", "--query", q["soql"]] + (["--target-org", target_org] if target_org else [])
        try:
            out[q["key"]] = strip_attributes(sf(args).get("records") or [])
        except ConsolidateError:
            if not q.get("optional"):
                raise
            out[q["key"]] = []
    return out


def snapshot_queries(catalog, oc=None):
    groups, _ = find_groups(catalog, oc)
    ids = [m["section_id"] for g in groups for m in g["members"] if m.get("section_id")]
    names = [m["component"] for g in groups for m in g["members"] if m.get("component")]
    queries = [{"key": "org", "soql": "SELECT Id, Name FROM Organization"},
               {"key": "import", "soql": "SELECT Id FROM ApexClass WHERE NamespacePrefix = 'FlowToolKit' AND Name = 'FormComponentImport'",
                "optional": True}]
    if ids:
        queries.append({"key": "sections", "soql": f"SELECT {', '.join(SECTION_COLUMNS)} FROM {NS}Form_Template_Page_Section__c "
                                                   f"WHERE Id IN ({soql_list(ids)})"})
    if names:
        queries.append({"key": "components", "soql": f"SELECT {', '.join(COMPONENT_COLUMNS)} FROM {NS}Form_Component__c "
                                                     f"WHERE {NS}QualifiedApiName__c IN ({soql_list(names)})"})
    return queries


def take_snapshot(catalog, target_org=None, rows_file=None, sf=run_sf, oc=None):
    rows = read_rows(snapshot_queries(catalog, oc), target_org, rows_file, sf)
    org = (rows.get("org") or [{}])[0]
    catalog_org = (catalog.get("org") or {}).get("id")
    if catalog_org and org.get("Id") and org["Id"][:15] != catalog_org[:15]:
        raise ConsolidateError(f"the catalog is for org {catalog_org}, but this org is {org['Id']}: run org-catalog here first")
    return {"snapshot_version": 1, "taken_at": stamp(), "source": "rows" if rows_file else "sf-cli",
            "org": {"id": org.get("Id"), "name": org.get("Name")}, "import_available": bool(rows.get("import")),
            "sections": rows.get("sections") or [], "components": rows.get("components") or []}


# ---- the dry run -------------------------------------------------------------------------------------------------------

def parse_pairs(values, option, sep="="):
    out = {}
    for value in values or []:
        key, mark, rest = value.partition(sep)
        if not mark or not key.strip() or not rest.strip():
            raise ConsolidateError(f"{option} takes <group>{sep}<value>, got {value!r}", 2)
        out.setdefault(key.strip(), []).append(rest.strip())
    return out


def answers_from(args):
    return {"merge": set(args.merge or []), "add": parse_pairs(args.add, "--add", ":"),
            "separate": set(args.separate or []), "join": set(args.join or []),
            "base": {k: v[-1] for k, v in parse_pairs(args.base, "--base").items()},
            "name": {k: v[-1] for k, v in parse_pairs(args.name, "--name").items()},
            "shape": {k: v[-1] for k, v in parse_pairs(args.shape, "--shape").items()},
            "describe": {k: v[-1] for k, v in parse_pairs(args.describe, "--describe").items()}}


def member_design(member, snapshot):
    """(design, row, source) for a member section, from the snapshot."""
    row = next((r for r in snapshot.get("sections") or [] if r.get("Id") == member["section_id"]), None)
    if row is None:
        return None, None, None
    source = section_source(row)
    if source["kind"] == "json":
        return source.get("design"), row, source
    if source["kind"] == "record":
        component = latest_record_design(snapshot.get("components") or [], source["name"])
        design = parse_json(col(component, "FormConfigJSON__c")) if component else None
        return design if isinstance(design, dict) else None, row, source
    return None, row, source


def clean_design(design):
    """A stored design ready to copy: record plumbing dropped, and the package prefix written as *__ throughout (the
    exact inverse of what the package does on load), so the copy never mixes the two forms."""
    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items() if local(k) not in DROPPED}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    return json.loads(json.dumps(walk(copy.deepcopy(design))).replace(NS, STAR))


def find_field_node(design, key):
    root_obj = str(get(design, "ObjectApiName__c") or "").replace(STAR, NS)
    for section in get(design, "sections__r") or []:
        for field in get(section, "fields__r") or []:
            name = str(get(field, "fieldName__c") or "").replace(STAR, NS)
            obj = str(get(field, "Object__c") or root_obj).replace(STAR, NS)
            if name and (bare(name).lower() == key.split(".")[-1] and (key.count(".") == 0 or bare(obj).lower() == key.split(".")[0] or not root_obj)):
                return field
    return None


def default_description(labels, templates):
    text = (f"Shared questions: {', '.join(labels)}. Placed on {', '.join(templates)}; each section that shows it keeps "
            "its own title, header and rules, and a change here reaches every one of them.")
    return text if len(text) <= 255 else text[:252].rsplit(" ", 1)[0] + "..."


def plan(catalog, snapshot, answers=None, oc=None, promote_at=PROMOTE_AT):
    answers = answers or {}
    merge = answers.get("merge") or set()
    groups, warnings = find_groups(catalog, oc, promote_at)
    problems = []
    index = catalog.get("fields_index") or {}
    taken = {bare(c.get("name")).lower() for c in catalog.get("components") or [] if c.get("name")}
    used_names = set()
    repoint = []
    known_sections = {m["section_id"] for g in groups for m in g["members"]}
    for value in sorted((answers.get("separate") or set()) | (answers.get("join") or set())):
        if value not in known_sections:
            warnings.append(f"{value} is not a section in any group; that answer was ignored")
    for group in groups:
        gid = group["id"]
        group["merge"] = "all" in merge or gid in merge
        designs = {}
        for m in group["members"]:
            design, row, source = member_design(m, snapshot)
            m["last_modified"] = col(row, "LastModifiedDate") if row else None
            m["before"] = {c: col(row, c) for c in ("FormConfigJSON__c", "FormQualifiedApiName__c", "Form_Component__c")} if row else {}
            m["source_digest"] = digest(m["before"]) if row else None
            if row is None:
                (problems if group["merge"] else warnings).append(
                    f"{gid}: {m['template']} page {m['page']} ({m['title']}) was not read: take the snapshot again")
                continue
            expected_kind = m["kind"]
            if (source or {}).get("kind") != expected_kind or design is None:
                (problems if group["merge"] else warnings).append(
                    f"{gid}: {m['template']} page {m['page']} ({m['title']}) is no longer the {'JSON section' if expected_kind == 'json' else 'record component'} "
                    "the catalog found: run org-catalog again")
                continue
            designs[m["section_id"]] = design
            m["questions"] = questions(design, group["object"], index)
        readable = [m for m in group["members"] if m["section_id"] in designs]
        if not readable:
            group["status"] = "unreadable"
            continue
        base_id = answers.get("base", {}).get(gid)
        if base_id and base_id not in designs:
            problems.append(f"{gid}: --base {base_id} is not a readable member of this group")
            base_id = None
        if not base_id:  # the member closest to the group's typical design, a JSON section before a record
            base_id = max(readable, key=lambda m: (float(m.get("by_field") or 0), float(m.get("exact") or 0), m["kind"] == "json"))["section_id"]
        base = designs[base_id]
        group["base"] = base_id
        shared = list(next(m for m in readable if m["section_id"] == base_id)["questions"])
        added = []
        for wanted in answers.get("add", {}).get(gid, []):
            key = wanted.replace(STAR, NS)
            matches = [(m, q) for m in readable for q in m["questions"]
                       if q["key"] == key.lower() or q["key"].split(".")[-1] == bare(key).lower()]
            if not matches:
                problems.append(f"{gid}: --add {wanted}: no member of this group asks that field")
                continue
            m, q = matches[0]
            if q["key"] in {s["key"] for s in shared}:
                continue
            node = find_field_node(designs[m["section_id"]], q["key"])
            added.append({"key": q["key"], "label": q["label"], "from": m["section_id"], "node": clean_design(node) if node else None})
            shared.append(q)
        group["added"] = added
        group["shared_questions"] = shared
        base_map = mapping_of(base)
        for m in group["members"]:
            if m["section_id"] not in designs:
                m["status"] = "unreadable"
                continue
            changes = differences(m["questions"], shared, mapping_of(designs[m["section_id"]]), base_map)
            m["changes"] = {k: v for k, v in changes.items() if v}
            others = [k for k in OTHER_CHANGES if changes[k]]
            if m["section_id"] in (answers.get("separate") or set()):
                m["status"], m["reason"] = "separate", "you chose to keep it as it is"
            elif changes["loses"]:
                m["status"] = "differs"
                m["reason"] = (f"it asks {', '.join(changes['loses'])}, which the shared component would not: add "
                               f"{'it' if len(changes['loses']) == 1 else 'them'} to the shared component, or keep this section separate")
            elif others and m["section_id"] not in (answers.get("join") or set()):
                m["status"] = "differs"
                m["reason"] = "it would change (" + "; ".join(x for k in others for x in changes[k]) + "): take the shared version, or keep it separate"
            else:
                m["status"] = "joins"
                m["reason"] = ("asks the same questions" if not changes["gains"] and not others else
                               "; ".join(([f"also asks {', '.join(changes['gains'])} from now on"] if changes["gains"] else [])
                                         + [x for k in others for x in changes[k]]))
        joining = [m for m in group["members"] if m.get("status") == "joins"]
        group["joining_templates"] = len({m["template_id"] for m in joining})
        name = answers.get("name", {}).get(gid)
        if name:
            if not API_NAME.match(name) or len(name) > 40 or re.search(r"_v\d+$", name):
                problems.append(f"{gid}: --name {name}: letters, digits and single underscores, at most 40 characters, no version suffix")
            elif name.lower() in taken or name.lower() in used_names:
                problems.append(f"{gid}: the org (or another group) already has a component named {name}; choose another name")
        else:
            name = shared_name(group["title"], taken | used_names)
        used_names.add(name.lower())
        shape = answers.get("shape", {}).get(gid, "record")
        if shape not in SHAPES:
            problems.append(f"{gid}: --shape {shape}: record or metadata")
            shape = "record"
        group.update({"name": name, "label": plain(group["title"])[:80], "shape": shape,
                      "description": answers.get("describe", {}).get(gid) or default_description(
                          [q["label"] for q in shared], sorted({m["template"] for m in joining}) or sorted({m["template"] for m in readable})),
                      "recommendation": ("One shared record component, built straight in the org with no deploy: every "
                                         "section that shows it picks up a change at once, and each keeps its own title, "
                                         "header and rules. Metadata can come later through convert-to-metadata, once the "
                                         "component is final."),
                      "base_design": clean_design(base)})
        if len(group["description"]) > 255:
            problems.append(f"{gid}: the description is {len(group['description'])} characters; a component description holds 255")
        if not group["merge"]:
            group["status"] = "proposed"
            continue
        if group["joining_templates"] < promote_at:
            group["status"] = "too few"
            warnings.append(f"{gid} ({group['title']}): only {group['joining_templates']} template would show the shared "
                            f"component after the answers; it takes {promote_at}. Nothing is built for it")
            continue
        group["status"] = "merge"
        if shape == "record" and not snapshot.get("import_available"):
            problems.append(f"{gid}: this org has no FlowToolKit.FormComponentImport (Flow Tool Kit 5.3 or later), which creates "
                            "a record component: upgrade Flow Tool Kit, or choose --shape metadata in Claude Code")
        ref = f"{name}_v0" if shape == "record" else name
        for m in joining:
            wrapper = parse_json(m["before"].get("FormConfigJSON__c") or "")
            repoint.append({"group": gid, "id": m["section_id"], "sobject": f"{NS}Form_Template_Page_Section__c",
                            "where": f"{m['template']} page {m['page']}, section {m['position']} ({m['title']})",
                            "last_modified": m["last_modified"], "before": m["before"],
                            "after": {"formSelectionMode": "component", "formQualifiedApiName": ref,
                                      "object": (wrapper or {}).get("object") if isinstance(wrapper, dict) else None},
                            "kept_json": m["kind"] == "json"})
    return {"consolidation_version": 1, "planned_at": stamp(), "promote_at": promote_at,
            "catalog": {"taken_at": catalog.get("taken_at"), "org": (catalog.get("org") or {}).get("id")},
            "org": snapshot.get("org"), "groups": groups, "repoint": repoint, "problems": problems, "warnings": warnings}


def approved_part(conversion):
    """What the person approves: every group that merges, with its design and members, and every repoint."""
    groups = [{k: g.get(k) for k in ("id", "name", "label", "shape", "object", "description", "base", "added", "base_design",
                                     "shared_questions")}
              | {"members": [{k: m.get(k) for k in ("section_id", "status", "source_digest", "last_modified")} for m in g["members"]]}
              for g in conversion["groups"] if g.get("status") == "merge"]
    return {"groups": groups, "repoint": conversion["repoint"]}


def conversion_digest(conversion):
    return digest(approved_part(conversion))


def print_plan(conversion, out=None):
    out = out or sys.stdout
    w = lambda line="": print(line, file=out)
    w("Dry run: sections that repeat across your Form Templates. Nothing has changed in the org.")
    if not conversion["groups"]:
        w()
        w(f"No section repeats on {conversion['promote_at']} or more templates: every section stays as it is.")
    for g in conversion["groups"]:
        w()
        state = {"merge": "MERGE", "proposed": "proposed (answer --merge " + g["id"] + " to include it)",
                 "too few": "not merged: too few templates after the answers", "unreadable": "not read"}.get(g.get("status"), g.get("status"))
        w(f"{g['id']} {g['title']} on {g['templates']} templates: {state}")
        if g.get("status") == "unreadable":
            continue
        w(f"    shared component: {g['name']} ({g['shape']} component on {g['object']}), built from the section on "
          + next((f"{m['template']} page {m['page']}" for m in g['members'] if m['section_id'] == g.get('base')), "?"))
        w(f"    asks: {', '.join(q['label'] for q in g.get('shared_questions') or [])}")
        if g.get("added"):
            w(f"    added by your answer: {', '.join(a['label'] for a in g['added'])}")
        w(f"    why: {g['recommendation']}")
        for m in g["members"]:
            w(f"    - {m['template']} page {m['page']}, section {m['position']} ({m['title']}, "
              f"{'JSON' if m['kind'] == 'json' else 'record component ' + str(m.get('component'))}): "
              f"{m.get('status')}{': ' + m['reason'] if m.get('reason') else ''}  [{m['section_id']}]")
    if conversion["repoint"]:
        w()
        w(f"Repointed ({len(conversion['repoint'])} sections; each keeps its own title, header and rules):")
        for r in conversion["repoint"]:
            w(f"  - {r['where']}: shows {r['after']['formQualifiedApiName']}")
    for title, rows in (("Problems (nothing can be built until each is fixed)", conversion["problems"]),
                        ("Warnings", conversion["warnings"])):
        if rows:
            w()
            w(title + ":")
            for row in rows:
                w(f"  - {row}")
    w()
    w("The old JSON stays on each repointed section until the separate cleanup step.")


# ---- build -------------------------------------------------------------------------------------------------------------

def load_component_module(path=None):
    """build-form-component's scripts/component.py: it copies and renames a design, checks it and writes metadata."""
    folder = None if path else sibling("build-form-component", "component.py")
    candidate = pathlib.Path(path) if path else (folder / "component.py" if folder else None)
    if candidate is None or not candidate.is_file():
        raise ConsolidateError("build-form-component's scripts/component.py was not found beside this skill. It writes the "
                               "shared component; install the whole Flow Tool Kit plugin, or pass --component-py <path>.")
    spec = importlib.util.spec_from_file_location("ftk_component", candidate)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shared_design(group, module):
    """The shared component's JSON: the base member's design under the shared name, every child renamed, plus the
    added fields, written by build-form-component's own copy and extend."""
    base = copy.deepcopy(group["base_design"])
    base.setdefault("QualifiedApiName", group["name"] + "_Source")
    if not get(base, "ObjectApiName__c"):
        base[STAR + "ObjectApiName__c"] = str(group["object"] or NS + "Form_Submission__c").replace(NS, STAR)
    nodes = [a["node"] for a in group.get("added") or [] if a.get("node")]
    if nodes:
        root = module.extend_component(base, group["name"], nodes, group["label"], group["description"])
    else:
        root = module._children_renamed(base, base.get("QualifiedApiName") or "", group["name"])
    root["QualifiedApiName"] = group["name"]
    root["Label"] = group["label"]
    for key in [k for k in root if local(k) in ("Description__c", "CategoryTag__c", "Active__c")]:
        del root[key]
    root[STAR + "Description__c"] = group["description"]
    root[STAR + "CategoryTag__c"] = "Component(s)"
    root[STAR + "Active__c"] = True
    return root


def manifest_xml(members):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<Package xmlns="http://soap.sforce.com/2006/04/metadata">', "    <types>"]
    lines += [f"        <members>{escape(m)}</members>" for m in sorted(members)]
    return "\n".join(lines + ["        <name>CustomMetadata</name>", "    </types>", "</Package>", ""])


def stamp_check(var, rows):
    return [f"Map<Id, String> {var}Stamp = new Map<Id, String>{{"
            + ", ".join(f"{apex_str(r['id'])} => {apex_str((r['last_modified'] or '')[:19])}" for r in rows) + "};",
            f"List<{NS}Form_Template_Page_Section__c> {var} = [SELECT Id, LastModifiedDate, {NS}FormConfigJSON__c, "
            f"{NS}FormQualifiedApiName__c, {NS}Form_Component__c FROM {NS}Form_Template_Page_Section__c WHERE Id IN :{var}Stamp.keySet()];",
            f"if ({var}.size() != {var}Stamp.size()) throw new IllegalArgumentException('A section in the dry run is gone. Run the "
            "dry run again. Nothing was changed.');",
            f"for ({NS}Form_Template_Page_Section__c row : {var}) {{",
            f"    if (row.LastModifiedDate.formatGmt('yyyy-MM-dd\\'T\\'HH:mm:ss') != {var}Stamp.get(row.Id)) throw new "
            "IllegalArgumentException('Section ' + row.Id + ' changed after the dry run. Run the dry run again. Nothing was changed.');",
            "}"]


def repoint_apex(conversion):
    """All or nothing: stops, changing nothing, when a section changed after the dry run or a shared component is missing."""
    groups = [g for g in conversion["groups"] if g.get("status") == "merge"]
    records = [g["name"] for g in groups if g["shape"] == "record"]
    metadata = [g["name"] for g in groups if g["shape"] == "metadata"]
    lines = ["// Repoint each member section at its shared component. Written by consolidate-sections.",
             "// Run it only after the shared components are created (record) or deployed (metadata).",
             "Map<String, Id> shared = new Map<String, Id>();"]
    if records:
        lines += [f"Set<String> recordNames = new Set<String>{{{', '.join(apex_str(n) for n in records)}}};",
                  f"for ({NS}Form_Component__c c : [SELECT Id, {NS}QualifiedApiName__c FROM {NS}Form_Component__c WHERE "
                  f"{NS}QualifiedApiName__c IN :recordNames AND RecordType.DeveloperName = 'Record_Component']) "
                  f"shared.put(c.{NS}QualifiedApiName__c, c.Id);",
                  "if (!shared.keySet().containsAll(recordNames)) throw new IllegalArgumentException('A shared record component "
                  "is not in this org yet. Run create.apex first. Nothing was changed.');"]
    if metadata:
        lines += [f"Set<String> metadataNames = new Set<String>{{{', '.join(apex_str(n) for n in metadata)}}};",
                  f"if ([SELECT COUNT() FROM {NS}Form__mdt WHERE QualifiedApiName IN :metadataNames] != metadataNames.size()) "
                  "throw new IllegalArgumentException('A shared metadata component is not in this org yet. Deploy it first. "
                  "Nothing was changed.');"]
    rows = conversion["repoint"]
    lines += stamp_check("sections", rows)
    lines.append("Map<Id, String> target = new Map<Id, String>{" + ", ".join(
        f"{apex_str(r['id'])} => {apex_str(r['after']['formQualifiedApiName'])}" for r in rows) + "};")
    lines.append(f"for ({NS}Form_Template_Page_Section__c row : sections) {{")
    lines.append(f"    Object parsed = String.isBlank(row.{NS}FormConfigJSON__c) ? null : JSON.deserializeUntyped(row.{NS}FormConfigJSON__c);")
    lines.append("    Map<String, Object> wrapper = new Map<String, Object>();")
    lines.append("    if (parsed instanceof Map<String, Object> && ((Map<String, Object>) parsed).containsKey('formSelectionMode')) "
                 "wrapper = (Map<String, Object>) parsed;")
    lines.append(f"    else if (parsed != null) wrapper.put('formJsonConfig', row.{NS}FormConfigJSON__c);")
    lines.append("    String ref = target.get(row.Id);")
    lines.append("    wrapper.put('formSelectionMode', 'component');")
    lines.append("    wrapper.put('formQualifiedApiName', ref);")
    lines.append(f"    row.{NS}FormConfigJSON__c = JSON.serialize(wrapper);")
    lines.append(f"    row.{NS}FormQualifiedApiName__c = ref;")
    lines.append(f"    row.{NS}Form_Component__c = ref.endsWith('_v0') ? shared.get(ref.removeEnd('_v0')) : null;")
    lines.append("}")
    lines.append("update sections;")
    lines.append(f"System.debug(LoggingLevel.ERROR, 'Repointed ' + sections.size() + ' sections.');")
    return "\n".join(lines) + "\n"


def rollback_apex(conversion):
    lines = ["// Put every repointed section back exactly as it was. Written by consolidate-sections.",
             "// The shared components stay in the org, unused; only the sections change back."]
    for n, r in enumerate(conversion["repoint"], 1):
        var = f"s{n}"
        lines.append(f"{NS}Form_Template_Page_Section__c {var} = new {NS}Form_Template_Page_Section__c(Id = {apex_str(r['id'])});")
        for field in ("FormConfigJSON__c", "FormQualifiedApiName__c", "Form_Component__c"):
            lines.append(f"{var}.{NS}{field} = {apex_str(r['before'].get(field))};")
        lines.append(f"update {var};")
    return "\n".join(lines) + "\n"


def mark_plans(conversion, plans):
    """Record each merged section in its template's plan.json, so a build-template rebuild keeps the shared component."""
    changes = []
    by_template = {}
    for path, plan_data in plans:
        template_id = (plan_data.get("build") or {}).get("template_id")
        if template_id:
            by_template[template_id[:15]] = (path, plan_data)
    for g in conversion["groups"]:
        if g.get("status") != "merge":
            continue
        for m in g["members"]:
            if m.get("status") != "joins" or not m.get("template_id") or m["template_id"][:15] not in by_template:
                continue
            path, plan_data = by_template[m["template_id"][:15]]
            pages = plan_data.get("pages") or []
            if not 1 <= int(m["page"] or 0) <= len(pages):
                continue
            sections = pages[int(m["page"]) - 1].get("sections") or []
            if not 1 <= int(m["position"] or 0) <= len(sections):
                continue
            key = re.sub(r"[^a-z0-9]+", "_", g["name"].lower()).strip("_")
            components = plan_data.setdefault("components", [])
            components[:] = [c for c in components if c.get("key") != key] + [
                {"key": key, "decision": "reuse", "name": g["name"], "object": g["object"],
                 "reason": "consolidate-sections: one shared component for the sections that ask these questions"}]
            sections[int(m["position"]) - 1]["component"] = key
            changes.append(f"{path}: page {m['page']} section {m['position']} reuses {g['name']}")
    for path, plan_data in plans:
        write_json(path, plan_data)
    return changes


def build(conversion, work, module, out=None, overwrite=False, form_object=None, new_form_object=False, catalog=None):
    if conversion.get("problems"):
        raise ConsolidateError("the dry run lists problems; fix them and run the dry run again", 2)
    confirmed = conversion.get("confirmed") or {}
    if confirmed.get("digest") != conversion_digest(conversion):
        raise ConsolidateError("not confirmed, or the dry run changed after it was confirmed: show it to the person and run "
                               "confirm on their yes", 3)
    groups = [g for g in conversion["groups"] if g.get("status") == "merge"]
    if not groups:
        raise ConsolidateError("no group is marked to merge; nothing to build", 2)
    work = pathlib.Path(work)
    findings, written, built = [], [], {}
    checker_catalog = module.Catalog(catalog) if catalog is not None and hasattr(module, "Catalog") else None
    designs = {}
    for g in groups:
        design = shared_design(g, module)
        expected = signature(g["shared_questions"])
        if signature(questions(design, g["object"], (catalog or {}).get("fields_index"))) != expected:
            findings.append({"severity": "error", "component": g["name"], "message": "the written design does not ask the "
                             "questions the dry run showed; nothing was written"})
        if hasattr(module, "Checker"):
            checker = module.Checker(catalog=checker_catalog, path=g["shape"]) if checker_catalog else module.Checker(path=g["shape"])
            findings += [dict(f, component=g["name"]) for f in checker.run(design) or checker.findings]
        designs[g["name"]] = design
    errors = [f for f in findings if f.get("severity") == "error"]
    if errors:
        return {"stopped": True, "findings": findings}
    files = {}
    for g in groups:
        files[work / "components" / f"{g['name']}.json"] = json.dumps(designs[g["name"]], indent=1, ensure_ascii=False) + "\n"
    metadata_members = []
    for g in [g for g in groups if g["shape"] == "metadata"]:
        if out is None:
            raise ConsolidateError(f"{g['name']} is a metadata component: pass --out <the project's customMetadata folder>")
        cmt, _ = module.emit_cmt(designs[g["name"]], form_object, new_form_object)
        for file_name, text in cmt.items():
            files[pathlib.Path(out) / file_name] = text
            metadata_members.append(file_name[:-len(".md-meta.xml")])
        built[g["name"]] = {"shape": "metadata", "records": sorted(n[:-len(".md-meta.xml")] for n in cmt)}
    for g in [g for g in groups if g["shape"] == "record"]:
        built[g["name"]] = {"shape": "record"}
    clashes = [p for p, text in files.items() if p.exists() and p.read_text(encoding="utf-8") != text
               and pathlib.Path(out or "/nonexistent") in p.parents]
    if clashes and not overwrite:
        raise ConsolidateError("these project files already exist with other content: " + ", ".join(map(str, clashes))
                               + ". Ask the person; rerun with --overwrite on a yes", 4)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(str(path))
    record_groups = [dict(g, _design=json.dumps(designs[g["name"]], ensure_ascii=True)) for g in groups if g["shape"] == "record"]
    if record_groups:
        (work / "create.apex").write_text(create_apex_from(record_groups), encoding="utf-8")
    if metadata_members:
        (work / "package.xml").write_text(manifest_xml(metadata_members), encoding="utf-8")
    (work / "repoint.apex").write_text(repoint_apex(conversion), encoding="utf-8")
    (work / "rollback.apex").write_text(rollback_apex(conversion), encoding="utf-8")
    return {"stopped": False, "findings": findings, "written": written, "built": built,
            "record": bool(record_groups), "metadata": bool(metadata_members)}


def create_apex_from(groups):
    names = [g["name"] for g in groups]
    lines = ["// Create the shared record components. Written by consolidate-sections; run it only on the person's yes.",
             f"Set<String> names = new Set<String>{{{', '.join(apex_str(n) for n in names)}}};",
             f"if ([SELECT COUNT() FROM {NS}Form_Component__c WHERE {NS}QualifiedApiName__c IN :names] > 0) "
             "throw new IllegalArgumentException('A component with one of these names already exists, and the import would "
             "change it in place. Choose another name and run the dry run again. Nothing was created.');"]
    for n, group in enumerate(groups, 1):
        lines.append(f"String component{n} = {apex_str(group['_design'])};")
        lines.append(f"Id created{n} = FlowToolKit.FormComponentImport.createRecordComponent(component{n});")
        lines.append(f"System.debug(LoggingLevel.ERROR, 'CREATED {group['name']}=' + created{n});")
    return "\n".join(lines) + "\n"


# ---- the round trip ---------------------------------------------------------------------------------------------------

def roundtrip_queries(conversion):
    groups = [g for g in conversion["groups"] if g.get("status") == "merge"]
    ids = [m["section_id"] for g in groups for m in g["members"] if m.get("section_id")]
    queries = [{"key": "sections", "soql": f"SELECT {', '.join(SECTION_COLUMNS)} FROM {NS}Form_Template_Page_Section__c "
                                           f"WHERE Id IN ({soql_list(ids)})"}]
    records = [g["name"] for g in groups if g["shape"] == "record"]
    if records:
        queries.append({"key": "components", "soql": f"SELECT {', '.join(COMPONENT_COLUMNS)} FROM {NS}Form_Component__c "
                                                     f"WHERE {NS}QualifiedApiName__c IN ({soql_list(records)})"})
    built = conversion.get("built") or {}
    for kind in METADATA_TYPES:
        names = [n for b in built.values() if b.get("shape") == "metadata" for n in b.get("records") or []
                 if n.startswith(f"{NS}{kind}.")]
        if names:
            queries.append({"key": f"names:{kind}", "soql": f"SELECT QualifiedApiName FROM {NS}{kind}__mdt WHERE QualifiedApiName "
                                                            f"IN ({soql_list(n.split('.', 1)[1] for n in names)})"})
    return queries


def roundtrip(conversion, rows, index=None):
    """Every member that joined now shows its shared component, which asks exactly the approved questions; every member
    kept separate is unchanged. Returns the list of mismatches (empty when the round trip passes)."""
    sections = {r.get("Id"): r for r in rows.get("sections") or []}
    mismatches, checked = [], 0
    for g in [g for g in conversion["groups"] if g.get("status") == "merge"]:
        ref = f"{g['name']}_v0" if g["shape"] == "record" else g["name"]
        if g["shape"] == "record":
            component = latest_record_design(rows.get("components") or [], g["name"])
            design = parse_json(col(component, "FormConfigJSON__c")) if component else None
            if not isinstance(design, dict):
                mismatches.append(f"{g['name']}: the shared record component is not in the org (run create.apex)")
            elif signature(questions(design, g["object"], index)) != signature(g["shared_questions"]):
                asked = [q["label"] for q in questions(design, g["object"], index)]
                mismatches.append(f"{g['name']}: asks {', '.join(asked)}; the approved list was "
                                  f"{', '.join(q['label'] for q in g['shared_questions'])}")
        else:
            for name in (conversion.get("built") or {}).get(g["name"], {}).get("records") or []:
                kind, record = name.split(".", 1)
                if record not in {col(r, "QualifiedApiName") for r in rows.get(f"names:{kind.replace(NS, '')}") or []}:
                    mismatches.append(f"{g['name']}: the metadata record {name} is not in the org (deploy package.xml)")
        for m in g["members"]:
            row = sections.get(m["section_id"])
            checked += 1
            if row is None:
                mismatches.append(f"{m['template']} page {m['page']} ({m['title']}): the section is gone")
                continue
            source = section_source(row)
            if m.get("status") == "joins":
                if source.get("kind") not in ("record", "metadata") or source.get("name") != ref or col(row, "FormQualifiedApiName__c") != ref:
                    mismatches.append(f"{m['template']} page {m['page']} ({m['title']}): shows {source.get('name') or 'its own JSON'}, "
                                      f"not {ref} (run repoint.apex)")
            else:
                now = {c: col(row, c) for c in ("FormConfigJSON__c", "FormQualifiedApiName__c", "Form_Component__c")}
                if digest(now) != m.get("source_digest"):
                    mismatches.append(f"{m['template']} page {m['page']} ({m['title']}): kept separate, but it changed")
    return mismatches, checked


# ---- cleanup: the separate, later step ---------------------------------------------------------------------------------

def cleanup_queries(conversion):
    joined = [m for g in conversion["groups"] if g.get("status") == "merge" for m in g["members"] if m.get("status") == "joins"]
    queries = [{"key": "sections", "soql": f"SELECT {', '.join(SECTION_COLUMNS)} FROM {NS}Form_Template_Page_Section__c "
                                           f"WHERE Id IN ({soql_list(m['section_id'] for m in joined)})"}]
    olds = [m for m in joined if m["kind"] == "record" and m.get("component")]
    if olds:
        refs = [m["component"] + "_v0" for m in olds]
        ids = [m["before"].get("Form_Component__c") for m in olds if m["before"].get("Form_Component__c")]
        where = " OR ".join([f"{NS}{c} IN ({soql_list(refs)})" for c in SECTION_NAME_COLUMNS[:3]]
                            + ([f"{NS}Form_Component__c IN ({soql_list(ids)})"] if ids else []))
        columns = ", ".join(NS + c for c in SECTION_NAME_COLUMNS[:3] + ["Form_Component__c"])
        queries += [{"key": "users", "soql": f"SELECT Id, {columns} FROM {NS}Form_Template_Page_Section__c WHERE {where}"},
                    {"key": "template_users", "soql": f"SELECT Id, Name, {NS}FormQualifiedApiName_Header__c, "
                                                      f"{NS}FormQualifiedApiName_Footer__c FROM {NS}Form_Template__c WHERE "
                                                      f"{NS}FormQualifiedApiName_Header__c IN ({soql_list(refs)}) OR "
                                                      f"{NS}FormQualifiedApiName_Footer__c IN ({soql_list(refs)})"},
                    {"key": "old_components", "soql": f"SELECT Id, {NS}QualifiedApiName__c, RecordType.DeveloperName FROM "
                                                      f"{NS}Form_Component__c WHERE {NS}QualifiedApiName__c IN "
                                                      f"({soql_list(m['component'] for m in olds)})"}]
    return queries


def cleanup_plan(conversion, rows):
    sections = {r.get("Id"): r for r in rows.get("sections") or []}
    strip, delete, keep = [], [], []
    for g in [g for g in conversion["groups"] if g.get("status") == "merge"]:
        ref = f"{g['name']}_v0" if g["shape"] == "record" else g["name"]
        for m in [m for m in g["members"] if m.get("status") == "joins"]:
            row = sections.get(m["section_id"])
            wrapper = parse_json(col(row, "FormConfigJSON__c") or "") if row else None
            if m["kind"] == "json" and isinstance(wrapper, dict) and wrapper.get("formQualifiedApiName") == ref and "formJsonConfig" in wrapper:
                strip.append({"id": m["section_id"], "where": f"{m['template']} page {m['page']} ({m['title']})",
                              "last_modified": col(row, "LastModifiedDate"), "ref": ref})
            if m["kind"] == "record" and m.get("component"):
                old_ref = m["component"] + "_v0"
                ids = [r.get("Id") for r in rows.get("old_components") or []
                       if col(r, "QualifiedApiName__c") == m["component"] and col(r, "RecordType.DeveloperName") == "Record_Component"]
                old_id = m["before"].get("Form_Component__c")
                users = [r.get("Id") for r in rows.get("users") or []
                         if old_ref in [col(r, c) for c in SECTION_NAME_COLUMNS[:3]] or (old_id and col(r, "Form_Component__c") in ids + [old_id])]
                users += [r.get("Name") for r in rows.get("template_users") or []
                          if old_ref in (col(r, "FormQualifiedApiName_Header__c"), col(r, "FormQualifiedApiName_Footer__c"))]
                entry = {"name": m["component"], "ref": old_ref, "ids": ids,
                         "where": f"{m['template']} page {m['page']} ({m['title']})"}
                (keep if users else delete).append(dict(entry, still_used_by=users) if users else entry)
    return {"strip": strip, "delete": [d for d in delete if d["ids"]], "keep": keep}


def cleanup_apex(conversion, cleanup):
    lines = ["// The separate cleanup step. Written by consolidate-sections; run it only after the person checked the",
             "// consolidated templates and said yes."]
    if cleanup["strip"]:
        lines += ["// 1. Remove the old JSON each repointed section still carries."]
        lines += stamp_check("sections", cleanup["strip"])
        lines += [f"for ({NS}Form_Template_Page_Section__c row : sections) {{",
                  f"    Map<String, Object> wrapper = (Map<String, Object>) JSON.deserializeUntyped(row.{NS}FormConfigJSON__c);",
                  "    if (wrapper.get('formSelectionMode') != 'component') throw new IllegalArgumentException('Section ' + row.Id + "
                  "' no longer shows the shared component. Nothing was changed.');",
                  "    wrapper.remove('formJsonConfig');",
                  f"    row.{NS}FormConfigJSON__c = JSON.serialize(wrapper);",
                  "}",
                  "update sections;"]
    if cleanup["delete"]:
        ids = [i for d in cleanup["delete"] for i in d["ids"]]
        refs = [d["ref"] for d in cleanup["delete"]]
        lines += ["// 2. Delete the one-off record components nothing uses any more.",
                  f"Set<Id> ids = new Set<Id>{{{', '.join(apex_str(i) for i in ids)}}};",
                  f"Set<String> refs = new Set<String>{{{', '.join(apex_str(r) for r in refs)}}};",
                  f"Integer users = [SELECT COUNT() FROM {NS}Form_Template_Page_Section__c WHERE {NS}FormQualifiedApiName__c IN :refs "
                  f"OR {NS}Alternate_FormQualifiedApiName__c IN :refs OR {NS}Bulk_FormQualifiedApiName__c IN :refs OR {NS}Form_Component__c IN :ids]"
                  f" + [SELECT COUNT() FROM {NS}Form_Template__c WHERE {NS}FormQualifiedApiName_Header__c IN :refs OR "
                  f"{NS}FormQualifiedApiName_Footer__c IN :refs];",
                  "if (users > 0) throw new IllegalArgumentException('A template still uses one of these record components. Nothing "
                  "was deleted.');",
                  f"List<{NS}Form_Component__c> rows = [SELECT Id FROM {NS}Form_Component__c WHERE Id IN :ids AND "
                  "RecordType.DeveloperName = 'Record_Component'];",
                  "delete rows;"]
    lines.append("System.debug(LoggingLevel.ERROR, 'Cleanup done.');")
    return "\n".join(lines) + "\n"


# ---- command line ------------------------------------------------------------------------------------------------------

def load_catalog(path, allow_stale=False):
    catalog = load_json(path)
    age = catalog_age_hours(catalog)
    if not allow_stale and (age is None or age > MAX_AGE_HOURS):
        raise ConsolidateError("The catalog is older than a day or undated: run org-catalog again, so it knows every template", 2)
    if catalog.get("status") not in (None, "ok"):
        raise ConsolidateError(f"The catalog's status is {catalog.get('status')!r} ({catalog.get('status_note')}); "
                               "it needs a complete read of the org", 2)
    return catalog


def print_queries(queries):
    for q in queries:
        print(f"-- key: {q['key']}{' (optional)' if q.get('optional') else ''}")
        print(q["soql"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge repeated sections into shared components (optional; dry run first)")
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queries")
    q.add_argument("--catalog")
    q.add_argument("--conversion")
    q.add_argument("--for", dest="stage", choices=("snapshot", "roundtrip", "cleanup"), default="snapshot")
    q.add_argument("--allow-stale", action="store_true")
    q.add_argument("--org-catalog-scripts", help="org-catalog's scripts folder, when it is not beside this skill")
    s = sub.add_parser("snapshot")
    s.add_argument("--catalog", required=True)
    s.add_argument("--target-org")
    s.add_argument("--rows")
    s.add_argument("--out", required=True)
    s.add_argument("--allow-stale", action="store_true")
    s.add_argument("--org-catalog-scripts", help="org-catalog's scripts folder, when it is not beside this skill")
    p = sub.add_parser("plan")
    p.add_argument("--catalog", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--merge", action="append")
    p.add_argument("--add", action="append")
    p.add_argument("--separate", action="append")
    p.add_argument("--join", action="append")
    p.add_argument("--base", action="append")
    p.add_argument("--name", action="append")
    p.add_argument("--shape", action="append")
    p.add_argument("--describe", action="append")
    p.add_argument("--promote-at", type=int, default=PROMOTE_AT)
    p.add_argument("--org-catalog-scripts", help="org-catalog's scripts folder, when it is not beside this skill")
    p.add_argument("--allow-stale", action="store_true")
    c = sub.add_parser("confirm")
    c.add_argument("conversion")
    b = sub.add_parser("build")
    b.add_argument("conversion")
    b.add_argument("--out", help="the project's customMetadata folder (metadata components only)")
    b.add_argument("--overwrite", action="store_true")
    b.add_argument("--form-object", help="the org's Form Object record name for a metadata component on a non-packaged object")
    b.add_argument("--new-form-object", action="store_true")
    b.add_argument("--plan", action="append", help="a template's plan.json, to record the shared component in it")
    b.add_argument("--catalog")
    b.add_argument("--component-py")
    for name in ("roundtrip", "cleanup"):
        r = sub.add_parser(name)
        r.add_argument("conversion")
        r.add_argument("--target-org")
        r.add_argument("--rows")
    args = parser.parse_args(argv)
    try:
        if args.command == "queries":
            if args.stage == "snapshot":
                if not args.catalog:
                    raise ConsolidateError("queries --for snapshot needs --catalog", 2)
                print_queries(snapshot_queries(load_catalog(args.catalog, args.allow_stale), load_org_catalog(args.org_catalog_scripts)))
            else:
                if not args.conversion:
                    raise ConsolidateError(f"queries --for {args.stage} needs --conversion", 2)
                conversion = load_json(args.conversion)
                print_queries(roundtrip_queries(conversion) if args.stage == "roundtrip" else cleanup_queries(conversion))
            return 0
        if args.command == "snapshot":
            snapshot = take_snapshot(load_catalog(args.catalog, args.allow_stale), args.target_org, args.rows,
                                     oc=load_org_catalog(args.org_catalog_scripts))
            write_json(args.out, snapshot)
            print(f"read {len(snapshot['sections'])} sections and {len(snapshot['components'])} record component rows into {args.out}")
            return 0
        if args.command == "plan":
            catalog = load_catalog(args.catalog, args.allow_stale)
            oc = load_org_catalog(args.org_catalog_scripts)
            conversion = plan(catalog, load_json(args.snapshot), answers_from(args), oc, args.promote_at)
            conversion["catalog"]["path"] = str(pathlib.Path(args.catalog).resolve())
            write_json(args.out, conversion)
            print_plan(conversion)
            print(f"\nWritten to {args.out}.")
            return 2 if conversion["problems"] else 0
        if args.command == "confirm":
            conversion = load_json(args.conversion)
            if conversion.get("problems"):
                raise ConsolidateError("the dry run lists problems; it cannot be confirmed", 2)
            merging = [g for g in conversion["groups"] if g.get("status") == "merge"]
            if not merging:
                raise ConsolidateError("no group is marked to merge (--merge); there is nothing to confirm", 2)
            conversion["confirmed"] = {"at": stamp(), "digest": conversion_digest(conversion)}
            write_json(args.conversion, conversion)
            print(f"confirmed {len(merging)} shared components and {len(conversion['repoint'])} repointed sections")
            return 0
        if args.command == "build":
            conversion = load_json(args.conversion)
            module = load_component_module(args.component_py)
            catalog_path = args.catalog or (conversion.get("catalog") or {}).get("path")
            catalog = load_json(catalog_path) if catalog_path and pathlib.Path(catalog_path).is_file() else None
            work = pathlib.Path(args.conversion).resolve().parent
            report = build(conversion, work, module, args.out, args.overwrite, args.form_object, args.new_form_object, catalog)
            for f in report["findings"]:
                print(f"  {f.get('severity')}: {f.get('component')} {f.get('where', '')}: {f.get('message')}")
            if report["stopped"]:
                print("Stopped: the shared design has errors. Nothing was written.")
                return 2
            conversion["built"] = report["built"]
            write_json(args.conversion, conversion)
            if args.plan:
                plans = [(pathlib.Path(p), load_json(p)) for p in args.plan]
                for line in mark_plans(conversion, plans):
                    print(line)
            print(f"wrote {len(report['written'])} files; repoint.apex and rollback.apex in {work}")
            print("Next, each step on the person's yes:")
            if report["record"]:
                print(f"  sf apex run --file {work / 'create.apex'} --target-org <org-alias>")
            if report["metadata"]:
                print(f"  sf project deploy start --manifest {work / 'package.xml'} --target-org <org-alias> --dry-run")
                print(f"  sf project deploy start --manifest {work / 'package.xml'} --target-org <org-alias>")
            print(f"  sf apex run --file {work / 'repoint.apex'} --target-org <org-alias>")
            print(f"  python3 consolidate.py roundtrip {args.conversion} --target-org <org-alias>")
            return 0
        conversion = load_json(args.conversion)
        if args.command == "roundtrip":
            rows = read_rows(roundtrip_queries(conversion), args.target_org, args.rows)
            catalog_path = (conversion.get("catalog") or {}).get("path")
            index = (load_json(catalog_path) if catalog_path and pathlib.Path(catalog_path).is_file() else {}).get("fields_index")
            mismatches, checked = roundtrip(conversion, rows, index)
            conversion["roundtrip"] = {"at": stamp(), "ok": not mismatches, "mismatches": mismatches,
                                       "digest": conversion_digest(conversion)}
            write_json(args.conversion, conversion)
            report = pathlib.Path(args.conversion).resolve().parent / "roundtrip.md"
            report.write_text("# Round trip\n\n" + (f"{checked} sections checked: every template asks the same questions, "
                              "apart from the changes you approved.\n" if not mismatches else
                              "\n".join(f"- {m}" for m in mismatches) + "\n"), encoding="utf-8")
            print(report.read_text(encoding="utf-8"))
            return 5 if mismatches else 0
        if args.command == "cleanup":
            done = conversion.get("roundtrip") or {}
            if not done.get("ok") or done.get("digest") != conversion_digest(conversion):
                raise ConsolidateError("the round trip has not passed for this consolidation: run roundtrip first", 3)
            rows = read_rows(cleanup_queries(conversion), args.target_org, args.rows)
            result = cleanup_plan(conversion, rows)
            work = pathlib.Path(args.conversion).resolve().parent
            if not result["strip"] and not result["delete"]:
                print("Nothing to clean up." + (" Still in use: " + ", ".join(k["name"] for k in result["keep"]) if result["keep"] else ""))
                return 0
            (work / "cleanup.apex").write_text(cleanup_apex(conversion, result), encoding="utf-8")
            for s in result["strip"]:
                print(f"remove the old JSON kept on {s['where']}")
            for d in result["delete"]:
                print(f"delete the record component {d['name']} (was {d['where']}); nothing uses it any more")
            for k in result["keep"]:
                print(f"keep {k['name']}: still used by {', '.join(k['still_used_by'])}")
            print(f"Wrote {work / 'cleanup.apex'}. Run it only on the person's yes:")
            print(f"  sf apex run --file {work / 'cleanup.apex'} --target-org <org-alias>")
            return 0
    except ConsolidateError as error:
        print(f"consolidate: {error}", file=sys.stderr)
        return error.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
