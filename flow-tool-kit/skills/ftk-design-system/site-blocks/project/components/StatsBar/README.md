# StatsBar

A row of figures, each a value over its label, as a plain row, tiles or a strip, with an optional count-up.

**Maps to:** a Form (Design Block) whose `sectionType` is `statsBar` (Stats in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `StatsBarProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |

### Stats (`items`)

A list of stats, up to 5. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Title | richtext |
| `value` | Value | richtext |
| `titleColor` | Title Color | color |
| `valueColor` | Value Color | color |
| `titleSize` | Title Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `valueSize` | Value Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `iconType` | Icon Source | `icon`, `image` |
| `icon` | Icon | icon |
| `iconColor` | Icon Color | color |
| `iconImage` | Icon Image | asset |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | color |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `blockHeight` | Images: Block Height | `auto`, `band`, `standard`, `tall` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `borderColor` | Border: Border Color | color |
| `borderColorOpacity` | Border: Border Color Opacity | opacity |
| `borderTop` | Border: Top | text |
| `borderWidth` | Border: Border Width (px) | text |
| `brandColor` | Background: Brand Color | color |
| `cardBackgroundColor` | Background: Card Background | color |
| `cardBackgroundOpacity` | Background: Card Background Opacity | opacity |
| `countUp` | Items / Stats: countUp | text |
| `iconStyle` | Items / Card Style: Icon Style | `plain`, `tile`, `circle` |
| `labelSize` | Items: Title Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `statsTreatment` | Items: Stats Treatment | `row`, `tiles`, `spread` |
| `valueSize` | Items: Value Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

8 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Event details strip with icons | Event or shift logistics (date, time, place, crew size) in a thin strip under a hero. |
| 02 | Tiles | A results band of four headline numbers on a dark page. |
| 03 | Tiles on crosshatch | The same headline numbers when the section above or below is plain navy and needs texture. |
| 04 | Light diagonal | A stats band on a light page, between two content sections. |
| 05 | Key dates on a tinted photo | Application or program dates (opens, info session, closes, decisions) as a strip. |
| 06 | Centered row | A simple row of four numbers directly under a hero. |
| 07 | Row band on a photo | A thin strip of numbers between two big sections. |
| 08 | Five selling points with icons | Five short selling points or promises in a strip (launch time, native, security). |

### Stats 01: Event details strip with icons

**Use it when:** Event or shift logistics (date, time, place, crew size) in a thin strip under a hero.

**Why it works:** Spread puts a small icon, label and value side by side, so four practical details read in one glance without a table.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `borderColor` | Border: Border Color | `#FFFFFF` |
| `borderColorOpacity` | Border: Border Color Opacity | `14` |
| `borderTop` | Border: Top | `true` |
| `borderWidth` | Border: Border Width (px) | `1` |
| `countUp` | Items: countUp | `true` |
| `iconStyle` | Items: Icon Style | `tile` (Tile) |
| `labelSize` | Items: Title Size | `x-small` (X-Small) |
| `statsTreatment` | Items: Stats Treatment | `spread` (Inline) |
| `valueSize` | Items: Value Size | `x-small` (X-Small) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "backgroundGradient": "off", "accentColor": "#8EE39A", "borderTop": true, "borderWidth": 1, "borderColor": "#FFFFFF", "borderColorOpacity": 14, "statsTreatment": "spread", "iconStyle": "tile", "bodyAlign": "left", "items": [{"title": "Date", "value": "Saturday, August 15", "iconType": "icon", "icon": "utility:clock"}, {"title": "Time", "value": "8:30 am to 12:30 pm", "iconType": "icon", "icon": "utility:settings"}, {"title": "Location", "value": "Riverside Community Kitchen", "iconType": "icon", "icon": "utility:search"}, {"title": "Crew size", "value": "24 volunteers, 9 spots open", "iconType": "icon", "icon": "utility:user"}], "countUp": true, "labelSize": "x-small", "valueSize": "x-small"}
```

### Stats 02: Tiles

**Use it when:** A results band of four headline numbers on a dark page.

**Why it works:** Each stat sits in its own tile and counts up, so the band reads at a glance and still has motion.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `countUp` | Items: countUp | `true` |
| `statsTreatment` | Items: Stats Treatment | `tiles` (Tiles) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "statsTreatment": "tiles", "items": [{"title": "applications received so far", "value": "214"}, {"title": "already given a first read", "value": "61%"}, {"title": "median days to decision", "value": "43"}, {"title": "of applicants get written feedback", "value": "100%"}], "countUp": true}
```

### Stats 03: Tiles on crosshatch

**Use it when:** The same headline numbers when the section above or below is plain navy and needs texture.

