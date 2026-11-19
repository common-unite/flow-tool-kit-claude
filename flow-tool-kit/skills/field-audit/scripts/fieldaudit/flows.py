"""The Flow Tool Kit flows, and the fields each one uses.

Only Flow Tool Kit flows are listed: the conversion and prefill flows a Form
Template or page section names, the screen flow a Flow Section shows, the flows
that use a Flow Tool Kit action or screen component (the FlowToolKit namespace
on the action, component or called flow), and every subflow those flows call. Any other flow is never listed:
Setup's Where is this used? covers it.

Which flows a template names, from the package's own fields:

* ``Form_Template__c.Conversion_Map_Flow_<target>__c`` (a picklist: Default or a
  flow's API name) and the read-only formula ``FlowApiName_<target>__c`` that
  resolves it; Default resolves through the Form Template Conversion Mapping
  Default record for that target (``Flow_API_Name__c``).
* ``Form_Template_Page_Section__c.Conversion_Map_Flow__c`` and its formula
  ``FlowApiName_Related__c`` (Default resolves through the section's
  ``Conversion_Rule__c`` and the same custom metadata).
* ``Form_Template__c.Prefill_Flow_Api_Name__c`` (Bypass means none).
* ``Form_Template_Page_Section__c.FlowApiName__c`` on a section whose
  ``Component_Type__c`` is Flow: the screen flow that Flow Section shows. A
  value left on a section of another type is not shown, so it names no flow.

Each Flow Tool Kit flow is read as JSON (Tooling API ``Flow.Metadata``, one query
per flow version), the active version or else the latest. The walk is
structural, never a text search over the source, except inside formula and
text template bodies, where ``{!Var.Field__c}`` tokens are the structure.

Dotted references (``FormSubmission.Contact1_Email__c``) resolve through the
flow's variable table, plus ``$Record`` to the start element's object. A
form name passed by reference (a dynamic form selector) is chased through
constants and variable defaults; when it stays dynamic it is reported as a
"not captured" row, never silently dropped.
"""

from __future__ import annotations

import json
import re

from . import NAMESPACE, SUBMISSION_OBJECT
from . import walk
from .names import fold_star, is_path, local
from .orgreads import ocutil

val, records = ocutil.val, ocutil.records
N = NAMESPACE
FTK_PREFIX = NAMESPACE  # FlowToolKit__ on an action or a called flow
FTK_COMPONENT_PREFIX = NAMESPACE[:-2] + ":"  # FlowToolKit: on a screen component

FORMULA_TOKEN_RE = re.compile(r"\{!([^}]+)\}")
SKIP_TOKEN_PREFIXES = ("$Flow.", "$Api.", "$Label.", "$System.", "$User.",
                       "$Profile.", "$Organization.", "$Setup.", "$Permission.",
                       "$UserRole.", "$GlobalConstant.", "$Client.")

URL_COMPONENT = "getUrlParameters"  # FlowToolKit:getUrlParameters, the URL parameter reader


def _bundle(field):
    extension = field.get("extensionName") or ""
    return local(extension.split(":", 1)[1] if ":" in extension else extension)


def _walk_screen_fields(fields):
    for field in fields:
        yield field
        yield from _walk_screen_fields(_as_list(field.get("fields")))


# Flow Tool Kit screen components and the input properties that carry a bare
# field API name directly (the config-JSON properties are handled separately).
KNOWN_COMPONENTS = {"flowForm", "flowDataTable", "flowFormRepeat", "flowFormLookup",
                    "fieldSetForm", "flowDateTimePicker", "mergeRecords", "formTemplate"}
COMPONENT_FIELD_PROPS = {"selectedMergeRecordField", "hierarchyFieldName",
                         "selectionReturnFieldValue", "repositionFieldApiName",
                         "viewDetailsUrlField", "startDateTimeFieldName",
                         "selectorLabelFieldName", "disabledFieldName",
                         "themeFieldName", "fieldName"}
FORM_NAME_PROPS = {"formQualifiedApiName", "overrideTableFormName",
                   "overrideTableFormBulkName", "editFormQualifiedApiName"}

