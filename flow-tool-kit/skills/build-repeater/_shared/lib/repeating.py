"""Shared core for Repeater and Table builds: the spec, the checks, and the two writers.

build-repeater (scripts/repeater.py) and build-table (scripts/table.py) import this module from their own
_shared/lib/ copy and add only what is particular to their kind: the flow screen component's property list and the
kind's own section fields. The rules it enforces are written out in standards/repeating-rows.md.

A spec is one JSON object (see either build skill's SKILL.md, "The spec"). Two writers:

    section_fields(spec, ...)  the Form Template Page Section fields, bare names for plan.json or
                               namespaced for a record update
    flow_field_xml(spec, ...)  the <fields> element for a flow screen, with its input parameters

Python 3 standard library only. Works the same in claude.ai chat (code execution) and Claude Code.
"""
import json
import re
from xml.sax.saxutils import escape

KINDS = ("repeater", "table")
PLACES = ("section", "flow-screen")
ACTIONS = ("new", "edit", "clone", "delete")

# Page section fields (Form_Template_Page_Section__c), read from the package source.
SECTION_ACTION_FIELDS = {
    "new": ("Enable_New_Action__c", "New_Action_Button_Label__c"),
    "edit": ("Enable_Edit_Action__c", "Edit_Action_Button_Label__c"),
    "clone": ("Enable_Clone_Action__c", "Clone_Action_Button_Label__c"),
    "delete": ("Enable_Delete_Action__c", "Delete_Action_Button_Label__c"),
}
SECTION_LABELS = {
    "new": ("New", "Add", "Create", "Insert"),
    "edit": ("Edit", "Update", "Change"),
    "clone": ("Clone", "Copy", "Duplicate"),
    "delete": ("Delete", "Remove", "Clear"),
}
FLOW_ACTION_PROPS = {
    "new": ("allowNew", "newButtonLabel"),
    "edit": ("allowEdit", "editButtonLabel"),
    "clone": ("allowClone", "cloneButtonLabel"),
    "delete": ("allowDelete", "deleteButtonLabel"),
}
SPACING = ("none", "xxx-small", "xx-small", "x-small", "small", "medium", "large", "x-large", "xx-large")
BOTTOM_MARGINS = tuple("slds-m-bottom_" + s for s in SPACING)
CONVERSION_RULES = (
    "Bypass", "Contact1", "Contact1 \U0001F449 Set Mailing Address", "Contact1 \U0001F449 Set Other Address",
    "Contact2", "Contact2 \U0001F449 Set Mailing Address", "Contact2 \U0001F449 Set Other Address",
    "Lead1", "Lead2", "Case",
)
SHIPPED_SECTION_TAGS = ("Default", "Contacts", "Tasks", "Cases", "Opportunities")
CONVERSION_FLAGS = {
    "add_to_account": "Add_to_Account__c",
    "add_to_campaign": "Add_to_Campaign__c",
    "update_most_confident_contact": "Update_Most_Confident_Contact__c",
    "update_most_confident_lead": "Update_Most_Confident_Lead__c",
}
CONVERSION_TEXT = {
    "contact_matching_rules": "Contact_Matching_Rules__c",
    "lead_matching_rules": "Lead_Matching_Rules__c",
    "contact_record_type": "Contact_Record_Type__c",
    "case_record_type": "Case_Record_Type__c",
    "data_conversion_tags": "Data_Conversion_Tag_s__c",
}
HEADER_FIELDS = {"title": "Header_Title__c", "subtitle": "Header_Subtitle__c", "icon": "Header_Icon_Name__c",
                 "text": "Header_Text__c"}
TEXT_LIMIT = 255
ROW_LIMIT = 999            # Min__c and Max__c hold three digits
DEFAULT_MIN = 1            # Min__c's field default, and the flow component's
DEFAULT_MAX = 5            # Max__c's field default, and the flow component's
SECTION_ZERO_MAX = 10      # a page section passes a Max__c of 0 (or one cleared on a saved section) as 10
TABLE_ROWS = 5             # about this many rows or more: a Table
TABLE_FIELDS = 8           # about this many questions per row or more: a Table with key columns
DEFAULT_NAMESPACE = "FlowToolKit"
FORM_SUBMISSION = "Form_Submission__c"
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
EM_DASH = chr(0x2014)


class SpecError(Exception):
    """A spec that cannot be read at all (not JSON, wrong kind or place)."""


