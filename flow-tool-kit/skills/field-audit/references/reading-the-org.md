# Reading the org

What field-audit reads, in which order, and the Salesforce details behind each read. It reads configuration and metadata: Form Templates, pages, page sections, Form Components (record and JSON), metadata components and the other Flow Tool Kit custom metadata, the email templates a template names, the prefill template records a template or section names (the one approved exception, below), field definitions and flow metadata. It never reads Apex, reports, page layouts or metadata dependencies (Setup's **Where is this used?** covers those), and it queries no Form Submission record but the named prefill templates: no counts, no samples, no other submissions. The query text lives in one place, `scripts/fieldaudit/queries.py` (and `sweep.py` and `flows.py` for the reads that depend on what was found); `audit.py next-queries` prints it for whichever runner is in use. The runner itself (the CLI call, the tooling fallback, reading a connector's rows) is org-catalog's, shared through `scripts/fieldaudit/orgreads.py`.

## The passes

| Pass | Keys | Why this order |
|---|---|---|
| 1 | `org`, `ftk` | Which org, its namespace, and whether Flow Tool Kit is installed (an EntityDefinition query, so a plain SOQL connector can answer it) |
| 2 | `templates`, `pages`, `sections`, `components`, `forms_mdt`, `sections_mdt`, `fields_mdt`, `conditions_mdt`, `sources_mdt`, `conversion_defaults`, `flow_definitions`, `fields:` and `particles:` for every audited object | Everything a field reference can be stored in, the flows templates and sections name, and every field of the audited objects |
| 3 | `fields:<source object>` for a Form Template Source that points at a custom field, `email_templates` (the templates the Email Template Name fields name) and `prefill_templates:<n>` (the named prefill templates, by Id, 100 to a query); then `source_records:<object>` and `flow:<ApiName>` for each flow to read, repeated until every subflow of a Flow Tool Kit flow is read | Depend on pass 2: which sources, email templates, prefill templates and flows the templates name, and which Form Submission fields a prefill template can set |
| 4 | `entities` when a config names an object by its Id (`01I...`); then `fields:` and `particles:` for every other object a form, mapping or Flow Tool Kit flow uses | Depend on every reference found so far |

A failed query whose error names a column comes back in the next pass without that column; every column left out is recorded.

## Field existence: FieldDefinition, never a describe

