#!/usr/bin/env python3
"""Check how a new conversion flow is wired to Form Templates before anyone types it into Setup.

    python3 wiring_check.py <wiring.json | mapping-spec.json> [--json]

A new conversion flow runs only when a Conversion Map Flow picklist names it. The picklist VALUE (its API name) must be
exactly the flow's API name, because the package reads the value as the flow to run; the LABEL is what admins pick, so
it should be friendly. This checks the `wiring` block (SKILL.md Step 6, references/work-list.md) for:

  - every picklist value equal to its flow's API name, character for character (a label typed as the value, a case
    difference, a missing or extra namespace prefix, stray spaces: each is a problem, named);
  - a friendly label (no underscores, not the API name);
  - a section value included under the Conversion Rule values it serves (the section picklist depends on Conversion Rule);
  - every Form Template default and section override naming a value that exists (Default, or one added here);
  - section overrides only on Repeater or Table sections, whose rows are the only ones that read them;
  - a Repeater or Table section left on Default, under a rule the template overrides: its rows run the packaged default,
    not the template's flow.

mapping_plan.py runs the same check when mapping-spec.json has a `wiring` key. Standard library only. Exit 1 on problems.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

N = "FlowToolKit__"
SECTION_FIELD = "Form_Template_Page_Section__c.Conversion_Map_Flow__c"
# Form Template field -> (what it converts, the Form Template Conversion Mapping Default record used on Default)
TEMPLATE_FIELDS = {
    "Conversion_Map_Flow_Controller__c": ("the controller", "Controller"),
    "Conversion_Map_Flow_Contact1__c": ("Contact 1", "Primary_Contact"),
    "Conversion_Map_Flow_Contact2__c": ("Contact 2", "Alternate_Contact"),
    "Conversion_Map_Flow_Lead1__c": ("Lead 1", "Primary_Lead"),
    "Conversion_Map_Flow_Lead2__c": ("Lead 2", "Alternate_Lead"),
    "Conversion_Map_Flow_Account__c": ("Account", "Account"),
    "Conversion_Map_Flow_Opportunity__c": ("Opportunity", "Opportunity"),
    "Conversion_Map_Flow_Case__c": ("Case", "Case"),
    "Conversion_Map_Flow_CampaignMember__c": ("Campaign Member", "CampaignMember"),
    "Conversion_Map_Flow_FileUpload__c": ("File Upload", "FileUpload"),
    "Conversion_Map_Flow_Order__c": ("Order", "Order"),
}
# Section Conversion Rule values (the controlling field) and the template field for the same rule
SECTION_RULES = {
    "Contact1": "Conversion_Map_Flow_Contact1__c",
    "Contact1 \U0001f449 Set Mailing Address": "Conversion_Map_Flow_Contact1__c",
    "Contact1 \U0001f449 Set Other Address": "Conversion_Map_Flow_Contact1__c",
    "Contact2": "Conversion_Map_Flow_Contact2__c",
    "Contact2 \U0001f449 Set Mailing Address": "Conversion_Map_Flow_Contact2__c",
    "Contact2 \U0001f449 Set Other Address": "Conversion_Map_Flow_Contact2__c",
    "Lead1": "Conversion_Map_Flow_Lead1__c",
    "Lead2": "Conversion_Map_Flow_Lead2__c",
    "Case": "Conversion_Map_Flow_Case__c",
}
ROW_TYPES = ("Repeater", "Table")


def bare(name: str | None) -> str:
    return (name or "").replace(N, "")


def field_key(field: str | None) -> str | None:
    """The field as Object.Field without the package prefix, or None when it is not a Conversion Map Flow field."""
    text = bare((field or "").strip())
    if "." in text:
        obj, _, name = text.partition(".")
    else:
        obj, name = ("Form_Template_Page_Section__c" if text == "Conversion_Map_Flow__c" else "Form_Template__c"), text
    key = f"{obj}.{name}"
    if key == SECTION_FIELD or (obj == "Form_Template__c" and name in TEMPLATE_FIELDS):
        return key
    return None


def value_problem(value: str, flow: str, label: str | None) -> str | None:
    """Why a picklist value is not the flow's API name, or None when it is exactly."""
    if value == flow:
        return None
    if label and value == label:
        return "the label was typed as the value"
    if value.strip() == flow:
        return "the value has spaces around it"
    if value.lower() == flow.lower():
        return "the case differs (API names are case-sensitive here)"
    if flow.startswith(N) and value == bare(flow):
        return f"the flow is packaged, so the value needs its {N} prefix"
    if value.startswith(N) and bare(value) == flow:
        return f"your own flow has no namespace, so the value must not start with {N}"
    if " " in value or "|" in value or "/" in value:
        return "it reads like a label, not an API name"
    return "it is not the flow's API name"


