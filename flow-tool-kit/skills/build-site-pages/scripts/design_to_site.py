#!/usr/bin/env python3
"""A page designed with the Site Blocks design system, written as Experience Builder metadata.

    python3 design_to_site.py <page.json | block folder> --bundle <site bundle folder> --page <url-name> [--title T]
        [--blocks <dir>] [--record-page] [--record-object <Object> [--record-prefix <key prefix>]]
        [--entire-site] [--site-config site.json] [--palette palette.json] [--brand-kit brand-kit.json]
        [--footer-support c:<component>]...

The design is a page.json from design-to-blocks, or a block folder this script wrote with --blocks (NN-name.json files
and _sections.json; files sharing a number, 10a and 10b, are one section). --bundle is the retrieved site: an LWR
DigitalExperienceBundle folder (digitalExperiences/site/<Site1>) or an Aura ExperienceBundle folder
(experiences/<Site1>). The site type is read from the folder, and a design drawn for the other type is converted (the
blocks are the same; sections and standard components change shape).

Writes the page's view and route into the bundle, and with --blocks the page as a block folder. --record-object makes
the page an object's record page on LWR: its detail route and view, plus the list and related-list companions
Experience Builder needs beside it, every record-bound component on {!Route.recordId}.

--entire-site also writes the site-wide parts: the theme layout's header and footer, FlowToolKit LWR Support (and any
--footer-support component) in the theme footer, the branding set, the --ftk-site-* head tokens, the web font link,
the site access and the navigation menu. Their values come from, lowest first: --brand-kit (the brand kit's
brand-kit.json), --site-config (design-to-blocks' site.json: its palette, brand and shared page settings, plus title,
branding, headTokens and authenticationType), then the page itself. --palette turns "$name" values into colours.

Prints what it wrote, the deploy and publish commands, and every part of the design the site cannot take as drawn
(the deviations). Ids are stable: a rerun with the same inputs writes the same files. Python 3 standard library only.
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import site_views  # noqa: E402

COLLECTIONS = {"items", "bullets", "stats", "buttons", "badges", "tableColumns", "columns"}
# Key prefixes of the standard objects a site page is usually built for; any other standard object needs --record-prefix
STANDARD_PREFIXES = {"Account": "001", "Asset": "02i", "Contact": "003", "Opportunity": "006", "Case": "500"}
# The design's Page theme as the design system's head tokens; the branding set carries the text colour
THEME_TOKENS = {"brand": "--ftk-site-brand-override", "accent": "--ftk-site-accent-override",
                "font": "--ftk-site-font-override", "headingFont": "--ftk-site-heading-font-override"}
# On the free edition a record-bound block or repeater shows content only for these objects
FREE_EDITION_OBJECTS = {"Account", "Contact", "Case", "Lead", "FlowToolKit__Form_Template__c"}
# Props that name an image by its Asset File name
IMAGE_KEYS = re.compile(r"(?:Asset|iconImage|logo)$")
# Page settings design-to-blocks keeps once in site.json "page" and every page draws
SHARED_PAGE_KEYS = ("layout", "logo", "siteName", "navItems", "searchPlaceholder", "loginLabel", "footer", "theme", "maxWidth", "header", "footerContent")
# The head parts this script owns: one token style and one font link, replaced on every run (any earlier generator's
# <style data-...tokens> too, so tokens never stack)
TOKEN_STYLE = re.compile(r"<style data-[\w-]*tokens>.*?</style>\n?", re.S)
# The head markup refuses data-* attributes on <link>, so the font link is marked by the comment before it
FONT_MARK = "<!-- site-blocks web font -->"
FONT_LINK = re.compile(re.escape(FONT_MARK) + r"\n?<link[^>]*>\n?")
LWR_SUPPORT = "FlowToolKit:flowToolKitLwrSupport"
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("design", help="page.json from design-to-blocks, or a block folder written by --blocks")
parser.add_argument("--bundle", required=True, help="the retrieved site folder: digitalExperiences/site/<Site1> (LWR) or experiences/<Site1> (Aura)")
parser.add_argument("--page", required=True, help="the page's URL name, such as funding-opportunity; home fills the site's existing Home page")
parser.add_argument("--title")
parser.add_argument("--blocks", help="also write the page as a block folder here")
parser.add_argument("--record-page", action="store_true", help="bind every block to the page's record")
parser.add_argument("--record-object", help="LWR: build the page as this object's record page (detail route and view, list and related-list companions)")
parser.add_argument("--record-prefix", help="the object's three-character key prefix, when the bundle has no route for it and it is not a standard object in the built-in list")
parser.add_argument("--entire-site", action="store_true", help="also the theme layout, LWR Support, branding, head tokens, site access and navigation menu")
parser.add_argument("--site-config", help="site.json: design-to-blocks' palette, brand and shared page settings, plus title, branding, headTokens and authenticationType")
parser.add_argument("--palette", help="palette.json: named colours; any \"$name\" value in the design or the site config becomes the colour")
parser.add_argument("--brand-kit", help="brand-kit.json from the brand-kit skill: the palette, theme, fonts and button corners when nothing closer sets them")
parser.add_argument("--footer-support", action="append", default=[], metavar="c:<component>",
                    help="a support component of your own for the theme footer (one that imports the custom components a form loads by name); repeatable")
args = parser.parse_args()


def fail(message):
    sys.exit(f"design_to_site.py: {message}")


def read_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except FileNotFoundError:
        fail(f"{path} not found")
    except json.JSONDecodeError as error:
        fail(f"{path} is not valid JSON: {error}")


def brand_kit_values(kit):
    """brand-kit.json as palette names, a Page theme and branding values (the brand kit standard's keys)"""
    colors, fonts, style = kit.get("colors") or {}, kit.get("fonts") or {}, kit.get("style") or {}
    palette = {name: colors[name] for name in ("primary", "accent", "heading", "background") if colors.get(name)}
    if colors.get("primary"): palette["brand"] = colors["primary"]
    theme = {"brand": colors.get("primary"), "accent": colors.get("accent"),
             "font": fonts.get("bodyStack") or fonts.get("body"), "headingFont": fonts.get("headingStack") or fonts.get("heading")}
    branding = {"ButtonBorderRadius": style["buttonRadius"]} if style.get("buttonRadius") else {}
    return palette, {key: value for key, value in theme.items() if value}, branding, fonts.get("href")


kit = read_json(args.brand_kit) if args.brand_kit else {}
kit_palette, kit_theme, kit_branding, kit_font_href = brand_kit_values(kit)
raw_site_config = read_json(args.site_config) if args.site_config else {}
palette = {**kit_palette, **(raw_site_config.get("palette") or {}), **(read_json(args.palette) if args.palette else {})}


def resolve(value):
    """"$brand" becomes the palette colour, recursively; every other value is left alone ("$11.4M" is money, not a colour)."""
    if isinstance(value, str) and value.startswith("$") and value[1:] in palette: return palette[value[1:]]
    if isinstance(value, list): return [resolve(item) for item in value]
    if isinstance(value, dict): return {key: resolve(item) for key, item in value.items()}
    return value


def compact(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# A block folder is page.json written one file per item: the layout of each section is in _sections.json
def file_item(path):
    """One block file as a page.json item. A design block's file is its props (collections as arrays); "_kind" names any
    other item kind; "_component" names another LWR component with the rest of the file as its attributes; "_recordId"
    pins the item to one record (a featured record on a page that has no record of its own)."""
    data = resolve(read_json(path))
    record_id = data.pop("_recordId", None)
    if "_kind" in data:
        item = {"kind": data.pop("_kind"), **data}
    elif "_component" in data:
        item = {"kind": "component", "definition": data.pop("_component"), "attributes": data}
    else:
        item = {"kind": "block", "props": {key: compact(value) if key in COLLECTIONS and isinstance(value, list) else value for key, value in data.items()}}
    if record_id is not None: item["recordId"] = record_id
    return item


def read_block_folder(folder):
    layout = read_json(folder / "_sections.json") if (folder / "_sections.json").exists() else {}
    groups = {}
    for path in sorted(folder.glob("[0-9]*.json")):
        groups.setdefault(re.match(r"\d+", path.name).group(0), []).append(path.name)
    sections = []
    for group, names in groups.items():
        spec = layout.get(group) or {}
        columns = spec.get("columns") or [[name] for name in names]
        widths = spec.get("widths") or [str(12 // len(columns))] * len(columns)
        if len(widths) != len(columns) or sum(int(width) for width in widths) != 12:
            fail(f"{folder}/_sections.json group {group}: give one width per column, summing to 12")
        attributes = dict(spec.get("attributes") or {})
        if spec.get("maxWidth"): attributes["maxContentWidth"] = spec["maxWidth"]
        if spec.get("gutter"): attributes["sectionColumnGutterWidth"] = spec["gutter"]
        section = {"columns": [{"width": str(width), "items": [file_item(folder / name) for name in column]} for width, column in zip(widths, columns)]}
        if attributes: section = {"attributes": attributes, **section}
        sections.append(section)
    return {"sections": sections}


design_path = pathlib.Path(args.design)
design = read_block_folder(design_path) if design_path.is_dir() else resolve(read_json(design_path))
site_config = resolve(raw_site_config)
# design-to-blocks keeps the shared Page settings (header, footer, navigation, theme) in site.json "page" and the
# brand's theme in site.json "brand"; the page's own value wins, then site.json, then the brand kit
shared_page = site_config.get("page") or {}
for key in SHARED_PAGE_KEYS:
    if key not in design and key in shared_page: design[key] = shared_page[key]
site_brand = site_config.get("brand") or {}
site_fonts = site_brand.get("fonts") or {}
font_theme = {key: site_fonts[source] for key, source in (("font", "body_css"), ("headingFont", "heading_css")) if site_fonts.get(source)}
design["theme"] = {**kit_theme, **font_theme, **resolve(site_brand.get("theme") or {}), **(design.get("theme") or {})}
font_href = site_fonts.get("href") or kit_font_href
# The page's own entry in site.json pages: its title, its record object and who sees it, unless the command line says otherwise
page_entry = next((entry for entry in site_config.get("pages") or [] if entry.get("urlName") == args.page), {})
if not args.record_object and page_entry.get("recordObject"): args.record_object = page_entry["recordObject"]
edition = site_config.get("edition")
audience = page_entry.get("audience") or site_config.get("audiences") or []
if not design.get("sections"): fail(f"{design_path} has no sections")

bundle = pathlib.Path(args.bundle)
if not bundle.is_dir(): fail(f"--bundle {bundle} is not a folder: retrieve the site first")
lwr = (bundle / "sfdc_cms__view").exists()
if not lwr and not (bundle / "views").exists(): fail(f"--bundle {bundle} is neither an LWR site (sfdc_cms__view) nor an Aura site (views)")
site_name = bundle.name
title = args.title or design.get("title") or page_entry.get("title") or args.page.replace("-", " ").title()
make_id = site_views.id_maker(f"site-blocks/{site_name}/{args.page}")
record_page = args.record_page or bool(args.record_object)
deviations, notes = [], []


def all_items(sections):
    """(where, item) for every item of every section, tab contents included"""
    for s, section in enumerate(sections or [], 1):
        for c, column in enumerate(section.get("columns") or [], 1):
            stack = [(item, f"section {s}, column {c}") for item in column.get("items") or []]
            while stack:
                item, where = stack.pop(0)
                yield where, item
                for tab in item.get("tabs") or []: stack += [(child, f"{where}, tab {tab.get('tabName')}") for child in tab.get("items") or []]


def validate():
    """A listing that silently disappears is the usual surprise: a Repeater must arrive with its object and card,
    and a section's columns must add up to 12."""
    problems = []
    for region in ("sections", "header", "footerContent"):
        if not isinstance(design.get(region), list): continue
        for s, section in enumerate(design[region], 1):
            widths = [int(column.get("width") or 0) for column in section.get("columns") or []]
            if not 1 <= len(widths) <= 4 or sum(widths) != 12:
                problems.append(f"{region} section {s} has columns {widths}: give one to four columns adding up to 12.")
        for where, item in all_items(design[region]):
            if item.get("kind") == "repeater" and not (item.get("object") and item.get("card")):
                missing = " and ".join(key for key in ("object", "card") if not item.get(key))
                problems.append(f"Repeater in {'' if region == 'sections' else region + ' '}{where} has no {missing}: give it object, card, filter, sortField and emptyMessage in page.json, then run again.")
    for component in args.footer_support:
        if not re.fullmatch(r"[A-Za-z][\w]*:[a-z]\w*", component):
            problems.append(f"--footer-support {component!r} is not a component name such as c:customSectionsLwrSupport.")
    if problems: fail("\n".join(problems))


validate()


def image_names(value, found):
    """Every Asset File a page names (backgroundImageAsset, imageAsset, iconImage, logo), collections parsed"""
    if isinstance(value, str) and value[:1] in "[{":
        try: value = json.loads(value)
        except ValueError: return found
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and IMAGE_KEYS.search(key) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", item): found.add(item)
            else: image_names(item, found)
    elif isinstance(value, list):
        for item in value: image_names(item, found)
    return found


def edition_and_audience():
    """The org's edition and the page's audience from site.json: what the free edition will not show, and what to check"""
    bound = {args.record_object} if args.record_object else set()
    for region in ("sections", "header", "footerContent"):
        bound |= {item["object"] for _, item in all_items(design.get(region) or []) if item.get("kind") == "repeater" and item.get("object")}
    if edition == "free":
        for obj in sorted(bound - FREE_EDITION_OBJECTS):
            deviations.append(f"Free edition: a record page or repeater on {obj} shows a notice instead of its content; only Account, Contact, Case, Lead and Form Template records show. Use one of those objects, or the paid edition.")
    if audience:
        guest = "guest" in audience
        notes.append(f"Audience: {', '.join(audience)}. " + ("Set up guest access (Step 5) and expect the render check to pass logged out"
                                                             if guest else "Members only: logged out, the render check should land on the login page"))


edition_and_audience()


def repeater_properties(item):
    """Form (Dynamic Repeater) settings for a designed Repeater: an inline Record Card form on the object, its card template, the query and the columns"""
    obj, name = item["object"], re.sub(r"\W", "_", f"Site_Blocks_{item['object']}_Cards")
    card = dict(item["card"], cardType=item.get("cardType") or item["card"].get("cardType") or "mediaTop")
    for key in COLLECTIONS:  # the card stores its collections as JSON strings, as component_properties writes them
        if isinstance(card.get(key), list): card[key] = json.dumps(card[key], ensure_ascii=False)
    for key in ("brandColor", "accentColor"):  # a colour set on the Repeater reaches every card, as the canvas draws it
        if item.get(key) and key not in card: card[key] = item[key]
    section = {"QualifiedApiName": name + "_S01", "FlowToolKit__position__c": 1, "FlowToolKit__sectionType__c": "recordCardSection", "FlowToolKit__showHeader__c": False,
               "isRecordCardSection": True, "FlowToolKit__widthLarge__c": "12", "FlowToolKit__widthMedium__c": "12", "FlowToolKit__widthSmall__c": "12",
               "FlowToolKit__Record_Card__c": json.dumps(card, ensure_ascii=False), "FlowToolKit__fields__r": []}
    form = {"QualifiedApiName": name, "FlowToolKit__ObjectApiName__c": obj, "FlowToolKit__type__c": "form", "FlowToolKit__Version__c": 0, "FlowToolKit__sections__r": [section]}
    columns = int(item.get("columns") or 3)
    properties = {"object": obj, "formSelectionMode": "custom", "formJsonConfig": json.dumps(form, ensure_ascii=False),
                  "largeColumns": columns, "mediumColumns": min(columns, 2), "smallColumns": 1, "pageSize": int(item.get("pageSize") or columns * 2)}
    for key in ("filter", "sortField", "sortDirection", "emptyMessage"):
        if item.get(key): properties[key] = item[key]
    return properties


def component_properties(properties):
    """Another component's settings dict as the one JSON string it stores: an inline form and its record card are strings too"""
    properties = json.loads(json.dumps(properties))
    form = properties.get("formJsonConfig")
    if isinstance(form, dict):
        for section in form.get("FlowToolKit__sections__r", []):
            card = section.get("FlowToolKit__Record_Card__c")
            if isinstance(card, dict):
                for key in COLLECTIONS:
                    if isinstance(card.get(key), list): card[key] = json.dumps(card[key], ensure_ascii=False)
                section["FlowToolKit__Record_Card__c"] = json.dumps(card, ensure_ascii=False)
        properties["formJsonConfig"] = json.dumps(form, ensure_ascii=False)
    return json.dumps(properties, ensure_ascii=False)


def record_binding(item):
    return item.get("recordId") or ("{!recordId}" if record_page else "")


def aura_item(item, path):
    """One design item as an Aura node; a part the site cannot take as drawn is listed and left out"""
    kind = item["kind"]
    item_id = make_id("item", *path)
    if kind == "block":
        props = {key: compact(value) if key in COLLECTIONS and isinstance(value, list) else value for key, value in item["props"].items()}
        attributes = {"properties": json.dumps(props, ensure_ascii=False)}
        if record_binding(item): attributes["recordId"] = record_binding(item)
        return site_views.aura_component("FlowToolKit:siteDesignBlock", attributes, item_id)
    if kind == "divider":
        return site_views.aura_component("FlowToolKit:header", dict(item.get("attributes") or {}), item_id)
    if kind == "richText":
        return site_views.aura_component("forceCommunity:richTextInline", {"richTextValue": item.get("richTextValue", "")}, item_id)
    if kind == "htmlEditor":
        return site_views.aura_component("forceCommunity:htmlBlock", {"richTextValue": item.get("richTextValue", "")}, item_id)
    if kind == "search":
        return site_views.aura_component("forceCommunity:searchBox", dict(site_views.SEARCH_DEFAULTS, placeholder=item.get("placeholder") or "Search..."), item_id)
    if kind == "languageSelector":
        return site_views.aura_component("forceCommunity:languagePicker", {}, item_id)
    if kind == "tabs":
        tabs = [(tab["tabName"], tab["tabKey"], [node for index, child in enumerate(tab.get("items") or []) if (node := aura_item(child, path + [tab["tabKey"], index]))]) for tab in item.get("tabs") or []]
        return site_views.aura_tabset(item_id, tabs, item.get("activeTab"), make_id)
    if kind == "formSlot":
        if item.get("formTemplate"):
            return site_views.aura_component("FlowToolKit:formTemplate", {"recordId": item["formTemplate"]}, item_id)
        deviations.append(f"Form Slot \"{item.get('form')}\" ({item.get('formKind')}) has no Form Template in the org yet: build it with form-design and build-template, then give the slot its formTemplate id. Left out.")
        return None
    if kind == "repeater":
        # validate() has refused a Repeater without its object and card
        return site_views.aura_component("FlowToolKit:formDynamicRepeater", {"properties": json.dumps(repeater_properties(item), ensure_ascii=False), "recordId": record_binding(item), "objectApiName": ""}, item_id)
    if kind == "component":
        attributes = dict(item.get("attributes") or {})
        if isinstance(attributes.get("properties"), dict):
            attributes.update(properties=component_properties(attributes["properties"]), recordId=record_binding(item), objectApiName=attributes.get("objectApiName", ""))
        return site_views.aura_component(item["definition"], attributes, item_id)
    deviations.append(f"{kind} is not a site component. Left out.")
    return None


def aura_sections(sections, region):
    nodes = []
    for s, section in enumerate(sections):
        columns = [(column["width"], [node for i, item in enumerate(column["items"]) if (node := aura_item(item, [region, s, c, i]))]) for c, column in enumerate(section["columns"])]
        nodes.append(site_views.aura_section(make_id("section", region, s), section.get("attributes") or {}, columns, make_id))
    return nodes


def lwr_sections(sections, region, convert):
    return [site_views.lwr_section(node, convert, route_record=record_page) for node in aura_sections(sections, region)]


def count_components(nodes):
    """FlowToolKit components in converted LWR content: what the render check should find on the page"""
    count = 0
    for node in nodes:
        if str(node.get("definition", "")).startswith("FlowToolKit:"): count += 1
        count += count_components(node.get("children") or [])
    return count


def item_file(item):
    """The block-folder form of one page.json item; file_item reads it back to the same item"""
    if item["kind"] == "block":
        data = {}
        for key, value in item["props"].items():
            if key in COLLECTIONS and isinstance(value, str) and value.startswith("["):
                parsed = json.loads(value)
                # an array only when it serialises back to the same string, so the folder rebuilds the same view
                data[key] = parsed if compact(parsed) == value else value
            else:
                data[key] = value
    elif item["kind"] == "component":
        data = {"_component": item["definition"], **(item.get("attributes") or {})}
    else:
        data = {"_kind": item["kind"], **{key: value for key, value in item.items() if key not in ("kind", "recordId")}}
    if item.get("recordId"): data["_recordId"] = item["recordId"]
    return data


def block_files(sections):
    """The page as a block folder: NN[a-z]-<type>.json per item, numbered by section (10a, 10b share section 10), and
    _sections.json with each section's widths, settings and, when a column stacks items, which files each column holds.
    The folder is an output of page.json: the next run from page.json overwrites a hand edit."""
    folder = pathlib.Path(args.blocks)
    folder.mkdir(parents=True, exist_ok=True)
    for old in list(folder.glob("[0-9]*.json")) + list(folder.glob("_sections.json")): old.unlink()
    layout, count = {}, 0
    for s, section in enumerate(sections, 1):
        group = f"{s:02d}"
        items = [item for column in section["columns"] for item in column["items"]]
        letters = iter([chr(97 + i) if i < 26 else f"z{i:03d}" for i in range(len(items))])
        columns = []
        for column in section["columns"]:
            names = []
            for item in column["items"]:
                kind = item["props"].get("sectionType", "block") if item["kind"] == "block" else item["kind"]
                name = f"{group}{'' if len(items) == 1 else next(letters)}-{kind}.json"
                write(folder / name, item_file(item))
                names.append(name)
                count += 1
            columns.append(names)
        spec = {"widths": [str(column["width"]) for column in section["columns"]]}
        if section.get("attributes"): spec["attributes"] = section["attributes"]
        if any(len(names) != 1 for names in columns): spec["columns"] = columns
        layout[group] = spec
    write(folder / "_sections.json", layout)
    return count


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def aura_home():
    """The site's own Home page: its content region takes the design's sections; the view, its id and its route stay"""
    path = bundle / "views" / "home.json"
    view = json.loads(path.read_text())
    content = next(region for region in view["regions"] if region.get("regionName") == "content")
    content["components"] = site_views.strip_private(aura_sections(design["sections"], "content"))
    write(path, view)
    return ["."]


def aura_page():
    if args.record_object:
        deviations.append(f"A record page for {args.record_object} is built this way on LWR only; an Aura site has no per-object route files in that shape, so the page was built as a custom page bound to {{!recordId}}. For a Form Template or Form Submission record page, use the packaged Form Template Detail and Form Submission Detail page variations in Builder instead.")
    if args.page == "home": return aura_home()
    content = aura_sections(design["sections"], "content")
    home = json.loads((bundle / "routes" / "home.json").read_text())
    app_page_id = json.loads((bundle / "config" / "mainAppPage.json").read_text())["id"]
    view_id = make_id("view")
    seo = site_views.aura_component("forceCommunity:seoAssistant", {"customHeadTags": "", "description": "", "title": title}, make_id("seo"))
    view = {"appPageId": app_page_id, "componentName": "siteforce:dynamicLayout", "dataProviders": [], "id": view_id, "label": title, "type": "view", "themeLayoutType": "Inner",
            "regions": [{"components": content, "id": make_id("content"), "regionName": "content", "type": "region"},
                        {"components": [seo], "id": make_id("hidden"), "regionName": "sfdcHiddenRegion", "type": "region"}],
            "viewType": f"custom-{args.page}"}
    route = dict(home)
    route.update({"activeViewId": view_id, "devName": re.sub(r"\W", "_", title), "id": make_id("route"), "label": title, "routeType": f"custom-{args.page}", "urlPrefix": args.page})
    write(bundle / "views" / f"{args.page}.json", site_views.strip_private(view))
    write(bundle / "routes" / f"{args.page}.json", route)
    # An Aura site deploys as one ExperienceBundle: the whole folder goes, so pull and compare it first
    return ["."]


def lwr_view(view_title, view_type, url_name, content, seo_record):
    seo = {"attributes": {"customHeadTags": "", "description": "", "dxpStyle": {}, "pageTitle": view_title, "recordId": seo_record},
           "definition": "community_builder:seoAssistant", "id": make_id("seo", view_type), "type": "component"}
    return {"type": "sfdc_cms__view", "title": view_title, "contentBody": {
        "component": {"children": [{"children": content, "id": make_id("content", view_type), "name": "content", "title": "Content", "type": "region"},
                                   {"children": [seo], "id": make_id("hidden", view_type), "name": "sfdcHiddenRegion", "title": "sfdcHiddenRegion", "type": "region"}],
                      "definition": "community_layout:sldsFlexibleLayout", "id": make_id("layout", view_type), "type": "component"},
        "dataProviders": [], "themeLayoutType": "Inner", "viewType": view_type}, "urlName": url_name}


def write_route_and_view(route_name, view_name, route_title, route_type, url_prefix, url_name, view):
    write(bundle / "sfdc_cms__view" / view_name / "_meta.json", {"apiName": view_name, "type": "sfdc_cms__view", "path": "views"})
    write(bundle / "sfdc_cms__view" / view_name / "content.json", view)
    write(bundle / "sfdc_cms__route" / route_name / "_meta.json", {"apiName": route_name, "type": "sfdc_cms__route", "path": "routes"})
    write(bundle / "sfdc_cms__route" / route_name / "content.json", {"type": "sfdc_cms__route", "title": route_title, "contentBody": {
        "activeViewId": view_name, "configurationTags": [], "pageAccess": "UseParent", "routeType": route_type, "urlPrefix": url_prefix}, "urlName": url_name})
    return [f"sfdc_cms__view/{view_name}", f"sfdc_cms__route/{route_name}"]


def bundle_routes():
    """{route api name: route content} for every route in the LWR bundle"""
    return {path.parent.name: json.loads(path.read_text()) for path in sorted((bundle / "sfdc_cms__route").glob("*/content.json"))}


def check_title(route_title, routes):
    """Experience Builder refuses two pages with one title (a record page titled "Home" is refused)"""
    clash = [name for name, route in routes.items() if route.get("title") == route_title]
    if clash: fail(f"the site already has a page titled \"{route_title}\" ({clash[0]}); give --title a name no other page uses.")


def route_key(obj, routes):
    """What follows "detail-" in the object's route types. Experience Builder keys a standard object's routes by its key
    prefix (Account detail-001) and a custom object's by its API name (detail-FlowToolKit__Form_Template__c). From the
    object's own route in the bundle, then the standard objects, then --record-prefix, then a custom object's API name;
    never an org query."""
    for name, route in routes.items():
        route_type = (route.get("contentBody") or {}).get("routeType", "")
        if route_type == f"detail-{obj}" or (name == f"{obj}_Detail__c" and route_type.startswith("detail-")): return route_type[len("detail-"):]
    key = STANDARD_PREFIXES.get(obj) or args.record_prefix or (obj if obj.endswith("__c") else None)
    if not key: fail(f"{obj} has no route in this site and is not in the built-in list of standard objects: give --record-prefix (the first three characters of a {obj} record Id).")
    return key


def lwr_record_pages(content):
    """An object's record page: the design fills the detail view's content region. The detail, list and related-list routes
    are one set (Experience Builder deploys an object page only with all three); a missing one is written with a one-block
    stub view, an existing one is kept as the site has it, so a Builder edit to a companion survives a rerun. New routes and
    views are named as Builder names them: Account_Detail__c and accountDetail, Form_Template_Detail__c and Form_Template_Detail."""
    obj = args.record_object
    routes = bundle_routes()
    prefix = route_key(obj, routes)
    by_type = {(route.get("contentBody") or {}).get("routeType"): name for name, route in routes.items()}
    custom = obj.endswith("__c")
    base = re.sub(r"__c$", "", re.sub(r"^[A-Za-z0-9]+__(?=\w+__c$)", "", obj))
    view_api = (lambda suffix: f"{base}_{suffix}") if custom else (lambda suffix: base[0].lower() + base[1:] + suffix.replace("_", ""))
    url_prefix = base.lower().replace("_", "-")
    label = base.replace("_", " ")
    written = []
    detail_type = f"detail-{prefix}"
    if detail_type in by_type:
        route_name = by_type[detail_type]
        view_name = routes[route_name]["contentBody"]["activeViewId"]
        view_path = bundle / "sfdc_cms__view" / view_name / "content.json"
        view = json.loads(view_path.read_text())
        next(region for region in view["contentBody"]["component"]["children"] if region["name"] == "content")["children"] = content
        write(view_path, view)
        written.append(f"sfdc_cms__view/{view_name}")
        notes.append(f"Routes: {route_name} ({detail_type}) kept; its view {view_name} takes the design")
    else:
        check_title(title, routes)
        written += write_route_and_view(f"{base}_Detail__c", view_api("Detail"), title, detail_type, url_prefix, f"{url_prefix}-detail",
                                        lwr_view(title, detail_type, f"{url_prefix}-detail", content, site_views.LWR_RECORD))
        routes[f"{base}_Detail__c"] = {"title": title}
        notes.append(f"Routes: {base}_Detail__c ({detail_type}) written")
    for kind, suffix, words in (("list", "List", "List"), ("relatedlist", "Related_List", "Related List")):
        route_type = f"{kind}-{prefix}"
        if route_type in by_type:
            notes.append(f"Routes: {by_type[route_type]} ({route_type}) kept as the site has it")
            continue
        companion_title = f"{label} {words}"
        check_title(companion_title, routes)
        url_name = f"{url_prefix}-{words.lower().replace(' ', '-')}"
        stub = {"kind": "block", "props": {"sectionType": "hero", "heading": companion_title}}
        stub_content = lwr_sections([{"columns": [{"width": "12", "items": [stub]}]}], route_type, lambda *parts: make_id("lwr", route_type, *parts))
        written += write_route_and_view(f"{base}_{suffix}__c", view_api(suffix), companion_title, route_type, url_prefix, url_name,
                                        lwr_view(companion_title, route_type, url_name, stub_content, "{!recordId}"))
        routes[f"{base}_{suffix}__c"] = {"title": companion_title}
        notes.append(f"Routes: {base}_{suffix}__c ({route_type}) written with a one-block stub page")
    return written


def lwr_page(content):
    if args.record_object:
        return lwr_record_pages(content)
    if args.page == "home":
        # The site's own Home page: its content region takes the design's sections; the view and its route stay as the site made them
        path = bundle / "sfdc_cms__view" / "home" / "content.json"
        view = json.loads(path.read_text())
        next(region for region in view["contentBody"]["component"]["children"] if region["name"] == "content")["children"] = content
        write(path, view)
        return ["sfdc_cms__view/home"]
    if record_page:
        deviations.append("--record-page on LWR binds the blocks to {!Route.recordId}, which only an object's record page has: give --record-object <Object> to build one.")
    api_name = re.sub(r"-(\w)", lambda match: match.group(1).upper(), args.page)
    route_name = api_name[0].upper() + api_name[1:] + "__c"
    # A page the site already has keeps its own route and view names: on a case-insensitive disk, writing "about" over an
    # existing "About" view would rename it in the org
    for existing in sorted((bundle / "sfdc_cms__route").glob("*/content.json")):
        route_body = json.loads(existing.read_text()).get("contentBody") or {}
        if route_body.get("urlPrefix") == args.page and route_body.get("activeViewId"):
            route_name, api_name = existing.parent.name, route_body["activeViewId"]
            break
    else:
        api_name = next((d.name for d in (bundle / "sfdc_cms__view").iterdir() if d.name.lower() == api_name.lower()), api_name)
        check_title(title, bundle_routes())
    view = lwr_view(title, f"custom-{args.page}", args.page, content, site_views.LWR_RECORD if record_page else "{!recordId}")
    write(bundle / "sfdc_cms__view" / api_name / "_meta.json", {"apiName": api_name, "type": "sfdc_cms__view", "path": "views"})
    write(bundle / "sfdc_cms__view" / api_name / "content.json", view)
    write(bundle / "sfdc_cms__route" / route_name / "_meta.json", {"apiName": route_name, "type": "sfdc_cms__route", "path": "routes"})
    write(bundle / "sfdc_cms__route" / route_name / "content.json", {"type": "sfdc_cms__route", "title": title, "contentBody": {
        "activeViewId": api_name, "configurationTags": [], "pageAccess": "UseParent", "routeType": f"custom-{args.page}", "urlPrefix": args.page}, "urlName": args.page})
    return [f"sfdc_cms__view/{api_name}", f"sfdc_cms__route/{route_name}"]


def navigation_menu():
    """The design's navItems as the site's default navigation menu: site-relative links, Home first."""
    items = design.get("navItems") or []
    if not items: return None
    # Salesforce refuses a menu item whose page the site does not have, so only links to existing pages go in
    route_files = (bundle / "sfdc_cms__route").glob("*/content.json") if lwr else (bundle / "routes").glob("*.json")
    prefixes = {"/"} | {"/" + ((data.get("contentBody") or data).get("urlPrefix") or "") for data in (json.loads(path.read_text()) for path in route_files)}
    entries = []
    for item in items:
        label = item if isinstance(item, str) else item["label"]
        target = (item.get("href") if isinstance(item, dict) else None) or ("/" if label.lower() == "home" else "/" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-"))
        if target not in prefixes:
            deviations.append(f"Navigation item \"{label}\" links to {target}, which the site has no page for yet: build that page, then rerun with --entire-site. Left out of the menu.")
            continue
        entries.append(f"    <navigationMenuItem>\n        <label>{label}</label>\n        <position>{len(entries)}</position>\n        <publiclyAvailable>true</publiclyAvailable>\n        <target>{target}</target>\n        <type>InternalLink</type>\n    </navigationMenuItem>\n")
    menu = (bundle.parent.parent.parent if lwr else bundle.parent.parent) / "navigationMenus"
    path = menu / f"SFDC_Default_Navigation_{re.sub(r'1$', '', site_name)}.navigationMenu-meta.xml"
    container = path.name.replace("SFDC_Default_Navigation_", "").replace(".navigationMenu-meta.xml", "").replace("_", " ")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<NavigationMenu xmlns="http://soap.sforce.com/2006/04/metadata">\n    <container>{container}</container>\n    <containerType>Network</containerType>\n    <label>Default Navigation</label>\n{"".join(entries)}</NavigationMenu>\n')
    notes.append("Navigation: deploy the menu after the bundle, because Salesforce refuses a menu item whose page is not in the org yet")
    return path


def aura_site():
    """The Customer Service theme's search placeholder and footer, and the brand colour and logo, from the design's Page"""
    theme_file = next((bundle / "themes").glob("*.json"))
    theme = json.loads(theme_file.read_text())
    inner = next(view for view in theme["views"] if view["id"] == theme["layouts"]["Inner"])
    regions = {region["regionName"]: region for region in inner["regions"]}
    if design.get("layout") == "customerService" and inner["componentName"] == "siteforce:serviceBody":
        if design.get("searchPlaceholder") and regions.get("search", {}).get("components"):
            regions["search"]["components"][0]["componentAttributes"]["placeholder"] = design["searchPlaceholder"]
        if design.get("footer"):
            regions["footer"]["components"] = [site_views.aura_component("forceCommunity:richTextInline", {"richTextValue": design["footer"]}, make_id("theme-footer"))]
        write(theme_file, theme)
    elif design.get("layout") == "customerService":
        deviations.append("The design uses the Customer Service theme layout; this site's theme is not siteforce:serviceBody, so its header and footer were left as they are.")
    brand = (design.get("theme") or {}).get("brand")
    branding_file = next((bundle / "brandingSets").glob("*.json"), None)
    if branding_file and (brand or design.get("logo")):
        branding = json.loads(branding_file.read_text())
        if brand: branding["values"].update({"ActionColor": brand, "LinkColor": brand})
        if design.get("logo"): branding["values"]["CompanyLogo"] = f"/file-asset/{design['logo']}?v=1"
        write(branding_file, branding)
    if any(site_config.get(key) for key in ("headTokens", "branding", "authenticationType")):
        deviations.append("Head tokens, branding values and site access from the site config apply on LWR only; on an Aura site set them in Builder.")
    return ["."]


def inner_layout_file():
    """The theme layout the site's pages use: the active theme's Inner layout, as the app page names it"""
    app_page = json.loads((bundle / "sfdc_cms__appPage" / "mainAppPage" / "content.json").read_text())
    theme_file = bundle / "sfdc_cms__theme" / str(app_page["contentBody"].get("currentThemeId")) / "content.json"
    if theme_file.exists():
        layouts = json.loads(theme_file.read_text())["contentBody"].get("layouts") or []
        layout_id = next((layout["layoutId"] for layout in layouts if layout.get("layoutType") == "Inner"), None)
        if layout_id and (bundle / "sfdc_cms__themeLayout" / layout_id / "content.json").exists():
            return bundle / "sfdc_cms__themeLayout" / layout_id / "content.json"
    return next(path for path in (bundle / "sfdc_cms__themeLayout").glob("*/content.json") if "scopedHeaderAndFooter" in path.read_text())


def footer_support(regions):
    """FlowToolKit LWR Support, and each --footer-support component, once in the theme footer. Since Winter '27 an LWR
    site's publisher bundles only what a page reaches by a static reference, and Flow Tool Kit loads its forms, modals,
    repeaters and any custom section component by name, so without these a form fails to load (LWR3008)."""
    footer = regions.get("footer")
    if footer is None:
        deviations.append("The theme layout has no footer region: add FlowToolKit LWR Support to the Theme Footer in Builder, then publish.")
        return
    sections = footer.setdefault("children", [])
    wanted = [LWR_SUPPORT] + list(dict.fromkeys(args.footer_support))
    present = json.dumps(sections)
    missing = [name for name in wanted if f'"definition": "{name}"' not in present]
    if not missing: return
    if not sections or not sections[-1].get("children"):
        # A footer with no Section yet (a new Build Your Own (LWR) site): give it one full-width Section to hold them
        sections.append(site_views.lwr_section(site_views.aura_section(make_id("footer-support-section"), {}, [("12", [])], make_id), lambda *parts: make_id("lwr-footer", *parts)))
    column = sections[-1]["children"][0].setdefault("children", [])
    for name in missing:
        column.append({"attributes": {"dxpStyle": {}}, "definition": name, "id": make_id("footer-support", name), "type": "component"})
    notes.append("Theme footer: " + ", ".join(missing) + " added")


def head_markup():
    """The design's Page theme, then the site config's headTokens on top, as one <style> in the head, and the brand's web
    font as one <link>; both replaced on every run. Returns the folder written."""
    theme = design.get("theme") or {}
    tokens = {token: theme[key] for key, token in THEME_TOKENS.items() if theme.get(key)}
    tokens.update(site_config.get("headTokens") or {})
    path = bundle / "sfdc_cms__appPage" / "mainAppPage" / "content.json"
    app_page = json.loads(path.read_text())
    before = app_page["contentBody"].get("headMarkup") or ""
    markup = FONT_LINK.sub("", TOKEN_STYLE.sub("", before))
    site_title = site_config.get("title")
    if site_title:
        markup = re.sub(r"<title>.*?</title>", f"<title>{site_title}</title>", markup, count=1) if "<title>" in markup else f"<title>{site_title}</title>\n" + markup
    markup = markup.rstrip("\n")
    if font_href:
        markup += f'\n{FONT_MARK}\n<link rel="stylesheet" href="{font_href}"/>'
        host = re.match(r"https?://[^/]+", font_href)
        deviations.append(f"Web font from {host.group(0) if host else font_href}: add it (and the host it loads font files from) as a Trusted URL for this site with style-src and font-src, or the site falls back to the next font in the stack.")
    if tokens:
        markup += "\n<style data-site-blocks-tokens>:root {" + "".join(f" {name}: {value};" for name, value in tokens.items()) + " }</style>"
    markup += "\n"
    notes.append(f"Head: {len(tokens)} --ftk-site-* tokens" + (", web font link" if font_href else ""))
    app_page["contentBody"]["headMarkup"] = markup
    write(path, app_page)
    return str(path.parent.relative_to(bundle))


def lwr_site():
    """The theme layout's header and footer, LWR Support, the branding set, the head markup and the site access"""
    written = []
    layout_file = inner_layout_file()
    layout = json.loads(layout_file.read_text())
    regions = {region["name"]: region for region in layout["contentBody"]["component"]["children"]}
    scoped = layout["contentBody"]["component"].get("definition") == "community_byo:scopedHeaderAndFooter"
    if scoped:
        # The Build Your Own (LWR) theme layout's header and footer regions hold the design's header and footer Sections
        convert = lambda *parts: make_id("lwr-theme", *parts)
        for region_name, key in (("header", "header"), ("footer", "footerContent")):
            sections = design.get(key)
            if not sections or not isinstance(sections, list) or "columns" not in sections[0]: continue
            regions[region_name]["children"] = [site_views.lwr_section(node, convert) for node in aura_sections(sections, region_name)]
    elif design.get("header") or design.get("footerContent"):
        deviations.append(f"The theme layout is {layout_file.parent.name} ({layout['contentBody']['component'].get('definition')}), not Build Your Own (LWR)'s: its header and footer were left as they are.")
    footer_support(regions)
    # Every site-wide file is listed on every run, changed or not, so the printed deploy is complete even after a rerun
    write(layout_file, layout)
    written.append(str(layout_file.parent.relative_to(bundle)))
    # The branding set's accent is the site brand (--dxp-g-brand); its darker steps follow the shades Builder derives for its default blue
    theme = design.get("theme") or {}
    brand = theme.get("brand")
    branding_file = next((bundle / "sfdc_cms__brandingSet").glob("*/content.json"), None)
    values = dict(kit_branding)
    if isinstance(brand, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", brand):
        shade = lambda factor: "#" + "".join(f"{round(int(brand[i:i + 2], 16) * factor):02x}" for i in (1, 3, 5))
        values.update({"PrimaryAccentColor": brand, "_PrimaryAccentColor1": shade(0.77), "_PrimaryAccentColor2": shade(0.32), "_PrimaryAccentColor3": "#000000"})
    elif brand:
        deviations.append(f"Brand colour {brand!r} is not a six-digit hex colour: the branding set was left as it is.")
    if theme.get("text"): values["TextColor"] = theme["text"]
    values.update(site_config.get("branding") or {})
    if values and branding_file:
        branding = json.loads(branding_file.read_text())
        branding["contentBody"]["values"].update(values)
        write(branding_file, branding)
        written.append(str(branding_file.parent.relative_to(bundle)))
    written.append(head_markup())
    if site_config.get("authenticationType"):
        site_file = next((bundle / "sfdc_cms__site").glob("*/content.json"))
        content = json.loads(site_file.read_text())
        content["contentBody"]["authenticationType"] = site_config["authenticationType"]
        write(site_file, content)
        written.append(str(site_file.parent.relative_to(bundle)))
    if design.get("layout") == "customerService":
        deviations.append("The Customer Service theme layout is Aura only; on LWR the header is the design's header Sections.")
    return written


if lwr:
    content = lwr_sections(design["sections"], "content", lambda *parts: make_id("lwr", *parts))
    written = lwr_page(content)
    expected = count_components(content)
else:
    written = aura_page()
    expected = None
if args.entire_site:
    written += lwr_site() if lwr else aura_site()
    menu = navigation_menu()
    if menu: written.append(str(menu))
elif args.footer_support:
    deviations.append("--footer-support applies with --entire-site; rerun with it to write the theme footer.")
elif site_config:
    notes.append("Site-wide settings (theme footer, branding, head, site access, menu) are written by the --entire-site run")
if design.get("site") and design["site"] != ("lwr" if lwr else "aura"):
    deviations.append(f"Designed as {design['site']}, built on {'LWR' if lwr else 'Aura'}: the blocks are the same; sections and standard components were converted.")
blocks = block_files(design["sections"]) if args.blocks else None

source_paths = " ".join(f"--source-dir {path if path.endswith('.xml') else bundle / path}" for path in dict.fromkeys(written) if not path.endswith(".xml"))
menu_paths = [path for path in dict.fromkeys(written) if path.endswith(".xml")]
publish = SKILL_DIR / "_shared" / "sf" / "site_publish.py"
print(f"{site_name} ({'LWR' if lwr else 'Aura'}): /{args.page}, {len(design['sections'])} sections"
      + (f", {expected} Flow Tool Kit components" if expected is not None else "")
      + (f", {blocks} block files in {args.blocks}" if blocks is not None else ""))
print("Wrote: " + ", ".join(dict.fromkeys(written)))
for note in notes: print(note)
print(f"Deploy (pull and compare first): sf project deploy start {source_paths} --target-org <org-alias>")
for path in menu_paths: print(f"Then the menu: sf project deploy start --source-dir {path} --target-org <org-alias>")
print(f"Publish: python3 {publish} \"<site label>\" --target-org <org-alias>")
images = sorted(image_names([design.get(region) for region in ("sections", "header", "footerContent")] + [design.get("logo")], set()))
if images:
    own = [name for name in images if not name.startswith("FlowToolKit__")]
    print(f"Images: {len(images)} by Asset File name" + (f"; the organization's own, which must be public Asset Files in the org: {', '.join(own)}" if own else ", all packaged with Flow Tool Kit"))
for deviation in deviations: print("Deviation: " + deviation)
