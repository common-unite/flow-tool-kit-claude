#!/usr/bin/env python3
"""Collect every form in a FormAssembly account into the archive, with no browser.

Two sources, which can be combined (run api first, then exports to add connector pages):

  python3 collect.py api [--root _formassembly] [--admin] [--forms 101,102] [--today YYYY-MM-DD]
                         [--no-connectors] [--response-check]
      Lists the account's forms through the FormAssembly REST API and reads each one with
      form-migrate's reader (formassembly_api.py): the form definition and markup, the
      connector list, and each connector definition the token may open.
      Token: the plugin's FormAssembly access token setting (sensitive, read as
      CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN), else FORMASSEMBLY_ACCESS_TOKEN in
      the session's environment. Never in a file.
      FORMASSEMBLY_API_BASE for plans not on app.formassembly.com.

  python3 collect.py exports <folder> [--root _formassembly] [--today YYYY-MM-DD]
      Reads files a person saved from FormAssembly, one folder per form id:
        <folder>/<form id>/form.html          the form page (required unless the API run saved it)
        <folder>/<form id>/aliases.html       optional: the field alias page, as HTML
        <folder>/<form id>/connector-<id>.html  each Salesforce connector's read-only view page
      and an optional <folder>/forms.csv (form_id,name,completed,incomplete,last_response).

Writes <root>/inventory.csv and <root>/archive/<form id>/ (layout in archive.py). A run
updates only the forms it reads; other rows and files stay. Then run verify.py.

Status uses a 12-month window ending on --today (default: today). The API gives response
counts but no last-response date, and its only dated call (the response export) returns
respondents' answers. So by default a form with no responses is "never used", and every
other form is "check": no answer content is read. With --response-check, the script asks the
export for one row since the window start, keeps only that row's submission date in memory,
drops the rest at once, and never saves any of it.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import json
import os
import re
import shutil
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402
from reader import api, formassembly_api  # noqa: E402

INPUTS = re.compile(r"<(?:input|select|textarea)\b", re.I)
CONDITIONS = re.compile(r'data-condition="')


def form_counts(html: str) -> dict:
    return {"formInputs": len(INPUTS.findall(html)), "formConditions": len(CONDITIONS.findall(html))}


def blank_secrets(text: str) -> str:
    return re.sub(r"(Your Secret Key:?\s*(?:<[^>]*>\s*)*)[0-9a-f]{20,}", r"\1[REDACTED]", text, flags=re.I)


# -- API ----------------------------------------------------------------------------------

def _flat(node: dict) -> dict:
    return {key.lower(): value for key, value in node.items() if not isinstance(value, (dict, list))}


def forms_from_index(data) -> list[dict]:
    """Each form in a forms index response as one flat dict (lower-case keys), whatever the wrapper.

    An entry such as ``{"Form": {...}, "Aggregate_metadata": {...}}`` merges both, so the
    response counts sit beside the id and name.
    """
    found, seen = [], set()

    def is_form(node):
        keys = {key.lower() for key in node}
        return "id" in keys and "name" in keys

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        nested = [value for value in node.values() if isinstance(value, dict)]
        form = node.get("Form") if isinstance(node.get("Form"), dict) else next((value for value in nested if is_form(value)), None)
        if form is not None and not is_form(node):
            merged = {}
            for value in nested:
                merged.update(_flat(value))
            merged.update(_flat(form))
        elif is_form(node):
            merged = _flat(node)
        else:
            for value in node.values():
                walk(value)
            return
        form_id = str(merged.get("id", "")).strip()
        if form_id and form_id not in seen:
            seen.add(form_id)
            found.append(merged)

    walk(data)
    return found


def _enabled(status: str):
    status = (status or "").strip().lower()
    if status in ("1", "active", "enabled", "true", "on"):
        return True
    if status in ("0", "inactive", "disabled", "false", "off"):
        return False
    return None


def connector_type(name: str, kind: str) -> str:
    raw = re.sub(r"^Connector", "", (kind or name or "").strip())
    return re.sub(r"[^a-z0-9_]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw).lower()).strip("_")


def connector_events(data) -> dict:
    """``{connector id: event}`` from a connector index response."""
    events = {}

    def walk(node):
        if isinstance(node, dict):
            keys = {key.lower(): key for key in node}
            if "id" in keys and "event" in keys:
                events[str(node[keys["id"]])] = str(node[keys["event"]])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return events


def settings_from_definition(data) -> dict:
    """Settings a form definition carries under FormAssembly's own key names."""
    wanted = {key.lower(): key for key in archive.SETTING_LABELS}
    found = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                name = wanted.get(str(key).lower())
                if name and not isinstance(value, (dict, list)) and value not in (None, "") and name not in found:
                    found[name] = str(value)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return found


