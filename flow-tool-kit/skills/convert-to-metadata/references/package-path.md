# How the conversion matches the package's own metadata save

The Form Builder saves a component by deployment type: `metadata`, `record` or `json`. A metadata save builds one custom metadata deploy holding every record of the component and enqueues it from inside the package. This page lists what that save writes and where the skill writes the same thing, so a converted component is indistinguishable from one built as metadata in Form Builder.

## Why not call the package

| Entry point | Reachable from the org's own code? | Saves |
|---|---|---|
| The Form Builder's save (its page calls it) | No. It is not global, so only the package's own pages can call it | Any type, by deployment type |
| `FlowToolKit.FormComponentImport.createRecordComponent` | Yes, it is global (anonymous Apex or the Import button) | Record components only |
| An older global save kept for compatibility | Yes, but it does nothing and returns no Id | Nothing |

None of these turns a design into metadata for an org's own Apex, so the skill writes the records as source files and deploys them with the Salesforce CLI. That is the same result through the supported path for metadata, and it leaves the files in the project.

## What the package's metadata save writes, and what the skill writes

| The package's save | The skill |
|---|---|
| One `Form__mdt` record named `<Form>.<Name>`, its label cut to 40 characters | `FlowToolKit__Form.<Name>.md-meta.xml`, labelled with the component's label (build-form-component's writer, the same one a new metadata component uses) |
| One record per section, field, rule and condition (`Form_Section__mdt`, `Form_Field__mdt`, `Form_Conditional_Logic__mdt`, `Form_Conditional_Logic_Condition__mdt`), each named by its API name | One file per record, named the same way. Every name is checked against the org's own metadata of that type and against the rest of the run, so a deploy never replaces a record it should not |
| Each record's columns, plus `config__c`: the record serialized flat, with no children lists | The same columns and a flat `config__c` with an `attributes` type and widths on every form, section and field |
| Changed Form Labels and their translations (`Form_Label__mdt`, `Form_Label_Translation__mdt`) | A record component's labels already are metadata in the org, so nothing new is created. `labels.xml` retrieves the org's own labels and translations the components use into the project, so the components deploy to any org |
| Changed Themes | Not needed: a theme a design names already exists as metadata |
| A record that remembers the builder's last open form for the user | Not written: it is the builder's own session state |
| The deploy, enqueued from inside the package | `sf project deploy start --manifest package.xml`, validated first with `--dry-run` |

## What a record component's stored design carries that metadata never does

The skill reads each record component's stored design (its `FormConfigJSON__c`) and each JSON section's own JSON, and removes before writing:

- record Ids and the record type, owner and audit fields;
- versions (`Version__c`, `VersionId__c`, the `_v0` suffix) and the copy of the design itself;
- the parent pointers between records (the writer sets each child's form and section by name);
- relationship objects (`...__r` pointers to a rule, a field, the Form Object or a theme), keeping the name each one stands for;
- a rule named by its record Id, which becomes the rule's name.

A JSON section's children were named by Form Builder with generated suffixes; they are renamed after the new component (`Plot_Preferences_S1`, `Plot_Preferences_F1`, `Plot_Preferences_R1`, `Plot_Preferences_C1`), with every rule reference rewritten. A record component's children keep their names, which already start with the component's name, unless a name is taken or too long for metadata (40 characters); each such change is a warning in the dry run.

## The template, before and after

| Place | Before | After |
|---|---|---|
| A section drawing a record component | `FormQualifiedApiName__c` `<Name>_v0`, the wrapper in `FormConfigJSON__c` naming `<Name>_v0`, `Form_Component__c` the record's Id | `<Name>` in both, the lookup cleared |
| A section with its own JSON | The wrapper in custom mode holding the JSON | The wrapper in component mode naming the new component; the old JSON stays inside it, as the section editor keeps it when you switch modes |
| A table's row, bulk or edit form, a header or a footer naming `<Name>_v0` | `<Name>_v0` | `<Name>` |

The page section's wrapper is read the way the package reads it: the wrapper's mode decides; in component mode its name wins over the `FormQualifiedApiName__c` column, which is only a mirror and can be stale.
