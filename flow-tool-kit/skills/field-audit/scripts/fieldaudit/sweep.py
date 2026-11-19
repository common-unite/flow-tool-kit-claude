"""The template sweep: every field reference stored in Flow Tool Kit
configuration, read from raw.json.

Surfaces: section forms in all three sources (metadata, record, JSON built in
place), header and footer forms, table New, Edit and bulk-edit forms, page and
section rules, payment rules, URL parameter mappings, prefill values, Form
Template Sources and their prefill mappings, nullable fields, merge tokens in
template, page and section text, the email templates a template names, the
prefill template records a template or section names, and Form Template
Mapping on forms built on another object.

Only configuration is read, with one narrow exception: a prefill template is a
Form Submission record an admin sets up as configuration, so the records a
template or section names (by Id, and only those) are read to learn which
fields they set and which merge tokens their values hold. No other Form
Submission record is read and nothing is counted.
"""

from __future__ import annotations

import re

from . import COMPONENT_OBJECT, NAMESPACE, SECTION_OBJECT, SUBMISSION_OBJECT
from . import walk
from .names import custom_field_id, email_merge_fields, fold_star, merge_tokens
from .orgreads import ocutil
from .queries import CMT_FIELD_REFS, EMAIL_TEMPLATE_NAMES, SOURCE_POINTERS, field_queries

N = NAMESPACE
val, records, parse_json = ocutil.val, ocutil.records, ocutil.parse_json

# Text the package merges {{tokens}} into, and what each column is on the form.
TEMPLATE_TEXT = {"Confirmation_Page_Message__c": "confirmation message", "Offline_Message__c": "offline message",
                 "Template_Header_Text__c": "template header text", "Template_Footer_Text__c": "template footer text",
                 "Form_Template_Subtitle__c": "template subtitle", "Header_Tags__c": "template header tags",
                 "Review_Page_Label__c": "review page label", "Review_Page_Subtitle__c": "review page subtitle",
                 "Email_Template_Body_Confirmation__c": "confirmation email body"}
PAGE_TEXT = {"Page_Label__c": "page label", "Page_Title__c": "page title", "Details__c": "page details",
             "Description__c": "page description", "Page_Footer__c": "page footer",
             "Header_Title__c": "page header title", "Header_Subtitle__c": "page header subtitle",
             "Header_Text__c": "page header text", "Header_Kicker__c": "page header kicker",
             "Header_Lead__c": "page header lead", "Header_Footer__c": "page header footer",
             "Header_Tags__c": "page header tags"}
SECTION_TEXT = {"Header_Title__c": "section header title", "Header_Subtitle__c": "section header subtitle",
                "Header_Text__c": "section header text", "Header_Kicker__c": "section header kicker",
                "Header_Lead__c": "section header lead", "Header_Footer__c": "section header footer",
                "Header_Tags__c": "section header tags", "Divider_Title__c": "divider title",
                "Divider_Subtitle__c": "divider subtitle", "Component_Section_Text__c": "section text"}
TABLE_FORMS = [("Alternate_FormQualifiedApiName__c", "table New and Edit form"),
               ("Bulk_FormQualifiedApiName__c", "table bulk edit form"),
               ("Edit_FormQualifiedApiName__c", "table edit form")]


def _f(row, column):
    """A packaged column's value, nested or flattened, with or without the prefix."""
    key = N + column
    if isinstance(row, dict) and key in row:  # the usual shape, read without a search
        return row[key]
    return val(row, key)


def _templates(raw):
    return [{"Id": val(r, "Id"), "Name": val(r, "Name") or "", "row": r} for r in records(raw, "templates")]


def _pages(raw):
    return [{"Id": val(r, "Id"), "Name": val(r, "Name") or "", "label": _f(r, "Page_Label__c") or "",
             "template": _f(r, "Form_Template__c"), "row": r} for r in records(raw, "pages")]


def _sections(raw):
    return [{"Id": val(r, "Id"), "Name": val(r, "Name") or "", "title": _f(r, "Title__c") or "",
             "page": _f(r, "Form_Template_Page__c"), "row": r} for r in records(raw, "sections")]


