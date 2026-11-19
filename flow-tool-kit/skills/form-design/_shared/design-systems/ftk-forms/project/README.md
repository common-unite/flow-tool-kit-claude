# FlowToolKit Forms

The visual reference for designing Flow Tool Kit forms in Claude. Implementation partners use it to lay out forms and interfaces, then hand the design to Claude Code, which builds it with the real FlowToolKit package. Every component here is named and configured after an actual FlowToolKit field, so a design translates straight into field configuration.

These components are for designing, not for shipping. They redraw what the package renders in a Salesforce org so a design looks right. Production forms always come from the FlowToolKit LWCs.

## How FlowToolKit draws a form

FlowToolKit is built on Salesforce, so the Salesforce Lightning Design System (SLDS) is the base. Three layers decide what you see:

| Layer | What it is | What a design can change |
| --- | --- | --- |
| SLDS | Blueprints, spacing, type, control geometry | Nothing. Heights, radii, focus behavior and error treatment are the platform's. |
| `lightning-*` base components | `lightning-input`, `lightning-combobox`, `lightning-textarea` | Only what a styling hook exposes. |
| FlowToolKit | `flowFormField` and friends pick and arrange base components, and add a few controls SLDS has no blueprint for | The Form Theme and the field configuration. |

The FlowToolKit override layer works through one value: the **brand color**. A Form Theme's `brandColor__c` (or a Form Style's `--ftk-color-primary`) is mapped onto every SLDS hook at once, which is why fields here show green where stock Salesforce shows blue:

- Focus: the border turns `brand` and the glow becomes `focus-ring` (`0 0 3px` brand) instead of Salesforce blue.
- Checked checkboxes fill with `brand` and draw an `on-brand` check, where stock SLDS draws a blue tick on white.
- Toggles, selected radios, selected separated buttons and brand buttons use `brand`, with `brand-hover` and `brand-active` derived from it.
- The text of an unselected separated button is `brand`.

To show a client's look, wrap the form in `FormStyle` with the client's saved Form Style values (see the Form Style card). Brand alone moves everything above. Picking those values for a converted form is part of the conversion workflow.

## Designing with these fields

**Do**
- Build forms from these components: fields inside a `Section`, each field wrapped in a `Column`, using the variant names exactly as written (`separatedbuttons`, `attestation`, and so on). Those are the stored configuration values.
- Use the 12-column field grid. A field spans whole columns at three container widths (large, medium below 800px, small below 500px). Width is measured from the form's container, not the screen.
- Keep labels above the field (`labelVariant` `standard`). Inline labels (`label-inline`) are supported but not recommended for most forms.
- Show required fields with `required`. The asterisk hangs outside the label's left edge, in `error`.
- Write error messages in Salesforce's voice: "Complete this field." for a missing required answer.
- Pick the control from the field's data type first: a Picklist field uses a `Picklist` variant, a Multi-Select Picklist a `MultiPicklist` variant, a Checkbox a `Checkbox` variant, a Number, Currency or Percent field a `NumberInput`, and a Date, Time or Date/Time field a `DateInput`.

**Don't**
- Don't invent input styles, heights, radii or focus rings. A real form can't reach them.
- Don't free-place fields. They sit on the 12-column grid.
- Don't use color alone to show state. Errors also carry a message; selected options also carry a fill or a mark.
- Don't use em dashes in field copy.

## Visual foundations

- **Color.** White fields on a white or `surface-muted` ground. Text in `text`, labels in `label`, placeholders in `placeholder`. One accent: `brand`. Errors in `error`.
- **Type.** `field-label` (12px) over `field-value` (13px). Help text is `field-help` (10.4px) in `help`. Label size can be raised with the `labelSize` option (the Label sizes group). The family is DM Sans, applied through `--ftk-font-family`; an unthemed form uses the site's font.
- **Shape.** `radius-medium` (4px) on inputs, buttons and cards; `radius-small` on checkboxes; `radius-survey` (10px) on Survey Buttons; `radius-pill` on toggles, radios and the attestation mark.
- **Size.** Controls are `control-height` (32px). Choice marks are `choice-mark` (16px).
- **Depth.** Flat. The shadows are `focus-ring`, `error-ring`, the open `dropdown`, and `frame-shadow` on a Shadow section.
- **Sections.** A section's title, subtitle and every field share one left edge: `section-inset` (0.8rem) for Classic, Card and Hero headers, and 1.25rem (20px) inside a Box or Shadow frame, where the frame border sits 20px from the fields and 24px below the last one. Classic headers draw a 2px `brand` rule; framed sections use `frame-border` at `radius-frame` (8px).

