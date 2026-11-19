# FormStyle

How a design picks up a client's Form Style: the Basic values of a saved Form Style (`Form_Style__c`, set in the builder's Style Editor), applied to a form or a whole design.

The Style Editor itself is builder UI that respondents never see, so it isn't drawn here. Choosing the values for a client (brand color, font, radius and so on from their website) is a step in the form conversion workflow, not a component.

**Maps to:** a saved Form Style's Basic tab (`formStyleConfig`, `formStyleHooks`). Each value is the same `--ftk-*` token the package saves, and this system maps it onto its own tokens the way `formStyleHooks` maps it onto the SLDS styling hooks. Hand-written from `formStyleConfig`, `formStyleHooks` and `formStyleTokens`.

| Prop | Style Editor label | Saved token | What follows it |
| --- | --- | --- | --- |
| `brand` | Brand | `--ftk-color-primary` | Focus borders and rings, checked boxes, toggles, selected radios, separated buttons, survey cards, attestation, header rules and icons, dividers. Hover, pressed and tint shades are derived from it |
| `brandText` | Brand text | `--ftk-color-on-primary` | Text and checks on a brand fill |
| `inputText` | Input text | `--ftk-color-text` | Typed values and placeholders |
| `fieldLabels` | Field labels | `--ftk-color-label` | Field labels and toggle questions |
| `choiceText` | Choice text | `--ftk-color-option` | Picklist values, options, unselected separated buttons, checkbox and attestation text |
| `formBackground` | Form background | `--ftk-color-background` | The form's canvas |
| `cardBackground` | Card background | `--ftk-color-surface` | Dropdown panels, separated buttons, framed sections |
| `inputBackground` | Input background | `--ftk-color-control-surface` | Inputs, text areas, picklists, checkboxes, radios, survey cards, attestation cards; selected tints blend over it |
| `borders` | Borders | `--ftk-color-border` | Control and frame edges |
| `borderThickness` | Border thickness | `--ftk-border-scale` | A multiplier saved as a plain number: `1` keeps 1px edges, `2` doubles them (formStyleConfig: fallback "1", no unit). Never a percent: `200` scales every border and the docked buttons 200 times |
| `cornerRadius` | Corner radius | `--ftk-radius-medium` | px. Inputs, buttons, cards, frames and checkboxes; circles stay circular |
| `inputSize` | Input size | `--ftk-control-scale` | A multiplier saved as a plain number (`1` is 100%, `1.25` is 125%); the editor shows it as a percent. Control height, padding, choice marks and control text |
| `textSize` | Text size | `--ftk-font-scale` | A multiplier saved as a plain number (`1` is 100%, `1.25` is 125%); the editor shows it as a percent. Labels, help, messages, headers, dividers |
| `fieldSpacing` | Field spacing | `--ftk-spacing-scale` | A multiplier saved as a plain number (`1` is 100%, `1.25` is 125%); the editor shows it as a percent. The gap between field rows |
| `labelWeight` | Label weight | `--ftk-font-weight-label` | 100 to 900 |
| `paddingInline` | Horizontal padding | `--ftk-section-padding-inline` | px. Inset for the header and fields of unframed sections. Framed sections (Box, Shadow, Title on Border) keep their 20px inset whatever this is set to. Package gap: `sectionFrame` and `formSectionTheme` still let this value override the frame inset (`--_ftk-frame-padding-side` reads `--ftk-section-padding-inline` first) |
| `paddingBlock` | Vertical padding | `--ftk-section-padding-block` | px. Space above a section's fields |
| `font` | Font | `--ftk-font-family` | A CSS font stack |
| `<color>Opacity` | Opacity % | (part of the color) | 0 to 100 beside any color, for example `brandOpacity={80}` |

## Using it in a design
Wrap the form: `<FTK.FormStyle brand="#5b2a86" fieldLabels="#032d60" cornerRadius={12}>…</FTK.FormStyle>`. Leave a prop out to keep the package default, exactly as an unset Style Editor field does. `advanced` takes the Advanced tab's tokens by name (for example `{ 'input-radius': '16px', 'help-color': '#5c5c5c' }`) when a client needs one.

The card shows the same section twice: with no Form Style, then wrapped in the Grant Application | Demo template's Form Style.

## Handing it over
List each Basic value you set by its Style Editor label, for example `Brand #5b2a86 · Field labels #032d60 · Corner radius 12px · Input size 125%`. Anything not listed stays at its default.
