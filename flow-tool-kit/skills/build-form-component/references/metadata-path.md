# Metadata components in an org with Flow Tool Kit installed

**Claude Code only.** A metadata component is a set of custom metadata records deployed with the Salesforce CLI from a project folder. In chat, say that plainly and ask whether to build a record component now ([record-path.md](record-path.md)) or wait for Claude Code.

Metadata (the component shapes standard, `_shared/standards/component-shapes.md`) is for a shared component that is final: one update reaches every Form Template, flow and Lightning record page form that uses it, it deploys to every org, moves with the rest of a release, and lives in version control. The price is that every change is a deploy and a **Reset Form Cache**. New work does not start here: it reaches metadata through convert-to-metadata once it is final, or is built as metadata from the start when the person asks for it. An extended metadata component stays metadata.

## 1. Before the first deploy

- **Assign Form Builder (Administrator)** (`FlowToolKit__Form_Builder_Admin`) to whoever builds and checks forms. The install assigns no permission sets, and without it the Form Builder hides Save and **Reset Form Cache**.
- **Grant field access to every field you add.** New fields deploy with no field-level security, and both the Form Builder and the form see fields through it. Ship a permission set that grants read and edit on every field you add to Form Submission (or the component's object), assign it, and add the fields to the guest's permission set for a public form.
- The packaged permission sets: `FlowToolKit__Form_Builder_Admin`, `FlowToolKit__Form_Builder_Manager`, `FlowToolKit__Form_Flow_User` (respondents; guests on a public site).

## 2. Namespacing: the first deploy fails without it

In an org where Flow Tool Kit is installed, the five metadata types and every one of their fields carry the `FlowToolKit__` prefix, and the deploy errors are misleading ("Custom metadata type Form_Section__mdt is not available in this organization"). `scripts/component.py cmt` applies all of this; the table is for reading and fixing files.

| Item | What to write |
|---|---|
| Record file name | `FlowToolKit__Form.<Name>.md-meta.xml`, and the same for `FlowToolKit__Form_Section.`, `FlowToolKit__Form_Field.`, `FlowToolKit__Form_Conditional_Logic.`, `FlowToolKit__Form_Conditional_Logic_Condition.` |
| Every `<field>` element | `FlowToolKit__config__c`, `FlowToolKit__Form__c`, ... (every column is packaged) |
| `Form_Object__c` value (a Form Object record) | `FlowToolKit__Form_Submission` for Form Submission, `FlowToolKit__Form_Template` for a header or footer. `FlowToolKit__Account` for Account. The package ships Form Object records only for those; for another object use the record the org already has (`SELECT QualifiedApiName, FlowToolKit__Object__c FROM FlowToolKit__Form_Object__mdt`) and pass it as `--form-object`, or, when the org has none, let `scripts/component.py cmt --new-form-object` write one beside the component |
| `Object__c` value (an object) | `FlowToolKit__Form_Submission__c`, or `Contact`, `Program_Enrollment__c` |
| `fieldName__c` value (a field on that object) | Packaged field: `FlowToolKit__Contact1_Email__c`. The org's own field: plain `Grade__c`. Standard field: `Email`, `Id` |
| Parent references (`Form__c`, `Form_Section__c`, `conditionalLogic__c` columns) | The plain record name: your records are not namespaced |
| Keys inside `config__c` | The literal `FlowToolKit__` prefix (never `*__`, which is only for component JSON) |
| Parent names inside `config__c` | Your plain record names |
| `fieldName__c` and `Object__c` inside `config__c` | Namespaced exactly like the columns |

**Name resolution:** `FlowToolKit__` is added to a binding name only when the org has its own namespace (the package's own development org). In an installed org your plain names resolve as written, so a page section names the component by its plain name.

**Same-deploy is fine:** Global Value Sets, custom fields, permission sets and the metadata records all deploy together in one `sf project deploy start`; the API orders them. Warnings that a Global Value Set "returned from org, but not found in the local project" are harmless.

## 3. Each record holds a flat `config__c`

`config__c` is the real payload; the package reads it, not the separate columns. It is a flat copy of one Form Component record:

- an `attributes` key naming the record's type (`FlowToolKit__Form_Component__c`, `..._Section__c`, `..._Field__c`, `..._Conditional_Logic__c`, `..._Condition__c`);
- **never** a children key (`sections__r`, `fields__r`, `conditionalLogic__r`, `conditions__r`): an empty children array overrides the child records and the form resolves to nothing;
- none of the JSON-only helpers (`QualifiedApiName`, the `is*Section` flags, the spacing class strings);
- widths on every root, section and field, even at `"12"`: without them the form renders as one column.

Build one form in Form Builder and read its `config__c` once when in doubt:

```
sf data query -o <org-alias> -q "SELECT DeveloperName, FlowToolKit__config__c FROM FlowToolKit__Form__mdt WHERE DeveloperName = '<name>'"
```

## 4. Generate the files, never hand-type them

Author the component JSON once (the same JSON a record component takes), check it, then:

```
python3 scripts/component.py cmt _forms/<slug>/components/Emergency_Contact.json \
  --out force-app/main/default/customMetadata [--form-object <Form Object name>]
```

It writes one file per record with the namespacing above, the flat `config__c`, the columns set from it, and the labels (component `Label`, section titles, rule labels) as each record's label. Rerun it after every design change; keep the JSON as the source of truth beside the plan. Then:

```
sf project deploy start -o <org-alias> --source-dir force-app/main/default/customMetadata
```

## 5. The platform cache: a redeploy does not refresh the form

Form configs are served from the org's platform cache. After any metadata redeploy the old form keeps drawing, which looks exactly like a failed deploy.

- **Reset it from the Form Builder:** open any form you can save and click the green **Reset Form Cache** button in the docked footer. It clears every cached form and rebuilds them; hand-authored records are not changed by it.
- Anonymous Apex in the org cannot clear the package's cache entries, so the button is the way. Plan for it in every author, deploy and check loop.

## 6. Picklist values: decide before creating fields

Before creating any picklist field, list the org's Global Value Sets and the picklists on the objects involved:

```
sf project retrieve start -m "GlobalValueSet:*" -m "CustomObject:Contact" -m "CustomObject:Account" -o <org-alias> --target-metadata-dir <tmp-dir> --unzip
```

Look for value sets to reuse, older fields whose values overlap the new form (they rarely match word for word), and name collisions with the fields you plan (an existing `Contact.Gender__c`). A Global Value Set suits a picklist that lives on both a Form Submission field and its target field; global value sets are always restricted. An existing inline picklist cannot be switched to one. [staging-fields.md](staging-fields.md) covers which fields to create at all.

## 7. Checking it

Template record, **Preview Form** tab: walk every page, every option against the plan, every required marker and every rule both ways. The preview writes a real Form Submission you can delete. The preview pane is about half width: stacked layouts read fine, but a segmented `radiobuttons` bar that does not fit clips at any width, so check it at full width too.
