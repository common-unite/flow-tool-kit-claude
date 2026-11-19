---
name: build-repeater
description: Not a front door: when ftk-start has not run in this conversation, load ftk-start first and let it route here. Use when a Flow Tool Kit Repeater has to be built or changed, on a Form Template page section or as a Form (Repeater) component on a screen flow, after repeating-data chose a Repeater or when someone asks for one directly ("let people add up to four household members", "make this section repeat"). Sets the minimum and maximum rows, the New, Clone and Delete actions and their labels, row spacing and the divider, the Pre-fill Template, the Section Tag a prefill flow fills, the conversion setting and the header, checks them against the package's property list, and writes them into plan.json, onto an existing section, or as the flow screen component.
---

# Build Repeater

A **Repeater is not a component.** It is a Form Template page section type, and a flow screen component (**Form (Repeater)**), that repeats one form component row by row, with every question of the row on the page. This skill sets the Repeater's own settings and writes them where they belong. The row's questions are a form component, built by **build-form-component**; the rows' prefill and conversion are flows, built by **new-mapping-flow**.

**Called by** repeating-data (after the person chose a Repeater), build-template's report (a section marked Repeater), and directly. **Hands off** the row component to build-form-component, the prefill flow and any custom row conversion to new-mapping-flow, and a Repeater inside a Flow Section to build-flow-section.

Read first, beside this file:
- [_shared/standards/repeating-rows.md](_shared/standards/repeating-rows.md): the rules both build skills follow (shape of the row component, rows in their own section, minimum and maximum, labels, prefill, deleted rows, conversion) and the spec's common keys.
- [references/properties.md](references/properties.md): every page section field and every flow screen property a Repeater uses, what it does and when to set it.
- Plugin standards: [_shared/standards/documentation.md](_shared/standards/documentation.md) (section 6 is Naming), [_shared/standards/component-shapes.md](_shared/standards/component-shapes.md), [_shared/standards/project-config.md](_shared/standards/project-config.md).

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat, no connector | Write the spec, run `scripts/repeater.py check`, `section` and `flow-screen` in the code sandbox, and hand over the files |
| claude.ai chat with a Salesforce connector | The above, plus read the org's section fields (a describe or a FieldDefinition query), and update an existing page section record with the `record` output. A flow file still needs Claude Code to deploy |
| Claude Code, local or on the web | Everything: the org's describe, `sf data update record` for an existing section, build-template's rebuild for a planned one, and deploying a flow that carries the component |

## 1. Read before building

1. **The project config** (`flow-tool-kit.json`): the org, its edition and its audiences. Guests need read on a Pre-fill Template record and on record components (a guest sharing rule on Form Component, record type Record Component).
2. **The org's property list, once per org.** Describe `FlowToolKit__Form_Template_Page_Section__c` (connector, or `sf sobject describe --sobject FlowToolKit__Form_Template_Page_Section__c --target-org <org-alias>`) and compare its fields with [references/properties.md](references/properties.md). A field the org lacks (an older Flow Tool Kit) is left out of the spec, and the person is told which setting their version cannot hold. For a flow screen, the component's properties are in the same file.
3. **The Section Tag values** the org has: the Data Conversion Tag(s) picklist value set. Pass them to the check with `--org-tags` so a tag the org lacks fails before the build, not during it.
4. **The decision.** From repeating-data, or from the person: the rows, the questions in one row, where it goes, the row component's shape, and whether a prefill flow fills it.

## 2. The row component

The row is one form component with every question of one row; never split a row across components. Its shape follows the rule in the shared standard, and is **recommended with the reason and asked**, never decided silently:

- **JSON on the section** by default (`component_json`, `component_shape: json`).
- A **record component** (`<Name>_v0`) when reuse is known at design time: "Main support contact" asked once as a Field Set section and again inside the "Additional contacts" Repeater is one Support Contact component both reference.
- **Metadata** later, through convert-to-metadata.

A new or extended component is built by **build-form-component** first, headerless (the header lives on the section), with its required questions and its rules inside it. A Repeater with a header hidden and no rows shows a start bar with New (and Import on a flow screen), so a hidden header is fine.

## 3. The spec

One JSON file per Repeater (`_forms/<slug>/repeating/<section>.json`), with the common keys from the shared standard and these:

| Key | What |
|---|---|
| `kind` | `repeater` |
| `repeater.record_spacing` | Space above every row: none, xxx-small, xx-small, x-small, small, medium, large, x-large, xx-large |
| `repeater.hide_divider` | true hides the line between rows |
| `flow.edit_form` | Flow screen only: the edit window's form by name, needed for Edit to show |

Invented example, a garden plot application asking for additional contacts:

```json
{"kind": "repeater", "where": "section", "title": "Additional contacts",
 "header": {"title": "Additional contacts", "subtitle": "Anyone else we may call about your garden plot."},
 "component": "Support_Contact_v0", "component_shape": "record",
 "rows": {"min": 0, "max": 4, "expected": 2}, "fields_per_row": 5,
 "actions": {"new": "Add", "delete": "Remove"},
 "prefill": {"planned": true, "section_tag": "Contacts"},
 "conversion": {"rule": "Contact1", "map_flow": "Default", "add_to_account": true},
 "repeater": {"record_spacing": "small"}}
```

