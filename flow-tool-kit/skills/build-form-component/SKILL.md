---
name: build-form-component
description: Not a front door: when ftk-start has not run in this conversation, load ftk-start first and let it route here. Use when a Flow Tool Kit Form Component has to be chosen, designed or written: a reusable block of questions or display content such as contact details, the fields of one household member (which a Repeater section repeats), a table, a survey or Likert grid, a consent or a header, including every shared, extended or metadata component build-template hands over from plan.json. Builds all three shapes (a metadata component, a record component, or JSON fixed to one section, flow or page) and recommends which, with the reason. Also for "can we build a form component?", "make this a reusable block", extending an existing component ("add a County field to our address component"), Form Template Mapping for a Contact or Account form, or component JSON or custom metadata for a form.
---

# Build Form Component

A Form Component is a reusable block of questions that belong together, or of design and display content: Contact Details, Mailing Address, one Household Member, Program Feedback, a header. A **table** is also a form component, stored the same way in metadata, as a record or as JSON; it renders through the Table component instead of the Flow Form component. A **Repeater is not a component**: it is a Form Template page section type, and a flow screen component, that repeats a form component row by row; its settings (minimum and maximum rows, the actions and their labels) live on the section or the screen, never in the component. It is built once, named for its purpose, and placed in the page sections of many Form Templates (a Form Template is one whole form; reuse is always of components, never of templates). This skill decides where a component's boundaries are, picks an existing component before building a new one, recommends its **shape** and asks, and writes it in that shape: a **metadata component** (custom metadata, deployed and version controlled), a **record component** (a Form Component record built as data in the org) or **JSON** fixed to one section, flow or page. Every shape carries its conditional logic, option labels, preset amounts and every rule and section labelled in plain words.

**Called by** build-template for every section whose plan decision is `shared-new` or `extend`, for every metadata-shaped component the plan names (`action: build metadata`), and directly when someone asks for a component. **Reads** org-catalog's `catalog.json`, form-design's `plan.json` and the project's `flow-tool-kit.json`. **Hands off** a section that needs a flow to build-flow-section and one that needs custom code to build-custom-lwc.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat with a Salesforce connector | Read the catalog, design the component, write its JSON and run `scripts/component.py check` in the code sandbox. **Form Component records are written from that JSON**: when the connector can run anonymous Apex, call the package's import (below); otherwise hand the person the JSON file to paste into **Form Components, Import Form Component**. Both create or update the record with its sections, fields and rules. |
| claude.ai chat, no connector | Everything up to the checked JSON file; the person imports it. |
| Claude Code, local or on the web | Everything above, plus custom metadata: `scripts/component.py cmt` writes the record files and `sf project deploy start` deploys them. |

**Custom metadata needs Claude Code.** A metadata component is files deployed with the Salesforce CLI from a project folder; chat has neither. When the person asks for metadata and you are in chat, say so in one line and ask: build it as a record component now (shared the same way, just not version controlled or deployed with the project), or wait and build the metadata component in Claude Code.

**Never create a `Form_Component__c` row on its own** (a plain record create through a connector or the API). Its sections, fields and rules live on protected child objects only the package can write, so a bare row renders nothing. Always go through the package's import:

```apex
Id componentId = FlowToolKit.FormComponentImport.createRecordComponent(componentJson);
```

It is all or nothing. Rerunning it with the same API name changes the component in place (same Id) and every template that uses it, which is "update the shared component", never what extend means. The running user needs Form Builder (Administrator), or Form Builder (Manager) and to be listed in the component's Form Managers. Details: [references/record-path.md](references/record-path.md).

## Before authoring

1. **The project config.** Read `flow-tool-kit.json` ([_shared/standards/project-config.md](_shared/standards/project-config.md)): the org's Id, its **edition** (paid or free) and its catalog file. No edition saved: ask the one question ftk-start asks ("Is this org on the paid or the free Flow Tool Kit edition?") and save the answer.
2. **The catalog.** Read org-catalog's `catalog.json` (`ftk-catalog/<org Id>/catalog.json`). If org-catalog's `check` reports it stale (older than 24 hours) or for another org, run org-catalog again first. No org connected: say so in one line; every component is then new, and nothing is written to an org.
3. **The reuse question, by name, never silently.** For each block you are about to build, look for an existing component on the same object with most of the same fields, or the same purpose (org-catalog's `match` command does this against a plan or a list of sections). When one matches, ask, naming it, its fields and where it is used: *"Household Contact (Contact, used on 3 templates) lacks Preferred Language. Extend it (a new version of Household Contact with that field; the original and every place it is used stay as they are), reuse it as is, or build a new component?"* Ask every match in one message, each with your recommendation, and with the shape question for anything extended or new (step 4). When `plan.json` already records the answers (`catalog_match` with `asked`, `shape` with `shape_asked`), follow them and do not ask again.
   - **Reuse**: the section uses the component as it is.
   - **Extend**: a **new version** under its own name: the component copied as it is, plus the added fields. The original is never changed, so every template and component that uses it keeps working as before. This works for packaged components too.
   - **New**: a component built for this need.
   - **Update the shared component** is a different action, never offered as the default and never assumed from "extend": the original itself changes, in place, and so does every template and form that uses it. Offer it only when the change belongs to everyone who uses the component, in its own question that lists every template and component it would reach (the catalog's "used in" lists): *"Update the shared Household Contact in place? It would change Volunteer Sign-up, Garden Plot Application and the Family Profile component."* No answer means no update. A packaged component can never be updated.
4. **The shape, recommended and asked, never decided silently** (next section). Reuse and update keep the component's own shape; extend and new need the person's answer.
5. **The source of truth.** The section in `plan.json` (fields, controls, widths, options, conditions, `form_template_mapping`), or form-migrate's `ir.json` when there is no plan. Never re-read the original source form: the plan is what the reviewer saw.
6. **The standards.** [Component shapes](_shared/standards/component-shapes.md), [mapping preference](_shared/standards/mapping-preference.md), [documentation and naming](_shared/standards/documentation.md), [form-type rules and house rules](_shared/standards/form-type-rules.md). The worked example is [_shared/examples/form-3-page-release/](_shared/examples/form-3-page-release/).

## The boundary, the edition, the shape and the JSON

Before authoring any component, read [references/boundary-shape-and-json.md](references/boundary-shape-and-json.md) (Decide the boundary, Where the answers land: the edition decides, Pick the shape: metadata, record or JSON, Author the JSON, Sections that need a flow or custom code).

## Checking, traps and common mistakes

Before writing a component to the project or the org, and when one misbehaves, read [references/check-traps-and-mistakes.md](references/check-traps-and-mistakes.md) (Check, write, verify, What a reviewed design can promise, Traps, Common mistakes).

## Done when

- Every catalog match was asked by name and answered; nothing reused, extended or duplicated silently. Every new or extended component's shape was recommended with its reason, asked and answered, and the component was built in that shape. Every extend produced a new version and left the original untouched; a shared component was changed in place only after its own question, listing everything it reaches, was answered yes.
- The component sits on the right object for the edition, and on a paid org its Form Template Mapping covers every field that feeds the conversion.
- `scripts/component.py check` reports no errors; the component, every section and every rule carry plain-words labels and a description to the standard.
- Fields were deployed before the component; the component is written, read back, bound and walked in Preview Form, every rule both ways.
- Flow Sections and custom LWCs are named for build-flow-section and build-custom-lwc.

