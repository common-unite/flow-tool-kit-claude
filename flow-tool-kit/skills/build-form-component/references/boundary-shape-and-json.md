# The boundary, the edition, the shape and the JSON

Moved from this skill's SKILL.md, read on demand: Decide the boundary, Where the answers land: the edition decides, Pick the shape: metadata, record or JSON, Author the JSON, Sections that need a flow or custom code.

## Decide the boundary

For a whole form, a migration or any change to boundaries, follow [references/component-composition.md](component-composition.md) and check the plan with `scripts/composition.py`. In short:

- **A block of questions that share a record and a purpose**, reusable on many forms: Contact Details, Mailing Address, Demographics, Emergency Contact, Consent. Not a component per page, and not a component per question.
- **Name it for its purpose, never for one form** (`Emergency_Contact`, not `Spring_Camp_Contact`). Another form's builder must see it and know they can use it.
- **Headerless.** The header, icon, subtitle and divider live on the page section that places it, so the same block shows as "Primary Contact" on one form and "Garden Coordinator" on another. Only wording intrinsic to the questions (help text, a consent statement) stays inside.
- **A shared block is one component, in the shape chosen for it.** When several forms share a question group, design it once and place it everywhere; a fix then lands everywhere at once. Which shape follows below.
- **Repeated people or items**: one component holding the fields of one row, which a Repeater section or flow screen component repeats; or one table component when the rows are edited as a grid. Never split one row across components.

## Where the answers land: the edition decides

Read [_shared/standards/mapping-preference.md](../_shared/standards/mapping-preference.md); it wins over anything here.

**Paid edition: build on the record's own object.** A block about a Contact, an Account, an Opportunity or the org's own object is a component on that object (reuse one the catalog found first), and its **Form Template Mapping** tells each field which Form Submission field it stands for. The form then reads and writes only the Form Submission; the packaged conversion's **Apply Submission Field Maps** fills the real record afterwards, so a new field is a Form Builder change, never a flow change.

- The map travels on the component's root as `*__Submission_Field_Map__c`, a JSON string keyed by the **Form Submission** field: `{"lookupField": "ALL", "fields": {"FlowToolKit__Contact1_Email__c": "Email"}}`. `lookupField` is `ALL` (every conversion of that object) or one Form Submission lookup (`FlowToolKit__Account__c`) when a submission converts to two records of the same object.
- plan.json writes it the other way round (`form_template_mapping`: component field to submission field). Convert it with `python3 scripts/component.py map plan.json --component <key>`, never by hand.
- One mapping per Form Submission field; types must line up (the package refuses a mismatch on save); a restricted Form Submission picklist must hold every value of the source picklist; status, conversion, owner, record type and internal fields are never targets. Two records of the same object (Account and Parent Account) need two components, each on its own lookup.
- Hand-built Transform rows (new-mapping-flow) only for calculated or combined values, Campaign Members and record types.

**Free edition: build on Form Submission.** Forms work only on Account, Contact, Lead, Case, Campaign, Campaign Member and the Flow Tool Kit objects, so the block's answers land on Form Submission fields and the conversion flow's Transform maps each one. Reuse the packaged fields first, then the generic answer slots, and create a field only when neither fits: [references/staging-fields.md](staging-fields.md).

**Both editions:** long answers, rich text, survey responses and fields that drive the form stay on Form Submission.

## Pick the shape: metadata, record or JSON

Every component is built in one of three shapes ([_shared/standards/component-shapes.md](../_shared/standards/component-shapes.md)). The choice decides who can change the questions and how far one change reaches.

