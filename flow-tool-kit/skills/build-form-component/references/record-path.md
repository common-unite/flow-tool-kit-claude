# Writing a Form Component record

A record component is a Form Component record (record type Record Component): built as data right in the org, with no metadata deploy. It is the shape recommended when reuse is known at design time, such as a contact block asked in one section and again in a Repeater for more contacts (the component shapes standard, `_shared/standards/component-shapes.md`): it is built right away, and every template, flow and record page form that points at it picks up a change at once. A section only one form asks is JSON on the section instead. It is not version controlled; it moves between orgs by Export and Import.

## Create or update

A record component's sections, fields, rules and conditions live on protected child objects that only the package writes. So it is always created through the package's import, never with a plain record insert (a bare `Form_Component__c` row draws nothing):

| Where | How |
|---|---|
| Claude Code | `sf apex run -o <org-alias> -f create_component.apex`, where the file holds `Id componentId = FlowToolKit.FormComponentImport.createRecordComponent(componentJson);` with the JSON as a string. For long JSON, build the string from pieces joined in Apex so no single literal is too long, and escape single quotes |
| claude.ai chat, a connector that runs anonymous Apex | The same Apex through the connector |
| claude.ai chat, a connector that only reads and writes records, or no connector | Give the person the checked JSON file. They open the **Form Components** tab, click **Import Form Component**, paste the JSON and click **Import Component**. They land on the component |

The import:

- is **all or nothing**, and its errors name the problem: a field the object does not have (create it first), an object the org does not have, a section, field or rule name that belongs to another component, or a name that belongs to a metadata component;
- **updates in place** when a component with the same API name exists: same record and Id, sections, fields and rules replaced to match. Settings that describe how the org files and manages it (label, description, category, folder, tags, Form Managers, object, type, widths and the Form Template Mapping) keep their value when the JSON leaves them out; any other design setting the JSON leaves out returns to its default;
- takes keys written `*__` or `FlowToolKit__`, and drops org-specific values (`Id`, `attributes`).

After it runs, read the component back to confirm it and get its Id (the parent object is readable outside the package):

```
sf data query -o <org-alias> -q "SELECT Id, FlowToolKit__QualifiedApiName__c, FlowToolKit__VersionId__c, FlowToolKit__Active__c FROM FlowToolKit__Form_Component__c WHERE FlowToolKit__QualifiedApiName__c = 'Emergency_Contact'"
```

## The JSON the import takes

The component JSON in [anatomy.md](anatomy.md): root `QualifiedApiName` (no `_v0`), `Label`, `*__ObjectApiName__c`, then `*__sections__r` with their `*__fields__r`, and optional `*__conditionalLogic__r` with `*__conditions__r`. An Export token from another org works as is. Start every section, field, rule and condition name with the component's name: child names are unique across the org, and a clash stops the import naming the component that owns it.

## Who can do it

| Permission set | Create | Update an existing component |
|---|---|---|
| Form Builder (Administrator) | Yes | Any |
| Form Builder (Manager) | Yes | Only one whose Form Managers list includes them |

Installing the package assigns no permission sets. Without Form Builder (Administrator) the Form Builder also hides its Save and Reset Form Cache buttons.

## Extend: a new version, the original untouched

Extend is the answer to "this form needs a little more than that component has". It never changes the original.

1. Get the component's current JSON: the **Export** action on the component record (copy the whole token), or the catalog's copy if it is current.
2. Write the fields to add as a JSON array of component fields (name, label, widths, required), then run `python3 scripts/component.py extend <original.json> --name <New_Name> --add <added-fields.json> --out <new.json>`. It copies the design under the new name, renames every section, field, rule and condition after it (child names are unique across the org), adds the fields at the end of the last input section, and describes the new version. A packaged component can be extended this way too.
3. Check it and import it as a new component. Only the section that asked for it points at the new version (`<New_Name>_v0`); every template and component that used the original keeps it, unchanged.

## Update the shared component (in place)

A different action from extend, and never the default. The original changes, and so does every template and component that uses it. Use it only when the change belongs to all of them.

1. List everything it reaches: the catalog's "used in" and "used by components" for the component.
2. Ask its own question, naming all of them: *"Update the shared Household Contact in place? It would change Volunteer Sign-up, Garden Plot Application and the Family Profile component."* No answer means no update.
3. On yes, add the change to its current JSON, keeping every existing name, and import it under the **same** name: same record and Id, and every template using it changes at once.

A packaged component can never be updated; extend it instead.

## Moving to another org

Export the component in one org and import the token in the other. The token carries sections, fields, rules and conditions and leaves out record Ids, the owner, dates, the record type and Form Managers. A theme the other org lacks falls back to the default. Fields must exist in the target org first.

## In an org that upgraded the package

Page layouts and list view buttons do not change on upgrade. If the Export action or the Import Form Component button is missing, add Export to the Form Component page layout's actions, and Import Form Component to the Form Component list view buttons.

## Public forms

The package reads record components with sharing. On a public site add a guest sharing rule giving Read on Form Component where the record type is Record Component, or the guest sees no header and no shared section.
