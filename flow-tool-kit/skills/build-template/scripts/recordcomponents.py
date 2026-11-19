"""Shared Form Components as records, through Flow Tool Kit's FormComponentImport.createRecordComponent (5.3 and later).

build-template creates every record component a plan owns (a promoted `shared-record`, an `extend` copy, the banner
headers it needs) BEFORE it touches the template, so a failed create stops the build with the package's own error text
and no template change. Sections then point at the component in component mode with its `_v0` name (a record
component's version 0); a metadata component keeps its plain name. Standard library only.

The method is all or nothing, and calling it again with the same API name replaces the component's contents in place
(same Id), so a rebuild updates every template that uses the component. references/record-components.md has the detail.
"""
from __future__ import annotations

import copy
import json

from sforg import quoted

N = "FlowToolKit__"
STAR = "*__"
RECORD = "Record_Component"
APEX_CHUNK = 2000  # characters per Apex string literal piece; the pieces are joined in Apex
# Keys a copied component must not carry: record Ids and the version the save assigns.
COPY_DROPPED = {"Id", "_Id", "attributes", "VersionId__c", "Version__c", "SystemModstamp__c"}


def versioned_name(name: str, kind: str) -> str:
    """The name a page section or header field uses: a record component's version 0 carries `_v0`, a metadata one never."""
    if kind == "record":
        return name if name.endswith("_v0") else f"{name}_v0"
    return name


def component_reference(name: str, kind: str, obj: str, component_id: str | None = None) -> dict:
    """The page-section fields that put a section in component mode."""
    qualified = versioned_name(name, kind)
    record = {N + "FormConfigJSON__c": json.dumps({"formSelectionMode": "component", "object": obj, "formQualifiedApiName": qualified}),
              N + "FormQualifiedApiName__c": qualified}
    if kind == "record" and component_id:
        record[N + "Form_Component__c"] = component_id
    return record


def apex_string(text: str, chunk: int = APEX_CHUNK) -> str:
    """An Apex expression whose value is `text`: escaped single-quoted pieces joined with +, so no one literal is huge.

    The text is cut before escaping, so an escape pair is never split across two pieces."""
    pieces = [text[i:i + chunk] for i in range(0, len(text), chunk)] or [""]
    escape = lambda s: s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    return "\n    + ".join(f"'{escape(p)}'" for p in pieces)


def create_code(component_json: dict, namespace_prefix: str = "FlowToolKit.") -> str:
    """Anonymous Apex that creates or updates one record component and prints its Id."""
    body = apex_string(json.dumps(component_json, ensure_ascii=True))
    return (f"String componentJson = {body};\n"
            f"Id componentId = {namespace_prefix}FormComponentImport.createRecordComponent(componentJson);\n"
            "System.debug(LoggingLevel.ERROR, 'COMPONENT_ID=' + componentId);\n")


def import_available(org) -> bool:
    """FormComponentImport is in Flow Tool Kit 5.3 and later; an older org cannot create record components."""
    try:
        return bool(org.query("SELECT Id FROM ApexClass WHERE NamespacePrefix = 'FlowToolKit' AND Name = 'FormComponentImport'"))
    except Exception:  # noqa: BLE001 - an org that refuses the read is tried, and the call's own error is reported
        return True


def component_rows(org, names) -> list[dict]:
    names = sorted({n[:-3] if n.endswith("_v0") else n for n in names if n})
    if not names:
        return []
    return org.query(f"SELECT Id, {N}QualifiedApiName__c, {N}FormConfigJSON__c, {N}Version__c, {N}ObjectApiName__c, RecordType.DeveloperName "
                     f"FROM {N}Form_Component__c WHERE {N}QualifiedApiName__c IN ({quoted(names)})")


def component_kinds(org, names) -> dict:
    """{name: ("record" | "metadata", record Id or None)} for the components that exist in the org.

    A metadata component has a row per version; one Record_Component row makes the name a record component."""
    kinds: dict = {}
    for row in component_rows(org, names):
        name = row.get(N + "QualifiedApiName__c")
        if (row.get("RecordType") or {}).get("DeveloperName") == RECORD:
            kinds[name] = ("record", row["Id"])
        else:
            kinds.setdefault(name, ("metadata", None))
    return kinds


def component_design(org, name: str) -> dict | None:
    """The stored design of an existing component (its newest version), as the JSON root Form Builder keeps, or None."""
    rows = [r for r in component_rows(org, [name]) if r.get(N + "FormConfigJSON__c")]
    if not rows:
        return None
    rows.sort(key=lambda r: ((r.get("RecordType") or {}).get("DeveloperName") == RECORD, float(r.get(N + "Version__c") or 0)), reverse=True)
    try:
        return json.loads(rows[0][N + "FormConfigJSON__c"])
    except ValueError:
        return None


