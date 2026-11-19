# Documenting and naming what you build with Flow Tool Kit

Reference for every skill in the plugin. Anything the plugin builds, flows, screens, fields, templates, follows this page. Written for the person who opens the result next: a consultant, an admin or a developer, often months later.

## 1. The writing shape (applies to every description and help text)

1. Open with a summary. One or two sentences so anyone can tell what the item is and what it does.
2. Add nuance and technical detail only where the complexity needs it. A checkbox gets one sentence. A matching rule, a mapping or a calculated value gets what a consultant needs to configure it right.
3. When it helps, connect it to the bigger picture: the feature it belongs to, the setting it works with, what it falls back to. Use field labels, not API names, where a label exists.

Never include:
- internal component, class or constant names (write "the form", "the table", not a component tag);
- history ("used to", "before that", "repurposed"), except an upgrade note when an upgraded org must act;
- issue numbers, ticket numbers, commit hashes or dates;
- em-dashes (use a colon, a comma or a new sentence).

Write for a system administrator, not for the person who built it. Lead with the purpose and the outcome. The canvas already shows the mechanics; only the reason is invisible.

Example, before and after:
- Before: "Picklist (Clone, Copy, Duplicate) passed as clone-button-label to the repeater component. Only takes effect when Enable Clone Action is checked."
- After: "Button text for the Clone action on repeating sections: Clone, Copy or Duplicate. Only applies when Enable Clone Action is checked."

## 2. Flows

### Labels and API names
- **Screen flows that are forms:** label `Form | <Form Name>` (Form | Volunteer Application), API `Form_<Form_Name>` (Form_Volunteer_Application). Every form flow sorts together in the Flows list.
- **Subflows that act on one object:** label `<Object> | <Action>` (Contact | Merge Duplicates), API `<Object>_<Action>`.
- **Utility subflows (general, reusable):** label `Utility | <Action> <Object label>` (Utility | Search Contacts, Utility | Deduplicate Accounts), API `Utility_<Action>_<Object>`. Filtering on "Utility" finds them all; the object word finds the right one.
- Before-save flows: label `<Object> (Before <Trigger> --> <Action>)`, API `<Object>_Before_<Trigger>_<Action>`.
- Scheduled flows: label `Scheduled | <Object> <Action>`; platform-event flows: label `<Event> (Event --> <Action>)`; API names follow the label words with underscores.
- **Flow Sections** (screen flows that run inside a Form Template page section): label `Form Section | <What it does>` (Form Section | Shift Picker), API `Form_Section_<What_It_Does>` (Form_Section_Shift_Picker). They sort beside the `Form | ` flows, and are named for their purpose, never for one form.
- **The org's own copy or override of a packaged flow:** keep the packaged label's prefix and replace its suffix with the copy's purpose: `(Form) Upsert | Guest Override` (`Form_Submission_Upsert_Guest`), `(Form) Prefill | Guest Resume` (`Form_Submission_Prefill_Guest`). The API name is the packaged one without the package prefix, plus the purpose. The description says why the copy exists (for example, why it runs in system context and what that exposes) and that it is compared with the packaged flow after each upgrade.
- Screen flows that are not forms (quick actions, record-page buttons): label `<Object> | <Action>` (Funding Award | Apply Budget Template), API `<Object>_<Action>`.
- Record-triggered flows: API `{Object}_After_{TriggerType}_{Action}`, label `{Object} (After {TriggerType} --> {Action})`.
- Form conversion flows (mapping flows): API `Form_Submission_Convert_Process_<Object>[_<Variant>_Default]_Overridable` or `..._Upsert_<Object>_Overridable`. Label `(Form Submission) Convert | Process | <Object> | Overridable`. Process flows label themselves Process, upsert flows Upsert, never the reverse.
- Flows you may want a partner or admin to override: set the flow overridable.
- Every flow has a description (section 2.3).

### Elements (every flow, not only mapping flows)
- **Get Records**: API `get<WhatItReturns>` (camelCase), label the same words with spaces. Use the object's own name when the query is plainly that object: `getPersonAccount` / "Person Account". Name what is returned when a filter is the point: `getPrimaryMember`. In flows built in Flow Builder, the label-derived form (`Get_Person_Account`) is equally fine: the object name is the rule.
- **Decisions**: every decision is labelled `Switch`. The meaning lives in the outcome labels and the default outcome label ("Role found" / "No role configured"). API name stays descriptive: `Switch_Primary_Member_Check`.
- **Create, Update, Delete**: named after the object, never the local business word. `Update Funding Disbursement`, not `Update Claim`. The flow's own label may keep the local word.
- **Assignments**: `Assign_*` or `Set_*`. **Transforms**: `*_Field_Map`. **Actions**: verb-named.
- **Logging in conversion flows**: `Log_Success_<Operation>` for each success path. Faults: `Fault_<Operation>` (settled, Q1), labelled "Log Error" on the canvas. Dedicated return step: `Return_to_Controller`. Chaining actions: `Process_<Object>`.
- When you rename an element, update every reference: connectors, `targetReference`, `elementReference`, `assignToReference`, `inputReference`, `collectionReference` and every `{!...}` inside formulas and transform expressions. A missed formula reference deploys fine and fails at runtime.

