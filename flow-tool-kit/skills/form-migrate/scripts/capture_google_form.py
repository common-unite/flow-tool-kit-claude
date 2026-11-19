#!/usr/bin/env python3
"""Capture a PUBLIC Google Form into ir.json from its page: every section, not just page 1.

    python3 <skill>/scripts/capture_google_form.py <viewform address> <out_dir> [--html <saved page>] [--name "<Form name>"]

Saves the page as <out_dir>/form.html (unless --html gives one or it is already there), reads the form data the page
embeds (FB_PUBLIC_LOAD_DATA_) and writes <out_dir>/ir.json. A Google Form has no Salesforce connector, so every
mapping becomes a review question. If the sandbox cannot reach the address, save the page in a browser
(Save Page As, HTML only) and pass it with --html.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import ir  # noqa: E402
from formmigrate.sources.google_forms import adapter, parser  # noqa: E402


def capture(url: str, out_dir: str, html_path: str | None = None, name: str = "") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    page = os.path.join(out_dir, "form.html")
    if html_path:
        if os.path.abspath(html_path) != os.path.abspath(page):
            shutil.copyfile(html_path, page)
    elif not os.path.exists(page):
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (form-migrate capture)"})
        with urllib.request.urlopen(request, timeout=60) as response, open(page, "wb") as handle:
            handle.write(response.read())
    document = adapter.build_from_file(page, form_name=name, source_url=url)
    with open(os.path.join(out_dir, "ir.json"), "w", encoding="utf-8") as handle:
        handle.write(ir.to_json(document))
    return document


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    args.add_argument("url")
    args.add_argument("out_dir")
    args.add_argument("--html", help="a saved copy of the form page, instead of downloading it")
    args.add_argument("--name", default="", help="form name; defaults to the form's own title")
    options = args.parse_args(argv)
    try:
        document = capture(options.url, options.out_dir, options.html, options.name)
    except parser.GoogleFormError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    sections = len(document["structure"])
    print(f"{document['source']['form_name']}: {len(document['fields'])} questions in {sections} sections, "
          f"{len(document['conditions'])} branch rules; no connector (Google Forms has none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