class Finding:
    def __init__(self, level, code, message):
        self.level, self.code, self.message = level, code, message

    def __repr__(self):
        return "%s %s: %s" % (self.level.upper(), self.code, self.message)

    __str__ = __repr__


def error(code, message):
    return Finding("error", code, message)


def warning(code, message):
    return Finding("warning", code, message)


def errors(findings):
    return [f for f in findings if f.level == "error"]


# ---------------------------------------------------------------- reading the spec
def load_spec(path, kind=None):
    try:
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SpecError("cannot read %s: %s" % (path, e))
    return validate_shape(spec, kind)


def validate_shape(spec, kind=None):
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a JSON object")
    spec.setdefault("kind", kind)
    if spec["kind"] not in KINDS:
        raise SpecError("kind must be one of %s" % ", ".join(KINDS))
    if kind and spec["kind"] != kind:
        raise SpecError("this spec is a %s; use the %s skill's script" % (spec["kind"], spec["kind"]))
    spec.setdefault("where", "section")
    if spec["where"] not in PLACES:
        raise SpecError("where must be one of %s" % ", ".join(PLACES))
    return spec


def action(spec, name):
    """(enabled, settings) for one action. A spec writes true, false, a label string, or an object."""
    raw = (spec.get("actions") or {}).get(name)
    if raw is None or raw is False:
        return False, {}
    if raw is True:
        return True, {}
    if isinstance(raw, str):
        return True, {"label": raw}
    if isinstance(raw, dict):
        settings = dict(raw)
        return settings.pop("enabled", True) is not False, settings
    return False, {"_bad": raw}


def namespaced_object(name, namespace=DEFAULT_NAMESPACE):
    if not name or name == FORM_SUBMISSION:
        return "%s__%s" % (namespace, FORM_SUBMISSION) if namespace else FORM_SUBMISSION
    return name


# ---------------------------------------------------------------- the decision rule
def recommend(expected_rows=None, fields_per_row=None, condensed=False):
    """('repeater' or 'table', reason). The rule repeating-data asks with: a handful of fields and a few rows is a
    Repeater; about five rows or more, many questions per row, or a section that must stay compact is a Table."""
    if condensed:
        return "table", "the section must stay compact: a Table shows one line per row and opens the rest in a window"
    if expected_rows is not None and expected_rows >= TABLE_ROWS:
        return "table", ("about %d rows: a Repeater would be a long scroll, a Table shows the key columns and "
                         "opens each row's questions in a window" % expected_rows)
    if fields_per_row is not None and fields_per_row >= TABLE_FIELDS:
        return "table", ("%d questions per row: a Table shows a few key columns and keeps the rest in the Edit "
                         "window" % fields_per_row)
    return "repeater", "a handful of questions and a few rows: every question stays on the page, row by row"


