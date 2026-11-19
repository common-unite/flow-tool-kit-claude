#!/usr/bin/env python3
"""org-catalog: read an org's Flow Tool Kit components and templates into catalog.json, and match a design against it.

Claude Code (Salesforce CLI):
    python3 catalog.py collect --target-org <org-alias> [--out <dir>] [--config flow-tool-kit.json] [--skip-placements]

claude.ai chat with a Salesforce connector (no CLI): run the queries through the connector, one pass at a time.
    python3 catalog.py next-queries raw.json            # the queries still needed, as JSON; [] when done
    python3 catalog.py add raw.json --key <key> --records-file rows.json   # or --error "<message>"
    python3 catalog.py add-brand-file raw.json --id <ContentVersion Id> --file brand-kit.json   # optional
    python3 catalog.py add-placements raw.json --dir <folder of retrieved metadata>             # optional
    python3 catalog.py build raw.json [--out <dir>] [--config flow-tool-kit.json]

No org connected:
    python3 catalog.py empty [--out <dir>]

Reading a catalog:
    python3 catalog.py check <catalog.json> [--org-id <Id>] [--max-age-hours 24]   # exit 0 fresh, 2 stale, 3 other org
    python3 catalog.py match <catalog.json> <plan.json> [--out match.json] [--threshold 0.8]
    python3 catalog.py name-check <catalog.json> --object Form_Submission__c --field Submitted_By__c

Writes catalog.json and catalog.md into --out (default ftk-catalog/<org Id>, or ftk-catalog/no-org). Python 3 standard
library only; reads configuration, never a respondent's answers.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ocbuild import build, empty, markdown, now  # noqa: E402
from ocmatch import THRESHOLD, match_design, match_markdown  # noqa: E402
from ocplaces import KINDS, scan_folder  # noqa: E402
from ocqueries import MISSING_COLUMN, ftk_present, next_queries, without_missing_column  # noqa: E402
from ocutil import NS, bare, canonical_object  # noqa: E402

MAX_AGE_HOURS = 24
API_VERSION = "v61.0"


# ---- files -----------------------------------------------------------------------------------------------------------

def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, data):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def edition_from(config_path, org_id):
    config = load(config_path, {}) if config_path else {}
    return (((config or {}).get("orgs") or {}).get(org_id) or {}).get("edition")


def write_catalog(catalog, out):
    org_id = (catalog.get("org") or {}).get("id")
    folder = pathlib.Path(out or f"ftk-catalog/{org_id or 'no-org'}")
    save(folder / "catalog.json", catalog)
    (folder / "catalog.md").write_text(markdown(catalog), encoding="utf-8")
    return folder


def one_line(catalog, folder):
    """The line Claude repeats to the person."""
    if catalog["status"] == "no org":
        return f"No Salesforce org is connected, so the catalog is empty and marked no org ({folder / 'catalog.json'})."
    if catalog["status"] == "no package":
        return f"{catalog['status_note']} ({folder / 'catalog.json'})"
    c = catalog["counts"]
    return (f"Catalog of {catalog['org']['name']}: {c['components']} Form Components ({c['metadata_components']} metadata, "
            f"{c['record_components']} record), {c['templates']} Form Templates, {c['repeated_sections']} repeated sections, "
            f"{c['mapped_forms']} mapped forms, {c.get('places_outside_templates', 0)} places outside templates (flows, Lightning "
            f"pages, site pages, wrapper components)" + ("" if (catalog.get("placements") or {}).get("complete") else
                                                        " [not every kind of place was read: see catalog.md]")
            + f". Brand kit: {catalog['brand_kit']['found']}. Status {catalog['status']}, "
            f"{len(catalog['problems'])} problems. Saved to {folder / 'catalog.json'} and catalog.md.")


# ---- the Salesforce CLI runner ---------------------------------------------------------------------------------------

def sf(args, cwd=None):
    """Run the sf CLI with --json; (ok, result or error message)."""
    try:
        done = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True, timeout=600, cwd=cwd)
    except FileNotFoundError:
        return False, "the Salesforce CLI (sf) is not installed"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    try:
        data = json.loads(done.stdout or "{}")
    except ValueError:
        return False, (done.stderr or done.stdout or "no output").strip()[:400]
    if data.get("status") not in (0, None) or done.returncode:
        return False, str(data.get("message") or data.get("name") or done.stderr)[:400]
    return True, data.get("result")


def run_query(query, org):
    """Run one query. A tooling query falls back to the data API; a column an older package lacks is dropped and the
    query rerun, and the dropped columns are recorded."""
    soql, dropped = query["soql"], []
    for _ in range(10):
        args = ["data", "query", "--query", soql, "--target-org", org]
        ok, result = sf(args + (["--use-tooling-api"] if query.get("tooling") else []))
        if not ok and query.get("tooling"):
            ok, result = sf(args)  # FieldDefinition also answers through the data API
        if ok:
            entry = {"records": (result or {}).get("records") or []}
            return dict(entry, dropped_columns=dropped) if dropped else entry
        retry = without_missing_column(soql, result)
        if retry is None:
            return dict({"error": result}, dropped_columns=dropped) if dropped else {"error": result}
        dropped.append(MISSING_COLUMN.search(str(result)).group(1))
        soql = retry
    return {"error": "too many missing columns", "dropped_columns": dropped}


def read_brand_files(raw, org):
    content = raw.setdefault("brand_file_content", {})
    for row in (raw["queries"].get("brand_files") or {}).get("records") or []:
        if row.get("Id") in content:
            continue
        try:
            done = subprocess.run(["sf", "api", "request", "rest", f"/services/data/{API_VERSION}/sobjects/ContentVersion/{row['Id']}/VersionData",
                                   "--target-org", org], capture_output=True, text=True, timeout=120)
            content[row["Id"]] = done.stdout if done.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            content[row["Id"]] = None


# Metadata types holding the places a form is used outside Form Templates. SOQL cannot read them; a retrieve can.
RETRIEVE = {"flows": ["Flow"], "lightning_pages": ["FlexiPage"], "site_pages": ["ExperienceBundle", "DigitalExperienceBundle"],
            "wrapper_components": ["LightningComponentBundle"]}


def short_read(result, out):
    """The retrieve's own list of files against the files that reached the folder: {"listed", "arrived"} when fewer
    arrived (seen with several retrieves against one org at the same time), else None. package.xml is not counted."""
    listed = (result or {}).get("fileProperties") or []
    listed = [listed] if isinstance(listed, dict) else listed
    names = {str(p.get("fileName") or "") for p in listed if isinstance(p, dict)}
    names = {n for n in names if n and not n.endswith("package.xml")}
    out = pathlib.Path(out)
    arrived = sum(1 for n in names if (out / n).exists() or (out / "unpackaged" / n).exists())
    return {"listed": len(names), "arrived": arrived} if arrived < len(names) else None


def read_placements(raw, org):
    """Retrieve flows, Lightning pages, site pages and the org's own Lightning web components into a temporary folder
    (Metadata API format, read only; nothing is deployed) and keep only the places that name a form."""
    placements = raw.setdefault("placements", {})
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        (base / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}],
                                                            "sourceApiVersion": API_VERSION.lstrip("v")}))
        for kind, types in RETRIEVE.items():
            entry, errors = {"files": 0, "items": [], "unreadable": []}, []
            for mtype in types:
                out = base / "retrieved" / mtype
                ok, result = sf(["project", "retrieve", "start", "--metadata", mtype, "--target-metadata-dir", str(out), "--unzip",
                                 "--target-org", org], cwd=str(base))
                if not ok:
                    errors.append(f"{mtype}: {result}")
                    continue
                short = short_read(result, out)
                if short:
                    entry.setdefault("short", []).append({"type": mtype, **short})
                found = scan_folder(out).get(kind) or {}
                entry["files"] += found.get("files", 0)
                entry["items"] += found.get("items", [])
                entry["unreadable"] += found.get("unreadable", [])
            if len(errors) == len(types):
                placements[kind] = {"error": "; ".join(errors)}
            else:
                entry["unreadable"] += [f"not retrieved, {e}" for e in errors]
                placements[kind] = entry


def collect(args):
    ok, info = sf(["org", "display", "--target-org", args.target_org] if args.target_org else ["org", "display"])
    if not ok:
        catalog = empty("no org", f"No Salesforce org could be reached ({info}), so this catalog is empty and every section is new.")
        folder = write_catalog(catalog, args.out)
        print(one_line(catalog, folder))
        return 0
    org = args.target_org or (info or {}).get("alias") or (info or {}).get("username")
    raw = {"source": "sf-cli", "taken_at": now(), "queries": {}}
    while True:
        todo = next_queries(raw)
        if not todo:
            break
        for query in todo:
            raw["queries"][query["key"]] = run_query(query, org)
    read_brand_files(raw, org)
    if ftk_present(raw) and not args.skip_placements:
        read_placements(raw, org)
    org_row = ((raw["queries"].get("org") or {}).get("records") or [{}])[0]
    catalog = build(raw, edition_from(args.config, org_row.get("Id")))
    folder = write_catalog(catalog, args.out)
    save(folder / "raw.json", raw)
    print(one_line(catalog, folder))
    return 0


# ---- the connector path (chat) ---------------------------------------------------------------------------------------

def rows_from(data):
    """Rows from whatever a connector returned: a list, {records: [...]}, or {result: {records: [...]}}."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "result", "data"):
            if key in data:
                return rows_from(data[key])
    return []


