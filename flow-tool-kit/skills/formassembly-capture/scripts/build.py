#!/usr/bin/env python3
"""Build the archive: one readable folder per form, from what collect.py, the exports and the
browser step captured.

Writes into each built form's archive/<id>/:
  ir.json      form-migrate's form description, plus prefill lookups, extra submit connectors and settings
  logic.md     settings, prefill, calculations, submit steps and show/hide rules, field ids replaced by labels
  mapping.csv  one row per Salesforce field written or prefilled
and archive/README.md (the index) and kept.txt (the forms built; the account map, flow plan
and pages read only these, so an earlier wider build never widens them).

Usage: python3 build.py [--root _formassembly] [--title "<Organization> FormAssembly archive"]
                        [--status active,check] [--forms 101,102]
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import html
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402
from archive import EVENT_LABEL, SETTING_LABELS  # noqa: E402
from reader import adapter, connector, prefill  # noqa: E402


def element_titles(form_html):
    titles = {}
    for match in re.finditer(r'<(fieldset|div)[^>]*\bid="(tfa_\d+)"[^>]*>(.{0,600})', form_html, re.S):
        tag, element_id, after = match.groups()
        legend = re.search(r"<legend[^>]*>(.*?)</legend>", after, re.S)
        text = legend.group(1) if legend and tag == "fieldset" else after
        text = re.sub(r"<[^>]*$", "", text)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()
        titles[element_id] = (("Section: " if tag == "fieldset" else "Text: ") + text[:70]) if text else f"untitled {tag}"
    for match in re.finditer(r'<label[^>]*\bfor="(tfa_\d+)"[^>]*>(.*?)</label>', form_html, re.S):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group(2)))).strip()
        if text:
            titles[match.group(1)] = text[:70]
    return titles


def label_map(document, form_html=""):
    """Field id to label. Fields that share a label carry their section, so two City fields stay two."""
    labels = element_titles(form_html)
    counts = {}
    for field in document["fields"]:
        counts[field["label"]] = counts.get(field["label"], 0) + 1
    for field in document["fields"]:
        section = (field.get("section_path") or "").split("/")[-1]
        same_name = counts[field["label"]] > 1 and section
        labels[field["id"]] = f'{field["label"]} ({section})' if same_name else field["label"]
        for option in field.get("options") or []:
            labels[option["id"]] = f'{field["label"]} = "{option["label"]}"'
    return labels


def resolve(text, labels, tokens_only=False):
    """Replace field ids with labels. tokens_only keeps bare ids, which in a redirect link belong to the target form."""
    if not text:
        return text
    text = re.sub(r"%%(tfa_\d+)%%", lambda m: "[" + labels.get(m.group(1), "missing field " + m.group(1)) + "]", text)
    if tokens_only:
        return text
    text = re.sub(r"\b(tfa_\d+)-[A-Z]\b", r"\1", text)
    return re.sub(r"\b(tfa_\d+)\b", lambda m: "[" + labels.get(m.group(1), "missing field " + m.group(1)) + "]", text)


def captured_connectors(folder):
    """(connectors, submit page paths, prefill page paths, Salesforce connectors with no page)."""
    connectors = archive.load_json(os.path.join(folder, "connectors.json"), []) or []
    submit, pull, missing = [], [], []
    for item in connectors:
        if not archive.is_salesforce(item):
            continue
        path = archive.connector_file(folder, item)
        if not path:
            missing.append(item)
        elif archive.is_prefill(item):
            pull.append(path)
        else:
            submit.append(path)
    return connectors, sorted(submit), sorted(pull), missing


def connector_id_of(path):
    return re.search(r"-([^-]+)\.html$", path).group(1)


def build_ir(folder, form_id, form_name, submit_path):
    work = tempfile.mkdtemp(prefix="fa-build-")
    try:
        for name in ("aliases.html", "form.html"):
            if os.path.exists(os.path.join(folder, name)):
                shutil.copy(os.path.join(folder, name), os.path.join(work, name))
        if submit_path:
            shutil.copy(submit_path, os.path.join(work, "connector.html"))
        return adapter.build_from_files(work, form_id=form_id, connector_id=connector_id_of(submit_path) if submit_path else "", form_name=form_name)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def node_list(model):
    nodes = model["nodes"]
    return list(nodes.values()) if isinstance(nodes, dict) else nodes


def describe_predicate(predicate):
    operands = predicate.get("operands") or []
    if operands:
        joiner = f' {(predicate.get("operator") or "and").upper()} '
        operator = predicate.get("operator") or "and"
        flat = []
        for operand in operands:
            same = operand.get("operands") and (operand.get("operator") or "and") == operator
            flat.extend(operand["operands"] if same else [operand])
        if len(flat) != len(operands):
            return describe_predicate({**predicate, "operands": flat})
        parts = [describe_predicate(operand) for operand in operands]
        return "(" + joiner.join(part for part in parts if part) + ")"
    comparison = (predicate.get("comparison") or "").replace("Record ID of", "the record from step").strip()
    right = predicate.get("right_value") or ""
    if predicate.get("right_kind") == "form_field":
        right = f"form field [{right}]"
    elif predicate.get("right_kind") == "formula":
        right = f'"{right}"'
    return f'{predicate.get("left_field") or ""} {comparison} {right}'.strip()


def repeat_field_ids(document):
    repeat_ids = {section["id"] for section in document["structure"] if section.get("repeat")}
    return {field["id"] for field in document["fields"] if field.get("section_id") in repeat_ids}


def calculation_variables(form_html, labels, repeat_ids=frozenset()):
    """Variable name to field label. A name on one field per repeated row reads 'every row'; a name shared by ordinary fields lists them."""
    owners = {}
    for match in re.finditer(r'<(?:input|select|textarea)[^>]*\bid="(tfa_\d+)"[^>]*class="[^"]*\bcalc-([\w-]+)', form_html):
        owners.setdefault(match.group(2), []).append(match.group(1))
    for match in re.finditer(r'<(?:input|select|textarea)[^>]*class="[^"]*\bcalc-([\w-]+)[^"]*"[^>]*\bid="(tfa_\d+)"', form_html):
        owners.setdefault(match.group(1), []).append(match.group(2))
    variables = {}
    for name, ids in owners.items():
        ids = sorted(set(ids))
        if len(ids) == 1:
            variables[name] = labels.get(ids[0], ids[0])
        elif all(i in repeat_ids for i in ids):
            variables[name] = re.sub(r"\s*\([^)]*\)$", "", labels.get(ids[0], ids[0])) + ", every row"
        else:
            variables[name] = " + ".join(dict.fromkeys(labels.get(i, i) for i in ids))
    return variables


def formula_with_fields(calculation, variables):
    return re.sub(r"\b([A-Za-z_]\w*)\b", lambda m: f"[{variables[m.group(1)]}]" if m.group(1) in variables else m.group(1), calculation)


def describe_condition(condition):
    value = condition["value"]
    if condition["value_kind"] == "url_parameter":
        value = f"URL parameter `{value}`"
    elif condition["value_kind"] == "lookup_result":
        value = "the record from " + re.sub(r"^#?(?:Lookup )?#?(\d+)\s*[-|]\s*", r"lookup #\1 ", value)
    elif condition["value_kind"] == "formula":
        value = f'"{value}"'
    return f"{condition['field_label']} {condition['operator'].lower()} {value}"


def describe_lookup(lookup, labels):
    if not lookup:
        return "creates a new record"
    match = resolve(describe_predicate(lookup.get("predicate") or {}), labels)
    return (
        f"finds the record where {match}. "
        f"No match: {lookup.get('on_no_match')}. One match: {lookup.get('on_one_match')}. "
        f"Several: {lookup.get('on_multiple_matches')}."
    )


def clean_source(value):
    value = re.sub(r"^(?:a field in your form|a Salesforce field)\s*", "", value or "").strip()
    return "deleted or unset field" if value.startswith("Not set.") else value


def mapping_source(mapping, labels):
    kind = mapping.get("source_kind")
    value = resolve(clean_source(mapping.get("source_value")), labels)
    if kind == "form_field":
        return f"form field [{value}]", "form field"
    if kind == "formula":
        return f"formula: {value}", "formula"
    if kind in ("lookup_result", "record_id"):
        return f"from earlier step {mapping.get('source_node_path') or ''}: {value}".strip(), "earlier step"
    return f"{kind}: {value}", kind or ""


def cell(text, limit=None):
    text = str(text if text is not None else "").replace("|", "/")
    return text[:limit] if limit else text


def write_form(root, form_id, row):
    folder = os.path.join(archive.paths(root)["archive"], form_id)
    connectors, submit_paths, prefill_paths, missing = captured_connectors(folder)
    with open(os.path.join(folder, "form.html"), encoding="utf-8", errors="replace") as handle:
        form_html = handle.read()
    document = build_ir(folder, form_id, row["name"], submit_paths[0] if submit_paths else None)
    report = archive.load_json(os.path.join(folder, "api-report.json"), None)
    if report is not None:
        document["source"]["api"] = report
    if missing:
        document["findings"].append({"source": "formassembly-capture", "message": "Mapping not captured for Salesforce connector(s) "
                                     + ", ".join(f"{c['id']} ({c.get('type') or 'type unknown'})" for c in missing)
                                     + ": their steps are unknown, not absent. Save each connector's read-only view page and rebuild."})
    labels = label_map(document, form_html)
    extra = {os.path.basename(path): dataclasses.asdict(connector.parse_file(path)) for path in submit_paths[1:]}
    prefill_lookups = {os.path.basename(path): [dataclasses.asdict(lookup) for lookup in prefill.parse_file(path)] for path in prefill_paths}
    settings = archive.read_settings(folder)
    if settings.get("thankyou_url"):
        settings["thankyou_url"] = resolve(settings["thankyou_url"], labels, tokens_only=True)
    archive.write_json(os.path.join(folder, "ir.json"), {"form": document, "additional_submit_connectors": extra, "prefill": prefill_lookups, "settings": settings})

    stat = archive.load_json(os.path.join(folder, "capture.json"), {}) or {}
    by_id = {c["id"]: c for c in connectors}
    rows = []
    out = [f"# {row['name']} (FormAssembly {form_id})", ""]
    out += [
        f"- Responses: {row.get('completed') or 'unknown'} completed, {row.get('incomplete') or 'unknown'} incomplete",
        f"- Status: {row.get('status') or 'check'} ({row.get('status_basis') or 'no basis recorded'})"
        + (f"  |  Last response: {row['last_response']}" if row.get("last_response") else "")
        + (f"  |  Last modified: {row['last_modified']}" if row.get("last_modified") else ""),
        f"- Public URL: {stat.get('publicUrl') or 'https://www.tfaforms.com/' + form_id}",
        f"- Fields: {len(document['fields'])}  |  Sections: {len(document['structure'])}  |  Show/hide rules: {len(document['conditions'])}",
        "",
        "## Connectors",
        "",
        "| When | Type | Enabled | Mapping captured | Id |",
        "|---|---|---|---|---|",
    ]
    for c in connectors:
        captured = "yes" if archive.connector_file(folder, c) else ("no" if archive.is_salesforce(c) else "n/a")
        enabled = {True: "yes", False: "no"}.get(c.get("enabled"), "unknown")
        out.append(f"| {EVENT_LABEL.get(c.get('event'), c.get('event') or 'unknown')} | {c.get('type') or 'unknown'} | {enabled} | {captured} | {c['id']} |")
    if missing:
        out += ["", "Mapping not captured for " + ", ".join(c["id"] for c in missing) + ": those steps are unknown, not absent."]
    if any("authorize" in (c.get("type") or "") and c.get("enabled") is not False for c in connectors):
        out += ["", "Takes a card payment through Authorize.Net. Not archived: the rebuild uses the org's own payment setup."]

    if settings:
        out += ["", "## Settings", "", "| Setting | Value |", "|---|---|"]
        for key, label in SETTING_LABELS.items():
            if settings.get(key) not in (None, ""):
                out.append(f"| {label} | {cell(settings[key], 300)} |")

    for path in prefill_paths:
        connector_id = connector_id_of(path)
        state = "DISABLED" if by_id.get(connector_id, {}).get("enabled") is False else "enabled"
        out += ["", f"## Prefill when the form opens (connector {connector_id}, {state})", ""]
        for lookup in prefill_lookups[os.path.basename(path)]:
            out.append(f"### {lookup['order']}. Find {lookup['sobject']} (lookup #{lookup['number']})")
            out.append("")
            joiner = f" {lookup['joiner']} "
            out.append("- Match: " + (joiner.join(describe_condition(c) for c in lookup["conditions"]) or "no conditions"))
            out.append(f"- No match: {lookup['on_no_match']}. One match: {lookup['on_one_match']}. Several: {lookup['on_multiple_matches']}.")
            if lookup["repeat_section"]:
                out.append(f"- Each match fills one copy of the repeating section [{lookup['repeat_section']}], sorted {lookup['repeat_order'] or 'as found'}.")
            out.append("")
            if lookup["mappings"]:
                out += ["| Form field | Gets its value from |", "|---|---|"]
            for mapping in lookup["mappings"]:
                source = f"formula: {mapping['source']}" if mapping["source_kind"] == "formula" else f"{lookup['sobject']}.{mapping['source']}"
                out.append(f"| {mapping['form_field_label'] or '(unlabelled field)'} | {cell(source)} |")
                rows.append(["Form opened (prefill)", lookup["sobject"], mapping["form_field_label"], source, "prefill " + mapping["source_kind"]])
            out.append("")

    calculations = [field for field in document["fields"] if field.get("calculation")]
    if calculations:
        variables = calculation_variables(form_html, labels, repeat_field_ids(document))
        out += ["", "## Calculations in the form", "", "Copies of a form section reuse labels, so compare the raw formulas: a copy that reads another copy's variable shows up there.", "", "| Field | Formula (variables shown as fields) | Raw formula |", "|---|---|---|"]
        seen = set()
        for field in calculations:
            if (field["label"], field["calculation"]) in seen:
                continue
            seen.add((field["label"], field["calculation"]))
            out.append(f"| {labels.get(field['id'], field['label'])} ({field['id']}) | `{cell(formula_with_fields(field['calculation'], variables))}` | `{cell(field['calculation'])}` |")

    repeats = [section for section in document["structure"] if section.get("repeat")]
    if repeats:
        out += ["", "## Repeating sections", ""]
        for section in repeats:
            name = next((f["section_path"].split("/")[-1] for f in document["fields"] if f.get("section_id") == section["id"] and f.get("section_path")), None)
            name = name or labels.get(section["id"], section["id"])
            inside = [labels.get(f["id"], f["label"]).replace(f" ({name})", "") for f in document["fields"] if f.get("section_id") == section["id"]]
            out.append(f"- {name}: {', '.join(inside[:8]) or 'fields not listed'}" + (f" (add button: {section['repeat_label']})" if section.get("repeat_label") else ""))

    for path in submit_paths:
        connector_id = connector_id_of(path)
        model = dataclasses.asdict(connector.parse_file(path))
        meta = by_id.get(connector_id, {})
        when = EVENT_LABEL.get(meta.get("event"), meta.get("event") or "Form submitted")
        out += ["", f"## {when}: write to Salesforce (connector {connector_id}, {'DISABLED' if meta.get('enabled') is False else 'enabled'})", ""]
        for node in sorted(node_list(model), key=lambda n: [int(p) if p.isdigit() else 999 for p in (n.get("order_path") or "999").split(".")]):
            out.append(f"### {node['order_path']} {archive.effective_action(node)} {node['sobject']}")
            out.append("")
            out.append(f"- Lookup: {describe_lookup(node.get('lookup'), labels)}")
            if node.get("skip_if"):
                out.append(f"- Skipped when: {resolve(node['skip_if'], labels)}")
            if node.get("comment"):
                out.append(f"- Note: {node['comment']}")
            out.append("")
            if node.get("mappings"):
                out += ["| Salesforce field | Value comes from |", "|---|---|"]
            for mapping in node.get("mappings") or []:
                source, kind = mapping_source(mapping, labels)
                out.append(f"| {mapping['target_field_label']} | {cell(source)} |")
                rows.append([when, node["sobject"], mapping["target_field_label"], source, kind])
            out.append("")

    if document["conditions"]:
        out += ["## Show/hide rules", "", "| Element | Shown when |", "|---|---|"]
        for condition in document["conditions"]:
            element = labels.get(re.sub(r"-[A-Z]$", "", condition["element_id"]), condition["element_id"])
            out.append(f"| {element} ({condition['governs']}) | {cell(condition['reads_as'])} |")
        out.append("")

    out += ["## Sections", ""] + [f"- {path}" for path in document["form"].get("section_paths", [])]
    with open(os.path.join(folder, "logic.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    with open(os.path.join(folder, "mapping.csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["when", "salesforce_object", "salesforce_field", "value_source", "source_kind"])
        writer.writerows(rows)
    return len(document["fields"]), len(document["conditions"]), len(rows), len(connectors), len(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default="_formassembly")
    parser.add_argument("--title", default="FormAssembly archive")
    parser.add_argument("--status", default="", help="comma list of inventory statuses to build; default every captured form")
    parser.add_argument("--forms", default="", help="comma list of extra form ids to build, whatever their status")
    args = parser.parse_args(argv)
    where = archive.paths(args.root)
    wanted = {s.strip() for s in args.status.split(",") if s.strip()}
    extra = {f.strip() for f in args.forms.split(",") if f.strip()}
    inventory = archive.load_inventory(args.root)
    index = [
        f"# {args.title}",
        "",
        "One folder per captured form. Start with `summary.md` where it exists (purpose and plain rules), then `logic.md` (every step, generated), `mapping.csv` and `ir.json`. Captured sources: `form.html`, `aliases.html` when exported, `connector-*.html`, `api-*.json`.",
        "",
        "| Form | Id | Status | Completed | Fields | Rules | Mappings | Connectors | Mappings not captured |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    folders = [i for i in os.listdir(where["archive"]) if os.path.isdir(os.path.join(where["archive"], i)) and i in inventory]
    folders.sort(key=lambda i: (archive.STATUS_ORDER.get(inventory[i].get("status", ""), 9), inventory[i]["name"].lower()))
    kept, failed = [], 0
    for form_id in folders:
        row = inventory[form_id]
        if (wanted or extra) and row.get("status") not in wanted and form_id not in extra:
            continue
        if not os.path.exists(os.path.join(where["archive"], form_id, "form.html")):
            print(f"{form_id} skipped: no form.html")
            failed += 1
            continue
        try:
            fields, rules, mappings, connector_count, missing = write_form(args.root, form_id, row)
        except Exception as error:  # one broken form must not stop the archive; it is reported and counted
            print(f"{form_id} FAILED: {type(error).__name__}: {error}")
            failed += 1
            continue
        start = "summary.md" if os.path.exists(os.path.join(where["archive"], form_id, "summary.md")) else "logic.md"
        index.append(f"| [{cell(row['name'])}]({form_id}/{start}) | {form_id} | {row.get('status', '')} | {row.get('completed', '')} | {fields} | {rules} | {mappings} | {connector_count} | {missing or '-'} |")
        kept.append(form_id)
        print(f"{form_id} fields={fields} rules={rules} mappings={mappings}" + (f" connector-gaps={missing}" if missing else ""))
    with open(os.path.join(where["archive"], "README.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(index) + "\n")
    with open(where["kept"], "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(kept)) + "\n")
    print(f"built {len(kept)} forms ({failed} failed); kept list in {where['kept']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
