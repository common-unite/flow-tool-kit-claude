#!/usr/bin/env python3
"""Map how the forms in a FormAssembly account fit together.

Reads <root>/inventory.csv and each built form's ir.json, and writes
<root>/account-map.json and <root>/account-map.md:
  links         form-to-form hand-offs from the after-submit redirect, with the URL parameters passed
  entry points  the URL parameters each form's prefill expects
  objects       which forms read, create and update each Salesforce object
  shared        groups of fields (by section) that appear in more than one form: shared component candidates

Usage: python3 account_map.py [--root _formassembly]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402

PAYMENT = re.compile(r"authorize|card number|name on card|billing|\bcvv\b|^code$|^mm$|^yy$")


def load(root):
    inventory = archive.load_inventory(root)
    kept = archive.load_kept(root)
    forms = {}
    folder = archive.paths(root)["archive"]
    for form_id in sorted(os.listdir(folder)):
        path = os.path.join(folder, form_id, "ir.json")
        if form_id in inventory and os.path.exists(path) and (kept is None or form_id in kept):
            forms[form_id] = archive.load_json(path)
    return inventory, forms


def links_from(form_id, bundle):
    redirect = bundle.get("settings", {}).get("thankyou_url", "")
    matches = list(archive.FORM_LINK.finditer(redirect))
    unique = {}
    for index, match in enumerate(matches):
        target = match.group(1)
        if target == form_id:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(redirect)
        parameters = set(re.findall(r"[?&]([A-Za-z_]\w*)=", redirect[match.end():end]))
        link = unique.setdefault(target, {"from": form_id, "to": target, "parameters": [], "how": "redirect after submit"})
        link["parameters"] = sorted(set(link["parameters"]) | parameters)
    return list(unique.values())


def entry_parameters(bundle):
    parameters = set()
    for lookups in bundle.get("prefill", {}).values():
        for lookup in lookups:
            for condition in lookup["conditions"]:
                if condition["value_kind"] == "url_parameter":
                    parameters.add((condition["value"], lookup["sobject"], condition["field_label"]))
    return sorted(parameters)


def objects_touched(bundle):
    touched = []
    for lookups in bundle.get("prefill", {}).values():
        for lookup in lookups:
            touched.append((lookup["sobject"], "read"))
    models = [bundle["form"].get("connector") or {}] + list(bundle.get("additional_submit_connectors", {}).values())
    for model in models:
        nodes = model.get("nodes", [])
        for node in nodes.values() if isinstance(nodes, dict) else nodes:
            if node.get("sobject"):
                action = archive.effective_action(node)
                touched += [(node["sobject"], "create"), (node["sobject"], "update")] if action == "upsert" else [(node["sobject"], action)]
    return touched


def field_groups(bundle):
    groups = {}
    for field in bundle["form"]["fields"]:
        path = field.get("section_path") or ""
        if not path or not field.get("label"):
            continue
        groups.setdefault(path.split("/")[-1], set()).add(re.sub(r"[:*\s]+$", "", field["label"].strip()).lower())
    return {name: labels for name, labels in groups.items() if len(labels) >= 3 and not any(PAYMENT.search(label) for label in labels)}


def build_map(inventory, forms):
    links = [link for form_id, bundle in forms.items() for link in links_from(form_id, bundle)]
    for link in links:
        target = forms.get(link["to"])
        if target:
            field_labels = {f["id"]: f["label"] for f in target["form"]["fields"]}
            link["parameters"] = [f"{p} ({field_labels[p]})" if p in field_labels else p for p in link["parameters"]]
    objects = {}
    for form_id, bundle in forms.items():
        for sobject, action in objects_touched(bundle):
            objects.setdefault(sobject, {}).setdefault(action, set()).add(form_id)
    signatures = {}
    for form_id, bundle in forms.items():
        for section, labels in field_groups(bundle).items():
            signatures.setdefault(frozenset(labels), []).append((form_id, section))
    shared = [
        {"fields": sorted(labels), "used_in": [{"form": form_id, "section": section} for form_id, section in sorted(uses)]}
        for labels, uses in signatures.items() if len({form_id for form_id, _ in uses}) > 1
    ]
    shared.sort(key=lambda group: (-len({use["form"] for use in group["used_in"]}), -len(group["fields"])))
    entries = {form_id: entry_parameters(bundle) for form_id, bundle in forms.items()}
    return {
        "links": links,
        "entry_parameters": {form_id: [{"parameter": p, "object": o, "matches": f} for p, o, f in params] for form_id, params in entries.items() if params},
        "objects": {sobject: {action: sorted(ids) for action, ids in actions.items()} for sobject, actions in sorted(objects.items())},
        "shared_field_groups": shared,
    }


def markdown(result, forms, name):
    out = ["# Account map", "", f"{len(forms)} forms built. Generated by account_map.py from each form's ir.json.", "", "## Forms that hand off to other forms", ""]
    if result["links"]:
        out += ["| From | To | Passes |", "|---|---|---|"]
        for link in sorted(result["links"], key=lambda l: name(l["from"]).lower()):
            out.append(f"| {name(link['from'])} ({link['from']}) | {name(link['to'])} ({link['to']}) | {', '.join(link['parameters']) or 'nothing'} |")
    else:
        out.append("None found.")
    out += ["", "## What each prefill form expects in its link", "", "| Form | URL parameter | Finds | By |", "|---|---|---|---|"]
    for form_id, params in sorted(result["entry_parameters"].items(), key=lambda item: name(item[0]).lower()):
        for item in params:
            out.append(f"| {name(form_id)} ({form_id}) | `{item['parameter']}` | {item['object']} | {item['matches']} |")
    out += ["", "## Salesforce objects", "", "| Object | Read by (prefill) | Created by | Updated by |", "|---|---|---|---|"]
    for sobject, actions in result["objects"].items():
        if not any(actions.get(key) for key in ("read", "create", "update")):
            continue
        listed = lambda key: ", ".join(name(i) for i in actions.get(key, [])) or "-"
        out.append(f"| {sobject} | {listed('read')} | {listed('create')} | {listed('update')} |")
    out += ["", "## Shared component candidates", "", "Sections with the same set of fields (3 or more) in more than one form. Candidates for one shared form component each (org-catalog checks what the org already has; build-form-component builds it), not decisions.", ""]
    for group in result["shared_field_groups"][:25]:
        forms_in = sorted({use["form"] for use in group["used_in"]})
        out.append(f"- **{len(forms_in)} forms**, {len(group['fields'])} fields ({', '.join(group['fields'][:8])}{', ...' if len(group['fields']) > 8 else ''}): " + "; ".join(f"{name(use['form'])} / {use['section']}" for use in group["used_in"]))
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default="_formassembly")
    args = parser.parse_args(argv)
    inventory, forms = load(args.root)
    result = build_map(inventory, forms)
    archive.write_json(os.path.join(args.root, "account-map.json"), result)
    with open(os.path.join(args.root, "account-map.md"), "w", encoding="utf-8") as handle:
        handle.write(markdown(result, forms, archive.name_of(inventory)))
    print(f"forms {len(forms)}  links {len(result['links'])}  prefill forms {len(result['entry_parameters'])}  objects {len(result['objects'])}  shared groups {len(result['shared_field_groups'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