# Invocable actions whose string inputs carry field API names.
INVOCABLE_FIELD_INPUTS = {
    "Flow_StripNullValues_Invocable": {"nullableFieldsCsv": "nullable fields"},
    "FormSubmission_LogEvent_Invocable": {"statusFieldApiName": "conversion status field",
                                          "lookupFieldApiName": "conversion lookup field"},
    "Recalculate_Positions_Invocable": {"fieldApiName": "position field"},
    "Flow_ApplySubmissionMap_Invocable": {"lookupField": "mapping lookup (Apply Submission Field Maps)"},
}


def _as_list(node):
    if node is None:
        return []
    return node if isinstance(node, list) else [node]


def _value_of(value_dict):
    """Flow <value> payload -> (kind, literal)."""
    for kind in ("stringValue", "elementReference", "booleanValue", "numberValue",
                 "dateValue", "dateTimeValue", "apexValue", "sobjectValue"):
        if isinstance(value_dict, dict) and value_dict.get(kind) is not None:
            return kind, value_dict[kind]
    return None, None


def flow_reference(obj, field, surface, role, flow, element="", element_type="",
                   snippet="", resolution="parsed"):
    return {
        "ftk_role": flow.get("ftk_role", ""),
        "object": fold_star(obj or ""),
        "field": fold_star(field or ""),
        "surface": surface,
        "role": role,
        "flow_label": flow["label"],
        "flow_api": flow["api_name"],
        "flow_type": flow["type"],
        "element": element,
        "element_type": element_type,
        "snippet": (snippet or "")[:120],
        "resolution": resolution,
        "flow_path": flow["path"],
        "is_path": is_path(field or ""),
    }


def flow_display_type(process_type, meta):
    start = (meta.get("start") or {}) if isinstance(meta.get("start"), dict) else {}
    trigger = start.get("triggerType") or ""
    if process_type == "Flow":
        return "Screen Flow"
    if trigger in ("RecordAfterSave", "RecordBeforeSave", "RecordBeforeDelete"):
        return "Record-Triggered"
    if trigger == "Scheduled":
        return "Scheduled"
    if trigger == "PlatformEvent" or process_type == "CustomEvent":
        return "Platform Event"
    if process_type == "AutoLaunchedFlow":
        return "Autolaunched"
    return process_type


