#!/usr/bin/env python3
"""The round trip: read the built template back from the org and compare it with the plan, field by field.

    python3 roundtrip.py <plan.json> [--org <org-alias>]

A build is not done until this prints 0 mismatches. It reads the template, its pages and sections, each section's own
form JSON, and the record components the sections point at, and lists every difference from plan.json: the template's
form-type switches and header, each page's label, description, button and rule, each section's title, header, frame,
rule and form, and inside each form every field's name, order, widths, required, label, hidden label, consent wording
and rule, every address the package could not draw or whose row and parts disagree on required (shared lib addressparts.py) and each address's header, and each choice field's options as
the form draws them (the org's values for the form's record type, the field's option subset and labels) against the
plan's: missing, extra or relabelled values. It also catches an edit someone made in Form Builder after the build, which the next rebuild would erase.
Writes roundtrip.md beside the plan and exits 1 on any mismatch. Fields the build reports as not built (a repeater)
are listed as known gaps, not mismatches. So are what a records-mode build left out until it is deployed (the plan's
build.left_out, which the build writes): the proposed new fields, and every rule that reads one. And so are planned
options the org does not have for the form's record type (the build's picklist-values warning, setup step and
follow-up): the form already lists them, so each shows once it is added in Setup, with no rebuild.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import buildtemplate as bt  # noqa: E402
import fieldmap  # noqa: E402
import picklists  # noqa: E402
from sforg import BuildError, Org, quoted  # noqa: E402

addressparts = fieldmap.addressparts  # the address rule (shared lib), loaded by fieldmap

N = "FlowToolKit__"
SWITCHES = ("Stages_Mode__c", "Allow_Save_Progress__c", "Send_Save_Progress_Email__c", "Enable_Review_Screen__c", "Attach_PDF_Confirmation__c",
            "Buttons_Position__c", "Button_Alignment__c", "Hide_Stage_Indicator__c", "Submit_Button_Label__c")


def bare(key: str) -> str:
    return key.replace("*__", "").replace(N, "")


def get(row: dict, key: str, default=None):
    for k, v in (row or {}).items():
        if bare(k) == key:
            return v
    return default


def field_id(name: str | None) -> str:
    return bare(name or "").lower()


def text(value) -> str:
    return re.sub(r"\s+", " ", bt.plain(str(value or ""))).strip()


def read_choices(org, plan: dict) -> dict:
    """{(object, field id): (record type name, [(value, label)])}: the org's values, for the record type the form uses,
    of every planned choice field the build writes. A field whose values cannot be read is left out (and noted)."""
    out, types = {}, {}
    names = bt.Names(org)
    pending, _ = left_out(plan)
    components = {c.get("key"): c for c in plan.get("components") or []}
    wanted = (plan.get("intake") or {}).get("record_type")
    for _, obj, f in bt.written_fields(plan, components, names):
        if not picklists.is_choice(f) or bt.bare_field(f.get("field")) in pending:
            continue
        if obj not in types:
            types[obj] = picklists.record_type(org, obj, wanted if obj.endswith("Form_Submission__c") else None)
        offered = picklists.org_options(org, obj, names.field(obj, f["field"]), types[obj][0])
        out[(obj, field_id(f["field"]))] = (types[obj][1], offered)
    return out


def read_org(org, template_id: str, plan: dict | None = None) -> dict:
    known = org.fields(N + "Form_Template__c")  # an older Flow Tool Kit lacks some switches
    switches = [N + s for s in SWITCHES if N + s in known]
    template = org.query(f"SELECT Id, Name, {', '.join(switches + [N + 'FormQualifiedApiName_Header__c'])} "
                         f"FROM {N}Form_Template__c WHERE Id = '{template_id}'")
    if not template:
        raise BuildError(f"Form Template {template_id} is not in this org")
    pages = org.query(f"SELECT Id, {N}Position__c, {N}Page_Label__c, {N}Description__c, {N}Button_Label__c, {N}Conditional_Logic__c "
                      f"FROM {N}Form_Template_Page__c WHERE {N}Form_Template__c = '{template_id}' ORDER BY {N}Position__c")
    sections = org.query(f"SELECT {N}Form_Template_Page__r.{N}Position__c, {N}Position__c, {N}Title__c, {N}Header_Title__c, {N}Show_Header__c, "
                         f"{N}Section_Frame__c, {N}Conditional_Logic__c, {N}Component_Type__c, {N}FlowApiName__c, {N}lwcComponentName__c, "
                         f"{N}FormConfigJSON__c, {N}FormQualifiedApiName__c FROM {N}Form_Template_Page_Section__c "
                         f"WHERE {N}Form_Template_Page__r.{N}Form_Template__c = '{template_id}' "
                         f"ORDER BY {N}Form_Template_Page__r.{N}Position__c, {N}Position__c")
    names = set()
    for s in sections:
        config = json.loads(s.get(N + "FormConfigJSON__c") or "{}")
        if config.get("formSelectionMode") == "component":
            names.add((config.get("formQualifiedApiName") or "").removesuffix("_v0"))
    components = {}
    if names:
        for row in org.query(f"SELECT {N}QualifiedApiName__c, {N}FormConfigJSON__c, {N}Version__c FROM {N}Form_Component__c "
                             f"WHERE {N}QualifiedApiName__c IN ({quoted(sorted(names))}) ORDER BY {N}Version__c"):
            try:
                components[row[N + "QualifiedApiName__c"]] = json.loads(row.get(N + "FormConfigJSON__c") or "{}")
            except ValueError:
                pass
    return {"template": template[0], "pages": pages, "sections": sections, "components": components,
            "choices": read_choices(org, plan) if plan else {}}


def address_rows(spot: str, root: dict, own_json: bool) -> list[tuple]:
    """Each address in a built form the package cannot draw: outside an address section, without its row or one of its
    five parts, or (on a section's own JSON, which the form reads as it is) not flagged isAddressSection."""
    rows = []
    for n, inner in enumerate(get(root, "sections__r") or [], 1):
        where = f"{spot}, inner section {n}"
        kind = get(inner, "sectionType__c")
        for problem in addressparts.section_problems(get(inner, "fields__r") or [], kind, where, addressparts.json_variant, addressparts.json_name):
            rows.append((where, "address", "an address the package draws", problem.split(": ", 1)[-1]))
        if own_json and kind == addressparts.SECTION_TYPE and inner.get("isAddressSection") is not True:
            rows.append((where, "address", "isAddressSection", "not flagged, so the form draws the address parts as plain fields"))
    return rows


def address_header_rows(spot: str, design: dict, root: dict) -> list[tuple]:
    """Each planned address whose own section does not show its label as the header: the package draws an editable
    address with its label hidden, so the section header is the only label on screen (fieldmap.address_title)."""
    planned = [p for p in fieldmap.section_parts(design or {}) if p.get("type") == addressparts.SECTION_TYPE]
    built = [s for s in get(root, "sections__r") or [] if get(s, "sectionType__c") == addressparts.SECTION_TYPE]
    rows = []
    for n, (part, inner) in enumerate(zip(planned, built), 1):
        want = part.get("title") or None
        got = get(inner, "title__c") if get(inner, "showHeader__c") else None
        if text(want or "") != text(got or ""):
            rows.append((f"{spot}, address {n}", "address header", want or "not shown", got or "not shown"))
    return rows


def built_fields(root: dict) -> list[dict]:
    return [f for s in get(root, "sections__r") or [] for f in get(s, "fields__r") or []]


def compare_options(spot: str, f: dict, b: dict, obj: str, choices: dict, rows: list, notes: list, setup: list) -> None:
    """The options the form draws for one built choice field against the plan's. A planned value the org does not have
    for the record type is waiting for Setup (setup), not a mismatch: the form lists it and shows it once it is added.
    A planned value the org stores under another value (the plan wrote its label) stays a mismatch: the plan is wrong."""
    if not picklists.is_choice(f) or (obj, field_id(f.get("field"))) not in choices:
        return
    record_type, offered = choices[(obj, field_id(f.get("field")))]
    if offered is None:
        notes.append(f"{spot}: the values of {f.get('field')} could not be read; compare its options in Preview Form")
        return
    options = picklists.planned(f)
    found = picklists.gap(options, offered) or {"missing": [], "stored_as": {}}
    absent = [v for v in found["missing"] if v not in found["stored_as"]]
    if absent:
        setup.append(f"{spot}: {', '.join(absent)}, not a value of {f.get('field')} for the {record_type} record type" +
                     (" (until one is added, the form shows every value the field has)" if found.get("shows_all") else ""))
        if found.get("shows_all") and not found["stored_as"]:
            return
        options = [o for o in options if o[0] not in absent]
    for what, want, got in picklists.differences(options, picklists.rendered(b, offered), offered):
        rows.append((spot, what, want, f"{got} ({record_type} record type)"))


def compare_fields(where: str, planned: list[dict], built: list[dict], rows: list, exact: bool = True, obj: str = "",
                   choices: dict | None = None, notes: list | None = None, setup: list | None = None) -> None:
    def miss(what, want, got):
        rows.append((where, what, want, got))
    choices, notes = choices or {}, notes if notes is not None else []
    setup = setup if setup is not None else []
    planned = [f for f in planned if f.get("control") not in bt.NOT_BUILT_CONTROLS]
    if not exact:  # a component the build points at: every planned field must be there
        have = {field_id(get(b, "fieldName__c")): b for b in built}
        for f in planned:
            if field_id(f.get("field")) not in have:
                miss(f"field {f.get('label') or f.get('field')}", "in the component", "missing")
            else:
                compare_options(f"{where}, field {f.get('label') or f.get('field')}", f, have[field_id(f.get("field"))], obj, choices, rows, notes, setup)
        return
    if len(planned) != len(built):
        miss("field count", len(planned), len(built))
    for n, (f, b) in enumerate(zip(planned, built), 1):
        spot = f"field {n} {f.get('label') or f.get('field')}"
        if field_id(f.get("field")) != field_id(get(b, "fieldName__c")):
            miss(spot, f.get("field"), get(b, "fieldName__c"))
            continue
        widths = [str(w) for w in (f.get("widths") or [12, 12, 12])]
        got = [str(get(b, k)) for k in ("widthLarge__c", "widthMedium__c", "widthSmall__c")]
        if widths != got:
            miss(f"{spot} widths L/M/S", "/".join(widths), "/".join(got))
        if bool(f.get("required")) != bool(get(b, "required__c")):
            miss(f"{spot} required", bool(f.get("required")), bool(get(b, "required__c")))
        keys = fieldmap.package_keys(f)
        for key in ("customLabel__c", "labelVariant__c", "booleanType__c", "picklistType__c", "richTextType__c", "helpText__c"):
            # Wording past 255 characters lives in the long twin, which the package reads first
            long = fieldmap.LONG_TEXT.get(key)
            want = (keys.get(long) or keys.get(key)) if long else keys.get(key)
            have = (get(b, long) or get(b, key)) if long else get(b, key)
            if want is not None and text(want) != text(have):
                miss(f"{spot} {key.removesuffix('__c')}", want, have)
        if f.get("variant") == "attestation" and text(keys.get("Label_Rich_Text__c")) != text(get(b, "Label_Rich_Text__c")):
            miss(f"{spot} consent wording", text(keys.get("Label_Rich_Text__c"))[:60], text(get(b, "Label_Rich_Text__c"))[:60])
        if bool(f.get("condition")) != bool(get(b, "conditionalLogic__c")):
            miss(f"{spot} rule", bool(f.get("condition")), bool(get(b, "conditionalLogic__c")))
        compare_options(f"{where}, {spot}", f, b, obj, choices, rows, notes, setup)


def left_out(plan: dict) -> tuple[set, list]:
    """(the field names, the parked rules) a records-mode build left out until the new fields are deployed."""
    left = (plan.get("build") or {}).get("left_out") or {}
    return {bt.bare_field(f) for f in left.get("fields") or []}, left.get("rules") or []


def as_built(fields: list, pending: set) -> list:
    """The planned fields as the build made them: a left-out field is not there, and a rule that reads one is not either."""
    return [dict(f, condition=None) if bt.reads_any(f.get("condition"), pending) else f
            for f in fields if bt.bare_field(f.get("field")) not in pending]


def known_gaps(plan: dict) -> tuple[list, list]:
    """(what build-template never builds, what a records-mode build left out until deployed), as lines for the report."""
    gaps = [f"{f.get('label') or f.get('field')} ({f.get('control')})" for p in plan.get("pages") or [] for s in p.get("sections") or []
            for f in s.get("fields") or [] if f.get("control") in bt.NOT_BUILT_CONTROLS]
    pending, rules = left_out(plan)
    left = [f"{name} (a new field, not in the org yet)" for name in sorted(pending)]
    left += [f"{r.get('where')}: the {r.get('level')} rule {r.get('label')!r}, which reads {', '.join(r.get('reads') or [])}" for r in rules]
    return gaps, left


def compare(plan: dict, built: dict, notes: list | None = None, setup: list | None = None) -> list[tuple]:
    """Mismatches as (where, what, plan, built). notes collects what could not be compared (a metadata component whose
    design is not stored as JSON): check those in Form Builder. What the build left out until deployed is not a mismatch,
    and neither is a planned option the org lacks: setup collects those, the values to add in Setup."""
    rows: list = []
    pending, _ = left_out(plan)
    notes = notes if notes is not None else []
    setup = setup if setup is not None else []
    template = plan.get("template") or {}
    record = built["template"]
    for key in SWITCHES:
        if key in template and N + key in record and template[key] != record.get(N + key):
            rows.append(("template", key.removesuffix("__c"), template[key], record.get(N + key)))
    if not record.get(N + "FormQualifiedApiName_Header__c"):
        notes.append("The template has no header form: the Banner needs a Flow Tool Kit release with the Banner header (see the build's warnings)")
    components = {c.get("key"): c for c in plan.get("components") or []}
    build, mode = plan.get("build") or {}, bt.build_mode(plan)
    pages = plan.get("pages") or []
    if len(pages) != len(built["pages"]):
        rows.append(("form", "page count", len(pages), len(built["pages"])))
    by_page: dict = {}
    for s in built["sections"]:
        by_page.setdefault(int((s.get(N + "Form_Template_Page__r") or {}).get(N + "Position__c") or 0), []).append(s)
    for p, (page, got) in enumerate(zip(pages, built["pages"]), 1):
        where = f"page {p} {page.get('Page_Label__c')}"
        for key in ("Page_Label__c", "Description__c", "Button_Label__c"):
            if page.get(key) and text(page[key]) != text(got.get(N + key)):
                rows.append((where, key.removesuffix("__c"), text(page[key])[:60], text(got.get(N + key))[:60]))
        wanted = bool(page.get("condition")) and not bt.reads_any(page.get("condition"), pending)
        if wanted != bool(got.get(N + "Conditional_Logic__c")):
            rows.append((where, "page rule", wanted, bool(got.get(N + "Conditional_Logic__c"))))
        sections, built_sections = page.get("sections") or [], by_page.get(p, [])
        if len(sections) != len(built_sections):
            rows.append((where, "section count", len(sections), len(built_sections)))
        for n, (section, b) in enumerate(zip(sections, built_sections), 1):
            spot = f"{where}, section {n} {section.get('Title__c') or section.get('Header_Title__c')}"
            for key in ("Title__c", "Header_Title__c", "Section_Frame__c"):
                if section.get(key) and text(section[key]) != text(b.get(N + key)):
                    rows.append((spot, key.removesuffix("__c"), section[key], b.get(N + key)))
            if section.get("Header_Title__c") and section.get("Show_Header__c") is not False and not b.get(N + "Show_Header__c"):
                rows.append((spot, "header shown", True, False))
            wanted = bool(section.get("condition")) and not bt.reads_any(section.get("condition"), pending)
            if wanted != bool(b.get(N + "Conditional_Logic__c")):
                rows.append((spot, "section rule", wanted, bool(b.get(N + "Conditional_Logic__c"))))
            kind = section.get("Component_Type__c")
            if kind == "Flow" and section.get("FlowApiName__c") != b.get(N + "FlowApiName__c"):
                rows.append((spot, "flow", section.get("FlowApiName__c"), b.get(N + "FlowApiName__c")))
            if kind == "Lightning Web Component" and section.get("lwcComponentName__c") != b.get(N + "lwcComponentName__c"):
                rows.append((spot, "custom LWC", section.get("lwcComponentName__c"), b.get(N + "lwcComponentName__c")))
            if kind in ("Flow", "Lightning Web Component") or section.get("display_text"):
                continue
            config = json.loads(b.get(N + "FormConfigJSON__c") or "{}")
            component = components.get(section.get("component")) or {}
            decision = component.get("decision")
            # A component section: every shared, reused or extended one, and a one-off component (form-only in the record
            # or metadata shape, or built as a record in records mode)
            one_off = decision == "form-only" and bt.built_shape(component, mode) in ("record", "metadata")
            if one_off or (decision in ("reuse", "update", "extend", "shared-new", "shared-record") and component.get("name")):
                wanted = bt.placed_name(component, build.get("prefix") or "", build.get("form_ids") or {}, mode)
                got_name = (config.get("formQualifiedApiName") or "").removesuffix("_v0")
                if config.get("formSelectionMode") != "component" or got_name != wanted:
                    rows.append((spot, "component", wanted, got_name or config.get("formSelectionMode")))
                    continue
                design = component.get("section") if decision == "shared-record" else section
                stored = built["components"].get(wanted)
                if not built_fields(stored or {}):
                    notes.append(f"{spot}: {wanted}'s fields are not stored as JSON here (a metadata component); compare them in Form Builder")
                    continue
                obj = bt.ns_object(component.get("object") or (design or {}).get("object") or "Form_Submission__c")
                compare_fields(spot, as_built((design or {}).get("fields") or [], pending), built_fields(stored), rows, exact=False,
                               obj=obj, choices=built.get("choices"), notes=notes, setup=setup)
                rows += address_rows(spot, stored, own_json=False)
                if one_off or decision in ("shared-new", "shared-record"):  # built from this plan's design
                    rows += address_header_rows(spot, design, stored)
            else:
                if config.get("formSelectionMode") != "custom":
                    rows.append((spot, "form", "its own JSON", config.get("formSelectionMode") or "none"))
                    continue
                root = json.loads(config.get("formJsonConfig") or "{}")
                # A field rule equal to its section's rule is built once, on the section
                planned = [dict(f, condition=None) if f.get("condition") and f.get("condition") == section.get("condition") else f
                           for part in fieldmap.section_parts(section) for f in part.get("fields") or []]
                obj = bt.ns_object(component.get("object") or section.get("object") or "Form_Submission__c")
                compare_fields(spot, as_built(planned, pending), built_fields(root), rows, obj=obj, choices=built.get("choices"), notes=notes,
                               setup=setup)
                rows += address_rows(spot, root, own_json=True)
                rows += address_header_rows(spot, section, root)
    return rows


def markdown(rows: list, gaps: list, notes: list | None = None, left: list | None = None, setup: list | None = None) -> str:
    lines = ["# Round trip: plan vs built", "", f"{len(rows)} mismatches.", ""]
    if rows:
        lines += ["| Where | What | Plan | Built |", "|---|---|---|---|"]
        lines += [f"| {w} | {k} | {str(a).replace('|', '/')} | {str(b).replace('|', '/')} |" for w, k, a, b in rows]
    if left:
        lines += ["", "Left out until deployed (records mode; rebuild once the new fields are in the org):", ""] + [f"- {x}" for x in left]
    if setup:
        lines += ["", "Waiting for Setup (picklist values the org does not have yet; the form already lists them, so each shows once it "
                      "is added to the field and its record type, with no rebuild):", ""] + [f"- {x}" for x in setup]
    if gaps:
        lines += ["", "Known gaps (not built by build-template):", ""] + [f"- {g}" for g in gaps]
    if notes:
        lines += ["", "Not compared here:", ""] + [f"- {n}" for n in notes]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare the built Form Template with plan.json")
    parser.add_argument("plan")
    parser.add_argument("--org")
    args = parser.parse_args(argv)
    path = pathlib.Path(args.plan)
    plan = json.loads(path.read_text())
    template_id = (plan.get("build") or {}).get("template_id")
    if not template_id:
        sys.exit("roundtrip: the plan has no build.template_id; run buildtemplate.py first")
    try:
        built = read_org(Org(args.org), template_id, plan)
    except BuildError as error:
        sys.exit(f"roundtrip: {error}")
    notes, setup = [], []
    rows = compare(plan, built, notes, setup)
    gaps, left = known_gaps(plan)
    out = path.parent / "roundtrip.md"
    out.write_text(markdown(rows, gaps, notes, left, setup))
    print(f"{len(rows)} mismatches" + (f", {len(left)} left out until deployed" if left else "") +
          (f", {len(setup)} waiting for picklist values in Setup" if setup else "") + f" -> {out}")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
