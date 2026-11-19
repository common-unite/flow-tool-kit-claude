"""Where else a Form Component is used, outside Form Templates: flows, Lightning pages, Experience Cloud site pages and
wrapper Lightning web components. These are metadata, not records, so SOQL cannot read them; the Salesforce CLI
retrieves them (catalog.py collect) and scan_folder() reads the files, in Metadata API or source format.

Pure and standard library only (the files are the org's own metadata, retrieved by the person; Python's XML parser
fetches no external entities). scan_folder() returns, per kind, the places that name a form; ocbuild links each name to
a catalog component. The component and property names are the package's own (the js-meta.xml of each component).
"""
from __future__ import annotations

import json
import pathlib
import re
import xml.etree.ElementTree as ET

PACKAGE = "flowtoolkit"

# Flow screen components and the inputs that carry a form's name (FlowToolKit:<component>, inputParameters.name)
FLOW_INPUTS = {
    "flowForm": ("Form (Component)", ("formQualifiedApiName",)),
    "flowFormRepeat": ("Form (Repeater)", ("formQualifiedApiName", "editFormQualifiedApiName")),
    "flowDataTable": ("Form (Table)", ("formQualifiedApiName", "overrideTableFormName", "overrideTableFormBulkName")),
    "flowFormLookup": ("Form (Lookup)", ("formQualifiedApiName", "overrideTableFormName")),
}
FLOW_JSON_INPUT = "formJSON"  # a form's own JSON held in the flow; components placed inside it are uses too

# Page components (Lightning pages and site pages) and the property that carries a form's name
PAGE_COMPONENTS = {
    "lightningRecordForm": ("Form (Component)", ("formQualifiedApiName",)),
    # Its one setting, "properties", is a JSON string: formQualifiedApiName unless formSelectionMode is "custom",
    # when the form's own JSON is in formJsonConfig
    "lightningRecordFormDynamicDisplay": ("Form (Dynamic Component)", ()),
}

# Package tags a wrapper component can render a form with, and the attributes that name one
WRAPPER_TAGS = ("lightning-record-form", "lightning-record-form-dynamic-display", "flow-form", "flow-form-repeat",
                "flow-data-table")
WRAPPER_ATTRIBUTES = ("form-qualified-api-name", "edit-form-qualified-api-name", "override-table-form-name",
                      "override-table-form-bulk-name")
NESTED_FIELDS = ("formComponent__c", "Default_Table_Form__c", "Default_Table_Form_bulk__c", "referenceFormComponent__c")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,79}$")
LITERAL = re.compile(r"""(['"])([A-Za-z][A-Za-z0-9_]{2,79})\1""")

KINDS = ("flows", "lightning_pages", "site_pages", "wrapper_components")


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _child(element, name):
    for child in element:
        if _tag(child) == name:
            return child
    return None


def _text(element, name):
    child = _child(element, name) if element is not None else None
    return (child.text or "").strip() if child is not None and child.text else None


def _package_component(name):
    """'flowForm' for 'FlowToolKit:flowForm'; None for any other namespace."""
    ns, sep, local = (name or "").partition(":")
    return local if sep and ns.lower() == PACKAGE else None


def nested_names(value):
    """Component names placed inside a form's own JSON: sections that place a component or a table form (also bulk),
    and fields that show a lookup as a component."""
    root = value if isinstance(value, (dict, list)) else None
    if root is None:
        try:
            root = json.loads(value) if isinstance(value, str) and value.strip() else None
        except ValueError:
            return []
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, item in node.items():
                short = key.split("__", 1)[1] if key.startswith(("*__", "FlowToolKit__")) else key
                if short in NESTED_FIELDS and isinstance(item, str) and NAME.match(item.replace("FlowToolKit__", "").replace("*__", "")):
                    found.append(item.replace("*__", "FlowToolKit__"))
                elif short.endswith("__r") and short[:-1] + "c" in NESTED_FIELDS and isinstance(item, dict) \
                        and isinstance(item.get("QualifiedApiName"), str):
                    found.append(item["QualifiedApiName"])
                else:
                    walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(root)
    return sorted(set(found))


# ---- flows -----------------------------------------------------------------------------------------------------------

