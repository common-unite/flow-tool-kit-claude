# Reading the org

What org-catalog reads, in which order, and the Salesforce details behind each read. The query text lives in one place, `scripts/ocqueries.py`; `catalog.py next-queries` prints it for whichever runner is in use.

## The passes

| Pass | Keys | Why this order |
|---|---|---|
| 1 | `org`, `platform_objects`, `packages` (tooling, optional), `person_accounts` (optional) | Which org, and whether Flow Tool Kit is installed at all. `platform_objects` is an EntityDefinition query, so it works through a plain SOQL connector even without the Tooling API |
| 2 | `forms_mdt`, `sections_mdt`, `fields_mdt`, `components`, `templates`, `pages`, `page_sections`, `fields:FlowToolKit__Form_Submission__c` (tooling), `style_defaults` (optional), `brand_files` (optional) | Everything the reuse map is made of. Runs only when Flow Tool Kit is installed |
| 3 | `fields:<object>` for every object a component or section uses (tooling, optional); `component_fields` and `component_sections` only for record components whose JSON is blank; `brand_file_libraries` when a brand file was found | Depend on what pass 2 found |
| 4 | Claude Code only: a read-only retrieve of `Flow`, `FlexiPage`, `ExperienceBundle` and `DigitalExperienceBundle`, and `LightningComponentBundle` (the org's own components), into a temporary folder | Where else each component is used. Metadata, not records, so no SOQL reads it. `--skip-placements` leaves it out |

Nothing reads a Form Submission, an answer, or any record a respondent created.

## What each read gives

- **Metadata components** are three custom metadata types: the Form (`FlowToolKit__Form__mdt`), its sections (`Form_Section__mdt`) and its fields (`Form_Field__mdt`). A section can place another component (`formComponent__c`), a table form (`Default_Table_Form__c`) or the table's bulk edit form (`Default_Table_Form_bulk__c`); a field can show a lookup as a component (`referenceFormComponent__c`). A record component's sections carry the same three, in its JSON or its `Form_Component_Section__c` rows. Those are the layers. Rows with `Delete__c` checked are soft-deleted and left out.
- **A metadata field's `fieldName__c` is a durable Id**, such as `Account.Website` for a standard field, `Account.ShippingAddress.ShippingCity` for part of a compound field, or `Account.<field Id>` and `<object Id>.<field Id>` for custom fields. The catalog resolves each one through the FieldDefinition rows of that object (`DurableId`), the same way the package does.
- **Record components** are `FlowToolKit__Form_Component__c` rows. Their whole design is in `FormConfigJSON__c` (sections in `*__sections__r`, fields in `*__fields__r`, `*__` standing for the package prefix). A component can have several version rows (`VersionId__c` is `<name>_v<n>`); the catalog reads the latest active one and lists every version Id. Rows of the **Metadata Component** record type only track a metadata form and are folded into it.
- **Folder and tags** are how the component browser files a component: `Folder__c` (a path, names joined with a slash) and `Tags__c` (comma separated) on `Form_Component__c`; a metadata form keeps the same keys in its `config__c`. Both fields arrived in version 4.49, so an older org drops them as missing columns and the catalog leaves folder and tags empty.
- **Form Template Mapping** is the JSON in a record component's `Submission_Field_Map__c` (or the same key inside a metadata form's `config__c`): `{"lookupField": "ALL" or a Form Submission lookup, "fields": {Form Submission field: the component's own field}}`.
- **A page section shows** whatever its `FormConfigJSON__c` says, the way the package resolves it: `formSelectionMode` `component` names a component (`formQualifiedApiName`); `custom` carries its own form JSON (`formJsonConfig`); a blank JSON falls back to `FormQualifiedApiName__c`. A name ending `_v0` is a record component; any other is a metadata one. Component Type `Flow`, `LightningWebComponent` and `DisplayText` show no component. A Table section can name a different form for its New and Edit window (`Alternate_FormQualifiedApiName__c`) and for bulk edit (`Bulk_FormQualifiedApiName__c`).
- **Templates** can name a header and a footer form (`FormQualifiedApiName_Header__c`, `_Footer__c`); those count as places a component is used.

## Where else a form is used

