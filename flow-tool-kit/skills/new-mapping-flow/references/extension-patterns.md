# Extension patterns

Patterns for extending the conversion pipeline beyond one cloned step: your own engine, follow-up records, rules that wait for each other, and repointing the package's defaults. The Flow Tool Kit Nonprofit Cloud extension is built this way; where these patterns and an older packaged flow differ, follow these.

## One engine, form-agnostic utilities

- **One Upsert engine per target family, not per record kind.** One engine can save person accounts, organizations and households. The calling step tells it everything: the mapped record (with `IsPersonAccount`, `RecordTypeId`, and `Id` or `PersonContactId` when known), the matching rule names and the most-confident setting. The engine never re-decides what the step decided.
- **Every follow-up is a subflow that knows nothing about forms**: no Form Submission, no platform event, no logging. Values in, values out, plus `HasError`, `ErrorMessage` and, on writers, `ConversionStatus` (`Created` or `Updated`). The engine logs; utilities stay silent, so an admin can reuse them from any automation. Name them `Utility | <Action> <Object>` (`Utility | Upsert Account Contact Relation`).
- **The engine follows the packaged Upsert engine step for step** (Apply Submission Field Maps, strip nulls, duplicate check, update or insert, read back, log, return), so anyone who knows the packaged flow can read yours.
- **Return primitives across subflow boundaries.** A utility returns an Id as text, not the record: some record types (enum picklists on industry objects) fail to cross a subflow output in a managed runtime even when they work in a source org.

## The post-save router

One decision, labelled `Switch`, that every follow-up's success path returns to. Each outcome is one follow-up, in priority order, guarded by `WasVisited = false` on that follow-up's result element so it runs at most once per pass; the default outcome goes to the return. It reads as a checklist and extends by adding an outcome. Never chain result decisions into one another.

## Ordering: hold back, never reorder

When rule B needs rule A's record (an application needs its person; a household rule needs Contact 1), do not move a packaged rule. B holds back in the controller:

```
Includes_B AND (status of B not terminal)
  AND ( <A's lookup is set> OR NOT(Includes_A) )
```

The last arm matters: without it, a template that never runs A leaves B waiting until Finish stamps it Bypassed. If B also has a mode switch that makes it independent of A, add `NOT(<mode>)` as another arm.

## Deferred work by resetting a status

A pass that cannot finish its follow-up yet (a person converted before the household exists) updates the submission record itself, setting that slot's status back to `Ready`, then returns. The controller dispatches the slot again once the missing record exists, and the router picks up exactly what was deferred. The slot's final status is `Updated`, because the second pass is an update. State that must survive between passes always goes to the database, never only to a variable.

## Log conventions

- `message` is always a fixed string: `Error | Add to Account`. Never pass a utility's error message as the message; it goes in `faultMessage`.
- `flowLabel` is always the flow's own label.
- A fault log keeps `statusFieldApiName = --From Platform Event--` and `status = Error`: the slot's status becomes Error, which is not terminal, which is what lets Reprocess run the slot again. Never stamp the overall Conversion Status for a follow-up's failure: the slot would stay terminal and Reprocess would skip it.
- A success log passes `conversionStatus` from the utility's output. A purely informational row (found the household) carries no status fields at all.

## Writing records

- **Find, then upsert by Id.** Look the record up (you need its other fields anyway), map its `Id` into the Transform, and save with one Create Records element set to upsert on `Id`. No external Id fields and no stamping automation.
- **Field maps live in Transforms** (`<Thing>_Field_Map`, labelled `<Thing> (Field Map)`). A conditional field is an Assignment onto the Transform's output (`Membership_Field_Map.IsPrimaryMember`), never a second map. Only mapped fields are written, so leaving a field out is how an existing value survives.
- **Preserve dates.** `StartDate = BLANKVALUE(existing.StartDate, TODAY())`, `EndDate = null`: a lapsed membership reactivates with its original start.
- **Read back after DML into the same variable.** A save, and Remove Null Values, return only the fields that were set; reading any other field faults ("hasn't been set or assigned"). One Get by Id after insert and after update, then everything downstream reads the fresh copy. This matters most for a Person Account, whose `PersonContactId` exists only after the insert.
- **No loops for a lookup per row.** A collection Transform projecting `Collection[$EachItem].Field`, then one Get Records filtered `In` that collection. Project the field the filter compares against, not the row's own Id.

