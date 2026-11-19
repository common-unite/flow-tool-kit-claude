---
name: pull-form
description: Use when a Flow Tool Kit metadata form or component (a Form__mdt form built in Form Builder) has to be put into a Salesforce project, so it can be versioned, reviewed or deployed to another org. Triggers include "pull the scholarship form into the repo", "get our registration form into source control", "copy this form from the sandbox to production", "version our forms", and a metadata form changed in Form Builder that now has to reach another org. Retrieves the form with its sections, fields, conditional logic rules, conditions and Form Labels with their translations, names everything it depends on (other forms, image files, flows, Lightning web components) and pulls the org's own on request, fixes org-specific field Ids, and never replaces project files without asking. Claude Code only.
---

# Pull Form

A Flow Tool Kit form built as metadata is not one record but a tree: the Form record, its sections, its fields, the conditional logic rules and their conditions, and the Form Labels its text uses, each translation a record of its own. Pulling it by hand misses pieces, and the piece that is missed only shows when the form is deployed somewhere else. This skill retrieves the whole tree with the Salesforce CLI into the person's own Salesforce project, checks it, and copies it into the project's package directory only when nothing there would be overwritten without a yes.

**Called by** build-form-component, when a metadata component changed in Form Builder should live in the project, and directly by the person. **Reads** org-catalog's `catalog.json` to find the form by its label, and `flow-tool-kit.json` for the org's alias. **Hands off** the landed files to build-form-component's `component.py check`.

## Where it runs

| Runtime | What works |
|---|---|
| Claude Code, local or on the web, with the Salesforce CLI signed in to the org | Everything below |
| claude.ai chat | Nothing. Say in one line: "Pulling a form into a project needs Claude Code, because it runs the Salesforce CLI and writes files into your Salesforce project; open the project in Claude Code and ask there." |

On the web there is no browser for `sf org login web`; the person signs the CLI in with `sf org login sfdx-url` or `sf org login jwt`. The script is Python 3 standard library only; run it by its path in this skill folder: `python3 scripts/pull_form.py ...`.

## Before pulling

1. **The project.** Run from inside the Salesforce project the form should land in (any folder below `sfdx-project.json`). New files go to the default package directory in `sfdx-project.json`, into the folder the project already keeps custom metadata in, or `<package directory>/main/default/customMetadata` when it has none. `--package-dir <path>` picks another listed package directory. A file the project already holds is updated where it is. No `sfdx-project.json`: offer to create the project with `sf project generate --name <project-name>` before anything else.
2. **The org.** Use the alias saved for this org in `flow-tool-kit.json` ([_shared/standards/project-config.md](_shared/standards/project-config.md)), otherwise the CLI's default org (`sf config get target-org`). Say which org you are pulling from in the same message as the result; do not stop to ask unless no org is set.
3. **The form.** People name forms by their label ("the scholarship form"). Find the API name one of two ways:
   - org-catalog's catalog is fresh: pass it with `--catalog ftk-catalog/<org Id>/catalog.json`, and the label is enough;
   - otherwise list the org's own metadata forms: `python3 scripts/pull_form.py list --target-org <org-alias> --search scholarship`.

   Two things cannot be pulled. A **record component** (a Form Component record, the catalog's `kind: record`) moves as JSON: the Export action on its record, then Import Form Component in the other org (build-form-component's record path). A **packaged form** (`FlowToolKit__...`) ships with Flow Tool Kit, so every org with the package already has it; to change one, build your own component (build-form-component).

## Pull

```bash
python3 scripts/pull_form.py pull "<API name or label>" --target-org <org-alias> [--catalog <catalog.json>]
```

It finds every record that belongs to the form (rules a section points at and conditions only their rule names included), retrieves them into a staging folder inside the project (`.pull-form-<id>/`, removed afterwards; the CLI writes only inside a project), fixes and checks the files, and then copies them into the package directory. `--dry-run` does all of it except the copy. What each step reads and why: [references/what-gets-pulled.md](references/what-gets-pulled.md).

Read the exit code, then the report:

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Landed (or, with `--dry-run`, ready to land) | Report and check (below) |
| 2 | The name matched no form, or several | Show the candidates it printed with their labels and ask which one |
| 3 | A packaged form or a record component | Explain in one line, as above |
| 4 | Files in the project differ from the org; nothing was copied | Ask before replacing them (below) |
| 5 | A field reference holds an org Id the record's own configuration cannot replace; nothing was copied | Explain the fix (below) |
| 1 | Anything else, with the CLI's own message | Read it out; most often the CLI is not signed in |

### Questions to ask, all in one message

Ask only the ones the report raises, each with your recommendation, after the first pull run:

