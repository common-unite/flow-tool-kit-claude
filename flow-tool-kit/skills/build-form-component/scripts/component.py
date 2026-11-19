#!/usr/bin/env python3
"""Check, map and write Flow Tool Kit Form Components. Python 3 standard library only; never touches an org.

Check a component before it is written (component JSON, or a folder of custom metadata record files):
    python3 component.py check <component.json | customMetadata folder> [--catalog catalog.json] [--plan plan.json]
                               [--edition paid|free] [--json]

Turn a plan's Form Template Mapping into the package's Submission Field Map (keyed by Form Submission field):
    python3 component.py map <plan.json> --component <key> [--into <component.json>]

Extend a component: a new version under its own name with the added fields; the original is never changed:
    python3 component.py extend <original.json> --name <New_Name> --add <added-fields.json> --out <new.json>

Write custom metadata record files for an org with Flow Tool Kit installed (Claude Code; deploy them with the CLI):
    python3 component.py cmt <component.json> --out <force-app/main/default/customMetadata>
                             [--form-object <Form Object record name>] [--new-form-object]

Exit codes: 0 clean, 1 errors found, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "_shared" / "lib"))
import addressparts  # noqa: E402  the address rule, one copy for every skill

NS = "FlowToolKit__"
STAR = "*__"
SUBMISSION = NS + "Form_Submission__c"
FTK_OBJECTS = {"Form_Submission__c", "Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c",
               "Form_Component__c", "Form_Submission_Stage__c", "Form_Submission_Answer__c"}
PACKAGED_FORM_OBJECTS = {"Form_Submission__c": "Form_Submission", "Form_Template__c": "Form_Template",
                         "Form_Template_Page__c": "Form_Template_Page", "Form_Template_Page_Section__c": "Form_Template_Page_Section",
                         "Account": "Account"}
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
ISSUE_NUMBER = re.compile(r"(?<![\w&])#\d+")
MERGE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
FREE_OBJECTS = {"Account", "Contact", "Lead", "Case", "Campaign", "CampaignMember"}
STANDARD_FIELDS = {"Id", "Name", "OwnerId", "CreatedById", "CreatedDate", "LastModifiedById", "LastModifiedDate",
                   "RecordTypeId", "CurrencyIsoCode"}
SCALE_FIELD = re.compile(r"^(?:Agreement|Satisfaction|Frequency|Importance|Likelihood|Confidence|Ease|Usefulness|Familiarity|"
                         r"Expectations|Change|Scale)_Question_\d+__c$|^Rating_\d+__c$")
# Form Submission fields that are plumbing, never a Form Template Mapping target (bare names; Internal_* and
# Conversion_Status_* are excluded as families)
UNMAPPABLE = {"Status__c", "Stage_Status__c", "Conversion_Status__c", "Conversion_Log__c", "Conversion_Dispatch_Counts__c",
              "Form_Template__c", "FormQualifiedApiName__c", "Parent_Form_Submission__c", "ParentFormSubmissionId__c",
              "IsPrefillTemplate__c", "UniqueId__c", "Tag_Internal__c", "Origin__c", "Submission_Date__c", "Last_Saved_Date__c",
              "CampaignId__c", "OwnerId", "RecordTypeId"}

# Value sets, from the package's Form Component objects. Keep in step with references/key-reference.md.
WIDTHS = {str(n) for n in range(1, 13)}
ENUMS = {
    "root": {
        "type__c": {"form", "table", "default", "scoped", "vertical", "carousel", "review"},
        "CategoryTag__c": {"Component(s)", "Form(s)", "Template(s)"},
        "horizontalAlign__c": {"start", "center", "space", "spread", "end"},
        "verticalAlign__c": {"start", "center", "end", "stretch"},
        "carouselBackButtonLabel__c": {"Back", "Previous", "Return", "Go Back"},
        "carouselNextButtonLabel__c": {"Continue", "Next", "Forward", "Proceed"},
        "carouselFinishButtonLabel__c": {"Submit", "Finish", "Done", "Complete", "Save"},
    },
    "section": {
        "sectionType__c": {"inputSection", "addressSection", "richTextSection", "accordionSection", "carouselSection",
                           "dividerSection", "illustrationSection", "imageSection", "tableSection", "formComponent",
                           "flowScreen", "lwcSection", "likertSection", "recordCardSection", "bannerSection"},
        "displayType__c": {"SHOW", "HIDE"},
        "sectionTheme__c": {"clean", "shadow", "box", "visualPicker"},
        "Message_Variant__c": {"default", "info", "warning", "error", "success", "highlight"},
        "Divider_Style__c": {"line", "compact", "centered", "label", "bookmark", "ornament", "pill", "chevron", "double",
                             "icon", "fade", "tag"},
        "Likert_Mode__c": {"Picklist", "Number"},
        "Illustration_Size__c": {"small", "large"},
        "modalSize__c": {"small", "medium", "large", "full"},
        "horizontalAlign__c": {"start", "center", "space", "spread", "end"},
    },
    "field": {
        "displayType__c": {"SHOW", "HIDE", "REQUIRED", "READONLY"},
        "picklistType__c": {"standard", "radio", "radiobuttons", "separatedbuttons", "iconbuttons", "pathbuttons",
                            "multiselectcheckbox", "multiselectbadge", "selectallmultiselectcheckbox", "combobox",
                            "surveybuttons", "visualpicker", "iconselector", "emailtemplateselector", "imageassetselector",
                            "stylesheetselector"},
        "picklistColumnsSize__c": {"none", "grow"} | {f"size_1-of-{n}" for n in range(1, 13)},
        "picklistDescriptionDisplay__c": {"Below Option", "Hover Bubble", "Below Field"},
        "booleanType__c": {"default", "checkbox", "picklist", "radio", "radiobuttons", "attestation"},
        "booleanPicklistTypeOverride__c": {"default", "Active/Inactive", "Yes/No", "Enabled/Disabled", "Valid/Invalid", "On/Off"},
        "numberType__c": {"standard", "stepper", "slider", "presetamounts"},
        "stringType__c": {"standard", "textarea", "iconselector", "emailtemplateselector", "imageassetselector", "stylesheetselector"},
        "longTextType__c": {"default", "fileUpload"},
        "richTextType__c": {"standard", "signaturePad", "imageUpload"},
        "referenceFieldOverrideType__c": {"standard", "component", "startnewform", "vieweditsubmission", "recordpicker"},
        "referenceFormDisplayType__c": {"inline", "modal"},
        "addressFieldType__c": {"Address", "Street", "City", "State", "PostalCode", "Country"},
        "labelVariant__c": {"standard", "label-hidden", "none", "label-inline", "label-stacked", "left", "right"},
        "labelSize__c": {"slds-text-body_small", "slds-text-body_regular", "slds-text-title_bold", "slds-text-heading_small",
                         "slds-text-heading_medium", "slds-text-heading_large"},
        "helpTextDisplay__c": {"Hover Bubble", "Below Label", "Below Field"},
        "iconPicklistOverrideIconSize__c": {"small", "medium", "large"},
        "currencyDisplayAs__c": {"symbol", "code", "name"},
        "phoneMask__c": {"none", "(xxx) xxx-xxxx", "xxx-xxx-xxxx", "xx xxxx xxxx", "xxxx xxx xxx"},
        "promptDisplayType__c": {"prompt", "richtext"},
        "promptDisplayValue__c": {"helptext", "custom"},
        "minDateType__c": {"specificDate", "specific", "today", "fieldValue"},
        "maxDateType__c": {"specificDate", "specific", "today", "fieldValue"},
        "minBeforeAfter__c": {"before", "after"},
        "maxBeforeAfter__c": {"before", "after"},
        "columnAlignment__c": {"left", "center", "right"},
        "columnIconPosition__c": {"left", "center", "right"},
        "columnVisibility__c": {"visible", "hidden"},
        "columnDisplayType__c": {"text", "url"},
        "columnCalculationType__c": {"Sum", "Min", "Max", "Average"},
    },
}
SECTION_FLAG = {"inputSection": "isInputSection", "richTextSection": "isRichTextSection", "addressSection": "isAddressSection",
                "imageSection": "isImageSection", "formComponent": "isFormComponentSection", "dividerSection": "isDividerSection",
                "illustrationSection": "isIllustrationSection", "flowScreen": "isFlowSection", "lwcSection": "isLwcSection",
                "likertSection": "isLikertSection", "recordCardSection": "isRecordCardSection", "bannerSection": "isBannerSection"}
JSON_ONLY = {"QualifiedApiName", "Label", "Id", "sectionVerticalPadding", "sectionMarginClass", "richTextClass", "hide"} | set(SECTION_FLAG.values())
TEXT_255 = {"customLabel__c": "customLabelLong__c", "helpText__c": "helpTextLong__c", "placeholder__c": "placeholderLong__c",
            "customValidationMessage__c": None, "formatAlertMessage__c": None, "fileNameFormat__c": None,
            "validationFormat__c": None, "Alternative_Field__c": None, "Total_Score_Label__c": None, "Description__c": None,
            "customLookupHeader__c": None, "customLookupSubheader__c": None}
TEXT_40 = {"min__c", "max__c", "step__c", "prepend__c", "append__c"}
TEXT_NOT_NUMBER = {"min__c", "max__c", "step__c", "inlineLabelWidth__c", "textAreaMinHeight__c", "textAreaMaxHeight__c"}
NUMERIC = {"position__c", "minDays__c", "maxDays__c", "columnInitialWidth__c", "columnFixedWidth__c", "imageOverlayOpacity__c",
           "minimumIntegerDigits__c", "minimumFractionDigits__c", "maximumFractionDigits__c", "minimumSignificantDigits__c",
           "maximumSignificantDigits__c"}
JSON_VALUED = {"numberPresets__c", "picklistOptionSettings__c", "picklistOptionLabels__c", "picklistOptionScores__c",
               "picklistVisualPickerOptions__c", "recordPickerConfig__c", "Likert_Scale__c", "Submission_Field_Map__c",
               "Banner__c", "Record_Card__c"}
OPERATIONS = {"==", "!=", "TRUE", "FALSE", "BLANK", "NOTBLANK", "CONTAINS", "INCLUDES", "<", ">", "<=", ">="}
NO_VALUE_OPS = {"TRUE", "FALSE", "BLANK", "NOTBLANK"}
TOKENS = {"label", "helptext", "fieldnumber", "sectionnumber"}


# ---- small helpers ---------------------------------------------------------------------------------------------------

def local(key):
    """A key without its namespace: '*__title__c' and 'FlowToolKit__title__c' both become 'title__c'."""
    for prefix in (STAR, NS):
        if key.startswith(prefix):
            return key[len(prefix):]
    return key


def get(node, name, default=None):
    """Read a key whatever prefix it was written with."""
    for key in (STAR + name, NS + name, name):
        if isinstance(node, dict) and key in node:
            return node[key]
    return default


def full(name):
    """A field or object name with the package prefix written out ('*__X' becomes 'FlowToolKit__X')."""
    return name.replace(STAR, NS) if isinstance(name, str) else name


def bare(name):
    name = full(name or "")
    return name[len(NS):] if name.startswith(NS) else name


def canonical_object(name):
    name = full(name or "").strip()
    return NS + name if name in FTK_OBJECTS else name


def plain_text(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def short_name(name, limit=40):
    """A custom metadata record name of at most 40 characters, stable across reruns."""
    if len(name) <= limit:
        return name
    digest = hashlib.sha1(name.encode()).hexdigest()[:8]
    return f"{name[:limit - 9].rstrip('_')}_{digest}"


def parse_json(text):
    if isinstance(text, (dict, list)):
        return text
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def type_family(data_type):
    """A field's type from a catalog (FieldDefinition DataType text such as 'Text(80)' or 'Picklist') as a family."""
    t = (data_type or "").lower()
    if "multi" in t:
        return "multipicklist"
    for prefix, family in (("multi", "multipicklist"), ("picklist", "picklist"), ("checkbox", "boolean"),
                           ("lookup", "reference"), ("master-detail", "reference"), ("rich", "richtext"),
                           ("long text", "longtext"), ("text area", "textarea"), ("text", "text"), ("email", "email"),
                           ("phone", "phone"), ("url", "url"), ("date/time", "datetime"), ("date", "date"),
                           ("time", "time"), ("currency", "number"), ("percent", "number"), ("number", "number"),
                           ("formula", "formula"), ("auto", "formula"), ("roll-up", "formula")):
        if t.startswith(prefix):
            return family
    return None


