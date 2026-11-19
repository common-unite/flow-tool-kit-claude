#!/usr/bin/env python3
"""The fallback wrapper: scaffold a record-page Lightning web component that shows one Flow Tool Kit form, with the record
form's Save button, or, with --autosave, saving each change as it is made and no Save button.

Most forms on a page need no component of their own: the package's Form (Component) or Form (Dynamic Component) is placed
and set up on the page. Write a wrapper only for autosave, which neither exposes as a page setting, or for a form baked
into the source on a Lightning record page, where Form (Component) can only name a saved Form Component.

Python 3 standard library only, so it runs in claude.ai chat's code sandbox as well as in Claude Code. It never touches
an org: it reads the form's JSON and writes files.

Read the JSON and say what the component will be (object, label, name, what the form needs in the org):
    python3 record_page_form.py inspect <form.json> [--json]

Write the component bundle, its Jest test, and the Jest stub for the package's record form:
    python3 record_page_form.py write <form.json> --lwc-dir <force-app/main/default/lwc>
                                     [--name <lwcName>] [--label <text>] [--site] [--autosave] [--force]

The same component for a saved Form Component, by name, so Form Builder edits show without a redeploy
(a Form Component record by its version name, <Name>_v0; a metadata component by its plain name):
    python3 record_page_form.py write --component-name <Name>_v0 --object <ObjectApiName>
                                     --label <text> --lwc-dir <force-app/main/default/lwc> [--site] [--autosave]

Add custom section components to the LWR site support component (creates it when missing):
    python3 record_page_form.py lwr-support --lwc-dir <force-app/main/default/lwc> c:feeSummarySection [...]

<form.json> is any of: the JSON Form Builder stores in a Form Component's FormConfigJSON field, the token from a Form
Component's Export action, or the JSON a Form (Dynamic Component) holds. Keys may carry the package prefix as
FlowToolKit__ or *__.

Exit codes: 0 done (warnings allowed), 1 errors found, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

NS = "FlowToolKit__"
STAR = "*__"
FTK_OBJECTS = {"Form_Submission__c", "Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c",
               "Form_Component__c", "Form_Submission_Stage__c", "Form_Submission_Answer__c"}
API_VERSION = "64.0"
RECORD_FORM_TAG = "flowtoolkit-lightning-record-form"   # the package's record form, Form (Component) in App Builder
RECORD_FORM_MODULE = "flowtoolkit/lightningRecordForm"  # the same component as Jest resolves it
SUPPORT_NAME = "customSectionsLwrSupport"               # shared with build-custom-lwc: one support component per project
LWC_NAME = re.compile(r"^[a-z][A-Za-z0-9]*$")
COMPONENT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
OBJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
HERE = pathlib.Path(__file__).resolve().parent
ICON = HERE.parent / "assets" / "flowtoolkit-icon.svg"
MAX_LABEL = 80
MAX_DESCRIPTION = 255
MAX_NAME = 40
ORG_KEYS = {"Id", "_Id", "_joined", "attributes"}  # the same keys the package's import leaves out


# ---- reading the JSON ------------------------------------------------------------------------------------------------

def local(key):
    """A key without the package prefix: '*__title__c' and 'FlowToolKit__title__c' both become 'title__c'."""
    for prefix in (STAR, NS):
        if isinstance(key, str) and key.startswith(prefix):
            return key[len(prefix):]
    return key


def get(node, name, default=None):
    """Read a key whatever prefix it was written with."""
    if isinstance(node, dict):
        for key in (STAR + name, NS + name, name):
            if key in node:
                return node[key]
    return default


def canonical_object(name):
    """The object's real API name: '*__Form_Submission__c' and 'Form_Submission__c' both become FlowToolKit__Form_Submission__c."""
    name = (name or "").strip().replace(STAR, NS)
    return NS + name if name in FTK_OBJECTS else name