### 2.3 Descriptions on flows and elements
- Flow description: what the flow is for, how to use or launch it, and the considerations (what it does not undo, what to override or deactivate to change it). For an overridable flow, state the clone and override contract.
- Element descriptions may name Flow concepts (Apex action, DML, platform event) because whoever overrides the flow reads them.
- Every element that can carry a description gets one: the flow, every variable, formula, constant and text template, and every element (Get, Create, Update, Delete, Assignment, Decision, Loop, Transform, Screen, action, subflow). Written for the client admin, in the summary-first shape. Claude writes them, so there is no exception for self-evident elements.

### Screens and variables
- Screen API names: `Pascal_Snake`, label the same words with spaces. `Contact_Information` / "Contact Information". No suffix such as `_Screen`.
- Message screens: use the illustration component with title and subtitle bound to custom labels, never Display Text with inline English. The flow header is always off (`showHeader` false); keep the footer for the Finish button.
- A screen or quick action flow always ends on a message screen with a Close button (a custom label, shared `Button_Close`). Every path ends there, success and refusal alike. Never end on Salesforce's own "Your flow finished" screen. Illustration fits the outcome: Approval (done), No Access (refused), Not Available (failure). Fault screens: title from a label, subtitle the flow's fault message. <!-- partner-clean: allow R4 -->
- **A Flow Section is the exception:** it never ends on a message screen and keeps Flow's own footer off. Finishing is how it hands control back to the form, and the form owns what happens next (its own buttons, confirmation and messages).
- Variables: no type prefixes (`Contact_Record`, not `rec_contact`). `Pascal_Snake` casing, with descriptions. Variables named by Flow Tool Kit contracts keep their exact names (for example the inputs `PlatformEvent` and `DebugRecord`, or the older `FormSubmission`, `FormTemplate`); never rename them.

### Build the simplest flow
Fewest elements that do the job. One Update that resets all fields beats a decision per field. A decision outcome carries every condition its path needs; use a formula only for what a condition cannot do (INCLUDES on a multi-select). Use a Transform instead of a loop with assignments when reshaping a collection. Check that a trigger, field default or another flow does not already do the step. Open every flow in Auto-Layout, one ordinary incoming path per element.

### Invocable actions (Apex a flow calls as an Action element)
- **Label:** a verb phrase in Title Case naming the outcome (Get Account Giving Summary). **Description:** what it does and what comes back, summary first.
- **Each input and output** has a Label written like a field label and a Description: for an input, what to pass and what a blank means; for an output, what it holds and its value when there is nothing to report.
- **Category** is optional and matches the org's other actions. **Class:** `<Object>_<Action>_Invocable`.

## 3. Custom fields (any object you add fields to)

Every custom field ships with a description at the moment it is created, never as a follow-up task. Inline help is the second element; where it goes depends on who sees the field (section 4).

| Element | Reader | Content |
|---|---|---|
| Description | Admin or consultant auditing in Setup | Summary first, then what reads or writes the field, its meaning and constraints ("0 means no limit", "blank hides the action") |
| Inline help text | The person filling the field in, max 255 characters | What to enter and when to leave it blank, in their vocabulary |

Never copy one into the other: they serve different readers. Custom metadata type fields support inline help too.

## 4. Fields on Form Submission and Form Template

These two objects look alike and are documented differently, because different people see them.

### Form Template fields (configuration object, admins and form creators only)
- Description: required. Written for the advanced admin. How the form, flow or process consumes the field, prerequisites, gotchas.
- Inline help text: required, **at least two sentences**. First: what to enter or toggle. Second: the effect, a prerequisite or a tip. Written for the person building the template.
- Name real related flows, objects and fields where it helps, but only ones that exist in the org. Check before citing; never invent a flow name.
- Verify behaviour against what the flow or form actually does, not against older help text, which can be wrong.
- Reference fields by their label, not the API name.

### Form Submission fields (respondent-facing)
- Fields on the submission are filled in by people answering a form, and their inline help can appear in the form itself. So:
  - Description: required, always. Admin guidance lives here (what the question captures, where it maps, what it does not do). Example: "Self-reported age range for demographic questions without collecting a date of birth. Bands do not overlap, with an explicit option to decline."
  - Inline help text: omit by default. Add it only when a respondent really needs it, and then in respondent language. Never admin instructions such as "pair with conditional logic". The form designer owns what the respondent sees; a form-level help text is usually the better place.