class FlowScanner:
    """One flow version: builds the variable table, then walks every
    field-bearing element shape."""

    def __init__(self, flow, meta, resolve_form, emit, coverage):
        self.flow, self.meta = flow, meta
        self.resolve_form, self.emit, self.coverage = resolve_form, emit, coverage
        start = meta.get("start") if isinstance(meta.get("start"), dict) else {}
        self.start_object = fold_star((start or {}).get("object") or "")
        self.var_types = {}
        for variable in _as_list(meta.get("variables")):
            if variable.get("dataType") == "SObject" and variable.get("objectType"):
                self.var_types[variable["name"]] = fold_star(variable["objectType"])
        if self.start_object:
            self.var_types["$Record"] = self.start_object
            self.var_types["$Record__Prior"] = self.start_object
        # recordLookups with automatic output become var-like element names
        for lookup in _as_list(meta.get("recordLookups")):
            if lookup.get("object") and lookup.get("name"):
                self.var_types.setdefault(lookup["name"], fold_star(lookup["object"]))
        # Get URL Parameters screen components: their outputs (pv1 to pv9 and the
        # rest) are the URL parameters a flow maps into fields
        self.url_components = set()
        for screen in _as_list(meta.get("screens")):
            for field in _walk_screen_fields(_as_list(screen.get("fields"))):
                if _bundle(field) == URL_COMPONENT and field.get("name"):
                    self.url_components.add(field["name"])
        self.literals = {}
        for constant in _as_list(meta.get("constants")):
            kind, value = _value_of(constant.get("value") or {})
            if kind == "stringValue":
                self.literals[constant["name"]] = value
        for variable in _as_list(meta.get("variables")):
            kind, value = _value_of(variable.get("value") or {})
            if kind == "stringValue":
                self.literals[variable["name"]] = value

    # -- reference helpers ---------------------------------------------------
    def ref(self, obj, field, surface, role, element, element_type, snippet="",
            resolution="parsed"):
        self.emit(flow_reference(obj, field, surface, role, self.flow, element,
                                 element_type, snippet, resolution))

    def var_ref(self, dotted, role, element, element_type, snippet="", surface="Flow Element"):
        """``Var.Field`` or ``Var.Rel__r.Field`` -> a reference on the
        variable's object; unresolvable variables are skipped quietly (they
        are non-SObject plumbing, not field references)."""
        if not dotted or "." not in dotted:
            return
        head, tail = dotted.split(".", 1)
        obj = self.var_types.get(head)
        if not obj:
            return
        self.ref(obj, tail, surface, role, element, element_type,
                 snippet or dotted)

    def url_param_ref(self, value_reference, target, element, element_type):
        """A field given the value of a Get URL Parameters output
        (``getUrlParametersCMP.pv1``) is a URL parameter mapping."""
        head, _, param = (value_reference or "").partition(".")
        if head in self.url_components and param:
            self.var_ref(target, f"URL parameter target ({param})", element, element_type,
                         snippet=f"?{param}= via {head}", surface="URL Parameter")

    def formula_refs(self, text, role, element, element_type):
        for token in FORMULA_TOKEN_RE.findall(text or ""):
            token = token.strip()
            if any(token.startswith(prefix) for prefix in SKIP_TOKEN_PREFIXES):
                continue
            if token.startswith("$Record.") or token.startswith("$Record__Prior."):
                if self.start_object:
                    self.ref(self.start_object, token.split(".", 1)[1], "Flow Formula",
                             role, element, element_type, token)
                continue
            if "." in token:
                head, tail = token.split(".", 1)
                obj = self.var_types.get(head)
                if obj:
                    self.ref(obj, tail, "Flow Formula", role, element, element_type, token)

    # -- element walks -------------------------------------------------------
    def scan(self):
        self._scan_start()
        self._scan_record_elements()
        self._scan_decisions()
        self._scan_assignments()
        self._scan_transforms()
        self._scan_formulas_and_text()
        self._scan_choice_sets()
        self._scan_screens()
        self._scan_actions()

    def _filters(self, element, obj, element_type):
        for criterion in _as_list(element.get("filters")):
            if criterion.get("field"):
                _, value = _value_of(criterion.get("value") or {})
                snippet = f"{criterion.get('operator', '')} {value if value is not None else ''}".strip()
                self.ref(obj, criterion["field"], "Flow Element", "record filter",
                         element.get("name") or element_type, element_type, snippet)

    def _scan_start(self):
        start = self.meta.get("start") if isinstance(self.meta.get("start"), dict) else {}
        if not start:
            return
        obj = self.start_object
        if obj:
            self._filters(start, obj, "start")
        self.formula_refs(start.get("filterFormula") or "", "entry criterion formula",
                          "start", "start")

    def _scan_record_elements(self):
        for element_type in ("recordLookups", "recordUpdates", "recordCreates",
                             "recordDeletes"):
            for element in _as_list(self.meta.get(element_type)):
                obj = fold_star(element.get("object") or "")
                name = element.get("name", "")
                if obj:
                    self._filters(element, obj, element_type)
                    for field in _as_list(element.get("queriedFields")):
                        self.ref(obj, field, "Flow Element", "queried field", name,
                                 element_type)
                    if element.get("sortField"):
                        self.ref(obj, element["sortField"], "Flow Element", "sort field",
                                 name, element_type)
                    for assignment in _as_list(element.get("inputAssignments")):
                        if assignment.get("field"):
                            kind, value = _value_of(assignment.get("value") or {})
                            self.ref(obj, assignment["field"], "Flow Element",
                                     "field assignment", name, element_type,
                                     str(value) if value is not None else "(null)")
                            if kind == "elementReference":
                                self.var_ref(value, "assignment value", name, element_type)
                                head, _, param = value.partition(".")
                                if head in self.url_components and param:
                                    self.ref(obj, assignment["field"], "URL Parameter",
                                             f"URL parameter target ({param})", name, element_type,
                                             f"?{param}= via {head}")
                    for assignment in _as_list(element.get("outputAssignments")):
                        if assignment.get("field"):
                            self.ref(obj, assignment["field"], "Flow Element",
                                     "output assignment", name, element_type)
                            self.var_ref(assignment.get("assignToReference") or "",
                                         "assignment target", name, element_type)

    def _scan_decisions(self):
        for decision in _as_list(self.meta.get("decisions")):
            for rule in _as_list(decision.get("rules")):
                for condition in _as_list(rule.get("conditions")):
                    self.var_ref(condition.get("leftValueReference") or "",
                                 "decision condition", decision.get("name", ""),
                                 "decision")
                    kind, value = _value_of(condition.get("rightValue") or {})
                    if kind == "elementReference":
                        self.var_ref(value, "decision condition", decision.get("name", ""),
                                     "decision")

    def _scan_assignments(self):
        for assignment in _as_list(self.meta.get("assignments")):
            for item in _as_list(assignment.get("assignmentItems")):
                self.var_ref(item.get("assignToReference") or "", "assignment target",
                             assignment.get("name", ""), "assignment")
                kind, value = _value_of(item.get("value") or {})
                if kind == "elementReference":
                    self.var_ref(value, "assignment value", assignment.get("name", ""),
                                 "assignment")
                    self.url_param_ref(value, item.get("assignToReference") or "",
                                       assignment.get("name", ""), "assignment")

    def _scan_transforms(self):
        for transform in _as_list(self.meta.get("transforms")):
            obj = fold_star(transform.get("objectType") or "")
            name = transform.get("name", "")
            values = transform.get("transformValues")
            for group in _as_list(values):
                for action in _as_list(group.get("transformValueActions")):
                    kind, value = _value_of(action.get("value") or {})
                    if action.get("outputFieldApiName") and obj:
                        self.ref(obj, action["outputFieldApiName"], "Flow Element",
                                 "transform output", name, "transform",
                                 str(value) if value is not None else "")
                    if kind == "elementReference":
                        self.var_ref(value, "transform source", name, "transform")

    def _scan_formulas_and_text(self):
        for formula in _as_list(self.meta.get("formulas")):
            self.formula_refs(formula.get("expression") or "", "formula operand",
                              formula.get("name", ""), "formula")
        for template in _as_list(self.meta.get("textTemplates")):
            self.formula_refs(template.get("text") or "", "text template merge",
                              template.get("name", ""), "textTemplate")

    def _scan_choice_sets(self):
        for choice_set in _as_list(self.meta.get("dynamicChoiceSets")):
            obj = fold_star(choice_set.get("object") or "")
            if not obj:
                continue
            name = choice_set.get("name", "")
            for prop, role in (("displayField", "choice display field"),
                               ("valueField", "choice value field"),
                               ("sortField", "sort field")):
                if choice_set.get(prop):
                    self.ref(obj, choice_set[prop], "Flow Element", role, name,
                             "dynamicChoiceSet")
            self._filters(choice_set, obj, "dynamicChoiceSet")

    # -- screens -------------------------------------------------------------
    def _scan_screens(self):
        for screen in _as_list(self.meta.get("screens")):
            self._scan_screen_fields(_as_list(screen.get("fields")), screen.get("name", ""))

    def _scan_screen_fields(self, fields, screen_name):
        for field in fields:
            nested = _as_list(field.get("fields"))
            if nested:  # section / region container
                self._scan_screen_fields(nested, screen_name)
            rule = field.get("visibilityRule")
            if isinstance(rule, dict):
                for condition in _as_list(rule.get("conditions")):
                    self.var_ref(condition.get("leftValueReference") or "",
                                 "visibility condition", field.get("name", screen_name),
                                 "screen field")
            validation = field.get("validationRule")
            if isinstance(validation, dict):
                self.formula_refs(validation.get("formulaExpression") or "",
                                  "validation formula", field.get("name", screen_name),
                                  "screen field")
            if field.get("objectFieldReference"):  # a record field placed on the screen
                self.var_ref(field["objectFieldReference"], "screen input field",
                             field.get("name", screen_name), "screen field")
            kind, value = _value_of(field.get("defaultValue") or {})
            if kind == "elementReference":
                self.var_ref(value, "default value", field.get("name", screen_name),
                             "screen field")
            if field.get("fieldType") == "ComponentInstance":
                if _bundle(field) == URL_COMPONENT:  # outputs stored straight into record fields
                    for output in _as_list(field.get("outputParameters")):
                        self.var_ref(output.get("assignToReference") or "",
                                     f"URL parameter target ({output.get('name', '')})",
                                     field.get("name", screen_name), URL_COMPONENT,
                                     snippet=f"?{output.get('name', '')}=", surface="URL Parameter")
                self._scan_component(field, screen_name)

    def _scan_component(self, field, screen_name):
        extension = field.get("extensionName") or ""
        bundle = local(extension.split(":", 1)[1] if ":" in extension else extension)
        if bundle not in KNOWN_COMPONENTS:
            return
        name = field.get("name", screen_name)
        inputs = {}
        for parameter in _as_list(field.get("inputParameters")):
            inputs[parameter.get("name")] = _value_of(parameter.get("value") or {})
        object_kind, object_value = inputs.get("object", (None, None))
        component_object = fold_star(object_value) if object_kind == "stringValue" else ""

        for prop in COMPONENT_FIELD_PROPS:
            kind, value = inputs.get(prop, (None, None))
            if kind == "stringValue" and value:
                self.ref(component_object or SUBMISSION_OBJECT, value, "Flow Screen Form",
                         f"component property ({prop})", name, bundle)

        json_enabled = inputs.get("formJsonEnabled", (None, None))[1] is True
        json_kind, json_value = inputs.get("formJSON", (None, None))
        if json_enabled and json_kind == "stringValue" and (json_value or "").strip():
            self._scan_form_json(json_value, component_object, name, bundle)
        else:
            for prop in FORM_NAME_PROPS:
                kind, value = inputs.get(prop, (None, None))
                if kind == "stringValue" and value:
                    self._emit_resolved_form(value, name, bundle, prop)
                elif kind == "elementReference" and value:
                    literal = self.literals.get(value)
                    if literal:
                        self._emit_resolved_form(literal, name, bundle, prop,
                                                 snippet=f"via {value}")
                    else:
                        self.ref(component_object, "", "Flow Screen Form",
                                 f"dynamic form selector ({prop})", name, bundle,
                                 snippet=f"{{!{value}}}", resolution="not captured")
        if bundle == "fieldSetForm":
            kind, value = inputs.get("fieldSetName", (None, None))
            if kind == "stringValue" and value:
                self.ref(component_object, value, "Flow Screen Form",
                         "field set (members not expanded)", name, bundle,
                         resolution="not captured")

    def _scan_form_json(self, json_text, component_object, element, bundle):
        try:
            config = json.loads(json_text)
        except (json.JSONDecodeError, ValueError):
            self.coverage.append({"store": "Flow formJSON", "status": "unparseable",
                                  "detail": f"{self.flow['api_name']} / {element}"})
            return
        collected = []
        walk.walk_config(config, component_object or SUBMISSION_OBJECT,
                         lambda obj, fld, role, snip, surface=None: collected.append((obj, fld, role, snip)))
        for obj, fld, role, snip in collected:
            self.ref(obj, fld, "Flow Screen Form", role, element, bundle, snip)

    def _emit_resolved_form(self, form_name, element, bundle, prop, snippet=""):
        resolved = self.resolve_form(form_name)
        if resolved is None:
            self.coverage.append({"store": "Flow Screen Form", "status": "missing",
                                  "detail": f"{self.flow['api_name']} / {element}: "
                                            f"form '{form_name}' not found"})
            return
        component_type, refs, label, key, path = resolved
        for obj, fld, role, snip, surface in refs:
            if surface == walk.MAPPING_SURFACE:
                continue  # the form's Form Template Mapping is counted once, by the template sweep
            self.ref(obj, fld, "Flow Screen Form", role, element, bundle,
                     snippet or f"{prop}: {label}")

    # -- invocable actions ---------------------------------------------------
    def _scan_actions(self):
        for action in _as_list(self.meta.get("actionCalls")):
            action_name = local(action.get("actionName") or "")
            field_inputs = INVOCABLE_FIELD_INPUTS.get(action_name)
            if not field_inputs:
                continue
            for parameter in _as_list(action.get("inputParameters")):
                role = field_inputs.get(parameter.get("name"))
                if not role:
                    continue
                kind, value = _value_of(parameter.get("value") or {})
                if kind != "stringValue" or not value:
                    continue
                if parameter.get("name") == "nullableFieldsCsv":
                    for obj, fld in walk.parse_nullable(value):
                        self.ref(obj or "", fld, "Flow Action", role,
                                 action.get("name", ""), action_name)
                elif value != "ALL":
                    # the map's lookup is a Form Submission field; other inputs name no object
                    obj = SUBMISSION_OBJECT if action_name == "Flow_ApplySubmissionMap_Invocable" else ""
                    self.ref(obj, value, "Flow Action", role, action.get("name", ""), action_name)


