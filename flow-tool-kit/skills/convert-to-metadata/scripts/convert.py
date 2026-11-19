#!/usr/bin/env python3
"""Convert a prototyped Form Template's record components and JSON sections into metadata components.

Only the pieces built for this form are converted: record components (Form Component records of record type Record
Component) that build-template's records mode built in place of planned metadata ones (its report's convert_later and
the plan's components[].built_shape marks; without those, the ones the plan made new or extended), and sections that
carry their own JSON. Components the template only
references (existing metadata components, and record components the reuse question answered "reuse") are left alone.

Commands, in the order a conversion runs them:
    queries   --template <Id or Name> | --snapshot snapshot.json   the SOQL a snapshot needs (for a chat connector)
    snapshot  --template <Id or Name> --target-org <org-alias> --out snapshot.json   read the org with the Salesforce CLI
    plan      --snapshot snapshot.json [--plan plan.json] [--build-report report.json] [--catalog catalog.json]
              [--include NAME] [--exclude NAME|SECTION_ID] [--rename OLD=NEW] --out conversion.json   the dry run
    confirm   conversion.json        record that the person approved this exact dry run
    build     conversion.json --out <project customMetadata folder> [--overwrite] [--clear-managers] [--clear-prefill]
              writes the metadata files, package.xml, labels.xml, repoint.apex and rollback.apex
    verify    conversion.json --target-org <org-alias> | --rows rows.json   the deployed components are in the org
    cleanup   conversion.json --target-org <org-alias> | --places places.json   the separate, later step: which
              original record components nothing uses any more, and cleanup.apex to delete them

Nothing here deploys, updates or deletes anything by itself: the deploy, the repoint and the cleanup are Salesforce CLI
commands the person approves (printed by each step). Python 3 standard library only.

Exit codes: 0 done; 1 an error; 2 the dry run found a problem that blocks the conversion; 3 not confirmed, or the
conversion changed after it was confirmed; 4 files in the project would change (rerun with --overwrite once the person
agrees); 5 verify found a component missing or incomplete in the org.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
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
CHILD_TYPES = ("Form_Section", "Form_Field", "Form_Conditional_Logic", "Form_Conditional_Logic_Condition")
ALL_TYPES = ("Form",) + CHILD_TYPES
TYPE_WORDS = {"Form": "form", "Form_Section": "section", "Form_Field": "field", "Form_Conditional_Logic": "rule",
              "Form_Conditional_Logic_Condition": "condition"}
# Page section types that draw no form component.
NON_FORM_TYPES = {"Flow", "Lightning Web Component", "Display Text"}
# Columns that name the component a place draws. The first is the section's own form.
SECTION_NAME_COLUMNS = ["FormQualifiedApiName__c", "Alternate_FormQualifiedApiName__c", "Bulk_FormQualifiedApiName__c",
                        "Edit_FormQualifiedApiName__c"]
TEMPLATE_NAME_COLUMNS = ["FormQualifiedApiName_Header__c", "FormQualifiedApiName_Footer__c"]
# Keys inside a component JSON that point at another component by name.
COMPONENT_REF_KEYS = {"formComponent__c", "referenceFormComponent__c", "Default_Table_Form__c", "Default_Table_Form_bulk__c"}
# Record plumbing a record component's stored JSON carries and metadata never does: Ids, versions, parent pointers
# (the metadata writer sets parents itself) and relationship objects.
RECORD_ONLY = {"Id", "_Id", "_joined", "attributes", "RecordTypeId", "RecordType", "OwnerId", "Name", "IsDeleted",
               "CreatedById", "CreatedDate", "LastModifiedById", "LastModifiedDate", "SystemModstamp",
               "Version__c", "VersionId__c", "QualifiedApiName__c", "SystemModstamp__c", "FormConfigJSON__c",
               "Has_Submission_Map__c", "Form_Component__c", "Form_Component_Section__c",
               "Form_Component_Conditional_Logic__c", "Form__c", "Form_Section__c", "Labels__r", "Translations__r",
               "Themes__r", "Form__r", "Form_Section__r", "Form_Component__r", "conditionalLogic__r", "fieldName__r",
               "Object__r", "Theme__r"}
CHILD_LISTS = {"sections__r": "Form_Section", "fields__r": "Form_Field", "conditionalLogic__r": "Form_Conditional_Logic",
               "conditions__r": "Form_Conditional_Logic_Condition"}
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
LABEL_RE = re.compile(r"\{\{\s*\$Label\.(\w+)\s*\}\}")
RECORD_REF = re.compile(r"^(\w+)_v0$")
NO_COLUMN_RE = re.compile(r"No such column '([^']+)'")
RECORD_ID = re.compile(r"^[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?$")
ORG_FIELD_ID = re.compile(r"^00N[a-zA-Z0-9]{12}|\.00N")
CLEAN_DECISIONS = {"extend", "shared-new", "shared-record", "form-only"}
REFERENCE_DECISIONS = {"reuse", "update"}


class ConvertError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


# ---- small helpers ---------------------------------------------------------------------------------------------------

def local(key):
    """A key without its namespace: '*__title__c' and 'FlowToolKit__title__c' both become 'title__c'."""
    for prefix in (STAR, NS):
        if isinstance(key, str) and key.startswith(prefix):
            return key[len(prefix):]
    return key


def get(node, name, default=None):
    for key in (STAR + name, NS + name, name):
        if isinstance(node, dict) and key in node:
            return node[key]
    return default


def col(row, name, default=None):
    """A column from a query row, written with or without the package prefix."""
    return get(row, name, default)


def bare(name):
    name = (name or "").replace(STAR, NS)
    return name[len(NS):] if name.startswith(NS) else name


def parse_json(text):
    if isinstance(text, (dict, list)):
        return text
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConvertError(f"cannot read {path}: {error}")


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def pascal_snake(text, limit=40):
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    name = "_".join(w[:1].upper() + w[1:] for w in words)
    if name and not name[0].isalpha():
        name = "Form_" + name
    return shorten(name, limit)


def shorten(name, limit=40):
    """Cut a name at a word boundary to fit a custom metadata record name (40 characters)."""
    if len(name) <= limit:
        return name
    cut = name[:limit]
    if "_" in cut[limit // 2:]:
        cut = cut[:cut.rindex("_")]
    return cut.rstrip("_")


def soql_str(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def soql_list(values):
    return "(" + ", ".join(soql_str(v) for v in sorted(values)) + ")"


def apex_str(value):
    """An Apex string expression for any text, split so no single literal is very long."""
    if value is None:
        return "null"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n")
    parts = [text[i:i + 2000] for i in range(0, len(text), 2000)] or [""]
    return " + ".join(f"'{p}'" for p in parts)


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---- reading a page section the way the package does ------------------------------------------------------------------

def section_source(section):
    """What a page section draws, decided as the package decides it: the section's FormConfigJSON__c wrapper first,
    then the FormQualifiedApiName__c column. Returns {kind: metadata|record|json|none, name, json, object, wrapper}."""
    kind_of_section = col(section, "Component_Type__c") or "Field Set"
    if kind_of_section in NON_FORM_TYPES:
        return {"kind": "none", "why": kind_of_section}
    raw = (col(section, "FormConfigJSON__c") or "").strip()
    column = col(section, "FormQualifiedApiName__c")
    wrapper = parse_json(raw) if raw else None
    wrapper = wrapper if isinstance(wrapper, dict) else None
    mode = wrapper.get("formSelectionMode") if wrapper else None
    obj = wrapper.get("object") if wrapper else None
    if raw and mode == "component":
        name = wrapper.get("formQualifiedApiName") or column
    elif raw:
        inner = wrapper.get("formJsonConfig") if wrapper and "formSelectionMode" in wrapper else raw
        return {"kind": "json", "json": parse_json(inner), "raw": inner, "object": obj, "wrapper": wrapper}
    else:
        name = column
    if not name:
        return {"kind": "none", "why": "no form"}
    return {"kind": "record" if RECORD_REF.match(name) else "metadata", "name": name, "object": obj}


# ---- the snapshot: what is read from the org ---------------------------------------------------------------------------

SECTION_COLUMNS = ["Id", "LastModifiedDate", f"{NS}Form_Template_Page__c", f"{NS}Position__c", f"{NS}Title__c",
                   f"{NS}Header_Title__c", f"{NS}Component_Type__c", f"{NS}FormConfigJSON__c",
                   f"{NS}Form_Component__c", f"{NS}Form_Component__r.RecordType.DeveloperName"] + \
                  [NS + c for c in SECTION_NAME_COLUMNS]
OPTIONAL_COLUMNS = {f"{NS}Edit_FormQualifiedApiName__c", f"{NS}Bulk_FormQualifiedApiName__c"}
COMPONENT_COLUMNS = ["Id", f"{NS}QualifiedApiName__c", f"{NS}VersionId__c", f"{NS}Label__c", f"{NS}Active__c",
                     f"{NS}ObjectApiName__c", f"{NS}FormConfigJSON__c", "RecordType.DeveloperName"]


def template_queries(template):
    is_id = re.fullmatch(r"[a-zA-Z0-9]{15}|[a-zA-Z0-9]{18}", template) and re.search(r"\d", template)
    where = f"Id = {soql_str(template)}" if is_id else f"Name = {soql_str(template)}"
    return [
        {"key": "org", "soql": "SELECT Id, Name, NamespacePrefix, IsSandbox FROM Organization"},
        {"key": "template", "soql": f"SELECT Id, Name, LastModifiedDate, {NS}FormQualifiedApiName_Header__c, "
                                    f"{NS}FormQualifiedApiName_Footer__c FROM {NS}Form_Template__c WHERE {where}"},
    ]


def page_queries(template_id):
    return [
        {"key": "pages", "soql": f"SELECT Id, {NS}Page_Label__c, {NS}Position__c FROM {NS}Form_Template_Page__c "
                                 f"WHERE {NS}Form_Template__c = {soql_str(template_id)}"},
        {"key": "sections", "soql": f"SELECT {', '.join(SECTION_COLUMNS)} FROM {NS}Form_Template_Page_Section__c "
                                    f"WHERE {NS}Form_Template_Page__r.{NS}Form_Template__c = {soql_str(template_id)}",
         "optional": sorted(OPTIONAL_COLUMNS)},
        {"key": "form_objects", "soql": f"SELECT QualifiedApiName, NamespacePrefix, {NS}Object__c FROM {NS}Form_Object__mdt"},
    ] + [{"key": f"names:{t}", "soql": f"SELECT DeveloperName, NamespacePrefix FROM {NS}{t}__mdt"} for t in ALL_TYPES]


def record_names(snapshot):
    """Every record component name (<name>_v0) the template's places or the components already read point at."""
    names = set()
    template = snapshot.get("template") or {}
    for c in TEMPLATE_NAME_COLUMNS:
        value = col(template, c)
        if value and RECORD_REF.match(value):
            names.add(value)
    for section in snapshot.get("sections") or []:
        for c in SECTION_NAME_COLUMNS:
            value = col(section, c)
            if value and RECORD_REF.match(value):
                names.add(value)
        source = section_source(section)
        if source["kind"] == "record":
            names.add(source["name"])
        if source["kind"] == "json":
            names |= nested_record_refs(source.get("json"))
    for row in snapshot.get("components") or []:
        names |= nested_record_refs(parse_json(col(row, "FormConfigJSON__c")))
    return names


