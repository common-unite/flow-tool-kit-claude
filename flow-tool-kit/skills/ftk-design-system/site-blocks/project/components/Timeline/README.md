# Timeline

Dated milestones on a rail, horizontal or vertical, each marked done, current or upcoming.

**Maps to:** a Form (Design Block) whose `sectionType` is `timeline` (Timeline in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `TimelineProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `footnote` | Footnote: Footnote | Rich text. |

### Milestones (`items`)

A list of milestones, up to 8. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Title | richtext |
| `meta` | Detail | richtext |
| `state` | State | `upcoming`, `current`, `done`, `warning` |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `brandColor` | Background: Brand Color | color |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `timelineOrientation` | Items: Orientation | `horizontal`, `vertical` |

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
| 01 | Vertical process | A short process (three stages) that a reader follows top to bottom. |
| 02 | Horizontal, five points | A season, year or cycle of five dates that should fit on one screen. |
| 03 | Vertical, gold on navy | A day-of schedule or a four-hour event in order. |
| 04 | Key dates on stripes | Application or program deadlines that people need to remember. |
| 05 | Vertical on a photo | How something happens behind the scenes (how a box reaches a neighbor). |
| 06 | Status, horizontal on mint | A project or build status where the reader wants to see how far along it is. |

### Timeline 01: Vertical process

**Use it when:** A short process (three stages) that a reader follows top to bottom.

**Why it works:** A vertical timeline with a left-aligned heading on white reads like a numbered list with more shape.

**Content it needs:** 3 items; a heading of about 1 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `timelineOrientation` | Items: Orientation | `vertical` (Vertical) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "vertical", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "headingAlign": "left", "heading": "Process", "items": [{"title": "Letter of interest", "meta": "Five questions, about 3 hours. Saves as you go.", "state": "done"}, {"title": "Full proposal, by invitation", "meta": "Budget detail, references, and a conversation.", "state": "current"}, {"title": "Decision and award", "meta": "Within 60 days of close; first payment in 30."}]}
```

### Timeline 02: Horizontal, five points

**Use it when:** A season, year or cycle of five dates that should fit on one screen.

**Why it works:** Horizontal orientation lays the dates across the page so the whole span is visible at once.

**Content it needs:** 5 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `timelineOrientation` | Items: Orientation | `horizontal` (Horizontal) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "horizontal", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "items": [{"title": "Opens", "meta": "July 15", "state": "done"}, {"title": "Info session", "meta": "Aug 12, 12 pm", "state": "current"}, {"title": "Closes", "meta": "Sept 30, 5 pm", "state": "warning"}, {"title": "Interviews", "meta": "Late Oct"}, {"title": "Decisions", "meta": "By Nov 30"}]}
```

### Timeline 03: Vertical, gold on navy

**Use it when:** A day-of schedule or a four-hour event in order.

**Why it works:** A vertical timeline on navy with gold markers gives the schedule weight on a dark section.

**Content it needs:** 4 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `timelineOrientation` | Items: Orientation | `vertical` (Vertical) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "vertical", "background": "#032D60", "brandColor": "#F4BE45", "headingAlign": "left", "sectionLabel": "Your first Saturday", "heading": "Four hours, start to finish", "items": [{"title": "8:30 · Check in", "meta": "Name tag, apron and a five-minute safety talk.", "state": "done"}, {"title": "8:45 · Meet your crew", "meta": "Every newcomer is paired with a shift lead.", "state": "current"}, {"title": "9:00 · Pack and load", "meta": "Boxes on the line, then out to the pickup lane."}, {"title": "12:00 · Lunch together", "meta": "On us, and the best part of the day."}]}
```

### Timeline 04: Key dates on stripes

**Use it when:** Application or program deadlines that people need to remember.

**Why it works:** A horizontal timeline on a striped light ground stands out from neighboring sections; five dates fit in one line.

**Content it needs:** 5 items; a heading of about 2 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `stripes` (Stripes) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `timelineOrientation` | Items: Orientation | `horizontal` (Horizontal) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "horizontal", "background": "#EEF1F4", "backgroundTexture": "stripes", "brandColor": "#2E844A", "sectionLabel": "2026 cycle", "heading": "Key dates", "items": [{"title": "Letters of interest", "meta": "Feb 1", "state": "done"}, {"title": "Invitations", "meta": "Mar 15", "state": "done"}, {"title": "Proposals due", "meta": "May 1", "state": "current"}, {"title": "Site visits", "meta": "June"}, {"title": "Awards", "meta": "July 30"}]}
```

### Timeline 05: Vertical on a photo

**Use it when:** How something happens behind the scenes (how a box reaches a neighbor).

**Why it works:** The tinted photo grounds the process in real work; the vertical line walks the reader through it.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `timelineOrientation` | Items: Orientation | `vertical` (Vertical) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "vertical", "background": "#032D60", "brandColor": "#53B95B", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Farmland_Aerial", "backgroundOverlay": "tint", "sectionLabel": "From seed to shelf", "heading": "How a box gets to your neighbor", "items": [{"title": "Grown", "meta": "Partner farms within sixty miles.", "state": "done"}, {"title": "Gleaned", "meta": "Volunteers harvest what would go unpicked.", "state": "done"}, {"title": "Packed", "meta": "Saturday crews sort and box.", "state": "current"}, {"title": "Delivered", "meta": "Pickup lane or home delivery for seniors."}]}
```

### Timeline 06: Status, horizontal on mint

**Use it when:** A project or build status where the reader wants to see how far along it is.

**Why it works:** A horizontal line on mint reads as progress; five stages show where things stand.

**Content it needs:** 5 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#F3FAF4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `timelineOrientation` | Items: Orientation | `horizontal` (Horizontal) |

JSON (the Configure Properties value):

```json
{"sectionType": "timeline", "timelineOrientation": "horizontal", "background": "#F3FAF4", "brandColor": "#2E844A", "headingAlign": "left", "sectionLabel": "Project roadmap", "heading": "Where your build stands", "items": [{"title": "Discovery", "meta": "2 weeks", "state": "done"}, {"title": "Build", "meta": "6 weeks", "state": "done"}, {"title": "Testing", "meta": "2 weeks", "state": "warning"}, {"title": "Launch", "meta": "Oct 1"}, {"title": "Support", "meta": "90 days"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Timeline design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
