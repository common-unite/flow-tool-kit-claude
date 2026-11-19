# Section

A form section: a titled group of related questions (an organization's details, a contact, an address, a budget), its frame, its header in any of FlowToolKit's five header styles, and the 12-column grid its fields sit on.

A page is made of sections, and a section almost always holds several fields: full-width rows for long answers, half rows for pairs like EIN and year founded, 5/7 for first and last name. Every example on this card and the Section layout card is a real section with at least five fields, so you can see where one section ends and the next begins.

**Maps to:** a `Form_Component_Section__c` and its theme. Hand-written from `formSectionTheme`, `sectionFrame`, `sectionFrameOptions` and `header`.

## Frame (`frame`, stored as `sectionTheme__c`)
| `frame` | Builder label | Renders |
| --- | --- | --- |
| `clean` | None (default) | No border. The header's own 2px rule separates it from the fields |
| `box` | Box | 1px `frame-border` edge, `radius-frame` corners |
| `shadow` | Shadow | The Box plus `frame-shadow` |

## Header style (`headerStyle`)
| `headerStyle` | Builder label | Frames | Renders |
| --- | --- | --- | --- |
| `classic` | Classic (default) | any | Subtitle (12px) 2px above a 20px bold title, both on a line-height of 1 (`header` adjustLineHeight); a 48px icon with a subtitle, 24px without, bottom-aligned with the title; icon in the gutter on the section's edge, 2px `brand` rule. On a Box or Shadow frame the header sits above the box and the box's top border is the rule |
| `classicSpread` | Classic Spread | any | Classic with the icon at the far right |
| `outlined` | Title on Border | Box, Shadow | The title sits in the border line (a fieldset legend); the subtitle goes under it; an icon rides the border at the right |
| `hero` | Stacked | any | A display header: eyebrow (icon plus subtitle), kicker, large title, lead, tags and footer. No rule |

Use Classic, Classic Spread or Title on Border for sections; with a Box or Shadow frame, prefer Title on Border. `outlined` needs a frame; without one the section falls back to `classic`, as the Form Builder does. The package also has a Card header (a band inside the frame), but it's rare, so this design system doesn't draw or recommend it.

## Props
- `title`, `subtitle`, `icon` (an SLDS icon name; use `utility:` icons such as `utility:company` or `utility:location`, which fill the icon box as the package draws them; `standard:` icons carry tile padding and draw small), `helpText`.
- `headerDisplay`: `Header` (default) or `Divider` (`Header_Display__c`). With `Divider` the title and subtitle draw as a `Divider` in `dividerStyle` (`Divider_Style__c`, any of its 12 values); `outlined` then falls back to `classic`, and `ruleSize` sets the divider rule thickness.
- `frame`, `headerStyle`: see the tables. `showHeader={false}` drops the header.
- Stacked only: `kicker` (`Header_Kicker__c`), `lead` (`Header_Lead__c`), `footer` (`Header_Footer__c`), `tags` (`Header_Tags__c`, strings), `tagsPosition` (`Header_Tags_Position__c`: `belowLead` default, `aboveEyebrow`, `aboveKicker`, `aboveTitle`). These are the stored names; `pretitle`, `body`, `abovePretitle` and `belowBody` are gone.
- `headerBottomMargin` (`Header_Bottom_Margin__c`, an `slds-m-bottom_*` class).
- Width: `large`, `medium`, `small` (the section's `widthLarge__c` / `widthMedium__c` / `widthSmall__c`, 1 to 12). Sections only sit side by side inside a `SectionGrid`, which stands for the form body.
- Spacing: `marginTop`, `marginBottom` (`slds-m-*` classes), `paddingTop`, `paddingBottom`, `paddingLeft`, `paddingRight`, `horizontalPadding` (`slds-p-*` classes). The package default for each is none.
- `horizontalAlign` (`horizontalAlign__c`: `start`, `center`, `space`, `spread`, `end`): how fields that do not fill a row line up. Rarely used; leave it at the default `start`, so it has no example on the cards.
- `richText` (`richText__c`): the section's rich text above the fields.
- Flow Action ("Add Flow Action" under the section's rich text in Form Builder; not on prompt-style or Flow screen sections). It's a brand button (`customFlowDynamicDisplay`) that opens a screen flow in a modal, for something the person does in a separate step: check eligibility, look up their organization, upload documents to another record.
  - `flowButtonLabel` (`flowButtonLabel__c`, Button Label, default "Run Flow"; takes merge fields).
  - `flowButtonStyle` (`flowButtonStyle__c`, "Flow Action Button (Custom Style)") is CSS, not a button variant. It places the button over the rich text and defaults to `z-index:3; right:0; bottom:20%`. With no rich text, the button sits right-aligned above the fields. Because it floats over the rich text, keep the lines beside it short, or the text runs under the button.
  - Write the flow (`flowApiName__c`, Select Flow), `modalSize__c` (default large) and `flowRecordId__c` in the handoff.
- `hideAccordionBorder` (`hideAccordionBorder__c`).
- Conditional sections: write the rule (`conditionalLogic__c`) in the handoff. The package draws nothing for it.
- `Do_Not_Print__c` (page and page section) has no visual; list it in the handoff.
- Theme values (the Form Theme's heading group): `headerBackground` (hex, `headingBackgroundColor__c`), `headerGradient` (`headingBackgroundGradient__c`: a 135deg gradient from the background darkened to 25% to the background, with white title, subtitle and icon), `titleColor`, `subtitleColor`, `iconColor`, `borderColor` (frame edge and header rule), `borderSize` (`borderSize__c`, px: the Box or Shadow frame edge width and the rule beside a Title on Border title; default 1px from the Form Style's Border thickness), `sectionBackground`.
- Accordion: `accordion` (`sectionType__c` = `accordionSection`), drawn the way `formSectionTheme` draws `lightning-accordion-section`: a square summary row (.75rem padding all round, 16px heading on a 1.25 line, so a 44px row, chevron right when closed and `utility:switch` when open), `#f3f2f2` behind `#080707` text unless the theme sets `accordionBackground` / `accordionFontColor`, and a 2px `#bbbbbb` rule under the section (`hideAccordionBorder` removes it). `open` is `accordionOpen__c` (Open on load): sections start closed unless it is set. They also all open when the form fails validation. Show a mix in a design: the first section open, the rest closed. Why .75rem: `formSectionTheme` sets the older `--slds-c-accordion-section-spacing-block-*` hooks to 2px, which only take effect under synthetic shadow (a 24px row in Lightning Experience). On native shadow pages, such as LWR Experience Cloud sites, `lightning-accordion-section` reads `--slds-c-accordionsection-spacing-*` instead, so the package's 2px never applies and SLDS's .75rem does. The card draws the .75rem row. Package follow-up: set both hook names so the two runtimes match.
- `children`: the section's fields, each wrapped in a `Column`.

## House default for form conversions
Start every framed section from this, then change it only when the client asks:
- `frame: 'box'` (no shadow) with `headerStyle: 'outlined'` (Title on Border) and a `utility:` icon at 48px.
- `borderSize: 2`, `borderColor` = the brand color, `titleColor` = the brand color, `iconColor` = the client's alternate (accent) color.
- The subtitle wraps before the icon (above).
- A choice among related records (a primary contact from the household) is a Flow section built from the packaged (Form) Flow Section | Template, drawn with selectable `RecordCard`s; never a picklist of records.

## Notes
- The header title, subtitle and fields share one left edge: `section-inset` (0.8rem), or 1.25rem (20px) inside a Box or Shadow frame, Outlined or Classic, with 24px of room under the last field. The Form Style's Horizontal padding changes the unframed inset only; frames stay at 20px. Package gap: the package currently lets Horizontal padding override the frame inset too. Outlined title: 1.25rem with a subtitle, 1.5rem without; subtitle 0.8125rem in `placeholder`. Keep it.
- Outlined with an icon: the 48px icon rides the border at the right and hangs 24px below it, so the subtitle stops 60px short of the right inset (the icon plus a 12px gap) and wraps before it, never running under the icon. Package gap: the package subtitle still runs the full width under the icon; fix pending.
- The header icon hides below 480px of container width.
- With no theme the rule and icon take the brand; the frame edge never does.
- A divider section (`sectionType__c` = `dividerSection`) is a `Divider` on its own between sections.
- Not drawn: heading background images and the visual-picker section theme.
