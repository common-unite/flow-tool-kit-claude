---
name: build-flow-section
description: Build a Flow Tool Kit Flow Section, the screen flow that runs inside a Form Template page section for logic a form component and a formula cannot do, such as picking from records already in the org, branching on org data, a short multi-step process inside one section, or calculating across records. Clones the shape of the packaged "(Form) Flow Section | Template", keeps its contract, returns only the fields it set, gives the page one button bar, and points the page section at the flow. Use when form-design, form-migrate or build-template hands over a section marked flow-section, or when someone asks to build, fix or upgrade a Flow Section.
---

# Build Flow Section

A Flow Section is a screen flow that the form runs inside one of its page sections. The form hands it the Form Submission and the page's buttons; the flow shows its screens and hands back what it changed. It is the middle rung of the ladder every form skill climbs, lowest first:

1. **Native**: a form component control, a setting, a formula field or a conditional rule. The admin changes it in Form Builder.
2. **Flow Section** (this skill): logic that needs records from the org, branches on them, takes several steps, or calculates across records. The admin changes it in Flow Builder.
3. **Custom LWC** (build-custom-lwc): an interaction no control or flow screen covers, such as options that must change as the person types, a live total over a table while they type, a map or a third-party widget.

Pick the lowest rung that does the job, and say why the rung below is not enough. A Flow Section reads the org when it opens and when the person moves between its screens; anything that must react on every keystroke is an LWC.

**Called by** form-design and form-migrate (they mark the section `decision: flow-section` with the flow's name), handed over by build-template after the template is built, and directly ("build a flow section that picks the household's primary contact"). **Hands over** to flow-access-fix for every guest or portal audience, and to build-custom-lwc when a screen needs a component no flow screen has.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat, with or without a Salesforce connector | Design the section, write its spec, and run `scripts/flowsection.py scaffold` and `check` in the code sandbox to produce a checked flow file the person can take to Claude Code. With a connector: read the org (the template, its sections, the records the flow will read), confirm the flow is active once someone has built it, and point the page section at it (a record update, step 6). **Chat cannot deploy or activate a flow.** Say so in one line, then either hand over the files for Claude Code, or give the person the Flow Builder steps in [references/flow-builder-steps.md](references/flow-builder-steps.md) to build it by hand from the gallery template. |
| Claude Code, local or on the web, with the Salesforce CLI | Everything: scaffold, edit, check, deploy, activate, wire the section, hand over to flow-access-fix, and check it in the form. |

Read on demand, beside this file:
- [references/contract.md](references/contract.md): **read first.** The form's side of the contract, each fact traced to the package source: how it launches the flow, every input and output, the button handoff (first-screen Back, middle screens, the last screen's label, who drives), records and rows in and out, repeaters, validation, Save Progress, review, guest prefill through the FLS Record(s) Sanitizer, and the traps.
- [references/buttons-and-saving.md](references/buttons-and-saving.md): one button bar, Back and Save Progress routed by label, several screens in one section, Save Progress as a screen action, and handing saved Ids back.
- [references/access.md](references/access.md): guest, portal and internal users; what the flow may read; when flow-access-fix runs.
- [references/pitfalls.md](references/pitfalls.md): the traps, each with its symptom and fix.
- [references/spec-format.md](references/spec-format.md): the section spec `scripts/flowsection.py` reads.
- [examples/README.md](examples/README.md): four worked examples (a household contact picker, a two-step section, a custom LWC inside a section, packaged screen components inside a section).
- Plugin standards: `_shared/standards/documentation.md` (section 2 is the flow standard: names, elements, descriptions; section 6, Naming), `_shared/standards/project-config.md`. Where this skill and a standard disagree, the standard wins, except where this page says the contract needs otherwise and why.

## 1. Start from what exists

