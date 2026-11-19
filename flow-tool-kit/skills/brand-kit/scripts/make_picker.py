#!/usr/bin/env python3
"""Gather the brand candidates and write the review: candidates.json, the picker page and a plain numbered list.

    python3 make_picker.py _brand/<slug> [--crawl site-crawl.json] [--styles site-styles.json] [--rendered render-scan.json ...]
                           [--previous brand-kit.json] [--no-thumbs] [--width 240]

Reads from the brand folder (default file names shown) and writes there:

- candidates.json  every image (grouped, with its size fit), every color with where it is used, the fonts, radius, button
                   labels and headings, and `defaults`: the best guess for each pick. With --previous, the saved kit's
                   values are the defaults, so an update starts from what was confirmed last time.
- brand-picker.html  one self-contained page: thumbnails are embedded, so it works opened as a file in any browser and
                   as a published artifact (which blocks images from other sites). The person picks, then copies or
                   downloads their picks as picks.json. Nothing is served from this computer.
- brand-review.md  the same choices as a numbered list, for chat and voice: "logo 3, banner 12, brand color 2".

Thumbnails need Pillow (pip install pillow). Without it, or with --no-thumbs, the page shows each image's address and
size instead; the numbered list works either way.
"""
import argparse
import base64
import concurrent.futures
import io
import json
import pathlib
import re
import sys

from site_styles import is_neutral
from webfetch import POLITE

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "brand-picker.html"
PEOPLE_NOTE = "shows people: needs their permission"


def load(path):
    p = pathlib.Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def first(items, test, default=None):
    return next((i for i, item in enumerate(items) if test(item)), default)


def merge_colors(styles, rendered):
    """One color list: stylesheet colors first by score, then colors only the rendered page showed, logo colors marked."""
    seen, out = {}, []
    for source in [styles or {}] + list(rendered or []):
        for color in (source.get("colors") or []) + (source.get("neutrals") or []):
            hex_color = (color.get("hex") or "").lower()
            if not re.fullmatch(r"#[0-9a-f]{6}", hex_color):
                continue
            if hex_color in seen:
                entry = seen[hex_color]
                entry["where"] = ", ".join(dict.fromkeys(filter(None, entry["where"].split(", ") + (color.get("where") or "").split(", "))))[:120]
                continue
            entry = {"hex": hex_color, "where": color.get("where") or "", "neutral": bool(color["neutral"]) if "neutral" in color else is_neutral(hex_color),
                     "from": color.get("from") or ("stylesheet" if source is styles else "rendered page")}
            seen[hex_color] = entry
            out.append(entry)
        for color in source.get("logoColors") or []:
            hex_color = (color.get("hex") or "").lower()
            if re.fullmatch(r"#[0-9a-f]{6}", hex_color) and hex_color not in seen:
                seen[hex_color] = {"hex": hex_color, "where": "inside the logo", "neutral": False, "from": "logo"}
                out.append(seen[hex_color])
    out.sort(key=lambda c: c["neutral"])
    return out


def merge_fonts(styles, rendered):
    fonts = {"body": [], "heading": [], "googleFontsHref": ""}
    s = (styles or {}).get("fonts") or {}
    for role in ("body", "heading"):
        for f in s.get(role) or []:
            if f["family"] not in [x["family"] for x in fonts[role]]:
                fonts[role].append({"family": f["family"], "generic": f.get("generic", ""), "from": "stylesheet"})
    fonts["googleFontsHref"] = s.get("googleFontsHref") or ""
    for scan in rendered or []:
        for role, key in (("body", "body"), ("heading", "heading")):
            stack = ((scan.get("fonts") or {}).get(key)) or ""
            family = next((f.strip().strip("'\"") for f in stack.split(",") if f.strip() and f.strip().lower() not in ("serif", "sans-serif")), "")
            if family and family not in [x["family"] for x in fonts[role]]:
                fonts[role].append({"family": family, "generic": "serif" if stack.rstrip().endswith(" serif") else "", "from": "rendered page"})
    return fonts


