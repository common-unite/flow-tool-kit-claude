#!/usr/bin/env python3
"""Draw a site's review canvas from its page.json files with the real FlowToolKit Site Blocks components.

    python3 -I build_site_review.py --site _site/<slug> [--mode code|chat] [--kit DIR] [--config flow-tool-kit.json] [--no-measure]
    python3 -I build_site_review.py --site _site/<slug> --record-blobs '<{"name or file": "/_blob/<id>"}>'

page.json is the source of truth and this draws it; every house rule for a site canvas lives here once. Rerun after any
page.json change. The site folder holds site.json (pages in order, palette, brand, shared header and footer, audiences,
assets) and pages/<urlName>.json (references/page-json.md). Writes, under <site>/design/:

  project/Main.dc.html                           the brand artboard (the selected palette, fonts, logo, tone, general copy)
  project/<page>.dc.html, <page>-phone.dc.html   each page at 1280 and at 390, every section tagged with its id and job
  project/<page>-<state>.dc.html                 the extra states a page declares (_design.states)
  project/SectionJobs.dc.html                    every section's job and design card, and the handoff checklist
  project/ContentToCollect.dc.html               photos, copy and numbers still owed, every [CONFIRM: ...], sample records
  project/canvas.json                            the canvas index, with the Site Blocks design system installed (namespace sb)
  publish-batches.json                           the publish as `files` maps (root design/), in order, within the per-call limit
  uploads.json                                   images the artboards draw that are not uploaded to the canvas yet
  review.html                                    one self-contained page with every artboard, for when the Design type is off

--mode code (Claude Code): the design system's code and tokens are copied server side from the person's own Site Blocks
design system (its link is design_systems.site_blocks.url in flow-tool-kit.json). --mode chat: chat cannot copy between
artifacts, so those files are written from the kit the plugin ships (its ftk-design-system skill) into design/project/ds/sb/ and sent 16 to a call. Images are
never copied: the canvas serves an image only as an upload to it.

Components are mounted as <x-import component-from-global-scope="SB.Section">, nested, each one's props from renderVals()
through dc-props. No screenshots, no look-alikes. Exit codes: 0 drawn, 1 errors (nothing publishable), 3 drawn without
a design system link (review.html is still written).
"""
import argparse
import base64
import html
import json
import mimetypes
import os
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import htmlcheck  # noqa: E402
sys.path.insert(0, str(HERE.parent / "_shared" / "lib"))
import siblings  # noqa: E402

NS = "sb"  # the folder the design system is installed in on the canvas: project/ds/sb/
DESKTOP, PHONE = 1280, 390
BAR = 40  # the page bar above each page artboard
CAP = 8000  # the tallest artboard the Design canvas takes
# The kits ship in the plugin's ftk-design-system skill; FTK_SITE_BLOCKS_KIT (the site-blocks folder) or
# FTK_DESIGN_SYSTEMS_DIR (the folder holding site-blocks/ and ftk-forms/) points at another copy
KITS_ENV = "FTK_DESIGN_SYSTEMS_DIR"
CONFIG_NAME = "flow-tool-kit.json"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BATCH = {"code": 255, "chat": 16}

# The design system's own files every artboard loads (React stays behind: the canvas has it)
DS_FILES = ["components/bundle.css", "components/lib/slds-icons-2.30.7.js", "components/lib/ftk-illustrations.js", "components/bundle.js"]
LWR_CSS = "components/bundle-lwr.css"
REACT_FILES = ["components/lib/react.production.min.js", "components/lib/react-dom.production.min.js"]
# The bundle's own Asset File rules: a packaged image name to its file in the design system
ASSET_GROUPS = [(re.compile(r"^Background_"), "Backgrounds", ".jpg"), (re.compile(r"^People_"), "People", ".jpg"), (re.compile(r"_Bear_\d+$"), "Bears", ".png")]
ASSET_ALIASES = {"FlowToolKit_Gray": "Logos/FlowToolKit_Gray.png", "FlowToolKit_White": "Logos/FlowToolKit_White.png"}
# Fallback heights when the artboards cannot be rendered here (over-tall beats clipped)
EST = {"hero": 640, "statsBar": 240, "facts": 420, "quote": 480, "callout": 300, "cards": 620, "steps": 560, "timeline": 640}
# The free edition, outside sandboxes and Developer Edition orgs (which show everything): a block on a record page shows a notice
# instead of the record unless the page's record is one of FREE_OBJECTS, and a record form (a repeater's card) works only on
# FREE_FORM_OBJECTS
FREE_OBJECTS = {"Account", "Contact", "Case", "Lead", "FlowToolKit__Form_Template__c"}
FREE_FORM_OBJECTS = {"Account", "Contact", "Lead", "Case", "Campaign", "CampaignMember", "FlowToolKit__Form_Submission__c",
                     "FlowToolKit__Survey_Response__c", "FlowToolKit__Form_Template__c", "FlowToolKit__Form_Page__c", "FlowToolKit__Form_Page_Section__c"}


class SiteError(SystemExit):
    pass


def esc(s):
    return html.escape(str(s or ""), quote=True).replace("{{", "{&#123;")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:32] or "section"


# ---------- Preflight: the design kit and the project config ----------

class Kit:
    """The Site Blocks kit as shipped (its libraries and photos live once, in the FlowToolKit Forms kit beside it) or as an
    installed design system (everything under one project/). file() finds a project-relative path in either."""

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.roots = [self.root / "project"]
        forms = self.root.parent / "ftk-forms" / "project"
        if forms.is_dir():
            self.roots.append(forms)

    def file(self, rel):
        for base in self.roots:
            path = base / rel
            if path.is_file():
                return path
        return None


def default_kit(skill_dir=HERE.parent):
    """site-blocks/ in the ftk-design-system skill beside this one (ftk-design-system/ or <plugin>:ftk-design-system/)"""
    try:
        return pathlib.Path(siblings.find(str(skill_dir), "ftk-design-system", markers=["site-blocks/project"],
                                          env=KITS_ENV)) / "site-blocks"
    except siblings.NotFound as missing:
        raise SiteError(f"Site Blocks kit not found. {missing}")


def find_kit(arg=None):
    root = pathlib.Path(arg or os.environ.get("FTK_SITE_BLOCKS_KIT") or default_kit()).expanduser()
    kit = Kit(root)
    missing = [p for p in ["tokens.json"] + DS_FILES + REACT_FILES if not kit.file(p)]
    if missing:
        raise SiteError(f"Site Blocks kit not found or incomplete at {root} (missing {', '.join(missing)}). The kits ship in "
                        "the plugin's ftk-design-system skill: install the whole Flow Tool Kit plugin, or pass --kit to use "
                        "another copy.")
    schema_file = root / "tools/schema.json"
    if schema_file.exists():
        schema = json.loads(schema_file.read_text())
        limits_file = root / "tools/column_limits.json"
        limits = json.loads(limits_file.read_text()) if limits_file.exists() else {}
    else:
        bundled = json.loads((HERE / "block_schema.json").read_text())
        schema, limits = {"types": bundled["types"]}, bundled.get("columnLimits") or {}
    return kit, schema, limits


def find_config(start, given=None):
    """flow-tool-kit.json (ftk-start writes it): --config, else the site folder or any folder above it"""
    if given:
        path = pathlib.Path(given)
        return json.loads(path.read_text()), path
    for folder in [start, *start.parents]:
        path = folder / CONFIG_NAME
        if path.exists():
            return json.loads(path.read_text()), path
    return {}, None


def design_system(config):
    return (config.get("design_systems") or {}).get("site_blocks") or {}


# ---------- Reading the site ----------

def load_site(folder):
    folder = pathlib.Path(folder)
    site_file = folder / "site.json"
    if not site_file.exists():
        raise SiteError(f"{site_file} not found: write site.json first (start_site.py, references/page-json.md)")
    site = json.loads(site_file.read_text())
    entries = site.get("pages") or [{"urlName": p.stem} for p in sorted((folder / "pages").glob("*.json"))]
    pages = []
    for entry in entries:
        path = folder / "pages" / f"{entry['urlName']}.json"
        if not path.exists():
            raise SiteError(f"site.json lists page {entry['urlName']} but {path} does not exist")
        pages.append((entry, merge_page(site, json.loads(path.read_text()))))
    return site, pages


def merge_page(site, page):
    """A page's settings over the site's shared ones (site.json "page"): the header, footer, layout, logo and navigation"""
    shared = site.get("page") or {}
    merged = {**shared, **page}
    for key in ("header", "footerContent"):
        if not page.get(key) and shared.get(key):
            merged[key] = shared[key]
    if not merged.get("theme") and site.get("brand", {}).get("theme"):
        merged["theme"] = site["brand"]["theme"]
    return merged


def audiences(site, entry):
    return tuple(entry.get("audience") or site.get("audiences") or ())


def swap_palette(value, palette):
    """"$name" colours in page.json become the palette's hex for drawing"""
    if isinstance(value, str) and value.startswith("$") and value[1:] in palette:
        return palette[value[1:]]
    if isinstance(value, dict):
        return {k: swap_palette(v, palette) for k, v in value.items()}
    if isinstance(value, list):
        return [swap_palette(v, palette) for v in value]
    return value


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def confirms(value):
    return [m.group(0) for s in strings(value) for m in re.finditer(r"\[CONFIRM:[^\]]*\]", s)]


# ---------- Validation ----------

def section_id(section, index):
    d = section.get("_design") or {}
    return d.get("id") or f"s{index:02d}-{slug(d.get('job') or 'section')}"