1. **The project config.** Read `flow-tool-kit.json` (`_shared/standards/project-config.md`): the org, its edition and its **audiences** (guest, portal, internal). No audiences saved: ask the one question ftk-start asks ("Who fills this form in: the public without signing in, signed-in community members, staff, or a mix?") and save the answer. The audiences decide the access work in step 7.
2. **The handover.** From build-template's report (`handoffs`, skill `build-flow-section`) or form-design's `plan.json`: the section's title, the flow's API name (`FlowApiName__c`) and `what_it_does`. Read the section's fields, questions and placement in `plan.json` too: the fields the flow sets are listed there as `submission: set by the Flow Section`.
3. **The org.** List the org's Flow Sections before building a new one; another template may already have one that does this job:

   ```bash
   sf data query -q "SELECT FlowToolKit__FlowApiName__c, FlowToolKit__Title__c FROM FlowToolKit__Form_Template_Page_Section__c WHERE FlowToolKit__Component_Type__c = 'Flow'" -o <org-alias>
   ```

   A flow already doing the job: **ask, naming it**: "Form Section | Shift Picker already lists open shifts on two templates. Reuse it here, or build a new one?" Never reuse or duplicate silently. In chat, run the same query through the connector.
4. **Confirm the ladder.** State in one sentence why a native control or a formula cannot do it. If one can, stop and hand the section back to build-form-component.

## 2. Design the section

Write down, before any flow:
- **What it reads** from the org, and as whom (step 7). Every record a guest or portal user sees through this flow is exposure: read only what the screen shows.
- **What it asks**: the screens, in order, each named for what it asks (`Choose_Primary_Contact`, never `Screen_2`).
- **What it hands back**: the Form Submission fields it sets (only these), and rows if it manages a repeater or table, with every saved row it removes still in the collection, flagged `IsDeleted`.
- **Who drives the buttons**: the page (one screen, the usual case) or the flow (several screens, or Save Progress that must keep the person on the screen). See [references/buttons-and-saving.md](references/buttons-and-saving.md).
- **Save Progress**: on (the default when the template allows it) or off.

A Flow Section **hands values back and never writes records itself**. The form saves the submission and the conversion creates the records. The one write it may make is Save Progress, through the packaged save flow, which the scaffold wires for you.

## 3. Name it

From `_shared/standards/documentation.md` section 2, applied to Flow Sections:
- Label `Form Section | <What it does>` (Form Section | Household Contact Picker), API name `Form_Section_<What_It_Does>`. Every Flow Section then sorts together in the Flows list, beside the `Form | ` flows. Name it for its purpose, not for one form, so another template can use it.
- Screens `Pascal_Snake` with no `_Screen` suffix; every decision labelled `Switch` with the meaning in its outcome labels; Get Records `get<WhatItReturns>`; assignments `Assign_*` or `Set_*`; your own variables `Pascal_Snake` with no type prefix.
- **The contract variables keep their exact names** (`record`, `recordId`, `relatedRecords`, `review`, `buttonLabel_Back`, `buttonLabel_Next`, `buttonLabel_Finish`, `buttonLabel_SaveProgress`, `stage`, `section`, `buttonTriggerName`, `hidePageButtons`, `isValid`, `buttonClickedLabel`). The form finds them by name and type; renaming one silently disconnects it.
- **Descriptions on everything** when you create it: the flow (what it does, where it runs, what it hands back, what to edit to change it), every element, variable, formula and choice set. Summary first, written for the admin who opens it next, no issue numbers, no history, no em-dashes.

## 4. Build it

**Claude Code, or chat with code execution: scaffold from a spec.** Write the section spec ([references/spec-format.md](references/spec-format.md)), then:

```bash
python3 scripts/flowsection.py scaffold <section-spec.json> --out <project-dir>
```

It writes `force-app/main/default/flows/<api_name>.flow-meta.xml` in the shape of the packaged template: the full contract, the template read, the review route, one screen per spec screen with the docked buttons bound to the contract, a Switch wherever a button can end the section, the form component and repeater wiring, record choice sets for picks, Save Progress as a screen action beside a form, a row template from the section's Prefill Template, and `Assign_Outputs`, which returns only what the section set on a fresh record (`New_Values`). It runs `check` on what it wrote. It refuses to overwrite a file: retrieve the org's copy first and merge.

