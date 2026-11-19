#!/usr/bin/env python3
"""The new fields a plan needs, as metadata to deploy before the template is built, so the form saves end to end.

    python3 newfields.py <plan.json> --out <project-dir> [--permission-set <API name>]

form-design marks a field it proposes with "new_field": true (and lists it in the plan's questions). This writes one
CustomField file per new field, on the object the plan names (Form Submission, or the object of a component in a paid
org), and one permission set that grants Read and Edit on all of them, for the people who fill in the form (guest
user, portal users or staff). Then deploy with the Salesforce CLI from Claude Code:

    sf project deploy start --source-dir <project-dir>/force-app/main/default/objects <project-dir>/force-app/main/default/permissionsets --target-org <org-alias>

Each field gets a description at creation (the documentation standard): what the question captures and where it is
used. On Form Submission there is no inline help by default, because a respondent can see it. The field type comes from
the control; a field the plan's control cannot type (an Address, a Repeater) is refused with the reason.
Check each name first with org-catalog's name-check: never create a field with the name of a packaged one.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

N = "FlowToolKit__"
PACKAGE_OBJECTS = {"Form_Submission__c", "Form_Template__c"}


def object_name(obj: str) -> str:
    obj = obj.replace("*__", N)
    return N + obj if obj in PACKAGE_OBJECTS else obj


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def field_type(field: dict) -> tuple[str, str]:
    """(metadata type, extra XML) for a plan field's control and variant."""
    control, variant = field.get("control") or "TextInput", field.get("variant") or "standard"
    options = [o.get("value", o.get("label")) if isinstance(o, dict) else o for o in field.get("options") or []]
    values = "".join(f"<value><fullName>{esc(v)}</fullName><default>false</default><label>{esc(v)}</label></value>" for v in options)
    picklist = f"<valueSet><restricted>true</restricted><valueSetDefinition><sorted>false</sorted>{values}</valueSetDefinition></valueSet>"
    if control == "Checkbox":
        return "Checkbox", "<defaultValue>false</defaultValue>"
    if control == "Picklist":
        return "Picklist", picklist
    if control == "MultiPicklist":
        return "MultiselectPicklist", picklist + f"<visibleLines>{min(max(len(options), 3), 10)}</visibleLines>"
    if control == "TextArea":
        return "LongTextArea", "<length>32768</length><visibleLines>5</visibleLines>"
    if control == "NumberInput":
        return ("Currency", "<precision>16</precision><scale>2</scale>") if variant == "currency" else ("Number", "<precision>18</precision><scale>2</scale>")
    if control == "DateInput":
        return {"time": "Time", "datetime": "DateTime"}.get(variant, "Date"), ""
    if control == "FormattedInput":
        return {"email": "Email", "phone": "Phone", "url": "Url"}.get(variant, "Text"), "" if variant in ("email", "phone", "url") else "<length>255</length>"
    if control in ("SignaturePad", "ImageUpload"):
        return "Html", "<length>131072</length><visibleLines>10</visibleLines>"
    if control == "FileUpload":
        return "LongTextArea", "<length>32768</length><visibleLines>3</visibleLines>"
    if control == "TextInput":
        return "Text", "<length>255</length>"
    raise ValueError(f"{field.get('field')}: a {control} cannot be a single new field; build it as its own section")


def description(field: dict, form: str) -> str:
    text = field.get("description") or (f"Answer to \"{field.get('label') or field['field']}\" on the {form} form.")
    placement = str(field.get("placement") or "")
    if placement.startswith("mapped:"):
        text += " " + placement.split(":", 1)[1].strip().capitalize() + "."
    return re.sub(r"\s+", " ", text).strip()[:1000]


def field_xml(field: dict, form: str) -> str:
    kind, extra = field_type(field)
    name = field["field"].replace("*__", "")
    label = (field.get("short_label") or field.get("label") or name.removesuffix("__c").replace("_", " "))[:40]
    help_text = f"<inlineHelpText>{esc(field['help_text'][:255])}</inlineHelpText>" if field.get("help_text") else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n'
            f"    <fullName>{esc(name)}</fullName>\n    <description>{esc(description(field, form))}</description>\n"
            f"    {help_text}<externalId>false</externalId>\n    <label>{esc(label)}</label>\n"
            f"    <required>false</required>\n    <trackHistory>false</trackHistory>\n    <type>{kind}</type>\n    {extra}\n"
            "</CustomField>\n").replace("    \n", "")


def new_fields(plan: dict) -> list[tuple[str, dict]]:
    """(object, field) for every new field in the plan, once each."""
    components = {c.get("key"): c for c in plan.get("components") or []}
    out, seen = [], set()
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            component = components.get(section.get("component")) or {}
            for field in section.get("fields") or []:
                if not field.get("new_field"):
                    continue
                obj = object_name(field.get("object") or component.get("object") or section.get("object") or "Form_Submission__c")
                key = (obj, field["field"])
                if key not in seen:
                    seen.add(key)
                    out.append((obj, field))
    return out


def permission_set_xml(label: str, entries: list[tuple[str, dict]]) -> str:
    perms = "".join(f"    <fieldPermissions>\n        <editable>true</editable>\n        <field>{esc(obj)}.{esc(f['field'])}</field>\n"
                    "        <readable>true</readable>\n    </fieldPermissions>\n" for obj, f in sorted(entries, key=lambda e: (e[0], e[1]["field"])))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">\n'
            f"    <description>{esc(f'Read and edit on the fields the {label} form added. Assign it to the people who fill in the form: the site guest user, portal users or staff.')}</description>\n"
            f"{perms}    <hasActivationRequired>false</hasActivationRequired>\n    <label>{esc((label + ' Form Fields')[:80])}</label>\n"
            "</PermissionSet>\n")


def write(plan: dict, out: pathlib.Path, permission_set: str | None = None) -> list[str]:
    form = (plan.get("template") or {}).get("Name") or "this"
    entries = new_fields(plan)
    written = []
    base = out / "force-app" / "main" / "default"
    for obj, field in entries:
        path = base / "objects" / obj / "fields" / f"{field['field']}.field-meta.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(field_xml(field, form))
        written.append(str(path))
    if entries:
        name = permission_set or re.sub(r"[^A-Za-z0-9]+", "_", form).strip("_")[:60] + "_Form_Fields"
        path = base / "permissionsets" / f"{name}.permissionset-meta.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(permission_set_xml(form, entries))
        written.append(str(path))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the plan's new fields and their permission set as metadata")
    parser.add_argument("plan")
    parser.add_argument("--out", required=True, help="the project folder (an SFDX project), where force-app/ is written")
    parser.add_argument("--permission-set", help="the permission set's API name (default: <form>_Form_Fields)")
    args = parser.parse_args(argv)
    plan = json.loads(pathlib.Path(args.plan).read_text())
    try:
        written = write(plan, pathlib.Path(args.out), args.permission_set)
    except ValueError as error:
        sys.exit(f"newfields: {error}")
    print(json.dumps({"written": written, "next": "review the files, then deploy them (sf project deploy start) and run the build"} if written
                     else {"written": [], "next": "the plan has no new fields"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
