#!/usr/bin/env python3
"""The confirmed brand kit, brand-kit.json: build it from the person's picks, check it, and hand its values to other skills.

    python3 brandkit.py contrast <hex> [<hex> ...]
    python3 brandkit.py confirm <candidates.json> <picks.json> --out <brand-kit.json> [--previous <saved brand-kit.json>]
    python3 brandkit.py validate <brand-kit.json>
    python3 brandkit.py tokens <brand-kit.json>
    python3 brandkit.py global-styles <brand-kit.json> [--export <exported.json>] --out <global-styles-import.json>
    python3 brandkit.py plan-style <brand-kit.json> [--plan-dir _forms/<slug>]

contrast       each color's contrast with white, and the darkened shade that reaches 4.5:1 when it falls short.
confirm        writes brand-kit.json in the plugin's shared format (_shared/standards/brand-kit.md): brand color and
               heading color darkened to 4.5:1 on white when needed (the original kept as the accent), fonts with their
               CSS stacks, the planned Asset File name of each picked image, the voice. --previous raises the version.
validate       the format check every reader relies on. Exit 1 with the problems listed.
tokens         the Form Style values the kit sets, by Global Styles token name (--ftk-color-primary and so on).
global-styles  the paste-in file for Form Builder's Global Styles, Import, when the org refuses the API write: the org's
               exported values first (Import replaces every saved org style), the kit's values only where the org has none.
plan-style     the style, assets, images and brand_board keys form-design's plan.json takes.

Picks may name an image by its index in candidates.json or by its URL. Standard library only.
"""
import argparse
import colorsys
import datetime
import json
import os
import pathlib
import re
import sys

MIN_CONTRAST = 4.5
TEXT_ON_BACKGROUND = "#1b1f24"  # the darkest body text a form shows on a tinted background
HEXCOLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
ASSET_NAME = re.compile(r"^[A-Za-z](?:[A-Za-z0-9]|_(?!_))*$")
IMAGE_ROLES = ("logo", "logoAlternate", "favicon", "banner", "tile")
SERIF_HINT = re.compile(r"serif|garamond|georgia|merriweather|playfair|lora|baskerville|caslon|times|bodoni|crimson|libre|slab|roboto slab|pt serif|noto serif|source serif|cormorant|spectral", re.I)


# ---- color and contrast ---------------------------------------------------------------------------------------------

def normalize_hex(value):
    value = (value or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", value):
        value = "#" + "".join(c * 2 for c in value.lstrip("#"))
    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        value = "#" + value
    if not HEXCOLOR.match(value):
        raise ValueError(f"not a color: {value!r} (use #rrggbb)")
    return value.lower()


def luminance(hex_color):
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b="#ffffff"):
    x, y = luminance(normalize_hex(a)), luminance(normalize_hex(b))
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def darken_to(hex_color, against="#ffffff", minimum=MIN_CONTRAST):
    """The same hue, darkened step by step until it reaches the contrast; the color itself when it already does."""
    hex_color = normalize_hex(hex_color)
    if contrast(hex_color, against) >= minimum:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    while l > 0:
        l = max(0.0, l - 0.01)
        candidate = "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(h, l, s))
        if contrast(candidate, against) >= minimum:
            return candidate
    return "#000000"


# ---- reading picks ----------------------------------------------------------------------------------------------------

def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_image(candidates, ref):
    """A pick (an index into candidates.json images, or a URL) as its candidate entry; None when not picked."""
    if ref is None or ref == "":
        return None
    images = candidates.get("images") or []
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        index = int(ref)
        if not 0 <= index < len(images):
            raise ValueError(f"image {index} is not in the candidates (0 to {len(images) - 1})")
        return images[index]
    for image in images:
        if image.get("url") == ref:
            return image
    return {"url": ref, "label": ref.rsplit("/", 1)[-1]}


