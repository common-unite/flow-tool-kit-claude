# Steps

A numbered process: how to apply, what happens next.

**Maps to:** a Form (Design Block) whose `sectionType` is `steps` (Steps in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `StepsProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |
| `footnote` | Footnote: Footnote | Rich text. |

### Steps (`items`)

A list of steps. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Title | richtext |
| `description` | Description | richtext |
| `link` | Link URL | text |
| `target` | Opens In | `same`, `new` |
| `linkLabel` | Link Label | richtext |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `stacked`, `split` |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `entrance` | Motion: Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `headerGap` | Heading: Space Below Heading | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
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
| 01 | Three steps, rise | A short how-it-works with three steps. |
| 02 | Left heading, steps below | Steps that follow a longer intro paragraph. |
| 03 | Four steps, gold on navy, cascade | A getting-started path on a dark section. |
| 04 | Split on crosshatch | Steps that need an intro beside them. |
| 05 | Three steps on a vertical gradient with links | A project process (first call to launch) where each step has its own link. |
| 06 | Four steps, coral | What happens next, four steps after an award or a form. |

### Steps 01: Three steps, rise

**Use it when:** A short how-it-works with three steps.

**Why it works:** The default numbered steps with a rise entrance: simple and clear.

**Content it needs:** 3 items; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `headerGap` | Heading: Space Below Heading | `default` (Default) |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "brandColor": "#2E844A", "entrance": "rise", "sectionLabel": "How it works", "heading": "Three steps from request to live form.", "items": [{"title": "Compose", "description": "Pick your blocks and arrange them. Every block is already wired to your objects."}, {"title": "Configure", "description": "Set the labels, the logic, and where each answer lands."}, {"title": "Publish", "description": "Push it live or share a link. Change it tomorrow without a release."}], "headerGap": "default"}
```

### Steps 02: Left heading, steps below

**Use it when:** Steps that follow a longer intro paragraph.

**Why it works:** The heading and intro sit left at full width and the numbered steps follow below, so the steps read as part of the content flow.

**Content it needs:** 3 items; a heading of about 9 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "brandColor": "#53B95B", "columns": "3", "sectionLabel": "How It Works", "heading": "A two-stage process that saves you the long form.", "subheading": "Most applicants only complete the short first stage. We invite full proposals from a small group, so nobody writes twenty pages on a long shot. Your application saves as you go, and you can return any time before the deadline.", "headingAlign": "left", "bodyAlign": "left", "items": [{"title": "Letter of interest", "description": "Five questions, about three hours. Who you are, who you serve, and what the money does."}, {"title": "Full proposal", "description": "By invitation. Budget detail, references, and a conversation with program staff."}, {"title": "Decision and award", "description": "Decisions within 60 days of close. First payment within 30 days of signing."}]}
```

### Steps 03: Four steps, gold on navy, cascade

**Use it when:** A getting-started path on a dark section.

**Why it works:** Gold numbers on navy and a cascade entrance bring the steps in one by one, in order.

**Content it needs:** 4 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `entrance` | Motion: Entrance | `cascade` (Cascade) |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "background": "#032D60", "brandColor": "#F4BE45", "columns": "4", "entrance": "cascade", "sectionLabel": "Getting started", "heading": "Four steps to your first shift.", "items": [{"title": "Create an account", "description": "Two minutes, and it remembers you next time."}, {"title": "Pick a shift", "description": "Filter by day, place and the kind of work you like."}, {"title": "Watch the welcome video", "description": "Eight minutes on safety and what to expect."}, {"title": "Show up", "description": "Your shift lead will be waiting at check-in."}]}
```

### Steps 04: Split on crosshatch

**Use it when:** Steps that need an intro beside them.

**Why it works:** arrangement split puts the heading and intro on one side and the steps on the other.

**Content it needs:** 3 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "background": "#EEF1F4", "backgroundTexture": "crosshatch", "brandColor": "#2E844A", "arrangement": "split", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "Reporting", "heading": "One honest conversation a year.", "subheading": "No twenty-page report. We ask three questions and listen.", "items": [{"title": "What changed?", "description": "For the people you serve, in your words."}, {"title": "What got in the way?", "description": "So we can fix what we control."}, {"title": "What's next?", "description": "Where you want to be this time next year."}]}
```

### Steps 05: Three steps on a vertical gradient with links

**Use it when:** A project process (first call to launch) where each step has its own link.

**Why it works:** A vertical navy gradient behind three numbered steps, each with a short link, so the reader can act at any step.

**Content it needs:** 3 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `vertical` (Vertical) |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "background": "#032D60", "backgroundGradient": "vertical", "brandColor": "#53B95B", "columns": "3", "sectionLabel": "Working with us", "heading": "From first call to launch.", "items": [{"title": "Scope", "description": "A free call to size the work and agree on done.", "link": "#", "linkLabel": "Book a call"}, {"title": "Build", "description": "Fixed-size requests, delivered in weekly increments.", "link": "#", "linkLabel": "See request sizes"}, {"title": "Hand off", "description": "Documentation and training so your team owns it.", "link": "#", "linkLabel": "View a sample"}]}
```

### Steps 06: Four steps, coral

**Use it when:** What happens next, four steps after an award or a form.

**Why it works:** Coral numbers on white separate this from the rest of a green and navy page.

**Content it needs:** 4 items; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#F26B4A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "steps", "background": "#FFFFFF", "brandColor": "#F26B4A", "columns": "2", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "After you're awarded", "heading": "What happens next.", "items": [{"title": "Sign the agreement", "description": "One page, e-signed, within two weeks."}, {"title": "Receive the first payment", "description": "Within 30 days of signing."}, {"title": "Meet your program officer", "description": "A thirty-minute call to say hello, not to audit."}, {"title": "Share one story", "description": "At year end, in whatever format suits you."}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Steps design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
