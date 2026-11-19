#!/usr/bin/env python3
"""Turn one-per-form FormAssembly connectors into a shared Flow Tool Kit flow plan.

FormAssembly gives every form its own prefill and submit connector. Flow Tool Kit shares
conversion flows per object (one rule per object, run by the controller in a fixed order,
switched on per Form Template) and shares prefill flows per entry record. This script reads
every built form's ir.json and writes <root>/flow-plan.md and <root>/flow-plan.json:

  conversion  each Salesforce object written, mapped to a controller rule (packaged or new),
              with the forms that need it, actions, match rules, record types, dependencies
              and order conflicts; plus each form's rule list in controller order
  prefill     shared prefill flows grouped by entry record (object + matching field), the
              chained lookups and repeating-section fills each form adds, and how the entry
              key reaches the flow (a Form Submission lookup set from a URL parameter)

new-mapping-flow (Step 0, a whole account) builds from this plan: each rule once, each prefill flow once.

Usage: python3 flow_plan.py [--root _formassembly] [--source force-app]
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402
import build  # noqa: E402

CONTROLLER_ORDER = ["Account", "Contact 1", "Lead 1", "Contact 2", "Lead 2", "Opportunity", "Case", "Additional Data", "Related Records", "Files", "Confirmation"]
SUBMISSION_LOOKUP = {"Account": "FlowToolKit__Account__c", "Contact": "FlowToolKit__Contact_1__c", "Lead": "FlowToolKit__Lead_1__c", "Opportunity": "FlowToolKit__Opportunity__c", "Case": "FlowToolKit__Case__c"}
FILE_OBJECTS = {"Attachment", "ContentVersion", "ContentDocumentLink"}
PAYMENT_OBJECTS = {"npe01__OppPayment__c"}
SIDE_RECORDS = {"npe5__Affiliation__c", "npe4__Relationship__c"}
# Conversion Rules values of the packaged rules (new-mapping-flow references/pipeline-architecture.md, Rules, types and statuses)
PACKAGED_VALUE = {"Account": "Account", "Contact 1": "Contact1", "Contact 2": "Contact2", "Lead 1": "Lead1", "Lead 2": "Lead2", "Opportunity": "Opportunity 💰", "Case": "Create Case"}


def nodes_of(model):
    nodes = model.get("nodes", [])
    return list(nodes.values()) if isinstance(nodes, dict) else nodes


def repeat_labels(document):
    repeat_ids = {s["id"] for s in document["structure"] if s.get("repeat")}
    return {f["label"].strip() for f in document["fields"] if f.get("section_id") in repeat_ids and f.get("label")}


def record_type_of(node):
    for mapping in node.get("mappings", []):
        if mapping["target_field_label"].lower().startswith("record type"):
            return mapping.get("source_value")
    return None


def depends_on(node, nodes_by_id):
    found = set()
    parent = nodes_by_id.get(node.get("parent_node_id"))
    if parent and parent.get("sobject"):
        found.add(parent["sobject"])
    for mapping in node.get("mappings", []):
        match = re.search(r"Record ID of [\d.]+\.?\s*(\w+)", mapping.get("source_value") or "")
        if mapping.get("source_kind") in ("record_id", "lookup_result") and match:
            found.add(match.group(1))
    predicate = json.dumps((node.get("lookup") or {}).get("predicate") or {})
    for match in re.finditer(r"Record ID of [\d.]+\.?\s*(\w+)", predicate):
        found.add(match.group(1))
    found.discard(node["sobject"])
    found.discard("RecordType")
    return sorted(found)


def match_rule(node):
    lookup = node.get("lookup")
    if not lookup:
        return "always creates"

    def walk(predicate):
        operands = predicate.get("operands") or []
        if operands:
            return "(" + f" {(predicate.get('operator') or 'and').upper()} ".join(walk(o) for o in operands) + ")"
        return f"{predicate.get('left_field') or '?'} = {predicate.get('right_kind') or '?'}"
    rule = walk(lookup.get("predicate") or {})
    return f"{rule}; several: {lookup.get('on_multiple_matches') or '?'}"


def classify(form_id, document, models, labels):
    """One entry per distinct object step in the form, with its controller rule."""
    labels_in_repeats = repeat_labels(document)
    steps, seen_paths = [], set()
    mirrored = {}
    for model in models:
        for branch in model.get("branches", []):
            for overlap in branch.get("overlaps", []):
                if overlap.get("overlap_ratio", 0) >= 0.8:
                    mirrored[overlap["with_root"]] = branch["root"]
        nodes = nodes_of(model)
        by_id = {n.get("node_id"): n for n in nodes}
        for node in nodes:
            if not node.get("sobject") or node["order_path"] in seen_paths:
                continue
            seen_paths.add(node["order_path"])
            root = node["order_path"].split(".")[0]
            sources = {re.sub(r"^(?:a field in your form|a Salesforce field)\s*", "", m.get("source_value", "")).strip() for m in node.get("mappings", []) if m.get("source_kind") == "form_field"}
            dead = bool(sources) and all("Not set" in source or "missing field" in source for source in sources)
            record_type = record_type_of(node)
            steps.append({
                "order_path": node["order_path"],
                "mirror_of": mirrored.get(root),
                "object": node["sobject"],
                "action": archive.effective_action(node),
                "match": match_rule(node),
                "record_type": build.resolve(record_type, labels) if record_type else None,
                "dead": dead,
                "depends_on": depends_on(node, by_id),
                "mappings": len(node.get("mappings", [])),
                "from_repeating_section": bool(sources & labels_in_repeats),
                "skip_if": node.get("skip_if"),
                "payment": node["sobject"] in PAYMENT_OBJECTS or any("AUTHORIZE" in (m.get("source_value") or "") for m in node.get("mappings", [])),
            })

    seen_slots = {}
    for step in steps:
        obj = step["object"]
        if step["dead"]:
            step["rule"], step["kind"] = f"drop: {obj} step on deleted fields", "dead"
        elif step["action"] == "lookup":
            step["rule"], step["kind"] = "match only (finds a record for later steps)", "match"
        elif step["payment"]:
            step["rule"], step["kind"] = "Payment (the org's payment setup)", "payment"
        elif obj in FILE_OBJECTS:
            step["rule"], step["kind"] = "Files", "packaged"
        elif obj in SIDE_RECORDS:
            step["rule"], step["kind"] = f"{obj} side record (synchronous subflow from its parent step)", "side"
        elif obj == "CampaignMember":
            step["rule"], step["kind"] = "Campaign Member (chained from Contact or Lead)", "packaged"
        elif step["from_repeating_section"] and step["action"] == "create":
            step["rule"], step["kind"] = f"Related Records: {obj} rows", "related"
        elif obj in ("Account", "Opportunity", "Case"):
            step["rule"], step["kind"] = obj, "packaged"
        elif obj in ("Contact", "Lead"):
            step["rule"], step["kind"] = obj, "packaged"
        else:
            step["rule"], step["kind"] = f"New rule: {obj}", "new"
        if step["kind"] == "packaged" and obj in ("Contact", "Lead") and not step["mirror_of"]:
            key = (obj, step["order_path"].split(".")[0])
            slots = seen_slots.setdefault(obj, [])
            if step["action"] != "lookup" and key not in slots:
                slots.append(key)
            number = slots.index(key) + 1 if key in slots else 1
            step["rule"] = f"{obj} {number}" if number <= 2 else f"New rule: {obj} {number}"
            step["kind"] = "packaged" if number <= 2 else "new"
        elif step["kind"] == "packaged" and obj in ("Contact", "Lead"):
            step["rule"] = f"{obj} 1"
    return steps


def position(rule, new_rules_after):
    """Packaged rules keep the controller's order; new rules slot in after Case, in dependency order."""
    if rule in CONTROLLER_ORDER:
        return CONTROLLER_ORDER.index(rule)
    if rule.startswith("Related Records"):
        return CONTROLLER_ORDER.index("Related Records")
    if rule == "Files":
        return CONTROLLER_ORDER.index("Files")
    return CONTROLLER_ORDER.index("Case") + 0.01 * (1 + new_rules_after.get(rule, 0))


