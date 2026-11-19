# Conversion pipeline architecture

How Flow Tool Kit turns a submitted Form Submission into records: one platform event, one dispatcher trigger, a controller that runs the rules in order, and one flow per object step, each in its own platform-event transaction.

In an org with the package installed every packaged name below carries the `FlowToolKit__` prefix: `FlowToolKit__Form_Submission__c`, `FlowToolKit__Form_Submission_Convert__e`, `FlowToolKit__Form_Submission_Convert_Process_Opportunity_Overridable`. Your own fields and flows never do.

## 1. The event chain

1. **Entry.** A record-triggered flow on Form Submission (`Form_Templates_Form_Submission_After_Insert_Update_Handle_Form_Submitted`) fires when Status is `Submitted`, Submission Date is set and the submission has no parent. It publishes one **Form Submission Convert** event with Event Name `Convert`, Start checked, the submission Id and the flow to run: the template's **Conversion Map Flow (Controller)** value, or on `Default` the Controller record of **Form Template Conversion Mapping Default**. Repeater and table rows never start themselves, and a submission without a Submission Date never converts by accident (for example from a data load).
2. **Dispatcher.** The package's Form Submission Convert trigger checks each event's flow: it must be an active autolaunched flow built in Flow Builder with one input, non-collection variable of the Form Submission Convert event type (any name). A flow that fails the check sets the submission's Conversion Status to Error and writes a Conversion Log row. That check is the whole dispatch contract.
3. **Controller.** `Form_Submission_Convert_Process_Form_Submission_Overridable` runs one rule per pass (section 4).
4. **Object steps.** Each converts one record, logs the outcome and hands control back through a dedicated Return to Controller action, which publishes the next Convert event at the template's controller. A repeater or table row returns to its parent. Every hop is a new transaction with fresh limits.
5. **Loop guard.** The dispatcher counts dispatches per submission and flow in each run, refuses past five with Conversion Status Error and a log naming the flow, exempts the controller, and resets the count on Start.