def logic_count(config_json: str | None) -> int:
    """Rules in a stored component JSON (FormConfigJSON__c), whatever the key prefix."""
    try:
        root = json.loads(config_json or "{}")
    except ValueError:
        return 0
    return sum(len(v or []) for k, v in root.items() if k.endswith("conditionalLogic__r") and isinstance(v, list))


def _bare(key: str) -> str:
    return key.replace(STAR, "").replace(N, "")


def copy_design(design: dict, new_name: str) -> dict:
    """A copy of a stored component under a new name: Ids and version keys dropped, every child renamed.

    Child names (sections, fields, rules, conditions) are unique across the org, so each one gets the new component's
    name in front of its old suffix, and every value that referred to an old child name (a field's rule, a condition's
    parent) is rewritten to the new one."""
    root = copy.deepcopy(design)
    old_root = root.get("QualifiedApiName") or ""
    renames: dict = {}

    def collect(node, in_list=False):
        # Children are the dicts inside lists (sections, fields, rules, conditions); a dict outside a list, such as
        # the theme or object reference, names something else and keeps its name.
        if isinstance(node, dict):
            name = node.get("QualifiedApiName")
            if in_list and isinstance(name, str) and name not in renames:
                suffix = name[len(old_root):] if old_root and name.startswith(old_root) else "_" + name
                candidate = new_name + suffix
                renames[name] = candidate if len(candidate) <= 40 else f"{new_name[:30]}_C{len(renames) + 1:03d}"
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item, True)
    collect(root)

    def rewrite(node):
        if isinstance(node, dict):
            return {k: rewrite(v) for k, v in node.items() if _bare(k) not in COPY_DROPPED}
        if isinstance(node, list):
            return [rewrite(item) for item in node]
        if isinstance(node, str) and node in renames:
            return renames[node]
        return node
    out = rewrite(root)
    out["QualifiedApiName"] = new_name
    return out


def extend_design(design: dict, new_name: str, added: list[dict], label: str, description: str) -> dict:
    """The new version an `extend` answer asks for: the named component copied as it is, plus the added fields at the end
    of its last input section. `added` holds field JSON already built by buildtemplate.field_json."""
    root = copy_design(design, new_name)
    root["Label"] = label[:80]
    root[STAR + "Description__c"] = description[:255]
    sections = next((v for k, v in root.items() if _bare(k) == "sections__r"), None)
    if sections is None:
        sections = root.setdefault(STAR + "sections__r", [])
    inputs = [s for s in sections if (next((v for k, v in s.items() if _bare(k) == "sectionType__c"), "inputSection")) in ("inputSection", None, "")]
    if not inputs:
        raise ValueError(f"{new_name}: the component has no input section to add fields to")
    target = inputs[-1]
    fields = next((v for k, v in target.items() if _bare(k) == "fields__r"), None)
    if fields is None:
        fields = target.setdefault(STAR + "fields__r", [])
    start = max([int(next((v for k, v in f.items() if _bare(k) == "position__c"), 0) or 0) for f in fields] or [0])
    existing = {str(next((v for k, v in f.items() if _bare(k) == "fieldName__c"), "")).replace(N, STAR) for f in fields}
    for offset, field in enumerate(added, 1):
        name = str(field.get(STAR + "fieldName__c") or "")
        if name.replace(N, STAR) in existing:
            continue
        field = dict(field)
        field[STAR + "position__c"] = start + offset
        field["QualifiedApiName"] = f"{new_name[:30]}_FX{start + offset}"
        fields.append(field)
    return root


def create_components(org, specs: list[dict], namespace_prefix: str = "FlowToolKit.") -> dict:
    """Create or update each record component in order; stop at the first failure with the package's message.

    specs: [{"name", "json"}]. Returns {name: {"id", "rules"}} read back from the org after the calls, so nothing depends
    on parsing the debug log. Raises RuntimeError naming the component and the package's error text."""
    for spec in specs:
        try:
            org.apex(create_code(spec["json"], namespace_prefix))
        except Exception as error:  # the Org raises BuildError; this module stays free of buildtemplate imports
            raise RuntimeError(f"Form Component {spec['name']} was not created, so no template was changed. {error}") from error
    if not specs:
        return {}
    names = [s["name"] for s in specs]
    rows = [r for r in component_rows(org, names) if (r.get("RecordType") or {}).get("DeveloperName") == RECORD]
    found = {r[N + "QualifiedApiName__c"]: r for r in rows}
    missing = [n for n in names if n not in found]
    if missing:
        raise RuntimeError(f"Form Components not found after the create call: {missing}; no template was changed.")
    return {n: {"id": found[n]["Id"], "rules": logic_count(found[n].get(N + "FormConfigJSON__c"))} for n in names}


def import_file_text(component_json: dict) -> str:
    """The JSON to paste into the Form Component Import button when no Apex can run (claude.ai chat)."""
    return json.dumps(component_json, indent=2, ensure_ascii=False)