def mapping_compatible(source, target):
    """Whether a component field's type family can feed a Form Submission field's family (the package checks again)."""
    if not source or not target:
        return True
    if target == "formula":
        return False
    if source in ("picklist", "multipicklist"):
        return target in ("picklist", "multipicklist", "text", "textarea", "longtext")
    if source in ("text", "textarea", "longtext"):
        return target in ("text", "textarea", "longtext")
    return source == target


# ---- the catalog -----------------------------------------------------------------------------------------------------

class Catalog:
    """org-catalog's catalog.json, read for field checks: which objects were read, and their fields and types."""

    def __init__(self, data=None):
        data = data or {}
        self.status = data.get("status")
        self.edition = data.get("edition")
        self.index = {}
        self.twins = {}
        for obj, info in (data.get("fields_index") or {}).items():
            if info.get("read") and isinstance(info.get("fields"), dict):
                self.index[canonical_object(obj)] = {full(k): v for k, v in info["fields"].items()}
                self.twins[canonical_object(obj)] = set(info.get("twins") or [])
        self.components = {c.get("name"): c for c in data.get("components") or []}

    def knows(self, obj):
        return canonical_object(obj) in self.index

    def field(self, obj, name):
        fields = self.index.get(canonical_object(obj))
        if fields is None:
            return None
        return fields.get(full(name))


# ---- check -----------------------------------------------------------------------------------------------------------

