#!/usr/bin/env python3
"""Check the capture is complete and safe before anything is built from it.

Usage: python3 verify.py [--root _formassembly] [--require-connectors]

Prints, in order: the status counts, every FAIL (the capture lost data or kept a secret),
every GAP (a Salesforce connector whose mapping page is not captured yet: unknown, not
absent), warnings, and the "keep too?" forms a likely kept form sends people to.
Exits 1 on any FAIL, and on a GAP with --require-connectors. Prints the form ids to fill
the gaps with, for an export or for the browser step.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402

MIN_CONNECTOR_BYTES = 2000
TOKEN_ENV = "FORMASSEMBLY_ACCESS_TOKEN"
# The plugin's sensitive formassembly_access_token setting, read before TOKEN_ENV.
SETTING_ENV = "CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN"
TOKEN_IN_URL = re.compile(r"access_token=[A-Za-z0-9._~+/=-]{16,}")
COLLAPSED = re.compile(r'class="sobject\b[^"]*\bcollapsed\b')


def check_form(folder: str) -> tuple[list, list, list]:
    failures, gaps, warnings = [], [], []
    stat = archive.load_json(os.path.join(folder, "capture.json"), {}) or {}
    connectors = archive.load_json(os.path.join(folder, "connectors.json"), []) or []
    form_html = archive.read_text(os.path.join(folder, "form.html"))
    if not re.search(r"<(?:input|select|textarea)\b", form_html, re.I):
        failures.append("form page has no fields (save the form page as form.html in the export)")
    elif stat.get("formConditions") is not None and len(re.findall(r'data-condition="', form_html)) != stat["formConditions"]:
        failures.append("show/hide rule count changed between capture and disk")
    if not os.path.exists(os.path.join(folder, "aliases.html")):
        warnings.append("no alias page: option labels come from the form page")

    for connector in connectors:
        if not archive.is_salesforce(connector):
            continue
        label = f"connector {connector['id']} ({connector.get('type') or 'type unknown'}, {'prefill' if archive.is_prefill(connector) else 'submit'})"
        path = archive.connector_file(folder, connector)
        if not path:
            if connector.get("enabled") is False:
                warnings.append(f"{label}: disabled, mapping not captured")
            else:
                gaps.append(f"{label}: mapping not captured")
            continue
        html = archive.read_text(path)
        detail = (stat.get("connectors") or {}).get(connector["id"], {})
        collapsed = detail.get("collapsed") or len(COLLAPSED.findall(html))
        if detail.get("error"):
            failures.append(f"{label}: {detail['error']}")
        elif collapsed:
            failures.append(f"{label}: {collapsed} objects still collapsed, their mappings are missing")
        elif len(html) < MIN_CONNECTOR_BYTES and connector.get("enabled") is not False:
            failures.append(f"{label}: only {len(html)} bytes")
        elif not re.search(r'class="sobject|id="sobject-', html):
            warnings.append(f"{label}: page has no objects")
    return failures, gaps, warnings


def secret_hits(root: str) -> list[str]:
    """Files under the root that still hold a secret key or the access token."""
    tokens = [t for t in (os.environ.get(n, "").strip() for n in (SETTING_ENV, TOKEN_ENV)) if len(t) >= 8]
    hits = []
    for folder, _, names in os.walk(root):
        for name in names:
            path = os.path.join(folder, name)
            try:
                text = archive.read_text(path)
            except OSError:
                continue
            relative = os.path.relpath(path, root)
            if archive.SECRET.search(text):
                hits.append(f"{relative}: secure-parameter secret key not blanked")
            if any(token in text for token in tokens) or TOKEN_IN_URL.search(text):
                hits.append(f"{relative}: holds an access token; delete the file and rotate the token")
    return hits


def keep_suggestions(root: str, inventory: dict) -> list[tuple[str, str]]:
    likely = {form_id for form_id, row in inventory.items() if row.get("status") in ("active", "check")}
    found = []
    for form_id in sorted(likely):
        settings = archive.read_settings(os.path.join(archive.paths(root)["archive"], form_id))
        for target in archive.redirect_targets(settings, form_id):
            if target in inventory and target not in likely:
                found.append((target, form_id))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default="_formassembly")
    parser.add_argument("--require-connectors", action="store_true", help="treat a connector without its mapping page as a failure")
    args = parser.parse_args(argv)
    inventory = archive.load_inventory(args.root)
    name = archive.name_of(inventory)

    statuses = {}
    for row in inventory.values():
        statuses[row.get("status") or "check"] = statuses.get(row.get("status") or "check", 0) + 1
    print(f"forms in inventory: {len(inventory)}  status: " + ", ".join(f"{key} {value}" for key, value in sorted(statuses.items(), key=lambda item: archive.STATUS_ORDER.get(item[0], 9))))

    failing, gap_forms, checked, connector_total = [], [], 0, 0
    lines = []
    for form_id, row in inventory.items():
        folder = os.path.join(archive.paths(args.root)["archive"], form_id)
        if not os.path.isdir(folder):
            lines.append(f"FAIL {form_id} {row['name']}: not captured")
            failing.append(form_id)
            continue
        checked += 1
        failures, gaps, warnings = check_form(folder)
        connector_total += sum(1 for c in archive.load_json(os.path.join(folder, "connectors.json"), []) or [] if archive.is_salesforce(c))
        lines += [f"FAIL {form_id} {row['name']}: {m}" for m in failures]
        lines += [f"GAP  {form_id} {row['name']}: {m}" for m in gaps]
        lines += [f"warn {form_id} {row['name']}: {m}" for m in warnings]
        if failures:
            failing.append(form_id)
        if gaps:
            gap_forms.append(form_id)
    secrets = secret_hits(args.root)
    lines += [f"FAIL secret {hit}" for hit in secrets]

    print(f"forms checked: {checked}  Salesforce connectors: {connector_total}  failing forms: {len(failing)}  forms with connector gaps: {len(gap_forms)}")
    for line in lines:
        print(line)
    for target, source in keep_suggestions(args.root, inventory):
        print(f"keep too? {target} {name(target)} ({inventory[target].get('status')}): {source} {name(source)} sends people to it")

    redo = sorted(set(failing) | set(gap_forms))
    if redo:
        print("\nForms to fill from an export (save each connector's read-only view page as "
              "<exports>/<form id>/connector-<connector id>.html), or, after the person agrees, from the browser step:")
        print("  " + ", ".join(redo))
        print("  localStorage.setItem('faCaptureConfig', JSON.stringify({formIds: " + json.dumps(redo) + "}))")
    if failing or secrets or (gap_forms and args.require_connectors):
        return 1
    print("capture complete" + (" except the connector gaps listed (their mappings are unknown, not absent)" if gap_forms else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
