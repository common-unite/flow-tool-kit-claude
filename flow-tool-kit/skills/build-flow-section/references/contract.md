# The Flow Section contract

How a Form Template runs a Flow Section, what it passes in, what it reads back, and how the two share one set of buttons. Every statement here was read in the Flow Tool Kit package source (version 5.3, plus the fixes noted); where a help page says otherwise, this page is right. Each fact names the source file it comes from, relative to the package's `force-app/main/default/`, with the function or element to look for:

| Short name | File | What it is |
|---|---|---|
| the page | `lwc/formTemplate/formTemplate.js` | The Form Template: pages, page buttons, saving |
| the section | `lwc/formTemplateSection/formTemplateSection.js` and `.html` | One page section; for Component Type Flow it hosts the flow |
| the host | `lwc/flowFormScreenFlow/flowFormScreenFlow.js` | Wraps `lightning-flow`: builds the inputs, reads the outputs |
| the buttons | `lwc/buttonsCustom/buttonsCustom.js` | The Flow Tool Kit buttons component on each flow screen |
| the input probe | `classes/Utilities_Form.cls` (`FlowValidInputParameters`) and `classes/Form_Flow_Utility.cls` | Which inputs the flow declares; which flows the section picklist lists |
| the template | `flows/Form_Flow_Section_Template.flow-meta.xml` | `(Form) Flow Section | Template` |
| the repeater | `lwc/flowFormRepeat/flowFormRepeat.js` | The repeater component, on a page or on a flow screen |
| the row save | `classes/FormSubmission_Data_Invocable.cls` | Turns the submission's rows into records to upsert and delete |
| the sanitizer | `classes/DataSanitizer_Invocable.cls` | The FLS Record(s) Sanitizer action |

## Where a Flow Section lives

- A **Form Template Page Section** whose **Component Type** is **Flow** (`FlowToolKit__Component_Type__c` = `Flow`) and whose **Flow API Name** (`FlowToolKit__FlowApiName__c`) names the flow. The section's header, frame and visibility rule work as on any section; on the review page a Flow section draws no header (the section, `showContentHeader`).
- The section editor's **Flow** picklist lists active screen flows (not templates) whose active version has the three outputs `isValid`, `buttonClickedLabel` and `record`, each available for output, spelled exactly so: the query matches names case for case (the input probe, `Form_Flow_Utility.queryActiveFlowSectionFlows`). A flow without them is not listed (a value saved earlier still shows, marked as not listed). A flow activated a moment ago appears after the page reloads.
- A flow name without a namespace matches your own flow first (`Form_Flow_Utility.queryActiveFlowVersion`, unmanaged before managed), so `Form_Section_Shift_Picker` finds the flow in your org.

## How the form launches it

1. **It asks which inputs the flow declares.** The probe reads the active version's input variables by exact name, type, collection and object (`Utilities_Form.FlowValidInputParameters`, `Form_Flow_Utility.queryFlowVariableView`: `IsInput = TRUE`, names matched case for case). The answer is kept in the package's org cache partition per flow name and object, so after you add or remove an input, **Reset Form Cache** in the Form Builder footer, or the form keeps passing the old set. The probe runs without sharing, so it works for guests too.
2. **It waits for the submission.** With a `record` input declared, nothing starts until the page has a submission record (the host, `buildInputVariablesIfReady`).
3. **It builds the inputs once and starts the flow once.** The input list is built a single time and never rebuilt while the interview runs, because a new list would restart it (the host, comment on `inputVariables`). So **the flow never sees changes made elsewhere on the page after it opened**: other sections' answers, a page rule.
4. **It reads the outputs on every status change**, not only at the end: on start and on every screen the flow reports its current outputs (the host, `handleStatusChange`; the page, `handleFlowStatusChange`). See "Records in and out".
5. **It acts on the finish by the clicked label** (below). The section's finish behaviour is set to none, so a finished interview does not restart on its own; the host hides it behind a spinner (the host, `flowFinishBehavior`, `handleStatusChange`).
6. **It restarts the flow** only when the page stayed after the finish (another section invalid, or Save Progress): the page bumps a reset signal and the host builds the inputs again from the **latest** record and rows and starts a fresh interview at its first screen (the page, `handleFlowStatusChange`; the host, `flowResetSignal`). Leaving the page and coming back also starts a fresh interview.