class Checker:
    def __init__(self, catalog=None, planned=None, edition=None, path="record"):
        self.catalog = catalog or Catalog()
        self.planned = planned or set()
        self.edition = edition or self.catalog.edition
        self.path = path
        self.object = ""
        self.findings = []

    def add(self, severity, check, where, message):
        self.findings.append({"severity": severity, "check": check, "where": where, "message": message})

    # values on any element
    def values(self, node, level, where):
        for key, value in node.items():
            name = local(key)
            if name in ENUMS[level] and value not in ENUMS[level][name] and value is not None:
                self.add("error", "bad-value", where, f"{name} is {value!r}, not one of its values; the package silently falls "
                         f"back to the default. Valid: {', '.join(sorted(ENUMS[level][name]))}")
            if name in ("widthSmall__c", "widthMedium__c", "widthLarge__c"):
                allowed = WIDTHS | ({"shrink"} if level == "field" and name == "widthLarge__c" else set())
                if str(value) not in allowed:
                    self.add("error", "bad-width", where, f"{name} is {value!r}; use a string 1 to 12"
                             + (" or 'shrink'" if "shrink" in allowed else ""))
                elif not isinstance(value, str):
                    self.add("warning", "wrong-type", where, f"{name} should be a string such as \"{value}\"")
            if name in TEXT_NOT_NUMBER and isinstance(value, (int, float)) and not isinstance(value, bool):
                self.add("error", "wrong-type", where, f"{name} is stored as text; write \"{value}\", not {value}")
            if name in NUMERIC and isinstance(value, str):
                self.add("warning", "wrong-type", where, f"{name} is a number; write {value} without quotes")
            if name in TEXT_40 and isinstance(value, str) and len(value) > 40:
                self.add("error", "too-long", where, f"{name} holds 40 characters at most ({len(value)} given)")
            if name in TEXT_255 and isinstance(value, str) and len(value) > 255 and not (level == "section" and name == "helpText__c"):
                longer = TEXT_255[name]
                self.add("error", "too-long", where, f"{name} is {len(value)} characters: past 255 it imports, then breaks the "
                         f"first save in Form Builder" + (f". Put it in {longer}" if longer else ""))
            if name == "iconPicklistOverrideActiveColor__c" and isinstance(value, str) and len(value) > 7:
                self.add("error", "too-long", where, f"{name} is a hex color such as #ffd602 (7 characters)")
            if name in JSON_VALUED and isinstance(value, str) and parse_json(value) is None:
                self.add("error", "bad-json", where, f"{name} must be valid JSON text")
            if name in JSON_VALUED and isinstance(value, (dict, list)):
                self.add("warning", "wrong-type", where, f"{name} is stored as JSON text: write it as a string, not an object")
            if isinstance(value, str) and "{{" in value:
                self.merges(value, where, name)

    def merges(self, text, where, key):
        for token in MERGE.findall(text):
            token = token.strip()
            if token in TOKENS or token.startswith("$Label.") or token.startswith("$"):
                continue
            field_name = token.split(".")[0]
            if not API_NAME.match(full(field_name).replace(NS, "")):
                continue
            if self.object and self.catalog.knows(self.object) and field_name not in STANDARD_FIELDS:
                if self.catalog.field(self.object, field_name) is None:
                    self.add("error", "merge-missing", where, f"{key} merges {{{{{token}}}}}, which {bare(self.object)} does not "
                             "have; a merge naming a missing field breaks the form")

    def field_ref(self, obj, name, where, what="field"):
        if not name:
            self.add("error", "missing-key", where, f"the {what} names no field")
            return None
        if name in STANDARD_FIELDS:
            return None
        if not self.catalog.knows(obj):
            return None
        info = self.catalog.field(obj, name)
        if info is None:
            if (canonical_object(obj), full(name)) in self.planned:
                self.add("warning", "field-planned", where, f"{full(name)} is a planned new field: deploy it before the component, "
                         "or the question silently disappears")
            else:
                self.add("error", "field-missing", where, f"{bare(obj)} has no field {full(name)}. The package skips an unknown "
                         "field without an error, so " + ("this question would vanish" if what == "field"
                                                           else f"this {what} would never work"))
            return None
        if full(name) in self.catalog.twins.get(canonical_object(obj), set()):
            self.add("warning", "twin-field", where, f"{full(name)} has the same name as a packaged field; the conversion leaves "
                     "it out of the record it hands a flow. Prefer the packaged field or rename yours")
        return info

    def run(self, component):
        root = component
        self.object = canonical_object(get(root, "ObjectApiName__c") or get(root, "Form_Object__c") or "")
        name = root.get("QualifiedApiName")
        if not name:
            self.add("error", "missing-key", "root", "QualifiedApiName is required; without it the component renders as nothing")
            name = "?"
        elif not API_NAME.match(name) or "__" in name or name.endswith("_"):
            self.add("error", "bad-name", "root", f"QualifiedApiName {name!r}: letters, digits and single underscores only")
        elif re.search(r"_v\d+$", name):
            self.add("error", "bad-name", "root", f"QualifiedApiName {name!r} ends in a version suffix; the package adds _v0 itself")
        if not root.get("Label"):
            self.add("warning", "label", "root", "Label is the name people see in Form Builder; give the purpose in words")
        if not self.object:
            self.add("error", "missing-key", "root", "ObjectApiName__c is required: the object the component is built on")
        if get(root, "Active__c") is not True:
            self.add("warning", "inactive", "root", "Active__c is not true; an inactive component does not render")
        self.description(get(root, "Description__c"), "root")
        if get(root, "CategoryTag__c") is None:
            self.add("warning", "category", "root", "CategoryTag__c: Component(s) for a reusable block")
        self.values(root, "root", "root")
        self.edition_checks(root)
        self.mapping(root)

        names = {"rule": {}, "section": {}, "field": {}}

        def claim(kind, qname, where):
            """Names are unique within one kind of record (rules, sections, fields), not across kinds."""
            if not qname:
                return
            seen = names[kind]
            if bare(qname) in seen:
                self.add("error", "duplicate-name", where, f"{qname} is also used by another {kind} at {seen[bare(qname)]}; "
                         f"{kind} names are unique across the org")
            seen[bare(qname)] = where
            if self.path == "record" and name != "?" and not qname.startswith(name) and qname != name:
                self.add("warning", "child-name", where, f"{qname} does not start with the component's name {name}; child names "
                         "are unique across the org, and a clash stops the import")

        rules = {}
        for i, rule in enumerate(get(root, "conditionalLogic__r") or []):
            where = f"rules[{i}]"
            qname = rule.get("QualifiedApiName")
            claim("rule", qname, where)
            rules[bare(qname)] = {"rule": rule, "used": False, "where": where, "name": qname}
        sections = get(root, "sections__r")
        if not isinstance(sections, list):
            self.add("error", "bad-shape", "root", "sections__r must be a plain array of sections")
            sections = []
        if not sections:
            self.add("error", "empty", "root", "the component has no sections")
        category = get(root, "CategoryTag__c")
        for s, section in enumerate(sections):
            where = f"sections[{s}]"
            qname = section.get("QualifiedApiName")
            if not qname:
                self.add("error", "missing-key", where, "QualifiedApiName is required")
            claim("section", qname, where)
            where = f"{where} {qname or ''}".strip()
            if get(section, "position__c") is None:
                self.add("error", "missing-key", where, "position__c is required")
            stype = get(section, "sectionType__c")
            if stype is None:
                self.add("error", "missing-key", where, "sectionType__c is required")
            elif self.path == "record" and SECTION_FLAG.get(stype) and section.get(SECTION_FLAG[stype]) is not True:
                self.add("error", "missing-flag", where, f"a {stype} needs \"{SECTION_FLAG[stype]}\": true; without it the "
                         "section renders as nothing")
            title = plain_text(get(section, "title__c") or "")
            if not title:
                self.add("error", "untitled", where, "every section needs a title__c of a few plain words; Form Builder lists "
                         "sections by it and shows Untitled Section otherwise")
            if get(section, "showHeader__c") is True and category == "Component(s)":
                self.add("warning", "header-in-component", where, "a shared component is headerless: put the header on the "
                         "page section, so each form can title it")
            self.values(section, "section", where)
            logic = get(section, "conditionalLogic__c")
            if logic:
                self.rule_ref(logic, rules, where)
            fields = get(section, "fields__r")
            if fields is None:
                if self.path == "record":
                    self.add("error", "missing-key", where, "fields__r must be present, even as []")
                fields = []
            # The package draws an address only in its own address section, with its row and all five parts; a part
            # left out draws one blank box, and an address among other fields draws as plain fields
            for problem in addressparts.section_problems(fields, stype, where, addressparts.json_variant, addressparts.json_name):
                self.add("error", "address-parts", where, problem.split(": ", 1)[-1])
            if stype == "addressSection":
                parts = [get(f, "addressFieldType__c") for f in fields]
                if set(parts) == set(addressparts.ORDER) and parts != list(addressparts.ORDER):
                    self.add("warning", "address-order", where, "an address section lists its parts in this order: Address, "
                             f"Street, City, State, PostalCode, Country (found {parts})")
            if stype == "likertSection":
                self.likert(section, fields, where)
            for f, field in enumerate(fields):
                fwhere = f"{where}.fields[{f}]"
                fq = field.get("QualifiedApiName")
                if not fq:
                    self.add("error", "missing-key", fwhere, "QualifiedApiName is required")
                claim("field", fq, fwhere)
                fwhere = f"{fwhere} {fq or ''}".strip()
                if get(field, "position__c") is None:
                    self.add("error", "missing-key", fwhere, "position__c is required")
                self.field(field, fwhere)
                logic = get(field, "conditionalLogic__c")
                if logic:
                    self.rule_ref(logic, rules, fwhere)
        for qname, entry in rules.items():
            self.rule(entry["rule"], entry["where"])
            if not entry["used"]:
                self.add("warning", "unused-rule", entry["where"], f"rule {entry['name']} governs no section or field")
        return self.findings

    def description(self, text, where):
        text = plain_text(text or "")
        if not text:
            self.add("error", "description", where, "Description__c is required: what the block collects, where the answers go, "
                     "how to reuse it (documentation standard)")
            return
        if ISSUE_NUMBER.search(text):
            self.add("error", "description", where, "the description names an issue number; describe what it does now")
        if "\u2014" in text:  # the em-dash character, written as an escape so editors and hooks cannot turn it into a hyphen
            self.add("error", "description", where, "the description has an em-dash; use a colon, a comma or a new sentence")
        if re.search(r"\b(used to|repurposed|formerly|previously)\b", text, re.I):
            self.add("warning", "description", where, "the description tells history; describe what the component does now")

    def edition_checks(self, root):
        obj = bare(self.object)
        if self.edition == "free" and obj and canonical_object(obj) not in {canonical_object(o) for o in FTK_OBJECTS} \
                and obj not in FREE_OBJECTS:
            self.add("error", "free-edition", "root", f"the free edition draws forms only on Account, Contact, Lead, Case, Campaign, "
                     f"Campaign Member and the Flow Tool Kit objects; {obj} shows 'Object Is Not Available'. Build on Form "
                     "Submission and map in the conversion")

    def mapping(self, root):
        raw = get(root, "Submission_Field_Map__c")
        on_submission = self.object == SUBMISSION
        body_object = self.object and self.object not in {canonical_object(o) for o in FTK_OBJECTS}
        if raw in (None, ""):
            if self.edition == "paid" and body_object:
                self.add("warning", "no-mapping", "root", f"a component on {bare(self.object)} with no Form Template Mapping: "
                         "placed in a page section, nothing it collects reaches the Form Submission")
            return
        if on_submission:
            self.add("error", "mapping-on-submission", "root", "a Form Submission component never carries a Form Template Mapping")
            return
        data = parse_json(raw)
        if not isinstance(data, dict) or not isinstance(data.get("fields"), dict) or not data["fields"]:
            self.add("error", "mapping-shape", "root", 'Submission_Field_Map__c must be {"lookupField": "ALL" or a Form '
                     'Submission lookup, "fields": {"<Form Submission field>": "<component field>"}}')
            return
        lookup = data.get("lookupField")
        if not lookup:
            self.add("error", "mapping-shape", "root", "lookupField is required: ALL, or the Form Submission lookup this record "
                     "converts through")
        elif lookup != "ALL":
            info = self.field_ref(SUBMISSION, lookup, "root mapping", "lookupField")
            if info and type_family(info.get("type")) not in (None, "reference"):
                self.add("error", "mapping-lookup", "root", f"lookupField {lookup} is not a lookup")
        component_fields = set()
        for section in get(root, "sections__r") or []:
            for field in get(section, "fields__r") or []:
                if get(field, "fieldName__c"):
                    component_fields.add(full(get(field, "fieldName__c")))
        for rule in get(root, "conditionalLogic__r") or []:
            for cond in get(rule, "conditions__r") or []:
                if get(cond, "fieldName__c"):
                    component_fields.add(full(get(cond, "fieldName__c")))
        for target, source in data["fields"].items():
            where = f"root mapping {target}"
            target_bare = bare(target)
            if target_bare in UNMAPPABLE or target_bare.startswith(("Internal_", "Conversion_Status_")):
                self.add("error", "mapping-target", where, f"{target} is plumbing on the Form Submission and never a mapping target")
            if not full(target).startswith(NS) and self.catalog.field(SUBMISSION, NS + target):
                self.add("error", "mapping-prefix", where, f"write the packaged field with its prefix: {NS + target}")
                continue
            if full(source) not in component_fields:
                self.add("error", "mapping-source", where, f"{source} is not a field on this component")
            tinfo = self.field_ref(SUBMISSION, target, where, "mapping target")
            sinfo = self.catalog.field(self.object, source) if self.catalog.knows(self.object) else None
            if tinfo and sinfo and not mapping_compatible(type_family(sinfo.get("type")), type_family(tinfo.get("type"))):
                self.add("error", "mapping-type", where, f"{source} ({sinfo.get('type')}) cannot feed {target} ({tinfo.get('type')}); "
                         "the Form Builder refuses it on save")

    def field(self, field, where):
        obj = canonical_object(get(field, "Object__c") or self.object)
        name = get(field, "fieldName__c")
        info = self.field_ref(obj, name, where)
        self.values(field, "field", where)
        family = type_family((info or {}).get("type"))
        if SCALE_FIELD.match(bare(name or "")) and (get(field, "picklistOptionOverrides__c") or get(field, "picklistOptionLabels__c")):
            self.add("warning", "scale-field", where, f"{bare(name)} draws its fixed packaged scale and ignores option overrides "
                     "and labels; a question with its own options needs its own picklist field")
        if get(field, "picklistType__c") == "radiobuttons":
            options = [o for o in (get(field, "picklistOptionOverrides__c") or "").split(";") if o]
            if len(options) > 3 or any(len(o) > 18 for o in options):
                self.add("warning", "radiobuttons", where, "a segmented bar never wraps and clips long or many options; use "
                         "surveybuttons")
        if get(field, "labelVariant__c") == "none" and get(field, "booleanType__c") != "attestation":
            self.add("warning", "label-none", where, "labelVariant__c none also hides the label from screen readers; a hidden "
                     "label is label-hidden unless that is the intent")
        if get(field, "booleanType__c") == "attestation":
            if not plain_text(get(field, "Label_Rich_Text__c") or ""):
                self.add("error", "attestation", where, "an attestation's statement goes in Label_Rich_Text__c, inside the card")
            if get(field, "labelVariant__c") not in ("none",):
                self.add("warning", "attestation", where, "set labelVariant__c to none so nothing labels the card twice")
            if get(field, "helpText__c"):
                self.add("warning", "attestation", where, "consent wording in helpText__c is capped at 255 and renders under the "
                         "card; keep it in Label_Rich_Text__c")
        if get(field, "numberType__c") in ("stepper", "slider", "presetamounts") and family not in (None, "number"):
            self.add("error", "number-control", where, f"{get(field, 'numberType__c')} needs a number, currency or percent field")
        presets = parse_json(get(field, "numberPresets__c")) if get(field, "numberPresets__c") else None
        if presets is not None and (not isinstance(presets, dict) or not isinstance(presets.get("options"), list)):
            self.add("error", "bad-json", where, 'numberPresets__c is {"enableCustomValues": true, "options": [{"label", "value"}]}')
        if get(field, "picklistType__c") and family and family not in ("picklist", "multipicklist"):
            self.add("warning", "control-type", where, f"picklistType__c on a {family} field has no effect")
        if get(field, "displayType__c") in ("HIDE", "REQUIRED", "READONLY") and not get(field, "conditionalLogic__c"):
            self.add("warning", "display-type", where, "displayType__c is the action a rule applies; without a rule it does nothing")

    def likert(self, section, fields, where):
        mode = get(section, "Likert_Mode__c") or "Picklist"
        if mode == "Number":
            scale = parse_json(get(section, "Likert_Scale__c"))
            if not isinstance(scale, list) or not scale or not all(isinstance(s, dict) and "label" in s and "value" in s for s in scale):
                self.add("error", "likert", where, 'Number mode needs Likert_Scale__c: [{"label": "Never", "value": 0}, ...]')
        for f in fields:
            info = self.catalog.field(canonical_object(get(f, "Object__c") or self.object), get(f, "fieldName__c")) or {}
            family = type_family(info.get("type"))
            if mode == "Number" and family not in (None, "number"):
                self.add("error", "likert", where, f"{get(f, 'fieldName__c')}: Number mode rows must be number fields")
            if mode == "Picklist" and family not in (None, "picklist"):
                self.add("error", "likert", where, f"{get(f, 'fieldName__c')}: Picklist mode rows must be picklists on one scale")
        total = get(section, "Alternative_Field__c")
        if total:
            info = self.field_ref(self.object, total, where, "total field")
            if info and type_family(info.get("type")) not in (None, "number"):
                self.add("error", "likert", where, f"{total} stores the total and must be a number field")

    def rule_ref(self, qname, rules, where):
        """A section or field's rule reference; stored config may write the rule's name with the package prefix."""
        if bare(qname) not in rules:
            self.add("error", "rule-missing", where, f"names rule {qname}, which this component does not have")
        else:
            rules[bare(qname)]["used"] = True

    def rule(self, rule, where):
        label = (rule.get("Label") or "").strip()
        qname = rule.get("QualifiedApiName")
        if not qname:
            self.add("error", "missing-key", where, "QualifiedApiName is required")
        where = f"{where} {qname or ''}".strip()
        if not label:
            self.add("error", "rule-label", where, "every rule needs a Label naming its purpose in plain words; Form Builder lists "
                     "rules by it")
        elif len(label) > 40 or "__" in label or (" " not in label and "_" in label):
            self.add("error", "rule-label", where, f"Label {label!r}: a few plain words, at most 40 characters, never an API name")
        ctype = get(rule, "conditionType__c") or "AND"
        if ctype not in ("AND", "OR", "CUSTOM"):
            self.add("error", "bad-value", where, f"conditionType__c is {ctype!r}; use AND, OR or CUSTOM")
        if ctype == "CUSTOM" and not get(rule, "customLogic__c"):
            self.add("error", "missing-key", where, "CUSTOM logic needs customLogic__c such as (1 OR 2) AND 3")
        conditions = get(rule, "conditions__r") or []
        if not conditions:
            self.add("error", "empty-rule", where, "the rule has no conditions")
        for c, cond in enumerate(conditions):
            cwhere = f"{where}.conditions[{c}]"
            op = get(cond, "operation__c")
            if op not in OPERATIONS:
                self.add("error", "bad-value", cwhere, f"operation__c {op!r}; use one of {', '.join(sorted(OPERATIONS))}")
            if op not in NO_VALUE_OPS and get(cond, "value__c") in (None, ""):
                self.add("error", "missing-key", cwhere, f"{op} needs a value__c")
            self.field_ref(canonical_object(get(cond, "Object__c") or self.object), get(cond, "fieldName__c"), cwhere, "condition")