def cmd_next(args):
    raw = load(args.raw, {"queries": {}})
    print(json.dumps(next_queries(raw), indent=1))
    return 0


def cmd_add(args):
    raw = load(args.raw, None) or {"source": "connector", "taken_at": now(), "queries": {}}
    if args.error:
        raw["queries"][args.key] = {"error": args.error}
    else:
        raw["queries"][args.key] = {"records": rows_from(load(args.records_file, []))}
    save(args.raw, raw)
    left = next_queries(raw)
    print(f"added {args.key}; {len(left)} queries left in this pass" if left else f"added {args.key}; all reads done, run build")
    return 0


def cmd_add_brand_file(args):
    """The text of a brand-kit.json file the connector downloaded, keyed by its ContentVersion Id."""
    raw = load(args.raw, None) or {"source": "connector", "taken_at": now(), "queries": {}}
    raw.setdefault("brand_file_content", {})[args.id] = pathlib.Path(args.file).read_text(encoding="utf-8")
    save(args.raw, raw)
    print(f"added brand file {args.id}")
    return 0


def cmd_add_placements(args):
    """Places a form is used outside Form Templates, from a folder of retrieved metadata (flows, flexipages, site
    bundles, lwc): for a connector that can retrieve metadata, or a project's source pulled from the org. Only the kinds
    of place whose files are in the folder count as read."""
    raw = load(args.raw, None) or {"source": "connector", "taken_at": now(), "queries": {}}
    found = scan_folder(args.dir)
    placements = raw.setdefault("placements", {})
    for kind in KINDS:
        if kind in found:
            placements[kind] = found[kind]
    save(args.raw, raw)
    read = [f"{kind} ({len(found[kind]['items'])} places in {found[kind]['files']} files)" for kind in KINDS if kind in found]
    unread = [kind for kind in KINDS if kind not in placements]
    print(("read " + ", ".join(read) if read else "no flows, Lightning pages, site pages or Lightning web components in that folder")
          + (f"; not read: {', '.join(unread)}" if unread else ""))
    return 0