A Form Component can be shown outside Form Templates by name. These are the package components and the inputs or properties that carry the name (from each component's `js-meta.xml`); `scripts/ocplaces.py` holds the same list.

| Where | Package component (label) | API name | Inputs or properties naming a form |
|---|---|---|---|
| Flow screen | Form (Component) | `FlowToolKit:flowForm` | `formQualifiedApiName`; `formJSON` holds a form's own JSON (components placed inside it count) |
| Flow screen | Form (Repeater) | `FlowToolKit:flowFormRepeat` | `formQualifiedApiName`, `editFormQualifiedApiName`; `formJSON` |
| Flow screen | Form (Table) | `FlowToolKit:flowDataTable` | `formQualifiedApiName`, `overrideTableFormName`, `overrideTableFormBulkName`; `formJSON` |
| Flow screen | Form (Lookup) | `FlowToolKit:flowFormLookup` | `formQualifiedApiName`, `overrideTableFormName` |
| Lightning record, app or Home page; site page | Form (Component) | `FlowToolKit:lightningRecordForm` | `formQualifiedApiName` |
| Site page (Aura or LWR) | Form (Dynamic Component) | `FlowToolKit:lightningRecordFormDynamicDisplay` | `properties`, a JSON string: `formQualifiedApiName` unless `formSelectionMode` is `custom`, when the form's own JSON is in `formJsonConfig` |
| The org's own Lightning web component | A wrapper rendering `<flowtoolkit-lightning-record-form>` (or another package form tag) | its bundle name | `form-qualified-api-name` in its HTML, or a name in its JavaScript; `form-json-config` means it holds a copy of the form's JSON |

How each is read:

- **Flows**: every screen field whose `extensionName` is one of the four, with its `inputParameters`. A `stringValue` names the form. An `elementReference` to a constant or variable with a fixed `stringValue` is resolved to it; any other reference (a formula, an input variable, a record field) is a form chosen at run time and goes into `run_time_forms`. The retrieve returns each flow's active version, or its latest when none is active (`status`).
- **Lightning pages**: every `componentInstance` in the FlexiPage's regions named `FlowToolKit:lightningRecordForm`, with its `componentInstanceProperties`. A value bound to the page (`{!...}`) is a run-time form.
- **Site pages**: Aura sites are `ExperienceBundle` views (`views/<page>.json`, `componentName` and `componentAttributes`); LWR sites are `DigitalExperienceBundle` views (`sfdc_cms__view/<page>/content.json`, `definition` and `attributes`). Both are read; an org whose ExperienceBundle setting is off retrieves LWR sites only, and the other retrieve's error is listed.
- **Wrapper components**: a retrieve of `LightningComponentBundle` returns only the org's own components. One counts when its HTML renders a package form tag; names in its HTML attributes, and strings in its JavaScript that are the name of a cataloged component, are its forms. Test files (`__tests__`) are skipped.

A name that is not in the org is a problem (a missing form); a wrapper's other strings are ignored. What the reads cannot see: a form name built in Apex or JavaScript at run time, a custom component that passes a name it was given in App Builder (only the package's own components are read on a page), and managed packages' own flows and pages.

**In chat**: a connector that runs SOQL cannot read flows, Lightning pages or site pages, because their content is metadata. The catalog then says so (`placements.complete` false, `placements.note`), and "used in" lists Form Templates and components only. A connector that can retrieve metadata, or the project's source pulled from this org, can fill it: put the files in one folder and run `catalog.py add-placements raw.json --dir <folder>`.

## Field existence: FieldDefinition, never a describe

`sf sobject describe` and any describe call silently leave out fields the running user has no field-level access to, so a field that exists looks missing. Every field list in the catalog comes from FieldDefinition through the Tooling API (`sf data query --use-tooling-api`), which lists every field. A connector without the Tooling API can run the same FieldDefinition query as a plain query. If a connector offers only describe, say that field existence is unverified, and check a name with a metadata list of CustomField in Claude Code before creating a field.

## Older Flow Tool Kit versions

Newer fields do not exist in an org on an older version (for example the template Logo fields, which are newer than 5.2). A query that names one fails with `No such column 'FlowToolKit__Logo__c'`. That is normal: remove the column, rerun the query, and the catalog notes the left-out columns as a warning. `catalog.py collect` does this by itself.

## The brand kit reads

- **Style defaults.** `FlowToolKit__Form_Style_Defaults__c` is a protected hierarchy setting; only the org-level row (`SetupOwnerId` is the org Id) is used. Whether an installed package lets an admin read it through the API can differ by org; when the read is refused, the catalog records it and falls back to the template Logo formula, which shows the org default logo on any template without its own Logo Override.
- **Brand file.** A ContentVersion titled `brand-kit` with the `json` extension, latest version only; `brand_file_libraries` says whether it sits in the Asset Library. In Claude Code the file's text is read through the REST API (`sf api request rest`) so the catalog can name the brand and its colors; a connector that cannot download files leaves the file listed but unread.

## The Tooling API and connectors

| Read | Tooling API | Plain SOQL instead |
|---|---|---|
| `packages` (installed version) | Yes | Not available; the version shows as not read. Flow Tool Kit itself is still detected from EntityDefinition |
| `fields:<object>` | Preferred | The same FieldDefinition query works |
| Everything else | No | Plain SOQL |

A connector that returns long text fields cut short breaks a component's JSON (`unreadable` in the catalog). Page the `components` and `page_sections` queries with `LIMIT 50 OFFSET n` or by Id so each row arrives whole.
