#!/usr/bin/env python3
"""Turn a form's design into new-mapping-flow's work list, without asking again what the design already answers.

    python3 mapping_plan.py <plan.json> [--catalog catalog.json] [--config flow-tool-kit.json]
                            [--report build-report.json] [--spec mapping-spec.json]
                            [--out mapping-work.json] [--json] [--allow-stale-catalog]

Reads, in this order, and never asks a question one of them answers:
  - plan.json (form-design, _shared/standards/plan-format.md): intake.edition, every component's object, decision and
    form_template_mapping, every field's object, field and placement, url_parameters, and build.template_id once
    build-template has run.
  - catalog.json (org-catalog, _shared/standards/catalog-format.md): the org's own map for a reused component, the other
    forms that already map the same object, the Form Submission fields that exist, and the platforms. Default: the
    plan's intake.catalog, then the config's orgs.<org id>.catalog.
  - flow-tool-kit.json (ftk-start, _shared/standards/project-config.md): the edition and the audiences. Found beside the
    plan or in a folder above it. A 15- or 18-character org Id matches the same org.
  - build-template's report (--out of buildtemplate.py), optional: its edition when nothing else names one.
  - mapping-spec.json, optional, beside the plan: this skill's own answers the plan has no key for (calculated or
    combined values, record types, Campaign Member values, free-edition targets for the org's own staging fields,
    prefill flows, and the `wiring` of a new flow to the template, checked by wiring_check.py). Format in
    references/work-list.md.

Writes the work list (references/work-list.md): one entry per target object (the Conversion Rules value, the packaged
flow to keep or a new object rule, the form maps, the Transform rows), the fields that stay on the submission, prefill
flows, handoffs to flow-access-fix (per audience) and new-invocable, and the questions, problems and warnings.

Standard library only, so it runs in claude.ai chat's code sandbox as well as Claude Code. Exit 1 when there are problems.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wiring_check  # noqa: E402  (beside this file)

N = "FlowToolKit__"
SUBMISSION = "Form_Submission__c"
PACKAGE_OBJECTS = {"Form_Submission__c", "Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c", "Form_Component__c"}
# Free edition: forms show only on these objects and the Flow Tool Kit objects (_shared/standards/mapping-preference.md)
FREE_OBJECTS = {"Account", "Contact", "Lead", "Case", "Campaign", "CampaignMember"} | PACKAGE_OBJECTS
# Objects the packaged controller converts: (Conversion Rules value, packaged step without the prefix)
PACKAGED_STEPS = {
    "Account": ("Account", "Form_Submission_Convert_Process_Account_Overridable"),
    "Contact": ("Contact1", "Form_Submission_Convert_Process_Contact_Primary_Default_Overridable"),
    "Lead": ("Lead1", "Form_Submission_Convert_Process_Lead_Primary_Default_Overridable"),
    "Case": ("Create Case", "Form_Submission_Convert_Process_Case_Overridable"),
    "Opportunity": ("Opportunity \U0001f4b0", "Form_Submission_Convert_Process_Opportunity_Overridable"),
    "CampaignMember": ("Contact1 \U0001f449 Create Campaign Member", "Form_Submission_Convert_Process_Campaign_Members_Overridable"),
}
SECOND_STEPS = {
    "Contact": ("Contact2", "Form_Submission_Convert_Process_Contact_Alternate_Default_Overridable"),
    "Lead": ("Lead2", "Form_Submission_Convert_Process_Lead_Alternate_Default_Overridable"),
}
# Packaged staging fields whose block names the rule that converts them
PACKAGED_BLOCKS = (("Contact1_", "Contact", "Contact1"), ("Contact2_", "Contact", "Contact2"),
                   ("Company", "Account", "Account"), ("Website", "Account", "Account"))
CATALOG_MAX_AGE = dt.timedelta(hours=24)


# ---------------------------------------------------------------- reading the inputs
def read_json(path: pathlib.Path | None) -> dict:
    if not path:
        return {}
    return json.loads(pathlib.Path(path).read_text())


def find_config(plan_path: pathlib.Path, explicit: str | None) -> tuple[dict, str | None]:
    if explicit:
        return read_json(pathlib.Path(explicit)), explicit
    folder = plan_path.resolve().parent
    for candidate in [folder, *folder.parents]:
        path = candidate / "flow-tool-kit.json"
        if path.exists():
            return read_json(path), str(path)
    return {}, None


def same_org(a: str | None, b: str | None) -> bool:
    """A 15- and an 18-character Id of the same org match; the first 15 characters are the Id."""
    return bool(a and b) and a[:15] == b[:15]


def org_entry(config: dict, org_id: str | None) -> dict:
    """The config's answers for the plan's org. With no Id to match, only a file holding one org is used."""
    orgs = config.get("orgs") or {}
    for key, entry in orgs.items():
        if same_org(key, org_id):
            return entry
    if not org_id and len(orgs) == 1:
        return next(iter(orgs.values()))
    return {}


def resolve_edition(plan: dict, entry: dict, catalog: dict, report: dict) -> tuple[str, str]:
    """The edition and where it came from. Never silently paid: 'assumed' raises a question."""
    for source, value in (("plan", (plan.get("intake") or {}).get("edition")), ("config", entry.get("edition")),
                          ("catalog", catalog.get("edition")), ("build report", report.get("edition"))):
        if value in ("paid", "free"):
            return value, source
    return "paid", "assumed"


AUDIENCE_WORDS = (("guest", ("guest", "public", "anonymous", "anyone")), ("portal", ("portal", "community", "member", "signed-in", "signed in")),
                  ("internal", ("internal", "staff", "employee", "admin")))


def resolve_audiences(plan: dict, entry: dict) -> tuple[list, str]:
    saved = [a for a in entry.get("audiences") or [] if a in ("guest", "portal", "internal")]
    if saved:
        return saved, "config"
    text = str((plan.get("intake") or {}).get("audience") or "").lower()
    found = [name for name, words in AUDIENCE_WORDS if any(w in text for w in words)]
    return (found, "plan") if found else ([], "unknown")


def load_catalog(plan_path: pathlib.Path, plan: dict, entry: dict, explicit: str | None) -> tuple[dict, str | None]:
    for candidate in (explicit, (plan.get("intake") or {}).get("catalog"), entry.get("catalog")):
        if not candidate:
            continue
        path = pathlib.Path(candidate)
        if not path.is_absolute() and not explicit:
            path = plan_path.resolve().parent / path
        if path.exists():
            return read_json(path), str(path)
    return {}, None


def catalog_age(catalog: dict, now: dt.datetime) -> dt.timedelta | None:
    taken = catalog.get("taken_at")
    if not taken:
        return None
    try:
        when = dt.datetime.fromisoformat(str(taken).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return now - when


# ---------------------------------------------------------------- small helpers
def bare(name: str | None) -> str:
    return (name or "").replace(N, "")


def plan_fields(plan: dict):
    """Every field in page order, with its section and the component key it belongs to."""
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            for field in section.get("fields") or []:
                yield section, field


def section_title(section: dict) -> str:
    return section.get("Header_Title__c") or section.get("Title__c") or section.get("component") or "untitled section"


def catalog_component(catalog: dict, name: str | None) -> dict | None:
    if not name:
        return None
    for c in catalog.get("components") or []:
        if name in (c.get("name"), c.get("ref"), *(c.get("refs") or [])) or bare(c.get("name")) == bare(name):
            return c
    return None


def submission_fields(catalog: dict) -> dict | None:
    """The Form Submission fields the catalog read, or None when it could not read them."""
    entry = (catalog.get("fields_index") or {}).get(N + SUBMISSION) or {}
    return entry.get("fields") if entry.get("read") else None


def plan_map(component: dict) -> tuple[str | None, dict]:
    """The plan's form_template_mapping as (apply_to, {component field: Form Submission field})."""
    mapping = component.get("form_template_mapping") or {}
    fields = {}
    for source, targets in (mapping.get("fields") or {}).items():
        for target in (targets if isinstance(targets, list) else [targets]):
            if target:
                fields.setdefault(source, target)
    return (mapping.get("apply_to") or ("all records" if fields else None)), fields