## Form-type rules

Which banner, button position, stage indicator, page headings and first page a form gets depends on its type, page count and length. The one canonical table is the form-type rules standard in the Flow Tool Kit plugin. In brief:

| Form | Banner | Buttons | Indicator |
| --- | --- | --- | --- |
| One page (survey or simple form) | Compact, Small, `singleCardHeader` | `Footer`, `spread` | Hidden |
| Two pages | Overlay, Small, `singleCardHeader` | `Footer`, `spread` | Hidden |
| Three or more pages, not long | Overlay, Small, `singleCardHeader` | `Docked`, `spread` | `base` |
| Long: an application or grant with three or more pages, or any form of three or more pages and about 10 minutes or more | Overlay, Small, `header`, Display Template Header | `Docked`, `center`, Save Progress | Stages mode, `vertical`, review screen |

Forward buttons read Continue, never Next. No "Page N of M" page headings. Intro pages are rare: most forms need none. The valid case is a long-form application, especially in stages mode, where an About or Learn More page of long-form information before the application is valuable; its label is meaningful ("About the Program", "Learn More"), never "Welcome", and its button Learn More or Get Started. Never leave a page labelled "Welcome". Templates and recipes we ship keep the default theme on the Form Template, with no theme per template and no new packaged Form Theme records; a client's look is Form Style values, and a client org may still use its own theme.

## Components

