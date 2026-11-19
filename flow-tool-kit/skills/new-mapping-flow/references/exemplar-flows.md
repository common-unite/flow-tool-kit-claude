# How the packaged conversion flows are built

The packaged conversion flows are the pattern to copy. Open them in your own org: Setup, Flows, search "Convert", open the flow in Flow Builder. Their descriptions are written as clone instructions. To get your own copy, use Save As (a flow override, or a plain copy), then retrieve it into your project:

```bash
sf project retrieve start -m "Flow:Form_Submission_Convert_Process_My_Object_Overridable" -o <org-alias>
```

Two flows are the canon for a new single-object step:
- **(Form Submission) Convert | Process | Opportunity | Overridable**: the fullest current action pattern.
- **(Form Submission) Convert | Process | Case | Overridable**: the canon for structure, naming and description voice.

Excerpts below are written as they look in a flow you build in your own org, where packaged actions, objects and fields carry the `FlowToolKit__` prefix. Layout coordinates and some inputs are trimmed.

## Every mapping is a pair, or one flow doing both

| Layer | What it owns | Packaged examples |
|---|---|---|
| **Process** (the step the controller dispatches) | Setup, the Transform, gating: what maps | Process Contact Primary and Alternate, Process Lead Primary and Alternate, Process Account, Process Campaign Members |
| **Upsert** (the engine, called as a subflow) | Apply Submission Field Maps, strip nulls, matching, DML, logs, return: how it saves | Upsert Contact, Upsert Lead, Upsert Account, Upsert Campaign Members |

Opportunity and Case do both in one flow, because they have no duplicate matching. A new object without matching is usually one flow like Opportunity; a new person or organization object that needs matching is a Process flow plus an Upsert engine.

## The Opportunity step, element by element

```
Setup (Conversion Setup action)
  -> Opportunity_Field_Map (Transform)
  -> Assign_Mappings_to_Opportunity (the Transform's record into the Opportunity variable)
  -> Apply_Source_Object_Mappings (Apply Submission Field Maps)
  -> Remove_Null_Values (Strip Null Values, output back into Opportunity)
  -> Switch (Insert or Update?) on Opportunity.Id
       Updated: Update_Opportunity -> Log_Success_Update
       default: Insert_Opportunity -> Log_Success_Insert
  -> Return_to_Controller
Every action and DML element has its own fault path to a Log Error element.
```

### Setup

```xml
<actionCalls>
    <description>Retrieves every record this step needs in one go: the submission, its Form Template, the parent submission and section when this is a repeater or table row, and the matching rules for this step. Use its outputs in the decisions, field maps and assignments that follow instead of querying each object yourself.</description>
    <name>Setup</name>
    <label>Setup</label>
    <actionName>FlowToolKit__Flow_ConversionSetup_Invocable</actionName>
    <actionType>apex</actionType>
    <connector><targetReference>Opportunity_Field_Map</targetReference></connector>
    <inputParameters>
        <name>debugEventName</name>
        <value><stringValue>Opportunity</stringValue></value>
    </inputParameters>
    <inputParameters>
        <name>debugEventType</name>
        <value><elementReference>Opportunity_FieldApiName</elementReference></value>
    </inputParameters>
    <inputParameters>
        <name>debugRecord</name>
        <value><elementReference>DebugRecord</elementReference></value>
    </inputParameters>
    <inputParameters>
        <name>platformEvent</name>
        <value><elementReference>PlatformEvent</elementReference></value>
    </inputParameters>
    <storeOutputAutomatically>true</storeOutputAutomatically>
</actionCalls>
```

`Opportunity_FieldApiName` is a String constant holding `FlowToolKit__Opportunity__c`, the lookup this step fills. For your own rule it holds your lookup, for example `Program_Enrollment__c`.

### The Transform

The Transform is the clone target for a custom mapping. Three rows are always there: `Id` from the submission's target lookup, `Latest_Form_Submission__c` from the submission Id, and the required fields. The Opportunity's Name is a calculated value, so on a paid org it stays a Transform row:

