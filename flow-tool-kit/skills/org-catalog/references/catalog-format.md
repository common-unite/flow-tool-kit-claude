# catalog.json

The file org-catalog writes and the other skills read: form-design (reuse questions, and it refuses a stale catalog), build-template and build-form-component (which components exist and where they are used), ftk-start (platforms and the brand kit). `catalog.md` beside it is the same content for people.

Unknown keys are ignored, so a reader adds rather than renames. All object and field names are full API names with the package prefix written out (`FlowToolKit__Form_Submission__c`); component JSON's `*__` placeholder is replaced.

```json
{
  "catalog_version": 1,
  "taken_at": "2026-01-15T09:00:00Z",
  "status": "ok",
  "status_note": null,
  "source": "sf-cli",
  "org": {"id": "00D000000000001AAA", "name": "Riverside Community Garden", "is_sandbox": true, "type": "Enterprise Edition", "instance": "XX1"},
  "package": {"namespace": "FlowToolKit", "name": "Flow Tool Kit", "version": "5.3.0.2"},
  "edition": "paid",
  "platforms": {"outbound_funds": false, "nonprofit_cloud": true, "npsp": false, "person_accounts": false,
                "evidence": {"nonprofit_cloud": ["ProgramEnrollment"]}},
  "components": [
    {"name": "Household_Contact", "ref": "Household_Contact_v0", "refs": ["Household_Contact_v0", "Household_Contact_v1"],
     "kind": "record", "shape": "record", "packaged": false, "label": "Household Contact", "object": "Contact", "type": "form", "active": true,
     "description": "The adult filling in the form.", "folder": "Shared/People", "tags": ["People", "Contact"],
     "id": "a04000000000002AAA", "versions": 2,
     "modified": "2026-01-10T10:00:00.000+0000", "rules": 1,
     "fields": [{"object": "Contact", "field": "FirstName", "label": "First Name", "type": "Text(40)", "section": "Contact"}],
     "sections": [{"title": "Contact", "type": "inputSection"}],
     "uses": [],
     "used_by_components": [],
     "used_in": [{"template_id": "a01000000000001AAA", "template": "Volunteer Sign-up", "page": 1, "position": 1,
                  "section": "Your details", "role": "section"},
                 {"template_id": null, "template": null, "role": "flow", "place": "Volunteer_Intake", "label": "Volunteer Intake",
                  "where": "screen About you, Household_Form", "via": "Form (Component)", "property": "formQualifiedApiName",
                  "status": "Active"},
                 {"template_id": null, "template": null, "role": "lightning page", "place": "Contact_Record_Page",
                  "label": "Contact Record Page", "where": "region main", "via": "Form (Component)",
                  "property": "formQualifiedApiName", "page_type": "RecordPage", "object": "Contact"},
                 {"template_id": null, "template": null, "role": "site page", "place": "Riverside_Garden1/volunteer",
                  "label": "Riverside_Garden1: Volunteer", "where": "page volunteer", "via": "Form (Dynamic Component)",
                  "property": "properties.formQualifiedApiName", "site": "Riverside_Garden1"}],
     "templates": 2,
     "places": {"templates": 2, "flows": 1, "lightning_pages": 1, "site_pages": 1, "wrapper_components": 0},
     "submission_map": {"lookup_field": "ALL", "fields": {"FlowToolKit__First_Name__c": "FirstName"}}}
  ],
  "templates": [
    {"id": "a01000000000001AAA", "name": "Volunteer Sign-up", "active": true, "header": "FlowToolKit__Form_Header_Banner",
     "footer": null, "logo": "riverside_logo", "logo_override": null,
     "pages": [{"id": "a02000000000001AAA", "position": 1, "label": "About you",
                "sections": [{"id": "a03000000000001AAA", "position": 1, "title": "Your details", "component_type": "FieldSet",
                              "source": "component", "shape": "record", "component": "Household_Contact", "object": "Contact"}]}]}
  ],
  "repeated_sections": [
    {"id": "r1", "title": "In case of emergency", "object": "FlowToolKit__Form_Submission__c", "templates": 2,
     "fields": [{"object": "FlowToolKit__Form_Submission__c", "field": "FlowToolKit__Relationship__c", "label": "Relationship to you"}],
     "sections": [{"template_id": "a01000000000002AAA", "template": "Garden Plot Application", "page": 1, "position": 2,
                   "section": "In case of emergency", "section_id": "a03000000000006AAA", "exact": 1.0, "by_field": 1.0}]}
  ],
  "mapped_forms": [
    {"object": "Contact", "component": "Household_Contact", "kind": "record", "lookup_field": "ALL", "mapped": 4, "fields": 4,
     "templates": 2, "map": {"FlowToolKit__First_Name__c": "FirstName"}}
  ],
  "placements": {"flows": {"read": true, "files": 12, "places": 3}, "lightning_pages": {"read": true, "files": 20, "places": 1},
                 "site_pages": {"read": true, "files": 31, "places": 1}, "wrapper_components": {"read": true, "files": 8, "places": 0},
                 "complete": true, "note": null},
  "run_time_forms": [{"role": "flow", "place": "Plot_Renewal", "label": "Plot Renewal", "where": "screen Your plot, Plot_Form",
                      "via": "Form (Component)", "property": "formQualifiedApiName", "variable": "recordFormName"}],
  "filing": {"folders": {"Shared/People": ["Household_Contact"]}, "tags": {"People": ["Household_Contact"]}},
  "brand_kit": {"found": "partial", "summary": "Partial brand kit: ...", "style_defaults": {"readable": false},
                "default_logo_from_templates": "riverside_logo",
                "brand_files": [{"title": "brand-kit", "content_version_id": "068000000000001AAA", "content_document_id": "069000000000001AAA",
                                 "libraries": ["Asset Library"], "in_asset_library": true, "read": true,
                                 "brand_name": "Riverside Community Garden", "colors": {}, "fonts": {}, "voice": {}}]},
  "fields_index": {"FlowToolKit__Form_Submission__c": {"read": true, "count": 345, "twins": ["Submitted_By__c"],
                                                       "fields": {"FlowToolKit__Email__c": {"label": "Email", "type": "Email"}}}},
  "counts": {"components": 6, "metadata_components": 3, "record_components": 3, "packaged_components": 1, "templates": 3,
             "pages": 4, "sections": 9, "custom_sections": 2, "repeated_sections": 1, "mapped_forms": 1,
             "layered_components": 2, "tracked_metadata_rows": 1, "places_outside_templates": 5, "run_time_forms": 1},
  "problems": ["Youth Camp Registration page 1: the section names Retired_Block_v0, which is not in the org"],
  "warnings": ["templates: left out FlowToolKit__Logo__c, ..., which this Flow Tool Kit version does not have"]
}
```