def guess_defaults(candidates):
    images, colors = candidates["images"], candidates["colors"]
    logos = [i for i, m in enumerate(images) if m.get("group") == "logo"]
    is_light = lambda m: re.search(r"(?<![a-z])(white|reversed?|knockout|light|negative|inverse)(?![a-z])", (m.get("label") or "") + " " + m["url"], re.I)
    d = {}
    if logos:
        d["logo"] = next((i for i in logos if images[i].get("homeLink") and not is_light(images[i])), next((i for i in logos if not is_light(images[i])), logos[0]))
        alt = next((i for i in logos if i != d["logo"] and is_light(images[i])), None)
        if alt is not None:
            d["logoAlternate"] = alt
    favicons = sorted((i for i, m in enumerate(images) if m.get("group") == "favicon"), key=lambda i: -(images[i].get("width") or 0))
    if favicons:
        d["favicon"] = favicons[0]
    banner = first(images, lambda m: m.get("program") and m.get("fit") == "banner" and not m.get("people"))
    banner = banner if banner is not None else first(images, lambda m: m.get("fit") == "banner" and not m.get("people"))
    if banner is not None:
        d["banner"] = banner
    tile = first(images, lambda m: m.get("program") and m.get("fit") in ("tile", "wide block") and not m.get("people"))
    if tile is not None:
        d["tile"] = tile
    brand = [c for c in colors if not c["neutral"]]
    buttons = [c for c in brand if "button background" in c["where"]]
    if brand:
        d["primary"] = (buttons or brand)[0]["hex"]
    heading = next((c for c in colors if "heading text" in c["where"] and c["hex"] != d.get("primary")), None)
    if heading:
        d["heading"] = heading["hex"]
    accent = next((c for c in brand if c["hex"] not in (d.get("primary"), d.get("heading"))), None)
    if accent:
        d["accent"] = accent["hex"]
    fonts = candidates["fonts"]
    if fonts["body"]:
        d["bodyFont"] = fonts["body"][0]["family"]
    if fonts["heading"]:
        d["headingFont"] = fonts["heading"][0]["family"]
    for key, value in (("cornerRadius", candidates.get("radius", {}).get("corner")), ("buttonRadius", candidates.get("radius", {}).get("button")),
                       ("headingWeight", candidates.get("headingWeight")), ("buttonStyle", candidates.get("buttonStyle"))):
        if value:
            d[key] = value
    d["photos"] = []
    return d


def defaults_from_kit(kit, candidates):
    """An update starts from the saved kit: its colors, fonts and style; images are picked again from the fresh scan."""
    d = guess_defaults(candidates)
    colors, fonts, style = kit.get("colors") or {}, kit.get("fonts") or {}, kit.get("style") or {}
    for key in ("primary", "heading", "accent", "background"):
        value = colors.get("primaryOriginal") if key == "primary" and colors.get("primaryOriginal") else colors.get(key)
        if value:
            d[key] = value
    for key, role in (("bodyFont", "body"), ("headingFont", "heading")):
        if fonts.get(role):
            d[key] = fonts[role]
    for key in ("cornerRadius", "buttonRadius", "headingWeight", "buttonStyle"):
        if style.get(key):
            d[key] = style[key]
    if kit.get("voice"):
        d["voice"] = kit["voice"]
    return d


