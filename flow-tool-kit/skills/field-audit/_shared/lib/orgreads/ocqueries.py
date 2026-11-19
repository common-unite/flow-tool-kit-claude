"""What org-catalog reads, in passes. One list for every runner: the Salesforce CLI (catalog.py collect) and a Salesforce
connector in chat (catalog.py next-queries, then the connector runs each query and the rows go into raw.json).

next_queries(raw) returns the queries still to run given what raw.json already holds. A later pass depends on an
earlier one (which objects the forms use, which components have no JSON), so a runner calls it until it returns [].

Every query reads configuration only: components, templates, field definitions, style settings and file names.
None reads a Form Submission or any other record a respondent created.
"""
from __future__ import annotations

import re

from ocutil import NS, SUBMISSION, canonical_object, ns, parse_json, ran, records, soql_list, val

# Objects whose presence names a platform. EntityDefinition works through a plain SOQL connector, so this also
# detects Flow Tool Kit itself when the tooling API is not available.
PLATFORM_OBJECTS = {
    NS + "Form_Template__c": "flow_tool_kit",
    "outfunds__Funding_Request__c": "outbound_funds",
    "ProgramEnrollment": "nonprofit_cloud",
    "GiftTransaction": "nonprofit_cloud",
    "IndividualApplication": "nonprofit_cloud",
    "npsp__General_Accounting_Unit__c": "npsp",
}

FIRST = [
    {"key": "org", "soql": "SELECT Id, Name, IsSandbox, OrganizationType, InstanceName FROM Organization",
     "why": "which org this catalog describes"},
    {"key": "platform_objects",
     "soql": "SELECT QualifiedApiName, NamespacePrefix FROM EntityDefinition WHERE QualifiedApiName IN ("
             + soql_list(PLATFORM_OBJECTS) + ")",
     "why": "Flow Tool Kit, Outbound Funds, Nonprofit Cloud and NPSP present or not"},
    {"key": "packages", "tooling": True, "optional": True,
     "soql": "SELECT SubscriberPackage.NamespacePrefix, SubscriberPackage.Name, SubscriberPackageVersion.MajorVersion, "
             "SubscriberPackageVersion.MinorVersion, SubscriberPackageVersion.PatchVersion, SubscriberPackageVersion.BuildNumber "
             "FROM InstalledSubscriberPackage",
     "why": "the installed Flow Tool Kit version"},
    {"key": "person_accounts", "optional": True,
     "soql": "SELECT Id FROM RecordType WHERE SobjectType = 'Account' AND IsPersonType = true LIMIT 1",
     "why": "person accounts on or off (Nonprofit Cloud forms convert to them)"},
]