def prefill_plan(form_id, bundle):
    lookups = [lookup for found in bundle.get("prefill", {}).values() for lookup in found]
    if not lookups:
        return None
    entries, chain = [], []
    for lookup in lookups:
        url = [c for c in lookup["conditions"] if c["value_kind"] == "url_parameter"]
        fixed = [f"{c['field_label']} {c['operator'].lower()} {c['value']}" for c in lookup["conditions"] if c["value_kind"] == "formula"]
        linked = [f"{c['field_label']} from {c['value']}" for c in lookup["conditions"] if c["value_kind"] == "lookup_result"]
        item = {
            "number": lookup["number"], "object": lookup["sobject"], "fixed_filters": fixed, "linked_by": linked,
            "repeat_section": lookup.get("repeat_section"), "several": lookup["on_multiple_matches"], "fills": len(lookup["mappings"]),
        }
        if url:
            item["entry"] = [{"parameter": c["value"], "field": c["field_label"]} for c in url]
            entries.append(item)
        else:
            chain.append(item)
    return {"entries": entries, "chain": chain}


def existing_controllers(paths):
    """Controller clones already in the project: flow name -> its rule names and each rule's Conversion_Rules__c value."""
    found = {}
    for path in paths:
        for flow in glob.glob(os.path.join(path, "**", "flows", "*Convert_Process_Form_Submission*.flow-meta.xml"), recursive=True):
            name = os.path.basename(flow).replace(".flow-meta.xml", "")
            if name.startswith("FlowToolKit__"):
                continue
            with open(flow, encoding="utf-8") as handle:
                text = handle.read()
            values = {}
            for formula in re.findall(r"<formulas>(.*?)</formulas>", text, re.S):
                formula_name = re.search(r"<name>Includes_(\w+)</name>", formula)
                value = re.search(r"INCLUDES\([^,]+,\s*&apos;([^&]+)&apos;\)", formula)
                if formula_name and value:
                    values["Convert_" + formula_name.group(1)] = value.group(1)
            found[name] = {"rules": re.findall(r"<rules>\s*<name>(Convert_\w+)</name>", text), "values": values}
    return found