## Inputs (the form passes each one only when the flow declares it, and only when it has a value)

All from the host, `buildInputVariablesIfReady`, fed by the section's attributes in `formTemplateSection.html` and the page's in `formTemplate.html`.

| Variable | Type | What the form passes |
|---|---|---|
| `record` | Form Submission record | The submission as the page holds it at launch, including answers from earlier pages not saved yet, and every section's rows serialized in `FlowToolKit__Internal_Additional_Data__c` (the page, `applyRelatedRecordsUpdate`). Read earlier answers here (`record.FlowToolKit__Account__c`) |
| `recordId` | Text | The submission's Id, only once it has been saved. A new submission has none: never rely on it for a new form |
| `relatedRecords` | Form Submission collection | **This section's rows only** (rows whose `Internal_SectionId__c` is this section; the section, `get relatedRecords`), and only when there is at least one. A new form passes nothing, so the variable starts empty |
| `review` | Boolean | True on the review page |
| `buttonLabel_Back` | Text | The page's Back label: the **previous page's name** (its Page Label), or Return in Stages mode. Not passed on the form's first page (the page, `setCurrentPage`) |
| `buttonLabel_Next` | Text | The page's forward label: the page's Button Label; on the last page the Submit label (or the open-review label when a review page follows, or Update once submitted); Mark Complete in Stages mode (the page, `setCurrentPage`) |
| `buttonLabel_Finish` | Text | **The same forward label as `buttonLabel_Next`**. The flow shows Next on its middle screens and Finish on its last, with the page's words (the host, comment above `buttonLabel_Finish`) |
| `buttonLabel_SaveProgress` | Text | The Save Progress label, only when the template allows Save Progress and the form is not read only or locked (the page, `allowSaveProgress`, `saveProgressButtonLabel`) |
| `stage` | Form Submission Stage record | The current stage, in Stages mode |
| `section` | Form Template Page Section record | The section the flow runs in: its Id, its page and its Prefill Template |
| `buttonTriggerName` | Text | `ftkPageButtons_<page Id>`, the name the page's buttons publish under (the page, `sectionFlowTriggerName`). Not passed on the review page |

`record` and `relatedRecords` must be on Form Submission (`FlowToolKit__Form_Submission__c`), or the probe does not count them and the form does not pass them.

## Outputs (what the form reads)

| Variable | Type | What the form does with it | Source |
|---|---|---|---|
| `record` | Form Submission record | Merged into the page's submission, but only the fields whose values **differ from the launch copy**, and never a blank (null or empty) value; `Id` is always kept. So a section can set a field, can set a checkbox to false, but can never blank a text, picklist or lookup field | the host, `changedFields`; the page, `handleFlowStatusChange` |
| `relatedRecords` | Form Submission collection | **Replaces this section's rows** wholesale, each row stamped with the section, page, parent submission and an upsert key | the section, `handleFlowStatusChange`, `stampRelatedRecord`; the page, `processRelatedRecordsChange` |
| `buttonClickedLabel` | Text | Read at the finish to route the click (below). A finish without it does nothing at all | the page, `handleFlowStatusChange`, `_sectionFlowButton` |
| `hidePageButtons` | Boolean | True: the page hides its buttons on this page and the section's own bar drives. Read on every screen, so the flow can change it per screen. Ignored on the review page | the page, `handleFlowStatusChange`, `flowOwnsCurrentPageButtons` |
| `isValid` | Boolean | Needed so the flow is listed. **A page section never reads its value**: the section has no handler for it, and the page's validity check does not look inside a Flow section | the section, `validate` (selects only forms, repeaters, tables and LWCs) |

Output names are matched without regard to case (the host lower-cases them), but input names and the three listing outputs are matched case for case. Keep the exact spelling everywhere.

The "changed fields only" rule arrived in **5.3**. On earlier versions the form merged the whole returned record, so a section that set values on `record` and returned it put old values back over answers changed elsewhere after it opened. A fresh record (`New_Values`) holding only what the section set is safe on every version; the 5.3 template itself now assigns `record` directly.

## The button handoff

### Who drives (one bar, since 5.2)