- Label the field as the respondent will read it, or as the question is worded on the form.
- Picklist fields on the submission: describe every value that is not obvious, and always include an explicit "prefer not to answer" value for sensitive questions.
- Fields that map to a target object: say so in the description in plain terms ("Copied to the Contact's mailing city when the mapping runs") so the mapping is auditable from either side.
- Lookup fields to converted records: say whether the field is set by the conversion or by the respondent.
- Do not store history or reasons that only the project team understands. Describe what the field does now.

### Checklist before you hand a field back
1. Description present, summary first, no issue numbers, no component names.
2. Form Template field: help is two or more sentences. Form Submission field: help is absent or respondent-language.
3. Every flow or field cited in the text exists in the org.
4. Help text is 255 characters or fewer.

## 5. The processes around it

- Write descriptions when the item is created, in the same step that creates it. Never as a later pass.
- When you change an item whose description misses this shape, fix it in the same change.
- Before handing over any metadata, search the touched files for issue numbers (`#` followed by digits), short hashes and em-dashes, and rewrite the sentence so it stands alone.
- Every flow you hand over is opened in Flow Builder once, to confirm Auto-Layout and that Builder saved nothing unexpected (raw field IDs, stripped action outputs).
- Retrofitting many fields: script the insertion keyed by object and field, skip fields that already have the element, enforce the 255-character limit.
- The plugin's skills read this page. If a skill's output disagrees with it, this page wins.

## 6. Naming

Names for what the plugin's skills create. Flows and flow elements are named in section 2 above; that section wins for anything about flows.

### Fields

- **Mirror the target field first.** A new Form Submission field that feeds a target field takes that field's API name where it is a good name (`Program_Interest__c` for `Program_Interest__c`), so the pair reads side by side. Then fix what a machine should get right: word boundaries, initialisms (`SMS`, not `Sms`), abbreviations, and widget words ("check all that apply" describes a control, not data).
- **Readable beats matching.** Never copy a target's naming problem into a new field; the mapping documents every pair.
- **Reuse, then org-wide, then form-specific.** A packaged field first; then an org-wide field named for its role (`Guardian_Phone__c`), named only after reading every form in the org; a field for one form last.
- **Shape it like its target**: the same type, and for a picklist the same values.
- **No type prefixes or suffixes** (`Contact_Record`, not `rec_contact`), and no issue numbers or dates in names.
- Labels read as the question is worded on the form (Form Submission) or as an admin knows the setting (Form Template).

### Form components and templates

- A **shared component** is named for its purpose, never for one form: `Contact_Details`, `Mailing_Address`, `Emergency_Contact`. A form-only section needs no component name.
- A **Form Template's Name** is the form's public title ("Community Program Registration"); it shows in the banner.
- A page is labelled for what it asks ("Your Details", "Release and Signature"), never "Page 2" or "Welcome".

### Files in a project

| File | Where |
|---|---|
| The project config | `flow-tool-kit.json` at the project root ([project-config.md](project-config.md)) |
| One form's work | `_forms/<slug>/`: the source files or `capture.json`, `ir.json`, `plan.json`, `field-audit.csv`, and `design/` for the canvas |
| One site's work | `_site/<slug>/`: `site.json`, `pages/<urlName>.json`, `photos.json`, `backups/<date>/` (the site as pulled before each build), `checks/<date>/` (render check screenshots) and `notes.md`. `<slug>` is the site's name in lowercase with hyphens |
| One brand's kit | `_brand/<slug>/`: the site crawl and stylesheet scan, `candidates.json`, the review (`brand-picker.html`, `brand-review.md`), `picks.json`, `brand-kit.json`, `assets/` and `canvas/`. `<slug>` is the brand's name in lowercase with hyphens |
| A FormAssembly account archive | `_formassembly/` at the project root: one folder per form, the summaries, `check-pass-report.md` and `pages/`. `_formassembly/raw/` holds API listings and browser bundles; keep it out of version control |
| An audit | `_audits/<audit>-<yyyy-mm-dd>/`, for example `_audits/guest-exposure-2026-01-15/` with `findings.md`, `findings.json` and `snapshot.json` |
| The org catalog | `ftk-catalog/<org Id>/`: `catalog.json`, `catalog.md` and (in Claude Code) `raw.json`; `ftk-catalog/no-org/` when no org is connected (the format is the catalog-format standard, carried by the skills that read a catalog) |
| A field audit | `field-audit/<org Id>/`: `data-dictionary.md`, the four CSVs (`data_dictionary.csv`, `template_references.csv`, `flow_references.csv`, `coverage.csv`) and `raw.json` |
| `<slug>` (a form) | The form's name in lowercase with hyphens, prefixed by the source when there is one: `formassembly-4874954`, `google-volunteer-survey`, `brief-community-registration` |
| Metadata | The project's own `force-app/` |