def is_version_snapshot(component):
    """Rows of the Metadata Component record type only track a metadata form's
    versions; they are never a live component (the package filters them the same way)."""
    return val(component, "RecordType.DeveloperName") == "Metadata_Component"


def _dedupe(refs):
    seen, kept = set(), []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            kept.append(ref)
    return kept


def _collector():
    refs = []

    def emit(obj, field, role, snippet, surface=None):
        refs.append((fold_star(obj or ""), fold_star(field or ""), role, snippet or "", surface))
    return refs, emit


def metadata_forms(raw):
    """Form__mdt name -> {label, object, refs[(obj, field, role, snippet, surface)]}."""
    forms = {}
    for row in records(raw, "forms_mdt"):
        name = val(row, "QualifiedApiName")
        if not name:
            continue
        form_object = fold_star(val(row, f"{N}Form_Object__r.{N}Object__r.QualifiedApiName") or "")
        refs, emit = _collector()
        config = parse_json(_f(row, "config__c"))
        if config:  # the form's own settings, including its Form Template Mapping
            walk.walk_config(config, form_object or SUBMISSION_OBJECT, emit)
        forms[name] = {"label": val(row, "Label") or name, "object": form_object, "refs": refs}

    def live(row):
        return not _f(row, "Delete__c")

    for row in records(raw, "sections_mdt"):
        entry = forms.get(val(row, f"{N}Form__r.QualifiedApiName"))
        config = parse_json(_f(row, "config__c"))
        if entry is not None and live(row) and config:
            refs, emit = _collector()
            walk.walk_config(config, entry["object"] or SUBMISSION_OBJECT, emit)
            entry["refs"] += refs

    for row in records(raw, "fields_mdt"):
        entry = forms.get(val(row, f"{N}Form__r.QualifiedApiName"))
        if entry is None or not live(row):
            continue
        # EntityParticle DurableIds hold an entity Id for custom objects, so the
        # field name comes from QualifiedApiName and the object from the row
        row_object = fold_star(val(row, f"{N}Object__r.QualifiedApiName") or entry["object"])
        for column, role in CMT_FIELD_REFS.items():
            field = val(row, f"{N}{column[:-3]}__r.QualifiedApiName")
            if field:
                entry["refs"].append((row_object, fold_star(field), role, "", None))
        alt = val(row, f"{N}Alternative_Field__r.QualifiedApiName")
        if alt:
            alt_object = fold_star(val(row, f"{N}Alternative_Object__r.QualifiedApiName") or row_object)
            entry["refs"].append((alt_object, fold_star(alt), "related-field override / score target", "", None))

    for row in records(raw, "conditions_mdt"):
        entry = forms.get(val(row, f"{N}Form__r.QualifiedApiName"))
        field = val(row, f"{N}fieldName__r.QualifiedApiName")
        if entry is not None and live(row) and field:
            row_object = fold_star(val(row, f"{N}Object__r.QualifiedApiName") or entry["object"])
            entry["refs"].append((row_object, fold_star(field), "rule operand", "form rule", None))

    for entry in forms.values():
        entry["refs"] = _dedupe(entry["refs"])
    return forms


def _component_refs(component):
    """Refs of one record component: its JSON, and the Form Template Mapping
    column (the same map the JSON root may carry, counted once)."""
    refs, emit = _collector()
    form_object = fold_star(_f(component, "ObjectApiName__c") or "")
    config = parse_json(_f(component, "FormConfigJSON__c"))
    if config:
        walk.walk_config(config, form_object or SUBMISSION_OBJECT, emit)
    mapping = walk.parse_submission_map(_f(component, "Submission_Field_Map__c"))
    if mapping:
        walk.emit_mapping(mapping, form_object, emit)
    return _dedupe(refs)