A describe (`sf sobject describe`, or a connector's describe tool) silently leaves out fields the running user has no field-level access to, so a field that exists looks missing. Every field list here comes from **FieldDefinition** (every field, with Description, DurableId, Security Classification, Compliance Group and Business Status) and **EntityParticle** (label and inline help text). Both answer through the Tooling API and through a plain query.

A field the user cannot read still gets its dictionary row and its verdict from FieldDefinition: the verdict depends on references, not on reading the field.

## Older Flow Tool Kit versions

Newer columns do not exist in an org on an older version (the page and section header fields, Payment Conditions, Submission Field Map, Header Tags). A query that names one fails with `No such column 'FlowToolKit__X__c'` or `Didn't understand relationship 'FlowToolKit__X__r'`. That is normal: the column is left out, the query runs again, and the store it fed is simply empty.

## No submission data

None counts records, and only one kind of query names `Form_Submission__c` in its `FROM`: the approved prefill template exception. A prefill template is a Form Submission record an admin sets up as configuration, named by a template (`Prefill_Template__c`, unless `Skip_Prefill__c`) or a section (`Prefill_Template__c`). The audit reads exactly those records, `SELECT Id, <settable fields> FROM FlowToolKit__Form_Submission__c WHERE Id IN (<the named Ids>)`, to learn which fields they set and which merge tokens their values hold; values are never written to the files. Settable means a custom field that is not a formula, roll-up or auto number, and not one the form resets when it seeds a submission. The tests check every query the audit sends: a Form Submission read must be limited to the named Ids.

## Email templates

`email_templates` reads `EmailTemplate` (Id, DeveloperName, Name, NamespacePrefix, TemplateType, UiType, RelatedEntityType, LastModifiedDate, Subject, HtmlValue, Body, Markup) for the developer names in `Email_Template_Name_Confirmation__c`, `_Saved__c`, `_Start_Form__c` and `_Resume_Form__c` (an Id there is matched by Id). Several templates can share a developer name; the send flows use the newest, so the audit does too. A template in a folder the running user cannot see does not come back: it is a `missing` coverage row.

## Form Template Sources

A source's pointer fields are custom metadata relationships. Queried raw, a standard field arrives as `Campaign.StartDate` and a custom field as `Campaign.00N...`. The custom field's name comes from the source object's FieldDefinition rows (their DurableId ends in the same Id), so no Tooling-only read is needed. The prefill mapping JSON is stored on the source records themselves (a long text field, so it cannot be filtered): the newest `--source-limit` records (default 300) are read, `SELECT Id, <mapping field>` and nothing else, and blank ones skipped. That column is configuration an admin sets; a source on Form Submission itself is never read.

## Flow Tool Kit flows

Only Flow Tool Kit flows are listed. A flow is one when:

| Why | Read from (package fields) |
|---|---|
| A template names it as a conversion flow | `Form_Template__c.Conversion_Map_Flow_<target>__c` (picklist: Default or a flow API name) and the read-only formula `FlowApiName_<target>__c`, for the targets Account, CampaignMember, Case, Contact1, Contact2, Controller, FileUpload, Lead1, Lead2, Opportunity and Order. When the picklist is Default and the formula is not readable, the flow comes from `Form_Template_Conversion_Mapping_Default__mdt.Flow_API_Name__c` (record Account, CampaignMember, Case, Primary_Contact, Alternate_Contact, Controller, FileUpload, Primary_Lead, Alternate_Lead, Opportunity or Order) |
| A page section names it as a conversion flow | `Form_Template_Page_Section__c.Conversion_Map_Flow__c` and the read-only formula `FlowApiName_Related__c`; on Default, the section's `Conversion_Rule__c` picks the same custom metadata record (Contact1 Primary_Contact, Contact2 Alternate_Contact, Lead1 Primary_Lead, Lead2 Alternate_Lead, Case Case) |
| A template names it as its prefill flow | `Form_Template__c.Prefill_Flow_Api_Name__c` (Bypass names none) |
| A Flow Section shows it | `Form_Template_Page_Section__c.FlowApiName__c` on a section whose `Component_Type__c` is Flow (a value left on a section of another type is not shown, so it names no flow) |
| It uses Flow Tool Kit | An action whose name starts `FlowToolKit__`, a screen component whose name starts `FlowToolKit:`, or a subflow call to a `FlowToolKit__` flow |
| A Flow Tool Kit flow calls it | Any subflow (`subflows[].flowName`) of the flows above, and theirs in turn |

- `flow_definitions` reads FlowDefinitionView (a plain query). Scope `all` (default) reads every flow the org owns to find the ones that use Flow Tool Kit; `named` reads only the named flows and their subflows; `none` reads no flow. A flow read only to check it, and not Flow Tool Kit's, is never listed, not even in the coverage.
- Each flow read is one Tooling query, `SELECT Id, Metadata FROM Flow WHERE Id = '<version Id>'` (the active version, else the latest). The Metadata arrives as JSON, never XML, so no retrieve or project folder is needed, in Claude Code or in chat. In chat it needs a connector with a Tooling API option; without one, flows are listed as not scanned.
- Every place a Flow Tool Kit flow uses a field is a Flow reference with the flow's API name, the element and why the flow is listed: entry filters, Get, Update, Create and Delete Records, decisions, assignments, formulas and text templates, Transform values, screen components and actions. A Form Submission field used only in a Flow Tool Kit flow is Active.
- Flows of an installed package, Flow Tool Kit's own default conversion flows among them, are never read: an org does not serve their metadata. When a template names one, the coverage lists it.

## The Tooling API and connectors

| Read | Tooling API | Plain SOQL instead |
|---|---|---|
| `fields:`, `particles:` | Preferred | The same query works |
| `flow:<ApiName>` | Required | Not available: flows show as not scanned |
| Everything else | No | Plain SOQL |