def object_base(object_api_name):
    """'FlowToolKit__Form_Submission__c' -> 'FormSubmission', 'Account' -> 'Account'."""
    name = object_api_name
    if "__" in name and not name.endswith("__"):
        parts = name.split("__")
        # namespace__Name__c -> Name; Name__c -> Name
        name = parts[1] if len(parts) == 3 else parts[0]
    return re.sub(r"[^A-Za-z0-9]", "", name)


def clean_label(label):
    return re.sub(r"^\(Clone\)\s*", "", (label or "").strip())


def lower_first(text):
    return text[:1].lower() + text[1:]


def derive_name(object_api_name, label):
    """The component's API name: the object, then the label's words, camel case (Contact + Volunteer Profile -> contactVolunteerProfile)."""
    base = object_base(object_api_name)
    words = "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9]+", clean_label(label)))
    if words.lower().startswith(base.lower()):
        words = words[len(base):]
    name = lower_first(base + words) if words else lower_first(base) + "Form"
    if name[:1].isdigit() or not name:
        name = "form" + name
    return name[:MAX_NAME]


def unwrap(data):
    """Return (component dict or None, wrapper facts) for any of the shapes a form's JSON arrives in."""
    facts = {}
    if isinstance(data, dict) and isinstance(get(data, "FormConfigJSON__c"), str) and not get(data, "sections__r"):
        facts["source"] = "Form Component record"
        data = parse_text(get(data, "FormConfigJSON__c"))
    if isinstance(data, dict) and "formSelectionMode" in data:
        facts["source"] = "Form (Dynamic Component) settings"
        facts["wrapper_object"] = data.get("object") or None
        if data.get("formSelectionMode") == "component":
            facts["component_name"] = data.get("formQualifiedApiName") or None
            return None, facts
        inner = data.get("formJsonConfig")
        data = parse_text(inner) if isinstance(inner, str) else inner
    facts.setdefault("source", "Form Component JSON")
    return (data if isinstance(data, dict) else None), facts


