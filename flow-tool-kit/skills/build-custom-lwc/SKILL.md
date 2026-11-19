---
name: build-custom-lwc
description: Use when a Flow Tool Kit form section needs behavior no native control or Flow Section can give, such as a live total or fee as the person types, a calculator display, a picker or widget the package has no control for, or a custom way to manage child rows, and a custom Lightning web component must be built for it. Also for every custom-lwc section build-template, form-design, form-migrate or build-form-component hands over, and when someone asks to build, fix or restyle a component for a Form Template page section or a Form Component section.
---

# Build Custom LWC

Some sections need behavior Flow Tool Kit's controls and a Flow Section cannot give well: a fee that updates as the person types, a calculator display, a widget the package has no control for, a custom way to add and remove child rows. This skill builds a Lightning web component for such a section on Flow Tool Kit's section contract, matched to the form's styles, tested, deployed and placed.

**Called by** build-template for each `build-custom-lwc` entry in its `handoffs`, after the template is built; form-design, form-migrate and build-form-component name the same sections (`decision: custom-lwc`). Also directly: "build a component that shows the membership fee as they type". **Reads** `plan.json` (the section and its questions), the handoff (section title, component name, what it does) and the project's `flow-tool-kit.json`. **Hands off** the section's questions to build-form-component and guest access to flow-access-fix.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat, with or without a Salesforce connector | Decide the design, write every file of the bundle, its Jest test and its metadata, run `scripts/check_lwc.py` in the code sandbox, and print the section values with `scripts/point_section.py` (no `--org`) for the connector to save. Then hand the files over |
| Claude Code, local or on the web, with the Salesforce CLI | Everything, including Jest, the deploy and the checks in the org |

**Deploying a Lightning web component needs Claude Code.** Say so plainly in chat, in one line, before you start writing files: chat can build the component but not put it in the org.

## First: is a custom component the right answer?

Climb the ladder from the bottom and stop at the first rung that fits. Say why each lower rung does not before you climb.

1. **A native control or setting**: a formula field, a picklist display, conditional logic, a repeater, a table, a record picker.
2. **A Flow Section** (build-flow-section): logic a flow does better, such as looking up org data, branching on records, calculating across records between steps.
3. **A custom LWC section** (this skill): an interaction in the browser no control covers. **The triggers that mean "this needs an LWC":**
   - **options that must be dynamic or come from a roster**: Flow Tool Kit's picklists are static, and a filtered Record Picker cannot express the rule (coaches with open spots this season);
   - **a live calculation, as the person types, that reads a table**: a fee from a rate schedule, an income band from a guidelines table;
   - **a custom interface for managing child rows**: a shift grid per volunteer, rows a Repeater section cannot draw;
   - **a widget Flow Tool Kit has no control for**: a map, a third-party widget, a calculator display, a chart.

When a lower rung is enough, say so and hand back. When this skill is right, tell the person plainly that the template alone cannot do it well, recommend a custom component, and say it is a small build that needs Claude Code to deploy. Ask before building one the plan does not already name.

## Before you build

1. **The project config** ([_shared/standards/project-config.md](_shared/standards/project-config.md)): the org Id, the **audiences** (guest, portal, internal) and the edition. Audiences decide the access the component needs.
2. **The section.** From the handoff or `plan.json`: the section's title, the component name (`lwcComponentName__c`, such as `c:feeSummarySection`), `what_it_does`, and the section's `fields`, which are the questions the admin's form asks. Without a plan, ask for the same in one message.
3. **The surface** ([references/contract.md](references/contract.md)):
   - **Form Template page section** (the usual one, and what build-template hands over): the component renders the section's own form and adds its behavior under or around it. It can manage child rows.
   - **Form Component section**: the behavior travels with a reusable component to every template that uses it. It sits beside the component's other sections and reads their answers from the live record. No child rows.
4. **The name**, by purpose, never by one form: `feeSummarySection`, `shiftPicker`, `rosterPicker` (lower camel case; the full name in the org is `c:<name>`, or `<namespace>:<name>` in a namespaced org).
5. **The standards**: [documentation](_shared/standards/documentation.md) for every description, [naming](_shared/standards/naming.md) for new fields.

## What you deliver

| Output | When |
|---|---|
| The component bundle: JavaScript, template, CSS, metadata, custom labels | Always |
| Its Jest tests | Always |
| The section's form, built by build-form-component and stored on the section | A page section whose questions the component wraps |
| New Form Submission fields, each with its description | Fields the plan proposes that the org lacks |
| An Apex controller (`with sharing`, user-mode queries) and its test class | Data the browser cannot read: a roster, a rate table in custom metadata |
| **Access grants for every audience**: read and edit on every field the component touches, Apex class access for its controller, custom metadata type access for any type it reads | Always, added to the permission sets the person names: ask which existing sets get them, and create a new one only when told to |
| The LWR support component's import line | Any LWR site that shows the form |
| The section pointed at the component by its full name | Always |

## Build it

Start from the worked example, [assets/fee-summary-card/](assets/fee-summary-card/README.md): a fee summary card under the admin's form, both surfaces, with its Jest tests, LWR support component, fields, labels and permission set. Copy it, rename it, and replace only the behavior. Shorter examples for the other triggers, each showing only what it adds, are in [references/examples.md](references/examples.md): the fee calculator with its rates in custom metadata, a roster-driven picker with its Apex, a volunteer shift selector that manages child rows through `relatedrecordchange`, and the full event contract in one skeleton.

