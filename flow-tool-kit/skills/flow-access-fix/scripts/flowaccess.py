#!/usr/bin/env python3
"""Flow access for Flow Tool Kit forms: find why a flow refuses a guest, portal or
internal user, and write the metadata that fixes it.

Commands (Python 3.9+, standard library only):

  inspect FLOW_FILE [--audience guest|portal|internal ...] [--json]
      What the flow needs to run for each audience: is it restricted, its run mode,
      the subflows and Apex actions it calls, the records it reads and writes.

  restrict FLOW_FILE [--write]
      Step one: set isAdditionalPermissionRequiredToRun to true.

  grant PERMSET_FILE --flow NAME [--flow NAME ...] [--apex CLASS ...]
        [--create --label LABEL --description TEXT] [--write]
      Step two: add Flow Access (and Apex Class Access) to the org's own
      permission set file, or create one.

  sharing-proposal FLOW_FILE --site SITE_NAME [--existing SHARING_FILE ...] [--json]
      The narrowest guest sharing rule for each object the flow reads, and
      whether a rule for that site already covers it.

  sharing-rule --object OBJ --site SITE_NAME --name API_NAME --label LABEL
               --criterion FIELD:OPERATION:VALUE [...] [--description TEXT]
               --out DIR [--write]
      Writes (or merges) one read-only guest sharing rule into
      DIR/sharingRules/OBJ.sharingRules-meta.xml.

  guest-copy upsert|prefill SOURCE_FILE --templates TEMPLATES.json --out DIR
             [--status Draft|Active] [--write]
      The org's own system-mode copy of a packaged flow, made from the packaged
      flow retrieved from the same org, and only when a guest template needs it:
      (Form) Upsert | Guest Override when one uses Save Progress, Stages or
      Autosave, (Form) Prefill | Guest Resume when one sends resume links.
      Otherwise it says why and builds nothing.

  queries --flow API_NAME [--site SITE_NAME | --user USERNAME] [--object OBJ ...]
      The read-only SOQL behind every check, for a Salesforce connector in chat.

  diagnose --org ALIAS --flow API_NAME [--site SITE_NAME | --user USERNAME] [--json]
      Claude Code only (runs the Salesforce CLI): the two-step verdict for one
      flow and one running user, following an active override to the flow that
      really runs.

Without --write, the editing commands print what they would change and touch
nothing. Exit codes: 0 fine, 1 findings that block the audience or a refused
input, 2 usage or file error.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

MD = "http://soap.sforce.com/2006/04/metadata"
NS = {"m": MD}
ET.register_namespace("", MD)
XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'
AUDIENCES = ("guest", "portal", "internal")
PACKAGE_NS = "FlowToolKit"

# Flow filter operators that a criteria-based sharing rule can express.
OPERATORS = {
    "EqualTo": "equals",
    "NotEqualTo": "notEqual",
    "GreaterThan": "greaterThan",
    "LessThan": "lessThan",
    "GreaterThanOrEqualTo": "greaterOrEqual",
    "LessThanOrEqualTo": "lessOrEqual",
    "Contains": "contains",
    "StartsWith": "startsWith",
}
SHARING_OPERATIONS = {"equals", "notEqual", "lessThan", "greaterThan", "lessOrEqual",
                      "greaterOrEqual", "contains", "notContain", "startsWith",
                      "includes", "excludes"}

COPIES = {
    "upsert": {
        "source": "Form_Submission_Upsert",
        "api_name": "Form_Submission_Upsert_Guest",
        "label": "(Form) Upsert | Guest Override",
        "override": True,
        "description": (
            "The org's own override of the packaged (Form) Upsert | Overridable flow, so site guests can "
            "save a form more than once: Save Progress, Stages Mode, Autosave, and a save that points at a "
            "record the guest cannot read. Runs in System Context Without Sharing because a guest can create "
            "a Form Submission but never update one. While active it replaces the packaged save flow for "
            "every form and every user, so anyone who fills in a form needs Flow Access to it (the guest "
            "through Form Flow (Guest User)). Keep it to saving the submission it receives. After a Flow "
            "Tool Kit upgrade, compare it with the packaged flow and copy in what changed."
        ),
    },
    "prefill": {
        "source": "Form_Submission_Prefill",
        "api_name": "Form_Submission_Prefill_Guest",
        "label": "(Form) Prefill | Guest Resume",
        "override": False,
        "description": (
            "The org's own copy of the packaged (Form) Prefill | Template flow, so a site guest's resume "
            "link reopens the saved draft. Runs in System Context Without Sharing because a guest cannot "
            "read a submission once it is saved. It reads only the one submission whose single-use token "
            "is in the link, matched with its Form Template, and clears the token. Choose it as the Prefill "
            "Flow on every Form Template whose guests should resume; a template on Bypass uses the packaged "
            "flow, which cannot open a guest's draft. Anyone holding a valid link can open that draft. After "
            "a Flow Tool Kit upgrade, compare it with the packaged flow and copy in what changed."
        ),
    },
}


class InputError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise InputError("cannot read %s: %s" % (path, error.strerror))


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def parse_xml(text, path):
    try:
        return ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as error:
        raise InputError("%s is not valid XML: %s" % (path, error))


def tag(element):
    return element.tag.split("}", 1)[-1]


def child_text(element, name, default=None):
    found = element.find("m:" + name, NS)
    return found.text if found is not None and found.text is not None else default


def flow_api_name(path):
    base = os.path.basename(path)
    for suffix in (".flow-meta.xml", ".flow"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return os.path.splitext(base)[0]


def serialize(root):
    ET.indent(root, space="    ")
    return XML_DECL + ET.tostring(root, encoding="unicode") + "\n"


def escape_xml(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def top_level(name):
    """A top-level element of a flow file: exactly four spaces of indent."""
    return re.compile(r"^    <%s>.*?</%s>\n" % (name, name), re.M | re.S)


def show_or_write(path, old, new, write):
    if old == new:
        print("unchanged: %s" % path)
        return False
    if write:
        write_text(path, new)
        print("wrote: %s" % path)
    else:
        print("would change: %s (run again with --write)" % path)
    return True


# ---------------------------------------------------------------- flow reading

def filter_value(value):
    """(kind, text) for a flow <value>: kind is 'constant', 'reference' or 'formula'."""
    if value is None:
        return ("none", "")
    for child in value:
        name = tag(child)
        text = child.text or ""
        if name == "booleanValue":
            return ("constant", "True" if text.lower() == "true" else "False")
        if name in ("stringValue", "numberValue", "dateValue", "dateTimeValue"):
            return ("constant", text)
        if name == "elementReference":
            if text == "$GlobalConstant.True":
                return ("constant", "True")
            if text == "$GlobalConstant.False":
                return ("constant", "False")
            if text == "$GlobalConstant.EmptyString":
                return ("constant", "")
            return ("reference", text)
        if name == "formulaExpression":
            return ("formula", text)
    return ("none", "")


def read_filters(element):
    filters = []
    for item in element.findall("m:filters", NS):
        kind, text = filter_value(item.find("m:value", NS))
        filters.append({
            "field": child_text(item, "field", ""),
            "operator": child_text(item, "operator", ""),
            "value_kind": kind,
            "value": text,
        })
    return filters


def read_flow(path):
    text = read_text(path)
    root = parse_xml(text, path)
    if tag(root) != "Flow":
        raise InputError("%s is not a flow file" % path)
    variables = {}
    for var in root.findall("m:variables", NS):
        variables[child_text(var, "name", "")] = child_text(var, "objectType")
    flow = {
        "file": path,
        "api_name": flow_api_name(path),
        "label": child_text(root, "label", ""),
        "process_type": child_text(root, "processType", ""),
        "status": child_text(root, "status", ""),
        "run_in_mode": child_text(root, "runInMode", "DefaultMode"),
        "restricted": (child_text(root, "isAdditionalPermissionRequiredToRun", "false") or "").lower() == "true",
        "overridable": (child_text(root, "isOverridable", "false") or "").lower() == "true",
        "template": (child_text(root, "isTemplate", "false") or "").lower() == "true",
        "overridden_flow": child_text(root, "overriddenFlow"),
        "has_description": bool(child_text(root, "description")),
        "subflows": sorted({child_text(s, "flowName", "") for s in root.findall("m:subflows", NS)} - {""}),
        "apex_actions": sorted({child_text(a, "actionName", "") for a in root.findall("m:actionCalls", NS)
                                if child_text(a, "actionType", "") == "apex"} - {""}),
        "reads": [],
        "writes": [],
    }
    for lookup in root.findall("m:recordLookups", NS):
        fields = [q.text for q in lookup.findall("m:queriedFields", NS) if q.text]
        flow["reads"].append({
            "element": child_text(lookup, "name", ""),
            "kind": "Get Records",
            "object": child_text(lookup, "object", ""),
            "filters": read_filters(lookup),
            "filter_logic": child_text(lookup, "filterLogic", "and"),
            "fields": fields,
            "all_fields": not fields and (child_text(lookup, "storeOutputAutomatically", "false") or "").lower() == "true",
        })
    for choices in root.findall("m:dynamicChoiceSets", NS):
        obj = child_text(choices, "object")
        if not obj:
            continue  # picklist or collection choice sets read no records
        fields = [f for f in (child_text(choices, "displayField"), child_text(choices, "valueField")) if f]
        fields += [child_text(o, "field") for o in choices.findall("m:outputAssignments", NS) if child_text(o, "field")]
        flow["reads"].append({
            "element": child_text(choices, "name", ""),
            "kind": "Record Choice Set",
            "object": obj,
            "filters": read_filters(choices),
            "filter_logic": child_text(choices, "filterLogic", "and"),
            "fields": sorted(set(fields)),
            "all_fields": False,
        })
    for kind, name in (("recordCreates", "Create"), ("recordUpdates", "Update"), ("recordDeletes", "Delete")):
        for element in root.findall("m:" + kind, NS):
            obj = child_text(element, "object")
            if not obj:
                ref = (child_text(element, "inputReference") or "").split(".")[0]
                obj = variables.get(ref) or "(from variable %s)" % ref
            flow["writes"].append({"element": child_text(element, "name", ""), "kind": name, "object": obj})
    return flow


def findings_for(flow, audiences):
    """List of (level, audience, message). level is 'error' or 'warn'."""
    out = []
    system = flow["run_in_mode"] in ("SystemModeWithoutSharing", "SystemModeWithSharing")
    for audience in audiences:
        if audience in ("guest", "portal") and not flow["restricted"]:
            out.append(("error", audience,
                        "not restricted: a %s user can never run it. Step one: restrict it (restrict)." % audience))
        if audience in ("guest", "portal"):
            out.append(("warn", audience,
                        "Step two: a permission set of the %s's own must grant %s (grant). The package's permission sets cannot grant your flows." % (audience, flow["api_name"])))
        if audience == "internal" and flow["restricted"]:
            out.append(("warn", audience,
                        "restricted: internal users need a permission set that grants it too, Run Flows is not enough."))
        for sub in flow["subflows"]:
            out.append(("warn", audience, "calls subflow %s: it needs the same two steps for this audience." % sub))
        for apex in flow["apex_actions"]:
            out.append(("warn", audience, "calls Apex action %s: grant Apex Class Access for its class (packaged actions come with Form Flow User)." % apex))
        if not system:
            for read in flow["reads"]:
                if audience == "guest":
                    out.append(("warn", audience, "%s %s reads %s: guests see none of its records without a guest sharing rule, plus Read on the object and its fields (sharing-proposal)." % (read["kind"], read["element"], read["object"])))
                elif audience == "portal":
                    out.append(("warn", audience, "%s %s reads %s: portal users see only what the external sharing model, sharing sets or sharing rules give them, plus Read on the object and its fields." % (read["kind"], read["element"], read["object"])))
                if read["all_fields"]:
                    out.append(("warn", audience, "%s stores every field of %s: choose only the fields the screen shows." % (read["element"], read["object"])))
        if audience == "guest":
            for write in flow["writes"]:
                if write["kind"] in ("Update", "Delete") and not system:
                    out.append(("error", audience, "%s %s on %s: a guest can never update or delete records. Hand the values back to the form instead." % (write["kind"], write["element"], write["object"])))
                elif write["kind"] == "Create":
                    out.append(("warn", audience, "creates %s in %s: the guest needs Create on it. A Flow Section should hand values back to the form instead." % (write["object"], write["element"])))
        if system:
            out.append(("warn", audience, "runs in %s: record access is not checked. Its description must say why, and it must return only what the screen shows." % flow["run_in_mode"]))
            if not flow["has_description"]:
                out.append(("error", audience, "runs in system context with no description saying why."))
    return out


def cmd_inspect(args):
    flow = read_flow(args.flow_file)
    audiences = args.audience or list(AUDIENCES)
    findings = findings_for(flow, audiences)
    if args.json:
        print(json.dumps({"flow": flow, "findings": [
            {"level": level, "audience": aud, "message": msg} for level, aud, msg in findings]}, indent=2))
    else:
        print("%s (%s)" % (flow["api_name"], flow["label"] or "no label"))
        print("  type %s, status %s, run mode %s" % (flow["process_type"] or "?", flow["status"] or "?", flow["run_in_mode"]))
        print("  restricted (requires permission to run): %s" % ("yes" if flow["restricted"] else "NO"))
        if flow["overridden_flow"]:
            print("  overrides: %s" % flow["overridden_flow"])
        for read in flow["reads"]:
            crit = ", ".join("%s %s %s" % (f["field"], f["operator"], f["value"] if f["value_kind"] == "constant" else "{%s}" % f["value"]) for f in read["filters"]) or "no filter"
            print("  reads %s in %s (%s)" % (read["object"], read["element"], crit))
        for write in flow["writes"]:
            print("  %s %s in %s" % (write["kind"].lower(), write["object"], write["element"]))
        for level, aud, msg in findings:
            print("  [%s] %s: %s" % (level.upper(), aud, msg))
    return 1 if any(level == "error" for level, _, _ in findings) else 0


# ---------------------------------------------------------------- step one

def restrict_text(text):
    if re.search(r"^    <isAdditionalPermissionRequiredToRun>true</isAdditionalPermissionRequiredToRun>", text, re.M):
        return text
    line = "    <isAdditionalPermissionRequiredToRun>true</isAdditionalPermissionRequiredToRun>\n"
    if re.search(r"^    <isAdditionalPermissionRequiredToRun>", text, re.M):
        return top_level("isAdditionalPermissionRequiredToRun").sub(line, text, count=1)
    after = top_level("interviewLabel").search(text)
    if after:
        return text[: after.end()] + line + text[after.end():]
    before = re.search(r"^    <(?:isOverridable|isTemplate|label)>", text, re.M)
    if not before:
        raise InputError("no interviewLabel or label element to place the setting beside")
    return text[: before.start()] + line + text[before.start():]


def cmd_restrict(args):
    text = read_text(args.flow_file)
    parse_xml(text, args.flow_file)
    show_or_write(args.flow_file, text, restrict_text(text), args.write)
    return 0


# ---------------------------------------------------------------- step two

PERMSET_KEYS = {"flowAccesses": "flow", "classAccesses": "apexClass"}


def sort_permset(root):
    children = list(root)
    order = {id(c): i for i, c in enumerate(children)}

    def key(child):
        name = tag(child)
        sub = PERMSET_KEYS.get(name)
        return (name, child_text(child, sub, "").lower() if sub else "", order[id(child)])
    for child in children:
        root.remove(child)
    for child in sorted(children, key=key):
        root.append(child)


def add_access(root, element_name, key_name, value):
    for existing in root.findall("m:" + element_name, NS):
        if (child_text(existing, key_name, "") or "").lower() == value.lower():
            enabled = existing.find("m:enabled", NS)
            if enabled is not None and enabled.text != "true":
                enabled.text = "true"
                return "enabled"
            return "present"
    access = ET.SubElement(root, "{%s}%s" % (MD, element_name))
    if element_name == "classAccesses":
        ET.SubElement(access, "{%s}apexClass" % MD).text = value
        ET.SubElement(access, "{%s}enabled" % MD).text = "true"
    else:
        ET.SubElement(access, "{%s}enabled" % MD).text = "true"
        ET.SubElement(access, "{%s}flow" % MD).text = value
    return "added"


def grant_text(text, flows, classes, path):
    root = parse_xml(text, path)
    if tag(root) != "PermissionSet":
        raise InputError("%s is not a permission set file" % path)
    if child_text(root, "license"):
        raise InputError("%s has a user license; a set for site guests must have none" % path)
    report = []
    for flow in flows:
        report.append((flow, add_access(root, "flowAccesses", "flow", flow)))
    for cls in classes:
        report.append((cls, add_access(root, "classAccesses", "apexClass", cls)))
    sort_permset(root)
    return serialize(root), report


def new_permset(label, description):
    root = ET.Element("{%s}PermissionSet" % MD)
    if description:
        ET.SubElement(root, "{%s}description" % MD).text = description
    ET.SubElement(root, "{%s}hasActivationRequired" % MD).text = "false"
    ET.SubElement(root, "{%s}label" % MD).text = label
    return serialize(root)


def cmd_grant(args):
    exists = os.path.exists(args.permset_file)
    if not exists and not args.create:
        raise InputError("%s does not exist. Retrieve the org's permission set first, or pass --create with --label." % args.permset_file)
    if exists and args.create:
        raise InputError("%s already exists; leave out --create and the grant is merged into it" % args.permset_file)
    if args.create and not args.label:
        raise InputError("--create needs --label")
    old = read_text(args.permset_file) if exists else ""
    base = old or new_permset(args.label, args.description)
    new, report = grant_text(base, args.flow or [], args.apex or [], args.permset_file)
    for name, state in report:
        print("%s: %s" % (name, state))
    show_or_write(args.permset_file, old, new, args.write)
    return 0


# ---------------------------------------------------------------- guest sharing

def safe_name(text):
    words = re.sub(r"[^A-Za-z0-9]+", " ", text).split()
    name = "_".join(w[:1].upper() + w[1:] for w in words)
    if not name or not name[0].isalpha():
        name = "Guest_" + name
    return name[:80].rstrip("_")


def object_label(api):
    core = re.sub(r"^[A-Za-z0-9]+__(?=[A-Za-z].*__c$)", "", api)
    return core.replace("__c", "").replace("_", " ")


def existing_guest_rules(paths, site, obj):
    rules = []
    for path in paths or []:
        base = os.path.basename(path)
        file_obj = base.split(".sharingRules")[0]
        if file_obj.lower() != obj.lower():
            continue
        root = parse_xml(read_text(path), path)
        for rule in root.findall("m:sharingGuestRules", NS):
            shared = rule.find("m:sharedTo/m:guestUser", NS)
            if shared is None or (shared.text or "").lower() != site.lower():
                continue
            rules.append({
                "name": child_text(rule, "fullName", ""),
                "access": child_text(rule, "accessLevel", ""),
                "criteria": ["%s %s %s" % (child_text(c, "field", ""), child_text(c, "operation", ""), child_text(c, "value", ""))
                             for c in rule.findall("m:criteriaItems", NS)],
                "items": [(child_text(c, "field", ""), child_text(c, "operation", ""), child_text(c, "value", "") or "")
                          for c in rule.findall("m:criteriaItems", NS)],
                "boolean_filter": child_text(rule, "booleanFilter"),
            })
    return rules


def constant_criteria(read):
    """(criteria, needs_choice) for one read: what a sharing rule can copy from its filters."""
    usable, needs_choice = [], []
    for item in read["filters"]:
        operation = OPERATORS.get(item["operator"])
        if item["value_kind"] == "constant" and operation:
            usable.append((item["field"], operation, item["value"]))
        else:
            why = ("compares to %s, which changes per person" % item["value"] if item["value_kind"] == "reference"
                   else "uses a formula" if item["value_kind"] == "formula"
                   else "operator %s has no sharing-rule form" % item["operator"])
            needs_choice.append({"element": read["element"], "field": item["field"], "operator": item["operator"],
                                 "why": why, "per_person": item["value_kind"] == "reference"})
    logic = (read["filter_logic"] or "and").lower()
    if logic not in ("and", "") and usable:
        needs_choice.append({"element": read["element"], "field": "(filter logic)", "operator": read["filter_logic"],
                             "why": "the read uses custom filter logic, and a guest rule ANDs its criteria: check the proposal"})
    return frozenset(usable), needs_choice


def rule_name(obj, criteria):
    words = " ".join(field.replace("__c", "") for field, _, _ in sorted(criteria)) or "Public"
    return safe_name("Guest %s %s" % (object_label(obj), words)), ("Guest %s %s" % (object_label(obj), words.replace("_", " ")))[:80]


def propose_for_object(obj, reads, site, existing):
    """One proposed rule per distinct set of constant criteria; rules add up, so this is the narrowest cover."""
    sets, needs_choice, fields, open_reads = [], [], set(), []
    all_fields = False
    for read in reads:
        criteria, needs = constant_criteria(read)
        needs_choice += needs
        fields.update(read["fields"])
        all_fields = all_fields or read["all_fields"]
        if criteria:
            sets.append((criteria, read["element"]))
        else:
            open_reads.append(read["element"])
    # A rule with fewer criteria shares more, so it covers any rule whose criteria include its own.
    kept = []
    for criteria, element in sorted(sets, key=lambda pair: len(pair[0])):
        if any(k[0] <= criteria for k in kept):
            for k in kept:
                if k[0] <= criteria:
                    k[1].append(element)
                    break
            continue
        kept.append((criteria, [element]))
    rules = []
    for criteria, elements in kept:
        name, label = rule_name(obj, criteria)
        wanted = {tuple(part.lower() for part in item) for item in criteria}
        covered_by = [rule["name"] for rule in existing
                      if rule["access"] in ("Read", "Edit") and rule["items"] and not rule.get("boolean_filter")
                      and {tuple(part.lower() for part in item) for item in rule["items"]} <= wanted]
        rules.append({
            "name": name, "label": label, "access": "Read", "site": site,
            "criteria": [{"field": f, "operation": o, "value": v} for f, o, v in sorted(criteria)],
            "for_reads": elements, "covered_by": covered_by,
        })
    if rules:  # a per-person lookup inside records a rule already shares needs no choice of its own
        needs_choice = [n for n in needs_choice if not (n.get("per_person") and n["element"] in open_reads)]
    notes = []
    if open_reads and rules:
        notes.append("%s finds %s records by a value that changes per person; it finds only records the rules above share. "
                     "That is right when the record is always one the form offered." % (", ".join(open_reads), obj))
    elif open_reads:
        notes.append("no read of %s has a fixed filter: choose a field that marks the records meant for the public "
                     "(for example a Show on Website checkbox) and build the rule on it. Never share every record." % obj)
    fields_list = sorted(fields)
    if all_fields:
        fields_list.append("(every field: a read stores all fields; give it only the fields the screen shows)")
    proposal = {"object": obj, "reads": [r["element"] for r in reads], "rules": rules,
                "needs_your_choice": needs_choice, "notes": notes, "existing_rules": existing,
                "fields_to_grant_read": fields_list}
    if obj.endswith("Form_Submission__c"):
        proposal["refuse"] = ("Never share Form Submission records with guests, except Pre-fill Templates "
                              "(Is Pre-fill Template equals True). A guest reopens its own draft only through the "
                              "system-mode resume copy.")
        proposal["rules"] = []
    return proposal


def cmd_sharing_proposal(args):
    flow = read_flow(args.flow_file)
    by_object = {}
    for read in flow["reads"]:
        by_object.setdefault(read["object"], []).append(read)
    proposals = [propose_for_object(obj, reads, args.site, existing_guest_rules(args.existing, args.site, obj))
                 for obj, reads in sorted(by_object.items())]
    if flow["run_in_mode"] in ("SystemModeWithoutSharing", "SystemModeWithSharing"):
        print("note: %s runs in %s, so it reads without sharing rules. Rules still matter for anything else the guest reads."
              % (flow["api_name"], flow["run_in_mode"]), file=sys.stderr)
    if args.json:
        print(json.dumps({"flow": flow["api_name"], "site": args.site, "proposals": proposals}, indent=2))
        return 0
    if not proposals:
        print("%s reads no records: no guest sharing rule needed for it." % flow["api_name"])
        return 0
    for p in proposals:
        print("%s (read by %s)" % (p["object"], ", ".join(p["reads"])))
        if p.get("refuse"):
            print("  REFUSE: " + p["refuse"])
            continue
        for rule in p["existing_rules"]:
            print("  existing rule %s (%s): %s" % (rule["name"], rule["access"], "; ".join(rule["criteria"]) or "no criteria"))
        if not p["existing_rules"]:
            print("  no guest rule for site %s in the files given" % args.site)
        for rule in p["rules"]:
            crit = "; ".join("%s %s %s" % (c["field"], c["operation"], c["value"]) for c in rule["criteria"])
            state = ("already covered by %s" % ", ".join(rule["covered_by"])) if rule["covered_by"] else "propose"
            print("  %s: %s, Read Only, criteria: %s (for %s)" % (state, rule["name"], crit, ", ".join(rule["for_reads"])))
        for note in p["notes"]:
            print("  note: " + note)
        for need in p["needs_your_choice"]:
            print("  your choice: %s in %s %s (%s)" % (need["field"], need["element"], need["operator"], need["why"]))
        print("  Read for the guest on: %s" % ", ".join(p["fields_to_grant_read"]))
    return 0


def parse_criterion(text):
    parts = text.split(":", 2)
    if len(parts) != 3 or not parts[0]:
        raise InputError("criterion %r must be FIELD:OPERATION:VALUE" % text)
    field, operation, value = parts
    if operation not in SHARING_OPERATIONS:
        raise InputError("operation %r is not one of %s" % (operation, ", ".join(sorted(SHARING_OPERATIONS))))
    return field, operation, value


def sharing_rule_text(old_text, path, name, label, site, criteria, description):
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name) or "__" in name or name.endswith("_"):
        raise InputError("rule name %r must be letters, digits and single underscores" % name)
    if not criteria:
        raise InputError("a guest rule needs at least one criterion: share only the records the form needs")
    root = parse_xml(old_text, path) if old_text else ET.Element("{%s}SharingRules" % MD)
    for rule in root.findall("m:sharingGuestRules", NS):
        if (child_text(rule, "fullName", "") or "").lower() == name.lower():
            root.remove(rule)
    rule = ET.SubElement(root, "{%s}sharingGuestRules" % MD)
    ET.SubElement(rule, "{%s}fullName" % MD).text = name
    ET.SubElement(rule, "{%s}accessLevel" % MD).text = "Read"
    if description:
        ET.SubElement(rule, "{%s}description" % MD).text = description
    ET.SubElement(rule, "{%s}label" % MD).text = label
    shared = ET.SubElement(rule, "{%s}sharedTo" % MD)
    ET.SubElement(shared, "{%s}guestUser" % MD).text = site
    for field, operation, value in criteria:
        item = ET.SubElement(rule, "{%s}criteriaItems" % MD)
        ET.SubElement(item, "{%s}field" % MD).text = field
        ET.SubElement(item, "{%s}operation" % MD).text = operation
        ET.SubElement(item, "{%s}value" % MD).text = value
    ET.SubElement(rule, "{%s}includeHVUOwnedRecords" % MD).text = "false"
    children = list(root)
    for child in children:
        root.remove(child)
    for child in sorted(children, key=lambda c: (tag(c), (child_text(c, "fullName", "") or "").lower())):
        root.append(child)
    return serialize(root)


def cmd_sharing_rule(args):
    if args.object.endswith("Form_Submission__c") and not any("IsPrefillTemplate__c" in c for c in args.criterion):
        raise InputError("Form Submission is shared with guests only for Pre-fill Templates: "
                         "criterion IsPrefillTemplate__c:equals:True (with the package prefix in an installed org)")
    criteria = [parse_criterion(c) for c in args.criterion]
    path = os.path.join(args.out, "sharingRules", "%s.sharingRules-meta.xml" % args.object)
    old = read_text(path) if os.path.exists(path) else ""
    new = sharing_rule_text(old, path, args.name, args.label, args.site, criteria, args.description)
    show_or_write(path, old, new, args.write)
    return 0


# ---------------------------------------------------------------- system-mode copies

def guest_copy_text(kind, source_text, source_path, status, namespace=PACKAGE_NS):
    spec = COPIES[kind]
    parse_xml(source_text, source_path)
    base = flow_api_name(source_path)
    if base.split("__")[-1] != spec["source"]:
        raise InputError("%s is not the packaged %s flow" % (source_path, spec["source"]))
    if re.search(r"^    <overriddenFlow>", source_text, re.M):
        raise InputError("%s is already an override; start from the packaged flow retrieved from the org" % source_path)
    if not re.search(r"\b%s__Form_Submission__c\b" % re.escape(namespace), source_text):
        raise InputError("%s has no %s__ references: retrieve it from the org where Flow Tool Kit is installed, "
                         "not from source, so every object and field keeps the package prefix" % (source_path, namespace))
    text = source_text
    text = top_level("label").sub("    <label>%s</label>\n" % escape_xml(spec["label"]), text, count=1)
    text = top_level("interviewLabel").sub("    <interviewLabel>%s {!$Flow.CurrentDateTime}</interviewLabel>\n" % escape_xml(spec["label"]), text, count=1)
    description = "    <description>%s</description>\n" % escape_xml(spec["description"])
    if top_level("description").search(text):
        text = top_level("description").sub(lambda _: description, text, count=1)
    else:
        anchor = re.search(r"^    <(?:dynamicChoiceSets|environments|formulas|interviewLabel)>", text, re.M)
        text = text[: anchor.start()] + description + text[anchor.start():] if anchor else text
    if top_level("runInMode").search(text):
        text = top_level("runInMode").sub("    <runInMode>SystemModeWithoutSharing</runInMode>\n", text, count=1)
    else:
        anchor = re.search(r"^    <(?:screens|start|startElementReference|status)>", text, re.M)
        text = text[: anchor.start()] + "    <runInMode>SystemModeWithoutSharing</runInMode>\n" + text[anchor.start():]
    text = top_level("status").sub("    <status>%s</status>\n" % status, text, count=1)
    text = top_level("isOverridable").sub("", text)
    text = top_level("isTemplate").sub("", text)
    text = restrict_text(text)
    if spec["override"]:
        anchor = re.search(r"^    <(?:processMetadataValues|processType)>", text, re.M)
        if not anchor:
            raise InputError("no processType element to place overriddenFlow before")
        line = "    <overriddenFlow>%s__%s</overriddenFlow>\n" % (namespace, spec["source"])
        text = text[: anchor.start()] + line + text[anchor.start():]
    parse_xml(text, "generated copy")
    return text


SAVE_SETTINGS = (("Allow_Save_Progress__c", "Save Progress"), ("Stages_Mode__c", "Stages"),
                 ("Enable_Autosave__c", "Autosave"))
SYSTEM_MODE_NOTICE = (
    "Once the save override is active, every save in the org runs through it in system mode: guests, "
    "portal users and staff, on every form, not only this one. Ask for the yes after saying this.")


def template_value(row, field):
    for key in (field, PACKAGE_NS + "__" + field):
        if key in row:
            return row[key]
    return None


def load_templates(path):
    """Form Template rows from a query result: a list, {"records": [...]}, or the CLI's --json output."""
    try:
        data = json.loads(read_text(path))
    except ValueError as error:
        raise InputError("%s is not JSON: %s" % (path, error))
    if isinstance(data, dict):
        data = data.get("result", data)
    if isinstance(data, dict):
        data = data.get("records")
    if not isinstance(data, list):
        raise InputError("%s holds no Form Template rows" % path)
    return data


