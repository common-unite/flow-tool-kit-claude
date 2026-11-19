---
name: field-audit
description: Before an admin deletes, relabels or changes picklist values on a Form Submission landing field, shows which Flow Tool Kit (FTK) places it affects, the ones an admin cannot easily see: Form Templates, page sections, Form Components, page and section rules, URL parameter mappings, merge tokens in page, section and confirmation text, email templates, prefill values and templates, mappings (Form Template Mapping), and FTK flows (conversion, prefill, Flow Section screen flows, flows using FTK actions or components, and subflows). Writes a data dictionary with a verdict per custom field: Active with its places, or Unreferenced. Reads no submission data except named prefill template records. Use for "can I delete or rename this submission field?", before cleaning up fields, for a data dictionary, or at the end of a build (ftk-start runs it). Claude Code with the Salesforce CLI, or claude.ai chat with a Salesforce connector that runs SOQL.
---

# Field Audit

An FTK audit for an admin who asks: **if I delete, relabel or change picklist values on this Form Submission landing field, which Form Templates, page sections, Form Components (metadata, record, JSON), mappings and FTK flows (conversion, prefill and Flow Section) does it affect?**

Those are the places an admin cannot easily see. A Flow Tool Kit form keeps its answers on Form Submission fields, but templates, pages, sections and form components store field names as record data and JSON, a template names its conversion and prefill flows by API name in a picklist, and a Flow Section names the screen flow it shows. Salesforce's dependency tracking never sees any of that, so Setup's **Where is this used?** button cannot answer the question. This audit reads every one of those places and says, for each field, where Flow Tool Kit uses it.

**What it leaves out, on purpose.** Apex, reports, page layouts, validation rules, list views and flows that have nothing to do with Flow Tool Kit are general metadata, and Salesforce's own **Where is this used?** already lists them. The audit neither counts nor lists them. Before a change, run both: this audit for the Flow Tool Kit places, Where is this used? for the rest.

## The places it reads

