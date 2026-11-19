"""Pull one Form Template from an org into an export file the adapter reads.

    python3 -m formmigrate.sources.formtemplate.extract --template <Id or Name> \
        --org <alias> --out _forms/formtemplate-<slug>/template-export.json

Read-only: SOQL and describes only, through the Salesforce CLI. Needs Claude
Code (local or web) with the CLI connected to the org. In chat, read the same
records through a Salesforce connector and save them in this export's shape.

It reuses the field-audit org helpers (the ``fieldaudit`` package) in place, from
the field-audit skill of this same plugin, found by ``_shared/lib/siblings.py``
whether its folder is called ``field-audit`` or ``<plugin name>:field-audit``. This
extract runs only where the Salesforce CLI runs (Claude Code), and there the plugin
is installed whole.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

_SKILL = pathlib.Path(__file__).resolve().parents[4]
if str(_SKILL / "_shared" / "lib") not in sys.path:
    sys.path.insert(0, str(_SKILL / "_shared" / "lib"))
try:
    import siblings  # noqa: E402
except ImportError:
    raise SystemExit("This skill's _shared/lib/siblings.py is missing: install the whole Flow Tool Kit plugin.")
try:
    _FOUND = siblings.find(str(_SKILL), "field-audit", subdir="scripts", markers=["fieldaudit"])
except siblings.NotFound as _missing:
    raise SystemExit("The field-audit org helpers (fieldaudit) were not found. %s" % _missing)
if _FOUND not in sys.path:
    sys.path.insert(0, _FOUND)

from fieldaudit import NAMESPACE as N  # noqa: E402
from fieldaudit import org as org_module  # noqa: E402
from fieldaudit import walk  # noqa: E402
from fieldaudit.names import fold_star  # noqa: E402

_SKIP_TYPES = {"address", "location"}


def _all_columns(sobject: str, org: str | None) -> list[str]:
    describe = org_module.describe_fields(sobject, org)
    return [name for name, entry in describe.items()
            if entry.get("type") not in _SKIP_TYPES and (name.endswith("__c") or name in ("Id", "Name"))]


def _config(row: dict) -> dict:
    try:
        parsed = json.loads(row.get(N + "config__c") or "{}")
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _key(config: dict, key: str):
    for candidate in (N + key, "*__" + key, key):
        if config.get(candidate) not in (None, ""):
            return config[candidate]
    return None


def _soql_list(values) -> str:
    return ",".join("'" + str(v).replace("'", "\\'") + "'" for v in sorted(set(values)))


def _find_template(reference: str, org: str | None) -> dict:
    columns = _all_columns(N + "Form_Template__c", org)
    key = "Id" if len(reference) in (15, 18) and reference.startswith("a") and reference.isalnum() else "Name"
    rows = org_module.query(f"SELECT {', '.join(columns)} FROM {N}Form_Template__c "
                            f"WHERE {key} = {_soql_list([reference])}", org)
    if not rows and key == "Id":
        rows = org_module.query(f"SELECT {', '.join(columns)} FROM {N}Form_Template__c "
                                f"WHERE Name = {_soql_list([reference])}", org)
    if len(rows) != 1:
        raise SystemExit(f"Expected one Form Template for {reference!r}, found {len(rows)}.")
    return rows[0]


def _cmt_forms(names: set[str], org: str | None) -> dict:
    """Form__mdt trees for the named forms, with rules, in one shape."""
    if not names:
        return {}
    in_names = _soql_list(names)
    forms = {}
    for row in org_module.query(
            f"SELECT QualifiedApiName, Label, {N}config__c, {N}Form_Object__r.{N}Object__r.QualifiedApiName "
            f"FROM {N}Form__mdt WHERE QualifiedApiName IN ({in_names})", org):
        form_object = ((row.get(N + "Form_Object__r") or {}).get(N + "Object__r") or {}).get("QualifiedApiName") or ""
        # config__c carries the form root, including its Submission Field Map.
        forms[row["QualifiedApiName"]] = {"label": row.get("Label") or "", "object": fold_star(form_object),
                                          "config": row.get(N + "config__c") or "", "sections": [], "logic": {}}
    if not forms:
        return {}
    in_found = _soql_list(forms)

    section_by_name = {}
    for row in org_module.query(
            f"SELECT QualifiedApiName, {N}Form__r.QualifiedApiName, {N}position__c, {N}config__c, "
            f"{N}conditionalLogic__c FROM {N}Form_Section__mdt "
            f"WHERE {N}Form__r.QualifiedApiName IN ({in_found}) AND {N}Delete__c = false", org):
        section = {"name": row["QualifiedApiName"], "position": row.get(N + "position__c") or 0,
                   "config": row.get(N + "config__c") or "", "condition_id": row.get(N + "conditionalLogic__c") or "",
                   "fields": []}
        section_by_name[row["QualifiedApiName"]] = section
        forms[row[N + "Form__r"]["QualifiedApiName"]]["sections"].append(section)

    for row in org_module.query(
            f"SELECT QualifiedApiName, {N}Form_Section__r.QualifiedApiName, {N}position__c, "
            f"{N}fieldName__r.QualifiedApiName, {N}Object__r.QualifiedApiName, {N}required__c, "
            f"{N}readOnly__c, {N}config__c, {N}conditionalLogic__c FROM {N}Form_Field__mdt "
            f"WHERE {N}Form__r.QualifiedApiName IN ({in_found}) AND {N}Delete__c = false", org):
        section = section_by_name.get((row.get(N + "Form_Section__r") or {}).get("QualifiedApiName"))
        if section is None:
            continue
        section["fields"].append({
            "name": row["QualifiedApiName"], "position": row.get(N + "position__c") or 0,
            "field": fold_star((row.get(N + "fieldName__r") or {}).get("QualifiedApiName") or ""),
            "object": fold_star((row.get(N + "Object__r") or {}).get("QualifiedApiName") or ""),
            "required": bool(row.get(N + "required__c")), "read_only": bool(row.get(N + "readOnly__c")),
            "config": row.get(N + "config__c") or "", "condition_id": row.get(N + "conditionalLogic__c") or ""})

    logic_rows = org_module.query(
        f"SELECT Id, QualifiedApiName, Label, {N}Form__r.QualifiedApiName, {N}config__c "
        f"FROM {N}Form_Conditional_Logic__mdt "
        f"WHERE {N}Form__r.QualifiedApiName IN ({in_found}) AND {N}Delete__c = false", org)
    logic_by_id = {}
    for row in logic_rows:
        config = _config(row)
        entry = {"label": row.get("Label") or "", "condition_type": _key(config, "conditionType__c") or "AND",
                 "display_type": _key(config, "displayType__c") or "",
                 "custom_logic": _key(config, "customLogic__c") or "", "conditions": []}
        logic_by_id[row["Id"]] = entry
        forms[row[N + "Form__r"]["QualifiedApiName"]]["logic"][row["Id"]] = entry
    if logic_by_id:
        for row in org_module.query(
                f"SELECT {N}conditionalLogic__c, {N}position__c, {N}fieldName__r.QualifiedApiName, "
                f"{N}Object__r.QualifiedApiName, {N}value__c, {N}config__c "
                f"FROM {N}Form_Conditional_Logic_Condition__mdt "
                f"WHERE {N}Form__r.QualifiedApiName IN ({in_found}) AND {N}Delete__c = false", org):
            entry = logic_by_id.get(row.get(N + "conditionalLogic__c"))
            if entry is None:
                continue
            entry["conditions"].append({
                "position": row.get(N + "position__c") or 0,
                "field": fold_star((row.get(N + "fieldName__r") or {}).get("QualifiedApiName") or ""),
                "object": fold_star((row.get(N + "Object__r") or {}).get("QualifiedApiName") or ""),
                "operation": _key(_config(row), "operation__c") or "",
                "value": row.get(N + "value__c") if row.get(N + "value__c") is not None else _key(_config(row), "value__c")})
    return forms


def _form_names(section: dict) -> set[str]:
    names = set()
    wrapper = walk.parse_section_wrapper(section.get(N + "FormConfigJSON__c") or "")
    for candidate in (section.get(N + "FormQualifiedApiName__c"), wrapper.get("form_name")):
        if candidate:
            names.add(fold_star(candidate))
    return names


def _objects_in(node, found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and (key.endswith("ObjectApiName__c") or key.endswith("Object__c")) \
                    and value and "." not in value and not value.startswith("01I"):
                found.add(fold_star(value))
            elif key == "QualifiedApiName" and isinstance(value, str) and value.endswith("__c") \
                    and node.get("Label") and "DataType" not in node:
                found.add(fold_star(value))
            _objects_in(value, found)
    elif isinstance(node, list):
        for item in node:
            _objects_in(item, found)


def _describe(sobject: str, org: str | None) -> dict:
    fields = {}
    for name, entry in org_module.describe_fields(sobject, org).items():
        fields[name] = {"label": entry.get("label") or name, "type": entry.get("type") or "",
                        "nillable": bool(entry.get("nillable", True)),
                        "picklist": [v.get("label") or v.get("value") for v in entry.get("picklistValues") or []
                                     if v.get("active", True)]}
    return fields


def extract(reference: str, org: str | None = None) -> dict:
    template = _find_template(reference, org)
    pages = org_module.query(
        f"SELECT {', '.join(_all_columns(N + 'Form_Template_Page__c', org))} FROM {N}Form_Template_Page__c "
        f"WHERE {N}Form_Template__c = '{template['Id']}' ORDER BY {N}Position__c", org)
    sections = []
    if pages:
        sections = org_module.query(
            f"SELECT {', '.join(_all_columns(N + 'Form_Template_Page_Section__c', org))} "
            f"FROM {N}Form_Template_Page_Section__c WHERE {N}Form_Template_Page__c IN ({_soql_list(p['Id'] for p in pages)}) "
            f"ORDER BY {N}Position__c", org)

    names, component_ids = set(), set()
    for section in sections:
        names |= _form_names(section)
        if section.get(N + "Form_Component__c"):
            component_ids.add(section[N + "Form_Component__c"])
    for column in ("FormQualifiedApiName_Header__c", "FormQualifiedApiName_Footer__c"):
        if template.get(N + column):
            names.add(fold_star(template[N + column]))

    components = []
    component_columns = ["Id", "Name", N + "Label__c", N + "QualifiedApiName__c", N + "VersionId__c", N + "Version__c",
                         N + "ObjectApiName__c", N + "FormConfigJSON__c", "RecordType.DeveloperName"]
    # The Submission Field Map arrived with cross-object page sections; an older
    # package has no such column, and naming it would fail the whole query.
    if N + "Submission_Field_Map__c" in _all_columns(N + "Form_Component__c", org):
        component_columns.append(N + "Submission_Field_Map__c")
    filters = []
    if component_ids:
        filters.append(f"Id IN ({_soql_list(component_ids)})")
    if names:
        filters.append(f"{N}VersionId__c IN ({_soql_list(names)})")
        filters.append(f"{N}QualifiedApiName__c IN ({_soql_list(names)})")
    if filters:
        components = org_module.query(f"SELECT {', '.join(component_columns)} FROM {N}Form_Component__c "
                                      f"WHERE {' OR '.join(filters)}", org)

    cmt = _cmt_forms(names, org)

    objects = {N + "Form_Submission__c"}
    for form in cmt.values():
        if form["object"]:
            objects.add(form["object"])
        for section in form["sections"]:
            objects |= {f["object"] for f in section["fields"] if f["object"]}
    for component in components:
        if component.get(N + "ObjectApiName__c"):
            objects.add(fold_star(component[N + "ObjectApiName__c"]))
        try:
            _objects_in(json.loads(component.get(N + "FormConfigJSON__c") or "{}"), objects)
        except ValueError:
            pass
    for section in sections:
        wrapper = walk.parse_section_wrapper(section.get(N + "FormConfigJSON__c") or "")
        if wrapper.get("object"):
            objects.add(fold_star(wrapper["object"]))
        _objects_in(wrapper.get("config") or {}, objects)

    describes, missing = {}, []
    for sobject in sorted(objects):
        try:
            describes[sobject] = _describe(sobject, org)
        except org_module.OrgError:
            missing.append(sobject)

    return {"export_version": "1", "extracted_on": datetime.date.today().isoformat(), "org": org or "",
            "namespace": N, "template": template, "pages": pages, "sections": sections,
            "components": components, "cmt_forms": cmt, "describes": describes,
            "undescribable_objects": missing}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export one Form Template for form-migrate")
    parser.add_argument("--template", required=True, help="Form Template Id or Name")
    parser.add_argument("--org", default=None, help="sf org alias (default: the default org)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    export = extract(args.template, args.org)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export, indent=1, sort_keys=True, ensure_ascii=False))
    print(f"{out}: {len(export['pages'])} pages, {len(export['sections'])} sections, "
          f"{len(export['components'])} component records, {len(export['cmt_forms'])} metadata forms, "
          f"{len(export['describes'])} objects described")


if __name__ == "__main__":
    main()