class Resolver:
    """Form name -> (component type, refs, label, key, link path), the way the
    package resolves a name: a metadata form first, then a record component by
    its version Id (``<name>_v<n>``), then the latest live version of that name."""

    def __init__(self, raw):
        self.metadata = metadata_forms(raw)
        self.components = records(raw, "components")
        self.by_id = {val(c, "Id"): c for c in self.components}
        self.latest = {}
        for component in self.components:
            name = _f(component, "QualifiedApiName__c") or ""
            if not name or is_version_snapshot(component):
                continue
            version = _f(component, "Version__c") or 0
            if name not in self.latest or version > (_f(self.latest[name], "Version__c") or 0):
                self.latest[name] = component
        # a section or header names a record component by its version Id (<name>_v<n>)
        self.versions = {_f(c, "VersionId__c"): c for c in self.components
                         if _f(c, "VersionId__c") and not is_version_snapshot(c)}
        self._cache = {}

    def component_refs(self, component):
        key = val(component, "Id")
        if key not in self._cache:
            self._cache[key] = _component_refs(component)
        return self._cache[key]

    def __call__(self, name):
        name = fold_star(name or "").strip()
        if not name:
            return None
        if name in self.metadata:
            entry = self.metadata[name]
            path = (f"/lightning/n/{N}Form_Builder?c__FormQualifiedApiName={name}"
                    f"&c__ObjectApiName={entry['object'] or SUBMISSION_OBJECT}")
            return "Metadata", entry["refs"], entry["label"], name, path
        component = self.versions.get(name) or self.latest.get(name)
        if component is not None:
            label = _f(component, "Label__c") or val(component, "Name") or name
            path = f"/lightning/r/{COMPONENT_OBJECT}/{val(component, 'Id')}/view"
            return "Record", self.component_refs(component), label, val(component, "Id"), path
        return None


def _emit_form(resolved, surface, context, emit, coverage, name, role_note=""):
    if resolved is None:
        if name:
            coverage.append({"store": surface, "status": "missing",
                             "detail": f"form '{name}' was not found as a metadata form or a record component"})
        return
    component_type, refs, label, key, path = resolved
    for obj, field, role, snippet, ref_surface in refs:
        emit(walk.reference(obj, field, ref_surface or surface,
                            role if ref_surface else (role_note or role), component_type=component_type,
                            component_key=key, component_label=label, snippet=snippet,
                            component_path=path, **context))


def _emit_section_json(wrapper, section, context, emit, component=None, label=""):
    refs, collect = _collector()
    walk.walk_config(wrapper.get("config"), wrapper.get("object"), collect)
    if component is not None:
        component_type, key = "Record", val(component, "Id")
        path = f"/lightning/r/{COMPONENT_OBJECT}/{key}/view"
    else:  # the JSON lives on the section record itself
        component_type, key = "JSON", section["Id"]
        path = f"/lightning/r/{SECTION_OBJECT}/{key}/view"
    for obj, field, role, snippet, surface in _dedupe(refs):
        emit(walk.reference(obj, field, surface or "Section Form", role, component_type=component_type,
                            component_key=key, component_label=label or section["title"],
                            snippet=snippet, component_path=path, **context))


def _emit_rule(text, surface, context, emit, coverage, store):
    rule = walk.parse_rule(text or "")
    if rule and rule.get("status") == "unparseable":
        coverage.append({"store": store, "status": "unparseable", "detail": _where(context)})
    elif rule and rule.get("status") == "parsed":
        for field, snippet in rule["hits"]:
            emit(walk.reference(rule["object"], field, surface, "rule operand", snippet=snippet, **context))


def _emit_merge(text, default_object, place, context, emit):
    for token_object, token in merge_tokens(text or ""):
        emit(walk.reference(token_object or default_object, token, "Merge Token", f"merge token in {place}",
                            snippet=text or "", **context))


def _where(context):
    parts = [(context.get("template") or {}).get("Name"), (context.get("page") or {}).get("label"),
             (context.get("section") or {}).get("title")]
    return " / ".join(p for p in parts if p) or "(no template)"


