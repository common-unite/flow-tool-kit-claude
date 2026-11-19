# Quote

One testimonial or pull quote with its attribution.

**Maps to:** a Form (Design Block) whose `sectionType` is `quote` (Quote in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `QuoteProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `description` | Body: Quote | Rich text. |
| `attribution` | Body: Attribution | Rich text. |
| `attributionDetail` | Body: Attribution Detail | Role or context line, such as "Executive Director, 2025 grantee". |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundEffect` | Images: Photo Motion | `none`, `parallax`, `kenburns` |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.15`, `0.25`, `0.4`, `0.6` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `blockHeight` | Images: Block Height | `auto`, `band`, `standard`, `tall` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `borderColor` | Border: Border Color | color |
| `borderLeft` | Border: Left | text |
| `borderTop` | Border: Top | text |
| `borderWidth` | Border: Border Width (px) | text |
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
| 01 | Left-aligned on a tinted photo | A short testimonial over a photo of the people it is about. |
| 02 | Right-aligned on navy photo | A testimonial placed beside a busy left side of the photo. |
| 03 | Centered, gold on photo | A headline testimonial from a key partner or funder. |
| 04 | Coral rule, left aligned | A quote inside a long text page, where a photo would be too much. |
| 05 | Centered on dots | A short, friendly quote between two sections on a light page. |
| 06 | Tall Ken Burns quote | A closing story or the strongest testimonial on the page. |

### Quote 01: Left-aligned on a tinted photo

**Use it when:** A short testimonial over a photo of the people it is about.

**Why it works:** A brand-tinted parallax photo with a zoom entrance gives the quote presence; left-aligned text keeps it readable over the image.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side). If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.25` (Gentle) |
| `borderTop` | Border: Top | `true` |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `zoom` (Soft Zoom) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "borderTop": true, "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "description": "The LOI took an afternoon and the money paid our people. That should not be rare.", "attribution": "Executive Director, Valley Harvest Pantry", "attributionDetail": "2025 grantee", "entrance": "zoom", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Volunteer_Team_Tables", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25"}
```

### Quote 02: Right-aligned on navy photo

**Use it when:** A testimonial placed beside a busy left side of the photo.

**Why it works:** Right alignment keeps the text off the photo's subject, so the image and quote do not collide.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side). If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.4` (Standard) |
| `blockHeight` | Images: Block Height | `standard` (Standard) |
| `bodyAlign` | Body: Alignment | `right` (Right) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `zoom` (Soft Zoom) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "background": "#032D60", "brandColor": "#53B95B", "description": "The letter of interest took an afternoon, the reporting is one honest conversation a year, and the money paid our people. That should not be rare.", "attribution": "Executive Director, Valley Harvest Pantry", "attributionDetail": "2025 grantee", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Farmland_Aerial", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.4", "blockHeight": "standard", "entrance": "zoom", "bodyAlign": "right"}
```

### Quote 03: Centered, gold on photo

**Use it when:** A headline testimonial from a key partner or funder.

**Why it works:** Gold brand, centered quote and a standard-height photo give it the feel of a pull quote.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side). If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.4` (Standard) |
| `blockHeight` | Images: Block Height | `standard` (Standard) |
| `bodyAlign` | Body: Alignment | `center` (Center) |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `entrance` | Motion: Entrance | `zoom` (Soft Zoom) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "background": "#032D60", "brandColor": "#F4BE45", "description": "They didn't just fix our Salesforce. They made it so our two-person team could actually keep it running.", "attribution": "Executive Director, Community Trust", "attributionDetail": "12 fewer admin hours per week", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.4", "blockHeight": "standard", "entrance": "zoom", "headingAlign": "left", "bodyAlign": "center"}
```

### Quote 04: Coral rule, left aligned

**Use it when:** A quote inside a long text page, where a photo would be too much.

**Why it works:** A thick coral border and a blur entrance mark it as a quote with no image needed.

**Content it needs:** nothing beyond the words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `borderColor` | Border: Border Color | `#F26B4A` |
| `borderLeft` | Border: Left | `true` |
| `borderWidth` | Border: Border Width (px) | `4` |
| `brandColor` | Background: Brand Color | `#F26B4A` |
| `entrance` | Motion: Entrance | `blur` (Blur In) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "background": "#FFFFFF", "brandColor": "#F26B4A", "borderLeft": true, "borderWidth": 4, "borderColor": "#F26B4A", "sectionLabel": "In their words", "bodyAlign": "left", "headingAlign": "left", "description": "We stopped chasing paperwork and started spending Fridays with the families we serve.", "attribution": "Program Director, Eastside Youth Collective", "attributionDetail": "Grantee since 2023", "entrance": "blur"}
```

### Quote 05: Centered on dots

**Use it when:** A short, friendly quote between two sections on a light page.

**Why it works:** A dotted light ground and rise entrance make a gentle break in the page.

**Content it needs:** nothing beyond the words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `dots` (Dots) |
| `bodyAlign` | Body: Alignment | `center` (Center) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "background": "#EEF1F4", "backgroundTexture": "dots", "brandColor": "#2E844A", "description": "I came for one Saturday. Two years later I run the packing line and I still learn something every shift.", "attribution": "Marisol T.", "attributionDetail": "38 shifts since 2024", "entrance": "rise", "bodyAlign": "center"}
```

### Quote 06: Tall Ken Burns quote

**Use it when:** A closing story or the strongest testimonial on the page.

**Why it works:** A tall photo that slowly pans, with the quote placed at the bottom right: the most cinematic quote, for one use per page.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side). If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `kenburns` (Ken Burns) |
| `backgroundOverlay` | Images: Photo Overlay | `bottom` (Bottom Scrim) |
| `blockHeight` | Images: Block Height | `tall` (Tall) |
| `bodyAlign` | Body: Alignment | `right` (Right) |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "quote", "background": "#032D60", "brandColor": "#F4BE45", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "backgroundOverlay": "bottom", "backgroundEffect": "kenburns", "blockHeight": "tall", "bodyAlign": "right", "headingAlign": "left", "description": "The grant was not the biggest we received. It was the only one that trusted us to decide what our community needed.", "attribution": "Executive Director, Riverside Food Network", "attributionDetail": "2024 Community Resilience Fund"}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Quote design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
