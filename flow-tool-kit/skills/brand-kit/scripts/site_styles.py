#!/usr/bin/env python3
"""Read an organization's colors, fonts, corner radius and button style from its own stylesheets, without a browser.

    python3 site_styles.py --crawl _brand/<slug>/site-crawl.json --out _brand/<slug>/site-styles.json
    python3 site_styles.py --css saved.css [--css more.css] --out _brand/<slug>/site-styles.json     (stylesheets saved by hand)

With --crawl it reads the home page's and the program page's stylesheets (their links and inline <style> blocks were kept
by site_crawl.py), follows @import once, and tallies:

- colors with where they are used (button background, link text, heading text, header background, theme color, CSS
  variables named brand, primary or accent), each scored by how much that place says "brand";
- platform defaults left out, and listed in notes: a site theme's untouched preset palette (block editor presets, a page
  builder's starting kit colors, a CSS framework's default variables) is not the organization's brand;
- neutrals (grays, near black, near white) kept apart, for the heading and background choices;
- fonts by role (body, headings, buttons), web font links and @font-face families, icon fonts left out;
- corner radius of buttons and of inputs and cards, heading weight, and whether buttons are filled or outlined.

Stylesheets give the colors a site declares, not always the ones it shows; a page built mostly in a page builder's inline
settings can hide its brand from them. The rendered-page scan (site-scan.js, through render_scan.cjs or a browser tool)
reads computed colors when this is not enough; ask before using a browser.

Standard library only.
"""
import argparse
import colorsys
import json
import re
import sys
import urllib.parse

from webfetch import POLITE, NetworkUnavailable

MAX_SHEETS, MAX_BYTES = 30, 3_000_000
SKIP_SHEET = re.compile(r"/wp-includes/|/wp-admin/|dashicons|admin-bar|font-?awesome|/plugins/(?!elementor)", re.I)
HEX = re.compile(r"#([0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})\b", re.I)
FUNC = re.compile(r"(rgba?|hsla?)\(([^)]*)\)", re.I)
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
ROLES = (
    ("button", re.compile(r"button|\.btn\b|\bbtn-|\.button|wp-block-button|wp-element-button|input\[type=.?(?:submit|button)|elementor-button|\.cta\b", re.I)),
    ("link", re.compile(r"(?:^|[\s>,+~])a(?=$|[\s:.,\[>])", re.I)),
    ("heading", re.compile(r"(?:^|[\s>,+~.])h[1-6](?=$|[\s:.,\[>])|\.(?:entry|page|section|site)-title", re.I)),
    ("header", re.compile(r"header|masthead|navbar|\bnav\b|top-?bar", re.I)),
    ("footer", re.compile(r"footer", re.I)),
    ("body", re.compile(r"^\s*(?:html|body|:root)\s*$", re.I)),
)
WEIGHTS = {("button", "background"): 6, ("link", "text"): 4, ("theme", "meta"): 4, ("heading", "text"): 3, ("header", "background"): 3,
           ("footer", "background"): 2, ("button", "border"): 2, ("button", "text"): 1}
BRANDY_VARIABLE = re.compile(r"brand|primary|accent|secondary|main|theme|highlight", re.I)
# Untouched platform defaults: (variable or class pattern, default value). A site that changed them keeps its own value.
PLATFORM_DEFAULTS = {
    "--wp--preset--color--black": "#000000", "--wp--preset--color--cyan-bluish-gray": "#abb8c3", "--wp--preset--color--white": "#ffffff",
    "--wp--preset--color--pale-pink": "#f78da7", "--wp--preset--color--vivid-red": "#cf2e2e",
    "--wp--preset--color--luminous-vivid-orange": "#ff6900", "--wp--preset--color--luminous-vivid-amber": "#fcb900",
    "--wp--preset--color--light-green-cyan": "#7bdcb5", "--wp--preset--color--vivid-green-cyan": "#00d084",
    "--wp--preset--color--pale-cyan-blue": "#8ed1fc", "--wp--preset--color--vivid-cyan-blue": "#0693e3",
    "--wp--preset--color--vivid-purple": "#9b51e0",
    "--e-global-color-primary": "#6ec1e4", "--e-global-color-secondary": "#54595f", "--e-global-color-text": "#7a7a7a",
    "--e-global-color-accent": "#61ce70",
    "--bs-blue": "#0d6efd", "--bs-indigo": "#6610f2", "--bs-purple": "#6f42c1", "--bs-pink": "#d63384", "--bs-red": "#dc3545",
    "--bs-orange": "#fd7e14", "--bs-yellow": "#ffc107", "--bs-green": "#198754", "--bs-teal": "#20c997", "--bs-cyan": "#0dcaf0",
    "--bs-primary": "#0d6efd", "--bs-secondary": "#6c757d", "--bs-success": "#198754", "--bs-info": "#0dcaf0",
    "--bs-warning": "#ffc107", "--bs-danger": "#dc3545",
}
PRESET_CLASS = re.compile(r"\.has-[a-z0-9-]+-(?:background-)?color|\.has-[a-z0-9-]+-border-color", re.I)
NOT_FONTS = re.compile(r"awesome|dashicons|icomoon|eicons|glyph|icon|fontello|material symbols|material icons|^-apple-system$|"
                       r"^blinkmacsystemfont$|^system-ui$|^inherit$|^initial$|^unset$|^var\(", re.I)
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif"}


