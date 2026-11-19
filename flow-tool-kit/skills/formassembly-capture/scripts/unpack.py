#!/usr/bin/env python3
"""Unpack a browser connector bundle (capture_connectors.js) into the archive.

Usage: python3 unpack.py <bundle.json> [--root _formassembly]

Replaces only the connector pages of the forms in the bundle, records what the browser saw
(objects opened, objects left collapsed, bytes) in each form's capture.json for verify.py,
and refreshes the connector list and the inventory's connectors column for those forms.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402


def unpack(bundle_path: str, root: str) -> dict:
    with open(bundle_path, encoding="utf-8") as handle:
        bundle = json.load(handle)
    if bundle.get("kind") != "connectors":
        raise SystemExit("not a connector bundle from capture_connectors.js")
    where = archive.paths(root)
    inventory = archive.load_inventory(root)
    written = 0
    for form_id, connectors in bundle.get("forms", {}).items():
        folder = os.path.join(where["archive"], form_id)
        if not os.path.isdir(folder):
            print(f"skip {form_id}: not in the archive; run collect.py first")
            continue
        captured = {path.split("/", 1)[1] for path in bundle.get("files", {}) if path.startswith(form_id + "/")}
        for name in os.listdir(folder):
            if name.startswith("connector-") and name.endswith(".html") and name not in captured:
                connector_id = name.rsplit("-", 1)[-1][:-5]
                if any(c["id"] == connector_id for c in connectors if archive.is_salesforce(c)):
                    os.remove(os.path.join(folder, name))
        archive.write_json(os.path.join(folder, "connectors.json"), connectors)
        stat = archive.load_json(os.path.join(folder, "capture.json"), {}) or {}
        stat["connectors"] = bundle.get("stats", {}).get(form_id, {}).get("connectors", {})
        stat["connectorPages"] = "browser " + bundle.get("capturedAt", "")[:10]
        archive.write_json(os.path.join(folder, "capture.json"), stat)
        if form_id in inventory:
            inventory[form_id]["connectors"] = archive.connector_summary(connectors)
    for path, content in bundle.get("files", {}).items():
        form_id = path.split("/", 1)[0]
        if os.path.isdir(os.path.join(where["archive"], form_id)):
            with open(os.path.join(where["archive"], path), "w", encoding="utf-8") as handle:
                handle.write(content)
            written += 1
    archive.write_inventory(root, list(inventory.values()))
    for problem in bundle.get("problems", []):
        print("problem: " + problem)
    return {"forms": len(bundle.get("forms", {})), "connector_pages": written}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("bundle")
    parser.add_argument("--root", default="_formassembly")
    args = parser.parse_args(argv)
    result = unpack(args.bundle, args.root)
    print(f"forms {result['forms']}  connector pages {result['connector_pages']}; next: verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