def build_candidates(crawl, styles, rendered, previous, slug):
    crawl = crawl or {}
    images = [{k: image.get(k) for k in ("url", "label", "alt", "group", "fit", "size", "width", "height", "pages", "page", "program", "people", "homeLink")}
              for image in crawl.get("images") or []]
    pages = crawl.get("pages") or {}
    buttons, headings = {}, []
    for page in pages.values():
        for label in page.get("buttons") or []:
            buttons[label] = buttons.get(label, 0) + 1
    home = pages.get("/") or {}
    program_path = re.sub(r"^https?://[^/]+", "", crawl.get("programPage") or "")
    headings = ((pages.get(program_path) or {}).get("headings") or []) + (home.get("headings") or [])
    candidates = {"slug": slug, "brandName": crawl.get("organization") or (previous or {}).get("brandName") or "",
                  "source": crawl.get("start") or (previous or {}).get("source") or "", "programPage": crawl.get("programPage") or "",
                  "scannedOn": crawl.get("crawledOn") or "", "pagesScanned": len(pages), "images": images,
                  "colors": merge_colors(styles, rendered), "fonts": merge_fonts(styles, rendered),
                  "radius": (styles or {}).get("radius") or {}, "headingWeight": (styles or {}).get("headingWeight"),
                  "buttonStyle": (styles or {}).get("buttonStyle"),
                  "buttons": [b for b, _ in sorted(buttons.items(), key=lambda item: -item[1])][:12],
                  "headings": list(dict.fromkeys(headings))[:12], "notes": list((styles or {}).get("notes") or [])}
    if crawl.get("errors"):
        candidates["notes"].append(f"{len(crawl['errors'])} pages could not be read: " + ", ".join(list(crawl["errors"])[:5]))
    candidates["defaults"] = defaults_from_kit(previous, candidates) if previous else guess_defaults(candidates)
    return candidates


# ---- thumbnails -------------------------------------------------------------------------------------------------------

def thumbnail(url, width):
    """A small JPEG (PNG for images with transparency) as a data URI, or None. SVGs are embedded as they are when small."""
    try:
        data, content_type = POLITE.body(url, limit=8_000_000)
    except Exception:
        return None
    if url.lower().endswith(".svg") or "svg" in (content_type or ""):
        return "data:image/svg+xml;base64," + base64.b64encode(data).decode() if len(data) < 150_000 else None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(io.BytesIO(data))
        image.thumbnail((width, width * 2))
        out = io.BytesIO()
        if image.mode in ("RGBA", "LA", "P"):
            image.convert("RGBA").save(out, "PNG", optimize=True)
            mime = "image/png"
        else:
            image.convert("RGB").save(out, "JPEG", quality=60)
            mime = "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(out.getvalue()).decode()
    except Exception:
        return None


def pillow_available():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


# ---- outputs -------------------------------------------------------------------------------------------------------

def picker_page(candidates, thumbs):
    template = TEMPLATE.read_text(encoding="utf-8")
    page_data = {**candidates, "images": [{**image, "thumb": thumbs.get(image["url"])} for image in candidates["images"]]}
    payload = json.dumps(page_data, ensure_ascii=False).replace("</", "<\\/")
    title = f"{candidates.get('brandName') or 'Brand'} Brand Picker"
    return template.replace("<title>Brand Picker</title>", f"<title>{title}</title>").replace("__CONFIG__", payload)


