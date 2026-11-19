"""Check the markup a page puts in the standard HTML Editor (and the Rich Content Editor) before it is drawn or built.

    python3 -I htmlcheck.py <file.html> [--audience guest|portal|internal] [--palette '{"brand": "#2e844a"}']

build_site_review.py runs this on every `htmlEditor` and `richText` item in page.json. An error stops the run, naming the
section; a warning goes on the Section jobs handoff checklist. The rules and why: references/html-editor.md.

Errors (the page is never drawn or built with them):
- a tag that runs code, loads another document or collects input: script, the privileged x-oasis-script, iframe, frame,
  object, embed, applet, form and its controls, base, meta, link;
- an event handler attribute (onclick and every other on*);
- a javascript:, vbscript: or data: address in href, src, srcset, action or xlink:href (a data: image only warns);
- a style that loads or runs something: expression(), behavior:, @import, url(javascript:...);
- a URL expression ({!Route.x}, {!x}) inside an attribute: the site escapes <, > and & in it, not a javascript: address;
- an image with no alt attribute (alt="" marks a decorative one).

Warnings: a <style> tag, an image or file from an outside host, a target="_blank" link without rel="noopener", a fixed
width wider than a phone, an h1, a Site Blocks {{Field}} merge field, user data on a guest page, a colour outside the
site palette.
Python 3 standard library only.
"""
import argparse
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

REFUSED_TAGS = {
    "script": "runs code; the HTML Editor is for markup only",
    "x-oasis-script": "a privileged script belongs only in the site's head markup, added and reviewed by the site's admin",
    "iframe": "loads another document into the page",
    "frame": "loads another document into the page",
    "frameset": "loads other documents into the page",
    "object": "embeds a plugin or another document",
    "embed": "embeds a plugin or another document",
    "applet": "embeds a plugin",
    "form": "collects input outside Flow Tool Kit; put a form in a Form Slot",
    "input": "collects input outside Flow Tool Kit; put a form in a Form Slot",
    "button": "a control with no handler; use a block's buttons",
    "select": "collects input outside Flow Tool Kit; put a form in a Form Slot",
    "textarea": "collects input outside Flow Tool Kit; put a form in a Form Slot",
    "base": "changes where every link on the page points",
    "meta": "page-level setting; it belongs in the site's head markup",
    "link": "loads a stylesheet or resource; it belongs in the site's head markup",
}
URL_ATTRS = {"href", "src", "srcset", "action", "formaction", "xlink:href", "poster", "background", "cite", "data"}
BAD_SCHEME = re.compile(r"^\s*(?:javascript|vbscript|data)\s*:", re.I)
DATA_IMAGE = re.compile(r"^\s*data:image/(?:png|jpe?g|gif|webp);", re.I)
BAD_STYLE = re.compile(r"expression\s*\(|behavio(?:u)?r\s*:|@import|url\(\s*['\"]?\s*(?:javascript|vbscript):|-moz-binding", re.I)
URL_EXPRESSION = re.compile(r"\{!\s*(?:Route\.[A-Za-z_]\w*|[A-Za-z_]\w*)\s*\}")
USER_EXPRESSION = re.compile(r"\{!\s*User\.(?:Record\.\w+|userId)\s*\}")
MERGE_FIELD = re.compile(r"\{\{\s*[A-Za-z_$][\w.]*\s*\}\}")
WIDTH = re.compile(r"(?:^|;)\s*(?:min-)?width\s*:\s*(\d+)px", re.I)
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
SALESFORCE_HOSTS = re.compile(r"(?:^|\.)(?:salesforce\.com|force\.com|site\.com|my\.site\.com|salesforce-sites\.com|sfdcstatic\.com)$", re.I)
PHONE = 390
NAMED_EXPRESSIONS = {"Site.basePath", "User.isGuest", "User.userId"}


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []  # (tag, {attr: value}, line)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag.lower(), {k.lower(): (v or "") for k, v in attrs}, self.getpos()[0]))

    handle_startendtag = handle_starttag


def _host(url):
    m = re.match(r"^\s*(?:https?:)?//([^/:?#]+)", url or "", re.I)
    return m.group(1).lower() if m else None