# ---- custom metadata files -------------------------------------------------------------------------------------------

CMT_TYPES = ["Form", "Form_Section", "Form_Field", "Form_Conditional_Logic", "Form_Conditional_Logic_Condition"]
RECORD_TYPE = {"Form": "Form_Component__c", "Form_Section": "Form_Component_Section__c", "Form_Field": "Form_Component_Field__c",
               "Form_Conditional_Logic": "Form_Component_Conditional_Logic__c",
               "Form_Conditional_Logic_Condition": "Form_Component_Condition__c"}
VALUE_RE = re.compile(r"<values>\s*<field>(?P<field>[^<]+)</field>\s*<value(?P<attrs>[^>]*?)(?:/>|>(?P<value>.*?)</value>)\s*</values>", re.S)


def ns_config(node, skip=()):
    """A component JSON element as flat metadata config: namespaced keys, no children, no JSON-only helpers."""
    out = {}
    for key, value in node.items():
        name = local(key)
        if key in JSON_ONLY or name in skip or name.endswith("__r") or name in ("Version__c", "VersionId__c", "QualifiedApiName__c"):
            continue
        out[NS + name] = full(value) if isinstance(value, str) and name in ("fieldName__c", "Object__c", "Alternative_Field__c") else value
    return out


def xml_value(value):
    if value is None:
        return '<value xsi:nil="true"/>'
    if isinstance(value, bool):
        return f'<value xsi:type="xsd:boolean">{"true" if value else "false"}</value>'
    if isinstance(value, (int, float)):
        return f'<value xsi:type="xsd:double">{float(value)}</value>'
    return f'<value xsi:type="xsd:string">{escape(str(value), {chr(34): "&quot;"})}</value>'


