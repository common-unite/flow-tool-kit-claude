# Form Component JSON: anatomy

> **This page describes the component JSON only: the shape of a Form Component record, of an Export token and of inline JSON on a page section. Do not apply it to custom metadata `config__c`.**
>
> Several rules below (`QualifiedApiName` required, `fields__r` present even when empty, the `is*Section` flags) are right for the JSON and wrong for metadata. In a metadata record's `config__c`, `sections__r` and `fields__r` are **fatal**: `config__c` is a flat copy of one record, so an empty children array tells the package the form has no children and overrides the child records it would otherwise read. The form resolves to nothing and the template that uses it fails. For metadata, author this JSON and let `scripts/component.py cmt` write the records; [metadata-path.md](metadata-path.md) has the details.

## Where the JSON lives and how it renders

- **Form Component records** keep their design in child records (sections, fields, rules, conditions). The record's `FormConfigJSON__c` is a copy the save writes; the form renders from the child records, never from that copy. So a record component is always created through the package's import, which writes the children ([record-path.md](record-path.md)).
- **Export tokens** and **inline JSON** on a page section use the same shape. On a page section the JSON is wrapped: `{"formSelectionMode": "custom" | "component", "object": "<SObject>", "formJsonConfig": "<inner JSON as a string>", "formQualifiedApiName": "<name>"}`. `custom` draws the inner JSON in the browser with no server lookup; `component` ignores the JSON and loads the named component. A root that has `QualifiedApiName` and no wrapper is read as custom JSON.
- When the form loads, the package joins the live field details (data type, label) to every field, so a field's type never has to be authored.

## The namespace placeholder `*__`

- Every Flow Tool Kit key is written `*__name__c` (or `*__name__r`). The package replaces `*__` with `FlowToolKit__` across the whole text, string values included. That is how field names (`"*__fieldName__c": "*__Contact1_Email__c"`) and merge tokens (`"{{*__Program__c}} details"`) stay right in every org.
- Never prefixed: `QualifiedApiName`, `Label`, `Id`, and the render helper keys (`isInputSection` and the other section flags, `sectionVerticalPadding`, `sectionMarginClass`, `richTextClass`, `hide`).
- The org's own fields and standard fields stay plain in values: `"*__fieldName__c": "Grade__c"`, `"Email"`.
- Writing the full `FlowToolKit__` prefix instead of `*__` also works; do not mix the two in one component.

## Root

Plain arrays and objects throughout, never `{totalSize, done, records}` wrappers.

| Key | Purpose |
|---|---|
| `QualifiedApiName` | Required unique name. The purpose name, such as `Emergency_Contact`. A record component is bound as `<QualifiedApiName>_v0` |
| `Label` | The name people see in Form Builder |
| `*__type__c` | `form` (also `table`, `carousel`, `review`, and the tabset kinds `default`, `scoped`, `vertical`) |
| `*__ObjectApiName__c` | The object the component is built on: `*__Form_Submission__c`, `Contact`, `Account`, `Program_Enrollment__c` |
| `*__Version__c` / `*__VersionId__c` | `0` and `<QualifiedApiName>_v0` in hand-authored JSON. The import sets them; leave them out when importing |
| `*__Active__c` | `true` |
| `*__CategoryTag__c` | `Component(s)` for a reusable block, `Form(s)` for a whole form, `Template(s)` for a section of one template |
| `*__Description__c` | Text(255). What the block collects, where the answers go, how to reuse it ([_shared/standards/documentation.md](../_shared/standards/documentation.md)) |
| `*__Folder__c`, `*__Tags__c` | Filing in the Form Components list: a folder such as `Volunteers/Shared`; tags such as `Address, Conditional Logic` |
| `*__Submission_Field_Map__c` | Paid edition, a component on another object: the Form Template Mapping as a JSON **string**, keyed by Form Submission field: `"{\"lookupField\":\"ALL\",\"fields\":{\"FlowToolKit__Contact1_Email__c\":\"Email\"}}"`. A Form Submission component never carries one |
| `*__Form_Managers__c` | User Ids who may edit the component with the Manager permission set. Org-specific: leave it out of anything that travels |
| `*__sections__r` | Array of sections |
| `*__conditionalLogic__r` | Array of rules |
| Rare | `*__Theme__c`, `*__horizontalAlign__c` / `*__verticalAlign__c`, `*__widthSmall/Medium/Large__c` (omitted at `"12"`), carousel button labels, `*__prefill__c` |

