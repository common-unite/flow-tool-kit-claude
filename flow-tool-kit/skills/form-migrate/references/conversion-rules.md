# Rules that govern the conversion, and the relay

Moved from this skill's SKILL.md, read on demand: Rules that govern the conversion, The relay.

## Rules that govern the conversion

**Reuse before creation.** Form Submission ships a large packaged field list: `Contact1_*` and `Contact2_*` blocks, two address blocks, organization fields and generic answer slots. Read it from the org (or the shipped list, marked verify); never hard-code a count, because the package gains fields between releases. Three tiers: reuse packaged, then create org-canonical (named for the role, shared by every form), then create form-specific. Anything ambiguous becomes a question, never a guess.

**A packaged picklist that lacks values can still be the right field.** A subscriber org can add values to a restricted packaged picklist (and, for a dependent picklist, map each new value to its controlling values). Choose between extending the packaged field and creating your own on three things that compound: **cardinality** (single or multiple select), **value set**, and **data model** (for example, one race multi-select that folds ethnicity in, against a separate ethnicity question). Record the choice as `extend_packaged` with the values to add.

**Name org-canonical fields only after reading every form in the org.** Naming from one form bakes its wording into fields every later form must live with (`corpus.py` merges several forms first).

**Calculations and custom scripts climb the escalation ladder, lowest rung first** (`ladder.py`):

1. **Native**: a formula field on Form Submission, with Trigger Formula Recalculations (`triggerFormulaRecalculation__c`) switched on for each input that feeds it, so it updates as the respondent types; show and hide logic becomes conditional logic.
2. **Flow Section**: a screen flow in the page section (section type `flowScreen`, flow in `flowApiName__c`) for logic that needs org data or several steps. Flag the section for **build-flow-section**.
3. **Custom LWC**: a Lightning Web Component in the section (section type `lwcSection`, component in `lwcComponentName__c`) for interaction no control or screen flow can draw. Flag the section for **build-custom-lwc**.

Section type `formComponent` is not a rung: it embeds another Form Builder form, which is how a native calculator is shared. The org's people choose the rung; the plan recommends one per item. Lift calendar-driven constants (fee tables, thresholds, dates) into a Custom Metadata Type so admins change them without a deploy.

**A component's contract is its Form Submission fields.** The rung changes who writes the fields, not whether they exist: stage the inputs the logic reads and the outputs it computes. Only card data and billing addresses are exempt.

**Payments use Flow Tool Kit's own payment step** on the Form Template. Never rebuild a legacy gateway, never stage card data.

**Self-host every image.** Deploy each as a ContentAsset that is publicly available (guests cannot see it otherwise) and file it in the Asset Library, or the image picker will not list it. Remove duplicates by content; classify banner, tile or inline, then confirm.

**Reproduce option sets faithfully, except addresses.** Program and survey choices carry meaning and drive reports, so they migrate unchanged, controlling and dependent pairs included. Address parts become an `addressSection` with typed parts (`addressFieldType__c` Street, City, State, PostalCode, Country), and city, state and postal code lists are dropped. Report stale lists; never silently change what people can select.

**Ask how addresses are stored before any plan is built; default to separate text fields.** A custom compound Address field has no text State or Country, only `StateCode__s` and `CountryCode__s` picklists: codes save (`MO`, `US`), names (`Missouri`, `USA`) and a state without a country fail at save, so a prefill or conversion from a text address needs a name-to-code translation. Use a compound field only when State and Country/Territory Picklists are on, or will be before the form is used. Turning that setting on is permanent, and a check-only deploy never turns it on, so every compound address field fails validation until the setting is on. Otherwise reuse the packaged text blocks (`Street__c`, `City__c`, `State_Province__c`, `Postal_Code__c`, `Country__c`, or the `Mailing_*` set) in an `addressSection` whose Address row points at `Id`. `questions.py` raises this first whenever the source has an address; pass `--compound-address` only after the answer is yes.

**Addresses resolve by position, never by label.** A form with two addresses repeats the same labels, so label matching lands both on one field and the second overwrites the first. A block is the run of address parts that follow each other; a repeated part (a second Street) or a new qualifier (Physical, then Mailing) starts the next. The mailing or home block takes the packaged `Mailing_*` fields, the next the `Street__c` set, any further block new fields named for its qualifier. Billing and payment sections are left out.

**One question, one field.** `plan_form.py` never puts two questions on one Form Submission field: the closer match keeps it and the other moves to its next packaged match or a new field, as a `Needs your decision` row and a "Two questions, one field" question. Packaged fields are matched by meaning as well as words: date of birth is Birthdate (never the generic Date), a bare "Date" under a signature is the signature date, "Other:" is read with the question before it, photo and media releases and liability waivers find their consent fields, and a person's section title ("Parent or Guardian") points at Contact 2. Standard fields (Name, the record number) are never targets.