def record_xml(label, columns):
    body = "".join(f"    <values>\n        <field>{NS}{field}</field>\n        {xml_value(value)}\n    </values>\n"
                   for field, value in columns)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n'
            f"    <label>{escape(label[:40])}</label>\n    <protected>false</protected>\n{body}</CustomMetadata>\n")


def emit_cmt(component, form_object=None, new_form_object=False):
    """Custom metadata record files for an org with Flow Tool Kit installed, as {file name: XML text}.
    Returns (files, renamed) where renamed maps names longer than 40 characters to their record names."""
    obj = canonical_object(get(component, "ObjectApiName__c") or "")
    if not obj:
        raise ValueError("the component has no ObjectApiName__c")
    files, renamed = {}, {}
    if form_object:
        form_object_value = form_object
    elif bare(obj) in PACKAGED_FORM_OBJECTS or obj in PACKAGED_FORM_OBJECTS:
        form_object_value = NS + PACKAGED_FORM_OBJECTS.get(bare(obj) if obj.startswith(NS) else obj)
    elif new_form_object:
        form_object_value = short_name(re.sub(r"__c$", "", obj))
        files[f"{NS}Form_Object.{form_object_value}.md-meta.xml"] = record_xml(obj, [("IsActive__c", True), ("Object__c", obj)])
    else:
        raise ValueError(f"no packaged Form Object for {obj}: pass --form-object with the org's Form Object record name "
                         "(SELECT QualifiedApiName, FlowToolKit__Object__c FROM FlowToolKit__Form_Object__mdt), or --new-form-object")

    def name_of(qname):
        record = short_name(qname)
        if record != qname:
            renamed[qname] = record
        return record

    form = name_of(component["QualifiedApiName"])
    root = ns_config(component, skip=("ObjectApiName__c", "Form_Object__c", "Active__c", "type__c"))
    config = {"attributes": {"type": NS + RECORD_TYPE["Form"]}, NS + "Active__c": bool(get(component, "Active__c", True)),
              NS + "Form_Object__c": form_object_value, NS + "type__c": get(component, "type__c") or "form"}
    config.update(root)
    for width in ("widthSmall__c", "widthMedium__c", "widthLarge__c"):
        config.setdefault(NS + width, "12")
    columns = [("Active__c", config[NS + "Active__c"]), ("CategoryTag__c", get(component, "CategoryTag__c")),
               ("Delete__c", False), ("Description__c", get(component, "Description__c")),
               ("Form_Object__c", form_object_value), ("type__c", config[NS + "type__c"]),
               ("config__c", json.dumps(config, indent=2, ensure_ascii=False))]
    if get(component, "prefill__c"):
        columns.append(("prefill__c", get(component, "prefill__c")))
    files[f"{NS}Form.{form}.md-meta.xml"] = record_xml(component.get("Label") or form, [c for c in columns if c[1] is not None])

    rule_names = {bare(r.get("QualifiedApiName")): name_of(bare(r["QualifiedApiName"])) for r in get(component, "conditionalLogic__r") or []}
    for rule in get(component, "conditionalLogic__r") or []:
        rname = rule_names[bare(rule["QualifiedApiName"])]
        config = {"attributes": {"type": NS + RECORD_TYPE["Form_Conditional_Logic"]}, NS + "Form__c": form}
        config.update(ns_config(rule))
        config.setdefault(NS + "conditionType__c", "AND")
        files[f"{NS}Form_Conditional_Logic.{rname}.md-meta.xml"] = record_xml(
            rule.get("Label") or rname, [("Delete__c", False), ("Form__c", form), ("config__c", json.dumps(config, indent=2, ensure_ascii=False))])
        for c, cond in enumerate(get(rule, "conditions__r") or [], 1):
            cname = name_of(bare(cond.get("QualifiedApiName") or f"{rule['QualifiedApiName']}_{c}"))
            cobj = canonical_object(get(cond, "Object__c") or obj)
            config = {"attributes": {"type": NS + RECORD_TYPE["Form_Conditional_Logic_Condition"]}, NS + "Form__c": form,
                      NS + "Object__c": cobj, NS + "conditionalLogic__c": rname}
            config.update(ns_config(cond))
            config[NS + "Object__c"] = cobj
            config.setdefault(NS + "position__c", float(c))
            value = get(cond, "value__c")
            files[f"{NS}Form_Conditional_Logic_Condition.{cname}.md-meta.xml"] = record_xml(
                f"Condition {c}: {rule.get('Label') or rname}"[:40],
                [("Delete__c", False), ("Form__c", form), ("Object__c", cobj), ("conditionalLogic__c", rname),
                 ("config__c", json.dumps(config, indent=2, ensure_ascii=False)), ("fieldName__c", full(get(cond, "fieldName__c"))),
                 ("position__c", get(cond, "position__c") or c), ("value__c", None if value in (None, "") else str(value))])

    for s, section in enumerate(get(component, "sections__r") or [], 1):
        sname = name_of(section["QualifiedApiName"])
        logic = get(section, "conditionalLogic__c")
        config = {"attributes": {"type": NS + RECORD_TYPE["Form_Section"]}, NS + "Form__c": form}
        config.update(ns_config(section))
        if logic:
            config[NS + "conditionalLogic__c"] = rule_names.get(bare(logic), bare(logic))
        config.setdefault(NS + "position__c", float(s))
        config.setdefault(NS + "displayType__c", "SHOW")
        for width in ("widthSmall__c", "widthMedium__c", "widthLarge__c"):
            config.setdefault(NS + width, "12")
        columns = [("Delete__c", False), ("Form__c", form), ("position__c", get(section, "position__c") or s),
                   ("conditionalLogic__c", rule_names.get(bare(logic), bare(logic)) if logic else None),
                   ("formComponent__c", get(section, "formComponent__c")), ("Default_Table_Form__c", get(section, "Default_Table_Form__c")),
                   ("contentAssetName__c", get(section, "contentAssetName__c")),
                   ("config__c", json.dumps(config, indent=2, ensure_ascii=False))]
        files[f"{NS}Form_Section.{sname}.md-meta.xml"] = record_xml(
            plain_text(get(section, "title__c") or "") or sname, [c for c in columns if c[1] is not None])
        for f, field in enumerate(get(section, "fields__r") or [], 1):
            fname = name_of(field["QualifiedApiName"])
            fobj = canonical_object(get(field, "Object__c") or obj)
            flogic = get(field, "conditionalLogic__c")
            config = {"attributes": {"type": NS + RECORD_TYPE["Form_Field"]}, NS + "Form__c": form, NS + "Form_Section__c": sname,
                      NS + "Object__c": fobj}
            config.update(ns_config(field))
            config[NS + "Object__c"] = fobj
            if flogic:
                config[NS + "conditionalLogic__c"] = rule_names.get(bare(flogic), bare(flogic))
            config.setdefault(NS + "position__c", float(f))
            config.setdefault(NS + "displayType__c", "SHOW")
            for width in ("widthSmall__c", "widthMedium__c", "widthLarge__c"):
                config.setdefault(NS + width, "12")
            label = plain_text(get(field, "customLabel__c") or "") or re.sub(r"__c$", "", bare(get(field, "fieldName__c") or fname)).replace("_", " ")
            columns = [("Delete__c", False), ("Form__c", form), ("Form_Section__c", sname), ("Object__c", fobj),
                       ("addressFieldType__c", get(field, "addressFieldType__c")),
                       ("conditionalLogic__c", rule_names.get(bare(flogic), bare(flogic)) if flogic else None),
                       ("config__c", json.dumps(config, indent=2, ensure_ascii=False)),
                       ("fieldName__c", full(get(field, "fieldName__c"))), ("position__c", get(field, "position__c") or f),
                       ("readOnly__c", bool(get(field, "readOnly__c", False))), ("required__c", bool(get(field, "required__c", False))),
                       ("referenceFormComponent__c", get(field, "referenceFormComponent__c"))]
            files[f"{NS}Form_Field.{fname}.md-meta.xml"] = record_xml(label, [c for c in columns if c[1] is not None])
    return files, renamed