| The flow | Who drives | Source |
|---|---|---|
| Declares the text input `buttonTriggerName` and leaves `hidePageButtons` false | **The page.** On load the host tells the page the section is listening; the page sends its forward, Back and Save Progress clicks to the section first and waits for the section to finish. The section's own Next and Finish (and Back, Save Progress) are hidden by formula | the host, `BUTTONS_LISTENING`; the page, `_sendToSectionFlows`, `processButtonClick` (first line); the template, formulas `HideDockedButtons`, `HideBackButton`, `HideSaveProgressButton` |
| Sets its output `hidePageButtons` to true | **The section.** The page empties its bar on this page and does not forward clicks; the section's docked bar drives and finishes with the clicked label. The review page always keeps its Submit | the page, `flowOwnsCurrentPageButtons` |
| Neither | **Both bars show**, and each works on its own (flows built before 5.2) | |

How a page click reaches the flow: the page publishes on the Flow Tool Kit button channel with the trigger name, a type (`BACK` for Back, `NEXT` for forward and Save Progress), the label, and "skip validation" on for Back and Save Progress. Every buttons component whose **Trigger Listener Name** equals that trigger name acts on it: it sets its `buttonClickedLabel` output to the page's label, then **after a one second pause** moves the flow (the buttons, `handleMessage`, `navigateAfterDelay`). A page click therefore takes about a second to land; that is expected.

### Labels

The labels go in through `buttonLabel_Back`, `buttonLabel_Next`, `buttonLabel_Finish` and `buttonLabel_SaveProgress` (table above) and are bound to the buttons component's label properties. The buttons component shows only the buttons whose type the current screen allows (the buttons, `buildButtons`: a Next type button needs a following screen, a Finish type button shows only on the last screen), and an enabled button with a blank label falls back to the component's own default words (the buttons, `buildManualButton`, `defaultButtonLabel`). The buttons are built once when the screen opens; a hidden button is not built at all.

### First screen: Back goes to the form's previous page

- **Page drives:** the page's Back arrives as type `BACK`. On the flow's first screen Flow has no earlier screen, so the buttons component runs **Next carrying the Back label** instead (the buttons, `handleMessage`, case `BACK`). The flow's Switch after that screen sees the Back label and ends the section without assigning outputs; the page matches the label and goes to the previous page, or back to the stages overview in Stages mode (the page, `_sectionFlowButton`, `processButtonClick`).
- **Section drives:** the template's Back button has **no type set, so it is a Next**, with "skip validation" on and the Back label (the template, `DockedButtons` `label2`, `bypassValidation2`). Same Switch, same result.
- **The asymmetry is deliberate:** Back ends the section with the record as it was; forward hands the edits back (the template, `Switch_Button_Clicked` description). On the form's first page there is no Back label, so the button hides.
- **Back is a Next under the hood**, so Flow validates that screen before it leaves. What "skip validation" covers, read in the source:
  - **A Flow Tool Kit form component: skipped**, whether the page or the section drives. Every form listens to every button message on the page and turns its own checks off when the click carries skip validation (`lwc/flowForm/flowForm.js`, `handleButtonMessage`, `validate`). The form's Prevent Validation Bypass setting is not read by `validate` in this version.
  - **A repeater: skipped only when the section drives.** It honours skip validation only from a buttons component in its own interview, and only while its Prevent Validation Bypass is off (the repeater, `handleButtonMessage`, interview Id check). The page's Back is published by the page, not by the flow, so a repeater on the first screen still validates when the page drives.
  - **A native screen input marked required** (radio buttons, a picklist, a text input): **never skipped.** The buttons component's skip validation only keeps its button enabled and rides in its message (the buttons, `buildButtons`, `buttonClickedPayload`); Back then runs Flow's own Next (`lwc/flowScreenBase/flowScreenBase.js`, `handleNext`), and the Flow runtime holds a Next on every empty required native input.
  - The packaged template matches this: its screen holds only the form and repeater components, no native input, and its Back and Save Progress buttons skip validation (the template, `bypassValidation2`, `bypassValidation3`).
- **So the first screen's native inputs are not required in Flow (the default).** The scaffold writes them not required and adds `Switch_<Screen>_Answers` on the forward path: it runs after the Back outcome has already ended the section, skips Save Progress, and sends a blank answer back to the screen with a message under the question. Required checks inside a Flow Tool Kit form component stay as they are. `flowsection.py check` warns on a required native input on the first screen.