def copies_needed(templates):
    """{"upsert": [(name, reasons)], "prefill": [(name, reasons)]} for the guest templates given."""
    needed = {"upsert": [], "prefill": []}
    for row in templates:
        name = row.get("Name") or row.get("Id") or "?"
        saves = [label for field, label in SAVE_SETTINGS if template_value(row, field) is True]
        if saves:
            needed["upsert"].append((name, saves))
        stages = template_value(row, "Stages_Mode__c") is True
        email = template_value(row, "Send_Save_Progress_Email__c") is True
        if template_value(row, "Allow_Save_Progress__c") is True and (stages or email):
            needed["prefill"].append((name, ["Stages resume link" if stages else "Save Progress email"]))
    return needed


def cmd_guest_copy(args):
    spec = COPIES[args.kind]
    needed_by = copies_needed(load_templates(args.templates))[args.kind]
    if not needed_by:
        if args.kind == "upsert":
            print("not needed, so not built: no guest template here uses Save Progress, Stages or Autosave, so "
                  "every guest save is a single insert the packaged (Form) Upsert | Overridable already handles. "
                  "The packaged flow stays in place.")
        else:
            print("not needed, so not built: no guest template here sends resume links (Save Progress email or "
                  "the Stages resume button). The packaged prefill flow stays in place.")
        return 0
    text = guest_copy_text(args.kind, read_text(args.source_file), args.source_file, args.status, args.namespace)
    path = os.path.join(args.out, "flows", "%s.flow-meta.xml" % spec["api_name"])
    old = read_text(path) if os.path.exists(path) else ""
    print("%s: %s, %s, System Context Without Sharing, status %s" % (spec["api_name"], spec["label"],
          "override of %s__%s" % (args.namespace, spec["source"]) if spec["override"] else "a plain copy for the Prefill Flow field",
          args.status))
    for name, reasons in needed_by:
        print("  needed by %s: %s" % (name, ", ".join(reasons)))
    if spec["override"]:
        print("  " + SYSTEM_MODE_NOTICE)
    show_or_write(path, old, text, args.write)
    return 0