```xml
<transformValueActions>
    <outputFieldApiName>Name</outputFieldApiName>
    <transformType>Map</transformType>
    <value>
        <formulaDataType>String</formulaDataType>
        <formulaExpression>Left(BlankValue({!Setup.formSubmission.FlowToolKit__Subject__c},BlankValue({!Setup.formSubmission.Name},'New Opportunity')),120)</formulaExpression>
    </value>
</transformValueActions>
```

A conditional value is a formula that returns `null` when its rule is off; Remove Null Values then drops it, so a match is never blanked:

```xml
<transformValueActions>
    <outputFieldApiName>MailingStreet</outputFieldApiName>
    <transformType>Map</transformType>
    <value>
        <formulaDataType>String</formulaDataType>
        <formulaExpression>IF({!AssignMailingAddress},{!Setup.formSubmission.FlowToolKit__Street__c},null)</formulaExpression>
    </value>
</transformValueActions>
```

### Apply Submission Field Maps

```xml
<actionCalls>
    <description>Fills the Opportunity fields the Transform left empty from the page sections of the submission's Form Template that are mapped to Opportunity. A value the Transform already set is never changed. To bring a new Opportunity field across, map it on the section's form in the Form Builder (Form Template Mapping tab); nothing in this flow changes.</description>
    <name>Apply_Source_Object_Mappings</name>
    <label>Apply Source Object Mappings</label>
    <actionName>FlowToolKit__Flow_ApplySubmissionMap_Invocable</actionName>
    <actionType>apex</actionType>
    <connector><targetReference>Remove_Null_Values</targetReference></connector>
    <dataTypeMappings><typeName>T__record</typeName><typeValue>Opportunity</typeValue></dataTypeMappings>
    <dataTypeMappings><typeName>U__record</typeName><typeValue>Opportunity</typeValue></dataTypeMappings>
    <inputParameters>
        <name>formSubmission</name>
        <value><elementReference>Setup.formSubmission</elementReference></value>
    </inputParameters>
    <inputParameters>
        <name>lookupField</name>
        <value><stringValue>FlowToolKit__Opportunity__c</stringValue></value>
    </inputParameters>
    <inputParameters>
        <name>record</name>
        <value><elementReference>Opportunity</elementReference></value>
    </inputParameters>
    <storeOutputAutomatically>true</storeOutputAutomatically>
</actionCalls>
```

Outputs: `record` (filled), `skippedMappings` and `skippedMappingCount`. A **Log Filled Fields** input writes a Success row naming what it filled; turn it on while testing.

### Remove Null Values with Nullable Fields

```xml
<actionCalls>
    <name>Remove_Null_Values</name>
    <label>Remove Null Values</label>
    <actionName>FlowToolKit__Flow_StripNullValues_Invocable</actionName>
    <actionType>apex</actionType>
    <connector><targetReference>Switch_Insert_or_Update</targetReference></connector>
    <dataTypeMappings><typeName>T__record</typeName><typeValue>Opportunity</typeValue></dataTypeMappings>
    <dataTypeMappings><typeName>U__record</typeName><typeValue>Opportunity</typeValue></dataTypeMappings>
    <inputParameters>
        <name>nullableFieldsCsv</name>
        <value><elementReference>Setup.formTemplate.FlowToolKit__Nullable_Fields__c</elementReference></value>
    </inputParameters>
    <inputParameters>
        <name>record</name>
        <value><elementReference>Apply_Source_Object_Mappings.record</elementReference></value>
    </inputParameters>
    <outputParameters>
        <assignToReference>Opportunity</assignToReference>
        <name>record</name>
    </outputParameters>
</actionCalls>
```

Note the hand-written `outputParameters`: Flow Builder can strip these on save (traps.md, "Flow Builder round trip").

### A success log and the return