def nested_record_refs(component):
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if local(key) in COMPONENT_REF_KEYS and isinstance(value, str) and RECORD_REF.match(value):
                    found.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(component)
    return found


def follow_up_queries(snapshot):
    """The queries that depend on what the template names: its record components, every other place that uses them,
    and the Form Labels their text uses."""
    names = sorted(record_names(snapshot))
    have = {col(r, "VersionId__c") for r in snapshot.get("components") or []}
    queries = []
    missing = [n for n in names if n not in have]
    if missing:
        queries.append({"key": "components", "soql": f"SELECT {', '.join(COMPONENT_COLUMNS)} FROM {NS}Form_Component__c "
                                                     f"WHERE {NS}VersionId__c IN {soql_list(missing)}"})
    if names:
        ors = " OR ".join(f"{NS}{c} IN {soql_list(names)}" for c in SECTION_NAME_COLUMNS[:3])
        queries.append({"key": "places:sections", "soql": f"SELECT Id, {NS}Form_Template_Page__r.{NS}Form_Template__c, "
                        f"{NS}Form_Template_Page__r.{NS}Form_Template__r.Name, {NS}FormQualifiedApiName__c, "
                        f"{NS}Alternate_FormQualifiedApiName__c, {NS}Bulk_FormQualifiedApiName__c "
                        f"FROM {NS}Form_Template_Page_Section__c WHERE {ors}"})
        ors = " OR ".join(f"{NS}{c} IN {soql_list(names)}" for c in TEMPLATE_NAME_COLUMNS)
        queries.append({"key": "places:templates", "soql": f"SELECT Id, Name, {NS}FormQualifiedApiName_Header__c, "
                        f"{NS}FormQualifiedApiName_Footer__c FROM {NS}Form_Template__c WHERE {ors}"})
        queries.append({"key": "places:components", "soql": f"SELECT Id, {NS}QualifiedApiName__c, {NS}FormConfigJSON__c "
                        f"FROM {NS}Form_Component__c WHERE RecordType.DeveloperName = 'Record_Component'",
                        "keep": "rows whose FormConfigJSON__c names one of the record components above"})
    labels = set()
    for text in texts_of(snapshot):
        labels |= set(LABEL_RE.findall(text))
    if labels:
        queries.append({"key": "labels", "soql": f"SELECT DeveloperName, QualifiedApiName, NamespacePrefix "
                                                 f"FROM {NS}Form_Label__mdt WHERE DeveloperName IN {soql_list(labels)}"})
        queries.append({"key": "translations", "soql": f"SELECT QualifiedApiName, {NS}Form_Label__r.DeveloperName "
                        f"FROM {NS}Form_Label_Translation__mdt WHERE {NS}Form_Label__r.DeveloperName IN {soql_list(labels)}"})
    return queries


def texts_of(snapshot):
    for section in snapshot.get("sections") or []:
        source = section_source(section)
        if source["kind"] == "json" and source.get("raw"):
            yield source["raw"]
    for row in snapshot.get("components") or []:
        yield col(row, "FormConfigJSON__c") or ""


def run_sf(args):
    """Run an sf command with --json and return its result, or raise ConvertError with the CLI's message."""
    try:
        proc = subprocess.run(["sf"] + args + ["--json"], capture_output=True, text=True)
    except FileNotFoundError:
        raise ConvertError("The Salesforce CLI (sf) is not installed or not on the PATH. Install it and sign in to the "
                           "org, or, in chat, run the queries through the Salesforce connector (convert.py queries).")
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError:
        data = {}
    if not data:
        raise ConvertError((proc.stderr or out or "sf returned nothing").strip()[:600])
    if data.get("status", 1) != 0:
        raise ConvertError(str(data.get("message") or data.get("name") or "sf failed").strip())
    return data.get("result") or {}


class Org:
    def __init__(self, alias=None, sf=run_sf):
        self.alias, self.sf, self.dropped = alias, sf, []

    def args(self):
        return ["--target-org", self.alias] if self.alias else []

    def query(self, soql, optional=()):
        """Run a query; drop an optional column an older Flow Tool Kit version lacks, and say so."""
        while True:
            try:
                return self.sf(["data", "query", "--query", soql] + self.args()).get("records") or []
            except ConvertError as error:
                match = NO_COLUMN_RE.search(str(error))
                gone = match.group(1) if match else None
                if not gone or gone not in optional:
                    raise
                soql = soql.replace(", " + gone, "")
                self.dropped.append(gone)


def strip_attributes(rows):
    def clean(node):
        if isinstance(node, dict):
            return {k: clean(v) for k, v in node.items() if k != "attributes"}
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node
    return clean(rows)


def add_result(snapshot, key, rows, names=()):
    """Put one query's rows into the snapshot under its key."""
    rows = strip_attributes(rows)
    if key == "org":
        row = rows[0] if rows else {}
        snapshot["org"] = {"id": row.get("Id"), "name": row.get("Name"), "namespace": row.get("NamespacePrefix"),
                           "is_sandbox": row.get("IsSandbox")}
    elif key == "template":
        if len(rows) != 1:
            raise ConvertError("the template matched " + ("no Form Template" if not rows else
                               "several Form Templates: " + ", ".join(f"{r.get('Name')} ({r.get('Id')})" for r in rows)
                               + "; pass its Id"), 2)
        snapshot["template"] = rows[0]
    elif key.startswith("names:"):
        snapshot.setdefault("metadata_names", {})[key[6:]] = rows
    elif key.startswith("places:"):
        kind = key[7:]
        if kind == "components":
            rows = [{"Id": r.get("Id"), "name": col(r, "QualifiedApiName__c"),
                     "mentions": sorted(n for n in names if n in (col(r, "FormConfigJSON__c") or ""))} for r in rows]
            rows = [r for r in rows if r["mentions"]]
        snapshot.setdefault("places", {})[kind] = rows
    elif key == "components":
        snapshot["components"] = (snapshot.get("components") or []) + rows
    else:
        snapshot[key] = rows