### Middle screens: their own buttons are fine

- On a middle screen the forward button moves within the flow; its label never reaches the form, because the form reads the label only when the section finishes. A middle screen may carry its own words ("Add guests") and extra buttons.
- **Page drives:** the page's forward button keeps the page's label on every screen of the section, and each click moves one screen. On the form's last page that button says Submit while it only steps through the section. A multi-screen section usually lets the section drive for this reason.
- **Back on a middle screen** (page Back, or the section's Back with type `BACK`) is a real Flow Back to the previous screen (the buttons, `handleMessage`, `handleBack`).
- **Save Progress on a middle screen**, when it is not a screen action, is a Next carrying the Save Progress label: without a Switch outcome for that label after the screen, the flow just moves to the next screen and nothing is saved.

### Last screen: the page's forward label

- The Finish type button is bound to `buttonLabel_Finish`, which carries the page's forward label (the host). So the section's last screen shows the same words as the page: Next, Submit, Mark Complete.
- **Page drives:** the page's forward click on the last screen finishes the flow (the buttons, `handleMessage`, case `NEXT`: `allowNext ? handleNext : handleFinish`).
- **Section drives:** only a Finish type button can end it; a Next type button is not shown on the last screen.
- A typed label on the last screen still counts as forward (any label that is not the Back or Save Progress label is forward), but it no longer matches the page.

### The finish, routed by label

At the finish the page compares `buttonClickedLabel` with the labels it passed in, exact text (the page, `_sectionFlowButton`):
- the Back label: the page's Back (previous page; Return to the overview in Stages mode). Back never validates the page;
- the Save Progress label: the page's Save Progress (saves and stays);
- anything else: forward, which validates the page's other sections and moves on, or submits on the last page.

Then, if the page did not move (another section invalid, or Save Progress), the section restarts (above). The Back label is matched first, so a previous page named the same as a button label routes that button as Back.

## Records in and out

- **In:** `record` is the page's copy at launch; `relatedRecords` is this section's rows at launch. Neither is updated while the interview runs.
- **Out, during the run:** the form reads `record` and `relatedRecords` every time the flow reports, which is on start and on each new screen, not only at the finish (the host, `handleStatusChange`; the page, `handleFlowStatusChange`). An assignment to `record` or `relatedRecords` between two screens reaches the form at the next screen, and a later Back does not take it back. Assign the outputs only on the path that finishes forward (`Assign_Outputs`), as the template and the scaffold do.
- **Out, record:** only changed, non-blank fields are merged (above). The flow's form component output `recordVisibleFields` carries only the fields its form shows, so values hidden by that form's rules are not echoed (the template, `Assign_Outputs` description).
- **Out, rows:** the returned collection replaces this section's rows; rows of other sections are untouched (the page, `processRelatedRecordsChange`). Each row is stamped with `Internal_SectionId__c`, `Internal_PageId__c`, `Internal_Is_Related_Record__c`, the parent submission and, when missing, `UniqueId__c` and `ExternalId__c` (the section, `stampRelatedRecord`).
- **Removing a saved row: hand it back flagged, never just drop it (the default).** The flag is the standard `IsDeleted` field on Form Submission, used as an in-memory flag; a flow Assignment can set `<row>.IsDeleted` to true on a record variable. Only a row with an Id and `IsDeleted` true is deleted: the packaged save flow splits such rows into its delete list (`flows/Form_Submission_Upsert.flow-meta.xml`, `Filter_Delete_Records`), and the conversion's row save does the same with the rows in the submission's additional data (the row save, `process`). For a guest the page keeps the flagged rows in that data and the conversion deletes them, since a guest cannot delete (the page, `saveViaUpsertOverride`). A saved row simply left out of the collection is never deleted; it stays in the database as a child of the submission. A row with no Id was never saved: drop it. The repeater does all of this for you: its `prefillRecords` output keeps deleted saved rows flagged and drops deleted unsaved ones (the repeater, `updatePrefillAttributes`), and the scaffold hands that output back. `flowsection.py check` warns when `relatedRecords` is set from anything else, or shrunk with a Remove operator, and nothing in the flow sets `IsDeleted` true.
- **Who saves:** the page saves the submission and its rows (forward, autosave, Save Progress); the conversion creates the org's records after submit. The flow only hands values back, except for the Save Progress screen action, which runs the packaged save flow.

## Repeaters

**A repeater on a Flow Section screen** (the template's `DemoRepeaterCMP`, the scaffold's `<Screen>_Rows`):
- It is fed `relatedRecords` through `prefillRecords` and hands its rows back through its own `prefillRecords` output, about a quarter second after the last change (the repeater, `updatePrefillAttributes`). The page's one second delay on a click gives that time to land.
- Row edits never restart the flow and never reach the form until the flow assigns `relatedRecords` and reports (normally at the forward finish). Flow echoes the rows back into the repeater on every edit; only a change in which rows there are, their order or their deleted state resets its paging (the repeater, `prefillRecords` setter).
- New rows start from the row template **the flow builds**: the form does not seed rows for a Flow section (the section, `connectedCallback`, skipped for Flow). The template reads the section's Prefill Template, clears its Id and stamps the parent and the section (the template, `getTemplate`, `Assign_Template_Values`).
- Validation: the section's own forward click validates every row. A page Back on the first screen does not skip the repeater's validation (Back, above).
- Save Progress as a screen action passes the repeater's rows to the save; put the saved Ids back on the rows (buttons-and-saving.md).
- A repeater whose row design is given as JSON (Form (JSON)) rather than by form name could save every row blank: the row form was ready before the repeater's first render and the rows stayed read-only copies (the repeater, `renderedCallback`). Fixed in the package source after 5.3; until the release that carries it, name the row form component on a section's repeater.

**Rows belong to one section.** A child Form Submission (a repeater or table row) lives in exactly one section, stamped with that section's Id, so a Flow Section manages only its own rows and never needs another Repeater or Table section's records. Its returned rows replace only its own (the page, `processRelatedRecordsChange`).

**A flow inside a repeated row** is the second host (below): it runs once per row with that row's record and can only hold the row with `isValid`; it hands nothing back to the row.

## Validation and errors

- The page does not validate a Flow section: the section reports itself valid on first render and its `validate` looks only at forms, repeaters, tables and LWCs (the section, `renderedCallback`, `validate`). The flow holds the person on its own screen with required inputs and the Flow Tool Kit form's validation; while it holds, the flow never finishes and the page never moves.
- **Page drives:** the forward click goes to the section first, before the page validates anything (the page, `processButtonClick`, first line). When the section finishes, the page validates its other sections; if one fails, the page stays, shows its summary and restarts the section with the values just handed back.
- **Section drives:** the same, from the section's Finish.
- `isValid` is read only by the second host (a flow inside a form component), where false holds the form (`lwc/flowForm/flowForm.js`, `handleFlowIsValidChange`).
- **A fault in the flow** shows Flow's error inside the section. The page is not told: it acts only on a finish that carries a clicked label, so a page-driven click then appears to do nothing. Give every Get Records and action a fault path that ends on a screen saying what went wrong.
- **A finish without `buttonClickedLabel`** is ignored by the page, and the host has already hidden the finished interview: the person sees a spinner and the page does not move.

## Save Progress and navigation

| Click | Linear mode | Stages mode |
|---|---|---|
| Back (first screen) | Section ends without outputs; previous page | Section ends; the page saves if anything changed and returns to the stages overview |
| Save Progress | Section ends with outputs; the page saves (guest or embedded: insert or update of the submission; signed in: submission and stages) and stays; section restarts at its first screen with the saved values | Stage marked In Progress, saved; stays |
| Forward (last screen) | Section ends with outputs; the page validates, then the next page, or submit on the last page | The page validates, marks the stage Done, saves, returns to the overview |

Source: the page, `processButtonClick`. Save Progress as a **screen action** on the form's screen (the template's `Form_Upsert_Overridable` action and its two triggers) saves through `FlowToolKit__Form_Submission_Upsert` without ending the section, debounced by the click time, and feeds the saved record back into the form component (`transformationRecord`). With the page driving, the page's Save Progress arrives as a Next with the Save Progress label, not as the screen action, so it ends the section through the Switch instead.

