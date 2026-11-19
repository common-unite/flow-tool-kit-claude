# Table

A comparison table with typed columns: text, badges, checks and figures.

**Maps to:** a Form (Design Block) whose `sectionType` is `table` (Comparison Table in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `TableProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Eyebrow | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Supporting Copy | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |

### Rows (`items`)

A list of rows. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `featured` | Highlight this row | checkbox |

### Columns (`columns`)

A list of columns, up to 6. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `label` | Header | richtext |
| `width` | Width | `auto`, `narrow`, `wide`, `widest`, `fit` |
| `align` | Alignment | `left`, `center`, `right` |
| `display` | Cell Display | `text`, `richtext`, `badge`, `emphasis` |
| `hideOnTablet` | Hide at tablet width | checkbox |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `brandColor` | Background: Brand Color | color |
| `footnoteAlign` | Footnote: Footnote Alignment | `left`, `center`, `right` |
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
| 01 | Cost table with footnote | Costs or prices by option, with fine print. |
| 02 | Shift chooser | Comparing shifts or sessions (time, place, role). |
| 03 | Funds on navy | Which fund is right for you: three funds compared. |
| 04 | Hours by site on grid | Opening hours or schedules by location. |
| 05 | Plan features on mint | What each plan includes. |
| 06 | Results on corner gradient | Last year's results by program. |

### Comparison Table 01: Cost table with footnote

**Use it when:** Costs or prices by option, with fine print.

**Why it works:** Seven rows on light gray with a left heading and footnote: a real table for real numbers.

**Content it needs:** 7 items; 4 table columns; a heading of about 10 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `footnoteAlign` | Footnote: Footnote Alignment | `left` (Left) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#EEF1F4", "brandColor": "#2E844A", "sectionLabel": "Plot Sizes", "heading": "Know what a plot will cost before you sign up.", "subheading": "The fee for a plot covers the whole season: soil, water, shared tools, compost, and a spot at every workday.", "headingAlign": "left", "footnote": "The upkeep column is a guide to the weekly time a plot usually takes. Fees are set each spring and confirmed before the season starts.", "footnoteAlign": "left", "tableColumns": [{"label": "Size", "width": "auto", "align": "left", "display": "emphasis"}, {"label": "What it usually looks like", "width": "widest", "align": "left", "display": "richtext"}, {"label": "Weekly upkeep", "width": "auto", "align": "left", "display": "text", "hideOnTablet": true}, {"label": "Fee", "width": "narrow", "align": "right", "display": "badge"}], "items": [{"cell1": "Herb box", "cell2": "A waist-high box by the shed for herbs", "cell3": "About 15 min", "cell4": "Included"}, {"cell1": "Extra Small", "cell2": "One planter, such as a herb tub or a berry pot", "cell3": "1 to 2 hours", "cell4": "$10"}, {"cell1": "Small", "cell2": "A single raised bed", "cell3": "2 to 3 hours", "cell4": "$20"}, {"cell1": "Medium", "cell2": "Two beds, or a bed and a trellis", "cell3": "4 to 6 hours", "cell4": "$35"}, {"cell1": "Large", "cell2": "A full plot with several crops", "cell3": "9 to 13 hours", "cell4": "$60"}, {"cell1": "X-Large", "cell2": "Two adjoining plots, or a plot and greenhouse space", "cell3": "18 to 26 hours", "cell4": "$90"}, {"cell1": "Larger than X-Large", "cell2": "Arranged as its own partnership", "cell3": "Varies", "cell4": "Separate", "featured": true}]}
```

### Comparison Table 02: Shift chooser

**Use it when:** Comparing shifts or sessions (time, place, role).

**Why it works:** Four rows on white: the table helps people pick, not just read.

**Content it needs:** 4 items; 4 table columns; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#FFFFFF", "brandColor": "#2E844A", "headingAlign": "left", "sectionLabel": "Volunteer roles", "heading": "Find the shift that fits you.", "tableColumns": [{"label": "Role", "width": "auto", "align": "left", "display": "emphasis"}, {"label": "What you'll do", "width": "widest", "align": "left", "display": "text"}, {"label": "Minimum age", "width": "narrow", "align": "center", "display": "text", "hideOnTablet": true}, {"label": "Open spots", "width": "narrow", "align": "right", "display": "badge"}], "items": [{"cell1": "Greeter", "cell2": "Welcome neighbors and hand out numbers", "cell3": "14", "cell4": "4"}, {"cell1": "Packer", "cell2": "Build boxes on the line", "cell3": "14", "cell4": "12"}, {"cell1": "Loader", "cell2": "Carry boxes to cars, lifting up to 25 lb", "cell3": "16", "cell4": "6"}, {"cell1": "Driver", "cell2": "Deliver to homebound seniors", "cell3": "21", "cell4": "2"}]}
```

### Comparison Table 03: Funds on navy

**Use it when:** Which fund is right for you: three funds compared.

**Why it works:** Gold brand on navy turns a comparison into a feature section.

**Content it needs:** 3 items; 4 table columns; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#032D60", "brandColor": "#F4BE45", "sectionLabel": "Compare the funds", "heading": "Which fund is right for you?", "tableColumns": [{"label": "Fund", "width": "auto", "align": "left", "display": "emphasis"}, {"label": "Award", "width": "auto", "align": "left", "display": "text"}, {"label": "Term", "width": "narrow", "align": "center", "display": "text"}, {"label": "Status", "width": "narrow", "align": "right", "display": "badge"}], "items": [{"cell1": "Community Resilience", "cell2": "$25k to $75k", "cell3": "2 years", "cell4": "Open"}, {"cell1": "Infrastructure", "cell2": "Up to $250k", "cell3": "3 years", "cell4": "Closed"}, {"cell1": "Micro Grants", "cell2": "Up to $5k", "cell3": "1 year", "cell4": "Rolling"}]}
```

### Comparison Table 04: Hours by site on grid

**Use it when:** Opening hours or schedules by location.

**Why it works:** A grid texture echoes a timetable; the footnote holds exceptions.

**Content it needs:** 3 items; 4 table columns; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `grid` (Grid) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `footnoteAlign` | Footnote: Footnote Alignment | `left` (Left) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#EEF1F4", "backgroundTexture": "grid", "brandColor": "#2E844A", "headingAlign": "left", "sectionLabel": "Schedule", "heading": "Distribution hours by site", "tableColumns": [{"label": "Site", "width": "wide", "align": "left", "display": "emphasis"}, {"label": "Day", "width": "auto", "align": "left", "display": "text"}, {"label": "Hours", "width": "auto", "align": "left", "display": "text"}, {"label": "Access", "width": "auto", "align": "right", "display": "badge", "hideOnTablet": true}], "items": [{"cell1": "Riverside Kitchen", "cell2": "Saturday", "cell3": "9 am to 12 pm", "cell4": "Walk-up"}, {"cell1": "Maple Street Library", "cell2": "Tuesday", "cell3": "4 to 7 pm", "cell4": "Drive-through"}, {"cell1": "Harbor View Church", "cell2": "Thursday", "cell3": "10 am to 1 pm", "cell4": "Walk-up"}], "footnote": "Holiday hours are posted two weeks ahead.", "footnoteAlign": "left"}
```

### Comparison Table 05: Plan features on mint

**Use it when:** What each plan includes.

**Why it works:** Four rows on mint with a light brand: a calm feature comparison.

**Content it needs:** 4 items; 4 table columns; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#F3FAF4` |
| `brandColor` | Background: Brand Color | `#53B95B` |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#F3FAF4", "brandColor": "#53B95B", "sectionLabel": "Plans", "heading": "What's included in each plan", "tableColumns": [{"label": "Feature", "width": "widest", "align": "left", "display": "text"}, {"label": "Free", "width": "narrow", "align": "center", "display": "badge"}, {"label": "Standard", "width": "narrow", "align": "center", "display": "badge"}, {"label": "Plus", "width": "narrow", "align": "center", "display": "badge"}], "items": [{"cell1": "Form Submissions per month", "cell2": "25", "cell3": "Unlimited", "cell4": "Unlimited"}, {"cell1": "Conditional logic", "cell2": "Yes", "cell3": "Yes", "cell4": "Yes"}, {"cell1": "Payments", "cell2": "No", "cell3": "Yes", "cell4": "Yes"}, {"cell1": "Priority support", "cell2": "No", "cell3": "No", "cell4": "Yes"}]}
```

### Comparison Table 06: Results on corner gradient

**Use it when:** Last year's results by program.

**Why it works:** A corner gradient on navy with a left heading frames numbers as a report.

**Content it needs:** 3 items; 4 table columns; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `corner` (Corner Glow) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "table", "background": "#032D60", "backgroundGradient": "corner", "brandColor": "#53B95B", "headingAlign": "left", "sectionLabel": "Impact", "heading": "Last year, by program", "tableColumns": [{"label": "Program", "width": "wide", "align": "left", "display": "emphasis"}, {"label": "People served", "width": "auto", "align": "right", "display": "text"}, {"label": "Volunteer hours", "width": "auto", "align": "right", "display": "text", "hideOnTablet": true}, {"label": "Change", "width": "narrow", "align": "right", "display": "badge"}], "items": [{"cell1": "Food distribution", "cell2": "12,400", "cell3": "8,900", "cell4": "+18%"}, {"cell1": "Youth mentoring", "cell2": "310", "cell3": "4,200", "cell4": "+9%"}, {"cell1": "Tree canopy", "cell2": "2,100", "cell3": "1,650", "cell4": "+32%"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Comparison Table 05 | 1 of 3 | The centered display heading breaks inside a word in 1 of 4 ("include / d"). |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
