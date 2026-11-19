# The files, what each column means, and where Flow Tool Kit stores a field name

## The files and what each column means

CSV files are UTF-8 with a byte-order mark, so Excel and Google Sheets open them with accents intact. Link columns hold Lightning addresses when the org's address is known (always in Claude Code; in chat, pass `--instance-url` to `build`), and are blank otherwise.

### data_dictionary.csv and data-dictionary.md

One row per field. Every custom field of an audited object (Form Submission, plus each `--object`) gets a row; a field of any other object gets one only when something uses it. With `--template`, only the fields that template uses.

| Column | Meaning |
|---|---|
| Object, Field Label, API Name, Type | From FieldDefinition and EntityParticle |
| Description, Help Text | The field's own, as Setup shows them |
| Security Classification, Compliance Group, Business Status | Salesforce's governance fields (Data Classification and Field Usage in Setup) |
| Sections, Rules, Mappings, Prefill, URL, Merge, Flows | How many uses of each kind (see Buckets) |
| Total Refs | Their sum |
| Surfaces | Each surface that uses it, by name (`Section Form; Form Template Mapping; Flow Action`), so a field the Mappings bucket counts shows whether a Form Template Mapping, a source or a nullable list uses it |
| Used In | The templates (or forms, or Flow Tool Kit flows) that use it, six at most |
| Mapped With | Its partner in a Form Template Mapping, with the form's name: `Account.Phone (Partner Organization)` on the Form Submission landing field, the landing field on the source field |
| Verdict | See Verdicts; custom fields only |
| Documentation | What the field lacks under the documentation standard, fields the org owns only |
| Field Link | The field in Object Manager |

A row with no label and the note `not a field on this object` is a reference to a field that does not exist: renamed, deleted, or misspelled in a config. Fix the config.

#### Buckets

| Bucket | Surfaces |
|---|---|
| Sections | Section Form, Header Form, Footer Form, Table Form |
| Rules | Page Rule, Section Rule, Payment Rule |
| Mappings | Form Template Mapping, Source Mapping, Source Config, Nullable |
| Prefill | Prefill Values |
| URL | URL Parameter |
| Merge | Merge Token |
| Flows | Flow Screen Form, Flow Element, Flow Formula, Flow Action |

### Verdicts

The verdict answers one question: does Flow Tool Kit reference this field? It is never based on records (the audit reads no Form Submission data), and never on Apex, reports, page layouts or flows outside Flow Tool Kit, which Setup's **Where is this used?** lists.

| Verdict | When |
|---|---|
| Active | Referenced or mapped in Flow Tool Kit: a Form Template, page, page section, Form Component (metadata, record or JSON), rule, mapping, prefill, URL parameter, merge token, or a Flow Tool Kit flow (conversion, prefill, the screen flow a Flow Section shows, one using a Flow Tool Kit action or screen component, or their subflows). The places are listed in Surfaces, Used In and the reference files. A Form Template Mapping counts: a landing field used only through one is Active |
| Unreferenced | No Flow Tool Kit place references it. A field used only in a flow outside Flow Tool Kit is Unreferenced here; Where is this used? shows that flow |

Only custom fields get a verdict. A field with the org's own namespace (a namespaced development org) belongs to the org. An unreferenced field an installed package owns is marked Packaged in `data-dictionary.md`: a subscriber cannot delete it.

### Documentation checks

From the plugin's documentation standard ([_shared/standards/documentation.md](../_shared/standards/documentation.md)), on custom fields the org owns:

| Gap | Rule |
|---|---|
| `no description` | Every custom field ships with a description |
| `no help text (a Form Template field needs two sentences)`, `help text is one sentence (...)` | Form Template fields are read by the people who build templates, so their help is required and at least two sentences |
| `help text over 255 characters` | Inline help is 255 characters at most |
| `... cites an issue number`, `... has an em-dash` | Descriptions and help stand alone: no ticket numbers, no em-dashes |

Form Submission fields need no help text (it can show to respondents), so its absence is not a gap.

### template_references.csv

One row per place a template or form uses a field: Object, Field Label, Field API Name, Surface, Role, Form Template, Page, Section, Component Type (`Metadata`, `Record` or `JSON` for a form built in place, `Email Template`, `Prefill Template`), Component, Snippet, and links to the field, template, page, section and component. The Snippet shows the context: a rule's operator and value, a mapping's partner, the merge text, a prefill value, the email template part a merge field is in. For a prefill template it names the field set, never the value.