| Place | What it reads there |
|---|---|
| Form Template | URL parameter mapping (`URL_Parameter_Mapping__c`), prefill values, nullable fields, header and footer forms, payment rules, merge tokens in its text (confirmation message, offline message, header, footer, subtitle, tags, review page label and subtitle, confirmation email body), Form Template Sources and their prefill mappings |
| Email templates | The stored email templates a template names (`Email_Template_Name_Confirmation__c`, `_Saved__c`, `_Start_Form__c`, `_Resume_Form__c`): their merge fields in Subject, HtmlValue, Body and Markup, in Lightning, Classic and Visualforce syntax |
| Prefill templates | The prefill template records a template or section names (`Prefill_Template__c`), read by Id: which Form Submission fields they set, and the merge tokens in their values |
| Form Template page and page section | The form each section shows, page rules and section rules (`Conditional_Logic__c`), a table's New, Edit and bulk edit forms, merge tokens in page text (label, title, details, description, footer, header) and section text (header, divider, section text) |
| Form Component | All three sources, with each form's own field and section rules: a metadata component (`Form__mdt` with its sections, fields and `Form_Conditional_Logic_Condition__mdt` rule conditions), a record component (`Form_Component__c.FormConfigJSON__c`, which the package regenerates from its sections, fields, rules and conditions on every save), and a form built in place on the section |
| Mappings | Form Template Mapping (`Submission_Field_Map__c`): a form on Account, Contact or another object mapped to its Form Submission landing fields, read from both sides |
| Flow Tool Kit flows | The conversion flows a template names (`Conversion_Map_Flow_<target>__c`, resolved by the read-only `FlowApiName_<target>__c` formulas, and through the Form Template Conversion Mapping Default records when the choice is Default), a section's conversion flow (`Conversion_Map_Flow__c`, `FlowApiName_Related__c`), the template's prefill flow (`Prefill_Flow_Api_Name__c`), the screen flow a Flow Section shows (a section's `FlowApiName__c` when its `Component_Type__c` is Flow), any flow that uses a Flow Tool Kit action or screen component (the `FlowToolKit` namespace on the action, component or called flow), and every subflow those flows call. A field given a Get URL Parameters output in one of them is a URL parameter mapping too |

Any other flow is read only to learn whether it uses Flow Tool Kit; if it does not, it is never listed.

**Form Template Mapping** matters most on the paid edition. A form component built on a source object maps each of its fields to the Form Submission field it lands on, and Apply Submission Field Maps fills the record from those landing fields at conversion. A landing field used only through such a mapping is still in use: the audit counts the mapping as a reference to the landing field and to the source field, so the field shows as Active, never Unreferenced.

What it gives back:

1. **Where each field is used in Flow Tool Kit.** Every template, page, section, component, rule, mapping and Flow Tool Kit flow that touches it, in what role, and for a flow, why it is a Flow Tool Kit flow (`conversion flow (Contact1) of template Volunteer Application`).
2. **A verdict per custom field.** **Active**: Flow Tool Kit references or maps it, with the places listed. **Unreferenced**: none of the places above references it.
3. **A data dictionary.** Label, type, description, help text, Salesforce's governance fields, the surfaces that use it, where it is used, what it is mapped to, and what its documentation lacks.

For a picklist change, the Snippet column of `template_references.csv` shows the value each page, section or payment rule compares against. The audit never changes the org and never reads submission data.

## Where it runs

| Surface | How it reads the org |
|---|---|
| Claude Code (local or on the web) with the Salesforce CLI | `audit.py collect` runs every query itself |
| claude.ai chat with a Salesforce connector that runs SOQL | The connector runs each query; `audit.py` (in code execution) says which queries are next and builds the files from the rows |
| Chat without a connector, or no org connected | Say so in one line: there is nothing to audit without an org |

Python 3 standard library only; nothing to install. Run the script by its path in this skill folder: `python3 scripts/audit.py ...`. It reads the org through org-catalog's helpers (the same query runner, connector protocol and row reader), so the org-catalog skill must be installed beside this one, as it is when the whole Flow Tool Kit plugin is installed.

## The run

### 1. Find the org and the scope

In Claude Code use the org the project points at: the alias saved for this org in `flow-tool-kit.json` ([_shared/standards/project-config.md](_shared/standards/project-config.md)), otherwise the Salesforce CLI's default org. In chat, look for a Salesforce connector with a query tool.

Then settle the scope from what the person asked, without asking when it is clear:

- **The whole org** (cleanup, "which fields do we use?", a client data dictionary): the default.
- **One template** (the end of a build, "document what we built"): add `--template "<Name or Id>"`. The files then hold only the fields that template uses, each with its org-wide verdict.
- **More objects**: Form Submission is always audited in full. Add `--object Contact` (repeatable) when the person wants every custom field on Contact judged too, not only the ones forms use.
- **Flows**: `all` (default in Claude Code: every flow the org owns is read once to find the ones that use Flow Tool Kit), `named` (only the conversion and prefill flows templates and sections name, the screen flows Flow Sections show, and their subflows; the default to suggest in chat, where each flow is one connector call) or `none`. Only Flow Tool Kit flows are ever listed.

### 2. Read the org

**Claude Code:**

```bash
python3 scripts/audit.py collect --target-org <org-alias> [--template "Volunteer Application"] [--object Contact] [--flows all]
```

It runs the queries in passes (each depends on the one before: which flows templates name and which use Flow Tool Kit, the subflows they call, which objects the forms use), retries a tooling query through the data API, and leaves out any column the org refuses (an older Flow Tool Kit version, or a field you cannot read), noting it in the coverage. On a large org it takes a few minutes; most of it is one query per flow.

**Chat with a connector:** loop until nothing is left.

```bash
python3 scripts/audit.py next-queries raw.json --flows named   # options are fixed by the first call
```

It prints a JSON list of `{key, soql, tooling, optional, why}`; `[]` means the reads are done. For each query, run its `soql` through the connector, save what came back to a file, and add it:

```bash
python3 scripts/audit.py add raw.json --key <key> --records-file rows.json
python3 scripts/audit.py add raw.json --key <key> --error "<the error message, word for word>"
```

- `tooling: true`: use the connector's Tooling API option if it has one; otherwise run the same SOQL as a plain query (FieldDefinition and EntityParticle answer both ways). Flow metadata needs the Tooling API; without it the flows are listed as not scanned.
- Pass every error through `--error` exactly as the connector gave it. When it names a column (`No such column`, `Didn't understand relationship`), the same key comes back from `next-queries` without that column; run it again. `optional` queries may fail for good; the files say what is missing.
- Rows can be added as the connector returns them (a list, `{"records": [...]}` or `{"result": {"records": [...]}}`). Long JSON fields (`FormConfigJSON__c`, `config__c`, `Prefill_Values__c`) must arrive whole: if the connector truncates long text, page the query with `LIMIT` and `OFFSET`, or by Id, and add the pages together as one list.

Then build:

```bash
python3 scripts/audit.py build raw.json [--template "<Name or Id>"] [--instance-url https://<my-domain>.my.salesforce.com]
```

`--instance-url` turns the record and Setup columns into links. What each query reads and why: [references/reading-the-org.md](references/reading-the-org.md).

### No submission data, with one approved exception

Every query reads configuration or metadata: Form Templates, pages, page sections, Form Components, Flow Tool Kit custom metadata, the email templates a template names, field definitions and flow metadata. None counts records. The one read of another object's records is a Form Template Source's prefill mapping column (`SELECT Id, <mapping field>`), which is configuration an admin sets.

**The prefill template exception (approved).** A prefill template is a Form Submission record that an admin sets up as configuration: a template or section names it, and the form copies its values into every new submission. It is the one Form Submission read, kept narrow on purpose: only the records a template (unless Skip Prefill) or section names, by Id (`WHERE Id IN (...)`), only the fields a prefill template can set, and only to learn which fields have a value and which merge tokens the values hold. No value is written to the files, no other submission is read, and nothing is counted. The coverage says how many named prefill templates were read.

### 3. The files

Both paths write into `field-audit/<org Id>/` (or `--out`); in chat, write them to the outputs folder and offer them as downloads.

| File | One row per | For |
|---|---|---|
| `data-dictionary.md` | field, grouped by object | People: summary, unreferenced fields, every field, coverage |
| `data_dictionary.csv` | field | Sorting and filtering in a spreadsheet; every column below |
| `template_references.csv` | place a template or form uses a field | Tracing one field to every section, rule and mapping |
| `flow_references.csv` | place a Flow Tool Kit flow uses a field | The same, in conversion, prefill and other Flow Tool Kit flows, with why each flow is listed |
| `coverage.csv` | place read, or not read | Knowing what an empty answer means |
| `raw.json` | query (Claude Code) | Rebuilding with `build` without reading the org again |

Columns, roles and verdicts in full: [references/outputs.md](references/outputs.md). Every place a field can be stored and how each is read: [references/surfaces.md](references/surfaces.md).

### 4. Tell the person, in a few lines

Lead with the counts, then what stands out, then what was not scanned. For example:

> I audited Riverside Community Garden: 34 fields, used in 39 places across templates and forms and 7 in Flow Tool Kit flows. 3 Form Submission fields are Unreferenced (Shirt Size, Tool Waiver, Visit Time): no template, section, form, rule, mapping or Flow Tool Kit flow references them. Garden Plot is Active only because the template's Contact 2 conversion flow, Garden Plot Convert, maps it. Contact 1 Email is referenced only through the Household Contact form's Form Template Mapping (Contact.Email lands there), so it is Active. 6 of your own fields miss part of their documentation, starting with Household Role on Contact, which has no description. One flow could not be read, so whether it uses Flow Tool Kit is not known. Before deleting anything, also open each field's Where is this used? in Setup for Apex, reports, layouts and other flows. Files: field-audit/00D000000000001EAA/data-dictionary.md and the CSVs beside it.

### 5. Before anyone removes a field

**Unreferenced means Flow Tool Kit does not use it, not that nothing does.** It says nothing about Apex, reports, layouts or other flows, which the audit leaves to Salesforce, and nothing about data, because the audit reads none. Say this whenever unreferenced fields are found:

- Read `coverage.csv` first. A Flow Tool Kit flow that could not be read, a page that could not be parsed, a prefill template or email template that could not be read can hold the one use the audit missed. The package's own default conversion flows are not served by the org; they are listed there too.
- Open the field's **Where is this used?** button in Setup for Apex, reports, page layouts, validation rules and flows outside Flow Tool Kit, and check list views and report filters by hand.
- A field can be unreferenced and still hold data an integration or import writes. Whether to keep that data is the person's call, outside this audit.
- A field that looks redundant beside its twin (a packaged field and an org field with the same purpose) can still carry a live job outside Flow Tool Kit: check Where is this used? before recommending removal.
- Packaged fields cannot be deleted by a subscriber: `data-dictionary.md` marks them Packaged.

Hand the list to the person; never delete or change a field from this skill.

### 6. Documentation gaps

For every custom field the org owns (a package documents its own), the audit checks the plugin's documentation standard ([_shared/standards/documentation.md](_shared/standards/documentation.md)): a description on every field; on a Form Template field, help text of at least two sentences; help text of 255 characters or fewer; no issue numbers or em-dashes in either. Each gap is in the `Documentation` column.

When the person wants them fixed, write the missing descriptions and help text in the standard's shape (summary first, written for the admin; help for the person filling the field, never admin instructions on a Form Submission field), cite only flows and fields the dictionary shows exist, and change them the way the project changes metadata. The audit only reports.

## Called by other skills

- **ftk-start**, at the end of a build: `collect --template "<the template built>"` and hand over `data-dictionary.md` as the record of what was built.
- **form-migrate** imports `scripts/fieldaudit/` (`org`, `walk`, `names`) to read an existing Form Template. Keep those names stable.
- **org-catalog** owns the shared query runner this skill uses.