- **Project files that differ** (exit 4). The report prints the lines that differ under each file (project first, org second); describe them in plain words. *"Two files in your project differ from the org: the Your Plot section's title was edited in the project, and the Start Date field is now required in the org. Replace them with the org's version?"* Yes: run again with `--overwrite`. A pull never deletes a project file; files of records no longer in the org are listed under "In the project but no longer in the org".
- **The org's own dependencies.** The report's "Outside this form" lists component forms placed in its sections, table forms, forms a Record Card button opens, its Form Object and Theme, the image files (Asset Files) its image sections, banners, Record Cards and visual picker options show, the flows its flow sections and flow buttons run, and the Lightning web components its LWC sections load. Packaged ones ship with Flow Tool Kit and need nothing. The org's own ones must exist in any org the form goes to. *"This form places Household Contact, shows your festival logo and runs the Volunteer Shifts flow. Pull them too, so the form deploys elsewhere?"* Recommend yes when the form is going to another org. Yes: run again with `--with-dependencies` (it pulls forms with their whole trees, and the image files, flows and components as metadata). A flow's or component's own dependencies (subflows, Apex, fields) are not followed; name them to the person. A form a button opens that is "not a metadata form in this org" is a record component: it moves as JSON.
- **Form Managers.** The user Ids in Form Managers name the same people only in this org and sandboxes copied from it. Recommend clearing them (`--clear-managers`) when the form goes to an unrelated org, keeping them otherwise.
- **Preview data.** A form's prefill holds the test values Form Builder's preview uses, often copied from a real record. Read it; recommend clearing it (`--clear-prefill`) before the files go into any shared repository.

Rerunning with the answers retrieves again; that is expected.

### Org Ids in field references (exit 5)

Salesforce sometimes writes a field reference as a raw field Id, or half resolved as `Object.00N...`. Such a file deploys in the org it came from and fails in every other one. The script replaces the Id from the same record's own configuration, which keeps the field's API name, and reports each fix. When the configuration has no name to use, it stops and copies nothing: open that field in Form Builder, choose the field again, save, and pull again. `--allow-org-ids` lands the files anyway, only when the person wants the files in the project for this org alone.

A value that only looks like a record Id outside a field reference is reported as a check, not fixed. A Record Type Id a condition compares against is named (which record type of which object) with the query that finds the same record type's Id in the target org; put that Id in the condition's value, in Form Builder after deploying or in the file before. Sandboxes of the same org keep the same Ids.

## Check what landed

Run build-form-component's checker (its skill folder sits beside this one) on the folder the files went to. It checks every form in that folder; read the lines for this form's records:

```bash
python3 ../build-form-component/scripts/component.py check <destination folder> [--catalog <catalog.json>]
```

With the catalog of the org the form is going to (run org-catalog against that org first), it also reports every field the form uses that the other org lacks, which is the usual reason a moved form renders with questions missing.

## When the form goes to another org

The pull stops when the files are in the project; deploying is the person's call. When they ask:

1. The org's own fields the form uses, its Form Object and Theme, every form it places or opens, and the image files, flows and components it names must be in the target org first, or in the same deploy.
2. Deploy the files: `sf project deploy start --source-dir <destination folder> --target-org <target-alias>` (or name the files).
3. In the target org, open any form in Form Builder and click **Reset Form Cache**: forms are served from the platform cache, and a stale form looks exactly like a failed deploy.
4. On an LWR site, an LWC section's component loads only when a component on the site imports it by name. The report names the org's own component that does (pulled with `--with-dependencies`), or says there is none. It goes in the site's Theme Footer beside FlowToolKit LWR Support, and the site is published.

Namespacing, permission sets and field access for metadata forms: build-form-component's `references/metadata-path.md`.

## Report to the person

A few lines, outcome first:

> Pulled Garden Plot Application from riverside-sandbox (Riverside Community Garden): the form, 2 sections, 4 fields, 2 rules with their conditions, and 1 Form Label with its Spanish translation, 13 files in force-app/main/default/customMetadata. I replaced one half-resolved field Id with its API name. It places Household Contact, your own component, which is not pulled yet; one label it uses, Plot_Rules_Link, is not a Form Label in this org.

## Traps

| Trap | What to do |
|---|---|
| Two forms share a label | The script lists both; ask, and pull by API name |
| A section shows a component from another form | Listed under "Outside this form"; `--with-dependencies` pulls it |
| A rule or condition is tied to the form only through a section, field or rule | Found by the pull; never hand-pick files |
| Text names a label that is not a Form Label | Listed as such. Flow Tool Kit fills `{{$Label.Name}}` only from Form Labels, never from a Salesforce custom label, so that text is empty on the form in every org; create the Form Label in Form Builder and pull again |
| An LWC section shows on a record page but is blank on an LWR site | The site bundles the component only when a component on the site imports it by name; see the report's LWR line |
| An image is missing after the deploy | Its Asset File was not in the target org; pull with `--with-dependencies`, or create the Asset File there with the same name |
| Records marked deleted in Form Builder | Pulled as they are and counted in the report; they stay hidden wherever they are deployed |
| A record deleted in the org since the last pull | Its file stays in the project and is listed; removing it from another org needs a destructive deploy |
| An older Flow Tool Kit version lacks a column | The script leaves the column out and names it in the report |
| A run stopped half way | Delete any leftover `.pull-form-<id>/` folder in the project, and consider adding `.pull-form-*/` to `.gitignore` |
| Deployed elsewhere and the old form still shows | Reset Form Cache in the target org's Form Builder |

## Done when

- The form and every record that belongs to it are in the project's package directory, and no project file was replaced without the person's yes.
- Each of the org's own dependencies was either pulled or named to the person.
- No org Id is left in a field reference, unless the person chose to keep the files for this org only.
- Form Managers and preview data were reported, and cleared where the person agreed.
- `component.py check` ran on the landed files, and the person heard the report: the form, the org, the counts, where the files are and what lies outside the form.
