---
name: build-table
description: Not a front door: when ftk-start has not run in this conversation, load ftk-start first and let it route here. Use when a Flow Tool Kit Table has to be built or changed, on a Form Template page section or as a Form (Table) component on a screen flow, after repeating-data chose a Table or when someone asks for one directly ("list the 20 volunteers in a table", "show the shifts as a compact table, edit each row in a pop-up"). Sets the table component with its key columns, the row form the New, Edit and Clone windows open, the bulk form, the actions, their labels and window wording, the display settings and the Section Tag a prefill flow fills, checks them against the package's property list, and writes them into plan.json, onto an existing section, or as the flow screen component. 
---

# Build Table

A **Table is a form component** (root type `table`) rendered through the Table component: a page section of type `Table`, or the **Form (Table)** flow screen component. The table shows a few key columns, one line per row; New, Edit and Clone open a window with the **row form**, a second form component holding every question of one row. Use it for many rows (about five or more) or many questions per row, and to keep a repeating section compact. Example (invented): 20 volunteers, the table shows First name, Last name and Email, and each row's Edit opens a window with their role, title, availability and demographics.

**Called by** repeating-data (after the person chose a Table), build-template's report, and directly. **Hands off** the table component and the row form to build-form-component, the prefill flow and any custom row conversion to new-mapping-flow, and a Table inside a Flow Section to build-flow-section.

Read first, beside this file:
- [_shared/standards/repeating-rows.md](_shared/standards/repeating-rows.md): the rules both build skills follow and the spec's common keys.
- [references/properties.md](references/properties.md): every page section field and every flow screen property a Table uses, which renderer reads it, and when to set it.
- Plugin standards: [_shared/standards/documentation.md](_shared/standards/documentation.md) (section 6 is Naming), [_shared/standards/component-shapes.md](_shared/standards/component-shapes.md), [_shared/standards/project-config.md](_shared/standards/project-config.md).

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat, no connector | Write the spec, run `scripts/table.py check`, `section` and `flow-screen` in the code sandbox, and hand over the files |
| claude.ai chat with a Salesforce connector | The above, plus read the org's section fields, and update an existing page section record with the `record` output. A flow file still needs Claude Code to deploy |
| Claude Code, local or on the web | Everything: the org's describe, `sf data update record` for an existing section, build-template's rebuild for a planned one, and deploying a flow that carries the component |

## 1. Read before building

1. **The project config** (`flow-tool-kit.json`): the org, its edition and its audiences. Guests need read on record components (a guest sharing rule on Form Component, record type Record Component) and on a Pre-fill Template record.
2. **The org's full Table property list, once per org.** Describe `FlowToolKit__Form_Template_Page_Section__c` (connector, or `sf sobject describe --sobject FlowToolKit__Form_Template_Page_Section__c --target-org <org-alias>`) and compare its fields with [references/properties.md](references/properties.md), the `Table_*` fields and the three form names above all. Leave out anything the org lacks and say which setting its version cannot hold.
3. **The Section Tag values** the org has (Data Conversion Tag(s)), for `--org-tags`.
4. **The decision**, from repeating-data or the person: the rows, the key columns, every question of one row, where it goes, the shapes, and whether a prefill flow fills it.

## 2. Two components: the table and the row form

| Component | Holds | Shape |
|---|---|---|
| **The table component** (root type `table`) | The key columns only: three or four fields that tell rows apart (First name, Last name, Email), with column widths in pixels | JSON on the section by default; a record component when reuse is known at design time |
| **The row form** | Every question of one row, in the order people answer them, with its required questions and rules | A **record component** (`<Name>_v0`) or an existing metadata component: the window loads it **by name**, so it is never JSON |

Both are built by **build-form-component**, on the same object (Form Submission on a page section, or the row object on a flow screen), headerless. The row form may reuse a component the form already has: the same Volunteer Details component can be a Field Set section for the main contact and the row form here. Recommend each shape with the reason and ask; never decide silently.

A table component can also name its own default row form inside its table section (`Default_Table_Form__c`); then the page section's row form is optional (`table.component_has_row_form`). Prefer setting it on the section, where the next person will look.

## 3. The spec

One JSON file per Table (`_forms/<slug>/repeating/<section>.json`), with the common keys from the shared standard and these:

| Key | What |
|---|---|
| `kind` | `table` |
| `table.row_form` | The row form by name. Required when New, Edit or Clone is on, unless `table.component_has_row_form` |
| `table.bulk_form` | Flow screen: the form for changing several selected rows at once |
| `table.bulk_edit` | Flow screen: turns on bulk edit (needs `bulk_form` and Edit) |
| `table.row_numbers`, `table.hide_column_headers`, `table.hide_footer`, `table.prevent_column_resize`, `table.disable_row_action_indicators` | Display switches (true or false) |
| `table.row_style` | `hideBorders`, `slds-table_striped` or `slds-table_col-bordered` |
| `actions.<name>.modal_title`, `.modal_subtitle` | The window's wording for New, Edit, Clone and Delete; `actions.delete.modal_body` the confirmation's message |

Invented example, a volunteer roster on an event sign-up form:

