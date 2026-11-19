# A new object rule: when the package has no conversion flow

Flow Tool Kit ships conversion flows for Account, Contact, Lead, Campaign Member, Opportunity, Case, files and repeater rows. Every other target (your own objects, Order, a Nonprofit Cloud Individual Application, a membership, a program enrollment) has no packaged flow. That is the normal case, not a gap: you build the rule, and the package runs it like its own.

A new rule is always two pieces of work:
1. **The step flow** that converts the record, built to the family contract (mechanism-and-contract.md, Step 3).
2. **A controller that runs it**: either the packaged controller extended with the new rule, or a custom controller for one workflow. Choose with the criteria below.

## What every new rule needs

| Piece | Example (Individual Application) | Notes |
|---|---|---|
| A lookup on Form Submission to the target | `Individual_Application__c` | Stamped by the step's success log |
| A status picklist on Form Submission | `Conversion_Status_Individual_Application__c` on the **Conversion Status** global value set | Start resets it, Finish stamps it Bypassed when the rule never ran. No default value |
| A Conversion Rules value | `Individual Application` | Add the value, then include it under its Conversion Type values in Field Dependencies (build-deploy-and-prefill.md, Step 7) |
| A lookup on the target back to Form Submission (recommended) | `Latest_Form_Submission__c` on Individual Application | Lets anyone open the submission from the record |
| The step flow | `Form_Submission_Convert_Process_Individual_Application_Overridable` | Label `(Form Submission) Convert | Process | Individual Application | Overridable` |
| A controller outcome and dispatch | `Convert_Individual_Application` rule and `Process_Individual_Application` action | In an extended or custom controller |
| Descriptions on every field and element | | Written as you create each one |

Describe the target object first (`sf sobject describe -s IndividualApplication -o <org-alias>`, or the connector in chat): its required fields, record types and picklist values decide the field map.

## Choose the controller

Packaged flows cannot be edited in place, so "adding a rule to the packaged controller" means running your own copy of it. Two shapes:

| | Extend the packaged controller | A custom controller |
|---|---|---|
| **What you build** | A clone of the controller template **(Form Submission) Convert \| Process \| Form Submission \| Template** (`Form_Submission_Convert_Process_Form_Submission_Template`, SKILL.md Step 3) with your rule added after the packaged rules, gated on its own `Includes_<Rule>` formula | A separate controller with the same contract (Setup first, status gating, one dispatch per pass, Finish), running only the rules this workflow needs, packaged steps included |
| **How templates reach it** | Test it on one template through a **Conversion Map Flow (Controller)** value, then make it the org default by repointing the Controller record of Form Template Conversion Mapping Default (a flow override of the packaged controller is for small tweaks only, SKILL.md Decision A; never both) | Only the templates that select its **Conversion Map Flow (Controller)** value |
| **Choose it when** | The new rule fits after the packaged rules; one to three new rules; many templates in the org may use them; templates that do not select the rule must behave as before (they do: each added rule runs only when a template selects it) | One workflow is mostly records only it converts (three or more such objects, or records created from other new records two levels down); its order contradicts the packaged order; or only a few templates use it and the rest of the org should run the packaged controller untouched |
| **What it costs** | After a package upgrade that changes the controller, copy the new packaged version again and re-add your rules rather than patching the old copy | One more state machine for an admin to read; it must keep up with packaged rule changes for the packaged steps it runs |

**No fixed default: recommend, then ask** (SKILL.md Decision B). The packaged controller is big because it is mostly an example; for a focused project a project controller that runs only its own steps is often the simpler thing for an administrator to read top to bottom. Give the person your recommendation with the reason, then let them choose. Reuse an existing extended or project controller in the org before making another, and record the decision and its reason in the controller's description, so templates added later follow it. Both shapes start from the controller template and reach templates through **Conversion Map Flow (Controller)** (`Conversion_Map_Flow_Controller__c`), whose value is exactly the controller's API name.

Two lighter options, when they fit:
- **No controller change.** A record with no status of its own that always follows another step (a junction, an affiliation) is a synchronous side-record subflow from that step (build-deploy-and-prefill.md, Step 4).
- **A second record of a packaged object** reuses the packaged engine through a new lookup and status pair; it still needs a controller outcome.

### Adding the rule to a controller

