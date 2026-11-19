"""What the audit reads, in passes, for every runner: the Salesforce CLI
(``audit.py collect``) and a Salesforce connector in chat (``audit.py
next-queries``, the connector runs each query, ``audit.py add``).

``next_queries(raw)`` returns the queries still to run given what raw.json
holds. A later pass depends on an earlier one (which objects the forms use,
which flows exist, which fields nothing references), so a runner calls it until
it returns [].

Each query is ``{key, soql, tooling, optional, why}``, plus ``dropped`` when it
is a retry without a column the org refused. Rows are read with org-catalog's
``val``, so nested (CLI) and flattened (connector) rows both work.

The audit answers only whether a field is referenced in Flow Tool Kit, and
where. It reads configuration (Form Templates, pages, sections, Form
Components, Flow Tool Kit custom metadata, the email templates a template
names), field definitions and the metadata of the flows that decide which
flows are Flow Tool Kit's. It reads one kind of Form Submission record, by
approved exception: the prefill templates a template or section names, by Id,
for the fields they set and the merge tokens they hold. No other submission,
no counts, no samples. Apex, reports, page
layouts and other general metadata are not read: Setup's Where is this used?
covers them.
"""

from __future__ import annotations

import re

from . import NAMESPACE, SUBMISSION_OBJECT
from .orgreads import ocqueries, ocutil

N = NAMESPACE
val, records, ran, failed, soql_list = ocutil.val, ocutil.records, ocutil.ran, ocutil.failed, ocutil.soql_list

DEFAULT_OPTIONS = {"objects": [SUBMISSION_OBJECT], "flows": "all", "source_limit": 300}
FLOW_SCOPES = ("all", "named", "none")
MAX_RETRIES = 45

# A Form Template names one conversion flow per target: the Conversion_Map_Flow_<target>__c
# picklist (Default, or a flow's API name) and the read-only FlowApiName_<target>__c formula
# that resolves it. Default resolves through this Form Template Conversion Mapping Default record.
CONVERSION_TARGETS = {"Account": "Account", "CampaignMember": "CampaignMember", "Case": "Case",
                      "Contact1": "Primary_Contact", "Contact2": "Alternate_Contact", "Controller": "Controller",
                      "FileUpload": "FileUpload", "Lead1": "Primary_Lead", "Lead2": "Alternate_Lead",
                      "Opportunity": "Opportunity", "Order": "Order"}
# A page section's Conversion_Rule__c (by its first word) -> the default record its
# FlowApiName_Related__c formula falls back to when Conversion_Map_Flow__c is Default.
SECTION_RULE_DEFAULTS = {"Contact1": "Primary_Contact", "Contact2": "Alternate_Contact",
                         "Lead1": "Primary_Lead", "Lead2": "Alternate_Lead", "Case": "Case"}

# The stored email templates a Form Template names, by developer name (the send
# flows take the newest template with that name), and which email each sends.
EMAIL_TEMPLATE_NAMES = {"Email_Template_Name_Confirmation__c": "confirmation email",
                        "Email_Template_Name_Saved__c": "save progress email",
                        "Email_Template_Name_Start_Form__c": "start link email",
                        "Email_Template_Name_Resume_Form__c": "resume link email"}

TEMPLATE_COLUMNS = ["Id", "Name", N + "URL_Parameter_Mapping__c", N + "Prefill_Values__c",
                    N + "Prefill_Template__c", N + "Nullable_Fields__c", N + "Skip_Prefill__c",
                    N + "FormQualifiedApiName_Header__c", N + "FormQualifiedApiName_Footer__c",
                    N + "Payment_Conditions__c", N + "Confirmation_Page_Message__c",
                    N + "Template_Header_Text__c", N + "Template_Footer_Text__c",
                    N + "Offline_Message__c", N + "Form_Template_Subtitle__c", N + "Header_Tags__c",
                    N + "Review_Page_Label__c", N + "Review_Page_Subtitle__c",
                    N + "Email_Template_Body_Confirmation__c", N + "Prefill_Flow_Api_Name__c"] \
    + [N + column for column in EMAIL_TEMPLATE_NAMES] \
    + [N + f"Conversion_Map_Flow_{target}__c" for target in CONVERSION_TARGETS] \
    + [N + f"FlowApiName_{target}__c" for target in CONVERSION_TARGETS]
