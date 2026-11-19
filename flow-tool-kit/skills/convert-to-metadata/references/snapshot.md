# snapshot.json and the files a conversion writes

## Reading the org in chat

In Claude Code, `convert.py snapshot` runs every query with the Salesforce CLI. In claude.ai chat, run them through the Salesforce connector:

1. `python3 scripts/convert.py queries --template "<Id or Name>"`: the org and template queries.
2. Save the rows into `snapshot.json` (below), then `python3 scripts/convert.py queries --snapshot snapshot.json` prints the next ones: pages, sections, Form Objects, the org's own metadata names, then the record components the template draws, every place that names them, and the Form Labels. Run it again after adding the components: a component can place another.
3. Save each result under the query's `key`, keeping the rows as the API returns them (with or without `attributes`).

A column an older Flow Tool Kit version lacks (`Edit_FormQualifiedApiName__c`) is dropped from the query and listed in `dropped_columns`.

## The keys

| Key | Rows |
|---|---|
| `org` | `{id, name, namespace, is_sandbox}` |
| `template` | The one Form Template: Id, Name, LastModifiedDate, header and footer component names |
| `pages` | Id, label and position of each page |
| `sections` | Every page section: Id, LastModifiedDate, page, position, titles, type, the four component name columns, `FormConfigJSON__c`, `Form_Component__c` with its record type |
| `components` | Each record component the template draws or a converted one places: Id, name, `VersionId__c`, label, active, object, stored design, record type |
| `places` | `sections` and `templates` anywhere in the org that name those components; `components`: other record components whose design names one (`{Id, name, mentions}`) |
| `form_objects` | Every Form Object record: name, namespace, object |
| `metadata_names` | `{Form, Form_Section, Form_Field, Form_Conditional_Logic, Form_Conditional_Logic_Condition}`: DeveloperName and NamespacePrefix of every record, so no name the org already has is reused |
| `labels`, `translations` | The Form Labels the designs use and their translations |

The test fixture `tests/skills/convert-to-metadata/fixtures/garden-plot.snapshot.json` (in the plugin repository) is a complete, invented example.

## Files in `_forms/<slug>/convert/`

| File | Written by | What |
|---|---|---|
| `snapshot.json` | snapshot | The org as read |
| `conversion.json` | plan, confirm | The dry run: `convert`, `leave`, `repoint`, `labels`, `problems`, `warnings`, and `confirmed` (time and digest) |
| `components/<Name>.json` | build | Each converted design as component JSON. Edit this and rerun build-form-component's `component.py cmt` for later changes |
| `package.xml` | build | The deploy manifest: exactly the new records |
| `labels.xml` | build | The retrieve manifest for the org's own Form Labels and translations |
| `repoint.apex`, `rollback.apex` | build | The repoint, and its exact undo |
| `cleanup.json`, `cleanup.apex` | cleanup | Which original records nothing uses, and the guarded delete |

`snapshot.json` and `conversion.json` hold the template's section designs as read from the org, including any preview data; keep the folder out of a shared repository when that matters.
