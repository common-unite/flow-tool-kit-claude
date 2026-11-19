# Flow Tool Kit style variables

Every Form Style setting an admin can set in Flow Tool Kit, as the CSS custom property a custom component reads. The list is read from the package's style runtime (release 5.3): the settings editor and the runtime list the same 157 names. `scripts/check_lwc.py` checks every `var(--ftk-...)` in a component against `scripts/style_tokens.json`, the same list.

## How the values get there

- **Org Form Style defaults** (Form Builder, Global Styles) and the **template's Style Overrides** are written onto the Form Template's outer container as custom properties. The template's value wins over the org's.
- **The template's theme** sets `--ftk-color-primary` from its Brand color, and `--borderColor` from its border color. A brand theme also sets Lightning's own button, input, checkbox and toggle styling hooks, so a `lightning-button` with `variant="brand"` inside your component follows the brand with no CSS at all.
- **A section theme** sets `--borderColor` and `--labelColor` for that one section.
- **A form on a flow screen with no template** carries the org's Form Style defaults on its own container, once the org has any.
- Custom properties inherit through shadow DOM, so a component inside a page section or a Form Component section reads them directly.

A variable exists only where one of those set it. An org with no Form Style settings sets none of them, and a component placed outside any form (on a record page, say) sees none. **So every `var()` has a fallback**, and the safest fallback is the chain the package itself uses: a specific setting, then the general one, then a plain value.

```css
.fee-card {
    border: var(--ftk-section-border-width, var(--ftk-border-width, 1px)) solid var(--ftk-section-border-color, var(--ftk-color-border, #dddbda));
    border-radius: var(--ftk-section-radius, var(--ftk-radius-medium, 5px));
    padding: var(--ftk-section-padding, 0.75rem);
}
.fee-card__total { color: var(--ftk-color-primary, #0176d3); }
```

**Scale settings** (kind `scale`) are plain multipliers with no unit, 1 by default. Multiply a length by them: `calc(1rem * var(--ftk-font-scale, 1))`.

## Never use

- Anything starting `--_ftk-`: private to the package, renamed without notice.
- Any other `--ftk-` name you see in the browser's inspector (banner, hero, site, survey card, frame and header internals). They belong to one package component and are not settings an admin controls; build only on the names below.
- Flow Tool Kit's style modules themselves (`formStyles` and its relatives). They are internal to the package, so a component in your org cannot import them.

## Theme variables

| Variable | Set by |
|---|---|
| `--borderColor` | Border color of the template's theme, or of the section's own theme inside a themed section. |
| `--labelColor` | Label color of a section theme, inside that section only. |

## The settings, by group

The group and label are what the admin sees in Form Style settings, so you can tell them which setting changes your component.

### Form fields

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-spacing-scale` | Field spacing | scale | Scales only the vertical gaps between field rows. |
| `--ftk-control-scale` | Input size | scale | Scales inputs, their text, inner padding and icons, choice controls, and buttons together. |
| `--ftk-radius-scale` | Corner scale | scale | Scales the rounding of input, button, choice, and card corners. |
| `--ftk-font-weight-label` | Label weight | font-weight | Controls how light or bold field labels appear. |
| `--ftk-border-scale` | Border thickness | scale | Scales input, textarea, choice, button, and section border thickness. |
| `--ftk-radius-medium` | Corner radius | length or percentage | One corner radius for inputs, buttons, choices, and containers. |

### Text

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-font-scale` | Text size | scale | Scales field labels, help text, headings, stage text, and unformatted rich text. Input text follows Input size. |
| `--ftk-font-family` | Font | font-family | Font for the whole form. |

### Form layout

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-section-padding-inline` | Horizontal padding | length | Sets left and right padding inside form sections. |
| `--ftk-section-padding-block` | Vertical padding | length | Sets top and bottom padding inside form sections. |
| `--ftk-layout-spacing-scale` | Section padding | scale | Scales padding around form sections without changing field gaps or input padding. |

### Color

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-color-primary` | Brand | color | Primary actions and selected controls; inherits host brand unless explicitly overridden |
| `--ftk-color-option` | Choice text | color | Text in radio choices, checkboxes, pills, and dropdown options. Selected brand buttons use Brand text. |
| `--ftk-color-label` | Field labels | color | Text above or beside each field, independent of Input text and Choice text. |
| `--ftk-color-text` | Input text | color | Text entered in inputs and textareas. Field labels, choices, and form content keep their own colors. |
| `--ftk-color-on-primary` | Brand text | color | Foreground on selected/primary surfaces |
| `--ftk-color-footer` | Color Footer | color | Docked action bar surface |
| `--ftk-color-footer-border` | Color Footer Border | color | Docked action bar top boundary |