def parse_text(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def walk(node, parent_key=None):
    """Every dict in the JSON with the key of the list or dict it sits in."""
    if isinstance(node, dict):
        yield node, parent_key
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from walk(value, local(key))
    elif isinstance(node, list):
        for item in node:
            yield from walk(item, parent_key)


def dependencies(component, object_api_name):
    """What the form needs in the org beyond this component: fields, custom sections, flows, nested components."""
    fields, lwcs, flows, nested = set(), set(), set(), set()
    for node, parent in walk(component):
        field = get(node, "fieldName__c")
        if isinstance(field, str) and field and parent in ("fields__r", None):
            obj = canonical_object(get(node, "Object__c") or object_api_name)
            fields.add(f"{obj}.{field.replace(STAR, NS)}")
        lwc = get(node, "lwcComponentName__c")
        if isinstance(lwc, str) and lwc.strip():
            lwcs.add(lwc.strip())
        flow = get(node, "flowApiName__c")
        if isinstance(flow, str) and flow.strip():
            flows.add(flow.strip().replace(STAR, NS))
        for key in ("formComponent__c", "Default_Table_Form__c", "Default_Table_Form_bulk__c"):
            value = get(node, key)
            if isinstance(value, str) and value.strip() and not value.strip().startswith("{"):
                nested.add(value.strip())
    return {"fields": sorted(fields), "lwc_sections": sorted(lwcs), "flows": sorted(flows), "components": sorted(nested)}


def inspect(text, name=None, label=None, component_name=None, object_name=None):
    """Read the form JSON (or a component name) and return the plan for the component, with findings."""
    findings = []

    def add(severity, message):
        findings.append({"severity": severity, "message": message})

    plan = {"mode": "json", "component": None, "deps": {"fields": [], "lwc_sections": [], "flows": [], "components": []}}
    if component_name:
        plan.update(mode="name", source="Form Component name", component_name=component_name)
        obj = canonical_object(object_name or "")
        if not obj:
            add("error", "--object is required with --component-name: the object the component is built on")
        if not label:
            add("error", "--label is required with --component-name: the name admins see in App Builder")
        if not COMPONENT_NAME.match(component_name):
            add("error", f"{component_name!r} is not a Form Component API name (letters, digits and underscores)")
        description = None
        qualified = component_name
    else:
        data = parse_text(text.lstrip("﻿"))
        if data is None:
            add("error", "the text is not JSON. Paste the whole value, from the first { to the last }")
            return plan, findings
        component, facts = unwrap(data)
        plan["source"] = facts["source"]
        if facts.get("component_name"):
            plan.update(mode="name", component_name=facts["component_name"])
            add("info", "these settings pick a saved Form Component by name, so the component will name it rather than hold its JSON")
            component = None
        elif component is None:
            add("error", "no form in the JSON: expected Form Builder's component JSON, an Export token or a Form (Dynamic Component) setting")
            return plan, findings
        plan["component"] = component
        root = component or {}
        form_object = get(root, "Form_Object__r")
        obj = canonical_object(object_name or get(root, "ObjectApiName__c") or get(form_object, "QualifiedApiName")
                               or facts.get("wrapper_object") or "")
        if facts.get("wrapper_object") and canonical_object(facts["wrapper_object"]) != obj:
            add("warning", f"the settings name {facts['wrapper_object']} but the form is built on {obj}; the component uses {obj}")
        if not obj:
            add("error", "the JSON names no object (ObjectApiName__c). Export the component again, or pass --object")
        label = label or clean_label(root.get("Label") or get(root, "Label__c") or "")
        description = get(root, "Description__c") or root.get("description")
        qualified = (re.sub(r"_v\d+$", "", root.get("QualifiedApiName") or get(root, "QualifiedApiName__c") or "")
                     or plan.get("component_name") or None)
        if component is not None:
            if not get(root, "sections__r"):
                add("error", "the form has no sections, so it would render nothing")
            if not label:
                add("warning", "the JSON has no Label; pass --label with the name admins should see in App Builder")
            sections = get(root, "sections__r") or []
            if get(root, "Version__c") is None or not all(isinstance(x, dict) and "sectionVerticalPadding" in x for x in sections):
                add("warning", "this JSON was not saved by Form Builder (no Version__c, or sections without the layout keys the "
                               "save adds), so field widths can render wrong. Save the component in the org (Form Builder, or "
                               "build-form-component's import), then use its Export token")
            if get(root, "Active__c") is False:
                add("warning", "the component is marked inactive in Form Builder; check it is the version you mean")
            plan["deps"] = dependencies(component, obj)

    if plan["mode"] == "name" and plan.get("component_name") and not re.search(r"_v\d+$", plan["component_name"]):
        add("warning", f"{plan['component_name']!r} is right for a metadata Form Component; a Form Component record is named by "
                       f"its version, {plan['component_name']}_v0, and renders nothing under its plain name")
    if obj and not OBJECT_NAME.match(obj):
        add("error", f"{obj!r} is not an object API name")
    label = clean_label(label or (qualified or "").replace("_", " "))
    if len(label) > MAX_LABEL:
        add("warning", f"the label is longer than {MAX_LABEL} characters; it was shortened")
        label = label[:MAX_LABEL].rstrip()
    lwc_name = name or (derive_name(obj, label) if obj else None)
    if lwc_name and not LWC_NAME.match(lwc_name):
        add("error", f"{lwc_name!r} is not a usable component name: start with a lowercase letter, letters and digits only")
    if lwc_name and len(lwc_name) > MAX_NAME:
        add("error", f"{lwc_name!r} is longer than {MAX_NAME} characters; pass a shorter --name")
    for lwc in plan["deps"]["lwc_sections"]:
        if ":" not in lwc:
            add("warning", f"custom section {lwc!r} has no namespace; the form expects the full name, such as c:{lwc}")
    plan.update(object=obj or None, label=label or None, name=lwc_name, description=description, qualified_name=qualified,
                class_name=(lwc_name[:1].upper() + lwc_name[1:]) if lwc_name else None)
    return plan, findings


# ---- writing the bundle ----------------------------------------------------------------------------------------------

def baked_config(component, object_api_name):
    """The form as the package stores it (*__ prefix), with its object written out so the record form can render it."""
    text = json.dumps(component, ensure_ascii=False)
    text = text.replace(NS, STAR)
    config = json.loads(text)
    if not get(config, "ObjectApiName__c"):
        config = {**config, STAR + "ObjectApiName__c": object_api_name.replace(NS, STAR)}
    return strip_org_values(config)


def strip_org_values(node):
    """Record Ids and builder-only keys belong to the org the form came from; the component carries the design only."""
    if isinstance(node, dict):
        return {k: strip_org_values(v) for k, v in node.items() if k not in ORG_KEYS}
    if isinstance(node, list):
        return [strip_org_values(v) for v in node]
    return node


def meta_description(plan, autosave=False):
    first = f"Shows the {plan['label']} form on {object_label(plan['object'])} record pages"
    first += " and saves each change as it is made." if autosave else "."
    extra = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", plan.get("description") or "")).strip()
    text = f"{first} {extra}".strip() if extra and extra.lower() not in first.lower() else first
    return text if len(text) <= MAX_DESCRIPTION else text[:MAX_DESCRIPTION - 1].rsplit(" ", 1)[0] + "."


def object_label(object_api_name):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", object_base(object_api_name))


def xml_escape(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_js(plan):
    by_json = plan["mode"] == "json"
    lines = ["import { LightningElement, api } from 'lwc';"]
    if by_json:
        lines.append(f"import FORM_CONFIG from './{plan['name']}Config';")
    lines += [
        "",
        f"// The form is built on {plan['object']}; the component is placed only on its record pages.",
        f"const OBJECT_API_NAME = '{plan['object']}';",
    ]
    if not by_json:
        lines.append(f"const FORM_COMPONENT_NAME = '{plan['component_name']}';")
    lines += [
        "",
        "// Flow Tool Kit's record form loads the record, lays out the form, validates and saves; this component only hands it the record and the form.",
        f"export default class {plan['class_name']} extends LightningElement {{",
        "    @api recordId; // set by the record page; on a site page, bound in Experience Builder",
        "",
        "    objectApiName = OBJECT_API_NAME;",
    ]
    lines.append("    formConfig = FORM_CONFIG;" if by_json else "    formComponentName = FORM_COMPONENT_NAME;")
    lines += ["}", ""]
    return "\n".join(lines)


def render_html(plan, autosave=False):
    form = ("            form-json-config={formConfig}" if plan["mode"] == "json"
            else "            form-qualified-api-name={formComponentName}")
    # By default the record form shows its Save button. Autosave saves each valid change and needs no button.
    attributes = ["record-id={recordId}", "object-api-name={objectApiName}", form.strip(), "check-record-access"]
    if autosave:
        attributes += ["auto-save", "hide-buttons"]
    lines = ["<template>", f"    <{RECORD_FORM_TAG}"]
    lines += [f"            {a}" for a in attributes[:-1]] + [f"            {attributes[-1]}>"]
    return "\n".join(lines + [f"    </{RECORD_FORM_TAG}>", "</template>", ""])


def render_config(plan):
    config = baked_config(plan["component"], plan["object"])
    body = json.dumps(config, ensure_ascii=False, indent=4)
    return "\n".join([
        f"// The {plan['label']} form from Form Builder, kept with the component. To change the form, export it again and rerun record_page_form.py write.",
        f"const FORM = {body};",
        "",
        "export default JSON.stringify(FORM);",
        "",
    ])


def render_meta(plan, site, autosave=False):
    targets = ["lightning__RecordPage"] + (["lightningCommunity__Page", "lightningCommunity__Default"] if site else [])
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">',
        f"    <apiVersion>{API_VERSION}</apiVersion>",
        f"    <description>{xml_escape(meta_description(plan, autosave))}</description>",
        "    <isExposed>true</isExposed>",
        f"    <masterLabel>{xml_escape(plan['label'])}</masterLabel>",
        "    <targets>",
        *[f"        <target>{t}</target>" for t in targets],
        "    </targets>",
        "    <targetConfigs>",
        '        <targetConfig targets="lightning__RecordPage">',
        "            <objects>",
        f"                <object>{plan['object']}</object>",
        "            </objects>",
        "        </targetConfig>",
    ]
    if site:
        out += [
            '        <targetConfig targets="lightningCommunity__Default">',
            '            <property name="recordId" type="String" label="Record Id" default="{!recordId}"'
            f' description="The {xml_escape(object_label(plan["object"]))} record the form shows. Keep {{!recordId}} on Aura and LWR sites; {{!Route.recordId}} also works on LWR."/>',
            "        </targetConfig>",
        ]
    out += ["    </targetConfigs>", "</LightningComponentBundle>", ""]
    return "\n".join(out)


def render_test(plan, autosave=False):
    kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", plan["name"]).lower()
    lines = [
        "import { createElement } from 'lwc';",
        f"import {plan['class_name']} from 'c/{plan['name']}';",
    ]
    if plan["mode"] == "json":
        lines.append(f"import FORM_CONFIG from '../{plan['name']}Config';")
    lines += [
        "",
        f"const OBJECT_API_NAME = '{plan['object']}';",
        "const RECORD_ID = '001000000000001AAA';",
        "",
        f"function mount(recordId = RECORD_ID) {{",
        f"    const element = createElement('c-{kebab}', {{ is: {plan['class_name']} }});",
        "    element.recordId = recordId;",
        "    document.body.appendChild(element);",
        f"    return element.shadowRoot.querySelector('{RECORD_FORM_TAG}');",
        "}",
        "",
        f"describe('c-{kebab}', () => {{",
        "    afterEach(() => {",
        "        while (document.body.firstChild) document.body.removeChild(document.body.firstChild);",
        "    });",
        "",
        "    it('hands the page record and its object to the Flow Tool Kit record form', () => {",
        "        const form = mount();",
        "        expect(form).not.toBeNull();",
        "        expect(form.recordId).toBe(RECORD_ID);",
        "        expect(form.objectApiName).toBe(OBJECT_API_NAME);",
        "    });",
        "",
    ]
    if autosave:
        lines += [
            "    it('saves each change as it is made, with no Save button', () => {",
            "        const form = mount();",
            "        expect(form.autoSave).toBe(true);",
            "        expect(form.hideButtons).toBe(true);",
            "    });",
        ]
    else:
        lines += [
            "    it('shows the Save button and saves only when it is pressed', () => {",
            "        const form = mount();",
            "        expect(form.hideButtons).toBe(false);",
            "        expect(form.autoSave).toBe(false);",
            "    });",
        ]
    lines += [
        "",
        "    it('asks the record form to check edit access, so people who may only read the record and site guests see it read only', () => {",
        "        expect(mount().checkRecordAccess).toBe(true);",
        "    });",
        "",
        "    it('follows the page when the record changes', async () => {",
        "        const element = createElement('c-" + kebab + "', { is: " + plan["class_name"] + " });",
        "        element.recordId = RECORD_ID;",
        "        document.body.appendChild(element);",
        "        element.recordId = '001000000000002AAA';",
        "        await Promise.resolve();",
        f"        expect(element.shadowRoot.querySelector('{RECORD_FORM_TAG}').recordId).toBe('001000000000002AAA');",
        "    });",
        "",
    ]
    if plan["mode"] == "json":
        lines += [
            "    it('hands over the baked form, built on this object, as JSON the package can read', () => {",
            "        const form = mount();",
            "        expect(form.formJsonConfig).toBe(FORM_CONFIG);",
            "        const parsed = JSON.parse(FORM_CONFIG.replaceAll('*__', 'FlowToolKit__'));",
            "        expect(parsed.FlowToolKit__ObjectApiName__c).toBe(OBJECT_API_NAME);",
            "        expect(Array.isArray(parsed.FlowToolKit__sections__r)).toBe(true);",
            "        expect(parsed.FlowToolKit__sections__r.length).toBeGreaterThan(0);",
            "    });",
        ]
    else:
        lines += [
            "    it('names the saved Form Component, so Form Builder edits show without a redeploy', () => {",
            "        const form = mount();",
            f"        expect(form.formQualifiedApiName).toBe('{plan['component_name']}');",
            "        expect(form.formJsonConfig).toBeUndefined();",
            "    });",
        ]
    lines += ["});", ""]
    return "\n".join(lines)


STUB = """import { LightningElement, api } from 'lwc';

// Stands in for Flow Tool Kit's record form in Jest; the real one exists only in an org with the package installed.
export default class LightningRecordForm extends LightningElement {
    @api recordId;
    @api objectApiName;
    @api formJsonConfig;
    @api formQualifiedApiName;
    @api autoSave = false;
    @api hideButtons = false;
    @api checkRecordAccess = false;
    @api readOnly = false;
}
"""

JEST_CONFIG = """const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    moduleNameMapper: {
        ...jestConfig.moduleNameMapper,
        // The template compiler lowercases the namespace of <flowtoolkit-lightning-record-form>, so the stub is mapped under that name.
        '^flowtoolkit/lightningRecordForm$': '<rootDir>/jest/stubs/flowtoolkit/lightningRecordForm/lightningRecordForm'
    }
};
"""

JEST_MAPPING = "'^flowtoolkit/lightningRecordForm$': '<rootDir>/jest/stubs/flowtoolkit/lightningRecordForm/lightningRecordForm'"


def project_root(lwc_dir):
    """The folder holding force-app (or the nearest one with sfdx-project.json); None when it cannot be told."""
    for parent in [lwc_dir, *lwc_dir.parents]:
        if (parent / "sfdx-project.json").exists():
            return parent
    parts = lwc_dir.resolve().parts
    if "force-app" in parts:
        return pathlib.Path(*parts[:parts.index("force-app")])
    return None


def write_jest_support(lwc_dir):
    """The stub and the mapping Jest needs. Returns notes for the person."""
    notes = []
    root = project_root(lwc_dir)
    if root is None:
        return ["could not find the project root, so the Jest stub was not written; copy it from the skill's assets"]
    stub = root / "jest" / "stubs" / "flowtoolkit" / "lightningRecordForm" / "lightningRecordForm.js"
    if not stub.exists():
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(STUB, encoding="utf-8")
        notes.append(f"wrote the Jest stub {stub.relative_to(root)}")
    config = root / "jest.config.js"
    if not config.exists():
        config.write_text(JEST_CONFIG, encoding="utf-8")
        notes.append("wrote jest.config.js with the mapping for the package's record form")
    elif "flowtoolkit/lightningRecordForm" not in config.read_text(encoding="utf-8"):
        notes.append(f"add this line to moduleNameMapper in jest.config.js: {JEST_MAPPING}")
    return notes


def write_bundle(plan, lwc_dir, site=False, force=False, autosave=False):
    folder = lwc_dir / plan["name"]
    if folder.exists() and not force:
        raise SystemExit(f"{folder} already exists. Pass --name for a new component, or --force to replace this one")
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        f"{plan['name']}.js": render_js(plan),
        f"{plan['name']}.html": render_html(plan, autosave),
        f"{plan['name']}.js-meta.xml": render_meta(plan, site, autosave),
        f"__tests__/{plan['name']}.test.js": render_test(plan, autosave),
    }
    if plan["mode"] == "json":
        files[f"{plan['name']}Config.js"] = render_config(plan)
    elif (folder / f"{plan['name']}Config.js").exists():
        (folder / f"{plan['name']}Config.js").unlink()
    for rel, content in files.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if ICON.exists():
        shutil.copyfile(ICON, folder / f"{plan['name']}.svg")
    return folder, sorted(files) + ([f"{plan['name']}.svg"] if ICON.exists() else [])