**Event fields:** Record Id (the submission), Flow API Name (the flow to run), Event Name (the dispatching element's API name, or `Convert` for Start and Return), Type (the API name of the submission lookup being converted, such as `FlowToolKit__Contact_1__c`), Conversion Status Field API Name (the paired status field), Start, Allow Repeat and Email Template Override. Type and Conversion Status Field API Name are how a step's logs know which fields to stamp; both blank means the log is written and nothing is stamped.

## 2. The Conversion Setup action

**Form Template | Conversion Setup** is the first element of every new conversion flow.

| Input | Meaning |
|---|---|
| `platformEvent` | The event the flow received |
| `debugRecord` | A Form Submission; Setup builds the event from it, so the flow runs in Flow Builder without publishing |
| `debugEventName`, `debugEventType` | The Event Name and Type to build in a debug run |

| Output | Meaning |
|---|---|
| `formSubmission` | The submission; for a repeater or table row, the row |
| `parentFormSubmission` | The parent, found by the parent lookup or the parent Id text stamp a guest save leaves |
| `formTemplate` | From the submission or its parent |
| `pageSection` | The section that captured a row; carries the per-row overrides |
| `allPageSections`, `relatedRecords` | Convert events only: sections with a conversion rule, and the rows still to convert |
| `matchingRuleNames` | Semicolon-separated matching rule names for the duplicate check |
| `updateMostConfidentMatch` | True when several matches should update the most confident one |
| `platformEvent` | The event, with Start cleared (or the one built in a debug run) |

Matching settings come from the section for a related row and from the template for the main submission. The status reset and the Start log run in the event trigger before any step. The older **Setup** subflow (`Form_Submission_Convert_Setup`) still ships for flows already built on it, with record outputs named `FormSubmission`, `FormTemplate`, `PageSection` and `ParentFormSubmission`.

## 3. The Convert/Log Event action

**Form Template | Convert/Log Event** has four modes, set by its `mode` input; its property editor shows only the inputs each mode reads.

- **Log** (the default): writes a Conversion Log row and optionally stamps a status field and a lookup. The only mode that reads `status` and `conversionStatus`. A blank `status` in Log mode means Error.
- **Start**: resets every conversion status to `Ready`, sets Conversion Status to `In Progress`, clears the log and publishes the first Convert event.
- **Convert to Record**: publishes an event at a chosen flow and stamps Type and Conversion Status Field API Name on it. Type may carry a person lookup purely to route the next flow (Campaign Member has no lookup of its own): a valid Id of another object type skips the lookup stamp silently.
- **Return to Controller**: publishes the return to the template's controller, for the parent when the record is a row. Always its own element, always silent.

The three dispatch modes write no log rows unless they fail, so a run reads: Start once, each outcome, then Finish.

Inputs: `mode`, `record` (the submission, required), `formTemplate`, `platformEvent`, `status`, `conversionStatus` (a Conversion Status value), `statusFieldApiName` and `lookupFieldApiName` (a field API name, or `--From Platform Event--` to read them off the event), `recordId` (the converted record), `elementApiName` (set by the property editor), `flowApiName` (Convert to Record target), `flowLabel`, `message`, `faultMessage`. The legacy `dispatchReturnEvent` input is honored for old clones; never set it in a new flow.

Behavior by outcome:
- **Start**: every discovered status field to `Ready`. Any accessible custom picklist on Form Submission whose values include all of the Conversion Status values counts, so a status field you add on the Conversion Status global value set is reset and finished with the rest.
- **Finish**: each status still blank or `Ready` becomes `Bypassed`; Conversion Status becomes `Complete`.
- **Error**: stamps the status field with the given value (or Error), sets Conversion Status to Error, and copies the error to the parent when the record is a row.
- **Success**: the status stamp and the lookup stamp are each optional; with neither it only writes the log. A converted row is stamped Complete on any success, which removes it from the related-row sweep.

A row's log is written twice, on the row and on its parent, so the parent shows every row's outcome.

## 4. Rules, types and statuses

**Conversion Type** (restricted, required, default `Bypass`): `Bypass`, `Lead(s)`, `Contact(s)`, `Account`, `Other`. It controls which Conversion Rules values a template can pick. Bypass or blank skips conversion.

**Conversion Rules** (restricted multi-select, dependent on Conversion Type): `Account`, `Account 👉 Set Billing Address`, `Account 👉 Set Shipping Address`, `Contact1`, `Contact1 👉 Set Mailing Address`, `Contact1 👉 Set Other Address`, `Contact1 👉 Add to Account`, `Contact1 👉 Create Campaign Member`, the same five for `Contact2`, `Lead1`, `Lead1 👉 Create Campaign Member`, `Lead2`, `Lead2 👉 Create Campaign Member`, `Create Case`, `Related Records`, `Opportunity 💰`.

**The controller's rule decision**: the first match wins, publishes one event and ends the pass. Each rule fires while its lookup is blank or its status is not terminal (`Created`, `Matched` and `Updated` are terminal) and the template includes the rule. Order: Account, Contact 1, Lead 1, Campaign Member 1, Contact 2, Lead 2 (both only when Contact 2's last name is filled), Campaign Member 2, Opportunity, Case, Additional Data, Related Records, Files, Confirmation email, then Finish. Gate a new rule on an exact-match formula, `INCLUDES({!Setup.formTemplate.Conversion_Rules__c}, 'MyRule')`: a decision condition cannot express INCLUDES, and Contains matches any value containing the word. Gate on the base rule value only; sub-rule values refine the mapping inside a step.

**Status fields** on Form Submission: the overall Conversion Status (`Ready`, `In Progress`, `Error`, `Bypassed`, `Complete`) and one per rule (Account, Contact 1 and 2, Lead 1 and 2, Campaign Member 1 and 2, Case, Opportunity, Order), all on the **Conversion Status** global value set: `Ready`, `In Progress`, `Matched`, `Multiple Matches`, `Created`, `Updated`, `Deserialized`, `Lead Converted`, `Error`, `Bypassed`.

**Tags are not conversion routing.** Data Conversion Tags (template, with a per-section override) are read by no packaged flow; they exist so your own record-triggered flows can branch on where a submission came from. Section Tag is a section's stable identifier for prefill and related-row routing.

## 5. Three ways to change what runs