# ---- colors ---------------------------------------------------------------------------------------------------------

def to_hex(value):
    """A CSS color as #rrggbb, or None for a see-through or unreadable one."""
    value = value.strip()
    m = HEX.fullmatch(value) or HEX.match(value)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            if len(h) == 4 and int(h[3], 16) < 8:
                return None
            h = "".join(c * 2 for c in h[:3])
        elif len(h) == 8:
            if int(h[6:], 16) < 128:
                return None
            h = h[:6]
        return "#" + h.lower()
    m = FUNC.match(value)
    if not m:
        return {"white": "#ffffff", "black": "#000000"}.get(value.lower())
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) < 3:
        return None
    if len(parts) >= 4:
        alpha = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1)
        if alpha < 0.5:
            return None
    try:
        if m.group(1).lower().startswith("rgb"):
            rgb = [round(float(p.rstrip("%")) * 2.55) if p.endswith("%") else round(float(p)) for p in parts[:3]]
        else:
            h, s, l = float(parts[0].rstrip("deg")) / 360, float(parts[1].rstrip("%")) / 100, float(parts[2].rstrip("%")) / 100
            rgb = [round(c * 255) for c in colorsys.hls_to_rgb(h % 1, l, s)]
    except ValueError:
        return None
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in rgb)


def is_neutral(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return s < 0.12 or l > 0.95 or l < 0.08


def role_of(selector):
    for role, pattern in ROLES:
        if pattern.search(selector):
            return role
    return "other"


def property_kind(prop):
    prop = prop.lower()
    if prop.startswith("background"):
        return "background"
    if prop == "color":
        return "text"
    if prop.startswith("border") or prop.startswith("outline"):
        return "border"
    if prop in ("fill", "stroke"):
        return "icon"
    return None


# ---- stylesheets ----------------------------------------------------------------------------------------------------

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def rules(css):
    """(selector, [(property, value)]) for every rule, at-rule wrappers flattened (the innermost braces are the rules)."""
    out = []
    for selector, body in RULE.findall(strip_comments(css)):
        selector = selector.strip()
        if selector.startswith("@"):
            selector = selector.split(";")[-1].strip()
        declarations = []
        for part in body.split(";"):
            if ":" in part:
                prop, value = part.split(":", 1)
                declarations.append((prop.strip(), value.replace("!important", "").strip()))
        out.append((selector, declarations))
    return out


def variables_of(all_rules):
    found = {}
    for selector, declarations in all_rules:
        for prop, value in declarations:
            if prop.startswith("--"):
                found.setdefault(prop, value)
    return found


def resolve(value, variables, depth=0):
    if "var(" not in value or depth > 5:
        return value
    return resolve(VAR.sub(lambda m: variables.get(m.group(1), m.group(2) or ""), value), variables, depth + 1)


def imports(css, base):
    return [urllib.parse.urljoin(base, m) for m in re.findall(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", strip_comments(css))]


def fetch_sheets(urls):
    """{url: css text} for each stylesheet and the ones it @imports, and {url: error}."""
    texts, errors, queue, seen = {}, {}, list(urls), set()
    while queue and len(texts) < MAX_SHEETS:
        url = queue.pop(0)
        if url in seen or SKIP_SHEET.search(url):
            continue
        seen.add(url)
        try:
            data, _ = POLITE.body(url, limit=MAX_BYTES)
        except NetworkUnavailable:
            raise
        except Exception as error:
            errors[url] = str(error)[:200]
            continue
        texts[url] = data.decode("utf-8", "replace")
        queue.extend(u for u in imports(texts[url], url) if "fonts.googleapis.com" not in u)
    return texts, errors


# ---- fonts and shape -------------------------------------------------------------------------------------------------

def font_stack(value):
    """(first real family, its generic fallback) from a font-family value, or (None, None) for an icon or system stack."""
    families = [f.strip().strip("'\"") for f in value.split(",") if f.strip()]
    generic = next((f for f in families if f.lower() in GENERIC), "")
    first = next((f for f in families if f.lower() not in GENERIC and not NOT_FONTS.search(f)), None)
    return first, generic


def shorthand_family(value):
    """The font-family part of a font shorthand ("bold 16px/1.5 'Source Sans 3', sans-serif"), or None."""
    m = re.search(r"(?:^|\s)[\d.]+(?:px|rem|em|pt|%)(?:\s*/\s*[\w.%]+)?\s+(.+)$", value.strip())
    return m.group(1) if m else None


def google_families(href):
    """Family names in a Google Fonts link (css and css2 forms)."""
    query = urllib.parse.urlsplit(href).query
    names = []
    for key, value in urllib.parse.parse_qsl(query):
        if key == "family":
            for part in value.split("|"):
                names.append(part.split(":")[0].replace("+", " ").strip())
    return [n for n in names if n]


def to_px(value):
    value = value.strip().split()[0] if value.strip() else ""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(px|rem|em|%)?", value)
    if not m:
        return None
    number, unit = float(m.group(1)), m.group(2) or "px"
    if unit == "%":
        return "pill" if number >= 40 else None
    px = number * 16 if unit in ("rem", "em") else number
    return "pill" if px >= 60 else f"{round(px)}px"


# ---- the tally ------------------------------------------------------------------------------------------------------

def tally(css_texts, theme_color="", google_links=()):
    all_rules = []
    for text in css_texts:
        all_rules.extend(rules(text))
    variables = variables_of(all_rules)
    colors, filtered, fonts, radii, weights, buttons = {}, {}, {"body": {}, "heading": {}, "button": {}}, {"button": {}, "corner": {}}, {}, {"filled": 0, "outline": 0}
    face_families = set()

    def add_color(hex_color, where, weight):
        entry = colors.setdefault(hex_color, {"hex": hex_color, "score": 0, "count": 0, "where": set()})
        entry["score"] += weight
        entry["count"] += 1
        entry["where"].add(where)

    for name, value in variables.items():
        hex_color = to_hex(resolve(value, variables))
        if not hex_color:
            continue
        default = PLATFORM_DEFAULTS.get(name)
        if default and default == hex_color:
            filtered[hex_color] = f"{name} is the platform's untouched default"
            continue
        if name.startswith("--wp--preset--color--") or name.startswith("--bs-") or name.startswith("--e-global-color-"):
            add_color(hex_color, f"theme variable {name}", 3 if BRANDY_VARIABLE.search(name) else 1)
        elif BRANDY_VARIABLE.search(name):
            add_color(hex_color, f"variable {name}", 5)
    for selector, declarations in all_rules:
        if selector.startswith("@font-face") or "font-face" in selector:
            for prop, value in declarations:
                if prop.lower() == "font-family":
                    family, _ = font_stack(value)
                    if family:
                        face_families.add(family)
            continue
        if PRESET_CLASS.search(selector) and not re.search(r"[\s>]", selector.strip()):
            continue  # the block editor's generated preset classes: present on every such site, chosen by none
        roles = {role_of(part) for part in selector.split(",")}
        roles = (roles - {"other"}) or {"other"}
        has_background = False
        for prop, value in declarations:
            if prop.startswith("--"):
                continue
            value = resolve(value, variables)
            low = prop.lower()
            kind = property_kind(prop)
            if kind:
                found = [m.group(0) for m in HEX.finditer(value)] + [m.group(0) for m in FUNC.finditer(value)]
                found = found or [w for w in value.split() if w.lower() in ("white", "black")]
                for hex_color in filter(None, map(to_hex, found)):
                    for role in roles:
                        if kind == "background" and role == "button":
                            has_background = True
                        add_color(hex_color, f"{role} {kind}", WEIGHTS.get((role, kind), 1))
            family_value = value if low == "font-family" else shorthand_family(value) if low == "font" else None
            if family_value:
                family, generic = font_stack(family_value)
                for role in roles & {"body", "heading", "button"}:
                    if family:
                        slot = fonts[role].setdefault(family, {"family": family, "generic": generic, "count": 0})
                        slot["count"] += 1
                        slot["generic"] = slot["generic"] or generic
            if low in ("border-radius", "border-top-left-radius"):
                px = to_px(value)
                if px:
                    bucket = "button" if "button" in roles else "corner" if re.search(r"input|textarea|select|card|\.box|form", selector, re.I) else None
                    if bucket:
                        radii[bucket][px] = radii[bucket].get(px, 0) + 1
            if low == "font-weight" and "heading" in roles and re.fullmatch(r"\d{3}|bold|normal", value.strip()):
                w = {"bold": "700", "normal": "400"}.get(value.strip(), value.strip())
                weights[w] = weights.get(w, 0) + 1
        if "button" in roles:
            if has_background:
                buttons["filled"] += 1
            elif any(p.lower().startswith("border") for p, _ in declarations):
                buttons["outline"] += 1
    if theme_color and to_hex(theme_color):
        add_color(to_hex(theme_color), "theme color (browser bar)", 4)
    for hex_color in list(filtered):
        if hex_color in colors:
            del filtered[hex_color]  # used for real somewhere else, so it stays a candidate
    google = [family for href in google_links for family in google_families(href)]
    ordered = sorted(colors.values(), key=lambda c: (-c["score"], -c["count"], c["hex"]))
    color_list = [{"hex": c["hex"], "score": c["score"], "count": c["count"], "where": ", ".join(sorted(c["where"])[:5]),
                   "neutral": is_neutral(c["hex"]), "from": "stylesheet"} for c in ordered]
    font_lists = {role: sorted(found.values(), key=lambda f: -f["count"]) for role, found in fonts.items()}
    for role in font_lists:
        for f in font_lists[role]:
            f["webFont"] = f["family"] in google or f["family"] in face_families
    best = lambda counts: max(counts, key=counts.get) if counts else None
    notes = [f"Left out {hex_color}: {why}" for hex_color, why in sorted(filtered.items())]
    return {"colors": [c for c in color_list if not c["neutral"]][:16], "neutrals": [c for c in color_list if c["neutral"]][:10],
            "fonts": {**font_lists, "webFonts": sorted(set(google) | face_families), "googleFontsHref": next(iter(google_links), "")},
            "radius": {"button": best(radii["button"]), "corner": best(radii["corner"]), "counts": radii},
            "headingWeight": best(weights), "buttonStyle": "outline" if buttons["outline"] > buttons["filled"] else "filled" if buttons["filled"] else None,
            "notes": notes}


def from_crawl(crawl):
    sources = crawl.get("styleSources") or {}
    sheets, inline, links, theme = [], [], [], ""
    for source in sources.values():
        sheets += [s for s in source.get("stylesheets", []) if s not in sheets]
        inline += source.get("inlineStyles", [])
        links += [g for g in source.get("googleFonts", []) if g not in links]
        theme = theme or source.get("themeColor", "")
    texts, errors = fetch_sheets(sheets)
    result = tally([*texts.values(), *inline], theme, links)
    result["stylesheets"] = [{"url": u, "bytes": len(t)} for u, t in texts.items()] + [{"url": u, "error": e} for u, e in errors.items()]
    result["pages"] = [source.get("url") for source in sources.values()]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--crawl", help="site_crawl.py's output")
    parser.add_argument("--css", action="append", default=[], help="a stylesheet saved as a file (repeatable)")
    parser.add_argument("--google-fonts", action="append", default=[], help="a Google Fonts link the site loads (repeatable)")
    parser.add_argument("--out", required=True)
    options = parser.parse_args(argv)
    if not options.crawl and not options.css:
        parser.error("give --crawl or at least one --css")
    try:
        if options.crawl:
            with open(options.crawl, encoding="utf-8") as handle:
                result = from_crawl(json.load(handle))
        else:
            texts = []
            for path in options.css:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    texts.append(handle.read())
            result = tally(texts, "", options.google_fonts)
            result["stylesheets"] = [{"file": p} for p in options.css]
    except NetworkUnavailable as error:
        print(f"site unreachable from here: {error}. Save the stylesheets with a web fetch tool and pass them with --css.", file=sys.stderr)
        return 3
    with open(options.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, ensure_ascii=False)
    top = ", ".join(f"{c['hex']} ({c['where']})" for c in result["colors"][:5]) or "none"
    body = (result["fonts"]["body"] or [{"family": "none found"}])[0]["family"]
    heading = (result["fonts"]["heading"] or [{"family": "none found"}])[0]["family"]
    print(f"{len(result['colors'])} brand colors, {len(result['neutrals'])} neutrals, fonts {body} / {heading}, "
          f"button radius {result['radius']['button']}, {len(result['notes'])} platform defaults left out -> {options.out}")
    print("top colors:", top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
