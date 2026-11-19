# Key reference: every setting on a Form Component

From the package's Form Component, Form Component Section and Form Component Field objects. `*` marks the default. In JSON every key is written `*__<name>__c` ([anatomy.md](anatomy.md)). `scripts/component.py check` holds the same value sets; when the package adds a value, update both.

**The 255-character trap.** Every Text(255) setting below deploys and imports fine past 255 characters and then breaks the first save in Form Builder. The ones that bite: field `helpText__c`, `customLabel__c`, `placeholder__c`, `customValidationMessage__c`, `formatAlertMessage__c`, `fileNameFormat__c`, `validationFormat__c`, `Alternative_Field__c`, and the component's `Description__c`. Longer or rich wording goes in `customLabelLong__c`, `helpTextLong__c` and `placeholderLong__c` (read first, with the short field as the fallback). A section's `helpText__c` is long text already.

## 1. Form Component (the root)

| Setting | Type | Values and purpose |
|---|---|---|
| `type__c` | Picklist | `form`*, `table`, `carousel`, `review`, and the tabset kinds `default`, `scoped`, `vertical` |
| `CategoryTag__c` | Picklist | `Component(s)`, `Form(s)`, `Template(s)` |
| `Active__c` | Checkbox | Must be true to render |
| `Label__c`, `QualifiedApiName__c`, `VersionId__c` | Text(255) | Identity. `VersionId__c` is `<name>_v0`, the binding name |
| `Description__c` | Text(255) | What the block collects and where its answers go |
| `Folder__c`, `Tags__c` | Long text | Filing in the Form Components list |
| `ObjectApiName__c`, `Form_Object__c` | Text(255) | The object the component is built on |
| `Submission_Field_Map__c` | Long text | Form Template Mapping, keyed by Form Submission field: `{"lookupField": "ALL" or a Form Submission lookup, "fields": {"<Form Submission field>": "<this component's field>"}}`. Empty on Form Submission components. `Has_Submission_Map__c` mirrors whether it is set |
| `Form_Managers__c` | Long text | User Ids allowed to edit with the Manager permission set |
| `Theme__c` | Text(255) | Theme name; leave the default |
| `horizontalAlign__c` | Picklist | `start`*, `center`, `space`, `spread`, `end` |
| `verticalAlign__c` | Picklist | `start`, `center`, `end`, `stretch` |
| `widthSmall/Medium/Large__c` | Picklist | `1` to `12`* |
| `carouselBackButtonLabel__c` | Picklist | `Back`*, `Previous`, `Return`, `Go Back` |
| `carouselNextButtonLabel__c` | Picklist | `Continue`*, `Next`, `Forward`, `Proceed` (house rule: Continue) |
| `carouselFinishButtonLabel__c` | Picklist | `Submit`*, `Finish`, `Done`, `Complete`, `Save` |
| `prefill__c` | Long text | Default values as a record JSON; for a table, an array of sample rows |

## 2. Section

