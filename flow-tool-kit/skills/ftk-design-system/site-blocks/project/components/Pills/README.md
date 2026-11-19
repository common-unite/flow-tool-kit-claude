# Pills

A tag cloud of short labels, optionally scrolling as a ticker.

**Maps to:** a Form (Design Block) whose `sectionType` is `pills` (Tag Cloud in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `PillsProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Eyebrow | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Supporting Copy | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |

### Pills (`items`)

A list of pills. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `style` | Style | `neutral`, `brand`, `accent`, `outline` |
| `link` | Link | text |
| `target` | Opens In | `same`, `new` |
| `iconImage` | Logo | asset |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | color |
| `arrangement` | Arrangement: Arrangement | `stacked`, `split` |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `entrance` | Motion: Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

6 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Simple tags | A few topics or keywords inside a section. |
| 02 | Split with scrolling tags on crosshatch navy | Many features (eight) beside a headline, when the list is a long run of short terms. |
| 03 | Diagonal, left aligned | Ways people can take part (five). |
| 04 | Spotlight, cascade | Every form or product type, seven tags, as a feature moment. |
| 05 | Split with gold tags | Funding priorities or eligible expenses beside a heading. |
| 06 | Scrolling places strip | Places served or partners (eight or more) as a moving strip under a centered heading. |

### Tag Cloud 01: Simple tags

**Use it when:** A few topics or keywords inside a section.

**Why it works:** Four tags on white: the lightest treatment.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "items": [{"title": "Unrestricted", "style": "neutral"}, {"title": "2-year term", "style": "neutral"}, {"title": "Tri-county region", "style": "neutral"}, {"title": "Budget under $2M", "style": "neutral"}]}
```

### Tag Cloud 02: Split with scrolling tags on crosshatch navy

**Use it when:** Many features (eight) beside a headline, when the list is a long run of short terms.

**Why it works:** arrangement split puts the headline beside the tags, and the tags scroll as a moving strip on a crosshatched dark band.

**Content it needs:** 8 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `background` | Background: Background | `#032D60` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#032D60", "accentColor": "#8EE39A", "arrangement": "split", "pillTicker": true, "heading": "The power of Flow, without the screen-building slog.", "subheading": "Keep all of it in Salesforce Flow. Make the form experience faster and more delightful with Flow Tool Kit.", "headingAlign": "left", "items": [{"title": "Prefill", "style": "outline"}, {"title": "Branching", "style": "outline"}, {"title": "Subflows", "style": "outline"}, {"title": "Invocable Apex", "style": "outline"}, {"title": "Record operations", "style": "outline"}, {"title": "Notifications", "style": "outline"}, {"title": "Post-submission automation", "style": "outline"}, {"title": "Campaigns, Funding Opportunities, Programs", "style": "outline"}], "backgroundTexture": "crosshatch"}
```

### Tag Cloud 03: Diagonal, left aligned

**Use it when:** Ways people can take part (five).

**Why it works:** A diagonal light gradient with a left-aligned intro and tags.

**Content it needs:** 5 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#EEF1F4", "brandColor": "#2E844A", "heading": "This garden runs on its members.", "subheading": "Shared plots only work when everyone pitches in. We need members for the parts only they can do: watering on their day, deciding what to plant, and passing on what they learned.", "headingAlign": "left", "bodyAlign": "left", "items": [{"title": "Watering shifts", "style": "neutral"}, {"title": "Monthly workdays", "style": "neutral"}, {"title": "Turning the compost", "style": "neutral"}, {"title": "Sharing the harvest", "style": "neutral"}, {"title": "Teaching new members", "style": "neutral"}], "backgroundGradient": "diagonal"}
```

### Tag Cloud 04: Spotlight, cascade

**Use it when:** Every form or product type, seven tags, as a feature moment.

**Why it works:** A spotlight gradient with tags cascading in makes a list feel like a showcase.

**Content it needs:** 7 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `spotlight` (Spotlight) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `cascade` (Cascade) |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#032D60", "backgroundGradient": "spotlight", "brandColor": "#53B95B", "sectionLabel": "Built in", "heading": "Every form, one toolkit.", "items": [{"title": "Conditional logic", "style": "brand"}, {"title": "Prefill", "style": "brand"}, {"title": "File uploads", "style": "brand"}, {"title": "Signatures", "style": "brand"}, {"title": "Payments", "style": "brand"}, {"title": "Save and return", "style": "brand"}, {"title": "Review mode", "style": "brand"}], "entrance": "cascade"}
```

### Tag Cloud 05: Split with gold tags

**Use it when:** Funding priorities or eligible expenses beside a heading.

**Why it works:** Split arrangement on white with filled accent tags, so the list reads as a set of highlights.

**Content it needs:** 6 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#F4BE45` |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `background` | Background: Background | `#FFFFFF` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#FFFFFF", "brandColor": "#2E844A", "accentColor": "#F4BE45", "arrangement": "split", "headingAlign": "left", "sectionLabel": "Eligible expenses", "heading": "Spend it where it helps most.", "subheading": "Unrestricted means unrestricted. These are the costs grantees reported most often last year.", "items": [{"title": "Staff salaries", "style": "accent"}, {"title": "Rent and utilities", "style": "accent"}, {"title": "Software", "style": "accent"}, {"title": "Training", "style": "accent"}, {"title": "Equipment", "style": "accent"}, {"title": "Transportation", "style": "accent"}]}
```

### Tag Cloud 06: Scrolling places strip

**Use it when:** Places served or partners (eight or more) as a moving strip under a centered heading.

**Why it works:** Outlined tags scroll in one line on a light ground, so a long list stays one line tall.

**Content it needs:** 8 items; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `grid` (Grid) |
| `brandColor` | Background: Brand Color | `#2E844A` |

JSON (the Configure Properties value):

```json
{"sectionType": "pills", "background": "#EEF1F4", "backgroundTexture": "grid", "brandColor": "#2E844A", "pillTicker": true, "heading": "Neighborhoods we serve", "items": [{"title": "Riverside", "style": "outline"}, {"title": "Ash Street", "style": "outline"}, {"title": "Maple Street", "style": "outline"}, {"title": "Old Mill", "style": "outline"}, {"title": "Harbor View", "style": "outline"}, {"title": "Maple Hill", "style": "outline"}, {"title": "Eastside", "style": "outline"}, {"title": "Cedar Hills", "style": "outline"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Tag Cloud 06 | 1 of 3 | The centered display heading breaks inside a word in 1 of 4 and at phone width ("Neighb / orhood / s"). On a phone page use a shorter heading or another design. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