```json
{"kind": "table", "where": "section", "title": "Volunteer roster",
 "header": {"title": "Your volunteers", "subtitle": "Add each person who will help on the day."},
 "component": "Volunteer_Roster_Table_v0", "component_shape": "record",
 "rows": {"expected": 20}, "fields_per_row": 9,
 "actions": {"new": {"label": "Add", "modal_title": "Add a volunteer"},
             "edit": {"label": "Edit", "modal_title": "Volunteer details"},
             "delete": {"label": "Remove", "modal_title": "Remove this volunteer?"}},
 "prefill": {"planned": true, "section_tag": "Contacts"},
 "conversion": {"rule": "Contact1", "map_flow": "Default"},
 "table": {"row_form": "Volunteer_Details_v0"}}
```

## 4. Check, then write

```bash
python3 scripts/table.py check <spec.json> --org-tags Default,Contacts,Tasks,Cases,Opportunities
```

Fix every error; read every warning to the person when it changes what they will see. On top of the shared rules (component named or JSON, min and max, allowed labels, Section Tag for a planned prefill, conversion values), it fails a Table whose New, Edit or Clone has no row form, a row form given as JSON or equal to the table component, an unknown row style, and bulk edit without a bulk form. It warns when the decision rule points to a Repeater instead, when min or max are set (the Table does not enforce them), when display switches are set on a page section, and when a bulk form is set on a page section.

Then write it where it goes:

| Where | Command | Then |
|---|---|---|
| A page section in a planned form | `python3 scripts/table.py section <spec.json> --out <file>` | Put the keys on the section in `plan.json` (with `component` naming the table component's entry) and rebuild with build-template. Never edit a planned section by hand |
| An existing page section, no plan | `section --format record` (JSON for a connector update) or `section --format values` | Chat: update the section record through the connector. Claude Code: `sf data update record --sobject FlowToolKit__Form_Template_Page_Section__c --record-id <Id> --values "<output>" --target-org <org-alias>` |
| A screen flow | `python3 scripts/table.py flow-screen <spec.json> --out <file>` | Paste the `<fields>` element into the screen in the flow file, beside the rows' record collection variable (`flow.rows_variable`), then deploy. Inside a Flow Section, hand it to build-flow-section |

**The row form goes in two fields.** The form reads `Edit_FormQualifiedApiName__c`, while the Page Section Preview on a record page reads `Alternate_FormQualifiedApiName__c` (the package's own help text says the opposite). The script writes the same name into both, so both show the same window.

## 5. What a page section does not do (in the package version these notes were read from)

Say these plainly before the person relies on them:

- **Min and Max are not enforced** by the Table. If the count matters, use a Repeater, or check the count in the conversion.
- **The display switches** (row numbers, hidden headers and footer, column resize, row style, row indicators) are applied by the Page Section Preview only; the form itself shows default rows, and removed rows always disappear rather than staying marked. Set them if wanted, then check Preview Form.
- **Bulk edit** is never turned on for a page section, so a bulk form there is unused. Bulk edit, bulk delete and bulk reset are flow screen features.

## 6. Rows in and out

The same as a Repeater (shared standard): a prefill flow fills the rows by the Section Tag (hand it to **new-mapping-flow**); a Pre-fill Template seeds new rows; a saved row the person removes goes back flagged `IsDeleted` and the save deletes it; each row converts by the section's Conversion Rule and Conversion Map Flow, Default running the packaged flow for the rule. Rows live only in their own section.

On a flow screen: bind **Prefill Collection** to the rows variable; read **Insert**, **Update** and **Delete Collection** to save rows of the flow's own object; use **Active Row** or the Changed Trigger outputs for components that react while the person works.

## 7. Walk it

In the template's **Preview Form** (Reset Form Cache first if any metadata changed), at desktop and phone width:

1. The table shows the key columns only, readable at phone width.
2. New opens the row form with its title; every question is there, required ones enforced. Edit opens it with the row's answers. Clone copies a row.
3. Delete asks first, then the row disappears; save, and its submission is deleted.
4. With prefill, open the form from a record with related records: one line per record.
5. Open the record page's Page Section Preview too if people configure there, and compare.
6. For a public form, open it as a guest: the table component and the row form must both load.

A Table is built when this walk passes.

## Traps

| Trap | What to do |
|---|---|
| New or Edit opens an empty window | No row form: set `table.row_form` (both row form fields) or the table component's default row form |
| The row form given as JSON | The window loads by name only. Build it as a record component |
| The table component used as the row form | The window then shows only the key columns. The row form is its own form component with every question |
| Row numbers, row style or hidden headers do not show on the form | Applied only by the Page Section Preview in this package version. Check Preview Form, and tell the person |
| A maximum that does nothing | The Table does not enforce Min or Max. Use a Repeater for a hard limit |
| Bulk edit missing on a page section | Not offered there. Use a flow screen, or edit rows one by one |
| `enableFilter` set to "false" still shows the filter | It is a text input; any value turns it on. Leave it out to keep it off |
| Every question as a column | A wide table nobody can read on a phone. Three or four key columns; the rest in the row form |
| A section tag the org lacks | A restricted picklist: add the value to Data Conversion Tag(s) first |
| A planned section edited in Form Builder | The next build-template rebuild replaces it. Change the spec, then the plan, then rebuild |

## Done when

- The decision and both components' shapes were recommended with the reason and answered; the row form is a named component.
- `scripts/table.py check` reports no errors and every warning was read to the person.
- The settings are in `plan.json` and rebuilt, on the section record, or in the flow, and the org's own Table property list had every field used.
- Prefill and conversion are handed to new-mapping-flow when planned, with the Section Tag.
- The Preview Form walk passed: New, Edit and Clone open the full row form, and a removed saved row is deleted.