Roles include: `input field`, `rule operand` (page, section and payment rules, and the field and section rules inside a Form Component), `min-date bound`, `max-date bound`, `related-field override / score target`, `column class driver`, `merge token` (inside a form), `merge token in <place>` (such as `merge token in confirmation message` or `merge token in page header text`), `merge field in the <email> template`, `URL parameter target`, `prefill value key`, `prefill template sets it`, `merge token in a prefill template value`, `may be cleared by a blank answer`, `keeps a mapped answer`, `mapped to Form Submission`, `mapping lookup`, `source pointer (<setting>)`, `mapping target`, `mapping source path` (`(live)` when the source keeps the answer in step).

### flow_references.csv

One row per place a Flow Tool Kit flow uses a field: Flow, Flow API Name, Flow Type, Flow Tool Kit Role, Element, Element Type, Surface (`URL Parameter` for a field given a Get URL Parameters output, with the role `URL parameter target (pv1)`), and a Resolution of `parsed` or `not captured` (a form chosen at run time, or a field set whose members are not expanded).

Flow Tool Kit Role says why the flow is listed, each reason once: `conversion flow (Contact1) of template <name>`, `conversion flow of section <title>`, `prefill flow of template <name>`, `Flow Section screen flow of section <title>`, `uses the Flow Tool Kit action <name>`, `uses the Flow Tool Kit screen component <name>`, `calls the Flow Tool Kit flow <name>`, `subflow of <flow>`. A flow with none of these is never listed.

### coverage.csv

| Status | Meaning |
|---|---|
| parsed | Read, with counts |
| not_captured | Deliberately or necessarily not read: Flow Tool Kit's own default conversion flows and other package flows (an org does not serve their metadata), a flow whose metadata could not be read, prefill template records or email templates when that read failed, a store an older package lacks |
| unparseable | Stored JSON that could not be read; the Detail names the template, page or section |
| missing | A form, flow, email template or prefill template that resolves to nothing (a template naming a conversion flow the org does not have, an email template you cannot read), or a read that failed |

## Where Flow Tool Kit stores a field name

Every surface the audit reads, the shape it is stored in, and the details that took a real org to find. `scripts/fieldaudit/sweep.py` reads the templates and forms, `flows.py` the flows, `walk.py` holds one parser per stored shape.

### Surfaces

| Surface (in the CSVs) | Stored in | Shape |
|---|---|---|
| Section Form | A page section's form: a metadata form (`Form__mdt` with its sections, fields and rule conditions), a record component (`Form_Component__c.FormConfigJSON__c`) or a form built in place (the section's own `FormConfigJSON__c`), including the form's own field and section rules | Field keys in config JSON, CMT relationships |
| Header Form, Footer Form | `Form_Template__c.FormQualifiedApiName_Header__c` and `_Footer__c` | A form name, resolved like a section's |
| Table Form | A table section's New and Edit form, bulk edit form and edit form (`Alternate_`, `Bulk_`, `Edit_FormQualifiedApiName__c`) | A form name |
| Page Rule, Section Rule, Payment Rule | `Conditional_Logic__c` on pages and sections; `Payment_Conditions__c` on the template | `{"objectApiName", "ruleMode", "conditions": [{"fieldApiName", "operator", "value"}]}` |
| URL Parameter | `Form_Template__c.URL_Parameter_Mapping__c`, the only place the package stores a URL parameter mapping; and, in Flow Tool Kit flows, a field given a Get URL Parameters output (`FlowToolKit:getUrlParameters`, outputs `pv1` to `pv9` and the rest) | `[{"field", "param"}]`; in a flow, an output's `assignToReference`, or an assignment or record element whose value is `<component>.pvN` |
| Prefill Values | `Form_Template__c.Prefill_Values__c` | A JSON object keyed by Form Submission field |
| Prefill Template | The prefill template records a template (`Form_Template__c.Prefill_Template__c`, unless Skip Prefill) or a section (`Form_Template_Page_Section__c.Prefill_Template__c`) names, read by Id | Each Form Submission field with a value is one the template sets (an unticked checkbox sets nothing, as the form treats it); `{{tokens}}` in a text value |
| Nullable | `Form_Template__c.Nullable_Fields__c` | A comma list, or `{"Contact": ["MobilePhone"]}` |
| Merge Token | Template text (confirmation message, offline message, header and footer text, subtitle, header tags, review page label and subtitle, confirmation email body), page text (label, title, details, description, footer, header title, subtitle, text, kicker, lead, footer and tags), section text (header title, subtitle, text, kicker, lead, footer and tags, divider title and subtitle, section text) and any string inside a form config (banner, rich text, labels, help) | `{{Field__c}}`, `{{$Template.X}}`, `{{$Page.X}}`, `{{$Section.X}}` |
| Email Template | The stored email templates a template names in `Email_Template_Name_Confirmation__c`, `_Saved__c`, `_Start_Form__c` and `_Resume_Form__c` (by developer name; the newest with that name is the one sent), read from `EmailTemplate` Subject, HtmlValue, Body and Markup | Lightning `{{{Object.Field}}}`, Classic `{!Object.Field}`, Visualforce `{!relatedTo.Field}` on the template's related object |
| Source Config | `Form_Template_Source__mdt`: the source object's pointer fields, and the Form Submission lookup back to it | Metadata relationships, raw |
| Source Mapping | The prefill mapping JSON stored on each source record (only that one column is read) | `{"<Form Submission field>": "<source path>"}` or `{"source", "live"}` |
| Form Template Mapping | A form built on another object: `Form_Component__c.Submission_Field_Map__c`, or the same key inside a metadata form's `config__c` or a form root in JSON | `{"lookupField": "ALL" or a Form Submission lookup, "fields": {"<Form Submission field>": "<the form's own field>"}}` |
| Flow Screen Form, Flow Element, Flow Formula, Flow Action | The metadata of Flow Tool Kit flows only (conversion and prefill flows a template or section names, the screen flow each Flow Section shows, flows using a Flow Tool Kit action or screen component, and their subflows), read through the Tooling API | See Flows below; `flow_references.csv` names the flow's API name, the element and why the flow is listed |