| Component | FlowToolKit source | Configuration |
| --- | --- | --- |
| `TextInput` | `flowFormField` drawing `lightning-input` | `stringType__c` = `standard` |
| `TextArea` | `flowFormField` drawing `lightning-textarea` plus its character counter | `stringType__c` = `textarea`, or a Long Text Area field; `textAreaMinHeight__c` / `textAreaMaxHeight__c` (`minHeight` for essay answers) |
| `Picklist` | `lightning-combobox`, `flowFormRadioCheckbox`, `flowFormPathPicklist`, `flowFormVisualPicker` | `picklistType__c` = `standard`, `radio`, `radiobuttons`, `separatedbuttons`, `surveybuttons`, `pathbuttons`, `iconbuttons`, `visualpicker` |
| `MultiPicklist` | `flowFormMultiselectCheckbox`, `comboBox`, `lightning-dual-listbox` | `picklistType__c` = `multiselectcheckbox`, `selectallmultiselectcheckbox`, `separatedbuttons`, `multiselectbadge`, `combobox`, `visualpicker`, `standard` (dual listbox); `max`; exclusive values such as None of the above |
| `Checkbox` | `flowFormCheckbox` | `booleanType__c` = `default` (toggle), `checkbox`, `attestation`, `picklist`, `radio`, `radiobuttons`; `booleanPicklistTypeOverride__c` = `True/False` (default), `Yes/No`, `Active/Inactive`, `Enabled/Disabled`, `Valid/Invalid`, `On/Off` for the two-choice labels and the positioned toggle's state text |
| `NumberInput` | `flowFormField` number, currency, percent; `flowFormNumberInput` | `numberType__c` = `standard`, `stepper`, `slider`, `presetamounts`; format, min, max, step, presets |
| `DateInput` | `lightning-input` date, time, datetime | type; `minDateType__c` / `maxDateType__c` limits |
| `Section` | `formSectionTheme`, `sectionFrame`, `header` | `sectionTheme__c` = `clean`, `box`, `shadow`; header style `classic`, `classicSpread`, `card`, `outlined`, `hero`; accordion sections; the Form Theme heading colors |
| `Column` | the field grid | `widthLarge__c`, `widthMedium__c`, `widthSmall__c` |
| `Divider` | `formSectionDivider` | `Divider_Style__c` (12 styles), as a divider section or a section header (`Header_Display__c` = `Divider`) |
| `FormStyle` | a saved Form Style's Basic values (`formStyleConfig`, `formStyleHooks`); the Style Editor itself is builder UI and isn't drawn | The 18 Basic overrides: brand, text, background and border colors, border thickness, corner radius, input size, text size, field spacing, label weight, section padding and font |
| `Icon` | `lightning-icon` | Any SLDS 2.30.7 icon name: `utility:*`, `standard:*`, `action:*`, `custom:*`, `doctype:*` |
| `Lookup` | `flowFormField` reference (`lightning-input-field`), `flowFormLookup`, `lightning-record-picker` | `referenceFieldOverrideType__c` = `standard`, `recordpicker`; `enableCustomLookup__c` (variant `customSearch`) |
| `Address` | `flowFormFieldAddress` (`lightning-input-address`) | Address lookup, State and Country picklists, per-part labels, placeholders and requiredness, read-only formatted address |
| `FormattedInput` | `flowFormField` tel, email, url | `phoneMask__c` = `(xxx) xxx-xxxx`, `xxx-xxx-xxxx`, `xx xxxx xxxx`, `xxxx xxx xxx`, `none` |
| `RichTextInput` | `flowFormRichTextInput` (`lightning-input-rich-text`) | `richTextType__c` = `standard`; `RichTextFormats__c`; `enableRichPlainTextToggle__c`; `textAreaMinHeight__c` / `textAreaMaxHeight__c` |
| `RichText` | `flowFormRichText` | `Header_Text_Variant__c` = `default`, `highlight`, `info`, `warning`, `error`, `success` |
| `FieldPrompt` | `flowFormPrompt` | `fieldPrompt__c`; `promptDisplayType__c` = `prompt`, `richtext`; `promptColor__c`, `promptFontColor__c` |
| `FileUpload` | `formFieldFileUpload`, `formFieldFileUploadDetail` (`lightning-file-upload`) | `longTextType__c` = `fileUpload`; `uploadMultipleFiles__c`, `max`, `acceptedFormats__c`, `fileNameFormat__c`, `preventFileDeletion__c`, `disablePreviewLink__c` |
| `ImageUpload` | `imgUpload` | `richTextType__c` = `imageUpload` |
| `SignaturePad` | `signaturePad` | `richTextType__c` = `signaturePad` |
| `DisplayImage` | `displayImage` | `contentAssetName` / `customImageLink`, `imageStyle`, `overlayHexColor`, `overlayOpacity`, `customRichText` with `overlayMode` (`viewAsPlainText__c`: rich text or HTML), `parallax` (`imageParallax__c`), top and bottom margin |
| `Illustration` | `displayIllustration`, `displayIllustrationArt` | `type` (23 scenes), `size` `small` / `large`, title, subtitle, top and bottom margin |
| `LikertMatrix` | `flowFormLikertMatrix` (Likert Matrix section) | `Likert_Mode__c` = Picklist or Number, `Likert_Scale__c`, `Show_Total_Score__c`, `Total_Score_Label__c`; grid, stacked under 480px |
| `Repeater` | `flowFormRepeat` | Repeats a form component once per record: `min` / `max`, `allowNew`, `allowDelete`, `allowClone`, `allowReposition`, `allowEdit`, `allowImport`, button labels, record widths and spacing. Not a table (`flowDataTable` is not drawn yet); pagination (`flowPagination`) when the records exceed `max` |
| `RecordCard` | `recordCard`, `recordCardConfig` | `cardType`: `mediaTop`, `photoOverlay`, `dateTile`, `progress`, `headerBand`, `strip`, `countdown`, `iconLead`, `profile`, `fieldList`, `valueSpotlight`; `cardStyle` elevated, outlined, flat |
| `ContactUsForm` | a one-page `formTemplate` | The Contact Us form for a site's Contact page; the Site Blocks design system's Form Slot draws it |
| `VolunteerApplicationForm` | a four-page `formTemplate`, path indicator (predates the 2026-11-17 form-type rules; see its card) | The volunteer application for a site's Volunteer page, on its first page; drawn by the Site Blocks Form Slot |
| `GrantApplicationForm` | a Stages Mode `formTemplate`, overview | A grant application with a header Banner and page rows, for an application's record page; drawn by the Site Blocks Form Slot |
| `Tabset` (with `Tab`) | `flowForm` tabset template | `FlowToolKit__type__c` = `default`, `scoped`, `vertical`; section icon and error indicator per tab |
| `Carousel` (with `Tab`) | `flowForm` carousel template | `FlowToolKit__type__c` = `carousel`: one section at a time, progress indicator, Back / Continue / Finish |
| `StageIndicator` | `formStageIndicator` | `Stage_Indicator_Type__c` = `base`, `path`, `vertical`, `footer base`, `footer path`; Stages Mode status markers |
| `StagesOverview` | `formTemplateStages`, `formTemplateStageRow` | `Stages_Mode__c`; `Stage_Mode_Layout__c`; page label, description, estimated time, button label; stage status |
| `Buttons` (alias `Navigation`) | `buttonsCustom` on a form template or a Flow screen: navigation and action buttons | Form Template: `Buttons_Position__c` = `Docked`, `Footer`, `Standard`; `Button_Alignment__c` = `start`, `center`, `end`, `spread`, `space`; page and submit button labels; Save Progress. Flow screen only: custom buttons, `numberOfButtonsToShow`, `groupButtons`, `showAsPath`, `enableModal` |
| `ReviewPage`, `ReviewSection`, `ReviewField` | Form Template review screen, `flowFormReview`, `flowFormFieldReview` | `Enable_Review_Screen__c`, `Review_Page_Label__c`, `Review_Page_Subtitle__c`; Edit or View per section; values by data type |
| `FormTemplate` | `formTemplate` | The whole template: header and footer forms (`FormQualifiedApiName_Header__c` / `_Footer__c`, footer disabled), stage mode, page header, buttons, `readOnly`, `Enable_Autosave__c` (no visual), and `state` = `active`, `inactive`, `confirmation`, `loading`, `error` |
| `PageHeader` | `formTemplatePageHeader` | Page `Header_Style__c` = `classic`, `classicSpread`, `hero`; kicker, lead, tags, `Header_Tags_Position__c`, icon, margins, `Show_Header__c` |
| `ConfirmationPage` | `formTemplate` confirmation branch | `Confirmation_Page_Message__c`, `Skip_Confirmation_Page__c`; View Receipt after payment |
| `LoadingStencil`, `Spinner` | `formLoadingStencil`, `lightning-spinner` | Shown while a prefill flow runs |
| `ConfirmModal` | `buttonsCustom` `enableModal` | `modalHeading`, `modalSubheading`, `modalBody`, confirm and cancel labels, `modalTheme` |
| `SurveyQuestion`, `SurveyScope` | `formSurveyQuestion`, `formSurveyScope`, the survey veil | `Survey_Section__c`: question count, Required and Answered pills, Next, dimmed inactive questions |
| `PaymentStep`, `StripePaymentElement` | Stripe Connector `stripePaymentForm`, the `StripePaymentForm` page and Stripe's Payment Element | `Payment_Required__c`, `Payment_Conditions__c`; Hide Header, billing address, Link, Express Checkout and button type; payment, subscription or setup; declined payment and Payment Unavailable |
| `BrandFooter` | `flowToolKitBrandFooter` | Free-version footer, logo left out |
| `LookupSearchTable` | `flowFormLookup` custom search | `enableCustomLookup__c`, `customLookupHeader__c`, `customLookupSubheader__c` |
| `SectionGrid` | the form body grid | Sections with `large` / `medium` / `small` widths sit side by side |