# ---------------------------------------------------------------- org queries

def soql_list(values):
    return ", ".join("'%s'" % v.replace("\\", "\\\\").replace("'", "\\'") for v in values)


def split_ns(api_name):
    if "__" in api_name and not api_name.endswith("__c"):
        ns, name = api_name.split("__", 1)
        return ns, name
    return None, api_name


def query_set(flow, site=None, user=None, objects=()):
    ns, name = split_ns(flow)
    flow_where = "ApiName = '%s'" % name + (" AND NamespacePrefix = '%s'" % ns if ns else "")
    queries = [
        ("flow", "SELECT DurableId, ApiName, NamespacePrefix, Label, ProcessType, IsActive, ActiveVersionId, LatestVersionId, IsOverridable, OverriddenById, IsTemplate FROM FlowDefinitionView WHERE %s" % flow_where, False),
        ("override", "SELECT DurableId, ApiName, Label, IsActive, ActiveVersionId FROM FlowDefinitionView WHERE DurableId = '<OverriddenById from the flow row>'  (set only while an override is active)", False),
        ("inactive_overrides", "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE OverriddenFlowId = '<DurableId from the flow row>'", False),
        ("run_mode", "SELECT VersionNumber, Status, RunInMode, ApiVersion FROM FlowVersionView WHERE DurableId = '<ActiveVersionId>'", False),
        ("restricted", "SELECT Metadata FROM Flow WHERE Id = '<ActiveVersionId>'  (Tooling API; read Metadata.isAdditionalPermissionRequiredToRun)", True),
        ("granted_by", "SELECT Parent.Name, Parent.Label, Parent.IsOwnedByProfile, Parent.Profile.Name FROM SetupEntityAccess WHERE SetupEntityType = 'FlowDefinition' AND SetupEntityId = '<DurableId of the flow that runs>'", False),
    ]
    if site:
        queries.append(("running_user", "SELECT Name, MasterLabel, GuestUserId, GuestUser.Username, Status FROM Site WHERE Name = '%s' OR MasterLabel = '%s'" % (site, site), False))
    elif user:
        queries.append(("running_user", "SELECT Id, Username, UserType, Profile.Name, IsActive FROM User WHERE Username = '%s'" % user, False))
    else:
        queries.append(("running_user", "SELECT Id, Username, UserType, Profile.Name FROM User WHERE <the person who sees the message>", False))
    queries += [
        ("assigned_sets", "SELECT PermissionSetId, PermissionSet.Name, PermissionSet.Label, PermissionSet.IsOwnedByProfile, PermissionSet.PermissionsRunFlow FROM PermissionSetAssignment WHERE AssigneeId = '<running user Id>'", False),
    ]
    if objects:
        queries += [
            ("sharing_model", "SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE QualifiedApiName IN (%s)" % soql_list(objects), False),
            ("object_access", "SELECT Parent.Name, SobjectType, PermissionsRead, PermissionsCreate, PermissionsEdit FROM ObjectPermissions WHERE ParentId IN ('<assigned set Ids>') AND SobjectType IN (%s)" % soql_list(objects), False),
            ("field_access", "SELECT Parent.Name, Field, PermissionsRead, PermissionsEdit FROM FieldPermissions WHERE ParentId IN ('<assigned set Ids>') AND SobjectType IN (%s)" % soql_list(objects), False),
        ]
    return queries