| Shape | Use it when | Trade-off | How it is built |
|---|---|---|---|
| **JSON** (questions attached directly to one page section, a form component inside a flow, or a dynamic form component on an Experience Cloud page) | **The default for every new section** unless reuse is known at design time: the easiest to build and change, and it cannot conflict with a shared component. Also when the questions must stay fixed to that form, section or page | Every edit is made in each place that carries it; reuse found later is consolidated into one shared component then | Author the same JSON and check it; build-template writes it into the section (plan decision `form-only`, shape `json`), or paste it into the flow's or page's form component |
| **Record component** (`Form_Component__c`, record type Record Component) | **Reuse is known at design time**: the same block is placed in more than one section, Repeater, Table or form, and the plan says so. One form can be enough (a section and a Repeater that repeat the same block). Built right away, and every place references it. Shared across flows, Form Templates and record page forms | Not version controlled; moves between orgs by Export and Import; guests need a sharing rule | Author the JSON, check it, create it through the package's import (chat or Claude Code). Bound as `<Name>_v0`. [references/record-path.md](record-path.md) |
| **Metadata component** (`Form__mdt` and its sections, fields and rules) | A shared component is **final** and should live in version control, so one deployed update reaches every Form Template, flow and Lightning record page form that uses it. Reached through convert-to-metadata once the work is final, or built as metadata from the start only when the person asks | A change is a deploy (Claude Code), then **Reset Form Cache** | Author the component JSON, then `scripts/component.py cmt` writes the namespaced record files; `sf project deploy start` with the person's go-ahead. Bound by its plain name. [references/metadata-path.md](metadata-path.md) |

**The choice rule.** Work through these in order:

1. Reused as it is: the component keeps its own shape. Nothing to ask.
2. Extended (a new version of an existing component): the original's shape.
3. New, and its reuse is known at design time (the plan places the same block in more than one place, even within one form, or org-catalog shows the same questions already built in place on other templates): **one record component**, built right away and referenced by every place.
4. Otherwise: **JSON on the section**. No shared shape on a guess; if the same questions turn up elsewhere later, they are merged into one shared component then.

Metadata is not recommended for new work. **Recommend one, give the reason, name the alternatives, and ask**, in the same message as the reuse question:

> 'Main support contact' is new, and the 'Additional contacts' Repeater on the same form asks the same questions. I recommend one **record component**, Support_Contact, built now: the section and the Repeater both reference it, so one change reaches both. **JSON** on each would mean two copies to keep in step, and **metadata** can come later through convert-to-metadata once the form is final. Record, JSON or metadata?
>
> 'Volunteer availability' is new, and nothing else in the plan asks it. I recommend **JSON on this section**: the simplest to build and change, and no shared component can change it. A **record component** if you already know another place will use it. JSON or record?

No answer means no shape: stop on that block until the person chooses, and record the answer (`shape`, `shape_asked` in `plan.json` or the composition plan). Changing an existing component's shape later is its own question.

## Author the JSON

The component JSON is one root with sections, fields, rules and conditions, exactly the shape Form Builder saves. Full key lists: [references/anatomy.md](anatomy.md) and [references/key-reference.md](key-reference.md); ready-to-adapt fragments for plain-English needs: [references/authoring-cookbook.md](authoring-cookbook.md).

