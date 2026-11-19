"""Build catalog.json from the rows in raw.json. Pure: no org access, so the same code runs after the Salesforce CLI
or after a connector in chat. The format is _shared/standards/catalog-format.md.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ocmatch import THRESHOLD, is_candidate, score
from ocqueries import PLATFORM_OBJECTS, ftk_present
from ocutil import NS, SUBMISSION, bare, canonical_object, failed, ns, parse_json, plain, ran, records, val

CATALOG_VERSION = 1
# A refused read of one of these leaves a hole in the reuse map, so the catalog is marked partial
ESSENTIAL = {"forms_mdt", "sections_mdt", "fields_mdt", "components", "templates", "pages", "page_sections", "fields:" + SUBMISSION}
ID_LIKE = re.compile(r"^(?=[a-zA-Z0-9]*\d)[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?$")  # a record Id has digits; ShippingPostalCode does not


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def empty(status, note, taken_at=None, org=None):
    """A catalog with nothing in it, saying why: 'no org' or 'no package'."""
    return {"catalog_version": CATALOG_VERSION, "taken_at": taken_at or now(), "status": status, "status_note": note,
            "source": None, "org": org, "package": None, "edition": None, "platforms": {}, "components": [], "templates": [],
            "repeated_sections": [], "mapped_forms": [], "placements": {}, "run_time_forms": [], "filing": {"folders": {}, "tags": {}},
            "brand_kit": {"found": "none" if status == "no package" else "unknown",
                                                                        "summary": note},
            "fields_index": {}, "counts": {}, "problems": [], "warnings": []}


# ---- fields ----------------------------------------------------------------------------------------------------------

def field_index(raw):
    """{object: {field: {label, type}}}, {durable id: (object, field)}, {object: [twin bare names]}."""
    by_object, durable = {}, {}
    for key, entry in (raw.get("queries") or {}).items():
        if not key.startswith("fields:") or not isinstance(entry, dict):
            continue
        obj = key.split(":", 1)[1]
        fields = by_object.setdefault(obj, {})
        for row in entry.get("records") or []:
            name = val(row, "QualifiedApiName")
            if not name:
                continue
            fields[name] = {"label": val(row, "Label"), "type": val(row, "DataType")}
            if val(row, "DurableId"):
                durable[val(row, "DurableId")] = (obj, name)
    twins = {}
    for obj, fields in by_object.items():
        names = set(fields)
        found = sorted(n for n in names if not n.startswith(NS) and NS + n in names)
        if found:
            twins[obj] = found
    return by_object, durable, twins


def resolve_durable(value, obj, durable):
    """A Form_Field__mdt fieldName value (a durable Id such as Account.Website or Account.<field Id>) as (object, field)."""
    if not value:
        return obj, None
    if value in durable:
        return durable[value]
    head, dot, tail = value.rpartition(".")
    if dot and not ID_LIKE.match(tail):
        return (obj or head), tail
    if not dot and not ID_LIKE.match(value):
        return obj, value
    return obj, None


def labelled(obj, name, custom, index, fallback=None):
    info = (index.get(obj) or {}).get(name) or {}
    return {"object": obj, "field": name, "label": plain(custom) or info.get("label") or fallback or name, "type": info.get("type")}


# ---- components ------------------------------------------------------------------------------------------------------

def tidy_folder(text):
    """A folder path as the component browser files it: names joined with a slash, blanks dropped; None when unfiled."""
    path = "/".join(name.strip() for name in str(text or "").split("/") if name.strip())
    return path or None


def split_tags(text):
    """Comma separated tags as a list, trimmed, without repeats, in their order."""
    out = []
    for tag in str(text or "").split(","):
        if tag.strip() and tag.strip() not in out:
            out.append(tag.strip())
    return out


def submission_map(value):
    """A Form Template Mapping ({lookupField, fields: {submission field: source field}}) or None."""
    parsed = parse_json(ns(value)) if isinstance(value, str) else (value if isinstance(value, dict) else {})
    fields = parsed.get("fields") if isinstance(parsed.get("fields"), dict) else {}
    fields = {ns(k): ns(v) for k, v in fields.items() if isinstance(v, str) and v and k}
    if not fields:
        return None
    return {"lookup_field": ns(parsed.get("lookupField")) or "ALL", "fields": fields}


def _map_in(root):
    for key, value in (root or {}).items():
        if key.endswith("Submission_Field_Map__c") and value:
            return submission_map(value)
    return None


def metadata_components(raw, index, durable, problems):
    forms = {val(r, "QualifiedApiName"): r for r in records(raw, "forms_mdt") if val(r, "QualifiedApiName")}
    sections_by_form, fields_by_form = {}, {}
    for row in records(raw, "sections_mdt"):
        if not val(row, f"{NS}Delete__c"):
            sections_by_form.setdefault(val(row, f"{NS}Form__r.QualifiedApiName"), []).append(row)
    for row in records(raw, "fields_mdt"):
        if not val(row, f"{NS}Delete__c"):
            fields_by_form.setdefault(val(row, f"{NS}Form__r.QualifiedApiName"), []).append(row)
    out = []
    for name, row in sorted(forms.items()):
        config = parse_json(ns(val(row, f"{NS}config__c") or ""))
        obj = canonical_object(val(row, f"{NS}Form_Object__r.{NS}Object__r.QualifiedApiName") or "")
        titles, sections, uses = {}, [], []
        for section in sorted(sections_by_form.get(name, []), key=lambda s: val(s, f"{NS}position__c") or 0):
            section_config = parse_json(ns(val(section, f"{NS}config__c") or ""))
            title = plain(val(section_config, "title__c")) or val(section, "MasterLabel") or ""
            titles[val(section, "QualifiedApiName")] = title
            sections.append({"title": title, "type": val(section_config, "sectionType__c")})
            nested = val(section, f"{NS}formComponent__r.QualifiedApiName")
            if nested:
                uses.append({"component": nested, "via": "section", "where": title})
            table = val(section, f"{NS}Default_Table_Form__r.QualifiedApiName")
            if table:
                uses.append({"component": table, "via": "table form", "where": title})
            bulk = val(section, f"{NS}Default_Table_Form_bulk__r.QualifiedApiName")
            if bulk:
                uses.append({"component": bulk, "via": "bulk table form", "where": title})
        fields = []
        for field in sorted(fields_by_form.get(name, []), key=lambda f: (val(f, f"{NS}position__c") or 0)):
            field_obj = canonical_object(val(field, f"{NS}Object__r.QualifiedApiName") or obj)
            field_obj, field_name = resolve_durable(val(field, f"{NS}fieldName__c"), field_obj, durable)
            field_config = parse_json(ns(val(field, f"{NS}config__c") or ""))
            reference = val(field, f"{NS}referenceFormComponent__r.QualifiedApiName")
            section_title = titles.get(val(field, f"{NS}Form_Section__r.QualifiedApiName"), "")
            if reference:
                uses.append({"component": reference, "via": "field", "where": section_title})
            if field_name is None:
                if val(field, f"{NS}fieldName__c"):
                    problems.append(f"Component {name}: a field points to a field this catalog could not resolve "
                                    f"({val(field, NS + 'fieldName__c')}); it may be deleted or unreadable")
                continue
            item = labelled(field_obj, field_name, val(field_config, "customLabel__c"), index, val(field, "MasterLabel"))
            item["section"] = section_title
            fields.append(item)
        out.append({"name": name, "ref": name, "kind": "metadata", "packaged": (val(row, "NamespacePrefix") or "") == "FlowToolKit",
                    "label": val(row, "MasterLabel") or name, "object": obj, "type": val(row, f"{NS}type__c"),
                    "active": bool(val(row, f"{NS}Active__c")), "description": plain(val(row, f"{NS}Description__c")),
                    "folder": tidy_folder(val(config, "Folder__c")), "tags": split_tags(val(config, "Tags__c")), "fields": fields, "sections": sections, "uses": uses,
                    "rules": None, "submission_map": _map_in(config)})
    return out


def json_fields(root, obj, index):
    """Fields, sections and nested components of a component JSON root."""
    fields, sections, uses = [], [], []
    for section in sorted(val(root, "sections__r") or [], key=lambda s: val(s, "position__c") or 0):
        title = plain(val(section, "title__c"))
        sections.append({"title": title, "type": val(section, "sectionType__c")})
        nested = val(section, "formComponent__r.QualifiedApiName") or (val(section, "formComponent__c") if isinstance(val(section, "formComponent__c"), str) else None)
        if nested:
            uses.append({"component": ns(nested), "via": "section", "where": title})
        table = val(section, "Default_Table_Form__r.QualifiedApiName") or (val(section, "Default_Table_Form__c") if isinstance(val(section, "Default_Table_Form__c"), str) else None)
        if table:
            uses.append({"component": ns(table), "via": "table form", "where": title})
        bulk = val(section, "Default_Table_Form_bulk__r.QualifiedApiName") or (val(section, "Default_Table_Form_bulk__c") if isinstance(val(section, "Default_Table_Form_bulk__c"), str) else None)
        if bulk:
            uses.append({"component": ns(bulk), "via": "bulk table form", "where": title})
        for field in sorted(val(section, "fields__r") or [], key=lambda f: val(f, "position__c") or 0):
            name = val(field, "fieldName__r.QualifiedApiName") or val(field, "fieldName__c")
            reference = val(field, "referenceFormComponent__r.QualifiedApiName") or (val(field, "referenceFormComponent__c") if isinstance(val(field, "referenceFormComponent__c"), str) else None)
            if reference:
                uses.append({"component": ns(reference), "via": "field", "where": title})
            if not isinstance(name, str) or not name:
                continue
            field_obj = canonical_object(val(field, "Object__r.QualifiedApiName") or val(field, "Object__c") or obj)
            item = labelled(field_obj, ns(name), val(field, "customLabel__c") or val(field, "Label_Rich_Text__c"), index)
            item["section"] = title
            fields.append(item)
    return fields, sections, uses


def record_components(raw, index, metadata_names, problems):
    by_name = {}
    for row in records(raw, "components"):
        name = val(row, f"{NS}QualifiedApiName__c") or row.get("Name")
        by_name.setdefault(name, []).append(row)
    child_fields, child_sections = {}, {}
    for row in records(raw, "component_fields"):
        child_fields.setdefault(val(row, f"{NS}Form_Component__c"), []).append(row)
    for row in records(raw, "component_sections"):
        child_sections.setdefault(val(row, f"{NS}Form_Component__c"), []).append(row)
    out, tracked = [], []
    for name, rows in sorted(by_name.items(), key=lambda item: str(item[0])):
        record_type = val(rows[0], "RecordType.DeveloperName")
        if record_type == "Metadata_Component" and (name in metadata_names or NS + str(name) in metadata_names):
            tracked.append(name)
            continue
        rows.sort(key=lambda r: (bool(val(r, f"{NS}Active__c")), val(r, f"{NS}Version__c") or 0))
        row = rows[-1]
        root = parse_json(ns(val(row, f"{NS}FormConfigJSON__c") or ""))
        obj = canonical_object(val(row, f"{NS}ObjectApiName__c") or val(root, "ObjectApiName__c") or SUBMISSION)
        if root:
            fields, sections, uses = json_fields(root, obj, index)
            rules = len(val(root, "conditionalLogic__r") or [])
        else:
            fields, sections, uses, rules = [], [], [], None
            for child in sorted(child_fields.get(row.get("Id"), []), key=lambda f: (val(f, f"{NS}Form_Component_Section__r.{NS}position__c") or 0, val(f, f"{NS}position__c") or 0)):
                if val(child, f"{NS}fieldName__c"):
                    item = labelled(canonical_object(val(child, f"{NS}Object__c") or obj), ns(val(child, f"{NS}fieldName__c")), val(child, f"{NS}customLabel__c"), index)
                    item["section"] = plain(val(child, f"{NS}Form_Component_Section__r.{NS}title__c"))
                    fields.append(item)
                if val(child, f"{NS}referenceFormComponent__c"):
                    uses.append({"component": val(child, f"{NS}referenceFormComponent__c"), "via": "field", "where": ""})
            for child in child_sections.get(row.get("Id"), []):
                sections.append({"title": plain(val(child, f"{NS}title__c")), "type": None})
                if val(child, f"{NS}formComponent__c"):
                    uses.append({"component": val(child, f"{NS}formComponent__c"), "via": "section", "where": plain(val(child, f"{NS}title__c"))})
                if val(child, f"{NS}Default_Table_Form__c"):
                    uses.append({"component": val(child, f"{NS}Default_Table_Form__c"), "via": "table form", "where": plain(val(child, f"{NS}title__c"))})
                if val(child, f"{NS}Default_Table_Form_bulk__c"):
                    uses.append({"component": val(child, f"{NS}Default_Table_Form_bulk__c"), "via": "bulk table form", "where": plain(val(child, f"{NS}title__c"))})
            if not fields and not ran(raw, "component_fields"):
                problems.append(f"Component {name}: its JSON is blank and its field rows were not read")
        version_ids = sorted({val(r, f"{NS}VersionId__c") for r in rows if val(r, f"{NS}VersionId__c")})
        out.append({"name": name, "ref": f"{name}_v0", "refs": version_ids, "kind": "record" if record_type != "Metadata_Component" else "metadata",
                    "packaged": False, "label": val(row, f"{NS}Label__c") or val(root, "Label") or name, "object": obj,
                    "type": val(row, f"{NS}type__c"), "active": bool(val(row, f"{NS}Active__c")),
                    "description": plain(val(row, f"{NS}Description__c")),
                    "folder": tidy_folder(val(row, f"{NS}Folder__c") or val(root, "Folder__c")),
                    "tags": split_tags(val(row, f"{NS}Tags__c") or val(root, "Tags__c")),
                    "fields": fields, "sections": sections, "uses": uses, "rules": rules, "id": row.get("Id"),
                    "versions": len(rows), "modified": val(row, "LastModifiedDate"),
                    "submission_map": submission_map(val(row, f"{NS}Submission_Field_Map__c")) or _map_in(root)})
    return out, tracked


class ComponentIndex:
    """Find a component by whatever a section or another component stores: its name, with or without the package
    prefix, or a record component's version Id (Name_v0)."""

    def __init__(self, components):
        self.by_ref = {}
        for component in components:
            names = [component["name"], component["ref"]] + component.get("refs", [])
            for name in names:
                if name:
                    self.by_ref.setdefault(str(name).lower(), component)
                    self.by_ref.setdefault(bare(str(name)).lower(), component)

    def get(self, ref):
        if not ref:
            return None
        ref = ns(str(ref)).lower()
        return self.by_ref.get(ref) or self.by_ref.get(bare(ref)) or self.by_ref.get(re.sub(r"_v\d+$", "", ref))