### Mapped forms (the paid edition)

On the paid edition, a question about a Contact or an Account goes on a form built on that object, and the Form Builder's **Form Template Mapping** tab pairs each of the form's fields with a Form Submission field ([_shared/standards/mapping-preference.md](../_shared/standards/mapping-preference.md)). The audit reads both sides of every pair:

- the Form Submission field keeps the mapped answer (role `keeps a mapped answer`, **Mapped With** names `Contact.Email (Household Contact)`);
- the form's own field is mapped to Form Submission (role `mapped to Form Submission`, **Mapped With** names the Form Submission field);
- a lookup other than `ALL` is itself a Form Submission field in use (role `mapping lookup`).

Each pair is a row in `template_references.csv` with the surface `Form Template Mapping`: the source object field and the Form Submission landing field each name the other in the Snippet (`mapped from Account.Phone`, `mapped to Partner_Phone__c`), and the row carries the template, page, section and component that place the form. So the dictionary documents the mapping from either side, the **Surfaces** column names `Form Template Mapping`, and a Form Submission field that only a mapping fills is Active, never Unreferenced.

The package stores the map on `Form_Component__c.Submission_Field_Map__c` (long text, with `Has_Submission_Map__c` checked when it holds a pair); the Form Builder's mapping tab writes it, and the package's Apply Submission Field Maps action reads it. A mapped component that no template places yet still has its pairs listed (role ends `(form not placed in a template)`). In flows, the conversion's **Apply Submission Field Maps** action is read for its lookup field; the pairs themselves are counted once, on the form.

### How a form name resolves

The way the package resolves it:

1. a metadata form (`Form__mdt`) of that name;
2. a record component whose `VersionId__c` is the name (`Household_Contact_v1`: sections and headers name a record component by version);
3. the latest live version of a record component whose `QualifiedApiName__c` is the name.

A name that resolves to nothing is a `missing` coverage row: a section pointing at a deleted component.

- **Rows of the Metadata Component record type are never live components.** They only track the versions of a metadata form. A section whose lookup points at one shows a form built in place (classified JSON), as the package treats it.
- A section's `FormQualifiedApiName__c` is a mirror that is never cleared; the wrapper JSON in `FormConfigJSON__c` decides. `formSelectionMode` `component` names a form; `custom` carries its own JSON (`formJsonConfig`, as text or an object); a blank wrapper falls back to the mirror; older sections hold raw form JSON with no wrapper.
- Metadata form fields marked `Delete__c` are soft-deleted and left out.

### Names in three encodings

`names.py` folds them to one:

- FieldDefinition and EntityParticle DurableIds: `Account.Type`;
- bare API names: `FlowToolKit__Email__c` (record columns, mappings);
- the placeholder `*__Email__c`, which every stored config JSON uses for the package prefix.

A relationship path (`Account.Owner.Name`, `Parent__r.Name`) is a path, not a field: it is listed in the references but never rolled up into a dictionary row.

Some configs name a custom object by its entity Id (`01I...`) instead of its name; the `entities` read turns those back into names.

### Two rule dialects

