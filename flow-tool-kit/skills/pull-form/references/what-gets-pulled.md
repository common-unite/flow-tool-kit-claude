# What a pull reads, retrieves and changes

`scripts/pull_form.py pull` in detail: which records belong to a form, how they are found, what is listed but not pulled, what the script changes in a file, and where the files land.

## The tree

```
Form                                   the form or component itself
├── Form Section                       each section; may place another form, a table form, a theme, a rule
│   └── Form Field                     each question; may show another form for a lookup, may have a rule
├── Conditional Logic                  each show, hide or require rule
│   └── Condition                      each test inside a rule
└── Form Label (from {{$Label.Name}})  reusable, translatable text the form's wording uses
    └── Form Label Translation         one per language
```

All are custom metadata records of the package's types (`FlowToolKit__Form__mdt`, `FlowToolKit__Form_Section__mdt` and so on), so they deploy like any other metadata.

## How each record is found

Custom metadata SOQL accepts no `OR`, so each rule below is its own query.

| Record | Found by |
|---|---|
| Form | `DeveloperName` (with or without `FlowToolKit__`), then `MasterLabel` when the name matches nothing |
| Sections, fields | Their Form is this form |
| Rules | Their Form is this form, plus every rule a section or field of the form points at (a rule can exist with no Form set) |
| Conditions | Their Form is this form, plus every condition of those rules (a condition can name only its rule) |
| Form Labels | Every `{{$Label.Name}}` in the records' configuration that is a Form Label of the org's own; packaged labels ship with Flow Tool Kit |
| Translations | Every translation of those labels |

The script then retrieves exactly those records with `sf project retrieve start --manifest`, so the files are the Metadata API's own, not rebuilt from query results. Members the org could not return are listed under "Not retrieved".

After the retrieve, every file's text is searched for label references again; a label found there but not pulled is reported, as is a name that is not a Form Label at all. Flow Tool Kit fills `{{$Label.Name}}` only from Form Labels (never from a Salesforce custom label), so such text is empty on the form until a Form Label of that name exists.

## Outside the form: listed, pulled only on request

| Column | Points at |
|---|---|
| Form's `Form_Object__c` | The Form Object record for the object the form is built on |
| Form's and sections' `Theme__c` | A Theme record |
| Section's `formComponent__c` | A component placed in the section |
| Section's `Default_Table_Form__c`, `Default_Table_Form_bulk__c` | The table's row form and bulk edit form |
| Field's `referenceFormComponent__c` | The form shown for a lookup |

The rest are named inside each record's `config__c`, under the keys Flow Tool Kit renders from:

| Where | Key | Points at |
|---|---|---|
| Image section | `contentAssetName__c` (also a column) | An image file (Asset File) |
| Banner section | `Banner__c`: `imageAsset`, `logoAsset`, or an asset name typed in `image` or `logo` | The background and logo image files |
| Record Card section | `Record_Card__c`: `imageAsset` or an asset name typed in `image` | The card's image file |
| Record Card section | `Record_Card__c`: `buttons`, type `flow` with `flowApiName` | A flow a button opens |
| Record Card section | `Record_Card__c`: `buttons`, type `recordForm` with `formQualifiedApiName` | A form a button opens |
| Flow section, or a flow button on a section's text | `flowApiName__c` | A flow |
| LWC section | `lwcComponentName__c` (`c:name`, `c/name` or `ns:name`) | A Lightning web component |
| Visual picker field | `picklistOptionSettings__c`, each option's `asset` (or the older `picklistVisualPickerOptions__c` while that is empty) | An option's image file |

A typed image setting counts as an Asset File when it is a bare name, `asset:<name>` or a site's `/file-asset/<name>` address; a merge field or a web link is not. Settings of another section type left behind in `config__c` are not rendered and not listed, except a flow button, which any section's text can carry. Illustration sections draw built-in illustrations and name no file. Banners have no buttons.