# ---- templates -------------------------------------------------------------------------------------------------------

def section_source(row, index_fields):
    """What a page section shows, the way the package resolves it: a component by name (metadata, or a record
    component by its _v0 name), its own custom JSON, a flow, an LWC or text."""
    kind = val(row, f"{NS}Component_Type__c") or "FieldSet"
    if kind == "Flow":
        return {"source": "flow", "flow": val(row, f"{NS}FlowApiName__c")}
    if kind == "LightningWebComponent":
        return {"source": "lwc", "lwc": val(row, f"{NS}lwcComponentName__c")}
    if kind == "DisplayText":
        return {"source": "text"}
    raw_config = val(row, f"{NS}FormConfigJSON__c") or ""
    wrapper = parse_json(raw_config)
    mode = wrapper.get("formSelectionMode")
    name = val(row, f"{NS}FormQualifiedApiName__c")
    if raw_config.strip() and mode == "component":
        return {"source": "component", "component": wrapper.get("formQualifiedApiName") or name, "object": wrapper.get("object")}
    if raw_config.strip():
        inner = wrapper.get("formJsonConfig") if "formJsonConfig" in wrapper else raw_config
        root = parse_json(ns(inner if isinstance(inner, str) else ""))
        if not root:
            return {"source": "unreadable"}
        obj = canonical_object(wrapper.get("object") or val(root, "ObjectApiName__c") or SUBMISSION)
        fields, _, uses = json_fields(root, obj, index_fields)
        return {"source": "custom", "object": obj, "fields": fields, "uses": uses, "map": _map_in(root)}
    if name:
        return {"source": "component", "component": name}
    return {"source": "empty"}