- The Form Builder's own, for a form's field and section rules: `conditionalLogic__r[].conditions__r[].fieldName__c` (a section or field names its rule by `conditionalLogic__c`). In a record component's `FormConfigJSON__c` and a form built in place, the walk marks a field a condition tests as `rule operand`, never as an input. A record component's JSON is regenerated by the package from its child records (`Form_Component_Section__c`, `Form_Component_Field__c`, `Form_Component_Conditional_Logic__c`, `Form_Component_Condition__c`) on every save, so the JSON is a faithful copy and the child records are not read. Metadata forms keep their conditions in `Form_Conditional_Logic_Condition__mdt` (`fieldName__c`, an EntityParticle relationship).
- Pages, sections, payment conditions and site design blocks: `conditions[].fieldApiName`.

### Email templates

A Form Template names its confirmation, save progress, start link and resume link emails by developer name; the package's send flows render the newest template with that name against the recipient and the Form Submission. The audit reads those templates (only those) and lists each merge field with the email it belongs to. `Recipient`, `Sender`, `Organization`, `$` globals and Visualforce variables other than `relatedTo` are skipped; `relatedTo.X` is a field of the template's related object (`RelatedEntityType`, or `relatedToType` in the Visualforce markup). A relationship path (`relatedTo.Form_Template__r.Name`) is listed as a path. A name that matches no template you can read is a `missing` coverage row. An email template chosen per record through a Form Template Source, or passed by a conversion event's override, is record data and not read.

### Merge tokens

`{{Field__c}}` reads the record the text renders against (the Form Submission for template, page and section text; the form's object inside a form config). `{{$Template.X}}`, `{{$Page.X}}` and `{{$Section.X}}` read the template, page or section record. Formatting prefixes and chained suffixes are stripped, so `{{$currency.Amount__c.toFixed(2)}}` is `Amount__c`. Skipped: `{{$Label.X}}`, `{{$Page.Number}}`, `{{$Page.Count}}`, and words that cannot be an API name (`{{label}}`).

### Flows

Which flows count as Flow Tool Kit's, and the package fields that name them: [reading-the-org.md](reading-the-org.md). Inside each one:

- Screen components of Flow Tool Kit: a form passed inline (`formJSON`), by name (`formQualifiedApiName` and the table form names, resolved like a section's), or through a variable (chased through constants and variable defaults; still dynamic, it is a `not captured` row). Field-carrying properties (`fieldName`, `hierarchyFieldName` and the like) are read too. A field set name is reported, not expanded.
- The start element's entry filters and formula (a record-triggered flow on Form Submission).
- Record elements (Get, Create, Update, Delete Records): filters, queried and sorted fields, input and output assignments. Transforms (`outputFieldApiName`: the conversion field maps). Decisions, assignments, formulas and text templates (`{!Var.Field__c}`, with each variable's object from the flow's variable table, `$Record` from the start element). Dynamic choice sets. Screen field visibility, validation and defaults, and record fields placed on a screen (`objectFieldReference`, how a Flow Section's screen flow shows the submission's fields).
- Actions whose text inputs carry field names: Remove Null Values (nullable fields), the conversion log (status and lookup fields), Recalculate Positions, Apply Submission Field Maps (lookup field).

### Not scanned

Listed in `coverage.csv` on every run, so an empty result is never read as a clean bill of health:

- Flows of installed packages, Flow Tool Kit's own default conversion flows among them, and any Flow Tool Kit flow whose metadata the org would not serve.
- Form Submission records, except the prefill templates templates and sections name (approved exception, below). The audit answers only whether Flow Tool Kit references a field and where; it never counts submission records or reads their data.

### The prefill template exception (approved)

A prefill template is a Form Submission record an admin sets up as configuration: a template or section names it, and the form copies its values into each new submission. Reading it is the only way to know which fields it sets, so the audit reads exactly those records, by Id (`SELECT Id, <settable Form Submission fields> FROM Form_Submission__c WHERE Id IN (<the named Ids>)`), and keeps only which fields have a value and the merge tokens inside text values. Values are never written to the files. Formula, roll-up and auto number fields, and the package fields the form resets (Form Template, Is Prefill Template, Status, Tag Internal, Internal Description, Submission Date, Internal Form Start Date Time), are not selected. A template with Skip Prefill checked is skipped, as the form skips it; one whose Prefill Values is also set is read and its rows say `(not applied while Prefill Values is set)`. No other Form Submission record is read and nothing is counted; the tests check every query the audit sends.

### Never listed

Apex, triggers, reports, page layouts, validation rules, list views, Lightning pages and flows outside Flow Tool Kit. They are general metadata, and Setup's **Where is this used?** on the field already lists them. The audit neither reads nor counts them.
