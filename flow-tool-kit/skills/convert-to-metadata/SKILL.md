---
name: convert-to-metadata
description: Use when a Flow Tool Kit Form Template that was prototyped in records mode is final and its new or extended components should become metadata components, so they live in source control and deploy to every org. Triggers include "convert this form to metadata", "the prototype is approved, make it metadata", "move the record components into the repo", "turn the JSON sections into components". Converts only the record components and JSON sections built for that template into Form__mdt components with their sections, fields, rules, conditions and Form Labels, after a dry run the person confirms, then repoints the template's sections at them. Components the template only references are left alone, and the original records are never deleted in the same run. The dry run works in chat; the deploy needs Claude Code.
---

# Convert to Metadata

A Form Template prototyped in **records mode** has its new and extended components built as Form Component records (record type Record Component) and its form-only questions as JSON on the page section, so it could be designed, reviewed and changed without a deploy. When the design is final, this skill turns exactly those pieces into **metadata components** (a Form, `Form__mdt`, with its sections, fields, conditional logic rules and conditions, plus the Form Labels and translations their text uses) and points the template at them. The shapes are explained in [_shared/standards/component-shapes.md](_shared/standards/component-shapes.md).

**What is converted, and what is not**

| The template uses | What happens |
| :- | :- |
| A record component build-template's records mode built in place of a planned metadata component (its build report's `convert_later`, or `built_shape: "record"` on the plan's component) | Converted to a metadata component under the same name |
| Without those marks (a plan built before build modes, or by hand): a record component the plan built for this form (`shared-new`, `extend` (the new version), `shared-record`, `form-only`) | Converted, the same way |
| A page section with its own JSON (the section editor's custom mode) | Converted to a metadata component of its own, named after the section's title |
| A metadata component (the org's own or packaged) | Left alone |
| A record component the reuse question answered **reuse** (or **update**), or the original of an **extend** | Left alone: it is referenced, not part of this form |
| Flow, Lightning Web Component and Display Text sections | Left alone: they draw no component |

**Called by** the person when the prototype is approved, usually after build-template built the template in records mode (`intake.build_mode: "records"`). **Reads** the template from the org, `plan.json` (every reuse, extend and new answer, and build-template's `built_shape` marks), build-template's build report (its `convert_later` list), org-catalog's `catalog.json` when it is fresh, and `flow-tool-kit.json` for the org's alias. **Uses** build-form-component's `scripts/component.py`, which writes the metadata record files and checks them, so a converted component is written exactly like one built as metadata from the start.

## Where it runs

| Runtime | What works |
|---|---|
| Claude Code, local or on the web, with the Salesforce CLI signed in | Everything below |
| claude.ai chat with a Salesforce connector | The dry run: run the snapshot queries through the connector, then `plan` in the code sandbox, and walk the person through the list. Say in one line: "Deploying metadata needs Claude Code; open the project there with this conversion file and it carries on from the build." Hand over `conversion.json` |
| claude.ai chat, no connector | Nothing to read the template with. Say the same line and stop |

On the web the CLI signs in with `sf org login sfdx-url` or `sf org login jwt` ([_shared/standards/runtime.md](_shared/standards/runtime.md)). Every script is Python 3 standard library only; run it by its path in this skill folder.

## Why the skill writes files instead of calling the package

The Form Builder saves a component by deployment type. For metadata it builds every record of the component (Form, sections, fields, rules, conditions, and changed Form Labels and translations) into one custom metadata deploy and enqueues it from inside the package. That save is not exposed to an org's own code: it is callable only from the Form Builder's own page, and the package's one global save, `FlowToolKit.FormComponentImport.createRecordComponent`, writes **record** components only. So the skill takes the other path the package supports: it writes the same custom metadata records as source files (the same types, record names, labels, columns and flat `config__c` the package's save writes) and deploys them with the Salesforce CLI. A bonus: the converted component is then in the project, version controlled, like every other metadata component. [references/package-path.md](references/package-path.md) maps each part of the package's save to what the skill writes.

## Before you start

1. **The org and the project.** The org's alias comes from `flow-tool-kit.json` ([_shared/standards/project-config.md](_shared/standards/project-config.md)), else the CLI's default org. Name the org in the same message as the dry run. Work inside the Salesforce project the components should land in (a folder below `sfdx-project.json`); the files go to the folder the project already keeps custom metadata in, else `<package directory>/main/default/customMetadata`. Keep the conversion's own files in `_forms/<slug>/convert/` ([_shared/standards/documentation.md](_shared/standards/documentation.md), section 6, Naming).
2. **The template.** Its Id, or its exact Name.
3. **The plan and the build report.** `plan.json` for this form ([_shared/standards/plan-format.md](_shared/standards/plan-format.md)) and, when build-template saved it, its build report. In records mode build-template lists every component it built as a record in place of a planned metadata one under the report's `convert_later` and marks it `built_shape: "record"` in the plan: that list is what gets converted, and a record component the plan chose to keep as a record is left alone unless you include it by name. A component the plan only references (reuse, update, the original of an extend) is never converted, even when a list or `--include` names it. Without those marks the plan's decisions decide. Without a plan the dry run still works: a record component only this template uses is proposed for conversion and marked "confirm", and one any other template or component uses is left alone.
4. **The catalog** (optional). org-catalog's `catalog.json`, when under 24 hours old, adds the components that place another component to the "used elsewhere" check ([_shared/standards/catalog-format.md](_shared/standards/catalog-format.md)).

## 1. Read the template

```bash
python3 scripts/convert.py snapshot --template "<Id or Name>" --target-org <org-alias> --out _forms/<slug>/convert/snapshot.json
```

It reads the template, its pages and sections, every record component they draw (and any those place in turn), every other template, section and record component that names them, the org's Form Objects, the names of the org's own metadata components and their children (so nothing is overwritten), and the Form Labels the designs use. In chat, `python3 scripts/convert.py queries --template "<Id or Name>"` prints the first queries and `queries --snapshot <file>` the follow-up ones; run each through the connector and save the rows under its `key` ([references/snapshot.md](references/snapshot.md)).

## 2. The dry run

```bash
python3 scripts/convert.py plan --snapshot _forms/<slug>/convert/snapshot.json --plan _forms/<slug>/plan.json \
  [--build-report <build-template's report.json>] [--catalog ftk-catalog/<org Id>/catalog.json] \
  --out _forms/<slug>/convert/conversion.json
```

Nothing changes in the org or the project. It prints three lists and writes them to `conversion.json`:

- **Convert to metadata**: each record component and JSON section, why it is converted, where the template uses it, the metadata component name it becomes, and every section, field, rule and condition record name it creates, plus a new Form Object when the org has none for its object.
- **Left alone**: every component the template references, with the reason (already metadata, packaged, the plan's answer was reuse, used by another template or component).
- **Repointed**: every page section (and the template's header or footer) that changes, with the value before and after.

Then the Form Labels the converted text uses, **problems** (exit 2: the conversion cannot run until each is fixed) and **warnings**. When build-form-component sits beside this skill, the dry run also runs its checker on every converted design and lists its errors as problems.

### Questions to ask, all in one message

Read the three lists to the person in plain words and ask only what the run raises, each with a recommendation:

- **The list itself.** *"I will convert Household Members (a record component built for this form) and the Plot preferences section into metadata components, and leave Contact Details as it is. Two sections of the template change. Go ahead?"* No yes, no build.
- **A missing description** (problem). A metadata component needs one ([_shared/standards/documentation.md](_shared/standards/documentation.md)). Draft it (what it collects, where the answers go) and pass `--describe <Name>="<text>"`.
- **Proposed without a plan.** Each record component marked "confirm": was it built for this form? `--exclude <Name>` leaves one alone; `--include <Name>` converts one the run left alone (never one the plan only references).
- **A name.** A JSON section is named after its title (`Plot preferences` becomes `Plot_Preferences`), named for its purpose ([_shared/standards/documentation.md](_shared/standards/documentation.md), section 6, Naming); offer a better one with `--rename <section Id>=<Name>`. A record component keeps its name; when the org already has a metadata component of that name the run stops rather than overwrite it, and `--rename <Name>=<New_Name>` picks another.
- **A section placing a record component that stays a record** (problem). Metadata cannot point at a record component: convert that one too, or leave this one as it is.
- **Form Managers and preview data** (warnings). User Ids in Form Managers mean the same people only in this org and its sandboxes; preview data is often copied from a real record. Recommend `--clear-managers` when the components will go to another org and `--clear-prefill` before the files go into any shared repository.

Changing a component's shape (record or JSON to metadata) is the person's decision ([_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)): the yes to this list is that decision. Rerun the dry run with the answers, read the changes back, and only on a yes:

```bash
python3 scripts/convert.py confirm _forms/<slug>/convert/conversion.json
```

`confirm` records a digest of exactly what was shown; the build refuses a conversion that changed afterwards.

## 3. Build

```bash
python3 scripts/convert.py build _forms/<slug>/convert/conversion.json --out <package directory>/main/default/customMetadata \
  [--clear-managers] [--clear-prefill]
```

It writes the metadata record files into the project (`FlowToolKit__Form.<Name>.md-meta.xml`, `FlowToolKit__Form_Section.<Name>.md-meta.xml` and so on), and beside `conversion.json`: `components/<Name>.json` (each converted design, the source to edit from now on), `package.xml` (exactly the new records, for the deploy), `labels.xml` (the org's own Form Labels and translations the components use), `repoint.apex` and `rollback.apex`. A file the project already holds with other content stops the build and nothing is written (exit 4); `--overwrite` only after the person agrees.

## 4. Deploy, verify, repoint

Each step with the person's yes:

1. **Validate, then deploy** only the new records:
   ```bash
   sf project deploy start --manifest _forms/<slug>/convert/package.xml --target-org <org-alias> --dry-run
   sf project deploy start --manifest _forms/<slug>/convert/package.xml --target-org <org-alias>
   ```
   Fields the components use must already be in the org; a deploy that names a missing field fails here, before anything changes.
2. **Land the Form Labels** in the project, so the components deploy anywhere: `sf project retrieve start --manifest _forms/<slug>/convert/labels.xml --target-org <org-alias>` (only when `labels.xml` was written; packaged labels ship with Flow Tool Kit).
3. **Verify** every component is in the org with every section, field and rule: `python3 scripts/convert.py verify _forms/<slug>/convert/conversion.json --target-org <org-alias>`. Exit 5 names what is missing; do not repoint until it passes.
4. **Reset Form Cache** in the Form Builder's footer: forms are served from the platform cache.
5. **Repoint the template**: `sf apex run --file _forms/<slug>/convert/repoint.apex --target-org <org-alias>`. It is all or nothing: it stops and changes nothing when a new component is missing or a section changed since the dry run (then take a new snapshot and dry run). A converted record section now names `<Name>` instead of `<Name>_v0`; a converted JSON section switches to component mode and keeps its old JSON in its configuration, as the section editor does.
6. **Walk it.** Open the template's **Preview Form** and walk every page: each converted section, every field, every rule both ways. For a public form, open it as a guest too.

`rollback.apex` puts every repointed section back exactly as it was (the metadata components stay in the org, unused) if the walk fails.

## 5. Later, a separate step: delete the originals

Never in the same run. Only after the person has checked the converted template and asks:

```bash
python3 scripts/convert.py cleanup _forms/<slug>/convert/conversion.json --target-org <org-alias>
```

It reads the org again and lists each converted record component that **nothing uses any more** (no template section, header or footer, and no other record component's design names it), and those still in use, which it never offers. It writes `cleanup.apex`; ask *"Delete the original Household Members record component? The template now uses the metadata one, and nothing else uses the record."* and only on a yes run `sf apex run --file _forms/<slug>/convert/cleanup.apex --target-org <org-alias>`. The Apex checks again and deletes nothing if any template still uses one; deleting a component deletes its sections, fields and rules with it. A JSON section leaves no record behind. In chat, the person can delete the record from the Form Components tab instead.

## Exit codes

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Done | The next step |
| 1 | An error, with the CLI's message | Read it out; most often the CLI is not signed in |
| 2 | The dry run (or the checker) found a problem | Fix each, run the dry run again |
| 3 | Not confirmed, or changed after it was | Show the dry run, confirm on a yes |
| 4 | Project files would change | Ask; `--overwrite` on a yes |
| 5 | Verify found a component missing or incomplete | Read the deploy's errors; deploy again |

## Report to the person

A few lines, outcome first:

> Converted Household Members and the Plot preferences section of Garden Plot Application into metadata components (2 forms, 2 sections, 7 fields, 2 rules and 2 conditions: 15 files in force-app/main/default/customMetadata, plus 1 Form Label with its Spanish translation), deployed them to the Riverside sandbox and repointed two sections. Contact Details and the packaged header were left as they are. The original Household Members record is still in the org. Tell me when you want it deleted.

## Traps

| Trap | What to do |
|---|---|
| The template still shows the old form | Reset Form Cache in Form Builder |
| A second dry run after the deploy says the names are taken | It sees the components you just deployed. Carry on from the confirmed `conversion.json` (verify, repoint) instead of planning again |
| A record component and a metadata component share a name until cleanup | Expected. A name ending `_v0` draws the record, the plain name draws the metadata. org-catalog lists both until the record is deleted |
| A converted record component is used by another template too | The dry run leaves it alone unless included by name; if included, only this template is repointed and the other keeps the record. Cleanup will not offer it while anything uses it |
| A field in a design is gone from the org | The deploy fails naming it. Create the field, or remove the question in Form Builder, then take a new snapshot |
| A metadata component that places a record component | Not possible in metadata; the dry run lists it as a problem |
| A JSON section copied into several templates | Each conversion is this template's only. Convert the other templates separately, or point them at the new component by hand |
| A public form after the conversion | A metadata component needs no guest sharing rule; the fields still need guest field access as before |

## Done when

- The person saw the dry run (every component converted, every one left alone, every place repointed) and said yes; `confirm` recorded it.
- Only the record components and JSON sections built for this template were converted; every referenced component is unchanged.
- The metadata files are in the project, deployed, verified, and the Form Labels they use are in the project.
- The template is repointed, the cache reset, and Preview Form walked.
- The original records are still in the org, and the person knows deleting them is a separate step they can ask for.