FTK = [
    {"key": "forms_mdt",
     "soql": f"SELECT QualifiedApiName, NamespacePrefix, MasterLabel, {NS}Active__c, {NS}type__c, {NS}Description__c, "
             f"{NS}Form_Object__r.{NS}Object__r.QualifiedApiName, {NS}config__c FROM {NS}Form__mdt",
     "why": "metadata Form Components"},
    {"key": "sections_mdt",
     "soql": f"SELECT QualifiedApiName, MasterLabel, {NS}Form__r.QualifiedApiName, {NS}formComponent__r.QualifiedApiName, "
             f"{NS}Default_Table_Form__r.QualifiedApiName, {NS}position__c, {NS}Delete__c, {NS}config__c FROM {NS}Form_Section__mdt",
     "why": "sections of metadata components, and the components placed inside them"},
    {"key": "fields_mdt",
     "soql": f"SELECT QualifiedApiName, MasterLabel, {NS}Form__r.QualifiedApiName, {NS}Form_Section__r.QualifiedApiName, "
             f"{NS}Object__r.QualifiedApiName, {NS}fieldName__c, {NS}referenceFormComponent__r.QualifiedApiName, {NS}position__c, "
             f"{NS}Delete__c, {NS}config__c FROM {NS}Form_Field__mdt",
     "why": "fields of metadata components (fieldName holds a field's durable Id, resolved from FieldDefinition)"},
    {"key": "components",
     "soql": f"SELECT Id, Name, RecordType.DeveloperName, {NS}QualifiedApiName__c, {NS}VersionId__c, {NS}Version__c, {NS}Label__c, "
             f"{NS}ObjectApiName__c, {NS}type__c, {NS}Active__c, {NS}Description__c, {NS}Folder__c, {NS}Has_Submission_Map__c, "
             f"{NS}Submission_Field_Map__c, {NS}FormConfigJSON__c, LastModifiedDate FROM {NS}Form_Component__c",
     "why": "record Form Components, with their JSON and Form Template Mapping"},
    {"key": "templates",
     "soql": f"SELECT Id, Name, {NS}IsActive__c, {NS}FormQualifiedApiName_Header__c, {NS}FormQualifiedApiName_Footer__c, "
             f"{NS}Logo__c, {NS}Logo_Override__c, {NS}Theme__c, LastModifiedDate FROM {NS}Form_Template__c",
     "why": "Form Templates"},
    {"key": "pages",
     "soql": f"SELECT Id, Name, {NS}Form_Template__c, {NS}Position__c, {NS}Page_Label__c, {NS}Page_Title__c FROM {NS}Form_Template_Page__c",
     "why": "template pages"},
    {"key": "page_sections",
     "soql": f"SELECT Id, Name, {NS}Form_Template_Page__c, {NS}Position__c, {NS}Title__c, {NS}Header_Title__c, {NS}Component_Type__c, "
             f"{NS}FormQualifiedApiName__c, {NS}FormConfigJSON__c, {NS}Form_Component__c, {NS}Alternate_FormQualifiedApiName__c, "
             f"{NS}Bulk_FormQualifiedApiName__c, {NS}Edit_FormQualifiedApiName__c, {NS}FlowApiName__c, {NS}lwcComponentName__c "
             f"FROM {NS}Form_Template_Page_Section__c",
     "why": "page sections: which component each one shows, or its own JSON"},
    {"key": "fields:" + SUBMISSION, "tooling": True,
     "soql": f"SELECT QualifiedApiName, Label, DataType, DurableId FROM FieldDefinition "
             f"WHERE EntityDefinition.QualifiedApiName = '{SUBMISSION}'",
     "why": "every Form Submission field, including ones the running user cannot read"},
    {"key": "style_defaults", "optional": True,
     "soql": f"SELECT SetupOwnerId, {NS}Color_Primary__c, {NS}Color_On_Primary__c, {NS}Font_Family__c, {NS}Font_Family_Heading__c, "
             f"{NS}Default_Logo__c, {NS}Default_Logo_Alt_Text__c FROM {NS}Form_Style_Defaults__c",
     "why": "a saved brand kit in the org's Form Style defaults (a protected setting: an installed package may refuse this read)"},
    {"key": "brand_files", "optional": True,
     "soql": "SELECT Id, ContentDocumentId, Title, FileExtension, LastModifiedDate FROM ContentVersion "
             "WHERE IsLatest = true AND FileExtension = 'json' AND Title LIKE 'brand-kit%'",
     "why": "a saved brand kit file (brand-kit.json)"},
]


MISSING_COLUMN = re.compile(r"No such column '([A-Za-z0-9_.]+)'")


def without_missing_column(soql, error):
    """The same query without the column an older Flow Tool Kit version does not have yet (the error names it), or
    None when the error is something else. A newer field missing from an older package is normal, not a failure."""
    found = MISSING_COLUMN.search(str(error or ""))
    if not found:
        return None
    column = found.group(1)
    head, sep, tail = soql.partition(" FROM ")
    if not sep or not head.upper().startswith("SELECT "):
        return None
    columns = [c.strip() for c in head[len("SELECT "):].split(",")]
    kept = [c for c in columns if c.lower() != column.lower() and not c.lower().endswith("." + column.lower())]
    if len(kept) == len(columns) or not kept:
        return None
    return "SELECT " + ", ".join(kept) + sep + tail