def sweep(raw, resolve=None):
    """(references, coverage, resolver) for everything stored in templates and forms."""
    resolve = resolve or Resolver(raw)
    references, coverage = [], []
    emit = references.append
    templates, pages, sections = _templates(raw), _pages(raw), _sections(raw)
    template_by_id = {t["Id"]: t for t in templates}
    page_by_id = {p["Id"]: p for p in pages}

    # ---- templates
    for template in templates:
        row, context = template["row"], {"template": template}
        mapping = walk.parse_url_mapping(_f(row, "URL_Parameter_Mapping__c") or "[]")
        if mapping is None:
            coverage.append({"store": "URL Parameter Mapping", "status": "unparseable", "detail": template["Name"]})
        for field, param in mapping or []:
            emit(walk.reference(SUBMISSION_OBJECT, field, "URL Parameter", "URL parameter target",
                                snippet=f"?{param}=", **context))
        prefill_values = parse_json(_f(row, "Prefill_Values__c"))
        if (_f(row, "Prefill_Values__c") or "").strip() and not prefill_values:
            coverage.append({"store": "Prefill Values", "status": "unparseable", "detail": template["Name"]})
        for key in prefill_values:
            emit(walk.reference(SUBMISSION_OBJECT, key, "Prefill Values", "prefill value key", **context))
        for obj, field in walk.parse_nullable(_f(row, "Nullable_Fields__c")):
            emit(walk.reference(obj or SUBMISSION_OBJECT, field, "Nullable", "may be cleared by a blank answer",
                                **context))
        _emit_rule(_f(row, "Payment_Conditions__c"), "Payment Rule", context, emit, coverage, "Payment Conditions")
        for surface, column in (("Header Form", "FormQualifiedApiName_Header__c"),
                                ("Footer Form", "FormQualifiedApiName_Footer__c")):
            name = _f(row, column)
            _emit_form(resolve(name), surface, context, emit, coverage, name)
        for column, place in TEMPLATE_TEXT.items():
            _emit_merge(_f(row, column), SUBMISSION_OBJECT, place, context, emit)

    # ---- pages
    for page in pages:
        row = page["row"]
        context = {"template": template_by_id.get(page["template"]), "page": page}
        _emit_rule(_f(row, "Conditional_Logic__c"), "Page Rule", context, emit, coverage, "Page Conditional Logic")
        for column, place in PAGE_TEXT.items():
            _emit_merge(_f(row, column), SUBMISSION_OBJECT, place, context, emit)

    # ---- sections, in all three sources
    stats = {"Metadata": 0, "Record": 0, "JSON": 0, "other": 0}
    for section in sections:
        row = section["row"]
        page = page_by_id.get(section["page"]) or {}
        context = {"template": template_by_id.get(page.get("template")), "page": page, "section": section}
        wrapper = walk.parse_section_wrapper(_f(row, "FormConfigJSON__c") or "")
        mirror = _f(row, "FormQualifiedApiName__c")
        if wrapper["status"] == "unparseable":
            coverage.append({"store": "Section form JSON", "status": "unparseable", "detail": _where(context)})
        elif wrapper["status"] == "blank":
            if mirror:  # a blank JSON falls back to the name field
                _emit_form(resolve(mirror), "Section Form", context, emit, coverage, mirror)
                stats["Metadata" if mirror in resolve.metadata else "Record"] += 1
            else:
                stats["other"] += 1
        elif wrapper["status"] == "legacy_raw":
            _emit_section_json(wrapper, section, context, emit)
            stats["JSON"] += 1
        elif wrapper.get("mode") == "component" or (wrapper.get("form_name") and not wrapper.get("config")):
            # the wrapper names the form; the name field is only a mirror of it
            name = wrapper.get("form_name") or mirror
            _emit_form(resolve(name), "Section Form", context, emit, coverage, name)
            stats["Metadata" if fold_star(name or "") in resolve.metadata else "Record"] += 1
        elif wrapper.get("config") is not None:
            component = resolve.by_id.get(_f(row, "Form_Component__c"))
            if component is not None and not is_version_snapshot(component):
                label = _f(component, "Label__c") or val(component, "Name") or ""
                _emit_section_json(wrapper, section, context, emit, component, label)
                stats["Record"] += 1
            else:  # a lookup to a version snapshot is JSON built in place, as the package treats it
                _emit_section_json(wrapper, section, context, emit)
                stats["JSON"] += 1
        else:
            stats["other"] += 1

        for column, role in TABLE_FORMS:
            name = _f(row, column)
            if name:
                _emit_form(resolve(name), "Table Form", context, emit, coverage, name, role_note=role)
        _emit_rule(_f(row, "Conditional_Logic__c"), "Section Rule", context, emit, coverage,
                   "Section Conditional Logic")
        for column, place in SECTION_TEXT.items():
            _emit_merge(_f(row, column), SUBMISSION_OBJECT, place, context, emit)
    coverage.append({"store": "Page sections", "status": "parsed",
                     "detail": f"{len(sections)} sections: {stats['Metadata']} metadata forms, {stats['Record']} "
                               f"record components, {stats['JSON']} built in place, {stats['other']} with no form"})
    coverage.append({"store": "Form Templates", "status": "parsed",
                     "detail": f"{len(templates)} templates, {len(pages)} pages"})

    _sweep_sources(raw, emit, coverage)
    _sweep_email_templates(raw, templates, emit, coverage)
    _sweep_prefill_templates(raw, templates, sections, template_by_id, page_by_id, emit, coverage)
    _sweep_mapped_components(resolve, references, emit, coverage)
    return references, coverage, resolve