def check_markup(markup, where="markup", audience=(), palette=None, kind="htmlEditor"):
    """(errors, warnings) for one item's richTextValue. audience: the page's audiences (guest, portal, internal)."""
    errors, warnings = [], []
    text = str(markup or "")
    scan = _Scan()
    try:
        scan.feed(text)
        scan.close()
    except Exception as e:  # html.parser is lenient; anything it cannot read is a reason to look by hand
        errors.append(f"{where}: the markup cannot be read ({e}); fix it before it is drawn")
        return errors, warnings
    allowed_hex = {str(v).lower() for v in (palette or {}).values()}
    seen_style_tag = False
    for tag, attrs, line in scan.tags:
        at = f"{where} line {line}"
        if tag in REFUSED_TAGS:
            errors.append(f"{at}: <{tag}> {REFUSED_TAGS[tag]}")
        if tag == "style" and not seen_style_tag:
            seen_style_tag = True
            warnings.append(f"{at}: a <style> tag may be removed, or apply to the whole page; use style attributes, or put shared CSS in the site's head markup")
        for name, value in attrs.items():
            if name.startswith("on"):
                errors.append(f"{at}: the {name} attribute runs code; the HTML Editor is for markup only")
            if name in URL_ATTRS:
                if BAD_SCHEME.match(value):
                    if tag == "img" and name == "src" and DATA_IMAGE.match(value):
                        warnings.append(f"{at}: an image written into the markup; load it as an Asset File and point to that instead")
                    else:
                        errors.append(f"{at}: {name} uses a {value.split(':', 1)[0].strip().lower()}: address")
                host = _host(value)
                if host and tag in ("img", "source", "video", "audio", "track") and not SALESFORCE_HOSTS.search(host):
                    warnings.append(f"{at}: {tag} from {host}: the site's Content Security Policy must trust that host, and every visitor's browser "
                                    "calls it; load the file as an Asset File instead")
            if name == "style":
                if BAD_STYLE.search(value):
                    errors.append(f"{at}: the style loads or runs something ({BAD_STYLE.search(value).group(0)})")
                widths = [int(w) for w in WIDTH.findall(value)]
                if any(w > PHONE for w in widths) and "max-width" not in value.lower():
                    warnings.append(f"{at}: a fixed width of {max(widths)}px is wider than a phone; add max-width: 100%")
            for m in URL_EXPRESSION.finditer(value):
                if m.group(0)[2:-1].strip() in NAMED_EXPRESSIONS:
                    continue
                errors.append(f"{at}: {m.group(0)} in the {name} attribute: a value from the address is escaped for <, > and &, "
                              "not for a javascript: address or a quote; show it as text, or use a block")
            for colour in HEX.findall(value):
                if allowed_hex and colour.lower() not in allowed_hex:
                    warnings.append(f"{at}: colour {colour} is not in the site palette; use var(--dxp-g-brand, <palette hex>) or a palette colour")
        if tag == "img" and "alt" not in attrs:
            errors.append(f"{at}: an image with no alt text; describe it, or write alt=\"\" for a decorative one")
        if tag == "a" and attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", ""):
            warnings.append(f"{at}: a link opening a new tab needs rel=\"noopener\"")
        if tag == "h1":
            warnings.append(f"{at}: an h1; the opening hero holds the page's one h1, so start at h2")
    if MERGE_FIELD.search(text):
        warnings.append(f"{where}: {MERGE_FIELD.search(text).group(0)} is Site Blocks merge syntax; the {kind_label(kind)} shows it as typed. "
                        "Record data belongs in a block or a record card")
    if "guest" in (audience or ()) and USER_EXPRESSION.search(text):
        warnings.append(f"{where}: {USER_EXPRESSION.search(text).group(0)} on a page guests see shows the guest user's own value, not a person's")
    return sorted(set(errors), key=errors.index), sorted(set(warnings), key=warnings.index)


def kind_label(kind):
    return "HTML Editor" if kind == "htmlEditor" else "Rich Content Editor"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", help="a file holding the markup")
    ap.add_argument("--audience", action="append", default=[], help="guest, portal or internal; repeat for several")
    ap.add_argument("--palette", help="the site palette as JSON, so its colours are not flagged")
    args = ap.parse_args(argv)
    errors, warnings = check_markup(pathlib.Path(args.file).read_text(), args.file, args.audience,
                                    json.loads(args.palette) if args.palette else None)
    for line in errors:
        print("ERROR " + line)
    for line in warnings:
        print("warn  " + line)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