1. A Boolean formula: `Includes_Individual_Application` = `INCLUDES({!Setup.formTemplate.FlowToolKit__Conversion_Rules__c}, 'Individual Application')`. Never Contains: it matches any value holding the word.
2. A new outcome in the rule decision, after the packaged Case rule and before Additional Data, with:
   - the lookup blank, or the status not `Created`, `Matched` or `Updated`;
   - `Includes_Individual_Application` true;
   - the hold-back for every record it needs (here: Contact 1's lookup set, or the template does not include Contact 1; see extension-patterns.md, "Ordering").
3. A Convert to Record action for the outcome:

```xml
<actionCalls>
    <description>Sends the submission to the Individual Application step once the applicant's person account exists. The step creates or updates the application and returns here.</description>
    <name>Process_Individual_Application</name>
    <label>Process Individual Application</label>
    <actionName>FlowToolKit__FormSubmission_LogEvent_Invocable</actionName>
    <actionType>apex</actionType>
    <inputParameters><name>mode</name><value><stringValue>Convert to Record</stringValue></value></inputParameters>
    <inputParameters><name>flowApiName</name><value><stringValue>Form_Submission_Convert_Process_Individual_Application_Overridable</stringValue></value></inputParameters>
    <inputParameters><name>lookupFieldApiName</name><value><stringValue>Individual_Application__c</stringValue></value></inputParameters>
    <inputParameters><name>statusFieldApiName</name><value><stringValue>Conversion_Status_Individual_Application__c</stringValue></value></inputParameters>
    <inputParameters><name>elementApiName</name><value><stringValue>Process_Individual_Application</stringValue></value></inputParameters>
    <inputParameters><name>record</name><value><elementReference>Setup.formSubmission</elementReference></value></inputParameters>
    <inputParameters><name>formTemplate</name><value><elementReference>Setup.formTemplate</elementReference></value></inputParameters>
    <inputParameters><name>platformEvent</name><value><elementReference>Setup.platformEvent</elementReference></value></inputParameters>
    <inputParameters><name>faultMessage</name><value><elementReference>$Flow.FaultMessage</elementReference></value></inputParameters>
</actionCalls>
```

Your rule has no Flow API Name field on Form Template, so the action names the step flow directly. To let one template use a different step, create a second rule value, or read the flow name from a field of your own.

## Worked example: a Nonprofit Cloud Individual Application

**The ask.** Riverside Community Foundation runs grant programs in Nonprofit Cloud. An individual applies to a Funding Opportunity through a Flow Tool Kit form on the foundation's site. Each submission must produce, in order: the applicant as a **person account**, then an **Individual Application** linked to that person and to the Funding Opportunity, with the applicant's answers on it.

### 1. The person account comes first

An Individual Application's `AccountId` is the applicant's account, which for an individual is their person account, and `ContactId` is that person's contact. So the person must exist before the application converts.

- **With the Flow Tool Kit Nonprofit Cloud extension installed**, the Contact 1 rule converts the applicant to a person account (matching with a person account matching rule) and stores the person's `PersonContactId` in the submission's Contact 1 lookup. In household mode the submission's Account lookup holds the **household**, not the person, so never use it for `AccountId`.
- **Without the extension**, the packaged Contact step saves a plain Contact. In a person account org that is a contact with no account, not a person account. Build your own Contact 1 step that saves an Account with `IsPersonAccount`, the person account record type and the person's fields through the packaged Account engine (or install the extension).
- **The application waits for it.** The controller outcome holds back until Contact 1's lookup is set or the template does not include Contact 1.
- **Inside the step**, find the person account from the contact: Get Records `getPersonAccount` on Account where `PersonContactId` equals `Setup.formSubmission.FlowToolKit__Contact_1__c`. Read it with its own Get Records; never through a relationship on the Setup output.

**If organizations apply instead of individuals**, `AccountId` is the organization converted by the Account rule (`Setup.formSubmission.FlowToolKit__Account__c`), `ContactId` is Contact 1, and the hold-back waits for both. Check how the org's own grant process fills `AccountId` before choosing; some grantmaking designs put the applicant's institution there even for an individual.

### 2. The Funding Opportunity and application context

The form must know which Funding Opportunity it is for.
- Add a lookup `Funding_Opportunity__c` on Form Submission, with a description saying it is set by the link, not by the respondent.
- Fill it from the link: the Funding Opportunity page (or the portal's apply button) opens the form with the Funding Opportunity's Id in a URL parameter, and the template's **URL Parameter Mapping** maps that parameter to `Funding_Opportunity__c`. Fifteen-character Ids are accepted.
- A prefill flow with the Funding Opportunity as its entry record (build-deploy-and-prefill.md, Step 8) can refuse a closed opportunity before the form shows: `hasError` true and the message "This funding opportunity is not accepting applications."
- In the step, Get Records `getFundingOpportunity` by that lookup. Guard it: no Funding Opportunity means a fault log, not an application without one.
- Other records the org's own apply process creates around an application (an application participant for the applicant with a participant role, an action plan from the Funding Opportunity's action plan template) become follow-ups of this step: form-agnostic utility subflows called from the post-save router, each run once (extension-patterns.md). Mirror what the org's existing apply flow does; do not invent extra records.

### 3. The field map

| Individual Application field | Source | How (paid edition) |
|---|---|---|
| `Id` | `Setup.formSubmission.Individual_Application__c` | Transform row (identity: a rerun updates) |
| `AccountId` | `getPersonAccount.Id` | Transform row (from the conversion) |
| `ContactId` | `Setup.formSubmission.FlowToolKit__Contact_1__c` | Transform row (from the conversion) |
| `FundingOpportunityId` | `Setup.formSubmission.Funding_Opportunity__c` | Transform row (context from the link) |
| `RecordTypeId` | `getRecordType.Id` (the org's grant application record type, when it uses one) | Transform row (record type) |
| `Status` | `IF(ISBLANK({!Setup.formSubmission.Individual_Application__c}), 'Submitted', null)`, with the value the org uses for a new application | Transform row (calculated; on create only, so a rerun never moves a reviewed application back) |
| `Category` | the org's value for a grant application, same create-only formula | Transform row (calculated) |
| `AppliedDate` | `DATEVALUE({!Setup.formSubmission.FlowToolKit__Submission_Date__c})` | Transform row (calculated) |
| `ApplicationName`, when the org fills it | `LEFT({!getFundingOpportunity.Name} & ' - ' & {!Setup.formSubmission.FlowToolKit__Contact1_Last_Name__c}, 80)` (check the field's length) | Transform row (combined) |
| `Latest_Form_Submission__c` | `Setup.formSubmission.Id` | Transform row |
| `RequestedAmount`, `FundingRequestPurpose`, `Description` and the org's own application questions | the applicant's answers | **Form Template Mapping**: build the application questions as a form on Individual Application, place it in a page section, map each field to a Form Submission field, and apply the map to the Individual Application lookup. Apply Submission Field Maps fills them |

A null from a create-only formula is removed by Remove Null Values, so the update path leaves Status and Category alone. Describe the object to see which fields are required in this org (Status and Category are in many) and give each one a source or a fallback.

**Free edition.** Individual Application is not one of the free edition's form objects, so its questions are sections built on Form Submission staging fields, and each answer is a Transform row (`RequestedAmount` from `Requested_Amount__c`, and so on). Everything else is the same.

### 4. The step flow

Clone the Account template (`Form_Submission_Convert_Process_Account_Template`, SKILL.md Step 3) and replace its Upsert Account call with the application's own lookups and save, keeping Setup, the Transform, Apply Submission Field Maps, Remove Null Values and the logs it already carries:

```
Setup
  -> getPersonAccount (Account where PersonContactId = Contact 1 lookup)
  -> getFundingOpportunity (by the Funding Opportunity lookup)
  -> Switch (Ready to convert?)
       No person account: Fault_Missing_Person_Account (Log Error, "Individual Application needs Contact 1's person account")
       No Funding Opportunity: Fault_Missing_Funding_Opportunity (Log Error)
       default: continue
  -> getRecordType (when the org uses one)
  -> Individual_Application_Field_Map (Transform)
  -> Assign_Mappings_to_Individual_Application
  -> Apply_Source_Object_Mappings (lookupField Individual_Application__c)
  -> Remove_Null_Values (nullableFieldsCsv = the template's Nullable Fields)
  -> Switch (Insert or Update?) on IndividualApplication.Id
       Update: Update_Individual_Application -> Log_Success_Update (Updated)
       default: Insert_Individual_Application -> Log_Success_Insert (Created)
  -> Switch (After Save) router: participant and other follow-ups, each once
  -> Return_to_Controller
Every Get, action and DML element: a fault path to its own Fault_<Operation> (Log Error).
```

The two guard faults stop the pass with the rule non-terminal, so once the data is fixed, Reprocess finishes the application. Both success logs stamp the Individual Application lookup and status from the event (`--From Platform Event--`), which is what lets the controller move on.

### 5. Template settings

- Conversion Type: the type the template already uses (with the extension, `Contact(s)` or `Other`); the `Individual Application` rules value must be included under it in Field Dependencies.
- Conversion Rules: `Contact1` and `Individual Application` (plus any address or campaign sub-rules).
- Matching: a person account matching rule for Contact 1.
- Conversion Map Flow (Controller): your extended controller's value while testing; `Default` once the Controller record points at it.

### 6. Check it

Submit a test application from the site as a guest, then read the submission's Conversion Log: Start, the person account Created or Matched, the Individual Application Created, Finish. Open the application: AccountId is the person account, ContactId the person, FundingOpportunityId the opportunity, and the mapped answers are filled. Submit the same person again for a second opportunity: the person matches, a second application is created. Reprocess the first submission: the application is Updated, not duplicated, and its Status is unchanged.
