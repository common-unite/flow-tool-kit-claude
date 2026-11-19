# Facts

Label and value pairs at a glance: a rubric, the terms of a fund, the details of a shift.

**Maps to:** a Form (Design Block) whose `sectionType` is `facts` (Facts in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `FactsProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Supporting Copy | Rich text. |
| `footnote` | Footnote: Footnote | Rich text. |

### Facts (`items`)

A list of facts, up to 10. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `value` | Value | richtext |
| `labelColor` | Label Color | color |
| `valueColor` | Value Color | color |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `brandColor` | Background: Brand Color | color |
| `entrance` | Motion: Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `factsDisplay` | Items: Display | `rows`, `bars`, `stacked`, `segmented` |
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
| 01 | Rubric bars | A scoring rubric or weighted criteria, where the proportions matter. |
| 02 | Stacked in a card | Four short facts inside a page section that already has its own background, or in a side column. |
| 03 | Key facts card on crosshatch | Five quick facts (amounts, term, deadline) as a band of their own on a light page. |
| 04 | Gold rows on navy | An event or shift summary (when, where, what to bring, who to ask). |
| 05 | Spending bars on a photo | Where the money went: budget shares on an impact or donor page. |
| 06 | Stacked on a radial gradient | A short four-line summary that should feel like a feature, not a table. |

### Facts 01: Rubric bars

**Use it when:** A scoring rubric or weighted criteria, where the proportions matter.

**Why it works:** factsDisplay bars draws each value as a bar, so readers see the weighting at a glance instead of comparing percentages.

**Content it needs:** 4 items; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `factsDisplay` | Items: Display | `bars` (Progress) |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "factsDisplay": "bars", "sectionLabel": "How we score", "heading": "The actual rubric", "items": [{"title": "Community accountability", "value": "30%"}, {"title": "Depth of need in service area", "value": "25%"}, {"title": "Track record with the community", "value": "25%"}, {"title": "Plan feasibility", "value": "20%"}], "footnote": "Grant-writing polish is deliberately not a criterion."}
```

### Facts 02: Stacked in a card

**Use it when:** Four short facts inside a page section that already has its own background, or in a side column.

**Why it works:** Stacked label over value in one bordered card with a footnote: the lightest facts treatment.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `factsDisplay` | Items: Display | `stacked` (Stacked) |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "brandColor": "#53B95B", "factsDisplay": "stacked", "items": [{"title": "Pool", "value": "$1.2 million"}, {"title": "Awards", "value": "$25k – $75k"}, {"title": "Term", "value": "Two years, unrestricted"}, {"title": "Closes", "value": "Sept 30"}], "footnote": "No. 04 in a series of five funds · 2026"}
```

### Facts 03: Key facts card on crosshatch

**Use it when:** Five quick facts (amounts, term, deadline) as a band of their own on a light page.

**Why it works:** Label and value rows in a white card on a light crosshatch ground: tidy and scannable, with texture to mark the band.

**Content it needs:** 5 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "sectionLabel": "Key facts", "brandColor": "#53B95B", "items": [{"title": "Total available", "value": "$1,200,000"}, {"title": "Award range", "value": "$25k – $75k"}, {"title": "Term", "value": "2 years"}, {"title": "Expected awards", "value": "18 – 24"}, {"title": "Deadline", "value": "Sept 30, 5 pm"}], "backgroundTexture": "crosshatch", "background": "#EEF1F4"}
```

### Facts 04: Gold rows on navy

**Use it when:** An event or shift summary (when, where, what to bring, who to ask).

**Why it works:** factsDisplay rows lists label and value in lines like a ticket; the gold brand on navy keeps it warm.

**Content it needs:** 4 items; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `factsDisplay` | Items: Display | `rows` (Rows) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "background": "#032D60", "brandColor": "#F4BE45", "factsDisplay": "rows", "headingAlign": "left", "sectionLabel": "At a glance", "heading": "Saturday food distribution", "items": [{"title": "Where", "value": "Riverside Community Kitchen"}, {"title": "When", "value": "Saturdays, 8:30 to 12:30"}, {"title": "Who", "value": "Ages 14 and up"}, {"title": "Cost", "value": "Free, lunch included"}], "entrance": "rise"}
```

### Facts 05: Spending bars on a photo

**Use it when:** Where the money went: budget shares on an impact or donor page.

**Why it works:** Bars show the split visually and the tinted photo reminds the reader what the money did.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `factsDisplay` | Items: Display | `bars` (Progress) |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "background": "#032D60", "brandColor": "#53B95B", "factsDisplay": "bars", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Forest_Sunbeams", "backgroundOverlay": "tint", "sectionLabel": "Last year's budget", "heading": "Where every dollar went", "items": [{"title": "Programs and direct services", "value": "72%"}, {"title": "Volunteer training", "value": "12%"}, {"title": "Operations", "value": "10%"}, {"title": "Fundraising", "value": "6%"}], "footnote": "Audited figures, fiscal year 2025."}
```

### Facts 06: Stacked on a radial gradient

**Use it when:** A short four-line summary that should feel like a feature, not a table.

**Why it works:** Stacked facts on a radial gradient with a cascade entrance turn four lines into a small moment.

**Content it needs:** 4 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `radial` (Radial) |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `entrance` | Motion: Entrance | `cascade` (Cascade) |
| `factsDisplay` | Items: Display | `stacked` (Stacked) |

JSON (the Configure Properties value):

```json
{"sectionType": "facts", "background": "#032D60", "backgroundGradient": "radial", "brandColor": "#F4BE45", "factsDisplay": "stacked", "sectionLabel": "Before you come", "heading": "Your shift, in four lines", "items": [{"title": "Arrive", "value": "8:30 am"}, {"title": "Wear", "value": "Closed-toe shoes"}, {"title": "Bring", "value": "A water bottle"}, {"title": "Park", "value": "North lot, free"}], "entrance": "cascade"}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Facts 04 | 1 of 3 | In 1 of 4 the label and value rows stack and long values wrap. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
