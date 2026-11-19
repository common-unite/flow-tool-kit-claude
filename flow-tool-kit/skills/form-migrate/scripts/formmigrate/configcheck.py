"""Validate a form component config's KEYS and VALUES, not just its field refs.

``componentcheck`` answers "does every field this config references exist?".
This answers the other half: "is every key real, and is every value in its
allowed set?" Both are needed, and neither catches the other's failures.

The renderer is permissive by design. An unknown key is ignored, and a picklist
override with an out-of-set value falls back to the standard control. Both
produce a form that deploys, saves, previews, and renders WRONG, with the config
looking entirely reasonable in the repo. On the first real run of this package a
generated config carried numeric ``min__c``/``max__c`` (they are Text(40)) and a
``CategoryTag__c`` of "Surveys" (the picklist has three values, none of them
that). Nothing anywhere would have reported either.

The vocabulary here mirrors the build-form-component skill's key reference.
Both are hand-maintained copies of what the storage objects' field metadata
says, and hand-maintained copies drift. Once this file rejected
``picklistType__c: separatedbuttons`` as out-of-set for months after the package
shipped it, so a CORRECT config was reported as an error and the reference doc
was stale in the same way.

``audit_enums()`` exists so that never has to be discovered by accident again:
point it at a repo that carries the storage objects and it reports any enum here
that disagrees with the metadata, in both directions. It returns nothing in a
client repo that has no such objects, so it is safe to call anywhere.
"""

from __future__ import annotations

import json

# Values that are enumerated in the storage-object metadata. A value outside the
# set is reported; the renderer would silently fall back to the default.
_ENUMS = {
    "type__c": {"form", "table", "default", "scoped", "vertical", "carousel", "review"},
    "CategoryTag__c": {"Component(s)", "Form(s)", "Template(s)"},
    "sectionType__c": {
        "inputSection", "addressSection", "richTextSection", "accordionSection",
        "carouselSection", "dividerSection", "illustrationSection", "imageSection",
        "tableSection", "formComponent", "flowScreen", "lwcSection", "likertSection",
        "recordCardSection", "bannerSection",
    },
    "Likert_Mode__c": {"Picklist", "Number"},
    "Message_Variant__c": {"default", "info", "warning", "error", "success"},
    "sectionTheme__c": {"clean", "shadow", "box", "visualPicker"},
    "picklistType__c": {
        "standard", "radio", "radiobuttons", "separatedbuttons", "iconbuttons",
        "pathbuttons", "multiselectcheckbox", "multiselectbadge",
        "selectallmultiselectcheckbox", "combobox", "surveybuttons", "visualpicker",
        "iconselector", "emailtemplateselector", "imageassetselector",
        "stylesheetselector",
    },
    "booleanType__c": {"default", "checkbox", "picklist", "radio", "radiobuttons",
                       "attestation"},
    "numberType__c": {"standard", "stepper", "slider", "presetamounts"},
    "stringType__c": {"standard", "textarea", "iconselector", "emailtemplateselector",
                      "imageassetselector", "stylesheetselector"},
    "longTextType__c": {"default", "fileUpload"},
    "richTextType__c": {"standard", "signaturePad", "imageUpload"},
    "addressFieldType__c": {"Address", "Street", "City", "State", "PostalCode",
                            "Country"},
    "labelVariant__c": {"standard", "label-hidden", "none", "label-inline",
                        "label-stacked", "left", "right"},
    "helpTextDisplay__c": {"Hover Bubble", "Below Label", "Below Field"},
    "iconPicklistOverrideIconSize__c": {"small", "medium", "large"},
    "currencyDisplayAs__c": {"symbol", "code", "name"},
    "Illustration_Size__c": {"small", "large"},
    "modalSize__c": {"small", "medium", "large", "full"},
}

# displayType__c allows 4 values on a field but only 2 on a section.
_DISPLAY_TYPE_FIELD = {"SHOW", "HIDE", "REQUIRED", "READONLY"}
_DISPLAY_TYPE_SECTION = {"SHOW", "HIDE"}

# Text(255) fields whose overflow breaks the FIRST builder save, not the deploy.
_MAX_255 = {
    "customLabel__c", "helpText__c", "placeholder__c", "customValidationMessage__c",
    "formatAlertMessage__c", "fileNameFormat__c", "validationFormat__c",
    "Alternative_Field__c", "Total_Score_Label__c", "Label__c", "Description__c",
    "QualifiedApiName__c", "VersionId__c",
}