def normalise_snapshot(raw):
    """A snapshot saved key by key from a chat connector (rows under "org", "template", "names:Form", "places:sections"
    and so on, as `queries` names them) in the shape take_snapshot writes."""
    snapshot = {k: v for k, v in raw.items() if ":" not in k and k not in ("org", "template", "components")}
    for key in ("org", "template"):
        value = raw.get(key)
        if isinstance(value, list):
            add_result(snapshot, key, value)
        elif value is not None:
            snapshot[key] = value
    snapshot["components"] = strip_attributes(raw.get("components") or [])
    names = record_names(snapshot)
    for key, rows in raw.items():
        if ":" in key:
            add_result(snapshot, key, rows, names)
    for row in (snapshot.get("places") or {}).get("components") or []:
        if "mentions" not in row:
            row["mentions"] = sorted(n for n in names if n in (col(row, "FormConfigJSON__c") or ""))
            row["name"] = row.get("name") or col(row, "QualifiedApiName__c")
    return snapshot


def take_snapshot(org, template):
    snapshot = {"snapshot_version": 1, "taken_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": "sf-cli"}
    for q in template_queries(template):
        add_result(snapshot, q["key"], org.query(q["soql"]))
    for q in page_queries(snapshot["template"]["Id"]):
        add_result(snapshot, q["key"], org.query(q["soql"], q.get("optional", ())))
    asked = set()
    while True:  # a record component can place another: follow until nothing new is named
        query = next((q for q in follow_up_queries(snapshot) if q["key"] == "components"), None)
        if query is None or query["soql"] in asked:
            break
        asked.add(query["soql"])
        add_result(snapshot, "components", org.query(query["soql"]))
    names = record_names(snapshot)
    for q in follow_up_queries(snapshot):
        if q["key"] != "components":
            add_result(snapshot, q["key"], org.query(q["soql"]), names)
    snapshot["dropped_columns"] = org.dropped
    return snapshot


# ---- the dry run --------------------------------------------------------------------------------------------------------

LETTER = {"Form_Section": "S", "Form_Field": "F", "Form_Conditional_Logic": "R", "Form_Conditional_Logic_Condition": "C"}