def cmd_queries(args):
    for key, soql, tooling in query_set(args.flow, args.site, args.user, args.object or ()):
        print("-- %s%s" % (key, " (Tooling API)" if tooling else ""))
        print(soql)
    print("-- guest sharing rules: no SOQL reaches them. Retrieve SharingRules:<Object> (Claude Code), "
          "or read Setup, Sharing Settings, <Object> Sharing Rules (chat).")
    return 0


def sf_query(org, soql, tooling=False):
    cmd = ["sf", "data", "query", "--json", "-q", soql, "-o", org]
    if tooling:
        cmd.append("--use-tooling-api")
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        raise InputError("the Salesforce CLI (sf) is not installed: diagnose needs Claude Code with the CLI. In chat, run `queries` and use the connector.")
    out = done.stdout[done.stdout.find("{"):] if "{" in done.stdout else "{}"
    data = json.loads(out)
    if data.get("status", 1) != 0:
        raise InputError("query failed: %s" % (data.get("message") or done.stderr.strip())[:300])
    return (data.get("result") or {}).get("records") or []


def diagnose(org, flow_name, site=None, user=None, query=sf_query):
    """Return a dict verdict. `query(org, soql, tooling)` returns records."""
    ns, name = split_ns(flow_name)
    where = "ApiName = '%s'" % name + (" AND NamespacePrefix = '%s'" % ns if ns else "")
    rows = query(org, "SELECT DurableId, ApiName, NamespacePrefix, Label, IsActive, ActiveVersionId, LatestVersionId, IsOverridable, OverriddenById, IsTemplate FROM FlowDefinitionView WHERE %s" % where, False)
    if not rows:
        return {"verdict": "no flow named %s in the org" % flow_name, "ok": False, "steps": []}
    if len(rows) > 1:
        return {"verdict": "several flows are named %s; pass it with its namespace (ns__%s)" % (name, name), "ok": False, "steps": []}
    named = rows[0]
    runs = named
    notes = []
    if named.get("OverriddenById"):
        over = query(org, "SELECT DurableId, ApiName, NamespacePrefix, Label, IsActive, ActiveVersionId, LatestVersionId, IsOverridable, OverriddenById, IsTemplate FROM FlowDefinitionView WHERE DurableId = '%s'" % named["OverriddenById"], False)
        if over and over[0].get("IsActive"):
            runs = over[0]
            notes.append("%s is overridden by %s, which is what runs: the checks below are on the override." % (named["ApiName"], runs["ApiName"]))
        elif over:
            notes.append("%s has an override, %s, that is not active: the packaged flow still runs." % (named["ApiName"], over[0]["ApiName"]))
    elif named.get("IsOverridable"):
        # Salesforce fills OverriddenById only while the override is active; a draft one points the other way.
        drafts = query(org, "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE OverriddenFlowId = '%s'" % named["DurableId"], False)
        for draft in drafts:
            notes.append("%s has an override, %s, that is not active: the packaged flow still runs until it is activated." % (named["ApiName"], draft["ApiName"]))
    version = runs.get("ActiveVersionId")
    steps = []
    if not version:
        steps.append({"step": "active", "ok": False, "detail": "%s has no active version: activate it" % runs["ApiName"]})
        version = runs.get("LatestVersionId")
    meta_rows = query(org, "SELECT Metadata FROM Flow WHERE Id = '%s'" % version, True) if version else []
    meta = (meta_rows[0].get("Metadata") or {}) if meta_rows else {}
    restricted = bool(meta.get("isAdditionalPermissionRequiredToRun"))
    run_mode = meta.get("runInMode") or "DefaultMode"
    grants = query(org, "SELECT ParentId, Parent.Name, Parent.Label, Parent.IsOwnedByProfile, Parent.Profile.Name FROM SetupEntityAccess WHERE SetupEntityType = 'FlowDefinition' AND SetupEntityId = '%s'" % runs["DurableId"], False)
    granted_by = {g["ParentId"]: (g.get("Parent") or {}) for g in grants}
    granted_names = ", ".join(sorted((p.get("Name") or "?") for p in granted_by.values())) or "nothing"
    running = None
    if site:
        sites = query(org, "SELECT Name, MasterLabel, GuestUserId, Status FROM Site WHERE Name = '%s' OR MasterLabel = '%s'" % (site, site), False)
        if not sites or not sites[0].get("GuestUserId"):
            return {"verdict": "no site or guest user named %s" % site, "ok": False, "steps": steps, "notes": notes}
        running = sites[0]["GuestUserId"]
    elif user:
        users = query(org, "SELECT Id, UserType FROM User WHERE Username = '%s'" % user, False)
        if not users:
            return {"verdict": "no user %s" % user, "ok": False, "steps": steps, "notes": notes}
        running = users[0]["Id"]
    run_flows = False
    granting = []
    if running:
        assigned = query(org, "SELECT PermissionSetId, PermissionSet.Name, PermissionSet.IsOwnedByProfile, PermissionSet.PermissionsRunFlow FROM PermissionSetAssignment WHERE AssigneeId = '%s'" % running, False)
        run_flows = any((a.get("PermissionSet") or {}).get("PermissionsRunFlow") for a in assigned)
        granting = [(a.get("PermissionSet") or {}).get("Name") or "?" for a in assigned if a["PermissionSetId"] in granted_by]
    if restricted:
        steps.append({"step": "restricted", "ok": True, "detail": "requires permission to run"})
        if running:
            steps.append({"step": "granted", "ok": bool(granting), "detail": (
                "granted through %s" % ", ".join(granting)) if granting else
                "none of the running user's permission sets grants %s (it is granted by: %s)" % (runs["ApiName"], granted_names)})
        else:
            steps.append({"step": "granted", "ok": None, "detail": "granted by: %s (pass --site or --user to check a running user)" % granted_names})
    elif run_flows:
        steps.append({"step": "restricted", "ok": None, "detail": "not restricted: this user runs it through Run Flows. Guests and portal users never have Run Flows, so restrict it before any of them use it"})
        steps.append({"step": "granted", "ok": None, "detail": "not needed for this user while the flow is unrestricted"})
    else:
        steps.append({"step": "restricted", "ok": False, "detail": "NOT restricted: guests and portal users can never run it, and a grant does nothing until it is"})
        steps.append({"step": "granted", "ok": None if not running else bool(granting), "detail": "granted by: %s; restrict it first" % granted_names})
    if run_mode != "DefaultMode":
        notes.append("%s runs in %s." % (runs["ApiName"], run_mode))
    ok = all(s["ok"] is not False for s in steps)
    verdict = ("both steps in place: look further (subflows, Apex actions, object, field and record access), and test in a new session"
               if ok else "fix the steps marked NO, then test in a new session")
    return {"flow": named["ApiName"], "runs": runs["ApiName"], "run_mode": run_mode, "ok": ok,
            "verdict": verdict, "steps": steps, "notes": notes}


