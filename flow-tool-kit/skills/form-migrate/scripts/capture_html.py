#!/usr/bin/env python3
"""Read a form on any web page, by its address or from a saved copy, into ir.json. Standard library only.

    python3 <skill>/scripts/capture_html.py <address or saved .html> <out_dir> ["Form Name"] [--conditions-complete]

An address is fetched once with a plain GET: a 20 second timeout, no cookies, no sign-in, no credentials
(an address carrying user:password@ is refused). The page is saved as <out_dir>/form.html, read by the
html adapter, and written as <out_dir>/ir.json. A saved page (File, Save Page As, Web Page HTML only) is
read the same way, which is the route for a page behind a sign-in.

Many form builders draw the form with script after the page loads (Typeform, Jotform, Cognito Forms,
Microsoft Forms, Wufoo and Formstack embeds, HubSpot and others). The fetched page then holds a placeholder
and no questions. This script says so plainly and writes no ir.json: use a screenshot of each page or the
builder's own export, and the hand-written capture.json route (references/sources/hand-written.md).

Exit codes: 0 read, 2 usage, 3 the form is drawn by script or the page holds no questions, 4 fetch failed.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import ir  # noqa: E402
from formmigrate.sources.html import adapter, parser  # noqa: E402

TIMEOUT_SECONDS = 20
MAX_BYTES = 5 * 1024 * 1024
USER_AGENT = "form-migrate/1.0 (reads one public form page)"

# Markers of a form drawn by script: (pattern, builder, what to do instead).
SCRIPT_BUILDERS = [
    (r"embed\.typeform\.com|form\.typeform\.com|data-tf-(?:widget|live|popup)", "Typeform",
     "screenshot each question, or export the questions from the Typeform workspace"),
    (r"jotform\.com/jsform|form\.jotform\.com|jotfor\.ms|jotform\.com/\d{6,}", "Jotform",
     "screenshot each page, or open the form's own address (form.jotform.com/...) and save that page"),
    (r"cognitoforms\.com", "Cognito Forms", "screenshot each page of the form"),
    (r"forms\.office\.com|forms\.microsoft\.com", "Microsoft Forms",
     "screenshot each section, or download the responses workbook (its columns are the questions)"),
    (r"wufoo\.com/scripts/embed|wufoo\.com/embed", "Wufoo",
     "open the form's own wufoo.com address and save that page, or screenshot it"),
    (r"formstack\.com/forms/js|formstack\.com/forms/\?", "Formstack", "screenshot each page of the form"),
    (r"js\.hsforms\.net|hbspt\.forms\.create", "HubSpot", "screenshot the form"),
    (r"tally\.so/widgets|tally\.so/embed", "Tally", "screenshot each page of the form"),
    (r"paperform\.co", "Paperform", "screenshot each page of the form"),
    (r"surveymonkey\.com/r/|widget\.surveymonkey\.com", "SurveyMonkey", "screenshot each page of the survey"),
    (r"docs\.google\.com/forms", "Google Forms",
     "run capture_google_form.py on the form's own viewform address instead"),
]

_FORM_TAG_RE = re.compile(r"<form\b", re.I)


class FetchError(RuntimeError):
    """The page could not be fetched."""


def fetch(address: str, opener=None) -> str:
    """One plain GET: no cookies, no credentials, a timeout and a size cap."""
    parts = urllib.parse.urlsplit(address)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"Only http and https addresses are fetched, not {parts.scheme or 'a bare path'!r}.")
    if parts.username or parts.password:
        raise ValueError("The address carries a user name or password. Never pass credentials: save the page "
                         "from a signed-in browser and read the saved file instead.")
    request = urllib.request.Request(address, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    # A bare opener: no cookie handler, no stored passwords, nothing but the GET.
    opener = opener or urllib.request.build_opener()
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_BYTES + 1)
            charset = response.headers.get_content_charset() or "utf-8"
    except (urllib.error.URLError, OSError) as error:
        raise FetchError(f"Could not fetch {address}: {error}. Save the page from a browser and pass the file.") from error
    if len(raw) > MAX_BYTES:
        raise FetchError(f"{address} is larger than {MAX_BYTES // (1024 * 1024)} MB; save the form page itself instead.")
    return raw.decode(charset, errors="replace")


def script_drawn(html_text: str, model) -> list[str]:
    """Plain warnings when the questions are drawn by script rather than written in the page."""
    warnings = []
    for pattern, builder, instead in SCRIPT_BUILDERS:
        if re.search(pattern, html_text, re.I):
            warnings.append(f"This page embeds a {builder} form, which is drawn by script after the page loads, "
                            f"so its questions are not in the page. Instead: {instead}.")
    questions = [field for field in model.ordered_fields() if not field.is_hidden]
    if not questions:
        if _FORM_TAG_RE.search(html_text):
            warnings.append("The page has a <form> element with no questions in it: the fields are added by "
                            "script. Screenshot each page of the live form instead.")
        elif not warnings:
            warnings.append("The page holds no form questions at all. Check the address points at the form "
                            "itself, or screenshot the live form.")
    return warnings


def capture(source: str, out_dir: str, form_name: str = "", conditions_complete: bool = False,
            opener=None) -> tuple[int, dict | None, list[str]]:
    """Read one page into out_dir. Returns (exit code, the IR or None, warnings)."""
    os.makedirs(out_dir, exist_ok=True)
    is_address = bool(re.match(r"^https?://", source, re.I))
    if is_address:
        html_text = fetch(source, opener=opener)
        with open(os.path.join(out_dir, "form.html"), "w", encoding="utf-8") as handle:
            handle.write(html_text)
    else:
        with open(source, encoding="utf-8", errors="replace") as handle:
            html_text = handle.read()
    model = parser.parse(html_text)
    warnings = script_drawn(html_text, model)
    if not [field for field in model.ordered_fields() if not field.is_hidden]:
        return 3, None, warnings
    document = adapter.build(model, form_name=form_name, source_url=source if is_address else "",
                             conditions_are_complete=conditions_complete)
    for warning in warnings:
        document["findings"].append({"source": "capture_html", "message": warning})
    with open(os.path.join(out_dir, "ir.json"), "w", encoding="utf-8") as handle:
        handle.write(ir.to_json(document))
    return 0, document, warnings


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    complete = "--conditions-complete" in argv
    argv = [arg for arg in argv if arg != "--conditions-complete"]
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    source, out_dir = argv[0], argv[1]
    form_name = argv[2] if len(argv) == 3 else ""
    try:
        code, document, warnings = capture(source, out_dir, form_name, complete)
    except (ValueError, FetchError) as error:
        print(f"Not read: {error}", file=sys.stderr)
        return 4
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if document is None:
        print("No ir.json written. Use the screenshot or hand-written route: write capture.json and run the "
              "manual adapter (references/sources/hand-written.md).", file=sys.stderr)
        return code
    fields = document["fields"]
    coverage = document["source"]["coverage"]
    print(f"{len(fields)} questions in {len(document['form']['section_paths'])} sections, "
          f"{len(document['custom_scripts'])} inline scripts; conditions {coverage['conditions']}, "
          f"connector {coverage['connector']}. Wrote {os.path.join(out_dir, 'ir.json')}. "
          "Read the findings before confirming the list with the person.")
    return code


if __name__ == "__main__":
    sys.exit(main())