def short_name(brand_name):
    """The asset name prefix: the first word of the brand when it is distinctive, else its initials ("Riverside")."""
    words = re.findall(r"[A-Za-z0-9]+", brand_name or "")
    if not words:
        return "Brand"
    first = words[0]
    if len(first) >= 4 and first.lower() not in ("the", "city", "north", "south", "east", "west", "saint", "community"):
        return first[0].upper() + first[1:]
    return "".join(w[0].upper() for w in words[:4])


def asset_name(prefix, *parts):
    """A ContentAsset name: letters, digits and single underscores, starting with a letter, at most 80 characters."""
    words = re.findall(r"[A-Za-z0-9]+", " ".join([prefix, *[p for p in parts if p]]))
    name = "_".join(w[0].upper() + w[1:] for w in words)
    if not name or not name[0].isalpha():
        name = "Brand_" + name
    return name[:80].rstrip("_")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "brand"


def font_stack(family, generic=""):
    if not family:
        return ""
    serif = generic == "serif" or (not generic and SERIF_HINT.search(family))
    fallback = "Georgia, serif" if serif else "Arial, sans-serif"
    return f"'{family}', {fallback}"


# ---- confirm ----------------------------------------------------------------------------------------------------------

def confirm(candidates, picks, previous=None, today=None):
    """brand-kit.json from the candidates and the person's picks, plus a list of warnings to tell them."""
    warnings = []
    defaults = candidates.get("defaults") or {}
    pick = lambda key: picks[key] if key in picks else defaults.get(key)
    brand_name = picks.get("brandName") or candidates.get("brandName") or (previous or {}).get("brandName")
    if not brand_name:
        raise ValueError("no brand name: put brandName in the picks")
    slug = (previous or {}).get("slug") or candidates.get("slug") or slugify(brand_name)
    prefix = picks.get("assetPrefix") or short_name(brand_name)

    colors = {}
    primary = pick("primary")
    if not primary:
        raise ValueError("no brand color: pick primary")
    primary = normalize_hex(primary)
    colors["primary"] = darken_to(primary)
    if colors["primary"] != primary:
        colors["primaryOriginal"] = primary
        warnings.append(f"Brand color {primary} has {contrast(primary):.2f}:1 on white, below 4.5:1, so buttons and links use "
                        f"{colors['primary']} ({contrast(colors['primary']):.2f}:1); {primary} stays as the accent.")
    if pick("heading"):
        heading = normalize_hex(pick("heading"))
        colors["heading"] = darken_to(heading)
        if colors["heading"] != heading:
            warnings.append(f"Heading color {heading} was darkened to {colors['heading']} to reach 4.5:1 on white.")
    # The original of a darkened brand color is the accent unless the person picked one on purpose
    accent = picks.get("accent") if "accent" in picks else (colors.get("primaryOriginal") or defaults.get("accent"))
    if accent:
        colors["accent"] = normalize_hex(accent)
    if pick("background"):
        background = normalize_hex(pick("background"))
        if contrast(TEXT_ON_BACKGROUND, background) < MIN_CONTRAST:
            warnings.append(f"Background {background} is too dark for body text ({contrast(TEXT_ON_BACKGROUND, background):.2f}:1); "
                            "it was left out. Pick a light tint.")
        else:
            colors["background"] = background

    fonts = {}
    generics = {f.get("family"): f.get("generic", "") for role in ("body", "heading") for f in (candidates.get("fonts") or {}).get(role, [])}
    for role, key in (("body", "bodyFont"), ("heading", "headingFont")):
        family = pick(key)
        if family:
            fonts[role] = family.strip().strip("'\"")
            fonts[role + "Stack"] = font_stack(fonts[role], generics.get(fonts[role], ""))
    href = pick("fontsHref") or (candidates.get("fonts") or {}).get("googleFontsHref")
    if href and fonts:
        fonts["href"] = href

    style = {}
    for key in ("cornerRadius", "buttonRadius", "headingWeight", "buttonStyle"):
        value = pick(key)
        if value not in (None, ""):
            style[key] = str(value)
    if style.get("buttonRadius") == "pill":
        style["buttonRadius"] = "999px"

    assets, files = {}, {}
    labels = {"logo": "Logo", "logoAlternate": "Logo Alternate", "favicon": "Favicon", "banner": "Banner", "tile": "Tile"}
    for role in IMAGE_ROLES:
        image = resolve_image(candidates, pick(role))
        if image:
            assets[role] = asset_name(prefix, labels[role])
            files[role] = image["url"]
    photos = [resolve_image(candidates, ref) for ref in (pick("photos") or [])]
    if photos:
        assets["photos"] = []
        for n, image in enumerate(p for p in photos if p):
            name = asset_name(prefix, "Photo", re.sub(r"\.[a-z]+$", "", image.get("label") or "")[:40] or str(n + 1))
            while name in assets["photos"]:
                name = f"{name}_{n + 1}"
            assets["photos"].append(name)
            files["photos/" + name] = image["url"]
    if "logo" in assets:
        assets["logoAlt"] = picks.get("logoAltText") or brand_name
    if "banner" in assets and picks.get("bannerAltText"):
        assets["bannerAlt"] = picks["bannerAltText"]
    if any(image and image.get("people") for image in [resolve_image(candidates, pick(r)) for r in IMAGE_ROLES] + photos):
        warnings.append("A picked photo shows identifiable people: confirm the organization has their permission before it goes public.")

    voice = {}
    given = pick("voice") or {}
    for key in ("adjectives", "do", "avoid", "sampleHeadings", "sampleButtons"):
        values = [str(v).strip() for v in (given.get(key) or []) if str(v).strip()]
        if values:
            voice[key] = values
    if "sampleButtons" not in voice and candidates.get("buttons"):
        voice["sampleButtons"] = candidates["buttons"][:6]
    if "sampleHeadings" not in voice and candidates.get("headings"):
        voice["sampleHeadings"] = candidates["headings"][:6]

    kit = {
        "brandName": brand_name,
        "version": int((previous or {}).get("version") or 0) + 1,
        "confirmedOn": today or datetime.date.today().isoformat(),
        "source": candidates.get("source") or picks.get("source") or "",
        "slug": slug,
        "orgDefault": bool(picks.get("orgDefault", (previous or {}).get("orgDefault", True))),
        "colors": colors,
        "fonts": fonts,
        "style": style,
        "assets": assets,
        "voice": voice,
    }
    if candidates.get("programPage"):
        kit["programPage"] = candidates["programPage"]
    if picks.get("bannerFocal"):
        kit["bannerFocal"] = picks["bannerFocal"]
    return kit, files, warnings