Each is reported as **packaged** (ships with Flow Tool Kit, or with another package, nothing to do) or **the org's own** (must exist in any org the form goes to). A form a button names that is not a metadata form in the org is reported as such: a record component moves as JSON. `--with-dependencies` pulls the org's own ones: referenced forms with their whole trees, the Form Object and Theme records, and the image files, flows and Lightning web components as metadata (`ContentAsset`, `Flow`, `LightningComponentBundle`). A packaged one, such as the Form Submission Form Object or a `FlowToolKit__Background_...` image, is never pulled. A flow's or component's own dependencies (subflows, Apex, fields, other components) are not followed.

**LWC sections on LWR sites.** The section's component is loaded on demand, and an LWR site's publisher bundles only what some component on the site imports by name. The pull searches the org's own components (a Tooling API query of their JavaScript) for one that imports it with a static `import`, names it, and pulls it with `--with-dependencies`. It belongs in the site's Theme Footer beside FlowToolKit LWR Support, then the site is published. When none exists the report says so; when the search fails it says that too, and the pull goes on.

Fields themselves are not pulled. The form names fields on Form Submission or on the org's objects; those are object metadata, deployed with the project's other fields.

## What the script changes in a file

Nothing, except:

| Change | When |
|---|---|
| A field reference holding an org Id (`00N...`, an Id pair, or `Object.00N...`) is replaced with the API name from the record's own `config__c` | Always, and each fix is reported. The configuration keeps the name the person chose in Form Builder |
| Form Managers (`Form_Managers__c`) cleared, in the column and in `config__c` | Only with `--clear-managers` |
| Form Builder preview data (`prefill__c`) cleared, in the column and in `config__c` | Only with `--clear-prefill` |

The package reads `config__c`, not the separate columns, which is why a cleared value leaves both. The rest of the file keeps the CLI's formatting, so a second pull of an unchanged form changes no file.

Reported but never changed: a value that looks like a record Id outside a field reference, a form with no Description (write one in Form Builder, to the plugin's [documentation standard](../_shared/standards/documentation.md)), and records marked deleted in Form Builder.

A Record Type Id a condition compares against is looked up in the org and reported by name (record type and object), with the query that finds the same record type's Id in the target org: `SELECT Id FROM RecordType WHERE SobjectType = '<object>' AND DeveloperName = '<name>'`. Put that Id in the condition's value, in Form Builder after deploying or in the file before. Sandboxes of the same org keep the same Ids.

## Where the files go

| Case | Location |
|---|---|
| A file with the same name is already in a package directory | Updated in place, with `--overwrite` only |
| The chosen package directory already has a `customMetadata` folder | New files go there (the one holding Flow Tool Kit forms, if there are several) |
| Otherwise | `<package directory>/main/default/customMetadata/` |
| An image file, flow or component | Updated in place when the project holds it; otherwise into the package directory's existing `contentassets`, `flows` or `lwc` folder, else beside the `customMetadata` folder |

The package directory is the default one in `sfdx-project.json` unless `--package-dir` names another listed one. File names are the CLI's: `FlowToolKit__Form.<Name>.md-meta.xml`, `FlowToolKit__Form_Section.<Name>.md-meta.xml` and so on, in an org where Flow Tool Kit is installed.

If any file would change and `--overwrite` was not given, nothing at all is copied, new files included, so the project is never left half pulled. The same holds for an org Id that could not be fixed.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Landed, or ready to land with `--dry-run` |
| 1 | An error, with the Salesforce CLI's message |
| 2 | The name matched no form or several (`candidates` lists them) |
| 3 | Nothing to pull: a packaged form or a record component |
| 4 | Project files differ from the org (`files.conflicts`, with `files.diffs`) |
| 5 | An org Id in a field reference could not be fixed (`unfixed_ids`) |

`--json` prints the whole result, including the counts, the dependency list and every fix, for a reader that is not a person.
