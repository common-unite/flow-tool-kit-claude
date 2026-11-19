# Callout

A band that asks for one thing: a short heading or statement, a line of copy and a button.

**Maps to:** a Form (Design Block) whose `sectionType` is `callout` (Callout in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `CalloutProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Eyebrow | Rich text. |
| `heading` | Heading: Statement | Rich text. |
| `subheading` | Heading: Supporting Copy | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |
| `description` | Heading: Emphasis Line | Rendered larger, directly under the supporting copy. |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `borderColor` | Border: Border Color | color |
| `borderTop` | Border: Top | text |
| `borderWidth` | Border: Border Width (px) | text |
| `brandColor` | Background: Brand Color | color |
| `buttonAlign` | Buttons: Button Alignment | `left`, `center`, `right` |
| `cardStyle` | Bullets / Card Style: Card Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined` |
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
| 01 | Quiet testimonial note | A one-line testimonial or note between two sections, no heading. |
| 02 | Documents checklist | What to have ready before starting a form. |
| 03 | Diagonal navy statement | A short statement that introduces options below it. |
| 04 | Top bar with items | What a funder does and does not fund. |
| 05 | Deadline alert, gold on navy | A changed deadline or urgent notice with one action. |
| 06 | Side overlay with a button | An invitation (bring your crew) over a photo. |

### Callout 01: Quiet testimonial note

**Use it when:** A one-line testimonial or note between two sections, no heading.

**Why it works:** A light gray panel with centered text and a brand-colored attribution: a gentle break that does not compete with the sections around it.

**Content it needs:** nothing beyond the words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `borderColor` | Border: Border Color | `#F4BE45` |
| `borderTop` | Border: Top | `true` |
| `borderWidth` | Border: Border Width (px) | `4` |
| `brandColor` | Background: Brand Color | `#2E844A` |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "background": "#EEF1F4", "brandColor": "#2E844A", "borderTop": true, "borderWidth": 4, "borderColor": "#F4BE45", "subheading": "\"I signed up alone for one Saturday and ended up coming back every month. The crew makes it easy, and you can see exactly who your work went to.\"", "footnote": "Marisol T. · 38 shifts since 2024"}
```

### Callout 02: Documents checklist

**Use it when:** What to have ready before starting a form.

**Why it works:** Crosshatch ground with a right-aligned button; the heading names the list.

**Content it needs:** 1 buttons; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `right` (Right) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "background": "#EEF1F4", "brandColor": "#53B95B", "heading": "You will need these documents", "description": "IRS determination letter · most recent Form 990 · current operating budget · board list · one letter of community support", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "right", "buttons": [{"label": "Run the eligibility check", "url": "#", "style": "brand"}], "backgroundTexture": "crosshatch"}
```

### Callout 03: Diagonal navy statement

**Use it when:** A short statement that introduces options below it.

**Why it works:** A diagonal gradient with left-aligned text: a bold callout without buttons.

**Content it needs:** a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "What We Do", "heading": "Three ways in.", "subheading": "Plots, classes, and everything we share before anyone pays us.", "backgroundGradient": "diagonal", "background": "#032D60"}
```

### Callout 04: Top bar with items

**Use it when:** What a funder does and does not fund.

**Why it works:** cardStyle topbar on white with three items: a callout that holds a short list.

**Content it needs:** 3 items; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `topbar` (Accent Top Bar) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "background": "#FFFFFF", "brandColor": "#2E844A", "cardStyle": "topbar", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "Before you apply", "heading": "What we fund, and what we don't.", "items": [{"title": "Operating costs", "description": "Salaries, rent and the unglamorous work that keeps doors open."}, {"title": "Capacity", "description": "Systems, training and the tools that let a small team do more."}, {"title": "Not capital campaigns", "description": "Buildings and endowments belong to our Infrastructure fund."}]}
```

### Callout 05: Deadline alert, gold on navy

**Use it when:** A changed deadline or urgent notice with one action.

**Why it works:** Centered heading, gold message and a gold button on navy: the most noticeable callout, for real alerts.

**Content it needs:** 1 buttons; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `borderColor` | Border: Border Color | `#F4BE45` |
| `borderTop` | Border: Top | `true` |
| `borderWidth` | Border: Border Width (px) | `4` |
| `brandColor` | Background: Brand Color | `#F4BE45` |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "background": "#032D60", "brandColor": "#F4BE45", "borderTop": true, "borderWidth": 4, "borderColor": "#F4BE45", "sectionLabel": "Deadline change", "heading": "Applications now close October 15.", "description": "Two extra weeks, because the September storms hit our applicants first.", "buttons": [{"label": "Finish your application", "url": "#", "style": "accent"}]}
```

### Callout 06: Side overlay with a button

**Use it when:** An invitation (bring your crew) over a photo.

**Why it works:** A side overlay keeps the text in a dark band beside the photo, with one button.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 1 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundOverlay` | Images: Photo Overlay | `side` (Side Scrim) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "callout", "background": "#032D60", "brandColor": "#53B95B", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Volunteer_Build_Day", "backgroundOverlay": "side", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "sectionLabel": "Groups welcome", "heading": "Bring your whole crew.", "subheading": "Workplaces, faith groups and teams of 8 to 30 get their own build day, tools and lunch included.", "buttons": [{"label": "Book a group day", "url": "#", "style": "light"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Callout 02, Callout 04, Callout 05 | 1 of 3 | In 1 of 4 the large heading runs to four or more lines and the button crowds the bottom edge. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