The fields share the `flowFormFieldLabel` label: `required`, `helpText` with `helpTextDisplay` (`Hover Bubble`, `Below Label`, `Below Field`), `labelSize`, and `labelHidden` (builds as `labelVariant__c` `none`, which also drops the required star; `label-hidden` keeps the star). Every field also takes the shared `flowFormField` options: `labelVariant` (`standard`, `label-stacked`, `label-inline` with `inlineLabelWidth`, `label-hidden`, `none`), `prepend` / `append`, `labelRichText`, `topMargin` / `bottomMargin`, `alignCenter`, `plainText` (`viewAsPlainText__c`), `disableHelpText`, and `customValidationMessage`. `Column` takes `large="shrink"`. The TextInput card shows them all.

`FormStyle` takes the 139 Advanced tokens as `advanced` (`FTK.FORM_STYLE_ADVANCED`).

## Handing a design to Claude Code

A handoff is ready when it says, for every field:

1. The Salesforce field it collects, or a plain-language name if the field doesn't exist yet.
2. The component and its variant, using the names above (for example `Picklist · separatedbuttons`).
3. Its width in columns at large, medium and small (for example 6 / 12 / 12).
4. Its label, help text and `helpTextDisplay`, whether it's required, and its options in order.
5. The section it sits in, and the section order.