Identity and content: `QualifiedApiName__c`, `position__c` (number), `title__c` and `subtitle__c` (rich, `{{merge}}` allowed), `showHeader__c`, `helpText__c` (long text), `conditionalLogic__c` (a rule's name), `displayAsPrompt__c`, `viewAsPlainText__c`.

| Setting | Values |
|---|---|
| `sectionType__c` | `inputSection`*, `addressSection`, `richTextSection`, `accordionSection`, `carouselSection`, `dividerSection`, `illustrationSection`, `imageSection`, `tableSection`, `formComponent`, `flowScreen`, `lwcSection`, `likertSection`, `recordCardSection`, `bannerSection` |
| `displayType__c` | `SHOW`*, `HIDE` (two values at section level) |
| `sectionTheme__c` | `clean`*, `shadow`, `box`, `visualPicker` |
| `Message_Variant__c` | `default`*, `info`, `warning`, `error`, `success`, `highlight` (a brand bar on the left, for a note) |
| `Divider_Style__c` | `line`*, `compact`, `centered`, `label`, `bookmark`, `ornament`, `pill`, `chevron`, `double`, `icon`, `fade`, `tag` |
| `Illustration_Type__c` | `Base`*, `Camping`, `Maintenance`, `Desert`, `Road`, `No Access`, `Balloon`, `Lightning`, `Axe`, `Not Available`, `Fishing`, `Mountain`, `No Events`, `No Tasks`, `Setup`, `Gone Fishing`, `No Access #2`, `No Content`, `No Preview`, `Preview`, `Research`, `Approval`; `Illustration_Size__c` `small`*, `large` | <!-- partner-clean: allow R4 (a package picklist value) -->
| `Likert_Mode__c` | `Picklist`* (columns from the first field's options), `Number` (columns from `Likert_Scale__c`) |
| `Likert_Scale__c` | Long text: Number mode's ordered `[{"label", "value", "help"}]` |
| `Show_Total_Score__c`, `Total_Score_Label__c`, `Alternative_Field__c` | Number mode: a live total row, its label, and the number field that stores the total (it must be editable by the respondent, or the total silently does not save) |
| `widthSmall/Medium/Large__c` | `1` to `12`* |
| `horizontalAlign__c` | `start`*, `center`, `space`, `spread`, `end` |
| `marginTop__c`, `marginBottom__c` | `slds-m-top_none`* through `slds-m-top_xx-large` (nine steps; `slds-m-bottom_...` for bottom) |
| `paddingTop/Bottom/Left/Right__c`, `horizontalPadding__c` | `slds-p-<side>_none`* through `_xx-large` |
| `enableAccordion__c`, `accordionOpen__c`, `hideAccordionBorder__c` | Collapsible section |
| `iconName__c` (Text 80) | `utility:` icons only (house rule) |
| `contentAssetName__c`, `imageOverrideFieldApiName__c` (Text 60), `imageOverlayColor__c`, `imageOverlayOpacity__c` (number), `imageParallax__c` | Image sections |
| `flowApiName__c`, `flowButtonLabel__c`, `flowButtonStyle__c`, `flowRecordId__c`, `modalSize__c` (`small`, `medium`, `large`*, `full`) | A flow launched from inside a component. A page-level Flow Section is a page section setting instead (build-flow-section) |
| `lwcComponentName__c` | A custom LWC (`c:myWidget`, exposing `@api record` and `@api objectApiName`) |
| `formComponent__c`, `hideHeaders__c` | Embed another component; hide its headers |
| `Default_Table_Form__c`, `Default_Table_Form_bulk__c` | A table section's row form and bulk-edit form |
| `Banner__c`, `Record_Card__c` | Settings JSON for a banner or a record card section |
| `Custom_CSS_Style__c` | Long text |

## 3. Field

Identity: `fieldName__c` (the plain API name), `Object__c`, `QualifiedApiName__c`, `position__c`, `conditionalLogic__c`, `Alternative_Field__c` / `Alternative_Object__c` (save the answer to another field or object).

### Display and wording

| Setting | Values and purpose |
|---|---|
| `displayType__c` | `SHOW`*, `HIDE`, `REQUIRED`, `READONLY`: the action a rule applies |
| `customLabel__c` (255), `customLabelLong__c` | The question's wording. `{{label}}`, `{{helptext}}`, `{{fieldnumber}}` and record merges allowed |
| `Label_Rich_Text__c` (HTML) | A rich label; the statement inside an attestation card |
| `labelVariant__c` | `standard`*, `label-hidden` (no visible label; screen readers still read it, and a required field keeps its star), `none` (no label at all, for screen readers too, and no star), `label-inline`, `label-stacked`, `left`, `right` |
| `labelSize__c` | `slds-text-body_small`, `slds-text-body_regular`, `slds-text-title_bold`, `slds-text-heading_small`, `slds-text-heading_medium`, `slds-text-heading_large` |
| `helpText__c` (255), `helpTextLong__c` | Respondent help |
| `helpTextDisplay__c` | `Hover Bubble`*, `Below Label`, `Below Field` |
| `disableHelpText__c` | Hide the field's own help text |
| `placeholder__c` (255), `placeholderLong__c` | Placeholder; `{{helptext}}` allowed |
| `fieldPrompt__c`, `promptDisplayType__c` (`prompt`*, `richtext`), `promptDisplayValue__c` (`helptext`, `custom`*) | Rich text above the input |
| `prepend__c`, `append__c` | Text(40) before or after the input; `append__c` doubles as a scale anchor |
| `required__c`, `readOnly__c`, `viewAsPlainText__c` | Behavior |
| `alignAbsoluteCenter__c`, `labelAlignAbsoluteCenter__c`, `triggerFormulaRecalculation__c`, `isAccordionAction__c` | Layout and behavior |

### Size

`widthSmall__c` and `widthMedium__c`: `1` to `12`*. `widthLarge__c`: `1` to `12`* and `shrink` (fit the content). `inlineLabelWidth__c` (Text 20, a CSS width, `label-inline` only). `topMargin__c` / `bottomMargin__c` (the SLDS nine steps; note the names differ from a section's `marginTop__c` / `marginBottom__c`). `textAreaMinHeight__c` / `textAreaMaxHeight__c` (Text 10, such as `120px`).

### Control overrides

| Setting | Values |
|---|---|
| `picklistType__c` | `standard`*, `radio`, `radiobuttons`, `separatedbuttons`, `iconbuttons`, `pathbuttons`, `multiselectcheckbox`, `multiselectbadge`, `selectallmultiselectcheckbox`, `combobox`, `surveybuttons`, `visualpicker`, and the admin selectors `iconselector`, `emailtemplateselector`, `imageassetselector`, `stylesheetselector` |
| `picklistColumnsSize__c` | `none`* (Auto), `grow`, `size_1-of-1` to `size_1-of-12` (the `size_` prefix is part of the value) |
| `picklistOptionOverrides__c` | Semicolon list of the stored values this form offers, in order (`Weekdays;Weekends`) |
| `picklistOptionSettings__c` | JSON per stored value: `{"Weekdays": {"label": "Monday to Friday", "description": "Daytime shifts", "score": 1, "icon": "utility:clock"}}` (an image card holds `asset` instead of `icon`). Once set, even as `{}`, it replaces the older `picklistOptionLabels__c`, `picklistOptionScores__c` and `picklistVisualPickerOptions__c` |
| `picklistDescriptionDisplay__c` | Blank is Auto (under each option for lists, survey buttons and visual pickers; a popup for button groups; inside the dropdown for a standard picklist); `Below Option`, `Hover Bubble`, `Below Field` |
| `iconPicklistOverrideIconName__c` (Text 60), `iconPicklistOverrideIconSize__c` (`small`*, `medium`, `large`), `iconPicklistOverrideActiveColor__c` (Text 7, a hex color) | Icon buttons, such as stars |
| `booleanType__c` | `default`* (toggle), `checkbox`, `picklist`, `radio`, `radiobuttons`, `attestation` |
| `booleanPicklistTypeOverride__c` | `default`* (True/False), `Yes/No`, `Active/Inactive`, `Enabled/Disabled`, `Valid/Invalid`, `On/Off` |
| `numberType__c` | `standard`*, `stepper`, `slider`, `presetamounts` |
| `numberPresets__c` | `{"enableCustomValues": true, "options": [{"label": "$25", "value": 25}]}` |
| `stringType__c` | `standard`*, `textarea`, and the admin selectors |
| `longTextType__c` | `default`*, `fileUpload` |
| `richTextType__c` | `standard`*, `signaturePad`, `imageUpload` |
| `referenceFieldOverrideType__c` | `standard`*, `component` (show the related record through another component, with `referenceFormComponent__c`), `startnewform`, `vieweditsubmission` (lookups to Form Template or Form Submission), `recordpicker` |
| `recordPickerConfig__c` | Record Picker settings JSON in the shape of the standard record picker (`filter`, `displayInfo`, `matchingInfo`). Filter values may merge other answers (`{{AccountId}}`); a filter whose merged value is blank is skipped |
| `referenceFormDisplayType__c` | `inline`, `modal` |
| `addressFieldType__c` | `Address`, `Street`, `City`, `State`, `PostalCode`, `Country` |

### Bounds and formats

`min__c` / `max__c` / `step__c` (Text 40: quote them; step only sets the increment). `minDateType__c` / `maxDateType__c` (`specificDate`, `specific`, `today`, `fieldValue`; also used for numbers). `minDateFieldName__c` / `maxDateFieldName__c` (the field a `fieldValue` bound reads). `minBeforeAfter__c` / `maxBeforeAfter__c` (`before`*, `after`). `minDays__c` / `maxDays__c` (numbers). `minimumIntegerDigits__c`, `minimum/maximumFractionDigits__c`, `minimum/maximumSignificantDigits__c`. `currencyCode__c` (ISO 4217, `USD` default), `currencyDisplayAs__c` (`symbol`*, `code`, `name`). Date and time display: `year__c`, `month__c`, `day__c`, `weekday__c`, `era__c`, `hour__c`, `minute__c`, `second__c`, `time_zone__c`, `time_zone_name__c`.

### Validation

`validationFormat__c` (a regular expression), `formatAlertMessage__c`, `customValidationMessage__c`, `phoneMask__c` (`(xxx) xxx-xxxx`*, `none`, `xxx-xxx-xxxx`, `xx xxxx xxxx`, `xxxx xxx xxx`).

### Lookups and files

`enableCustomLookup__c`, `customLookupHeader__c` / `customLookupSubheader__c`, `disablePreviewLink__c`, `formSelectorObjectApiName__c`, `formSelectorIsTableSelector__c`. Files (`longTextType__c: fileUpload`): `acceptedFormats__c`, `uploadMultipleFiles__c`, `preventFileDeletion__c`, `fileNameFormat__c`.

### Table columns (parent `type__c: table`)

`columnDisplayType__c` (`text`, `url`), `columnAlignment__c` (`left`*, `center`, `right`), `columnVisibility__c` (`visible`*, `hidden`), `columnWrapText__c`, `columnInitialWidth__c` / `columnFixedWidth__c` (pixels, numbers; `0` sizes to content), `columnCalculationType__c` (`Sum`, `Min`, `Max`, `Average`), `columnClass__c`, `columnIconName__c`, `columnIconPosition__c`, and the `...FieldReference__c` keys that read the class, icon or link label from another field.

### Rich text

`RichTextFormats__c` (toolbar list), `enableRichPlainTextToggle__c`.

## Naming quirks

- Margins: `marginTop__c` / `marginBottom__c` on a section, `topMargin__c` / `bottomMargin__c` on a field.
- `helpText__c`: long text on a section, Text(255) on a field.
- `displayType__c`: two values on a section, four on a field.
- `widthLarge__c`: `shrink` only on a field.
- `picklistType__c` accepts both `radio` (a vertical list) and `radiobuttons` (a segmented bar).
