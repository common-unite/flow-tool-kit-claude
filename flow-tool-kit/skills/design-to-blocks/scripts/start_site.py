#!/usr/bin/env python3
"""Start a site folder from what the project already knows: the org's answers, the saved brand kit and org-catalog's platforms.

    python3 -I start_site.py --slug riverside-fund --title "Riverside Community Fund" \
        --page home="Home" --page funding="Funding" --page fund="Fund page:/funding/:recordId:Funding_Opportunity__c" \
        [--brand-kit _brand/<slug>/brand-kit.json] [--config flow-tool-kit.json] [--org <18-character org Id>] \
        [--site-type lwr|aura] [--out _site] [--force]

Writes _site/<slug>/site.json (references/page-json.md) and prints what it took from where and what is still open. It never
writes pages/: each page starts from the closest Page example card in the design system (SKILL.md, Draw).

- flow-tool-kit.json (ftk-start writes it, format in _shared/standards/project-config.md): the org's edition, its audiences
  (guest, portal, internal) and its platforms (org-catalog finds them). The edition decides which objects a record page or
  repeater can use; the audiences decide what the HTML Editor may show; the platforms suggest the pages.
- brand-kit.json (brand-kit writes it, format in _shared/standards/brand-kit.md): the palette, fonts, button corners, logo,
  photos, tone and sample headings. Images are listed in site.json assets with the canvas copies brand-kit wrote
  (assets/manifest.json, its "canvas" files), so the review canvas uploads them. No brand kit: the palette is the design
  system's default and the brand board says what is unconfirmed.

--page urlName="Title[:route[:recordObject]]", repeated, in navigation order. The route defaults to /urlName (/ for home).
Python 3 standard library only.
"""
import argparse
import colorsys
import json
import os
import pathlib
import sys

CONFIG_NAME = "flow-tool-kit.json"
DEFAULT_PALETTE = {"brand": "#2e844a", "accent": "#F4BE45", "deep": "#032D60", "tint": "#EEF1F4"}
PLATFORM_PAGES = {
    "outbound_funds": "Outbound Funds is installed: a funding listing (a repeater of open Funding Programs) and a funding program record page "
                      "fit; applications go in a Form Slot",
    "nonprofit_cloud": "Nonprofit Cloud is installed: a program listing and a program record page fit (Program and its enrollments); "
                       "applications go in a Form Slot",
    "npsp": "NPSP is installed: campaign or volunteer pages fit, with the records in a repeater",
    "person_accounts": "Person accounts are on: a portal page about the signed-in person reads the Account, not a separate Contact",
}


def find(start, name, given=None):
    if given:
        path = pathlib.Path(given)
        return path if path.exists() else None
    for folder in [start, *start.parents]:
        if (folder / name).exists():
            return folder / name
    return None


def luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_on_white(hex_color):
    return 1.05 / (luminance(hex_color) + 0.05)


