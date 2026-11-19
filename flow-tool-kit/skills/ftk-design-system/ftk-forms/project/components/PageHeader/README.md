# PageHeader

The header above a form template page's sections. It is drawn by the same `c-header` as a section header.

**Maps to:** `Form_Template_Page__c`:
- `Show_Header__c`, `Header_Style__c` (`classic` default, `classicSpread`, `hero`).
- `Header_Title__c`, `Header_Subtitle__c`, `Header_Icon_Name__c`.
- Hero only: `Header_Kicker__c`, `Header_Lead__c`, `Header_Tags__c`, `Header_Tags_Position__c` (`belowLead` default, `aboveEyebrow`, `aboveKicker`, `aboveTitle`), `Header_Footer__c`.
- `Header_Text__c` with `Header_Text_Variant__c`.
- `Header_Top_Margin__c` and `Header_Bottom_Margin__c`.

A page header offers only classic, classicSpread and hero. Card and Outlined are section-only styles.

Use one only on a page that needs its own title (an information page, a review lead-in). Never a "Page N of M" header: the indicator or the stage list already shows position, and one- and two-page forms need none (C4, 2026-11-17, the form-type rules in the form-design skill's house preferences).

## Icon size
`c-header` sets the size, so a design should not change it: **large (48px)** when the header has a subtitle, **small (24px)** with a title only, and **x-small (16px)** in the hero eyebrow. Use `utility:` icons: they draw in the brand color (or `headingIconColor__c`) as the package does. `standard:` icons carry their own colored tile. The name must be a real SLDS 2.30.7 icon; an unknown name draws nothing.

## Title and subtitle (Classic and Classic Spread)
From `header.html`: the subtitle is `slds-text-body_small` (12px) with a 2px bottom margin; the title is `slds-page-header__title slds-text-heading_medium`, so 20px and bold (700, from `slds-page-header__title`). Both rich texts carry `adjustLineHeight`, a line-height of 1, so the text block is 34px (12 + 2 + 20). The row is bottom-aligned (`vertical-align="end"`), so the 48px icon lines up with the bottom of the title and rises 14px above the subtitle. A Form Style's heading font, weight, size and line height (Advanced) change this.

## Needs a build change
`bannerImage` stands for `Form_Banner_Image__c` / `Form_Banner_Image_URL__c`. The package stores these on the template, page and section, but no component draws them yet. Use it for client review only, and list it under "Needs a build change" in the handoff. It may also suit Experience Cloud blocks.

## Props
- `headerStyle`, `title`, `subtitle`, `icon`, `kicker`, `lead`, `tags`, `tagsPosition`, `footer`, `text`, `textVariant`, `topMargin`, `bottomMargin`, `bannerImage`, colors as on `Section`.