def _objects_used(raw):
    """Every object a component or a template section is built on, plus the objects of cross-object fields."""
    objects = set()
    for row in records(raw, "forms_mdt"):
        objects.add(val(row, f"{NS}Form_Object__r.{NS}Object__r.QualifiedApiName"))
    for row in records(raw, "fields_mdt"):
        objects.add(val(row, f"{NS}Object__r.QualifiedApiName"))
    for row in records(raw, "components"):
        objects.add(val(row, f"{NS}ObjectApiName__c"))
        root = parse_json(ns(val(row, f"{NS}FormConfigJSON__c") or ""))
        for section in val(root, "sections__r") or []:
            for field in val(section, "fields__r") or []:
                objects.add(val(field, "Object__c"))
    for row in records(raw, "page_sections"):
        objects.add(parse_json(val(row, f"{NS}FormConfigJSON__c")).get("object"))
    return sorted({canonical_object(o) for o in objects if isinstance(o, str) and o.strip()} - {SUBMISSION})


def _components_without_json(raw):
    """Record components with a blank JSON field. A Metadata Component row only tracks a metadata form, whose fields
    come from Form_Field__mdt, so it is left out."""
    return sorted({row["Id"] for row in records(raw, "components")
                   if row.get("Id") and val(row, "RecordType.DeveloperName") != "Metadata_Component"
                   and not (val(row, f"{NS}FormConfigJSON__c") or "").strip()})


def ftk_present(raw):
    names = {val(r, "QualifiedApiName") for r in records(raw, "platform_objects")}
    return NS + "Form_Template__c" in names


def next_queries(raw):
    """The queries raw.json still needs, each {key, soql, tooling, optional, why}. [] means the reads are complete."""
    todo = [q for q in FIRST if not ran(raw, q["key"])]
    if todo:
        return todo
    if not ftk_present(raw):
        return []
    todo = [q for q in FTK if not ran(raw, q["key"])]
    if todo:
        return todo
    later = []
    for obj in _objects_used(raw):
        key = "fields:" + obj
        if not ran(raw, key):
            later.append({"key": key, "tooling": True, "optional": True,
                          "soql": f"SELECT QualifiedApiName, Label, DataType, DurableId FROM FieldDefinition "
                                  f"WHERE EntityDefinition.QualifiedApiName = '{obj}'",
                          "why": f"labels and types of {obj} fields used by components"})
    missing = _components_without_json(raw)
    if missing and not ran(raw, "component_fields"):
        later.append({"key": "component_fields", "optional": True,
                      "soql": f"SELECT {NS}Form_Component__c, {NS}fieldName__c, {NS}Object__c, {NS}customLabel__c, {NS}position__c, "
                              f"{NS}referenceFormComponent__c, {NS}Form_Component_Section__r.{NS}position__c, "
                              f"{NS}Form_Component_Section__r.{NS}title__c FROM {NS}Form_Component_Field__c "
                              f"WHERE {NS}Form_Component__c IN ({soql_list(missing)})",
                      "why": "fields of record components whose JSON is blank"})
        later.append({"key": "component_sections", "optional": True,
                      "soql": f"SELECT {NS}Form_Component__c, {NS}formComponent__c, {NS}Default_Table_Form__c, {NS}title__c, "
                              f"{NS}position__c FROM {NS}Form_Component_Section__c WHERE {NS}Form_Component__c IN ({soql_list(missing)})",
                      "why": "components placed inside record components whose JSON is blank"})
    docs = sorted({val(r, "ContentDocumentId") for r in records(raw, "brand_files") if val(r, "ContentDocumentId")})
    if docs and not ran(raw, "brand_file_libraries"):
        later.append({"key": "brand_file_libraries", "optional": True,
                      "soql": "SELECT ContentDocumentId, ContentWorkspace.Name, ContentWorkspace.DeveloperName FROM ContentWorkspaceDoc "
                              f"WHERE ContentDocumentId IN ({soql_list(docs)})",
                      "why": "whether each brand file is in the Asset Library"})
    return later
