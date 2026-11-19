#!/usr/bin/env python3
"""Write site-copy.md from a site crawl: the program page's words in full, the site's voice, and the opening lines of
every other program and about page.

    python3 make_site_copy.py _brand/<slug>/site-crawl.json _brand/<slug>/site-copy.md

form-design reads it for section titles, page descriptions, help text, the intro and the confirmation message, so the
form uses the organization's own names for the program, its rules, prices, dates and contacts, and sounds like the site.
The kit's voice (adjectives, do and avoid, sample headings and buttons) is written from it.
"""
import json
import pathlib
import re
import sys

UTILITY = re.compile(r"privacy|terms|cookie|cart|checkout|login|log-in|account|search|sitemap|shop|store|product|news|blog|"
                     r"press|careers|employment|jobs|faqs?|contact|donate|calendar|events?/\d", re.I)


def render(blocks):
    out = []
    first_heading = next((index for index, block in enumerate(blocks) if block["tag"] in ("h1", "h2")), 0)
    for block in blocks[first_heading:]:
        text = block["text"]
        if block["tag"] in ("h1", "h2"):
            out.append(f"\n## {text}\n")
        elif block["tag"] in ("h3", "h4"):
            out.append(f"\n### {text}\n")
        elif block["tag"] == "li":
            out.append(f"- {text}")
        else:
            out.append(text + "\n")
    return out


def site_copy(crawl):
    pages = crawl.get("pages") or {}
    program_path = re.sub(r"^https?://[^/]+", "", crawl.get("programPage") or "")
    lines = [f"# Site copy: {crawl.get('start')}", "",
             f"Read on {crawl.get('crawledOn')} from {len(pages)} pages. Program page: {crawl.get('programPage') or 'none given'}.", ""]
    if program_path and program_path in pages:
        lines += ["# Program page, in full", ""] + render(pages[program_path]["copy"]) + [""]
    buttons = {}
    for page in pages.values():
        for label in page.get("buttons", []):
            buttons[label] = buttons.get(label, 0) + 1
    home = pages.get("/", {})
    lines += ["# Voice", ""]
    if buttons:
        lines += ["Button labels on the site, most common first: " + ", ".join(f"{label} ({count})" for label, count in
                                                                                  sorted(buttons.items(), key=lambda item: -item[1])) + ".", ""]
    if home.get("headings"):
        lines += ["Home page headings: " + " / ".join(home["headings"]) + ".", ""]
    intro = [block["text"] for block in home.get("copy", []) if block["tag"] == "p" and len(block["text"]) > 60][:3]
    if intro:
        lines += ["Home page opening lines:", ""] + [f"> {text}" for text in intro] + [""]
    lines += ["# Other program and about pages", "", "Headings and opening lines, for the organization's own names and phrasing.", ""]
    for path, page in sorted(pages.items()):
        if path in ("/", program_path) or UTILITY.search(path):
            continue
        paragraphs = [block["text"] for block in page["copy"] if block["tag"] == "p" and len(block["text"]) > 60][:2]
        if not page["headings"] and not paragraphs:
            continue
        title = re.split(r"\s+[|:\-]\s+", page.get("title") or "")[0] or path
        lines += [f"## {title} ({path})", "", "Headings: " + " / ".join(page["headings"]), ""]
        lines += [f"> {text}" for text in paragraphs] + [""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)) + "\n"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    crawl = json.loads(pathlib.Path(argv[0]).read_text(encoding="utf-8"))
    text = site_copy(crawl)
    pathlib.Path(argv[1]).write_text(text, encoding="utf-8")
    print(argv[1], text.count("\n"), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