# Keys the metadata types STORE AS TEXT even though the value looks numeric.
# Emitting a JSON number here produces a type mismatch on save.
_TEXT_NOT_NUMBER = {"min__c", "max__c", "step__c", "inlineLabelWidth__c",
                    "textAreaMinHeight__c", "textAreaMaxHeight__c"}

# Genuinely numeric keys, for contrast.
_NUMERIC = {"position__c", "Version__c", "minDays__c", "maxDays__c",
            "columnInitialWidth__c", "columnFixedWidth__c", "imageOverlayOpacity__c",
            "minimumIntegerDigits__c", "minimumFractionDigits__c",
            "maximumFractionDigits__c", "minimumSignificantDigits__c",
            "maximumSignificantDigits__c"}

# Widths are strings 1-12, plus shrink at FIELD level only.
_WIDTH_KEYS = {"widthSmall__c", "widthMedium__c", "widthLarge__c"}

# Section flags the JSON render path never recomputes; the matching one MUST be
# authored or the section renders as nothing.
_SECTION_FLAG = {
    "inputSection": "isInputSection",
    "richTextSection": "isRichTextSection",
    "addressSection": "isAddressSection",
    "imageSection": "isImageSection",
    "formComponent": "isFormComponentSection",
    "dividerSection": "isDividerSection",
    "illustrationSection": "isIllustrationSection",
    "flowScreen": "isFlowSection",
    "lwcSection": "isLwcSection",
    "likertSection": "isLikertSection",
    "recordCardSection": "isRecordCardSection",
    "bannerSection": "isBannerSection",
}

# Baked SLDS strings Apex precomputes and the JSON path does not.
_BAKED_SECTION_KEYS = ("sectionVerticalPadding", "sectionMarginClass", "richTextClass")

# Keys present on 100% of the records in a real org (155 root, 506 section and
# 754 field configs, zero exceptions). The renderer branches on
# them UNGUARDED, so an absent key is undefined and the component dies partway
# through materializing -- the Form Builder left orphan sections behind on the
# form that failed.
#
# Hand-authored configs that omit them crash the form partway through loading.
_REQUIRED_ROOT = {
    "Active__c": True, "Form_Object__c": None, "horizontalAlign__c": "start",
    "type__c": "form", "widthSmall__c": "12", "widthMedium__c": "12",
    "widthLarge__c": "12",
}
_REQUIRED_SECTION = {
    "position__c": None, "sectionType__c": None, "displayType__c": "SHOW",
    "showHeader__c": False, "sectionTheme__c": "clean",
    "horizontalAlign__c": "start", "accordionOpen__c": False,
    "enableAccordion__c": False, "displayAsPrompt__c": False,
    "viewAsPlainText__c": False, "marginTop__c": "slds-m-top_none",
    "marginBottom__c": "slds-m-bottom_none", "paddingTop__c": "slds-p-top_none",
    "paddingBottom__c": "slds-p-bottom_none", "paddingLeft__c": "slds-p-left_none",
    "paddingRight__c": "slds-p-right_none", "widthSmall__c": "12",
    "widthMedium__c": "12", "widthLarge__c": "12",
}
_REQUIRED_FIELD = {
    "fieldName__c": None, "position__c": None, "Object__c": None,
    "displayType__c": "SHOW", "required__c": False, "readOnly__c": False,
    "disableHelpText__c": False, "alignAbsoluteCenter__c": False,
    "labelAlignAbsoluteCenter__c": False, "enableCustomLookup__c": False,
    "triggerFormulaRecalculation__c": False, "columnWrapText__c": False,
    "labelVariant__c": "standard", "picklistType__c": "standard",
    "picklistColumnsSize__c": "none", "booleanType__c": "default",
    "booleanPicklistTypeOverride__c": "default", "richTextType__c": "standard",
    "referenceFieldOverrideType__c": "standard", "promptDisplayType__c": "prompt",
    "promptDisplayValue__c": "custom", "iconPicklistOverrideIconSize__c": "small",
    "minDateType__c": "specificDate", "maxDateType__c": "specificDate",
    "minBeforeAfter__c": "before", "maxBeforeAfter__c": "before",
    "minute__c": "numeric", "phoneMask__c": "(xxx) xxx-xxxx",
    "currencyCode__c": "USD", "currencyDisplayAs__c": "symbol",
    "columnAlignment__c": "left", "columnIconPosition__c": "left",
    "columnVisibility__c": "visible", "topMargin__c": "slds-m-top_none",
    "bottomMargin__c": "slds-m-bottom_none", "widthSmall__c": "12",
    "widthMedium__c": "12", "widthLarge__c": "12",
}