def cmd_diagnose(args):
    result = diagnose(args.org, args.flow, args.site, args.user)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("runs"):
            print("%s (runs: %s, %s)" % (result["flow"], result["runs"], result["run_mode"]))
        for note in result.get("notes", []):
            print("  note: " + note)
        for step in result.get("steps", []):
            mark = "yes" if step["ok"] else ("?" if step["ok"] is None else "NO")
            print("  %-10s %-3s %s" % (step["step"], mark, step["detail"]))
        print(result["verdict"])
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------- CLI

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("flow_file")
    p.add_argument("--audience", action="append", choices=AUDIENCES)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("restrict")
    p.add_argument("flow_file")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_restrict)

    p = sub.add_parser("grant")
    p.add_argument("permset_file")
    p.add_argument("--flow", action="append")
    p.add_argument("--apex", action="append")
    p.add_argument("--create", action="store_true")
    p.add_argument("--label")
    p.add_argument("--description")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_grant)

    p = sub.add_parser("sharing-proposal")
    p.add_argument("flow_file")
    p.add_argument("--site", required=True)
    p.add_argument("--existing", action="append")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_sharing_proposal)

    p = sub.add_parser("sharing-rule")
    p.add_argument("--object", required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--criterion", action="append", required=True)
    p.add_argument("--description")
    p.add_argument("--out", required=True)
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_sharing_rule)

    p = sub.add_parser("guest-copy")
    p.add_argument("kind", choices=sorted(COPIES))
    p.add_argument("source_file")
    p.add_argument("--templates", required=True,
                   help="JSON rows of the guest Form Templates (the query in references/guest-save-and-resume.md)")
    p.add_argument("--out", required=True)
    p.add_argument("--status", choices=("Draft", "Active"), default="Draft")
    p.add_argument("--namespace", default=PACKAGE_NS)
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_guest_copy)

    p = sub.add_parser("queries")
    p.add_argument("--flow", required=True)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--site")
    group.add_argument("--user")
    p.add_argument("--object", action="append")
    p.set_defaults(func=cmd_queries)

    p = sub.add_parser("diagnose")
    p.add_argument("--org", required=True)
    p.add_argument("--flow", required=True)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--site")
    group.add_argument("--user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_diagnose)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "grant" and not (args.flow or args.apex):
        print("flowaccess: grant needs --flow or --apex", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except InputError as error:
        print("flowaccess: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