def rule_value(rule, existing_values):
    """The Conversion_Rules__c value a template selects for a plan rule, or how the rule runs instead."""
    if rule in PACKAGED_VALUE:
        return PACKAGED_VALUE[rule]
    if rule.startswith("Related Records"):
        return "Related Records (plus a section-level Conversion_Map_Flow__c on the repeating section)"
    if rule.startswith("Campaign Member"):
        return "Contact1 👉 Create Campaign Member"
    if rule == "Files":
        return "none: runs when the form has file uploads"
    if rule.startswith("Payment"):
        return "none: the org's payment setup"
    if "side record" in rule:
        return "none: subflow inside its parent step"
    if rule in existing_values:
        return f"{existing_values[rule]} (exists in the clone)"
    if rule.startswith("New rule: "):
        label = re.sub(r"__c$", "", rule[len("New rule: "):]).replace("_", " ")
        return f"{label} (new value to add)"
    return rule


def covered_by(rule_object, rule_names):
    """The existing rule that converts this object, matched on the words in the names."""
    words = set(re.sub(r"__c$", "", rule_object).lower().split("_")) - {"a", "c"}
    for rule_name in rule_names:
        rule_words = set(rule_name.lower().split("_")) - {"convert"}
        if rule_words and (rule_words <= words or len(rule_words & words) >= 2):
            return rule_name
    return None


