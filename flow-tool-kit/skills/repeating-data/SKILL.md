---
name: repeating-data
description: Not a front door: when ftk-start has not run in this conversation, load ftk-start first and let it route here. Use when a Flow Tool Kit form or screen flow must collect several of the same thing (household members, additional contacts, emergency contacts, volunteers, line items, references, shifts) and nobody has decided yet how: "let parents add more than one emergency contact", "families list everyone in the household", "should this be a repeater or a table". Recommends a Repeater or a Table with the reason, settles where it goes (a Form Template page section or a screen flow), the row component's shape, and the rows in and out (prefill by Section Tag, saving, conversion), then hands off to build-repeater or build-table.
---

# Repeating Data

When a form needs several of the same thing, there are two ways to show it, and each is its own build skill:

- A **Repeater** (build-repeater) repeats one form component row by row, every question on the page. It is not a component: it is a page section type and a flow screen component.
- A **Table** (build-table) is a form component that shows a few key columns, one line per row; New and Edit open a window with every question of the row.

This skill decides between them with the person, settles the questions both builds need answered, writes the build spec, and hands off. It builds nothing itself. The rules both builds follow are in [_shared/standards/repeating-rows.md](_shared/standards/repeating-rows.md); read it first.

**Called by** form-design, form-migrate and build-template (a plan with a repeating field or section), ftk-start, and directly. **Hands off** to build-repeater or build-table, which hand the components to build-form-component and the flows to new-mapping-flow.

## 1. Listen for the outcome

Ask what the person wants to happen, not which component they want: who fills it in, what they list, how many they usually have, what each one needs, and what happens to the rows afterwards. Pull these out, and confirm them rather than asking again when the plan or the conversation already says them:

| Need | Ask, in their words |
|---|---|
| How many rows | "How many do people usually list? What is the most?" |
| How much per row | "What do you need to know about each one?" Count the questions |
| What shows at a glance | "Which two or three details tell them apart?" (the key columns, for a Table) |
| Where | "Is this part of a form people fill in (a Form Template), or a step in a flow you are building?" |
| Rows in | "Should the form start with ones you already have on file?" |
| Rows out | "What should each one become in Salesforce: a Contact, a Lead, a Case, or nothing?" |
| Reuse | "Is the same set of questions asked anywhere else, on this form or another?" |

## 2. Recommend a Repeater or a Table, with the reason, then ask

The rule:

- **A Repeater** for a handful of questions and only a few rows: every question stays on the page, row by row, and nothing opens.
- **A Table** when there are many rows (about 5 or more) or many questions per row (about 8 or more): the table shows just the key columns, and each row's Edit opens a window with all the questions.
- **A Table also keeps a section compact**, even with few rows, when the page is already long.

Say the recommendation and the reason in one message, name the alternative, and ask. Never build without the answer. Examples (invented):

> Each household lists two or three children, and you need name, birthdate, school and grade for each. I recommend a **Repeater**: four questions, a few rows, everything on the page as they type. A Table would hide the questions behind an Edit window. Repeater or Table?

> The event needs up to 20 volunteers, each with first name, last name, email, role, title, T-shirt size, availability and two demographic questions. I recommend a **Table**: it shows First name, Last name and Email for all 20 on one screen, and each row's Edit opens a window with the other questions. A Repeater would be a scroll of 20 full forms. Table or Repeater?

> Only two references, but each has eight questions and the page already has three sections. I recommend a **Table** to keep the page compact: Name and Relationship as columns, the rest in the window. A Repeater shows everything at once if you prefer. Table or Repeater?

The build scripts apply the same rule as a second opinion: a spec whose kind goes against it gets a warning, kept only when the person chose it.

## 3. Settle the rest

**Where it goes.**
- A **Form Template page section** (`Component_Type__c` Repeater or Table): rows are Form Submissions, children of the main submission, and the section carries every setting.
- A **screen flow component** (Form (Repeater) or Form (Table)): rows are any object the flow passes as a record collection, and the flow saves them. Inside a Flow Section, build-flow-section owns the screen.

**The row component's shape** (the shared standard, and [_shared/standards/component-shapes.md](_shared/standards/component-shapes.md)). Recommend with the reason, then ask:
- **JSON on the section** by default.
- A **record component** when reuse is known now. Example: a Contact block asked once as "Who's your main support contact?" and again inside a Repeater for additional contacts is one component both reference.
- **Metadata** only later, through convert-to-metadata.
- A Table needs two components: the table (key columns) and the **row form** (every question). The row form is loaded by name, so it is a record or metadata component, never JSON.

**Rows in.** A prefill flow fills the rows by the section's **Section Tag**; ask for the tag now (a Data Conversion Tag(s) value, unique within the template). Defaults for each new row come from a Pre-fill Template record, not a flow.

**Rows out.** Removed saved rows are flagged `IsDeleted` and deleted on save. Each row converts by the section's **Conversion Rule** and **Conversion Map Flow**, set only on Repeater and Table sections; Default runs the packaged flow for the rule. A custom row flow comes from new-mapping-flow.

**Own rows only.** Each Repeater or Table holds its own rows; a section never shows or links to another section's rows. Two places that need the same people are two sets of rows, each with its own prefill.

## 4. Write the spec and hand off

Write `_forms/<slug>/repeating/<section>.json` with the common keys from the shared standard (`kind`, `where`, `title`, `header`, `component` or `component_json`, `component_shape`, `rows`, `fields_per_row`, `condensed`, `actions`, `prefill`, `conversion`, `flow`), then hand off:

| Chosen | Next |
|---|---|
| A new or extended row component, table component or row form | **build-form-component** first, in the shape chosen |
| A Repeater | **build-repeater**, with the spec |
| A Table | **build-table**, with the spec |
| Prefill by Section Tag, or a custom conversion flow for the rows | **new-mapping-flow**, with the tag and the rule |
| A screen inside a Flow Section | **build-flow-section**, with the component the build skill writes |

A form-design `plan.json` field with control `Repeater` (`repeater.columns`, `newButtonLabel`, `max`) becomes a spec this way: its columns are the row's questions (or a Table's key columns and row form), `newButtonLabel` is `actions.new`, and `max` is `rows.max`. The section then carries `Component_Type__c` from the build skill's output, which build-template builds and keeps on rebuild.

## Done when

- The outcome was heard and confirmed: rows, questions per row, key columns, where, rows in and out, reuse.
- A Repeater or a Table was recommended with the reason and the person answered; so were the shapes.
- The spec is written and handed to the build skill, with build-form-component and new-mapping-flow named for what they own.

## Common mistakes

| Mistake | Instead |
|---|---|
| Asking "Repeater or Table?" with no recommendation | Recommend one with the reason, then ask |
| A Repeater for 20 people | A Table with key columns; each row opens a window |
| Every question as a Table column | Three or four key columns; the rest in the row form |
| A Table's row form as JSON | A record component, loaded by name |
| Treating a Repeater as a component | The component is the row; the Repeater is the section or screen that repeats it |
| One section reading another section's rows | Each section has its own rows and its own prefill |
| Leaving removed rows out of the collection | Flag them `IsDeleted` so the save deletes them |
| A shared record component on a guess | JSON on the section unless reuse is known now |