# ---- the LWR support component ---------------------------------------------------------------------------------------

SUPPORT_META = """<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>64.0</apiVersion>
    <description>Renders nothing. Place it in the Theme Footer of every LWR site that shows a form with a custom section component, beside FlowToolKit LWR Support, then publish the site. It makes the site include the custom section components, which the form loads only by name. Add an import line here for each new custom section component.</description>
    <isExposed>true</isExposed>
    <masterLabel>Custom Sections LWR Support</masterLabel>
    <targets>
        <target>lightningCommunity__Page</target>
        <target>lightningCommunity__Default</target>
    </targets>
</LightningComponentBundle>
"""
SUPPORT_JS_HEAD = ("import { LightningElement } from 'lwc';\n"
                   "// Flow Tool Kit loads section components by name, which an LWR site's publisher cannot see; these imports make it bundle them.\n")
SUPPORT_JS_TAIL = "\nexport default class CustomSectionsLwrSupport extends LightningElement {}\n"


def lwr_support(lwc_dir, components):
    """Create or extend the support component so an LWR site bundles each custom section component. Returns the imports added."""
    modules = []
    for name in components:
        name = name.strip()
        if not name or ":" not in name:
            raise SystemExit(f"{name!r}: give the full name, such as c:feeSummarySection")
        namespace, bare = name.split(":", 1)
        if namespace.lower() == "flowtoolkit":
            continue  # the package's own sections come with FlowToolKit LWR Support
        modules.append(f"{namespace}/{bare}")
    folder = lwc_dir / SUPPORT_NAME
    folder.mkdir(parents=True, exist_ok=True)
    js = folder / f"{SUPPORT_NAME}.js"
    existing = js.read_text(encoding="utf-8") if js.exists() else SUPPORT_JS_HEAD + SUPPORT_JS_TAIL
    present = set(re.findall(r"^import '([^']+)';", existing, re.M))
    added = [m for m in dict.fromkeys(modules) if m not in present]
    if added:
        block = "".join(f"import '{m}';\n" for m in added)
        marker = existing.find("\nexport default")
        existing = existing[:marker] + "\n" + block.rstrip("\n") + existing[marker:] if marker >= 0 else existing + block
        existing = re.sub(r"\n{3,}", "\n\n", existing)
    js.write_text(existing, encoding="utf-8")
    (folder / f"{SUPPORT_NAME}.html").write_text("<template></template>\n", encoding="utf-8")
    meta = folder / f"{SUPPORT_NAME}.js-meta.xml"
    if not meta.exists():
        meta.write_text(SUPPORT_META, encoding="utf-8")
    return added


