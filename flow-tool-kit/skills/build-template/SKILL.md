---
name: build-template
description: Use when a Flow Tool Kit (FTK) form design (form-design's plan.json) needs to become a working draft Form Template in a Salesforce org, or when a review changes the plan and the draft must be rebuilt. Also when someone asks to build, rebuild or seed a Form Template from a plan, or to check a built template against its plan. Runs after form-design, usually from ftk-start.
---

# Build Template

Turns `plan.json` into a draft Form Template (one whole form, end to end) someone can click through: the template, its pages and sections, every field with its control, widths and words, every page, section and field rule, the banner header and logo, and the form-type settings (stages, Save Progress, review screen, answers PDF). It builds **records**, not metadata, so a rebuild during a review takes seconds. Each component is built in the **shape** the plan names ([_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)): JSON on its section, a record component through the package's import, or a metadata component that build-form-component deploys and the build then binds by name.

It builds exactly what the plan says. Anything it cannot build exactly stops the build with a list of what to fix in the plan; it never guesses and never leaves a rule for someone to finish in Form Builder.

## Build modes

Before running a build, to pick metadata or records mode, read [references/build-modes.md](references/build-modes.md) (Build modes).

## Where it runs

| Surface | What it does |
|---|---|
| Claude Code (local or on the web) with the Salesforce CLI | Everything: the records, the record components (through anonymous Apex), metadata components bound by name once build-form-component has deployed them, the add-only brand styles, new fields and the PDF running user (metadata, deployed with the person's go-ahead), the round trip. In records mode, everything but the deploys, which stay follow-ups |
| claude.ai chat with a Salesforce connector that can create, update and delete records | A records-mode build: template, pages, sections and record components, from a dry run ([references/chat-build.md](references/chat-build.md)). Record components go in through Apex when the connector runs it, otherwise Form Builder's Import button. A metadata-mode plan with metadata components cannot finish in chat: say so in one line and ask whether to switch the plan to records mode or wait for Claude Code. The round trip needs Claude Code |
| No org connected | A dry run: every record and component the build would write, to review or build later |

Python 3 standard library only. Run the scripts by their path in this skill folder.

## Before you build

1. **The plan** comes from form-design, normalized (`draw_plan.py` has run, so `form_type`, `styleTokens` and the template's switches are written) and reviewed. Its format is form-design's `references/plan-format.md`; the keys this skill reads, and the few it adds, are in [references/plan-keys.md](references/plan-keys.md).
2. **The project config** `flow-tool-kit.json` (ftk-start writes it) gives the org's **edition**, **audiences** and **brand kit** choice. The build finds it beside the plan or in a folder above it. Without it the build says so and assumes the paid edition with no brand kit.
3. **New fields** (metadata mode; records mode leaves them out and names them as a follow-up). If the plan proposes fields (`new_field: true`, listed in its questions and answered), create them first, after org-catalog's `name-check` says each name is free:
   ```bash
   python3 scripts/newfields.py _forms/<slug>/plan.json --out <project-dir>
   ```
   It writes each field with its description (the documentation standard: `_shared/standards/documentation.md`) and one permission set that grants the form's respondents Read and Edit on them. Show the person the files, deploy them once they agree (`sf project deploy start`), and assign the permission set to the site guest user, portal users or staff who fill in the form. The build stops while a planned field is missing from the org, because the form silently draws nothing for an unknown field.
4. **Form Labels** (metadata mode). If the plan's words use `{{$Label.X}}` tokens, each needs a Form Label in the org (and a Form Label Translation per language): `python3 scripts/formlabels.py _forms/<slug>/plan.json --out <project-dir>` writes the ones the plan defines under `form_labels`; deploy them once the person agrees. The build stops while one is missing, because the package shows nothing for an unknown label.
5. **Brand images** named in the plan's `assets` must already be public Asset Files (brand-kit loads them).

## Run it

```bash
python3 scripts/buildtemplate.py _forms/<slug>/plan.json --org <org-alias> --dry-run   # see every record first
python3 scripts/buildtemplate.py _forms/<slug>/plan.json --org <org-alias>
```

The first run writes `build.template_id`, `build.key`, `build.prefix` and `build.form_ids` back into `plan.json`, so every rebuild updates the same template and keeps every generated name. Later runs update the template and pages in place, delete pages the plan dropped, and recreate every section. A run that fails after creating a new template deletes it, with the Pre-fill Template Flow Tool Kit made for it (the report's `prefill_template_id`), so no half-built template is ever left; a rebuild that fails says so, and the fix is to correct the plan and run it again, never to patch the template by hand.

The report lists the build mode, what was created, updated and deleted, the rules counted in the org against the plan, the header, the styles, the **setup** the org still needs, and the **handoffs** to other skills; in records mode also `convert_later`, `left_out` and the `follow_ups` for Claude Code.

## What it builds, the brand and the handoffs

While building, and before handing over, read [references/what-it-builds.md](references/what-it-builds.md) (What it builds, The header, the logo and the brand, Setup and handoffs, Optional: offer consolidate-sections once, Know the org you are building in).

## After the build: check it

A template is not done until all three pass.

1. **Round trip.** `python3 scripts/roundtrip.py _forms/<slug>/plan.json --org <org-alias>` reads the built template back and compares it with the plan, field by field: switches, header, pages, sections, frames, rules, and inside each form every field's name, order, widths, required, label, hidden label and consent wording. It must print `0 mismatches`. What a records-mode build left out until deployed (the new fields and every rule that reads one, recorded in the plan's `build.left_out`) is listed on its own, never as a mismatch, and so is a planned picklist value the org lacks for the form's record type (listed as waiting for Setup: the form already lists it, so it shows once added, with no rebuild). It also catches an edit made in Form Builder since the build, which the next rebuild would erase.
2. **Walk every rule both ways.** In the template's Preview Form, answer each controlling question both ways and watch its page, section or field appear and disappear. Count them against the plan. In Claude Code with a headless browser, do it there; otherwise ask the person to, and list the rules to walk.
3. **Look at it.** Walk every page in Preview Form at desktop and phone width: the banner with its logo, section headers and frames, widths, button labels and placement. Reset Form Cache in Form Builder first if any metadata changed.

## Common mistakes

| Mistake | Instead |
|---|---|
| Editing the draft in Form Builder during a review | Change `plan.json` and rebuild, or the next rebuild erases the edit (the round trip finds it) |
| Building before the plan's new fields exist | `newfields.py`, deploy, then build |
| Patching a half-built template by hand | Fix the plan and rerun; a failed new template is deleted for you |
| Choosing the shape, or building every component one way | Build the shape the plan records; a shape never asked stops the build |
| Copying a reused component into a new record or JSON | Reference it: its API name, or `<Name>_v0` with its Id; only new or extended pieces are created |
| Deploying metadata, or stopping, in records mode | Build the record component, record `built_shape`, and name the deploy as a follow-up for Claude Code |
| Calling a Form Template reused | A template is one whole form; reuse is of the components placed in it |
| Extending a component by editing the original | `extend` builds a new version; changing the original is `update`, its own answered question naming every template it reaches |
| A form on Contact or Account in a paid org with no Form Template Mapping | Map every field in the plan's `form_template_mapping` |
| Turning on the Save Progress email in stages mode | Stages sends the resume button's email; the build keeps Save Progress email off |
| Making a theme for a brand, or overwriting the org's styles | Add-only Form Style defaults, the rest on the template's Style Overrides |
| A header component or logo field made for one org | The packaged Banner settings and the template's own Logo, Logo Override and Default Logo |
| Saying "built" from the report alone | The round trip at 0 mismatches, every rule walked both ways, every page looked at |
| Sharing a section during the build because two forms have it | Build the shapes the plan names; after the build, offer consolidate-sections once (optional) |