def items_of(section):
    for column in section.get("columns") or []:
        for item in column.get("items") or []:
            yield item
            for tab in item.get("tabs") or []:
                yield from tab.get("items") or []


def markup_items(page):
    """(where, item) for every HTML Editor and Rich Content Editor item: sections, header and footer"""
    regions = [("header", s) for s in page.get("header") or []] + [(None, s) for s in page.get("sections") or []] + \
              [("footer", s) for s in page.get("footerContent") or []]
    n = 0
    for region, section in regions:
        if region is None:
            n += 1
        sid = section_id(section, n) if region is None else f"{region}-{slug((section.get('_design') or {}).get('job') or 'shared')}"
        for item in items_of(section):
            if item.get("kind") in ("htmlEditor", "richText"):
                yield sid, item


def validate(page_name, page, schema, site, entry):
    """Refuse what the build cannot take or must not ship, naming the section: an unknown block type, a column set that is
    not one to four adding to 12, a repeater without its object and card, markup that runs code or loads another document.
    Returns warnings."""
    types = schema.get("types") or {}
    warnings, seen = [], set()
    for i, section in enumerate(page.get("sections") or [], 1):
        sid = section_id(section, i)
        if sid in seen:
            raise SiteError(f"{page_name}: section id {sid} is used twice; give each section its own _design.id")
        seen.add(sid)
        widths = [int(c.get("width") or 12) for c in section.get("columns") or []]
        if not widths or len(widths) > 4 or (len(widths) > 1 and sum(widths) != 12):
            raise SiteError(f"{page_name} section {sid}: columns must be one to four adding up to 12, got {' + '.join(map(str, widths)) or 'none'}")
        for item in items_of(section):
            if item.get("kind") == "repeater" and not (item.get("object") and item.get("card")):
                missing = " and ".join(k for k in ("object", "card") if not item.get(k))
                raise SiteError(f"{page_name} section {sid}: the repeater has no {missing}. build-site-pages cannot build a listing drawn only from "
                                "sample records: give it object, card (the fields each card shows, as {{Field}}), filter, sortField and "
                                "emptyMessage (references/page-json.md); ask for them if they are not known yet")
            if item.get("kind") == "block":
                st = (item.get("props") or {}).get("sectionType")
                if st not in types:
                    raise SiteError(f"{page_name} section {sid}: unknown block type {st!r}; use one of {', '.join(sorted(types))}")
                if types[st].get("deprecated"):
                    warnings.append(f"{page_name} section {sid}: {st} is soft-retired; pick another block")
    for region in ("header", "footerContent"):
        for section in page.get(region) or []:
            if any(i.get("kind") == "repeater" and not (i.get("object") and i.get("card")) for i in items_of(section)):
                raise SiteError(f"{page_name} {region}: a repeater has no object or card; give it object, card, filter, sortField and emptyMessage")
    errors = []
    for sid, item in markup_items(page):
        found, _ = htmlcheck.check_markup(item.get("richTextValue"), f"{page_name} {sid}", audiences(site, entry), site.get("palette"), item["kind"])
        errors += found
    if errors:
        raise SiteError("Markup the site must not run (references/html-editor.md):\n  " + "\n  ".join(errors))
    if (site.get("edition") or "").lower() == "free":
        for i, section in enumerate(page.get("sections") or [], 1):
            for item in items_of(section):
                obj = item.get("object") if item.get("kind") == "repeater" else None
                if obj and obj not in FREE_FORM_OBJECTS:
                    warnings.append(f"{page_name} section {section_id(section, i)}: a repeater on {obj} cannot show its record cards on the free "
                                    "edition (record forms work on Account, Contact, Lead, Case, Campaign, Campaign Member and Form Submission)")
        record = entry.get("recordObject")
        if record and record not in FREE_OBJECTS:
            warnings.append(f"{page_name}: a record page on {record} shows a notice instead of the record's values on the free edition "
                            "(blocks read records of Account, Contact, Case, Lead and Form Template)")
    return warnings


# ---------- The tree: one structure, drawn as x-dc markup and rendered locally to measure ----------

def comp(name, props, children=()):
    return {"c": name, "p": props, "k": list(children)}


# A record page's photo is the record's own field ({{Photo__c}}); the canvas has no record, so it draws a package demo image
# in its place. A section may name another with _design.photoStandIn, or several with _design.photoStandIns.
PHOTO_STAND_IN = "FlowToolKit__Background_Volunteer_Build_Day"
IMAGE_KEYS = (("imageSource", "imageAsset", "imageUrl"), ("backgroundImageSource", "backgroundImageAsset", "backgroundImageUrl"))


def merge_token(value):
    return isinstance(value, str) and bool(re.search(r"\{\{\s*[A-Za-z_][\w.]*\s*\}\}", value))


def record_photo(props, which="image"):
    """The block or card takes its photo (or, with which="background", its background) from a record field"""
    source, _, url = IMAGE_KEYS[which == "background"]
    return (props.get(source) == "url" and merge_token(props.get(url))) or (which == "image" and not props.get(source) and merge_token(props.get("image")))


def stand_in(props, standin):
    """The props as the canvas draws them: a record-field photo becomes the package stand-in, drawn as an asset. standin is one asset
    name or a list (_design.photoStandIns), which the items' photos take in turn.

    Item photos matter as much as the block's: the package blanks every {{token}} when the page has no record, and a photo-led
    item (a carousel slide) with a blank photo and a blank {{Name}} title is dropped, so a record carousel would draw empty."""
    standins = [standin] if isinstance(standin, str) else list(standin) or [PHOTO_STAND_IN]
    drawn = dict(props)
    for which, (source, asset, url) in zip(("image", "background"), IMAGE_KEYS):
        if record_photo(props, which):
            drawn.update({source: "asset", asset: standins[0]})
            drawn.pop(url, None)
            if which == "image":
                drawn.pop("image", None)
    if isinstance(props.get("items"), list):
        photos = [i for i in props["items"] if isinstance(i, dict) and merge_token(i.get("iconImage"))]
        if photos:
            turn = iter(range(len(photos)))
            drawn["items"] = [dict(i, iconImage=standins[next(turn) % len(standins)]) if i in photos else i for i in props["items"]]
    return drawn


REPEATER_KEYS = ("cardType", "columns", "largeColumns", "mediumColumns", "smallColumns", "brandColor", "accentColor")


def item_node(item, palette, empty_repeaters=False, standin=PHOTO_STAND_IN):
    kind = item.get("kind")
    if kind == "block":
        return comp("SB.Block", swap_palette(stand_in(item.get("props") or {}, standin), palette))
    if kind == "divider":
        return comp("SB.Divider", {k: v for k, v in (item.get("attributes") or {}).items() if k != "displayAsDivider"})
    if kind == "richText":
        return comp("SB.RichContent", {"richTextValue": item.get("richTextValue", "")})
    if kind == "htmlEditor":
        # designTag draws a small "HTML" tag on the canvas, so reviewers see where custom markup sits; the build ignores it
        return comp("SB.HtmlEditor", {"richTextValue": item.get("richTextValue", ""), "designTag": True})
    if kind == "search":
        return comp("SB.Search", {"placeholder": item.get("placeholder")} if item.get("placeholder") else {})
    if kind == "languageSelector":
        return comp("SB.LanguageSelector", {})
    if kind == "tabs":
        tabs = item.get("tabs") or []
        return comp("SB.Tabs", {"tabs": [{"tabName": t["tabName"], "tabKey": t["tabKey"]} for t in tabs], "activeTab": item.get("activeTab")},
                    [comp("div", {}, [item_node(i, palette, empty_repeaters, standin) for i in t.get("items") or []]) for t in tabs])
    if kind == "formSlot":
        return comp("SB.FormSlot", {k: v for k, v in {"form": item.get("form"), "kind": item.get("formKind"), "component": item.get("component"),
                                                       "formTemplate": item.get("formTemplate")}.items() if v})
    if kind == "repeater":
        records = [] if empty_repeaters else ((item.get("_design") or {}).get("sampleRecords") or [])
        props = {k: item[k] for k in REPEATER_KEYS if item.get(k)}
        # a sample card is drawn the way the build's card template lays out every record: the template's fixed settings (no merge
        # field) under the sample's own values, so a style set once on the card shows on every sample
        template = {k: v for k, v in (item.get("card") or {}).items() if k != "link" and not any(merge_token(x) for x in strings(v))}
        return comp("SB.Repeater", dict(swap_palette(props, palette), records=swap_palette([stand_in(dict(template, **r), standin) for r in records], palette)))
    raise SiteError(f"{kind!r} is not a site component")


def section_node(section, palette, empty_repeaters=False):
    attrs = {k: v for k, v in (section.get("attributes") or {}).items() if k != "sectionConfig"}
    design = section.get("_design") or {}
    standin = design.get("photoStandIns") or design.get("photoStandIn") or PHOTO_STAND_IN
    columns = [comp("SB.Column", {"columnWidth": str(c.get("width") or 12)}, [item_node(i, palette, empty_repeaters, standin) for i in c.get("items") or []])
               for c in section.get("columns") or []]
    return comp("SB.Section", swap_palette(attrs, palette), columns)


def tag_text(number, section, region=None):
    d = section.get("_design") or {}
    parts = [f"{number:02d}" if number else region, d.get("job") or ("Shared " + region.lower() if region else "No job named"), d.get("designCard")]
    count = len(confirms(section))
    if count:
        parts.append(f"{count} to confirm")
    return " · ".join(p for p in parts if p)