# ---------------------------------------------------------------- checks every build runs
def check_common(spec, org_tags=None):
    """Findings shared by both kinds. org_tags: the org's Section Tag values when known (else the shipped ones)."""
    out = []
    kind, where = spec["kind"], spec["where"]
    section = where == "section"

    # the component the rows are built from
    if not spec.get("component") and not spec.get("component_json"):
        out.append(error("component", "name the %s component (component) or give its JSON (component_json)"
                         % ("row" if kind == "repeater" else "table")))
    if spec.get("component") and spec.get("component_json"):
        out.append(error("component", "give the component by name or as JSON, not both"))
    shape = spec.get("component_shape")
    if shape and shape not in ("json", "record", "metadata"):
        out.append(error("shape", "component_shape is json, record or metadata"))
    if shape == "json" and spec.get("component"):
        out.append(error("shape", "component_shape json needs component_json, not a component name"))
    if shape == "record" and spec.get("component") and not str(spec["component"]).endswith("_v0"):
        out.append(warning("shape", "a record component is placed as <Name>_v0; %r would load a metadata component"
                           % spec["component"]))
    if shape == "metadata" and not spec.get("component_exists"):
        out.append(warning("shape", "a new component is JSON on the section by default, a record component when "
                           "reuse is known now; metadata comes later through convert-to-metadata"))

    # minimum and maximum rows
    rows = spec.get("rows") or {}
    lo, hi = rows.get("min"), rows.get("max")
    for name, value in (("min", lo), ("max", hi)):
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= ROW_LIMIT):
            out.append(error("rows", "rows.%s must be a whole number from 0 to %d" % (name, ROW_LIMIT)))
    good = lambda v: isinstance(v, int) and not isinstance(v, bool)
    # Not set: a new page section takes the field defaults and the flow component its property defaults (1 and 5).
    # A Max of 0 is read as 10 on a page section and as 5 on a flow screen.
    eff_lo = lo if good(lo) else DEFAULT_MIN
    eff_hi = hi if good(hi) and hi else (DEFAULT_MAX if hi is None else (SECTION_ZERO_MAX if section else DEFAULT_MAX))
    if good(lo) and good(hi) and hi and lo > hi:
        out.append(error("rows", "rows.min (%d) is above rows.max (%d)" % (lo, hi)))
    elif eff_lo > eff_hi:
        out.append(error("rows", "rows.min (%d) is above the maximum the form will use (%d)" % (eff_lo, eff_hi)))
    if kind == "repeater" and hi is None:
        out.append(warning("rows", "rows.max is not set: the Repeater takes the default, %d rows; set min and max "
                           "on purpose" % DEFAULT_MAX))
    if kind == "repeater" and hi == 0:
        out.append(warning("rows", "rows.max 0 is read as %d rows%s" % (eff_hi, " on a page section" if section
                                                                        else "")))
    if kind == "table" and (lo or hi):
        out.append(warning("rows", "the Table does not enforce min or max in the package version these notes were "
                           "read from; if the count must be limited, use a Repeater or check it in the conversion"))

    # actions and labels
    for name in ACTIONS:
        on, settings = action(spec, name)
        if "_bad" in settings:
            out.append(error("actions", "actions.%s must be true, false, a label or an object" % name))
            continue
        label = settings.get("label")
        if not on and settings:
            out.append(warning("actions", "actions.%s has settings but is off; turn it on or drop them" % name))
        if label is None:
            continue
        if section and label not in SECTION_LABELS[name]:
            out.append(error("labels", "the %s label %r is not one of %s (the page section editor offers only those)"
                             % (name, label, ", ".join(SECTION_LABELS[name]))))
        elif not section and len(str(label)) > 40:
            out.append(warning("labels", "the %s label is long for a button: %r" % (name, label)))

    # prefill
    prefill = spec.get("prefill") or {}
    tag = prefill.get("section_tag")
    if section:
        if prefill.get("planned") and not tag:
            out.append(error("section_tag", "a prefill flow will fill these rows: set prefill.section_tag, the "
                             "Section Tag its Prefill From Mapped Record step (Related Records) names"))
        if tag:
            allowed = tuple(org_tags) if org_tags else SHIPPED_SECTION_TAGS
            if tag not in allowed:
                level = error if org_tags else warning
                out.append(level("section_tag", "Section Tag %r is not a Data Conversion Tag(s) value%s: add it in "
                                 "Setup, Picklist Value Sets, Data Conversion Tag(s), before the build"
                                 % (tag, " in this org" if org_tags else " as shipped")))
        if prefill.get("rows_from_section"):
            out.append(error("own_rows", "rows live only in their own section; a section never shows another "
                             "section's rows. Give this section its own prefill"))
        template_id = prefill.get("template")
        if template_id and not re.match(r"^[a-zA-Z0-9]{15}([a-zA-Z0-9]{3})?$", str(template_id)):
            out.append(error("prefill", "prefill.template is the Id of a Form Submission marked as a prefill template"))
    else:
        flow = spec.get("flow") or {}
        if tag:
            out.append(warning("section_tag", "a Section Tag belongs to a page section; on a flow screen the rows "
                               "come in through the rows variable"))
        if prefill.get("planned") and not flow.get("rows_variable"):
            out.append(error("prefill", "prefill is planned: name the flow's record collection in flow.rows_variable"))

    # conversion
    conv = spec.get("conversion")
    if conv:
        if not section:
            out.append(error("conversion", "conversion settings belong to a page section; a screen flow saves its "
                             "own rows (Insert, Update and Delete Collections)"))
        rule = conv.get("rule", "Bypass")
        if rule not in CONVERSION_RULES:
            out.append(error("conversion", "conversion.rule %r is not a Conversion Rule value" % rule))
        flow_value = conv.get("map_flow", "Default")
        if flow_value != "Default":
            if rule == "Bypass":
                out.append(error("conversion", "a Conversion Map Flow under Bypass converts nothing; set the rule"))
            if not API_NAME.match(str(flow_value)):
                out.append(error("conversion", "conversion.map_flow is the flow's API name, not its label: %r"
                                 % flow_value))
            out.append(warning("conversion", "%r must be a Conversion Map Flow value included under %r; run "
                               "new-mapping-flow's wiring check" % (flow_value, rule)))
        for key in conv:
            if key not in ("rule", "map_flow") and key not in CONVERSION_FLAGS and key not in CONVERSION_TEXT:
                out.append(error("conversion", "conversion.%s is not a section conversion setting" % key))

    margin = spec.get("bottom_margin")
    if margin is not None and margin not in BOTTOM_MARGINS:
        out.append(error("layout", "bottom_margin is one of %s" % ", ".join(BOTTOM_MARGINS)))

    # the decision rule, as a second opinion
    advised, reason = recommend(rows.get("expected", hi), spec.get("fields_per_row"), spec.get("condensed", False))
    if advised != kind:
        out.append(warning("decision", "the rule points to a %s: %s. Keep the %s only if the person chose it"
                           % (advised.capitalize(), reason, kind.capitalize())))

    # wording
    for key, value in iter_text(spec):
        if EM_DASH in value:
            out.append(error("wording", "%s has an em-dash; use a colon, a comma or a new sentence" % key))
        if key.endswith((".label", ".modal_title", ".modal_subtitle", "title")) and len(value) > TEXT_LIMIT:
            out.append(error("wording", "%s is over %d characters" % (key, TEXT_LIMIT)))
    return out


