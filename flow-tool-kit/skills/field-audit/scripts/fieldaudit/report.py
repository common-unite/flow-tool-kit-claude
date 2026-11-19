"""The audit's files: four CSVs that open cleanly in Excel or Google Sheets,
and data-dictionary.md for people to read.

* data_dictionary.csv: one row per field, with its attributes, where it is
  used, its mapped partners, its verdict and documentation gaps.
* template_references.csv: one row per place a template or form uses a field.
* flow_references.csv: one row per place a Flow Tool Kit flow uses a field.
* coverage.csv: what was read, what was not, and what could not be parsed.
"""

from __future__ import annotations

import csv
import os

from . import NAMESPACE, PAGE_OBJECT, SECTION_OBJECT, TEMPLATE_OBJECT
from .dictionary import BUCKET_ORDER, UNREFERENCED, VERDICTS

DICTIONARY_COLUMNS = [
    "Object", "Field Label", "API Name", "Type", "Description", "Help Text",
    "Security Classification", "Compliance Group", "Business Status",
    "Sections", "Rules", "Mappings", "Prefill", "URL", "Merge", "Flows", "Total Refs",
    "Surfaces", "Used In", "Mapped With", "Verdict",
    "Documentation", "Field Link",
]
REFERENCE_COLUMNS = [
    "Object", "Field Label", "Field API Name", "Surface", "Role", "Form Template", "Page", "Section",
    "Component Type", "Component", "Snippet", "Field Link", "Template Link", "Page Link", "Section Link",
    "Component Link",
]
FLOW_COLUMNS = [
    "Object", "Field Label", "Field API Name", "Surface", "Role", "Flow", "Flow API Name", "Flow Type",
    "Flow Tool Kit Role", "Element", "Element Type", "Resolution", "Snippet", "Field Link", "Flow Link",
]
COVERAGE_COLUMNS = ["Store", "Status", "Detail"]
USED_IN_LIMIT = 6


def _write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _list(items, limit=USED_IN_LIMIT):
    items = list(items)
    shown = "; ".join(items[:limit])
    return shown + (f"; and {len(items) - limit} more" if len(items) > limit else "")


class Links:
    """Lightning links, or blanks when the org's address is unknown (chat)."""

    def __init__(self, instance_url, labels):
        self.base = (instance_url or "").rstrip("/")
        self.labels = labels  # (object, field) -> (label, setup token)

    def record(self, sobject, record_id):
        return f"{self.base}/lightning/r/{sobject}/{record_id}/view" if self.base and record_id else ""

    def field(self, sobject, field):
        token = (self.labels.get((sobject, field)) or ("", ""))[1]
        return (f"{self.base}/lightning/setup/ObjectManager/{sobject}/FieldsAndRelationships/{token}/view"
                if self.base and token else "")

    def path(self, path):
        return f"{self.base}{path}" if self.base and path else ""


def dictionary_rows(rows, links):
    out = []
    for row in rows:
        meta, buckets = row["meta"], row["buckets"]
        out.append({
            "Object": row["object"], "Field Label": meta["label"], "API Name": row["field"],
            "Type": meta["type"], "Description": meta["description"], "Help Text": meta["help_text"],
            "Security Classification": meta["security"], "Compliance Group": meta["compliance"],
            "Business Status": meta["status"],
            **{bucket.capitalize() if bucket != "url" else "URL": buckets[bucket] for bucket in BUCKET_ORDER},
            "Total Refs": row["total_refs"], "Surfaces": "; ".join(row["surfaces"]),
            "Used In": _list(row["used_in"]), "Mapped With": _list(row["mapped_with"]),
            "Verdict": row["verdict"], "Documentation": "; ".join(row["documentation"]),
            "Field Link": links.field(row["object"], row["field"]),
        })
    return out


def reference_rows(references, links):
    return [{
        "Object": ref["object"], "Field Label": (links.labels.get((ref["object"], ref["field"])) or ("", ""))[0],
        "Field API Name": ref["field"], "Surface": ref["surface"], "Role": ref["role"],
        "Form Template": ref["template_name"], "Page": ref["page_label"], "Section": ref["section_title"],
        "Component Type": ref["component_type"], "Component": ref["component_label"] or ref["component_key"],
        "Snippet": ref["snippet"],
        "Field Link": "" if ref["is_path"] else links.field(ref["object"], ref["field"]),
        "Template Link": links.record(TEMPLATE_OBJECT, ref["template_id"]),
        "Page Link": links.record(PAGE_OBJECT, ref["page_id"]),
        "Section Link": links.record(SECTION_OBJECT, ref["section_id"]),
        "Component Link": links.path(ref.get("component_path")),
    } for ref in references]


def flow_rows(flow_references, links):
    return [{
        "Object": ref["object"], "Field Label": (links.labels.get((ref["object"], ref["field"])) or ("", ""))[0],
        "Field API Name": ref["field"], "Surface": ref["surface"], "Role": ref["role"],
        "Flow": ref["flow_label"], "Flow API Name": ref["flow_api"], "Flow Type": ref["flow_type"],
        "Flow Tool Kit Role": ref["ftk_role"],
        "Element": ref["element"], "Element Type": ref["element_type"], "Resolution": ref["resolution"],
        "Snippet": ref["snippet"],
        "Field Link": "" if ref["is_path"] else links.field(ref["object"], ref["field"]),
        "Flow Link": links.path(ref.get("flow_path")),
    } for ref in flow_references]