# ---- which flows are Flow Tool Kit's ------------------------------------------------------------------------------

def _split(name):
    """``FlowToolKit__Convert`` -> ("FlowToolKit", "Convert"). A flow API name
    cannot hold two underscores in a row, so ``__`` is the namespace separator."""
    name = (name or "").strip()
    namespace, sep, rest = name.partition("__")
    return (namespace, rest) if sep else ("", name)


def named_flows(raw):
    """Flow name (as stored) -> [why], for every conversion and prefill flow a
    Form Template or page section names, and the screen flow each Flow Section
    shows. Default and Bypass name no flow of their own."""
    from .queries import CONVERSION_TARGETS, SECTION_RULE_DEFAULTS

    defaults = {val(r, "DeveloperName"): val(r, N + "Flow_API_Name__c") for r in records(raw, "conversion_defaults")}
    found = {}

    def add(name, why):
        name = (name or "").strip()
        if name and name not in ("Default", "Bypass"):
            found.setdefault(name, [])
            if why not in found[name]:
                found[name].append(why)

    for row in records(raw, "templates"):
        template = val(row, "Name") or val(row, "Id") or ""
        for target, default_record in CONVERSION_TARGETS.items():
            why = f"conversion flow ({target}) of template {template}"
            choice = (val(row, f"{N}Conversion_Map_Flow_{target}__c") or "").strip()
            formula = val(row, f"{N}FlowApiName_{target}__c")
            add(formula, why)
            if choice and choice != "Default":
                add(choice, why)
            elif not formula:
                add(defaults.get(default_record), why)
        add(val(row, N + "Prefill_Flow_Api_Name__c"), f"prefill flow of template {template}")
    for row in records(raw, "sections"):
        section = val(row, N + "Title__c") or val(row, "Name") or ""
        why = f"conversion flow of section {section}"
        choice = (val(row, N + "Conversion_Map_Flow__c") or "").strip()
        formula = val(row, N + "FlowApiName_Related__c")
        add(formula, why)
        if choice and choice != "Default":
            add(choice, why)
        elif not formula:
            rule = (val(row, N + "Conversion_Rule__c") or "").split(" ")[0]
            add(defaults.get(SECTION_RULE_DEFAULTS.get(rule, "")), why)
        if (val(row, N + "Component_Type__c") or "").strip() == "Flow":
            add(val(row, N + "FlowApiName__c"), f"Flow Section screen flow of section {section}")
    return found