**Why it works:** Crosshatch behind the tiles separates this band from neighbouring dark sections without a color change.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardBackgroundColor` | Background: Card Background | `#FFFFFF` |
| `cardBackgroundOpacity` | Background: Card Background Opacity | `10` |
| `countUp` | Items: countUp | `true` |
| `statsTreatment` | Items: Stats Treatment | `tiles` (Tiles) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "statsTreatment": "tiles", "cardBackgroundColor": "#FFFFFF", "cardBackgroundOpacity": 10, "items": [{"title": "applications received so far", "value": "214"}, {"title": "already given a first read", "value": "61%"}, {"title": "median time to decision, 2025", "value": "43 days"}, {"title": "of applicants get written feedback", "value": "100%"}], "countUp": true, "backgroundTexture": "crosshatch"}
```

### Stats 04: Light diagonal

**Use it when:** A stats band on a light page, between two content sections.

**Why it works:** A light diagonal gradient with counting numbers is soft enough to sit between sections without becoming the focus.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `countUp` | Items: countUp | `true` |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#EEF1F4", "backgroundGradient": "diagonal", "brandColor": "#53B95B", "items": [{"title": "total available", "value": "$1.2M"}, {"title": "award range", "value": "$25–75k"}, {"title": "unrestricted term", "value": "2 yrs"}, {"title": "expected awards", "value": "18–24"}], "countUp": true}
```

### Stats 05: Key dates on a tinted photo

**Use it when:** Application or program dates (opens, info session, closes, decisions) as a strip.

**Why it works:** Count-up is off because these are dates, not achievements; the tinted photo gives a thin strip weight.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 5 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `countUp` | Items: countUp | `false` |
| `statsTreatment` | Items: Stats Treatment | `spread` (Inline) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "backgroundGradient": "off", "accentColor": "#8EE39A", "countUp": false, "statsTreatment": "spread", "bodyAlign": "left", "items": [{"title": "Opens", "value": "July 15, 2026"}, {"title": "Info session", "value": "August 12, 12 pm"}, {"title": "Applications close", "value": "September 30, 5 pm"}, {"title": "Finalist interviews", "value": "Late October"}, {"title": "Decisions", "value": "By November 30"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Forest_Sunbeams", "backgroundOverlay": "tint"}
```

### Stats 06: Centered row

**Use it when:** A simple row of four numbers directly under a hero.

**Why it works:** The plainest treatment: one centered row that counts up, never competing with the hero above it.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `background` | Background: Background | `#032D60` |
| `bodyAlign` | Body: Alignment | `center` (Center) |
| `countUp` | Items: countUp | `true` |
| `statsTreatment` | Items: Stats Treatment | `row` (Row) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "accentColor": "#8EE39A", "statsTreatment": "row", "bodyAlign": "center", "items": [{"title": "awarded in 2025", "value": "$1.1M"}, {"title": "organizations funded", "value": "21"}, {"title": "first-time grantees", "value": "67%"}, {"title": "median award", "value": "$52k"}], "countUp": true}
```

### Stats 07: Row band on a photo

**Use it when:** A thin strip of numbers between two big sections.

**Why it works:** blockHeight band keeps it short; the tinted photo gives it more weight than a plain strip.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `background` | Background: Background | `#032D60` |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `blockHeight` | Images: Block Height | `band` (Band) |
| `countUp` | Items: countUp | `true` |
| `statsTreatment` | Items: Stats Treatment | `row` (Row) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "accentColor": "#8EE39A", "statsTreatment": "row", "countUp": true, "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Farmland_Aerial", "backgroundOverlay": "tint", "blockHeight": "band", "items": [{"value": "120+", "title": "nonprofits served"}, {"value": "90%+", "title": "of clients renew"}, {"value": "170+", "title": "free how-to videos"}, {"value": "10 min", "title": "to your first form"}]}
```

### Stats 08: Five selling points with icons

**Use it when:** Five short selling points or promises in a strip (launch time, native, security).

**Why it works:** The same spread and icons as the event strip, wrapping to two lines, so short statements read like facts.

**Content it needs:** 5 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#8EE39A` |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `borderColor` | Border: Border Color | `#FFFFFF` |
| `borderColorOpacity` | Border: Border Color Opacity | `14` |
| `borderTop` | Border: Top | `true` |
| `borderWidth` | Border: Border Width (px) | `1` |
| `countUp` | Items: countUp | `true` |
| `iconStyle` | Items: Icon Style | `tile` (Tile) |
| `statsTreatment` | Items: Stats Treatment | `spread` (Inline) |

JSON (the Configure Properties value):

```json
{"sectionType": "statsBar", "background": "#032D60", "backgroundGradient": "off", "accentColor": "#8EE39A", "borderTop": true, "borderWidth": 1, "borderColor": "#FFFFFF", "borderColorOpacity": 14, "statsTreatment": "spread", "iconStyle": "tile", "bodyAlign": "left", "items": [{"title": "", "value": "Grab your spoon and your bowl.", "iconType": "icon", "icon": "utility:favorite"}, {"title": "Launch in", "value": "under 10 minutes", "iconType": "icon", "icon": "utility:clock"}, {"title": "100%", "value": "Salesforce Native", "iconType": "icon", "icon": "utility:desktop_and_phone"}, {"title": "Built for", "value": "Security & Scale", "iconType": "icon", "icon": "utility:database"}, {"title": "Built by Nonprofits", "value": "for Nonprofits", "iconType": "icon", "icon": "utility:user"}], "countUp": true}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Stats design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
