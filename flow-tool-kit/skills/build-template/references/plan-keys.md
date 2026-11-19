# What the build reads from plan.json, and what it writes

`_shared/standards/plan-format.md` (form-design's contract) defines `plan.json`. This page lists what build-template does with each part, and the few keys only this skill reads. Keys it does not know are ignored.

## Plan to records

| Plan | Built as |
|---|---|
| `template` keys ending `__c`, and `Name` | Form Template fields. Package fields get the `FlowToolKit__` prefix; a key that is your own Form Template field (no packaged field by that name) is used as written; a key that is neither stops the build. `IsActive__c` defaults to true (an inactive draft previews as Not Available) |
| `template.banner` | `subtitle` to Form Template Subtitle, `tags` to Header Tags (one pill per `;`), `layout` picks the header (below). `image: false` leaves the banner image empty, so the banner fills with the brand color |
| `assets.banner`, `assets.tile` | Form Banner Image and Form Tile Image as `/file-asset/<Asset File name>`. No banner asset: the package's banner photo, which the design draws too. The build stops if a named asset is not a public Asset File in the org |
| `assets.logo`, `assets.logo_alt` | The org Default Logo and Default Logo Alt Text when blank and the brand kit is the org's; otherwise this template's Logo Override and Logo Alt Text Override (headers-and-brand.md) |
| `styleTokens` | Add-only into the org's Form Style defaults, the rest into this template's Style Overrides (headers-and-brand.md). Keys already in `template.Style_Overrides__c` win |
| `form_type` and the template switches | Kept as the plan writes them. A switch the plan leaves out is set from the form type; the Save Progress email is always off in stages mode |
| `pages[]` | Form Template Pages in plan order (`Position__c`), matched on rebuild by `ExternalId__c` (`<build.key>:p<n>`) |
| `pages[].header` | The page's own header: `title`, `subtitle`, `icon`, `style`, shown |
| `pages[].condition`, `sections[].condition` | The page's or section's Conditional Logic: the whole page or section, frame and header included, shows or hides |
| `pages[].sections[]` | Form Template Page Sections: their `__c` keys as fields, Show Header on when a header title is set (it defaults to off, which hides a planned title) |
| `intake.build_mode` | `metadata` (also when absent: every plan before modes) or `records`, asked in ftk-start's and form-design's gap round. `records` builds records and JSON only, never a metadata deploy: a component this plan builds and marks `metadata` becomes a record component (below, `components[].built_shape`), a proposed new field the org lacks is left out, and every deploy is a follow-up for Claude Code (SKILL.md, Build modes). Any other value stops the build |
| `components[].shape` | The shape the component is built in (the component shapes standard): `json` on the section, `record` through the package's import, `metadata` handed to build-form-component and bound by name. Needs `shape_asked.answer` equal to it on `form-only`, `shared-new` and `extend`; `json` only with `form-only`. Absent (a plan from before shapes): `form-only` is JSON, `shared-new`, `extend` and `shared-record` are record, with a warning |
| A section's `fields` with a `form-only` component | In the JSON shape, the section's own form as component JSON (in the record shape, the same design as a one-off record component the section points at): one inner section for its text block, then one for its fields, each field with its control, variant, widths, label, help, required and read-only, and its rule |
| `fields[].condition` | A rule inside the form: the field shows when it is true. A field rule equal to its section's rule is built once, on the section |
| `fields[].attestation_text` | A consent's statement, inside the card, with the label as the card's bold first line and no label above it |
| `fields[].label`, `fields[].help` | `customLabel__c` and `helpText__c` (Text(255)). Longer wording goes whole into `customLabelLong__c` and `helpTextLong__c`, which the package reads first; the short key is left out. A `placeholder__c` past 255 in `config` moves to `placeholderLong__c` the same way. An org whose Flow Tool Kit has no long fields gets the old 255-character cut and a warning |
| `fields[].label_hidden` | `label-hidden`: no label on screen, still read by screen readers. A consent card always has `none`, its statement being the label |
| `fields[].options` on a Picklist or MultiPicklist | The field's option subset, `picklistOptionOverrides__c` (the values, in plan order): the form shows only those. An option `{value, label}` whose label differs from the value relabels it in the option settings (`picklistOptionSettings__c`). A real build reads the field's values for the record type the form uses (`intake.record_type`, else on Form Submission the record type named Default, else the user's default) and reports a planned value the field lacks (warnings, setup, and the follow-up "picklist values" in records mode): the package skips it without a word, and shows every value when none of the planned ones is there. The round trip compares the options the form draws with the plan; a planned value the org lacks is listed as waiting for Setup, not as a mismatch, while a label planned as a value (the org stores it under another value) stays a mismatch |
| `intake.record_type` | The Form Submission record type (its label) the form's choice options are checked against, when it is not the one named Default |
| `fields[].option_descriptions` | Each choice's explanation in the field's option settings, keeping any icon already there |
| `fields[].config` | Package field settings, written as given |
| `components[]` | See what-it-builds.md, What it builds. A paid-edition form on another object carries `form_template_mapping` as its Form Template Mapping |
| `Component_Type__c` Flow or Lightning Web Component | The section names the flow (`FlowApiName__c`) or component (`lwcComponentName__c`); the skills that build them run after |
| A field with control `Repeater` | Not built: the report lists it under `not_built` and the round trip as a known gap. Build the repeated form with build-form-component, then set the section to a repeater in Form Builder |
| `emails.confirmation`, `emails.saved`, `emails.resume` | Their names on the template (form-design writes them); build-email-templates builds the email templates |

Generated names follow the Form Builder's pattern (`scripts/formnames.py`): every form, section and field of one template shares a tag, so a search for it finds them all. The family is `build.prefix` (`ORG_FORM`, at most four characters before the underscore, for example `RCG_VA`); the build makes one from the organization's and the form's initials when the plan has none, and writes it back.

## Keys build-template adds

| Key | What |
|---|---|
| `build.template_id`, `build.key`, `build.org` | Written by the first build; later builds update that template |
| `build.prefill_template_id` | The Pre-fill Template (a Form Submission) Flow Tool Kit created with the template the build created; never one the plan names. Deleted with that template when a failed build removes it or a rebuild finds the template gone, and named in the steps for removing a draft build ([after-the-build.md](after-the-build.md)) |
| `build.prefix`, `build.form_ids` | The name family and each form's id, kept so a rebuild keeps every name |
| `build.left_out` | Written by a records-mode build that left proposed new fields out: `fields` (their names) and `rules` (each page, section or field rule that reads one: `level`, `where`, `label`, `reads`). The round trip lists them as left out until deployed, never as mismatches. Removed by the first build that leaves nothing out |
| `build.folder` | The Form Builder folder for this template's components. Default: `intake.workstream`, else the template name |
| `components[].built_name` | The name an `extend` copy was built under |
| `components[].built_shape` | `record` when records mode built this component as a record component in place of the planned metadata one; convert-to-metadata reads it (with the report's `convert_later`). A successful metadata-mode build clears it |
| `build.form_ids` for a one-off component | A `form-only` component in the record or metadata shape is named like the section's own form (`<family><id>_<key>`), so a rebuild updates the same component |
| `components[]` with `decision` `update` | Changes the shared component `name` (or `component_id`) in place, for everyone using it. Required, as form-design writes them and build-form-component checks them: `asked.answer` "update", "update the shared component" or "update shared"; `usage.status` "complete" with `usage.consumers`, every one named in `asked.question`; `shared_change_reason` and `changes`. Refused when the component is packaged: `packaged`, `catalog_match.packaged`, `catalog_match.editable` false, or a `FlowToolKit__` name. The build points the section at the component and hands the change to build-form-component |
| `components[].new_name` | For `extend`: the new version's name, never the original's. Without it the build names the copy from the template's family |
| `components[].design_file` | For `extend`, a component's exported JSON (Form Builder, Export) when the org's copy cannot be read; also lets a dry run show the copy |
| `payment` | `{"required": true, "condition": <a rule>}`: Payment Required and Payment Conditions. Without `condition`, payment is always required. The rule has the same shape as a page rule, on Form Submission fields |
| `url_parameters` | `[{"param": "pv1", "field": "FlowToolKit__Shift_Time__c"}]`: the template's URL Parameter Mapping. Parameters: `pv1` to `pv9`, `utm_source`, `utm_content`, `utm_medium`, `utm_term`, `utm_campaign`, `payment_intent`, `eventType`. `sourceId` is never mapped: the form reads it by itself |
| `prefill` | `{"flow": "<flow API name>"}`: the template's Prefill Flow API Name (a packaged flow as `FlowToolKit__Form_Submission_Prefill`). `template.Prefill_Flow_Api_Name__c` wins when both are set. A real build checks the flow is active and lists a setup step (records mode: a follow-up) when it is not |
| `pages[].sections[].section_tag` | The section's Section Tag, so a prefill flow's Prefill From Mapped Record action (Related Records mode) can put rows into it. Once per template; the value must be in the org's Data Conversion Tag(s) values (after-the-build.md) |
| `form_labels` | `{"<Label_Name>": {"value": "...", "rich_text": true, "group": "...", "tag": "...", "translations": {"es": "..."}}}` (a plain string is the value): the Form Labels the copy's `{{$Label.<Label_Name>}}` tokens need. `scripts/formlabels.py` writes them as Form Label and Form Label Translation custom metadata. A token neither the org nor `form_labels` has stops the build |
| `header` | `"metadata"` with `template.FormQualifiedApiName_Header__c`: keep a header form of your own. It must be built on Form Template (the build checks) |

## Rules

Every rule has the shape form-design writes:

```json
{"label": "Other pronouns chosen", "object": "Form_Submission__c", "mode": "showWhen", "type": "AND",
 "conditions": [{"field": "FlowToolKit__Contact1_Pronouns__c", "operator": "==", "value": "Other"}]}
```

Operators: `==`, `!=`, `CONTAINS`, `INCLUDES`, `EXCLUDES`, `<`, `>`, `<=`, `>=`, and `TRUE`, `FALSE`, `BLANK`, `NOTBLANK` (no value). `type` is `AND`, `OR` or `CUSTOM` with `custom` (`"(1 OR 2) AND 3"`). A rule that is only text, names no field, uses another operator, misses a value, or holds a second question in its value stops the build.