def _screen_components(fields):
    for field in _as_list(fields):
        yield field.get("extensionName") or ""
        yield from _screen_components(field.get("fields"))


def ftk_uses(meta):
    """Why a flow is Flow Tool Kit's from its own elements: a Flow Tool Kit
    action, screen component or called flow, by the namespace on its name."""
    uses = []
    for action in _as_list(meta.get("actionCalls")):
        name = action.get("actionName") or ""
        if name.startswith(FTK_PREFIX):
            uses.append(f"uses the Flow Tool Kit action {name[len(FTK_PREFIX):]}")
    for screen in _as_list(meta.get("screens")):
        for extension in _screen_components(screen.get("fields")):
            if extension.startswith(FTK_COMPONENT_PREFIX):
                uses.append(f"uses the Flow Tool Kit screen component {extension[len(FTK_COMPONENT_PREFIX):]}")
    for subflow in _as_list(meta.get("subflows")):
        name = subflow.get("flowName") or ""
        if name.startswith(FTK_PREFIX):
            uses.append(f"calls the Flow Tool Kit flow {name[len(FTK_PREFIX):]}")
    return list(dict.fromkeys(uses))


def subflow_names(meta):
    return [s.get("flowName") for s in _as_list(meta.get("subflows")) if s.get("flowName")]