def _sweep_mapped_components(resolve, references, emit, coverage):
    """Form Template Mapping on components no template section uses yet still
    names real fields; list it so the dictionary shows every mapped pair."""
    placed = {r["component_key"] for r in references if r["component_key"]}
    count = 0
    for name, entry in resolve.metadata.items():
        if name in placed:
            continue
        for obj, field, role, snippet, surface in entry["refs"]:
            if surface == walk.MAPPING_SURFACE:
                emit(walk.reference(obj, field, surface, role + " (form not placed in a template)",
                                    component_type="Metadata", component_key=name,
                                    component_label=entry["label"], snippet=snippet))
                count += 1
    for name, component in resolve.latest.items():
        if val(component, "Id") in placed:
            continue
        for obj, field, role, snippet, surface in resolve.component_refs(component):
            if surface == walk.MAPPING_SURFACE:
                emit(walk.reference(obj, field, surface, role + " (form not placed in a template)",
                                    component_type="Record", component_key=val(component, "Id"),
                                    component_label=_f(component, "Label__c") or name, snippet=snippet,
                                    component_path=f"/lightning/r/{COMPONENT_OBJECT}/{val(component, 'Id')}/view"))
                count += 1
    if count:
        coverage.append({"store": "Form Template Mapping", "status": "parsed",
                         "detail": f"{count} mapped fields on forms no template places yet"})


# ---- Form Template Sources -------------------------------------------------------------------------------------------

def _field_names_by_id(raw, sobject):
    """15-character custom field Id -> API name, from the object's FieldDefinition rows."""
    return {custom_field_id(val(r, "DurableId")): val(r, "QualifiedApiName")
            for r in records(raw, "fields:" + sobject) if custom_field_id(val(r, "DurableId"))}


def _source_rows(raw):
    for row in records(raw, "sources_mdt"):
        yield row, val(row, f"{N}Source_Object__r.QualifiedApiName") or ""


def sources(raw):
    """Each Form Template Source: its object, pointer fields and the Form
    Submission lookup back to it. A pointer to a custom field arrives as
    ``Object.00N...``; its name comes from the object's FieldDefinition rows."""
    found = []
    for row, source_object in _source_rows(raw):
        names = _field_names_by_id(raw, source_object)
        pointers = {}
        for column in SOURCE_POINTERS:
            value = _f(row, column) or ""
            if not value:
                continue
            field = value.split(".", 1)[1] if "." in value else value
            pointers[column] = names.get(field[:15], field) if field.startswith("00N") else field
        found.append({"name": val(row, "QualifiedApiName") or "", "object": source_object,
                      "pointers": pointers, "lookup": _f(row, "Source_Lookup_Field__c") or ""})
    return found