def tab_state(page, state):
    """A state {id, title, section, activeTab}: that one section drawn with that tab open, so every tab's content is on the canvas"""
    for n, section in enumerate(page.get("sections") or [], 1):
        if section_id(section, n) == state.get("section"):
            opened = json.loads(json.dumps(section))
            for column in opened.get("columns") or []:
                for item in column.get("items") or []:
                    if item.get("kind") == "tabs" and any(t.get("tabKey") == state["activeTab"] for t in item.get("tabs") or []):
                        item["activeTab"] = state["activeTab"]
            return dict(page, sections=[opened])
    raise SiteError(f"state {state.get('id')}: no section {state.get('section')!r} to open tab {state['activeTab']!r} in")


def sample_needed(section, empty_repeaters):
    return [i for i in items_of(section) if i.get("kind") == "repeater" and (empty_repeaters or not (i.get("_design") or {}).get("sampleRecords"))]


# {{Field}}, {{Account.Name}}, and a formatted {{$number.Field}} (the sample value is written already formatted)
TOKEN = re.compile(r"\{\{\s*(?:\$\w+\.)?([A-Za-z_][\w.]*)\s*\}\}")


def fill_sample(value, record):
    """Every {{Field}} the sample record names, filled in; any other token is left for the package (which blanks it) or stand_in"""
    if isinstance(value, str):
        return TOKEN.sub(lambda m: str(record[m.group(1)]) if m.group(1) in record else m.group(0), value)
    if isinstance(value, list):
        return [fill_sample(v, record) for v in value]
    if isinstance(value, dict):
        return {k: fill_sample(v, record) for k, v in value.items()}
    return value


def sample_section(section, record):
    """The section as a record page draws it on the canvas: its blocks' {{Field}} text filled from the page's _design.sampleRecord.
    The canvas has no record and the package blanks every token without one, so a heading would read "The story of" with the
    name missing. Only blocks are filled: a repeater's card fields belong to its own records (_design.sampleRecords)."""
    if not record:
        return section

    def fill_items(items):
        out = []
        for item in items or []:
            if item.get("kind") == "block":
                item = dict(item, props=fill_sample(item.get("props") or {}, record))
            elif item.get("kind") == "tabs":
                item = dict(item, tabs=[dict(t, items=fill_items(t.get("items"))) for t in item.get("tabs") or []])
            out.append(item)
        return out

    return dict(section, columns=[dict(c, items=fill_items(c.get("items"))) for c in section.get("columns") or []])


def page_tree(page, palette, empty_repeaters=False):
    """SB.Page > each section in its own tagged wrapper. Header and footer sections are drawn on every page"""
    record = (page.get("_design") or {}).get("sampleRecord") or {}
    page = dict(page, sections=[sample_section(s, record) for s in page.get("sections") or []])
    settings = {k: v for k, v in page.items() if k not in ("sections", "header", "footerContent", "_design")}
    settings = swap_palette(settings, palette)
    settings.pop("site", None)  # drawn as Aura; the build places it on either site type (design system README, Aura and LWR)
    wrapped = []
    header = page.get("header") or []
    footer = page.get("footerContent") or []
    regions = [("Header", s, None) for s in header] + [(None, s, i) for i, s in enumerate(page.get("sections") or [], 1)] + [("Footer", s, None) for s in footer]
    for region, section, number in regions:
        sid = section_id(section, number) if number else f"{region.lower()}-{slug((section.get('_design') or {}).get('job') or 'shared')}"
        d = section.get("_design") or {}
        wrapper = {"id": sid, "data-section-id": sid, "style": {"position": "relative"}}
        tag = {"text": tag_text(number, section, region), "source": d.get("source"), "sample": bool(sample_needed(section, empty_repeaters))}
        wrapped.append(comp("div", wrapper, [section_node(section, palette, empty_repeaters)]) | {"tag": tag})
    return comp("SB.Page", settings, wrapped)


# ---------- Drawing: x-dc markup ----------

def css(style):
    return "; ".join(f"{re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), k)}: {v}" for k, v in style.items())


TAG_STYLE = ("position: absolute; top: -11px; right: 8px; z-index: 20; display: flex; gap: 6px; align-items: center; padding: 4px 10px; "
             "border-radius: 4px; background: #181818; color: #ffffff; font: 600 12px/1.3 system-ui, sans-serif; pointer-events: auto")
NEED_STYLE = "background: #c23934; padding: 1px 6px; border-radius: 3px"


def tag_html(t):
    src = f'<a href="{esc(t["source"])}" target="_blank" rel="noopener" style="color: #9fd4ff">source</a>' if str(t.get("source") or "").startswith("http") else ""
    need = f'<span style="{NEED_STYLE}">sample records needed</span>' if t.get("sample") else ""
    return f'<div style="{TAG_STYLE}"><span>{esc(t["text"])}</span>{src}{need}</div>'


def markup(node, vals):
    """No whitespace between elements: a text node inside an x-import becomes a child the SB components would try to clone"""
    if node["c"] == "div":
        attrs = "".join(f' {k}="{esc(v)}"' for k, v in node["p"].items() if k != "style")
        style = f' style="{css(node["p"].get("style") or {})}"' if node["p"].get("style") else ""
        tag = tag_html(node["tag"]) if node.get("tag") else ""
        return f"<div{attrs}{style}>{tag}" + "".join(markup(k, vals) for k in node["k"]) + "</div>"
    key = f"n{len(vals)}"
    vals[key] = node["p"]
    return f'<x-import component-from-global-scope="{node["c"]}" dc-props="{{{{{key}}}}}">' + "".join(markup(k, vals) for k in node["k"]) + "</x-import>"


def head(title, width, lwr=False, fonts_href=None, sb=True):
    font = f'<link rel="stylesheet" href="{esc(fonts_href)}">\n' if fonts_href else ""
    if not sb:
        return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                f'<title>{esc(title)}</title>\n<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n{font}'
                "<style>\nbody{margin:0;background:#ffffff}\n</style>\n</helmet>\n")
    links = "".join(f'<link rel="stylesheet" href="ds/{NS}/{f}">\n' for f in DS_FILES if f.endswith(".css"))
    if lwr:
        links += f'<link rel="stylesheet" href="ds/{NS}/{LWR_CSS}">\n'
    scripts = "".join(f'<script src="ds/{NS}/{f}"></script>\n' for f in DS_FILES if f.endswith(".js"))
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<title>{esc(title)}</title>\n<script src="./support.js"></script>\n<link rel="stylesheet" href="sb-tokens.css">\n{links}{scripts}'
            f'<script src="sb-site.js"></script>\n<script src="sb-{width}.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n{font}'
            "<style>\nbody{margin:0;background:#ffffff}\n</style>\n</helmet>\n")


def logic(props, vals):
    dp = json.dumps(props).replace("&", "&amp;").replace("'", "&#39;")
    body = json.dumps(vals, ensure_ascii=False).replace("</", "<\\/")
    return (f"<script type=\"text/x-dc\" data-dc-script data-props='{dp}'>\n"
            "class Component extends DCLogic {\n  renderVals() {\n"
            f"    return {body};\n  }}\n}}\n</script>\n</body>\n</html>\n")


def page_bar(title, entry, width):
    route = entry.get("route") or "/" + entry["urlName"]
    current = f' · <a href="{esc(entry["currentUrl"])}" target="_blank" rel="noopener">the page it replaces</a>' if entry.get("currentUrl") else ""
    who = f' · seen by {esc(", ".join(entry["audience"]))}' if entry.get("audience") else ""
    return (f'<div style="height: {BAR}px; box-sizing: border-box; padding: 10px 16px; background: #f3f3f3; border-bottom: 1px solid #d9d9d9; '
            f'font: 13px/20px system-ui, sans-serif; color: #353535">{esc(title)} · {esc(route)}{who} · drawn at {width}px{current}</div>')


def page_artboard(title, entry, tree, width, height, lwr, fonts_href):
    vals = {}
    body = markup(tree, vals)
    return (head(title, width, lwr, fonts_href) +
            f'<div style="width: {width}px; min-height: {height}px; box-sizing: border-box; background: #ffffff; display: flex; flex-direction: column">\n  '
            + page_bar(title, entry, width) + "\n" + body + "\n</div>\n</x-dc>\n" + logic({"$preview": {"width": width, "height": height}}, vals))


def static_body(width, height, inner, bg="#ffffff"):
    return (f'<div style="width: {width}px; min-height: {height}px; box-sizing: border-box; padding: 56px; display: flex; flex-direction: column; '
            f'gap: 32px; background: {bg}; color: #181818; font-family: system-ui, sans-serif">\n{inner}\n</div>')


def static_artboard(title, width, height, inner, fonts_href=None, bg="#ffffff"):
    return (head(title, width, False, fonts_href, sb=False) + static_body(width, height, inner, bg) + "\n</x-dc>\n"
            + logic({"$preview": {"width": width, "height": height}}, {}))


def h2(text):
    return f'<h2 style="margin: 0; font-size: 28px; font-weight: 600">{esc(text)}</h2>'