**Flag sensitive questions.** Every read marks a question that collects a government identifier (Social Security, tax id, passport, license number), a bank or card account, health information, a password, or a date of birth on a form that also asks the name (`ir.json` `fields[].sensitive`, `formmigrate/sensitive.py`). The plan makes it a `Needs your decision` row with a Sensitive column, and questions.md asks first whether to collect it at all and how to store it (not collected, an encrypted field with restricted access, or an ordinary field), recommending not collecting it on a public form. form-design carries the answer onto the plan field and stops until it is asked.

**A date asked as Month, Day and Year is one date.** Three questions next to each other in one section, one Month, one Day and one Year, are read together (`formmigrate/dateparts.py`), by their labels and grouping, never by a source's ids. The date takes its name from the nearest context: words the labels share ("Birth Month"), the help text, the section's title, or a short text block that names a date in the section or the one around it ("Date of Birth:"). Only a context that says birth makes it a date of birth: then it is flagged sensitive like a single date of birth question (on the first part, `sensitive.parts` naming all three) and planned on Birthdate. Any other trio ("Program Start Date:", or no context at all) is an ordinary date. The plan keeps the first part as the one date question (a Date field) and marks the other two `Folded into one date question`; form-design builds one date control and lists the folded parts in `dropped`.

**A field that drives conditional visibility needs a landing field**, even when the old connector never saved it: the rebuilt form reads its rules from the submission.

**Name new fields in two passes.** Mirror the target field's API name first, then let `review.py` fix what a machine always gets right (lost camelCase boundaries, flattened initialisms, abbreviations, widget phrasing such as "check all that apply"). Judgment renames go in `name-overrides.json`, keyed by field id so they survive a rerun. Readable names beat matching names; never copy a naming problem into a fresh field.

**Shape every new field like the target it feeds**: same type and, for picklists, the same values. A text field feeding a picklist accepts answers the target rejects, and the conversion fails long after the form was filled in.

**Describe every new field when it is created** (`_shared/standards/documentation.md`): `fieldmeta.py` writes a description that says what the question captures and where the answer is copied. Form Submission fields are respondent-facing, so no inline help text.

**An introduction page is for the respondent.** Most forms need none. When a long application opens on an About or Learn More page (a meaningful label such as "About the Program", never "Welcome"), set that page's Visibility to External Only, so staff reviewing a submission land on the first page of questions. Leave Visibility at Both on any page that holds a question.

## The relay

```
form-migrate          ir.json, mappings, questions, discovery report
    form-design       plan.json and the review canvas (next step)
    build-template    the Form Template in the org
    build-form-component, build-flow-section, build-custom-lwc   the sections that need them
    new-mapping-flow  conversion flows, from the built template
```

Hand `ir.json`, the mappings file and the project config to **form-design**; it carries the section tree, input types, validation, option sets, dependent picklists, conditions, content blocks, repeats and the ladder flags. Never hand-author component JSON here; the build skills own it. The ladder's Flow Section and custom LWC items go to **build-flow-section** and **build-custom-lwc** (both need Claude Code).

**new-mapping-flow** has its own discovery: from the built Form Template it drafts what the rebuild *does*. This skill's mappings say what the legacy form *did*. Compare the two before conversion flows are built; every disagreement (a dropped question, a mapping to the wrong field, a section rebuilt without its rule) is a finding neither file shows alone.

What new-mapping-flow needs, and where it comes from:

| It needs | From the form description |
|---|---|
| Source fields and sections, main or repeating | section paths and mappings |
| Target object and record type rules | node object and RecordTypeId mappings; flag hard-coded 15-character Ids, which do not survive an org move |
| Matching rules and what happens on several matches | lookup conditions and `on_multiple_matches` |
| Field map | mappings, formula tokens resolved |
| Trigger point and order | `order_path`, mirrored branches collapsed |
| Extension mechanism; picklists, permission sets, run-as | not in the description: new-mapping-flow decides |

A FormAssembly connector gives five of these; a source with no connector gives only the first.

**Check a built component before trusting it.** The form skips a `fieldName__c` that does not exist with only a console warning, so a component built against an undeployed field renders without that question. `componentcheck.check_file(config, "force-app", proposals=plan)` reports `field-missing` (the question will not appear), `field-planned` (deploy the field first) and `field-unused` (a planned question no component uses). `configcheck.check_file(config)` reports unknown keys and out-of-set values, which the form also ignores silently.