def _sweep_sources(raw, emit, coverage):
    if not ocutil.ran(raw, "sources_mdt") or ocutil.failed(raw, "sources_mdt"):
        coverage.append({"store": "Form Template Sources", "status": "not_captured",
                         "detail": "the source settings could not be read"})
        return
    for source in sources(raw):
        source_object = source["object"]
        if not source_object:
            continue
        snippet = f"source {source['name']}"
        for column, field in source["pointers"].items():
            logical = column[:-len("_Field__c")].replace("_", " ").lower()
            emit(walk.reference(source_object, field, "Source Config", f"source pointer ({logical})",
                                snippet=snippet))
        if source["lookup"]:
            emit(walk.reference(SUBMISSION_OBJECT, source["lookup"], "Source Config",
                                "source lookup on Form Submission", snippet=snippet))
        mapping_field = source["pointers"].get("Prefill_Mapping_Field__c")
        key = f"source_records:{source_object}"
        if not mapping_field or not ocutil.ran(raw, key):
            continue
        if ocutil.failed(raw, key):
            coverage.append({"store": f"Source records ({source_object})", "status": "missing",
                             "detail": str(raw["queries"][key].get("error"))[:200]})
            continue
        rows, parsed = records(raw, key), 0
        for row in rows:
            text = val(row, mapping_field) or ""
            if not text.strip():
                continue
            mapping = walk.parse_prefill_mapping(text, source_object)
            if mapping is None:
                coverage.append({"store": f"{source_object}.{mapping_field}", "status": "unparseable",
                                 "detail": f"record {val(row, 'Id')}"})
                continue
            parsed += 1
            for entry in mapping:
                live = " (live)" if entry["live"] else ""
                emit(walk.reference(SUBMISSION_OBJECT, entry["target"], "Source Mapping", "mapping target" + live,
                                    snippet=f"{val(row, 'Id') or ''}: {entry['path']}"))
                if entry["path"]:
                    emit(walk.reference(source_object, entry["path"], "Source Mapping", "mapping source path" + live,
                                        snippet=f"{val(row, 'Id') or ''} -> {entry['target']}"))
        coverage.append({"store": f"Source mappings ({source_object})", "status": "parsed",
                         "detail": f"{parsed} of {len(rows)} records carry a mapping"})


# ---- email templates ---------------------------------------------------------------------------------------------

def email_template_names(templates):
    """Developer name -> [(template, which email)], from the Email Template Name fields."""
    named = {}
    for template in templates:
        for column, email in EMAIL_TEMPLATE_NAMES.items():
            name = (_f(template["row"], column) or "").strip()
            if name:
                named.setdefault(name, []).append((template, email))
    return named


def _newest_email_templates(raw):
    """Developer name (and Id) -> the EmailTemplate row the send flows use: the
    newest with that name, the way the package resolves one."""
    newest = {}
    for row in records(raw, "email_templates"):
        name = val(row, "DeveloperName") or ""
        if name not in newest or (val(row, "LastModifiedDate") or "") > (val(newest[name], "LastModifiedDate") or ""):
            newest[name] = row
    by_id = {}
    for row in newest.values():
        by_id[(val(row, "Id") or "")[:15]] = row
    return newest, by_id


def _related_object(row):
    related = val(row, "RelatedEntityType") or ""
    if not related:  # a Visualforce template names it in its markup
        found = re.search(r'relatedToType\s*=\s*"([^"]+)"', val(row, "Markup") or "")
        related = found.group(1) if found else ""
    return related


def _sweep_email_templates(raw, templates, emit, coverage):
    """Merge fields in the stored email templates a Form Template names
    (Lightning {{{Object.Field}}}, Classic {!Object.Field}, Visualforce
    {!relatedTo.Field}), read from the template's subject and bodies."""
    named = email_template_names(templates)
    if not named:
        return
    if not ocutil.ran(raw, "email_templates") or ocutil.failed(raw, "email_templates"):
        error = (raw.get("queries", {}).get("email_templates") or {}).get("error")
        coverage.append({"store": "Email templates", "status": "not_captured",
                         "detail": f"{len(named)} named; not read" + (f": {str(error)[:160]}" if error else "")})
        return
    newest, by_id = _newest_email_templates(raw)
    found = 0
    for name, uses in named.items():
        row = newest.get(name) or by_id.get(name[:15])
        if row is None:
            coverage.append({"store": "Email templates", "status": "missing",
                             "detail": f"'{name}' ({', '.join(email for _, email in uses)}) was not found as an "
                                       f"email template you can read"})
            continue
        found += 1
        related = _related_object(row)
        key, label = val(row, "Id") or "", val(row, "DeveloperName") or name
        for part in ("Subject", "HtmlValue", "Body", "Markup"):
            for obj, field in email_merge_fields(val(row, part) or "", related):
                for template, email in uses:
                    emit(walk.reference(obj, field, "Email Template", f"merge field in the {email} template",
                                        template=template, component_type="Email Template", component_key=key,
                                        component_label=label, snippet=f"{part}: {obj}.{field}",
                                        component_path=f"/lightning/setup/CommunicationTemplatesEmail/page?address="
                                                       f"%2F{key}" if key else ""))
    coverage.append({"store": "Email templates", "status": "parsed",
                     "detail": f"{found} of {len(named)} named email templates read (subject, HTML, text and "
                               f"Visualforce bodies)"})


