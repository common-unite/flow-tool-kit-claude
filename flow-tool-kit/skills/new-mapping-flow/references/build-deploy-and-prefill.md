# The hard parts, deploying, the spec, prefill and naming

Moved from this skill's SKILL.md, read on demand: Step 4: The hard parts, Step 5: Run-as, debugging and recovery, Step 6: Deploy, wire, activate and check, Step 7: The spec, before building, Step 8: Prefill flows, Naming and descriptions.

## Step 4: The hard parts

Recipes for each are in [exemplar-flows.md](exemplar-flows.md) and [extension-patterns.md](extension-patterns.md).

- **Matching.** A single match always updates; Update Most Confident changes only what happens with several. With several and the setting off, the step logs `Multiple Matches`, stops and waits for a person to merge or pick, then Reprocess. Related rows read the section's matching rules and confidence setting; main submissions read the template's. A record whose Id is already known (a prefill, an earlier run) skips matching and updates.
- **Record types.** The section's record type falls back to the template's; the `-- Use Default --` value skips; an active-record-type lookup validates; a stale name falls back to the default instead of failing. The packaged Contact engine finds the record type but saves the Contact without `RecordTypeId`, so the Contact takes the running user's default record type and **a duplicate rule with a Record Type condition never matches a conversion**. Either take the Record Type condition off the duplicate rules conversions should use, or set `RecordTypeId` in your own clone from a Get Records on RecordType.
- **Opt-in address groups.** `INCLUDES(Conversion_Rules__c, 'Contact1 👉 Set Mailing Address')` style formulas gate a whole group of fields; related rows check the section's single-value Conversion Rule instead.
- **Fallback chains.** `BLANKVALUE(submission, BLANKVALUE(prefill template, parent))`, as the Campaign Member step resolves its Campaign; Lead's Company chain ending in first and last name for a required field.
- **Side records.** A linked record with no lookup and status pair of its own (a junction such as an affiliation) is a synchronous subflow from the step that owns it, returning a `Success` output, stamping no status and publishing no event. Use a Convert to Record dispatch only for a tracked rule.
- **Ordering.** A rule that needs a record converted later holds back in the controller; it is never a reordered packaged rule ([extension-patterns.md](extension-patterns.md), "Ordering").
- **Transform limits.** A Transform `Map` of a multi-select picklist writes nothing and raises nothing: map multi-selects in an Assignment. An `InnerJoin` returns no rows when any join-key column is null, and the step still logs Success. A Transform re-checks the running user's field access on rows that come out of an Apex action, so it works for you and fails as the Automated Process user: loop with an Assignment over Apex action output instead.
- **Several child rows to several records.** Join on the build side (carry each child's Id into the target collection before the DML), never stamp afterwards: stamping collects the parent Id once per child and fails on duplicate Ids, yet passes every single-row test. Map both `Latest_Form_Submission__c` (the parent) and `Latest_Form_Submission_Child__c` (the row). Test with more than one row.
- **Loop cursors.** Never read a collection filter's `currentItem_*` variable after the filter ends; inside a loop, read the loop variable.
- **A step Flow cannot do well** (parsing text, totals across many records, matching or sorting large collections, a call to an outside service): hand it to **new-invocable** with the object, the inputs and the output it must return (the work list's `new-invocable` handoffs), then call the action before the Transform and map its output. Check first that a formula, a Transform or an existing action cannot do it.

## Step 5: Run-as, debugging and recovery

- **Who runs it.** Conversion runs as Salesforce's **Automated Process** user unless the org names a running user for the Form Submission Convert trigger. That user has no profile and takes no permission sets: an Apex action that queries in user mode, or a class saved at API 67 or later that runs plain queries, sees no custom metadata rows and none of the fields it lacks access to. Either test the action as that user, or name a running user: deploy a **PlatformEventSubscriberConfig** for `FlowToolKit__Form_Submission_Convert` with an active administrator's username, then **Suspend** and **Resume** the subscription (Setup, Platform Events, Form Submission Convert, Subscriptions, Manage). The trigger still runs in system context. The file is in [traps.md](traps.md).
- **Debugging.** Set a trace flag on the running user (Automated Process by default), or run the flow in Flow Builder with Setup's Debug Record, Debug Event Name and Debug Event Type inputs, which builds the event for you.
- **A green log is not proof.** The Conversion Log records that a step finished, not that it changed anything: a Transform with no rows, a join that matched nothing or a map that wrote nulls all log Success. Confirm `SystemModstamp` moved on the target and spot-check field values.
- **The loop guard.** The dispatcher refuses the sixth dispatch of the same flow for the same submission in one run and logs an Error naming the flow. Logs that read fine while statuses stay `Ready` mean a step is not stamping its status, almost always a hand-written Log call missing the `--From Platform Event--` sentinel.
- **Recovery and reruns.** Fix the data, then **Reprocess** the submission. For many submissions, **Reprocess All** (Form Template actions) reruns every submitted submission of that template, and **Reprocess Selected** (Form Submissions list view) reruns the ticked ones. Both show a summary first: how many run, how many already converted (skipped unless included) and how many are already queued. Submissions then convert one at a time, in the order they arrived, so two submissions for the same new person never both create that person. An org upgraded from an earlier version adds both buttons to its layouts by hand: Reprocess All on the Form Template page layout (Mobile and Lightning Actions), Reprocess Selected on Form Submission, Search Layouts, List View buttons.

## Step 6: Deploy, wire, activate and check

1. Retrieve and compare before you deploy: never overwrite a flow someone changed in the org since your copy.
2. Deploy the controller, its object steps and any shared engine they use **as one set**, and activate them together. A step whose logs read field names from the event, running under a controller that does not stamp them, logs but never stamps status, and the loop guard trips.
3. A deployed flow lands as **Draft** unless the org deploys flows as active (Setup, Process Automation Settings). Activate each one after the deploy, or the previous version keeps running.
4. Open every flow once in Flow Builder in Auto-Layout, save, retrieve it again and diff: Flow Builder can write raw field IDs and strip action outputs ([traps.md](traps.md), "Flow Builder round trip").
5. **Wire every new flow** (an override needs no wiring) with the checklist below.
6. Submit a test form, read the Conversion Log, and confirm the records changed (Step 5).

### The wiring checklist for a new flow

A new flow runs only where a **Conversion Map Flow** picklist names it. The package reads the picklist **value** (its API name) as the flow to run, through the read-only **FlowApiName** formula beside it; the **label** is only what an administrator picks. So:

- **The value is exactly the flow's API name.** Character for character and case: your own flow without a prefix (`Form_Submission_Convert_Process_Contact_Primary_Contact`), a packaged flow with `FlowToolKit__`. A label typed as the value ("Primary Contact") saves fine and stops every conversion that selects it.
- **The label is friendly.** Plain words, no underscores: "Primary Contact", "Child / Minor".

**The fields, on Form Template** (`FlowToolKit__Form_Template__c`; on the record page under Data Conversion Settings, Advanced Data Mapping Overrides). Each is a restricted picklist with one packaged value, `Default`. `Default` runs the flow named by that rule's record in the **Form Template Conversion Mapping Default** custom metadata type, and the FlowApiName formula shows which flow resolves.

| Picklist (label, API name) | Chooses the flow for | `Default` record, and the packaged flow it names | Shows the result |
|---|---|---|---|
| Conversion Map Flow (Controller), `Conversion_Map_Flow_Controller__c` | The controller (Decision B) | Controller: `Form_Submission_Convert_Process_Form_Submission_Overridable` | FlowApiName (Controller), `FlowApiName_Controller__c` |
| Conversion Map Flow (Contact1), `Conversion_Map_Flow_Contact1__c` | Contact 1, the primary person | Primary_Contact: `Form_Submission_Convert_Process_Contact_Primary_Default_Overridable` | `FlowApiName_Contact1__c` |
| Conversion Map Flow (Contact2), `Conversion_Map_Flow_Contact2__c` | Contact 2 | Alternate_Contact: `Form_Submission_Convert_Process_Contact_Alternate_Default_Overridable` | `FlowApiName_Contact2__c` |
| Conversion Map Flow (Lead1), `Conversion_Map_Flow_Lead1__c` | Lead 1 | Primary_Lead: `Form_Submission_Convert_Process_Lead_Primary_Default_Overridable` | `FlowApiName_Lead1__c` |
| Conversion Map Flow (Lead2), `Conversion_Map_Flow_Lead2__c` | Lead 2 | Alternate_Lead: `Form_Submission_Convert_Process_Lead_Alternate_Default_Overridable` | `FlowApiName_Lead2__c` |
| Conversion Map Flow (Account), `Conversion_Map_Flow_Account__c` | Account | Account: `Form_Submission_Convert_Process_Account_Overridable` | `FlowApiName_Account__c` |
| Conversion Map Flow (Opportunity), `Conversion_Map_Flow_Opportunity__c` | Opportunity | Opportunity: `Form_Submission_Convert_Process_Opportunity_Overridable` | `FlowApiName_Opportunity__c` |
| Conversion Map Flow (Case), `Conversion_Map_Flow_Case__c` | Case | Case: `Form_Submission_Convert_Process_Case_Overridable` | `FlowApiName_Case__c` |
| Conversion Map Flow (CampaignMember), `Conversion_Map_Flow_CampaignMember__c` | Campaign Members | CampaignMember: `Form_Submission_Convert_Process_Campaign_Members_Overridable` | `FlowApiName_CampaignMember__c` |
| Conversion Map Flow (File Upload), `Conversion_Map_Flow_FileUpload__c` | Uploaded files | FileUpload: `Form_Submission_Convert_Process_File_Uploads_Overridable` | `FlowApiName_FileUpload__c` |
| Conversion Map Flow (Order), `Conversion_Map_Flow_Order__c` | Order | Order: reserved, no packaged Order flow ships, so a template that converts Orders selects your own flow here | `FlowApiName_Order__c` |

**The per-component setting, on Form Template Page Section** (`FlowToolKit__Form_Template_Page_Section__c`, the section that places a form component on a page). Only **Repeater and Table** sections have it (Form Builder, the section's settings, Conversion Rules), because only their rows convert one by one:

| Field | What it does |
|---|---|
| Conversion Rule, `Conversion_Rule__c` | What each row converts into: `Bypass` (the default), `Contact1`, `Contact2` (each with Set Mailing Address and Set Other Address variants), `Lead1`, `Lead2`, `Case` |
| Conversion Map Flow, `Conversion_Map_Flow__c` | The flow for this section's rows. A **dependent** picklist: Conversion Rule controls it |
| FlowApiName (Related), `FlowApiName_Related__c` | Read-only: the flow the rows run. On `Default` it is the rule's **Form Template Conversion Mapping Default** flow, **not** the template's Conversion Map Flow: a Repeater left on `Default` ignores the template's custom Contact 1 flow |

**Checklist**, in order, for each new flow:
1. The flow is deployed and **active** (step 3 above). A picklist value can name a flow that does not exist or is inactive; the conversion then fails at that step.
2. **Add the value** to the field for its rule: Setup, Object Manager, Form Template (or Form Template Page Section), Fields, the Conversion Map Flow field, Values, New. Enter the flow's API name, save, then **Edit** the value and change only its **Label** to the friendly name. Typing the friendly name first is how a label ends up as the value.
3. **A section value needs its dependency**: Form Template Page Section, Field Dependencies, Conversion Rule and Conversion Map Flow, Edit, and include the value under every Conversion Rule it serves. Without it no section can select the value.
4. **A new Conversion Rules value** on Form Template (a new object rule) takes two operations, because Conversion Rules depends on Conversion Type: add the value, then include it under the Conversion Type values it belongs to (usually `Other` and the type the template uses) in Form Template's Field Dependencies. Doing only the first is the classic failure: the value reads as active, yet every save that sets it fails with `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST`.
5. **Set the defaults.** On each Form Template that should use the flow, pick the friendly label in its Conversion Map Flow field and check that the FlowApiName field beside it shows the flow's API name. For a Repeater or Table section, set its Conversion Rule, then its Conversion Map Flow. To make a flow every `Default` template's flow instead, repoint the rule's Form Template Conversion Mapping Default record ([extension-patterns.md](extension-patterns.md), "Repointing packaged custom metadata").
6. **Check the wiring before anyone types it into Setup**: put it in `mapping-spec.json` under `wiring` (format in [work-list.md](work-list.md)) and run `python3 scripts/wiring_check.py _forms/<slug>/mapping-spec.json` (`mapping_plan.py` runs the same check). It fails on a value that is not exactly the flow's API name (naming the cause: a label typed as the value, a case difference, a missing or extra prefix, stray spaces), a section value with no Conversion Rule dependency, a section override on a section that is not a Repeater or Table, and a default naming a value not added yet; it warns on an unfriendly label and on a Repeater left on `Default` under a rule the template overrides.

Adding values through metadata instead: retrieve the field fresh, add the value and its value settings, deploy. Never deploy an old copy of a managed picklist field: it replaces the value set and deactivates values the package added since. A deactivated value still exists, so it is not added again; reactivate it in Setup. Add the values **before** any data that uses them (a Form Template insert fails on the restricted picklist otherwise).

**Example** (invented). A clinic's registration template converts the parent or guardian through a custom Primary Contact flow, while its Children repeater converts each child through a Child / Minor flow that maps only name, birthdate and the household link, so no sensitive health answers are stored on a minor's Contact:

| Where | Field | Value (API name) | Label |
|---|---|---|---|
| Form Template | Conversion Map Flow (Contact1) | `Form_Submission_Convert_Process_Contact_Primary_Contact` | Primary Contact |
| Form Template Page Section | Conversion Map Flow, included under Conversion Rule `Contact1` | `Form_Submission_Convert_Process_Contact_Child_Minor` | Child / Minor |
| The Registration template | Conversion Map Flow (Contact1) | Primary Contact | |
| Its Children section (Repeater) | Conversion Rule, then Conversion Map Flow | `Contact1`, then Child / Minor | |

Both flows are clones of the Contact template (Step 3). Left on `Default`, the Children rows would run the packaged Contact flow, not Primary Contact and not Child / Minor.

## Step 7: The spec, before building

Capture for each new or changed mapping. Items the work list already holds (Step 0) are not asked again; the answers the plan has no key for go in `mapping-spec.json`, and the work list is run again.
1. **Source**: which submission fields or sections (main submission or repeater rows; section tags involved).
2. **Target**: object, record type rules, and any new paired lookup and status fields.
3. **Identity**: matching rules, and what happens on several matches (most confident or a person decides).
4. **Field map**: source, target, how (form map, Transform row, formula), on create only or always. On a paid org most rows are form maps.
5. **Trigger point**: which Conversion Rules value gates it, where it sits in the controller order, and what it waits for.
6. **Mechanism** from Step 2, with Decision A (override or new flow) and Decision B (which controller) each recommended with its reason and answered by the person, and whether a packaged engine is reused.
7. **Rollout**: picklist values (value = the flow's API name, a friendly label) and which templates and sections select them, Form Submission fields, permission sets, the running user, Reprocess for existing submissions.

**Picklist values you add.** The Conversion Map Flow picklists and Conversion Rules are restricted packaged picklists, and you can still add values to them in your own org without a package release. How, with the exact fields: Step 6, "The wiring checklist for a new flow". Record each value, its label and its defaults in the spec's Rollout and in `mapping-spec.json` `wiring`.

**What only a package release changes.** The packaged controller's own rules and their order, the Conversion Type picklist that controls Conversion Rules and its values, the formula behind each Flow API Name field on Form Template, and the packaged values themselves belong to Flow Tool Kit. Treat them as fixed: put a new rule under the existing Conversion Type values, extend the controller in your own flow (Step 2), and point the template at your flow through the values you add.

## Step 8: Prefill flows

A prefill flow fills a new submission from existing records before the form shows. Build one per **entry record** (the record the link identifies: an Account, a Contact, a Funding Opportunity), shared by every template that starts from it, never one per form.

- **Contract** (the packaged `Form_Prefill_w_Screen_Template`): a screen flow; input `record` (the new Form Submission, URL parameters already applied); outputs `prefillRecord`, `prefillRelatedRecords` (the repeater and table rows), `hasError` and `errorMessage` (shown instead of the form) and `stages`. The template names the flow in **Prefill Flow API Name** and maps each URL parameter to a Form Submission field in **URL Parameter Mapping**.
- **Entry key.** Map the link's parameter to the submission lookup for the entry record and Get Records by it; a custom entry object needs its own lookup on Form Submission. Pass the record Id in the link rather than a number a person could guess. When the link can only carry a number (a search form), keep one Get Records that finds the record from it, and flag it.
- **Filling.** Use the **Prefill From Mapped Record** action, never a field-by-field Transform: Single Record per fetched record, chained; Related Records for a collection into a repeater or table (by the section's Section Tag). Several lookups that each exclude the previous one ("the second, third and fourth contact") become one Get Records collection into one Related Records call.
- **Shared core, template extras.** The shared flow covers the entry record and what most templates read from it; a template that needs more gets its own prefill flow that calls the shared one as a subflow, then adds its lookups.
- **Strip what the person may not read (default for guest and portal prefill).** A prefill flow that runs in System Mode can read every field, and whatever it hands the form reaches the browser, shown or not. So every fetched record goes through the package's **FLS Record(s) Sanitizer** action (`DataSanitizer_Invocable`, inputs Record or Record(s)) before Prefill From Mapped Record or any form or record component receives it: it removes every field the running user has not been granted read access to. Access is then controlled the normal way, by permission sets and profiles: a guest that can read only First Name and Last Name on Contact gets only those. Query only the fields the form needs as well. sf-guest-audit flags a System Mode Get Records that reaches a component without this step.
- **Errors.** Not found, not eligible, already submitted: set `hasError` and `errorMessage` with the sentence the person should read, and return. A screen in a prefill flow is only for a choice the person must make first (which of their records to renew), never for showing data.
- **Access.** A prefill flow runs as the person opening the form, unlike a conversion flow (Automated Process or the named running user). Hand every prefill flow, and every subflow it calls, to **flow-access-fix** once per audience in `flow-tool-kit.json` (guest, portal, internal; the work list's `flow-access-fix` handoffs): it restricts the flow, grants it in each audience's own permission set and proposes the guest sharing rule for the entry record. A guest who resumes a saved form needs flow-access-fix's own copy of the prefill flow, not yours.

## Naming and descriptions

Follow section 6 (Naming) and section 2 (Flows) of `_shared/standards/documentation.md`. In short:
- **Conversion flow names stay in the package's pattern**: API `Form_Submission_Convert_Process_<Object>[_<Variant>_Default]_Overridable` or `Form_Submission_Convert_Upsert_<Object>_Overridable`, label `(Form Submission) Convert | Process | <Object> | Overridable` (Upsert flows say Upsert, never Process). The `flowLabel` input on every Log action reads `Convert | Process | <Object>` or `Convert | Upsert | <Object>`: it is what admins read in the log list. Utility subflows: label `Utility | <Action> <Object>`, API `Utility_<Action>_<Object>`.
- **A clone of a template** (Step 3) keeps the template's label prefix and API name and replaces `Template` with its purpose: `(Form Submission) Convert | Process | Contact | Primary Contact`, API `Form_Submission_Convert_Process_Contact_Primary_Contact`; a project controller `(Form Submission) Convert | Process | Form Submission | Funding Requests`, API `Form_Submission_Convert_Process_Form_Submission_Funding_Requests`. Its Conversion Map Flow picklist label is the purpose alone ("Primary Contact"), its value the API name.
- **Elements**: Get Records `get<WhatItReturns>`; every decision labelled `Switch`, the meaning in its outcome labels; Create, Update and Delete named after the object; `Assign_*` or `Set_*`; Transforms `*_Field_Map`; actions verb-named; `Log_Success_<Operation>`; faults `Fault_<Operation>` labelled "Log Error"; `Return_to_Controller`; `Process_<Object>` for a Convert to Record chain. A cloned packaged flow keeps the packaged element names; elements you add follow these.
- **Variables** keep the contract names exactly (`PlatformEvent`, `DebugRecord`, and on older clones `FormSubmission`, `FormTemplate`); everything else `Pascal_Snake` with no type prefix.
- **Descriptions on everything**: the flow (what it is for, where it fits, what to clone or override to change it), every element, variable, formula and constant, written for the administrator who opens it next, summary first, the reason rather than the mechanics, no issue numbers or history. Write them in the same step that creates the element.
- When you rename an element, update every reference: connectors, `targetReference`, `elementReference`, `assignToReference`, `inputReference`, `collectionReference` and every `{!...}` inside formulas and Transform values. A missed formula reference deploys and fails at run time.
