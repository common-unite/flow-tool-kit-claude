# Authoring cookbook: form needs to component JSON

Plain-English needs translated to component JSON fragments you adapt. Part 1 indexes them. Part 2 holds structure that has worked across many forms. Part 3 holds the newer controls; prefer them where they fit. Part 4 is the one translation from a plan.json field to package keys. Every fragment is component JSON ([anatomy.md](anatomy.md)): sections also need their `is*Section` flag, and every section and field its `QualifiedApiName` and `*__position__c` (left out below for brevity). All names and values are invented.

## Part 1: Need index

| The ask sounds like | Recipe |
|---|---|
| "Name and email side by side" | 2.1 pairs on one row |
| "A settings toggle" | 2.2 shrink toggle, with 2.13 for the fields it reveals |
| "Label next to the input" | 2.3 label variants |
| "Collect their address" | 2.12 address section |
| "Break the form into visual groups" | 3.7 styled divider |
| "Intro text or a banner image" | 2.10 rich text and image sections |
| "Collapsible optional section" | 2.11 accordion |
| "Show X only when Y" | 2.13 rules |
| "Warning or important note" | 3.8 message card |
| "Consent with legal wording" | 3.2 attestation |
| "Donation amounts with suggested tiers" | 3.3 preset amounts |
| "Quantity picker or percent slider" | 3.4 stepper and slider |
| "Survey: rate these 8 statements" | 3.1 Likert section |
| "How likely to recommend" | 3.5 0 to 10 row |
| "Star rating" | 2.8 icon buttons |
| "Big tappable options on phones" | 3.6 survey buttons and visual picker |
| "Explain what each option means" | 3.9 option settings with descriptions |
| "A short paragraph answer" | 3.10 textarea |
| "Pick an Account, filtered by another answer" | 3.11 record picker |
| "Household members, one row each" | 3.12 a component a Repeater section repeats |
| "A table of line items with a total" | 2.14 table columns |
| "Contact details that update the Contact (paid edition)" | 3.13 a mapped component on Contact |
| "One header for every form" | 3.14 the packaged banner header |
| "Numbered questions" | `{{fieldnumber}}` in `*__customLabel__c` |
| "Default values" | 2.15 prefill |

## Part 2: Structure that has worked

### 2.1 Pairs on one row (6/6 is the common split; 5/7 for a short value and a wide qualifier)
```json
{"*__fieldName__c": "*__Contact2_Email__c", "*__widthSmall__c": "12", "*__widthMedium__c": "6", "*__widthLarge__c": "6", "*__required__c": true}
{"*__fieldName__c": "*__Contact2_Phone__c", "*__widthSmall__c": "12", "*__widthMedium__c": "6", "*__widthLarge__c": "6"}
```
Small stays `"12"` so phones stack. Width each field by its expected answer (first name narrower than last name, email wider than phone).

### 2.2 Shrink toggle (settings pattern; a one-word label)
```json
{"*__fieldName__c": "*__Send_Reminder__c", "*__customLabel__c": "Enabled",
 "*__widthSmall__c": "12", "*__widthMedium__c": "12", "*__widthLarge__c": "shrink"}
```

