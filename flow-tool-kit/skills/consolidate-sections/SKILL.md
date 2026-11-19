---
name: consolidate-sections
description: Optional, and only when asked (or offered once after a build). Use when the same questions have been built as separate sections on several Flow Tool Kit Form Templates and should become one shared component. Triggers include "these forms all ask the same emergency contact questions", "merge the repeated sections", "make this section shared", "which sections repeat across our forms", "consolidate our templates". Runs on the whole org, any time: groups the templates' JSON sections and one-off record components that ask the same questions (org-catalog's repeated-sections finding), shows what each group shares and where its members differ, recommends one shared record component, and on a yes creates it and repoints each section, after a dry run the person approves. Every difference is settled by the person, never changed silently. Never a required step.
---

# Consolidate Sections

**This skill is optional.** Not every consultant or organization will use it. It runs only when someone asks, or when build-template offers it once after a build; nothing else depends on it, and a form works the same whether its sections are ever consolidated or not.

Every new section starts as **JSON on the section**: its own questions, the simplest shape to build and change. A shared **record component** is used from the start only when reuse is known at design time, and **metadata** comes later through convert-to-metadata ([_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)). So reuse found later shows up as the same questions built several times. This skill finds those repeats across the org, and for the ones the person wants merged it builds one shared component and points each section at it. Each section keeps its own title, header and rules; only where its questions come from changes.

**Reads** org-catalog's `catalog.json` (its `repeated_sections` finding, the same measure the reuse questions use; this skill never measures sections a second way) and the member sections from the org. **Writes** the shared component through build-form-component's writer (`scripts/component.py`, beside this skill in the plugin), so it is written exactly like any other component. **Hands on** to convert-to-metadata when a shared record component is final and should become metadata.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat with a Salesforce connector | Everything in records mode: run the queries through the connector, the scripts in the code sandbox, and the Apex files through the connector when it runs anonymous Apex. Without Apex, the person imports `components/<Name>.json` in **Form Components, Import Form Component** and repoints each section in Form Builder (the dry run lists each one) |
| Claude Code, local or on the web | Everything above, plus a shared component built as **metadata**: files written into the project and deployed with the Salesforce CLI |
| claude.ai chat, no connector | Nothing to read the templates with. Say so in one line and stop |

On the web the CLI signs in with `sf org login sfdx-url` or `sf org login jwt` ([_shared/standards/runtime.md](_shared/standards/runtime.md)). Every script is Python 3 standard library only; run it by its path in this skill folder. In chat the skill folder alone is copied into the sandbox, so org-catalog's and build-form-component's scripts are not beside it: grouping then uses the catalog's repeated JSON sections only (one-off record components are left out, and the dry run says so), and the build needs build-form-component's writer (use Claude Code, or have the person import the JSON the dry run describes).

## Before you start

1. **The org and the catalog.** The org's alias comes from `flow-tool-kit.json` ([_shared/standards/project-config.md](_shared/standards/project-config.md)), else the CLI's default org. Run **org-catalog** first if its `catalog.json` is older than a day, or was taken before the latest templates were built: the catalog is what knows every template. Keep this skill's files in `_forms/consolidate-<yyyy-mm-dd>/` ([_shared/standards/documentation.md](_shared/standards/documentation.md), section 6, Naming).
2. **Plans.** If any of these templates are rebuilt from a `plan.json` by build-template, a rebuild from the old plan would put each section's own JSON back. Pass those plans to `build --plan` (step 4), which records the shared component in them, or use the plan route below instead.

## 1. Read the member sections

```bash
python3 scripts/consolidate.py snapshot --catalog ftk-catalog/<org Id>/catalog.json --target-org <org-alias> \
  --out _forms/consolidate-<date>/snapshot.json
```

It reads, for every group the catalog finds, each member section's stored JSON and each one-off record component's design, and whether the org has the package's import (Flow Tool Kit 5.3 or later). In chat, `python3 scripts/consolidate.py queries --catalog <catalog.json>` prints the queries; run each through the connector, save the rows under each `key` in one JSON file, and pass it as `snapshot --rows <file>` ([references/consolidation.md](references/consolidation.md)).