def scan_flow(text, api_name):
    """Places in one flow file. A form name set from a variable or constant with a fixed value is resolved; one set at
    run time (a formula, a record field, an input) is returned with form None and the variable named."""
    root = ET.fromstring(text)
    label, status = _text(root, "label") or api_name, _text(root, "status")
    fixed = {}
    for element in root:
        if _tag(element) in ("variables", "constants"):
            value = _child(element, "value")
            if _text(element, "name") and value is not None and _text(value, "stringValue"):
                fixed[_text(element, "name")] = _text(value, "stringValue")
    places = []
    for screen in (e for e in root if _tag(e) == "screens"):
        screen_label = _text(screen, "label") or _text(screen, "name")
        for field in screen.iter():
            if _tag(field) != "fields":
                continue
            local = _package_component(_text(field, "extensionName"))
            if local not in FLOW_INPUTS:
                continue
            component_label, inputs = FLOW_INPUTS[local]
            where = f"screen {screen_label}, {_text(field, 'name')}"
            for param in (p for p in field if _tag(p) == "inputParameters"):
                name, value = _text(param, "name"), _child(param, "value")
                literal, reference = _text(value, "stringValue"), _text(value, "elementReference")
                base = {"kind": "flow", "name": api_name, "label": label, "status": status, "where": where,
                        "component": local, "component_label": component_label, "property": name}
                if name in inputs:
                    if literal:
                        places.append(dict(base, form=literal))
                    elif reference:
                        resolved = fixed.get(reference)
                        places.append(dict(base, form=resolved, variable=reference) if resolved else dict(base, form=None, variable=reference))
                elif name == FLOW_JSON_INPUT:
                    for nested in nested_names(literal or fixed.get(reference or "")):
                        places.append(dict(base, form=nested, inside=True))
    return places


# ---- Lightning pages -------------------------------------------------------------------------------------------------

def scan_flexipage(text, api_name):
    root = ET.fromstring(text)
    label, page_type, sobject = _text(root, "masterLabel") or api_name, _text(root, "type"), _text(root, "sobjectType")
    places = []
    for region in (e for e in root.iter() if _tag(e) == "flexiPageRegions"):
        region_name = _text(region, "name")
        for instance in region.iter():
            if _tag(instance) not in ("componentInstance", "componentInstances"):
                continue
            local = _package_component(_text(instance, "componentName"))
            if local not in PAGE_COMPONENTS:
                continue
            properties = {_text(p, "name"): _text(p, "value") for p in instance if _tag(p) == "componentInstanceProperties"}
            base = {"kind": "lightning page", "name": api_name, "label": label, "page_type": page_type, "object": sobject,
                    "where": f"region {region_name}", "component": local, "component_label": PAGE_COMPONENTS[local][0]}
            places += _page_component_places(local, properties, base)
    return places


def _page_component_places(local, attributes, base):
    """Form names a page component instance carries, from its properties (FlexiPage) or attributes (site view)."""
    places = []
    if local == "lightningRecordFormDynamicDisplay":
        settings = attributes.get("properties")
        if isinstance(settings, str):
            try:
                settings = json.loads(settings) if settings.strip() else {}
            except ValueError:
                settings = {}
        settings = settings if isinstance(settings, dict) else {}
        if settings.get("formSelectionMode") != "custom" and isinstance(settings.get("formQualifiedApiName"), str) \
                and settings["formQualifiedApiName"].strip():
            places.append(dict(base, property="properties.formQualifiedApiName", form=settings["formQualifiedApiName"].strip()))
        if settings.get("formSelectionMode") != "component":
            for nested in nested_names(settings.get("formJsonConfig")):
                places.append(dict(base, property="properties.formJsonConfig", form=nested, inside=True))
        return places
    for prop in PAGE_COMPONENTS[local][1]:
        value = attributes.get(prop)
        if isinstance(value, str) and value.strip():
            bound = value.strip().startswith("{!")
            places.append(dict(base, property=prop, form=None if bound else value.strip(), **({"variable": value.strip()} if bound else {})))
    return places


# ---- Experience Cloud site pages -------------------------------------------------------------------------------------

def scan_site_view(data, site, view):
    """Places in one site view: an Aura view (componentName, componentAttributes) or an LWR view's content.json
    (definition, attributes)."""
    places = []
    label = (data.get("label") or data.get("title") or view) if isinstance(data, dict) else view

    def walk(node):
        if isinstance(node, dict):
            name = node.get("definition") or node.get("componentName")
            attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else node.get("componentAttributes")
            local = _package_component(name) if isinstance(name, str) else None
            if local in PAGE_COMPONENTS and isinstance(attributes, dict):
                base = {"kind": "site page", "name": f"{site}/{view}", "label": f"{site}: {label}", "site": site,
                        "where": f"page {view}", "component": local, "component_label": PAGE_COMPONENTS[local][0]}
                places.extend(_page_component_places(local, attributes, base))
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return places


