#!/usr/bin/env python3
"""Capture a PUBLIC FormAssembly form into ir.json: no account, no alias export, no connector.

    python3 -I <form-migrate>/scripts/capture_public.py <form_id> <out_dir> "<Form name>" [--html <saved form.html>]

Saves the rendered page as <out_dir>/form.html (unless it is already there or --html gives one), builds the aliases from
the page itself (labels, option labels and titles, legends; formmigrate.sources.formassembly.page_aliases) and writes
<out_dir>/ir.json in the same shape as a full export. The connector is not_captured, so prefill, lookups and the
Salesforce mapping are unknown, not absent: raise them as review questions.

Works with no account at all, so it is the first step for a prospect's form. Reads attributes in any order, so a
select whose aria-required comes before its id, options carrying data-conditionals and matrix rows labelled by a th
all parse (the repository's tests/skills/form-migrate/test_public_capture.py holds one case for each). If the sandbox cannot reach the address, save the
page some other way and pass it with --html.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import ir  # noqa: E402
from formmigrate.sources.formassembly import adapter  # noqa: E402

PUBLIC_URL = "https://www.tfaforms.com/{}"


def capture(form_id: str, out_dir: str, name: str, html_path: str | None = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    page = os.path.join(out_dir, "form.html")
    if html_path:
        if os.path.abspath(html_path) != os.path.abspath(page):
            shutil.copyfile(html_path, page)
    elif not os.path.exists(page):
        request = urllib.request.Request(PUBLIC_URL.format(form_id), headers={"User-Agent": "Mozilla/5.0 (form-migrate public capture)"})
        with urllib.request.urlopen(request, timeout=60) as response, open(page, "wb") as handle:
            handle.write(response.read())
    if os.path.exists(os.path.join(out_dir, "aliases.html")):
        print("aliases.html is present: building from the full export", file=sys.stderr)
    document = adapter.build_from_files(out_dir, form_id=form_id, form_name=name, source_url=PUBLIC_URL.format(form_id))
    with open(os.path.join(out_dir, "ir.json"), "w", encoding="utf-8") as handle:
        handle.write(ir.to_json(document))
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("form_id")
    parser.add_argument("out_dir")
    parser.add_argument("name")
    parser.add_argument("--html", help="a saved copy of the public form page, instead of downloading it")
    args = parser.parse_args(argv)
    document = capture(args.form_id, args.out_dir, args.name, args.html)
    unlabeled = [f["id"] for f in document["fields"] if not f.get("label")]
    print(f"{args.form_id}: {len(document['fields'])} fields, {len(document['conditions'])} conditions, "
          f"{len(unlabeled)} without a visible label {unlabeled[:10]}; connector not captured")


if __name__ == "__main__":
    main()