def brand_inner(site, asset_url):
    """The brand as picked: only the selected palette, fonts, logo, button style, tone and general copy"""
    b = site.get("brand") or {}
    fonts = b.get("fonts") or {}
    heading_css = fonts.get("heading_css") or "inherit"
    logo = b.get("logo")
    logo_src = asset_url(logo) if logo else None
    swatches = "".join(
        f'<div style="display: flex; flex-direction: column; gap: 6px"><div style="width: 180px; height: 96px; background: {esc(c["hex"])}; border: 1px solid #d9d9d9"></div>'
        f'<strong style="font-size: 14px">{esc(c["name"])}</strong><span style="font-size: 13px; color: #353535">{esc(c["hex"])} · {esc(c.get("role", ""))}</span></div>'
        for c in b.get("colors") or [{"name": k, "hex": v} for k, v in (site.get("palette") or {}).items()])
    images = "".join(f'<figure style="margin: 0; display: flex; flex-direction: column; gap: 6px"><img src="{esc(asset_url(i["asset"]))}" alt="{esc(i.get("alt", ""))}" '
                     f'style="width: 320px; height: 200px; object-fit: cover"><figcaption style="font-size: 13px; color: #353535">{esc(i.get("caption", ""))}</figcaption></figure>'
                     for i in b.get("images") or [])
    brand = (site.get("palette") or {}).get("brand") or (b.get("theme") or {}).get("brand") or "#181818"
    radius = b.get("buttonRadius", "4px")
    inner = (f'<div style="display: flex; align-items: center; gap: 28px">'
             + (f'<img src="{esc(logo_src)}" alt="{esc(site.get("title", ""))} logo" style="height: 96px; width: auto">' if logo_src else "")
             + f'<div style="display: flex; flex-direction: column; gap: 6px"><h1 style="margin: 0; font-family: {esc(heading_css)}; font-size: 52px">{esc(site.get("title", ""))}</h1>'
             f'<p style="margin: 0; font-size: 16px; color: #353535">The brand as selected, for every page of this site. Change a pick in the brand kit or site.json, not here.</p></div></div>\n'
             f'<section style="display: flex; flex-direction: column; gap: 16px">{h2("Colors")}<div style="display: flex; gap: 24px; flex-wrap: wrap">{swatches}</div></section>\n'
             f'<section style="display: flex; gap: 64px"><div style="display: flex; flex-direction: column; gap: 12px; flex: 1">{h2("Type and buttons")}'
             f'<p style="margin: 0; font-family: {esc(heading_css)}; font-size: 40px; font-weight: 600">{esc(fonts.get("heading", "Heading font"))}</p>'
             f'<p style="margin: 0; font-family: {esc(fonts.get("body_css") or "inherit")}; font-size: 18px">{esc(fonts.get("body", "Body font"))}: the quick brown fox jumps over the lazy dog.</p>'
             f'<div style="display: flex; gap: 16px"><span style="padding: 12px 32px; border-radius: {esc(radius)}; background: {esc(brand)}; color: #ffffff; font-weight: 600">Primary</span>'
             f'<span style="padding: 12px 32px; border-radius: {esc(radius)}; border: 2px solid {esc(brand)}; color: {esc(brand)}; font-weight: 600">Secondary</span></div></div>'
             f'<div style="display: flex; flex-direction: column; gap: 12px; flex: 1">{h2("Tone")}<p style="margin: 0; font-size: 16px; line-height: 1.6">{esc(b.get("tone", "[CONFIRM: tone paragraph from the intake]"))}</p></div></section>\n'
             + (f'<section style="display: flex; flex-direction: column; gap: 16px">{h2("Selected images")}<div style="display: flex; gap: 24px; flex-wrap: wrap">{images}</div></section>\n' if images else "")
             + f'<section style="display: flex; flex-direction: column; gap: 12px">{h2("General copy")}'
             + "".join(f'<p style="margin: 0; font-size: 16px; line-height: 1.6; max-width: 1200px">{esc(p)}</p>' for p in b.get("copy") or ["[CONFIRM: general copy from the intake]"])
             + "</section>")
    height = 1300 + (260 if images else 0) + 40 * len(b.get("copy") or [])
    return inner, height


def table(head_cells, rows):
    th = "".join(f'<th style="padding: 8px 10px; text-align: left">{esc(c)}</th>' for c in head_cells)
    trs = "".join("<tr style=\"border-bottom: 1px solid #e5e5e5; background: {}\">".format(r[1]) + "".join(f'<td style="padding: 7px 10px; vertical-align: top">{c}</td>' for c in r[0]) + "</tr>" for r in rows)
    return (f'<table style="width: 100%; border-collapse: collapse; font-size: 13px"><thead><tr style="background: #353535; color: #ffffff">{th}</tr></thead>'
            f"<tbody>{trs}</tbody></table>")


# ---------- The handoff checklist (Choosing-blocks.md, "Before you hand a design over"), as far as page.json can show it ----------

def limit_rows(limits, block):
    entry = limits.get(block) or {}
    rows = entry.get("rows") if isinstance(entry, dict) else entry
    return json.loads(rows.replace("'", '"')) if isinstance(rows, str) else (rows or [])


def column_minimum(limits, card):
    """A design card such as "Hero 03" and the narrowest column its block README allows (1 of 3 -> 4, 1 of 2 -> 6)"""
    m = re.match(r"(.+?)\s+(\d+)$", card or "")
    if not m:
        return 0
    for row in limit_rows(limits, m.group(1).replace(" ", "")):
        if m.group(2) in row.get("designs", []):
            return {"1 of 2": 6, "1 of 3": 4, "full width": 12}.get(row.get("narrowest"), 0)
    return 0


def ground(section):
    """What a section reads as from a distance: its own background, else the lead block in its widest column (a photo counts as the photo).
    A side column's card (an Action Card beside a Repeater) is not the ground"""
    columns = section.get("columns") or []
    widest = max(columns, key=lambda c: int(c.get("width") or 12), default={})
    lead = next((i.get("props") or {} for i in widest.get("items") or [] if i.get("kind") == "block"), {})
    face = "photo:" + lead["backgroundImageAsset"] if lead.get("backgroundImageAsset") else str(lead.get("background") or "")
    return str((section.get("attributes") or {}).get("background") or "") + "|" + face


def handoff(page, limits):
    sections = page.get("sections") or []
    blocks = [i.get("props") or {} for s in sections for i in items_of(s) if i.get("kind") == "block"]
    widths = {tuple(str(c.get("width")) for c in s.get("columns") or []) for s in sections}
    grounds = [ground(s) for s in sections]
    attached = [any((i.get("props") or {}).get("attachToPrevious") for i in items_of(s)) for s in sections]
    neighbours = [f"{section_id(sections[n], n + 1)}" for n in range(1, len(sections)) if grounds[n] == grounds[n - 1] and grounds[n] != "|" and not attached[n]]
    last = [i.get("props") or {} for i in items_of(sections[-1])] if sections else []
    closing = any(p.get("sectionType") == "actionCard" or p.get("heroLayout") == "band" or p.get("sectionType") == "callout" for p in last)
    narrow = [f"{section_id(s, n)} {(s.get('_design') or {}).get('designCard')}" for n, s in enumerate(sections, 1)
              for c in s.get("columns") or [] if int(c.get("width") or 12) < column_minimum(limits, (s.get("_design") or {}).get("designCard"))]
    html_items = [(section_id(s, n), i) for n, s in enumerate(sections, 1) for i in items_of(s) if i.get("kind") == "htmlEditor"]
    no_reason = [sid for sid, i in html_items if not (i.get("_design") or {}).get("reason")]
    return [
        ("Each section names its job", all((s.get("_design") or {}).get("job") for s in sections), ""),
        ("Each section names its design card", all((s.get("_design") or {}).get("designCard") for s in sections), ""),
        ("No two neighbours share a background unless attached", not neighbours, ", ".join(neighbours)),
        ("At most one entrance", sum(1 for p in blocks if p.get("entrance")) <= 1, f"{sum(1 for p in blocks if p.get('entrance'))} entrances"),
        ("Records come from record cards, not hand-written cards", True, "check by eye"),
        ("Ends with a closing band, Callout or Action Card", closing, ""),
        ("Column widths vary somewhere", len(widths) > 1, ""),
        ("No design in a column narrower than its Column limits", not narrow, ", ".join(narrow)),
        ("Each HTML Editor says why no block does the job", not no_reason, f"add _design.reason to {', '.join(no_reason)}" if no_reason else ""),
        ("Blocks first: at most two HTML Editors on a page", len(html_items) <= 2, f"{len(html_items)} HTML Editors"),
        ("Every fact still to supply is listed", True, f"{len(confirms(page))} [CONFIRM] marks"),
    ]


# ---------- House checks (references/house-rules.md): rich block use is the norm, as far as page.json can show it ----------

SCRIM = {"tint", "side", "bottom", "light", "custom"}
# Keys that carry words, palette or alignment, never a design: a block with nothing else set is the block's defaults
NOT_DESIGN = {"sectionType", "brandColor", "accentColor", "buttons", "badges", "imageAlt", "imageSource", "backgroundImageSource",
              "headingAlign", "bodyAlign", "buttonAlign", "badgeAlign", "footnoteAlign", "eyebrow", "title", "subtitle", "badge", "value", "date"}
TEXT_KINDS = {"richText", "htmlEditor", "divider"}


def collection(props, key):
    value = props.get(key)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    return value if isinstance(value, list) else []


def plain(text):
    return re.sub(r"<[^>]+>", " ", str(text or "")).strip()


def photo_band(props, record_page=False):
    """A packaged or organization photo behind the block, or on a record page the record's own photo field, with a scrim so the text reads"""
    photo = bool(props.get("backgroundImageAsset")) or (record_page and record_photo(props, "background"))
    return photo and props.get("backgroundOverlay") in SCRIM


