#!/usr/bin/env python3
"""Turn a form folder's ir.json into the review files: mappings, questions and the discovery report.

    python3 <skill>/scripts/plan_form.py <form_dir>
        [--org <alias> | --use-default-org | --describe-file <file>] [--force-app force-app]
        [--edition paid|free] [--org-id <00D...>] [--config flow-tool-kit.json]
        [--compound-address] [--edits <mappings.csv|mappings.json>]

The edition comes from flow-tool-kit.json, the project config ftk-start writes (found at or above the form
folder or the working directory, the org's entry picked by org Id, alias, or as the only entry). --edition
overrides it. With neither, placement stays open and the edition becomes the first question.

Reads <form_dir>/ir.json. Writes into <form_dir>:
    mappings.csv, mappings.json   one row per question; the reviewer edits the first three columns
    decisions.json                the reviewer's edits, kept across regenerations
    questions.md                  the decisions only the org's people can make
    discovery-report.md           what the form does, what was and was not captured, and the plan
    validation.json               the checks, including the ones skipped and why

Where the Form Submission field names come from, best first: --describe-file (a describe saved from a Salesforce
connector in chat), the org through the Salesforce CLI (--org or --use-default-org), --force-app, else the snapshot
shipped with the skill. Anything short of the org marks every row "Verify In Org".

Edits: run it, let the reviewer edit mappings.csv or mappings.json (or an artifact page whose edits you copy into
mappings.json), then run it again. The newer of the two files is read back unless --edits names one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import (decisions, fieldplan, ir, ladder, mappings, projectconfig,  # noqa: E402
                         questions, review, schema, sensitive, validate)

_SCHEMA_SOURCE = {
    "org": "read live from the org",
    "describe-file": "read from a describe saved from the org",
    "force-app": "read from the project's retrieved metadata",
    "force-app+snapshot": "the project's own fields plus the shipped snapshot (verify each)",
    "snapshot": "the snapshot shipped with the skill (verify each in the org)",
}


def _latest_edits(form_dir: str, named: str | None) -> str | None:
    if named:
        return named
    candidates = [os.path.join(form_dir, n) for n in ("mappings.json", "mappings.csv")]
    present = [p for p in candidates if os.path.exists(p)]
    return max(present, key=os.path.getmtime) if present else None


def settings_for(form_dir: str, org: str | None = None, use_org: bool = False,
                 org_id: str | None = None, config_path: str | None = None) -> dict:
    """This org's entry in flow-tool-kit.json, searched from the form folder, then the working directory."""
    found = projectconfig.resolve(form_dir, config_path, org_id, org, use_cli=bool(org or use_org))
    if not found.get("config_path") and not config_path:
        found = projectconfig.resolve(None, None, org_id, org, use_cli=bool(org or use_org))
    return found