def review_list(candidates):
    images, colors, fonts, d = candidates["images"], candidates["colors"], candidates["fonts"], candidates["defaults"]
    lines = [f"# Brand review: {candidates.get('brandName') or 'the organization'}", "",
             f"Scanned {candidates.get('source') or 'the website'} ({candidates.get('pagesScanned', 0)} pages) on {candidates.get('scannedOn') or 'today'}. "
             "Answer with numbers, for example: logo 3, alternate logo 5, banner 12, tile 14, photos 20 21, brand color 2, heading color 4, "
             "body font 1, heading font 2, corner radius 8px. The current guesses are marked GUESS.", ""]
    lines += ["## Images", ""]
    groups = {}
    for i, image in enumerate(images):
        groups.setdefault("program page" if image.get("program") else image.get("group") or "other", []).append(i)
    order = sorted(groups, key=lambda g: (g != "logo", g != "program page", g != "banners", g))
    for group in order:
        lines += [f"### {group} ({len(groups[group])})", ""]
        for i in groups[group]:
            image = images[i]
            marks = "".join(f" GUESS {k}" for k in ("logo", "logoAlternate", "favicon", "banner", "tile") if d.get(k) == i)
            marks += " GUESS photo" if i in (d.get("photos") or []) else ""
            lines.append(f"- {i}. {image.get('label') or image['url']} ({image.get('fit') or ''}{', ' + image['size'] if image.get('size') else ''})"
                         f"{', ' + PEOPLE_NOTE if image.get('people') else ''}{marks}: {image['url']}")
        lines.append("")
    lines += ["## Colors", ""]
    for n, color in enumerate(colors, 1):
        marks = "".join(f" GUESS {k}" for k in ("primary", "heading", "accent", "background") if d.get(k) == color["hex"])
        lines.append(f"- color {n}. {color['hex']} ({'neutral, ' if color['neutral'] else ''}{color['where'] or color['from']}){marks}")
    lines += ["", "## Fonts", ""]
    for role in ("body", "heading"):
        for n, font in enumerate(fonts[role], 1):
            lines.append(f"- {role} font {n}. {font['family']} ({font['from']}){' GUESS' if d.get(role + 'Font') == font['family'] else ''}")
    lines += ["", "## Style", "",
              f"- Corner radius: {d.get('cornerRadius') or 'not found (default 8px)'}; button corners: {d.get('buttonRadius') or 'same'}; "
              f"heading weight: {d.get('headingWeight') or 'not found'}; buttons: {d.get('buttonStyle') or 'not found'}.", ""]
    if candidates.get("buttons"):
        lines += ["## The site's own words", "", "Buttons: " + ", ".join(candidates["buttons"]) + ".", ""]
    if candidates.get("notes"):
        lines += ["## Left out", ""] + [f"- {note}" for note in candidates["notes"]] + [""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", help="the brand folder, _brand/<slug>")
    parser.add_argument("--crawl", default="site-crawl.json")
    parser.add_argument("--styles", default="site-styles.json")
    parser.add_argument("--rendered", action="append", default=[], help="render_scan.cjs or browser scan output (repeatable)")
    parser.add_argument("--previous", help="the saved brand-kit.json, when this is an update")
    parser.add_argument("--no-thumbs", action="store_true")
    parser.add_argument("--width", type=int, default=240)
    a = parser.parse_args(argv)
    folder = pathlib.Path(a.folder)
    folder.mkdir(parents=True, exist_ok=True)
    resolve = lambda name: str(folder / name) if (folder / name).exists() else name
    crawl, styles = load(resolve(a.crawl)), load(resolve(a.styles))
    rendered = [load(resolve(r)) for r in a.rendered]
    previous = load(a.previous) if a.previous else None
    if not crawl and not styles:
        print(f"nothing to review: no {a.crawl} or {a.styles} in {folder}", file=sys.stderr)
        return 1
    candidates = build_candidates(crawl, styles, [r for r in rendered if r], previous, folder.name)
    (folder / "candidates.json").write_text(json.dumps(candidates, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    thumbs = {}
    if not a.no_thumbs and candidates["images"]:
        if not pillow_available():
            print("Pillow is not installed (pip install pillow): the picker shows SVGs only; other images are listed by address.")
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            urls = [image["url"] for image in candidates["images"]]
            thumbs = {u: t for u, t in zip(urls, pool.map(lambda u: thumbnail(u, a.width), urls)) if t}
    page = picker_page(candidates, thumbs)
    (folder / "brand-picker.html").write_text(page, encoding="utf-8")
    (folder / "brand-review.md").write_text(review_list(candidates), encoding="utf-8")
    missing = len(candidates["images"]) - len(thumbs)
    print(f"{folder / 'candidates.json'}: {len(candidates['images'])} images, {len(candidates['colors'])} colors, "
          f"{len(candidates['fonts']['body'])} body and {len(candidates['fonts']['heading'])} heading fonts")
    print(f"{folder / 'brand-picker.html'}: {len(page) // 1024} KB, {len(thumbs)} thumbnails, {missing} images without one")
    print(f"{folder / 'brand-review.md'}: the numbered list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
