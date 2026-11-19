# The work list: from the design to the mapping work

`scripts/mapping_plan.py` reads what the earlier skills already decided and writes what this skill still has to build. It asks nothing a file already answers; it turns what no file answers into `questions`.

```bash
python3 scripts/mapping_plan.py _forms/<slug>/plan.json --out _forms/<slug>/mapping-work.json
```

Standard library only: it runs in Claude Code and in claude.ai chat's code sandbox on uploaded files. Exit 1 when there are problems.

## What it reads

| File | Written by | What it takes |
|---|---|---|
| `_forms/<slug>/plan.json` (`_shared/standards/plan-format.md`) | form-design | `intake.edition`, `intake.audience`, `intake.org_id`, `intake.catalog`; each component's `object`, `decision`, `name` and `form_template_mapping`; each field's `object`, `field`, `control` and `placement`; `url_parameters`; `template.Attach_PDF_Confirmation__c`; `build.template_id` once build-template has run |
| `catalog.json` (`_shared/standards/catalog-format.md`) | org-catalog | A reused component's own map (`submission_map`), the org's other mapped forms on the same object (`mapped_forms`), the Form Submission fields that exist (`fields_index`), `platforms`, `taken_at` (over 24 hours old stops the run unless `--allow-stale-catalog`) |
| `flow-tool-kit.json` (`_shared/standards/project-config.md`) | ftk-start | `orgs.<org id>.edition`, `audiences` and `catalog`. A 15- or 18-character org Id matches the same org; with several orgs and no match, nothing is assumed |
| build-template's report (`--report`, its `--out` file) | build-template | `edition`, only when the plan, the config and the catalog name none |
| `_forms/<slug>/mapping-spec.json` (optional, beside the plan) | this skill | The answers the plan has no key for (below) |

The edition comes from the plan, then the config, the catalog and the report. When none names it, the list uses paid (the package default) and asks the edition question; save the answer in `flow-tool-kit.json` and run again.

## mapping-spec.json: this skill's own answers

Write it from the spec (SKILL.md Step 7) when the mapping needs any of these. Every key is optional.

```json
{
 "derived": [
  {"object": "Contact", "field": "Description", "how": "combined", "from": ["Voice_Part__c", "FlowToolKit__Contact1_Pronouns__c"],
   "formula": "{!Voice_Part} & ', ' & {!Pronouns}"},
  {"object": "Contact", "field": "Vocal_Range_Summary__c", "how": "apex", "from": ["Voice_Part__c"],
   "what": "turns the voice part into the range the director files singers by"}
 ],
 "record_types": [{"object": "Contact", "record_type": "Singer"}],
 "campaign_members": [{"field": "Status", "from": "Attendance_Status__c"}],
 "targets": {"Voice_Part__c": "Contact.Voice_Part__c"},
 "prefill": [{"entry_object": "Account", "parameter": "pv2", "lookup": "FlowToolKit__Account__c", "flow": "Form_Prefill_School"}]
}
```

| Key | Rule |
|---|---|
| `derived` | Calculated or combined values: a Transform row each. `how`: `combined`, `formula` or `apex` (a step Flow cannot do well, handed to new-invocable) |
| `record_types` | The record type each conversion sets: a Get Records on RecordType by DeveloperName, then a Transform row. Form Submission's record type fields are never map targets |
| `campaign_members` | Campaign Member values: Transform rows, because the maps do not apply to Campaign Member conversion yet |
| `targets` | Free edition: the org's own Form Submission fields that reach a record, as `Object.Field`. Without an entry a field stays on the submission |
| `prefill` | One prefill flow per entry record (SKILL.md Step 8): the entry object, the URL parameter and submission lookup that carry it, the flow's API name |
| `wiring` | How each new flow reaches templates and sections (SKILL.md Step 6, the wiring checklist), checked by `scripts/wiring_check.py`. Below |

### `wiring`: picklist value = the flow's API name

```json
"wiring": {
 "flows": {"Form_Submission_Convert_Process_Contact_Primary_Contact": {"active": true},
           "Form_Submission_Convert_Process_Contact_Child_Minor": {"active": true}},
 "picklist_values": [
  {"field": "Form_Template__c.Conversion_Map_Flow_Contact1__c", "flow": "Form_Submission_Convert_Process_Contact_Primary_Contact",
   "value": "Form_Submission_Convert_Process_Contact_Primary_Contact", "label": "Primary Contact"},
  {"field": "Form_Template_Page_Section__c.Conversion_Map_Flow__c", "flow": "Form_Submission_Convert_Process_Contact_Child_Minor",
   "value": "Form_Submission_Convert_Process_Contact_Child_Minor", "label": "Child / Minor", "controlling_values": ["Contact1"]}
 ],
 "existing_values": {"Form_Template__c.Conversion_Map_Flow_Controller__c": ["Form_Submission_Convert_Process_Form_Submission_Funding_Requests"]},
 "template": {"Conversion_Map_Flow_Contact1__c": "Form_Submission_Convert_Process_Contact_Primary_Contact"},
 "sections": [{"section": "Children", "component_type": "Repeater", "conversion_rule": "Contact1",
               "conversion_map_flow": "Form_Submission_Convert_Process_Contact_Child_Minor"}]
}
```