### State

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-color-primary-hover` | Color Primary Hover | color | Primary hover shade; follows primary unless overridden; optional override |
| `--ftk-color-primary-active` | Selected state | color | Primary pressed shade; follows primary unless overridden; optional override |
| `--ftk-focus-ring` | Focus Ring | box-shadow | Visible keyboard focus; optional override |
| `--ftk-color-danger` | Color Danger | color | Color of field errors: the error border, icon and message, the required mark, and the attestation error tint. |

### Surfaces

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-color-background` | Form background | color | Background behind the entire form template. Transparent lets the page background show through. |

### Typography

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-font-size` | Body and input text size | font-size | Sets inherited body and input text size. Native controls may grow to fit larger text. Labels and headings have separate controls. |
| `--ftk-line-height` | Text line spacing | number or length | Line spacing for body text, rich text and multiline inputs. Headings retain independent spacing. |

### Labels and help

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-font-size-label` | Field label text size | font-size | Default label size |
| `--ftk-label-gap` | Label-to-control gap | length | Gap below default field labels |
| `--ftk-help-font-size` | Help text size | font-size | Help text size for labels and help. Specific overrides take priority over shared controls. |
| `--ftk-help-color` | Help text color | color | Help text color for labels and help. Specific overrides take priority over shared controls. |

### Headers

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-font-size-heading` | Font Size Heading | font-size | Section title size |
| `--ftk-font-weight-heading` | Font Weight Heading | font-weight | Section title weight |
| `--ftk-heading-background` | Heading Background | color | Default header surface |
| `--ftk-heading-border-color` | Heading Border Color | color | Default header rule color |
| `--ftk-heading-border-width` | Heading Border Width | border-width | Default header rule thickness |
| `--ftk-font-family-heading` | Font Family Heading | font-family | Section-heading typeface independent of body copy |
| `--ftk-heading-letter-spacing` | Heading Letter Spacing | letter-spacing | Section-heading tracking |
| `--ftk-heading-text-transform` | Heading Text Transform | text-transform | Section-heading case treatment without changing authored text |
| `--ftk-header-shadow` | Header shadow | box-shadow | Header shadow for headers. Specific overrides take priority over shared controls. |
| `--ftk-heading-line-height` | Heading line spacing | number or length | Heading line spacing for headers. Specific overrides take priority over shared controls. |
| `--ftk-header-radius` | Header corners | length | Header corners for headers. Specific overrides take priority over shared controls. |
| `--ftk-header-padding-block` | Header vertical padding | length | Header vertical padding for headers. Specific overrides take priority over shared controls. |
| `--ftk-header-padding-left` | Header left padding | length | Header left padding for headers. Specific overrides take priority over shared controls. |
| `--ftk-header-padding-right` | Header right padding | length | Header right padding for headers. Specific overrides take priority over shared controls. |
| `--ftk-header-title-color` | Header title color | color | Title color for section headers. A Form Theme's heading color takes priority, except the packaged Form Default theme. |
| `--ftk-header-subtitle-color` | Header subtitle color | color | Header subtitle color for headers. Specific overrides take priority over shared controls. |

### Spacing

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-field-gap` | Additional field gap | length | Additional field separation |