def required_defaults(level: str) -> dict:
    """The full default set for a level, for generators to merge in."""
    return dict({"root": _REQUIRED_ROOT, "section": _REQUIRED_SECTION,
                 "field": _REQUIRED_FIELD}[level])


def _check_required(node: dict, path: str, level: str) -> list[dict]:
    """No-op. Retained so callers do not break.

    This once required 41 "universal" keys, derived from 754 records generated
    by an OLD builder that wrote every default. A form built in the CURRENT
    Form Builder carries 10 root / 9 section / 12-16 field keys: config__c holds
    only what is actually SET. Requiring the long set was measuring history, not
    a rule. The real fatal defect is check_cmt() below.
    """
    return []
    # unreachable, kept for reference
    required = {"root": _REQUIRED_ROOT, "section": _REQUIRED_SECTION,
                "field": _REQUIRED_FIELD}[level]
    present = {_local(key) for key in node}
    missing = sorted(key for key in required if key not in present)
    if not missing:
        return []
    return [_finding(
        "error", "missing-required",
        f"{path}: {len(missing)} key(s) that every record in the package carries "
        f"are absent: {', '.join(missing)}. The renderer reads these unguarded, "
        "so the component crashes partway through rendering. Merge "
        f"configcheck.required_defaults('{level}') in.",
        keys=missing, level=level)]


_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _finding(severity, check, message, **extra):
    return {"severity": severity, "check": check, "message": message, **extra}


def _local(key: str) -> str:
    """Strip the namespace escape so a key can be looked up by its plain name."""
    return key.replace("*__", "").replace("FlowToolKit__", "")


def _check_value(key: str, value, path: str, level: str) -> list[dict]:
    local = _local(key)
    findings = []

    if local == "displayType__c":
        allowed = _DISPLAY_TYPE_SECTION if level == "section" else _DISPLAY_TYPE_FIELD
        if value not in allowed:
            findings.append(_finding(
                "error", "bad-value",
                f"{path}: displayType__c is {value!r}; at {level} level only "
                f"{sorted(allowed)} are valid.", key=key, value=value))
        return findings

    if local in _ENUMS and value not in _ENUMS[local]:
        findings.append(_finding(
            "error", "bad-value",
            f"{path}: {local} is {value!r}, which is not in its value set. The "
            f"renderer falls back to the default silently. Valid: "
            f"{sorted(_ENUMS[local])}", key=key, value=value))

    if local in _TEXT_NOT_NUMBER and isinstance(value, (int, float)) and not isinstance(value, bool):
        findings.append(_finding(
            "error", "wrong-type",
            f"{path}: {local} is stored as Text(40) but was emitted as the number "
            f"{value}. Quote it.", key=key, value=value))

    if local in _NUMERIC and isinstance(value, str):
        findings.append(_finding(
            "warning", "wrong-type",
            f"{path}: {local} is numeric but was emitted as the string {value!r}.",
            key=key, value=value))

    if local in _MAX_255 and isinstance(value, str) and len(value) > 255:
        findings.append(_finding(
            "error", "too-long",
            f"{path}: {local} is {len(value)} chars; Text(255) overflow deploys "
            "fine and then breaks the FIRST builder save.", key=key))

    if local in _WIDTH_KEYS:
        allowed = {str(n) for n in range(1, 13)}
        if local == "widthLarge__c" and level == "field":
            allowed.add("shrink")
        if str(value) not in allowed:
            findings.append(_finding(
                "error", "bad-value",
                f"{path}: {local} is {value!r}; expected a string 1-12"
                + (" or 'shrink'" if local == "widthLarge__c" and level == "field" else "")
                + ".", key=key, value=value))
        elif not isinstance(value, str):
            findings.append(_finding(
                "warning", "wrong-type",
                f"{path}: {local} should be a string, got {type(value).__name__}.",
                key=key))

    if local == "iconPicklistOverrideActiveColor__c" and isinstance(value, str) and len(value) > 7:
        findings.append(_finding(
            "error", "too-long",
            f"{path}: iconPicklistOverrideActiveColor__c is Text(7); {value!r} is "
            f"{len(value)}. Use a 6-digit hex with the hash.", key=key))

    return findings


