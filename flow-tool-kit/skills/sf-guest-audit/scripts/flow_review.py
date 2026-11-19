#!/usr/bin/env python3
"""Flow review: guest flows that send whole records to the browser.

Reads flow metadata (.flow-meta.xml or .flow files) and flags the risky but common
pattern: a flow running in system context gets a record with every field and hands
it to a screen component (a Flow Tool Kit form, table or repeater, or any other) or
returns it to the page. Every field value then reaches the visitor's browser, shown
or not. Python 3.9+, standard library only. Read only: it never changes the org.

  review [FILE_OR_DIR ...] [--org ALIAS --flow NAME ...] [--guest-flow NAME ...]
         [--snapshot snapshot.json] [--out DIR] [--json]

  - Files or folders: flow metadata the person already has (a retrieve, a project).
  - --org with --flow: Claude Code only. Retrieves those flows with the Salesforce
    CLI into DIR/flows (metadata only, no records).
  - Which flows a guest runs: --guest-flow names, or --snapshot from guest_audit.py
    (the flows granted to each site's guest). A flow not known either way is
    reviewed as "if a guest runs it".

Checks, per flow:
  1. System context and a Get Records storing all fields whose record reaches a
     screen component or an output, without the FLS Record(s) Sanitizer action
     between them. HIGH when a guest runs it.
  2. A Get Records in system context filtered by a value from the visitor (an input
     variable or a URL parameter) whose record reaches the screen: anyone who edits
     the link reads another person's record. HIGH when a guest runs it.
  3. System context and chosen fields, one of which looks sensitive: MEDIUM.
  4. Default context and all fields: LOW (the guest's field access still applies).

Exit codes: 0 no HIGH, 1 at least one HIGH, 2 usage or input error.
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

MD = "{http://soap.sforce.com/2006/04/metadata}"
SEVERITIES = ("HIGH", "MEDIUM", "LOW", "INFO")
RANK = {s: i for i, s in enumerate(SEVERITIES)}
SANITIZER = re.compile(r"^(?:[A-Za-z0-9]+__)?DataSanitizer_Invocable$")
SANITIZER_NAME = "FLS Record(s) Sanitizer (FlowToolKit__DataSanitizer_Invocable)"
FTK_GUEST_COPIES = {"Form_Submission_Upsert_Guest", "Form_Submission_Prefill_Guest"}
TOKEN_FIELD = re.compile(r"token", re.I)
COMPONENTS = {
    "flowForm": "Form (Component)", "formTemplate": "Form (Template)", "flowFormRepeat": "Form (Repeater)",
    "flowDataTable": "Form (Table)", "mergeRecords": "Form (Merge Records)", "datatable": "Data Table",
}
SENSITIVE_FIELD = re.compile(r"birth|dob|ssn|social_?security|tax_?id|passport|licen[cs]e|bank|routing|account_?number|"
                             r"income|salary|health|medical|diagnos|medication|disabilit|insurance|note|comment|internal|"
                             r"confidential|private|gender|race|ethnic|religio|token|password|secret|description", re.I)


class InputError(Exception):
    pass


def text(node, tag):
    child = node.find(MD + tag)
    return child.text.strip() if child is not None and child.text else None


def value_ref(node):
    value = node.find(MD + "value")
    return text(value, "elementReference") if value is not None else None


def component_label(extension):
    short = (extension or "").split(":")[-1]
    return COMPONENTS.get(short, short or "a screen component")


def walk_screen_fields(parent):
    for field in parent.findall(MD + "fields"):
        yield field
        yield from walk_screen_fields(field)


def parse_flow(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise InputError("cannot read %s: %s" % (path, error))
    name = os.path.basename(path).split(".flow")[0]
    flow = {"name": name, "file": os.path.basename(path), "label": text(root, "label") or name,
            "process": text(root, "processType") or "", "mode": text(root, "runInMode") or "DefaultMode",
            "lookups": {}, "variables": {}, "edges": [], "sinks": [], "sanitizers": [], "clean": set(), "sanitizer_edges": []}
    for var in root.findall(MD + "variables"):
        flow["variables"][text(var, "name")] = {"input": text(var, "isInput") == "true", "output": text(var, "isOutput") == "true",
                                                "type": text(var, "dataType"), "object": text(var, "objectType")}
    for lookup in root.findall(MD + "recordLookups"):
        lname = text(lookup, "name")
        auto = text(lookup, "storeOutputAutomatically") == "true"
        queried = [q.text.strip() for q in lookup.findall(MD + "queriedFields") if q.text]
        assigned = lookup.findall(MD + "outputAssignments")
        target = lname if auto else text(lookup, "outputReference")
        filters = []
        for flt in lookup.findall(MD + "filters"):
            filters.append({"field": text(flt, "field"), "ref": value_ref(flt)})
        if assigned and not target:
            continue
        flow["lookups"][lname] = {"object": text(lookup, "object"), "target": target, "queried": queried,
                                  "all_fields": not queried, "filters": filters}
    for assignment in root.findall(MD + "assignments"):
        for item in assignment.findall(MD + "assignmentItems"):
            flow["edges"].append((value_ref(item), text(item, "assignToReference"), "assignment " + text(assignment, "name")))
    for loop in root.findall(MD + "loops"):
        source = text(loop, "collectionReference")
        item = text(loop, "assignNextValueToReference") or text(loop, "name")
        flow["edges"].append((source, item, "loop " + text(loop, "name")))
    # Actions are not followed: a record passed through the sanitizer (or any action) reaches the screen as its output, already reduced.
    for action in root.findall(MD + "actionCalls"):
        if SANITIZER.match(text(action, "actionName") or ""):
            flow["sanitizers"].append(text(action, "name"))
            outputs = {text(o, "assignToReference") for o in action.findall(MD + "outputParameters")}
            if text(action, "storeOutputAutomatically") == "true":
                outputs |= {text(action, "name") + ".record", text(action, "name") + ".records"}
            flow["clean"] |= outputs
            for param in action.findall(MD + "inputParameters"):
                flow["sanitizer_edges"] += [(value_ref(param), target, "sanitizer " + text(action, "name")) for target in outputs]
    for screen in root.findall(MD + "screens"):
        for field in walk_screen_fields(screen):
            extension = text(field, "extensionName")
            if not extension:
                continue
            for param in field.findall(MD + "inputParameters"):
                ref = value_ref(param)
                if ref:
                    flow["sinks"].append({"ref": ref, "screen": text(screen, "name"), "component": component_label(extension),
                                          "field": text(field, "name"), "param": text(param, "name")})
    for name, var in flow["variables"].items():
        if var["output"] and var["type"] == "SObject":
            flow["sinks"].append({"ref": name, "screen": None, "component": "the flow's output variable %s" % name,
                                  "field": None, "param": name})
    return flow


def root_ref(ref):
    return (ref or "").split(".")[0]


def reach(flow, through_sanitizer=False):
    """For each lookup, the variables its whole record flows into (assignments and loops), and the sinks it reaches.
    through_sanitizer follows the record past the sanitizer too: it strips fields, not records."""
    clean = set() if through_sanitizer else flow["clean"]
    edges = flow["edges"] + (flow["sanitizer_edges"] if through_sanitizer else [])
    results = {}
    for lname, lookup in flow["lookups"].items():
        carriers = {lookup["target"]: [lname]} if lookup["target"] not in clean else {}
        changed = True
        while changed:
            changed = False
            for source, target, via in edges:
                if source in carriers and target and "." not in target and target not in carriers and target not in clean:
                    carriers[target] = carriers[source] + [via]
                    changed = True
        hits = []
        for sink in flow["sinks"]:
            if sink["ref"] in carriers:
                hits.append(dict(sink, path=carriers[sink["ref"]]))
        results[lname] = {"carriers": carriers, "sinks": hits}
    return results


def from_visitor(ref, flow, url_components):
    root = root_ref(ref)
    return root in url_components or flow["variables"].get(root, {}).get("input", False)


def url_parameter_components(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return set()
    names = set()
    for screen in root.findall(MD + "screens"):
        for field in walk_screen_fields(screen):
            if (text(field, "extensionName") or "").split(":")[-1] == "getUrlParameters":
                names.add(text(field, "name"))
    return names


def review_flow(path, guest):
    flow = parse_flow(path)
    url_components = url_parameter_components(path)
    system = flow["mode"].startswith("SystemMode")
    findings = []
    inventory = {"flow": flow["name"], "label": flow["label"], "mode": flow["mode"], "guest": guest,
                 "sanitized": list(flow["sanitizers"]), "chosen_fields": []}
    copy = flow["name"] in FTK_GUEST_COPIES

    def base(lname, lookup, sink):
        return {"flow": flow["name"], "label": flow["label"], "element": lname, "object": lookup["object"],
                "component": sink["component"], "screen": sink["screen"], "param": sink["param"], "mode": flow["mode"], "guest": guest}

    def where(sink):
        return "%s on screen %s (parameter %s)" % (sink["component"], sink["screen"], sink["param"]) if sink["screen"] else sink["component"]

    for lname, info in reach(flow, through_sanitizer=True).items():
        lookup = flow["lookups"][lname]
        visitor_filters = [f for f in lookup["filters"] if f["ref"] and from_visitor(f["ref"], flow, url_components)
                           and not TOKEN_FIELD.search(f["field"] or "")]
        if system and visitor_filters and info["sinks"]:
            sink = info["sinks"][0]
            findings.append(dict(base(lname, lookup, sink), severity=cap(guest_severity("HIGH", guest), copy), check="visitor lookup",
                                 title="%s looks up %s by %s, a value the visitor controls, in system context, and sends the record to %s" % (
                                     lname, lookup["object"], ", ".join(f["ref"] for f in visitor_filters), where(sink)),
                                 evidence=["runInMode %s" % flow["mode"],
                                           "filter %s" % "; ".join("%s = {!%s}" % (f["field"], f["ref"]) for f in visitor_filters),
                                           "record path: %s" % " > ".join(sink["path"])],
                                 fix=fix_visitor(lname, lookup)))
    for lname, info in reach(flow).items():
        lookup = flow["lookups"][lname]
        for sink in info["sinks"]:
            if system and lookup["all_fields"]:
                severity = cap(guest_severity("HIGH", guest), copy)
                findings.append(dict(base(lname, lookup, sink), severity=severity, check="all fields",
                                     title="%s gets every field of %s in system context and passes the whole record to %s, "
                                           "without the FLS Record(s) Sanitizer" % (lname, lookup["object"], where(sink)),
                                     evidence=["runInMode %s" % flow["mode"], "%s stores all fields (no fields chosen)" % lname,
                                               "record path: %s" % " > ".join(sink["path"])],
                                     fix=fix_all_fields(lname, lookup, sink)))
            elif system:
                risky = [f for f in lookup["queried"] if SENSITIVE_FIELD.search(f)]
                inventory["chosen_fields"].append({"element": lname, "fields": lookup["queried"]})
                if risky:
                    findings.append(dict(base(lname, lookup, sink), severity=cap("MEDIUM", copy), check="chosen fields",
                                         title="%s chooses fields that look sensitive (%s) and passes them to %s in system context" % (
                                             lname, ", ".join(risky), where(sink)),
                                         evidence=["runInMode %s" % flow["mode"], "queried: %s" % ", ".join(lookup["queried"])],
                                         fix=["Check the form shows %s. If not, drop them from %s's fields, or pass the record "
                                              "through %s so the guest's field access decides." % (", ".join(risky), lname, SANITIZER_NAME)]))
            elif lookup["all_fields"]:
                findings.append(dict(base(lname, lookup, sink), severity="LOW", check="all fields, default context",
                                     title="%s gets every field of %s the running user can read and passes the whole record to %s" % (
                                         lname, lookup["object"], where(sink)),
                                     evidence=["runInMode %s: the guest's object and field access apply" % flow["mode"]],
                                     fix=["Every field the guest can read reaches the browser. Keep the guest's field Read to what "
                                          "the form shows, or choose only the needed fields in %s." % lname]))
    return findings, inventory, flow


def guest_severity(severity, guest):
    if guest is True:
        return severity
    if guest is None:
        return "MEDIUM" if severity == "HIGH" else severity
    return "LOW"


def cap(severity, copy):
    return "LOW" if copy and RANK[severity] < RANK["LOW"] else severity


def fix_all_fields(lname, lookup, sink):
    many = sink["param"] in ("records", "prefillRecords", "relatedRecords", "tableData") or "Records" in (sink["param"] or "")
    return [
        "Add the Flow Tool Kit action %s right after %s: pass {!%s} into its %s input, and give %s the action's %s output "
        "instead. It removes every field the running user cannot read, so the guest's profile and permission sets decide "
        "what the form receives: if the guest can read only First Name and Last Name on %s, that is all the form gets." % (
            SANITIZER_NAME, lname, lookup["target"], "Record(s)" if many else "Record", sink["component"],
            "Record(s)" if many else "Record", lookup["object"]),
        "Then keep the guest's field Read (the org's guest permission set) to the fields the form shows.",
        "Or choose only the needed fields in %s (Choose fields and let Salesforce do the rest) instead of storing all fields." % lname,
        "Run the flow in the default context (user permissions) unless it truly needs system context.",
        "If this is a prefill flow, set only the fields the form shows on prefillRecord (the Prefill From Mapped Record "
        "action copies only mapped sections), and keep a Pre-fill Template to defaults only.",
    ]


def fix_visitor(lname, lookup):
    return [
        "Never look up %s by an Id or value from the link in system context: whoever edits the link reads another "
        "person's record. Use a single-use token, as the Flow Tool Kit resume link does (Internal_Unique_Token__c), "
        "or require sign-in." % lookup["object"],
        "The FLS Record(s) Sanitizer strips fields, not records, so add it as well but do not rely on it for this.",
        "Or run the flow in the default context and share only the records a guest may read with a narrow guest sharing rule.",
    ]


# ---------------------------------------------------------------- inputs

def flow_files(paths):
    files = []
    for path in paths:
        if os.path.isdir(path):
            files += glob.glob(os.path.join(path, "**", "*.flow-meta.xml"), recursive=True)
            files += glob.glob(os.path.join(path, "**", "*.flow"), recursive=True)
        elif os.path.exists(path):
            files.append(path)
        else:
            raise InputError("not found: %s" % path)
    return sorted(set(files))


def guest_flows_from_snapshot(path):
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("guest_audit", os.path.join(here, "guest_audit.py"))
    ga = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ga)
    snap = ga.load_snapshot(path)
    sets = set()
    for aud in ga.build_audiences(snap):
        sets |= set(aud["sets"])
    granted = {r["SetupEntityId"] for r in ga.rows(snap, "grants") if r.get("SetupEntityType") == "FlowDefinition" and r.get("ParentId") in sets}
    return {ga.flow_key(f) for f in ga.rows(snap, "flows") if f["DurableId"] in granted} | \
           {f["ApiName"] for f in ga.rows(snap, "flows") if f["DurableId"] in granted}


def retrieve(org, names, out_dir):
    tmp = tempfile.mkdtemp(prefix="flow-review-")
    try:
        cmd = ["sf", "project", "retrieve", "start", "--json", "--target-metadata-dir", tmp, "--unzip", "-o", org]
        for name in names:
            cmd += ["-m", "Flow:" + name]
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            raise InputError("the Salesforce CLI (sf) is not installed. In chat, upload the flow files instead.")
        data = json.loads(done.stdout[done.stdout.find("{"):]) if "{" in done.stdout else {}
        if data.get("status", 1) != 0:
            raise InputError((data.get("message") or "retrieve failed").strip()[:300])
        target = os.path.join(out_dir, "flows")
        os.makedirs(target, exist_ok=True)
        for path in glob.glob(os.path.join(tmp, "**", "*.flow*"), recursive=True):
            shutil.copy(path, target)
        return target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- output

def md(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(result):
    lines = ["# Flow review: what guest flows send to the browser", ""]
    counts = {s: sum(1 for f in result["findings"] if f["severity"] == s) for s in SEVERITIES}
    lines.append("%d flows reviewed. %s." % (len(result["flows"]), ", ".join("%s %d" % (s, counts[s]) for s in SEVERITIES)))
    lines += ["", "| Flow | Runs as | Guest runs it | Sanitized | Findings |", "|---|---|---|---|---|"]
    for inv in result["flows"]:
        n = sum(1 for f in result["findings"] if f["flow"] == inv["flow"])
        guest = {True: "yes", False: "no", None: "unknown"}[inv["guest"]]
        lines.append("| %s | %s | %s | %s | %d |" % (md(inv["flow"]), inv["mode"], guest, ", ".join(inv["sanitized"]) or "no", n))
    for finding in result["findings"]:
        lines += ["", "## %s %s: %s" % (finding["id"], finding["severity"], finding["flow"]), "", finding["title"] + ".", ""]
        lines += ["- %s" % e for e in finding["evidence"]]
        if finding["guest"] is None:
            lines.append("- Whether a guest runs this flow is not known: it is HIGH if one does.")
        lines += ["", "Fix:", ""] + ["%d. %s" % (i, f) for i, f in enumerate(finding["fix"], 1)]
    return "\n".join(lines) + "\n"


def cmd_review(args):
    out = args.out or "."
    paths = list(args.paths or [])
    if args.org:
        if not args.flow:
            raise InputError("--org needs at least one --flow NAME")
        paths.append(retrieve(args.org, args.flow, out))
    files = flow_files(paths)
    if not files:
        raise InputError("no flow files given")
    guests = set(args.guest_flow or [])
    known = bool(guests) or bool(args.snapshot)
    if args.snapshot:
        guests |= guest_flows_from_snapshot(args.snapshot)
    findings, flows = [], []
    for path in files:
        name = os.path.basename(path).split(".flow")[0]
        guest = (name in guests) if known else None
        found, inventory, _ = review_flow(path, guest)
        findings += found
        flows.append(inventory)
    findings.sort(key=lambda f: (RANK[f["severity"]], f["flow"], f["element"]))
    for i, finding in enumerate(findings, 1):
        finding["id"] = "F%d" % i
    result = {"flows": flows, "findings": findings}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "flow-review.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    with open(os.path.join(out, "flow-review.md"), "w", encoding="utf-8") as f:
        f.write(render(result))
    if args.json:
        print(json.dumps(result, indent=1))
    else:
        print("flow review: %s" % os.path.join(out, "flow-review.md"))
        for finding in findings:
            print("  %s %s %s" % (finding["id"], finding["severity"], finding["title"]))
    return 1 if any(f["severity"] == "HIGH" for f in findings) else 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("review")
    p.add_argument("paths", nargs="*", help="flow files or folders")
    p.add_argument("--org", help="Claude Code: retrieve the --flow names from this org")
    p.add_argument("--flow", action="append", help="a flow API name to retrieve")
    p.add_argument("--guest-flow", action="append", help="a flow a guest runs")
    p.add_argument("--snapshot", help="guest_audit.py snapshot: the flows granted to each site's guest")
    p.add_argument("--out")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_review)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as error:
        print("flow_review: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