def deepen(hex_color, lightness=0.18):
    """The brand's hue at a deep lightness, for the serious bands white text sits on"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, _, sat = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, min(sat, 0.75))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def org_entry(config, org_id=None):
    orgs = config.get("orgs") or {}
    if org_id:
        return orgs.get(org_id) or {}
    return next(iter(orgs.values())) if len(orgs) == 1 else {}


def brand_from_kit(kit, kit_path, site_dir):
    """site.json palette, brand and assets from a confirmed brand-kit.json; image files are written relative to the site folder"""
    colors, fonts, style, assets, voice = (kit.get(k) or {} for k in ("colors", "fonts", "style", "assets", "voice"))
    primary = colors.get("primary") or DEFAULT_PALETTE["brand"]
    heading = colors.get("heading")
    palette = {"brand": primary}
    if colors.get("accent"):
        palette["accent"] = colors["accent"]
    palette["deep"] = heading if heading and contrast_on_white(heading) >= 7 else deepen(primary)
    palette["tint"] = colors.get("background") or DEFAULT_PALETTE["tint"]
    roles = {"brand": "buttons, links, the brand band", "accent": "one bright highlight", "deep": "serious bands with white text",
             "tint": "quiet bands"}
    brand = {
        "logo": assets.get("logo"),
        "theme": {k: v for k, v in {"brand": primary, "accent": colors.get("accent"), "font": fonts.get("bodyStack"),
                                    "headingFont": fonts.get("headingStack")}.items() if v},
        "colors": [{"name": name.title(), "hex": hexv, "role": roles[name]} for name, hexv in palette.items()],
        "fonts": {k: v for k, v in {"heading": fonts.get("heading"), "body": fonts.get("body"), "heading_css": fonts.get("headingStack"),
                                    "body_css": fonts.get("bodyStack"), "href": fonts.get("href")}.items() if v},
        "buttonRadius": style.get("buttonRadius") or style.get("cornerRadius") or "4px",
        "tone": ". ".join(filter(None, [", ".join(voice.get("adjectives") or []).capitalize()] + list(voice.get("do") or []))) or None,
        "copy": list(voice.get("sampleHeadings") or [])[:3],
        "images": [{"asset": name, "alt": "", "caption": "Picked in the brand kit"} for name in assets.get("photos") or []],
    }
    brand = {k: v for k, v in brand.items() if v}
    site_assets = {}
    manifest_path = kit_path.parent / "assets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for entry in manifest.values():
        name, rel = entry.get("asset"), entry.get("canvas") or entry.get("file")
        if name and rel:
            file = (manifest_path.parent / rel).resolve()
            if file.exists():
                site_assets[name] = {"file": os.path.relpath(file, site_dir)}
    return palette, brand, site_assets


def parse_page(spec):
    url_name, _, rest = spec.partition("=")
    parts = rest.split(":")
    title = parts[0] or url_name.replace("-", " ").title()
    route = None
    record = None
    if len(parts) > 1:
        # a route may hold :params, so the record object is the last part only when it looks like an object name
        tail = parts[-1]
        if len(parts) > 2 and (tail.endswith("__c") or tail[:1].isupper()):
            record = tail
            parts = parts[:-1]
        route = ":".join(parts[1:]) or None
    return {"urlName": url_name, "title": title, "route": route or ("/" if url_name == "home" else f"/{url_name}"), "recordObject": record}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True, help="the organization or site name")
    ap.add_argument("--page", action="append", required=True, help='urlName="Title[:route[:recordObject]]", in navigation order')
    ap.add_argument("--brand-kit", help="brand-kit.json (default: the only _brand/*/brand-kit.json in the project, if there is one)")
    ap.add_argument("--config", help=f"the project config (default: {CONFIG_NAME} here or in a folder above)")
    ap.add_argument("--org", help="the org's 18-character Id in the config (default: the only org there)")
    ap.add_argument("--site-type", choices=("lwr", "aura"), default="lwr")
    ap.add_argument("--out", default="_site")
    ap.add_argument("--force", action="store_true", help="replace an existing site.json")
    args = ap.parse_args(argv)

    here = pathlib.Path.cwd()
    site_dir = (here / args.out / args.slug).resolve()
    target = site_dir / "site.json"
    if target.exists() and not args.force:
        print(f"{target} exists; edit it, or pass --force to start over", file=sys.stderr)
        return 1
    notes = []
    config_path = find(here, CONFIG_NAME, args.config)
    config = json.loads(config_path.read_text()) if config_path else {}
    org = org_entry(config, args.org)
    if not config_path:
        notes.append("No flow-tool-kit.json: run ftk-start first, or answer the edition and audience questions and add them to site.json")
    elif not org:
        notes.append("flow-tool-kit.json has no single org to use; pass --org")

    kit_path = pathlib.Path(args.brand_kit) if args.brand_kit else None
    if not kit_path:
        found = sorted(here.glob("_brand/*/brand-kit.json"))
        kit_path = found[0] if len(found) == 1 else None
        if len(found) > 1:
            notes.append(f"{len(found)} brand kits in _brand/; pass --brand-kit for this site's brand")
    if kit_path and kit_path.exists():
        palette, brand, assets = brand_from_kit(json.loads(kit_path.read_text()), kit_path.resolve(), site_dir)
        notes.append(f"Brand from {kit_path}: {', '.join(f'{k} {v}' for k, v in palette.items())}; {len(assets)} images to upload to the canvas")
    else:
        palette, brand, assets = dict(DEFAULT_PALETTE), {"tone": "[CONFIRM: tone paragraph]", "copy": ["[CONFIRM: general copy]"]}, {}
        notes.append("No brand kit: the design system's default palette; the brand board marks the tone and copy to confirm")

    pages = [parse_page(p) for p in args.page]
    audiences = list(org.get("audiences") or [])
    for page in pages:
        if audiences:
            page["audience"] = audiences
    site = {"slug": args.slug, "title": args.title, "canvasTitle": f"{args.title} site review", "siteType": args.site_type,
            "edition": org.get("edition") or "paid", "audiences": audiences, "pages": pages, "palette": palette, "brand": brand,
            "page": {"siteName": args.title, "navItems": [p["title"] for p in pages if not p.get("recordObject")]}}
    if brand.get("logo"):
        site["page"]["logo"] = brand["logo"]
    if assets:
        site["assets"] = assets
    if org.get("edition_source") == "assumed":
        notes.append("The edition was assumed paid; ask once which edition the org has before designing record pages")
    if not audiences:
        notes.append("No audiences recorded: ask who sees each page (guest, portal, internal) and set audience on each page")
    for key, on in (org.get("platforms") or {}).items():
        if on and key in PLATFORM_PAGES:
            notes.append(PLATFORM_PAGES[key])
    if site["edition"] == "free":
        notes.append("Free edition: blocks on a record page read Account, Contact, Case, Lead and Form Template records only, and a repeater's "
                     "cards need an object free forms use (Account, Contact, Lead, Case, Campaign, Form Submission)")
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "pages").mkdir(exist_ok=True)
    target.write_text(json.dumps(site, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {target}")
    for line in notes:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
