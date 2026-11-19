# Pricing

Plans or tiers side by side, each with a price, its inclusions and a button, one optionally featured.

**Maps to:** a Form (Design Block) whose `sectionType` is `pricing` (Pricing in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `PricingProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |

### Pricing Tiers (`items`)

A list of tiers, up to 6. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Title | richtext |
| `value` | Price | richtext |
| `description` | Description | richtext |
| `link` | Link URL | text |
| `target` | Opens In | `same`, `new` |
| `linkLabel` | Link Label | richtext |
| `features` | Features (one per line) | textarea |
| `featured` | Featured / highlighted tier | checkbox |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `brandColor` | Background: Brand Color | color |
| `entrance` | Motion: Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `hoverStyle` | Motion: Hover | ``, `lift`, `tilt`, `trace`, `ring`, `tint` |

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
| 01 | Three tiers, lift | Service or membership tiers that people compare. |
| 02 | Membership on navy, gold | Donor or membership levels on a dark section. |
| 03 | Four sponsor levels on dots | Event sponsorship levels (four). |
| 04 | Two options, white | A simple choice between two plans. |
| 05 | Event tickets on mint | Ticket types for a dinner or event. |
| 06 | Grant sizes on diagonal navy | Grant amounts or award sizes. |

### Pricing 01: Three tiers, lift

**Use it when:** Service or membership tiers that people compare.

**Why it works:** Three columns with a lift on hover on a light ground: the standard tier layout.

**Content it needs:** 3 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#EEF1F4", "brandColor": "#2E844A", "sectionLabel": "Garden Memberships", "heading": "Pick the plot size that fits your season.", "subheading": "Every membership works the same way: a reserved plot, shared tools and water, and a seat at the monthly workday. Only the plot size changes.", "footnote": "Plot sizes and prices are placeholders for this sample. Every membership includes the tool shed, the seed swap, and the monthly newsletter.", "columns": "3", "items": [{"title": "Steady", "value": "$20 / month", "description": "One raised bed for herbs and greens. A good first season, with a mentor gardener a row away.", "features": "Billed monthly, cancel anytime\nFits: first-time growers, small households, a balcony gardener", "link": "#", "linkLabel": "Start with Steady"}, {"title": "Momentum", "value": "$40 / month", "featured": true, "description": "A full-size plot with room for tomatoes, squash and beans. Most members grow here by their second season.", "features": "Billed monthly, cancel anytime\nFits: families, returning members, anyone who cans in August", "link": "#", "linkLabel": "Start with Momentum"}, {"title": "Scale", "value": "$80 / month", "description": "Two adjoining plots and greenhouse space. Room to grow for a food pantry, a classroom or a faith group.", "features": "Billed monthly, cancel anytime\nFits: schools and partners growing food for donation", "link": "#", "linkLabel": "Talk through Scale"}], "hoverStyle": "lift"}
```

### Pricing 02: Membership on navy, gold

**Use it when:** Donor or membership levels on a dark section.

**Why it works:** Gold brand on navy makes levels feel premium, suited to donor recognition.

**Content it needs:** 3 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#032D60", "brandColor": "#F4BE45", "columns": "3", "sectionLabel": "Membership", "heading": "Join the people who keep the doors open.", "items": [{"title": "Friend", "value": "$50 / year", "description": "Our newsletter and first word on events.", "features": "Quarterly newsletter\nMember events", "link": "#", "linkLabel": "Become a Friend"}, {"title": "Supporter", "value": "$250 / year", "featured": true, "description": "Feeds a family of four for a month.", "features": "Everything in Friend\nAnnual impact report\nVolunteer priority", "link": "#", "linkLabel": "Become a Supporter"}, {"title": "Champion", "value": "$1,000 / year", "description": "Funds a full Saturday distribution.", "features": "Everything in Supporter\nSite visit with our director", "link": "#", "linkLabel": "Become a Champion"}]}
```

### Pricing 03: Four sponsor levels on dots

**Use it when:** Event sponsorship levels (four).

**Why it works:** Four columns on a dotted light ground fit four levels without crowding.

**Content it needs:** 4 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `dots` (Dots) |
| `brandColor` | Background: Brand Color | `#2E844A` |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#EEF1F4", "backgroundTexture": "dots", "brandColor": "#2E844A", "columns": "4", "sectionLabel": "Sponsorship", "heading": "Put your name behind the gala.", "items": [{"title": "Table", "value": "$2,500", "features": "Table for eight\nProgram listing", "link": "#", "linkLabel": "Sponsor a table"}, {"title": "Silver", "value": "$5,000", "features": "Two tables\nLogo on signage", "link": "#", "linkLabel": "Go Silver"}, {"title": "Gold", "value": "$10,000", "featured": true, "features": "Three tables\nStage mention\nLogo on every screen", "link": "#", "linkLabel": "Go Gold"}, {"title": "Presenting", "value": "$25,000", "features": "Naming rights\nRemarks at dinner", "link": "#", "linkLabel": "Talk to us"}]}
```

### Pricing 04: Two options, white

**Use it when:** A simple choice between two plans.

**Why it works:** Two columns on white with a left heading: no more structure than two options need.

**Content it needs:** 2 items; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#FFFFFF", "brandColor": "#53B95B", "columns": "2", "headingAlign": "left", "sectionLabel": "Class passes", "heading": "Learn at your own pace, no membership.", "items": [{"title": "Starter pass", "value": "4 classes", "description": "For trying a few workshops before you join.", "features": "Use within 6 months\nAny weekend workshop", "link": "#", "linkLabel": "Buy 4 classes"}, {"title": "Season pass", "value": "12 classes", "featured": true, "description": "Enough for a whole growing season, seed to harvest.", "features": "Use within 12 months\nTools included\nAny weekend workshop", "link": "#", "linkLabel": "Buy 12 classes"}]}
```

### Pricing 05: Event tickets on mint

**Use it when:** Ticket types for a dinner or event.

**Why it works:** Three columns on mint with a rise entrance feel festive but stay clear.

**Content it needs:** 3 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#F3FAF4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#F3FAF4", "brandColor": "#2E844A", "columns": "3", "entrance": "rise", "sectionLabel": "Tickets", "heading": "Harvest Dinner, October 24", "items": [{"title": "Community", "value": "$35", "description": "Pay what you can, starting here.", "link": "#", "linkLabel": "Get a ticket"}, {"title": "Standard", "value": "$75", "featured": true, "description": "Dinner and the farm tour.", "link": "#", "linkLabel": "Get a ticket"}, {"title": "Host", "value": "$150", "description": "Covers a Community seat for someone else.", "link": "#", "linkLabel": "Host a seat"}]}
```

### Pricing 06: Grant sizes on diagonal navy

**Use it when:** Grant amounts or award sizes.

**Why it works:** Three columns on a diagonal gradient present amounts like tiers, so applicants pick the right size.

**Content it needs:** 3 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "pricing", "background": "#032D60", "backgroundGradient": "diagonal", "brandColor": "#53B95B", "columns": "3", "sectionLabel": "Grant tiers", "heading": "Three sizes, one simple application.", "items": [{"title": "Micro", "value": "Up to $5,000", "description": "Decision in 3 weeks.", "features": "One-page application\nNo report"}, {"title": "Program", "value": "$25k to $75k", "featured": true, "description": "Two years, unrestricted.", "features": "Letter of interest first\nOne conversation a year"}, {"title": "Capacity", "value": "Up to $150k", "description": "Systems, staff and training.", "features": "By invitation\nPeer cohort included"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| All | 1 of 3 | Never in a 1 of 4 column: the tiers stack, prices wrap ("$20 / / month") and the heading breaks inside words. Prefer full width or 1 of 2; in 1 of 3 tiers stack one under another. |
| Pricing 06 | 1 of 3 | Also breaks "application." at phone width; shorten the heading for phone-heavy pages. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