### Shape

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-container-border-width` | Container Border Width | border-width | Decorative template framing independent of essential field boundaries |

### Sections

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-plain-section-padding-top` | Plain section padding - top | length | Plain section padding - top for sections. Specific overrides take priority over shared controls. |
| `--ftk-boxed-section-padding-top` | Boxed section padding - top | length | Boxed section padding - top for sections. Specific overrides take priority over shared controls. |
| `--ftk-plain-section-padding-right` | Plain section padding - right | length | Plain section padding - right for sections. Specific overrides take priority over shared controls. |
| `--ftk-boxed-section-padding-right` | Boxed section padding - right | length | Boxed section padding - right for sections. Specific overrides take priority over shared controls. |
| `--ftk-plain-section-padding-bottom` | Plain section padding - bottom | length | Plain section padding - bottom for sections. Specific overrides take priority over shared controls. |
| `--ftk-boxed-section-padding-bottom` | Boxed section padding - bottom | length | Boxed section padding - bottom for sections. Specific overrides take priority over shared controls. |
| `--ftk-plain-section-padding-left` | Plain section padding - left | length | Plain section padding - left for sections. Specific overrides take priority over shared controls. |
| `--ftk-boxed-section-padding-left` | Boxed section padding - left | length | Boxed section padding - left for sections. Specific overrides take priority over shared controls. |
| `--ftk-section-header-gap` | Gap below section header | length | Gap below section header for sections. Specific overrides take priority over shared controls. |
| `--ftk-section-radius` | Section corners | length | Section corners for sections. Specific overrides take priority over shared controls. |
| `--ftk-section-border-width` | Section border width | border-width | Section border width for sections. Specific overrides take priority over shared controls. |
| `--ftk-section-border-color` | Section border color | color | Section border color for sections. Specific overrides take priority over shared controls. |
| `--ftk-section-shadow` | Section shadow | box-shadow | Section shadow for sections. Specific overrides take priority over shared controls. |

### Form card

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-form-card-radius` | Form card corners | length | Form card corners for form card. Specific overrides take priority over shared controls. |
| `--ftk-form-card-shadow-hover` | Form card hover shadow | box-shadow | Form card hover shadow for form card. Specific overrides take priority over shared controls. |
| `--ftk-form-card-shadow` | Form card shadow | box-shadow | Form card shadow for form card. Specific overrides take priority over shared controls. |
| `--ftk-form-card-surface` | Form card background | color | Form card background for form card. Specific overrides take priority over shared controls. |
| `--ftk-form-card-border-color` | Form card border color | color | Form card border color for form card. Specific overrides take priority over shared controls. |

### Text fields

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-read-only-radius` | Read-only text corners | length | Corners of a read-only text input and of the read-only long-text box. Specific overrides take priority over shared controls. |
| `--ftk-read-only-border-width` | Read-only long-text border width | border-width | Border width of the read-only long-text box (a read-only long text with a maximum height). A read-only input keeps the platform's disabled border. Specific overrides take priority over shared controls. |
| `--ftk-read-only-border-color` | Read-only long-text border color | color | Border color of the read-only long-text box (a read-only long text with a maximum height). A read-only input keeps the platform's disabled border. Specific overrides take priority over shared controls. |
| `--ftk-richtext-radius` | Rich-text editor corners | length | Rich-text editor corners for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-radius` | Input corners | length | Input corners for text fields. Specific overrides take priority over shared controls. |
| `--ftk-textarea-radius` | Textarea corners | length | Textarea corners for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-border-color` | Input border color | color | Input border color for text fields. Specific overrides take priority over shared controls. |
| `--ftk-textarea-border-color` | Textarea border color | color | Textarea border color for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-surface` | Input background | color | Input background for text fields. Specific overrides take priority over shared controls. |
| `--ftk-textarea-surface` | Textarea background | color | Textarea background for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-padding-inline` | Input horizontal padding | length | Input horizontal padding for text fields. Specific overrides take priority over shared controls. |
| `--ftk-textarea-padding-inline` | Textarea horizontal padding | length | Textarea horizontal padding for text fields. Specific overrides take priority over shared controls. |
| `--ftk-textarea-padding-block` | Textarea vertical padding | length | Textarea vertical padding for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-height` | Input height | length | Input height for text fields. Specific overrides take priority over shared controls. |
| `--ftk-input-placeholder-color` | Placeholder text color | color | Placeholder text in empty inputs and text areas. Follows an authored input text color unless overridden. |

### Survey choices

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-survey-height` | Survey choice minimum height | length | Survey choice minimum height for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-radius` | Survey choice corners | length | Survey choice corners for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-border-width` | Survey choice border width | border-width | Survey choice border width for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-border-color` | Survey choice border color | color | Survey choice border color for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-surface` | Survey choice background | color | Survey choice background for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-padding-inline` | Survey horizontal padding | length | Survey horizontal padding for survey choices. Specific overrides take priority over shared controls. |
| `--ftk-survey-padding-block` | Survey vertical padding | length | Survey vertical padding for survey choices. Specific overrides take priority over shared controls. |

### Joined choices

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-joined-choice-padding-inline` | Joined-choice horizontal padding | length | Joined-choice horizontal padding for joined choices. Specific overrides take priority over shared controls. |
| `--ftk-joined-choice-radius` | Joined-choice corners | length | Joined-choice corners for joined choices. Specific overrides take priority over shared controls. |