class FlowPlan:
    """Which flows to read and which are Flow Tool Kit's, from what raw.json holds.

    scope ``all`` reads every flow the org owns to find the ones using Flow Tool
    Kit; ``named`` reads only the flows templates and sections name and their
    subflows. Either way only Flow Tool Kit flows are listed."""

    def __init__(self, raw, options):
        self.raw, self.scope = raw, options["flows"]
        self.org_namespace = val((records(raw, "org") or [{}])[0], "NamespacePrefix") or ""
        self.definitions = {}
        for row in records(raw, "flow_definitions"):
            api_name = val(row, "ApiName") or ""
            if api_name and (val(row, "ActiveVersionId") or val(row, "LatestVersionId")):
                self.definitions[self.key(f"{val(row, 'NamespacePrefix') or ''}__{api_name}"
                                          if val(row, "NamespacePrefix") else api_name)] = row
        self.named = {}  # key -> [why]
        self.unknown = []  # (name, why): named, but no such flow in the org
        for name, whys in named_flows(raw).items():
            key = self.key(name)
            if key in self.definitions or key[0]:
                self.named.setdefault(key, []).extend(whys)
            else:
                self.unknown.append((name, whys[0]))
        self.reasons = {}  # key -> [why], every Flow Tool Kit flow
        self._close()

    def key(self, name):
        namespace, api_name = _split(name)
        return ("" if namespace == self.org_namespace else namespace, api_name)

    def own(self, key):
        """A flow the org owns; an org does not serve a package's flow metadata."""
        return not key[0] and key in self.definitions

    def metadata(self, key):
        return _metadata(self.raw, key[1]) if self.own(key) else None

    def _close(self):
        """Named flows and flows using Flow Tool Kit, then every subflow they call."""
        for key, whys in self.named.items():
            self.reasons[key] = list(whys)
        if self.scope == "all":
            for key in self.definitions:
                meta = self.metadata(key)
                if meta is not None and ftk_uses(meta):
                    self.reasons.setdefault(key, []).extend(ftk_uses(meta))
        queue = list(self.reasons)
        while queue:
            parent = queue.pop()
            meta = self.metadata(parent)
            for name in subflow_names(meta or {}):
                key = self.key(name)
                if key[0] == NAMESPACE[:-2]:
                    continue  # Flow Tool Kit's own flow, already a reason on the parent
                why = f"subflow of {parent[1]}"
                if key not in self.reasons:
                    self.reasons[key] = [why]
                    queue.append(key)
                elif why not in self.reasons[key]:
                    self.reasons[key].append(why)
        for key in self.reasons:
            meta = self.metadata(key)
            if meta is not None:
                for use in ftk_uses(meta):
                    if use not in self.reasons[key]:
                        self.reasons[key].append(use)

    def to_read(self):
        keys = self.definitions if self.scope == "all" else self.reasons
        return [self.definitions[key] for key in keys if self.own(key)]