## Sections (`*__sections__r[]`)

| Key | Purpose |
|---|---|
| `QualifiedApiName` | Required, unique across the org: start it with the component's name (`Emergency_Contact_Details`) |
| `*__position__c` | Required, 1-based order |
| `*__sectionType__c` | Required: `inputSection`, `addressSection`, `richTextSection`, `imageSection`, `dividerSection`, `illustrationSection`, `likertSection`, `tableSection`, `formComponent`, `flowScreen`, `lwcSection`, `accordionSection`, `carouselSection`, `recordCardSection`, `bannerSection` |
| Matching flag | `isInputSection`, `isAddressSection`, `isRichTextSection`, `isImageSection`, `isDividerSection`, `isIllustrationSection` (sets `isDividerSection` too), `isLikertSection`, `isFormComponentSection`, `isFlowSection`, `isLwcSection`, `isRecordCardSection`, `isBannerSection`. The JSON path does not work it out from the type: without it the section renders as nothing |
| `sectionVerticalPadding`, `sectionMarginClass`, `richTextClass` | Spacing class strings the package computes for saved records but not for JSON. Copy them from a component built in Form Builder when spacing matters |
| `*__fields__r` | Array of fields, present on every section, even `[]` |
| `*__title__c` | A few plain words naming what the section holds. Form Builder lists sections by it |
| `*__subtitle__c`, `*__showHeader__c`, `*__iconName__c`, `*__richText__c` | Header and body content (`{{merge}}` tokens allowed). Keep `showHeader__c` off in a shared component: the page section carries the header |
| `*__enableAccordion__c`, `*__accordionOpen__c`, `*__hideAccordionBorder__c` | Collapsible behavior |
| `*__conditionalLogic__c` | The `QualifiedApiName` of the rule that governs the whole section |
| `*__displayType__c` | `SHOW` (default) or `HIDE` while that rule matches |
| `*__widthSmall/Medium/Large__c` | `"1"` to `"12"` |
| Spacing | `*__marginTop__c`, `*__marginBottom__c`, `*__paddingTop/Bottom/Left/Right__c`, `*__horizontalPadding__c` (full SLDS class names, such as `slds-m-top_small`) |
| By type | `*__Divider_Style__c`; `*__Illustration_Type__c` and `*__Illustration_Size__c`; `*__formComponent__c` (an embedded component's name); `*__Likert_Mode__c`, `*__Likert_Scale__c`, `*__Show_Total_Score__c`, `*__Total_Score_Label__c`, `*__Alternative_Field__c`; `*__Message_Variant__c`; image keys; flow keys; `*__lwcComponentName__c`; `*__Default_Table_Form__c` / `*__Default_Table_Form_bulk__c` |

## Fields (`*__fields__r[]`)

| Key | Purpose |
|---|---|
| `QualifiedApiName` | Required, unique across the org (`Emergency_Contact_Phone`) |
| `*__position__c` | Required, 1-based order within the section |
| `*__fieldName__c` | The field's plain API name. A name the object does not have is skipped with a console warning, never an error: the question just disappears. On an Account form in an org with person accounts, Contact fields take their `Person` names |
| `*__Object__c` | Only when it differs from the component's object |
| `*__displayType__c` | `SHOW` (default), `HIDE`, `REQUIRED` or `READONLY`: the action applied while the field's rule matches. Not the input type |
| `*__conditionalLogic__c` | The rule's `QualifiedApiName`. A field with a rule starts hidden until the rule is evaluated |
| Wording | `*__customLabel__c` (255) or `customLabelLong__c`; `*__Label_Rich_Text__c` (rich label, the attestation statement; `{{label}}` and `{{helptext}}` allowed); `*__labelVariant__c`; `*__labelSize__c`; `*__inlineLabelWidth__c` |
| Help and prompts | `*__helpText__c` (255) or `helpTextLong__c`; `*__helpTextDisplay__c`; `*__disableHelpText__c`; `*__placeholder__c` (255) or `placeholderLong__c`; `*__fieldPrompt__c` |
| Widths and margins | `*__widthSmall/Medium/Large__c` (`"1"` to `"12"`; `"shrink"` on large); `*__topMargin__c`, `*__bottomMargin__c` (field margins are named differently from section margins) |
| Control overrides | `*__picklistType__c`, `*__picklistColumnsSize__c`, `*__picklistOptionOverrides__c`, `*__picklistOptionSettings__c`, `*__picklistDescriptionDisplay__c`, `*__booleanType__c`, `*__booleanPicklistTypeOverride__c`, `*__numberType__c`, `*__numberPresets__c`, `*__stringType__c`, `*__longTextType__c`, `*__richTextType__c`, `*__referenceFieldOverrideType__c`, `*__recordPickerConfig__c`, `*__addressFieldType__c`, the icon picker keys |
| Bounds | `*__min__c`, `*__max__c`, `*__step__c` (text), date bounds (`*__minDateType__c`, `*__minDays__c`, `*__minDateFieldName__c` ...), digits, currency |
| Text | `*__phoneMask__c`, `*__validationFormat__c`, `*__customValidationMessage__c`, `*__prepend__c` / `*__append__c` (40), `*__textAreaMinHeight__c` / `*__textAreaMaxHeight__c` |
| Behavior | `*__required__c`, `*__readOnly__c`, `*__viewAsPlainText__c`, `*__triggerFormulaRecalculation__c` |
| Lookups | `*__enableCustomLookup__c`, `*__customLookupHeader__c`, `*__disablePreviewLink__c`, `*__referenceFormComponent__c` |
| Files | `*__acceptedFormats__c`, `*__uploadMultipleFiles__c`, `*__preventFileDeletion__c`, `*__fileNameFormat__c` |
| Table columns | `*__columnInitialWidth__c` (pixels, a number), `*__columnWrapText__c`, `*__columnCalculationType__c`, `*__columnAlignment__c`, `*__columnIconName__c` and the rest of the `column*` family |
| Save elsewhere | `*__Alternative_Field__c`, `*__Alternative_Object__c` |

## Rules (`*__conditionalLogic__r[]`)

| Key | Purpose |
|---|---|
| `QualifiedApiName` | Required; the string sections and fields name in `*__conditionalLogic__c` |
| `Label` | The rule's purpose in plain words, at most 40 characters ("Show emergency phone"). Form Builder lists rules by it |
| `*__conditionType__c` | `AND` or `OR`; `CUSTOM` with `*__customLogic__c` such as `(1 OR 2) AND 3` |
| `*__conditions__r` | Array of conditions |

### Conditions (`*__conditions__r[]`)

| Key | Purpose |
|---|---|
| `QualifiedApiName` | Required, unique (`Show_Emergency_Phone_1`) |
| `*__position__c` | 1-based order; numbering for `CUSTOM` logic |
| `*__fieldName__c` | The field the condition reads on the current record |
| `*__operation__c` | `==`, `!=`, `TRUE`, `FALSE`, `BLANK`, `NOTBLANK`, `CONTAINS` (substring), `INCLUDES` (a multi-select holds the value), `<`, `>`, `<=`, `>=` |
| `*__value__c` | The comparison value; left out for `TRUE`, `FALSE`, `BLANK`, `NOTBLANK` |

How rules act: the element's own `displayType__c` is the action. `SHOW` means visible only while the rule matches (a reveal); `HIDE` means hidden while it matches; `REQUIRED` and `READONLY` apply while it matches and the element stays visible. Hidden fields have their values cleared. A rule that governs a whole section goes on the section, not on each of its fields.

## Emission style

- Absent keys instead of `null`, empty strings or `false`; booleans only when `true`.
- Widths are strings (`"6"`, `"shrink"`), `"12"` may be left out. Positions are numbers. `min__c`, `max__c`, `step__c` are text. `imageOverlayOpacity__c` and `columnInitialWidth__c` are numbers.
- Leave out what the package fills in when the form loads: children's `VersionId__c`, parent stubs, the field details join, `*__Object__c` when it equals the component's object.
- Strip every `Id` before reusing JSON from another org.
- Merge tokens name only fields that exist.