def normalise(node, top=True):
    """A stored design as the metadata writer takes it: record plumbing removed, every package key written *__.
    The children lists stay; a relationship object (a rule or field pointer) goes, its name is kept in the __c key."""
    if isinstance(node, list):
        return [normalise(v, False) for v in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        k = local(key)
        if k in CHILD_LISTS and isinstance(value, list):
            out[STAR + k] = normalise(value, False)
            continue
        if k in RECORD_ONLY:
            continue
        out[key if key in ("QualifiedApiName", "Label") or not key.startswith((STAR, NS)) else STAR + k] = normalise(value, False)
    field_ref = get(node, "fieldName__r")
    field = out.get(STAR + "fieldName__c")
    if isinstance(field_ref, dict) and field_ref.get("QualifiedApiName") and (not field or ORG_FIELD_ID.search(str(field))):
        out[STAR + "fieldName__c"] = field_ref["QualifiedApiName"]
    rule_ref = get(node, "conditionalLogic__r")
    if isinstance(rule_ref, dict) and rule_ref.get("QualifiedApiName") and RECORD_ID.match(str(out.get(STAR + "conditionalLogic__c") or "")):
        out[STAR + "conditionalLogic__c"] = rule_ref["QualifiedApiName"]
    return out


def resolve_rule_ids(design):
    """A saved record design can point at a rule by its record Id; metadata points by name."""
    ids = {r.get("Id"): r.get("QualifiedApiName") for r in get(design, "conditionalLogic__r") or []
           if isinstance(r, dict) and r.get("Id") and r.get("QualifiedApiName")}

    def walk(node):
        if isinstance(node, dict):
            return {k: (ids.get(v, v) if local(k) == "conditionalLogic__c" else walk(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    return walk(design) if ids else design


def design_object(component, *fallbacks):
    form_object = get(component, "Form_Object__r") or {}
    via_form_object = (get(form_object, "Object__r") or {}).get("QualifiedApiName") if isinstance(form_object, dict) else None
    for value in (get(component, "ObjectApiName__c"), via_form_object) + fallbacks:
        if value:
            return value
    return None


def rewrite_values(node, renames):
    """Every value that named an old child or a converted record component now names its new one."""
    if isinstance(node, dict):
        return {k: (v if k == "QualifiedApiName" else rewrite_values(v, renames)) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite_values(v, renames) for v in node]
    if isinstance(node, str) and node in renames:
        return renames[node]
    return node


def built_as_records(plan, report=None):
    """build-template's records mode: the components it built as record components in place of the planned metadata
    ones, from its build report's convert_later and the plan's components[].built_shape marks, as {name: decision}.
    None when neither says anything (a plan built before modes, or by hand): then the planner's own detection decides."""
    found, said = {}, False
    if report and "convert_later" in report:
        said = True
        for entry in report.get("convert_later") or []:
            if entry.get("component") and entry.get("decision") in CLEAN_DECISIONS:
                found[entry["component"]] = entry["decision"]
    for c in (plan or {}).get("components") or []:
        if c.get("built_shape") == "record" and c.get("decision") in CLEAN_DECISIONS:
            said = True
            name = (c.get("built_name") or c.get("new_name")) if c.get("decision") == "extend" else c.get("name")
            if name:
                found.setdefault(name, c["decision"])
    return found if said else None


class Planner:
    def __init__(self, snapshot, plan=None, catalog=None, include=(), exclude=(), renames=None, descriptions=None,
                 checker=None, build_report=None):
        self.s = snapshot = normalise_snapshot(snapshot)
        self.plan = plan or {}
        self.catalog = catalog or {}
        self.include, self.exclude = set(include), set(exclude)
        self.renames = dict(renames or {})
        self.descriptions = dict(descriptions or {})
        self.checker = checker
        self.template = snapshot.get("template") or {}
        self.template_id = self.template.get("Id")
        self.components = {col(r, "VersionId__c"): r for r in snapshot.get("components") or []}
        self.pages = {p.get("Id"): p for p in snapshot.get("pages") or []}
        self.problems, self.warnings = [], []
        ns = (snapshot.get("org") or {}).get("namespace") or None
        self.taken = {t: {r.get("DeveloperName") for r in (snapshot.get("metadata_names") or {}).get(t, [])
                          if (r.get("NamespacePrefix") or None) == ns} for t in ALL_TYPES}
        self.planned = {t: set() for t in ALL_TYPES}
        self.record_names = {bare(col(r, "QualifiedApiName__c") or "") for r in self.components.values()}
        self.record_names |= {c.get("name") for c in self.catalog.get("components") or [] if c.get("kind") == "record"}
        self.built = built_as_records(self.plan, build_report)
        self.used_built = set()


    # -- which record components were built for this form

    def plan_entry(self, name):
        for component in self.plan.get("components") or []:
            if component.get("decision") == "extend":
                if component.get("new_name") == name:
                    return component
                if component.get("name") == name:  # the original of an extend is referenced, never converted
                    return dict(component, decision="reuse")
            elif component.get("name") == name or component.get("new_name") == name:
                return component
        return None

    def uses_elsewhere(self, ref):
        places = self.s.get("places") or {}
        found = []
        for row in places.get("sections") or []:
            page = col(row, "Form_Template_Page__r") or {}
            if col(page, "Form_Template__c") != self.template_id and ref in [col(row, c) for c in SECTION_NAME_COLUMNS]:
                found.append("template " + str(col(col(page, "Form_Template__r") or {}, "Name") or col(page, "Form_Template__c")))
        for row in places.get("templates") or []:
            if row.get("Id") != self.template_id and ref in [col(row, c) for c in TEMPLATE_NAME_COLUMNS]:
                found.append(f"template {row.get('Name')}")
        for row in places.get("components") or []:
            if ref in row.get("mentions", []) and row.get("name") != ref[:-3]:
                found.append(f"component {row.get('name')}")
        for c in self.catalog.get("components") or []:
            if c.get("name") == ref[:-3] and c.get("kind") == "record":
                found += [f"template {u.get('template')}" for u in c.get("used_in") or []
                          if u.get("template_id") != self.template_id]
                found += [f"component {u if isinstance(u, str) else u.get('name')}" for u in c.get("used_by_components") or []]
        return sorted(set(found))

    def decide(self, ref):
        """(convert?, reason) for one record component this template uses."""
        name = ref[:-3]
        row = self.components.get(ref)
        if ref in self.exclude or name in self.exclude:
            return False, "you asked to leave it"
        if row is None:
            return False, "not found in the org: the template names a record component that does not exist"
        if (col(row, "RecordType") or {}).get("DeveloperName") not in (None, "Record_Component"):
            return False, "not a record component"
        entry = self.plan_entry(name) if self.plan else None
        decision = (entry or {}).get("decision")
        asked = ref in self.include or name in self.include
        if decision in REFERENCE_DECISIONS:
            if asked or name in (self.built or {}):
                self.problems.append(f"{name} is only referenced by this form (the plan's answer was {decision}), so it "
                                     "is never converted here, even when a list or --include names it")
            return False, f"referenced: the plan's answer was {decision}"
        if asked:
            return True, "you asked to convert it"
        elsewhere = self.uses_elsewhere(ref)
        if self.built is not None:
            if name not in self.built:
                why = "the plan chose a record component for it" if decision in CLEAN_DECISIONS else \
                    "build-template did not mark it to convert"
                return False, f"{why}; include it by name to convert it"
            self.used_built.add(name)
            if elsewhere:
                return False, (f"build-template built it for this form, but it is now also used by {', '.join(elsewhere)}; "
                               "include it by name to convert it anyway")
            return True, (f"build-template built it as a record in place of the planned metadata component "
                          f"({self.built[name]}, convert_later)")
        if self.plan:
            if decision in CLEAN_DECISIONS and elsewhere:
                return False, (f"built for this form ({decision}) but now also used by {', '.join(elsewhere)}; "
                               f"include it by name to convert it anyway")
            if decision in CLEAN_DECISIONS:
                return True, f"built for this form: the plan's answer was {decision}"
            return False, ("not in the plan" if entry is None else f"the plan's answer was {decision}") + \
                "; include it by name to convert it"
        if elsewhere:
            return False, f"referenced: also used by {', '.join(elsewhere)}"
        return True, "no plan to say so, but only this template uses it, so it looks built for this form; confirm"

    def metadata_reason(self, name):
        if name.startswith(NS):
            return "referenced: packaged, ships with Flow Tool Kit"
        decision = (self.plan_entry(name) or {}).get("decision")
        return "referenced: already metadata" + (f" (the plan's answer was {decision})" if decision else "")

    # -- names

    def free_name(self, kind, wanted, own=None):
        """A custom metadata record name of this type that neither the org nor this run already uses."""
        wanted = shorten(wanted)
        candidate, n = wanted, 2
        while candidate in self.taken[kind] or candidate in self.planned[kind] or \
                (kind == "Form" and candidate in self.record_names and candidate != own):
            candidate = shorten(wanted, 40 - len(f"_{n}")) + f"_{n}"
            n += 1
        self.planned[kind].add(candidate)
        return candidate

    def name_children(self, component, name, rename_all):
        """Give every section, field, rule and condition a free metadata record name. A JSON section's children are
        named after the new component; a record component keeps its children's names unless one is taken."""
        renames, count = {}, {t: 0 for t in CHILD_TYPES}

        def visit(node, kind):
            old = node.get("QualifiedApiName")
            count[kind] += 1
            fine = old and API_NAME.match(old) and "__" not in old and len(old) <= 40
            wanted = old if fine and not rename_all else f"{name}_{LETTER[kind]}{count[kind]}"
            new = self.free_name(kind, wanted)
            if not rename_all and old and new != old:
                self.warnings.append(f"{name}: {TYPE_WORDS[kind]} {old} becomes {new} in metadata "
                                     f"({'that name is taken' if fine else 'not a valid metadata record name'})")
            if old:
                renames[old] = new
            node["QualifiedApiName"] = new

        for section in get(component, "sections__r") or []:
            visit(section, "Form_Section")
            for field in get(section, "fields__r") or []:
                visit(field, "Form_Field")
        for rule in get(component, "conditionalLogic__r") or []:
            visit(rule, "Form_Conditional_Logic")
            for condition in get(rule, "conditions__r") or []:
                visit(condition, "Form_Conditional_Logic_Condition")
        return rewrite_values(component, renames)

    def form_object(self, obj):
        """The org's Form Object record for the component's object, the packaged one first; None when it has none."""
        found = None
        for row in self.s.get("form_objects") or []:
            value = col(row, "Object__c") or col(row, "Object__r")
            value = value.get("QualifiedApiName") if isinstance(value, dict) else value
            if bare(value or "").lower() == bare(obj).lower():
                if (row.get("NamespacePrefix") or "") == NS[:-2]:
                    return row.get("QualifiedApiName")
                found = found or row.get("QualifiedApiName")
        return found

    # -- the template

    def where(self, section):
        page = self.pages.get(col(section, "Form_Template_Page__c")) or {}
        title = col(section, "Header_Title__c") or col(section, "Title__c") or "untitled section"
        return (f"page {int(col(page, 'Position__c') or 0)} '{col(page, 'Page_Label__c') or ''}', "
                f"section {int(col(section, 'Position__c') or 0)} '{title}'")

    def run(self):
        sections = sorted(self.s.get("sections") or [], key=lambda s: (
            col(self.pages.get(col(s, "Form_Template_Page__c")) or {}, "Position__c") or 0, col(s, "Position__c") or 0))
        leave, uses = [], {}

        # 1. every place the template draws a component from
        for section in sections:
            source, here = section_source(section), self.where(section)
            if source["kind"] == "record":
                uses.setdefault(source["name"], []).append(here)
            elif source["kind"] == "metadata":
                leave.append({"name": source["name"], "shape": "metadata", "where": [here],
                              "reason": self.metadata_reason(source["name"])})
            elif source["kind"] == "json" and section.get("Id") not in self.exclude:
                for nested in nested_record_refs(source.get("json")):
                    uses.setdefault(nested, []).append(f"inside {here}")
            for c in SECTION_NAME_COLUMNS[1:]:
                value = col(section, c)
                if value and RECORD_REF.match(value):
                    uses.setdefault(value, []).append(f"{here} ({c.split('_')[0].lower()} form)")
        for c in TEMPLATE_NAME_COLUMNS:
            value, here = col(self.template, c), "the template's " + ("header" if "Header" in c else "footer")
            if value and RECORD_REF.match(value):
                uses.setdefault(value, []).append(here)
            elif value:
                leave.append({"name": value, "shape": "metadata", "where": [here], "reason": self.metadata_reason(value)})

        # 2. record components: converted only when built for this form; a converted one may place others
        converted, items, queue, seen = {}, [], sorted(uses), set()
        while queue:
            ref = queue.pop(0)
            if ref in seen:
                continue
            seen.add(ref)
            convert, reason = self.decide(ref)
            if not convert:
                leave.append({"name": ref, "shape": "record", "where": uses.get(ref, []), "reason": reason})
                continue
            row = self.components[ref]
            design = parse_json(col(row, "FormConfigJSON__c"))
            if not isinstance(design, dict):
                self.problems.append(f"{ref}: its stored design is empty or not JSON; open it in Form Builder, save it "
                                     "once, and run the dry run again")
                continue
            name = self.renames.get(ref) or self.renames.get(ref[:-3]) or ref[:-3]
            if not API_NAME.match(name) or "__" in name or len(name) > 40:
                self.problems.append(f"{ref}: {name} is not a metadata record name (letters, digits and single "
                                     f"underscores, 40 characters at most); pass --rename {ref[:-3]}=<New_Name>")
                continue
            if name in self.taken["Form"] or name in self.planned["Form"]:
                self.problems.append(f"{ref}: the org already has a metadata component named {name}, which a deploy "
                                     f"would replace; pass --rename {ref[:-3]}=<New_Name>")
                continue
            self.planned["Form"].add(name)
            converted[ref] = name
            for nested in sorted(nested_record_refs(design)):
                uses.setdefault(nested, []).append(f"inside {ref[:-3]}")
                queue.append(nested)
            items.append({"kind": "record", "source": ref, "record_id": row.get("Id"), "reason": reason,
                          "label": col(row, "Label__c") or design.get("Label") or name,
                          "object": design_object(design, col(row, "ObjectApiName__c")), "metadata_name": name,
                          "where": uses.get(ref, []), "design": design, "active": col(row, "Active__c") is not False})

        # 3. JSON sections: each is this form's own and becomes a component of its own
        for section in sections:
            source, sid, here = section_source(section), section.get("Id"), self.where(section)
            if source["kind"] != "json":
                continue
            if sid in self.exclude:
                leave.append({"name": sid, "shape": "json", "where": [here], "reason": "you asked to leave it"})
                continue
            design = source.get("json")
            if not isinstance(design, dict) or not get(design, "sections__r"):
                self.problems.append(f"{here}: its JSON is empty or not a form; fix it in the section editor, or leave it "
                                     f"with --exclude {sid}")
                continue
            title = col(section, "Header_Title__c") or col(section, "Title__c") or ""
            wanted = self.renames.get(sid) or pascal_snake(title) or \
                pascal_snake(f"{self.template.get('Name')} Section {int(col(section, 'Position__c') or 0)}")
            if not API_NAME.match(wanted) or "__" in wanted or len(wanted) > 40:
                self.problems.append(f"{here}: {wanted} is not a metadata record name; pass --rename {sid}=<Name>")
                continue
            name = self.free_name("Form", wanted)
            items.append({"kind": "json", "source": sid, "section_id": sid, "reason": "this section's own questions",
                          "label": title or name.replace("_", " "), "metadata_name": name, "where": [here],
                          "object": design_object(design, source.get("object")), "wrapper_object": source.get("object"),
                          "design": design, "note": None if name == wanted else f"named {name}: {wanted} is taken"})

        # 4. a metadata component cannot point at a record component
        for item in items:
            for nested in sorted(nested_record_refs(item["design"])):
                if nested not in converted:
                    owner = item["source"][:-3] if item["kind"] == "record" else item["source"]
                    self.problems.append(f"{item['metadata_name']} places the record component {nested}, which stays a "
                                         f"record. A metadata component cannot point at a record component: convert "
                                         f"{nested[:-3]} too (--include {nested[:-3]}), or leave this one as it is "
                                         f"(--exclude {owner})")

        # 5. the design each conversion writes: names, object, Form Object, description, labels, checks
        for item in items:
            design = item.pop("design")
            if not item["object"]:
                self.problems.append(f"{item['metadata_name']}: its design names no object; set one in Form Builder")
                continue
            component = normalise(rewrite_values(resolve_rule_ids(design), converted))
            component["QualifiedApiName"] = item["metadata_name"]
            component["Label"] = item["label"]
            component["*__ObjectApiName__c"] = item["object"]
            component["*__Active__c"] = True
            component.setdefault("*__type__c", "form")
            component.setdefault("*__CategoryTag__c", "Component(s)")
            text = self.descriptions.get(item["metadata_name"]) or self.descriptions.get(item["source"]) or \
                self.descriptions.get(item["source"][:-3] if item["kind"] == "record" else "")
            if text:
                component["*__Description__c"] = text
            item["component"] = self.name_children(component, item["metadata_name"], item["kind"] == "json")
            item["children"] = children_names(item["component"])
            fo = self.form_object(item["object"])
            item["form_object"] = {"name": fo, "new": fo is None}
            if fo is None:
                self.warnings.append(f"{item['metadata_name']}: the org has no Form Object for {item['object']}; the "
                                     "build writes one beside the component")
            item["labels"] = sorted(set(LABEL_RE.findall(json.dumps(item["component"], ensure_ascii=False))))
            if get(item["component"], "Form_Managers__c"):
                self.warnings.append(f"{item['metadata_name']}: Form Managers holds user Ids from this org; pass "
                                     "--clear-managers to the build when the component will go to another org")
            if get(item["component"], "prefill__c"):
                self.warnings.append(f"{item['metadata_name']}: it holds Form Builder preview data, often copied from a "
                                     "real record; pass --clear-prefill to the build to leave it out")
            if not item.get("active", True):
                self.warnings.append(f"{item['source']} is inactive; its metadata component is written active")
            if not get(item["component"], "Description__c"):
                self.problems.append(f"{item['metadata_name']} has no description. Write one (what it collects, where "
                                     f"the answers go) and pass --describe {item['metadata_name']}=\"<text>\"")
            if self.checker:
                for f in self.checker(item["component"]):
                    if f.get("check") == "description" and not get(item["component"], "Description__c"):
                        continue
                    line = f"{item['metadata_name']} {f.get('where', '')}: {f['message']}"
                    (self.problems if f.get("severity") == "error" else self.warnings).append(line)

        for name in sorted(set(self.built or {}) - self.used_built - {e["name"][:-3] for e in leave}):
            self.warnings.append(f"build-template built {name} as a record to convert later, but this template does not "
                                 "draw it now; nothing to convert for it here")
        repoints = self.repoints(sections, converted, items)
        if not items and not self.problems:
            self.warnings.append("nothing to convert: every component this template uses is already metadata or "
                                 "only referenced")
        if self.checker is None and items:
            self.warnings.append("the converted designs were not checked here (build-form-component's checker was not "
                                 "found); the build checks them before it writes anything")
        return {"conversion_version": 1, "taken_at": self.s.get("taken_at"), "org": self.s.get("org"),
                "template": {"id": self.template_id, "name": self.template.get("Name")},
                "convert": items, "leave": dedupe_leave(leave), "repoint": repoints, "labels": self.label_report(items),
                "dropped_columns": self.s.get("dropped_columns") or [],
                "problems": self.problems, "warnings": self.warnings, "confirmed": None}

    def repoints(self, sections, converted, items):
        out = []
        by_section = {i["section_id"]: i for i in items if i["kind"] == "json"}
        for section in sections:
            sid, source = section.get("Id"), section_source(section)
            before = {c: col(section, c) for c in SECTION_NAME_COLUMNS + ["FormConfigJSON__c", "Form_Component__c"]
                      if (NS + c) in section or c in section}
            after = {}
            item = by_section.get(sid)
            if item:
                after = {"FormQualifiedApiName__c": item["metadata_name"],
                         "FormConfigJSON__c": {"formQualifiedApiName": item["metadata_name"], "object": item["wrapper_object"]}}
            elif source["kind"] == "record" and source["name"] in converted:
                new = converted[source["name"]]
                after["FormQualifiedApiName__c"] = new
                wrapper = parse_json(col(section, "FormConfigJSON__c") or "")
                if isinstance(wrapper, dict) and wrapper.get("formSelectionMode") == "component":
                    after["FormConfigJSON__c"] = {"formQualifiedApiName": new, "object": None}
            for c in SECTION_NAME_COLUMNS[1:]:
                if col(section, c) in converted:
                    after[c] = converted[col(section, c)]
            if after and col(section, "Form_Component__c"):
                after["Form_Component__c"] = None
            if after:
                out.append({"sobject": f"{NS}Form_Template_Page_Section__c", "id": sid, "where": self.where(section),
                            "last_modified": section.get("LastModifiedDate"), "before": before, "after": after})
        after = {c: converted[col(self.template, c)] for c in TEMPLATE_NAME_COLUMNS if col(self.template, c) in converted}
        if after:
            out.append({"sobject": f"{NS}Form_Template__c", "id": self.template_id, "where": "the template's header or footer",
                        "last_modified": self.template.get("LastModifiedDate"),
                        "before": {c: col(self.template, c) for c in TEMPLATE_NAME_COLUMNS}, "after": after})
        return out

    def label_report(self, items):
        used = sorted({label for item in items for label in item.get("labels", [])})
        rows = {r.get("DeveloperName"): r for r in self.s.get("labels") or []}
        ns = (self.s.get("org") or {}).get("namespace") or None
        own = [n for n in used if n in rows and (rows[n].get("NamespacePrefix") or None) == ns]
        packaged = [n for n in used if n in rows and n not in own]
        missing = [n for n in used if n not in rows]
        translations = sorted(r.get("QualifiedApiName") for r in self.s.get("translations") or []
                              if (col(r, "Form_Label__r") or {}).get("DeveloperName") in own)
        if missing:
            self.warnings.append("not Form Labels in this org, so they show as written: " + ", ".join(missing))
        return {"own": own, "translations": translations, "packaged": packaged, "missing": missing}


def children_names(component):
    names = {t: [] for t in CHILD_TYPES}
    for section in get(component, "sections__r") or []:
        names["Form_Section"].append(section["QualifiedApiName"])
        for field in get(section, "fields__r") or []:
            names["Form_Field"].append(field["QualifiedApiName"])
    for rule in get(component, "conditionalLogic__r") or []:
        names["Form_Conditional_Logic"].append(rule["QualifiedApiName"])
        for condition in get(rule, "conditions__r") or []:
            names["Form_Conditional_Logic_Condition"].append(condition["QualifiedApiName"])
    return names


def dedupe_leave(leave):
    merged = {}
    for entry in leave:
        key = (entry["name"], entry["shape"])
        if key in merged:
            merged[key]["where"] = sorted(set(merged[key]["where"]) | set(entry["where"]))
        else:
            merged[key] = dict(entry)
    return list(merged.values())


def conversion_digest(conversion):
    """What the person approves: everything the build writes or changes."""
    return digest({k: conversion.get(k) for k in ("template", "convert", "repoint", "labels")})


def print_plan(conversion, out=None):
    out = out or sys.stdout
    w = lambda line="": print(line, file=out)
    t = conversion["template"]
    w(f"Dry run for the Form Template {t['name']} ({t['id']}). Nothing has changed in the org or the project.")
    w()
    w(f"Convert to metadata ({len(conversion['convert'])}):")
    for item in conversion["convert"]:
        what = "record component " + item["source"] if item["kind"] == "record" else "JSON section " + item["source"]
        w(f"  - {what} ({item['label']}, on {item['object']}) becomes metadata component {item['metadata_name']}")
        w(f"      why: {item['reason']}")
        w(f"      used at: {'; '.join(item['where'])}")
        for kind in CHILD_TYPES:
            names = item.get("children", {}).get(kind) or []
            if names:
                w(f"      {TYPE_WORDS[kind]}s ({len(names)}): {', '.join(names)}")
        fo = item.get("form_object") or {}
        if fo.get("new"):
            w(f"      a new Form Object for {item['object']}")
        if item.get("note"):
            w(f"      note: {item['note']}")
    w()
    w(f"Left alone ({len(conversion['leave'])}):")
    for entry in conversion["leave"]:
        w(f"  - {entry['name']} ({entry['shape']}): {entry['reason']}. Used at: {'; '.join(entry['where'])}")
    w()
    w(f"Repointed ({len(conversion['repoint'])} records):")
    for r in conversion["repoint"]:
        changes = []
        for field, value in r["after"].items():
            if field == "FormConfigJSON__c":
                changes.append(f"draws {value.get('formQualifiedApiName')} (component mode)")
            elif value is None:
                changes.append(f"{field} cleared")
            else:
                changes.append(f"{field} {r['before'].get(field) or '(blank)'} -> {value}")
        w(f"  - {r['where']} ({r['id']}): {'; '.join(changes)}")
    labels = conversion.get("labels") or {}
    if labels.get("own") or labels.get("packaged"):
        w()
        w(f"Form Labels used: {len(labels.get('own', []))} of the org's own (retrieved into the project with "
          f"{len(labels.get('translations', []))} translations), {len(labels.get('packaged', []))} packaged")
    for title, rows in (("Problems (the conversion cannot run until each is fixed)", conversion["problems"]),
                        ("Warnings", conversion["warnings"])):
        if rows:
            w()
            w(title + ":")
            for row in rows:
                w(f"  - {row}")
    if conversion.get("dropped_columns"):
        w()
        w("Columns this Flow Tool Kit version lacks, left out: " + ", ".join(conversion["dropped_columns"]))
    w()
    w("The original records stay as they are. Deleting them is a separate step, after you have checked the "
      "converted template.")


# ---- build ---------------------------------------------------------------------------------------------------------------

def load_component_module(path=None):
    """build-form-component's scripts/component.py, which writes the custom metadata record files (emit_cmt) and checks
    them (Checker). It sits beside this skill in the plugin."""
    candidates = [pathlib.Path(path)] if path else [HERE.parent.parent / "build-form-component" / "scripts" / "component.py"]
    for candidate in candidates:
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("ftk_component", candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ConvertError("build-form-component's scripts/component.py was not found beside this skill. It writes the "
                       "metadata files; install the whole Flow Tool Kit plugin, or pass --component-py <path>.")


def manifest_xml(members, api_version=None):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<Package xmlns="http://soap.sforce.com/2006/04/metadata">',
             "    <types>"]
    lines += [f"        <members>{escape(m)}</members>" for m in sorted(members)]
    lines += ["        <name>CustomMetadata</name>", "    </types>"]
    if api_version:
        lines.append(f"    <version>{escape(api_version)}</version>")
    return "\n".join(lines + ["</Package>", ""])


def build(conversion, out, module, overwrite=False, clear_managers=False, clear_prefill=False, work_dir=None):
    """Write the metadata files into the project folder and the deploy, label, repoint and rollback files beside the
    conversion. Returns a report dict."""
    confirmed = conversion.get("confirmed") or {}
    if not confirmed or confirmed.get("digest") != conversion_digest(conversion):
        raise ConvertError("this dry run has not been confirmed, or it changed after it was: show it to the person, "
                           "and run confirm only after they agree", 3)
    if conversion.get("problems"):
        raise ConvertError("the dry run lists problems; fix them and run the dry run again", 2)
    out, work = pathlib.Path(out), pathlib.Path(work_dir or ".")
    files, findings, members = {}, [], set()
    for item in conversion["convert"]:
        component = copy.deepcopy(item["component"])
        for key, flag in (("Form_Managers__c", clear_managers), ("prefill__c", clear_prefill)):
            if flag:
                for k in (STAR + key, NS + key, key):
                    component.pop(k, None)
        write_json(work / "components" / f"{item['metadata_name']}.json", component)
        for f in module.Checker(path="metadata").run(component):
            findings.append(dict(f, component=item["metadata_name"]))
        fo = item.get("form_object") or {}
        emitted, renamed = module.emit_cmt(component, fo.get("name"), bool(fo.get("new")))
        if renamed:
            raise ConvertError(f"{item['metadata_name']}: the metadata writer renamed {renamed}; run the dry run again")
        files.update(emitted)
    errors = [f for f in findings if f.get("severity") == "error"]
    if errors:
        return {"written": [], "findings": findings, "stopped": True}
    conflicts, same = [], []
    for name, text in files.items():
        target = out / name
        if target.is_file():
            if target.read_text(encoding="utf-8") == text:
                same.append(name)
            else:
                conflicts.append(name)
        members.add(name[:-len(".md-meta.xml")])
    if conflicts and not overwrite:
        raise ConvertError("these files are already in the project and differ: " + ", ".join(sorted(conflicts))
                           + ". Nothing was written. Rerun with --overwrite once the person agrees", 4)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in sorted(files.items()):
        if name not in same:
            (out / name).write_text(text, encoding="utf-8")
            written.append(name)
    (work / "package.xml").write_text(manifest_xml(members), encoding="utf-8")
    labels = conversion.get("labels") or {}
    label_members = [f"{NS}Form_Label.{bare(n)}" for n in labels.get("own", [])] + \
                    [f"{NS}Form_Label_Translation.{bare(n)}" for n in labels.get("translations", [])]
    if label_members:
        (work / "labels.xml").write_text(manifest_xml(label_members), encoding="utf-8")
    (work / "repoint.apex").write_text(repoint_apex(conversion), encoding="utf-8")
    (work / "rollback.apex").write_text(rollback_apex(conversion), encoding="utf-8")
    return {"written": written, "unchanged": same, "members": sorted(members), "findings": findings, "stopped": False,
            "labels": bool(label_members)}


# ---- repoint, rollback, cleanup (Apex the person runs) ---------------------------------------------------------------

def _stamp(value):
    return (value or "")[:19]


def repoint_apex(conversion):
    """All or nothing: stops, changing nothing, when a record changed after the dry run or a metadata component is not
    in the org."""
    names = sorted(i["metadata_name"] for i in conversion["convert"])
    lines = [f"// Repoint the Form Template {conversion['template']['name']} at its new metadata components.",
             "// Written by convert-to-metadata. Run it only after the deploy and verify step.",
             f"Set<String> forms = new Set<String>{{{', '.join(apex_str(n) for n in names)}}};",
             f"List<{NS}Form__mdt> found = [SELECT QualifiedApiName FROM {NS}Form__mdt WHERE QualifiedApiName IN :forms];",
             "if (found.size() != forms.size()) throw new IllegalArgumentException('Not every new metadata component is in "
             "this org yet. Deploy and verify first. Nothing was changed.');"]
    for sobject in (f"{NS}Form_Template_Page_Section__c", f"{NS}Form_Template__c"):
        rows = [r for r in conversion["repoint"] if r["sobject"] == sobject]
        if not rows:
            continue
        var = "sections" if "Section" in sobject else "templates"
        fields = sorted({f for r in rows for f in r["after"]})
        lines.append(f"Map<Id, String> {var}Stamp = new Map<Id, String>{{"
                     + ", ".join(f"{apex_str(r['id'])} => {apex_str(_stamp(r['last_modified']))}" for r in rows) + "};")
        lines.append(f"List<{sobject}> {var} = [SELECT Id, LastModifiedDate, {', '.join(NS + f for f in fields)} "
                     f"FROM {sobject} WHERE Id IN :{var}Stamp.keySet()];")
        lines.append(f"if ({var}.size() != {var}Stamp.size()) throw new IllegalArgumentException('A record in the dry "
                     "run is gone. Run the dry run again. Nothing was changed.');")
        lines.append(f"for ({sobject} row : {var}) {{")
        lines.append(f"    if (row.LastModifiedDate.formatGmt('yyyy-MM-dd\\'T\\'HH:mm:ss') != {var}Stamp.get(row.Id)) "
                     "throw new IllegalArgumentException('Record ' + row.Id + ' changed after the dry run. Run the "
                     "dry run again. Nothing was changed.');")
        lines.append("}")
        for r in rows:
            lines.append(f"for ({sobject} row : {var}) if (row.Id == {apex_str(r['id'])}) {{")
            for field, value in r["after"].items():
                if field == "FormConfigJSON__c":
                    lines.append(f"    Map<String, Object> wrapper = new Map<String, Object>();")
                    lines.append(f"    Object parsed = String.isBlank(row.{NS}FormConfigJSON__c) ? null : "
                                 f"JSON.deserializeUntyped(row.{NS}FormConfigJSON__c);")
                    lines.append("    if (parsed instanceof Map<String, Object> && ((Map<String, Object>) parsed)"
                                 ".containsKey('formSelectionMode')) wrapper = (Map<String, Object>) parsed;")
                    lines.append(f"    else if (parsed != null) wrapper.put('formJsonConfig', row.{NS}FormConfigJSON__c);")
                    lines.append("    wrapper.put('formSelectionMode', 'component');")
                    lines.append(f"    wrapper.put('formQualifiedApiName', {apex_str(value['formQualifiedApiName'])});")
                    if value.get("object"):
                        lines.append(f"    wrapper.put('object', {apex_str(value['object'])});")
                    lines.append(f"    row.{NS}FormConfigJSON__c = JSON.serialize(wrapper);")
                else:
                    lines.append(f"    row.{NS}{field} = {apex_str(value)};")
            lines.append("}")
        lines.append(f"update {var};")
    lines.append("System.debug('Repointed ' + " + str(len(conversion["repoint"])) + " + ' records.');")
    return "\n".join(lines) + "\n"


def rollback_apex(conversion):
    lines = [f"// Put the Form Template {conversion['template']['name']} back as it was before the repoint.",
             "// Written by convert-to-metadata. The metadata components stay in the org; only the places change back."]
    for r in conversion["repoint"]:
        var = "s" + r["id"]
        lines.append(f"{r['sobject']} {var} = new {r['sobject']}(Id = {apex_str(r['id'])});")
        for field in r["after"]:
            lines.append(f"{var}.{NS}{field} = {apex_str(r['before'].get(field))};")
        lines.append(f"update {var};")
    return "\n".join(lines) + "\n"


def cleanup_plan(conversion, places, component_mentions=()):
    """Which converted record components nothing uses any more. places: rows of sections and templates that still
    name <name>_v0 or the record Id; component_mentions: other record components whose design names it."""
    delete, keep = [], []
    for item in conversion["convert"]:
        if item["kind"] != "record":
            continue
        ref, rid = item["source"], item["record_id"]
        users = []
        for row in places.get("sections") or []:
            if ref in [col(row, c) for c in SECTION_NAME_COLUMNS] or col(row, "Form_Component__c") == rid:
                users.append(f"section {row.get('Id')}")
        for row in places.get("templates") or []:
            if ref in [col(row, c) for c in TEMPLATE_NAME_COLUMNS]:
                users.append(f"template {row.get('Name') or row.get('Id')}")
        for row in component_mentions:
            if ref in row.get("mentions", []) and row.get("Id") != rid:
                users.append(f"component {row.get('name')}")
        entry = {"name": ref, "record_id": rid, "metadata_name": item["metadata_name"]}
        if users:
            keep.append(dict(entry, still_used_by=sorted(set(users))))
        else:
            delete.append(entry)
    return {"delete": delete, "keep": keep}


def cleanup_apex(conversion, plan):
    ids = [d["record_id"] for d in plan["delete"]]
    names = [d["name"] for d in plan["delete"]]
    cols = " OR ".join(f"{NS}{c} IN :names" for c in SECTION_NAME_COLUMNS[:3]) + f" OR {NS}Form_Component__c IN :ids"
    return "\n".join([
        f"// Delete the original record components of {conversion['template']['name']} that nothing uses any more.",
        "// Written by convert-to-metadata. Run it only after the person has checked the converted template and said yes.",
        f"Set<Id> ids = new Set<Id>{{{', '.join(apex_str(i) for i in ids)}}};",
        f"Set<String> names = new Set<String>{{{', '.join(apex_str(n) for n in names)}}};",
        f"Integer sections = [SELECT COUNT() FROM {NS}Form_Template_Page_Section__c WHERE {cols}];",
        f"Integer templates = [SELECT COUNT() FROM {NS}Form_Template__c WHERE {NS}FormQualifiedApiName_Header__c IN :names "
        f"OR {NS}FormQualifiedApiName_Footer__c IN :names];",
        "if (sections + templates > 0) throw new IllegalArgumentException('A template still uses one of these record "
        "components. Nothing was deleted.');",
        f"List<{NS}Form_Component__c> rows = [SELECT Id FROM {NS}Form_Component__c WHERE Id IN :ids "
        "AND RecordType.DeveloperName = 'Record_Component'];",
        "if (rows.size() != ids.size()) throw new IllegalArgumentException('A record is missing or is not a record "
        "component. Nothing was deleted.');",
        "delete rows;",
        "System.debug('Deleted ' + rows.size() + ' record components with their sections, fields and rules.');",
    ]) + "\n"


# ---- verify -------------------------------------------------------------------------------------------------------------

def verify_queries(conversion):
    names = sorted(i["metadata_name"] for i in conversion["convert"])
    return [
        {"key": "Form", "soql": f"SELECT QualifiedApiName, {NS}Active__c FROM {NS}Form__mdt WHERE QualifiedApiName IN {soql_list(names)}"},
        {"key": "Form_Section", "soql": f"SELECT QualifiedApiName, {NS}Form__r.QualifiedApiName FROM {NS}Form_Section__mdt "
                                        f"WHERE {NS}Form__r.QualifiedApiName IN {soql_list(names)}"},
        {"key": "Form_Field", "soql": f"SELECT QualifiedApiName, {NS}Form__r.QualifiedApiName FROM {NS}Form_Field__mdt "
                                      f"WHERE {NS}Form__r.QualifiedApiName IN {soql_list(names)}"},
        {"key": "Form_Conditional_Logic", "soql": f"SELECT QualifiedApiName, {NS}Form__r.QualifiedApiName FROM "
                                                  f"{NS}Form_Conditional_Logic__mdt WHERE {NS}Form__r.QualifiedApiName IN {soql_list(names)}"},
    ] if names else []


def verify(conversion, rows):
    """rows: {key: query rows} from verify_queries. Returns a list of problems (empty when every component is whole)."""
    problems = []
    forms = {r.get("QualifiedApiName"): r for r in rows.get("Form") or []}
    for item in conversion["convert"]:
        name = item["metadata_name"]
        if name not in forms:
            problems.append(f"{name} is not in the org")
            continue
        if col(forms[name], "Active__c") is False:
            problems.append(f"{name} is in the org but inactive")
        for kind in ("Form_Section", "Form_Field", "Form_Conditional_Logic"):
            have = {r.get("QualifiedApiName") for r in rows.get(kind) or []
                    if (col(r, "Form__r") or {}).get("QualifiedApiName") == name}
            missing = sorted(set(item["children"].get(kind) or []) - have)
            if missing:
                problems.append(f"{name}: {len(missing)} {TYPE_WORDS[kind]}(s) missing in the org: {', '.join(missing)}")
    return problems


# ---- commands -----------------------------------------------------------------------------------------------------------

def parse_renames(values, option="--rename"):
    renames = {}
    for value in values or []:
        if "=" not in value:
            raise ConvertError(f"{option} takes NAME=VALUE, not {value!r}")
        old, new = value.split("=", 1)
        renames[old.strip()] = new.strip()
    return renames


def command_queries(args):
    if args.snapshot:
        queries = follow_up_queries(load_json(args.snapshot))
    else:
        queries = template_queries(args.template) + [{"key": "then", "soql": "run convert.py queries --snapshot <file> "
                                                      "for the page, section, component, place and label queries"}]
    print(json.dumps(queries, indent=1))
    return 0


def command_snapshot(args):
    snapshot = take_snapshot(Org(args.target_org), args.template)
    write_json(args.out, snapshot)
    print(f"wrote {args.out}: {len(snapshot.get('sections') or [])} sections, {len(snapshot.get('components') or [])} "
          f"record components")
    return 0


def command_plan(args):
    snapshot = load_json(args.snapshot)
    plan = load_json(args.plan) if args.plan else None
    catalog = load_json(args.catalog) if args.catalog else None
    try:
        module = load_component_module(args.component_py)
        checker = lambda component: module.Checker(path="metadata").run(component)
    except ConvertError:
        checker = None
    report = load_json(args.build_report) if args.build_report else None
    conversion = Planner(snapshot, plan, catalog, args.include, args.exclude, parse_renames(args.rename),
                         parse_renames(args.describe, "--describe"), checker, report).run()
    write_json(args.out, conversion)
    if args.json:
        print(json.dumps(conversion, indent=1, ensure_ascii=False))
    else:
        print_plan(conversion)
        print(f"\nWritten to {args.out}.")
    return 2 if conversion["problems"] else 0


def command_confirm(args):
    conversion = load_json(args.conversion)
    if conversion.get("problems"):
        print("error: the dry run lists problems; it cannot be confirmed", file=sys.stderr)
        return 2
    conversion["confirmed"] = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "digest": conversion_digest(conversion)}
    write_json(args.conversion, conversion)
    print(f"confirmed {len(conversion['convert'])} conversions and {len(conversion['repoint'])} repoints")
    return 0


def command_build(args):
    conversion = load_json(args.conversion)
    module = load_component_module(args.component_py)
    work = pathlib.Path(args.conversion).resolve().parent
    report = build(conversion, args.out, module, args.overwrite, args.clear_managers, args.clear_prefill, work)
    for f in report["findings"]:
        print(f"  {f['severity']}: {f['component']} {f.get('where', '')}: {f['message']}")
    if report["stopped"]:
        print("Stopped: the checker found errors in the converted design. Nothing was written to the project.")
        return 2
    print(f"wrote {len(report['written'])} metadata files to {args.out}" +
          (f" ({len(report['unchanged'])} already the same)" if report["unchanged"] else ""))
    print(f"wrote package.xml, repoint.apex and rollback.apex{', labels.xml' if report['labels'] else ''} to {work}")
    print("Next, with the person's yes for each:")
    print(f"  sf project deploy start --manifest {work / 'package.xml'} --target-org <org-alias> --dry-run")
    print(f"  sf project deploy start --manifest {work / 'package.xml'} --target-org <org-alias>")
    if report["labels"]:
        print(f"  sf project retrieve start --manifest {work / 'labels.xml'} --target-org <org-alias>")
    print(f"  python3 convert.py verify {args.conversion} --target-org <org-alias>")
    print(f"  sf apex run --file {work / 'repoint.apex'} --target-org <org-alias>")
    return 0


def command_verify(args):
    conversion = load_json(args.conversion)
    if args.rows:
        rows = load_json(args.rows)
    else:
        org = Org(args.target_org)
        rows = {q["key"]: strip_attributes(org.query(q["soql"])) for q in verify_queries(conversion)}
    problems = verify(conversion, rows)
    for p in problems:
        print(f"  missing: {p}")
    if problems:
        print("Do not repoint the template yet: deploy again, or read the deploy's errors.")
        return 5
    print(f"All {len(conversion['convert'])} metadata components are in the org with every section, field and rule. "
          "Reset Form Cache in Form Builder, then run repoint.apex.")
    return 0


def command_cleanup(args):
    conversion = load_json(args.conversion)
    refs = sorted(i["source"] for i in conversion["convert"] if i["kind"] == "record")
    ids = sorted(i["record_id"] for i in conversion["convert"] if i["kind"] == "record")
    if not refs:
        print("No record components were converted; there is nothing to delete. JSON sections leave no records behind.")
        return 0
    if args.places:
        data = load_json(args.places)
        places, mentions = data, data.get("components") or []
    else:
        org = Org(args.target_org)
        ors = " OR ".join(f"{NS}{c} IN {soql_list(refs)}" for c in SECTION_NAME_COLUMNS[:3])
        places = {"sections": strip_attributes(org.query(
                      f"SELECT Id, {', '.join(NS + c for c in SECTION_NAME_COLUMNS[:3])}, {NS}Form_Component__c FROM "
                      f"{NS}Form_Template_Page_Section__c WHERE {ors} OR {NS}Form_Component__c IN {soql_list(ids)}")),
                  "templates": strip_attributes(org.query(
                      f"SELECT Id, Name, {NS}FormQualifiedApiName_Header__c, {NS}FormQualifiedApiName_Footer__c FROM "
                      f"{NS}Form_Template__c WHERE {NS}FormQualifiedApiName_Header__c IN {soql_list(refs)} OR "
                      f"{NS}FormQualifiedApiName_Footer__c IN {soql_list(refs)}"))}
        rows = org.query(f"SELECT Id, {NS}QualifiedApiName__c, {NS}FormConfigJSON__c FROM {NS}Form_Component__c "
                         "WHERE RecordType.DeveloperName = 'Record_Component'")
        mentions = [{"Id": r.get("Id"), "name": col(r, "QualifiedApiName__c"),
                     "mentions": [n for n in refs if n in (col(r, "FormConfigJSON__c") or "")]} for r in rows]
    result = cleanup_plan(conversion, places, mentions)
    work = pathlib.Path(args.conversion).resolve().parent
    write_json(work / "cleanup.json", result)
    for d in result["delete"]:
        print(f"  can delete: {d['name']} ({d['record_id']}), now metadata component {d['metadata_name']}")
    for k in result["keep"]:
        print(f"  keep: {k['name']}, still used by {', '.join(k['still_used_by'])}")
    if result["delete"]:
        (work / "cleanup.apex").write_text(cleanup_apex(conversion, result), encoding="utf-8")
        print(f"After the person says yes: sf apex run --file {work / 'cleanup.apex'} --target-org <org-alias>")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queries", help="the SOQL a snapshot needs, for a chat connector")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("--template")
    g.add_argument("--snapshot")
    q.set_defaults(func=command_queries)
    s = sub.add_parser("snapshot", help="read the template and its components with the Salesforce CLI")
    s.add_argument("--template", required=True, help="the Form Template's Id or Name")
    s.add_argument("--target-org")
    s.add_argument("--out", required=True)
    s.set_defaults(func=command_snapshot)
    p = sub.add_parser("plan", help="the dry run")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--plan", help="form-design's plan.json, which says what was built for this form")
    p.add_argument("--catalog", help="org-catalog's catalog.json")
    p.add_argument("--build-report", help="build-template's build report (its convert_later list)")
    p.add_argument("--include", action="append", default=[], help="convert this record component too")
    p.add_argument("--exclude", action="append", default=[], help="leave this record component or JSON section")
    p.add_argument("--rename", action="append", default=[], help="OLD=NEW: a record component's or section Id's metadata name")
    p.add_argument("--describe", action="append", default=[], help="NAME=TEXT: the description a converted component gets")
    p.add_argument("--component-py", help="build-form-component's scripts/component.py, when it is not beside this skill")
    p.add_argument("--out", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_plan)
    c = sub.add_parser("confirm", help="record the person's yes to this exact dry run")
    c.add_argument("conversion")
    c.set_defaults(func=command_confirm)
    b = sub.add_parser("build", help="write the metadata files and the deploy, repoint and rollback files")
    b.add_argument("conversion")
    b.add_argument("--out", required=True, help="the project's customMetadata folder")
    b.add_argument("--overwrite", action="store_true")
    b.add_argument("--clear-managers", action="store_true")
    b.add_argument("--clear-prefill", action="store_true")
    b.add_argument("--component-py", help="build-form-component's scripts/component.py, when it is not beside this skill")
    b.set_defaults(func=command_build)
    v = sub.add_parser("verify", help="check the deployed components are in the org, whole")
    v.add_argument("conversion")
    v.add_argument("--target-org")
    v.add_argument("--rows", help="the verify queries' rows as JSON (chat)")
    v.set_defaults(func=command_verify)
    k = sub.add_parser("cleanup", help="the separate step: which original record components can be deleted")
    k.add_argument("conversion")
    k.add_argument("--target-org")
    k.add_argument("--places", help="fresh place rows as JSON (chat)")
    k.set_defaults(func=command_cleanup)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConvertError as error:
        print(f"error: {error}", file=sys.stderr)
        return error.code


if __name__ == "__main__":
    raise SystemExit(main())
