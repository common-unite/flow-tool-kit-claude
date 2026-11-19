#!/usr/bin/env python3
"""Write and check Flow Tool Kit Flow Section flows.

A Flow Section is a screen flow that runs inside a Form Template page section. The form launches it with the Form
Submission and its navigation context and reads back what it changed. The contract is a set of variables with exact
names and types (references/contract.md). This script writes a new flow from a small spec, in the shape of the
packaged "(Form) Flow Section | Template", and checks any Flow Section flow file against the contract and the
plugin's documentation standard.

    python3 flowsection.py scaffold <section-spec.json> --out <project-dir>
    python3 flowsection.py check <Flow_Api_Name.flow-meta.xml> [--audiences guest,portal] [--namespace FlowToolKit]

scaffold writes <project-dir>/force-app/main/default/flows/<api_name>.flow-meta.xml and prints its path. It refuses
to overwrite an existing file unless --force is given. check prints one line per finding and exits 1 when any
finding is an error.

Exit codes: 0 clean (warnings allowed), 1 errors found, 2 a malformed spec, file or argument.
Python 3 standard library only. Works the same in claude.ai chat (code execution) and Claude Code.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MD = "http://soap.sforce.com/2006/04/metadata"
Q = "{%s}" % MD
ET.register_namespace("", MD)

DEFAULT_NAMESPACE = "FlowToolKit"
DEFAULT_API_VERSION = "68.0"
API_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$")
DEMO_FORMS = {"Form_Organization_Details_Template", "Primary_Contact_Default"}
ISSUE_REF = re.compile(r"(?<![&\w])#\d+")
EM_DASH = chr(0x2014)  # the em-dash, written by code point

# The contract (references/contract.md). Each entry: data type, object (bare, without the package prefix), collection,
# input, output, and what breaks without it.
CONTRACT = {
    "record": ("SObject", "Form_Submission__c", False, True, True,
               "the form passes the submission in and reads the section's changes back from it"),
    "recordId": ("String", None, False, True, True, "the submission Id; optional, kept for screens that need it"),
    "relatedRecords": ("SObject", "Form_Submission__c", True, True, True,
                       "repeater and table rows the section manages"),
    "review": ("Boolean", None, False, True, False, "the form relaunches the section read-only for its review pass"),
    "buttonLabel_Back": ("String", None, False, True, False, "the section's Back button matches the page"),
    "buttonLabel_Next": ("String", None, False, True, False, "the section's Next button matches the page"),
    "buttonLabel_Finish": ("String", None, False, True, False, "the section's last-screen button matches the page"),
    "buttonLabel_SaveProgress": ("String", None, False, True, False, "Save Progress inside the section"),
    "stage": ("SObject", "Form_Submission_Stage__c", False, True, False, "saves record stage progress in Stages mode"),
    "section": ("SObject", "Form_Template_Page_Section__c", False, True, False,
                "rows are tagged with the section and seeded from its Prefill Template"),
    "buttonTriggerName": ("String", None, False, True, False, "the page's own buttons drive the section (one bar)"),
    "hidePageButtons": ("Boolean", None, False, False, True, "the section takes the page's buttons over (one bar)"),
    "isValid": ("Boolean", None, False, False, True, "the page section picklist lists only flows with this output"),
    "buttonClickedLabel": ("String", None, False, False, True,
                           "the page routes Back, Save Progress and forward by this label"),
}
PICKLIST_OUTPUTS = ("isValid", "buttonClickedLabel", "record")
OPTIONAL = {"recordId"}
ONE_BAR = {"buttonTriggerName", "hidePageButtons"}  # flows cloned before the one-bar release lack them and still run

DESCRIBED = ("actionCalls", "assignments", "choices", "collectionProcessors", "constants", "decisions",
             "dynamicChoiceSets", "formulas", "loops", "recordCreates", "recordDeletes", "recordLookups",
             "recordUpdates", "screens", "subflows", "textTemplates", "transforms", "variables")
NODES = ("actionCalls", "assignments", "collectionProcessors", "decisions", "loops", "recordCreates", "recordDeletes",
         "recordLookups", "recordUpdates", "screens", "subflows", "transforms", "waits")
DML = ("recordCreates", "recordUpdates", "recordDeletes")
REF_TAGS = ("elementReference", "targetReference", "leftValueReference", "assignToReference", "screenActionName",
            "choiceReferences", "collectionReference", "inputReference", "assignRecordIdToReference", "eventSource")
MERGE = re.compile(r"\{!([^}]+)\}")


class SpecError(Exception):
    pass


# ---------------------------------------------------------------- helpers to build XML


def sub(parent, tag, text=None):
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def value(parent, kind, val):
    v = sub(parent, "value")
    sub(v, kind, ("true" if val else "false") if kind == "booleanValue" else val)
    return v


def param(parent, name, kind, val, tag="inputParameters"):
    p = sub(parent, tag)
    sub(p, "name", name)
    value(p, kind, val)
    return p


def node_head(el, name, label, description):
    if description:
        sub(el, "description", description)
    sub(el, "name", name)
    sub(el, "label", label)
    sub(el, "locationX", 0)
    sub(el, "locationY", 0)


def connect(el, target, tag="connector"):
    if target:
        c = sub(el, tag)
        sub(c, "targetReference", target)


def condition(rule, left, op, kind, right):
    c = sub(rule, "conditions")
    sub(c, "leftValueReference", left)
    sub(c, "operator", op)
    r = sub(c, "rightValue")
    sub(r, kind, ("true" if right else "false") if kind == "booleanValue" else right)


def words(api):
    return api.replace("_", " ")


def style_full_width(field):
    sp = sub(field, "styleProperties")
    va = sub(sp, "verticalAlignment")
    sub(va, "stringValue", "top")
    w = sub(sp, "width")
    sub(w, "stringValue", "12")


# ---------------------------------------------------------------- spec


def load_spec(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SpecError("no spec at %s" % path)
    except json.JSONDecodeError as e:
        raise SpecError("the spec is not valid JSON: %s" % e)
    return validate_spec(spec)


def validate_spec(spec):
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a JSON object")
    problems = []
    api = spec.get("api_name") or ""
    if not API_NAME.match(api) or len(api) > 80:
        problems.append("api_name %r: letters, digits and single underscores, starting with a letter, 80 at most" % api)
    for key in ("label", "description"):
        if not (spec.get(key) or "").strip():
            problems.append("%s is required" % key)
    if spec.get("buttons", "page") not in ("page", "flow"):
        problems.append("buttons must be 'page' (the page's buttons drive) or 'flow' (the section's buttons drive)")
    screens = spec.get("screens") or []
    if not screens:
        problems.append("screens needs at least one screen")
    names = set()
    forms = rows = 0
    for i, s in enumerate(screens):
        where = "screens[%d]" % i
        n = s.get("name") or ""
        if not API_NAME.match(n):
            problems.append("%s.name %r is not a valid API name" % (where, n))
        if n.endswith("_Screen"):
            problems.append("%s.name %r: no _Screen suffix (name the screen for what it asks)" % (where, n))
        if not (s.get("description") or "").strip():
            problems.append("%s.description is required" % where)
        names.add(n)
        forms += bool(s.get("form"))
        rows += bool(s.get("rows"))
        for j, p in enumerate(s.get("picks") or []):
            pw = "%s.picks[%d]" % (where, j)
            for key in ("name", "label", "object", "display_field", "description"):
                if not (p.get(key) or "").strip():
                    problems.append("%s.%s is required" % (pw, key))
            if p.get("name") and not API_NAME.match(p["name"]):
                problems.append("%s.name %r is not a valid API name" % (pw, p["name"]))
            if p.get("control", "RadioButtons") not in ("RadioButtons", "DropdownBox"):
                problems.append("%s.control must be RadioButtons or DropdownBox" % pw)
            if "required_message" in p and not (isinstance(p["required_message"], str) and p["required_message"].strip()):
                problems.append("%s.required_message must be text" % pw)
            names.add(p.get("name"))
    if forms > 1:
        problems.append("only one screen may carry the record's form: each form returns only its own visible fields")
    if rows > 1:
        problems.append("only one screen may carry rows: the section hands back one relatedRecords collection")
    for j, v in enumerate(spec.get("variables") or []):
        if not API_NAME.match(v.get("name") or "") or not (v.get("description") or "").strip():
            problems.append("variables[%d] needs a valid name and a description" % j)
        if v.get("name") in CONTRACT:
            problems.append("variables[%d] %r is a contract name; it is already declared" % (j, v.get("name")))
        names.add(v.get("name"))
    for j, s in enumerate(spec.get("sets") or []):
        if not s.get("field") or not s.get("value"):
            problems.append("sets[%d] needs field (a Form Submission field) and value (a resource in this flow)" % j)
        elif s["value"].split(".")[0] not in names:
            problems.append("sets[%d] value %r names no screen, pick or variable in the spec" % (j, s["value"]))
    if not forms and not spec.get("sets") and not rows:
        problems.append("the section returns nothing: give a screen a form, rows, or list the fields it sets")
    audiences = spec.get("audiences") or []
    if not set(audiences) <= {"guest", "portal", "internal"}:
        problems.append("audiences may hold guest, portal and internal only")
    if problems:
        raise SpecError("; ".join(problems))
    return spec


# ---------------------------------------------------------------- scaffold


def scaffold(spec, namespace=DEFAULT_NAMESPACE, api_version=DEFAULT_API_VERSION, active=True):
    ns = namespace + "__" if namespace else ""
    pfx = namespace + ":" if namespace else "c:"
    sub_obj = ns + "Form_Submission__c"
    screens = spec["screens"]
    first = screens[0]["name"]
    form_screen = next((s for s in screens if s.get("form")), None)
    rows_screen = next((s for s in screens if s.get("rows")), None)
    save = bool(spec.get("save_progress", True))
    flow_drives = spec.get("buttons", "page") == "flow"
    sets = spec.get("sets") or []
    # Back on the first screen is a Next under the hood, and the Flow runtime holds a Next on any empty native input
    # marked required, whatever the buttons component says. So the first screen's inputs are written not required,
    # and a check on the forward path (after Back has left) sends a blank answer back to the screen with a message.
    first_required = [p for p in screens[0].get("picks") or [] if p.get("required", True)]
    missing_var = "%s_Answer_Missing" % first

    root = ET.Element(Q + "Flow")
    root.tag = "Flow"
    root.set("xmlns", MD)
    sub(root, "apiVersion", api_version)
    sub(root, "areMetricsLoggedToDataCloud", "false")

    # assignments ------------------------------------------------------------------------------------------------
    out = sub(root, "assignments")
    node_head(out, "Assign_Outputs", "Assign Outputs",
              "Hands the section's changes back to the form on a fresh record holding only what the section set. "
              "Flow Tool Kit 5.3 and later keep only the values that differ from the record they passed in; on "
              "earlier versions a returned launch copy would put old values back over answers changed on other "
              "sections, so the fresh record keeps this flow safe on every version. Runs only on the forward finish: "
              "the form reads record on every new screen, so an earlier assignment could not be undone by Back."
              + (" The rows go back as the repeater hands them out: a saved row the person removed stays in the "
                 "collection with IsDeleted true, so the save and the conversion delete it." if rows_screen else ""))
    if form_screen:
        a = sub(out, "assignmentItems")
        sub(a, "assignToReference", "New_Values")
        sub(a, "operator", "Assign")
        v = sub(a, "value")
        sub(v, "elementReference", "%s_Form.recordVisibleFields" % form_screen["name"])
    for s in sets:
        a = sub(out, "assignmentItems")
        sub(a, "assignToReference", "New_Values.%s" % s["field"])
        sub(a, "operator", "Assign")
        v = sub(a, "value")
        sub(v, "elementReference", s["value"])
    a = sub(out, "assignmentItems")
    sub(a, "assignToReference", "record")
    sub(a, "operator", "Assign")
    v = sub(a, "value")
    sub(v, "elementReference", "New_Values")
    if rows_screen:
        a = sub(out, "assignmentItems")
        sub(a, "assignToReference", "relatedRecords")
        sub(a, "operator", "Assign")
        v = sub(a, "value")
        sub(v, "elementReference", "%s_Rows.prefillRecords" % rows_screen["name"])

    if rows_screen:
        tpl = sub(root, "assignments")
        node_head(tpl, "Assign_Row_Template", "Assign Row Template",
                  "Turns the section's Prefill Template into the starting values of every new row. Clearing the Id "
                  "makes each added row a new record instead of an edit of the template; the parent submission and "
                  "the section Id make saved rows come back to this section and convert under its rule.")
        for target, ref in (("getRowTemplate.%sParent_Form_Submission__c" % ns, "record.Id"),
                            ("getRowTemplate.Id", None),
                            ("getRowTemplate.%sInternal_SectionId__c" % ns, "section.Id")):
            a = sub(tpl, "assignmentItems")
            sub(a, "assignToReference", target)
            sub(a, "operator", "Assign")
            if ref:
                v = sub(a, "value")
                sub(v, "elementReference", ref)
        connect(tpl, first)

    for i, s in enumerate(screens):
        lab = sub(root, "assignments")
        node_head(lab, "Set_%s_Clicked_Label" % s["name"], "Set %s Clicked Label" % words(s["name"]),
                  "Keeps the label of the button pressed on %s. The form compares it with the labels it passed in: "
                  "Back goes back, Save Progress saves, anything else moves forward. Return it exactly as received."
                  % words(s["name"]))
        a = sub(lab, "assignmentItems")
        sub(a, "assignToReference", "buttonClickedLabel")
        sub(a, "operator", "Assign")
        v = sub(a, "value")
        sub(v, "elementReference", "%s_Buttons.buttonClickedLabel" % s["name"])
        connect(lab, "Switch_%s_Button" % s["name"] if needs_switch(i, len(screens), save)
                else ("Assign_Outputs" if i == len(screens) - 1 else screens[i + 1]["name"]))

    if first_required:
        miss = sub(root, "assignments")
        node_head(miss, "Set_%s" % missing_var, "Set %s" % words(missing_var),
                  "Turns on the message under each unanswered question and sends the person back to %s. The "
                  "questions there are not required in Flow, so that Back can always leave the section; this is "
                  "where the forward path asks for them instead." % words(first))
        a = sub(miss, "assignmentItems")
        sub(a, "assignToReference", missing_var)
        sub(a, "operator", "Assign")
        value(a, "booleanValue", True)
        connect(miss, first)

    # customProperties -------------------------------------------------------------------------------------------
    cp = sub(root, "customProperties")
    sub(cp, "name", "ScreenProgressIndicator")
    v = sub(cp, "value")
    sub(v, "stringValue", '{"location":"top","type":"simple"}')

    # decisions --------------------------------------------------------------------------------------------------
    for i, s in enumerate(screens):
        last = i == len(screens) - 1
        nxt = "Assign_Outputs" if last else screens[i + 1]["name"]
        if not needs_switch(i, len(screens), save):
            continue
        if i == 0 and first_required:
            nxt = "Switch_%s_Answers" % s["name"]
        d = sub(root, "decisions")
        node_head(d, "Switch_%s_Button" % s["name"], "Switch",
                  ("Routes by the button pressed on %s. %s%s"
                   % (words(s["name"]),
                     "Back on the first screen ends the section without handing back its edits, so the page goes back "
                     "with the record as it was. " if i == 0 else "",
                     "Save Progress hands the edits back and ends the section so the page saves them."
                     if save and not last else "")).strip())
        connect(d, nxt, "defaultConnector")
        sub(d, "defaultConnectorLabel", "Forward" if last else "Next screen")
        if i == 0:
            r = sub(d, "rules")
            sub(r, "name", "Back")
            sub(r, "conditionLogic", "and")
            condition(r, "buttonClickedLabel", "EqualTo", "elementReference", "buttonLabel_Back")
            sub(r, "label", "Back")
        if save and not last:
            r = sub(d, "rules")
            sub(r, "name", "Save_Progress_From_%s" % s["name"])
            sub(r, "conditionLogic", "and")
            condition(r, "buttonClickedLabel", "EqualTo", "elementReference", "buttonLabel_SaveProgress")
            c = sub(r, "connector")
            sub(c, "targetReference", "Assign_Outputs")
            sub(r, "label", "Save Progress")

    if first_required:
        d = sub(root, "decisions")
        node_head(d, "Switch_%s_Answers" % first, "Switch",
                  "Checks the answers on %s when the person moves forward. Those questions are not required in Flow, "
                  "because Back on the first screen is a Next under the hood and Flow would hold it on an empty "
                  "required input; Back has already left by the Switch before this one%s. A blank answer goes back to "
                  "the screen with a message." % (words(first), ", and Save Progress skips the check" if save else ""))
        connect(d, "Assign_Outputs" if len(screens) == 1 else screens[1]["name"], "defaultConnector")
        sub(d, "defaultConnectorLabel", "Answered")
        r = sub(d, "rules")
        sub(r, "name", "Answer_Missing")
        n = len(first_required)
        blanks = " OR ".join(str(k + 1) for k in range(n))
        sub(r, "conditionLogic", ("(%s) AND %d" % (blanks, n + 1) if n > 1 else "1 AND 2") if save else
            ("or" if n > 1 else "and"))
        for p in first_required:
            condition(r, p["name"], "IsNull", "booleanValue", True)
        if save:
            condition(r, "buttonClickedLabel", "NotEqualTo", "elementReference", "buttonLabel_SaveProgress")
        c = sub(r, "connector")
        sub(c, "targetReference", "Set_%s" % missing_var)
        sub(r, "label", "Answer missing")

    rv = sub(root, "decisions")
    node_head(rv, "Switch_Review", "Switch",
              "When the form runs its review pass it relaunches the section with Review on, and the section shows "
              "its read-only screen instead of the editable one.")
    connect(rv, "getRowTemplate" if rows_screen else first, "defaultConnector")
    sub(rv, "defaultConnectorLabel", "Edit")
    r = sub(rv, "rules")
    sub(r, "name", "Review_On")
    sub(r, "conditionLogic", "and")
    condition(r, "review", "EqualTo", "booleanValue", True)
    lookups = review_lookups(sets, ns)
    c = sub(r, "connector")
    sub(c, "targetReference", lookups[0]["name"] if lookups else "Section_Review")
    sub(r, "label", "Review")

    sub(root, "description", spec["description"])

    # dynamicChoiceSets ------------------------------------------------------------------------------------------
    for s in screens:
        for p in s.get("picks") or []:
            d = sub(root, "dynamicChoiceSets")
            sub(d, "description", p["description"])
            sub(d, "name", "%s_Choices" % p["name"])
            sub(d, "dataType", "String")
            sub(d, "displayField", p["display_field"])
            filters = p.get("filters") or []
            if filters:
                sub(d, "filterLogic", "and")
            for f in filters:
                fe = sub(d, "filters")
                sub(fe, "field", f["field"])
                sub(fe, "operator", f.get("operator", "EqualTo"))
                v = sub(fe, "value")
                if "reference" in f:
                    sub(v, "elementReference", f["reference"])
                else:
                    sub(v, "stringValue", f["value"])
            sub(d, "object", p["object"])
            if p.get("sort_field"):
                sub(d, "sortField", p["sort_field"])
                sub(d, "sortOrder", "Asc")
            sub(d, "valueField", p.get("value_field", "Id"))

    sub(root, "environments", "Default")

    # formulas ---------------------------------------------------------------------------------------------------
    page_drives = "NOT(ISBLANK({!buttonTriggerName})) && NOT({!hidePageButtons})"
    for name, desc, expr in (
            ("Hide_Docked_Buttons",
             "True while the page's own buttons drive this section: the form passed a trigger name and the section "
             "has not taken the buttons back. Hides the section's Next and Finish so the page shows one bar.",
             page_drives),
            ("Hide_Back_Button",
             "Hides Back on the form's first page, where the form passes no Back label, and while the page drives.",
             "ISBLANK({!buttonLabel_Back}) || (%s)" % page_drives),
            ("Hide_Save_Progress_Button",
             "Hides Save Progress when the Form Template does not allow it, and while the page drives, so the "
             "section never offers a button the template forbids.",
             "{!getFormTemplate.%sAllow_Save_Progress__c} != TRUE || (%s)" % (ns, page_drives))):
        f = sub(root, "formulas")
        sub(f, "description", desc)
        sub(f, "name", name)
        sub(f, "dataType", "Boolean")
        sub(f, "expression", expr)

    sub(root, "interviewLabel", "%s {!$Flow.CurrentDateTime}" % spec["label"])
    audiences = set(spec.get("audiences") or [])
    if audiences & {"guest", "portal"}:
        sub(root, "isAdditionalPermissionRequiredToRun", "true")
    sub(root, "label", spec["label"])
    for name, val in (("BuilderType", "LightningFlowBuilder"), ("CanvasMode", "AUTO_LAYOUT_CANVAS"),
                      ("OriginBuilderType", "LightningFlowBuilder")):
        pm = sub(root, "processMetadataValues")
        sub(pm, "name", name)
        v = sub(pm, "value")
        sub(v, "stringValue", val)
    sub(root, "processType", "Flow")

    # recordLookups ----------------------------------------------------------------------------------------------
    g = sub(root, "recordLookups")
    node_head(g, "getFormTemplate", "Form Template",
              "Reads Stages Mode and Allow Save Progress from the submission's Form Template, so the section's "
              "buttons follow the template's settings.")
    sub(g, "assignNullValuesIfNoRecordsFound", "false")
    connect(g, "Switch_Review")
    sub(g, "filterLogic", "and")
    fe = sub(g, "filters")
    sub(fe, "field", "Id")
    sub(fe, "operator", "EqualTo")
    v = sub(fe, "value")
    sub(v, "elementReference", "record.%sForm_Template__c" % ns)
    sub(g, "getFirstRecordOnly", "true")
    sub(g, "object", ns + "Form_Template__c")
    for f in ("Id", ns + "Stages_Mode__c", ns + "Allow_Save_Progress__c"):
        sub(g, "queriedFields", f)
    sub(g, "storeOutputAutomatically", "true")
    if rows_screen:
        g = sub(root, "recordLookups")
        node_head(g, "getRowTemplate", "Row Template",
                  "Loads the section's Prefill Template, a Form Submission whose values become the defaults of every "
                  "row the person adds.")
        sub(g, "assignNullValuesIfNoRecordsFound", "false")
        connect(g, "Assign_Row_Template")
        sub(g, "filterLogic", "and")
        fe = sub(g, "filters")
        sub(fe, "field", "Id")
        sub(fe, "operator", "EqualTo")
        v = sub(fe, "value")
        sub(v, "elementReference", "section.%sPrefill_Template__c" % ns)
        sub(g, "getFirstRecordOnly", "true")
        sub(g, "object", sub_obj)
        sub(g, "storeOutputAutomatically", "true")
    for i, lk in enumerate(lookups):
        g = sub(root, "recordLookups")
        node_head(g, lk["name"], lk["label"],
                  "Reads the %s the section picked, so the review shows its %s instead of a record Id."
                  % (words(lk["object"].replace("__c", "")), words(lk["name_field"].replace("__c", ""))))
        sub(g, "assignNullValuesIfNoRecordsFound", "false")
        connect(g, lookups[i + 1]["name"] if i + 1 < len(lookups) else "Section_Review")
        sub(g, "filterLogic", "and")
        fe = sub(g, "filters")
        sub(fe, "field", "Id")
        sub(fe, "operator", "EqualTo")
        v = sub(fe, "value")
        sub(v, "elementReference", "record.%s" % lk["field"])
        sub(g, "getFirstRecordOnly", "true")
        sub(g, "object", lk["object"])
        sub(g, "queriedFields", "Id")
        sub(g, "queriedFields", lk["name_field"])
        sub(g, "storeOutputAutomatically", "true")

    # screens ----------------------------------------------------------------------------------------------------
    review = sub(root, "screens")
    node_head(review, "Section_Review", "Section Review",
              "Read-only copy of the section for the form's review pass, so the section reviews like every other "
              "section on the page.")
    sub(review, "allowBack", "true")
    sub(review, "allowFinish", "true")
    sub(review, "allowPause", "true")
    if form_screen:
        form_field(review, "%s_Form_Review" % form_screen["name"], form_screen["form"], ns, pfx, sub_obj, review=True)
    if rows_screen:
        rows_field(review, "%s_Rows_Review" % rows_screen["name"], rows_screen["rows"], ns, pfx, sub_obj, review=True)
    if sets:
        by_field = {lk["field"]: lk for lk in lookups}
        lines = []
        for st in sets:
            shown = ("%s.%s" % (by_field[st["field"]]["name"], by_field[st["field"]]["name_field"])
                     if st["field"] in by_field else "record.%s" % st["field"])
            lines.append("<p><strong>%s</strong> {!%s}</p>" % (review_label(st, ns), shown))
        f = sub(review, "fields")
        sub(f, "name", "Review_Summary")
        sub(f, "fieldText", "".join(lines))
        sub(f, "fieldType", "DisplayText")
    sub(review, "showFooter", "false")
    sub(review, "showHeader", "false")

    for i, s in enumerate(screens):
        last = i == len(screens) - 1
        scr = sub(root, "screens")
        node_head(scr, s["name"], s.get("label") or words(s["name"]), s["description"])
        has_action = save and s is form_screen
        if has_action:
            act = sub(scr, "actions")
            sub(act, "name", "Save_Progress")
            sub(act, "actionName", ns + "Form_Submission_Upsert")
            sub(act, "actionType", "flow")
            p = sub(act, "inputParameters")
            sub(p, "name", "LastTriggeredDateTime")
            v = sub(p, "value")
            sub(v, "elementReference", "%s_Buttons.actionClickedDateTime" % s["name"])
            param(act, "SaveProgress", "booleanValue", True)
            p = sub(act, "inputParameters")
            sub(p, "name", "record")
            v = sub(p, "value")
            sub(v, "elementReference", "%s_Form.recordVisibleFields" % s["name"])
            if s is rows_screen:
                p = sub(act, "inputParameters")
                sub(p, "name", "relatedRecords")
                v = sub(p, "value")
                sub(v, "elementReference", "%s_Rows.prefillRecords" % s["name"])
            p = sub(act, "inputParameters")
            sub(p, "name", "stage")
            v = sub(p, "value")
            sub(v, "elementReference", "stage")
            sub(act, "label", "Save Progress")
            sub(act, "nameSegment", ns + "Form_Submission_Upsert")
        sub(scr, "allowBack", "true")
        sub(scr, "allowFinish", "true")
        sub(scr, "allowPause", "true")
        connect(scr, "Set_%s_Clicked_Label" % s["name"])
        if s is form_screen:
            form_field(scr, "%s_Form" % s["name"], s["form"], ns, pfx, sub_obj, review=False,
                       transformation="Save_Progress.Results.record" if has_action else None)
        if s is rows_screen:
            rows_field(scr, "%s_Rows" % s["name"], s["rows"], ns, pfx, sub_obj, review=False)
        for p in s.get("picks") or []:
            f = sub(scr, "fields")
            sub(f, "name", p["name"])
            sub(f, "choiceReferences", "%s_Choices" % p["name"])
            sub(f, "dataType", "String")
            sub(f, "fieldText", p["label"])
            sub(f, "fieldType", p.get("control", "RadioButtons"))
            if p.get("help"):
                sub(f, "helpText", p["help"])
            sub(f, "inputsOnNextNavToAssocScrn", "UseStoredValues")
            # first screen: never required in Flow (Back is a Next there); Switch_<Screen>_Answers asks instead
            sub(f, "isRequired", "true" if p.get("required", True) and i > 0 else "false")
            if i == 0 and p in first_required:
                m = sub(scr, "fields")
                sub(m, "name", "%s_Required_Message" % p["name"])
                sub(m, "fieldText", "<p><strong>%s</strong></p>"
                    % (p.get("required_message") or "Answer this question to continue."))
                sub(m, "fieldType", "DisplayText")
                vr = sub(m, "visibilityRule")
                sub(vr, "conditionLogic", "and")
                condition(vr, missing_var, "EqualTo", "booleanValue", True)
                condition(vr, p["name"], "IsNull", "booleanValue", True)
        buttons_field(scr, s["name"], first=i == 0, save=save, save_is_action=has_action, pfx=pfx)
        sub(scr, "showFooter", "false")
        sub(scr, "showHeader", "false")
        if has_action:
            sources = ["%s_Buttons.actionClickedDateTime" % s["name"], "%s_Form.recordVisibleFields" % s["name"]]
            if s is rows_screen:
                sources.append("%s_Rows.prefillRecords" % s["name"])
            save_trigger(scr, "flow__screeninit", s["name"], s["name"])
            for src in sources:
                save_trigger(scr, "flow__screenfieldattributechange", src, s["name"])

    st = sub(root, "start")
    sub(st, "locationX", 0)
    sub(st, "locationY", 0)
    connect(st, "getFormTemplate")
    sub(root, "status", "Active" if active else "Draft")

    # variables --------------------------------------------------------------------------------------------------
    var_desc = {
        "record": "Input and output: the Form Submission the form passes in. The section hands its changes back on "
                  "this variable at the end, set from New Values. Keep the name and type.",
        "recordId": "Input and output: the Form Submission's Id.",
        "relatedRecords": "Input and output: the submission's rows for this section's repeater or table. A saved "
                          "row the person removed comes back in it with IsDeleted true, so the save and the "
                          "conversion delete it; a saved row left out would stay. Keep the name and type.",
        "review": "Input: on when the form shows its review pass; the section shows its read-only screen.",
        "buttonLabel_Back": "Input: the page's Back label, so the section's Back button matches the form. Blank on "
                            "the first page.",
        "buttonLabel_Next": "Input: the page's forward label, so the section's Next button matches the form.",
        "buttonLabel_Finish": "Input: the label for the section's last-screen button; the form passes its forward "
                              "label here too.",
        "buttonLabel_SaveProgress": "Input: the page's Save Progress label, passed when the Form Template allows "
                                    "Save Progress.",
        "stage": "Input: the current Form Submission Stage in Stages mode, passed to the save so section saves record "
                 "stage progress like a page.",
        "section": "Input: the Form Template Page Section this flow runs in. Its Prefill Template seeds new rows and "
                   "its Id tags them, so one flow can serve several sections.",
        "buttonTriggerName": "Input: set by the form when its own page buttons can drive this section. The "
                             "section's buttons listen for it and run Next with the clicked label. Keep the name and "
                             "type.",
        "hidePageButtons": "Output: %s" % (
            "true, so the page hides its own buttons and this section's buttons drive the page."
            if flow_drives else
            "false, so the page's own buttons drive this section. Set it true to let the section's buttons drive."),
        "isValid": "Output: whether the section's own screens validated. Its presence also lists the flow in the page "
                   "section's Flow picklist.",
        "buttonClickedLabel": "Output: the label of the button pressed, returned exactly as received. The form "
                              "routes Back, Save Progress and forward by it.",
    }
    variables = []
    for name, (dtype, obj, coll, inp, outp, _) in CONTRACT.items():
        variables.append((name, dtype, ns + obj if obj else None, coll, inp, outp, var_desc[name],
                          {"hidePageButtons": ("booleanValue", flow_drives),
                           "isValid": ("booleanValue", True),
                           "review": ("booleanValue", False)}.get(name)))
    variables.append(("New_Values", "SObject", sub_obj, False, False, False,
                      "The values this section changed, on a fresh record. Assign Outputs copies it to record, so "
                      "only what the section set goes back to the form.", None))
    if first_required:
        variables.append((missing_var, "Boolean", None, False, False, False,
                          "On after the person moved forward from %s with a question unanswered; shows the message "
                          "under each blank question." % words(first), ("booleanValue", False)))
    for v in spec.get("variables") or []:
        variables.append((v["name"], v.get("type", "String"), v.get("object"), bool(v.get("collection")), False,
                          False, v["description"], None))
    for name, dtype, obj, coll, inp, outp, desc, default in sorted(variables, key=lambda x: x[0].lower()):
        ve = sub(root, "variables")
        sub(ve, "description", desc)
        sub(ve, "name", name)
        sub(ve, "dataType", dtype)
        sub(ve, "isCollection", "true" if coll else "false")
        sub(ve, "isInput", "true" if inp else "false")
        sub(ve, "isOutput", "true" if outp else "false")
        if obj:
            sub(ve, "objectType", obj)
        if default:
            value(ve, *default)
    return root


def needs_switch(index, count, save):
    """A screen needs a Switch when a button can end the section from it: Back on the first screen, Save Progress on
    any screen but the last (the last screen's forward path already hands the edits back)."""
    return index == 0 or (save and index < count - 1)


def bare_field(field, ns):
    name = field[len(ns):] if ns and field.startswith(ns) else field
    return name[:-3] if name.endswith("__c") else name


def review_label(st, ns):
    return st.get("review_label") or words(bare_field(st["field"], ns))


def review_lookups(sets, ns):
    """One Get Records per set lookup field that names review_object, so the review shows a name, not an Id."""
    out = []
    for st in sets:
        if st.get("review_object"):
            out.append({"name": "get" + bare_field(st["field"], ns).replace("_", ""), "label": words(bare_field(st["field"], ns)),
                        "object": st["review_object"], "name_field": st.get("review_field", "Name"),
                        "field": st["field"]})
    return out


def form_field(screen, name, form, ns, pfx, sub_obj, review, transformation=None):
    f = sub(screen, "fields")
    sub(f, "name", name)
    dm = sub(f, "dataTypeMappings")
    sub(dm, "typeName", "T")
    sub(dm, "typeValue", sub_obj)
    sub(f, "extensionName", pfx + "flowForm")
    sub(f, "fieldType", "ComponentInstance")
    for pname, ref in (("interviewGuid", "$Flow.InterviewGuid"), ("interviewStartDateTime", "$Flow.InterviewStartTime"),
                       ("serverURL", "$Api.Enterprise_Server_URL_140")):
        p = sub(f, "inputParameters")
        sub(p, "name", pname)
        v = sub(p, "value")
        sub(v, "elementReference", ref)
    param(f, "elementApiName", "stringValue", name)
    param(f, "selectedMergeRecordField", "stringValue", ns + "UniqueId__c")
    param(f, "object", "stringValue", sub_obj)
    p = sub(f, "inputParameters")
    sub(p, "name", "record")
    v = sub(p, "value")
    sub(v, "elementReference", "record")
    param(f, "formQualifiedApiName", "stringValue", form)
    if review:
        p = sub(f, "inputParameters")
        sub(p, "name", "review")
        v = sub(p, "value")
        sub(v, "elementReference", "review")
    if transformation:
        p = sub(f, "inputParameters")
        sub(p, "name", "transformationRecord")
        v = sub(p, "value")
        sub(v, "elementReference", transformation)
    sub(f, "inputsOnNextNavToAssocScrn", "UseStoredValues")
    sub(f, "isRequired", "true")
    sub(f, "storeOutputAutomatically", "true")
    style_full_width(f)


def rows_field(screen, name, form, ns, pfx, sub_obj, review):
    f = sub(screen, "fields")
    sub(f, "name", name)
    dm = sub(f, "dataTypeMappings")
    sub(dm, "typeName", "T")
    sub(dm, "typeValue", sub_obj)
    sub(f, "extensionName", pfx + "flowFormRepeat")
    sub(f, "fieldType", "ComponentInstance")
    for pname, ref in (("interviewGuid", "$Flow.InterviewGuid"), ("interviewStartDateTime", "$Flow.InterviewStartTime"),
                       ("serverURL", "$Api.Enterprise_Server_URL_140"), ("selectedRecords", name + ".selectedRecords")):
        p = sub(f, "inputParameters")
        sub(p, "name", pname)
        v = sub(p, "value")
        sub(v, "elementReference", ref)
    param(f, "object", "stringValue", sub_obj)
    p = sub(f, "inputParameters")
    sub(p, "name", "prefillRecords")
    v = sub(p, "value")
    sub(v, "elementReference", "relatedRecords")
    param(f, "formQualifiedApiName", "stringValue", form)
    if review:
        p = sub(f, "inputParameters")
        sub(p, "name", "review")
        v = sub(p, "value")
        sub(v, "elementReference", "review")
    else:
        for pname in ("allowNew", "allowDelete", "allowClone", "dynamicHeaders"):
            param(f, pname, "booleanValue", True)
        p = sub(f, "inputParameters")
        sub(p, "name", "recordTemplate")
        v = sub(p, "value")
        sub(v, "elementReference", "getRowTemplate")
    sub(f, "inputsOnNextNavToAssocScrn", "UseStoredValues")
    sub(f, "isRequired", "true")
    sub(f, "storeOutputAutomatically", "true")
    style_full_width(f)


def buttons_field(screen, sname, first, save, save_is_action, pfx):
    f = sub(screen, "fields")
    name = "%s_Buttons" % sname
    sub(f, "name", name)
    sub(f, "extensionName", pfx + "buttonsCustom")
    sub(f, "fieldType", "ComponentInstance")

    def ref(pname, target):
        p = sub(f, "inputParameters")
        sub(p, "name", pname)
        v = sub(p, "value")
        sub(v, "elementReference", target)

    ref("triggerListenerName", "buttonTriggerName")
    ref("hideButton4", "Hide_Docked_Buttons")
    ref("hideButton5", "Hide_Docked_Buttons")
    param(f, "manual", "booleanValue", True)
    ref("interviewGuid", "$Flow.InterviewGuid")
    ref("interviewStartDateTime", "$Flow.InterviewStartTime")
    param(f, "elementApiName", "stringValue", name)
    param(f, "buttonAlignment", "stringValue", "center")
    param(f, "docked", "booleanValue", True)
    param(f, "iconPosition", "stringValue", "Left")
    # Back: on the first screen a forward click carrying the Back label (the Switch ends the section with it);
    # on later screens a real Flow Back to the previous screen.
    param(f, "button2Enabled", "booleanValue", True)
    ref("label2", "buttonLabel_Back")
    param(f, "variant2", "stringValue", "brand-outline")
    param(f, "iconName2", "stringValue", "utility:back")
    param(f, "iconPosition2", "stringValue", "Left")
    param(f, "bypassValidation2", "booleanValue", True)
    if not first:
        param(f, "type2", "stringValue", "BACK")
    ref("hideButton2", "Hide_Back_Button" if first else "Hide_Docked_Buttons")
    shown = 2
    if save:
        param(f, "button3Enabled", "booleanValue", True)
        ref("label3", "buttonLabel_SaveProgress")
        param(f, "variant3", "stringValue", "brand-outline")
        param(f, "iconName3", "stringValue", "utility:save")
        param(f, "iconPosition3", "stringValue", "Right")
        param(f, "bypassValidation3", "booleanValue", True)
        if save_is_action:
            param(f, "type3", "stringValue", "ACTION")
        ref("hideButton3", "Hide_Save_Progress_Button")
        shown = 3
    param(f, "button4Enabled", "booleanValue", True)
    ref("label4", "buttonLabel_Next")
    param(f, "variant4", "stringValue", "brand")
    param(f, "button5Enabled", "booleanValue", True)
    ref("label5", "buttonLabel_Finish")
    param(f, "variant5", "stringValue", "brand")
    param(f, "type5", "stringValue", "FINISH")
    param(f, "iconPosition5", "stringValue", "Left")
    param(f, "numberOfButtonsToShow", "numberValue", "%d.0" % shown)
    sub(f, "inputsOnNextNavToAssocScrn", "UseStoredValues")
    sub(f, "isRequired", "true")
    sub(f, "storeOutputAutomatically", "true")
    style_full_width(f)


def save_trigger(screen, event, source, sname):
    t = sub(screen, "triggers")
    sub(t, "eventName", event)
    sub(t, "eventSource", source)
    h = sub(t, "handlers")
    sub(h, "conditionLogic", "1 AND 2 AND (3 OR 4)")
    clicked = "%s_Buttons.actionClickedDateTime" % sname
    condition(h, "Save_Progress.InProgress", "NotEqualTo", "booleanValue", True)
    condition(h, clicked, "IsNull", "booleanValue", False)
    condition(h, "Save_Progress.Results.LastTriggeredDateTime", "IsNull", "booleanValue", True)
    condition(h, clicked, "GreaterThan", "elementReference", "Save_Progress.Results.LastTriggeredDateTime")
    sub(h, "screenActionName", "Save_Progress")


def to_xml(root):
    ET.indent(root, space="    ")
    body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"


# ---------------------------------------------------------------- check


class Finding:
    def __init__(self, level, code, text):
        self.level, self.code, self.text = level, code, text

    def __str__(self):
        return "%s [%s] %s" % (self.level.upper(), self.code, self.text)


def text_of(el, tag):
    child = el.find(Q + tag)
    return child.text if child is not None and child.text is not None else None


def local(el):
    return el.tag.split("}", 1)[-1]


def first_screen_from(root, name):
    """Follow single connectors from one element until a screen; the review path may read records first."""
    nodes = {text_of(el, "name"): el for el in root if local(el) in NODES}
    seen = set()
    while name in nodes and name not in seen:
        seen.add(name)
        el = nodes[name]
        if local(el) == "screens":
            return name
        nxt = el.find(Q + "connector/" + Q + "targetReference")
        if nxt is None:
            nxt = el.find(Q + "defaultConnector/" + Q + "targetReference")
        if nxt is None:
            return None
        name = nxt.text
    return None


SANITIZER = "DataSanitizer_Invocable"  # the FLS Record(s) Sanitizer action
# Screen field types that are not native inputs: a Flow Tool Kit component checks its own requiredness (and skips it
# for Back), display text and sections hold no answer. Everything else is a native input the Flow runtime enforces.
NOT_NATIVE_INPUT = {"ComponentInstance", "DisplayText", "RegionContainer", "Region"}


def button_slots(field):
    """The enabled buttons of one Flow Tool Kit buttons component, in manual mode: slot number, type, label binding
    (('ref', variable), ('typed', text) or ('default', None)) and whether it skips validation."""
    params = {text_of(p, "name"): p.find(Q + "value") for p in field.findall(Q + "inputParameters")}

    def val(name):
        v = params.get(name)
        if v is None or len(v) == 0:
            return None, None
        return local(v[0]), v[0].text

    if val("manual")[1] != "true":
        return []
    slots = []
    for i in range(1, 6):
        sfx = "" if i == 1 else str(i)
        if val("button%dEnabled" % i)[1] != "true":
            continue
        kind, text = val("buttonLabel") if i == 1 else val("label%d" % i)
        if i == 1 and kind is None:
            kind, text = val("label")
        label = (("ref", text) if kind == "elementReference" else
                 ("typed", text) if kind == "stringValue" and text else ("default", None))
        btype = (val("type" + sfx)[1] or "NEXT").upper()
        slots.append({"slot": i, "type": btype, "label": label, "bypass": val("bypassValidation" + sfx)[1] == "true"})
    return slots


def compares_label(root, label_var):
    """True when a decision condition compares a clicked label with the given buttonLabel_ variable."""
    for c in root.iter(Q + "conditions"):
        left = text_of(c, "leftValueReference") or ""
        rv = c.find(Q + "rightValue")
        right = text_of(rv, "elementReference") if rv is not None else None
        if left.split(".")[-1] == "buttonClickedLabel" and right == label_var:
            return True
    return False


def check(xml_text, audiences=(), namespace=DEFAULT_NAMESPACE, file_name=None):
    """Return a list of Findings for one flow file's text."""
    findings = []

    def err(code, msg):
        findings.append(Finding("error", code, msg))

    def warn(code, msg):
        findings.append(Finding("warning", code, msg))

    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise SpecError("the flow file declares a DOCTYPE or entities; a flow file never does, so it is not read")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise SpecError("the flow file is not valid XML: %s" % e)
    if local(root) != "Flow":
        raise SpecError("not a flow file (root element %s)" % local(root))
    ns = namespace + "__" if namespace else ""

    if text_of(root, "processType") != "Flow":
        err("not-screen-flow", "processType must be Flow (a screen flow); the form only runs screen flows in a section")
    if text_of(root, "isTemplate") == "true":
        err("is-template", "isTemplate is true: a template is never active and never listed. Remove it from the clone")
    if text_of(root, "status") != "Active":
        warn("not-active", "status is %s: the form reads the active version's variables, and the page section "
             "picklist lists only active flows. Activate it after the deploy" % text_of(root, "status"))
    if not (text_of(root, "description") or "").strip():
        err("no-flow-description", "the flow needs a description: what it does, where it runs, what it hands back")
    label = text_of(root, "label") or ""
    if not label.startswith("Form Section | "):
        warn("label-pattern", "label %r: name Flow Sections 'Form Section | <What it does>' so they sort together" % label)
    if file_name:
        api = file_name.split(".flow-meta.xml")[0].split(".flow")[0]
        if not api.startswith("Form_Section_"):
            warn("api-pattern", "API name %r: use Form_Section_<What_It_Does>" % api)

    # contract variables
    variables = {text_of(v, "name"): v for v in root.findall(Q + "variables")}
    for name, (dtype, obj, coll, inp, outp, why) in CONTRACT.items():
        v = variables.get(name)
        level = warn if name in OPTIONAL or name in ONE_BAR else err
        if v is None and name in ONE_BAR:
            warn("two-bars", "variable %s is missing: the page shows its buttons and the section shows its own. Add "
                 "buttonTriggerName (text input) and hidePageButtons (Boolean output) to get one bar" % name)
            continue
        if v is None:
            level("contract-missing", "variable %s is missing: %s" % (name, why))
            continue
        problems = []
        if text_of(v, "dataType") != dtype:
            problems.append("type %s, needs %s" % (text_of(v, "dataType"), dtype))
        if (text_of(v, "isCollection") == "true") != coll:
            problems.append("collection must be %s" % str(coll).lower())
        if inp and text_of(v, "isInput") != "true":
            problems.append("must be available for input")
        if outp and text_of(v, "isOutput") != "true":
            problems.append("must be available for output")
        if obj and text_of(v, "objectType") != ns + obj:
            problems.append("object %s, needs %s" % (text_of(v, "objectType"), ns + obj))
        if problems:
            level("contract-shape", "variable %s: %s (%s)" % (name, "; ".join(problems), why))

    xml_flat = xml_text
    if re.search(r"<assignToReference>\s*record\.", xml_flat):
        warn("stale-record", "an assignment writes onto record.<Field>. Flow Tool Kit 5.3 and later keep only the "
             "fields that differ from the record they passed in, so this is safe there; on earlier versions the whole "
             "launch copy goes back and puts old values over answers changed elsewhere. A fresh record (New_Values) "
             "assigned to record last is safe on every version")

    decisions = root.findall(Q + "decisions")
    if not any(text_of(c, "leftValueReference") == "review" for d in decisions for c in d.iter(Q + "conditions")):
        err("no-review", "no decision reads review: in the form's review pass the section would stay editable. "
            "Route review = true to a read-only screen")
    for d in decisions:
        if text_of(d, "label") != "Switch":
            err("decision-label", "decision %s is labelled %r: every decision is labelled Switch; the meaning goes "
                "in its outcome labels" % (text_of(d, "name"), text_of(d, "label")))

    # screens and their components
    screens = root.findall(Q + "screens")
    review_screens = set()
    for d in decisions:
        for rule in d.findall(Q + "rules"):
            if any(text_of(c, "leftValueReference") == "review" for c in rule.findall(Q + "conditions")):
                tgt = rule.find(Q + "connector/" + Q + "targetReference")
                if tgt is not None:
                    review_screens.add(first_screen_from(root, tgt.text))
    for scr in screens:
        sname = text_of(scr, "name")
        if sname and sname.endswith("_Screen"):
            warn("screen-name", "screen %s: no _Screen suffix; name it for what it asks" % sname)
        if text_of(scr, "showHeader") != "false" or text_of(scr, "showFooter") != "false":
            warn("two-bars", "screen %s: turn the header and footer off; the docked buttons match the form, and "
                 "Flow's own footer would add a second bar" % sname)
        buttons = [f for f in scr.iter(Q + "fields") if (text_of(f, "extensionName") or "").endswith("buttonsCustom")]
        if not buttons and sname not in review_screens:
            err("no-buttons", "screen %s has no Flow Tool Kit buttons component: the section could not move on or "
                "report which button was pressed" % sname)
        for b in buttons:
            params = {text_of(p, "name"): p for p in b.findall(Q + "inputParameters")}
            listener = params.get("triggerListenerName")
            listener_value = listener.find(Q + "value") if listener is not None else None
            if listener_value is None or text_of(listener_value, "elementReference") != "buttonTriggerName":
                err("no-listener", "screen %s: the buttons' Trigger Listener Name must be {!buttonTriggerName}, or "
                    "the page's buttons cannot drive the section" % sname)
            for s in button_slots(b):
                bound = s["label"][1] if s["label"][0] == "ref" else None
                if s["type"] in ("NEXT", "FINISH") and s["bypass"] and not bound:
                    err("hard-coded-label", "screen %s: button %d skips validation and ends or moves the section like "
                        "Back or Save Progress, but its label is %s. Bind it to buttonLabel_Back or "
                        "buttonLabel_SaveProgress: the form routes the finish by label, and an unknown label always "
                        "moves forward" % (sname, s["slot"], "typed" if s["label"][0] == "typed" else "left at the "
                                           "component's default"))
                elif s["type"] == "FINISH" and bound not in ("buttonLabel_Finish", "buttonLabel_Next"):
                    warn("finish-label", "screen %s: the Finish button (button %d) is not bound to buttonLabel_Finish, "
                         "so the section's last screen does not show the page's forward label. It still moves "
                         "forward" % (sname, s["slot"]))
        for f in scr.iter(Q + "fields"):
            for p in f.findall(Q + "inputParameters"):
                if text_of(p, "name") == "formQualifiedApiName":
                    fv = p.find(Q + "value")
                    form = (text_of(fv, "stringValue") if fv is not None else None) or ""
                    if form.split("__", 1)[-1] in DEMO_FORMS:
                        err("demo-form", "screen %s still shows the template's sample form %s; put your own form "
                            "component there or remove it" % (sname, form))

    # the button handoff: what the form needs from the section's buttons (references/contract.md)
    editable = [s for s in screens if text_of(s, "name") not in review_screens]
    start = root.find(Q + "start")
    first_name = None
    if start is not None:
        tgt = start.find(Q + "connector/" + Q + "targetReference")
        first_name = first_screen_from(root, tgt.text if tgt is not None else text_of(root, "startElementReference"))
    all_slots = {}
    for scr in editable:
        sname = text_of(scr, "name")
        bars = [f for f in scr.iter(Q + "fields") if (text_of(f, "extensionName") or "").endswith("buttonsCustom")]
        listening = [f for f in bars if any(text_of(p, "name") == "triggerListenerName" and
                                            text_of(p.find(Q + "value"), "elementReference") == "buttonTriggerName"
                                            for p in f.findall(Q + "inputParameters") if p.find(Q + "value") is not None)]
        if len(listening) > 1:
            warn("two-listeners", "screen %s has %d buttons components listening to buttonTriggerName: each one moves "
                 "the flow on the page's click. Keep one" % (sname, len(listening)))
        all_slots[sname] = [s for f in bars for s in button_slots(f)]
    flat = [s for slots in all_slots.values() for s in slots]

    clicked = [a for a in root.iter(Q + "assignmentItems") if text_of(a, "assignToReference") == "buttonClickedLabel"]
    clicked_var = variables.get("buttonClickedLabel")
    if editable and not clicked and (clicked_var is None or clicked_var.find(Q + "value") is None):
        err("no-clicked-label", "nothing assigns buttonClickedLabel: the form acts only on a finish that carries it, "
            "so the page would neither move nor save and the section would sit on a spinner. Assign the buttons "
            "component's buttonClickedLabel to it on every path that finishes")

    if first_name in all_slots:
        for s in all_slots[first_name]:
            if s["label"] == ("ref", "buttonLabel_Back") and s["type"] == "BACK":
                err("first-screen-back", "screen %s is the first screen and its Back (button %d) has type BACK: Flow has "
                    "no earlier screen, so the button is hidden and the person cannot reach the form's previous page "
                    "when the section drives. Leave its type Next: it ends the section with the Back label"
                    % (first_name, s["slot"]))
    for scr in editable:
        if text_of(scr, "name") != first_name:
            continue
        for f in scr.iter(Q + "fields"):
            if text_of(f, "fieldType") not in NOT_NATIVE_INPUT and text_of(f, "isRequired") == "true":
                warn("first-screen-required", "screen %s is the first screen and its input %s is required in Flow: "
                     "Back there is a Next under the hood, and the Flow runtime holds a Next on an empty required "
                     "input whatever the buttons' skip validation says, so the person cannot go back to the form's "
                     "previous page. Mark it not required and check the answer on the forward path, after the Back "
                     "outcome, sending a blank answer back to the screen with a message (the scaffold's "
                     "Switch_<Screen>_Answers)" % (first_name, text_of(f, "name")))
    if any(s["label"] == ("ref", "buttonLabel_Back") for s in flat) and not compares_label(root, "buttonLabel_Back"):
        warn("back-keeps-edits", "no decision compares the clicked label with buttonLabel_Back: Back from the first "
             "screen would hand the section's unsaved edits back to the form. Add a Switch after the first screen "
             "whose Back outcome skips the outputs")
    if len(editable) > 1 and any(s["label"] == ("ref", "buttonLabel_SaveProgress") for s in flat) \
            and not compares_label(root, "buttonLabel_SaveProgress"):
        warn("save-progress-route", "the section has several screens and no decision compares the clicked label with "
             "buttonLabel_SaveProgress: on a screen before the last, Save Progress (and the page's Save Progress) "
             "moves to the next screen and saves nothing. Add a Save Progress outcome that assigns the outputs and ends")
    if editable and flat and not any(s["type"] == "FINISH" for s in flat):
        hide = variables.get("hidePageButtons")
        hide_value = hide.find(Q + "value") if hide is not None else None
        hide_default = hide_value is not None and text_of(hide_value, "booleanValue") == "true"
        section_drives = hide_default or "buttonTriggerName" not in variables or any(
            text_of(a, "assignToReference") == "hidePageButtons" for a in root.iter(Q + "assignmentItems"))
        (err if section_drives else warn)(
            "no-finish-button", "no screen has a Finish button: Flow offers only Finish on the last screen, so when the "
            "section drives its last screen shows no forward button. Add one bound to buttonLabel_Finish")

    # rows handed back: a saved row the flow removes must come back with IsDeleted true, or it is never deleted
    repeaters = {text_of(f, "name") for scr in screens for f in scr.iter(Q + "fields")
                 if (text_of(f, "extensionName") or "").endswith("flowFormRepeat")}
    flags_deleted = False
    for a in root.iter(Q + "assignmentItems"):
        v = a.find(Q + "value")
        if (text_of(a, "assignToReference") or "").endswith(".IsDeleted") and v is not None \
                and text_of(v, "booleanValue") == "true":
            flags_deleted = True
    drops = []
    for a in root.iter(Q + "assignmentItems"):
        if text_of(a, "assignToReference") != "relatedRecords":
            continue
        op = text_of(a, "operator") or ""
        v = a.find(Q + "value")
        ref = text_of(v, "elementReference") if v is not None else None
        if op.startswith("Remove"):
            drops.append("%s on relatedRecords" % op)
        elif op == "Assign" and not (ref == "relatedRecords" or (
                ref and ref.split(".")[0] in repeaters and ref.endswith(".prefillRecords"))):
            drops.append("relatedRecords set from %s" % (ref or "a blank value"))
    if drops and not flags_deleted:
        warn("dropped-rows", "%s can leave saved rows out of what the section hands back, and nothing sets IsDeleted "
             "true: a saved row missing from relatedRecords is not deleted, it stays a child of the submission. Keep "
             "each removed saved row in the collection with IsDeleted true (drop only rows with no Id), as the "
             "repeater's prefillRecords output does, so the save and the conversion delete it" % "; ".join(drops))

    # a System Mode read handed to a screen goes through the FLS Record(s) Sanitizer first
    if (text_of(root, "runInMode") or "").startswith("SystemMode"):
        reads = {}
        for el in root.findall(Q + "recordLookups"):
            n = text_of(el, "name")
            reads[n] = n
            out = text_of(el, "outputReference")
            if out:
                reads[out] = n
        sanitized = set()
        for act in root.findall(Q + "actionCalls"):
            if (text_of(act, "actionName") or "").split("__")[-1] != SANITIZER:
                continue
            for p in act.findall(Q + "inputParameters"):
                v = p.find(Q + "value")
                ref = text_of(v, "elementReference") if v is not None else None
                if ref and ref.split(".")[0] in reads:
                    sanitized.add(reads[ref.split(".")[0]])
        shown = set()
        for scr in screens:
            for f in scr.iter(Q + "fields"):
                for p in f.findall(Q + "inputParameters"):
                    v = p.find(Q + "value")
                    ref = text_of(v, "elementReference") if v is not None else None
                    if ref and ref.split(".")[0] in reads:
                        shown.add(reads[ref.split(".")[0]])
                for tag in ("fieldText", "helpText"):
                    for r in MERGE.findall(text_of(f, tag) or ""):
                        if r.split(".")[0].strip() in reads:
                            shown.add(reads[r.split(".")[0].strip()])
        for n in sorted(shown - sanitized):
            warn("unsanitized-system-read", "Get Records %s runs in System Mode and reaches a screen without the FLS "
                 "Record(s) Sanitizer: a guest or portal user would receive every queried field, whatever their field "
                 "access. Pass it through %s first and show the sanitized record" % (n, ns + SANITIZER))

    # descriptions on everything
    for kind in DESCRIBED:
        for el in root.findall(Q + kind):
            if not (text_of(el, "description") or "").strip():
                err("no-description", "%s %s has no description" % (kind[:-1] if kind.endswith("s") else kind,
                                                                     text_of(el, "name")))
    for el in root.iter(Q + "description"):
        t = el.text or ""
        if EM_DASH in t:
            err("em-dash", "a description has an em-dash; use a colon, a comma or a new sentence: %r" % t[:60])
        if ISSUE_REF.search(t):
            err("issue-number", "a description cites an issue number; describe what it does now: %r" % t[:60])

    for el in root.findall(Q + "recordLookups"):
        if not (text_of(el, "name") or "").startswith("get"):
            warn("get-name", "Get Records %s: name it get<WhatItReturns>" % text_of(el, "name"))
    for kind in DML:
        for el in root.findall(Q + kind):
            warn("writes-records", "%s %s: a Flow Section hands values back and the form saves them; writing records "
                 "here runs as the person filling the form (a guest, for a public form). Keep it only with a reason "
                 "in its description" % (kind, text_of(el, "name")))
            if el.find(Q + "faultConnector") is None:
                err("no-fault", "%s %s has no fault path" % (kind, text_of(el, "name")))
    for el in root.findall(Q + "actionCalls") + root.findall(Q + "subflows"):
        if local(el) == "actionCalls" and el.find(Q + "faultConnector") is None:
            warn("no-fault", "action %s has no fault path" % text_of(el, "name"))

    # names are unique ignoring case (Flow treats Review and review as the same name)
    seen = {}
    named = [el for el in root if text_of(el, "name") and local(el) not in ("processMetadataValues", "customProperties")]
    named += [f for scr in screens for f in scr.iter(Q + "fields")] + [a for scr in screens for a in scr.findall(Q + "actions")]
    for el in named:
        n = text_of(el, "name")
        if n.lower() in seen and seen[n.lower()] != n:
            err("duplicate-name", "%r and %r differ only in case; Flow rejects the deploy with Duplicate developer name"
                % (seen[n.lower()], n))
        elif n.lower() in seen:
            err("duplicate-name", "%r is used twice" % n)
        seen[n.lower()] = n

    # every reference resolves
    defined = set()
    for el in root:
        n = text_of(el, "name")
        if n:
            defined.add(n)
    for scr in screens:
        for f in scr.iter(Q + "fields"):
            defined.add(text_of(f, "name"))
        for a in scr.findall(Q + "actions"):
            defined.add(text_of(a, "name"))
    for el in root.iter():
        tag = local(el)
        refs = []
        if tag in REF_TAGS and el.text:
            refs.append(el.text.strip())
        if tag in ("expression", "fieldText", "text", "stringValue", "helpText") and el.text:
            refs += MERGE.findall(el.text)
        for r in refs:
            rootname = r.split(".")[0].strip()
            if not rootname or rootname.startswith("$") or rootname in defined:
                continue
            err("unresolved", "%s refers to %r, which is not in this flow (renamed or removed?)" % (tag, r))

    audiences = set(a.strip() for a in audiences if a.strip())
    if audiences & {"guest", "portal"} and text_of(root, "isAdditionalPermissionRequiredToRun") != "true":
        err("not-restricted", "a guest or portal user runs this flow, so it must require permission to run "
            "(isAdditionalPermissionRequiredToRun true) and be granted in that user's permission set: run "
            "flow-access-fix")
    return findings


# ---------------------------------------------------------------- command line


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scaffold", help="write a new Flow Section flow from a spec")
    s.add_argument("spec")
    s.add_argument("--out", default=".", help="the project folder (holds force-app/)")
    s.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="the package prefix; FlowToolKit in every org "
                   "that installed the package")
    s.add_argument("--api-version", default=DEFAULT_API_VERSION)
    s.add_argument("--draft", action="store_true", help="write status Draft instead of Active")
    s.add_argument("--force", action="store_true", help="overwrite an existing file")
    c = sp.add_parser("check", help="check a Flow Section flow file")
    c.add_argument("flow")
    c.add_argument("--audiences", default="", help="comma list of guest, portal, internal")
    c.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "scaffold":
            spec = load_spec(args.spec)
            root = scaffold(spec, args.namespace, args.api_version, active=not args.draft)
            out = Path(args.out) / "force-app" / "main" / "default" / "flows" / (spec["api_name"] + ".flow-meta.xml")
            if out.exists() and not args.force:
                raise SpecError("%s exists; pass --force to overwrite it (retrieve the org's copy first)" % out)
            out.parent.mkdir(parents=True, exist_ok=True)
            text = to_xml(root)
            out.write_text(text, encoding="utf-8")
            findings = check(text, spec.get("audiences") or [], args.namespace, out.name)
            for f in findings:
                print(f)
            print(str(out))
            return 1 if any(f.level == "error" for f in findings) else 0
        path = Path(args.flow)
        if not path.is_file():
            raise SpecError("no flow file at %s" % path)
        findings = check(path.read_text(encoding="utf-8"), args.audiences.split(","), args.namespace, path.name)
        for f in findings:
            print(f)
        errors = sum(f.level == "error" for f in findings)
        print("flowsection check: %d errors, %d warnings" % (errors, len(findings) - errors))
        return 1 if errors else 0
    except SpecError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