### Separated choices

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-separated-choice-height` | Separated-choice minimum height | length | Separated-choice minimum height for separated choices. Specific overrides take priority over shared controls. |
| `--ftk-separated-choice-radius` | Separated-choice corners | length | Separated-choice corners for separated choices. Specific overrides take priority over shared controls. |
| `--ftk-separated-choice-line-height` | Separated-choice line spacing | number or length | Separated-choice line spacing for separated choices. Specific overrides take priority over shared controls. |
| `--ftk-separated-choice-padding-inline` | Separated-choice horizontal padding | length | Separated-choice horizontal padding for separated choices. Specific overrides take priority over shared controls. |
| `--ftk-separated-choice-padding-block` | Separated-choice vertical padding | length | Separated-choice vertical padding for separated choices. Specific overrides take priority over shared controls. |

### Visual choices

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-visual-choice-radius` | Visual-choice corners | length | Visual-choice corners for visual choices. Specific overrides take priority over shared controls. |
| `--ftk-visual-choice-border-width` | Visual-choice border width | border-width | Visual-choice border width for visual choices. Specific overrides take priority over shared controls. |
| `--ftk-visual-choice-border-color` | Visual-choice border color | color | Visual-choice border color for visual choices. Specific overrides take priority over shared controls. |
| `--ftk-visual-choice-surface` | Visual-choice background | color | Visual-choice background for visual choices. Specific overrides take priority over shared controls. |

### Matrix

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-matrix-radius` | Matrix frame corners | length | Matrix frame corners for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-card-radius` | Matrix card corners | length | Matrix card corners for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-secondary-font-size` | Matrix secondary text size | font-size | Matrix secondary text size for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-secondary-color` | Matrix secondary text color | color | Matrix secondary text color for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-choice-border-width` | Matrix choice border width | border-width | Matrix choice border width for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-choice-surface` | Matrix choice background | color | Matrix choice background for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-shade` | Matrix shaded background | color | Matrix shaded background for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-border-color` | Matrix frame border color | color | Matrix frame border color for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-divider-color` | Matrix divider color | color | Matrix divider color for matrix. Specific overrides take priority over shared controls. |
| `--ftk-matrix-choice-border-color` | Matrix choice border color | color | Matrix choice border color for matrix. Specific overrides take priority over shared controls. |

### Checkboxes

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-attestation-radius` | Attestation corners | length | Attestation corners for checkboxes. Specific overrides take priority over shared controls. |
| `--ftk-attestation-surface` | Attestation background | color | Attestation background for checkboxes. Specific overrides take priority over shared controls. |
| `--ftk-attestation-target-size` | Attestation target size (platform limited) | length | Attestation target size for checkboxes. Specific overrides take priority over shared controls. |
| `--ftk-checkbox-radius` | Checkbox corners | length | Checkbox corners for checkboxes. Specific overrides take priority over shared controls. |
| `--ftk-checkbox-border-color` | Checkbox border color | color | Checkbox border color for checkboxes. Specific overrides take priority over shared controls. |
| `--ftk-checkbox-surface` | Checkbox background | color | Unchecked checkbox fill. Follows Input background; a specific override takes priority. |

### Calendar

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-calendar-day-size` | Calendar day size | length | Calendar day size for calendar. Specific overrides take priority over shared controls. |
| `--ftk-calendar-font-size` | Calendar text size | font-size | Calendar text size for calendar. Specific overrides take priority over shared controls. |
| `--ftk-calendar-border-width` | Calendar border width | border-width | Calendar border width for calendar. Specific overrides take priority over shared controls. |
| `--ftk-calendar-border-color` | Calendar border color | color | Calendar border color for calendar. Specific overrides take priority over shared controls. |

### Modals

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-modal-surface` | Modal background | color | Modal background for modals. Specific overrides take priority over shared controls. |

