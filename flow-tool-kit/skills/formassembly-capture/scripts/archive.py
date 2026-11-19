"""What every step of the account capture shares: the archive layout, the inventory,
the keep list, form statuses and the settings a form's files carry.

Layout under the root (default ``_formassembly``):

    inventory.csv              one row per form in the account (pipe-delimited)
    kept.txt                   the forms the last build used
    raw/                       API listings and browser bundles; keep out of version control
    archive/<form id>/         one folder per captured form
        form.html              the form markup (API definition, public page or an export)
        aliases.html           optional: the alias page, from an export
        connectors.json        the form's connectors: id, type, event, enabled
        connector-<type>-<id>.html   a connector's read-only view page, when captured
        capture.json           what the capture saw: counts used by verify.py
        settings.json          optional: settings read from the API definition
        processing.txt, notifications.txt   optional: settings pages from the browser step
        api-*.json             the API responses, saved by form-migrate's reader

Python 3 standard library only.
"""
from __future__ import annotations

import csv
import datetime
import html
import json
import os
import re

COLUMNS = ["form_id", "name", "completed", "incomplete", "last_modified", "last_response", "status", "status_basis", "connectors"]
STATUS_ORDER = {"active": 0, "check": 1, "inactive": 2, "never used": 3}
WINDOW_DAYS = 365

# Connector events as FormAssembly names them, in plain words.
EVENT_LABEL = {
    "beforerender": "Form opened (prefill)",
    "before_save": "Before the response is saved",
    "interactive": "Form submitted",
    "background": "After form submitted",
}

# Settings worth carrying, by the key FormAssembly uses.
SETTING_LABELS = {
    "thankyou_url": "After submit, go to",
    "thankyou_message": "Thank-you message",
    "notification_emails": "Notification emails to",
    "notification_type": "Notification email",
    "autoresponder_type": "Confirmation email to the respondent",
    "autoresponder_subject": "Confirmation email subject",
    "expired_message": "Message when closed",
    "response_quota": "Response limit",
    "use_save_resume": "Save and resume",
    "enabled": "E-signature",
}

# A link to a FormAssembly form, on any plan's host.
FORM_LINK = re.compile(r"(?:tfaforms\.(?:com|net)|formassembly\.com)/(?:forms/view/)?(\d{4,})")

# A prefill page prints the secure-parameter secret key; every capture blanks it.
SECRET = re.compile(r"Your Secret Key:?\s*(?:<[^>]*>\s*)*[0-9a-f]{20,}", re.I)


def paths(root: str) -> dict:
    return {
        "root": root,
        "archive": os.path.join(root, "archive"),
        "raw": os.path.join(root, "raw"),
        "inventory": os.path.join(root, "inventory.csv"),
        "kept": os.path.join(root, "kept.txt"),
    }


def load_inventory(root: str) -> dict:
    """``{form_id: row}`` in file order."""
    with open(paths(root)["inventory"], encoding="utf-8") as handle:
        return {row["form_id"]: row for row in csv.DictReader(handle, delimiter="|")}


def write_inventory(root: str, rows: list[dict]) -> None:
    os.makedirs(root, exist_ok=True)
    with open(paths(root)["inventory"], "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="|", lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([str(row.get(column, "")).replace("|", "/").replace("\n", " ") for column in COLUMNS])


def load_kept(root: str) -> set | None:
    """The forms the last build used, or None when no build ran yet."""
    path = paths(root)["kept"]
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: str) -> str:
    """A file's text, or "" when it is missing."""
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, default=str)


def cutoff(today: datetime.date) -> datetime.date:
    return today - datetime.timedelta(days=WINDOW_DAYS)


def count(value) -> int | None:
    """A response count as an int, or None when it is not known."""
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def status_from_date(completed, incomplete, last_response: str, today: datetime.date) -> tuple[str, str]:
    """(status, basis) from response counts and a last response date (YYYY-MM-DD or blank)."""
    if count(completed) == 0 and count(incomplete) in (0, None):
        return "never used", "no responses"
    if not last_response:
        return "check", "last response date unknown"
    window = cutoff(today).isoformat()
    if last_response >= window:
        return "active", f"a response on or after {window}"
    return "inactive", f"no response since {window}"


def connector_summary(connectors: list[dict]) -> str:
    return ", ".join(f"{c.get('type') or 'unknown'}@{c.get('event') or '?'}" + ("" if c.get("enabled", True) else "(off)") for c in connectors)


def is_salesforce(connector: dict) -> bool:
    return "salesforce" in (connector.get("type") or "").lower()


def is_prefill(connector: dict) -> bool:
    kind = (connector.get("type") or "").lower()
    return "pull" in kind or connector.get("event") == "beforerender"


def connector_file(folder: str, connector: dict) -> str | None:
    """The captured read-only page for a connector, or None."""
    for name in sorted(os.listdir(folder)):
        if name.startswith("connector-") and name.endswith(f"-{connector['id']}.html"):
            return os.path.join(folder, name)
    return None


def read_settings(folder: str) -> dict:
    """Key settings as ``{key: value}``: settings.json first, then the browser step's settings pages."""
    settings = {}
    saved = load_json(os.path.join(folder, "settings.json"), {}) or {}
    for key, value in saved.items():
        if key in SETTING_LABELS and value not in (None, ""):
            settings[key] = str(value)
    for name in ("processing.txt", "notifications.txt"):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for match in re.finditer(r"\{data((?:\[[^\]]+\])+)=(.*?)\}(?=\s|$)", text, re.S):
            key = re.findall(r"\[([^\]]+)\]", match.group(1))[-1]
            value = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group(2)))).strip()
            if key not in SETTING_LABELS or key in settings:
                continue
            if value in ("[x]", "[ ]"):
                value = "on" if value == "[x]" else "off"
            settings[key] = value
    return settings


def redirect_targets(settings: dict, form_id: str) -> list[str]:
    """Form ids the after-submit redirect sends people to (any FormAssembly host)."""
    targets = FORM_LINK.findall(settings.get("thankyou_url", ""))
    return [target for target in dict.fromkeys(targets) if target != form_id]


def effective_action(node: dict) -> str:
    """A connector step's real action. A "Lookup" step with field mappings that creates on no match
    or updates on a match writes the record, so it is an upsert, not only a match."""
    action = node.get("action") or "write"
    lookup = node.get("lookup") or {}
    outcomes = f"{lookup.get('on_no_match') or ''} {lookup.get('on_one_match') or ''}".lower()
    if action == "lookup" and node.get("mappings") and ("create" in outcomes or "update" in outcomes):
        return "upsert"
    return action


def name_of(inventory: dict):
    return lambda form_id: inventory.get(form_id, {}).get("name", form_id)