## 4. Check, then write

```bash
python3 scripts/repeater.py check <spec.json> --org-tags Default,Contacts,Tasks,Cases,Opportunities
```

Fix every error; read every warning to the person when it changes what they will see. The check enforces the shared rules: the component is named or given as JSON, min and max are whole numbers from 0 to 999 with min never above max (and both set on purpose), every label is one the section editor offers (New, Add, Create, Insert; Clone, Copy, Duplicate; Delete, Remove, Clear), a planned prefill has a Section Tag the org has, a Conversion Map Flow is never set under Bypass, and every extra property is one the package has. It warns when the decision rule points to a Table instead, and when Edit is turned on for a page section (it has no effect there: rows are edited in place).

Then write it where it goes:

| Where | Command | Then |
|---|---|---|
| A page section in a planned form | `python3 scripts/repeater.py section <spec.json> --out <file>` | Put the keys on the section in `plan.json` (with `component` naming the row component's entry) and rebuild with build-template, which keeps them on every rebuild. Never edit a planned section by hand: the next rebuild replaces it |
| An existing page section, no plan | `section --format record` (JSON for a connector update) or `section --format values` | Chat: update the section record with the JSON through the connector. Claude Code: `sf data update record --sobject FlowToolKit__Form_Template_Page_Section__c --record-id <Id> --values "<output>" --target-org <org-alias>` |
| A screen flow | `python3 scripts/repeater.py flow-screen <spec.json> --out <file>` | Paste the `<fields>` element into the screen in the flow file, beside a record collection variable named in `flow.rows_variable` (and a record for `flow.new_row_variable`), then deploy. Inside a Flow Section, hand it to build-flow-section, which owns the screen and its contract variables |

On a flow screen: bind **Prefill Collection** to the rows variable so rows survive Back; read **Insert**, **Update** and **Delete Collection** when the flow saves rows of its own object; for Form Submission rows, pass the rows variable to the packaged save flow's `relatedRecords`, which deletes rows flagged `IsDeleted`. Set Edit only with `flow.edit_form`, and never mix **Form (Repeater) Configuration** with individual properties: when it is set it replaces them all.

## 5. Rows in and out

- **Prefill.** A prefill flow fills the rows by the section's Section Tag (Prefill From Mapped Record, Related Records mode). Hand the flow to **new-mapping-flow** with the tag and the source records; it also hands the flow to flow-access-fix. Defaults for new rows come from the Pre-fill Template (`prefill.template`), not from a flow.
- **Saving.** A saved row the person removes goes back flagged `IsDeleted`, and the save deletes it. Anything of your own that removes rows flags them the same way.
- **Conversion.** Each row converts by the section's Conversion Rule and Conversion Map Flow. Default runs the packaged flow for the rule; a custom flow is built and wired by **new-mapping-flow** first, then named here.
- Rows live only in their own section. Two sections that need the same people each get their own rows and their own prefill.

## 6. Walk it

In the template's **Preview Form** (Reset Form Cache first if any metadata changed), at desktop and phone width:

1. The section starts with `min` rows (none when min is 0, then a start bar or New in the header).
2. Add rows up to `max`: New and Clone disappear at the limit. Delete disappears at `min`.
3. With prefill, open the form from a record that has related records: each one is a row, and more than `max` are paged, not lost.
4. Save, remove a saved row, save again: the row's submission is deleted, and after conversion the record it made is handled by the conversion rule.
5. For a public form, open it as a guest: the row component and the Pre-fill Template must both load.

A Repeater is built when this walk passes, not when the record saved.

## Traps

| Trap | What to do |
|---|---|
| Max left blank | The Repeater takes the default (5 on a new section, 10 once cleared on a saved one). Set min and max on purpose |
| Min 1 on optional rows | It starts the section with one empty row. Use 0 |
| Edit turned on for a page section | No Edit button appears. Rows are edited in place; a row that needs a window is a Table |
| A label typed outside the allowed values | Form Builder cannot keep it. Use New, Add, Create, Insert; Clone, Copy, Duplicate; Delete, Remove, Clear |
| A prefill flow fills nothing | The section has no Section Tag, the tag is not the one the flow passes, or the row component has no Form Template Mapping to the source object. The action's Skipped Mappings output says which |
| A section tag the org lacks | A restricted picklist: add the value to Data Conversion Tag(s) first |
| A removed row comes back after saving | Something removed it from the collection instead of flagging `IsDeleted` |
| A Repeater left on Default ignores the template's custom Contact flow | Default runs the rule's packaged flow. Name the custom flow in the section's Conversion Map Flow |
| A planned section edited in Form Builder | The next build-template rebuild replaces it. Change the spec, then the plan, then rebuild |
| Form (Repeater) Configuration and individual properties together | The configuration wins and every individual property is ignored |

## Done when

- The decision and the row component's shape were recommended with the reason and answered.
- `scripts/repeater.py check` reports no errors and every warning was read.
- The settings are in `plan.json` and rebuilt, on the section record, or in the flow, and the org's own property list had every field used.
- Prefill and conversion are handed to new-mapping-flow when planned, with the Section Tag.
- The Preview Form walk passed, including a removed saved row being deleted.