### Tables

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-table-shadow` | Table shadow | box-shadow | Table shadow for tables. Specific overrides take priority over shared controls. |
| `--ftk-table-shade` | Table shaded background | color | Table shaded background for tables. Specific overrides take priority over shared controls. |
| `--ftk-table-surface` | Table background | color | Table background for tables. Specific overrides take priority over shared controls. |

### Dividers

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-divider-subtitle-color` | Divider subtitle color | color | Divider subtitle color for dividers. Specific overrides take priority over shared controls. |
| `--ftk-divider-rule-color` | Divider rule color | color | Divider rule color for dividers. Specific overrides take priority over shared controls. |

### Buttons

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-button-radius` | Button corners | length | Button corners for buttons. Specific overrides take priority over shared controls. |
| `--ftk-button-font-size` | Button text size | font-size | Text size for action buttons, independent of their height and other form text. |
| `--ftk-button-height` | Button height | length | Button height for buttons. Specific overrides take priority over shared controls. |
| `--ftk-icon-button-size` | Icon button size (platform limited) | length | Icon button size for buttons. Specific overrides take priority over shared controls. |

### Shared overrides

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-color-text-muted` | Color Text Muted | color | Secondary help foreground |
| `--ftk-color-surface` | Card background | color | Background of cards, choice tiles, and panels. Input field background can be changed separately. |
| `--ftk-color-border` | Borders | color | Essential field boundaries |
| `--ftk-color-border-muted` | Color Border Muted | color | Decorative container boundaries |
| `--ftk-font-size-small` | Font Size Small | font-size | Help text size |
| `--ftk-border-width` | Border Width | border-width | Boundary thickness |
| `--ftk-input-padding-x` | Input Padding X | length | Horizontal control padding |
| `--ftk-input-padding-y` | Input Padding Y | length | Vertical control padding |
| `--ftk-control-height` | Control height | length | Control minimum target height |
| `--ftk-shadow-medium` | Shadow Medium | box-shadow | Container elevation |
| `--ftk-color-surface-muted` | Color Surface Muted | color | Subtle secondary surfaces |
| `--ftk-radius-small` | Radius Small | length or percentage | Compact control corners |
| `--ftk-section-padding` | Shared section padding fallback | length | One CSS length shared by boxed section sides/bottom and standard headers. Use the separate section-content edge controls for independent spacing. |
| `--ftk-section-padding-top` | Section content padding - top | length | Controls only the top inset of plain and boxed section content. Header padding and special address/image layouts remain separate. |
| `--ftk-section-padding-right` | Section content padding - right | length | Controls only the right inset of plain and boxed section content. Header padding and special address/image layouts remain separate. |
| `--ftk-section-padding-bottom` | Section content padding - bottom | length | Controls only the bottom inset of plain and boxed section content. Header padding and special address/image layouts remain separate. |
| `--ftk-section-padding-left` | Section content padding - left | length | Controls only the left inset of plain and boxed section content. Header padding and special address/image layouts remain separate. |
| `--ftk-radius-large` | Radius Large | length | Template card corners; separate scale for large surfaces |
| `--ftk-color-control-surface` | Input background | color | Fill inside inputs, textareas, dropdowns, survey choices, visual pickers, and attestation cards. |

### Stacked headers

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-hero-title-size` | Title size | font-size | Title size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-eyebrow-size` | Eyebrow size | font-size | Eyebrow size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-kicker-size` | Pretitle size | font-size | Pretitle size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-lead-size` | Body size | font-size | Body size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-footer-size` | Footer size | font-size | Footer size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-tag-size` | Tag text size | font-size | Tag text size for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-line-gap` | Space between lines | length | Space between lines for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-lead-gap` | Title to body gap | length | Title to body gap for the Stacked header style. Shared text and layout scales apply until a specific value is set. |
| `--ftk-hero-max-width` | Maximum text width | length | Maximum text width for the Stacked header style. Shared text and layout scales apply until a specific value is set. |

### Section surfaces

| Variable | Setting | Kind | What it styles |
|---|---|---|---|
| `--ftk-section-surface` | Frame background | color | Default fill of Box, Shadow, Card and Title on border frames. An explicit Classic Theme section background takes priority. |