def hero_range(props):
    """Which parts of a hero's range the block uses: tags, a longer description, two buttons, a secondary image, facts or stats"""
    parts = []
    if collection(props, "badges"):
        parts.append("tags")
    if len(plain(props.get("subheading")) + plain(props.get("description"))) >= 120:
        parts.append("a longer description")
    if len(collection(props, "buttons")) >= 2:
        parts.append("two buttons")
    if (props.get("imageAsset") or props.get("imageUrl")) and props.get("heroMedia") in (None, "", "image"):
        parts.append("a secondary image")
    if collection(props, "stats") or collection(props, "items") or collection(props, "bullets"):
        parts.append("facts or stats")
    return parts


def at_defaults(props, schema):
    t = (schema.get("types") or {}).get(props.get("sectionType")) or {}
    content = {f.get("name") if isinstance(f, dict) else f for f in t.get("contentFields") or []} | set(t.get("collections") or [])
    return not [k for k in props if k not in NOT_DESIGN and k not in content]


IMAGE_CARDS = {"mediaTop", "photoOverlay", "dateTile", "profile"}  # record card types that draw a photo


def image_problems(where, props, client, needs_image=False, tokens=False):
    """A sample or placeholder image must be a packaged FlowToolKit demo asset (or the organization's own, from site.json assets), and must
    draw: a block or record card reads imageAsset only when imageSource is "asset" (else it draws no photo)"""
    found = []
    for source, asset, url in (("imageSource", "imageAsset", "imageUrl"), ("backgroundImageSource", "backgroundImageAsset", "backgroundImageUrl")):
        name, link = props.get(asset), props.get(url) or (props.get("image") if asset == "imageAsset" else None)
        if name:
            bare = re.sub(r"^FlowToolKit__", "", str(name))
            if not str(name).startswith("FlowToolKit__") and bare not in client and name not in client:
                found.append(f"{where} {asset} {name} is not a package demo asset or one of the site's own assets")
            if props.get(source) != "asset":
                found.append(f"{where} sets {asset} without {source} \"asset\", so it draws no photo")
        elif merge_token(link):
            if not tokens:
                found.append(f"{where} takes its photo from a record field ({link}) on a page with no record")
        elif link and not str(link).startswith(("resource:", "/_blob/")):
            found.append(f"{where} {url if props.get(url) else 'image'} {link} is not a package demo asset")
    if needs_image and not any(props.get(k) for k in ("imageAsset", "imageUrl", "image")):
        found.append(f"{where} has no image")
    return found


def house_checks(page, schema, client=frozenset(), record_page=False):
    """The mechanical half of references/house-rules.md; each row is (check, passes, what to fix)"""
    sections = page.get("sections") or []
    blocks = [(section_id(s, n), i.get("props") or {}) for n, s in enumerate(sections, 1) for i in items_of(s) if i.get("kind") == "block"]
    heroes = [(sid, p) for sid, p in blocks if p.get("sectionType") == "hero" and p.get("heroLayout") != "band"]
    opening_id = section_id(sections[0], 1) if sections else None
    opening = next((p for sid, p in heroes if sid == opening_id), None)
    band = lambda p: photo_band(p, record_page)
    thin = []
    for sid, p in heroes:
        need = 3 if sid == opening_id else 2
        got = hero_range(p)
        if len(got) < need:
            thin.append(f"{sid} uses {len(got)} of tags, a longer description, two buttons, a secondary image, facts or stats (needs {need})")
    bands = [sid for sid, p in blocks if sid != opening_id and band(p) and p.get("width") == "full"]
    text_tabs = [f"{section_id(s, n)} tab {t.get('tabName')}" for n, s in enumerate(sections, 1) for c in s.get("columns") or [] for i in c.get("items") or []
                 for t in i.get("tabs") or [] if all(x.get("kind") in TEXT_KINDS for x in t.get("items") or [])]
    plain_blocks = [f"{sid} {p.get('sectionType')}" for sid, p in blocks if at_defaults(p, schema)]
    cards = [(s.get("_design") or {}).get("designCard") for s in sections if (s.get("_design") or {}).get("designCard")]
    repeated = sorted({c for c in cards if cards.count(c) > 1 and c != "HTML Editor"})
    images = [p for sid, b in blocks for p in image_problems(sid, b, client, b.get("sectionType") == "recordCard" and b.get("cardType") in IMAGE_CARDS, record_page)]
    images += [p for n, s in enumerate(sections, 1) for i in items_of(s) if i.get("kind") == "repeater"
               for r, rec in enumerate((i.get("_design") or {}).get("sampleRecords") or [], 1)
               for p in image_problems(f"{section_id(s, n)} record {r}", rec, client, i.get("cardType") in IMAGE_CARDS, True)]
    return [
        ("Opening hero on a photo with a scrim", bool(opening and band(opening)),
         "" if opening and band(opening) else "set backgroundImageAsset (a packaged FlowToolKit__Background_* photo) and backgroundOverlay tint, side or bottom"),
        ("Heroes use the range", not thin, "; ".join(thin)),
        ("A full-bleed photo band below the hero", bool(bands), ", ".join(bands) or "add one: width full, backgroundImageAsset, backgroundOverlay"),
        ("Tabs carry rich content, not only text", not text_tabs, ", ".join(text_tabs)),
        ("No block left at its defaults", not plain_blocks, ", ".join(plain_blocks)),
        ("Designs vary down the page", not repeated, ", ".join(f"{c} used twice" for c in repeated)),
        ("Sample and placeholder images are package demo assets, and draw", not images, "; ".join(images)),
    ]


def markup_rows(site, pages):
    """The HTML Editor and Rich Content warnings, one checklist row per page"""
    rows = []
    for entry, page in pages:
        notes = []
        for sid, item in markup_items(page):
            notes += htmlcheck.check_markup(item.get("richTextValue"), sid, audiences(site, entry), site.get("palette"), item["kind"])[1]
        rows.append(("Custom markup is safe for every audience and fits a phone", not notes, "; ".join(notes)))
    return rows


def jobs_inner(site, pages, limits, schema=None, client=frozenset()):
    rows = []
    for entry, page in pages:
        for n, s in enumerate(page.get("sections") or [], 1):
            d = s.get("_design") or {}
            kinds = ", ".join((i.get("props") or {}).get("sectionType") or i.get("kind") for i in items_of(s))
            widths = "/".join(str(c.get("width")) for c in s.get("columns") or [])
            rows.append(([esc(entry.get("title") or entry["urlName"]), esc(section_id(s, n)), esc(d.get("job") or "NOT NAMED"), esc(d.get("designCard") or "NOT NAMED"),
                          esc(kinds), widths, str(len(confirms(s)) or "")], "#fde2e2" if not d.get("job") or not d.get("designCard") else "#ffffff"))
        for region in ("header", "footerContent"):
            for s in page.get(region) or []:
                rows.append(([esc(entry.get("title") or entry["urlName"]), region, esc((s.get("_design") or {}).get("job") or "Shared"), "", "", "", ""], "#f3f3f3"))
    checks = []
    for (entry, page), markup_row in zip(pages, markup_rows(site, pages)):
        for name, ok, note in handoff(page, limits) + house_checks(page, schema or {}, client, bool(entry.get("recordObject"))) + [markup_row]:
            checks.append(([esc(entry.get("title") or entry["urlName"]), esc(name), "Pass" if ok else "Fix", esc(note)], "#ffffff" if ok else "#fde2e2"))
    inner = (f'<h1 style="margin: 0; font-size: 44px">Section jobs and the handoff checklist</h1>'
             f'<p style="margin: 0; font-size: 14px">Every section, its job and its design card. Pin a comment on a section in its page artboard; the id on its tag names it in page.json.</p>'
             + table(["Page", "Section id", "Job", "Design card", "Components", "Columns", "To confirm"], rows)
             + h2("Handoff checklist (Choosing blocks and the site house rules)") + table(["Page", "Check", "Result", "Note"], checks))
    height = 420 + 40 * len(rows) + 38 * len(checks)
    return inner, height, checks


def collect_inner(pages):
    rows = []
    for entry, page in pages:
        title = esc(entry.get("title") or entry["urlName"])
        for thing in (page.get("_design") or {}).get("contentToCollect") or []:
            rows.append(([title, "page", esc(thing)], "#ffffff"))
        for n, s in enumerate(page.get("sections") or [], 1):
            for c in confirms(s):
                rows.append(([title, esc(section_id(s, n)), esc(c)], "#fff8c4"))
            for r in sample_needed(s, False):
                rows.append(([title, esc(section_id(s, n)), esc(f"Sample records for the {r.get('cardType') or 'record'} repeater on {r.get('object') or '[object]'}")], "#fde2e2"))
    inner = (f'<h1 style="margin: 0; font-size: 44px">Content to collect</h1>'
             f'<p style="margin: 0; font-size: 14px">{len(rows)} items: photos, copy and numbers still owed, every [CONFIRM: ...] in the copy (yellow), and what a repeater needs (red).</p>'
             + table(["Page", "Where", "What"], rows or [(["", "", "Nothing outstanding"], "#ffffff")]))
    height = 320 + 40 * max(len(rows), 1)
    return inner, height, len(rows)


# ---------- Images, the local render (heights, console errors, broken images) ----------

def asset_resolver(site, kit):
    client = site.get("assets") or {}

    def ds_path(name):
        bare = re.sub(r"^FlowToolKit__", "", str(name))
        if bare in ASSET_ALIASES:
            return "assets/" + ASSET_ALIASES[bare]
        for rx, folder, ext in ASSET_GROUPS:
            if rx.search(bare):
                return f"assets/{folder}/{bare}{ext}"
        return None

    def url(name):
        """An image's url on the canvas: its upload. Not uploaded yet, a package image names its kit path, which the canvas does not
        serve: the generator lists it in uploads.json and site_review.cjs site fails it"""
        if str(name).startswith(("/_blob/", "http")):
            return name
        bare = re.sub(r"^FlowToolKit__", "", str(name))
        if bare in client or name in client:
            return (client.get(bare) or client.get(name)).get("blob") or ""
        path = ds_path(name)
        return f"ds/{NS}/{path}" if path else ""
    return ds_path, url