And for every section: its title, subtitle and SLDS icon name, its frame (`clean`, `box`, `shadow`), its header style (`classic`, `classicSpread`, `card`, `outlined`, `hero`), whether it is an accordion, whether its header displays as a divider (and which `Divider_Style__c`), and any heading colors it changes from the form's theme. Divider sections go in the section order like any other.

And once for the form: the Form Style Basic values you set, by their Style Editor labels (for example `Brand #5b2a86 · Corner radius 12px`), plus any Form Theme values you changed (label color, label size, borders, backgrounds, heading colors) when the form is for a client org that keeps its own theme. A template or recipe we ship keeps the default theme and changes nothing here. Anything you couldn't express with these components goes in a "Needs a build change" list instead of being drawn.

A good line looks like this: `Household size · Picklist · separatedbuttons · 12/12/12 · required · options: 1 to 5, 6 to 20, 21 to 50, 51 or more`.

## Accessibility

Field text passes 4.5:1 on its ground: `text` 17.8:1, `label` 9.7:1, `placeholder` 4.7:1, `error` 4.7:1, `brand` 4.7:1 and `on-brand` on `brand` 4.7:1. A few values are kept because Salesforce or the package ships them, and they're flagged here rather than changed:

- `help` is 3.1:1 on white, under the 4.5:1 text minimum. Prefer `Hover Bubble` for help that matters.
- The character counter draws `text` at 50% opacity, about 3.4:1.
- `border` (#c9c9c9) is 1.7:1 and `toggle-off` (#aeaeae) is 2.2:1 on white, under the 3:1 guide for control edges. These are SLDS's own values.

A client brand color must reach 4.5:1 against white for the same reasons `brand` does.

## Source

Hand-written from the Flow Tool Kit package source: `formSectionDivider`, `flowFormField`, `flowFormFieldLabel`, `flowFormRadioCheckbox`, `flowFormResponsiveChoice`, `joinedChoiceStyles`, `flowFormPathPicklist`, `flowFormVisualPicker`, `flowFormNumberInput`, `flowFormMultiselectCheckbox`, `comboBox`, `flowFormCheckbox`, `separatedButtonStyles`, `formSectionTheme`, `sectionFrame`, `sectionFrameOptions`, `header`, `formStyles`, `formStyleHooks` and `formStyleTokens`, with SLDS 2.30.7 blueprint values.

Icons are the Salesforce Lightning Design System icons, version 2.30.7, copyright Salesforce, licensed CC BY-ND 4.0 (https://creativecommons.org/licenses/by-nd/4.0/), artwork unchanged. See `assets/Icons/`.

**Not drawn, by decision.** Admin-only screens (survey results, builder selectors), grouped comboboxes, lookup overrides that open another form, currency display options, reCAPTCHA, heading and form background images, the visual-picker section theme, repeater carousel autoplay, the dynamic repeater, filter panels, the record card Edit modal, and style sheets.

**The package draws nothing for these, so they are handoff values only:** autosave status, quiz correct or incorrect marks, the template banner image (`Form_Banner_Image__c`, stored but only read by Apex), `Confirmation_Page_Label__c`, and `Do_Not_Print__c`.

**Still not synced.** Brand logos (each form's logo comes from its brand kit). The DM Sans font files (DM Sans loads from Google Fonts). An SLDS 2 (Cosmos) profile: everything here is the standard SLDS 1 look.
