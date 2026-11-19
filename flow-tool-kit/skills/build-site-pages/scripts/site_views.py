"""Experience Builder page JSON for both site types, used by design_to_site.py.

Aura nodes (componentName, componentAttributes, regions) are built first; lwr_section converts one to the LWR shape
(definition, attributes, children). The LWR component names were confirmed by deploys to an LWR site.
Python 3 standard library only.
"""
import json
import uuid

# Aura standard component -> LWR definition. Only attributes seen in real LWR bundles are carried; Search and Language Selector keep their Builder defaults
STANDARD = {
    "forceCommunity:richTextInline": ("community_builder:richTextEditor", lambda a: {"imageInfos": "", "richTextValue": a.get("richTextValue", "")}),
    # An LWR site stores its HTML Editor with an empty imageInfos beside the markup, so it is written the same way
    "forceCommunity:htmlBlock": ("community_builder:htmlEditor", lambda a: {"imageInfos": "", "richTextValue": a.get("richTextValue", "")}),
    "forceCommunity:searchBox": ("dxp_search:searchInput", lambda a: {}),
    "forceCommunity:languagePicker": ("dxp_base:languageSelector", lambda a: {}),
}
# dxp_layout:tabs as Builder drops it (attributes from a Builder-saved LWR bundle); tabsetConfig is added per tabset
TABS_DEFAULTS = {
    "activeTabBorderHighlightWeight": "2px", "activeTabTextEmphasis": "{\"bold\":true}",
    "activeTabTextStyle": "{\"textStyle\":\"paragraph1\",\"headingTag\":\"p\"}", "borderColor": "", "borderRadius": "0px",
    "borderWeight": "0px", "enableOverflowMenu": False, "imageFit": "cover", "imagePosition": "center center",
    "overflowIconColor": "rgb(116,116,116)", "overflowIconStyle": "down-arrow", "overflowMenuLabel": "More", "tabAlignment": "left",
    "tabBorderColor": "", "tabBorderRadius": "0px", "tabBorderWeight": "0px", "tabHoverBorderHighlightWeight": "1px",
    "tabLayout": "horizontal", "tabPadding": "12px", "tabTextStyle": "{\"textStyle\":\"paragraph1\",\"headingTag\":\"p\"}", "width": "100%"}
# Section settings only LWR has: carried on the Aura node as a private hint, written by lwr_section, dropped on Aura
LWR_SECTION_HINTS = ("sectionVerticalAlign", "maxContentWidth", "sectionColumnGutterWidth")
AURA_SECTION_DEFAULTS = {"background": "background: rgba(0,0,0,0)", "backgroundOverlay": "rgba(0,0,0,0.5)", "contentAreaWidth": 100, "sectionHeight": 32}
SEARCH_DEFAULTS = {"enableAutocomplete": True, "maxNumberOfResults": 6, "showContinueAction": False, "showTopics": False,
                   "crossObjectTypeaheadApiNames": [{"isPublic": True, "name": "KnowledgeArticleVersion"}]}


def id_maker(namespace):
    """Stable ids: the same names always give the same id, so a rerun with the same inputs writes the same files."""
    space = uuid.uuid5(uuid.NAMESPACE_URL, namespace)
    return lambda *parts: str(uuid.uuid5(space, "/".join(str(part) for part in parts)))


def aura_component(name, attributes, component_id, regions=None):
    node = {"componentAttributes": attributes, "componentName": name, "id": component_id, "renderPriority": "NEUTRAL", "renditionMap": {}, "type": "component"}
    if regions is not None:
        node["regions"] = regions
    return node


def aura_section(section_id, attributes, columns, make_id):
    """columns: [(width, [aura nodes])]. Region names are the column number, as Builder writes them."""
    config_columns, regions = [], []
    for index, (width, components) in enumerate(columns, start=1):
        column_id = make_id(section_id, "column", index)
        config_columns.append({"UUID": column_id, "columnKey": str(index), "columnName": f"Column {index}", "columnWidth": str(width), "seedComponents": []})
        regions.append({"components": components, "id": column_id, "regionLabel": f"Column {index}", "regionName": str(index), "renditionMap": {}, "type": "region"})
    merged = dict(AURA_SECTION_DEFAULTS, **{key: value for key, value in attributes.items() if key in AURA_SECTION_DEFAULTS})
    merged["sectionConfig"] = {"UUID": section_id, "columns": config_columns}
    node = aura_component("forceCommunity:section", merged, section_id, regions)
    node["_lwr"] = {key: value for key, value in attributes.items() if key in LWR_SECTION_HINTS}
    return node