# ---- command line ----------------------------------------------------------------------------------------------------

def print_findings(findings):
    order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda f: order[f["severity"]]):
        print(f"{f['severity'].upper():7} {f['message']}")
    return sum(1 for f in findings if f["severity"] == "error")


def summary(plan):
    deps = plan["deps"]
    rows = [
        ("Object", plan.get("object")),
        ("Label in App Builder", plan.get("label")),
        ("Component name", f"c:{plan['name']}" if plan.get("name") else None),
        ("Form", f"Form Component {plan['component_name']}, by name" if plan["mode"] == "name"
         else f"{plan.get('qualified_name') or 'the pasted form'}, baked into the component ({plan.get('source')})"),
        ("Description", plan.get("description")),
    ]
    out = [f"{k:22} {v}" for k, v in rows if v]
    if deps["fields"]:
        out.append(f"{'Fields it shows':22} {len(deps['fields'])}: " + ", ".join(deps["fields"]))
    if deps["lwc_sections"]:
        out.append(f"{'Custom sections':22} " + ", ".join(deps["lwc_sections"]) + "  (LWR sites: run lwr-support)")
    if deps["flows"]:
        out.append(f"{'Flows it launches':22} " + ", ".join(deps["flows"]) + "  (grant them to every audience)")
    if deps["components"]:
        out.append(f"{'Components it embeds':22} " + ", ".join(deps["components"]) + "  (must exist in the org)")
    return "\n".join(out)


