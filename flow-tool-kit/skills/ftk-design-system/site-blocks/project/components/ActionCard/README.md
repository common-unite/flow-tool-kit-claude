# ActionCard

A single call to act: a status or figure, a short line, and the button that acts on it.

**Maps to:** a Form (Design Block) whose `sectionType` is `actionCard` (Action Card in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `ActionCardProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `heading` | Body: Label | The row label beside the big value, such as "Closes in" or "Seats remaining". |
| `deadline` | Body: Deadline (date) | A date the card counts down to. Merge fields work, so {{Close_Date__c}} makes it record-driven. |
| `opensOn` | Body: Opens (date) | Optional cycle start. With both dates the progress bar tracks the open window. |
| `progressCurrent` | Body: Progress Current | Numeric alternative to the dates: the remaining count, such as seats left. |
| `progressTotal` | Body: Progress Total | The total the current value counts against. |
| `footnote` | Footnote: Microcopy | The small line under the buttons, such as "Save and return any time". |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `brandColor` | Background: Brand Color | color |
| `cardStyle` | Bullets / Card Style: Card Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined` |

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
| 01 | Progress meter, plain | A goal or capacity meter beside other content (in a 4 column next to an 8), with two actions. |
| 02 | Spots left, elevated | Limited capacity (spots left this Saturday) that should drive a sign-up. |
| 03 | Opening countdown, glow | Applications or registration not yet open, on a dark page. |
| 04 | Goal progress, top bar | A campaign goal (hours, dollars, volunteers) with progress toward it. |
| 05 | Final week, deep | Last-chance urgency (final week to apply). |
| 06 | Seats, side rule | A gentle limited-seats notice on a mint page. |

### Action Card 01: Progress meter, plain

**Use it when:** A goal or capacity meter beside other content (in a 4 column next to an 8), with two actions.

**Why it works:** The default action card: a label, a count of a total, a bar and two buttons, small enough for a sidebar.

**Content it needs:** 2 buttons; a heading of about 2 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "heading": "Closes in", "brandColor": "#53B95B", "opensOn": "2026-07-15", "deadline": "2026-09-30", "buttons": [{"label": "Start an application", "url": "#", "style": "brand"}, {"label": "Check your eligibility", "url": "#", "style": "outline"}], "footnote": "Save and return any time", "progressCurrent": "50", "progressTotal": "100"}
```

### Action Card 02: Spots left, elevated

**Use it when:** Limited capacity (spots left this Saturday) that should drive a sign-up.

**Why it works:** An elevated card on light gray lifts off the page, so the scarcity message is seen.

**Content it needs:** 1 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `elevated` (Elevated) |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "background": "#EEF1F4", "brandColor": "#2E844A", "cardStyle": "elevated", "heading": "Spots left this Saturday", "progressCurrent": "28", "progressTotal": "40", "buttons": [{"label": "Pick a shift", "url": "#", "style": "brand"}], "footnote": "Shifts fill by Thursday most weeks"}
```

### Action Card 03: Opening countdown, glow

**Use it when:** Applications or registration not yet open, on a dark page.

**Why it works:** cardStyle glow puts a colored halo around the card on navy, so the date reads as an event.

**Content it needs:** 1 buttons; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#0B827C` |
| `cardStyle` | Bullets: Card Style | `glow` (Brand Glow) |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "background": "#032D60", "brandColor": "#0B827C", "cardStyle": "glow", "heading": "Applications open in", "opensOn": "2026-11-01", "deadline": "2026-12-15", "buttons": [{"label": "Remind me", "url": "#", "style": "outline"}], "footnote": "We send one email the day it opens"}
```

### Action Card 04: Goal progress, top bar

**Use it when:** A campaign goal (hours, dollars, volunteers) with progress toward it.

**Why it works:** cardStyle topbar marks the card with a brand bar on white: clean, and clearly a status card.

**Content it needs:** 2 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardStyle` | Bullets: Card Style | `topbar` (Accent Top Bar) |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "background": "#FFFFFF", "brandColor": "#53B95B", "cardStyle": "topbar", "heading": "Summer of Service goal", "progressCurrent": "3180", "progressTotal": "5000", "buttons": [{"label": "Join a shift", "url": "#", "style": "brand"}, {"label": "Donate instead", "url": "#", "style": "link"}], "footnote": "Neighbors served so far"}
```

### Action Card 05: Final week, deep

**Use it when:** Last-chance urgency (final week to apply).

**Why it works:** cardStyle deep on a spotlight gradient with a coral brand is the strongest alarm in the set; use it once.

**Content it needs:** 1 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `spotlight` (Spotlight) |
| `brandColor` | Background: Brand Color | `#F26B4A` |
| `cardStyle` | Bullets: Card Style | `deep` (Deep Drop Shadow) |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "background": "#032D60", "backgroundGradient": "spotlight", "brandColor": "#F26B4A", "cardStyle": "deep", "heading": "Final week to apply", "deadline": "2026-10-15", "buttons": [{"label": "Finish your application", "url": "#", "style": "brand"}], "footnote": "Drafts save automatically"}
```

### Action Card 06: Seats, side rule

**Use it when:** A gentle limited-seats notice on a mint page.

**Why it works:** cardStyle siderule adds a single side line: present but calm, for low-pressure reminders.

**Content it needs:** 1 buttons; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#F3FAF4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `siderule` (Side Rule) |

JSON (the Configure Properties value):

```json
{"sectionType": "actionCard", "background": "#F3FAF4", "brandColor": "#2E844A", "cardStyle": "siderule", "heading": "Info session seats", "progressCurrent": "12", "progressTotal": "30", "buttons": [{"label": "Save a seat", "url": "#", "style": "outline"}], "footnote": "Aug 12 at noon · recorded for anyone who can't attend"}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Action Card design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
