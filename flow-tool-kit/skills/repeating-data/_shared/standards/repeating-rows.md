# Repeating rows: Repeaters and Tables

What every skill that builds repeating data follows: repeating-data decides, build-repeater and build-table build. It states the rules once; each build skill's `references/properties.md` lists every property in full. Read from the Flow Tool Kit package source (the page section editor, the form's section renderer, the repeater and table components, the save flow and the Prefill From Mapped Record action). Where the package's own field help says something different, this page says what the code does.

## What a Repeater and a Table are

- A **Repeater is not a component.** It is a page section type (`Component_Type__c` `Repeater`) and a flow screen component (**Form (Repeater)**) that repeats one form component, row by row, every question of the row on the page.
- A **Table is a form component** (root `type` `table`), rendered through the Table component: a page section of type `Table`, or the **Form (Table)** flow screen component. The table shows a few key columns; New and Edit open a window with the row's form.
- The repeated component, the table component and the Table's row form are built by **build-form-component**. Their settings (minimum and maximum rows, the actions and their labels, spacing, the row form) live on the section or the screen component, never in the component.

## The row component's shape

1. **JSON on the section** by default: the questions are fixed to this section and nothing else can change them.
2. A **record component** (`<Name>_v0`) when reuse is known at design time. Example: a Contact block asked once as "Who is your main support contact?" and again inside a Repeater for additional contacts. One component, both places reference it, one change reaches both.
3. **Metadata** only later, through convert-to-metadata, once the form is final.

One exception, from the package: a Table's **row form** (the New and Edit window) and a flow repeater's **edit form** are loaded by name only. They are a record component or an existing metadata component, never JSON.

## Rows live in their own section

- On a Form Template every row is its own Form Submission, a child of the main submission, stamped with its own section. A section shows and saves only the rows stamped with it.
- A section never shows, reads or links to another section's rows. Two sections that need the same people are two sets of rows, each filled by its own prefill and converted by its own rule.
- In a screen flow the rows are a record collection the flow owns: the component's **Prefill Collection** goes in and comes back changed.

## Minimum and maximum rows

| Setting | Repeater | Table |
|---|---|---|
| `Min__c` (section), `min` (flow) | That many empty rows are created when there are none, and Delete is not offered at the minimum | Passed to the table but not enforced by it in the package version these notes were read from |
| `Max__c` (section), `max` (flow) | New, Clone and Import stop at the maximum. Prefilled rows beyond it are paged, not dropped | Same as Min: passed, not enforced |
| Not set | A new page section takes the field defaults, Min 1 and Max 5; the flow component's defaults are the same. A `Max__c` of 0, or one cleared on a saved section, is read as 10 on a page section; a `max` of 0 on a flow screen is read as 5. A blank `Min__c` on a saved section is 0 | No effect |

Rules every build checks: both are whole numbers from 0 to 999 (the fields hold three digits), the minimum is never above the maximum, and a Repeater sets both on purpose rather than taking the defaults. A minimum of 1 or more starts the section with that many empty rows; use 0 when the rows are optional. When a Table's count must be limited, say so plainly: use a Repeater, or check the count in the conversion.

## Actions and their labels

| Action | Switch (section) | Label field (section) | Allowed labels | Flow screen |
|---|---|---|---|---|
| New | `Enable_New_Action__c` | `New_Action_Button_Label__c` | New, Add, Create, Insert | `allowNew`, `newButtonLabel` (any text) |
| Edit | `Enable_Edit_Action__c` | `Edit_Action_Button_Label__c` | Edit, Update, Change | `allowEdit`, `editButtonLabel` |
| Clone | `Enable_Clone_Action__c` | `Clone_Action_Button_Label__c` | Clone, Copy, Duplicate | `allowClone`, `cloneButtonLabel` |
| Delete | `Enable_Delete_Action__c` | `Delete_Action_Button_Label__c` | Delete, Remove, Clear | `allowDelete`, `deleteButtonLabel` |

- Every switch is off by default. A label applies only when its switch is on.
- On a section, a label is one of the allowed values: the page section editor offers only those, so another value cannot be kept in Form Builder.
- **Edit on a Repeater page section has no effect**: the section never hands the repeater an edit form, and the repeater shows Edit only when it has one. Rows are edited in place. Edit belongs to Tables, and to a flow repeater given `editFormQualifiedApiName`.
- **A Table needs a row form for New, Edit and Clone**: the page section's row form, or the table component's own default row form. Without either the window opens with nothing to fill in.

## Prefill: rows in

- **Section Tag** (`Section_Tag__c`) is a section's stable identifier. A prefill flow's **Form Submission | Prefill From Mapped Record** action in **Related Records** mode takes the source records and the tag, and returns one row per record for that section. The tag is a restricted picklist sharing the **Data Conversion Tag(s)** value set (Default, Contacts, Tasks, Cases and Opportunities as shipped; add a value in Setup, Picklist Value Sets, before using it). Each tag is used once per Form Template; the package refuses a second section with the same tag.
- Set a Section Tag on every Repeater or Table section a prefill flow will fill. Without one the action has no section to fill and reports it.
- Related Records mode fills only a section whose component is on the source record's object with a Form Template Mapping (paid edition). On the free edition, or for anything the map cannot say, the prefill flow builds the rows itself. Either way the flow returns them in its `prefillRelatedRecords` output. **new-mapping-flow** builds the prefill flow.
- **Pre-fill Template** (`Prefill_Template__c`): a Form Submission marked as a prefill template whose values seed every new row (defaults such as a relationship or a role). It is not a source of rows. A guest needs read on that record, or the form reports that its defaults could not be loaded.
- In a screen flow: rows in through **Prefill Collection** (`prefillRecords`), defaults for new rows through **Record** (`recordTemplate`).