def check(config: dict) -> list[dict]:
    """Validate one component config. Empty result means conforming."""
    findings: list[dict] = []

    for required in ("QualifiedApiName",):
        if not config.get(required):
            findings.append(_finding(
                "error", "missing-key",
                f"root: {required} is required; convertFormJSON returns early "
                "without it and the component renders as nothing."))

    findings.extend(_check_required(config, "root", "root"))
    for key, value in config.items():
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            findings.extend(_check_value(key, value, "root", "root"))

    sections = config.get("*__sections__r") or config.get("FlowToolKit__sections__r") or []
    if not isinstance(sections, list):
        findings.append(_finding("error", "bad-shape",
                                 "root: sections__r must be a plain JSON array."))
        return sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f["severity"], 9))

    for index, section in enumerate(sections):
        path = f"sections[{index}]"
        if not section.get("QualifiedApiName"):
            findings.append(_finding("error", "missing-key",
                                     f"{path}: QualifiedApiName is required."))

        findings.extend(_check_required(section, path, "section"))
        section_type = None
        for key, value in section.items():
            if _local(key) == "sectionType__c":
                section_type = value
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                findings.extend(_check_value(key, value, path, "section"))

        if section_type is None:
            findings.append(_finding("error", "missing-key",
                                     f"{path}: sectionType__c is required."))
        else:
            flag = _SECTION_FLAG.get(section_type)
            if flag and not section.get(flag):
                findings.append(_finding(
                    "error", "missing-flag",
                    f"{path}: sectionType {section_type!r} needs its baked flag "
                    f"{flag}: true. The JSON render path does NOT recompute these, "
                    "so the section silently renders as nothing.", key=flag))

        for baked in _BAKED_SECTION_KEYS:
            if baked not in section:
                findings.append(_finding(
                    "warning", "missing-baked",
                    f"{path}: {baked} is precomputed by Apex and not recomputed on "
                    "the JSON path; author it or spacing renders unstyled.",
                    key=baked))

        fields = section.get("*__fields__r")
        if fields is None:
            fields = section.get("FlowToolKit__fields__r")
        if fields is None:
            findings.append(_finding(
                "error", "missing-key",
                f"{path}: fields__r must be present on every section, even if []."))
            continue

        for field_index, field in enumerate(fields):
            field_path = f"{path}.fields[{field_index}]"
            if not field.get("QualifiedApiName"):
                findings.append(_finding("error", "missing-key",
                                         f"{field_path}: QualifiedApiName is required."))
            findings.extend(_check_required(field, field_path, "field"))
            for key, value in field.items():
                if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                    findings.extend(_check_value(key, value, field_path, "field"))

    return sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f["severity"], 9))


def check_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return check(json.load(handle))


def check_directory(directory: str) -> dict[str, list[dict]]:
    import os

    return {
        entry: check_file(os.path.join(directory, entry))
        for entry in sorted(os.listdir(directory))
        if entry.endswith(".json")
    }


# --- self-audit ------------------------------------------------------------

_ENUM_OBJECTS = ("Form_Component__c", "Form_Component_Section__c",
                 "Form_Component_Field__c")
_MDAPI_NS = {"sf": "http://soap.sforce.com/2006/04/metadata"}


def _metadata_value_sets(source_root):
    """{field name: {object: {values}}} for enumerated fields, from field-meta.xml."""
    import xml.etree.ElementTree as ElementTree
    from pathlib import Path

    found: dict[str, dict[str, set]] = {}
    for object_name in _ENUM_OBJECTS:
        fields_dir = Path(source_root) / object_name / "fields"
        if not fields_dir.is_dir():
            continue
        for path in fields_dir.glob("*.field-meta.xml"):
            root = ElementTree.parse(path).getroot()
            name = root.findtext("sf:fullName", default="", namespaces=_MDAPI_NS)
            values = {v.text for v in root.iterfind(
                ".//sf:valueSetDefinition/sf:value/sf:fullName", _MDAPI_NS)}
            if values:
                found.setdefault(name, {})[object_name] = values
    return found