# ---- prefill template records ----------------------------------------------------------------------------------------

# Package fields the form resets or drops when it seeds a submission from a
# prefill template, so a value there sets nothing.
PREFILL_RESET = {N + name for name in ("Form_Template__c", "IsPrefillTemplate__c", "Status__c", "Tag_Internal__c",
                                       "Internal_Description__c", "Submission_Date__c",
                                       "Internal_Form_Start_Date_Time__c")}
_NOT_SETTABLE = ("Formula", "Roll-Up", "Auto Number")
PREFILL_CHUNK = 100


def prefill_template_ids(templates, sections):
    """Prefill template record Id -> [(template, section or None, note)], for every
    template (unless Skip Prefill) and section that names one. Only these
    records are ever read."""
    named = {}
    for template in templates:
        record_id = _f(template["row"], "Prefill_Template__c")
        if record_id and not _f(template["row"], "Skip_Prefill__c"):
            note = " (not applied while Prefill Values is set)" if (_f(template["row"], "Prefill_Values__c") or "").strip() else ""
            named.setdefault(record_id, []).append((template, None, note))
    for section in sections:
        record_id = _f(section["row"], "Prefill_Template__c")
        if record_id:
            named.setdefault(record_id, []).append((None, section, ""))
    return named


def prefill_fields(raw):
    """The Form Submission fields a prefill template can set: custom fields that
    are not formulas, roll-ups or auto numbers, and not ones the form resets."""
    fields = []
    for row in records(raw, "fields:" + SUBMISSION_OBJECT):
        name = val(row, "QualifiedApiName") or ""
        if name.endswith("__c") and name not in PREFILL_RESET \
                and not (val(row, "DataType") or "").startswith(_NOT_SETTABLE):
            fields.append(name)
    return fields


def prefill_queries(raw):
    """The one read of Form Submission records: the prefill templates a template
    or section names, by Id, and only the fields a prefill template can set."""
    ids = sorted(prefill_template_ids(_templates(raw), _sections(raw)))
    if not ids or not ocutil.ran(raw, "fields:" + SUBMISSION_OBJECT) \
            or ocutil.failed(raw, "fields:" + SUBMISSION_OBJECT):
        return []
    columns = ", ".join(["Id"] + prefill_fields(raw))
    queries = []
    for index in range(0, len(ids), PREFILL_CHUNK):
        chunk = ids[index:index + PREFILL_CHUNK]
        queries.append({"key": f"prefill_templates:{index // PREFILL_CHUNK + 1}", "optional": True,
                        "soql": f"SELECT {columns} FROM {SUBMISSION_OBJECT} WHERE Id IN ({ocutil.soql_list(chunk)})",
                        "why": "the prefill template records templates and sections name (by Id, nothing else): "
                               "which fields they set and which merge tokens they hold"})
    return queries