def aura_tabset(tabset_id, tabs, active, make_id):
    """tabs: [(tabName, tabKey, [aura nodes])]"""
    config, regions = [], []
    for name, key, components in tabs:
        tab_id = make_id(tabset_id, "tab", key)
        config.append({"UUID": tab_id, "allowGuestUser": True, "locked": False, "seedComponents": [], "tabKey": key, "tabName": name})
        regions.append({"components": components, "id": tab_id, "regionLabel": name, "regionName": key, "renditionMap": {}, "type": "region"})
    return aura_component("forceCommunity:tabset", {"tabsetConfig": {"UUID": tabset_id, "activeTab": active or (tabs[0][1] if tabs else None), "useOverflowMenu": False, "tabs": config}}, tabset_id, regions)


AURA_RECORD, LWR_RECORD = "{!recordId}", "{!Route.recordId}"
# Experience Builder expands {!...} even inside a String property, so a binding kept for the component to resolve is stored
# with its braces JSON-escaped, the way the repeater's property editor writes it (formDynamicRepeaterModel serializeConfig)
ESCAPED_RECORD = "\\u007b!recordId\\u007d"


def lwr_component(node, make_id, route_record=False):
    """route_record: the page is an object's record page, so a component bound to the page record reads {!Route.recordId}
    (LWR's binding) instead of Aura's {!recordId}."""
    name = node["componentName"]
    source = node.get("componentAttributes") or {}
    if name == "forceCommunity:tabset":
        return lwr_tabs(node, make_id, route_record)
    if name in STANDARD:
        name, convert = STANDARD[name]
        attributes = convert(source)
    else:
        attributes = dict(source)
    if route_record and attributes.get("recordId") == AURA_RECORD:
        attributes["recordId"] = LWR_RECORD
    # A repeater's filter value {!recordId} is resolved by the component itself; a design block's text is left as written
    if name != "FlowToolKit:siteDesignBlock" and isinstance(attributes.get("properties"), str):
        attributes["properties"] = attributes["properties"].replace(AURA_RECORD, ESCAPED_RECORD)
    attributes["dxpStyle"] = {}
    return {"attributes": attributes, "definition": name, "id": make_id(node.get("id")), "type": "component"}


def lwr_tabs(node, make_id, route_record=False):
    config = node["componentAttributes"]["tabsetConfig"]
    regions = {region.get("regionName"): region for region in node.get("regions") or []}
    tabs, children = [], []
    for tab in config["tabs"]:
        tab_id = make_id(tab["UUID"])
        tabs.append({"UUID": tab_id, "tabName": tab["tabName"], "tabKey": tab["tabKey"], "locked": False, "allowGuestUser": True})
        region = regions.get(tab["tabKey"]) or {}
        children.append({"children": [lwr_component(item, make_id, route_record) for item in region.get("components") or []],
                         "id": tab_id, "name": tab["tabKey"], "title": tab["tabKey"], "type": "region"})
    attributes = dict(TABS_DEFAULTS, dxpStyle={}, tabsetConfig=json.dumps(
        {"UUID": make_id(config["UUID"]), "activeTab": config.get("activeTab"), "useOverflowMenu": None, "tabs": tabs}))
    return {"attributes": attributes, "children": children, "definition": "dxp_layout:tabs", "id": make_id(node.get("id")), "type": "component"}


def lwr_section(node, make_id, route_record=False):
    """An Aura forceCommunity:section as community_layout:section: same column widths, each component converted. Aura's background, height and width settings do not exist on LWR."""
    config = node["componentAttributes"]["sectionConfig"]
    regions = {region.get("regionName"): region for region in node.get("regions") or []}
    hints = node.get("_lwr") or {}
    lwr_columns, children = [], []
    for position, column in enumerate(config["columns"], 1):
        key = f"col{position}"
        lwr_columns.append({"UUID": make_id(column["UUID"]), "columnName": f"Column {position}", "columnKey": key, "columnWidth": column["columnWidth"], "seedComponents": None})
        region = regions.get(column["columnKey"]) or {}
        children.append({"children": [lwr_component(item, make_id, route_record) for item in region.get("components") or []],
                         "id": make_id(column["UUID"], "region"), "name": key, "title": f"Column {position}", "type": "region"})
    return {
        "attributes": {
            "backgroundImageConfig": "", "backgroundImageOverlay": "rgba(0,0,0,0)", "componentSpacerSize": "",
            "dxpStyle": {}, "layoutDirectionDesktop": "row", "layoutDirectionMobile": "column",
            "layoutDirectionTablet": "column", "maxContentWidth": hints.get("maxContentWidth", ""), "sectionColumnGutterWidth": hints.get("sectionColumnGutterWidth", ""),
            "sectionConfig": json.dumps({"UUID": make_id(config["UUID"]), "columns": lwr_columns}),
            "sectionMinHeight": "", "sectionVerticalAlign": hints.get("sectionVerticalAlign", "flex-start")},
        "children": children, "definition": "community_layout:section", "id": make_id(node.get("id")), "type": "component"}


def strip_private(node):
    """Drops the _lwr hints before an Aura node is written."""
    if isinstance(node, dict):
        return {key: strip_private(value) for key, value in node.items() if key != "_lwr"}
    if isinstance(node, list):
        return [strip_private(item) for item in node]
    return node
