# The preference, the mechanism and the family contract

Moved from this skill's SKILL.md, read on demand: Step 1: The mapping preference (paid and free), Step 2: Choose the mechanism, Step 3: The family contract for a new conversion flow.

## Step 1: The mapping preference (paid and free)

How a form's answers reach a record depends on the edition. Full standard: `_shared/standards/mapping-preference.md`.

**Paid edition (the default):**
- Place forms built on the **target object** (an Account form, an Opportunity form, a form on your own object) in the Form Template's page sections, and map each field to a Form Submission field on the Form Builder's **Form Template Mapping** tab. Choose **Apply these mappings to**: all records of that object, or one Form Submission lookup when the submission converts to two records of the same object.
- Keep the **packaged conversion flow** for the object. It runs **Form Submission | Apply Submission Field Maps** after its Transform, which fills every field the Transform left empty from those maps. A new field is then a Form Builder change, never a flow change.
- Hand-built Transform rows only for what a map cannot express: **calculated or combined values** (a name built from two answers, a date from a formula), **Campaign Members** (the action does not apply maps to Campaign Member conversion yet) and **record types** (Form Submission's record type fields are never offered as map targets).
- Every flow you build or clone keeps the Apply Submission Field Maps action right after the Transform and before Remove Null Values, with its Record output assigned back to the record variable (Step 3).

**Free edition:**
- Forms and form components work only on Account, Contact, Lead, Case, Campaign, Campaign Member and the Flow Tool Kit objects. A form on Opportunity or on your own object shows "Object Is Not Available Within the Free Version", so Form Template Mapping cannot carry those answers.
- Keep the current approach: sections built on Form Submission staging fields, and the conversion flow's Transform maps each staging field to its target. Keep the Apply Submission Field Maps action in every flow anyway, so an upgrade to paid needs no flow change.
- Conversion flows themselves run the same in both editions.

## Step 2: Choose the mechanism

| The requirement sounds like | Mechanism |
|---|---|
| "Map these answers to Contacts, Accounts, Leads, Cases or Opportunities" (paid) | Nothing in a flow: Form Template Mapping on the section's form (Step 1) and the packaged flow |
| "Change which fields map" for one template, and a map cannot express it | Clone the starter template (`Form_Submission_Convert_Process_Contact_Template`, shipped Draft), edit its Transform, activate, add a value to the matching **Conversion Map Flow** picklist whose API name is the clone's API name, and select it on the template (Step 6 wiring checklist) |
| "Change matching or saving for every template" (Person Accounts, a required field) | A flow override of the shared Upsert engine (Save As in Flow Builder offers **Save as flow override**). Only one active override exists per packaged flow |
| "Use a different flow org-wide for one rule" | Repoint the rule's record in **Form Template Conversion Mapping Default** (custom metadata) at your flow ([extension-patterns.md](extension-patterns.md), "Repointing packaged custom metadata") |
| "Convert to an object the package has no conversion flow for" (your own object, Order, Individual Application, a membership) | **A new object rule**: Step 3 and [new-object-rule.md](new-object-rule.md). This is the normal case, not a gap |
| "Convert a second record of an object the package already converts" (a Parent Account, a co-applicant) | A new rule with its own lookup and status pair that reuses the packaged Upsert engine unchanged: the controller's Convert to Record action stamps the field names on the event, and the engine writes whatever it is told |
| "Different mapping for one repeater or table section's rows" | The section's **Conversion Map Flow**; a non-default value makes Related Records publish a dedicated event so the custom flow runs in its own transaction |
| "Route rows to our own automation, not conversion" | The **Data Conversion Tags** stamp, which no packaged flow reads; your record-triggered flows branch on it |

Never use a flow override and a clone for the same job. Nothing in the pipeline raises sharing: duplicate rules are bypassed through DML options, not through system mode.

### Decision A: an override, or a new flow

Two different tools, and the person should choose with your recommendation in front of them.

| | A flow override of a packaged flow | A new flow, started from a package template |
|---|---|---|
| **Use it for** | A **small tweak** to a built-in standard rule (Contact, Account, Opportunity, Case, Campaign Member): one more field, a default value, a different matching setting, a required field the org enforces | Conversion logic or mapping that is **genuinely different**: another set of fields, another order, other records created, a different person (a minor, a co-applicant) |
| **Reach** | Org-wide, with no wiring: once active, everything that names the packaged flow runs yours, on every template | Only where a Conversion Map Flow picklist selects it: one template, or one Repeater or Table section (Step 6) |
| **How** | Open the packaged `..._Overridable` flow, Save As, **Save as flow override**. One active override per packaged flow | Step 3: clone the template, then wire it (Step 6) |
| **Costs** | Hidden: the packaged name still shows in picklists and logs; look on the packaged flow in Setup to know an override runs | One more flow to name and wire; templates that do not select it run the packaged flow as before |

Recommend one with the reason in a sentence, then ask, and build nothing until the person answers. For example: "This only adds a Preferred Name field to every Contact, a small tweak to the standard Contact rule, so I recommend an override of the packaged Contact flow. Override, or a new flow?" When the answer is a tweak on some templates only, that is a new flow: an override cannot be limited to some templates.

### Decision B: the packaged controller, or a project controller

The packaged controller (`Form_Submission_Convert_Process_Form_Submission_Overridable`) is big because it is mostly an example: it runs every packaged rule (Contacts, Leads, Account, Opportunity, Case, Campaign Members, files, related rows, the confirmation email) so that any template can switch any of them on. For a focused project it is often simpler to build a **project-specific controller** that runs only that project's steps, so an administrator can read the conversion top to bottom. For example, an Outbound Funds controller that verifies the Account, then the Contact, then creates or updates the Funding Request and its Review records, and nothing else.

| Lean toward | When |
|---|---|
| **A project controller** | One workflow; its steps are mostly the org's own objects (or records created from other new records); its order differs from the packaged order; only a few templates use it; administrators will maintain it |
| **The packaged controller, extended** | Many templates in the org use the standard rules; one to three new rules fit after the packaged ones; templates that do not select the new rule must behave exactly as before ([new-object-rule.md](new-object-rule.md), "Choose the controller") |
| **The packaged controller, unchanged** | Every object has a packaged rule; only mappings differ (Decision A) |

This is partly a matter of taste, so recommend with the reason, then ask: "This project converts only an Account, a Contact and two records of your own, in a fixed order, so I recommend a project controller an admin can read top to bottom. Project controller, or extend the packaged one?" Either way the controller starts from the controller template (Step 3) and reaches templates through **Conversion Map Flow (Controller)** (Step 6). Record the decision and its reason in the controller's description.

## Step 3: The family contract for a new conversion flow

**Start from the package's template. Always.** Every new conversion flow begins as a clone of a packaged template, never a blank flow and never a Save As of an `_Overridable` flow (that is how an override is made, Decision A). The templates ship as Draft, are never dispatched themselves, and carry the latest wiring: the Setup action, the Transform, Apply Submission Field Maps, the shared Upsert engine and the logs. Starting from them is what keeps every custom flow on the current pattern.

| You are building | Clone this template (API name, then label) |
|---|---|
| A controller (Decision B) | `Form_Submission_Convert_Process_Form_Submission_Template`, (Form Submission) Convert \| Process \| Form Submission \| Template |
| A Contact step (Contact 1, Contact 2, a row of people) | `Form_Submission_Convert_Process_Contact_Template`, (Form Submission) Convert \| Process \| Contact \| Template |
| An Account step | `Form_Submission_Convert_Process_Account_Template`, (Form Submission) Convert \| Process \| Account \| Template |
| A step for an object with no template (your own object, Opportunity, Case) | The Account template: it carries Setup, validation, the Transform, the Upsert call and both kinds of log. Replace the Upsert subflow call with your object's matching and save ([new-object-rule.md](new-object-rule.md)) |

In the org: Setup, Flows, search "Template", open it, **Save As**, **A New Flow**, with the name from "Naming and descriptions". Read the template's description before changing anything: it states the contract the clone must keep. After a package upgrade, compare your clone with the new template ([traps.md](traps.md), "Keeping cloned flows current").

Every flow you build follows these nine points. [exemplar-flows.md](exemplar-flows.md) shows each one in the packaged Opportunity flow.

1. **Inputs.** `PlatformEvent` (record, Form Submission Convert event, input) and `DebugRecord` (Form Submission, input) for debugging in Flow Builder. The dispatcher runs any active autolaunched flow with one input, non-collection variable of the Form Submission Convert event type; that is the whole dispatch contract.
2. **Setup first.** The first element is the **Form Template | Conversion Setup** Apex action, named `Setup`, with `platformEvent` = `PlatformEvent`, `debugRecord` = `DebugRecord` and the step's literals for `debugEventName` and `debugEventType`. Read everything from its outputs, never from copies in record variables: `Setup.formSubmission`, `Setup.parentFormSubmission`, `Setup.formTemplate`, `Setup.pageSection`, `Setup.allPageSections`, `Setup.relatedRecords`, `Setup.matchingRuleNames`, `Setup.updateMostConfidentMatch`, `Setup.platformEvent`. The older Setup subflow still ships for flows built on it; new flows never call it, so a finished flow has no subflow element naming it. Never read a parent through a relationship on these outputs (traps.md, "Action outputs").
3. **A paired lookup and status on Form Submission.** `<Rule>__c` (lookup to the target) and `Conversion_Status_<Rule>__c` (picklist on the packaged **Conversion Status** global value set). The Log action finds both on its own: Start resets them, Finish stamps the untouched ones Bypassed. The controller's Convert to Record action stamps both field names on the event, and the step's logs read them back with the `--From Platform Event--` sentinel.
4. **Transform** (`<Object>_Field_Map`). Always map `Id` from the submission's target lookup (a prefilled or earlier record updates, never duplicates) and `Latest_Form_Submission__c` from the submission Id when the target has that lookup. On a paid org it holds only the rows Step 1 lists; on a free org it holds the field map.
5. **Apply Submission Field Maps** right after the Transform: `formSubmission` = `Setup.formSubmission`, `record` = the Transform's record, `lookupField` = the Form Submission lookup this step fills (`My_Object__c`, or `FlowToolKit__Opportunity__c` for a packaged lookup), with the target object on both generic types. A map it cannot write is skipped and logged as a non-failing error row naming the field.
6. **Remove Null Values before any DML** (the **Strip Null Values** action), on the Apply action's Record output. Pass `nullableFieldsCsv` = `Setup.formTemplate.Nullable_Fields__c` so the template's **Nullable Fields** work (traps.md, "Nullable Fields"). Updates enrich, never blank.
7. **Matching for people and organizations.** The **Duplicate Check** action with `Setup.matchingRuleNames`: one match always updates; several matches update the most confident only when `Setup.updateMostConfidentMatch` is true; otherwise log `Multiple Matches` and stop. Write through the **Upsert (Bypass Duplicate Rules)** action with `bypassDuplicateRules` true, so the org's blocking duplicate rules cannot stop an unattended transaction. Copy OwnerId only when its key prefix is `005` (a user).
8. **A fault path on every action and DML element** to its own Log action in Log mode, status Error, named `Fault_<Operation>` and labelled "Log Error", with a message naming the element. Fault logs have no outgoing connector: the pass stops, the status stays non-terminal, and Reprocess picks it up.
9. **One success log per outcome, then one return.** Split insert and update into separate elements, each connected straight to its own `Log_Success_<Operation>` (Log mode, status Success, `conversionStatus` written as the literal `Created`, `Updated` or `Matched`, both field names `--From Platform Event--`, `recordId` from the real record variable). Every success path then reaches one `Return_to_Controller` action (mode Return to Controller; inputs `record`, `formTemplate`, `platformEvent`, `faultMessage` only). Chaining a second step (a person, then their Campaign Member) is a Convert to Record action, one per person slot, never a hand-built publish and never the legacy `dispatchReturnEvent` input. **Trace every success log to the return before calling the flow done**: a success log left without its connector stalls the whole conversion with no error.

**Fewest elements.** A Log action per path with its literals instead of assigning a status into a variable; a Create Records that writes its new Id into the Get Records output (`assignRecordIdToReference`) so the found and created paths read the same Id; Setup's outputs read directly. Use an Assignment or a variable only for a value that is set more than once and read later. The canon: Setup, `getRecord`, Switch, then Found: `Log_Success_Matched`, or Not Found: Create, `Log_Success_Created`, then the return, with no Assignment.