def read_input(path):
    if path in (None, "-"):
        return sys.stdin.read()
    try:
        return pathlib.Path(path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ins = sub.add_parser("inspect", help="say what the component will be")
    wr = sub.add_parser("write", help="write the component bundle and its Jest test")
    for p in (ins, wr):
        p.add_argument("form", nargs="?", help="the form's JSON file, or - for standard input")
        p.add_argument("--component-name", help="name a saved Form Component instead of baking JSON: <Name>_v0 for a record, the plain name for metadata")
        p.add_argument("--object", help="the object (needed with --component-name; otherwise read from the JSON)")
        p.add_argument("--name", help="the component's API name (default: derived from the object and label)")
        p.add_argument("--label", help="the name admins see in App Builder (default: the form's Label)")
    ins.add_argument("--json", action="store_true")
    wr.add_argument("--lwc-dir", required=True, help="the project's lwc folder, such as force-app/main/default/lwc")
    wr.add_argument("--site", action="store_true", help="also expose it on Experience Cloud pages (Aura and LWR)")
    wr.add_argument("--autosave", action="store_true",
                    help="save each valid change as it is made and hide the Save button (off by default: the form shows its Save button)")
    wr.add_argument("--force", action="store_true", help="replace a component of the same name")
    sup = sub.add_parser("lwr-support", help="add custom section components to the LWR site support component")
    sup.add_argument("--lwc-dir", required=True)
    sup.add_argument("components", nargs="+", help="full names, such as c:feeSummarySection")
    args = parser.parse_args(argv)

    if args.command == "lwr-support":
        added = lwr_support(pathlib.Path(args.lwc_dir), args.components)
        print(f"{SUPPORT_NAME}: " + (("added " + ", ".join(added)) if added else "already imports them"))
        print("Place it in the Theme Footer of each LWR site that shows the form, beside FlowToolKit LWR Support, then publish.")
        return 0

    if not args.component_name and not args.form:
        parser.error("give the form's JSON file, or --component-name with --object and --label")
    text = "" if args.component_name else read_input(args.form)
    plan, findings = inspect(text, args.name, args.label, args.component_name, args.object)

    if args.command == "inspect" and args.json:
        out = {k: v for k, v in plan.items() if k != "component"}
        print(json.dumps({"plan": out, "findings": findings}, indent=1))
        return 1 if any(f["severity"] == "error" for f in findings) else 0

    errors = print_findings(findings)
    if errors:
        print(f"{errors} error(s): nothing written")
        return 1
    print(summary(plan))
    if args.command == "inspect":
        return 0
    folder, files = write_bundle(plan, pathlib.Path(args.lwc_dir), site=args.site, force=args.force, autosave=args.autosave)
    print(f"\nWrote {folder}: " + ", ".join(files))
    print("Saving: " + ("autosave, each valid change as it is made, no Save button" if args.autosave
                        else "the Save button (pass --autosave to save each change as it is made)"))
    for note in write_jest_support(pathlib.Path(args.lwc_dir)):
        print(note)
    if plan["deps"]["lwc_sections"] and args.site:
        print("LWR sites: the form has custom sections. Run: record_page_form.py lwr-support --lwc-dir "
              f"{args.lwc_dir} " + " ".join(plan["deps"]["lwc_sections"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