def has_rows(data):
    """True when a response export holds at least one response, False when empty, None when unclear."""
    if data is None:
        return None
    if isinstance(data, list):
        return bool(data)
    if isinstance(data, dict):
        lists = []

        def walk(node):
            if isinstance(node, list):
                lists.append(node)
            elif isinstance(node, dict):
                for value in node.values():
                    walk(value)

        walk(data)
        if lists:
            return any(lists)
        for key in ("count", "total", "total_count"):
            if isinstance(data.get(key), (int, str)) and archive.count(data[key]) is not None:
                return archive.count(data[key]) > 0
    return None


SUBMITTED_KEY = re.compile(r"^(?:date_?submitted|submitted(?:_?(?:at|date|on))?|date_?created|created(?:_?at)?|response_?date)$", re.I)
DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})|(\d{2})/(\d{2})/(\d{4})")


def submitted_date(data) -> str:
    """The first submission-date value in an export, as YYYY-MM-DD, or "". Reads only keys named for the submission date."""
    stack = [data]
    while stack:
        node = stack.pop(0)
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, (str, int)) and SUBMITTED_KEY.match(str(key)):
                    match = DATE.search(str(value))
                    if match:
                        year, month, day = (match.group(1), match.group(2), match.group(3)) if match.group(1) else (match.group(6), match.group(4), match.group(5))
                        return f"{year}-{month}-{day}"
            stack.extend(value for value in node.values() if isinstance(value, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)
    return ""


def recent_response(form_id: str, since: datetime.date, opener=None):
    """(used since ``since``: True, False or None; submission date or ""; note). Opt-in only.

    Asks for one row. Only its submission date is kept; the row itself is dropped before
    this returns, and nothing from it is written anywhere.
    """
    query = urllib.parse.urlencode({"date_from": since.isoformat(), "filter": "all", "page_size": 1})
    try:
        raw = api.get(f"responses/export/{form_id}.json?{query}", opener=opener)
    except api.ApiError as error:
        return None, "", f"response check failed: {error}"
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        data = None
    del raw
    found = has_rows(data)
    date = submitted_date(data) if found else ""
    del data
    return found, date, ""


def collect_api(args, opener=None) -> list[dict]:
    where = archive.paths(args.root)
    os.makedirs(where["raw"], exist_ok=True)
    os.makedirs(where["archive"], exist_ok=True)
    base = api.admin_base() if args.admin else None
    raw = api.get("forms/index.json", base=base, opener=opener)
    with open(os.path.join(where["raw"], "api-forms.json"), "wb") as handle:
        handle.write(raw)
    listed = forms_from_index(json.loads(raw.decode("utf-8-sig")))
    wanted = {item.strip() for item in (args.forms or "").split(",") if item.strip()}
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    rows, problems = [], []
    for entry in listed:
        form_id = str(entry["id"])
        if wanted and form_id not in wanted:
            continue
        name = str(entry.get("name") or form_id)
        folder = os.path.join(where["archive"], form_id)
        os.makedirs(folder, exist_ok=True)
        completed = entry.get("submitted_count", entry.get("response_count", ""))
        incomplete = entry.get("saved_count", "")
        row = {"form_id": form_id, "name": name, "completed": completed, "incomplete": incomplete,
               "last_modified": str(entry.get("modified") or "")[:10], "last_response": ""}
        try:
            document = formassembly_api.run(form_id, folder, name, read_connectors=not args.no_connectors, opener=opener)
            report = document["source"].get("api", {})
        except api.ApiError as error:
            problems.append(f"{form_id} {name}: {error}")
            report = {"connectors": [], "notes": [str(error)]}
        archive.write_json(os.path.join(folder, "api-report.json"), report)

        events = connector_events(archive.load_json(os.path.join(folder, "api-connectors.json"), None))
        connectors = [{
            "id": c["id"], "type": connector_type(c.get("name", ""), c.get("type", "")),
            "event": events.get(c["id"], ""), "enabled": _enabled(c.get("status", "")), "listed_by": "api",
        } for c in report.get("connectors", [])]
        archive.write_json(os.path.join(folder, "connectors.json"), connectors)

        definition = archive.load_json(os.path.join(folder, "api-form.json"), None)
        settings = settings_from_definition(definition) if definition is not None else {}
        if settings:
            archive.write_json(os.path.join(folder, "settings.json"), settings)

        stat = archive.load_json(os.path.join(folder, "capture.json"), {}) or {}
        page = os.path.join(folder, "form.html")
        if os.path.exists(page):
            stat.update(form_counts(archive.read_text(page)))
        stat.update({"source": "api", "publicUrl": formassembly_api.public_url(form_id), "capturedAt": today.isoformat()})
        archive.write_json(os.path.join(folder, "capture.json"), stat)

        if archive.count(completed) == 0 and archive.count(incomplete) in (0, None):
            row["status"], row["status_basis"] = "never used", "no responses"
        elif not args.response_check:
            row["status"], row["status_basis"] = "check", "has responses; last use not read (no answer content without --response-check)"
        else:
            since = archive.cutoff(today)
            recent, date, note = recent_response(form_id, since, opener=opener)
            if recent is True:
                row["status"], row["status_basis"] = "active", f"a response on or after {since.isoformat()}"
                row["last_response"] = date
            elif recent is False:
                row["status"], row["status_basis"] = "inactive", f"no response since {since.isoformat()}"
            else:
                row["status"], row["status_basis"] = "check", note or "response export not readable"
        row["connectors"] = archive.connector_summary(connectors)
        rows.append(row)
        print(f"{form_id} {name}: {row['status']}, {len(connectors)} connector(s)")
    if wanted - {row["form_id"] for row in rows}:
        problems.append("not in the forms list: " + ", ".join(sorted(wanted - {row["form_id"] for row in rows})))
    summary = {"forms_listed": len(listed), "forms_read": len(rows), "problems": problems}
    print(json.dumps(summary))
    return rows


# -- Exports ------------------------------------------------------------------------------

PREFILL_PAGE = re.compile(r'<fieldset class="sobject"|class="sobjectSelected"')
SUBMIT_PAGE = re.compile(r'class="sobject[^"]*"[^>]*id="sobject-\d+"|id="sobject-\d+"[^>]*class="sobject')


def exported_connector(path: str, text: str, index: int) -> dict | None:
    if PREFILL_PAGE.search(text):
        kind, event = "salesforce_pull", "beforerender"
    elif SUBMIT_PAGE.search(text):
        kind, event = "salesforce2", "interactive"
    else:
        return None
    digits = re.findall(r"(\d+)", os.path.basename(path))
    found = re.search(r"connector_salesforce\w*/(?:setup|view)/(\d+)", text)
    connector_id = digits[-1] if digits else (found.group(1) if found else f"export{index}")
    return {"id": connector_id, "type": kind, "event": event, "enabled": True, "listed_by": "export"}


def form_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def collect_exports(args) -> list[dict]:
    where = archive.paths(args.root)
    os.makedirs(where["archive"], exist_ok=True)
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    listed = {}
    forms_csv = os.path.join(args.folder, "forms.csv")
    if os.path.exists(forms_csv):
        with open(forms_csv, encoding="utf-8-sig") as handle:
            listed = {row["form_id"].strip(): row for row in csv.DictReader(handle) if row.get("form_id")}
    rows, problems = [], []
    for source in sorted(glob.glob(os.path.join(args.folder, "*"))):
        form_id = os.path.basename(source)
        if not os.path.isdir(source) or not form_id.isdigit():
            continue
        folder = os.path.join(where["archive"], form_id)
        os.makedirs(folder, exist_ok=True)
        connectors = archive.load_json(os.path.join(folder, "connectors.json"), []) or []
        by_id = {c["id"]: c for c in connectors}
        for index, path in enumerate(sorted(glob.glob(os.path.join(source, "*.html"))), 1):
            name = os.path.basename(path)
            text = archive.read_text(path)
            if name in ("form.html", "aliases.html"):
                with open(os.path.join(folder, name), "w", encoding="utf-8") as handle:
                    handle.write(text)
                continue
            found = exported_connector(path, text, index)
            if not found:
                problems.append(f"{form_id}: {name} is neither a form page nor a connector read-only view; skipped")
                continue
            listed_already = by_id.get(found["id"], {})
            # The page decides the type; the API list, when it ran, knows the event and whether it is on.
            found.update({key: listed_already[key] for key in ("event", "enabled") if listed_already.get(key) not in (None, "")})
            for old in glob.glob(os.path.join(folder, f"connector-*-{found['id']}.html")):
                os.remove(old)
            with open(os.path.join(folder, f"connector-{found['type']}-{found['id']}.html"), "w", encoding="utf-8") as handle:
                handle.write(blank_secrets(text))
            by_id[found["id"]] = {**listed_already, **found}
        for name in ("processing.txt", "notifications.txt"):
            if os.path.exists(os.path.join(source, name)):
                shutil.copy(os.path.join(source, name), os.path.join(folder, name))
        connectors = list(by_id.values())
        archive.write_json(os.path.join(folder, "connectors.json"), connectors)

        page = os.path.join(folder, "form.html")
        html = archive.read_text(page)
        if not html:
            problems.append(f"{form_id}: no form.html in the export or the archive")
        stat = archive.load_json(os.path.join(folder, "capture.json"), {}) or {}
        stat.update(form_counts(html))
        stat.setdefault("publicUrl", f"https://www.tfaforms.com/{form_id}")
        stat["source"] = "api" if stat.get("source") == "api" else "exports"
        stat["exportsRead"] = today.isoformat()
        stat.setdefault("capturedAt", today.isoformat())
        archive.write_json(os.path.join(folder, "capture.json"), stat)

        given = listed.get(form_id, {})
        row = {"form_id": form_id, "name": (given.get("name") or "").strip() or form_title(html) or form_id,
               "completed": (given.get("completed") or "").strip(), "incomplete": (given.get("incomplete") or "").strip(),
               "last_response": (given.get("last_response") or "").strip(), "connectors": archive.connector_summary(connectors)}
        if given:
            row["status"], row["status_basis"] = archive.status_from_date(row["completed"], row["incomplete"], row["last_response"], today)
        rows.append(row)
        print(f"{form_id} {row['name']}: {len(connectors)} connector(s) on file")
    print(json.dumps({"forms_read": len(rows), "problems": problems}))
    return rows


def merge_inventory(root: str, rows: list[dict]) -> None:
    """Update the rows read this run; keep every other form, and keep known values a run left blank."""
    existing = archive.load_inventory(root) if os.path.exists(archive.paths(root)["inventory"]) else {}
    for row in rows:
        old = existing.get(row["form_id"], {})
        merged = dict(old)
        merged.update({key: value for key, value in row.items() if value not in (None, "")})
        merged.setdefault("status", "check")
        merged.setdefault("status_basis", "no response data in the export")
        existing[row["form_id"]] = merged
    archive.write_inventory(root, list(existing.values()))


def main(argv=None, opener=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    from_api = sub.add_parser("api")
    from_api.add_argument("--admin", action="store_true", help="list every form in an Enterprise instance (admin token)")
    from_api.add_argument("--forms", default="", help="comma list of form ids; default every form")
    from_api.add_argument("--no-connectors", action="store_true")
    from_api.add_argument("--response-check", action="store_true",
                          help="opt in: read one response row per form to learn if it was used in the window; only its date is kept")
    from_exports = sub.add_parser("exports")
    from_exports.add_argument("folder")
    for each in (from_api, from_exports):
        each.add_argument("--root", default="_formassembly")
        each.add_argument("--today", default="", help="end of the 12-month status window; default today")
    args = parser.parse_args(argv)
    try:
        rows = collect_api(args, opener=opener) if args.mode == "api" else collect_exports(args)
    except api.ApiError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    merge_inventory(args.root, rows)
    print(f"inventory: {archive.paths(args.root)['inventory']}; next: verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
