---
name: org-catalog
description: Reads a Salesforce org's Flow Tool Kit (FTK) Form Components (metadata and record, including JSON ones), Form Templates with their pages and sections, the layers between them (components built from other components, sections repeated across templates), every place each component is used (templates, flows, Lightning pages, site pages), mapped forms on other objects and any brand kit, into a catalog file in the project that form-design and build-template read. Use first, before designing or building any FTK form (ftk-start runs it every time), and for "what components do we already have?", "can this form reuse our address block?", "which sections repeat across our templates?", "refresh the catalog", or whether a new field name is free. Never reuses silently: offers each matching section as reuse, extend or new, and recommends a shape (metadata, record or JSON) with its reason. Works in Claude Code with the Salesforce CLI and in claude.ai chat with a Salesforce connector.
---

# Org Catalog

A reuse map of what the org already has, taken before anything is designed. Reuse is about Form Components: the blocks of questions placed in the sections of many Form Templates. A Form Template is one whole form. It reads every Form Component (with its shape: metadata or record), every Form Template with its pages and sections (each section's shape: the component it places, or JSON fixed to that section), and how they connect, and every flow, Lightning page, Experience Cloud page and wrapper component that names a component, and writes `catalog.json` (for the other skills) and `catalog.md` (for people) into the project. It also finds the org's platforms, a saved brand kit, and Form Submission field names that would clash with packaged ones.

It never changes the org, and it never decides reuse. When a new design has a section that looks like something the org already has, it names the existing component, its shape, its fields and where it is used, and the person chooses **reuse**, **extend** or **new**. For anything extended or new it also recommends a **shape**, with the reason, and asks: a metadata component, a record component or JSON ([_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)).

It reads configuration only: components, templates, field definitions, style settings and file names. It never reads a Form Submission or any respondent's answers.

## Where it runs

| Surface | How it reads the org |
|---|---|
| Claude Code (local or on the web) with the Salesforce CLI | `catalog.py collect` runs every query itself, then retrieves (read only, nothing is deployed) the org's flows, Lightning pages, site pages and its own Lightning web components to find every place a form is named |
| claude.ai chat with a Salesforce connector that runs SOQL | The connector runs each query; `catalog.py` (in code execution) says which queries are next and builds the catalog from the rows. Flows, Lightning pages and site pages are metadata, not records, so SOQL cannot read what they contain: "used in" then covers Form Templates and components only, and the catalog says so (`placements.complete` is false) |
| Chat without a connector, or no org connected | One line saying so, and an empty catalog marked `no org` |

Python 3 standard library only; nothing to install. Run the script by its path in this skill folder: `python3 scripts/catalog.py ...`.

## The run

### 1. Find the org

In Claude Code use the org the project points at: the alias in `flow-tool-kit.json` for this org if ftk-start saved one, otherwise the Salesforce CLI's default org. In chat, look for a Salesforce connector with a query tool. If there is none, go to step 5.

### 2. Read it

**Claude Code:**

```bash
python3 scripts/catalog.py collect --target-org <org-alias> --config flow-tool-kit.json
```

It runs the queries in passes (each pass depends on the one before: which objects the forms use, which components have no JSON), retries a tooling query through the data API, and drops any column an older Flow Tool Kit version does not have yet, noting it in the catalog.

**Chat with a connector:** loop until nothing is left.

```bash
python3 scripts/catalog.py next-queries raw.json        # JSON list of {key, soql, tooling, optional, why}; [] when done
```

For each query, run its `soql` through the connector, save what came back to a file, and add it:

```bash
python3 scripts/catalog.py add raw.json --key <key> --records-file rows.json
python3 scripts/catalog.py add raw.json --key <key> --error "<the error message>"
```

- `tooling: true`: use the connector's Tooling API option if it has one; otherwise run the same SOQL as a plain query.
- An error that says **No such column 'X'**: the org runs an older Flow Tool Kit version. Remove that column from the SELECT, run it again and add the rows. Do the same for each further missing column.
- Any other error: add it with `--error`. `optional` queries may fail; the catalog says what is missing.
- Rows can be pasted as the connector returns them (a list, `{"records": [...]}` or `{"result": {"records": [...]}}`). Long JSON fields must arrive whole: if the connector truncates long text, page the query with `LIMIT` and `OFFSET`, or by Id, and add the pages together as one list.
- Optional: if a brand file was found and the connector can download a file, save its text and run `catalog.py add-brand-file raw.json --id <ContentVersion Id> --file brand-kit.json`.
- Optional: if the connector can retrieve metadata (Flow, FlexiPage, ExperienceBundle or DigitalExperienceBundle, LightningComponentBundle), or the person shares the project's source pulled from this org, put the files in one folder and run `catalog.py add-placements raw.json --dir <folder>`. Only the kinds whose files are in the folder count as read; a folder pulled earlier is only as current as that pull.

Then build:

```bash
python3 scripts/catalog.py build raw.json --config flow-tool-kit.json
```

What each query and retrieve reads and why: [references/reading-the-org.md](references/reading-the-org.md).

### 3. Save where the other skills find it

Both paths write `ftk-catalog/<org Id>/catalog.json` and `catalog.md` (and `raw.json` in Claude Code). The catalog records the time it was taken (`taken_at`, UTC) so form-design can refuse a stale one. Put the catalog's path in `flow-tool-kit.json` under this org (`orgs.<org Id>.catalog`), and its `platforms` there too, so ftk-start does not ask what the org already says. In chat, write the files to the outputs folder and suggest adding them to the claude.ai Project's files, so the next chat reads them.

The format, key by key: [references/catalog-format.md](references/catalog-format.md).

### 4. Tell the person, in a few lines

Lead with the counts, then what is reusable, then anything that needs attention. For example:

> I cataloged Riverside Community Garden: 6 Form Components (3 metadata, 3 record) and 3 Form Templates. Household Contact, a record component, is used on 2 templates, the Volunteer Intake flow, the Contact record page and the Volunteer site page, and maps to the Form Submission's name, email and phone fields. Emergency Contact is JSON built in place on 2 templates. One template section points to a component that no longer exists, and your field Submitted_By__c sits beside the packaged one of the same name. Saved brand file found: Riverside Community Garden.

Say plainly when the catalog is `partial` (an essential read was refused) and what is missing, and when flows, Lightning pages, site pages or wrapper components were not read (`placements.note`): "used in" is then not every place a component is used. Problems and warnings are listed at the end of `catalog.md`; the ones worth saying out loud are a section pointing at a missing component, a component on another object placed in a template without a Form Template Mapping (nothing it collects reaches the submission), and twin field names.

### 5. No org

With no org connected (chat without a Salesforce connector, or the CLI cannot reach an org), say so in one line and write an empty catalog:

```bash
python3 scripts/catalog.py empty
```

> No Salesforce org is connected, so I have nothing to reuse yet: every section will be new, and Salesforce targets in the design are marked verify until an org is connected.

It writes `ftk-catalog/no-org/catalog.json` with status `no org`. Once an org is connected, `check` reports it stale and the catalog is taken again.

If the org is reachable but Flow Tool Kit is not installed, the catalog's status is `no package` and says so; there is nothing to reuse.

## Where each component is used

`components[].used_in` is every place that names the component, and the list build-form-component reads before it asks to update a shared component in place:

- **Form Templates**: a page section, a section's table, bulk edit or edit form, a header or footer, or inside a section's own JSON.
- **Flows**: Form (Component), Form (Repeater), Form (Table) and Form (Lookup) screen components, by their form name inputs, including a constant or variable with a fixed value, and components placed inside a form's own JSON in the flow.
- **Lightning pages**: Form (Component) on a record, app or Home page.
- **Experience Cloud pages**: Form (Dynamic Component) or Form (Component), on Aura and LWR sites.
- **Wrapper components**: the org's own Lightning web components that render the package's form and name it (as new-record-page-form writes them). One that holds a copy of the form's JSON is marked `copy`: a change to the component does not reach it until the copy is made again.

Components inside components are in `used_by_components` (sections, table forms, bulk table forms, lookup fields). A form chosen at run time (a flow input from a formula or an input variable) cannot be tied to one component; it is listed in `run_time_forms`. When `placements.complete` is false, say which kinds of place were not read before any update in place. Components can also be found by the component browser's folder and tags (`folder`, `tags`, and the `filing` index).

## Matching a design: reuse, extend or new

form-design runs this for every section of its plan, before drawing components into the design.

```bash
python3 scripts/catalog.py check ftk-catalog/<org Id>/catalog.json --org-id <org Id>   # exit 0 fresh, 2 stale, 3 another org
python3 scripts/catalog.py match ftk-catalog/<org Id>/catalog.json plan.json --out match.json
```

`match` refuses a catalog older than 24 hours (exit 2): take the catalog again. A section matches an existing component when they share at least 80% of the larger set of fields, counted twice: with labels and with labels ignored. It compares each component on its own fields together with the components placed inside it, and, for a component with a Form Template Mapping, on the Form Submission fields its map writes, so a free-edition design on Form Submission fields still finds a Contact form mapped to them. The measure and its edge cases: [references/matching.md](references/matching.md).

For each section with a candidate, `match` writes a question that names the component, its shape, its fields and where it is used, then the shape question; every section, matched or not, gets a shape recommendation (`shape` in `match.json`). Ask them all at once, in one message, each with a recommendation, and record each answer in the design plan:

> 1. 'Your details' matches your record component Household Contact on Contact through its Form Template Mapping (100% by field, 75% with labels; used in 2 templates). It already has every field this section needs. Reuse it, or build new? Reuse keeps it a record component. If you build new, I recommend JSON on this section (only this section asks these questions; JSON is the simplest and cannot conflict with a shared component). Or a record component if you already know another place will use these questions, or metadata if you keep forms in source control and want it deployed. JSON, record or metadata?
> 2. 'Where you live' matches your metadata component Mailing Address on Contact (80% by field; used in no template yet, inside 2 other components). It lacks Neighborhood. Extend it (a new version of Mailing Address with that field; the original and every place it is used stay as they are), reuse it as is, or build new? If you extend, I recommend a metadata component: a new version stays in Mailing Address's shape, so one deployed update still reaches every form that uses it. Or JSON on this section if these questions must stay fixed to it, or a record component to build it straight in the org with no deploy.
> 3. 'Main support contact' is new: no component matches. I recommend a record component (this design asks the same questions in 'Additional contacts' too, a Repeater for more contacts, so one record component built now and referenced by each keeps them in step). Or JSON on this section if these questions must stay fixed to it, or metadata later through convert-to-metadata once the form is final. Record, JSON or metadata?
> 4. 'Availability' is new: no component matches. I recommend JSON on this section (only this section asks these questions; if other forms ask them later they can be merged into one shared component then). Or a record component if you already know another place will use these questions, or metadata if you keep forms in source control. JSON, record or metadata?

- **Never decide silently.** A match is a question, never a decision. Every `decision` in `match.json` starts empty, and a question with no answer stays unanswered: the next skill (form-design, build-form-component) stops on that section until the person chooses.
- **Recommend the shape, with the reason, and ask** ([_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)). **JSON on the section** is the default for a new section: the easiest, and it cannot conflict with a shared component. **Record** only when reuse is known at design time: the design asks the same questions in more than one place (a section and a Repeater, several sections, several forms in the plan) or the org already has them built in place on other templates; one record component is built right away and every place references it. **Metadata** is not recommended for new work: it comes later through convert-to-metadata once the work is final, or when the person asks. A reused component keeps its shape and an extended one keeps the original's. Reuse found later is consolidated then, never guessed up front. A shape with no answer stays unanswered.
- **Reuse** puts the existing component in the section as it is, in its own shape. **Extend** makes a new version of the named component with the added fields, and this section uses the new version; the original is never changed, so every template and component that uses it (the question lists them) keeps working as before. **New** builds the section on its own.
- A section with no component match but the same design already built in place on other templates is listed too: build it new here, or make one shared component.
- Never change a design to force a match. Layout and styling are not scored.

## Name check before any new field

Before any skill creates a field on Form Submission (or any object the catalog read), check the name:

```bash
python3 scripts/catalog.py name-check ftk-catalog/<org Id>/catalog.json --object Form_Submission__c --field Shirt_Size__c
```

It answers `free`, `exists` (reuse it), or `twin`: a name that matches a packaged Form Submission field without its prefix, such as your Submitted_By__c beside FlowToolKit__Submitted_By__c. The Conversion Setup action leaves such a field out of the record it hands a flow, because inside the package the bare name means the packaged field; never create one, and read an existing one with your own Get Records.

Field existence comes from FieldDefinition (Tooling API) or a metadata list of CustomField, never from a describe: a describe silently leaves out any field the running user cannot read, so a field you cannot see looks like a field that does not exist.

## The brand kit it detects

A saved brand kit lives in two places, and the catalog reads both:

- **The org's Form Style defaults** (the Form Style Defaults setting, org-level row): a brand color (`Color_Primary__c`) or a default logo (`Default_Logo__c`) means styles were saved. The setting is protected; if the read is refused, the Logo formula on a template without its own Logo Override still shows the default logo, and the Global Styles tab shows the rest.
- **`brand-kit.json` in the Asset Library**: the brand file with tone of voice, asset names by role and the confirmed colors and fonts. Several brands mean several files.

`brand_kit.found` is `saved` (styles and a file), `partial` (one of them; styles alone carry no tone), `logo only`, `none` or `unknown` (nothing found and the styles could not be read). ftk-start uses `brand_kit.summary` to ask "use your saved brand kit, update it, or ignore it?"

## Done when

- `catalog.json` and `catalog.md` are saved in the project with the time they were taken, or an empty catalog marked `no org` or `no package`.
- The person has heard the counts, the reusable components, and the problems worth acting on, in a few lines.
- `flow-tool-kit.json` points to the catalog and holds the org's platforms.
- When a design was matched: every matching section has its question asked, every extended or new section has its shape recommended with the reason and asked, and no decision was made for the person.

## Common mistakes

| Mistake | Instead |
|---|---|
| Designing from an old catalog file | Run org-catalog first, every time; `match` refuses a catalog older than 24 hours |
| Reusing a component because its name fits | Compare fields; ask reuse, extend or new, naming the component and where it is used |
| Picking metadata, record or JSON for the person | Recommend a shape with its reason, name the alternatives, and ask |
| Saying a Form Template is reused | Templates are whole forms; reuse is of Form Components placed in many templates |
| Extending a component by editing the original | Extend makes a new version with the added fields; the original, and every place it is used, never changes |
| Treating a describe's field list as the truth | FieldDefinition through the Tooling API, or a metadata list |
| Creating Submitted_By__c beside the packaged FlowToolKit__Submitted_By__c | `name-check` first; never name a field after a packaged one |
| Reporting "no components" when no org is connected | Say no org is connected, in one line, and mark the catalog `no org` |
| Counting a "No such column" error as a failure | An older Flow Tool Kit version; drop the column and rerun |
| Reading submissions to see how a form is used | Configuration only; never respondent data |
| Calling "used in" complete when flows, pages or sites were not read | Check `placements.complete`; name the kinds not read, and the run-time forms, in the update question |