## Review

On the review page the section gets `review` true and no trigger name; the page's Submit acts on its own and never waits for the section (the host, `drivenByPage`). The flow must route `review` to a read-only screen (the template's `Switch_Review` and `Review_Screen`; the scaffold's `Section_Review`). `hidePageButtons` is ignored there.

## Guest and portal users

- The flow runs as the person filling the form. A guest or portal user can run it only when it requires permission to run and their permission set grants it (access.md).
- The input probe and the section picklist read flow definitions without sharing, so a guest's form still learns the flow's inputs (the input probe, class comment on `Form_Flow_Utility`).
- Every Get Records in a flow that runs as the user reads as the respondent, including the template's two: the Form Template (which every form user can read) and the section's **Prefill Template**, a Form Submission record a guest may not be able to read. The page's own repeater sections detect an unreadable Prefill Template (the section, `isPrefillTemplateUnreadable`); a flow's Get Records simply finds nothing. Walk adding a row as a guest.
- `recordId` is blank for a guest's new submission; a guest's Save Progress from the page inserts or updates the submission directly (the page, `processButtonClick`).

### Guest prefill: sanitize every System Mode read (the default)

When a Flow Section that may run as a guest (or portal user) puts an org record into a screen or a form component, and the read has to run in System Mode (the guest's sharing cannot reach the record), the default pattern is:

1. **Get Records in System Mode**, filtered so it returns only the record or records this person is meant to see. The filter decides *which* records are exposed; nothing after it does.
2. **FLS Record(s) Sanitizer** (Flow Tool Kit action, Apex `FlowToolKit__DataSanitizer_Invocable`; inputs and outputs `Record` and `Record(s)`, any object). It runs `Security.stripInaccessible` with read access as the running user, so every field the respondent's profile and permission sets cannot read is removed (the sanitizer, `sanitizeRecords`). Assign its output back over the Get Records result, or into a new variable.
3. **Pass the stripped record** into the form component (`record`, `prefillRecords`, a data table's collection) or the screen's text, never the raw Get Records result.

So field access stays governed by permission sets and profiles: a guest who can read only First Name and Last Name on Contact receives only those two values, whatever the Get Records returned. Without step 2, a System Mode read hands every queried field to the browser, where it sits in the page's memory even when the form does not draw it. The sanitizer strips fields, not records: step 1's filter still decides which records a guest sees. A flow that runs as the user (the default for a Flow Section) already reads with the user's field access and needs no sanitizer. `flowsection.py check` warns when a System Mode Get Records reaches a screen without passing through the sanitizer. In flow metadata the action looks like this:

```xml
<actionCalls>
    <name>Sanitize_Contact</name>
    <actionName>FlowToolKit__DataSanitizer_Invocable</actionName>
    <actionType>apex</actionType>
    <dataTypeMappings><typeName>T__record</typeName><typeValue>Contact</typeValue></dataTypeMappings>
    <dataTypeMappings><typeName>U__record</typeName><typeValue>Contact</typeValue></dataTypeMappings>
    <inputParameters><name>record</name><value><elementReference>getContact</elementReference></value></inputParameters>
    <outputParameters><assignToReference>getContact</assignToReference><name>record</name></outputParameters>
</actionCalls>
```

For a collection use `records` and the `T__records` and `U__records` mappings.

## The second host: a flow inside a form component

A form component (Form Builder) section of type flow screen runs a flow named in its `flowApiName__c`. There the form passes only `record` (on the component's own object) and `SectionQualifiedApiName`, reads back only `isValid` (false holds the form), and hands no record back; it gets no labels and no trigger name, and its finish restarts the interview (`lwc/flowForm/flowForm.html`, `c-flow-form-screen-flow`; the host, `flowFinishBehavior`). Inside a repeater's row form it runs once per row with that row's record. Use it only for a self-contained check. Everything else on this page is about page sections, which is what this skill builds.

## What the packaged template carries

`(Form) Flow Section | Template` (`FlowToolKit__Form_Flow_Section_Template`) is a gallery template: Draft, marked as a template, never listed in the section picklist and never run. Create your flow from it (Flow Builder, New Flow, the Templates tab) or scaffold the same shape with `scripts/flowsection.py`. It holds:
- every variable above;
- a read of the Form Template (Allow Save Progress, Stages Mode) so the section's Save Progress button follows the template;
- a review route to a read-only screen;
- one sample screen with the package's sample form and repeater (replace both), the docked buttons component bound to the label variables, the page's trigger name and three hide formulas;
- Save Progress as a screen action that runs the packaged save flow, debounced by the click time;
- a row template built from the section's Prefill Template (Id cleared, parent submission and section Id stamped);
- a Switch after the screen: Back skips the outputs (the page goes back with the record as it was), forward assigns them.

Flows created from the template before 5.2 lack `buttonTriggerName` and `hidePageButtons`; they keep working with two bars. Add both variables, bind the buttons' Trigger Listener Name to `buttonTriggerName`, and add the hide formulas to adopt one bar.

## Traps

Each follows from the source above; `flowsection.py check` catches the ones marked *checked*.

| Trap | What happens | What to do |
|---|---|---|
| A System Mode read shown to a guest unsanitized | Every queried field reaches the guest's browser, whatever their field access | Pass it through the FLS Record(s) Sanitizer before any screen or component. *Checked* as a warning |
| A required native input on the first screen | Back from the first screen is a Next, and the Flow runtime holds it on an empty required native input whatever the buttons component says, so the person cannot go back | Leave the first screen's native inputs not required and ask for the answer on the forward path after the Back outcome (the scaffold's `Switch_<Screen>_Answers`). Flow Tool Kit form components skip their own checks for Back. *Checked* as a warning |
| A repeater on the first screen, page driving | The page's Back does not skip the repeater's validation; an invalid row holds Back | Let the section drive, or put the repeater on a later screen |
| No `buttonClickedLabel` at the finish | The page ignores the finish; the section shows a spinner and the page never moves | Assign the buttons component's `buttonClickedLabel` to the output on every path that finishes. *Checked* |
| A typed Back or Save Progress label | The finish carries words the page did not pass, so it counts as forward: Back submits, Save Progress moves on | Bind Back to `buttonLabel_Back` and Save Progress to `buttonLabel_SaveProgress`. *Checked* |
| Back type `BACK` on the first screen | Flow has no earlier screen, so the button is hidden; with the section driving, nobody can reach the previous page | Leave the first screen's Back as a Next carrying the Back label. *Checked* |
| No Finish type button | With the section driving, the last screen shows no forward button | Keep the Finish button bound to `buttonLabel_Finish`. *Checked* |
| No Switch for Back | Back from the first screen hands half-finished edits back | A Switch on the clicked label after the first screen; Back skips the outputs. *Checked* as a warning |
| No Switch for Save Progress on a middle screen | Save Progress moves to the next screen and saves nothing | A Save Progress outcome that assigns the outputs and ends. *Checked* as a warning |
| Outputs assigned before the last screen | The form takes them at the next screen; Back cannot undo them | Assign `record` and `relatedRecords` only on the forward finish |
| Two buttons components listening on one screen | Each one moves the flow on the page's click | One listening buttons component per screen. *Checked* as a warning |
| Two Flow Sections on one page | Both listen under the same trigger name, so one page click runs both, and each finish is handled as its own click | One page-driven Flow Section per page, or let each drive its own bar |
| A multi-screen section with the page driving | The page's Submit steps through the section one screen per click | Let the section drive (`hidePageButtons` true) |
| A previous page named like a button | The Back label is matched first, so that button routes as Back | Keep page names different from the button labels |
| Expecting live data from the page | The flow sees the page as it was when it opened | Read what it needs at the start; anything that must react while the person types elsewhere is an LWC |
| A saved row removed from the collection | It is not deleted; it stays as a child of the submission | Keep it with `IsDeleted` true, as the repeater does; drop only rows with no Id. *Checked* as a warning |
| Blanking a field from the section | Blank values are dropped from the returned record | Clear it with a rule on the form, or in the conversion |
| Input names in another case (`Record`) | The probe matches case for case, so the input is not passed and the flow is not listed | Keep the contract's exact spelling. *Checked* |
| Two long flow names that start alike | The cache key is the name without underscores, cut to 50 characters with `v4` in front, so names that agree in their first 48 letters (or differ only by underscores) share one cached answer (the input probe) | Keep Flow Section names short and distinct in their first 30 letters |
| Inputs changed after the form first ran the flow | The cache still lists the old inputs | Reset Form Cache |