```xml
<actionCalls>
    <description>Logs the new Opportunity as Created, stamps the Opportunity status and lookup on the submission, then goes to the return.</description>
    <name>Log_Success_Insert</name>
    <label>Log Success (Insert)</label>
    <actionName>FlowToolKit__FormSubmission_LogEvent_Invocable</actionName>
    <actionType>apex</actionType>
    <connector><targetReference>Return_to_Controller</targetReference></connector>
    <inputParameters><name>mode</name><value><stringValue>Log</stringValue></value></inputParameters>
    <inputParameters><name>status</name><value><stringValue>Success</stringValue></value></inputParameters>
    <inputParameters><name>conversionStatus</name><value><stringValue>Created</stringValue></value></inputParameters>
    <inputParameters><name>statusFieldApiName</name><value><stringValue>--From Platform Event--</stringValue></value></inputParameters>
    <inputParameters><name>lookupFieldApiName</name><value><stringValue>--From Platform Event--</stringValue></value></inputParameters>
    <inputParameters><name>recordId</name><value><elementReference>Opportunity.Id</elementReference></value></inputParameters>
    <inputParameters><name>record</name><value><elementReference>Setup.formSubmission</elementReference></value></inputParameters>
    <inputParameters><name>formTemplate</name><value><elementReference>Setup.formTemplate</elementReference></value></inputParameters>
    <inputParameters><name>platformEvent</name><value><elementReference>Setup.platformEvent</elementReference></value></inputParameters>
    <inputParameters><name>flowLabel</name><value><stringValue>Convert | Process | Opportunity</stringValue></value></inputParameters>
    <inputParameters><name>message</name><value><stringValue>Opportunity Created</stringValue></value></inputParameters>
    <inputParameters><name>elementApiName</name><value><stringValue>Log_Success_Insert</stringValue></value></inputParameters>
    <inputParameters><name>faultMessage</name><value><elementReference>$Flow.FaultMessage</elementReference></value></inputParameters>
</actionCalls>
<actionCalls>
    <name>Return_to_Controller</name>
    <label>Return to Controller</label>
    <actionName>FlowToolKit__FormSubmission_LogEvent_Invocable</actionName>
    <actionType>apex</actionType>
    <inputParameters><name>mode</name><value><stringValue>Return to Controller</stringValue></value></inputParameters>
    <inputParameters><name>record</name><value><elementReference>Setup.formSubmission</elementReference></value></inputParameters>
    <inputParameters><name>formTemplate</name><value><elementReference>Setup.formTemplate</elementReference></value></inputParameters>
    <inputParameters><name>platformEvent</name><value><elementReference>Setup.platformEvent</elementReference></value></inputParameters>
    <inputParameters><name>faultMessage</name><value><elementReference>$Flow.FaultMessage</elementReference></value></inputParameters>
</actionCalls>
```

The property editor fills `statusFieldApiName`, `lookupFieldApiName` and `elementApiName` for you; hand-written XML must carry them. A fault log is the same action in Log mode with `status` Error, `conversionStatus` Error, its own message ("Insert Opportunity failed") and no outgoing connector. The packaged flows name fault elements `Log_Error_*`; elements you add are named `Fault_<Operation>`, labelled "Log Error".

## Matching (the Contact, Lead and Account engines)

Inside the engine: Apply Submission Field Maps, Remove Null Values, a check that skips matching when the record already has an Id (a prefill or an earlier run), the **Duplicate Check** action, then a three-way decision:

- **Update the match** when there are duplicates, a most confident match exists, and either Update Most Confident is on or there is exactly one match: copy the match's Id onto the mapped record (keeping the mapped values) and update.
- **Multiple matches** when there are several and the setting is off: log `Multiple Matches` and stop. The status stays non-terminal; a person resolves the duplicates; Reprocess resumes.
- **No match**: check the owner (copy OwnerId only when it starts `005`), then insert.

