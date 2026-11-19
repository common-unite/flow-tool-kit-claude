# consolidation.json and the reads behind it

What `scripts/consolidate.py` reads from the org, how it compares members, and the file the dry run writes. The tests in `tests/` run every step on an invented org.

## Which sections are grouped

- **JSON sections**: page sections with their own form (`formSelectionMode` `custom`, or a bare component JSON). org-catalog's `catalog.json` already groups them under `repeated_sections`: sections on two or more templates whose fields match at 80% by field or with labels. That list is used as it is.
- **One-off record components**: record components (record type Record Component) placed in exactly one template section and nowhere else (no flow, Lightning page, site page or other component uses them). They are a section's own questions, built as a record. When org-catalog's scripts sit beside this skill, its own `repeated_sections` function groups them together with the JSON sections, so the measure is still org-catalog's. Without them (chat), they are left out and the dry run says so.
- A group needs members on **two or more templates** (`--promote-at` raises it). Packaged and shared components are never members.

## The reads

`consolidate.py queries --catalog <catalog.json>` prints them, each with its key. Save the rows a connector returns under each key in one JSON file (`{"org": [...], "import": [...], "sections": [...], "components": [...]}`) and pass it as `--rows`.

| Key | What |
|---|---|
| `org` | The org's Id, checked against the catalog's |
| `import` | Whether `FlowToolKit.FormComponentImport` exists (Flow Tool Kit 5.3 or later); a record component cannot be created without it. Optional |
| `sections` | Each member section: `LastModifiedDate`, `FormConfigJSON__c`, `FormQualifiedApiName__c`, `Form_Component__c` |
| `components` | Each one-off record component's versions, with their `FormConfigJSON__c` (the newest active Record Component version is read) |

The round trip (`queries --conversion <file> --for roundtrip`) reads the sections again, the shared record components, and for metadata the custom metadata record names the build wrote (`names:Form`, `names:Form_Section` and so on). Cleanup (`--for cleanup`) reads the merged sections and, for each replaced one-off record component, every section and template that still names it (`users`, `template_users`, `old_components`).

## How members are compared

Each member's questions are read from its design, in order: the field (object and API name, without the package prefix), the label people see (the custom label, else the field's own label from the catalog's field index), required, choices (option overrides, option labels, Yes/No wording, number presets) and the rule that shows or hides it (the section's and the field's, by condition, operator and value). The member's Form Template Mapping is compared as a whole.

| Difference | Default | Answer |
|---|---|---|
| The member asks a question the shared component would not | Kept separate | `--add g1:<field>` adds it to the shared component; every member that joins then asks it, and the dry run says so |
| The shared component asks a question the member does not | Joins, and the dry run says "also asks ... from now on" (only possible after an `--add`) | `--separate <section Id>` |
| A label, required, choices, a rule or the mapping differs | Kept separate | `--join <section Id>` takes the shared version |
| None | Joins | `--separate <section Id>` |

Nothing outside the member's questions changes: the page section's title, header, icon, position, its own rule and its page stay exactly as they are.

## consolidation.json

| Key | What |
|---|---|
| `groups[]` | `id` (g1, g2 ...), `title`, `object`, `templates`, `status` (`merge`, `proposed` without a merge answer, `too few` when the answers leave under two templates, `unreadable`), `name`, `label`, `shape` (`record` or `metadata`), `description`, `base` (the member section the design is built from), `base_design`, `added[]` (with the field node copied from the member that has it), `shared_questions[]`, `joining_templates`, `recommendation` |
| `groups[].members[]` | `section_id`, `template_id`, `template`, `page`, `position`, `title`, `kind` (`json` or `record`), `component` (a one-off record's name), `status` (`joins`, `differs`, `separate`), `reason`, `changes`, `questions`, `before` (the three section fields as read), `source_digest`, `last_modified` |
| `repoint[]` | Each merged member: `id`, `where`, `last_modified`, `before`, and `after.formQualifiedApiName` (`<Name>_v0` for a record component, `<Name>` for metadata) |
| `problems`, `warnings` | A problem blocks `confirm` (exit 2) |
| `confirmed` | `{at, digest}`: the fingerprint of every merged group (design, questions, members and their stamps) and every repoint |
| `built` | Written by `build`: each shared component's shape, and for metadata the record names written |
| `roundtrip` | Written by `roundtrip`: `{at, ok, mismatches, digest}`. Cleanup needs `ok` for the confirmed consolidation |

## The Apex files

| File | What it does | Safety |
|---|---|---|
| `create.apex` | `FlowToolKit.FormComponentImport.createRecordComponent` for each shared record component | Stops, creating nothing, when any of the names already exists (the import would change that component in place) |
| `repoint.apex` | Each merged section to component mode, naming its shared component; the old JSON stays in the configuration | All or nothing: stops when a shared component is missing or any section changed after the dry run |
| `rollback.apex` | Each repointed section back to the exact values read before | Leaves the shared components in the org, unused |
| `cleanup.apex` | Removes the old JSON from merged sections; deletes one-off record components nothing uses | Separate step after a passed round trip; stops when a section no longer shows its shared component or a template still uses a record component |