def image_names(site, trees):
    """Every image name the trees and the brand use: packaged ones (FlowToolKit__*), resource: files, and the organization's own
    images by their name in site.json assets"""
    names, own = set(), set(site.get("assets") or {})
    for value in list(trees) + [site.get("brand") or {}]:
        for s in strings(value):
            if s in own:
                names.add(s)
            names.update(m.group(0) for m in re.finditer(r"FlowToolKit__[A-Za-z0-9_]+", s))
            names.update("resource:" + m.group(1) for m in re.finditer(r"resource:([A-Za-z0-9_./-]+)", s))
    return names


def local_image(name, ds_path, kit, site, site_dir):
    """The local file for one image name: the organization's own (site.json assets file) first, then the kit's copy"""
    key = re.sub(r"^FlowToolKit__", "", name)
    entry = (site.get("assets") or {}).get(key) or (site.get("assets") or {}).get(name) or {}
    if entry.get("file") and (site_dir / entry["file"]).exists():
        return site_dir / entry["file"]
    path = "assets/resources/" + name[len("resource:"):] if name.startswith("resource:") else ds_path(name)
    return kit.file(path) if path else None


def used_images(site, trees, ds_path, kit, site_dir):
    """Every image the artboards draw that the canvas does not hold yet, and the ones found nowhere.

    The Design canvas serves an image only as an upload (`/_blob/<id>`), never as a file copied from a design system: a package
    photo copied into project/ds/sb/assets/ draws as a broken image on the live canvas, although a local check passes. So each
    package image a page or the brand board uses is listed for upload by its bare name (a `resource:` file as
    "resource:<path>"), with the kit's copy as the file; so is an image in site.json assets with a file and no blob yet.
    Returns (uploads [{name, source}], missing names)."""
    assets = site.get("assets") or {}
    uploads, missing = {}, []
    for n in sorted(image_names(site, trees)):
        key = re.sub(r"^FlowToolKit__", "", n)
        if (assets.get(key) or assets.get(n) or {}).get("blob"):
            continue
        file = local_image(n, ds_path, kit, site, site_dir)
        if file:
            uploads[key] = str(file.resolve())
        elif key not in assets and n not in assets:
            missing.append(n)
    for key, entry in assets.items():
        if not entry.get("blob") and entry.get("file") and (site_dir / entry["file"]).exists():
            uploads.setdefault(key, str((site_dir / entry["file"]).resolve()))
    return [{"name": k, "source": f} for k, f in sorted(uploads.items())], missing


def stage_uploads(design, uploads):
    """Copy each image to upload into design/uploads/ (kept out of version control), so one Artifact call sends them all: the
    tool takes a file_paths batch only from the session's working folder, and the kit may sit elsewhere"""
    folder = design / "uploads"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / ".gitignore").write_text("*\n")
    for u in uploads:
        ext = pathlib.Path(u["source"]).suffix
        name = re.sub(r"[^A-Za-z0-9_.-]+", "-", u["name"])
        staged = folder / (name if name.lower().endswith(ext.lower()) else name + ext)
        shutil.copyfile(u["source"], staged)
        u["file"] = str(staged.resolve())
    return uploads


def record_blobs(site_dir, returned):
    """Write the /_blob/ urls an upload returned into site.json assets. `returned` maps each design/uploads.json name, or the file
    uploaded (matched by its file name), to the url the Artifact tool returned. A package image keeps no file path (the kit is
    found again on every run); the organization's own image keeps its file."""
    site_file = pathlib.Path(site_dir) / "site.json"
    site = json.loads(site_file.read_text())
    listed = json.loads((pathlib.Path(site_dir) / "design/uploads.json").read_text()).get("files") or []
    by_key = {}
    for u in listed:
        by_key.update({u["name"]: u, u["file"]: u, pathlib.Path(u["file"]).name: u})
    assets = site.setdefault("assets", {})
    for key, url in returned.items():
        if not str(url).startswith("/_blob/"):
            raise SiteError(f"{key}: {url!r} is not a /_blob/ url; give each upload's url exactly as the Artifact tool returned it")
        u = by_key.get(key) or by_key.get(pathlib.Path(key).name)
        if not u:
            raise SiteError(f"{key} is not in design/uploads.json; rerun the generator, then upload what it lists")
        assets[u["name"]] = dict(assets.get(u["name"]) or {}, blob=url)
    site_file.write_text(json.dumps(site, indent=2, ensure_ascii=False) + "\n")
    return len(returned)


