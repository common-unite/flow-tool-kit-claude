#!/usr/bin/env python3
"""Draw one or more plan.json files as one review canvas, after checking them and filling in what the rules decide.

    python3 draw_plan.py _forms/<slug>/plan.json [more plan.json ...] [--mode code|chat] [--out DIR] [--config flow-tool-kit.json]
                         [--kit DIR] [--check] [--title TEXT]

Steps, in order:
1. normalize: counted page times, the form-type row's template switches, banner, Continue buttons, section spacing,
   Style Editor tokens and rich text scaled to the Text size are written into each plan.json (each change is printed).
   --check changes nothing and fails when a plan is out of step.
2. check: the design checks (references/checks.md). Any error stops here with every message listed.
3. draw: <out>/project/*.dc.html and canvas.json, <out>/publish-batches.json for the mode, <out>/uploads.json (images
   still to upload to the canvas), <out>/review.html (the self-contained fallback page) and field-audit.csv beside each plan.

The design system link comes from flow-tool-kit.json (design_systems.forms.url), found next to the first plan or in a
folder above it. Without it, plan.json, the field audit and review.html are still written, and the run says to install
the design system with ftk-start. Exit codes: 0 drawn, 1 check errors, 3 drawn without a design system link.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from formdesign import boards, checks, planrules, publish  # noqa: E402

# The full kit is a release asset, not part of the plugin: ftk-start unpacks it here (ds_install.py fetch or unpack)
DEFAULT_KIT = pathlib.Path(os.environ.get("FTK_DESIGN_SYSTEMS_DIR") or "~/.flow-tool-kit/design-systems").expanduser() / "ftk-forms"
CONFIG_NAME = "flow-tool-kit.json"


def find_config(start: pathlib.Path, given: str | None) -> tuple[dict, pathlib.Path | None]:
    if given:
        path = pathlib.Path(given)
        return json.loads(path.read_text()), path
    for folder in [start, *start.parents]:
        path = folder / CONFIG_NAME
        if path.exists():
            return json.loads(path.read_text()), path
    return {}, None


def org_settings(config: dict, plan: dict) -> dict:
    """This plan's org in the config: intake.org_id, else the only org there."""
    orgs = config.get("orgs") or {}
    org_id = (plan.get("intake") or {}).get("org_id")
    if org_id in orgs:
        return orgs[org_id]
    return next(iter(orgs.values())) if len(orgs) == 1 else {}