# ---- data-dictionary.md --------------------------------------------------------------------------------------------

def _cell(text):
    return " ".join(str(text if text is not None else "").split()).replace("|", "\\|")


def _short_object(sobject):
    return sobject.replace(NAMESPACE, "")


def summary(analysis):
    rows = analysis["rows"]
    verdicts = {v: 0 for v in VERDICTS}
    for row in rows:
        if row["verdict"]:
            verdicts[row["verdict"]] += 1
    gaps = [row for row in rows if row["documentation"]]
    coverage = analysis["coverage"]
    return {
        "template_references": len(analysis["references"]),
        "flow_references": len(analysis["flow_references"]),
        "fields": len(rows),
        "verdicts": {k: v for k, v in verdicts.items() if v},
        "documentation_gaps": len(gaps),
        "not_captured": sum(1 for c in coverage if c["status"] == "not_captured"),
        "problems": sum(1 for c in coverage if c["status"] in ("unparseable", "missing")),
    }


def markdown(analysis, org, taken_at):
    rows, totals = analysis["rows"], summary(analysis)
    org_name = org.get("Name") or "the org"
    focus = analysis.get("focus")
    scope = (f"every field the {focus} template uses, with its org-wide verdict" if focus else
             "every custom field on " + ", ".join(f"`{o}`" for o in analysis["audit_objects"])
             + ", and every other field a form, mapping or Flow Tool Kit flow uses")
    lines = [f"# Data dictionary: {focus or org_name}", "",
             f"Taken {taken_at} from {org_name}" + (f" ({org['Id']})" if org.get("Id") else "")
             + f". Flow scan: {analysis['options']['flows']}.", "",
             "## Summary", "",
             f"- {totals['fields']} fields: {scope}.",
             f"- {totals['template_references']} uses in templates and forms, {totals['flow_references']} in "
             f"Flow Tool Kit flows."]
    for name, count in totals["verdicts"].items():
        lines.append(f"- {name}: {count}")
    lines.append(f"- Documentation gaps on fields the org owns: {totals['documentation_gaps']}.")
    if totals["not_captured"] or totals["problems"]:
        lines.append(f"- Not scanned: {totals['not_captured']} places; could not parse: {totals['problems']} "
                     f"(see Coverage). A field used only there can look unused here.")
    unreferenced = [r for r in rows if r["verdict"] == UNREFERENCED]
    if unreferenced:
        lines += ["", "## Unreferenced fields", "",
                  "No Form Template, page section, Form Component, mapping or Flow Tool Kit flow references "
                  "these. This is about Flow Tool Kit references only: no record was read, and Apex, reports, "
                  "page layouts and other flows are not checked. Check Coverage and Setup's Where is this used? "
                  "before removing one; a packaged field cannot be deleted.", "",
                  "| Object | Field | API name | Type | Packaged |", "|---|---|---|---|---|"]
        for row in unreferenced:
            lines.append(f"| {_cell(_short_object(row['object']))} | {_cell(row['meta']['label'])} | "
                         f"`{row['field']}` | {_cell(row['meta']['type'])} | "
                         f"{'yes' if row['meta']['is_managed'] else ''} |")
    for sobject in sorted({row["object"] for row in rows}):
        object_rows = [row for row in rows if row["object"] == sobject]
        lines += ["", f"## {_short_object(sobject)} (`{sobject}`)", "",
                  "| Field | API name | Type | Description | Help text | Surfaces | Used in | Mapped with | "
                  "Verdict | Documentation |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for row in object_rows:
            meta = row["meta"]
            lines.append(" | ".join([
                f"| {_cell(meta['label'])}", f"`{row['field']}`", _cell(meta["type"]), _cell(meta["description"]),
                _cell(meta["help_text"]), _cell("; ".join(row["surfaces"])), _cell(_list(row["used_in"], 4)),
                _cell(_list(row["mapped_with"], 4)),
                _cell(row["verdict"]), _cell("; ".join(row["documentation"])) + " |"]))
    lines += ["", "## Coverage", "", "| Store | Status | Detail |", "|---|---|---|"]
    for item in analysis["coverage"]:
        lines.append(f"| {_cell(item['store'])} | {item['status']} | {_cell(item['detail'])} |")
    return "\n".join(lines) + "\n"


def write(out_dir, analysis, org, taken_at, instance_url=""):
    os.makedirs(out_dir, exist_ok=True)
    labels = {(row["object"], row["field"]): (row["meta"]["label"], row["meta"]["setup_token"])
              for row in analysis["rows"]}
    links = Links(instance_url, labels)
    _write_csv(os.path.join(out_dir, "data_dictionary.csv"), DICTIONARY_COLUMNS,
               dictionary_rows(analysis["rows"], links))
    _write_csv(os.path.join(out_dir, "template_references.csv"), REFERENCE_COLUMNS,
               reference_rows(analysis["references"], links))
    _write_csv(os.path.join(out_dir, "flow_references.csv"), FLOW_COLUMNS,
               flow_rows(analysis["flow_references"], links))
    _write_csv(os.path.join(out_dir, "coverage.csv"), COVERAGE_COLUMNS,
               [{"Store": c["store"], "Status": c["status"], "Detail": c["detail"]} for c in analysis["coverage"]])
    with open(os.path.join(out_dir, "data-dictionary.md"), "w", encoding="utf-8") as handle:
        handle.write(markdown(analysis, org, taken_at))
    return summary(analysis)