def controller_decision(per_form, rules, conflicts, depth, existing):
    """Per form: packaged, extended or bespoke controller; account: one extended clone, how it is selected, bespoke candidates."""
    new_rules = {r["rule"]: r for r in rules.values() if r["kind"] == "new"}
    hold_back = {}
    for conflict in conflicts:
        rule = conflict.split(" uses the ")[0]
        hold_back.setdefault(rule, []).append(conflict)
    decisions = {}
    for form_id, item in per_form.items():
        own_new = [r for r in item["rules"] if r in new_rules]
        exclusive = [r for r in own_new if len(new_rules[r]["forms"]) == 1]
        chain = max((depth.get(r, 0) for r in own_new), default=0)
        reasons = []
        if len(exclusive) >= 3:
            reasons.append(f"{len(exclusive)} custom objects only this form converts")
        if chain >= 2:
            reasons.append(f"custom records {chain + 1} levels deep (records created from records created from records)")
        if reasons:
            choice = "bespoke"
        elif own_new or any(r in hold_back and set(rules[r]["forms"]) & {form_id} for r in item["rules"]):
            choice = "extended"
        else:
            choice = "packaged"
        decisions[form_id] = {"controller": choice, "new_rules": own_new, "reasons": reasons}

    extended_forms = [f for f, d in decisions.items() if d["controller"] == "extended"]
    bespoke_forms = [f for f, d in decisions.items() if d["controller"] == "bespoke"]
    extension_rules = []
    for rule in rules.values():
        if rule["kind"] == "new" and set(rule["forms"]) & set(extended_forms):
            extension_rules.append(rule["rule"])
    clone = None
    coverage = {}
    for name, info in existing.items():
        hits = {r: covered_by(rules[r]["object"], info["rules"]) for r in extension_rules}
        hits = {r: h for r, h in hits.items() if h}
        if len(hits) > len(coverage):
            clone, coverage = name, hits
    converting = len(per_form)
    share = len(extended_forms) / converting if converting else 0
    selection = (
        "Override: make the extended clone the org default (repoint the Controller record of Form_Template_Conversion_Mapping_Default__mdt). Its added rules only run when a template switches them on, so templates that need nothing new behave as before."
        if share >= 0.8 else
        "Extend, selected per template: add the clone as a Conversion_Map_Flow_Controller__c value and pick it on the templates listed. The other templates keep the packaged controller."
    )
    return {
        "per_form": decisions,
        "extended": {
            "forms": extended_forms,
            "rules_to_add": extension_rules,
            "existing_clone": clone,
            "already_in_clone": coverage,
            "hold_back": {r: c for r, c in hold_back.items() if set(rules[r]["forms"]) & set(extended_forms)},
            "selection": selection,
            "share": round(share, 2),
        },
        "bespoke_candidates": bespoke_forms,
        "packaged_forms": [f for f, d in decisions.items() if d["controller"] == "packaged"],
    }


