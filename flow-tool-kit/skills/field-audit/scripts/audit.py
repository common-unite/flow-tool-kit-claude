#!/usr/bin/env python3
"""field-audit: before an admin deletes, relabels or changes picklist values on a
Form Submission landing field, which Flow Tool Kit places it affects: Form
Templates, page sections, Form Components (metadata, record, JSON), mappings and
Flow Tool Kit flows (conversion, prefill, and flows using Flow Tool Kit actions
or screen components). Writes a data dictionary with a verdict per custom field.
Apex, reports, page layouts and other general metadata are left to Setup's
Where is this used?.

Claude Code (Salesforce CLI):
    python3 audit.py collect --target-org <org-alias> [--out <dir>] [--template "<Name or Id>"] [--object Contact]
                             [--flows all|named|none] [--source-limit 300]

claude.ai chat with a Salesforce connector (no CLI): run the queries through the connector, one pass at a time.
    python3 audit.py next-queries raw.json [--flows named] [--object Contact]   # [] when done
    python3 audit.py add raw.json --key <key> --records-file rows.json    # or --error "<message>"
    python3 audit.py build raw.json [--out <dir>] [--template "<Name or Id>"] [--instance-url https://<domain>]

Writes data-dictionary.md, data_dictionary.csv, template_references.csv, flow_references.csv and coverage.csv
into --out (default field-audit/<org Id>). Python 3 standard library only. Answers only whether Flow Tool Kit
references a field and where: it reads configuration and flow metadata, never a Form Submission record, and never
changes the org.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from fieldaudit import dictionary, report  # noqa: E402
from fieldaudit.orgreads import catalog, ocutil  # noqa: E402
from fieldaudit.queries import FLOW_SCOPES, next_queries, store  # noqa: E402

load, save, rows_from = catalog.load, catalog.save, catalog.rows_from


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def org_row(raw):
    return (ocutil.records(raw, "org") or [{}])[0]


def set_options(raw, args):
    """Options are fixed by the first call that names them and kept in raw.json."""
    options = raw.setdefault("options", {})
    if getattr(args, "object", None):
        options["objects"] = sorted(set(options.get("objects") or []) | set(args.object))
    for name in ("flows", "source_limit"):
        value = getattr(args, name, None)
        if value is not None:
            options[name] = value


def out_folder(raw, out):
    return pathlib.Path(out or f"field-audit/{org_row(raw).get('Id') or 'unknown-org'}")


def build_files(raw, out, instance_url="", template=None):
    folder = out_folder(raw, out)
    if not ocutil.ran(raw, "ftk") or not any(ocutil.val(r, "QualifiedApiName") for r in ocutil.records(raw, "ftk")):
        print(f"Flow Tool Kit is not installed in {org_row(raw).get('Name') or 'this org'}, so there is nothing "
              f"to audit.")
        return 0
    analysis = dictionary.analyze(raw)
    if template:
        analysis = dictionary.focus(analysis, template)
        if analysis is None:
            print(f"No Form Template named {template!r} uses any field; check the Name or Id.")
            return 1
    totals = report.write(str(folder), analysis, org_row(raw), raw.get("taken_at") or now(),
                          instance_url or raw.get("instance_url") or "")
    verdicts = ", ".join(f"{count} {name}" for name, count in totals["verdicts"].items()) or "no verdicts"
    print(f"Field audit of {org_row(raw).get('Name') or 'the org'}: {totals['fields']} fields, "
          f"{totals['template_references']} uses in templates and forms, {totals['flow_references']} in "
          f"Flow Tool Kit flows. "
          f"Verdicts: {verdicts}. {totals['documentation_gaps']} fields the org owns miss part of their "
          f"documentation. {totals['not_captured']} places not scanned, {totals['problems']} that could not be "
          f"parsed. Saved to {folder / 'data-dictionary.md'} and the CSV files beside it.")
    return 0


# ---- the Salesforce CLI runner ---------------------------------------------------------------------------------------

def collect(args):
    ok, info = catalog.sf(["org", "display", "--target-org", args.target_org] if args.target_org
                          else ["org", "display"])
    if not ok:
        print(f"No Salesforce org could be reached ({info}). Connect one with the Salesforce CLI and run this again.")
        return 1
    org = args.target_org or (info or {}).get("alias") or (info or {}).get("username")
    raw = {"source": "sf-cli", "taken_at": now(), "instance_url": (info or {}).get("instanceUrl") or "",
           "queries": {}}
    set_options(raw, args)
    passes = 0
    while True:
        todo = next_queries(raw)
        if not todo:
            break
        passes += 1
        print(f"pass {passes}: {len(todo)} queries", flush=True)
        # flows are one query each, so a pass can hold hundreds; run them side by side
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda query: catalog.run_query(query, org), todo))
        for query, result in zip(todo, results):
            store(raw, query, result)
    folder = out_folder(raw, args.out)
    save(folder / "raw.json", raw)
    return build_files(raw, args.out, template=args.template)


# ---- the connector path (chat) ---------------------------------------------------------------------------------------

def cmd_next(args):
    raw = load(args.raw, None) or {"source": "connector", "taken_at": now(), "queries": {}}
    set_options(raw, args)
    save(args.raw, raw)
    print(json.dumps(next_queries(raw), indent=1))
    return 0


def cmd_add(args):
    raw = load(args.raw, None) or {"source": "connector", "taken_at": now(), "queries": {}}
    pending = {query["key"]: query for query in next_queries(raw)}
    query = pending.get(args.key)
    if query is None:
        print(f"{args.key} is not a query this audit is waiting for; run next-queries to see the list.",
              file=sys.stderr)
        return 1
    if args.error:
        store(raw, query, {"error": args.error})
    else:
        store(raw, query, {"records": rows_from(load(args.records_file, []))})
    save(args.raw, raw)
    left = next_queries(raw)
    entry = raw["queries"][args.key]
    retry = next((q for q in left if q["key"] == args.key), None)
    if retry:
        print(f"added {args.key}; it failed on {retry['dropped'][-1]}, so it is listed again without that column")
    else:
        size = f"{len(entry.get('records') or [])} rows"
        print(f"added {args.key} ({size}); {len(left)} queries left in this pass"
              if left else f"added {args.key}; all reads done, run build")
    return 0


def cmd_build(args):
    raw = load(args.raw, None)
    if raw is None:
        print(f"{args.raw} not found", file=sys.stderr)
        return 1
    left = [q["key"] for q in next_queries(raw)]
    if left and not args.partial:
        print("not finished: still to run " + ", ".join(left[:20]) + ("..." if len(left) > 20 else "")
              + " (or pass --partial to build from what is there)", file=sys.stderr)
        return 1
    return build_files(raw, args.out, args.instance_url, args.template)


def _options(parser):
    parser.add_argument("--object", action="append",
                        help="another object whose custom fields all get a row and a verdict (repeatable); "
                             "Form Submission is always audited")
    parser.add_argument("--flows", choices=FLOW_SCOPES,
                        help="all (default): read every flow the org owns to find the Flow Tool Kit ones; named: "
                             "only the conversion and prefill flows templates and sections name, the screen "
                             "flows Flow Sections show, and their subflows; none. Only Flow Tool Kit flows are ever listed")
    parser.add_argument("--source-limit", type=int, dest="source_limit",
                        help="source records whose prefill mapping column is read, per Form Template Source "
                             "(default 300)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="field-audit: where Flow Tool Kit uses each field, and a data "
                                                 "dictionary")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("collect", help="read the org with the Salesforce CLI and write the files")
    p.add_argument("--target-org")
    p.add_argument("--out")
    p.add_argument("--template", help="narrow the files to one Form Template (Name or Id)")
    _options(p)
    p.set_defaults(fn=collect)
    p = sub.add_parser("next-queries", help="the queries raw.json still needs (connector path)")
    p.add_argument("raw")
    _options(p)
    p.set_defaults(fn=cmd_next)
    p = sub.add_parser("add", help="put one query's rows (or its error) into raw.json")
    p.add_argument("raw")
    p.add_argument("--key", required=True)
    p.add_argument("--records-file")
    p.add_argument("--error")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("build", help="write the files from a finished raw.json")
    p.add_argument("raw")
    p.add_argument("--out")
    p.add_argument("--instance-url", default="", help="the org's address, for links in the CSV files")
    p.add_argument("--partial", action="store_true", help="build even though some reads are still to run")
    p.add_argument("--template", help="narrow the files to one Form Template (Name or Id)")
    p.set_defaults(fn=cmd_build)
    args = parser.parse_args(argv)
    if args.command == "add" and not (args.records_file or args.error):
        parser.error("add needs --records-file or --error")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