def templates_tree(raw, components, index_fields, problems):
    index = ComponentIndex(components)
    pages_by_template = {}
    for page in records(raw, "pages"):
        pages_by_template.setdefault(val(page, f"{NS}Form_Template__c"), []).append(page)
    sections_by_page = {}
    for section in records(raw, "page_sections"):
        sections_by_page.setdefault(val(section, f"{NS}Form_Template_Page__c"), []).append(section)
    templates, custom_sections = [], []

    def use(ref, where, role):
        component = index.get(ref)
        if component is None:
            problems.append(f"{where['template']} page {where['page']}: the {role} names {ref}, which is not in the org")
            return None
        component.setdefault("used_in", []).append(dict(where, role=role))
        return component["name"]

    for template in sorted(records(raw, "templates"), key=lambda t: str(val(t, "Name"))):
        t_id, t_name = template.get("Id"), val(template, "Name")
        entry = {"id": t_id, "name": t_name, "active": bool(val(template, f"{NS}IsActive__c")),
                 "header": None, "footer": None, "logo": val(template, f"{NS}Logo__c"),
                 "logo_override": val(template, f"{NS}Logo_Override__c"), "pages": []}
        for role, field in (("header", "FormQualifiedApiName_Header__c"), ("footer", "FormQualifiedApiName_Footer__c")):
            ref = val(template, NS + field)
            if ref:
                entry[role] = use(ref, {"template_id": t_id, "template": t_name, "page": 0, "position": 0, "section": role}, role) or ref
        for page in sorted(pages_by_template.get(t_id, []), key=lambda p: val(p, f"{NS}Position__c") or 0):
            page_no = int(val(page, f"{NS}Position__c") or 0)
            page_entry = {"id": page.get("Id"), "position": page_no,
                          "label": plain(val(page, f"{NS}Page_Label__c") or val(page, f"{NS}Page_Title__c") or val(page, "Name")), "sections": []}
            for section in sorted(sections_by_page.get(page.get("Id"), []), key=lambda s: val(s, f"{NS}Position__c") or 0):
                title = plain(val(section, f"{NS}Header_Title__c")) or plain(val(section, f"{NS}Title__c")) or "(untitled)"
                where = {"template_id": t_id, "template": t_name, "page": page_no,
                         "position": int(val(section, f"{NS}Position__c") or 0), "section": title}
                source = section_source(section, index_fields)
                item = {"id": section.get("Id"), "position": where["position"], "title": title,
                        "component_type": val(section, f"{NS}Component_Type__c") or "FieldSet", **source}
                if source["source"] == "component":
                    item["component"] = use(source["component"], where, "section") or source["component"]
                if source["source"] == "custom":
                    item["field_count"] = len(source["fields"])
                    custom_sections.append(dict(where, section_id=item["id"], object=source["object"], fields=source["fields"]))
                for role, field in (("table form", "Alternate_FormQualifiedApiName__c"), ("bulk form", "Bulk_FormQualifiedApiName__c"),
                                    ("edit form", "Edit_FormQualifiedApiName__c")):
                    ref = val(section, NS + field)
                    if ref:
                        item[role.replace(" ", "_")] = use(ref, where, role) or ref
                page_entry["sections"].append(item)
            entry["pages"].append(page_entry)
        templates.append(entry)
    return templates, custom_sections