def collapse_chain(chain):
    """Consecutive lookups of one object that each exclude the previous ones are one Related Records call."""
    collapsed = []
    for link in chain:
        excludes = any("from" in text and re.search(r"(?i)contact id|\bid\b", text) for text in link["linked_by"]) and len(link["linked_by"]) > 1
        last = collapsed[-1] if collapsed else None
        if last and last["object"] == link["object"] and excludes and not link["repeat_section"]:
            last["count"] = last.get("count", 1) + 1
            last["fills"] = max(last["fills"], link["fills"])
            continue
        collapsed.append(dict(link))
    return collapsed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default="_formassembly")
    parser.add_argument("--source", action="append", default=None, help="source folder to scan for controller clones; default every force-app* folder")
    args = parser.parse_args(argv)
    sources = args.source or sorted(glob.glob("force-app*"))
    inventory = archive.load_inventory(args.root)
    folder = archive.paths(args.root)["archive"]
    name = archive.name_of(inventory)

    kept = archive.load_kept(args.root)
    forms, prefills = {}, {}
    for form_id in sorted(os.listdir(folder)):
        path = os.path.join(folder, form_id, "ir.json")
        if form_id not in inventory or not os.path.exists(path) or (kept is not None and form_id not in kept):
            continue
        bundle = archive.load_json(path)
        models = [bundle["form"].get("connector") or {}] + list(bundle.get("additional_submit_connectors", {}).values())
        with open(os.path.join(folder, form_id, "form.html"), encoding="utf-8", errors="replace") as handle:
            labels = build.label_map(bundle["form"], handle.read())
        steps = classify(form_id, bundle["form"], models, labels)
        if steps:
            forms[form_id] = steps
        plan = prefill_plan(form_id, bundle)
        if plan:
            prefills[form_id] = plan

    rules = {}
    for form_id, steps in forms.items():
        for step in steps:
            if step["kind"] in ("match", "dead"):
                continue
            rule = rules.setdefault(step["rule"], {"rule": step["rule"], "kind": step["kind"], "object": step["object"], "forms": set(), "actions": set(), "match_rules": set(), "record_types": set(), "depends_on": set(), "mirrored_paths": 0})
            rule["forms"].add(form_id)
            rule["actions"].add(step["action"])
            rule["match_rules"].add(step["match"])
            if step["record_type"]:
                rule["record_types"].add(step["record_type"])
            rule["depends_on"].update(step["depends_on"])
            rule["mirrored_paths"] += 1 if step["mirror_of"] else 0

    object_rule = {}
    for rule in rules.values():
        object_rule.setdefault(rule["object"], []).append(rule["rule"])
    pending = [r for r in rules.values() if r["kind"] in ("new", "side", "payment")]
    depth = {}
    for _ in range(len(pending) + 1):
        for rule in pending:
            parents = [depth.get(other, 0) + 1 for obj in rule["depends_on"] for other in object_rule.get(obj, []) if other != rule["rule"] and other in {p["rule"] for p in pending}]
            depth[rule["rule"]] = max(parents, default=0)
    new_after = depth
    ordered = sorted(rules.values(), key=lambda r: (position(r["rule"], new_after), r["rule"]))

    conflicts = []
    for rule in ordered:
        here = position(rule["rule"], new_after)
        for obj in rule["depends_on"]:
            for other in object_rule.get(obj, []):
                if position(other, new_after) > here:
                    conflicts.append(f"{rule['rule']} uses the {obj} record, but {other} runs later in the controller")

    per_form = {}
    for form_id, steps in forms.items():
        enabled = sorted({s["rule"] for s in steps if s["kind"] not in ("match", "dead")}, key=lambda r: position(r, new_after))
        notes = [f"drop step {s['order_path']} ({s['action']} {s['object']}): its fields were deleted" for s in steps if s["kind"] == "dead"]
        mirrored = sorted({s["mirror_of"] for s in steps if s["mirror_of"]})
        if mirrored:
            notes.append(f"FormAssembly repeats the same steps on mirrored paths (roots {', '.join(mirrored)} and their copies): one pipeline in the rebuild")
        repeats = {}
        for s in steps:
            repeats[(s["object"], s["action"])] = repeats.get((s["object"], s["action"]), 0) + 1
        for (obj, action), count in repeats.items():
            if count > 1 and action != "lookup" and not any(s["kind"] in ("related", "dead") for s in steps if s["object"] == obj):
                notes.append(f"{action} {obj} appears {count} times: alternative paths, or one record per slot (check the skip rules); slots usually become Related Records")
        per_form[form_id] = {"rules": enabled, "notes": notes}

    existing = existing_controllers(sources)
    controller = controller_decision(per_form, rules, conflicts, new_after, existing)
    clone_values = {}
    if controller["extended"]["existing_clone"]:
        clone_values_by_rule = existing[controller["extended"]["existing_clone"]]["values"]
        clone_values = {plan_rule: clone_values_by_rule[clone_rule] for plan_rule, clone_rule in controller["extended"]["already_in_clone"].items() if clone_rule in clone_values_by_rule}
    for item in per_form.values():
        item["conversion_rule_values"] = list(dict.fromkeys(rule_value(rule, clone_values) for rule in item["rules"]))
    kinds_by_object = {}
    for rule in rules.values():
        kinds_by_object.setdefault(rule["object"], set()).add(rule["kind"])
    two_ways = {obj: sorted(kinds) for obj, kinds in kinds_by_object.items() if len(kinds & {"new", "related", "packaged"}) > 1}

    groups = {}
    for form_id, plan in prefills.items():
        for entry in plan["entries"][:1]:
            group = groups.setdefault(entry["object"], {"object": entry["object"], "matched_on": set(), "parameters": set(), "forms": {}})
            for key in entry["entry"]:
                group["matched_on"].add(key["field"])
                group["parameters"].add(key["parameter"])
            group["forms"][form_id] = {"matched_on": [k["field"] for k in entry["entry"]], "fixed_filters": entry["fixed_filters"], "chain": collapse_chain(plan["entries"][1:] + plan["chain"])}

    result = {
        "conversion_rules": [{**r, "forms": sorted(r["forms"]), "actions": sorted(r["actions"]), "match_rules": sorted(r["match_rules"]), "record_types": sorted(r["record_types"]), "depends_on": sorted(r["depends_on"])} for r in ordered],
        "conflicts": conflicts,
        "controller": controller,
        "planned_two_ways": two_ways,
        "forms": per_form,
        "prefill_flows": [{**g, "parameters": sorted(g["parameters"]), "matched_on": sorted(g["matched_on"])} for g in sorted(groups.values(), key=lambda g: -len(g["forms"]))],
        "prefill_without_entry": sorted(f for f, p in prefills.items() if not p["entries"]),
    }
    archive.write_json(os.path.join(args.root, "flow-plan.json"), result)

    out = ["# Flow plan", "", "FormAssembly runs one prefill and one submit connector per form. In Flow Tool Kit, conversion flows are shared per object and run by the controller in a fixed order, and prefill flows are shared per entry record. This plan lists what to build once and which Form Templates use it. Generated by flow_plan.py; build with new-mapping-flow.", ""]
    packaged = [r for r in ordered if r["kind"] == "packaged"]
    new = [r for r in ordered if r["kind"] in ("new", "related", "side")]
    out += [f"**{len(forms)} forms with submit connectors need {len(ordered)} conversion rules: {len(packaged)} packaged, {len(new)} to build or configure. {len(groups)} shared prefill flows cover {len(prefills)} prefill forms.**", ""]
    ext = controller["extended"]
    out += ["## Controller", "", "The controller choice (new-mapping-flow Step 2 and references/new-object-rule.md) applied to this account: each form runs on the packaged controller, on one extended clone (selected per template, or made the default as an override), or on a bespoke controller for a workflow too custom to share. The script proposes; a person decides, especially for bespoke.", ""]
    out += ["| Controller | Forms | Why |", "|---|---|---|"]
    out.append(f"| Packaged (no change) | {len(controller['packaged_forms'])}: {', '.join(name(f) for f in controller['packaged_forms']) or '-'} | Only packaged rules, no ordering conflict |")
    out.append(f"| Extended clone | {len(ext['forms'])}: {', '.join(name(f) for f in ext['forms']) or '-'} | Needs new object rules or a hold-back the packaged controller cannot express |")
    for form_id in controller["bespoke_candidates"]:
        out.append(f"| Bespoke candidate: {name(form_id)} ({form_id}) | 1 | {'; '.join(controller['per_form'][form_id]['reasons'])} |")
    out += ["", f"**Extended clone.** " + (f"Extend the existing `{ext['existing_clone']}` ({len(ext['already_in_clone'])} of its rules already cover this plan: {', '.join(f'{r} = {h}' for r, h in ext['already_in_clone'].items())}). " if ext["existing_clone"] else "Clone `Form_Submission_Convert_Process_Form_Submission_Template`. ") + f"Rules to add after Case, in this order: {', '.join(r for r in [x['rule'] for x in ordered] if r in ext['rules_to_add'] and r not in ext['already_in_clone']) or 'none'}.", ""]
    if ext["hold_back"]:
        out += ["Hold-back gates (the rule waits until the record it needs exists; new-mapping-flow references/extension-patterns.md, Ordering: hold back, never reorder):", ""] + [f"- {c}" for cs in ext["hold_back"].values() for c in cs] + [""]
    out += [f"**How it is selected.** {ext['selection']} ({int(ext['share'] * 100)}% of converting forms need it.)", ""]
    out += ["**Each new rule needs**: a `Conversion_Rules__c` value for templates to switch it on (added in your org, new-mapping-flow Step 7, Picklist values you add), a Form Submission lookup plus a `Conversion_Status_<Rule>__c` picklist on the `Conversion_Status` value set, an `Includes_<Rule>` formula gating the decision outcome, and its Process (+ Upsert) flow (new-mapping-flow Step 3 and references/new-object-rule.md).", ""]
    if controller["bespoke_candidates"]:
        out += ["**Bespoke candidates.** A separate controller with its own order and gating, selected only on that template. Choose it when the workflow is mostly custom records chained to each other; otherwise fold its rules into the extended clone.", ""]
    out += ["## Conversion rules, in controller order", "", "| Rule | Object | Kind | Forms | Actions | Match rules | Record types | Uses |", "|---|---|---|---|---|---|---|---|"]
    for r in result["conversion_rules"]:
        out.append(f"| {r['rule']} | {r['object']} | {r['kind']} | {len(r['forms'])}: {', '.join(name(f) for f in r['forms'][:6])}{' ...' if len(r['forms']) > 6 else ''} | {', '.join(r['actions'])} | {len(r['match_rules'])} variant(s) | {', '.join(r['record_types']) or '-'} | {', '.join(r['depends_on']) or '-'} |")
    out += ["", "Kinds: **packaged** is a controller rule Flow Tool Kit already ships (configure the template; on a paid org map the answers with Form Template Mapping, on a free org with the flow's Transform; clone the Process flow only if the mapping needs logic); **new** needs a Process + Upsert pair and a controller slot (new-mapping-flow Step 3); **related** is repeating-section rows converted through Related Records with a section-level map flow; **side** is a linked record written by a synchronous subflow from its parent step; **payment** is rebuilt with the org's payment setup.", ""]
    out += ["## Order conflicts", ""] + ([f"- {c}" for c in conflicts] or ["None found: every rule's records come from rules that run before it."])
    if two_ways:
        out += ["", "## Objects planned two ways", "", "The same object converts as a new rule in some forms and as repeating-section rows (or a packaged rule) in others. Build it one way: usually the Related Records map flow, with single-record forms using a one-row section. Decide before building so the object gets one flow.", ""]
        out += [f"- **{obj}**: {', '.join(kinds)} ({'; '.join(r['rule'] + ' in ' + ', '.join(name(f) for f in r['forms']) for r in ordered if r['object'] == obj)})" for obj, kinds in two_ways.items()]
    out += ["", "## Each form's rules", "", "`Conversion_Rules__c` lists the values the form's template selects (pick the Conversion Type that offers them); entries marked none run another way.", "", "| Form | Rules, in run order | `Conversion_Rules__c` | Notes |", "|---|---|---|---|"]
    for form_id, item in sorted(per_form.items(), key=lambda kv: name(kv[0]).lower()):
        out.append(f"| {name(form_id)} ({form_id}) | {' > '.join(item['rules'])} | {'; '.join(item['conversion_rule_values'])} | {'; '.join(item['notes']) or '-'} |")
    out += ["", "## Match rules by rule", ""]
    for r in result["conversion_rules"]:
        if r["kind"] in ("packaged", "new"):
            out.append(f"- **{r['rule']}**: " + "; ".join(r["match_rules"][:4]) + (" ..." if len(r["match_rules"]) > 4 else ""))
    out += ["", "## Prefill flows", "", "One prefill flow per entry record. Flow Tool Kit passes the entry record's Id in a URL parameter that the Form Template writes to a Form Submission lookup; the flow reads `record.<lookup>`, gets the records, and fills the form with the **Prefill From Mapped Record** action (Single Record per record, Related Records for repeating sections). Each template then adds only its own extra lookups.", "", "| Prefill flow (entry record) | FormAssembly matched on | URL parameters | Submission lookup | Forms |", "|---|---|---|---|---|"]
    for g in result["prefill_flows"]:
        lookup = SUBMISSION_LOOKUP.get(g["object"], f"new lookup to {g['object']}")
        out.append(f"| {g['object']} | {', '.join(g['matched_on'])} | {', '.join('`' + p + '`' for p in g['parameters'])} | {lookup} | {len(g['forms'])}: {', '.join(name(f) for f in g['forms'])} |")
    out += ["", "Where FormAssembly matched on something other than the record Id (a membership or renter number), decide per flow: pass the record Id in the link instead (the safer choice, rebuild check 9), or keep a search step that finds the record from the number first.", ""]
    for g in result["prefill_flows"]:
        out += [f"### {g['object']} prefill flow", ""]
        for form_id, item in g["forms"].items():
            out.append(f"- **{name(form_id)}** ({form_id}), matched on {', '.join(item['matched_on'])}" + (f", also filters {'; '.join(item['fixed_filters'])}" if item["fixed_filters"] else ""))
            for link in item["chain"]:
                if link.get("count", 1) > 1:
                    mode = f"one Related Records call for {link['count']} records, each excluding the ones before"
                else:
                    mode = f"Related Records into [{link['repeat_section']}]" if link["repeat_section"] else "Single Record"
                extra = "; ".join(link["linked_by"] + link["fixed_filters"])
                out.append(f"  - then {link['object']} ({mode}, {link['fills']} fields){': ' + extra if extra else ''}")
        out.append("")
    if result["prefill_without_entry"]:
        out += ["Prefill connectors with no URL parameter (they match on fixed values only): " + ", ".join(f"{name(f)} ({f})" for f in result["prefill_without_entry"]), ""]
    with open(os.path.join(args.root, "flow-plan.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    print(f"forms {len(forms)}  rules {len(ordered)} (packaged {len(packaged)}, to build {len(new)})  conflicts {len(conflicts)}  prefill flows {len(groups)} for {len(prefills)} forms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