def find_kit(given: str | None) -> pathlib.Path | None:
    kit = pathlib.Path(given) if given else DEFAULT_KIT
    return kit if (kit / "project" / "components" / "bundle.js").exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plans", nargs="+", help="plan.json files; one canvas holds them all")
    ap.add_argument("--mode", choices=("code", "chat"), default="code",
                    help="code: Claude Code copies the design system server side; chat: files from the full kit, 16 a call")
    ap.add_argument("--out", help="the canvas folder (default: design/ beside the first plan)")
    ap.add_argument("--config", help=f"the project config (default: {CONFIG_NAME} next to the first plan or above it)")
    ap.add_argument("--kit", help="the full FlowToolKit Forms kit folder holding project/ (default: where ftk-start unpacks it, ~/.flow-tool-kit/design-systems/ftk-forms)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 when a plan is out of step or fails a check")
    ap.add_argument("--title", help="the canvas title (default: the first form's name)")
    args = ap.parse_args(argv)

    paths = [pathlib.Path(p).resolve() for p in args.plans]
    plans = [(p, json.loads(p.read_text())) for p in paths]
    config, config_path = find_config(paths[0].parent, args.config)
    failed = False
    for path, plan in plans:
        base = path.parent
        trial = copy.deepcopy(plan)
        changes = planrules.normalize(trial, base)
        if args.check and changes:
            print(f"{path}: out of step with the rules ({len(changes)} value(s)); run without --check to write them:")
            failed = True
        elif changes:
            plan.clear()
            plan.update(trial)
            path.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
            print(f"{path}: updated {len(changes)} value(s)")
        for line in changes:
            print(f"  {line}")
        errors, warnings = checks.check(trial, base, org_settings(config, trial))
        for w in warnings:
            print(f"  warning: {w}")
        for e in errors:
            print(f"  ERROR: {e}")
        failed = failed or bool(errors)
    if failed:
        print("Stopped: fix the errors above in plan.json and run again. Nothing was drawn.")
        return 1
    if args.check:
        print("All plans pass.")
        return 0

    out = pathlib.Path(args.out).resolve() if args.out else paths[0].parent / "design"
    out.mkdir(parents=True, exist_ok=True)
    kit = find_kit(args.kit)
    ds = (config.get("design_systems") or {}).get("forms") or {}
    slugs = []
    for path, plan in plans:
        slug = plan.get("slug") or path.parent.name or "form"
        while slug in slugs:
            slug += "-2"
        slugs.append(slug)
    triples = [(slug, plan, path.parent) for slug, (path, plan) in zip(slugs, plans)]
    files = publish.local_images(triples, kit)
    urls, pending = publish.canvas_urls(out, files)
    measured_path = out / "measured-heights.json"
    measured = json.loads(measured_path.read_text()) if measured_path.exists() else {}

    def draw(images: dict) -> tuple[list, list, list]:
        groups, everything, rows = [], [], []
        ctxs = []
        for slug, plan, base in triples:
            shot = files.get(f"source-{slug}")
            ctx = boards.Ctx(plan, images, slug, planrules.load_ir(plan, base))
            ctxs.append(ctx)
            form_boards = boards.source_boards(ctx, images.get(f"source-{slug}"), publish.pixel_size(shot) if shot else (0, 0))
            if ctx.long:
                form_boards.append(boards.stages_board(ctx))
            for i in range(len(ctx.pages)):
                form_boards += boards.page_boards(ctx, i)
            if ctx.long:
                form_boards += boards.review_boards(ctx)
            groups.append({"kind": "multi" if ctx.multipage else "single", "slug": slug, "title": ctx.title, "boards": form_boards,
                           "notes": boards.design_notes(ctx)})
            rows.append((base, boards.audit_rows(ctx)))
        brand = boards.brand_board(ctxs[0])
        if brand:
            groups.insert(0, {"kind": "brand", "boards": [brand]})
        tail = [boards.confirmations_board(ctxs)] + boards.email_boards(ctxs, images)
        tail += boards.audit_boards([r for _, rs in rows for r in rs], ctxs[0].style, len(ctxs))
        groups.append({"kind": "tail", "boards": tail})
        for g in groups:
            everything += g["boards"]
        return groups, everything, rows

    style = planrules.style(plans[0][1])
    fonts = style.get("fonts_href")
    title = args.title or f"{(plans[0][1].get('template') or {}).get('Name') or 'Form'}: design review"
    groups, everything, rows = draw(urls)
    for base, form_rows in rows:
        with open(base / "field-audit.csv", "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(boards.AUDIT_COLUMNS)
            writer.writerows(form_rows)
    result = publish.write_canvas(out, everything, groups, style, fonts, ds, measured, title)
    publish.write_uploads(out, pending, plans[0][1].get("canvas_url"))
    if kit:
        _, standalone, _ = draw(publish.image_refs(files))
        for b in standalone:
            b["h"] = min(boards.CAP, int(measured.get(b["name"]) or b["h"]))
        size = publish.write_standalone(out / "review.html", standalone, style, fonts, kit, title, publish.data_urls(files))
        print(f"review.html written ({size // 1024} KB): the self-contained fallback page")
    else:
        print("review.html not written: the full FlowToolKit Forms kit was not found; get it with ftk-start's design system step (`ds_install.py fetch` in Claude Code, or `ds_install.py unpack --zip` on the attached release zip in chat), or pass --kit")
    print(f"{len(everything)} artboards in {out / 'project'}; tallest {max(b['h'] for b in everything)}px")
    for slug, plan, _ in triples:
        print(f"  {slug}: {len(planrules.pages(plan))} page(s), row {planrules.form_row(plan)}, {plan.get('form_type')}, "
              f"{planrules.minutes_range(planrules.form_seconds(plan))}")
    if result["stale"]:
        print("removed stale artboards: " + ", ".join(result["stale"]))
    if pending:
        print(f"{len(pending)} image(s) to upload to the canvas (uploads.json): " + ", ".join(p["name"] for p in pending)
              + ". Upload them as canvas assets, record each url and sha1 in blobs.json, and run again; until then they draw as placeholders.")
    if not ds.get("url"):
        ready = "plan.json, field-audit.csv and review.html are ready now." if kit else \
            "plan.json and field-audit.csv are ready now; review.html is not (the full kit is missing)."
        print("No FlowToolKit Forms design system link in flow-tool-kit.json. Run ftk-start's design system step to install your "
              "own copy; then run this again to write the publish batches. " + ready)
        return 3
    if args.mode == "chat" and not kit:
        print("Chat publishing needs the full kit to write the design system files; get it with ftk-start's design system step (`ds_install.py fetch` in Claude Code, or `ds_install.py unpack --zip` on the attached release zip in chat), or pass --kit.")
        return 3
    batches = publish.publish_batches(out, result["written"], result["stale"], args.mode, ds, kit)
    print(f"publish-batches.json: {len(batches['batches'])} call(s) of at most {batches['per_call']} files, in order, to the canvas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