def read_cmt_folder(folder):
    """Custom metadata record files (an installed org's FlowToolKit__Form... files) back into component JSON, one per Form,
    plus findings about the metadata itself (children arrays, JSON-only keys, missing widths)."""
    records = {t: {} for t in CMT_TYPES}
    findings = []
    for path in sorted(pathlib.Path(folder).glob("*.md-meta.xml")):
        match = re.match(r"^(?:FlowToolKit__)?(Form(?:_Section|_Field|_Conditional_Logic(?:_Condition)?)?)\.(.+)\.md-meta\.xml$", path.name)
        if not match:
            continue
        kind, name = match.groups()
        text = path.read_text(encoding="utf-8")
        columns = {}
        for m in VALUE_RE.finditer(text):
            columns[local(m.group("field"))] = None if "nil" in (m.group("attrs") or "") else html.unescape(m.group("value") or "")
        config = parse_json(columns.get("config__c") or "") or {}
        label = html.unescape((re.search(r"<label>(.*?)</label>", text, re.S) or [None, name])[1])
        where = f"{path.name}"
        children = sorted(k for k in config if local(k).endswith("__r"))
        if children:
            findings.append({"severity": "error", "check": "cmt-children", "where": where, "message": f"config__c carries {children}: "
                             "an empty children array overrides the child records and the form resolves to nothing. Remove them"})
        stray = sorted(k for k in config if k in JSON_ONLY)
        if stray:
            findings.append({"severity": "warning", "check": "cmt-json-only", "where": where, "message": f"config__c carries {stray}, "
                             "which belong to component JSON only"})
        if "attributes" not in config:
            findings.append({"severity": "warning", "check": "cmt-attributes", "where": where,
                             "message": "config__c should carry an attributes key naming its record type"})
        if kind in ("Form", "Form_Section", "Form_Field"):
            missing = [w for w in ("widthSmall__c", "widthMedium__c", "widthLarge__c") if not any(local(k) == w for k in config)]
            if missing:
                findings.append({"severity": "error", "check": "cmt-widths", "where": where, "message": f"config__c lacks {missing}; "
                                 "a metadata form without explicit widths renders as one column"})
        node = {STAR + local(k): v for k, v in config.items() if k != "attributes" and not local(k).endswith("__r")}
        node["QualifiedApiName"] = name
        node["Label"] = label
        records[kind][name] = (node, columns)
    components = []
    for form_name, (root, columns) in records["Form"].items():
        root[STAR + "ObjectApiName__c"] = root.get(STAR + "ObjectApiName__c") or _object_from_form_object(columns.get("Form_Object__c"))
        root[STAR + "sections__r"] = []
        root[STAR + "conditionalLogic__r"] = []
        sections = {}
        for sname, (snode, scols) in records["Form_Section"].items():
            if scols.get("Form__c") == form_name and scols.get("Delete__c") != "true":
                snode[STAR + "fields__r"] = []
                sections[sname] = snode
                root[STAR + "sections__r"].append(snode)
        for fname, (fnode, fcols) in records["Form_Field"].items():
            if fcols.get("Form__c") == form_name and fcols.get("Delete__c") != "true" and fcols.get("Form_Section__c") in sections:
                fnode.setdefault(STAR + "fieldName__c", fcols.get("fieldName__c"))
                sections[fcols["Form_Section__c"]][STAR + "fields__r"].append(fnode)
        rules = {}
        for rname, (rnode, rcols) in records["Form_Conditional_Logic"].items():
            if rcols.get("Form__c") == form_name:
                rnode[STAR + "conditions__r"] = []
                rules[rname] = rnode
                root[STAR + "conditionalLogic__r"].append(rnode)
        for cname, (cnode, ccols) in records["Form_Conditional_Logic_Condition"].items():
            if ccols.get("conditionalLogic__c") in rules:
                rules[ccols["conditionalLogic__c"]][STAR + "conditions__r"].append(cnode)
        for snode in root[STAR + "sections__r"]:
            snode[STAR + "fields__r"].sort(key=lambda n: n.get(STAR + "position__c") or 0)
        root[STAR + "sections__r"].sort(key=lambda n: n.get(STAR + "position__c") or 0)
        components.append(root)
    return components, findings