## Saving and deleting: rows out

- A saved row (it has an Id) that the person removes stays in the collection with `IsDeleted` set to true. A row never saved (no Id) is simply dropped.
- The save flow (**Form Submission Upsert**, its **Filter (Delete Records)** step) deletes only the rows flagged `IsDeleted`. A row left out of the collection is never deleted, and the record it converted to stays.
- Any logic of your own that removes rows (a Flow Section, a custom component) flags them before leaving them out; build-flow-section's scaffold does this.
- In a screen flow the component also returns **Insert Collection**, **Update Collection** and **Delete Collection**, for a flow that saves records of its own object directly.

## Conversion: one setting per section

Only Repeater and Table sections have these, because only their rows convert one by one. **new-mapping-flow** decides and builds what they point at; the build skills only set what it decided.

| Field | What |
|---|---|
| `Conversion_Rule__c` | What each row converts into: Bypass (the default, no conversion), Contact1, Contact2 (each also with Set Mailing Address and Set Other Address), Lead1, Lead2, Case |
| `Conversion_Map_Flow__c` | The flow for this section's rows. Dependent on Conversion Rule. **Default** runs the packaged default flow for the rule, not the template's own Conversion Map Flow. Any other value is a flow's API name, added to the picklist and included under the rule (new-mapping-flow's wiring check) |
| `FlowApiName_Related__c` | Read-only: the flow the rows will run, resolved from the two above |
| `Add_to_Account__c`, `Add_to_Campaign__c` | Link each converted Contact to the converted Account; add each converted Contact or Lead to the submission's Campaign |
| `Contact_Matching_Rules__c`, `Lead_Matching_Rules__c` | Matching rules used to find existing records for the rows. Blank checks every active rule; the section never inherits the template's |
| `Update_Most_Confident_Contact__c`, `Update_Most_Confident_Lead__c` | With several matches, update the most confident one instead of stopping for a person to choose |
| `Contact_Record_Type__c`, `Case_Record_Type__c` | Record type for records created from the rows |
| `Data_Conversion_Tag_s__c` | Tags stamped on each row for your own record-triggered flows; no packaged flow reads them |

A Conversion Map Flow other than Default under Bypass converts nothing: set the rule first.

## Where they go

| Place | How it is built |
|---|---|
| A Form Template page section | The section's fields, written into `plan.json` for build-template (which keeps them on every rebuild), or onto an existing section record. Rows are Form Submissions |
| A screen flow | The **Form (Repeater)** or **Form (Table)** component on a screen, with its properties as input parameters. Rows are any object the flow passes. Inside a Flow Section, build-flow-section owns the screen and its contract variables |

## The build spec

build-repeater and build-table read one JSON spec per Repeater or Table, kept beside the form's plan (`_forms/<slug>/repeating/<section>.json`). repeating-data writes it from the answers; each build skill's page lists the keys only its kind has. The keys both read:

| Key | What |
|---|---|
| `kind` | `repeater` or `table` |
| `where` | `section` (a Form Template page section, the default) or `flow-screen` |
| `title` | The section's name in Form Builder (`Title__c`) |
| `header` | `{title, subtitle, icon, text, show}`: the section's header, or the flow component's header |
| `component` | The repeated component (Repeater) or the table component (Table) by name: a record component as `<Name>_v0`, a metadata component by its name |
| `component_json` | Or the component's JSON, fixed to this section or screen |
| `component_shape` | `json`, `record` or `metadata`, as asked (shape rule above); `component_id` the record component's Id; `component_exists` true when reusing a metadata component |
| `rows` | `{min, max, expected}`: the limits, and how many rows people usually have |
| `fields_per_row` | How many questions one row asks; with `rows.expected` and `condensed` it feeds the decision rule |
| `condensed` | true when the section must stay compact |
| `actions` | `{new, edit, clone, delete}`: each `true`, `false`, a label, or an object (`label`, and the window's `modal_title` and `modal_subtitle` for a Table or a flow Repeater's Edit, plus `modal_body` for a Table's Delete) |
| `prefill` | `{planned, section_tag, template}`: a prefill flow will fill the rows, by this Section Tag; `template` the Pre-fill Template record's Id |
| `conversion` | `{rule, map_flow}` plus any of `add_to_account`, `add_to_campaign`, `contact_matching_rules`, `lead_matching_rules`, `update_most_confident_contact`, `update_most_confident_lead`, `contact_record_type`, `case_record_type`, `data_conversion_tags` (page sections only) |
| `bottom_margin` | Space below the section, `slds-m-bottom_none` to `slds-m-bottom_xx-large` |
| `extra` | Any other page section field by its API name, checked against the kind's property list |
| `flow` | For `flow-screen`: `element_name` (the component's API name on the screen), `object` (the rows' object; Form Submission when blank), `rows_variable` (the record collection bound to Prefill Collection), `new_row_variable` (the record bound to Record, seeding new rows), and `properties` (any other input property by name; a flow resource as `{"ref": "<name>"}`) |

Each script's `check` runs every rule on this page before it writes anything; `section` and `flow-screen` refuse a spec with errors.