- **Root:** `QualifiedApiName` (the purpose name, no `_v0`), `Label`, `*__ObjectApiName__c`, `*__type__c` (`form` or `table`), `*__Active__c: true`, `*__CategoryTag__c: "Component(s)"`, `*__Description__c`, `*__sections__r`, `*__conditionalLogic__r`.
- **Namespace:** every Flow Tool Kit key is written `*__name__c`, and the package rewrites `*__` to `FlowToolKit__` everywhere in the text, values included, so a packaged field is `"*__fieldName__c": "*__Contact1_Email__c"`. The org's own fields and standard fields stay plain (`Grade__c`, `Email`). `QualifiedApiName`, `Label` and `Id` are never prefixed.
- **Every section** has `QualifiedApiName` (start it with the component's name: child names are unique across the org), `*__position__c`, `*__sectionType__c` with its matching flag (`isInputSection`, `isAddressSection`, `isLikertSection` and so on), `*__title__c`, and `*__fields__r` even when it is `[]`.
- **Every field** has `QualifiedApiName`, `*__position__c` and `*__fieldName__c` (the plain API name). `*__displayType__c` is the action a rule applies (`SHOW`, `HIDE`, `REQUIRED`, `READONLY`), not the input type; the input comes from the field's data type and the override keys (`picklistType__c`, `booleanType__c`, `numberType__c`, `stringType__c`, `richTextType__c`, `longTextType__c`, `referenceFieldOverrideType__c`).
- **Emit like the package:** plain arrays, absent keys instead of nulls or `false`, widths as strings (`"6"`, `"shrink"`), numbers as numbers except `min__c`, `max__c` and `step__c`, which are text.
- **Translate plan fields the one way.** A plan field becomes package keys by one table only, which build-template shares: a hidden label is `labelVariant__c` `label-hidden`, as the house rules say, so screen readers keep the label (`none` is an option only when you also want it gone for screen readers); a consent's wording is `Label_Rich_Text__c` inside the attestation card, never 255-character help text; a section's own text is its own `richTextSection` ahead of the fields; a multi-select's columns are `picklistColumnsSize__c`. The full table is in [references/authoring-cookbook.md](authoring-cookbook.md), Part 4.

### Controls that render well

Pick the control by the option set's size and label length, not by habit:

| Option set | Control |
|---|---|
| Single-select, four or more options, or any label longer than a couple of words | `picklistType__c: surveybuttons` (stacked, tappable rows) |
| Single-select, two or three short options in a wide layout | `radiobuttons` (a segmented bar that never wraps: it clips silently when the set does not fit) |
| Multi-select, short values | `multiselectcheckbox` with `picklistColumnsSize__c: size_1-of-3` |
| Multi-select, longer labels | `multiselectcheckbox` with `size_1-of-2`, or one per row |
| A consent | `booleanType__c: attestation` with the statement in `Label_Rich_Text__c` |
| Donation amounts | `numberType__c: presetamounts` with `numberPresets__c` |
| Counts and scales | `numberType__c: stepper` or `slider` (`min__c`, `max__c`, `step__c` as text) |
| A grid of statements on one scale | `sectionType: likertSection` (Picklist mode on same-scale picklists, Number mode on number fields with `Likert_Scale__c`, optional total score) |
| A filtered lookup | `referenceFieldOverrideType__c: recordpicker` with `recordPickerConfig__c` |
| Friendlier wording or a short explanation per option | `picklistOptionSettings__c` (label, description, score, icon per stored value) and `picklistDescriptionDisplay__c` |

When one page mixes single-selects, make them all `surveybuttons`. The house rules (in [_shared/standards/form-type-rules.md](../_shared/standards/form-type-rules.md)) and [references/presentation-decisions.md](presentation-decisions.md) set widths, option columns and Boolean shapes.

### Labels and descriptions people can read

Write them when the component is created, in the same step, to [_shared/standards/documentation.md](../_shared/standards/documentation.md):

- **Component:** `Label` the purpose in words ("Emergency Contact"); `*__Description__c` (255 characters) opens with what the block collects, then where the answers go and how to reuse it: "Collects a second person to call in an emergency: name, phone and relationship. Answers land on the Contact 2 fields of the Form Submission, which the conversion turns into a related Contact." No issue numbers, no dates, no history, no em-dashes.
- **Sections:** every inner section has a `*__title__c` of a few plain words naming what it holds (Form Builder lists sections by it and shows "Untitled Section" when it is blank). `*__showHeader__c` stays off unless the plan asks for an inner header.
- **Rules:** every rule's `Label` names its purpose in plain words, at most 40 characters ("Show emergency phone", "Is a returning volunteer"), never an API name: Form Builder lists rules by it.
- **Field wording:** `*__customLabel__c` is the question as the form asks it; `*__helpText__c` tells the respondent what to enter, in their words. Both are 255 characters; longer or rich text goes in `customLabelLong__c`, `helpTextLong__c` or `placeholderLong__c`.
- **New fields** a component needs ship with their description at creation (sections 3 and 4 of the documentation standard), and they are deployed before the component that references them.

## Sections that need a flow or custom code

A section that looks up org data, branches on records or calculates across records is a **Flow Section**: hand it to **build-flow-section** (page section `Component_Type__c` `Flow`). An interaction no control covers is a **custom LWC section**: hand it to **build-custom-lwc** (`Component_Type__c` `Lightning Web Component`). The plan names them (`decision: flow-section` or `custom-lwc`). Build the component's ordinary questions here, and leave a marked placeholder in your notes for the section the other skill builds; never imitate a flow or script with hidden fields and rules.