def plan(form_dir: str, edition: str | None = None, org: str | None = None, use_org: bool = False,
         describe_file: str | None = None, force_app: str | None = None,
         compound_address: bool = False, edits: str | None = None,
         org_id: str | None = None, config_path: str | None = None) -> dict:
    """Write the review files. ``edition`` overrides the project config's answer."""
    settings = settings_for(form_dir, org, use_org, org_id, config_path)
    options_edition = edition
    edition = edition or projectconfig.edition(settings)
    ir_path = os.path.join(form_dir, "ir.json")
    document = ir.load(ir_path)
    before = [f.get("sensitive") for f in document["fields"]]
    sensitive.mark(document)
    if [f.get("sensitive") for f in document["fields"]] != before:
        # An ir.json captured before the check existed gets its marks, so form-design reads them too.
        with open(ir_path, "w", encoding="utf-8") as handle:
            handle.write(ir.to_json(document))
    form_name = document["source"].get("form_name") or document["source"].get("form_id") or "Form"

    submission = schema.load(force_app=force_app, org=org, use_org=use_org, describe_file=describe_file)
    target_org = (org or "") if submission.source == "org" else None
    proposals = fieldplan.build(document, submission, force_app=force_app,
                                compound_address=compound_address, edition=edition, org=target_org)
    review.apply(proposals, review.load_overrides(form_dir))

    kept = decisions.load(form_dir)
    edit_file = _latest_edits(form_dir, edits)
    if edit_file:
        kept.update(decisions.read_edits(edit_file))
        decisions.save(form_dir, kept)
    applied = decisions.apply(proposals, kept)

    if submission.source == "org":
        metadata = validate.load_org_metadata_from_org(document, org)
    elif force_app and os.path.isdir(force_app):
        metadata = validate.load_org_metadata(force_app)
    else:
        metadata = None
    findings = validate.validate(document, metadata)
    items = ladder.plan(document)
    asks = questions.build(document, proposals, findings, edition=edition, ladder_items=items)
    summary = fieldplan.summarize(proposals)

    def write(name, text):
        with open(os.path.join(form_dir, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    write("mappings.csv", mappings.to_csv(form_name, proposals, kept))
    write("mappings.json", mappings.to_json(form_name, proposals, kept, summary))
    write("questions.md", questions.to_markdown(form_name, asks))
    write("validation.json", json.dumps(findings, indent=2, ensure_ascii=False))
    text = report(document, proposals, findings, items, asks, submission, edition, summary)
    if edition and not options_edition and settings.get("edition_source") == "assumed":
        text = text.replace("## Plan\n", "## Plan\n\nThe edition is assumed (paid) in flow-tool-kit.json: "
                            "confirm the edition on the license before building.\n", 1)
    write("discovery-report.md", text)
    return {"proposals": proposals, "findings": findings, "ladder": items, "questions": asks,
            "schema_source": submission.source, "applied": applied, "summary": summary,
            "edition": edition, "settings": settings}


def report(document, proposals, findings, items, asks, submission, edition, summary) -> str:
    source = document["source"]
    coverage = source.get("coverage", {})
    lines = [f"# Discovery report: {source.get('form_name') or source.get('form_id')}", ""]
    lines += [f"Source: {source.get('platform')}" + (f", {source.get('source_url')}" if source.get("source_url") else ""), ""]
    lines += ["## How each part was read", "", "| Aspect | State |", "|---|---|"]
    lines += [f"| {aspect} | {state} |" for aspect, state in coverage.items()]
    lines += ["", "parsed: read by a parser. hand_authored: transcribed by a person or by Claude from the page. "
              "none_exist: the source has no such thing. not_captured: it exists and was not read, a known gap. "
              "unknown: nobody said, treated as a gap.", ""]
    lines += ["## What the form holds", "",
              f"- {len(document['fields'])} questions in {len(document['structure'])} sections or pages",
              f"- {len(document['conditions'])} show/hide rules",
              f"- {sum(len(f.get('options') or []) for f in document['fields'])} choices",
              f"- {len(document.get('images') or [])} images, {len(document.get('custom_scripts') or [])} custom scripts",
              ""]
    lines += ["## Plan", "",
              f"Flow Tool Kit edition: {edition or 'not known yet (see questions.md)'}. "
              f"Form Submission fields: {_SCHEMA_SOURCE.get(submission.source, submission.source)}.", ""]
    lines += [f"- {mappings.DISPOSITION_LABEL.get(k, k)}: {v}" for k, v in summary.items()]
    placed = {}
    for p in proposals:
        key = mappings._built_on(p) if p.placement else "Not placed"
        placed[key] = placed.get(key, 0) + 1
    lines += ["", "Where questions are built:", ""] + [f"- {k}: {v}" for k, v in sorted(placed.items())]
    verify = sum(1 for p in proposals if p.verify)
    if verify:
        lines += ["", f"{verify} rows are marked Verify In Org: their Form Submission field names were not checked "
                      "in the org this form will run in."]
    for note in submission.notes:
        lines += ["", note]
    lines += ["", "## Calculations and custom code", "", ladder.to_markdown(items)]
    lines += ["## Checks", ""]
    for finding in findings:
        lines.append(f"- **{finding['severity']}** ({finding['check']}): {finding['message']}")
    lines += ["", "## Findings from the source", ""]
    lines += [f"- {f['source']}: {f['message']}" for f in document.get("findings", [])] or ["- None."]
    lines += ["", f"## Decisions needed: {len(asks)}", "", "See questions.md.", ""]
    return "\n".join(lines)


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    args.add_argument("form_dir")
    args.add_argument("--edition", choices=("paid", "free"),
                      help="overrides the edition in flow-tool-kit.json")
    args.add_argument("--org-id", help="the org's Id, to pick its entry in flow-tool-kit.json")
    args.add_argument("--config", help="path to flow-tool-kit.json, if it is not at or above the form folder")
    args.add_argument("--org", help="Salesforce CLI alias or username to read the org through")
    args.add_argument("--use-default-org", action="store_true", help="read the CLI's default org")
    args.add_argument("--describe-file", help="a Form Submission describe saved from a Salesforce connector")
    args.add_argument("--force-app", help="the project's source folder, if it holds retrieved metadata")
    args.add_argument("--compound-address", action="store_true",
                      help="only when State and Country/Territory Picklists are on in the org")
    args.add_argument("--edits", help="the edited mappings file to read back (default: the newer of the two)")
    options = args.parse_args(argv)
    result = plan(options.form_dir, options.edition, options.org, options.use_default_org,
                  options.describe_file, options.force_app, options.compound_address, options.edits,
                  options.org_id, options.config)
    verify = sum(1 for p in result["proposals"] if p.verify)
    source = "argument" if options.edition else ("flow-tool-kit.json" if result["edition"] else "unknown, asked")
    print(f"edition: {result['edition'] or 'not set'} ({source}); "
          f"{len(result['proposals'])} rows ({', '.join(f'{k} {v}' for k, v in result['summary'].items())}); "
          f"schema: {result['schema_source']}; {verify} to verify in the org; "
          f"{len(result['questions'])} questions; {len(result['ladder'])} ladder items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