def _object_from_form_object(value):
    name = bare(value or "")
    for obj, record in PACKAGED_FORM_OBJECTS.items():
        if record == name:
            return canonical_object(obj)
    return name


# ---- plan helpers ----------------------------------------------------------------------------------------------------

def _children_renamed(root, old, new):
    """Every child name (sections, fields, rules, conditions) given the new component's name in front of its old suffix,
    and every value that named an old child rewritten, so the copy shares no name with the original."""
    renames = {}

    def collect(node, in_list=False):
        if isinstance(node, dict):
            name = node.get("QualifiedApiName")
            if in_list and isinstance(name, str) and name not in renames:
                suffix = name[len(old):] if old and name.startswith(old) else "_" + name
                candidate = new + suffix
                renames[name] = candidate if len(candidate) <= 40 else f"{new[:30]}_C{len(renames) + 1:03d}"
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item, True)

    def rewrite(node):
        if isinstance(node, dict):
            return {k: rewrite(v) for k, v in node.items() if k not in ("Id", "attributes") and local(k) not in ("Version__c", "VersionId__c", "Form_Managers__c")}
        if isinstance(node, list):
            return [rewrite(item) for item in node]
        if isinstance(node, str) and (node in renames or bare(node) in renames):
            return renames.get(node) or renames[bare(node)]
        return node
    collect(root)
    return rewrite(root)


def extend_component(original, new_name, added, label=None, description=None):
    """The new version an extend answer asks for: the original copied as it is under new_name, every child renamed,
    plus the added fields at the end of its last input section. The original is never changed."""
    old = original.get("QualifiedApiName") or ""
    if not new_name or not API_NAME.match(new_name) or "__" in new_name:
        raise ValueError("--name must be a new API name: letters, digits and single underscores")
    if bare(new_name) == bare(old):
        raise ValueError(f"extend builds a new version under its own name; {new_name} is the original. Changing the original "
                         "is 'update the shared component', its own question")
    if not added:
        raise ValueError("extend adds at least one field")
    root = _children_renamed(json.loads(json.dumps(original)), old, new_name)
    root["QualifiedApiName"] = new_name
    names = ", ".join(plain_text(get(f, "customLabel__c") or "") or bare(get(f, "fieldName__c") or "") for f in added)
    root["Label"] = (label or f"{original.get('Label') or old} with {names}")[:80]
    root[STAR + "Description__c"] = (description or f"A version of {original.get('Label') or old} with {names} added. The original "
                                     "component is unchanged, so the templates that use it keep it.")[:255]
    for key in [k for k in root if local(k) == "Description__c" and k != STAR + "Description__c"]:
        del root[key]
    sections = get(root, "sections__r") or []
    inputs = [x for x in sections if (get(x, "sectionType__c") or "inputSection") == "inputSection"]
    if not inputs:
        raise ValueError(f"{old} has no input section to add fields to")
    target = inputs[-1]
    fields = get(target, "fields__r")
    if fields is None:
        fields = target.setdefault(STAR + "fields__r", [])
    have = {full(get(f, "fieldName__c") or "") for f in fields}
    start = max([int(get(f, "position__c") or 0) for f in fields] or [0])
    n = 0
    for field in added:
        if full(get(field, "fieldName__c") or "") in have:
            continue
        n += 1
        field = dict(field)
        field[STAR + "position__c"] = start + n
        field["QualifiedApiName"] = f"{new_name[:30]}_FX{start + n}"
        fields.append(field)
    if not n:
        raise ValueError("every added field is already on the component; reuse it instead")
    return root