def check_label(label: str | None, value: str) -> str | None:
    if not label:
        return "no label: give it a friendly one admins will recognise (Primary Contact, Child / Minor)"
    if label == value or "_" in label:
        return f"label {label!r} reads like an API name: use plain words with no underscores"
    return None


def check(wiring: dict) -> dict:
    """Problems, warnings and the resolved settings for a `wiring` block."""
    out = {"problems": [], "warnings": [], "values": [], "template": {}, "sections": []}
    flows = wiring.get("flows")  # optional: {qualified API name: {"active": bool}} from the org
    added: dict = {}  # field key -> {value: entry}

    for entry in wiring.get("picklist_values") or []:
        key = field_key(entry.get("field"))
        value, flow, label = entry.get("value") or "", entry.get("flow") or "", entry.get("label")
        where = f"{entry.get('field')} value {value!r}"
        result = {"field": key or entry.get("field"), "value": value, "label": label, "flow": flow, "ok": True}
        out["values"].append(result)
        if not key:
            out["problems"].append(f"{where}: {entry.get('field')!r} is not a Conversion Map Flow field. Use a Form Template "
                                   f"Conversion_Map_Flow_* field or {SECTION_FIELD}.")
            result["ok"] = False
            continue
        if not flow:
            out["problems"].append(f"{where}: name the flow it runs (its API name, with {N} only for a packaged flow).")
            result["ok"] = False
        else:
            why = value_problem(value, flow, label)
            if why:
                out["problems"].append(f"{where}: must be exactly {flow!r}; {why}. Edit the value's API name in Setup "
                                       "(Object Manager, the field, Values), not its label.")
                result["ok"] = False
            if flows is not None:
                found = flows.get(flow)
                if found is None:
                    out["problems"].append(f"{where}: no flow named {flow!r} in the org. Deploy it before adding the value.")
                    result["ok"] = False
                elif found.get("active") is False:
                    out["warnings"].append(f"{where}: {flow} is not active, so selecting it stops the conversion. Activate it first.")
        label_note = check_label(label, value)
        if label_note:
            out["warnings"].append(f"{where}: {label_note}.")
        if key == SECTION_FIELD:
            rules = entry.get("controlling_values") or []
            unknown = [r for r in rules if r not in SECTION_RULES]
            if not rules:
                out["problems"].append(f"{where}: the section picklist depends on Conversion Rule. Include the value under the "
                                       "rule(s) it serves in Field Dependencies (for example Contact1), or no section can select it.")
                result["ok"] = False
            if unknown:
                out["problems"].append(f"{where}: {', '.join(map(repr, unknown))} is not a section Conversion Rule value "
                                       f"({', '.join(SECTION_RULES)}).")
                result["ok"] = False
            result["controlling_values"] = rules
        added.setdefault(key, {})[value] = result

    def exists(key: str, value: str) -> bool:
        return value in ("", "Default") or value in added.get(key, {}) or value in (wiring.get("existing_values") or {}).get(key, [])

    template = {}
    for field, value in (wiring.get("template") or {}).items():
        key = field_key(field)
        if not key or key == SECTION_FIELD:
            out["problems"].append(f"Form Template setting {field!r} is not a Form Template Conversion Map Flow field.")
            continue
        name = key.split(".", 1)[1]
        template[name] = value
        if not exists(key, value):
            out["problems"].append(f"Form Template {name} = {value!r}: no such picklist value. Add it (value = the flow's API name) "
                                   "before setting it on a template.")
        what, default = TEMPLATE_FIELDS[name]
        out["template"][name] = {"value": value, "runs": f"the {default} record of Form Template Conversion Mapping Default"
                                 if value in ("", "Default") else value, "converts": what}

    for section in wiring.get("sections") or []:
        title = section.get("section") or "a section"
        rule = section.get("conversion_rule") or "Bypass"
        value = section.get("conversion_map_flow") or "Default"
        kind = section.get("component_type")
        row = {"section": title, "component_type": kind, "conversion_rule": rule, "conversion_map_flow": value}
        out["sections"].append(row)
        if value != "Default":
            if kind not in ROW_TYPES:
                out["problems"].append(f"{title}: a section Conversion Map Flow only changes Repeater and Table rows; this is a "
                                       f"{kind or 'section of unknown type'}. Set the flow on the Form Template instead.")
            if rule == "Bypass" or rule not in SECTION_RULES:
                out["problems"].append(f"{title}: Conversion Rule {rule!r} converts nothing, so {value!r} never runs. Pick the rule the "
                                       "rows convert under (Contact1, Contact2, Lead1, Lead2 or Case).")
            elif not exists(SECTION_FIELD, value):
                out["problems"].append(f"{title}: {value!r} is not a value of the section's Conversion Map Flow. Add it (value = the "
                                       "flow's API name) and include it under Conversion Rule " + repr(rule) + ".")
            else:
                entry = added.get(SECTION_FIELD, {}).get(value)
                if entry and rule not in (entry.get("controlling_values") or []):
                    out["problems"].append(f"{title}: {value!r} is not included under Conversion Rule {rule!r} in Field Dependencies, "
                                           "so the section cannot select it.")
        elif kind in ROW_TYPES and rule in SECTION_RULES:
            template_value = template.get(SECTION_RULES[rule])
            if template_value not in (None, "", "Default"):
                out["warnings"].append(f"{title}: its rows convert under {rule} on Default, which runs the packaged default flow, not "
                                       f"the template's {template_value!r}. Set the section's Conversion Map Flow if the rows should "
                                       "run it too.")
    out["status"] = "problems" if out["problems"] else "ok"
    return out


def summary(result: dict) -> str:
    lines = [f"Wiring check: {result['status']}"]
    for v in result["values"]:
        lines.append(f"- {'ok' if v['ok'] else 'FIX'}: {v['field']} value {v['value']!r} label {v.get('label')!r} -> {v['flow']}")
    for name, t in result["template"].items():
        lines.append(f"- Form Template {name}: {t['value'] or 'Default'} ({t['converts']} runs {t['runs']})")
    for s in result["sections"]:
        lines.append(f"- Section {s['section']} ({s['component_type']}, {s['conversion_rule']}): {s['conversion_map_flow']}")
    lines += [f"Problem: {p}" for p in result["problems"]] + [f"Warning: {w}" for w in result["warnings"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a new conversion flow's picklist values and template settings")
    parser.add_argument("file", help="a wiring.json, or a mapping-spec.json with a `wiring` key")
    parser.add_argument("--json", action="store_true", help="print the JSON instead of the summary")
    args = parser.parse_args(argv)
    data = json.loads(pathlib.Path(args.file).read_text())
    result = check(data.get("wiring", data))
    print(json.dumps(result, indent=1, ensure_ascii=False) if args.json else summary(result))
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