PAGE_COLUMNS = ["Id", "Name", N + "Page_Label__c", N + "Form_Template__c", N + "Conditional_Logic__c",
                N + "Page_Title__c", N + "Details__c", N + "Page_Footer__c", N + "Header_Title__c",
                N + "Header_Subtitle__c", N + "Header_Kicker__c", N + "Header_Lead__c",
                N + "Header_Footer__c", N + "Header_Text__c", N + "Header_Tags__c", N + "Description__c"]
SECTION_COLUMNS = ["Id", "Name", N + "Title__c", N + "Form_Template_Page__c", N + "Conditional_Logic__c",
                   N + "FormConfigJSON__c", N + "FormQualifiedApiName__c", N + "Form_Component__c",
                   N + "Alternate_FormQualifiedApiName__c", N + "Bulk_FormQualifiedApiName__c",
                   N + "Edit_FormQualifiedApiName__c", N + "Prefill_Template__c", N + "Header_Title__c",
                   N + "Header_Subtitle__c", N + "Header_Kicker__c", N + "Header_Lead__c",
                   N + "Header_Footer__c", N + "Header_Tags__c", N + "Header_Text__c", N + "Divider_Title__c",
                   N + "Divider_Subtitle__c", N + "Component_Section_Text__c", N + "Conversion_Rule__c", N + "Conversion_Map_Flow__c",
                   N + "FlowApiName_Related__c", N + "Component_Type__c", N + "FlowApiName__c"]
COMPONENT_COLUMNS = ["Id", "Name", "RecordType.DeveloperName", N + "Label__c", N + "QualifiedApiName__c",
                     N + "VersionId__c", N + "Version__c", N + "ObjectApiName__c", N + "FormConfigJSON__c",
                     N + "Submission_Field_Map__c"]

# Form_Field__mdt columns that point at a field through an EntityParticle
# relationship, and the role each plays.
CMT_FIELD_REFS = {
    "fieldName__c": "input field",
    "minDateFieldName__c": "min-date bound",
    "maxDateFieldName__c": "max-date bound",
    "columnClassFieldReference__c": "column class driver",
    "columnIconNameFieldReference__c": "column icon driver",
    "columnUrlLabelOverrideFieldReference__c": "column URL label driver",
}
SOURCE_POINTERS = ["Active_Field__c", "Banner_Image_URL_Field__c", "Confirmation_Message_Field__c",
                   "Email_Template_Field__c", "End_Date_Field__c", "Form_Template_Field__c", "Name_Field__c",
                   "Offline_Message_Field__c", "Prefill_Flow_Field__c", "Prefill_Mapping_Field__c",
                   "Prefill_Template_Field__c", "Start_Date_Field__c", "Submit_Button_Label_Field__c",
                   "Subtitle_Field__c", "Theme_Field__c"]


def _select(columns, sobject, where=""):
    return f"SELECT {', '.join(columns)} FROM {sobject}" + (f" WHERE {where}" if where else "")


def field_queries(sobject, why):
    """FieldDefinition (every field, even ones the running user cannot read) and
    EntityParticle (labels and help text) for one object."""
    return [
        {"key": "fields:" + sobject, "tooling": True,
         "soql": "SELECT QualifiedApiName, Label, DataType, Description, DurableId, SecurityClassification, "
                 f"ComplianceGroup, BusinessStatus FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{sobject}'",
         "why": why},
        {"key": "particles:" + sobject, "tooling": True, "optional": True,
         "soql": "SELECT QualifiedApiName, Label, DataType, InlineHelpText FROM EntityParticle "
                 f"WHERE EntityDefinition.QualifiedApiName = '{sobject}'",
         "why": f"labels and help text of {sobject} fields"},
    ]


FIRST = [
    {"key": "org", "soql": "SELECT Id, Name, IsSandbox, OrganizationType, NamespacePrefix FROM Organization",
     "why": "which org this audit describes"},
    {"key": "ftk", "soql": f"SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '{N}Form_Template__c'",
     "why": "whether Flow Tool Kit is installed"},
]