Both insert and update use **Upsert (Bypass Duplicate Rules)** with `bypassDuplicateRules` true. Contact 1 and Contact 2 share one engine; the event's Type picks which lookup and status get stamped. Account reads its matching settings from the template directly. Campaign Member does no matching: it queries the existing membership by Campaign and person.

## Record types

- **Contact** (in the engine): the section's Contact Record Type for a row, else the template's; `-- Use Default --` skips; a Get Records on RecordType (developer name, object Contact, active) validates; a stale name falls back to the default. The engine does not write `RecordTypeId`, so the Contact gets the running user's default record type and a Record Type condition on a duplicate rule never matches (build-deploy-and-prefill.md, Step 4).
- **Account** (in the Process step): the template's Account Record Type, the same sentinel and fallback.
- **Lead and Campaign Member**: none.

To set a record type yourself, add a Get Records on RecordType and a Transform row for `RecordTypeId` in your clone. On a paid org that is one of the three reasons a Transform row is still hand-built.

## Template and section settings as formulas

```
AssignMailingAddress (Contact Process step):
IF({!PlatformEvent.FlowToolKit__Type__c} == {!Contact1_FieldApiName},
  IF({!Setup.formSubmission.FlowToolKit__Internal_Is_Related_Record__c},
     ISPICKVAL({!Setup.pageSection.FlowToolKit__Conversion_Rule__c}, 'Contact1 👉 Set Mailing Address'),
     INCLUDES({!Setup.formTemplate.FlowToolKit__Conversion_Rules__c}, 'Contact1 👉 Set Mailing Address')),
  ... the same for Contact 2 ..., false)
```

Address mapping is opt-in per rule so a match never has its curated address overwritten. A row reads its section's single Conversion Rule; the main submission reads the template's multi-select.

```
CampaignId (Campaign Member step):
IF(row, BLANKVALUE(parent's Campaign, parent template's prefill template's Campaign),
        BLANKVALUE(submission's Campaign, template's prefill template's Campaign))
```

A fallback chain lets one template serve every event. Read the prefill template's Campaign from `Setup.formTemplate` plus a Get Records on the prefill template, not through a relationship on an action output (traps.md, "Action outputs").

```
Lead Company (required field fallback):
BLANKVALUE(Lead.Company, BLANKVALUE(submission Company, BLANKVALUE(submission Name, FirstName & " " & LastName)))
```

## Null handling

Remove Null Values runs before every DML: it rebuilds the record as its Id plus the fields that hold a value, so a match is enriched and never blanked, and conditional formulas can return `null` freely. The template's Nullable Fields list is the deliberate exception (traps.md). Campaign Member goes further on update and writes only the member status, so a repeat conversion updates engagement without rewriting member data.

## Differences at a glance

| | Contact | Lead | Account | Campaign Member | Opportunity, Case |
|---|---|---|---|---|---|
| Steps | Primary and Alternate, one engine | Primary and Alternate, one engine | one | one step for all four person slots | one flow each |
| Matching | rules (section override) | rules (section override) | rules (template only) | query by Campaign and person | none; the lookup is the identity |
| Record type | section or template, in engine | none | template, in step | none | Case: section or template |
| Apply Submission Field Maps | in engine | in engine | in engine | not yet | in the flow |
| Update scope | the stripped record | the stripped record | the stripped record | status only | the stripped record |
| Extra | Add to Account, Add to Campaign | Add to Campaign, Company fallback | | creates a missing Campaign Member Status | Opportunity Name from Subject |

## Chaining a Campaign Member per person slot

After a person converts, the Contact and Lead engines chain the Campaign Member step with a Convert to Record action, **one action per slot**: `Process_Campaign_Member_Primary` (Type Contact 1 or Lead 1, status field Campaign Member 1) and `Process_Campaign_Member_Alternate` (Type Contact 2 or Lead 2, status field Campaign Member 2), routed on the incoming event's Type. One generic action would stamp only one slot's status and leave the other non-terminal, so the controller would re-fire it until the loop guard stops it.