def org_map(component: dict | None) -> tuple[str | None, dict]:
    """A catalog component's own map, turned around to {component field: Form Submission field}."""
    submission_map = (component or {}).get("submission_map") or {}
    fields = {}
    for submission_field, own in (submission_map.get("fields") or {}).items():
        fields.setdefault(own, submission_field)
    lookup = submission_map.get("lookup_field")
    return ("all records" if lookup == "ALL" else lookup) if fields else None, fields


def rule_for(obj: str, apply_to: str | None) -> tuple[str | None, str | None]:
    """The Conversion Rules value and packaged step for an object; a second lookup (Contact 2, Lead 2) picks the second step."""
    if obj in SECOND_STEPS and apply_to and bare(apply_to).startswith(obj + "2"):
        return SECOND_STEPS[obj]
    return PACKAGED_STEPS.get(obj, (None, None))


# ---------------------------------------------------------------- the work list
def work_list(plan: dict, catalog: dict, config: dict, report: dict, spec: dict, *, now: dt.datetime | None = None,
              allow_stale: bool = False, paths: dict | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    intake = plan.get("intake") or {}
    entry = org_entry(config, intake.get("org_id"))
    edition, edition_source = resolve_edition(plan, entry, catalog, report)
    audiences, audiences_source = resolve_audiences(plan, entry)
    out = {"work_list_version": 1, "slug": plan.get("slug"), "inputs": paths or {},
           "template_id": (plan.get("build") or {}).get("template_id"),
           "edition": edition, "edition_source": edition_source, "audiences": audiences, "audiences_source": audiences_source,
           "conversion_rules": [], "objects": [], "transform_rows": [], "stays_on_submission": [], "prefill_flows": [],
           "handoffs": [], "questions": [], "problems": [], "warnings": [], "notes": []}
    objects: dict = {}

    def target(obj: str, apply_to: str | None = None) -> dict:
        key = (obj, rule_for(obj, apply_to)[0])  # one entry per packaged rule; an object the package does not convert is one entry
        if key not in objects:
            rule, step = rule_for(obj, apply_to)
            item = {"object": obj, "rule": rule, "flow": {"kind": "packaged", "name": N + step} if step else {"kind": "new-object-rule"},
                    "form_maps": [], "transform_rows": [], "org_maps": []}
            if not step:
                item["flow"]["see"] = "references/new-object-rule.md"
                item["rule"] = None
            objects[key] = item
        return objects[key]

    # --- the inputs themselves
    if edition_source == "assumed":
        out["questions"].append("Which Flow Tool Kit edition does the org run, paid or free? Nothing names it (plan, flow-tool-kit.json, "
                                "catalog). The work list assumes paid; save the answer in flow-tool-kit.json and run again.")
    if not catalog:
        out["warnings"].append("No catalog: reused components' own maps and the org's other mapped forms are unknown. Run org-catalog first.")
    else:
        age = catalog_age(catalog, now)
        if age is not None and age > CATALOG_MAX_AGE:
            text = f"The catalog is {int(age.total_seconds() // 3600)} hours old (over 24): run org-catalog again before building."
            (out["warnings"] if allow_stale else out["problems"]).append(text)
        if catalog.get("status") not in (None, "ok"):
            out["warnings"].append(f"The catalog's status is {catalog.get('status')!r}: {catalog.get('status_note') or 'some reads were refused'}.")
        if intake.get("org_id") and (catalog.get("org") or {}).get("id") and not same_org(intake["org_id"], catalog["org"]["id"]):
            out["problems"].append(f"The catalog is of org {catalog['org']['id']}, the plan of {intake['org_id']}: use the catalog of the org the plan builds in.")
    if not out["template_id"]:
        out["notes"].append("No build.template_id in the plan: build-template has not built it yet. The work list is the plan's; "
                            "run it again after the build to tie it to the template.")
    existing = submission_fields(catalog)
    platforms = catalog.get("platforms") or {}

    # --- components on another object: the form maps (paid) or the free-edition fallback
    components = {c.get("key"): c for c in plan.get("components") or [] if c.get("key")}
    mapped_by_component: dict = {}
    for key, component in components.items():
        obj = bare(component.get("object"))
        if not obj or obj in PACKAGE_OBJECTS or component.get("decision") in ("flow-section", "custom-lwc"):
            continue
        apply_to, fields = plan_map(component)
        source = "plan"
        org_component = catalog_component(catalog, component.get("name")) if component.get("decision") in ("reuse", "extend") else None
        if component.get("decision") in ("reuse", "extend") and catalog and not org_component:
            out["warnings"].append(f"Component {component.get('name')!r} ({key}) is not in the catalog: its map in the org is unknown.")
        if not fields and org_component:
            apply_to, fields = org_map(org_component)
            source = "org"
        elif fields and org_component and component.get("decision") == "reuse":
            org_apply, org_fields = org_map(org_component)
            if org_fields and (org_fields != fields or (org_apply or "").lower() != (apply_to or "").lower()):
                out["warnings"].append(f"{component.get('name')}: the plan's map differs from the one saved on the component in the org. A reused "
                                       f"component keeps its own map, so the org's map runs (used on {org_component.get('templates', 0)} templates).")
                apply_to, fields, source = org_apply, org_fields, "org"
        mapped_by_component[key] = set(fields)
        item = target(obj, apply_to)
        where = f"{section_label(plan, key)} ({obj})"

        if edition == "free" and obj not in FREE_OBJECTS:
            out["warnings"].append(f"{where}: the free edition shows no form on {obj}. Free-edition fallback: put these answers on Form Submission "
                                   "fields and map each in the conversion flow's Transform (rows listed).")
            for own, submission_field in fields.items():
                item["transform_rows"].append(row(obj, own, submission_field, "free-edition fallback: the form cannot show on this object"))
            continue
        if not fields:
            if edition == "paid":
                out["problems"].append(f"{where}: a form on {obj} in a paid org with no Form Template Mapping, so nothing it collects reaches the "
                                       "submission. Map each field to a Form Submission field (form-design's form_template_mapping)."
                                       + (" Mapping the shared component in Form Builder changes it on every template that uses it "
                                          f"({org_component.get('templates', 0)}): ask first, or extend it." if org_component else ""))
            continue
        form_map = {"component": component.get("name") or key, "decision": component.get("decision"), "apply_to": apply_to,
                    "fields": fields, "source": source}
        if edition == "free":
            form_map["confirm"] = (f"A mapped form on {obj} may work in the free edition; confirm it in this org before relying on it. "
                                   "Fallback: the Transform rows listed.")
            out["questions"].append(f"{where}: does the form map apply in this free-edition org? Try one submission; if not, use the fallback Transform rows.")
            for own, submission_field in fields.items():
                item["transform_rows"].append(row(obj, own, submission_field, "free-edition fallback, only if the map does not apply"))
        item["form_maps"].append(form_map)
        if existing is not None:
            missing = sorted({f for f in fields.values() if f not in existing})
            if missing:
                out["warnings"].append(f"{where}: the map names Form Submission fields the org does not have yet: {', '.join(missing)}. "
                                       "Create them before the map is saved.")

    # --- every field: placement answers, packaged blocks, the submission
    for section, field in plan_fields(plan):
        obj = bare(field.get("object"))
        name = field.get("field") or ""
        placement = str(field.get("placement") or "")
        key = section.get("component")
        label = field.get("label") or name
        if obj == "CampaignMember" or name == "RecordTypeId":
            reason = "Campaign Member: the maps do not apply to its conversion" if obj == "CampaignMember" else "record type: never a map target"
            target(obj)["transform_rows"].append(row(obj, name, name, reason))
            continue
        if obj and obj != SUBMISSION:
            if placement.startswith("mapped:") and edition == "paid" and key in mapped_by_component and name not in mapped_by_component[key]:
                out["problems"].append(f"{label} ({obj}.{name}, {section_title(section)}): its placement says mapped, but its component's map "
                                       "has no row for it. Add it to form_template_mapping.")
            continue
        block = next(((o, r) for prefix, o, r in PACKAGED_BLOCKS if bare(name).startswith(prefix)), None) if name.startswith(N) else None
        if block:
            item = target(*((block[0], N + "Contact2__c") if block[1] == "Contact2" else (block[0],)))
            item.setdefault("packaged_fields", []).append(name)
            continue
        target_name = (spec.get("targets") or {}).get(name)
        if target_name:
            t_obj, _, t_field = target_name.partition(".")
            target(t_obj)["transform_rows"].append(row(t_obj, t_field, name, "this skill's spec names the target"))
            continue
        out["stays_on_submission"].append({"field": name, "label": label, "section": section_title(section),
                                           "why": placement.split(":", 1)[1].strip() if ":" in placement else "placed on the submission"})

    own_staging = [s for s in out["stays_on_submission"] if not s["field"].startswith(N)]
    if edition == "free" and own_staging:
        out["questions"].append(f"{len(own_staging)} of the org's own Form Submission fields stay on the submission "
                                f"({', '.join(s['field'] for s in own_staging[:6])}{', ...' if len(own_staging) > 6 else ''}). "
                                "Name any that should reach a record in mapping-spec.json targets.")

    # --- this skill's own answers: calculated values, record types, Campaign Members
    for d in spec.get("derived") or []:
        obj = d.get("object") or ""
        how = d.get("how") or "formula"
        r = row(obj, d.get("field"), " + ".join(d.get("from") or []) or None, f"{how} value: a map cannot express it")
        if d.get("formula"):
            r["formula"] = d["formula"]
        if how == "apex":
            r["how"] = "Apex action (new-invocable), output assigned before the Transform"
            out["handoffs"].append({"skill": "new-invocable", "for": f"{obj}.{d.get('field')}", "inputs": d.get("from") or [],
                                    "output": d.get("field"), "what": d.get("what") or f"computes {d.get('field')} for the {obj} conversion"})
        target(obj)["transform_rows"].append(r)
    for rt in spec.get("record_types") or []:
        r = row(rt.get("object"), "RecordTypeId", None, "record type: never a map target")
        r["how"] = f"Get Records on RecordType (DeveloperName {rt.get('record_type')!r}), then the Transform row"
        target(rt.get("object") or "")["transform_rows"].append(r)
    for cm in spec.get("campaign_members") or []:
        target("CampaignMember")["transform_rows"].append(row("CampaignMember", cm.get("field"), cm.get("from"),
                                                              "Campaign Member: the maps do not apply to its conversion"))

    # --- the org's other forms on the same objects, and platform notes
    for item in objects.values():
        for mapped in catalog.get("mapped_forms") or []:
            if bare(mapped.get("object")) == item["object"] and mapped.get("component") not in {m["component"] for m in item["form_maps"]}:
                item["org_maps"].append({"component": mapped.get("component"), "lookup_field": mapped.get("lookup_field"),
                                         "mapped": mapped.get("mapped"), "templates": mapped.get("templates")})
        if platforms.get("person_accounts") and item["object"] in ("Account", "Contact"):
            out["warnings"].append(f"{item['object']}: the org uses person accounts; matching and saving change for every template "
                                   "through a flow override of the shared Upsert engine (SKILL.md Step 2).")
        if item["flow"]["kind"] == "new-object-rule" and item["object"] == "IndividualApplication":
            item["flow"]["see"] = "references/new-object-rule.md (the Individual Application worked example)"

    # --- prefill flows: one per entry record, run by whoever opens the form
    for p in spec.get("prefill") or []:
        flow = p.get("flow") or f"Form_Prefill_{p.get('entry_object')}"
        out["prefill_flows"].append({"flow": flow, "entry_object": p.get("entry_object"), "parameter": p.get("parameter"),
                                     "lookup": p.get("lookup")})
    lookups = {f.get("field") for _, f in plan_fields(plan) if f.get("control") == "Lookup"}
    for param in plan.get("url_parameters") or []:
        if param.get("field") in lookups and not any(p.get("parameter") == param.get("param") for p in spec.get("prefill") or []):
            out["questions"].append(f"URL parameter {param.get('param')} fills the lookup {param.get('field')}. Should the form also fill answers "
                                    "from that record? Then add a prefill flow for it to mapping-spec.json (one per entry record).")
    for flow in out["prefill_flows"]:
        if not audiences:
            out["questions"].append(f"Who opens the form that runs {flow['flow']}: the public without signing in, signed-in community "
                                    "members, staff, or a mix? flow-access-fix needs it for each audience.")
        for audience in audiences:
            out["handoffs"].append({"skill": "flow-access-fix", "flow": flow["flow"], "audience": audience,
                                    "why": "a prefill flow runs as the person opening the form: restrict it and grant it in this audience's permission set"})

    # --- the template's switches that reach this skill
    template = plan.get("template") or {}
    if template.get("Attach_PDF_Confirmation__c"):
        out["notes"].append("Attach PDF to Confirmation Email is on: if the org overrides (Form Submission) Convert | Utility | Send Email | "
                            "Overridable, copy the PDF steps into the override (references/traps.md).")

    # --- how a new flow is wired to the template: picklist value = the flow's API name (wiring_check.py)
    if spec.get("wiring"):
        wiring = wiring_check.check(spec["wiring"])
        out["wiring"] = wiring
        out["problems"] += [f"Wiring: {p}" for p in wiring["problems"]]
        out["warnings"] += [f"Wiring: {w}" for w in wiring["warnings"]]

    # --- assemble
    seen_rules = set()
    for item in objects.values():
        lookups_used = {(m["apply_to"] or "").lower() for m in item["form_maps"]}
        if len(lookups_used) > 1:
            out["warnings"].append(f"{item['object']}: form maps apply to {len(lookups_used)} different lookups, so the submission converts to "
                                   "two records of it. The second is a new rule with its own lookup and status pair (SKILL.md Step 2).")
        if item["rule"] and item["rule"] not in seen_rules:
            seen_rules.add(item["rule"])
            out["conversion_rules"].append(item["rule"])
        out["transform_rows"] += item["transform_rows"]
        if item["flow"]["kind"] == "packaged" and not item["transform_rows"]:
            item["flow"]["change"] = "none: keep the packaged flow; the form maps and its Transform carry everything"
        elif item["flow"]["kind"] == "packaged":
            item["flow"]["change"] = ("clone the starter template or extend the step for the Transform rows (SKILL.md Step 2)"
                                      if edition == "paid" else "the Transform rows go in the conversion flow (free edition)")
        out["objects"].append(item)
    out["status"] = "problems" if out["problems"] else ("questions" if out["questions"] else "ready")
    return out


def row(obj: str | None, target_field: str | None, source: str | None, reason: str) -> dict:
    return {"object": obj, "target": target_field, "source": source, "why": reason}


def section_label(plan: dict, key: str) -> str:
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            if section.get("component") == key:
                return section_title(section)
    return key


# ---------------------------------------------------------------- output
def summary(work: dict) -> str:
    lines = [f"Mapping work list for {work.get('slug') or 'the form'}: {work['status']}",
             f"Edition: {work['edition']} ({work['edition_source']}). Audiences: {', '.join(work['audiences']) or 'unknown'} ({work['audiences_source']}).",
             f"Conversion Rules to enable: {', '.join(work['conversion_rules']) or 'none'}"]
    for item in work["objects"]:
        flow = item["flow"]
        lines.append(f"- {item['object']}: " + (f"packaged {flow['name']}; {flow.get('change')}" if flow["kind"] == "packaged"
                                                else f"new object rule ({flow['see']})")
                     + f"; {sum(len(m['fields']) for m in item['form_maps'])} mapped by the form, {len(item['transform_rows'])} Transform rows")
    lines.append(f"Stay on the submission: {len(work['stays_on_submission'])} fields")
    for p in work["prefill_flows"]:
        lines.append(f"Prefill flow: {p['flow']} (entry record {p.get('entry_object')})")
    for h in work["handoffs"]:
        lines.append(f"Hand to {h['skill']}: " + (f"{h['flow']} for {h['audience']}" if h["skill"] == "flow-access-fix" else h["for"]))
    for title in ("problems", "questions", "warnings", "notes"):
        for text in work[title]:
            lines.append(f"{title[:-1].capitalize()}: {text}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="new-mapping-flow's work list from plan.json, the catalog and flow-tool-kit.json")
    parser.add_argument("plan")
    parser.add_argument("--catalog", help="org-catalog's catalog.json (default: the plan's intake.catalog, then the config's)")
    parser.add_argument("--config", help="flow-tool-kit.json (default: found beside the plan or in a folder above it)")
    parser.add_argument("--report", help="build-template's report (buildtemplate.py --out)")
    parser.add_argument("--spec", help="this skill's mapping-spec.json (default: beside the plan, when present)")
    parser.add_argument("--out", help="write the work list as JSON to this file")
    parser.add_argument("--json", action="store_true", help="print the JSON instead of the summary")
    parser.add_argument("--allow-stale-catalog", action="store_true", help="a catalog over 24 hours old is a warning, not a problem")
    args = parser.parse_args(argv)

    plan_path = pathlib.Path(args.plan)
    plan = read_json(plan_path)
    config, config_path = find_config(plan_path, args.config)
    entry = org_entry(config, (plan.get("intake") or {}).get("org_id"))
    catalog, catalog_path = load_catalog(plan_path, plan, entry, args.catalog)
    spec_path = pathlib.Path(args.spec) if args.spec else plan_path.resolve().parent / "mapping-spec.json"
    spec = read_json(spec_path) if spec_path.exists() else {}
    report = read_json(pathlib.Path(args.report)) if args.report else {}
    paths = {"plan": str(plan_path), "catalog": catalog_path, "config": config_path, "report": args.report,
             "spec": str(spec_path) if spec else None}
    work = work_list(plan, catalog, config, report, spec, allow_stale=args.allow_stale_catalog, paths=paths)
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(work, indent=1, ensure_ascii=False))
    print(json.dumps(work, indent=1, ensure_ascii=False) if args.json else summary(work))
    return 1 if work["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
