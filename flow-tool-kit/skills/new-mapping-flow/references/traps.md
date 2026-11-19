# Traps, and keeping cloned flows current

Each trap here has made a conversion run clean and write nothing, or stop every conversion in an org. Check the relevant ones before calling a flow done.

## Flow Builder round trip

Flows written as XML and then opened in Flow Builder get rewritten silently, and still deploy. After every Builder save, retrieve the flow and check:

- **Raw field IDs.** A field picked in Builder can be saved as its 15-character ID (starting `00N`) instead of its API name. It works in the org it was built in and breaks everywhere else. Search the flow files for `00N` before deploying anywhere else.
- **Stripped action outputs.** Builder removes hand-written `outputParameters` from Apex actions (such as Remove Null Values writing back into the record variable). Nothing errors; the variable is simply never filled, and the flow does half its job. Diff the flow after every Builder save and put the outputs back.
- **The `--From Platform Event--` sentinel.** The Log action's property editor fills `statusFieldApiName` and `lookupFieldApiName`; hand-written XML must pass `--From Platform Event--` itself. Without it the log row is written, no status is stamped, the rule never finishes and the loop guard stops it at five dispatches. Logs that read fine with statuses stuck at `Ready` are this.
- **Draft after deploy.** Unless the org deploys flows as active (Setup, Process Automation Settings), every deployed flow version lands as Draft and the previous version keeps running. Activate each one, and activate the controller and its steps together.

## Action outputs: no relationship reads

Never read a parent record through a relationship on an Apex action's record output. `Setup.formSubmission.FlowToolKit__Form_Template__r.Some_Field__c` fails at run time with "field is not available to the running user", even for an administrator, because the action returns the submission without its parent loaded. Read the parent from its own output (`Setup.formTemplate.Some_Field__c`, `Setup.parentFormSubmission.Some_Field__c`) or add a Get Records. The same holds for the outputs of every other Apex action.

## Namespaces

- In your org every packaged object, field, event, action and flow carries `FlowToolKit__`: `FlowToolKit__Form_Submission__c`, `Setup.formSubmission.FlowToolKit__Contact_1__c`, the action `FlowToolKit__Flow_StripNullValues_Invocable`. Your own fields and flows never do: `Setup.formSubmission.Funding_Opportunity__c`.
- String values that name fields carry the prefix exactly when the field is packaged: `lookupFieldApiName` is `FlowToolKit__Opportunity__c` for the packaged lookup and `Individual_Application__c` for yours.
- A Conversion Map Flow value names a packaged flow with its prefix and your flow without one.
- **Twin field names.** A custom field of yours on Form Submission whose API name matches a packaged field without the prefix (your `Submitted_By__c` beside `FlowToolKit__Submitted_By__c`) is left out of the record the Setup action hands your flow, because inside the package the bare name means the packaged field; a debug log says so. Read it with your own Get Records on the submission, or rename it. Never name a new Form Submission field after a packaged one.
- Custom Address and Geolocation fields on Form Submission are also left out of Setup's record (a flow cannot pass them into an action); their component fields (street, city, latitude, longitude) are there.

## The Automated Process user

Conversion runs as Automated Process unless the org names a running user. That user has no profile and takes no permission sets, so:
- An Apex action of your own called from a conversion flow sees no custom metadata rows and none of the fields it lacks access to when it queries in user mode, and a class saved at API 67 or later runs plain queries that way too. Test the action as that user, or name a running user.
- A Visualforce page the package renders (the answers PDF) refuses to open, which is why Attach PDF to Confirmation Email needs a running user.
- A Transform re-checks field access on rows that come out of an Apex action; it passes when you debug as yourself and fails as Automated Process. Use an Assignment loop over action output instead.

Name a running user with a Platform Event Subscriber Config (no Setup screen creates one). In your project, `platformEventSubscriberConfigs/Form_Submission_Convert_Running_User.platformEventSubscriberConfig-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PlatformEventSubscriberConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Form Submission Convert Running User</masterLabel>
    <platformEventConsumer>FlowToolKit__Form_Submission_Convert</platformEventConsumer>
    <user>admin.user@example.org</user>
</PlatformEventSubscriberConfig>
```

Deploy it (`sf project deploy start -d platformEventSubscriberConfigs -o <org-alias>`), then Setup, Platform Events, Form Submission Convert, Subscriptions, Manage: **Suspend**, then **Resume**. Choose an active administrator who will stay active; if that user is deactivated, name another the same way. Records the conversion creates then show that user as creator and owner; the trigger still runs in system context.

## Record types and duplicate rules