def measure(kit, renders, out):
    """Render every artboard's tree with the kit's bundle at its width (site_review.cjs measure): heights, console errors, broken images"""
    node = shutil.which("node")
    if not node:
        return None, "node not found"
    job = out / "measure.json"
    job.write_text(json.dumps({"roots": [str(r) for r in kit.roots], "boards": renders}))
    try:
        proc = subprocess.run([node, str(HERE / "site_review.cjs"), "measure", str(job), str(out / "heights.json")],
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return None, "the render took over ten minutes"
    finally:
        job.unlink(missing_ok=True)
    if proc.returncode not in (0, 1) or not (out / "heights.json").exists():
        return None, (proc.stderr or proc.stdout).strip()[-400:]
    return json.loads((out / "heights.json").read_text()), None


def estimate(page, width):
    total = 0
    for s in (page.get("header") or []) + (page.get("sections") or []) + (page.get("footerContent") or []):
        tallest = max((sum(EST.get((i.get("props") or {}).get("sectionType"), 520) for i in c.get("items") or []) for c in s.get("columns") or []), default=200)
        total += tallest if width >= 1024 else tallest * 2
    return total + (200 if page.get("layout") == "customerService" else 0)


# ---------- Support files, publish batches and the fallback page ----------

def tokens_css(kit):
    tokens = json.loads(kit.file("tokens.json").read_text())
    lines = [f"--{t['name']}: {t['value']['light'] if isinstance(t['value'], dict) else t['value']};" for t in (tokens.get("color") or {}).get("tokens") or []]
    for family in ("spacing", "radius", "sizing", "shadow"):
        lines += [f"--{t['name']}: {t['value']};" for t in (tokens.get(family) or {}).get("tokens") or []]
    return re.sub(r"\{([A-Za-z0-9_.-]+)\}", r"var(--\1)", ":root{" + "".join(lines) + "}")


def site_js(image_urls, asset_base):
    """Every image, packaged or the organization's, comes from image_urls (uploads on the canvas, data urls in review.html)"""
    return ("// Every image, packaged or the organization's own, is an upload to the canvas (site.json assets)\n"
            f"SB.assetBase = {asset_base};\n(function () {{\n  var client = {json.dumps(image_urls)};\n  var base = SB.assetUrl;\n"
            "  SB.assetUrl = function (name) { var bare = String(name || '').replace(/^FlowToolKit__/, ''); return client[bare] || client[name] || base(name); };\n"
            "  window.SiteBlocksAssetUrl = SB.assetUrl;\n  var resource = SB.resourceUrl;\n"
            "  SB.resourceUrl = function (path) { return client['resource:' + String(path || '').replace(/^\\/+/, '')] || resource(path); };\n"
            "  window.SiteBlocksResourceUrl = SB.resourceUrl;\n})();\n"
            "// The canvas wraps each mounted component in a display: contents div; give SB.Section its Columns as direct children, as the site has them\n"
            "(function () {\n  var Section = SB.Section;\n  if (!Section || Section.canvasAdapter) return;\n"
            "  var unwrap = function (c) { var inner = c && c.type === 'div' && c.props && c.props.children; return inner && inner.props && inner.props.columnWidth != null ? React.cloneElement(inner, { key: c.key }) : c; };\n"
            "  SB.Section = function (p) {\n"
            "    var kids = React.Children.map(p.children, unwrap);\n"
            "    return React.createElement(Section, Object.assign({}, p, { children: kids }));\n  };\n"
            "  SB.Section.canvasAdapter = true;\n})();\n")


def publish_batches(design, files, stale, mode, ds_url, kit, lwr):
    """design/publish-batches.json: the publish as `files` maps (root design/), in order, each within the mode's per-call limit.

    code: the design system's code and tokens copied server side from the person's own Site Blocks artifact. chat: written from
    the kit into design/project/ds/sb/ first. canvas.json goes in the last batch, so the canvas opens on a complete set.
    Images are never in a batch: they are uploads (uploads.json). Returns None when code mode has no design system link."""
    entries = [(f, f) for f in files]
    ds = DS_FILES + ([LWR_CSS] if lwr else []) + ["tokens.json"]
    if mode == "code":
        if not ds_url:
            (design / "publish-batches.json").unlink(missing_ok=True)
            return None
        entries += [(f"project/ds/{NS}/{f}", {"artifact": ds_url, "path": f"project/{f}"}) for f in ds]
    else:
        for f in ds:
            target = design / "project" / "ds" / NS / f
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kit.file(f), target)
            entries.append((f"project/ds/{NS}/{f}", f"project/ds/{NS}/{f}"))
    entries += [(f"project/{name}", None) for name in stale]
    size = BATCH[mode] - 1
    batches = [dict(entries[i:i + size]) for i in range(0, len(entries), size)] or [{}]
    batches[-1]["project/canvas.json"] = "project/canvas.json"
    out = {"mode": mode, "root": str(design.resolve()), "per_call": BATCH[mode], "design_system": ds_url, "batches": batches}
    (design / "publish-batches.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


STANDALONE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{fonts}<style>{tokens}</style>
<style>{bundle_css}</style>
<style>body{{margin:0;background:#e9e9e9;font-family:system-ui,sans-serif}}
.sr-bar{{position:relative;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;padding:10px 16px;background:#181818;color:#fff;font-size:14px}}
.sr-bar a{{color:#9fd4ff}}.sr-bar a[aria-current]{{color:#fff;font-weight:600;text-decoration:none}}
.sr-board{{margin:24px 0 48px}}.sr-board>h2{{font-size:16px;font-weight:600;color:#353535;margin:0 16px 8px}}
.sr-scroll{{overflow-x:auto;padding:0 16px}}.sr-frame{{display:inline-block;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.2)}}</style>
<script>{react}</script>
<script>{react_dom}</script>
<script>{icons}</script>
<script>{illustrations}</script>
<script>{bundle_js}</script>
<script>{site_js}</script>
</head>
<body>
<nav class="sr-bar" aria-label="Review width"><strong>{title_text}</strong><span>The same Site Blocks components as the review canvas, in one file. Nothing here is the live site.</span>
<a href="#w=1280" data-w="1280">Desktop 1280</a><a href="#w=390" data-w="390">Phone 390</a></nav>
<div id="boards"></div>
<script>
var BOARDS = {boards};
var STATIC = {static};
var width = /w=390/.test(location.hash) ? 390 : 1280;
document.querySelectorAll('.sr-bar a[data-w]').forEach(function (a) {{
  if (+a.getAttribute('data-w') === width) a.setAttribute('aria-current', 'true');
  a.addEventListener('click', function () {{ setTimeout(function () {{ location.reload(); }}, 0); }});
}});
SB.previewAt(width);
var h = React.createElement;
function el(n, key) {{
  var kids = (n.k || []).map(function (k, i) {{ return el(k, key + '.' + i); }});
  if (n.c === 'div') {{ var p = Object.assign({{ key: key }}, n.p); delete p.tag; return h.apply(null, ['div', p].concat(kids)); }}
  var C = n.c.split('.').slice(1).reduce(function (o, k) {{ return o && o[k]; }}, window.SB);
  if (!C) return h('div', {{ key: key, style: {{ color: '#b3261e' }} }}, 'Unknown component ' + n.c);
  return h.apply(null, [C, Object.assign({{ key: key }}, n.p)].concat(kids));
}}
var root = document.getElementById('boards');
function frame(b) {{
  var sec = document.createElement('section'); sec.className = 'sr-board'; sec.setAttribute('data-board', b.name);
  sec.innerHTML = '<h2></h2><div class="sr-scroll"><div class="sr-frame"></div></div>';
  sec.querySelector('h2').textContent = b.title; root.appendChild(sec); return sec.querySelector('.sr-frame');
}}
var shown = STATIC.slice(0, 1).concat(BOARDS.filter(function (b) {{ return b.w === width; }}), STATIC.slice(1));
shown.forEach(function (b, i) {{
  var box = frame(b);
  if (b.html !== undefined) {{ box.innerHTML = b.html; return; }}
  box.style.width = b.w + 'px';
  box.innerHTML = b.bar;
  var mount = document.createElement('div'); box.appendChild(mount);
  ReactDOM.createRoot(mount).render(el(b.tree, 'b' + i));
}});
</script>
</body>
</html>
"""


def icon_subset(kit, trees):
    """Only the icons the pages name, plus every icon the bundle draws on its own"""
    text = kit.file("components/lib/slds-icons-2.30.7.js").read_text()
    start = text.index("window.SLDSIcons=") + len("window.SLDSIcons=")
    lib = json.loads(text[start:].rstrip().rstrip(";"))
    bundle = kit.file("components/bundle.js").read_text()
    wanted = set(re.findall(r"\b(?:utility|standard|custom|action|doctype):[a-z0-9_]+", bundle + json.dumps(trees)))
    return "window.SLDSIcons=" + json.dumps({k: v for k, v in lib.items() if k in wanted}, separators=(",", ":")) + ";"


def data_url(path):
    kind = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{kind};base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def tree_json(node):
    """A drawn tree for review.html: section tags become plain markup the page shows above each section"""
    out = {"c": node["c"], "p": dict(node["p"]), "k": [tree_json(k) for k in node["k"]]}
    if node.get("tag"):
        out["k"].insert(0, {"c": "div", "p": {"dangerouslySetInnerHTML": {"__html": tag_html(node["tag"])}}, "k": []})
    return out


def write_standalone(path, site, page_boards, static_boards, kit, site_dir, ds_path, fonts_href):
    """design/review.html: every artboard in one self-contained page (React, the bundle, its styles, only the icons used and the
    images drawn, inlined). For accounts without the Design type, and for a quick look in any browser."""
    images = {}
    for n in image_names(site, [b["tree"] for b in page_boards]):
        file = local_image(n, ds_path, kit, site, site_dir)
        if file:
            images[n if n.startswith("resource:") else re.sub(r"^FlowToolKit__", "", n)] = data_url(file)
    boards = [dict(b, tree=tree_json(b["tree"])) for b in page_boards]
    safe = lambda s: s.replace("</script", "<\\/script")
    page = STANDALONE.format(
        title=esc(site.get("canvasTitle") or f"{site.get('title', 'Site')} site review"), title_text=esc(site.get("title", "Site review")),
        fonts=f'<link rel="stylesheet" href="{esc(fonts_href)}">\n' if fonts_href else "",
        tokens=tokens_css(kit), bundle_css=kit.file("components/bundle.css").read_text().replace("</style", "<\\/style"),
        react=safe(kit.file(REACT_FILES[0]).read_text()), react_dom=safe(kit.file(REACT_FILES[1]).read_text()),
        icons=safe(icon_subset(kit, [b["tree"] for b in page_boards])), illustrations=safe(kit.file("components/lib/ftk-illustrations.js").read_text()),
        bundle_js=safe(kit.file("components/bundle.js").read_text()), site_js=safe(site_js(images, json.dumps("./"))),
        boards=safe(json.dumps(boards, ensure_ascii=False)), static=safe(json.dumps(static_boards, ensure_ascii=False)))
    path.write_text(page)
    return len(page.encode())


# ---------- main ----------

def build(site_dir, kit_arg=None, do_measure=True, mode="code", config_arg=None):
    kit, schema, limits = find_kit(kit_arg)
    site_dir = pathlib.Path(site_dir).resolve()
    site, pages = load_site(site_dir)
    config, _ = find_config(site_dir, config_arg)
    ds = design_system(config)
    warnings = [w for entry, page in pages for w in validate(entry["urlName"], page, schema, site, entry)]
    palette = site.get("palette") or {}
    ds_path, asset_url = asset_resolver(site, kit)
    lwr = site.get("siteType") == "lwr" and site.get("drawAs") == "lwr"
    fonts_href = ((site.get("brand") or {}).get("fonts") or {}).get("href")
    design = site_dir / "design"
    project = design / "project"
    project.mkdir(parents=True, exist_ok=True)

    # Every page artboard: desktop and phone, plus its states (desktop)
    boards_src = []  # (file, title, width, tree, entry, page)
    for entry, page in pages:
        title = entry.get("title") or page.get("title") or entry["urlName"].replace("-", " ").title()
        tree = page_tree(page, palette)
        boards_src.append((f"{entry['urlName']}.dc.html", f"{title} (desktop {DESKTOP})", DESKTOP, tree, entry, page))
        boards_src.append((f"{entry['urlName']}-phone.dc.html", f"{title} (phone {PHONE})", PHONE, tree, entry, page))
        for state in (page.get("_design") or {}).get("states") or []:
            variant = dict(page, sections=state["sections"]) if state.get("sections") else tab_state(page, state) if state.get("activeTab") else page
            boards_src.append((f"{entry['urlName']}-{slug(state['id'])}.dc.html", f"{title}: {state['title']}", DESKTOP,
                               page_tree(variant, palette, bool(state.get("emptyRepeaters"))), entry, variant))

    heights, why = (None, "skipped (--no-measure)")
    if do_measure:
        assets = {}
        for n in image_names(site, [b[3] for b in boards_src]):
            file = local_image(n, ds_path, kit, site, site_dir)
            if file:
                assets[re.sub(r"^FlowToolKit__", "", n)] = str(file.resolve())
        heights, why = measure(kit, [{"file": f, "width": w, "tree": t, "fonts": fonts_href, "assets": assets} for f, _, w, t, _, _ in boards_src], design)
    if heights is None:
        warnings.append(f"Heights estimated, not measured ({why}); look at the bottom of every artboard")

    boards, order, notes = {}, [], {}
    inner, bh = brand_inner(site, asset_url)
    (project / "Main.dc.html").write_text(static_artboard(f"{site.get('title', 'Site')} brand", 1600, bh, inner, fonts_href))
    boards["Main.dc.html"] = {"x": 0, "y": 0, "w": 1600, "h": bh, "title": f"{site.get('title', 'Site')} brand: selected palette, fonts, logo and tone"}
    order.append("Main.dc.html")
    notes["t_brand"] = {"x": 0, "y": -300, "text": "Brand", "kind": "title1", "maxW": 1600}
    y = bh + 120 + 300
    errors, standalone_pages = [], []
    for entry, page in pages:
        title = entry.get("title") or page.get("title") or entry["urlName"]
        row = [b for b in boards_src if b[4] is entry]
        x, row_h = 0, 0
        notes[f"t_{slug(entry['urlName']).replace('-', '_')}"] = {"x": 0, "y": y - 300, "text": f"{title} · {entry.get('route') or '/' + entry['urlName']}", "kind": "title1", "maxW": 3000}
        for file, btitle, width, tree, _, variant in row:
            m = (heights or {}).get(file) or {}
            errors += [f"{file}: {e}" for e in m.get("errors") or []] + [f"{file}: broken image {b}" for b in m.get("broken") or []]
            h = int(m["height"]) + BAR + 40 if m.get("height") else estimate(variant, width) + BAR
            if h > CAP:
                if m.get("height"):
                    warnings.append(f"{file}: {h}px is taller than the canvas takes ({CAP}px); move sections into a state artboard")
                h = CAP
            (project / file).write_text(page_artboard(title, entry, tree, width, h, lwr, fonts_href))
            boards[file] = {"x": x, "y": y, "w": width, "h": h, "title": btitle}
            standalone_pages.append({"name": file, "title": btitle, "w": width, "tree": tree, "bar": page_bar(title, entry, width)})
            order.append(file)
            x += width + 80
            row_h = max(row_h, h)
        d = page.get("_design") or {}
        text = "\n".join(["Design notes"] + [f"- {n}" for n in d.get("notes") or []] +
                         [f"- {section_id(s, n)}: {len(confirms(s))} to confirm" for n, s in enumerate(page.get("sections") or [], 1) if confirms(s)] +
                         (["- Shared header and footer: a change here changes every page"] if page.get("header") or page.get("footerContent") or page.get("layout") == "customerService" else []))
        notes[f"n_{slug(entry['urlName']).replace('-', '_')}"] = {"x": x, "y": y, "text": text, "w": 700, "fill": "orange"}
        y += row_h + 120 + 300

    client = frozenset(site.get("assets") or {})
    for entry, page in pages:
        warnings += [f"{entry['urlName']}: {name}: {note}" for name, ok, note in house_checks(page, schema, client, bool(entry.get("recordObject"))) if not ok]
    warnings += [f"{entry['urlName']}: {note}" for (entry, _), (_, ok, note) in zip(pages, markup_rows(site, pages)) if not ok]
    jinner, jh, checks = jobs_inner(site, pages, limits, schema, client)
    (project / "SectionJobs.dc.html").write_text(static_artboard("Section jobs", 1800, jh, jinner))
    boards["SectionJobs.dc.html"] = {"x": 0, "y": y, "w": 1800, "h": min(jh, CAP), "title": "Section jobs and handoff checklist"}
    cinner, ch, collect = collect_inner(pages)
    (project / "ContentToCollect.dc.html").write_text(static_artboard("Content to collect", 1400, ch, cinner))
    boards["ContentToCollect.dc.html"] = {"x": 1880, "y": y, "w": 1400, "h": min(ch, CAP), "title": "Content to collect"}
    order += ["SectionJobs.dc.html", "ContentToCollect.dc.html"]
    notes["t_end"] = {"x": 0, "y": y - 300, "text": "Section jobs and content to collect", "kind": "title1", "maxW": 3280}

    # Support files: the design system's tokens as CSS, the site's image map, the preview widths
    (project / "sb-tokens.css").write_text(tokens_css(kit) + "\n")
    blobs = {k: v["blob"] for k, v in (site.get("assets") or {}).items() if v.get("blob")}
    (project / "sb-site.js").write_text(site_js(blobs, f"new URL('ds/{NS}/', document.baseURI).href"))
    for w in (DESKTOP, PHONE):
        (project / f"sb-{w}.js").write_text(f"// Lay the page out at {w}px and settle every width media query there (the Page README, Preview at desktop width)\nSB.previewAt({w});\n")

    canvas_path = project / "canvas.json"
    previous = json.loads(canvas_path.read_text()) if canvas_path.exists() else {}
    created = previous.get("createdOnFiles") or {"v": 1, "at": NOW}
    kept_notes = {k: v for k, v in (previous.get("notes") or {}).items() if not re.match(r"^(t|n)_", k)}  # notes people drew stay
    systems = [s for s in previous.get("designSystems") or [] if s.get("namespace") != NS]
    old = next((s for s in previous.get("designSystems") or [] if s.get("namespace") == NS), {})
    systems.append({"title": ds.get("title") or "FlowToolKit Site Blocks", "namespace": NS, "artifact": ds.get("url"),
                    "version": ds.get("kit_version") or old.get("version"), "copiedAt": old.get("copiedAt") or created["at"]})
    # Keep the index keys this run does not own: the canvas editor adds some of its own
    canvas = {**previous, "v": 3, "createdOnFiles": created, "title": previous.get("title") or site.get("canvasTitle") or f"{site.get('title', 'Site')} site review",
              "launch": previous.get("launch") or {"view": "canvas"}, "pages": previous.get("pages") or [], "boards": boards, "order": order,
              "notes": {**kept_notes, **notes}, "designSystems": systems}
    canvas_path.write_text(json.dumps(canvas, indent=1) + "\n")
    stale = sorted(p.name for p in project.glob("*.dc.html") if p.name not in boards)
    for name in stale:
        (project / name).unlink()

    # the drawn trees too: a record-field photo is drawn with a package stand-in the pages never name
    uploads, missing = used_images(site, [p for _, p in pages] + [b[3] for b in boards_src], ds_path, kit, site_dir)
    files = [f"project/{p.name}" for p in sorted(project.iterdir()) if p.is_file() and p.name != "canvas.json"]
    publish = publish_batches(design, files, stale, mode, ds.get("url"), kit, lwr)
    paths = [u["file"] for u in stage_uploads(design, uploads)]
    (design / "uploads.json").write_text(json.dumps({"canvas": site.get("canvasUrl"), "files": uploads,
                                                     "file_paths": [paths[i:i + 25] for i in range(0, len(paths), 25)]}, indent=1) + "\n")
    if uploads:
        warnings.append(f"{len(uploads)} images are not on the canvas yet and draw broken until uploaded: {', '.join(u['name'] for u in uploads)}. "
                        "Upload design/uploads.json file_paths to the canvas (Artifact publish, url the canvas, asset: true, file_paths, 25 a call), "
                        "then rerun with --record-blobs before publishing (references/canvas.md)")
    warnings += [f"Image not in the design system and not in site.json assets: {m}" for m in missing]
    def inline_url(name):
        file = None if str(name).startswith(("/_blob/", "http")) else local_image(str(name), ds_path, kit, site, site_dir)
        return data_url(file) if file else ""
    statics = [{"name": "Main.dc.html", "title": boards["Main.dc.html"]["title"], "html": static_body(1600, bh, brand_inner(site, inline_url)[0])},
               {"name": "SectionJobs.dc.html", "title": "Section jobs and handoff checklist", "html": static_body(1800, jh, jinner)},
               {"name": "ContentToCollect.dc.html", "title": "Content to collect", "html": static_body(1400, ch, cinner)}]
    size = write_standalone(design / "review.html", site, standalone_pages, statics, kit, site_dir, ds_path, fonts_href)
    if size > 15_000_000:
        warnings.append(f"review.html is {size // 1_000_000} MB, near the 16 MB page limit; fewer photos keep it smaller")
    if publish is None:
        warnings.append("No FlowToolKit Site Blocks design system link in flow-tool-kit.json (design_systems.site_blocks.url): run ftk-start's design "
                        "system step to install your own copy, then rerun. review.html is written meanwhile; in chat, use --mode chat")
    failing = [c for c in checks if c[0][2] == "Fix"]
    print(f"pages {len(pages)} artboards {len(boards)} sections {sum(len(p.get('sections') or []) for _, p in pages)} "
          f"to-collect {collect} handoff-fixes {len(failing)} errors {len(errors)} measured {'yes' if heights else 'no'} "
          f"publish {'%d batch(es), %s mode' % (len(publish['batches']), mode) if publish else 'waiting for a design system link'}")
    for line in warnings + errors:
        print("  " + line)
    return {"boards": boards, "errors": errors, "warnings": warnings, "publish": publish, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--site", default=".", help="the site folder (_site/<slug>) holding site.json and pages/")
    parser.add_argument("--mode", choices=("code", "chat"), default="code",
                        help="code: Claude Code copies the design system server side; chat: files from the bundled kit, 16 a call")
    parser.add_argument("--kit", help="the Site Blocks kit folder (default: site-blocks/ in the plugin's ftk-design-system skill)")
    parser.add_argument("--config", help=f"the project config (default: {CONFIG_NAME} in the site folder or a folder above it)")
    parser.add_argument("--no-measure", action="store_true", help="estimate heights instead of rendering each artboard here")
    parser.add_argument("--record-blobs", metavar="JSON", help="a file or inline JSON object mapping each design/uploads.json name or file to the "
                        "/_blob/ url its upload returned; written into site.json assets before the build")
    args = parser.parse_args(argv)
    if args.record_blobs:
        raw = pathlib.Path(args.record_blobs).read_text() if pathlib.Path(args.record_blobs).is_file() else args.record_blobs
        print(f"recorded {record_blobs(args.site, json.loads(raw))} blobs in site.json")
    result = build(args.site, args.kit, not args.no_measure, args.mode, args.config)
    if result["errors"]:
        return 1
    return 3 if result["publish"] is None else 0


if __name__ == "__main__":
    sys.exit(main())
