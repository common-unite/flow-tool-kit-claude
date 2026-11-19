#!/usr/bin/env python3
"""The plan route: which form-only sections of built plans should share one component, marked in the plans so the next
build-template rebuild makes it. Optional, like the rest of consolidate-sections. A file to mark up, never a change on
its own.

    python3 reviewpass.py review --catalog <catalog.json> --plan <plan.json>[=<match.json>] [--plan ...] --out <review-dir>
    python3 reviewpass.py apply <review-dir>/review-decisions.csv --plan <plan.json> [--plan ...]

Use it instead of consolidate.py when the templates are rebuilt from plan.json files: a rebuild from an unmarked plan
would put each section's own JSON back. It reads org-catalog's findings, never the org itself, and never measures
sections on its own:

- org-catalog's catalog.json (taken after the builds, so it knows them): `repeated_sections` groups the local sections
  that match each other at 80% (by field or with labels) across templates.
- org-catalog's `catalog.py match` result for a plan (match.json, optional): the existing components each section of
  that plan matches, with `fit` covers (the component already has every field) or extend.

From those it proposes, one line per group:

    switch   an existing component already covers the section: use it (existing components first)
    promote  the same design is on --promote-at templates or more (default 2): make one shared record component
    keep     the design repeats on fewer templates than --promote-at

For promote it lists, per member, where its questions differ from the section the shared component is built from
(a field one has and another lacks, a label, required, options). Applying a promote changes only the members that ask
exactly the same questions; a member that differs stays local and is named, so a form's questions never change
silently. To merge a member that differs, settle the difference in its plan first (or use consolidate.py, which asks).

It writes review.md (the report), review-decisions.csv (the file to mark up: put promote, switch or keep in the
decision column, or leave it empty) and review.json (the details apply needs). apply changes only the plans whose rows
are marked promote or switch; then rebuild each changed plan with build-template.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from consolidate import PROMOTE_AT, shared_name  # noqa: E402

MAX_AGE_HOURS = 24
CHOICES = ("promote", "switch", "keep")
DESIGN_KEYS = ("fields", "inner_sections", "rich_text", "rich_text_variant", "inner_title", "inner_type", "label", "Header_Title__c",
               "Header_Subtitle__c", "Title__c", "likert_mode", "likert_scale", "object")
LOCAL = (None, "", "form-only")


class ReviewError(RuntimeError):
    pass


def pct(value) -> str:
    return f"{round(float(value or 0) * 100)}%"


def catalog_age_hours(catalog: dict, now: datetime | None = None) -> float | None:
    taken = catalog.get("taken_at")
    if not taken:
        return None
    when = datetime.fromisoformat(taken.replace("Z", "+00:00"))
    return ((now or datetime.now(timezone.utc)) - when).total_seconds() / 3600


def plan_section(plan: dict, page: int, position: int) -> dict | None:
    pages = plan.get("pages") or []
    if not 1 <= int(page or 0) <= len(pages):
        return None
    sections = pages[int(page) - 1].get("sections") or []
    return sections[int(position) - 1] if 1 <= int(position or 0) <= len(sections) else None


def is_local(plan: dict, section: dict | None) -> bool:
    if not section or section.get("Component_Type__c") in ("Flow", "Lightning Web Component") or section.get("display_text"):
        return False
    component = next((c for c in plan.get("components") or [] if c.get("key") == section.get("component")), {})
    return component.get("decision") in LOCAL and bool(section.get("fields") or section.get("inner_sections"))


def section_fields(section: dict) -> list[dict]:
    fields = list(section.get("fields") or [])
    for inner in section.get("inner_sections") or []:
        fields += inner.get("fields") or []
    return fields


def asks(section: dict) -> dict:
    """{field: (label, required, options)} for the questions a plan section asks."""
    out = {}
    for f in section_fields(section or {}):
        name = re.sub(r"^(\*__|FlowToolKit__)", "", str(f.get("field") or "")).lower()
        if name:
            out[name] = (str(f.get("label") or "").strip().lower(), bool(f.get("required")), json.dumps(f.get("options"), sort_keys=True))
    return out


def plan_differences(member: dict, source: dict) -> list[str]:
    """Where a member section's questions differ from the source section's, in words."""
    mine, theirs = asks(member), asks(source)
    labels = {re.sub(r"^(\*__|FlowToolKit__)", "", str(f.get("field") or "")).lower(): f.get("label") or f.get("field")
              for f in section_fields(source) + section_fields(member)}  # the member's own wording wins
    out = [f"asks {labels[k]}, which the shared component would not" for k in mine if k not in theirs]
    out += [f"lacks {labels[k]}" for k in theirs if k not in mine]
    for k in mine.keys() & theirs.keys():
        if mine[k][0] != theirs[k][0]:
            out.append(f"labels it '{labels[k]}' (the shared component's wording differs)")
        if mine[k][1] != theirs[k][1]:
            out.append(f"{labels[k]} is {'required' if mine[k][1] else 'optional'} here")
        if mine[k][2] != theirs[k][2]:
            out.append(f"{labels[k]} has other options")
    return out


def review(catalog: dict, plans: dict, matches: dict | None = None, promote_at: int = PROMOTE_AT) -> dict:
    """plans: {template Id: plan}; matches: {template Id: catalog.py match result}. Returns the candidates."""
    matches = matches or {}
    candidates, claimed = [], set()
    # 1. switch: an existing component covers a local section (org-catalog's match, best candidate first)
    for template_id, result in matches.items():
        plan = plans.get(template_id) or {}
        for entry in result.get("sections") or []:
            section = plan_section(plan, entry.get("page"), entry.get("position"))
            top = next((c for c in entry.get("candidates") or [] if c.get("fit") == "covers"), None)
            if not top or not is_local(plan, section):
                continue
            member = {"template_id": template_id, "template": (plan.get("template") or {}).get("Name"), "page": entry["page"],
                      "position": entry["position"], "title": entry.get("title")}
            group = next((c for c in candidates if c["call"] == "switch" and c["component"]["component"] == top["component"]), None)
            if group is None:
                group = {"call": "switch", "title": entry.get("title"), "component": top, "members": [],
                         "reason": f"{top.get('label') or top['component']} ({top.get('kind')}) already has every field: "
                                   f"{pct(top.get('by_field'))} by field, {pct(top.get('exact'))} with labels"}
                candidates.append(group)
            group["members"].append(member)
            claimed.add((template_id, int(entry["page"]), int(entry["position"])))
    # 2. promote or keep: org-catalog's repeated sections that touch the templates under review
    for group in catalog.get("repeated_sections") or []:
        members = [m for m in group.get("sections") or [] if m.get("template_id") in plans
                   and (m["template_id"], int(m["page"]), int(m["position"])) not in claimed
                   and is_local(plans[m["template_id"]], plan_section(plans[m["template_id"]], m["page"], m["position"]))]
        if not members:
            continue
        templates = int(group.get("templates") or len({m.get("template_id") for m in group.get("sections") or []}))
        call = "promote" if templates >= promote_at else "keep"
        reason = (f"the same design is on {templates} templates" if call == "promote"
                  else f"repeats on {templates} templates, under the {promote_at}-template rule for sharing")
        source = members[0]
        source_section = plan_section(plans[source["template_id"]], source["page"], source["position"]) or {}
        rows = []
        for m in members:
            section = plan_section(plans[m["template_id"]], m["page"], m["position"]) or {}
            rows.append({"template_id": m["template_id"], "template": m.get("template"), "page": m["page"],
                         "position": m["position"], "title": m.get("section"),
                         "differs": [] if m is source else plan_differences(section, source_section)})
        candidates.append({"call": call, "title": group.get("title"), "component": None, "templates": templates, "reason": reason,
                           "group": group.get("id"), "fields": [f.get("label") or f.get("field") for f in group.get("fields") or []],
                           "outside": [f"{m.get('template')} p{m.get('page')}" for m in group.get("sections") or [] if m.get("template_id") not in plans],
                           "members": rows})
    order = {"switch": 0, "promote": 1, "keep": 2}
    candidates.sort(key=lambda c: (order[c["call"]], -len(c["members"]), str(c["title"])))
    for n, c in enumerate(candidates, 1):
        c["id"] = f"g{n}"
        c.setdefault("templates", len({m["template_id"] for m in c["members"]}))
    taken = {str(c.get("name") or "").lower() for c in catalog.get("components") or []}
    for c in candidates:
        if c["call"] != "switch":
            c["name"] = shared_name(c["title"], taken)
            taken.add(c["name"].lower())
    return {"promote_at": promote_at, "catalog_taken_at": catalog.get("taken_at"), "candidates": candidates}


def markdown(result: dict, title: str = "Review pass") -> str:
    lines = [f"# {title}", "",
             f"Sections that repeat across templates, or that an existing component already covers (org-catalog, taken {result['catalog_taken_at']}). "
             f"Promote at {result['promote_at']} templates. Nothing changes until review-decisions.csv says promote or switch.", ""]
    if not result["candidates"]:
        return "\n".join(lines + ["No section repeats and no existing component covers one: every section stays as built.", ""])
    lines += ["| # | Proposed | Section | Templates | Component | Why |", "|---|---|---|---|---|---|"]
    for c in result["candidates"]:
        existing = (c["component"] or {}).get("label") or (c["component"] or {}).get("component") or c.get("name") or ""
        lines.append(f"| {c['id']} | {c['call']} | {c['title']} | {c['templates']} | {existing} | {c['reason']} |")
    for c in result["candidates"]:
        lines += ["", f"## {c['id']} {c['title']} ({c['call']})", ""]
        if c["component"]:
            top = c["component"]
            lines.append(f"Existing: {top.get('label') or top['component']}, used in {', '.join(top.get('where_used') or []) or 'no template yet'}.")
            if top.get("relabelled"):
                lines.append("Labels that differ: " + ", ".join(f"{r.get('design')} / {r.get('existing')}" for r in top["relabelled"]) + ". "
                             "Switching shows the component's labels.")
        elif c.get("name"):
            lines.append(f"Shared record component: {c['name']}, built from the section on {c['members'][0]['template']}.")
        if c.get("fields"):
            lines.append("Fields: " + ", ".join(c["fields"]))
        for m in c["members"]:
            note = f": differs ({'; '.join(m['differs'])}), stays local unless its plan is settled first" if m.get("differs") else ""
            lines.append(f"- {m['template']} page {m['page']}, section {m['position']} ({m['title']}){note}")
        if c.get("outside"):
            lines.append(f"- also on templates outside this review: {', '.join(c['outside'])}")
    return "\n".join(lines) + "\n"


def write_decisions(result: dict, path: pathlib.Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "proposed", "decision", "section", "templates", "component", "why"])
        for c in result["candidates"]:
            writer.writerow([c["id"], c["call"], "", c["title"], c["templates"],
                             (c["component"] or {}).get("component") or c.get("name") or "", c["reason"]])


def read_decisions(path: pathlib.Path) -> dict:
    out = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            decision = (row.get("decision") or "").strip().lower()
            if decision and decision not in CHOICES:
                raise ReviewError(f"{row.get('id')}: decision {decision!r} is not promote, switch or keep")
            if decision:
                out[row["id"]] = decision
    return out


def apply(result: dict, decisions: dict, plans: dict) -> list[str]:
    """Edit the plans for each candidate marked promote or switch. plans: {template Id: plan}. Returns what changed."""
    changes = []
    for c in result["candidates"]:
        decision = decisions.get(c["id"])
        if decision not in ("promote", "switch"):
            continue
        if decision == "switch" and not c["component"]:
            raise ReviewError(f"{c['id']}: switch needs an existing component, and this row has none; mark it promote or keep")
        source = next(((m, plans[m["template_id"]]) for m in c["members"] if m["template_id"] in plans), None)
        if source is None:
            changes.append(f"{c['id']}: none of its templates' plans was given; nothing applied")
            continue
        member, plan = source
        section = plan_section(plan, member["page"], member["position"]) or {}
        key = re.sub(r"[^a-z0-9]+", "_", str(c["title"]).lower()).strip("_")[:24] or c["id"]
        if decision == "promote":
            local = next((x for x in plan.get("components") or [] if x.get("key") == section.get("component")), {})
            joining = [m for m in c["members"] if not m.get("differs")]
            entry = {"key": key, "decision": "shared-record", "shape": "record", "name": c.get("name") or shared_name(c["title"], set()),
                     "object": section.get("object") or local.get("object") or "Form_Submission__c",
                     "section": {k: section[k] for k in DESIGN_KEYS if k in section},
                     "used_by": sorted({m["template_id"] for m in joining})}
            if local.get("form_template_mapping"):
                entry["form_template_mapping"] = local["form_template_mapping"]
            if len({m["template_id"] for m in joining}) < 2:
                changes.append(f"{c['id']}: only one template asks exactly these questions; nothing applied "
                               "(settle the differences in the plans first)")
                continue
        else:
            top = c["component"]
            joining = c["members"]
            entry = {"key": key, "decision": "reuse", "name": top["component"], "object": top.get("object") or "Form_Submission__c",
                     "reason": f"consolidate-sections: {c['reason']}"}
        for m in c["members"]:
            if m not in joining:
                changes.append(f"{c['id']}: {m['title']} on {m['template'] or m['template_id']} stays local: {'; '.join(m['differs'])}")
                continue
            target = plans.get(m["template_id"])
            if target is None:
                changes.append(f"{c['id']}: the plan for template {m['template_id']} was not given; {m['title']} stays local")
                continue
            sec = plan_section(target, m["page"], m["position"])
            if sec is None:
                changes.append(f"{c['id']}: page {m['page']} section {m['position']} is not in the plan for {m['template_id']}")
                continue
            components = target.setdefault("components", [])
            components[:] = [x for x in components if x.get("key") != key] + [dict(entry)]
            sec["component"] = key
            changes.append(f"{c['id']}: {m['title']} on {m['template'] or m['template_id']} -> {decision} {entry['name']}")
    return changes


def load_plans(values: list[str]) -> tuple[dict, dict, dict]:
    """{template Id: (path, plan)} and {template Id: match result} from --plan <plan.json>[=<match.json>]."""
    plans, matches = {}, {}
    for value in values:
        plan_path, _, match_path = value.partition("=")
        plan = json.loads(pathlib.Path(plan_path).read_text())
        template_id = (plan.get("build") or {}).get("template_id")
        if not template_id:
            raise ReviewError(f"{plan_path} has no build.template_id: build it first")
        plans[template_id] = (pathlib.Path(plan_path), plan)
        if match_path:
            matches[template_id] = json.loads(pathlib.Path(match_path).read_text())
    return plans, matches, {k: v[1] for k, v in plans.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan route: propose shared components from org-catalog's findings; apply the marked-up file")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("review")
    run.add_argument("--catalog", required=True, help="org-catalog's catalog.json, taken after the builds")
    run.add_argument("--plan", action="append", required=True, help="a built plan.json, optionally =<its catalog.py match result>")
    run.add_argument("--out", default="review")
    run.add_argument("--title", default="Review pass")
    run.add_argument("--promote-at", type=int, default=PROMOTE_AT)
    run.add_argument("--allow-stale", action="store_true")
    put = sub.add_parser("apply")
    put.add_argument("decisions", help="the marked-up review-decisions.csv (review.json must be beside it)")
    put.add_argument("--plan", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "review":
            catalog = json.loads(pathlib.Path(args.catalog).read_text())
            age = catalog_age_hours(catalog)
            if not args.allow_stale and (age is None or age > MAX_AGE_HOURS):
                raise ReviewError("The catalog is older than a day or undated: run org-catalog again after the builds, so it knows them")
            _, matches, plans = load_plans(args.plan)
            result = review(catalog, plans, matches, args.promote_at)
            out = pathlib.Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "review.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
            (out / "review.md").write_text(markdown(result, args.title))
            write_decisions(result, out / "review-decisions.csv")
            print(markdown(result, args.title))
        else:
            path = pathlib.Path(args.decisions)
            result = json.loads((path.parent / "review.json").read_text())
            paths, _, plans = load_plans(args.plan)
            changes = apply(result, read_decisions(path), plans)
            for plan_path, plan in paths.values():
                plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
            print("\n".join(changes) or "No row says promote or switch; nothing changed.")
    except ReviewError as error:
        sys.exit(f"reviewpass: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