The packaged Contact engine saves the Contact without `RecordTypeId`. A duplicate rule with a Record Type condition therefore never matches a conversion, and the Contact gets the running user's default record type. Remove the Record Type condition from the duplicate rules conversions should use, or set `RecordTypeId` in your own clone from a Get Records on RecordType. Conversion bypasses blocking duplicate rules on save through the Upsert (Bypass Duplicate Rules) action; matching uses the matching rules the template names.

## Nullable Fields

By default a blank answer never overwrites existing data: Remove Null Values drops every null before the save. **Nullable Fields** on the Form Template names the fields a conversion may clear when the form leaves them blank (a checkbox is set to false, since it cannot hold null).

- Set it with the **Edit Nullable Fields** selector on the template, which picks valid fields per object. It stores either a comma-separated list of field API names or an object-keyed JSON map: `{"Contact":["MobilePhone","npe01__WorkPhone__c"],"Account":["Website"]}`. The JSON form applies only the entry matching the record's object; use it whenever a template converts more than one object.
- The packaged Process Case, Process Opportunity, Process Campaign Members and Upsert Account, Contact and Lead flows pass it already. **Every flow you build or clone passes it too**: Remove Null Values' `nullableFieldsCsv` input = `Setup.formTemplate.FlowToolKit__Nullable_Fields__c` (or the template variable's field on an older clone).
- A name that is not a valid, updateable field on the object, or JSON that does not parse, raises a conversion error rather than being skipped. Test a template's list with one submission before turning it on.

## Keeping cloned flows current after an upgrade

A clone or override keeps its own copy and none of the package's later fixes. After every upgrade, read the release notes for fixes to flows you cloned, and either re-clone from the new packaged version and re-apply your changes, or patch the clone. Fixes a clone must carry:

| Fix | Packaged flow | What to change in your clone |
|---|---|---|
| **Add to Account links the Contact** | (Form Submission) Convert, Upsert, Contact | In **Switch (Add to Account)**, outcome **Add to Account**, change the operator on both Conversion Rules conditions (`Contact1 👉 Add to Account`, `Contact2 👉 Add to Account`) from **Equals** to **Contains**. Then Reprocess submissions whose Contacts were left without an Account |
| **Opportunity named from the submission's Subject** | (Form Submission) Convert, Process, Opportunity | In **Opportunity (Field Map)**, set the Name output's formula to `Left(BlankValue({!Setup.formSubmission.FlowToolKit__Subject__c},BlankValue({!Setup.formSubmission.Name},'New Opportunity')),120)` |
| **The save flow's run mode** | (Form) Upsert, the form's save flow | The form starts the save flow from Apex, where the default **How to Run the Flow** runs in system context. Save your override at API version 68.0 or later and choose **User Context, Enforces User Permissions** to keep each respondent's own access, or **System Context Without Sharing** only for an override that lets guests update their saved submissions |
| **Apply Submission Field Maps** | Upsert Account, Contact and Lead; Process Case and Opportunity | Add the action between the Transform and Remove Null Values and assign its Record output back to the record variable, or fields mapped on the Form Template Mapping tab never reach the record |
| **Nullable Fields** | the same flows | Pass the template's Nullable Fields to Remove Null Values (above) |
| **PDF of the answers on the confirmation email** | (Form Submission) Convert, Utility, Send Email | Copy the new steps into your override: **Switch (Attach PDF)**, **Get Answers PDF**, **Generate PDF** with its fault path **Log Warning (PDF Not Attached)**, **Assign PDF Attachment**, **Update Answers PDF Id**, and the **Attachment ID** value on **Send Confirmation Email**. Without them the override sends no PDF. The setting also needs a running user (above) |

Upgrading also leaves page layouts unchanged: add new buttons such as **Reprocess All** and **Reprocess Selected** by hand (build-deploy-and-prefill.md, Step 5).

## Smaller traps

- A Transform `Map` of a multi-select picklist writes nothing and raises nothing: map multi-selects with an Assignment.
- A Transform `InnerJoin` returns no rows when any join-key column is null, and the step still logs Success.
- An industry enum picklist (such as the type or status of a Nonprofit Cloud party relationship group) that holds a value cannot be passed into an Apex action on a record: the action fails with "Unable to convert value". Pass the value as text and set it inside the action.
- Adding an `SObject` input to an Apex action of your own makes every existing flow that calls it fail to deploy until each caller gets a `dataTypeMappings` block. The org keeps running, so it surfaces at the next deploy. Update every caller in the same change.
- Reading `currentItem_*` from a collection filter after the filter has finished reads a stale or null value; inside a loop read the loop variable.