## Keys

| Key | Rule |
|---|---|
| `taken_at` | UTC time the reads started. Readers refuse a catalog older than 24 hours (`catalog.py check`) |
| `status` | `ok`; `partial` when an essential read was refused (components, templates, pages, sections or Form Submission fields; `status_note` names it); `no org`; `no package` (Flow Tool Kit is not installed) |
| `source` | `sf-cli` or `connector` |
| `edition` | Copied from `flow-tool-kit.json` when `--config` is given. The edition cannot be read from an org (sandboxes run without limits); ftk-start asks it |
| `platforms` | From EntityDefinition and installed packages: Outbound Funds (`outfunds`), Nonprofit Cloud (ProgramEnrollment, GiftTransaction or IndividualApplication), NPSP, person accounts |
| `components[].name` | Metadata: the Form record's QualifiedApiName (package ones start `FlowToolKit__`). Record: `QualifiedApiName__c` |
| `components[].ref` | What a page section stores to show it: the metadata name, or a record component's `<name>_v0` |
| `components[].kind` | `metadata` (Form__mdt) or `record` (Form_Component__c). A Form_Component__c row of the Metadata Component record type only tracks a metadata form and is folded into it (`counts.tracked_metadata_rows`) |
| `components[].shape` | The component's shape (the component shapes standard, `component-shapes.md`): `metadata` or `record`, the same value as `kind`. Every reuse question names it |
| `components[].fields` | Own fields in section order. Label is the custom label when the component sets one, else the field's label. A record component is read from its JSON (the latest active version); a metadata one from its Form Field rows, whose field reference is a durable Id resolved through FieldDefinition. Soft-deleted rows are left out |
| `components[].folder`, `components[].tags` | How the component browser files it: the folder path (names joined with a slash, `null` when unfiled) and the tags (a list, from the comma separated value). A record component's come from `Folder__c` and `Tags__c`; a metadata component's from the same keys in its `config__c` |
| `components[].uses` | Layers: components placed inside this one, `via` `section` (a component section), `field` (a lookup shown as a component), `table form` or `bulk table form` (the table's bulk edit form, `Default_Table_Form_bulk__c`) |
| `components[].used_by_components` | The reverse of `uses` |
| `components[].used_in` | Every place that names it. Template places carry `template_id`, `template`, `page`, `position`, `section` and `role` `section`, `table form`, `bulk form`, `edit form`, `header`, `footer` or `inside a custom section`. Other places carry `template_id: null`, `role` `flow`, `lightning page`, `site page` or `wrapper component`, `place` (API name), `label`, `where` (the screen and field, region or page), `via` (the package component, such as Form (Repeater)) and `property` (the input or property naming the form); `inside_own_json: true` when the name sits inside a form's own JSON there, `copy: true` for a wrapper holding a copy of the form's JSON (a change to the component does not reach it), and `status` for a flow. The list is every place only when `placements.complete` is true |
| `components[].templates` | The number of templates it is used in (template places only) |
| `components[].places` | Counts by kind: `templates`, `flows`, `lightning_pages`, `site_pages`, `wrapper_components` |
| `components[].submission_map` | Its Form Template Mapping: `lookup_field` `ALL` (every conversion of the object) or one Form Submission lookup; `fields` maps Form Submission field to the component's own field |
| `templates[].pages[].sections[].source` | `component` (shows `component`), `custom` (its own form JSON; `fields`, `field_count`, `object`, `map`), `flow`, `lwc`, `text`, `empty` or `unreadable` |
| `templates[].pages[].sections[].shape` | The shape of the section's questions: `json` for a `custom` section (its own form, fixed to this section), the placed component's `metadata` or `record` for a `component` section, absent for the rest |
| `repeated_sections` | Custom sections that match each other at 80% (by field or with labels) on two or more templates, grouped; `fields` is the most typical member's |
| `mapped_forms` | Components on objects other than Form Submission that carry a Form Template Mapping, by object |
| `placements` | Which kinds of place outside templates were read: per kind `read`, `files`, `places` (and `error` when a retrieve was refused); `complete` is true only when all four were read; `note` says what was not. A catalog built from a SOQL connector alone has `complete: false` |
| `run_time_forms` | Flow inputs or page properties that take the form from a formula, an input variable or a page binding: the form is chosen at run time, so it is not tied to one component. Name them in any update in place question |
| `filing` | Component names by folder path and by tag |
| `brand_kit.found` | `saved`, `partial`, `logo only`, `none` or `unknown`; `summary` is the sentence to say |
| `fields_index` | Per object read: every field name with label and type (from FieldDefinition, so fields hidden from the running user are included), and `twins`: your own field names that match a packaged field without its prefix |
| `problems` | Things to fix in the org: a section pointing at a missing component, a component on another object without a map placed in a template, an unresolved field reference |
| `warnings` | Things the reader should know: refused reads, columns an older package lacks, twin fields |

## Files beside it

| File | What |
|---|---|
| `catalog.md` | The readable summary: counts, your components with their shape, package components, repeated sections, mapped forms, templates (each section with its shape), problems |
| `raw.json` | The rows as read (`queries.<key>.records` or `.error`, `dropped_columns`) and the places found outside templates (`placements.<kind>.items`, or `.error`), so a catalog can be rebuilt with `catalog.py build` without reading the org again |
| `match.json` | Written by `catalog.py match` for one design (see matching.md) |