1. **The admin's form, never hand-built inputs** ([references/house-pattern.md](references/house-pattern.md)). The component renders the admin's own form inside itself and adds only the calculation or behavior. The questions stay in Form Builder: build-form-component builds the section's `fields` as the section's form, and `scripts/point_section.py --form` (a named component) or `--form-json` (a form for this section alone) stores it on the page section, because the section editor hides its form picker once the type is Lightning Web Component. The component renders it with `<FlowToolKit-flow-form is-extension>`, passing both `form-qualified-api-name` and `form-j-s-o-n` from `section`, and owns only the behavior. It hands the form a copy of `record`, replaced only when a value changes, or the admin's section preview loops.
2. **The contract** ([references/contract.md](references/contract.md)): declare all seven inputs with defaults; send one `formfieldchange` per field with `bubbles: true` and `composed: true` and the field as `fieldApiName`; child rows only through `relatedrecordchange` with `add`, `update` or `remove`; never write to `record`, `section` or `relatedRecords`; send nothing in `review` or `disableAll`; `@api validate()` that runs the inner form's `validate()` first and returns `invalidItems` for the summary.
3. **Derived values go back through the form's transformation record**: hand each one to the inner form through `transformation-record` as a new object, so a read-only field the admin placed shows it, and send it with `formfieldchange` so it is saved. Keep the code that is genuinely code in its own module (the example's `feeRules.js`); send a derived value only when it differs from `record` and from the last value sent, and never before its lookup data has loaded. Derive in getters and react in `renderedCallback`, because a Form Component section changes `record` in place. Import every field name from `@salesforce/schema`.
4. **Styles** ([references/style-matching.md](references/style-matching.md)): the inner form takes the template's styles by itself. Anything else the component draws uses only the Form Style variables in [references/style-variables.md](references/style-variables.md), each with a fallback, and Lightning base components (`variant="brand"`) for buttons. Never import Flow Tool Kit's style modules; they are internal to the package.
5. **Words** in custom labels, so they translate. **Titles** stay on the page section; the component draws no section header.
6. **Metadata**: `isExposed` true (the renderer loads it from Flow Tool Kit's namespace), a description that says what it shows and where an admin places it, new fields with descriptions, any Apex with its test class, and the access grants in the table above.
7. **Tests.** A Jest test for the behavior and for the contract: the event shape, one event per change, the loop guard, nothing sent in review, `validate()`. Copy the example's `jest/` stub and `jest.config.js` mapping. Then:

```bash
python3 scripts/check_lwc.py force-app/main/default/lwc/<name>
```

It checks the contract and the styles: event flags, `fieldApiName`, public inputs and `validate()`, writes to inputs, package imports, the inner form's attributes, every `--ftk-` name against the package's list and every fallback. Zero errors before you deploy. Run it on section components only, not on the LWR support component.

## Deploy, place and check (Claude Code)

Details: [references/deploy-and-place.md](references/deploy-and-place.md).

1. Lightning Web Security is on (ask before turning it on: it affects the whole org). Retrieve anything the deploy would overwrite.
2. Jest, then deploy fields and labels, then the component and the permission set.
3. Access for every audience, in the same deploy as the fields: a field nobody can read hides even from the admin who deployed it, and the form renders blank. Assign the grants to the deploying admin, staff reviewers, portal users and the site guest user; for guests, run **flow-access-fix**.
4. Point the section: page sections are already named by build-template, otherwise `scripts/point_section.py`; a Form Component section gets a Lightning Web Component section in Form Builder.
5. LWR sites: add the component to the support component's imports, put it in the Theme Footer beside FlowToolKit LWR Support, and publish. Publish again after every change.
6. **Check it in the org**, not from the deploy result: the template's Preview Form at desktop and phone width, the card following a Brand color and corner radius change, each audience and surface, a submission read back, the review page, and a `validate()` refusal. Lightning caches builds for a while: reload with the cache cleared before deciding a change failed.

## Report

What you built (files, the component name, the surface), what the person or admin still has to do (assign the permission set, publish the site), the checks you saw pass, and anything left to check in the org. In chat, the files and the one line that the deploy needs Claude Code.

## Common mistakes

| Mistake | Instead |
|---|---|
| Hand-writing inputs for questions the admin could build | Render the admin's form with `<FlowToolKit-flow-form is-extension>`; code adds behavior |
| Building a component where a formula, a rule or a Flow Section would do | Climb the ladder from the bottom and say why each rung does not fit |
| Events without `composed: true` | `bubbles: true, composed: true`, always |
| Recomputing in a `record` setter | Getters and `renderedCallback`, with a guard against resending |
| Hard-coded colors and fonts | Form Style variables with fallbacks; base components for buttons |
| Importing Flow Tool Kit's style sheets or modules | The wrapped form and the variables; the modules are internal |
| Binding `record` straight to the wrapped form | A copy, replaced only when a value changes |
| Inventing a permission set for the build | Ask which existing permission sets get the grants |
| Trusting a fee the browser calculated | Recalculate it in the conversion flow or before payment |
| A bare component name (`feeSummarySection`) | The full name, `c:feeSummarySection` |
| Deployed but missing on an LWR site | The LWR support component in the Theme Footer, then publish |
| Calling it done from the deploy result | Preview, each audience and surface, the data read back |

More, with symptoms and causes: [references/pitfalls.md](references/pitfalls.md).