def config_queries(options):
    queries = [
        {"key": "templates", "soql": _select(TEMPLATE_COLUMNS, N + "Form_Template__c"),
         "why": "Form Templates: URL parameters, prefill, nullable fields, header and footer forms, payment rules, "
                "merge text, the email templates and the conversion and prefill flows each names"},
        {"key": "pages", "soql": _select(PAGE_COLUMNS, N + "Form_Template_Page__c"),
         "why": "template pages: page rules and header merge text"},
        {"key": "sections", "soql": _select(SECTION_COLUMNS, N + "Form_Template_Page_Section__c"),
         "why": "page sections: the form each shows, section rules, table forms, merge text, conversion flow, and the "
                "screen flow a Flow Section shows"},
        {"key": "components", "soql": _select(COMPONENT_COLUMNS, N + "Form_Component__c"),
         "why": "record Form Components with their JSON and Form Template Mapping"},
        {"key": "forms_mdt",
         "soql": f"SELECT QualifiedApiName, Label, {N}Form_Object__r.{N}Object__r.QualifiedApiName, {N}config__c "
                 f"FROM {N}Form__mdt",
         "why": "metadata Form Components (and the Form Template Mapping in their config)"},
        {"key": "sections_mdt", "optional": True,
         "soql": f"SELECT QualifiedApiName, {N}Form__r.QualifiedApiName, {N}Delete__c, {N}config__c FROM {N}Form_Section__mdt",
         "why": "section settings of metadata components (score targets, merge text)"},
        {"key": "fields_mdt",
         "soql": f"SELECT QualifiedApiName, {N}Form__r.QualifiedApiName, {N}Object__r.QualifiedApiName, "
                 + ", ".join(f"{N}{column[:-3]}__r.QualifiedApiName" for column in CMT_FIELD_REFS)
                 + f", {N}Alternative_Field__r.QualifiedApiName, {N}Alternative_Object__r.QualifiedApiName, "
                   f"{N}Delete__c FROM {N}Form_Field__mdt",
         "why": "fields of metadata components and every field they point at"},
        {"key": "conditions_mdt",
         "soql": f"SELECT {N}Form__r.QualifiedApiName, {N}fieldName__r.QualifiedApiName, {N}Object__r.QualifiedApiName, "
                 f"{N}Delete__c FROM {N}Form_Conditional_Logic_Condition__mdt",
         "why": "rule conditions of metadata components"},
        {"key": "sources_mdt", "optional": True,
         "soql": f"SELECT QualifiedApiName, {N}Source_Object__r.QualifiedApiName, {N}Source_Lookup_Field__c, "
                 + ", ".join(N + column for column in SOURCE_POINTERS) + f" FROM {N}Form_Template_Source__mdt",
         "why": "Form Template Sources: which source-object fields drive a form"},
    ]
    if options["flows"] != "none":
        queries.append({"key": "conversion_defaults", "optional": True,
                        "soql": f"SELECT DeveloperName, {N}Flow_API_Name__c "
                                f"FROM {N}Form_Template_Conversion_Mapping_Default__mdt",
                        "why": "the conversion flow a template or section uses when its Conversion Map Flow is Default"})
        queries.append({"key": "flow_definitions", "optional": True,
                        "soql": "SELECT ApiName, Label, ProcessType, ActiveVersionId, LatestVersionId, NamespacePrefix "
                                "FROM FlowDefinitionView WHERE ProcessType IN ('Flow', 'AutoLaunchedFlow', "
                                "'CustomEvent', 'InvocableProcess')",
                        "why": "the org's flows, to find the Flow Tool Kit ones"})
    for sobject in options["objects"]:
        queries += field_queries(sobject, f"every {sobject} field, including ones you cannot read")
    return queries


# ---- retries -------------------------------------------------------------------------------------------------------

_RELATIONSHIP = re.compile(r"Didn't understand relationship '([A-Za-z0-9_]+)'")


def _drop_item(soql, column):
    """The SOQL without a select item that is the column, a path ending in it,
    or a path through the relationship named."""
    head, sep, tail = soql.partition(" FROM ")
    if not sep or not head.upper().startswith("SELECT "):
        return None
    items = [item.strip() for item in head[len("SELECT "):].split(",")]
    low = column.lower()

    def hit(item):
        target = item.lower()
        return target == low or target.endswith("." + low) or target.startswith(low + ".")

    kept = [item for item in items if not hit(item)]
    if len(kept) == len(items) or not kept:
        return None
    return "SELECT " + ", ".join(kept) + sep + tail


