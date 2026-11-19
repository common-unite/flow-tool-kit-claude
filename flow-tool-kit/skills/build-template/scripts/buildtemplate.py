#!/usr/bin/env python3
"""Build a draft Form Template as records from form-design's plan.json.

    python3 buildtemplate.py <plan.json> [--org <org-alias>] [--config flow-tool-kit.json] [--dry-run] [--out <file>]
                             [--missing-fields <Field__c,...>]

Records only: the template, its pages and sections (each section's form as component JSON or a reference to a
component), and the record components the plan owns. No metadata is deployed, so a rebuild takes seconds.

The plan's intake.build_mode picks the build mode: "metadata" (the default, and every plan written before modes) builds
each component in the shape the plan names and hands metadata components to build-form-component; "records" builds
records and JSON only, so the whole build can run from claude.ai chat with a Salesforce connector: a component the plan
marks metadata becomes a record component (recorded as components[].built_shape for convert-to-metadata), and what
needs a deploy (new fields, Flow Sections, custom LWCs, the PDF running user) is listed as a follow-up for Claude Code.

Rerunnable. The first run writes build.template_id, build.key, build.prefix and build.form_ids back into plan.json.
Later runs update the template and its pages in place (pages are matched by ExternalId__c within this template),
delete pages the plan dropped, and delete and recreate every section, because the package overwrites a section's
ExternalId__c with its own Id on every save. A run that fails after it created a new template deletes that template,
so no half-built template is left behind. The package gives each new template a Pre-fill Template (a Form Submission):
the report and build.prefill_template_id name it, and it is deleted with a template the build created and removes.

--dry-run needs no org: it prints every record and component the build would write (and --out saves them), which is
also how claude.ai chat builds through a Salesforce connector (references/chat-build.md). Standard library only.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brandstyles  # noqa: E402
import fieldmap  # noqa: E402
import formlabels  # noqa: E402
import formnames  # noqa: E402
import header  # noqa: E402
import newfields  # noqa: E402
import picklists  # noqa: E402
import recordcomponents  # noqa: E402
from sforg import BuildError, Org, quoted  # noqa: E402

N = "FlowToolKit__"
STAR = "*__"
PACKAGE_OBJECTS = {"Form_Submission__c", "Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c", "Form_Component__c"}
FREE_OBJECTS = {"Form_Submission__c", "Account", "Contact", "Lead", "Case", "Campaign", "CampaignMember"}
DECISIONS = ("reuse", "extend", "update", "shared-new", "form-only", "flow-section", "custom-lwc", "shared-record")
REFERENCED = ("reuse", "update")  # components the build only points at; it cannot put a field rule inside them
# The component shapes standard: how a component's questions are stored. The person chooses it for a form-only, shared-new
# or extend component (form-design records shape and shape_asked); reuse and update keep the existing component's shape.
# A plan written before shapes has none, and is built as plans always were (LEGACY_SHAPE)
SHAPES = ("metadata", "record", "json")
CHOSEN_SHAPE = ("form-only", "shared-new", "extend")
LEGACY_SHAPE = {"form-only": "json", "shared-new": "record", "extend": "record", "shared-record": "record"}
OWNED = ("form-only", "shared-new", "extend", "shared-record")  # components this plan builds, in the shape it names


def shape_of(c: dict) -> str | None:
    """The shape the build makes a component in: the plan's shape, else what plans before shapes were built as."""
    return c.get("shape") or LEGACY_SHAPE.get(c.get("decision"))


def check_shape(c: dict, where: str) -> tuple[list[str], list[str]]:
    """(problems, warnings) for a component's shape: one of the three, asked and answered, JSON only on one section."""
    problems, warnings = [], []
    decision, shape = c.get("decision"), c.get("shape")
    if shape is None:
        if decision in CHOSEN_SHAPE:
            warnings.append(f"{where}: the plan records no shape, so it is built as {LEGACY_SHAPE[decision]}, as plans before shapes "
                            "were. Recommend metadata, record or JSON in form-design, ask, and record shape and shape_asked")
        return problems, warnings
    if shape not in SHAPES:
        return [f"{where}: shape {shape!r} is not one of {', '.join(SHAPES)}"], warnings
    if decision in ("flow-section", "custom-lwc"):
        problems.append(f"{where}: a {decision} section has no shape; remove shape")
    elif shape == "json" and decision != "form-only":
        problems.append(f"{where}: JSON is fixed to one section, so only a form-only component can be JSON; a {decision} component "
                        "is a metadata or record component")
    elif decision == "shared-record" and shape != "record":
        problems.append(f"{where}: a promoted section (consolidate-sections) is a record component; shape must be record")
    if decision in CHOSEN_SHAPE and str((c.get("shape_asked") or {}).get("answer") or "").strip().lower() != shape:
        problems.append(f"{where}: shape {shape!r} has no matching answer in shape_asked; the shape is recommended and asked, "
                        "never decided silently")
    return problems, warnings


def owned_name(c: dict, family: str, form_ids: dict) -> str:
    """The name a component this plan builds goes by: an extend copy's new_name, a shared one's name, else the generated
    name a section's own form would have had (kept in build.form_ids, so a rebuild keeps it)."""
    if c.get("decision") == "extend":
        return c.get("built_name") or c.get("new_name") or formnames.form_name(family, c.get("key") or c["name"], form_ids)
    return c.get("name") or formnames.form_name(family, c.get("key"), form_ids)


# Build modes (intake.build_mode, asked in ftk-start's and form-design's gap round: "Build as metadata, or load as records
# for fast prototyping?"). metadata: each component in the shape the plan names. records: records and JSON only, never
# a metadata deploy, so the whole build can run from chat; a component this plan builds as metadata is built as a
# record component instead. A plan without the key (every plan before modes) builds as metadata, exactly as before.
BUILD_MODES = ("metadata", "records")


def build_mode(plan: dict) -> str:
    return str((plan.get("intake") or {}).get("build_mode") or "metadata").strip().lower()


def built_shape(c: dict, mode: str = "metadata") -> str | None:
    """The shape this build makes a component in: the plan's (shape_of), except that records mode builds a component
    this plan owns as a record component where the plan says metadata. Reused and updated components are never built
    here, only referenced, so their shape never changes."""
    shape = shape_of(c)
    if mode == "records" and shape == "metadata" and c.get("decision") in OWNED:
        return "record"
    return shape


def placed_name(c: dict, family: str, form_ids: dict, mode: str = "metadata") -> str:
    """The component name a page section points at: a one-off component's generated name, an extend copy's new name,
    else the component's own name (a reused one by the name the org knows it by)."""
    decision = c.get("decision")
    if decision == "form-only" or (decision == "extend" and built_shape(c, mode) == "metadata"):
        return owned_name(c, family, form_ids)
    return c.get("built_name") or c["name"]


def bare_field(name: str | None) -> str:
    return str(name or "").replace(STAR, N).removeprefix(N)


# The answers that mean "update the shared component in place", as build-form-component's composition.py reads them
UPDATE_ANSWERS = {"update", "update the shared component", "update shared"}


def check_update(c: dict, where: str) -> list[str]:
    """update changes a shared component in place, and every template and component that uses it. It is never the
    default: it needs its own question, answered update, naming everything it reaches (build-form-component's keys:
    asked, usage.status, usage.consumers, shared_change_reason, changes), and a packaged component can never be updated.
    build-template only points the section at the component; build-form-component makes the change."""
    problems = []
    name = c.get("name") or c.get("component_id") or ""
    match = c.get("catalog_match") or {}
    if c.get("packaged") or match.get("packaged") or match.get("editable") is False or name.startswith(N):
        problems.append(f"{where}: {name} is a Flow Tool Kit component, which can never be updated; answer extend for a new version")
    asked = c.get("asked") or {}
    question = str(asked.get("question") or "")
    if str(asked.get("answer") or "").strip().lower() not in UPDATE_ANSWERS:
        problems.append(f"{where}: updating the shared component in place needs its own question, answered update; it is never the default")
    usage = c.get("usage") or {}
    consumers = [str(x) for x in usage.get("consumers") or []]
    if usage.get("status") != "complete" or not consumers:
        problems.append(f"{where}: the update's reach is not recorded: usage.status complete and usage.consumers, every template and component it changes")
    unnamed = [x for x in consumers if x not in question]
    if unnamed:
        problems.append(f"{where}: the update question must name every template and component it reaches; it does not name {', '.join(unnamed)}")
    if not c.get("shared_change_reason") or not c.get("changes"):
        problems.append(f"{where}: an update needs shared_change_reason and changes (what changes for everyone who uses it)")
    return problems
OPERATORS = {"TRUE", "FALSE", "==", "!=", "CONTAINS", "INCLUDES", "EXCLUDES", "BLANK", "NOTBLANK", "<", ">", "<=", ">="}
NO_VALUE = {"TRUE", "FALSE", "BLANK", "NOTBLANK"}
LABEL_LIMIT = 40  # the Label length Form Builder stores
API_NAME_LIKE = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$")
DESIGN_ONLY_KEYS = {"Likert_Mode__c"}  # plan keys that shape the inner form, not page-section fields
URL_PARAMETERS = {f"pv{i}" for i in range(1, 10)} | {"utm_source", "utm_content", "utm_medium", "utm_term", "utm_campaign", "payment_intent", "eventType"}
FLOW_API_NAME = re.compile(r"^([A-Za-z][A-Za-z0-9]*__)?[A-Za-z][A-Za-z0-9_]*$")
SECTION = N + "Form_Template_Page_Section__c"
NOT_BUILT_CONTROLS = {"Repeater": "a repeating section: build the repeated form with build-form-component, then set the section to Repeater in Form Builder"}


# ---------------------------------------------------------------- names
def star(name: str) -> str:
    return STAR + name[len(N):] if name.startswith(N) else name


def ns_object(name: str) -> str:
    """Package objects carry the namespace; the org's own and standard objects keep their names."""
    name = name.replace(STAR, N)
    return N + name if name in PACKAGE_OBJECTS else name


class Names:
    """Resolves the API names the plan writes against the org. Without an org (a dry run), package record keys get the
    namespace and field names are used exactly as the plan writes them: packaged fields as FlowToolKit__X__c, the org's
    own as X__c (references/plan-keys.md)."""

    def __init__(self, org=None):
        self.org = org
        self.unknown: list[str] = []
        self.missing_optional: list[str] = []

    def object_fields(self, obj: str) -> set[str]:
        return self.org.fields(obj) if self.org else set()

    def record_key(self, obj: str, key: str, optional: bool = False) -> str | None:
        """A Form Template, page or section field from the plan: package field, or the org's own field on that object.
        optional: a value the build adds itself, left out (not an error) when this org's Flow Tool Kit has no such field."""
        if not key.endswith("__c") or key.startswith(N):
            return key
        if self.org is None:
            return N + key
        fields = self.object_fields(obj)
        if N + key in fields:
            return N + key
        if key in fields:
            return key
        if optional:
            self.missing_optional.append(key)
        else:
            self.unknown.append(f"{obj}.{key}")
        return None

    def field(self, obj: str, name: str) -> str:
        """A field a form or rule uses, as the org spells it (a plan written with bare package names still resolves)."""
        name = name.replace(STAR, N)
        if self.org is None or name.startswith(N) or not name.endswith("__c"):
            return name
        fields = self.object_fields(obj)
        return name if name in fields or N + name not in fields else N + name

    def exists(self, obj: str, name: str) -> bool:
        return self.org is None or self.field(obj, name) in self.object_fields(obj)


def record_fields(entry: dict, obj: str, names: Names) -> dict:
    out = {}
    for key, value in entry.items():
        if key in DESIGN_ONLY_KEYS or isinstance(value, (dict, list)) or value is None:
            continue
        if key == "Name" or key.endswith("__c"):
            resolved = names.record_key(obj, key)
            if resolved:
                out[resolved] = value
    return out