def section_tag(section, labels):
    """How catalog.md shows one template section: its component and shape, JSON for its own form, or its source."""
    if section["source"] == "component":
        name = labels.get(section.get("component"), section.get("component"))
        return f"{name}, {section['shape']}" if section.get("shape") else name
    return "JSON" if section["source"] == "custom" else section["source"]


def repeated_sections(custom_sections, twins, threshold=THRESHOLD):
    """Custom sections that repeat across two or more templates at the threshold (grouped, union-find)."""
    pool = [s for s in custom_sections if s["fields"]]
    parent = list(range(len(pool)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            if pool[i]["template_id"] != pool[j]["template_id"] and is_candidate(score(pool[i]["fields"], pool[j]["fields"], twins), threshold):
                parent[find(j)] = find(i)
    groups = {}
    for i in range(len(pool)):
        groups.setdefault(find(i), []).append(pool[i])
    out = []
    for members in groups.values():
        templates = {m["template_id"] for m in members}
        if len(templates) < 2:
            continue
        rep = max(members, key=lambda m: sum(score(m["fields"], o["fields"], twins)[1] for o in members))
        out.append({"title": rep["section"], "object": rep["object"], "templates": len(templates),
                    "fields": [{k: f.get(k) for k in ("object", "field", "label")} for f in rep["fields"]],
                    "sections": [{"template_id": m["template_id"], "template": m["template"], "page": m["page"], "position": m["position"],
                                  "section": m["section"], "section_id": m["section_id"],
                                  "exact": score(m["fields"], rep["fields"], twins)[0], "by_field": score(m["fields"], rep["fields"], twins)[1]}
                                 for m in sorted(members, key=lambda m: (m["template"], m["page"], m["position"]))]})
    out.sort(key=lambda g: (-g["templates"], g["title"]))
    for n, group in enumerate(out, 1):
        group["id"] = f"r{n}"
    return out


# ---- places outside templates: flows, Lightning pages, site pages, wrapper components -----------------------------------

PLACE_KINDS = {"flows": "flows", "lightning_pages": "Lightning pages", "site_pages": "site pages",
               "wrapper_components": "wrapper components"}
ROLE_KIND = {"flow": "flows", "lightning page": "lightning_pages", "site page": "site_pages", "wrapper component": "wrapper_components"}


def link_places(raw, index, problems, warnings):
    """Add every flow, Lightning page, site page and wrapper component that names a form to that component's used_in.
    Returns the read summary ({kind: {read, files, places}, complete, note}) and the places whose form is chosen at run
    time, which cannot be tied to a component."""
    read = raw.get("placements") or {}
    summary, dynamic = {}, []
    for kind, words in PLACE_KINDS.items():
        entry = read.get(kind)
        if not isinstance(entry, dict) or "error" in (entry or {}):
            summary[kind] = {"read": False, "files": 0, "places": 0}
            if isinstance(entry, dict):
                summary[kind]["error"] = str(entry["error"])[:200]
                warnings.append(f"Read refused: {words} ({str(entry['error'])[:160]})")
            continue
        linked = 0
        for item in entry.get("items") or []:
            where = {"template_id": None, "template": None, "role": item["kind"], "place": item["name"],
                     "label": item.get("label") or item["name"], "where": item.get("where"),
                     "via": item.get("component_label"), "property": item.get("property")}
            for key in ("status", "page_type", "object", "site"):
                if item.get(key):
                    where[key] = item[key]
            if item.get("inside"):
                where["inside_own_json"] = True
            if item.get("copy"):
                where["copy"] = True  # holds the form's JSON: a later change to the component does not reach it
            if item.get("form") is None:
                if item.get("variable"):
                    dynamic.append(dict(where, variable=item["variable"]))
                continue
            component = index.get(item["form"])
            if component is None:
                if not item.get("candidate"):
                    problems.append(f"{where['label']} ({item['kind']}, {where['where']}): {where['via']} names {item['form']}, "
                                    f"which is not in the org")
                continue
            key = (where["role"], where["place"], where["where"], where["via"]) + (() if item["kind"] == "wrapper component" else (where["property"],))
            seen = {(u["role"], u.get("place"), u.get("where"), u.get("via")) + (() if u["role"] == "wrapper component" else (u.get("property"),))
                    for u in component.get("used_in") or []}
            if key in seen:
                continue
            component.setdefault("used_in", []).append(where)
            linked += 1
        for unreadable in entry.get("unreadable") or []:
            warnings.append(f"{words}: could not read {unreadable}")
        summary[kind] = {"read": True, "files": entry.get("files", 0), "places": linked}
        for short in entry.get("short") or []:
            # A retrieve that lists more files than reach the folder is a partial read, never a quiet one
            summary[kind].setdefault("short", []).append(short)
            warnings.append(f"{words}: the {short['type']} retrieve listed {short['listed']} files but only {short['arrived']} arrived, "
                            f"so used_in may miss {words} that name a form. Run collect again with no other retrieve against this "
                            f"org at the same time")
    missing = [PLACE_KINDS[k] for k in PLACE_KINDS if not summary[k]["read"]]
    partial = []
    for k in PLACE_KINDS:
        counts = ", ".join(f"{s['arrived']} of {s['listed']}" for s in summary[k].get("short") or [])
        if counts:
            partial.append(f"{PLACE_KINDS[k]} ({counts} files)")
    summary["complete"] = not missing and not partial
    notes = []
    if missing:
        notes.append(f"Not read: {', '.join(missing)}.")
    if partial:
        notes.append(f"Read in part: {', '.join(partial)}.")
    summary["note"] = None if not notes else (
        " ".join(notes) + " used_in lists Form Templates, components and only the places that were read, "
        "so it is not every place a component is used. Name what was not read before changing a shared component in place.")
    for place in dynamic:
        warnings.append(f"{place['label']} ({place['role']}, {place['where']}): {place['via']} takes its form from {place['variable']}, "
                        f"chosen at run time, so it cannot be tied to one component")
    return summary, dynamic


def place_counts(component):
    counts = {"templates": len({u["template_id"] for u in component["used_in"] if u.get("template_id")})}
    for kind in PLACE_KINDS:
        counts[kind] = len({u["place"] for u in component["used_in"] if ROLE_KIND.get(u.get("role")) == kind})
    return counts


def filing(components):
    """Components by folder and by tag, for finding them the way the component browser files them."""
    folders, tags = {}, {}
    for component in components:
        if component.get("folder"):
            folders.setdefault(component["folder"], []).append(component["name"])
        for tag in component.get("tags") or []:
            tags.setdefault(tag, []).append(component["name"])
    return {"folders": {k: sorted(v) for k, v in sorted(folders.items())}, "tags": {k: sorted(v) for k, v in sorted(tags.items())}}


# ---- brand kit and platforms -----------------------------------------------------------------------------------------

def brand_kit(raw, templates):
    style = {"readable": not failed(raw, "style_defaults") and ran(raw, "style_defaults")}
    org_row = next((r for r in records(raw, "style_defaults") if str(val(r, "SetupOwnerId") or "").startswith("00D")), None)
    if org_row:
        for key, field in (("color_primary", "Color_Primary__c"), ("color_on_primary", "Color_On_Primary__c"), ("font_family", "Font_Family__c"),
                           ("font_family_heading", "Font_Family_Heading__c"), ("default_logo", "Default_Logo__c"),
                           ("default_logo_alt_text", "Default_Logo_Alt_Text__c")):
            style[key] = val(org_row, NS + field)
    # The template Logo formula falls back to the org default logo, so a template without its own override shows it
    logo_seen = next((t["logo"] for t in templates if t.get("logo") and not t.get("logo_override")), None)
    libraries = {}
    for row in records(raw, "brand_file_libraries"):
        libraries.setdefault(val(row, "ContentDocumentId"), []).append(val(row, "ContentWorkspace.Name") or val(row, "ContentWorkspace.DeveloperName"))
    files = []
    for row in records(raw, "brand_files"):
        doc = val(row, "ContentDocumentId")
        content = parse_json((raw.get("brand_file_content") or {}).get(row.get("Id")))
        names = libraries.get(doc, [])
        files.append({"title": val(row, "Title"), "content_version_id": row.get("Id"), "content_document_id": doc,
                      "libraries": names, "in_asset_library": any("asset" in str(n).lower() for n in names),
                      "modified": val(row, "LastModifiedDate"), "read": bool(content),
                      "brand_name": content.get("brandName") or content.get("brand_name") or content.get("name"),
                      "colors": content.get("colors"), "fonts": content.get("fonts"), "voice": content.get("voice")})
    has_style = bool(style.get("color_primary") or style.get("default_logo"))
    if has_style and files:
        found = "saved"
    elif has_style or files:
        found = "partial"
    elif logo_seen:
        found = "logo only"
    else:
        found = "none" if style["readable"] else "unknown"
    parts = []
    if style.get("color_primary"):
        parts.append(f"brand color {style['color_primary']}")
    if style.get("font_family"):
        parts.append(f"font {style['font_family']}")
    if style.get("default_logo") or logo_seen:
        parts.append(f"default logo {style.get('default_logo') or logo_seen}")
    for f in files:
        detail = ", ".join(str(v) for v in ((f.get("colors") or {}).get("primary"), (f.get("fonts") or {}).get("body")) if v) \
            if isinstance(f.get("colors"), dict) and isinstance(f.get("fonts"), dict) else ""
        parts.append(f"brand file {f.get('brand_name') or f['title']}" + (f" ({detail})" if detail else "")
                     + ("" if f["in_asset_library"] else ", not in the Asset Library"))
    lead = {"saved": "Saved brand kit", "partial": "Partial brand kit", "logo only": "Default logo only",
            "none": "No saved brand kit", "unknown": "No brand file found"}[found]
    summary = lead + (": " + "; ".join(parts) if parts else "") + "."
    if has_style and not files:
        summary += " No brand file, so no tone of voice."
    if not style["readable"]:
        summary += (" The org's Form Style defaults could not be read (a protected setting in an installed package);"
                    " the Global Styles tab shows them.")
    return {"found": found, "summary": summary, "style_defaults": style, "default_logo_from_templates": logo_seen, "brand_files": files}


def platforms(raw):
    found = {}
    for row in records(raw, "platform_objects"):
        name = val(row, "QualifiedApiName")
        if name in PLATFORM_OBJECTS:
            found.setdefault(PLATFORM_OBJECTS[name], []).append(name)
    namespaces = {val(r, "SubscriberPackage.NamespacePrefix") for r in records(raw, "packages")}
    out = {"outbound_funds": "outbound_funds" in found or "outfunds" in namespaces,
           "nonprofit_cloud": "nonprofit_cloud" in found, "npsp": "npsp" in found or "npsp" in namespaces,
           "person_accounts": person_accounts(raw),
           "evidence": {k: v for k, v in found.items() if k != "flow_tool_kit"}}
    return out


def person_accounts(raw):
    """True or False; None when not read. RecordType has no IsPersonType column until person accounts are turned on."""
    if not ran(raw, "person_accounts"):
        return None
    if failed(raw, "person_accounts"):
        return False if "IsPersonType" in str(raw["queries"]["person_accounts"].get("error")) else None
    return bool(records(raw, "person_accounts"))


def package(raw):
    for row in records(raw, "packages"):
        if (val(row, "SubscriberPackage.NamespacePrefix") or "") == "FlowToolKit":
            parts = [val(row, f"SubscriberPackageVersion.{k}") for k in ("MajorVersion", "MinorVersion", "PatchVersion", "BuildNumber")]
            return {"namespace": "FlowToolKit", "name": val(row, "SubscriberPackage.Name"),
                    "version": ".".join(str(p) for p in parts if p is not None) or None}
    return {"namespace": "FlowToolKit", "name": None, "version": None}


# ---- the catalog -----------------------------------------------------------------------------------------------------

def org_info(raw):
    row = (records(raw, "org") or [None])[0]
    if not row:
        return None
    return {"id": row.get("Id"), "name": val(row, "Name"), "is_sandbox": val(row, "IsSandbox"),
            "type": val(row, "OrganizationType"), "instance": val(row, "InstanceName")}


def build(raw, edition=None):
    taken_at = raw.get("taken_at") or now()
    org = org_info(raw)
    if org is None:
        return empty("no org", "No Salesforce org was read, so this catalog is empty and every section is new.", taken_at)
    if not ftk_present(raw):
        catalog = empty("no package", f"Flow Tool Kit is not installed in {org['name']}, so there is nothing to reuse.", taken_at, org)
        catalog.update(source=raw.get("source"), platforms=platforms(raw))
        return catalog
    problems, warnings = [], []
    index, durable, twins = field_index(raw)
    if not index.get(SUBMISSION):
        warnings.append("Form Submission fields were not read, so name checks and twin checks are unavailable")
    for obj, names in twins.items():
        for name in names:
            warnings.append(f"{obj} has your own field {name} beside the packaged {NS}{name}: the Conversion Setup action leaves "
                            f"{name} out of the record it hands a flow, so read it with your own Get Records or rename it")
    metadata = metadata_components(raw, index, durable, problems)
    records_, tracked = record_components(raw, index, {c["name"] for c in metadata}, problems)
    components = metadata + records_
    templates, custom_sections = templates_tree(raw, components, index, problems)
    by_name = ComponentIndex(components)
    for section in custom_sections:
        for use in section.get("uses", []):
            target = by_name.get(use["component"])
            if target:
                where = {k: section[k] for k in ("template_id", "template", "page", "position", "section")}
                target.setdefault("used_in", []).append(dict(where, role="inside a custom section"))
    for component in components:
        for use in component["uses"]:
            target = by_name.get(use["component"])
            if target is None:
                problems.append(f"Component {component['name']} places {use['component']}, which is not in the org")
                continue
            use["component"] = target["name"]
            target.setdefault("used_by_components", []).append({"component": component["name"], "via": use["via"]})
    places, dynamic = link_places(raw, by_name, problems, warnings)
    for component in components:
        component["shape"] = component["kind"]  # the component shapes standard: metadata or record
        component.setdefault("used_in", [])
        component.setdefault("used_by_components", [])
        component["places"] = place_counts(component)
        component["templates"] = component["places"]["templates"]
    mapped = []
    for component in components:
        if component["object"] == SUBMISSION:
            continue
        smap = component.get("submission_map")
        if smap:
            sources = {f["field"] for f in component["fields"]}
            mapped.append({"object": component["object"], "component": component["name"], "kind": component["kind"],
                           "lookup_field": smap["lookup_field"], "mapped": len(smap["fields"]),
                           "fields": len(sources), "templates": component["templates"],
                           "map": smap["fields"]})
        elif any(u["role"] == "section" for u in component["used_in"]):
            problems.append(f"Component {component['name']} is on {component['object']} with no Form Template Mapping but is placed in a "
                            f"template section, so nothing it collects reaches the Form Submission")
    for template in templates:
        for page in template["pages"]:
            for section in page["sections"]:
                if section["source"] == "custom" and section["object"] != SUBMISSION and not section.get("map"):
                    problems.append(f"{template['name']} page {page['position']} section '{section['title']}': its own form is on "
                                    f"{section['object']} with no Form Template Mapping")
                section.pop("uses", None)
                if section["source"] == "custom":
                    section["shape"] = "json"  # its own form, fixed to this section
                elif section["source"] == "component":
                    placed = by_name.get(section.get("component"))
                    if placed:
                        section["shape"] = placed["kind"]
    mapped.sort(key=lambda m: (m["object"], m["component"]))
    repeats = repeated_sections(custom_sections, twins)
    fields_index = {obj: {"read": True, "count": len(fields), "twins": twins.get(obj, []),
                          "fields": {name: info for name, info in sorted(fields.items())}}
                    for obj, fields in sorted(index.items())}
    for key in (k for k in (raw.get("queries") or {}) if k.startswith("fields:") and failed(raw, k)):
        fields_index[key.split(":", 1)[1]] = {"read": False, "count": 0, "twins": [], "fields": None}
    refused = [k for k, e in (raw.get("queries") or {}).items() if isinstance(e, dict) and "error" in e and k != "person_accounts"]
    for key, entry in (raw.get("queries") or {}).items():
        if isinstance(entry, dict) and entry.get("dropped_columns"):
            warnings.append(f"{key}: left out {', '.join(entry['dropped_columns'])}, which this Flow Tool Kit version does not have")
    for key in refused:
        warnings.append(f"Read refused: {key} ({str(raw['queries'][key].get('error'))[:160]})")
    essential = [k for k in refused if k in ESSENTIAL]
    counts = {"components": len(components), "metadata_components": len(metadata), "record_components": len(records_),
              "packaged_components": sum(1 for c in components if c["packaged"]), "templates": len(templates),
              "pages": sum(len(t["pages"]) for t in templates), "sections": sum(len(p["sections"]) for t in templates for p in t["pages"]),
              "custom_sections": len(custom_sections), "repeated_sections": len(repeats), "mapped_forms": len(mapped),
              "layered_components": sum(1 for c in components if c["uses"]), "tracked_metadata_rows": len(tracked),
              "places_outside_templates": sum(places[k]["places"] for k in PLACE_KINDS), "run_time_forms": len(dynamic)}
    note = f"Some reads were refused ({', '.join(essential)}); what they hold is missing from this catalog" if essential else None
    return {"catalog_version": CATALOG_VERSION, "taken_at": taken_at, "status": "partial" if essential else "ok",
            "status_note": note, "source": raw.get("source"), "org": org, "package": package(raw), "edition": edition,
            "platforms": platforms(raw), "components": components, "templates": templates, "repeated_sections": repeats,
            "mapped_forms": mapped, "placements": places, "run_time_forms": dynamic, "filing": filing(components),
            "brand_kit": brand_kit(raw, templates), "fields_index": fields_index,
            "counts": counts, "problems": problems, "warnings": warnings}


def used_in_text(component):
    """'2 template(s), 1 flow(s), 1 component(s)': every kind of place a component is used."""
    places = component.get("places") or {"templates": component.get("templates", 0)}
    parts = [f"{places.get('templates', 0)} template(s)"]
    for kind, words in (("flows", "flow(s)"), ("lightning_pages", "Lightning page(s)"), ("site_pages", "site page(s)"),
                        ("wrapper_components", "wrapper component(s)")):
        if places.get(kind):
            parts.append(f"{places[kind]} {words}")
    inside = len({u["component"] for u in component.get("used_by_components") or []})
    if inside:
        parts.append(f"{inside} component(s)")
    return ", ".join(parts)


# ---- the readable summary --------------------------------------------------------------------------------------------

def markdown(catalog):
    org = catalog.get("org") or {}
    head = [f"# Flow Tool Kit catalog: {org.get('name') or 'no org'}", "",
            f"Taken {catalog['taken_at']} (UTC). Status: {catalog['status']}." + (f" {catalog['status_note']}" if catalog.get("status_note") else "")]
    if catalog["status"] in ("no org", "no package"):
        return "\n".join(head) + "\n"
    pkg = catalog.get("package") or {}
    plat = catalog.get("platforms") or {}
    on = [name for name, key in (("Outbound Funds", "outbound_funds"), ("Nonprofit Cloud", "nonprofit_cloud"), ("NPSP", "npsp")) if plat.get(key)]
    c = catalog["counts"]
    lines = head + [
        f"Org Id {org.get('id')}, {'sandbox' if org.get('is_sandbox') else org.get('type') or 'org'}. Flow Tool Kit {pkg.get('version') or '(version not read)'}."
        + (f" Edition: {catalog['edition']}." if catalog.get("edition") else "")
        + f" Platforms: {', '.join(on) or 'none found'}." + (" Person accounts on." if plat.get("person_accounts") else ""), "",
        "| What | Count |", "|---|---|",
        f"| Form Components | {c['components']} ({c['metadata_components']} metadata, {c['record_components']} record, {c['packaged_components']} from the package) |",
        f"| Components built from other components | {c['layered_components']} |",
        f"| Form Templates | {c['templates']} ({c['pages']} pages, {c['sections']} sections, {c['custom_sections']} with their own JSON form) |",
        f"| Sections repeated across templates | {c['repeated_sections']} |",
        f"| Mapped forms on other objects | {c['mapped_forms']} |", "",
        f"**Brand kit:** {catalog['brand_kit']['summary']}", ""]
    own = [x for x in catalog["components"] if not x["packaged"]]
    if own:
        lines += ["## Your components", "", "| Component | Shape | Object | Fields | Used in | Built from | Folder | Tags |",
                  "|---|---|---|---|---|---|---|---|"]
        for x in sorted(own, key=lambda x: (-x["templates"], x["name"])):
            built = ", ".join(sorted({u["component"] for u in x["uses"]})) or ""
            lines.append(f"| {x['name']} ({x['label']}) | {x['kind']} | {bare(x['object'])} | {len(x['fields'])} | {used_in_text(x)} | {built} "
                         f"| {x.get('folder') or ''} | {', '.join(x.get('tags') or [])} |")
        lines.append("")
    packaged = sorted((x for x in catalog["components"] if x["packaged"] and x["fields"]), key=lambda x: (-x["templates"], x["label"]))
    if packaged:
        shown = ", ".join(f"{x['label']} ({bare(x['object'])}, {len(x['fields'])} fields)" for x in packaged[:12])
        more = f", and {len(packaged) - 12} more in catalog.json" if len(packaged) > 12 else ""
        lines += [f"Package components you can also reuse: {shown}{more}.", ""]
    if catalog["repeated_sections"]:
        lines += ["## Sections repeated across templates", ""]
        for g in catalog["repeated_sections"]:
            where = "; ".join(f"{s['template']} p{s['page']} '{s['section']}'" for s in g["sections"])
            lines.append(f"- **{g['id']} {g['title']}** on {g['templates']} templates ({bare(g['object'])}: "
                         f"{', '.join(f['label'] or f['field'] for f in g['fields'][:8])}{'...' if len(g['fields']) > 8 else ''}). {where}.")
        lines.append("")
    if catalog["mapped_forms"]:
        lines += ["## Mapped forms (Form Template Mapping)", "", "| Object | Component | Applies to | Mapped | Used in |", "|---|---|---|---|---|"]
        for m in catalog["mapped_forms"]:
            applies = "every conversion" if m["lookup_field"] == "ALL" else f"lookup {bare(m['lookup_field'])}"
            lines.append(f"| {m['object']} | {m['component']} | {applies} | {m['mapped']} of {m['fields']} fields | {m['templates']} template(s) |")
        lines.append("")
    outside = [(x, u) for x in catalog["components"] for u in x["used_in"] if u.get("role") in ROLE_KIND]
    places = catalog.get("placements") or {}
    if outside or places:
        lines += ["## Used outside templates", ""]
        for x, u in sorted(outside, key=lambda pair: (pair[0]["name"], pair[1]["role"], pair[1]["label"])):
            extra = (", inside its own JSON" if u.get("inside_own_json") else "") + (", a copy of the form's JSON" if u.get("copy") else "")
            lines.append(f"- **{x['label']}**: {u['role']} {u['label']} ({u['where']}, {u['via']}{extra})")
        for d in catalog.get("run_time_forms") or []:
            lines.append(f"- A form chosen at run time: {d['role']} {d['label']} ({d['where']}, {d['via']} from {d['variable']})")
        if places.get("note"):
            lines.append(f"- {places['note']}")
        lines.append("")
    if catalog["templates"]:
        label = {x["name"]: x["label"] for x in catalog["components"]}
        lines += ["## Templates", "", "Each section shows its component's label and shape (metadata or record), or how it is built: JSON (its own form, "
                  "fixed to that section), flow, lwc or text.", ""]
        for t in catalog["templates"]:
            lines.append(f"- **{t['name']}**{'' if t['active'] else ' (inactive)'}: " + "; ".join(
                f"p{p['position']} {p['label']}: " + ", ".join(
                    f"{s['title']} [{section_tag(s, label)}]" for s in p["sections"]) for p in t["pages"]))
        lines.append("")
    if catalog["problems"] or catalog["warnings"]:
        lines += ["## Problems and warnings", ""] + [f"- {p}" for p in catalog["problems"] + catalog["warnings"]] + [""]
    return "\n".join(lines)