## 2. The dry run

```bash
python3 scripts/consolidate.py plan --catalog ftk-catalog/<org Id>/catalog.json --snapshot _forms/consolidate-<date>/snapshot.json \
  --out _forms/consolidate-<date>/consolidation.json
```

Nothing changes in the org. It lists every **group**: sections on **two or more templates** that ask the same questions (org-catalog's 80% match by field or with labels). Per group:

- **What they share**: the questions the shared component would ask, built from the member closest to the group's typical design.
- **Each member** and where it differs from that: a question it asks that the shared component would not (**loses**), a question it would gain, a label, required, choices or options, a rule that shows or hides a question, or its Form Template Mapping.
- **The recommendation**: one shared **record component**, named for its purpose (`In_Case_Of_Emergency`, offer a better name), with the reason: it is built in the org with no deploy, and one change reaches every section that shows it. Metadata only when the person asks (Claude Code), or later through convert-to-metadata.

### Ask, all in one message

Read the groups to the person in plain words, one numbered item per group, each with your recommendation, and ask only what the run raises:

> 1. **In case of emergency** is built three times: Volunteer Application, Youth Camp Registration and Garden Plot Application. The first two ask the same four questions; Garden Plot also asks **Alternate phone**. I recommend one shared record component, In_Case_Of_Emergency, used by all three, with Alternate phone added (Volunteer Application and Youth Camp would then ask it too). Or merge the first two and keep Garden Plot's section as it is. Merge, and add Alternate phone or keep Garden Plot separate?

Then record the answers and run the dry run again:

| Answer | Flag |
|---|---|
| Merge this group (no answer means it is not merged) | `--merge g1` (or `--merge all`) |
| Add a question one member has to the shared component (every member that joins then asks it; the dry run names them) | `--add g1:Alternate_Phone__c` |
| A member whose label, required, choices, rule or mapping differs takes the shared version | `--join <section Id>` |
| Keep a member as it is | `--separate <section Id>` |
| Build from another member's design | `--base g1=<section Id>` |
| Another name, a description, or metadata | `--name g1=<Name>`, `--describe g1="<text>"`, `--shape g1=metadata` |

**Differences are never settled silently.** A member that differs is kept separate until the person answers for it: it would lose a question unless that question is added, and any other difference needs its own `--join`. A group whose answers leave fewer than two templates is not merged, and the dry run says so. Write the description in the documentation standard's shape ([_shared/standards/documentation.md](_shared/standards/documentation.md)): what the block collects and where the answers go; the default only lists the questions.

Read the final list back and, only on a yes:

```bash
python3 scripts/consolidate.py confirm _forms/consolidate-<date>/consolidation.json
```

`confirm` records a fingerprint of exactly what was shown (every shared design, member and repoint). The build refuses a consolidation that changed afterwards.

## 3. Build

```bash
python3 scripts/consolidate.py build _forms/consolidate-<date>/consolidation.json \
  [--plan <template's plan.json> ...] [--out <project's customMetadata folder>]
```

It writes, beside `consolidation.json`: `components/<Name>.json` (each shared component's JSON: the base member's design under the shared name, every section, field, rule and condition renamed after it, plus any added questions, checked by build-form-component's checker), `create.apex` (record components, through the package's `FormComponentImport.createRecordComponent`; it stops if a component of that name already exists), `repoint.apex` and `rollback.apex`. A metadata component's files go to `--out`, with `package.xml`; a project file that already exists with other content stops the build (exit 4) until the person agrees to `--overwrite`. Every plan given gets each merged section recorded as a reuse of the shared component.

## 4. Create, repoint, check

Each step on the person's yes:

1. **Create the shared component.** Record: `sf apex run --file _forms/consolidate-<date>/create.apex --target-org <org-alias>` (in chat, the connector, or **Import Form Component** with the JSON). Metadata: `sf project deploy start --manifest .../package.xml --target-org <org-alias> --dry-run`, then without `--dry-run`, then **Reset Form Cache** in Form Builder.
2. **Repoint**: `sf apex run --file _forms/consolidate-<date>/repoint.apex --target-org <org-alias>`. It is all or nothing: it stops and changes nothing when a shared component is missing or a section changed since the dry run. Each section switches to component mode and keeps its old JSON in its configuration until cleanup, as the section editor does; its title, header, page and rules are not touched.
3. **The round trip**:
   ```bash
   python3 scripts/consolidate.py roundtrip _forms/consolidate-<date>/consolidation.json --target-org <org-alias>
   ```
   It reads every member again and checks that each merged section shows its shared component, that the component asks exactly the approved questions (labels, required, choices and rules included), and that every section kept separate is unchanged. Exit 5 lists each difference; `rollback.apex` puts every section back exactly as it was (the shared component stays, unused).
4. **Walk it.** Open each changed template's **Preview Form** and walk the merged sections, every rule both ways. For a public form, a guest needs a sharing rule on Form Component (Read, where the record type is Record Component) to see a record component; flow-access-fix sets it up.

## 5. Later, a separate step: cleanup

Never in the same run. Only after the person has checked the templates and asks:

```bash
python3 scripts/consolidate.py cleanup _forms/consolidate-<date>/consolidation.json --target-org <org-alias>
```

It needs a passed round trip. It lists the old JSON each merged section still carries, and each one-off record component that **nothing uses any more**, and writes `cleanup.apex`. Ask *"Remove the old JSON kept on the three merged sections, and delete the Garden Day Details record component nothing uses now?"* and only on a yes run it. The Apex checks again and changes nothing if a section no longer shows its shared component or a template still uses a record component.

## The plan route: templates rebuilt from plan.json

When the templates are built and rebuilt by build-template from plans in this project, mark the plans instead, and let the rebuild do the work: `scripts/reviewpass.py` proposes switch (an existing component covers a section), promote (the same design on two or more templates) or keep, and changes only the plans the person marks. Members that differ are listed and stay local. Details: [references/review-pass.md](references/review-pass.md).

## Exit codes

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Done | The next step |
| 1 | An error, with the CLI's message | Read it out; most often the CLI is not signed in |
| 2 | The dry run found a problem, or nothing is marked to merge | Fix each, run the dry run again |
| 3 | Not confirmed, changed after it was, or cleanup before a passed round trip | Show the dry run and confirm on a yes; run the round trip |
| 4 | Project files would change | Ask; `--overwrite` on a yes |
| 5 | The round trip found a difference | Read each; fix, or run `rollback.apex` |

## Report to the person

A few lines, outcome first:

> Merged In case of emergency on Volunteer Application, Youth Camp Registration and Garden Plot Application into one shared record component, In_Case_Of_Emergency, with Alternate phone added, and repointed the three sections. The round trip found every template asking the approved questions. Event day details stays as two separate sections, as you chose. The old JSON is still on the three sections; tell me when you want it removed.

## Traps

| Trap | What to do |
|---|---|
| A rebuild puts the JSON back | The template is built from a plan: pass it to `build --plan`, or use the plan route |
| The dry run groups nothing you expected | The catalog is older than the templates: run org-catalog again. Sections must match at 80% (org-catalog's measure) on two or more templates |
| A one-off record component is not grouped | org-catalog's scripts were not found beside this skill (as `org-catalog` or `<plugin name>:org-catalog`): only JSON sections are grouped. Install the whole plugin, or pass `--org-catalog-scripts` |
| The build stops on the checker | Read each error: a field the org lacks, a section with no title, a description the documentation standard rejects. Fix the source section or the answer (`--describe`), then dry run again |
| A shared component's name exists | Pick another with `--name`; the import would change an existing component in place |
| The template still shows the old questions | Metadata: Reset Form Cache. An Experience Cloud LWR site serves its last publish: publish it again |
| Guests see a blank section after the merge | A record component needs the guest sharing rule; flow-access-fix sets it up |

## Done when

- The person saw every group, its differences and the recommendation, answered each difference, and said yes to the final list; `confirm` recorded it.
- Only the groups and members the person approved were changed; every section kept separate is unchanged.
- The shared components exist, every merged section shows its own, and the round trip passed.
- Each changed template was walked in Preview Form.
- The old JSON and the replaced one-off records are still there, and the person knows removing them is a separate step.