Then add what the spec cannot say (a Get Records the screen needs, a formula, a component from build-custom-lwc), following section 2 of the documentation standard, and keep the shape:
- set returned values on `New_Values` (safe on every version; setting them on `record` is safe only from Flow Tool Kit 5.3), and assign `record` and `relatedRecords` only on the forward finish, because the form reads them on every new screen;
- bind Back, Save Progress and the last screen's Finish to their `buttonLabel_` variables, never typed text; a middle screen's Next may carry its own words, since the form never sees it;
- the first screen's native inputs stay **not required** in Flow, by default: Back there is a Next under the hood, and the Flow runtime holds a Next on an empty required input whatever the buttons component's skip validation says. The scaffold asks for those answers on the forward path instead (`Switch_<Screen>_Answers`, after the Back outcome, skipped for Save Progress), sending a blank answer back to the screen with a message under the question. Required fields inside a Flow Tool Kit form component stay as they are: the form skips its own checks for Back;
- a saved row the section removes goes back in `relatedRecords` with `IsDeleted` true, by default, never just left out: the save and the conversion delete only flagged rows, and a dropped row stays. The repeater's output already does this; in your own logic, flag the row before you leave it out (buttons-and-saving.md, "Removing rows");
- a record read in System Mode for a guest or portal user goes through the **FLS Record(s) Sanitizer** before any screen or form component, by default (contract.md, "Guest prefill");
- keep the Section Review screen in step with the editable screens;
- every element you add gets its description in the same edit.

**By hand in Flow Builder** (chat without Claude Code): [references/flow-builder-steps.md](references/flow-builder-steps.md) walks through creating it from the gallery template and making the same changes.

## 5. Check it

```bash
python3 scripts/flowsection.py check force-app/main/default/flows/<api_name>.flow-meta.xml --audiences guest,portal
```