1. **Configuration (the main one).** Each rule's flow comes from a formula field on Form Template: the rule's Conversion Map Flow picklist, or on `Default` the matching **Form Template Conversion Mapping Default** record (Controller, Primary_Contact, Alternate_Contact, Primary_Lead, Alternate_Lead, Case, CampaignMember, Opportunity, Order, FileUpload, Account). Add a picklist value whose API name is your flow's API name and select it on a template, or repoint the default record for the whole org. Sections have the same pair for their rows.
2. **A flow override.** Most packaged conversion flows are overridable: Save As in Flow Builder offers Save as flow override, and once your override is active everything that names the packaged flow runs yours. Best for the shared Upsert engines, to change matching or saving for every rule. The packaged name still appears in the picklists, the logs and the dispatch counts; to know an override ran, look for it on the packaged flow in Setup.
3. **A starter template.** `Form_Submission_Convert_Process_Contact_Template`, `Form_Submission_Convert_Process_Account_Template` and the controller starter `Form_Submission_Convert_Process_Form_Submission_Template` ship as Draft: clone, edit, activate, and point a picklist value at the clone (the value exactly the clone's API name, a friendly label). Every new flow starts from one of them (SKILL.md Step 3).

Which of 2 and 3: an override for a small tweak to a standard rule on every template, a new flow from a template when the logic or mapping is genuinely different or only some templates should run it (SKILL.md Decision A).

Never mix an override and a clone for one job.

## 6. Section settings and who reads them

| Section field | Read by |
|---|---|
| Conversion Rule (Bypass, Contact1 and its address rules, Contact2 and its address rules, Lead1, Lead2, Case) | Setup's section filter and the Related Records step |
| Conversion Map Flow | Sets the row's flow (a picklist dependent on Conversion Rule; the value must be included under the rule in Field Dependencies); a non-default value makes Related Records publish a dedicated event, a default one runs the packaged step inline. `Default` resolves through **FlowApiName (Related)** to the rule's Form Template Conversion Mapping Default record, never to the template's own Conversion Map Flow. Only Repeater and Table sections show it |
| Add to Account | The Contact engine links the row's Contact to the converted Account |
| Add to Campaign | The Contact and Lead engines chain a Campaign Member for the row |
| Contact Record Type, Case Record Type | The section's value wins, the template's is the fallback |
| Contact and Lead Matching Rules, Update Most Confident | Setup's matching outputs for rows |

A step reads these only through `Setup.pageSection`.

## 7. Packaged conversion flows

| API name (without the prefix) | Role |
|---|---|
| `Form_Templates_Form_Submission_After_Insert_Update_Handle_Form_Submitted` | Entry; publishes the Start event |
| `Form_Submission_Convert_Process_Form_Submission_Overridable` | The controller |
| `Form_Submission_Convert_Process_Form_Submission_Template` | Draft starter of the controller |
| `Form_Submission_Convert_Setup` | The older Setup subflow |
| `Form_Submission_Convert_Process_Account_Overridable` | Account step |
| `Form_Submission_Convert_Process_Contact_Primary_Default_Overridable`, `..._Contact_Alternate_Default_Overridable` | Contact 1 and Contact 2 steps |
| `Form_Submission_Convert_Process_Contact_Template` | Draft starter for a Contact mapping |
| `Form_Submission_Convert_Process_Lead_Primary_Default_Overridable`, `..._Lead_Alternate_Default_Overridable` | Lead 1 and Lead 2 steps |
| `Form_Submission_Convert_Process_Case_Overridable` | Case step |
| `Form_Submission_Convert_Process_Opportunity_Overridable` | Opportunity step; the submission's Opportunity lookup is the identity |
| `Form_Submission_Convert_Process_Campaign_Members_Overridable` | Campaign Member step |
| `Form_Submission_Convert_Process_File_Uploads_Overridable` | Files step |
| `Form_Submission_Convert_Process_Related_Records_Overridable` | Repeater and table rows |
| `Form_Submission_Convert_Deserialize_Additional_Data_Overridable` | Turns Additional Data into related rows |
| `Form_Submission_Convert_Upsert_Account_Overridable`, `..._Upsert_Contact_Overridable`, `..._Upsert_Lead_Overridable` | Shared engines: Apply Submission Field Maps, strip nulls, duplicate check, update or insert, log |
| `Form_Submission_Convert_Upsert_Campaign_Member_s_Overridable` | Existing member: status only; new member: template defaults |
| `Form_Submission_Convert_Upsert_File_Upload_Overridable` | Links uploaded files to the converted record |
| `Form_Submission_Convert_Utility_Send_Email_Overridable` | Confirmation email, called inline by the controller, so it ends without a return |
| `Form_Templates_Convert_Reprocess_Form_Submission` | Reprocess one submission |

An event-dispatched step returns through Return to Controller; a step called as a subflow returns by ending.

There is no packaged Order step: the Order lookup, status and default record are reserved. Treat Order like any other object the package does not convert ([new-object-rule.md](new-object-rule.md)).

## 8. Things to know

- An error in any step stops the pass: error outcomes publish nothing. Fix the data and Reprocess; Start resets the statuses and the loop count.
- The package's flow descriptions are the accurate contract for each packaged flow; read them in Flow Builder before cloning.
- A confirmation email that cannot be sent never fails the conversion; it is logged as an error row.