def plain(markup: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup or "")).strip()


# ---------------------------------------------------------------- checks
def check_label(label: str | None, where: str) -> list[str]:
    """Rules and sections show their Label in Form Builder, so it names their purpose, never an API name."""
    if not label or not label.strip():
        return [f"{where} needs a label that says its purpose, for example \"Over 18\" or \"Is a major donor\""]
    if len(label) > LABEL_LIMIT:
        return [f"{where} label {label!r} is over {LABEL_LIMIT} characters"]
    if API_NAME_LIKE.match(label) or label.endswith("__c"):
        return [f"{where} label {label!r} looks like an API name; write its purpose in plain words"]
    return []


def check_rule(condition: dict, where: str) -> list[str]:
    """Every planned rule must be buildable exactly; a rule that is not is a build error, never a warning."""
    if condition.get("show_when") and not condition.get("conditions"):
        return [f"{where}: the rule is only text ({condition['show_when']!r}); form-design must write field, operator and value"]
    problems = []
    if not condition.get("conditions"):
        problems.append(f"{where}: the rule has no conditions")
    for c in condition.get("conditions") or []:
        op = c.get("operator", "==")
        if not c.get("field"):
            problems.append(f"{where}: a condition has no field")
        if op not in OPERATORS:
            problems.append(f"{where}: operator {op!r} is not one the package evaluates")
        if op not in NO_VALUE and c.get("value") in (None, ""):
            problems.append(f"{where}: the condition on {c.get('field')} has no value")
        if re.search(r" (?:\||&) \S+ !?= ", str(c.get("value") or "")):
            problems.append(f"{where}: the value {c.get('value')!r} holds a second question; split the rule into one condition per question")
    if (condition.get("type") or "AND").upper() not in ("AND", "OR", "CUSTOM"):
        problems.append(f"{where}: type must be AND, OR or CUSTOM")
    if (condition.get("type") or "").upper() == "CUSTOM" and not condition.get("custom"):
        problems.append(f"{where}: a CUSTOM rule needs its logic in custom, for example \"(1 OR 2) AND 3\"")
    return problems + check_label(condition.get("label"), f"{where}: rule")


def check_copy(plan: dict) -> list[str]:
    """Every page needs a description of two or more sentences; every titled section a Title__c, header title and subtitle.
    Stage cards show the page description, and the stages accordion lists each section's title and subtitle."""
    problems = []
    for page in plan.get("pages") or []:
        label = page.get("Page_Label__c") or "?"
        description = (page.get("Description__c") or "").strip()
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", plain(description)) if s]
        # A Form Label token ({{$Label.X}}, from a translated plan) stands for copy already checked in the source language.
        if len(sentences) < 2 and not re.fullmatch(r"\{\{\$Label\.[A-Za-z0-9_]+\}\}", description):
            problems.append(f"page {label}: Description__c needs at least two sentences built from the page's questions")
        for section in page.get("sections") or []:
            if section.get("Component_Type__c") in ("Flow", "Lightning Web Component") and section.get("Title__c"):
                continue
            # A headerless section (a follow-up, a lone question, a note) still needs its name in the section list
            wanted = ("Title__c",) if section.get("Show_Header__c") is False or not section.get("Header_Title__c") else ("Title__c", "Header_Title__c", "Header_Subtitle__c")
            missing = [k for k in wanted if not section.get(k)]
            if missing:
                problems.append(f"page {label}, section {section.get('Header_Title__c') or section.get('component') or '?'}: missing {', '.join(missing)}")
    return problems