| Key | Rule |
|---|---|
| `flows` | Optional: the org's flows by API name (your own bare, packaged with `FlowToolKit__`) from the Step 0 query. When present, a value naming a missing flow fails and an inactive one warns |
| `picklist_values` | Each value you add: `field` (a Form Template `Conversion_Map_Flow_*` field or the section's `Conversion_Map_Flow__c`, prefix optional), `flow`, `value`, `label`; a section value also lists `controlling_values`, the Conversion Rule values it is included under |
| `existing_values` | Optional: values already in the org's picklists, by field, so settings may select them |
| `template` | A Form Template's Conversion Map Flow fields and the value each selects (`Default` or an added value) |
| `sections` | Repeater or Table sections that select a value: `section`, `component_type`, `conversion_rule`, `conversion_map_flow` |

Problems: a value that is not exactly its flow's API name (the cause named: a label typed as the value, case, a missing or extra `FlowToolKit__`, spaces), a field that is not a Conversion Map Flow field, a section value with no or an unknown `controlling_values`, a setting naming a value not added, an override on a section that is not a Repeater or Table, under `Bypass`, or under a rule its value is not included under. Warnings: a label with underscores or equal to the value, an inactive flow, and a Repeater or Table on `Default` under a rule the template overrides (its rows run the packaged default, not the template's flow). `mapping_plan.py` copies the result into the work list's `wiring` and prefixes its problems and warnings with `Wiring:`. Run it alone with `python3 scripts/wiring_check.py <mapping-spec.json or wiring.json>`.

## What it writes

| Key | What |
|---|---|
| `edition`, `edition_source` | `plan`, `config`, `catalog`, `build report` or `assumed` |
| `audiences`, `audiences_source` | `config`, `plan` (read from `intake.audience` words) or `unknown` |
| `template_id` | From `build.template_id`; empty until build-template has built the form |
| `conversion_rules` | The Conversion Rules values the template needs, in order of first use |
| `objects[]` | One per target: `rule`, `flow` (`packaged` with its name and `change`, or `new-object-rule`), `form_maps` (component, `apply_to`, fields, `source` `plan` or `org`), `transform_rows`, `packaged_fields` (packaged staging fields that name this rule) and `org_maps` (the org's other forms on the object) |
| `transform_rows` | Every Transform row across objects: `object`, `target`, `source`, `why` |
| `stays_on_submission` | Fields that never leave Form Submission, with the placement reason |
| `prefill_flows` | From `mapping-spec.json` `prefill` |
| `handoffs` | `flow-access-fix` once per audience for each prefill flow; `new-invocable` for each `apex` value |
| `wiring` | Only when `mapping-spec.json` has `wiring`: `wiring_check.py`'s result (`values`, `template`, `sections`, `problems`, `warnings`, `status`) |
| `questions`, `problems`, `warnings`, `notes` | As named. `status` is `problems`, `questions` or `ready` |

## How it decides

- **Paid, a component on another object:** the form map carries its fields and the packaged flow stays. A reused component maps through the map saved on it in the org (the catalog's), never the plan's: a reused component keeps its own map. No map at all stops the run, and when the component is shared it names how many templates a new map would change.
- **A field placed `mapped:`** must have a row in its component's map.
- **Free, an object the free edition cannot show** (Opportunity, your own objects): the free-edition fallback. The map's rows become Transform rows on Form Submission staging fields. **Free, Account, Contact, Lead or Case with a map:** confirm the map applies in that org, with the same fallback rows listed.
- **Packaged staging fields** (`Contact1_`, `Contact2_`, `Company`, `Website`) name the rule that converts them; the packaged step's Transform decides the target, so read it before promising one.
- **Transform rows** come only from `derived`, `record_types`, `campaign_members`, a `RecordTypeId` or Campaign Member field in the plan, the free-edition fallback and free-edition `targets`.
- **Two maps on one object to different lookups** mean two records of it: the second is a new rule with its own lookup and status pair.
- **Conversion flows hand nothing to flow-access-fix:** they run as the Automated Process user or the named running user, not as the person filling in the form. Prefill flows run as that person, so each goes to flow-access-fix for every audience.