def _sweep_prefill_templates(raw, templates, sections, template_by_id, page_by_id, emit, coverage):
    named = prefill_template_ids(templates, sections)
    if not named:
        return
    keys = [k for k in raw.get("queries", {}) if k.startswith("prefill_templates:")]
    failed = [k for k in keys if ocutil.failed(raw, k)]
    if not keys or failed:
        error = str((raw["queries"][failed[0]].get("error") if failed else "") or "")[:160]
        coverage.append({"store": "Prefill Template records", "status": "not_captured",
                         "detail": f"{len(named)} prefill templates named; not read" + (f": {error}" if error else "")})
        return
    rows = {(val(r, "Id") or "")[:15]: r for k in keys for r in records(raw, k)}
    read = 0
    for record_id, uses in named.items():
        row = rows.get(record_id[:15])
        if row is None:
            coverage.append({"store": "Prefill Template records", "status": "missing",
                             "detail": f"prefill template {record_id} was not found or cannot be read"})
            continue
        read += 1
        for template, section, note in uses:
            if section is not None:
                page = page_by_id.get(section["page"]) or {}
                context = {"template": template_by_id.get(page.get("template")), "page": page, "section": section}
            else:
                context = {"template": template}
            key = dict(component_type="Prefill Template", component_key=record_id,
                       component_label=f"prefill template {record_id}",
                       component_path=f"/lightning/r/{SUBMISSION_OBJECT}/{record_id}/view")
            for column, value in row.items():
                field = fold_star(column)
                if field == "Id" or "." in field or field.startswith("attributes") or value is None or value is False or value == "" \
                        or isinstance(value, dict):
                    continue
                emit(walk.reference(SUBMISSION_OBJECT, field, "Prefill Template", "prefill template sets it" + note,
                                    snippet=f"prefill template {record_id} sets {field}", **key, **context))
                if isinstance(value, str) and "{{" in value:
                    for token_object, token in merge_tokens(value):
                        emit(walk.reference(token_object or SUBMISSION_OBJECT, token, "Prefill Template",
                                            "merge token in a prefill template value" + note,
                                            snippet=f"{{{{{token}}}}} in {field}", **key, **context))
    coverage.append({"store": "Prefill Template records", "status": "parsed",
                     "detail": f"{read} of {len(named)} named prefill templates read, by Id: only the fields they set "
                               f"and merge tokens in their values. No other Form Submission record is read."})


# ---- the reads this sweep needs after the configuration ---------------------------------------------------------

def _email_template_query(raw):
    names = sorted(email_template_names(_templates(raw)))
    if not names:
        return []
    ids = [n for n in names if re.match(r"^00X[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$", n)]
    where = f"DeveloperName IN ({ocutil.soql_list(names)})" + (f" OR Id IN ({ocutil.soql_list(ids)})" if ids else "")
    return [{"key": "email_templates", "optional": True,
             "soql": "SELECT Id, DeveloperName, Name, NamespacePrefix, TemplateType, UiType, RelatedEntityType, "
                     f"LastModifiedDate, Subject, HtmlValue, Body, Markup FROM EmailTemplate WHERE {where}",
             "why": "the email templates Form Templates name (confirmation, save progress, start and resume link): "
                    "their merge fields"}]


def dependent_queries(raw, options):
    queries = []
    pointing = sorted({obj for row, obj in _source_rows(raw) if obj and any(
        "00N" in (_f(row, column) or "") for column in SOURCE_POINTERS)})
    for sobject in pointing:  # the names behind the source pointers, before the source records are read
        queries += field_queries(sobject, f"fields of {sobject}, to name the fields a Form Template Source points at")
    queries += _email_template_query(raw) + prefill_queries(raw)
    if any(not ocutil.ran(raw, q["key"]) for q in queries):
        return queries
    for source in sources(raw):
        mapping_field = source["pointers"].get("Prefill_Mapping_Field__c")
        # never a Form Submission record: its columns are submission data
        if source["object"] and source["object"] != SUBMISSION_OBJECT and mapping_field \
                and not mapping_field.startswith("00N"):
            queries.append({"key": f"source_records:{source['object']}", "optional": True,
                            # only the Id and the mapping column, a configuration value an admin sets; a long
                            # text field cannot be filtered, so read the newest records and skip blanks
                            "soql": f"SELECT Id, {mapping_field} FROM {source['object']} "
                                    f"ORDER BY LastModifiedDate DESC LIMIT {int(options['source_limit'])}",
                            "why": f"the prefill mapping configured on {source['object']} records (only the "
                                   f"mapping column)"})
    return queries