Errors stop the work; fix every one. It checks the contract (names, types, input and output), the three outputs the page section picklist needs, a write onto `record.<Field>` (a warning: safe from 5.3), the review route, buttons that listen to the page (one listener per screen), the button handoff (the clicked label returned on finish, the first screen's Back left as a Next with the Back label and routed by a Switch, a required native input on the first screen, a Finish button bound to `buttonLabel_Finish`, typed Back or Save Progress labels, a Save Progress Switch on several screens), rows handed back in a way that can drop saved rows without `IsDeleted`, a System Mode read that reaches a screen without the FLS Record(s) Sanitizer, the template's sample forms left in place, decision labels, descriptions, em-dashes and issue numbers, every reference resolving (a rename that missed a formula), names that differ only in case (Flow rejects them), records written from the section, and, for guest or portal audiences, that the flow requires permission to run. Read every warning.

## 6. Deploy, activate and point the section at it

1. **Retrieve before you deploy** when the flow already exists in the org, and merge: never overwrite changes someone made in Flow Builder.
2. **Deploy**: `sf project deploy start --source-dir force-app/main/default/flows/<api_name>.flow-meta.xml -o <org-alias>`. The scaffold writes the flow as Active; an org that deploys flows as Draft needs it activated in Setup. The form reads the **active** version's variables, and the section picklist lists only active flows.
3. **Open it once in Flow Builder** in Auto-Layout and save; retrieve again and diff. Flow Builder can rewrite parts of a file.
4. **Point the section at it.** When the template came from `plan.json`, the plan is the source of truth: the section's `Component_Type__c` is `Flow` and its `FlowApiName__c` is this flow's API name, and build-template writes both. Rebuild rather than editing by hand; a hand edit is erased by the next rebuild. With no plan, set them in the org, in the section's **Customize** (Component Type **Flow**, then pick the flow), or as a record update:

   ```bash
   sf data update record -s FlowToolKit__Form_Template_Page_Section__c -i <section Id> -v "FlowToolKit__Component_Type__c=Flow FlowToolKit__FlowApiName__c=<api_name>" -o <org-alias>
   ```

   In chat, the connector can make the same update once the flow is active.
5. **Reset Form Cache** (Form Builder footer) whenever the flow's input variables changed since the form last ran it: the form caches which inputs a flow declares, per flow name.

## 7. Access, for every audience

Run **flow-access-fix** for each audience in the project config other than internal users with Run Flows. In short ([references/access.md](references/access.md)):
- A guest or portal user runs the flow only when the flow **requires permission to run** (the scaffold sets it for those audiences) **and** a permission set of theirs grants it. The packaged permission sets cannot grant your flow; use the org's own set for that audience.
- The flow runs as the person filling the form. A guest reads nothing without a guest sharing rule; a portal user reads what their sharing gives them. Read the minimum; prefer a sharing rule for records meant to be public. A read in System Mode is the last resort: filter it to exactly the records this person may see, and pass the result through the FLS Record(s) Sanitizer before any screen or form component, so field access still follows the user's profile and permission sets (contract.md, "Guest prefill").

## 8. Check it in the form

A Flow Section is not done until it has been walked in the form, as each audience:
1. Open the template's **Preview Form** (and the site page for guests or portal users) and reach the section's page.
2. **One bar**: only one set of buttons shows (the page's, or the section's when it drives).
3. **Forward**: answer, continue, and confirm on the next page (or the Form Submission record after Save Progress) that only the fields the section sets changed; fields answered on other sections are untouched.
4. **Back** from the section's first screen returns to the previous page (Return to the stages overview in Stages mode) without keeping the section's unsaved edits. Try it once with nothing answered: Back must still leave. Then continue with nothing answered: the section stays, with the message under each blank question. Back on a later screen steps back a screen. The page's own clicks take about a second to reach the section; that is expected.
5. **Labels**: the section's last screen shows the page's forward label (Next, Submit or Mark Complete); a middle screen shows its own words or the same label.
6. **Save Progress** saves and keeps the person where they were (a screen action), or saves and restarts the section (page drives): match what the design said.
7. **Review**: on the review page, the section shows read-only.
8. **Another section invalid**: leave a required field empty elsewhere on the page and continue; the page stays and the section comes back filled in.
9. A guest or portal walk that shows "You do not have the level of access" goes straight to flow-access-fix. A guest walk that prefills a record shows only the fields the guest's profile and permission sets can read.

In Claude Code with a headless browser, walk it there; otherwise give the person this list.

## Done when

- The ladder was stated: why native was not enough, and why this is not an LWC.
- The flow keeps the full contract, returns only what it sets on a fresh record, gives the page one bar, routes Back and Save Progress by label, and has a read-only review screen.
- `flowsection.py check` reports no errors, and every element carries a description to the standard.
- The flow is active, the section points at it, the form cache was reset after input changes, and flow-access-fix ran for every guest and portal audience.
- The walk in step 8 passed for each audience.

## Common mistakes

| Mistake | Instead |
|---|---|
| Building a Flow Section for something a control, formula or rule can do | Native first, and state why it is not enough |
| Setting values on `record` and returning it on a version before 5.3 | Set them on `New_Values` and assign `record = New_Values` last; it is safe on every version |
| A typed Back, Save Progress or Finish label | Bind it to its `buttonLabel_` variable; the form routes the finish by label, and an unknown label always moves forward |
| A finish path that never sets `buttonClickedLabel` | Set it from the buttons component on every path; without it the page ignores the finish and shows a spinner |
| A guest shown a System Mode read as it came back | Pass it through the FLS Record(s) Sanitizer first |
| Renaming or deleting a contract variable, or leaving out `isValid` | Keep every one; without the three outputs the flow is not even listed |
| A required native input on the first screen | Not required in Flow; ask for it on the forward path after the Back outcome, as the scaffold does |
| Leaving a removed saved row out of `relatedRecords` | Keep it with `IsDeleted` true; only flagged rows are deleted |
| Leaving the template's sample form and repeater on the screen | Your own form component, or none |
| Writing records from the section | Hand values back; the form saves and the conversion writes |
| A page that shows two button bars | Declare `buttonTriggerName` and `hidePageButtons` (flows cloned before the one-bar release lack them) |
| Pointing the section at the packaged template | Clone it; the template is never active |
| A guest flow that "does nothing" or shows the access message | flow-access-fix: require permission to run and grant it |
| Calling it done after the deploy | After the walk in the form, for every audience |