### 2.3 Label variants
```json
{"*__fieldName__c": "*__Monthly_Income__c", "*__labelVariant__c": "label-inline", "*__inlineLabelWidth__c": "16rem",
 "*__placeholder__c": "$0.00", "*__disableHelpText__c": true}
```
`label-hidden` hides the label from view but keeps it for screen readers (the default for a question asked by the section's text; a required field keeps its star); `none` removes the label entirely, for screen readers too, so use it only when that is the intent; `label-inline` with `inlineLabelWidth__c` lines up a stack of labels.

### 2.4 Spacing
Defaults are `_none`; any other value is deliberate. Divider rhythm: section `marginTop__c` `slds-m-top_small`, `marginBottom__c` `slds-m-bottom_xx-small`. Survey question spacing on fields: `topMargin__c` and `bottomMargin__c` `_x-small`. The gap between page sections belongs to the page section, not the component.

### 2.6 Merge tokens
- Record merge in a title: `"*__title__c": "{{*__Program__c}} schedule"`, or `"{{Name}}"`.
- Number formatting in rich text: `Total: ${{$number.*__Total_Amount__c.toFixed(2)}}`.
- Field tokens: `"*__placeholder__c": "{{helptext}}"`, `"*__customLabel__c": "{{*__Email_Type__c}} {{label}}"`.
- A translatable custom label inside rich text: `{{$Label.Volunteer_Intro}}`.
- Numbering: `{{fieldnumber}}`, `{{sectionnumber}}` in labels.
- Merge only fields that exist: a token naming a missing field breaks the form.

### 2.7 Prepend, append and masks
```json
{"*__fieldName__c": "Hours_Worked__c", "*__append__c": "hrs.", "*__widthMedium__c": "3", "*__widthLarge__c": "3"}
{"*__fieldName__c": "*__Company_Phone__c", "*__placeholder__c": "(###) ###-####"}
```
`append__c` takes merge tokens and works as a scale anchor ("Very likely"). For giving, prefer 3.3 over a `$0.00` placeholder.

### 2.8 Star rating with icon buttons
```json
{"*__fieldName__c": "*__Rating_1__c", "*__customLabel__c": "How would you rate the workshop?",
 "*__picklistType__c": "iconbuttons", "*__iconPicklistOverrideIconName__c": "utility:favorite",
 "*__iconPicklistOverrideActiveColor__c": "#ffd602", "*__iconPicklistOverrideIconSize__c": "large"}
```
The packaged `*__Rating_1__c` to `*__Rating_5__c` fields hold 1 to 5. The same mechanism with `utility:user` makes a household-size picker.

### 2.10 Rich text and image sections
```json
{"*__sectionType__c": "richTextSection", "isRichTextSection": true, "*__title__c": "Survey introduction",
 "*__richText__c": "<p style=\"font-size: 16px; line-height: 1.5\">Please take a few minutes to tell us how the season went.</p>", "*__fields__r": []}
{"*__sectionType__c": "imageSection", "isImageSection": true, "*__title__c": "Program banner",
 "*__contentAssetName__c": "Program_Banner", "*__imageOverlayOpacity__c": 0.4, "*__imageOverlayColor__c": "#000000",
 "*__imageOverrideFieldApiName__c": "Banner_Image_URL__c", "*__fields__r": []}
```
Overlay opacity is a number. Text a respondent reads is 16px or larger, set inside the rich text (house rules). Ordinary headings belong to the page section header, not to a component.

### 2.11 Accordion
```json
{"*__sectionType__c": "inputSection", "isInputSection": true, "*__title__c": "Optional details",
 "*__showHeader__c": true, "*__iconName__c": "utility:edit_form",
 "*__enableAccordion__c": true, "*__accordionOpen__c": true, "*__sectionTheme__c": "box"}
```
Leave out `accordionOpen__c` to start collapsed.

### 2.12 Address section (six parts, in this order, all width 12)
```json
{"*__sectionType__c": "addressSection", "isAddressSection": true, "*__title__c": "Mailing address", "*__fields__r": [
 {"*__fieldName__c": "Id",                         "*__addressFieldType__c": "Address"},
 {"*__fieldName__c": "*__Mailing_Street__c",        "*__addressFieldType__c": "Street"},
 {"*__fieldName__c": "*__Mailing_City__c",          "*__addressFieldType__c": "City"},
 {"*__fieldName__c": "*__Mailing_State_Province__c","*__addressFieldType__c": "State"},
 {"*__fieldName__c": "*__Mailing_Postal_Code__c",   "*__addressFieldType__c": "PostalCode"},
 {"*__fieldName__c": "*__Mailing_Country__c",       "*__addressFieldType__c": "Country"}]}
```
On a Form Submission (or any custom object) with text address fields, the `Address` row binds to `Id`, as the packaged Address component does. On Contact, use the standard parts (`MailingAddress`, `MailingStreet`, `MailingCity`, `MailingState`, `MailingPostalCode`, `MailingCountry`). Bind a compound custom address field only when the org has State and Country picklists turned on and the people who run it accept that the setting is permanent: its state and country take codes only, so prefill and conversion maps written with names fail.

### 2.13 Rules: reveal, suppress, require
The element's own `displayType__c` is the action applied while its rule matches.

Reveal (details appear when the checkbox is checked):
```json
"*__conditionalLogic__r": [
 {"QualifiedApiName": "Accessibility_Show_Details", "Label": "Show accessibility details", "*__conditionType__c": "AND",
  "*__conditions__r": [{"QualifiedApiName": "Accessibility_Show_Details_1", "*__position__c": 1,
                        "*__fieldName__c": "*__Accessibility_Needs__c", "*__operation__c": "TRUE"}]}]
FIELD: {"*__fieldName__c": "*__Accessibility_Details__c", "*__displayType__c": "SHOW", "*__conditionalLogic__c": "Accessibility_Show_Details"}
```
Suppress: the same rule shape, the controlled element carries `"*__displayType__c": "HIDE"`. Require: `*__Preferred_Contact__c == "Phone"` makes the phone field `REQUIRED` while it matches.

One condition per allowed value, joined by OR: `*__Role__c == "Volunteer"` OR `*__Role__c == "Board Member"`. A multi-select controller uses `INCLUDES`. A checkbox uses `TRUE`. Mixed logic uses `CUSTOM` with `*__customLogic__c` `(1 OR 2) AND 3`. A rule governing a whole section goes on the section.

### 2.14 Table columns (root `*__type__c: "table"`; widths are pixel numbers)
```json
{"*__fieldName__c": "*__Item_Description__c", "*__columnInitialWidth__c": 250, "*__columnWrapText__c": true},
{"*__fieldName__c": "*__Quantity__c", "*__columnInitialWidth__c": 100},
{"*__fieldName__c": "*__Total_Amount__c", "*__columnInitialWidth__c": 150, "*__columnCalculationType__c": "Sum"}
```
`columnInitialWidth__c: 0` sizes to content. The table section's `*__Default_Table_Form__c` names the row form used for New and Edit.

### 2.15 Prefill (root `*__prefill__c`: a JSON string of a record)
```json
{"attributes": {"type": "*__Form_Submission__c"}, "*__Preferred_Contact__c": "Email"}
```
A table's prefill is an array of rows.

### 2.16 A hand-authored root
```json
{"QualifiedApiName": "Emergency_Contact", "Label": "Emergency Contact",
 "*__Active__c": true, "*__type__c": "form", "*__ObjectApiName__c": "*__Form_Submission__c",
 "*__CategoryTag__c": "Component(s)",
 "*__Description__c": "Collects a second person to call in an emergency: name, phone and relationship. Answers land on the Contact 2 fields of the Form Submission.",
 "*__sections__r": [], "*__conditionalLogic__r": []}
```

## Part 3: Newer controls (prefer these)

### 3.1 Likert section
The mode picks the row field type. **Picklist mode**: rows are picklist fields sharing the first field's exact option set (the packaged agreement, satisfaction and frequency fields exist for this). **Number mode**: rows are number fields; the scale comes from `Likert_Scale__c`; a picklist row fails on save. Rows and the total field must be editable by the respondent: a read-only row renders read-only and a read-only total silently does not save. `Total_Score_N__c` fields are totals, never rows.

```json
{"*__sectionType__c": "likertSection", "isLikertSection": true, "*__title__c": "Program feedback",
 "*__Likert_Mode__c": "Picklist", "*__fields__r": [
  {"*__fieldName__c": "*__Agreement_Question_1__c", "*__customLabel__c": "The workshop was easy to follow"},
  {"*__fieldName__c": "*__Agreement_Question_2__c", "*__customLabel__c": "Staff answered my questions clearly"},
  {"*__fieldName__c": "*__Agreement_Question_3__c", "*__customLabel__c": "I would recommend this program"}]}
```
Scored (Number mode): number rows (`*__Number_Question_1__c` ...) and
```json
{"*__Likert_Mode__c": "Number",
 "*__Likert_Scale__c": "[{\"label\":\"Never\",\"value\":0},{\"label\":\"Sometimes\",\"value\":1},{\"label\":\"Often\",\"value\":2},{\"label\":\"Always\",\"value\":3}]",
 "*__Show_Total_Score__c": true, "*__Total_Score_Label__c": "Screening total",
 "*__Alternative_Field__c": "FlowToolKit__Total_Score_1__c"}
```
A scale field (`Agreement_Question_N__c`, `Rating_N__c`, `Satisfaction`, `Frequency`, `Scale`) always draws its own packaged scale and ignores option overrides. Never use one for a question with its own options.

### 3.2 Attestation consent
```json
{"*__fieldName__c": "*__Agree_Consent__c", "*__booleanType__c": "attestation", "*__labelVariant__c": "none",
 "*__Label_Rich_Text__c": "<p><strong>Photo release</strong></p><p>I agree that photos taken at program events may include me and may be used in the organization's newsletters. I have read the <a href=\"https://www.example.org/photo-policy\">photo policy</a>.</p>",
 "*__required__c": true}
```
The statement sits inside the clickable card; nothing else labels it. Keep consent wording word for word.

### 3.3 Preset amounts
```json
{"*__fieldName__c": "*__Amount__c", "*__numberType__c": "presetamounts",
 "*__numberPresets__c": "{\"enableCustomValues\":true,\"options\":[{\"label\":\"$25\",\"value\":25},{\"label\":\"$50\",\"value\":50},{\"label\":\"$100\",\"value\":100}]}"}
```
`enableCustomValues` adds an Other choice with free entry; a prefilled amount outside the list selects Other.

### 3.4 Stepper and slider
```json
{"*__fieldName__c": "*__Number_of_Guests__c", "*__numberType__c": "stepper", "*__min__c": "0", "*__max__c": "10", "*__step__c": "1"}
{"*__fieldName__c": "*__Percent_1__c", "*__numberType__c": "slider", "*__min__c": "0", "*__max__c": "100", "*__step__c": "5"}
```
Bounds are text. Step sets the increment only; typing any valid value is still allowed.

### 3.5 A 0 to 10 row
```json
{"*__fieldName__c": "*__Scale_Question_1__c", "*__customLabel__c": "How likely are you to recommend us to a friend?",
 "*__picklistType__c": "surveybuttons", "*__prepend__c": "Not likely", "*__append__c": "Very likely"}
```

### 3.6 Survey buttons and visual picker
```json
{"*__fieldName__c": "*__Shirt_Size__c", "*__picklistType__c": "surveybuttons"}
{"*__fieldName__c": "*__Preferred_Contact__c", "*__picklistType__c": "visualpicker",
 "*__picklistOptionSettings__c": "{\"Email\":{\"icon\":\"utility:email\"},\"Phone\":{\"icon\":\"utility:call\"},\"Text Message\":{\"icon\":\"utility:sms\"}}"}
```

### 3.7 Styled divider
```json
{"*__sectionType__c": "dividerSection", "isDividerSection": true, "*__title__c": "Household",
 "*__Divider_Style__c": "bookmark", "*__iconName__c": "utility:home", "*__marginTop__c": "slds-m-top_medium", "*__fields__r": []}
```
A divider carries a title, a subtitle that explains the next block, and an icon; leave out one with nothing to say.

### 3.8 Message card
```json
{"*__sectionType__c": "richTextSection", "isRichTextSection": true, "*__title__c": "Deadline note",
 "*__Message_Variant__c": "warning", "*__richText__c": "<p>Applications close June 30.</p>", "*__fields__r": []}
```
Variants: `info`, `warning`, `error`, `success`, and `highlight` (a brand bar on the left, the house choice for a note).

### 3.9 Option settings: wording, descriptions, scores
```json
{"*__fieldName__c": "*__Volunteer_Availability__c", "*__picklistType__c": "surveybuttons",
 "*__picklistOptionOverrides__c": "Weekdays;Weekends;Either",
 "*__picklistOptionSettings__c": "{\"Weekdays\":{\"label\":\"Monday to Friday\",\"description\":\"Daytime shifts between 9 and 3\"},\"Weekends\":{\"description\":\"Saturday morning work days\"}}",
 "*__picklistDescriptionDisplay__c": "Below Option"}
```
Stored values never change, so reports stay stable; each form shows its own subset (`picklistOptionOverrides__c`) and its own wording. Descriptions only when the source supplies the words. Merge tokens work in labels and descriptions.

### 3.10 Textarea on a text field
```json
{"*__fieldName__c": "*__Text_Question_1__c", "*__stringType__c": "textarea",
 "*__textAreaMinHeight__c": "80px", "*__textAreaMaxHeight__c": "200px"}
```

### 3.11 Record picker with a filter that follows another answer
```json
{"*__fieldName__c": "*__Account__c", "*__referenceFieldOverrideType__c": "recordpicker",
 "*__recordPickerConfig__c": "{\"filter\":{\"criteria\":[{\"fieldPath\":\"Type\",\"operator\":\"eq\",\"value\":\"{{*__Organization_Type__c}}\"}]},\"displayInfo\":{\"additionalFields\":[\"BillingCity\"]},\"matchingInfo\":{\"primaryField\":{\"fieldPath\":\"Name\"},\"additionalFields\":[{\"fieldPath\":\"BillingCity\"}]}}"}
```
For lookups to one object. A filter whose merged value is blank is skipped, so the picker shows everything until the other answer is given. The settings follow the standard Salesforce record picker's shape; set one up in Record Picker Settings in Form Builder once and copy its JSON when in doubt.

### 3.12 A component a Repeater section repeats (household members)
The component is ordinary: one input section with the fields of one row. The page section makes it repeat (`Component_Type__c` `Repeater`), and build-template sets the repeater's settings there: `Min__c`, `Max__c`, the New, Edit, Clone and Delete actions and their labels, `Repeater_Record_Spacing__c` (space above each row, none to xx-large) and `Repeater_Hide_Divider__c`. Keep every repeated question in this one component. Each row is its own Form Submission; give the page section a `Section_Tag__c` when a prefill flow fills the rows. A repeater with its header hidden and no rows shows a start bar with Import and New; Lookup Import lists only records not already added.

### 3.13 A component on Contact with Form Template Mapping (paid edition)
```json
{"QualifiedApiName": "Contact_Details", "Label": "Contact Details", "*__ObjectApiName__c": "Contact",
 "*__type__c": "form", "*__Active__c": true, "*__CategoryTag__c": "Component(s)",
 "*__Description__c": "A person's name, email and phone, built on Contact and mapped to the Contact 1 fields of the Form Submission, so the packaged conversion creates or updates the Contact.",
 "*__Submission_Field_Map__c": "{\"lookupField\":\"ALL\",\"fields\":{\"FlowToolKit__Contact1_First_Name__c\":\"FirstName\",\"FlowToolKit__Contact1_Last_Name__c\":\"LastName\",\"FlowToolKit__Contact1_Email__c\":\"Email\",\"FlowToolKit__Contact1_Phone__c\":\"Phone\"}}",
 "*__sections__r": [{"QualifiedApiName": "Contact_Details_Fields", "*__position__c": 1, "*__sectionType__c": "inputSection",
   "isInputSection": true, "*__title__c": "Contact details", "*__fields__r": [
    {"QualifiedApiName": "Contact_Details_FirstName", "*__position__c": 1, "*__fieldName__c": "FirstName", "*__widthMedium__c": "5", "*__widthLarge__c": "5", "*__required__c": true},
    {"QualifiedApiName": "Contact_Details_LastName", "*__position__c": 2, "*__fieldName__c": "LastName", "*__widthMedium__c": "7", "*__widthLarge__c": "7", "*__required__c": true},
    {"QualifiedApiName": "Contact_Details_Email", "*__position__c": 3, "*__fieldName__c": "Email", "*__widthMedium__c": "7", "*__widthLarge__c": "7", "*__required__c": true},
    {"QualifiedApiName": "Contact_Details_Phone", "*__position__c": 4, "*__fieldName__c": "Phone", "*__widthMedium__c": "5", "*__widthLarge__c": "5"}]}],
 "*__conditionalLogic__r": []}
```
The map is keyed by the Form Submission field, and the values inside the map's string use the full `FlowToolKit__` prefix. In a page section the form reads and writes only the Form Submission; the conversion fills the Contact. For a second person (an emergency contact as its own Contact), build a second component whose map applies to that person's Form Submission lookup.

### 3.14 One header for every form
A header or footer component is built on **Form Template** (`*__ObjectApiName__c` `*__Form_Template__c`), never on Form Submission: the template's Header/Footer settings list only Form Template components and clear any other on load. Before building one, reuse the packaged **Form Header Banner** (`FlowToolKit__Form_Header_Banner`): its banner section merges the template's own fields, `{{Name}}` for the title, `{{FlowToolKit__Form_Template_Subtitle__c}}`, `{{FlowToolKit__Header_Tags__c}}`, `{{FlowToolKit__Form_Banner_Image__c}}` and `{{FlowToolKit__Logo__c}}`, so one header serves every template and each shows its own title, image and logo. Build your own only when it needs more than the banner draws, and merge the same template fields so it stays shared.

## Part 4: From a plan.json field to package keys

form-design's plan names controls as the design system does. Translate them exactly this way, the same table build-template uses for a page section's own JSON, so the canvas and the build cannot drift:

| Plan field | Package keys |
|---|---|
| `field`, `widths: [large, medium, small]`, `required` | `*__fieldName__c`; `*__widthLarge__c`, `*__widthMedium__c`, `*__widthSmall__c` as strings; `*__required__c: true` |
| `label` | `*__customLabel__c` (up to 255; longer goes in `customLabelLong__c`) |
| `help` | `*__helpText__c`, with `*__helpTextDisplay__c` `Below Field` unless the plan says otherwise |
| `label_hidden: true` | `*__labelVariant__c: label-hidden` (the house rule): the label is hidden from view and screen readers still read it. `none` is an option only on purpose, because it also hides the label from screen readers (and drops a required field's star) |
| `control: Picklist` or `MultiPicklist`, `variant` | `*__picklistType__c` = the variant, unless it is `standard` |
| `control: Checkbox`, `variant: attestation` | `*__booleanType__c: attestation`, `*__labelVariant__c: none` (not a hidden label: the statement inside the card is the label, so an outer one would be read twice), and `*__Label_Rich_Text__c` = the label in bold as a first line, then the statement (`attestation_text` or `help`). Never `helpText__c`: it is capped at 255 and renders under the card |
| `control: Checkbox`, other variants | `*__booleanType__c` = the variant |
| `control: NumberInput`, `variant` | `*__numberType__c` (`stepper`, `slider`, `presetamounts`); `currency` needs no key, the field's type draws it |
| `control: TextArea` on a text field | `*__stringType__c: textarea` |
| `control: FileUpload` | `*__longTextType__c: fileUpload` |
| `control: ImageUpload`, `SignaturePad` | `*__richTextType__c: imageUpload` or `signaturePad` |
| `control: Address` | `*__addressFieldType__c` = the variant (`Address` for the compound row, then `Street`, `City`, ...) in an `addressSection` |
| `control: MultiPicklist`, `columns` | `*__picklistColumnsSize__c: size_1-of-<columns>` |
| `options` on a packaged Yes/No field, or on a new picklist several forms share | `*__picklistOptionOverrides__c` = the plan's options joined with `;` (each form shows only its own) |
| `option_descriptions` | `*__picklistOptionSettings__c` descriptions, keeping any label or icon already there |
| `config` | Copied as given (`acceptedFormats__c`, `referenceFieldOverrideType__c` ...) |
| A section's `rich_text` | Its own `richTextSection` ahead of the fields (frame `clean`), titled `<section title>: intro`, never `richText__c` on the input section, which renders out of line |
| A section's fields | An `inputSection` titled with the section's title in a few plain words; each address its own `addressSection` (the row and all five parts, split out of a section of other fields, which `component.py check` refuses); `likertSection` when `inner_type` says so |
| A field or section `condition` | A rule in `*__conditionalLogic__r` with the plan's `label` as its `Label`, the element's `*__displayType__c` SHOW (or the plan's mode), one condition per `conditions[]` entry |
| The component's `form_template_mapping` | `*__Submission_Field_Map__c`, inverted to be keyed by Form Submission field: `python3 scripts/component.py map plan.json --component <key>` |