def _site_and_view(path):
    """(site, view) for a site view file, or None: experiences/<Site>/views/<view>.json (Aura) or
    digitalExperiences/site/<Site>/sfdc_cms__view/<view>/content.json (LWR)."""
    parts = path.parts
    if "experiences" in parts and path.suffix == ".json" and "views" in parts:
        i = parts.index("experiences")
        return (parts[i + 1], path.stem) if len(parts) > i + 2 else None
    if "digitalExperiences" in parts and path.name == "content.json" and "sfdc_cms__view" in parts:
        i = parts.index("sfdc_cms__view")
        site = parts[i - 1] if i >= 1 else "site"
        return (site, parts[i + 1]) if len(parts) > i + 1 else None
    return None


# ---- wrapper components ----------------------------------------------------------------------------------------------

def scan_wrapper(files, bundle):
    """A Lightning web component of the org's own that renders the package's form. Names come from literal attributes
    in its HTML and from string literals in its JavaScript (ocbuild keeps only those that are catalog components). A
    wrapper that holds the form's JSON (form-json-config) is a copy: it does not follow later changes to the component."""
    html = "\n".join(text for path, text in files if path.suffix == ".html")
    tags = [t for t in WRAPPER_TAGS if f"<{PACKAGE}-{t}" in html.lower()]
    if not tags:
        return []
    copy = "form-json-config" in html.lower()
    base = {"kind": "wrapper component", "name": bundle, "label": bundle, "where": f"<{PACKAGE}-{tags[0]}>",
            "component": tags[0], "component_label": "wrapper of " + tags[0], "copy": copy}
    places, seen = [], set()
    for attribute in WRAPPER_ATTRIBUTES:
        for value in re.findall(attribute + r"""\s*=\s*["']([^"'{}]+)["']""", html, re.I):
            if value not in seen:
                seen.add(value)
                places.append(dict(base, property=attribute, form=value.strip()))
    for path, text in files:
        if path.suffix != ".js":
            continue
        for _, value in LITERAL.findall(text):
            if value not in seen:
                seen.add(value)
                places.append(dict(base, property="literal in " + path.name, form=value, candidate=True))
    return places


# ---- a folder of retrieved metadata ----------------------------------------------------------------------------------

def scan_folder(folder):
    """Every place in a folder of retrieved metadata (Metadata API or source format), by kind:
    {kind: {"files": n, "items": [...]}} for each kind whose files were found."""
    folder = pathlib.Path(folder)
    out = {}

    def add(kind, items):
        entry = out.setdefault(kind, {"files": 0, "items": [], "unreadable": []})
        entry["files"] += 1
        entry["items"].extend(items)

    bundles = {}
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        name = path.name
        try:
            if name.endswith((".flow", ".flow-meta.xml")):
                add("flows", scan_flow(path.read_text(encoding="utf-8"), re.sub(r"\.flow(-meta\.xml)?$", "", name)))
            elif name.endswith((".flexipage", ".flexipage-meta.xml")):
                add("lightning_pages", scan_flexipage(path.read_text(encoding="utf-8"), re.sub(r"\.flexipage(-meta\.xml)?$", "", name)))
            elif _site_and_view(path):
                site, view = _site_and_view(path)
                add("site_pages", scan_site_view(json.loads(path.read_text(encoding="utf-8")), site, view))
            elif "lwc" in path.parts and "__tests__" not in path.parts and path.suffix in (".html", ".js"):
                i = len(path.parts) - 1 - path.parts[::-1].index("lwc")
                if len(path.parts) > i + 2:
                    bundles.setdefault(path.parts[i + 1], []).append((path, path.read_text(encoding="utf-8")))
        except (ET.ParseError, ValueError, UnicodeDecodeError) as error:
            kind = "flows" if ".flow" in name else "lightning_pages" if ".flexipage" in name else "site_pages"
            out.setdefault(kind, {"files": 0, "items": [], "unreadable": []})["unreadable"].append(f"{path.name}: {str(error)[:120]}")
    for bundle, files in sorted(bundles.items()):
        add("wrapper_components", scan_wrapper(files, bundle))
    return out