def check_components(plan: dict, edition: str, components: dict) -> tuple[list[str], list[str]]:
    """(problems that stop the build, warnings) for the components the sections name."""
    problems, warnings = [], []
    used = {s.get("component") for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component")}
    for key in sorted(used - set(components)):
        problems.append(f"a section names component {key!r}, which is not in components[]")
    for key, c in components.items():
        decision = c.get("decision")
        obj = (c.get("object") or "Form_Submission__c").replace(N, "")
        where = f"component {key}"
        if decision not in DECISIONS:
            problems.append(f"{where}: decision {decision!r} is not one of {', '.join(DECISIONS)}")
            continue
        if c.get("catalog_match") and not (c.get("asked") or {}).get("answer"):
            problems.append(f"{where}: the org has a matching component ({(c['catalog_match'] or {}).get('name')}) and the reuse question has no answer in asked")
        if decision == "update" and not c.get("name") and c.get("component_id"):
            c["name"] = c["component_id"]  # build-form-component's key for the same thing
        if decision == "update":
            problems += check_update(c, where)
        shape_problems, shape_warnings = check_shape(c, where)
        problems += shape_problems
        warnings += shape_warnings
        if decision in ("reuse", "extend", "update", "shared-new", "shared-record") and not c.get("name"):
            problems.append(f"{where}: a {decision} component needs the component's name")
        if decision == "extend" and not c.get("add_fields"):
            problems.append(f"{where}: extend needs add_fields, the fields the new version adds")
        if decision == "extend" and c.get("new_name") and str(c["new_name"]).replace(N, "") == str(c.get("name") or "").replace(N, ""):
            problems.append(f"{where}: extend builds a new version under its own new_name, never the original's name; changing the original is update")
        if decision in ("flow-section", "custom-lwc") and key in used:
            section = next(s for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component") == key)
            need = "FlowApiName__c" if decision == "flow-section" else "lwcComponentName__c"
            kind = "Flow" if decision == "flow-section" else "Lightning Web Component"
            if not section.get(need) or section.get("Component_Type__c") != kind:
                problems.append(f"{where}: its section needs Component_Type__c {kind!r} and {need}")
        on_other = obj != "Form_Submission__c" and decision in ("form-only", "extend", "shared-new", "shared-record")
        if edition == "paid" and on_other and not (c.get("form_template_mapping") or {}).get("fields") and decision != "extend":
            problems.append(f"{where}: a form on {obj} in a paid org needs form_template_mapping (each field's Form Submission field), "
                            "or nothing it collects reaches the submission")
        if edition == "free" and obj not in FREE_OBJECTS:
            warnings.append(f"{where}: the free edition shows forms only on {', '.join(sorted(FREE_OBJECTS))}; {obj} needs the paid edition")
    return problems, warnings


def check_page_header(page: dict) -> dict:
    head = page.get("header") or {}
    if not head:
        return {}
    return {k: v for k, v in {"Header_Title__c": head.get("title"), "Header_Subtitle__c": head.get("subtitle"),
                               "Header_Icon_Name__c": head.get("icon"), "Header_Style__c": head.get("style"),
                               "Show_Header__c": True if head.get("title") else None}.items() if v is not None}


# ---------------------------------------------------------------- the form-type switches
def template_settings(plan: dict) -> tuple[dict, list[str]]:
    """The form-type rules' template switches, for keys the plan does not set (form-design normally writes them all).

    Long (form_type "long"): stages mode, Save Progress, the review screen, and the answers PDF when a confirmation email
    is sent. The Save Progress email serves ordinary pages only: a stages template never sends it, and the stages
    'Email me a resume link' button has its own email, so it is never turned on in stages mode."""
    template = plan.get("template") or {}
    long_form = (plan.get("form_type") or "").lower() == "long" or (not plan.get("form_type") and _counted_long(plan))
    stages = template.get("Stages_Mode__c", long_form)
    save = template.get("Allow_Save_Progress__c", long_form)
    out = {"Stages_Mode__c": stages, "Allow_Save_Progress__c": save, "Enable_Review_Screen__c": long_form,
           "Send_Save_Progress_Email__c": bool(save) and not stages,
           "Attach_PDF_Confirmation__c": long_form and bool((plan.get("emails") or {}).get("confirmation"))}
    notes = []
    if stages and template.get("Send_Save_Progress_Email__c"):
        notes.append("Send_Save_Progress_Email__c was on in stages mode, where the package never sends it; it is built off. "
                     "The stages 'Email me a resume link' button sends Email_Template_Name_Resume_Form__c instead.")
    settings = {k: v for k, v in out.items() if k not in template}
    if stages:
        settings["Send_Save_Progress_Email__c"] = False
    return settings, notes


def _counted_long(plan: dict) -> bool:
    pages = plan.get("pages") or []
    minutes = sum(float(p.get("Estimated_Time__c") or 0) for p in pages)
    return len(pages) >= 3 and (str(plan.get("form_kind") or "").lower() in ("application", "grant") or minutes >= 10)


# ---------------------------------------------------------------- component JSON
class Build:
    """One build: the plan, the names it resolves, and what it learns from the org."""

    def __init__(self, plan: dict, names: Names, edition: str = "paid", mode: str = "metadata"):
        self.plan = plan
        self.names = names
        self.edition = edition
        self.mode = mode
        self.pending: set[str] = set()   # records mode: proposed new fields the org lacks, left out until deployed
        self.left_out: list[str] = []
        self.parked: list[dict] = []     # records mode: page, section and field rules that read a left-out field
        build = plan.setdefault("build", {})
        self.form_ids = build.setdefault("form_ids", {})
        self.family = build.get("prefix") or ""
        intake = plan.get("intake") or {}
        self.form = (plan.get("template") or {}).get("Name") or "Draft template"
        self.workstream = intake.get("workstream") or ""
        self.folder = build.get("folder") or self.workstream or self.form
        self.kinds: dict = {}        # {component name: ("record" | "metadata", Id)}
        self.designs: dict = {}      # {component name: stored JSON root} for extend
        self.not_built: list[str] = []
        self.untagged: set[str] = set()  # records mode: Section Tags the org's picklist lacks, left off until added
        self.labels_pending: dict = {}   # records mode: Form Labels (and translations) the org lacks, {label: [languages]}
        self.prefill_state: str | None = None  # the prefill flow in the org: active, inactive, missing or unknown
        self.picklist_gaps: list[dict] = []  # planned options the field lacks for the form's record type
        self.long_text = True        # the org has the long twins of label, help text and placeholder (fieldmap.LONG_TEXT)
        self.cut_text: list[str] = []  # wording an org without them cut at 255 characters

    # ---- fields and rules
    def logic_json(self, condition: dict, qualified_name: str, obj: str) -> dict:
        """A field rule inside a component's JSON: the field points at it with conditionalLogic__c and displayType SHOW."""
        entry = {"QualifiedApiName": qualified_name, "Label": condition["label"],
                 f"{STAR}conditionType__c": (condition.get("type") or "AND").upper(),
                 f"{STAR}conditions__r": [{"QualifiedApiName": f"{qualified_name}_C{i + 1}", f"{STAR}position__c": i + 1,
                                           f"{STAR}fieldName__c": star(self.names.field(obj, c["field"])), f"{STAR}operation__c": c.get("operator", "=="),
                                           **({f"{STAR}value__c": str(c["value"])} if c.get("operator", "==") not in NO_VALUE else {})}
                                          for i, c in enumerate(condition["conditions"])]}
        if condition.get("custom"):
            entry[f"{STAR}customLogic__c"] = condition["custom"]
        return entry

    def field_json(self, field: dict, position: int, obj: str, part: str, where: str = "") -> dict:
        # A unique QualifiedApiName per field: Form Builder keys each field's hover toolbar and editor by it.
        entry = {"QualifiedApiName": part, f"{STAR}fieldName__c": star(self.names.field(obj, field["field"])), f"{STAR}position__c": position,
                 f"{STAR}required__c": bool(field.get("required")), f"{STAR}readOnly__c": bool(field.get("read_only"))}
        for key, value in zip(("widthLarge__c", "widthMedium__c", "widthSmall__c"), field.get("widths") or [12, 12, 12]):
            entry[STAR + key] = str(value)
        cut: list = []
        for key, value in fieldmap.package_keys(field, self.long_text, cut).items():  # the one design-to-package table
            entry[STAR + key] = value
        self.cut_text += [f"{field.get('label') or field.get('field')} ({key.removesuffix('__c')})" for key in cut]
        if field.get("condition") and self.keeps_rule(field["condition"], "field", field_where(where, field)):
            entry[f"{STAR}conditionalLogic__c"] = part + "_L"
            entry[f"{STAR}displayType__c"] = "SHOW"
        return entry

    def kept(self, field: dict) -> bool:
        """False for a proposed new field that records mode leaves out until it is deployed."""
        return not (self.pending and bare_field(field.get("field")) in self.pending)

    def waits_for(self, condition: dict | None) -> list[str]:
        """The left-out fields a rule reads (records mode). The renderer cannot draw a section whose rule names a field
        the object does not have, so such a rule is never written."""
        if not self.pending or not condition:
            return []
        return [c.get("field") for c in condition.get("conditions") or [] if bare_field(c.get("field")) in self.pending]

    def keeps_rule(self, condition: dict, level: str, where: str) -> bool:
        """False for a page, section or field rule that reads a left-out field: the rule is parked (left_out, follow-ups)
        and what it governs is built without it, so it always shows until the field is deployed and the form rebuilt."""
        reads = self.waits_for(condition)
        if not reads:
            return True
        entry = {"level": level, "where": where, "label": condition.get("label"), "reads": reads}
        if entry not in self.parked:
            self.parked.append(entry)
            self.left_out.append(f"{where}: the {level} rule {condition.get('label')!r} reads {', '.join(reads)} (a new field, not in "
                                 "the org yet), so it is built without that rule and always shows until the field is deployed")
        return False

    def leave_out(self, where: str, field: dict) -> None:
        note = f"{where}: {field.get('field')} (a new field, not in the org yet)"
        if note not in self.left_out:
            self.left_out.append(note)

    def buildable(self, fields: list, where: str) -> list:
        out = []
        for f in fields or []:
            if f.get("control") in NOT_BUILT_CONTROLS:
                self.not_built.append(f"{where}: {f.get('label') or f.get('field')} is {NOT_BUILT_CONTROLS[f['control']]}")
                continue
            if not self.kept(f):
                self.leave_out(where, f)
                continue
            out.append(f)
        return out

    def inner_section_json(self, name: str, position: int, inner: dict, obj: str, where: str) -> dict:
        section_type = inner.get("type") or "inputSection"
        flags = {"inputSection": "isInputSection", "richTextSection": "isRichTextSection", "recordCardSection": "isRecordCardSection",
                 "bannerSection": "isBannerSection", "likertSection": "isLikertSection", "addressSection": "isAddressSection"}
        label = section_label(inner)
        fields = self.buildable(inner.get("fields"), where)
        # Section Title (title__c) is required in Form Builder and names the part in a few plain words; a visible inner
        # header only when the plan gives an explicit title.
        entry = {"QualifiedApiName": formnames.part_name(name, "FS", position, 0), "Label": label, f"{STAR}title__c": inner.get("title") or label or "",
                 f"{STAR}sectionType__c": section_type, f"{STAR}position__c": position, flags.get(section_type, "isInputSection"): True,
                 f"{STAR}fields__r": [self.field_json(f, i + 1, obj, formnames.part_name(name, "FF", i + 1, position), where)
                                      for i, f in enumerate(fields)]}
        for key, target in {"subtitle": "subtitle__c", "icon": "iconName__c", "frame": "sectionTheme__c", "header_style": "Header_Style__c",
                            "rich_text": "richText__c", "variant": "Message_Variant__c", "banner": "Banner__c", "record_card": "Record_Card__c",
                            "likert_mode": "Likert_Mode__c", "likert_scale": "Likert_Scale__c"}.items():
            value = inner.get(key)
            if value is not None:
                entry[STAR + target] = json.dumps(value) if isinstance(value, (dict, list)) else value
        entry[f"{STAR}showHeader__c"] = bool(inner.get("title"))
        # The server computes these when a saved form loads; a JSON form must carry them, or a text block loses its
        # gutter padding and sits 8px left of the fields under it.
        entry["richTextClass"] = "slds-container_fluid slds-p-horizontal_x-small"
        entry["sectionMarginClass"] = "slds-is-relative slds-m-top_none slds-m-bottom_none "
        entry["sectionVerticalPadding"] = "slds-container_fluid slds-p-horizontal_none slds-p-top_none slds-p-bottom_none"
        if inner.get("rich_text"):
            entry["showRichText"] = True
        return entry

    def component_json(self, section: dict, component: dict | None, name: str, kind: str = "Template section") -> tuple[str, dict]:
        """A section's form as component JSON: a page section's own JSON, or (kind "Shared component") the body of a
        record component. Field rules travel inside it either way; a paid org's map travels on its root."""
        component = component or {}
        obj = ns_object(component.get("object") or section.get("object") or "Form_Submission__c")
        where = section.get("Header_Title__c") or section.get("Title__c") or name
        parts = fieldmap.section_parts(section)
        inner_list = [self.inner_section_json(name, n + 1, inner, obj, where) for n, inner in enumerate(parts)]
        logic = []
        for n, inner in enumerate(parts):
            for i, f in enumerate(f for f in inner.get("fields") or [] if f.get("control") not in NOT_BUILT_CONTROLS and self.kept(f)):
                if f.get("condition") and self.keeps_rule(f["condition"], "field", field_where(where, f)):
                    logic.append(self.logic_json(f["condition"], formnames.part_name(name, "FF", i + 1, n + 1) + "_L", obj))
        title = plain(section.get("Header_Title__c") or section.get("Title__c")) or "Section"
        fields = [f for inner in parts for f in (inner.get("fields") or [])]
        subtitle = plain(section.get("Header_Subtitle__c"))
        shared = kind == "Shared component"
        if shared:
            used_by = component.get("used_by") or []
            description = component.get("description") or (f"{title}, shared by {len(used_by) or 'several'} forms" + (f": {subtitle}" if subtitle else "."))
            label = component.get("label") or title
            filed = fieldmap.filing(f"{self.folder}/Shared" if self.folder else "Shared", kind, fields, bool(section.get("condition")),
                                    bool(section.get("rich_text")), self.workstream)
        else:
            description = f"The {title} section of the {self.form} form" + (f": {subtitle}" if subtitle else ".")
            label = f"{self.form}: {title}"
            filed = fieldmap.filing(self.folder, kind, fields, bool(section.get("condition")), bool(section.get("rich_text")), self.workstream)
        root = {f"{STAR}ObjectApiName__c": star(obj), f"{STAR}type__c": "form", "QualifiedApiName": name, "Label": label[:80],
                f"{STAR}CategoryTag__c": "Component(s)" if shared else "Template(s)", f"{STAR}Description__c": description[:255],
                **{f"{STAR}{k}": v for k, v in filed.items()},
                f"{STAR}conditionalLogic__r": logic, f"{STAR}sections__r": inner_list}
        if obj != N + "Form_Submission__c":
            mapped = fieldmap.submission_map(component.get("form_template_mapping")) or component.get("submission_field_map")
            if mapped:
                root[f"{STAR}Submission_Field_Map__c"] = mapped if isinstance(mapped, str) else json.dumps(mapped)
                root[f"{STAR}Has_Submission_Map__c"] = True
        return obj, root

    def extend_json(self, component: dict, section: dict) -> dict:
        """The new version an extend answer builds: the named component as it is, plus add_fields from the section's design,
        under its own name. The original is never changed, so every template already using it keeps it."""
        original = component["name"]
        new_name = component.get("new_name") or formnames.form_name(self.family, component.get("key") or original, self.form_ids)
        component["built_name"] = new_name
        design = self.designs.get(original)
        if design is None:
            raise BuildError(f"component {component.get('key')}: {original} was not found in the org, or its design could not be read. "
                             "Open it in Form Builder, Export it, and save the JSON as components[].design_file, or answer form-only")
        obj = ns_object(component.get("object") or section.get("object") or "Form_Submission__c")
        by_name = {self.names.field(obj, f["field"]): f for f in section.get("fields") or []}
        added, labels = [], []
        for n, wanted in enumerate(component.get("add_fields") or [], 1):
            field = by_name.get(self.names.field(obj, wanted))
            if field is None:
                raise BuildError(f"component {component.get('key')}: add_fields names {wanted}, which is not one of its section's fields")
            if not self.kept(field):
                self.leave_out(f"component {component.get('key')}", field)
                continue
            added.append(self.field_json(field, n, obj, f"x{n}"))
            labels.append(field.get("label") or wanted)
        label = f"{design.get('Label') or original} with {', '.join(labels)}"
        description = (f"A version of {design.get('Label') or original} with {', '.join(labels)} added for the {self.form} form. "
                       "The original component is unchanged, so the templates that use it keep it.")
        root = recordcomponents.extend_design(design, new_name, added, label, description)
        mapping = component.get("form_template_mapping")
        if mapping:
            stored = next((v for k, v in root.items() if k.endswith("Submission_Field_Map__c")), None)
            merged = json.loads(stored) if stored else {"lookupField": "ALL", "fields": {}}
            extra = json.loads(fieldmap.submission_map(mapping))
            merged["fields"].update(extra["fields"])
            if mapping.get("apply_to") and not stored:
                merged["lookupField"] = extra["lookupField"]
            for k in [k for k in root if k.endswith("Submission_Field_Map__c") or k.endswith("Has_Submission_Map__c")]:
                root.pop(k)
            root[f"{STAR}Submission_Field_Map__c"] = json.dumps(merged)
            root[f"{STAR}Has_Submission_Map__c"] = True
        return {"name": new_name, "json": root, "kind": "extend", "original": original}

    # ---- sections
    def section_record(self, section: dict, components: dict, page_key: str, index: int) -> dict:
        record = record_fields(section, N + "Form_Template_Page_Section__c", self.names)
        record[N + "Position__c"] = index + 1
        record[N + "ExternalId__c"] = f"{page_key}:s{index + 1}"
        tag = section_tag(section)
        record.pop(N + "Section_Tag__c", None)
        if tag and tag not in self.untagged:
            # A prefill flow's Related Records step finds this section by its tag (Prefill From Mapped Record)
            resolved = self.names.record_key(SECTION, "Section_Tag__c")
            if resolved:
                record[resolved] = tag
        record.setdefault(N + "Component_Type__c", section.get("component_type") or "Field Set")
        if section.get("condition") and self.keeps_rule(section["condition"], "section", section_where(section)):
            record[N + "Conditional_Logic__c"] = self.rule_json(section["condition"])
        if record.get(N + "Header_Title__c"):
            record.setdefault(N + "Show_Header__c", True)  # it defaults to false, which hides a planned title
        if section.get("display_text"):
            record[N + "Component_Type__c"] = "Display Text"
            record[N + "Component_Section_Text__c"] = section["display_text"]
            record[N + "Message_Variant__c"] = section.get("variant") or "default"
            return record
        if record[N + "Component_Type__c"] in ("Flow", "Lightning Web Component"):
            return record  # the flow or LWC is built by its own skill; the section only names it
        component = components.get(section.get("component") or "") or {}
        decision = component.get("decision")
        shape = built_shape(component, self.mode)
        if decision == "form-only" and shape in ("record", "metadata"):
            # questions only this form asks, built as a one-off record or metadata component instead of JSON on the section
            obj = ns_object(component.get("object") or section.get("object") or "Form_Submission__c")
            name = placed_name(component, self.family, self.form_ids, self.mode)
            kind, component_id = self.kinds.get(name, (shape, None))
            record.update(recordcomponents.component_reference(name, kind, obj, component_id))
        elif decision in ("reuse", "update", "shared-new", "shared-record", "extend") and component.get("name"):
            # A reused or updated component is only referenced, never copied: by its plain name when it is metadata, as
            # <Name>_v0 with its Id when it is a record component. The org says which; without one (a dry run), the
            # catalog's shape the plan carries does
            obj = ns_object(component.get("object") or "Form_Submission__c")
            name = placed_name(component, self.family, self.form_ids, self.mode)
            unread = shape if decision in OWNED else (shape if shape in ("record", "metadata") else "metadata")
            kind, component_id = self.kinds.get(name, (unread, None))
            record.update(recordcomponents.component_reference(name, kind, obj, component_id))
        elif section.get("fields") or section.get("inner_sections") or section.get("rich_text"):
            # A text-only section still needs its own form, or the package fills in a default form
            key = component.get("key") or section.get("component") or f"s{index + 1}"
            obj, root = self.component_json(section, component, formnames.form_name(self.family, key, self.form_ids))
            record[N + "FormConfigJSON__c"] = json.dumps({"formSelectionMode": "custom", "object": obj, "formJsonConfig": json.dumps(root)})
        return record

    def rule_json(self, condition: dict, default_object: str = "Form_Submission__c") -> str:
        """A page, section or payment rule, in the shape the package evaluates."""
        obj = ns_object(condition.get("object") or default_object)
        return json.dumps({
            "objectApiName": obj,
            "ruleMode": "hideWhen" if condition.get("mode") == "hideWhen" else "showWhen",
            "conditionType": (condition.get("type") or "AND").upper(),
            **({"customLogic": condition["custom"]} if condition.get("custom") else {}),
            "conditions": [{"fieldApiName": self.names.field(obj, c["field"]), "operator": c.get("operator", "=="),
                            "value": c.get("value"), "position": i + 1} for i, c in enumerate(condition.get("conditions") or [])],
        })


def section_where(section: dict) -> str:
    return f"section {section.get('Header_Title__c') or section.get('Title__c') or section.get('component')}"


def field_where(where: str, field: dict) -> str:
    return f"{where}, field {field.get('label') or field.get('field')}"


def reads_any(condition: dict | None, fields) -> bool:
    return bool(condition) and any(bare_field(c.get("field")) in fields for c in condition.get("conditions") or [])


def section_label(inner: dict) -> str | None:
    """A section's Label is its title, cut at a word boundary to the stored limit."""
    text = (inner.get("label") or plain(inner.get("title"))).strip()
    if len(text) <= LABEL_LIMIT:
        return text or None
    cut = text[:LABEL_LIMIT + 1].rsplit(" ", 1)[0]
    return cut[:LABEL_LIMIT].rstrip(" ,;:-")


# ---------------------------------------------------------------- project config
def find_config(plan_path: pathlib.Path | None, explicit: str | None) -> dict:
    if explicit:
        return json.loads(pathlib.Path(explicit).read_text())
    folder = plan_path.resolve().parent if plan_path else pathlib.Path.cwd()
    for candidate in [folder, *folder.parents]:
        path = candidate / "flow-tool-kit.json"
        if path.exists():
            return json.loads(path.read_text())
    return {}


def org_settings(plan: dict, config: dict) -> dict:
    """The org's answers from ftk-start: edition, audiences and brand kit choice. The plan's intake.edition wins."""
    orgs = config.get("orgs") or {}
    org_id = (plan.get("intake") or {}).get("org_id")
    entry = orgs.get(org_id) if org_id in orgs else (next(iter(orgs.values())) if len(orgs) == 1 else {})
    return {"edition": (plan.get("intake") or {}).get("edition") or entry.get("edition") or "paid",
            "audiences": entry.get("audiences") or [], "brand_kit": (entry.get("brand_kit") or {}).get("choice"),
            "org_name": entry.get("name"), "known": bool(entry)}


# ---------------------------------------------------------------- prefill
def section_tag(section: dict) -> str | None:
    """The Section Tag a prefill flow finds this section by: the plan's section_tag (or the field itself)."""
    tag = section.get("section_tag") or section.get("Section_Tag__c")
    return str(tag).strip() if tag else None


def prefill_flow(plan: dict) -> str | None:
    """The template's prefill flow: prefill.flow, unless the plan sets Prefill_Flow_Api_Name__c on the template itself."""
    template = plan.get("template") or {}
    named = template.get("Prefill_Flow_Api_Name__c") or (plan.get("prefill") or {}).get("flow")
    return str(named).strip() if named else None


def check_prefill(plan: dict) -> tuple[list[str], list[str]]:
    """(problems, warnings) for the prefill flow and the Section Tags: a flow API name, each tag once in the template."""
    problems, warnings = [], []
    prefill = plan.get("prefill")
    if prefill is not None and not isinstance(prefill, dict):
        return ["prefill must be an object: {\"flow\": \"<flow API name>\"}"], warnings
    flow = prefill_flow(plan)
    if flow and flow != "Bypass" and not FLOW_API_NAME.match(flow):
        problems.append(f"prefill flow {flow!r} is not a flow API name (Letters_Digits_Underscores, a packaged flow as Namespace__Name)")
    seen: dict = {}
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            tag = section_tag(section)
            if not tag:
                continue
            where = f"page {page.get('Page_Label__c')}, section {section.get('Title__c') or section.get('Header_Title__c') or section.get('component')}"
            if len(tag) > 255:
                problems.append(f"{where}: section_tag is over 255 characters")
            if tag in seen:
                problems.append(f"{where}: section_tag {tag!r} is already on {seen[tag]}; a Section Tag is unique within the Form Template")
            seen.setdefault(tag, where)
    if seen and (not flow or flow == "Bypass"):
        warnings.append("Sections carry Section Tags (" + ", ".join(seen) + ") but the plan names no prefill flow (prefill.flow); the tags "
                        "do nothing until a prefill flow's Related Records step uses them")
    return problems, warnings


def section_tags(plan: dict) -> list[str]:
    return list(dict.fromkeys(t for p in plan.get("pages") or [] for s in p.get("sections") or [] for t in [section_tag(s)] if t))


def prefill_flow_state(org, name: str) -> str:
    """active, inactive, missing, or unknown (the user cannot read flow definitions)."""
    if name == "Bypass":
        return "active"
    namespace, _, bare = name.rpartition("__") if "__" in name else ("", "", name)
    where = f"ApiName = '{bare}'" + (f" AND NamespacePrefix = '{namespace}'" if namespace else "")
    try:
        rows = org.query(f"SELECT ApiName, IsActive FROM FlowDefinitionView WHERE {where}")
    except Exception:  # noqa: BLE001 - the step is listed either way
        return "unknown"
    if not rows:
        return "missing"
    return "active" if rows[0].get("IsActive") else "inactive"


# ---------------------------------------------------------------- the build
def written_fields(plan: dict, components: dict, names: Names):
    """(where, object, field) for every planned field the build writes: not a reused or updated component's (only
    referenced), not a Flow Section's or custom LWC's, and of an extend copy only its added fields."""
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            component = components.get(section.get("component") or "") or {}
            if component.get("decision") in ("reuse", "update", "flow-section", "custom-lwc") or section.get("Component_Type__c") in ("Flow", "Lightning Web Component"):
                continue
            design = component.get("section") if component.get("decision") == "shared-record" else section
            obj = ns_object(component.get("object") or (design or {}).get("object") or "Form_Submission__c")
            wanted = (design or {}).get("fields") or []
            if component.get("decision") == "extend":
                wanted = [f for f in wanted if names.field(obj, f["field"]) in {names.field(obj, a) for a in component.get("add_fields") or []}]
            for f in wanted:
                if f.get("control") not in NOT_BUILT_CONTROLS and f.get("field"):
                    yield section_where(section), obj, f


def check_picklists(org, choices: list, wanted: str | None, report: dict) -> list[dict]:
    """Each planned choice field's options against the org's values for the record type the form uses (picklists.py).
    A planned value the field lacks never shows: it is reported (warnings, setup, and a records-mode follow-up), never
    dropped in silence."""
    types, gaps, unread = {}, [], []
    for where, obj, field, f in choices:
        if obj not in types:
            types[obj] = picklists.record_type(org, obj, wanted if obj.endswith("Form_Submission__c") else None)
            if types[obj][2]:
                report["warnings"].append(types[obj][2])
        record_type_id, record_type_name, _ = types[obj]
        offered = picklists.org_options(org, obj, field, record_type_id)
        if offered is None:
            unread.append(f"{obj}.{field}")
            continue
        found = picklists.gap(picklists.planned(f), offered)
        if found:
            gaps.append({"where": where, "field": f"{obj}.{field}", "record_type": record_type_name, **found})
    report["picklists"] = {"record_types": {o: t[1] for o, t in types.items()}, "gaps": gaps, "unread": unread}
    for g in gaps:
        stored = "".join(f"; the org stores {v!r} as {g['stored_as'][v]!r}, so write {{\"value\": {g['stored_as'][v]!r}, \"label\": {v!r}}}"
                         for v in g["stored_as"])
        report["warnings"].append(f"{g['where']}: {g['field']} has no value {', '.join(map(repr, g['missing']))} for the {g['record_type']} "
                                  "record type, so the form does not offer it" +
                                  (" and, offering none of the planned values, shows every value the field has" if g["shows_all"] else "") + stored)
    if unread:
        report["warnings"].append("The picklist values of " + ", ".join(unread) + " could not be read, so their planned options were not "
                                  "checked; the round trip compares them with what the form shows")
    return gaps


def plan_problems(plan: dict, edition: str, mode: str = "metadata", pending: frozenset | set = frozenset()) -> tuple[dict, list[str], list[str], dict]:
    """Everything that can be checked without an org. Returns (components, problems, warnings, planned rule counts).
    pending: proposed new fields records mode leaves out, so their own rules, and every rule that reads one, are not counted."""
    components = {c["key"]: c for c in plan.get("components") or [] if c.get("key")}
    problems, warnings = check_components(plan, edition, components)
    if mode not in BUILD_MODES:
        problems.append(f"intake.build_mode {(plan.get('intake') or {}).get('build_mode')!r} is not one of {', '.join(BUILD_MODES)}")
    planned = {"page": 0, "section": 0, "field": 0}
    for page in plan.get("pages") or []:
        if page.get("condition"):
            planned["page"] += 0 if reads_any(page["condition"], pending) else 1
            problems += check_rule(page["condition"], f"page {page.get('Page_Label__c')}")
        for section in page.get("sections") or []:
            where = f"section {section.get('Header_Title__c') or section.get('Title__c') or section.get('component')}"
            if section.get("condition"):
                planned["section"] += 0 if reads_any(section["condition"], pending) else 1
                problems += check_rule(section["condition"], where)
            component = components.get(section.get("component") or "") or {}
            decision = component.get("decision")
            owned = decision == "shared-record"
            design = component.get("section") if owned else section
            if owned and not (design or {}).get("fields") and not (design or {}).get("inner_sections"):
                problems.append(f"component {component.get('key')}: a shared-record component needs its design in components[].section")
            if decision in ("flow-section", "custom-lwc") or section.get("Component_Type__c") in ("Flow", "Lightning Web Component"):
                continue
            for field in (design or {}).get("fields") or []:
                if not field.get("condition"):
                    continue
                if field.get("condition") == section.get("condition") and not owned:
                    field["condition"] = None  # the section rule already governs it
                    continue
                if decision in REFERENCED + ("extend",):
                    problems.append(f"{where}, field {field.get('field')}: a rule on one field of a component this build does not change "
                                    f"({decision}) cannot be built here; put it on the section, or answer form-only")
                    continue
                if field.get("control") in NOT_BUILT_CONTROLS:
                    continue
                problems += check_rule(field["condition"], f"{where}, field {field.get('field')}")
                if bare_field(field.get("field")) in pending or reads_any(field["condition"], pending):
                    continue  # the field, or the field its rule reads, is left out until it is deployed, and the rule with it
                if not (decision in OWNED and built_shape(component, mode) == "metadata"):
                    planned["field"] += 1  # a metadata component's rules are deployed by build-form-component, not counted here
            if decision not in REFERENCED + ("extend",) and not section.get("display_text"):
                for n, inner in enumerate(fieldmap.section_parts(design or {})):
                    problems += check_label(section_label(inner), f"{where}, inner section {n + 1} (give the section a Header_Title__c or label)")
                problems += fieldmap.address_problems(design or {}, where)
    payment = plan.get("payment") or {}
    if payment.get("condition"):
        problems += check_rule(payment["condition"], "payment condition")
    prefill_problems, prefill_warnings = check_prefill(plan)
    problems += prefill_problems + formlabels.problems(plan)
    warnings += prefill_warnings
    for i, p in enumerate(plan.get("url_parameters") or [], 1):
        if p.get("param") not in URL_PARAMETERS:
            problems.append(f"url_parameters[{i}]: {p.get('param')!r} is not a parameter the package reads ({', '.join(sorted(URL_PARAMETERS))})")
        if not p.get("field"):
            problems.append(f"url_parameters[{i}]: no Form Submission field")
    problems += check_copy(plan)
    return components, problems, warnings, planned


def header_choice(plan: dict) -> dict:
    template = plan.get("template") or {}
    banner = {**(template.get("banner") or {}), **(plan.get("banner") or {})}
    if plan.get("header") == "metadata" or template.get("FormQualifiedApiName_Header__c"):
        return {"mode": "named", "name": template.get("FormQualifiedApiName_Header__c"), "banner": banner}
    shape = header.shape_of(banner, len(plan.get("pages") or []))
    return {"mode": "packaged" if shape == "overlay" else "created", "shape": shape, "banner": banner}


def build(plan: dict, org=None, dry_run: bool = False, settings: dict | None = None, out_dir: pathlib.Path | None = None,
          on_template=None, refresh_headers: bool = False, missing_fields=None) -> dict:
    """missing_fields (records mode, a dry run): the plan's proposed new fields the org does not have yet, which chat
    found through its connector; they are left out of the forms and named as a follow-up."""
    settings = settings or {"edition": "paid", "audiences": [], "brand_kit": None}
    started = time.time()
    out_dir = out_dir or pathlib.Path.cwd()
    names = Names(None if dry_run else org)
    edition = settings.get("edition") or "paid"
    build_info = plan.setdefault("build", {})
    if not build_info.get("prefix"):
        build_info["prefix"] = formnames.default_family(settings.get("org_name") or (plan.get("emails") or {}).get("letterhead", {}).get("org"),
                                                        (plan.get("template") or {}).get("Name"))
    formnames.check_family(build_info["prefix"])
    mode = build_mode(plan)
    run = Build(plan, names, edition, mode)
    report = {"created": {}, "updated": {}, "deleted": {}, "warnings": [], "setup": [], "handoffs": [], "edition": edition, "build_mode": mode}
    if not settings.get("known"):
        report["warnings"].append(f"No project config for this org (flow-tool-kit.json): built as the {edition} edition with no brand kit. Run ftk-start first to record the org's answers.")

    components, problems, warnings, planned = plan_problems(plan, edition, mode)
    report["warnings"] += warnings
    proposed = {bare_field(f["field"]): f"{obj}.{f['field']}" for obj, f in newfields.new_fields(plan)}
    if missing_fields and mode == "records":
        wanted = {bare_field(str(x).split(".")[-1]) for x in missing_fields if str(x).strip()}
        problems += [f"--missing-fields names {x}, which the plan does not propose as a new field (new_field); a field the plan "
                     "uses as existing must be in the org" for x in sorted(wanted - set(proposed))]
        run.pending = wanted & set(proposed)
    elif missing_fields:
        report["warnings"].append("--missing-fields is for records mode; in metadata mode create the new fields first (newfields.py)")
    if problems:
        raise BuildError("The plan cannot be built exactly:\n  " + "\n  ".join(problems))
    if run.pending:
        planned = plan_problems(plan, edition, mode, run.pending)[3]
    report["rules"] = planned
    if mode == "records":
        mark_records_mode(components, run, report)

    template = plan.get("template") or {}
    template_fields = record_fields(template, N + "Form_Template__c", names)
    switches, notes = template_settings(plan)
    report["warnings"] += notes
    for key, value in switches.items():
        resolved = names.record_key(N + "Form_Template__c", key, optional=not value)
        if resolved and (key == "Send_Save_Progress_Email__c" or resolved not in template_fields):
            template_fields[resolved] = value  # the Save Progress email is forced off in stages mode
    template_fields.setdefault(N + "IsActive__c", True)  # an inactive draft previews as Not Available
    template_fields["Name"] = run.form
    key = build_info.get("key") or f"plan:{re.sub(r'[^a-z0-9]+', '-', run.form.lower()).strip('-')[:40]}"
    payment = plan.get("payment") or {}
    if payment:
        template_fields[N + "Payment_Required__c"] = bool(payment.get("required", True))
        template_fields[N + "Payment_Conditions__c"] = run.rule_json(payment["condition"]) if payment.get("condition") else None
    if plan.get("url_parameters"):
        template_fields[N + "URL_Parameter_Mapping__c"] = json.dumps([{"param": p["param"], "field": names.field(N + "Form_Submission__c", p["field"])}
                                                                       for p in plan["url_parameters"]])
    flow = prefill_flow(plan)
    if flow and "Prefill_Flow_Api_Name__c" not in template:
        resolved = names.record_key(N + "Form_Template__c", "Prefill_Flow_Api_Name__c")
        if resolved:
            template_fields[resolved] = flow
    if flow or section_tags(plan):
        report["prefill"] = {"flow": flow, "section_tags": section_tags(plan)}
    if formlabels.wanted(plan):
        report["form_labels"] = {"tokens": formlabels.tokens(plan), "defined": sorted(formlabels.entries(plan))}
    head = header_choice(plan)
    for field, value in header.template_fields(head["banner"], template, plan.get("assets")).items():
        resolved = names.record_key(N + "Form_Template__c", field, optional=True)
        if resolved:
            template_fields.setdefault(resolved, value)

    tile = (plan.get("assets") or {}).get("tile")
    if tile and "Form_Tile_Image__c" not in template:
        template_fields[N + "Form_Tile_Image__c"] = f"/file-asset/{tile}"

    # Record components this plan owns: promoted shared components and new shared ones (created when missing), extend copies
    def owned_specs() -> list[dict]:
        specs = []
        for c in components.values():
            if built_shape(c, mode) != "record":
                continue  # JSON goes on the section; a metadata component is written and deployed by build-form-component
            if c.get("decision") == "shared-record" or (c.get("decision") == "shared-new" and c["name"] not in run.kinds):
                design = c.get("section") or next((s for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component") == c["key"]), {})
                _, body = run.component_json(design, c, c["name"], "Shared component")
                specs.append({"name": c["name"], "json": body, "kind": "shared"})
            elif c.get("decision") == "form-only":
                design = next((s for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component") == c["key"]), {})
                name = owned_name(c, run.family, run.form_ids)
                _, body = run.component_json(design, c, name)
                specs.append({"name": name, "json": body, "kind": "one-off"})
        return specs

    def extend_specs() -> list[dict]:
        specs = []
        for c in components.values():
            if c.get("decision") == "extend" and built_shape(c, mode) == "record":
                section = next((s for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component") == c["key"]), {})
                specs.append(run.extend_json(c, section))
        return specs

    def records() -> tuple[list, list]:
        pages, sections = [], []
        for page_index, page in enumerate(plan.get("pages") or []):
            page_key = f"{key}:p{page_index + 1}"
            record = record_fields({**page, **check_page_header(page)}, N + "Form_Template_Page__c", names)
            record[N + "Position__c"] = page_index + 1
            record[N + "ExternalId__c"] = page_key
            if page.get("condition") and run.keeps_rule(page["condition"], "page", f"page {page.get('Page_Label__c')}"):
                record[N + "Conditional_Logic__c"] = run.rule_json(page["condition"])
            pages.append(record)
            for section_index, section in enumerate(page.get("sections") or []):
                sections.append((page_key, run.section_record(section, components, page_key, section_index)))
        return pages, sections

    if dry_run:
        for c in components.values():
            if c.get("decision") == "extend" and c.get("design_file"):
                run.designs[c["name"]] = json.loads((out_dir / c["design_file"]).read_text())
        specs = owned_specs()
        try:
            specs += extend_specs()
        except BuildError as error:
            report["warnings"].append(f"{error} (a dry run cannot read the org; the extend copy is made on a real build)")
        if head["mode"] == "created":
            name, body = header.component_json(head["shape"])
            specs.append({"name": name, "json": body, "kind": "header"})
            template_fields[N + "FormQualifiedApiName_Header__c"] = recordcomponents.versioned_name(name, "record")
        elif head["mode"] == "packaged":
            template_fields[N + "FormQualifiedApiName_Header__c"] = N + header.PACKAGED
        else:
            template_fields[N + "FormQualifiedApiName_Header__c"] = head["name"]
        report["header"] = {k: v for k, v in head.items() if k != "banner"}
        pages, sections = records()
        candidates, template_only = brandstyles.split(plan.get("styleTokens") or {}, settings.get("brand_kit"))
        report["styles"] = {"org_wide_candidates": candidates, "template_only": template_only,
                            "note": "A real build reads the org's Form Style defaults and adds only blank brand values there. Without an org, "
                                    "every value is on this template's Style Overrides, so the form looks right either way."}
        tokens = {**(plan.get("styleTokens") or {}), **json.loads(template_fields.get(N + "Style_Overrides__c") or "{}")}
        if tokens:
            template_fields[N + "Style_Overrides__c"] = json.dumps(tokens)
        for asset_key, field in (("logo", "Logo_Override__c"), ("logo_alt", "Logo_Alt_Text_Override__c")):
            if (plan.get("assets") or {}).get(asset_key):
                template_fields[N + field] = plan["assets"][asset_key]
        report["components_to_create"] = [{"name": s["name"], "kind": s["kind"], "json": s["json"]} for s in specs]
        report["not_built"] = run.not_built
        report["handoffs"] = handoffs(plan, components, run)
        if mode == "records":
            report["left_out"] = run.left_out
            report["follow_ups"] = follow_ups(plan, components, run, template_fields, report["handoffs"], proposed, dry_run=True)
        return {"template": template_fields, "pages": pages, "sections": [dict(s, page_key=k) for k, s in sections], **report}

    # ---- a real build: read the org, create components, then write the template
    info = org.query("SELECT Id, Name, NamespacePrefix, OrganizationType FROM Organization")[0]
    report["org"] = {"name": info.get("Name"), "namespace": info.get("NamespacePrefix") or None}
    template_object = N + "Form_Template__c"
    template_known = org.fields(template_object)
    if not template_known:
        raise BuildError("Form Template is not visible in this org: is Flow Tool Kit installed, and does this user have Form Builder (Administrator)?")
    has_logo_fields = N + "Logo__c" in template_known
    field_keys = org.fields(N + "Form_Component_Field__c")
    run.long_text = not field_keys or N + "customLabelLong__c" in field_keys  # unreadable: assume a current release
    brand_color_field = header.BRAND_COLOR_FIELD in template_known

    # Objects and fields: the renderer silently draws nothing for an unknown object or field, so every one is checked
    missing_objects, missing_fields, new_fields, choices = set(), [], [], []
    for where, obj, f in written_fields(plan, components, names):
        if not org.fields(obj):
            missing_objects.add(obj)
        elif not names.exists(obj, f["field"]):
            (new_fields if f.get("new_field") else missing_fields).append(f"{obj}.{f['field']}")
        elif picklists.is_choice(f):
            choices.append((where, obj, names.field(obj, f["field"]), f))
    if missing_objects:
        raise BuildError(f"Objects not in this org: {sorted(missing_objects)}. Package objects carry the FlowToolKit__ namespace; "
                         "the org's own keep their names (Form_Submission__c in the plan becomes FlowToolKit__Form_Submission__c).")
    if new_fields and mode == "records":
        # Records mode never deploys: the form leaves the new fields out until Claude Code creates them, then a rebuild adds them
        run.pending = {bare_field(name.split(".", 1)[1]) for name in new_fields}
        report["rules"] = planned = plan_problems(plan, edition, mode, run.pending)[3]
    elif new_fields:
        raise BuildError("The plan's new fields are not in the org yet: " + ", ".join(sorted(set(new_fields))) + ". Create them first: "
                         "python3 scripts/newfields.py <plan.json> --out <project-dir>, then deploy what it writes (Claude Code).")
    if missing_fields:
        raise BuildError("Fields the plan names are not in this org, or this user cannot see them: " + ", ".join(sorted(set(missing_fields))))
    run.picklist_gaps = check_picklists(org, choices, (plan.get("intake") or {}).get("record_type"), report)

    # Section Tags: a restricted picklist sharing the Data Conversion Tag(s) value set, so each tag must be a value there
    tags = section_tags(plan)
    if tags:
        allowed = org.picklist_values(SECTION, N + "Section_Tag__c")
        if allowed is None:
            raise BuildError("This org's Flow Tool Kit has no Section Tag on Form Template Page Section: upgrade it, or take section_tag out of the plan.")
        absent = [t for t in tags if t not in allowed]
        if absent and mode == "records":
            run.untagged = set(absent)
        elif absent:
            raise BuildError(f"Section Tags not in this org's Data Conversion Tag(s) values: {', '.join(absent)}. Section Tag is a restricted picklist "
                             "sharing that value set: add each value in Setup, Picklist Value Sets, Data Conversion Tag(s), then build again.")
    flow = prefill_flow(plan)
    if flow:
        run.prefill_state = prefill_flow_state(org, flow)
        report["prefill"]["flow_state"] = run.prefill_state

    # Form Labels: every {{$Label.X}} the copy uses must be a Form Label in the org, or one the plan defines to deploy
    try:
        lacking, undefined = formlabels.missing(org, plan)
    except BuildError as error:
        lacking, undefined = {}, []
        report["warnings"].append(f"The Form Labels could not be read ({str(error)[:160]}); check each token in the plan has a Form Label.")
    if undefined:
        raise BuildError("The plan's words use Form Labels that neither this org nor the plan's form_labels has: " + ", ".join(undefined) +
                         ". Add each to form_labels with its value (and translations), or take the token out; a missing label shows as nothing.")
    if lacking and mode == "records":
        run.labels_pending = lacking
    elif lacking:
        raise BuildError("Form Labels the plan defines are not in this org yet: " + ", ".join(
            f"{name} ({', '.join(langs)})" if langs else name for name, langs in sorted(lacking.items())) +
                         ". Create them first: python3 scripts/formlabels.py <plan.json> --out <project-dir>, then deploy what it writes (Claude Code).")

    # Assets: every one the plan names must be a public Asset File
    assets = plan.get("assets") or {}
    asset_names = sorted({assets[k] for k in ("banner", "tile", "logo") if assets.get(k)})
    if asset_names:
        found = {r["DeveloperName"] for r in org.query(f"SELECT DeveloperName FROM ContentAsset WHERE DeveloperName IN ({quoted(asset_names)})")}
        missing = [n for n in asset_names if n not in found]
        if missing:
            raise BuildError(f"Brand images not loaded as public Asset Files: {missing}. Load them first (brand-kit), or remove them from assets.")

    # Components: what each referenced name is, the designs extend copies, then create everything the plan owns
    referenced = [c["name"] for c in components.values() if c.get("decision") in ("reuse", "update", "shared-new", "extend") and c.get("name")]
    as_metadata = {c["key"]: owned_name(c, run.family, run.form_ids) for c in components.values()
                   if c.get("decision") in OWNED and built_shape(c, mode) == "metadata"}
    run.kinds.update(recordcomponents.component_kinds(org, referenced + list(as_metadata.values())))
    waiting = [f"{key} ({name})" for key, name in as_metadata.items() if run.kinds.get(name, ("",))[0] != "metadata"]
    if waiting:
        raise BuildError("The plan builds these as metadata components, which build-template does not deploy: " + ", ".join(waiting) +
                         ". build-form-component writes and deploys them (Claude Code): component.py cmt, sf project deploy start, "
                         "then Reset Form Cache. Build them first, or answer record or JSON for them, then run the build again.")
    for c in components.values():
        if c.get("decision") in ("reuse", "update") and c.get("name") not in run.kinds:
            raise BuildError(f"component {c['key']}: {c['name']} is not in this org's Form Components. Check the name (org-catalog), or answer form-only.")
        if c.get("decision") == "update":
            stored = recordcomponents.component_design(org, c["name"])
            if stored is not None:
                have = {str(v).replace(STAR, N).removeprefix(N) for sec in next((v for k, v in stored.items() if k.endswith("sections__r")), []) or []
                        for f in next((v for k, v in sec.items() if k.endswith("fields__r")), []) or []
                        for k, v in f.items() if k.endswith("fieldName__c")}
                section = next((x for p in plan.get("pages") or [] for x in p.get("sections") or [] if x.get("component") == c["key"]), {})
                waiting = [f["field"] for f in section.get("fields") or [] if f.get("field") and f["field"].replace(STAR, N).removeprefix(N) not in have]
                if waiting:
                    report["warnings"].append(f"component {c['key']}: {c['name']} does not have {', '.join(waiting)} yet. Run build-form-component's "
                                              "approved update first, then rebuild; until then the section shows the component as it is.")
        if c.get("decision") == "shared-new" and c.get("name") in run.kinds:
            section = next((s for p in plan.get("pages") or [] for s in p.get("sections") or [] if s.get("component") == c["key"]), {})
            if any(f.get("condition") for f in section.get("fields") or []):
                raise BuildError(f"component {c['key']}: {c['name']} already exists, so a rule on one of its fields cannot be added from this plan; "
                                 "put the rule on the section")
        if c.get("decision") == "extend":
            run.designs[c["name"]] = (json.loads((out_dir / c["design_file"]).read_text()) if c.get("design_file")
                                      else recordcomponents.component_design(org, c["name"]))
        if c.get("decision") == "reuse" and edition == "paid" and (c.get("object") or "Form_Submission__c").replace(N, "") != "Form_Submission__c":
            design = recordcomponents.component_design(org, c["name"]) or {}
            if not any(k.endswith("Submission_Field_Map__c") and v for k, v in design.items()):
                report["warnings"].append(f"component {c['key']}: {c['name']} has no Form Template Mapping, so nothing it collects reaches the submission. "
                                          "Map it in Form Builder (Form Template Mapping tab), or answer extend.")
    specs = owned_specs() + extend_specs()
    head_name = None
    # Flow Tool Kit 5.3 has no Logo fields on Form Template (5.4): the logo goes on the banner's own logo image setting,
    # in a header named after the logo. The packaged Overlay header cannot carry it, so an Overlay form gets its own too.
    # Before 5.3 no record component can be made, so the packaged header stays and the banner has no logo, as before.
    banner_logo = None
    if not has_logo_fields and assets.get("logo") and head["mode"] != "named" and recordcomponents.import_available(org):
        banner_logo = {"asset": assets["logo"], "alt": assets.get("logo_alt")}
    if banner_logo and head["mode"] == "packaged":
        head["mode"] = "created"
    if head["mode"] == "packaged":
        found = org.query(f"SELECT QualifiedApiName FROM {N}Form__mdt WHERE DeveloperName = '{header.PACKAGED}'")
        if found:
            head_name = found[0]["QualifiedApiName"]
        else:
            head["mode"] = "created"  # an older Flow Tool Kit with no packaged Banner header: create the Overlay one too
    if head["mode"] == "created":
        name, body = header.component_json(head["shape"], has_logo_fields, brand_color_field, banner_logo)
        existing = recordcomponents.component_kinds(org, [name]).get(name)
        if existing and existing[0] == "record" and not refresh_headers:
            run.kinds[name] = existing
            report["header_reused"] = True
        else:
            specs.append({"name": name, "json": body, "kind": "header"})
        head_name = recordcomponents.versioned_name(name, "record")
    elif head["mode"] == "named":
        rows = org.query(f"SELECT Form_Object__r.QualifiedApiName FROM {N}Form__mdt WHERE QualifiedApiName = '{head['name']}'")
        on = rows[0].get("Form_Object__r", {}).get("QualifiedApiName", "") if rows else ""
        if rows and not on.endswith("Form_Template"):
            raise BuildError(f"Header {head['name']} is built on {on}, not Form Template: the Header/Footer tab lists only Form Template "
                             "forms and clears any other the first time someone opens it. Rebuild it on Form Template.")
        head_name = head["name"]
    template_fields[N + "FormQualifiedApiName_Header__c"] = head_name
    report["header"] = {"mode": head["mode"], "shape": head.get("shape"), "component": head_name}
    brand = (plan.get("style") or {}).get("brand") or (plan.get("styleTokens") or {}).get("--ftk-color-primary")
    if brand_color_field and brand:
        template_fields.setdefault(header.BRAND_COLOR_FIELD, brand)

    if specs and not recordcomponents.import_available(org):
        # Flow Tool Kit before 5.3 cannot create record components. The header is a nicety the template can live without;
        # a shared or extended component is the design itself, so that stops the build.
        if any(s["kind"] != "header" for s in specs):
            raise BuildError("This org's Flow Tool Kit cannot create record components (FormComponentImport arrived in 5.3): "
                             f"{', '.join(s['name'] for s in specs if s['kind'] != 'header')}. Upgrade Flow Tool Kit, or answer form-only for those sections.")
        specs = []
        template_fields.pop(N + "FormQualifiedApiName_Header__c", None)
        report["header"] = {"mode": "org default", "shape": head.get("shape"), "component": None}
        report["warnings"].append(f"This org's Flow Tool Kit cannot create the {head.get('shape')} Banner header (record components arrived in 5.3), "
                                  "so the template keeps the header the org gives new templates. Upgrade Flow Tool Kit and rebuild for the planned banner.")
    if specs:
        try:
            created = recordcomponents.create_components(org, specs, "" if info.get("NamespacePrefix") == "FlowToolKit" else "FlowToolKit.")
        except RuntimeError as error:
            raise BuildError(str(error))
        for name, row in created.items():
            run.kinds[name] = ("record", row["id"])
        report["components"] = {name: {"id": row["id"], "rules": row["rules"], "kind": next(s["kind"] for s in specs if s["name"] == name)}
                                for name, row in created.items()}

    logo_on_banner = bool(banner_logo and head["mode"] == "created" and template_fields.get(N + "FormQualifiedApiName_Header__c"))
    if logo_on_banner:
        report["header"]["logo"] = "on the banner"
        report["warnings"].append(f"This org's Flow Tool Kit predates the Logo fields on Form Template (5.4), so the logo is set on the banner "
                                  f"header itself ({head_name}, shared by every template with this logo). After upgrading, rebuild: the "
                                  "template then takes its Logo Override or the org Default Logo.")
    elif not has_logo_fields:
        report["warnings"].append("This org's Flow Tool Kit predates the Logo fields: the banner shows no logo until Flow Tool Kit is upgraded.")
    overrides, logo_fields = brandstyles.apply(org, plan.get("styleTokens") or {}, {"logo": assets.get("logo"), "logoAlt": assets.get("logo_alt")},
                                               settings.get("brand_kit"), report, out_dir, has_logo_fields, logo_on_banner)
    if overrides:
        planned_overrides = json.loads(template_fields.get(N + "Style_Overrides__c") or "{}")
        template_fields[N + "Style_Overrides__c"] = json.dumps({**overrides, **planned_overrides})
    for field, value in logo_fields.items():
        template_fields[N + field] = value
    if names.unknown:
        raise BuildError("Plan keys that are not fields in this org: " + ", ".join(sorted(set(names.unknown))) +
                         ". A Flow Tool Kit field the org lacks means an older release: upgrade it, or take the key out of the plan.")
    if names.missing_optional:
        report["warnings"].append("This org's Flow Tool Kit has no " + ", ".join(sorted(set(names.missing_optional))) +
                                  " on Form Template, so the build left them out; upgrade Flow Tool Kit to use them.")
    pages, sections = records()
    if run.cut_text:
        report["warnings"].append("This org's Flow Tool Kit has no long label, help text or placeholder fields, so wording past 255 characters "
                                  "was cut: " + "; ".join(dict.fromkeys(run.cut_text)) + ". Upgrade Flow Tool Kit and rebuild for the whole text.")

    template_id = build_info.get("template_id")
    prefill_field = N + "Prefill_Template__c" if N + "Prefill_Template__c" in template_known else None
    found = org.query(f"SELECT Id{', ' + prefill_field if prefill_field else ''} FROM {template_object} WHERE Id = '{template_id}'") if template_id else []
    if template_id and not found:
        template_id = None
        # The template this plan built is gone: its Pre-fill Template, which nothing else uses, goes with it
        gone = build_info.pop("prefill_template_id", None)
        if gone and remove_prefill(org, gone):
            report["deleted"]["prefill_template"] = 1
    prefill_before = found[0].get(prefill_field) if found and prefill_field else None
    created_now, new_prefill = False, None
    try:
        if template_id:
            org.save("PATCH", [{"attributes": {"type": template_object}, "Id": template_id, **template_fields}])
            report["updated"]["template"] = 1
        else:
            template_id = org.save("POST", [{"attributes": {"type": template_object}, **template_fields}])[0]
            created_now = True
            report["created"]["template"] = 1
        if prefill_field and prefill_field not in template_fields:
            # The package gives a template with no Pre-fill Template a new one (a Form Submission) on every save
            prefill_after = (org.query(f"SELECT Id, {prefill_field} FROM {template_object} WHERE Id = '{template_id}'") or [{}])[0].get(prefill_field)
            if prefill_after and prefill_after != prefill_before:
                new_prefill = prefill_after
                report["created"]["prefill_template"] = 1
        write_pages_and_sections(org, template_id, pages, sections, report)
        report["rules_built"] = count_rules(org, template_id, report.get("components") or {}, run.kinds)
        if report["rules_built"] != planned:
            raise BuildError(f"Conditional rules in the org {report['rules_built']} differ from the plan {planned}")
    except BuildError as error:
        if created_now:
            org.delete([template_id])  # pages and sections go with it
            if new_prefill:
                remove_prefill(org, new_prefill)
            raise BuildError(f"{error}\nThe new template was deleted, with its Pre-fill Template, so no half-built template is left. "
                             "Fix the problem and run the build again.")
        raise BuildError(f"{error}\nThe template {template_id} may be partly rebuilt: fix the problem and run the build again; never patch it by hand.")
    if new_prefill:
        build_info["prefill_template_id"] = new_prefill
    if on_template:
        on_template(template_id, key)
    report["template_id"] = template_id
    if build_info.get("prefill_template_id"):
        report["prefill_template_id"] = build_info["prefill_template_id"]
    report["not_built"] = run.not_built
    report["record_components"] = sorted(name for name, (kind, _) in run.kinds.items() if kind == "record")
    report["setup"] = setup_steps(org, plan, template_fields, components, settings, report)
    report["handoffs"] = handoffs(plan, components, run)
    if run.pending:
        # The round trip reads this, so the fields and rules the build left out are reported as such, never as mismatches
        build_info["left_out"] = {"fields": sorted(run.pending), "rules": run.parked}
    else:
        build_info.pop("left_out", None)
    if mode == "records":
        report["left_out"] = run.left_out
        report["follow_ups"] = follow_ups(plan, components, run, template_fields, report["handoffs"], proposed)
    else:
        for c in components.values():
            c.pop("built_shape", None)  # built in its planned shape now; convert-to-metadata has nothing left to convert
    report["seconds"] = round(time.time() - started, 1)
    return report


def remove_prefill(org, prefill_id: str) -> bool:
    """Delete the Pre-fill Template the package made with a template this build created, once that template is gone.
    Only while it is still a Pre-fill Template and no template or section names it (templates can share one)."""
    submission = N + "Form_Submission__c"
    if not re.fullmatch(r"[a-zA-Z0-9]{15,18}", prefill_id or ""):
        return False
    if not org.query(f"SELECT Id FROM {submission} WHERE Id = '{prefill_id}' AND {N}IsPrefillTemplate__c = true"):
        return False
    for obj in (N + "Form_Template__c", N + "Form_Template_Page_Section__c"):
        if N + "Prefill_Template__c" in org.fields(obj) and org.query(f"SELECT Id FROM {obj} WHERE {N}Prefill_Template__c = '{prefill_id}' LIMIT 1"):
            return False
    org.delete([prefill_id])
    return True


def write_pages_and_sections(org, template_id: str, pages: list, sections: list, report: dict) -> None:
    page_object, section_object = N + "Form_Template_Page__c", N + "Form_Template_Page_Section__c"
    existing_pages = org.query(f"SELECT Id, {N}ExternalId__c FROM {page_object} WHERE {N}Form_Template__c = '{template_id}'")
    page_ids = {p.get(N + "ExternalId__c"): p["Id"] for p in existing_pages if p.get(N + "ExternalId__c")}
    to_update = [{"attributes": {"type": page_object}, "Id": page_ids[p[N + "ExternalId__c"]], **p} for p in pages if p[N + "ExternalId__c"] in page_ids]
    to_insert = [{"attributes": {"type": page_object}, N + "Form_Template__c": template_id, **p} for p in pages if p[N + "ExternalId__c"] not in page_ids]
    if to_update:
        org.save("PATCH", to_update)
    if to_insert:
        for record, new_id in zip(to_insert, org.save("POST", to_insert)):
            page_ids[record[N + "ExternalId__c"]] = new_id
    report["updated"]["pages"], report["created"]["pages"] = len(to_update), len(to_insert)
    # Every section is recreated: the package overwrites a section's ExternalId__c on every save. This also clears the
    # default section the package adds to each new page.
    existing_sections = org.query(f"SELECT Id FROM {section_object} WHERE {N}Form_Template_Page__r.{N}Form_Template__c = '{template_id}'")
    if existing_sections:
        org.delete([s["Id"] for s in existing_sections])
    inserts = [{"attributes": {"type": section_object}, **record, N + "Form_Template_Page__c": page_ids[page_key]} for page_key, record in sections]
    if inserts:
        org.save("POST", inserts)
    report["deleted"]["sections"], report["created"]["sections"] = len(existing_sections), len(inserts)
    wanted = {p[N + "ExternalId__c"] for p in pages}
    # The default page a new template gets has no ExternalId__c, so it goes here too
    stale = [p["Id"] for p in existing_pages if p.get(N + "ExternalId__c") not in wanted]
    if stale:
        org.delete(stale)
    report["deleted"]["pages"] = len(stale)
    counts: dict = {}
    for row in org.query(f"SELECT {N}Form_Template_Page__c FROM {section_object} WHERE {N}Form_Template_Page__r.{N}Form_Template__c = '{template_id}'"):
        counts[row[N + "Form_Template_Page__c"]] = counts.get(row[N + "Form_Template_Page__c"], 0) + 1
    planned: dict = {}
    for page_key, _ in sections:
        planned[page_ids[page_key]] = planned.get(page_ids[page_key], 0) + 1
    differs = {pid: counts.get(pid, 0) - planned.get(pid, 0) for pid in set(counts) | set(planned) if counts.get(pid, 0) != planned.get(pid, 0)}
    if differs:
        raise BuildError(f"Section counts in the org differ from the plan on pages {differs}")


def count_rules(org, template_id: str, created: dict, kinds: dict) -> dict:
    built = {"page": 0, "section": 0, "field": 0}
    for row in org.query(f"SELECT {N}Conditional_Logic__c FROM {N}Form_Template_Page__c WHERE {N}Form_Template__c = '{template_id}'"):
        built["page"] += 1 if row.get(N + "Conditional_Logic__c") else 0
    for row in org.query(f"SELECT {N}Conditional_Logic__c, {N}FormConfigJSON__c FROM {N}Form_Template_Page_Section__c "
                         f"WHERE {N}Form_Template_Page__r.{N}Form_Template__c = '{template_id}'"):
        built["section"] += 1 if row.get(N + "Conditional_Logic__c") else 0
        config = json.loads(row.get(N + "FormConfigJSON__c") or "{}")
        inner = json.loads(config.get("formJsonConfig") or "{}")
        built["field"] += len(inner.get(f"{STAR}conditionalLogic__r") or [])
        if config.get("formSelectionMode") == "component":
            name = (config.get("formQualifiedApiName") or "").removesuffix("_v0")
            # A shared component the plan owns carries the plan's field rules; an extend copy's rules are the original's own
            built["field"] += (created.get(name) or {}).get("rules", 0) if (created.get(name) or {}).get("kind") in ("shared", "one-off") else 0
    return built


def mark_records_mode(components: dict, run, report: dict) -> None:
    """Records mode: each component the plan marks metadata is built as a record component instead. Say so, and record
    it on the plan (components[].built_shape) and in the report (convert_later), so convert-to-metadata can convert it
    once the project moves to metadata."""
    report["convert_later"] = []
    for c in components.values():
        if built_shape(c, run.mode) != shape_of(c):
            name = placed_name(c, run.family, run.form_ids, run.mode)
            c["built_shape"] = "record"
            report["convert_later"].append({"key": c.get("key"), "component": name, "decision": c.get("decision"),
                                            "planned_shape": shape_of(c), "built_shape": "record"})
            report["warnings"].append(f"component {c.get('key')}: planned as a metadata component; records mode builds {name} as a record "
                                      "component instead (convert-to-metadata converts it later)")


def follow_ups(plan: dict, components: dict, run, template_fields: dict, handoff_list: list, proposed: dict, dry_run: bool = False) -> list[dict]:
    """Records mode: what cannot be done without a metadata deploy, named for Claude Code instead of failing the build.
    Nothing here is done by this build."""
    out = []
    if run.pending:
        out.append({"follow_up": "new fields", "names": sorted(proposed.get(f, f) for f in run.pending), "skill": "build-template (scripts/newfields.py)",
                    "what": "Create the fields and their permission set, deploy them, then rebuild: until then the form leaves them out (left_out), "
                            "and any rule that reads them waits for them."})
        if run.parked:
            out.append({"follow_up": "rules waiting for new fields", "skill": "build-template (rebuild once the new fields are deployed)",
                        "names": [f"{p['where']}: {p['label']} (reads {', '.join(p['reads'])})" for p in run.parked],
                        "what": "Each rule reads a new field the form leaves out. A rule on a field the object does not have stops its "
                                "section from drawing, so the build left the rule out: until the rebuild, what it shows or hides always shows."})
    elif dry_run and proposed:
        out.append({"follow_up": "new fields", "names": sorted(proposed.values()), "skill": "build-template (scripts/newfields.py)",
                    "what": "The plan proposes these fields. Check each in the org (FieldDefinition through the connector); run the dry run again "
                            "with --missing-fields naming the ones it lacks, so the form leaves them out, and create them from Claude Code."})
    if run.picklist_gaps:
        out.append({"follow_up": "picklist values", "skill": "Setup, Object Manager: the field's values, then the record type's picklist values",
                    "names": [f"{g['field']}: {', '.join(g['missing'])} ({g['record_type']} record type)" for g in run.picklist_gaps],
                    "what": "The form offers only the planned values the field has for that record type, so these do not show until they "
                            "are added (a picklist value is metadata). The form already lists them, so no rebuild is needed."})
    elif dry_run:
        planned_choices = sorted({f"{obj}.{f['field']}" for _, obj, f in written_fields(plan, components, run.names)
                                  if picklists.is_choice(f) and run.kept(f)})
        if planned_choices:
            out.append({"follow_up": "picklist values", "skill": "the Salesforce connector (picklist values by record type)", "names": planned_choices,
                        "what": "Check each planned option is a value of the field for the record type the form uses (on Form Submission, "
                                "the one named Default): a value the field lacks never shows. List each missing one to add in Setup."})
    by_name = {c.get("name"): c for c in components.values() if c.get("name")}

    def kind(name: str) -> str | None:  # what the org says, else the catalog's shape the plan carries
        return (run.kinds.get(name) or (None,))[0] or (by_name.get(name) or {}).get("shape")

    updates = [h["component"] for h in handoff_list if h.get("action") == "update" and kind(h["component"]) == "metadata"]
    if updates:
        out.append({"follow_up": "update a shared metadata component", "names": updates, "skill": "build-form-component",
                    "what": "The approved update changes a metadata component, which is a deploy; until then the section shows it as it is."})
    for skill, label in (("build-flow-section", "Flow Sections"), ("build-custom-lwc", "custom LWCs")):
        names = [h.get("flow") or h.get("component") for h in handoff_list if h.get("skill") == skill]
        if names:
            out.append({"follow_up": label, "names": names, "skill": skill,
                        "what": f"The sections already name them; the {label} themselves are metadata, built and deployed from Claude Code."})
    emails = next((h["emails"] for h in handoff_list if h.get("skill") == "build-email-templates"), None)
    if emails:
        out.append({"follow_up": "email templates", "names": sorted(set(emails.values())), "skill": "build-email-templates",
                    "what": "The template already names them; until they exist the package sends its built-in emails. Build them from "
                            "Claude Code when they need a deploy."})
    labels = run.labels_pending or ({name: [] for name in formlabels.wanted(plan)} if dry_run else {})
    if labels:
        out.append({"follow_up": "Form Labels", "names": [f"{name} ({', '.join(langs)})" if langs else name for name, langs in sorted(labels.items())],
                    "skill": "build-template (scripts/formlabels.py)",
                    "what": ("Check each in the org (Form Label by API name, and its translations); " if dry_run and not run.labels_pending else "") +
                            "Form Labels and their translations are custom metadata, written by formlabels.py and deployed from Claude Code. "
                            "Until then the words show nothing where the token is."})
    if run.untagged:
        out.append({"follow_up": "Section Tags", "names": sorted(run.untagged), "skill": "Setup, Picklist Value Sets, Data Conversion Tag(s)",
                    "what": "Section Tag is a restricted picklist: add each value, then rebuild. Until then those sections carry no tag, so the "
                            "prefill flow's Related Records step finds no section for them."})
    if run.prefill_state in ("missing", "inactive"):
        out.append({"follow_up": "prefill flow", "names": [prefill_flow(plan)], "skill": "Flow Builder (Claude Code for a deploy)",
                    "what": "The template names it; build and activate it before the form is opened, or the form shows that its default answers "
                            "could not be loaded."})
    if template_fields.get(N + "Attach_PDF_Confirmation__c"):
        out.append({"follow_up": "answers PDF running user", "names": ["Form Submission Convert trigger"], "skill": "build-template (scripts/runninguser.py)",
                    "what": "The Platform Event Subscriber Config is metadata; until it is deployed the confirmation email goes without the PDF."})
    return out


def handoffs(plan: dict, components: dict, run=None) -> list[dict]:
    """What other skills do: a metadata component the plan names and the org does not have yet, and an approved update to
    a shared component, first (build-form-component makes them, before the template is walked), then Flow Sections,
    custom LWCs, then the emails."""
    out = []
    for c in components.values():
        if run is not None and c.get("decision") in OWNED and built_shape(c, run.mode) == "metadata":
            name = owned_name(c, run.family, run.form_ids)
            if run.kinds.get(name, ("",))[0] != "metadata":
                out.append({"skill": "build-form-component", "action": "build metadata", "component": name, "key": c.get("key"),
                            "decision": c.get("decision"), "extends": c.get("name") if c.get("decision") == "extend" else None})
    out += [{"skill": "build-form-component", "action": "update", "component": c["name"], "changes": c.get("changes"),
             "shared_change_reason": c.get("shared_change_reason"), "reaches": (c.get("usage") or {}).get("consumers") or []}
            for c in components.values() if c.get("decision") == "update" and c.get("name")]
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            if section.get("Component_Type__c") == "Flow":
                out.append({"skill": "build-flow-section", "section": section.get("Title__c"), "flow": section.get("FlowApiName__c"),
                            "what": (components.get(section.get("component")) or {}).get("what_it_does")})
            elif section.get("Component_Type__c") == "Lightning Web Component":
                out.append({"skill": "build-custom-lwc", "section": section.get("Title__c"), "component": section.get("lwcComponentName__c"),
                            "what": (components.get(section.get("component")) or {}).get("what_it_does")})
    emails = {k: v.get("name") for k, v in (plan.get("emails") or {}).items() if isinstance(v, dict) and v.get("name") and k in ("confirmation", "saved", "resume")}
    if emails:
        out.append({"skill": "build-email-templates", "emails": emails})
    return out


def setup_steps(org, plan: dict, template_fields: dict, components: dict, settings: dict, report: dict) -> list[str]:
    """What the org needs, beyond the records, for this template to work end to end."""
    steps = []
    audiences = set(settings.get("audiences") or [])
    if template_fields.get(N + "Attach_PDF_Confirmation__c"):
        configured = []
        try:
            configured = org.tooling_query("SELECT DeveloperName, UserId FROM PlatformEventSubscriberConfig")
        except Exception:  # noqa: BLE001 - the Tooling object is missing on some editions; the step is listed either way
            configured = []
        if not any("Form_Submission_Convert" in str(r.get("DeveloperName")) for r in configured):
            steps.append("Answers PDF: the confirmation runs as the Automated Process user, which cannot open the PDF page, so the email goes "
                         "without the PDF until the Form Submission Convert trigger has a running user. Run scripts/runninguser.py "
                         "--org <org-alias> --user <an active system administrator's username>, deploy what it writes, then in Setup, "
                         "Platform Events, Form Submission Convert, Subscriptions, Manage: Suspend, then Resume.")
    if template_fields.get(N + "Send_Save_Progress_Email__c") or template_fields.get(N + "Stages_Mode__c"):
        steps.append("Save Progress and resume emails: set the template's web form address (Open Web Form or Change Web Form Address) or the org's "
                     "Default Web Form URL, and verify the org's Default Workflow User's email address; the emails are sent from it.")
    record_components = list(report.get("record_components") or [])
    if report.get("header", {}).get("mode") == "created":
        record_components.append(str(report["header"]["component"]).removesuffix("_v0"))
    if "guest" in audiences:
        if record_components:
            steps.append("Guests read record components only through a guest sharing rule on Form Component (Read, where Record Type is Record "
                         f"Component); without it the header or section is blank for guests. Used here: {', '.join(sorted(set(filter(None, record_components))))}. "
                         "flow-access-fix sets it up.")
        if template_fields.get(N + "Payment_Conditions__c"):
            fields = sorted({c["field"] for c in ((plan.get("payment") or {}).get("condition") or {}).get("conditions") or []})
            steps.append("Conditional payment: the guest permission set needs Read on Form Template's Payment Conditions and on every field the "
                         f"rule reads ({', '.join(fields)}); an unreadable rule blocks submission rather than waiving payment.")
        if plan.get("url_parameters"):
            steps.append("URL parameters: the guest needs Edit on every Form Submission field a parameter fills.")
    for p in plan.get("url_parameters") or []:
        steps += url_parameter_notes(org, p)
    flow = prefill_flow(plan)
    state = (report.get("prefill") or {}).get("flow_state")
    if flow and state != "active":
        steps.append(f"Prefill flow {flow}: " + ("not found among this org's flows" if state == "missing" else "not active" if state == "inactive"
                                                 else "could not be checked") + ". Build and activate it before the form is opened (it takes the "
                     "input record and returns prefillRecord, and prefillRelatedRecords for tagged sections); until then the form shows that its "
                     "default answers could not be loaded.")
    emails = [v.get("name") for k, v in (plan.get("emails") or {}).items() if isinstance(v, dict) and v.get("name") and k in ("confirmation", "saved", "resume")]
    if emails:
        found = {r["DeveloperName"] for r in org.query(f"SELECT DeveloperName FROM EmailTemplate WHERE DeveloperName IN ({quoted(emails)})")}
        missing = [e for e in emails if e not in found]
        if missing:
            steps.append(f"Email templates the template names but the org does not have yet: {', '.join(missing)}. build-email-templates builds them; "
                         "until then the package sends its built-in emails.")
    gaps = (report.get("picklists") or {}).get("gaps") or []
    if gaps:
        steps.append("Picklist values the plan offers but the org does not, so the form leaves them out: " +
                     "; ".join(f"{g['field']}: {', '.join(g['missing'])} ({g['record_type']} record type)" for g in gaps) +
                     ". Add each value to the field (Setup, Object Manager), then to that record type's picklist values. The form "
                     "already lists them, so no rebuild is needed.")
    steps.append("Reset Form Cache in Form Builder after any metadata change, then open Preview Form from the template record.")
    return steps


def url_parameter_notes(org, parameter: dict) -> list[str]:
    obj = N + "Form_Submission__c"
    try:
        rows = org.query(f"SELECT QualifiedApiName, DataType FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{obj}' "
                         f"AND QualifiedApiName = '{parameter['field'].replace(STAR, N)}'")
    except Exception:  # noqa: BLE001
        rows = []
    kind = (rows[0].get("DataType") if rows else "") or ""
    if kind.startswith("Time"):
        return [f"URL parameter {parameter['param']}: a Time field takes the 24-hour clock in the link ({parameter['param']}=9:30 or 14:05); "
                "9:30 PM or noon is skipped. Flow Tool Kit 5.3 or later."]
    if kind.startswith("Lookup") or kind == "Id":
        return [f"URL parameter {parameter['param']}: a 15-character record Id (what a Lightning email template's lookup merge writes) is "
                "turned into its 18-character form before the prefill flow sees it, on the Flow Tool Kit release that adds this; on an older "
                "org, put the 18-character Id in the link (CASESAFEID in a formula)."]
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a draft Form Template from plan.json")
    parser.add_argument("plan")
    parser.add_argument("--org", help="the org alias; the Salesforce CLI's default org when left out")
    parser.add_argument("--config", help="flow-tool-kit.json (default: found beside the plan or in a folder above it)")
    parser.add_argument("--dry-run", action="store_true", help="no org: print every record and component the build would write")
    parser.add_argument("--out", help="write the full report (with --dry-run, every record) to this file")
    parser.add_argument("--refresh-headers", action="store_true", help="rewrite the org's Compact or Split header component from the current settings")
    parser.add_argument("--missing-fields", help="records mode, with --dry-run: comma-separated proposed new fields the org lacks (left out until deployed)")
    args = parser.parse_args(argv)
    path = pathlib.Path(args.plan)
    plan = json.loads(path.read_text())
    settings = org_settings(plan, find_config(path, args.config))
    org = None if args.dry_run else Org(args.org)

    def remember(template_id: str, key: str) -> None:
        plan.setdefault("build", {}).update({"org": args.org or "default", "template_id": template_id, "key": key})
        path.write_text(json.dumps(plan, indent=1, ensure_ascii=False))

    missing = [x.strip() for x in (args.missing_fields or "").split(",") if x.strip()]
    report = build(plan, org, args.dry_run, settings, path.parent, remember, args.refresh_headers, missing)
    if not args.dry_run:
        path.write_text(json.dumps(plan, indent=1, ensure_ascii=False))  # keeps build.prefix and form_ids, so a rebuild keeps every name
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        pathlib.Path(args.out).write_text(text)
    print(text if args.out is None and len(text) < 6000 else json.dumps({k: v for k, v in report.items() if k not in ("template", "pages", "sections", "components_to_create")}, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as error:
        sys.exit(f"build-template: {error}")