def _metadata(raw, api_name):
    rows = records(raw, "flow:" + api_name)
    if not rows:
        return None
    metadata = val(rows[0], "Metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except ValueError:
            return None
    return metadata if isinstance(metadata, dict) else None


def _flows_readable(raw, options):
    return (options["flows"] != "none" and ocutil.ran(raw, "flow_definitions")
            and not ocutil.failed(raw, "flow_definitions"))


def metadata_queries(raw, options):
    if not _flows_readable(raw, options):
        return []
    queries = []
    for row in FlowPlan(raw, options).to_read():
        version = val(row, "ActiveVersionId") or val(row, "LatestVersionId")
        queries.append({"key": "flow:" + val(row, "ApiName"), "tooling": True, "optional": True,
                        "soql": f"SELECT Id, Metadata FROM Flow WHERE Id = '{version}'",
                        "why": f"the {'active' if val(row, 'ActiveVersionId') else 'latest'} version of flow "
                               f"{val(row, 'Label') or val(row, 'ApiName')}"})
    return queries


def _names(items, limit=8):
    items = list(items)
    return ", ".join(items[:limit]) + ("..." if len(items) > limit else "")


def scan_all(raw, options, resolve_form, coverage,
             base_path="/builder_platform_interaction/flowBuilder.app?flowId="):
    """Flow reference rows for every Flow Tool Kit flow, and coverage rows for
    the ones that could not be read. Other flows are never listed."""
    references = []
    if options["flows"] == "none":
        coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                         "detail": "flow scan turned off (flows: none)"})
        return references
    if not _flows_readable(raw, options):
        coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                         "detail": "the flow list could not be read"})
        return references
    plan = FlowPlan(raw, options)
    scanned, named, unreadable, packaged = 0, 0, [], []
    for key, reasons in plan.reasons.items():
        name = f"{key[0]}__{key[1]}" if key[0] else key[1]
        if not plan.own(key):
            packaged.append(name)
            continue
        definition = plan.definitions[key]
        meta = plan.metadata(key)
        if meta is None:
            unreadable.append(name)
            continue
        version = val(definition, "ActiveVersionId") or val(definition, "LatestVersionId")
        flow = {"api_name": key[1], "label": val(definition, "Label") or key[1],
                "type": flow_display_type(val(definition, "ProcessType") or "", meta),
                "path": f"{base_path}{version}", "ftk_role": "; ".join(reasons)}
        FlowScanner(flow, meta, resolve_form, references.append, coverage).scan()
        scanned += 1
        named += key in plan.named
    coverage.append({"store": "Flow Tool Kit flows", "status": "parsed",
                     "detail": f"{scanned} scanned ({named} named by a template or section as a conversion, "
                               f"prefill or Flow Section flow; the rest use a Flow Tool Kit action or screen component, or are "
                               f"their subflows; scope: {options['flows']}; active version, else latest)"})
    for name, why in plan.unknown:
        coverage.append({"store": "Flow Tool Kit flows", "status": "missing",
                         "detail": f"{why} names {name}, which is not a flow in this org"})
    if packaged:
        coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                         "detail": f"{len(packaged)} belong to Flow Tool Kit or another package (such as the default "
                                   f"conversion flows), and an org does not serve their metadata: {_names(packaged)}"})
    if unreadable:
        coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                         "detail": f"metadata not read for {len(unreadable)}: {_names(unreadable)}"})
    if options["flows"] == "all":
        missed = [key[1] for key in plan.definitions if plan.own(key) and key not in plan.reasons
                  and plan.metadata(key) is None]
        if missed:
            coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                             "detail": f"{len(missed)} flows could not be read, so whether they use Flow Tool Kit is "
                                       f"not known: {_names(missed)}"})
    else:
        coverage.append({"store": "Flow Tool Kit flows", "status": "not_captured",
                         "detail": "scope named: flows that use a Flow Tool Kit action or screen component but are "
                                   "not named by a template or section were not checked"})
    return references
