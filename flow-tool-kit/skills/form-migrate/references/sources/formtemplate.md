# Existing Form Template

Use when a Flow Tool Kit Form Template is being cleaned up, redesigned, or merged with other forms. Clean-up is the most common job, and the data needs no third-party parsing.

## Why this source is different

Every other source says what a form *asks*. A template also says where each answer **already lands** in Salesforce. So every IR field carries:

| Key | Holds | Why it matters |
|---|---|---|
| `target` | `{object, field}` the field writes today | Placement: a field already on Account stays on the Account form (with its Form Template Mapping); the plan marks it `keep_target` instead of proposing a new staging field |
| `component` | `{kind: Metadata/Record/JSON, name, section_record_id}` | Reuse: shows which forms are shared components and which are one-off JSON |
| `read_only` | the field's read-only flag | Clean-up: read-only fields are often prefill displays, not questions |
| `submission_landing` | the Form Submission fields the component's Submission Field Map lands this answer on | A mapped Contact or Account form keeps its landing fields; the Field Plan shows the first as the staging field |
| `repeat_section` | the Repeater or Table section the field repeats in (absent for single questions) | A repeater is never rebuilt as one set of questions |

The connector is `parsed` (the template is its own mapping spec), and `form.template` keeps the template's settings (confirmation message, Stages Mode, save progress) for the redesign.

## Getting it

Read-only: SOQL and describes through the Salesforce CLI, so it needs Claude Code. In chat, read the same records through a Salesforce connector and save them in the export's shape (the keys `extract.py` writes).

```bash
cd <form-migrate skill>/scripts
python3 -m formmigrate.sources.formtemplate.extract --org <alias> \
    --template <Form Template Id or Name> \
    --out <project>/_forms/formtemplate-<slug>/template-export.json
```

Then `adapter.build_from_file(".../template-export.json")` gives the IR. The adapter needs no org, so it can be rerun and tested offline from the export. The extractor reuses the field-audit org helpers (`fieldaudit`), which the Flow Tool Kit plugin ships with this skill.

## How a section's form is chosen

The adapter follows `FormTemplate_Utility.sectionFormConfig`, so the IR shows what the package actually draws:

1. A form name ending `_v0` (in component mode, or on a section with no inline JSON) is a **record component**, found by `VersionId__c`.
2. Component mode, or no inline JSON with a form name: a **metadata form** (`Form__mdt`).
3. Anything else: the section's **inline JSON**.

A section in component mode that also carries inline JSON draws the named form; the JSON is left over. The adapter reports it as a finding to clear during clean-up. That leftover is why a raw count of `fieldName__c` in the export can read higher than the IR.

## What each page section draws

`Component_Type__c` on the page section decides what the package draws, and the IR keeps it on the section's structure node as `section.component_type`. An export read before the picklist existed falls back to the `isRepeater__c`, `isTable__c`, `isFlow__c` and `isFieldSet__c` checkboxes, then to Field Set (the package default); `component_type_source` says which.

| Component Type | What `section` keeps |
|---|---|
| Field Set | `form` (kind, name, `FormQualifiedApiName__c`, selection mode, and the inline JSON itself in custom mode) |
| Repeater | `form`, `min`, `max`, `actions` (New, Edit, Clone, Delete: enabled, button label, modal title and subtitle), `Repeater_*` settings, `section_tag`; the node is marked `repeat` and each field carries `repeat_section` |
| Table | as Repeater, with the `Table_*` settings and modal texts, `alternate_form` (`Alternate_FormQualifiedApiName__c`), `bulk_form` (`Bulk_FormQualifiedApiName__c`) and `legacy_edit_form` when the older `Edit_FormQualifiedApiName__c` is set |
| Flow | `flow_api_name` (`FlowApiName__c`) |
| Lightning Web Component | `lwc_component_name` (`lwcComponentName__c`) |
| Display Text | `text` (`Component_Section_Text__c`) and `message_variant`; also a `form.content_blocks` entry |

Section text above a form (`Component_Section_Text__c` on the other types) is kept as `intro_text` and as a content block. A Flow, LWC or Display Text section is never reported as having no form; a Repeater, Table or Field Set with no form is. `form.section_types` counts each type.

## Rules

Page rules and page-section rules (`Conditional_Logic__c` on `Form_Template_Page__c` and on `Form_Template_Page_Section__c`, one JSON shape: AND, OR or custom logic, hide-when negated) and component rules (`Form_Conditional_Logic__mdt` or `conditionalLogic__r` in JSON: AND or OR, HIDE negated) all become condition trees. A section rule governs the whole section (frame, header and form) and is tagged `page-section`. A rule used by two fields appears once per field it governs. A rule that does not parse is a finding and sets `conditions` coverage to `not_captured`.

## Submission Field Maps

A component on another object (a Contact or Account form) can land its answers on Form Submission fields through its Submission Field Map, `{"lookupField": "ALL" or a lookup, "fields": {"<Form Submission field>": "<source field>"}}`. The adapter reads it where the package does: `Submission_Field_Map__c` on a record component, `*__Submission_Field_Map__c` (or the namespaced key) on the form root of a metadata form (`Form__mdt.config__c`) or inline JSON. It keeps the map on the section (`section.submission_field_map`), sets `submission_landing` on each field it lands, and adds a `submission_field_map` node to the connector. A map on a Form Submission form is ignored by the package, so it is reported for clean-up instead.

## Branding

`form.branding` keeps the template's `Header_Tags__c` (split on semicolons), `Form_Banner_Image__c`, `Logo_Override__c` and `Logo_Alt_Text_Override__c` (Flow Tool Kit 5.4 and later), the header form (`FormQualifiedApiName_Header__c`, resolved as a metadata form or a `_v0` record component) and every banner section (`bannerSection`, the `Banner__c` settings JSON) in the header form and in page-section forms. `images` lists the literal image references found: logo override, banner images, banner settings that are not merge fields, image sections (`contentAssetName__c`) and `<img>` sources in rich text. A merge field such as `{{FlowToolKit__Logo__c}}` stays in the banner settings and is not listed as an image.

## Checks before trusting the output

Count independently from the export, following the selection order above, and compare with the IR: fields (raw `fieldName__c` count against IR fields, after setting aside leftover inline JSON on component-mode sections), rules (one IR rule per element a rule governs, page sections with a `Conditional_Logic__c` included), section types (`Component_Type__c` values against `form.section_types`), and unresolved references (expected zero).

## Known gaps

- `images` is `parsed` unless the header form is named but missing from the export; then it is `not_captured` and a finding says so.
- When `Logo_Override__c` is blank the banner shows the org default logo from the Form Builder's Global Styles tab, which is not part of the template; a finding names it. An export from before 5.4 has no logo override fields at all.
- The page and section `Form_Banner_Image__c` values are listed as images, but the current page section does not render them.
- The Alternate and Bulk forms of a Table, and the template's footer form, are named but not read; extract them separately when redesigning those.
- Field-level config such as picklist option overrides, widths and placeholders is not carried into the IR; read the export when redesigning those.
- `validate.py` reports the packaged objects (`FlowToolKit__Form_Submission__c`) as missing when run against a `force-app` that does not contain them; read the org instead (`plan_form.py --use-default-org`), or treat that error as expected for this source.