def audit_enums(source_root="force-app/main/default/objects") -> list[dict]:
    """Report where _ENUMS disagrees with the storage objects' field metadata.

    Empty result means in sync, OR that this repo has no storage objects to
    compare against (a client repo). Both are silent by design - the point is to
    catch drift where the metadata IS present, not to nag where it cannot be.

    Two directions matter and they fail differently. A value the metadata has and
    _ENUMS lacks makes this module reject CORRECT config, which is how
    separatedbuttons was found. A value _ENUMS has and the metadata lacks means a
    real mistake sails through unreported.
    """
    metadata = _metadata_value_sets(source_root)
    if not metadata:
        return []

    findings = []
    for key, declared in sorted(_ENUMS.items()):
        per_object = metadata.get(key)
        if not per_object:
            continue
        union = set().union(*per_object.values())

        absent = union - declared
        if absent:
            findings.append(_finding(
                "error", "enum-stale",
                f"{key}: metadata has {sorted(absent)} but _ENUMS does not. "
                "Valid config using these values is being reported as an error.",
                key=key))

        surplus = declared - union
        if surplus:
            findings.append(_finding(
                "warning", "enum-surplus",
                f"{key}: _ENUMS has {sorted(surplus)} but no metadata value set "
                "does. Either the value was removed or the name is wrong; real "
                "mistakes using it go unreported.", key=key))

        if len({frozenset(v) for v in per_object.values()}) > 1:
            shape = ", ".join(f"{o}={len(v)}" for o, v in sorted(per_object.items()))
            findings.append(_finding(
                "warning", "enum-ambiguous",
                f"{key}: the value set differs by object ({shape}), but _ENUMS is "
                "keyed on field name alone, so one object is validated against "
                "the other's vocabulary.", key=key))

    return findings


# --- CMT config__c ---------------------------------------------------------
#
# A DIFFERENT PIPELINE from the component JSON above, with opposite rules.
# config__c is a flat serialization of ONE record; the hierarchy is assembled by
# querying child CMTs through the Form__c / Form_Section__c lookups.

# Keys that belong to the component-JSON path and must NEVER appear in CMT
# config__c. Verified against a form hand-built in the Form Builder and against
# 661 existing records: zero occurrences.
_JSON_ONLY_IN_CMT = {
    "QualifiedApiName", "Label", "sectionVerticalPadding", "sectionMarginClass",
    "richTextClass", "sectionClass", "fieldClass", "hide", "_joined",
    "validForReview", "Version__c", "VersionId__c", "ObjectApiName__c",
}
_SECTION_FLAGS = {v for v in _SECTION_FLAG.values()}


def check_cmt(config: dict, level: str, path: str = "config__c") -> list[dict]:
    """Validate a CMT config__c payload. Empty result means conforming.

    The one that matters is the children arrays. An empty ``sections__r`` tells
    the render engine the form has ZERO sections, overriding the child CMT
    records it would otherwise find, so the form resolves to nothing and dies
    dereferencing it. This crashed a live Form Template and took four deploys to
    find, because every other check passed.
    """
    findings = []

    children = sorted(k for k in config if _local(k).endswith("__r"))
    if children:
        findings.append(_finding(
            "error", "cmt-children",
            f"{path}: carries child relationship key(s) {children}. CMT config__c "
            "is a FLAT serialization of one record. An empty children array tells "
            "the engine the record has no children and OVERRIDES the child CMTs, "
            "so the form renders as nothing and crashes the template. Remove them.",
            keys=children))

    stray = sorted(_local(k) for k in config if _local(k) in _JSON_ONLY_IN_CMT)
    if stray:
        findings.append(_finding(
            "warning", "cmt-json-only",
            f"{path}: carries {stray}, which belong to the component-JSON path "
            "and appear in zero real CMT records.", keys=stray))

    flags = sorted(k for k in config if k in _SECTION_FLAGS)
    if flags:
        findings.append(_finding(
            "warning", "cmt-json-only",
            f"{path}: carries is*Section flag(s) {flags}. Those are JSON-path "
            "render-branch flags; CMT uses sectionType__c alone.", keys=flags))

    if "attributes" not in config:
        findings.append(_finding(
            "warning", "cmt-attributes",
            f"{path}: every real record carries an 'attributes' key naming its "
            "sobject type."))

    widths = {"widthSmall__c", "widthMedium__c", "widthLarge__c"}
    missing = sorted(w for w in widths if not any(_local(k) == w for k in config))
    if missing:
        findings.append(_finding(
            "error", "cmt-widths",
            f"{path}: missing {missing}. A CMT config without explicit widths "
            "renders as a single column; '12' is stripped by the builder on SAVE "
            "but is not optional on the way in.", keys=missing))

    return sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f["severity"], 9))
