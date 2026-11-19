#!/usr/bin/env python3
"""Read one FormAssembly form through the REST API into ir.json.

    # token: the plugin's FormAssembly access token setting, else the environment variable
    export FORMASSEMBLY_ACCESS_TOKEN=...        # never in a file, never in the chat
    export FORMASSEMBLY_API_BASE=https://<instance>.tfaforms.net/api_v1/   # if not formassembly.com
    python3 <skill>/scripts/formassembly_api.py <form_id> <out_dir> "<Form name>" [--no-connectors]

Saves the API responses beside the IR (api-form.json, api-connectors.json, one
api-connector-<id>.json per connector the token can open), builds ir.json from
the form markup (the definition's, or a form.html already in out_dir, or the
public page), and lists the connectors as a finding. Connector mappings stay
not_captured: read the connector's read-only view page for them
(references/sources/formassembly.md).
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import ir  # noqa: E402
from formmigrate.sources.formassembly import adapter, api  # noqa: E402


def public_url(form_id: str) -> str:
    """The public form address for the account's API base."""
    host = urllib.parse.urlsplit(os.environ.get(api.BASE_ENV) or api.DEFAULT_BASE).netloc
    if host in ("app.formassembly.com", "developer.formassembly.com", ""):
        return f"https://www.tfaforms.com/{form_id}"
    return f"https://{host}/{form_id}"


def run(form_id: str, out_dir: str, name: str, read_connectors: bool = True, opener=None) -> dict:
    report = api.fetch(form_id, out_dir, read_connectors=read_connectors, opener=opener)
    page = os.path.join(out_dir, "form.html")
    if not os.path.exists(page):
        request = urllib.request.Request(public_url(form_id), headers={"User-Agent": "form-migrate"})
        try:
            with (opener or urllib.request.urlopen)(request, timeout=60) as response, open(page, "wb") as handle:
                handle.write(response.read())
        except (urllib.error.URLError, OSError) as error:
            raise api.ApiError(
                f"No form markup, and the public page could not be read ({error}). Save the "
                "public form page as form.html in the folder, then run this again.") from None
    document = adapter.build_from_files(out_dir, form_id=form_id, form_name=name)
    api.annotate(document, report)
    with open(os.path.join(out_dir, "ir.json"), "w", encoding="utf-8") as handle:
        handle.write(ir.to_json(document))
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("form_id")
    parser.add_argument("out_dir")
    parser.add_argument("name")
    parser.add_argument("--no-connectors", action="store_true")
    args = parser.parse_args(argv)
    try:
        document = run(args.form_id, args.out_dir, args.name, not args.no_connectors)
    except api.ApiError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    connectors = document["source"].get("api", {}).get("connectors", [])
    print(f"{args.form_id}: {len(document['fields'])} fields, {len(document['conditions'])} conditions, "
          f"{len(connectors)} connectors listed; connector mappings not captured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
