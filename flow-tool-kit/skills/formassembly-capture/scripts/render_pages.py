#!/usr/bin/env python3
"""Render the archive as reviewable pages: an account overview plus one analysis page per built form.

Reads inventory.csv, account-map.json, and each form's ir.json, mapping.csv, connectors.json
and summary.md (optional). Writes <root>/pages/index.html and <root>/pages/forms/<id>.html,
plain HTML files that open from the folder, or publish as one multi-file page where an
artifact or hosting tool is available (index.html plus every forms/<id>.html at the same path).

Usage: python3 render_pages.py [--root _formassembly] [--title "<Organization> FormAssembly archive"]
"""
import argparse
import csv
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402
import build  # noqa: E402

CSS = archive.read_text(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "page.css"))
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
SOURCE_STYLE = {
    "form field": ("Form field", "var(--accent)"),
    "formula using form fields": ("Formula using form fields", "var(--accent)"),
    "fixed value or date": ("Fixed value or date", "var(--muted)"),
    "earlier step": ("Record from earlier step", "var(--ok)"),
    "payment": ("Payment system", "var(--warn)"),
    "deleted field": ("Deleted or unset field", "var(--bad)"),
}
e = html.escape


def page(title, body):
    return f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{e(title)}</title>\n{FONTS}\n<style>\n{CSS}</style>\n</head>\n<body>\n<div class="wrap">\n{body}\n</div>\n</body>\n</html>\n'