def cmd_build(args):
    raw = load(args.raw)
    if raw is None:
        print(f"{args.raw} not found", file=sys.stderr)
        return 1
    left = [q["key"] for q in next_queries(raw)]
    if left:
        print("not finished: still to run " + ", ".join(left), file=sys.stderr)
        return 1
    org_row = ((raw.get("queries", {}).get("org") or {}).get("records") or [{}])[0]
    catalog = build(raw, edition_from(args.config, org_row.get("Id")))
    folder = write_catalog(catalog, args.out)
    print(one_line(catalog, folder))
    return 0


def cmd_empty(args):
    catalog = empty("no org", "No Salesforce org is connected, so this catalog is empty and every section is new. "
                              "Salesforce targets in the design are marked verify until an org is connected.")
    folder = write_catalog(catalog, args.out)
    print(one_line(catalog, folder))
    return 0


# ---- reading a catalog -----------------------------------------------------------------------------------------------

def freshness(catalog, org_id=None, max_age_hours=MAX_AGE_HOURS):
    """(exit code, sentence). 0 fresh, 2 stale, 3 taken from another org (or no org while one is connected)."""
    taken = datetime.fromisoformat(catalog["taken_at"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - taken).total_seconds() / 3600
    caught = (catalog.get("org") or {}).get("id")
    if org_id and catalog.get("status") == "no org":
        return 3, "The catalog was taken with no org connected; an org is connected now, so run org-catalog again."
    if org_id and caught and caught[:15] != org_id[:15]:
        return 3, f"The catalog is of another org ({caught}); run org-catalog against this one."
    if age > max_age_hours:
        return 2, f"The catalog is {age:.0f} hours old (limit {max_age_hours}); run org-catalog again before designing."
    return 0, f"The catalog is fresh ({age:.1f} hours old, status {catalog.get('status')})."


def cmd_check(args):
    catalog = load(args.catalog)
    if catalog is None:
        print("No catalog file: run org-catalog first.")
        return 2
    code, sentence = freshness(catalog, args.org_id, args.max_age_hours)
    print(sentence)
    return code


def cmd_match(args):
    catalog, design = load(args.catalog), load(args.design)
    if catalog is None or design is None:
        print("catalog or design file not found", file=sys.stderr)
        return 1
    code, sentence = freshness(catalog, None, args.max_age_hours)
    if code and not args.allow_stale:
        print(sentence)
        return code
    if catalog["status"] in ("no org", "no package"):
        print(f"Catalog status is {catalog['status']}: no existing components to match, so every section is new.")
    result = match_design(catalog, design, args.threshold)
    if args.out:
        save(args.out, result)
    print(match_markdown(result))
    return 0


def name_check(catalog, obj, field):
    """Whether a field name is free on an object: exists, would sit beside a packaged twin, or is free."""
    obj = canonical_object(obj)
    info = (catalog.get("fields_index") or {}).get(obj)
    if not info or not info.get("read") or info.get("fields") is None:
        return "unknown", (f"{obj} fields are not in the catalog. Check with a Tooling API FieldDefinition query or a metadata "
                           f"list of CustomField, never with a describe: a describe leaves out fields you cannot read.")
    fields = info["fields"]
    name = field.replace("*__", NS)
    if not name.startswith(NS) and NS + name in fields:
        state = "already sits" if name in fields else "would sit"
        return "twin", (f"{name} {state} beside the packaged {NS}{name}. The Conversion Setup action leaves your field out of the "
                        f"record it hands a flow, because inside the package the bare name means the packaged field. "
                        f"Never create it; read an existing one with your own Get Records.")
    if name in fields:
        return "exists", f"{obj}.{name} already exists ({fields[name].get('label')}, {fields[name].get('type')}). Reuse it."
    if name.startswith(NS) and bare(name) in fields:
        return "exists", f"Your own {bare(name)} already sits beside the packaged {name}; read it with your own Get Records."
    return "free", f"{obj}.{name} does not exist (checked against every field, including ones hidden from your profile)."


def cmd_name_check(args):
    catalog = load(args.catalog)
    if catalog is None:
        print("No catalog file: run org-catalog first.")
        return 2
    verdict, sentence = name_check(catalog, args.object, args.field)
    print(sentence)
    return {"free": 0, "exists": 4, "twin": 5, "unknown": 6}[verdict]


def main(argv=None):
    parser = argparse.ArgumentParser(description="org-catalog: a reuse map of the org's Flow Tool Kit components and templates")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("collect", help="read the org with the Salesforce CLI and write the catalog")
    p.add_argument("--target-org")
    p.add_argument("--out")
    p.add_argument("--config", help="the project's flow-tool-kit.json, to copy the edition answer into the catalog")
    p.add_argument("--skip-placements", action="store_true",
                   help="do not retrieve flows, Lightning pages, site pages and components (used_in is then templates only)")
    p.set_defaults(fn=collect)
    p = sub.add_parser("next-queries", help="the queries raw.json still needs (connector path)")
    p.add_argument("raw")
    p.set_defaults(fn=cmd_next)
    p = sub.add_parser("add", help="put one query's rows (or its error) into raw.json")
    p.add_argument("raw")
    p.add_argument("--key", required=True)
    p.add_argument("--records-file")
    p.add_argument("--error")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("add-brand-file", help="put a downloaded brand-kit.json into raw.json (optional)")
    p.add_argument("raw")
    p.add_argument("--id", required=True, help="the brand file's ContentVersion Id")
    p.add_argument("--file", required=True)
    p.set_defaults(fn=cmd_add_brand_file)
    p = sub.add_parser("add-placements", help="put the flows, pages and components in a folder of retrieved metadata into raw.json (optional)")
    p.add_argument("raw")
    p.add_argument("--dir", required=True)
    p.set_defaults(fn=cmd_add_placements)
    p = sub.add_parser("build", help="write the catalog from a finished raw.json")
    p.add_argument("raw")
    p.add_argument("--out")
    p.add_argument("--config")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("empty", help="write an empty catalog marked no org")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_empty)
    p = sub.add_parser("check", help="is the catalog fresh, and of this org?")
    p.add_argument("catalog")
    p.add_argument("--org-id")
    p.add_argument("--max-age-hours", type=float, default=MAX_AGE_HOURS)
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("match", help="candidates for each section of a design (plan.json)")
    p.add_argument("catalog")
    p.add_argument("design")
    p.add_argument("--out")
    p.add_argument("--threshold", type=float, default=THRESHOLD)
    p.add_argument("--max-age-hours", type=float, default=MAX_AGE_HOURS)
    p.add_argument("--allow-stale", action="store_true")
    p.set_defaults(fn=cmd_match)
    p = sub.add_parser("name-check", help="is a field name free on an object?")
    p.add_argument("catalog")
    p.add_argument("--object", required=True)
    p.add_argument("--field", required=True)
    p.set_defaults(fn=cmd_name_check)
    args = parser.parse_args(argv)
    if args.command == "add" and not (args.records_file or args.error):
        parser.error("add needs --records-file or --error")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