def iter_text(value, path=""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from iter_text(v, "%s.%s" % (path, k) if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from iter_text(v, "%s[%d]" % (path, i))


def check_extra(spec, known, where_label):
    """spec['extra']: any other property by its API name, checked against the kind's known list."""
    out = []
    for name in (spec.get("extra") or {}):
        if name not in known:
            out.append(error("extra", "%s is not a %s property (see references/properties.md)" % (name, where_label)))
    return out


# ---------------------------------------------------------------- the page section writer
def section_fields(spec, record=False, namespace=DEFAULT_NAMESPACE):
    """Fields shared by both kinds. record=False: bare names and plan keys for build-template's plan.json section.
    record=True: namespaced API names for a record update of an existing section."""
    f = {"Component_Type__c": "Repeater" if spec["kind"] == "repeater" else "Table"}
    if spec.get("title"):
        f["Title__c"] = spec["title"]
    header = spec.get("header") or {}
    for key, field in HEADER_FIELDS.items():
        if header.get(key):
            f[field] = header[key]
    if header:
        f["Show_Header__c"] = header.get("show", bool(header.get("title")))
    rows = spec.get("rows") or {}
    if "min" in rows:
        f["Min__c"] = rows["min"]
    if "max" in rows:
        f["Max__c"] = rows["max"]
    for name in ACTIONS:
        on, settings = action(spec, name)
        switch, label = SECTION_ACTION_FIELDS[name]
        f[switch] = on
        if on and settings.get("label"):
            f[label] = settings["label"]
    prefill = spec.get("prefill") or {}
    if prefill.get("template"):
        f["Prefill_Template__c"] = prefill["template"]
    if prefill.get("section_tag"):
        f["section_tag" if not record else "Section_Tag__c"] = prefill["section_tag"]
    conv = spec.get("conversion") or {}
    if conv:
        f["Conversion_Rule__c"] = conv.get("rule", "Bypass")
        f["Conversion_Map_Flow__c"] = conv.get("map_flow", "Default")
        for key, field in list(CONVERSION_FLAGS.items()) + list(CONVERSION_TEXT.items()):
            if key in conv:
                f[field] = conv[key]
    if spec.get("bottom_margin"):
        f["Bottom_Margin__c"] = spec["bottom_margin"]
    if record:
        # The component: by name, or JSON fixed to the section. In plan.json build-template writes these itself
        # from the section's component entry, so they are only written for a record update.
        obj = namespaced_object(FORM_SUBMISSION, namespace)
        if spec.get("component"):
            f["FormQualifiedApiName__c"] = spec["component"]
            f["FormConfigJSON__c"] = json.dumps({"formSelectionMode": "component", "object": obj,
                                                 "formQualifiedApiName": spec["component"]})
            if spec.get("component_id"):
                f["Form_Component__c"] = spec["component_id"]
        elif spec.get("component_json"):
            f["FormConfigJSON__c"] = json.dumps({"formSelectionMode": "custom", "object": obj,
                                                 "formJsonConfig": json.dumps(spec["component_json"])})
    f.update(spec.get("extra") or {})
    return f


def values_argument(fields):
    """Field=value pairs for sf data update record --values: text in single quotes, quotes escaped."""
    pairs = []
    for name, value in fields.items():
        if isinstance(value, bool):
            text = "true" if value else "false"
        elif isinstance(value, (int, float)):
            text = str(value)
        else:
            text = "'%s'" % str(value).replace("\\", "\\\\").replace("'", "\\'")
        pairs.append("%s=%s" % (name, text))
    return " ".join(pairs)


def apply_namespace(fields, namespace=DEFAULT_NAMESPACE):
    if not namespace:
        return dict(fields)
    return {("%s__%s" % (namespace, k) if k.endswith("__c") else k): v for k, v in fields.items()}


# ---------------------------------------------------------------- the flow screen writer
VALUE_TAGS = {"Boolean": "booleanValue", "Integer": "numberValue", "String": "stringValue"}


def flow_params_common(spec, namespace=DEFAULT_NAMESPACE):
    """Input parameters both flow screen components share, as [(name, kind, value)].
    kind is a Flow value type (Boolean, Integer, String) or 'ref' for an element reference."""
    flow = spec.get("flow") or {}
    p = [("interviewGuid", "ref", "$Flow.InterviewGuid"),
         ("interviewStartDateTime", "ref", "$Flow.InterviewStartTime"),
         ("serverURL", "ref", "$Api.Enterprise_Server_URL_140"),
         ("object", "String", namespaced_object(flow.get("object"), namespace))]
    if spec.get("component"):
        p.append(("formQualifiedApiName", "String", spec["component"]))
    elif spec.get("component_json"):
        p.append(("formJsonEnabled", "Boolean", True))
        p.append(("formJSON", "String", json.dumps(spec["component_json"])))
    if flow.get("rows_variable"):
        p.append(("prefillRecords", "ref", flow["rows_variable"]))
    if flow.get("new_row_variable"):
        p.append(("recordTemplate", "ref", flow["new_row_variable"]))
    rows = spec.get("rows") or {}
    if "min" in rows:
        p.append(("min", "Integer", rows["min"]))
    if "max" in rows:
        p.append(("max", "Integer", rows["max"]))
    for name in ACTIONS:
        on, settings = action(spec, name)
        switch, label = FLOW_ACTION_PROPS[name]
        if on:
            p.append((switch, "Boolean", True))
            if settings.get("label"):
                p.append((label, "String", settings["label"]))
    if spec.get("bottom_margin"):
        p.append(("bottomMargin", "String", spec["bottom_margin"]))
    header = spec.get("header") or {}
    for key, prop in (("title", "title"), ("subtitle", "subtitle"), ("icon", "iconName"), ("text", "richText")):
        if header.get(key):
            p.append((prop, "String", header[key]))
    if header:
        p.append(("showHeader", "Boolean", header.get("show", bool(header.get("title")))))
    return p


def param_kind(value, declared):
    if declared in VALUE_TAGS:
        return declared
    return "String"


def flow_field_xml(element_name, extension, object_name, params, indent="        "):
    """One <fields> screen element, in the shape the package's own flows save."""
    lines = ["<fields>", "    <name>%s</name>" % escape(element_name),
             "    <dataTypeMappings>", "        <typeName>T</typeName>",
             "        <typeValue>%s</typeValue>" % escape(object_name), "    </dataTypeMappings>",
             "    <extensionName>%s</extensionName>" % escape(extension),
             "    <fieldType>ComponentInstance</fieldType>"]
    for name, kind, value in params:
        if kind == "ref":
            inner = "<elementReference>%s</elementReference>" % escape(str(value))
        elif kind == "Boolean":
            inner = "<booleanValue>%s</booleanValue>" % ("true" if value else "false")
        elif kind == "Integer":
            inner = "<numberValue>%s</numberValue>" % float(value)
        else:
            inner = "<stringValue>%s</stringValue>" % escape(str(value))
        lines += ["    <inputParameters>", "        <name>%s</name>" % escape(name),
                  "        <value>", "            " + inner, "        </value>", "    </inputParameters>"]
    lines += ["    <inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>",
              "    <isRequired>true</isRequired>",
              "    <storeOutputAutomatically>true</storeOutputAutomatically>", "</fields>"]
    return "\n".join(indent + line for line in lines) + "\n"


def check_flow_common(spec, known):
    """Flow screen checks both kinds share. known: the component's property table {name: (type, role, ...)}."""
    out = []
    flow = spec.get("flow") or {}
    name = flow.get("element_name")
    if not name or not API_NAME.match(name) or "__" in name or name.endswith("_"):
        out.append(error("flow", "flow.element_name is the screen component's API name, for example "
                         "Additional_Contacts"))
    if not flow.get("rows_variable"):
        out.append(warning("flow", "no flow.rows_variable: rows the person adds are returned only through the "
                           "Insert Collection; bind Prefill Collection to a record collection to keep them on Back"))
    for prop, value in (flow.get("properties") or {}).items():
        if prop not in known:
            out.append(error("flow", "%s is not a property of this component (see references/properties.md)" % prop))
            continue
        declared, role = known[prop][0], known[prop][1]
        if role == "outputOnly":
            out.append(error("flow", "%s is an output; read it from the component, never set it" % prop))
        elif declared == "Boolean" and not isinstance(value, bool):
            out.append(error("flow", "%s takes true or false" % prop))
        elif declared == "Integer" and (not isinstance(value, int) or isinstance(value, bool)):
            out.append(error("flow", "%s takes a whole number" % prop))
        elif declared not in VALUE_TAGS and not (isinstance(value, dict) and "ref" in value):
            out.append(error("flow", "%s takes a flow resource: write {\"ref\": \"<variable>\"}" % prop))
    return out


def flow_params_extra(spec, known):
    out = []
    for prop, value in ((spec.get("flow") or {}).get("properties") or {}).items():
        if isinstance(value, dict) and "ref" in value:
            out.append((prop, "ref", value["ref"]))
        else:
            out.append((prop, param_kind(value, known.get(prop, ("String",))[0]), value))
    return out


def dedupe_params(params):
    """Later entries win, so a property named in flow.properties overrides the spec's own setting."""
    seen = {}
    for item in params:
        seen[item[0]] = item
    return list(seen.values())


# ---------------------------------------------------------------- the command line both scripts share
def run_cli(argv, kind, check_kind, section_kind, flow_kind, doc):
    """check | section | flow-screen, the same for both kinds. Exit 0 clean, 1 errors, 2 a bad spec or argument."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=doc.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("check", "section", "flow-screen"):
        p = sub.add_parser(cmd)
        p.add_argument("spec")
        p.add_argument("--org-tags", help="comma-separated Section Tag values the org has (Data Conversion Tag(s))")
        p.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="the package namespace (blank inside the package)")
        if cmd == "section":
            p.add_argument("--format", choices=("plan", "record", "values"), default="plan",
                           help="plan: bare keys for plan.json; record: namespaced fields as JSON for a record "
                                "update; values: the same as one --values argument for sf data update record")
        if cmd != "check":
            p.add_argument("--out", help="write here instead of printing")
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec, kind)
    except SpecError as e:
        print("ERROR spec: %s" % e, file=sys.stderr)
        return 2
    tags = [t.strip() for t in (args.org_tags or "").split(",") if t.strip()] or None
    findings = check_kind(spec, tags)
    for f in findings:
        print(f, file=sys.stderr if args.command != "check" else sys.stdout)
    if errors(findings):
        return 1
    if args.command == "check":
        print("OK: %d warning(s)" % len(findings))
        return 0
    if args.command == "section":
        if spec["where"] != "section":
            print("ERROR where: this spec is for a flow screen; run flow-screen", file=sys.stderr)
            return 2
        fields = section_kind(spec, record=args.format != "plan", namespace=args.namespace)
        if args.format != "plan":
            fields = apply_namespace(fields, args.namespace)
        if args.format == "values":
            text = values_argument(fields) + "\n"
        else:
            text = json.dumps(fields, indent=2, ensure_ascii=False) + "\n"
    else:
        if spec["where"] != "flow-screen":
            print("ERROR where: this spec is for a page section; run section", file=sys.stderr)
            return 2
        text = flow_kind(spec, namespace=args.namespace)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote %s" % args.out)
    else:
        sys.stdout.write(text)
    return 0