def inline(text):
    text = e(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def markdown(text):
    """The small markdown subset the summaries use: headings, lists, tables, paragraphs."""
    out, items, kind, table = [], [], None, []

    def flush():
        nonlocal items, kind, table
        if items:
            out.append(f"<{kind}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{kind}>")
        if table:
            rows = [r for r in table if not re.match(r"^\|[\s:|-]+\|$", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            head = "".join(f"<th>{inline(c)}</th>" for c in cells[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
            out.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        items, kind, table = [], None, []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            if items:
                flush()
            table.append(stripped)
            continue
        if table:
            flush()
        bullet = re.match(r"^\s*[-*]\s+(.*)", line)
        number = re.match(r"^\s*\d+\.\s+(.*)", line)
        if bullet or number:
            wanted = "ul" if bullet else "ol"
            if kind and kind != wanted:
                flush()
            kind = wanted
            items.append((bullet or number).group(1))
            continue
        if items and line.startswith("  ") and stripped:
            items[-1] += " " + stripped
            continue
        flush()
        heading = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if heading:
            level = min(len(heading.group(1)) + 1, 4)
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif stripped:
            out.append(f"<p>{inline(stripped)}</p>")
    flush()
    return "\n".join(out)


def table(headers, rows):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def classify(row):
    source, kind = row["value_source"], row["source_kind"]
    if "AUTHORIZE" in source:
        return "payment"
    if "Not set" in source or "missing field" in source or "deleted or unset field" in source:
        return "deleted field"
    if kind in ("record_id", "earlier step") or source.startswith("record_id"):
        return "earlier step"
    if kind == "formula":
        return "formula using form fields" if re.search(r"\[[^\]]+\]", source) else "fixed value or date"
    return "form field"


def bars(counts):
    total = sum(counts.values()) or 1
    rows = []
    for key, (label, color) in SOURCE_STYLE.items():
        if counts.get(key):
            width = 100 * counts[key] / total
            rows.append(f'<div class="bar"><span>{label}</span><div class="track"><div class="fill" style="width:{width:.1f}%;background:{color}"></div></div><span class="n">{counts[key]}</span></div>')
    label = ", ".join(f"{SOURCE_STYLE[k][0]} {v}" for k, v in counts.items() if v)
    return f'<div class="bars" role="img" aria-label="Value sources: {e(label)}">' + "".join(rows) + "</div>"


def summary_parts(path):
    if not os.path.exists(path):
        return "", ""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    text = re.sub(r"^#\s+.*\n", "", text, count=1)
    purpose = re.search(r"\*\*Purpose:\*\*\s*(.*)", text)
    rest = text.replace(purpose.group(0), "") if purpose else text
    return (purpose.group(1).strip() if purpose else ""), rest


def stat(value, label):
    return f'<div class="stat"><b>{e(str(value))}</b><span>{e(label)}</span></div>'


def number(value):
    known = archive.count(value)
    return f"{known:,}" if known is not None else "unknown"


def form_page(root, form_id, row, title):
    folder = os.path.join(root, "archive", form_id)
    bundle = archive.load_json(os.path.join(folder, "ir.json"))
    document = bundle["form"]
    connectors = archive.load_json(os.path.join(folder, "connectors.json"), []) or []
    public_url = (archive.load_json(os.path.join(folder, "capture.json"), {}) or {}).get("publicUrl") or f"https://www.tfaforms.com/{form_id}"
    with open(os.path.join(folder, "mapping.csv"), encoding="utf-8") as handle:
        mapping = list(csv.DictReader(handle))
    with open(os.path.join(folder, "form.html"), encoding="utf-8", errors="replace") as handle:
        form_html = handle.read()
    labels = build.label_map(document, form_html)
    purpose, summary = summary_parts(os.path.join(folder, "summary.md"))

    lookups = [lookup for found in bundle.get("prefill", {}).values() for lookup in found]
    submit = [m for m in mapping if m["when"] != "Form opened (prefill)"]
    models = [document.get("connector", {})] + list(bundle.get("additional_submit_connectors", {}).values())
    nodes = [node for model in models for node in (model.get("nodes", {}).values() if isinstance(model.get("nodes"), dict) else model.get("nodes", []))]
    calculations = [f for f in document["fields"] if f.get("calculation")]

    parts = [
        f'<nav class="crumbs"><a href="../index.html">{e(title)}</a></nav>',
        "<header>",
        f'<div class="eyebrow">FormAssembly form {e(form_id)} &middot; <span class="pill s-{e((row.get("status") or "check").split()[0])}">{e(row.get("status", ""))}</span></div>',
        f"<h1>{e(row['name'])}</h1>",
        f'<p class="lede">{inline(purpose)}</p>' if purpose else '<p class="lede">No summary written yet. The sections below are generated from the capture.</p>',
        '<div class="stats">',
        stat(number(row.get("completed")), f"completed ({row.get('incomplete') or 'unknown'} incomplete)"),
        stat(row.get("last_response") or row.get("status_basis") or "unknown", "last response" if row.get("last_response") else "status basis"),
        stat(len(lookups), "prefill lookups"),
        stat(len(nodes), "Salesforce steps on submit"),
        stat(len(submit), "field mappings on submit"),
        "</div>",
        "</header>",
    ]
    if summary.strip():
        parts.append(f'<section><h2>Summary</h2><div class="md">{markdown(summary)}</div></section>')

    if lookups:
        rows = []
        for lookup in lookups:
            match = f" {lookup['joiner']} ".join(e(build.describe_condition(c)) for c in lookup["conditions"])
            fills = ", ".join(e(m["form_field_label"] or "(unlabelled)") for m in lookup["mappings"][:12]) + (" ..." if len(lookup["mappings"]) > 12 else "")
            repeat = f"<br><span class='note'>Fills a copy of [{e(lookup['repeat_section'])}] per record</span>" if lookup.get("repeat_section") else ""
            outcome = f"<span class='note'>No match: {e(lookup['on_no_match'])}. Several: {e(lookup['on_multiple_matches'])}.</span>"
            rows.append([f'<span class="step">{e(lookup["order"])}</span>', f"<b>{e(lookup['sobject'])}</b>", f"{match}<br>{outcome}{repeat}", fills])
        parts.append("<section><h2>Prefill: when the form opens</h2>" + table(["#", "Finds", "Match rule", "Fills in"], rows) + "</section>")

    if calculations:
        variables = build.calculation_variables(form_html, labels, build.repeat_field_ids(document))
        seen, rows = set(), []
        for field in calculations:
            formula = build.formula_with_fields(field["calculation"], variables)
            key = (field["label"], field["calculation"])
            if key not in seen:
                seen.add(key)
                rows.append([e(labels.get(field["id"], field["label"])) + f" <span class='note'>{e(field['id'])}</span>", f"<code>{e(formula)}</code>", f"<code>{e(field['calculation'])}</code>"])
        parts.append("<section><h2>Calculations inside the form</h2><p>Copies of a section reuse labels, so compare the raw formulas: a copy that reads another copy's variable shows up there.</p>" + table(["Field", "Formula", "Raw formula"], rows) + "</section>")

    if document["conditions"]:
        rows = [[e(labels.get(re.sub(r"-[A-Z]$", "", c["element_id"]), c["element_id"])), e(c["reads_as"])] for c in document["conditions"]]
        parts.append(f"<section><h2>Show/hide rules ({len(rows)})</h2>" + table(["Element", "Shown when"], rows) + "</section>")

    if nodes:
        rows = []
        for node in nodes:
            skip = f"<br><span class='note'>Skipped when: {e(build.resolve(node['skip_if'], labels))}</span>" if node.get("skip_if") else ""
            rows.append([f'<span class="step">{e(node["order_path"])}</span>', f"{e(archive.effective_action(node))} <b>{e(node['sobject'])}</b>", e(build.describe_lookup(node.get("lookup"), labels)) + skip])
        parts.append("<section><h2>Post-processing: what is written to Salesforce</h2>" + table(["Step", "Action", "How the record is found, and when it is skipped"], rows) + "</section>")

    if submit:
        counts = {}
        for item in submit:
            kind = classify(item)
            counts[kind] = counts.get(kind, 0) + 1
        by_object = {}
        for item in submit:
            by_object.setdefault(item["salesforce_object"], []).append(item)
        rows = []
        for sobject, items in by_object.items():
            rows.append([f'<b>{e(sobject)}</b>', "", ""])
            seen = set()
            for item in items:
                key = (item["salesforce_field"], item["value_source"])
                if key in seen:
                    continue
                seen.add(key)
                kind = classify(item)
                pill = "p-dead" if kind == "deleted field" else "p-step" if kind == "earlier step" else "p-sys" if kind == "payment" else "p-const" if kind == "fixed value or date" else "p-form"
                rows.append([e(item["salesforce_field"]), e(item["value_source"][:220]), f'<span class="pill {pill}">{e(kind)}</span>'])
        parts.append(f"<section><h2>Field mapping analysis</h2><p>{len(submit)} values written on submit. Repeated rows (the same field and source) are shown once.</p>{bars(counts)}" + table(["Salesforce field", "Value", "Source"], rows) + "</section>")

    settings = bundle.get("settings", {})
    rows = [[e(label), e(settings[key][:300])] for key, label in archive.SETTING_LABELS.items() if settings.get(key)]
    rows += [[e(f"Connector {c['id']}"), e(f"{archive.EVENT_LABEL.get(c.get('event'), c.get('event') or 'event unknown')}: {c.get('type') or 'type unknown'}"
                                            + (" (disabled)" if c.get("enabled") is False else "")
                                            + ("" if not archive.is_salesforce(c) or archive.connector_file(folder, c) else ": mapping not captured"))] for c in connectors]
    parts.append("<section><h2>Settings and connectors</h2>" + table(["Setting", "Value"], rows) + "</section>")
    parts.append(f'<footer class="note">Generated by render_pages.py from <code>_formassembly/archive/{e(form_id)}/</code>. Public form: {e(public_url)}</footer>')
    return page(f"{row['name']} ({form_id})", "\n".join(parts))


def index_page(root, inventory, built, title):
    statuses = {}
    for row in inventory.values():
        statuses[row.get("status", "")] = statuses.get(row.get("status", ""), 0) + 1
    account_map_path = os.path.join(root, "account-map.json")
    account_map = archive.load_json(account_map_path, {})
    name = lambda form_id: inventory.get(form_id, {}).get("name", form_id)
    link = lambda form_id: f'<a href="forms/{e(form_id)}.html">{e(name(form_id))}</a>' if form_id in built else e(name(form_id))

    parts = [
        "<header>",
        '<div class="eyebrow">FormAssembly account archive</div>',
        f"<h1>{e(title)}</h1>",
        f'<p class="lede">{len(inventory)} forms are in the inventory. {len(built)} kept forms have an analysis page; the rest are listed in inventory.csv.</p>',
        '<div class="stats">',
        stat(len(inventory), "forms in the account"),
        stat(len(built), "analysed"),
        stat(statuses.get("active", 0), "active (a response in the last 12 months)"),
        stat(len(account_map.get("links", [])), "form-to-form hand-offs"),
        "</div>",
        "</header>",
    ]
    rows = []
    for form_id in built:
        row = inventory[form_id]
        status = row.get("status") or "check"
        rows.append([link(form_id), e(form_id), f'<span class="pill s-{e(status.split()[0])}">{e(status)}</span>', f'<span class="num">{number(row.get("completed"))}</span>', e(row.get("last_response") or row.get("status_basis") or ""), e(row.get("connectors", ""))])
    parts.append("<section><h2>Forms</h2>" + table(["Form", "Id", "Status", "Completed", "Last response or basis", "Connectors"], rows) + "</section>")

    if account_map.get("links"):
        rows = [[link(l["from"]), link(l["to"]), e(", ".join(l["parameters"]) or "nothing")] for l in account_map["links"]]
        parts.append("<section><h2>Forms that hand off to other forms</h2>" + table(["From", "Sends the person to", "Passes"], rows) + "</section>")
    if account_map.get("objects"):
        rows = []
        for sobject, actions in account_map["objects"].items():
            if not any(actions.get(key) for key in ("read", "create", "update")):
                continue
            cell = lambda key: f"{len(actions.get(key, []))}" if actions.get(key) else "-"
            rows.append([f"<b>{e(sobject)}</b>", cell("read"), cell("create"), cell("update")])
        parts.append("<section><h2>Salesforce objects</h2><p>Number of forms that read (prefill), create or update each object.</p>" + table(["Object", "Read", "Create", "Update"], rows) + "</section>")
    if account_map.get("shared_field_groups"):
        rows = []
        for group in account_map["shared_field_groups"][:15]:
            forms_in = sorted({use["form"] for use in group["used_in"]})
            rows.append([e(", ".join(group["fields"][:10])) + (" ..." if len(group["fields"]) > 10 else ""), str(len(forms_in)), "; ".join(f"{link(use['form'])} / {e(use['section'])}" for use in group["used_in"][:6])])
        parts.append("<section><h2>Shared component candidates</h2><p>Sections with the same fields in more than one form. Candidates for one shared form component each (org-catalog, then build-form-component), not decisions.</p>" + table(["Fields", "Forms", "Where"], rows) + "</section>")
    plan_path = os.path.join(root, "flow-plan.json")
    if os.path.exists(plan_path):
        plan = archive.load_json(plan_path)
        decision = plan.get("controller")
        if decision:
            ext = decision["extended"]
            rows = [["Packaged (no change)", str(len(decision["packaged_forms"])), ", ".join(link(f) for f in decision["packaged_forms"]) or "-"],
                    ["Extended clone" + (f" (extend {e(ext['existing_clone'])})" if ext.get("existing_clone") else ""), str(len(ext["forms"])), ", ".join(link(f) for f in ext["forms"])]]
            rows += [[f"Bespoke candidate", "1", link(f) + "<br><span class='note'>" + e("; ".join(decision["per_form"][f]["reasons"])) + "</span>"] for f in decision["bespoke_candidates"]]
            parts.append(f"<section><h2>Controller</h2><p>{e(ext['selection'])}</p>" + table(["Controller", "Forms", "Which"], rows) + "</section>")
        rows = [[e(r["rule"]), e(r["kind"]), str(len(r["forms"])), ", ".join(link(f) for f in r["forms"][:5]) + (" ..." if len(r["forms"]) > 5 else "")] for r in plan["conversion_rules"]]
        parts.append("<section><h2>Flow plan: conversion rules, in run order</h2><p>FormAssembly ran one submit connector per form. In the rebuild each rule below is built once and switched on by every form that needs it.</p>" + table(["Rule", "Kind", "Forms", "Used by"], rows) + "</section>")
        if plan.get("conflicts"):
            parts.append("<section><h2>Order conflicts to resolve</h2><ul>" + "".join(f"<li>{e(c)}</li>" for c in plan["conflicts"]) + "</ul></section>")
        rows = [[f"<b>{e(g['object'])}</b>", e(", ".join(g["matched_on"])), e(", ".join(g["parameters"])), ", ".join(link(f) for f in g["forms"])] for g in plan["prefill_flows"]]
        parts.append("<section><h2>Flow plan: shared prefill flows</h2><p>One prefill flow per entry record, shared by the forms listed; each form adds only its own lookups. See flow-plan.md for each form's chain.</p>" + table(["Entry record", "FormAssembly matched on", "URL parameters", "Forms"], rows) + "</section>")
    parts.append('<footer class="note">Generated by render_pages.py (formassembly-capture skill).</footer>')
    return page(title, "\n".join(parts))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default="_formassembly")
    parser.add_argument("--title", default="FormAssembly archive")
    args = parser.parse_args(argv)
    inventory = archive.load_inventory(args.root)
    folder = archive.paths(args.root)["archive"]
    kept = archive.load_kept(args.root) or set()
    built = [i for i in inventory if (not kept or i in kept) and os.path.exists(os.path.join(folder, i, "ir.json")) and os.path.exists(os.path.join(folder, i, "mapping.csv"))]
    built.sort(key=lambda i: (archive.STATUS_ORDER.get(inventory[i].get("status", ""), 9), inventory[i]["name"].lower()))
    pages = os.path.join(args.root, "pages", "forms")
    os.makedirs(pages, exist_ok=True)
    for stale in os.listdir(pages):
        if stale.endswith(".html") and stale[:-5] not in built:
            os.remove(os.path.join(pages, stale))
    for form_id in built:
        with open(os.path.join(pages, f"{form_id}.html"), "w", encoding="utf-8") as handle:
            handle.write(form_page(args.root, form_id, inventory[form_id], args.title))
    with open(os.path.join(args.root, "pages", "index.html"), "w", encoding="utf-8") as handle:
        handle.write(index_page(args.root, inventory, built, args.title))
    print(f"pages: index + {len(built)} forms in {os.path.join(args.root, 'pages')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