## Style

- Get Records: `get<WhatItReturns>`, label the thing ("Party Relationship Group").
- Every decision labelled `Switch`; the meaning in the outcome and default outcome labels.
- No formula resources an expression can replace: conditions in the decision, expressions in the Transform value. Exceptions: `INCLUDES()` on a multi-select (no decision operator for it) and a value handed to a subflow input (inputs take references).
- No `runInMode` without a written reason in the description.
- Flow descriptions: what it does, how it works step by step, where it fits. Every element described with the reason.

## Repointing packaged custom metadata

To make every template on `Default` use your flow for a rule, change the **Flow API Name** on the matching **Form Template Conversion Mapping Default** record (Controller, Account, Primary_Contact, and so on).

- **Easiest: edit the packaged record in Setup.** Custom Metadata Types, Form Template Conversion Mapping Default, Manage Records, the record, Edit. Flow API Name is subscriber-controlled, so the package lets you change it, and upgrades keep your value.
- **Through metadata: name the file after the packaged record, prefix included.** In your org the packaged record's full name is `FlowToolKit__Form_Template_Conversion_Mapping_Default.FlowToolKit__Controller`, so the file is `customMetadata/FlowToolKit__Form_Template_Conversion_Mapping_Default.FlowToolKit__Controller.md-meta.xml` (CumulusCI projects can write `___NAMESPACE___Controller` instead of `FlowToolKit__Controller`).
- **Never deploy a record without the prefix in its developer name.** A bare `...Default.Controller` file creates a second, local record beside the packaged one; the package's Apex then refuses to choose between them and every conversion in the org fails with "Row with duplicate DeveloperName". Delete such a record at once if one was deployed.

Before repointing any packaged custom metadata field, confirm it is subscriber-controlled (its field definition in Setup, or `FieldDefinition` through the Tooling API); a field the package controls cannot be changed this way.

## Person Accounts and Nonprofit Cloud: platform facts

- The packaged conversion flows have no Person Account branch. A Person Account org either installs the Flow Tool Kit Nonprofit Cloud extension, which converts Contact 1 and Contact 2 to Person Accounts, or overrides the Account engine and the Contact steps itself.
- **A standard Contact matching rule never matches a Person Account.** Use a Person Account matching rule (activate Salesforce's standard one, or create your own) and name it in the template's matching rules.
- With the Nonprofit Cloud extension, the submission's Contact 1 lookup holds the person's `PersonContactId`, and in household mode the submission's Account lookup holds the **household**, not the person. To reach the person account, query Account where `PersonContactId` equals the Contact 1 lookup.
- One Account Contact Relation per Contact and Account pair is enforced (`DUPLICATE_VALUE`); one primary member per Account is enforced; one primary group per person is not, so demote the others yourself. A Person Account's household membership is the indirect relation (`IsDirect = false`).
- The platform never writes the inverse Contact Contact Relation for automation: write both directions, using the role's inverse role, or the same role when it is symmetric.
- Related rows never carry the conversion's Account: resolve `BLANKVALUE(Setup.formSubmission.FlowToolKit__Account__c, Setup.parentFormSubmission.FlowToolKit__Account__c)` before handing an AccountId to a follow-up, and guard on it being set.
- A decision condition without a right-hand value cannot be activated in Flow Builder but deploys through the API and evaluates false. A hand-edited flow that is inexplicably stuck as Draft usually has one.