def plan_findings(plan, component):
    """What plan.json says about this component: an extend answer must never be built over the original."""
    out = []
    name = bare(component.get("QualifiedApiName") or "")
    for item in (plan or {}).get("components") or []:
        if item.get("decision") == "extend" and bare(item.get("name") or "") == name:
            out.append({"severity": "error", "check": "extend-in-place", "where": "root",
                        "message": f"the plan answers extend for {item.get('name')}: build a new version under its own name "
                                   "(component.py extend) and leave the original as it is. Changing the original is 'update the "
                                   "shared component', which needs its own question listing every template it reaches"})
    return out


def planned_fields(plan):
    out = set()
    for page in (plan or {}).get("pages") or []:
        for section in page.get("sections") or []:
            for field in section.get("fields") or []:
                if field.get("new_field") and field.get("field"):
                    out.add((canonical_object(field.get("object") or "Form_Submission__c"), full(field["field"])))
    for item in (plan or {}).get("new_fields") or []:
        if isinstance(item, dict) and item.get("field"):
            out.add((canonical_object(item.get("object") or "Form_Submission__c"), full(item["field"])))
    return out


def submission_map(plan, key):
    """The plan's form_template_mapping ({apply_to, fields: {component field: Form Submission field}}) as the package's
    Submission Field Map ({lookupField, fields: {Form Submission field: component field}})."""
    components = {c.get("key"): c for c in plan.get("components") or []}
    if key not in components:
        raise ValueError(f"plan.json has no component with key {key!r}; keys: {', '.join(k for k in components if k)}")
    mapping = components[key].get("form_template_mapping")
    if not mapping or not mapping.get("fields"):
        raise ValueError(f"component {key!r} has no form_template_mapping in the plan")
    apply_to = str(mapping.get("apply_to") or "ALL").strip()
    lookup = "ALL" if apply_to.upper() == "ALL" or apply_to.lower().startswith("all") else full(apply_to)
    out = {}
    for source, target in mapping["fields"].items():
        target = full(target)
        if target in out and out[target] != source:
            raise ValueError(f"{target} is mapped from both {out[target]} and {source}; a Form Submission field takes one mapping")
        out[target] = source
    return {"lookupField": lookup, "fields": out}


# ---- command line ----------------------------------------------------------------------------------------------------

def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"cannot read {path}: {error}") from None


def print_findings(findings, label):
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda f: order.get(f["severity"], 9)):
        print(f"{f['severity'].upper():7} {f['check']:20} {f['where']}: {f['message']}")
    print(f"{label}: {errors} error(s), {warnings} warning(s)")
    return errors


def command_check(args):
    catalog = Catalog(load_json(args.catalog)) if args.catalog else Catalog()
    plan = load_json(args.plan) if args.plan else {}
    edition = args.edition or ((plan.get("intake") or {}).get("edition")) or catalog.edition
    target = pathlib.Path(args.component)
    results = []
    if target.is_dir():
        components, meta = read_cmt_folder(target)
        if not components:
            raise SystemExit(f"no Form records (FlowToolKit__Form.<name>.md-meta.xml) in {target}")
        for component in components:
            checker = Checker(catalog, planned_fields(plan), edition, path="metadata")
            results.append((component.get("QualifiedApiName"), checker.run(component)))
        results.append(("metadata files", meta))
    else:
        checker = Checker(catalog, planned_fields(plan), edition, path="record")
        component = load_json(target)
        results.append((component.get("QualifiedApiName") or target.name, checker.run(component) + plan_findings(plan, component)))
    if not catalog.index:
        note = {"severity": "info", "check": "no-catalog", "where": "-", "message": "no catalog with field lists, so field names, "
                "mapping targets and merges were not checked against the org"}
        results[0][1].append(note)
    if args.json:
        print(json.dumps({name: findings for name, findings in results}, indent=1))
        return 1 if any(f["severity"] == "error" for _, fs in results for f in fs) else 0
    errors = 0
    for name, findings in results:
        errors += print_findings(findings, name)
    return 1 if errors else 0


def command_extend(args):
    added = load_json(args.add)
    if isinstance(added, dict):
        added = [added]
    try:
        root = extend_component(load_json(args.component), args.name, added, args.label, args.description)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    pathlib.Path(args.out).write_text(json.dumps(root, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {args.name}, a new version; the original is unchanged. Check it, import it as a new component, "
          f"and point only this section at {args.name}_v0")
    return 0


def command_map(args):
    try:
        value = submission_map(load_json(args.plan), args.component)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    text = json.dumps(value, separators=(",", ":"))
    if args.into:
        component = load_json(args.into)
        for key in list(component):
            if local(key) == "Submission_Field_Map__c":
                del component[key]
        component[STAR + "Submission_Field_Map__c"] = text
        pathlib.Path(args.into).write_text(json.dumps(component, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote *__Submission_Field_Map__c into {args.into}")
    else:
        print(text)
    return 0


def command_cmt(args):
    component = load_json(args.component)
    findings = Checker(path="metadata").run(component)
    hard = [f for f in findings if f["severity"] == "error"]
    if hard:
        print_findings(hard, "not written; fix these first")
        return 1
    try:
        files, renamed = emit_cmt(component, args.form_object, args.new_form_object)
    except (ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(files.items()):
        (out / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} record file(s) to {out}")
    for long_name, record in renamed.items():
        print(f"  {long_name} is longer than 40 characters; its record is named {record}")
    print("Deploy with: sf project deploy start -o <org-alias> --source-dir " + str(out) + "  then Reset Form Cache in Form Builder")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="check component JSON, or a folder of custom metadata record files")
    check.add_argument("component")
    check.add_argument("--catalog", help="org-catalog's catalog.json")
    check.add_argument("--plan", help="form-design's plan.json (planned new fields, edition)")
    check.add_argument("--edition", choices=["paid", "free"])
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=command_check)
    ex = sub.add_parser("extend", help="a new version of a component with added fields; the original is never changed")
    ex.add_argument("component", help="the original component's JSON (its Export token)")
    ex.add_argument("--name", required=True, help="the new version's API name")
    ex.add_argument("--add", required=True, help="JSON array of the component fields to add")
    ex.add_argument("--out", required=True)
    ex.add_argument("--label")
    ex.add_argument("--description")
    ex.set_defaults(func=command_extend)
    mp = sub.add_parser("map", help="a plan component's Form Template Mapping as the package's Submission Field Map")
    mp.add_argument("plan")
    mp.add_argument("--component", required=True, help="the component's key in plan.json")
    mp.add_argument("--into", help="write it into this component JSON's root")
    mp.set_defaults(func=command_map)
    cmt = sub.add_parser("cmt", help="write custom metadata record files for an org with Flow Tool Kit installed")
    cmt.add_argument("component")
    cmt.add_argument("--out", required=True)
    cmt.add_argument("--form-object", help="the org's Form Object record name for an object the package does not cover")
    cmt.add_argument("--new-form-object", action="store_true", help="also write a Form Object record for the component's object")
    cmt.set_defaults(func=command_cmt)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