# ---- validate ---------------------------------------------------------------------------------------------------------

def validate(kit):
    problems = []
    need = lambda cond, msg: None if cond else problems.append(msg)
    need(isinstance(kit.get("brandName"), str) and kit["brandName"].strip(), "brandName: the organization's name is required")
    need(isinstance(kit.get("version"), int) and kit["version"] >= 1, "version: a whole number, 1 or more")
    need(isinstance(kit.get("confirmedOn"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", kit.get("confirmedOn") or ""), "confirmedOn: YYYY-MM-DD")
    need(isinstance(kit.get("source", ""), str), "source: the website address, as text")
    colors = kit.get("colors") or {}
    need(isinstance(colors, dict), "colors: an object")
    for key, value in colors.items():
        try:
            normalize_hex(value)
        except (ValueError, TypeError, AttributeError):
            problems.append(f"colors.{key}: {value!r} is not #rrggbb")
    if "primary" not in colors:
        problems.append("colors.primary: the brand color is required")
    for key in ("primary", "heading"):
        if key in colors and HEXCOLOR.match(str(colors[key])) and contrast(colors[key]) < MIN_CONTRAST:
            problems.append(f"colors.{key}: {colors[key]} has {contrast(colors[key]):.2f}:1 on white; it needs 4.5:1 (brandkit.py contrast)")
    for key, value in (kit.get("fonts") or {}).items():
        need(isinstance(value, str) and value.strip(), f"fonts.{key}: text")
    assets = kit.get("assets") or {}
    for key, value in assets.items():
        if key in ("logoAlt", "bannerAlt"):
            need(isinstance(value, str) and 0 < len(value) <= 255, f"assets.{key}: alt text, 1 to 255 characters")
        elif key == "photos":
            need(isinstance(value, list) and all(isinstance(v, str) and ASSET_NAME.match(v) for v in value), "assets.photos: a list of Asset File names")
        elif key == "folder":
            need(isinstance(value, str), "assets.folder: text")
        else:
            need(isinstance(value, str) and (ASSET_NAME.match(value) and len(value) <= 80 or value.startswith("https://")),
                 f"assets.{key}: {value!r} must be an Asset File name (letters, digits, single underscores) or an https:// link")
    if "logo" in assets:
        need("logoAlt" in assets, "assets.logoAlt: the logo needs alt text (usually the organization's name)")
    for key, value in (kit.get("voice") or {}).items():
        need(isinstance(value, list) and all(isinstance(v, str) for v in value), f"voice.{key}: a list of short texts")
    return problems


# ---- what other skills take ------------------------------------------------------------------------------------------

def tokens(kit):
    """Form Style values by Global Styles token name. Only brand values: layout sizes stay with each template."""
    colors, fonts, style = kit.get("colors") or {}, kit.get("fonts") or {}, kit.get("style") or {}
    out = {}
    if colors.get("primary"):
        out["--ftk-color-primary"] = colors["primary"]
        out["--ftk-color-on-primary"] = "#ffffff"  # the primary always reaches 4.5:1 on white, so white text reads on it
    if fonts.get("body"):
        out["--ftk-font-family"] = fonts.get("bodyStack") or font_stack(fonts["body"])
    if fonts.get("heading"):
        out["--ftk-font-family-heading"] = fonts.get("headingStack") or font_stack(fonts["heading"])
    if style.get("headingWeight"):
        out["--ftk-font-weight-heading"] = style["headingWeight"]
    if style.get("cornerRadius"):
        out["--ftk-radius-medium"] = style["cornerRadius"]
    if style.get("buttonRadius") and style.get("buttonRadius") != style.get("cornerRadius"):
        out["--ftk-button-radius"] = style["buttonRadius"]
    return out


def style_field(token, namespace="FlowToolKit__"):
    """--ftk-color-primary -> FlowToolKit__Color_Primary__c: every Global Styles token maps to one Form Style Defaults field."""
    return namespace + "_".join(part.capitalize() for part in token.removeprefix("--ftk-").split("-")) + "__c"


def logo_fields(kit, namespace="FlowToolKit__"):
    assets = kit.get("assets") or {}
    out = {}
    if assets.get("logo"):
        out[namespace + "Default_Logo__c"] = assets["logo"]
        if assets.get("logoAlt"):
            out[namespace + "Default_Logo_Alt_Text__c"] = assets["logoAlt"]
    return out


def global_styles_import(kit, exported=None):
    """Import replaces every saved org style, so the org's exported values win and the kit only fills what is blank."""
    current = dict(exported or {})
    merged = dict(current)
    added = []
    for token, value in tokens(kit).items():
        if token not in merged or merged[token] in (None, ""):
            merged[token] = value
            added.append(token)
    kept = sorted(t for t, v in tokens(kit).items() if t in current and current[t] not in (None, "") and str(current[t]).lower() != str(v).lower())
    return dict(sorted(merged.items())), added, kept


def plan_style(kit, images=None):
    """The keys form-design's plan.json takes from the kit (its references/plan-format.md)."""
    colors, fonts, style, assets, voice = (kit.get(k) or {} for k in ("colors", "fonts", "style", "assets", "voice"))
    plan_style_keys = {"brand": colors.get("primary"), "heading_color": colors.get("heading"), "accent": colors.get("accent"),
                       "background": colors.get("background"), "font": fonts.get("body"), "heading_font": fonts.get("heading"),
                       "fonts_href": fonts.get("href"), "Corner radius": style.get("cornerRadius")}
    out = {"style": {k: v for k, v in plan_style_keys.items() if v},
           "assets": {k: v for k, v in {"logo": assets.get("logo"), "banner": assets.get("banner"), "tile": assets.get("tile"),
                                        "logo_alt": assets.get("logoAlt"), "banner_alt": assets.get("bannerAlt")}.items() if v}}
    if images:
        out["images"] = images
    swatches = [[name, colors[key], role] for key, name, role in (
        ("primary", "Brand", "buttons, links, selected choices"), ("heading", "Heading", "titles"),
        ("accent", "Accent", "highlights and dividers"), ("background", "Background", "behind the form")) if colors.get(key)]
    out["brand_board"] = {"headline": kit.get("brandName"), "tone": ", ".join(voice.get("adjectives") or []),
                          "copy": (voice.get("sampleHeadings") or [])[:3], "swatches": swatches}
    return out


# ---- command line -----------------------------------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("contrast")
    p.add_argument("colors", nargs="+")
    p = sub.add_parser("confirm")
    p.add_argument("candidates")
    p.add_argument("picks")
    p.add_argument("--out", required=True)
    p.add_argument("--previous", help="the kit saved before, when this is an update")
    p.add_argument("--today")
    p = sub.add_parser("validate")
    p.add_argument("kit")
    p = sub.add_parser("tokens")
    p.add_argument("kit")
    p = sub.add_parser("global-styles")
    p.add_argument("kit")
    p.add_argument("--export", help="the JSON from Global Styles, Export (leave out when nothing is saved)")
    p.add_argument("--out", required=True)
    p = sub.add_parser("plan-style")
    p.add_argument("kit")
    p.add_argument("--plan-dir", help="the form's folder; image paths are written relative to it")
    a = parser.parse_args(argv)

    if a.command == "contrast":
        for value in a.colors:
            hex_color = normalize_hex(value)
            ratio = contrast(hex_color)
            fixed = darken_to(hex_color)
            print(f"{hex_color}: {ratio:.2f}:1 on white" + ("" if fixed == hex_color else f"; {fixed} reaches {contrast(fixed):.2f}:1"))
        return 0
    if a.command == "confirm":
        previous = load(a.previous) if a.previous else None
        kit, files, warnings = confirm(load(a.candidates), load(a.picks), previous, a.today)
        problems = validate(kit)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        out = pathlib.Path(a.out)
        out.write_text(json.dumps(kit, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (out.parent / "picked-files.json").write_text(json.dumps(files, indent=1) + "\n", encoding="utf-8")
        for w in warnings:
            print("note:", w)
        print(f"{out}: {kit['brandName']} version {kit['version']}, {len(kit['assets'])} asset roles; picked image addresses in "
              f"{out.parent / 'picked-files.json'}")
        return 0
    kit = load(a.kit)
    if a.command == "validate":
        problems = validate(kit)
        print("\n".join(problems) if problems else f"{a.kit}: valid")
        return 1 if problems else 0
    if a.command == "tokens":
        print(json.dumps(tokens(kit), indent=1))
        return 0
    if a.command == "global-styles":
        exported = None
        if a.export:
            text = pathlib.Path(a.export).read_text(encoding="utf-8").strip()
            exported = json.loads(text) if text else {}
        merged, added, kept = global_styles_import(kit, exported)
        pathlib.Path(a.out).write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"out": a.out, "added": added, "kept_org_values": kept,
                          "logo": "set the Default Logo by hand: Global Styles, Logo, Select Image" if (kit.get("assets") or {}).get("logo") else None}, indent=1))
        return 0
    if a.command == "plan-style":
        images = None
        manifest = pathlib.Path(a.kit).parent / "assets" / "manifest.json"
        if manifest.exists():
            files = load(manifest)
            base = pathlib.Path(a.plan_dir).resolve() if a.plan_dir else pathlib.Path.cwd()
            images = {}
            for role in ("logo", "banner"):
                entry = files.get(role) or {}
                path = entry.get("canvas") or entry.get("file")
                if path:
                    images[role] = os.path.relpath((manifest.parent / path).resolve(), base).replace(os.sep, "/")
        print(json.dumps(plan_style(kit, images), indent=1, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