def retry_without(soql, error):
    """(soql without the column the error names, that column, why) or None.

    Covers a column an older package lacks or the running user cannot read
    (``No such column``) and a relationship an older package lacks; why is
    "missing" for both."""
    message = str(error or "")
    found = ocqueries.MISSING_COLUMN.search(message)
    if found:
        column = found.group(1)
        return (ocqueries.without_missing_column(soql, message) or _drop_item(soql, column)), column, "missing"
    found = _RELATIONSHIP.search(message)
    if found:
        return _drop_item(soql, found.group(1)), found.group(1), "missing"
    return None


def _retry(raw, key):
    """The next attempt at a query that failed on a column it can do without."""
    entry = raw["queries"][key]
    if not entry.get("soql") or len(entry.get("dropped_columns") or []) >= MAX_RETRIES:
        return None
    attempt = retry_without(entry["soql"], entry.get("error"))
    if not attempt or not attempt[0]:
        return None
    soql, column, reason = attempt
    query = dict(entry.get("query") or {})
    query.update({"key": key, "soql": soql,
                  "dropped": (entry.get("dropped_columns") or []) + [column],
                  "drop_reasons": dict(entry.get("drop_reasons") or {}, **{column: reason})})
    return query


def store(raw, query, result):
    """Put one query's outcome into raw.json: its rows or its error, the SOQL that
    ran, and every column left out on the way (with why), so a retry and the
    build both know what is missing."""
    result = dict(result or {})
    inner = result.pop("dropped_columns", None) or []
    entry = {k: result[k] for k in ("records", "error") if k in result}
    entry["soql"] = query.get("soql", "")
    entry["dropped_columns"] = list(query.get("dropped") or []) + list(inner)
    entry["drop_reasons"] = dict(query.get("drop_reasons") or {}, **{c: "missing" for c in inner})
    entry["query"] = {k: query[k] for k in ("tooling", "optional", "why") if k in query}
    raw.setdefault("queries", {})[query["key"]] = entry
    raw["_rev"] = (raw.get("_rev") or 0) + 1
    return entry


# ---- passes -----------------------------------------------------------------------------------------------------------

def options_of(raw):
    merged = dict(DEFAULT_OPTIONS)
    merged.update(raw.get("options") or {})
    objects = [ocutil.canonical_object(o) for o in merged["objects"]] or [SUBMISSION_OBJECT]
    if SUBMISSION_OBJECT not in objects:
        objects.insert(0, SUBMISSION_OBJECT)
    merged["objects"] = objects
    return merged


def ftk_present(raw):
    return any(val(row, "QualifiedApiName") == N + "Form_Template__c" for row in records(raw, "ftk"))


def _pending(raw, queries):
    """Queries not yet run, and retries of ones that failed on a droppable column.
    Empty means this pass is finished (a query that failed for good counts as run)."""
    todo = []
    for query in queries:
        if not ran(raw, query["key"]):
            todo.append(query)
        elif failed(raw, query["key"]):
            retry = _retry(raw, query["key"])
            if retry:
                todo.append(retry)
    return todo


def next_queries(raw):
    """The queries raw.json still needs. [] means the reads are complete."""
    from . import dictionary, flows, sweep  # the later passes depend on what earlier ones found

    raw.setdefault("queries", {})
    options = options_of(raw)
    todo = _pending(raw, FIRST)
    if todo:
        return todo
    if not ftk_present(raw):
        return []

    todo = _pending(raw, config_queries(options))
    if todo:
        return todo

    # pass 3: depends on the configuration read above. Flow reads repeat until
    # every subflow of a Flow Tool Kit flow is read.
    later = sweep.dependent_queries(raw, options) + flows.metadata_queries(raw, options)
    todo = _pending(raw, later)
    if todo:
        return todo

    # pass 4: the names of objects a config gives by entity Id, then the field
    # definitions of every other object a form, mapping or flow uses
    entity_ids = dictionary.unresolved_entities(raw)
    if entity_ids and not ran(raw, "entities"):
        return [{"key": "entities", "optional": True,
                 "soql": f"SELECT DurableId, QualifiedApiName FROM EntityDefinition WHERE DurableId IN "
                         f"({soql_list(entity_ids)})",
                 "why": "names of the objects some form configs give only by Id"}]
    referenced = sorted({o for o in dictionary.referenced_objects(raw) if not o.startswith("01I")}
                        - set(options["objects"]))
    more = []
    for sobject in referenced:
        more += field_queries(sobject, f"fields of {sobject}, which a form, mapping or flow uses")
    for query in more:
        query["optional"] = True
    return _pending(raw, more)
