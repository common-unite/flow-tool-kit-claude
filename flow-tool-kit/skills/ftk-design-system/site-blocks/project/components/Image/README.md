# Image

One photo as the content, with an optional caption below or over it.

**Maps to:** a Form (Design Block) whose `sectionType` is `image` (Image in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `ImageProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Doubles as the image caption when Caption Style puts a caption below or over the photo. |
| `subheading` | Heading: Subheading | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `hoverStyle` | Motion: Hover | ``, `lift`, `tilt`, `trace`, `ring`, `tint` |
| `imageAlt` | Media / Image / Images: Image Alt Text | text |
| `imageCaption` | Image: Caption Style | `below`, `overlay`, `none` |
| `imageStyle` | Media / Image / Images: Image Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined`, `mascot` |

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
| 01 | Clean with lift | A single photo with a caption inside a content page. |
| 02 | Elevated card | A service or offering presented as a picture with a label. |
| 03 | Elevated on crosshatch | An event photo as its own band on a light page. |
| 04 | Glow with tilt | A standout story image on a dark page (a single event recap). |
| 05 | Outlined with ring | A program photo with a call to action, on a mint page. |
| 06 | Deep on spotlight | A feature image in a dark, dramatic section (a retreat, a gala). |

### Image 01: Clean with lift

**Use it when:** A single photo with a caption inside a content page.

**Why it works:** A clean frame and a lift on hover: the image looks clickable without heavy styling.

**Content it needs:** one photo or screenshot; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `imageAlt` | Media: Image Alt Text | `Farmland from the air at the start of the growing season` |
| `imageCaption` | Image: Caption Style | `overlay` (Over the image) |
| `imageStyle` | Media: Image Style | `clean` (Clean) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "background": "#EEF1F4", "brandColor": "#2E844A", "sectionLabel": "Where Your Hours Go", "heading": "Fresh from partner farms", "subheading": "Half of every box comes from growers within sixty miles. The same crew runs October's street tree planting and the spring and fall shoreline cleanups.", "headingAlign": "left", "bodyAlign": "left", "imageCaption": "overlay", "imageStyle": "clean", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "Farmland from the air at the start of the growing season", "hoverStyle": "lift"}
```

### Image 02: Elevated card

**Use it when:** A service or offering presented as a picture with a label.

**Why it works:** An elevated image floats like a card, so a row of these reads as choices.

**Content it needs:** one photo or screenshot; a heading of about 2 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `imageAlt` | Media: Image Alt Text | `Volunteers talking at a distribution table` |
| `imageCaption` | Image: Caption Style | `below` (Below the image) |
| `imageStyle` | Media: Image Style | `elevated` (Elevated) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "brandColor": "#2E844A", "imageCaption": "below", "hoverStyle": "lift", "heading": "Garden workshops", "subheading": "Weekend classes, seed swaps, and a season-long growing course.", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "Volunteers talking at a distribution table", "imageStyle": "elevated"}
```

### Image 03: Elevated on crosshatch

**Use it when:** An event photo as its own band on a light page.

**Why it works:** The crosshatch ground gives the elevated image something to sit on, so it does not float in white space.

**Content it needs:** one photo or screenshot; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `imageAlt` | Media: Image Alt Text | `Volunteers planting saplings` |
| `imageCaption` | Image: Caption Style | `overlay` (Over the image) |
| `imageStyle` | Media: Image Style | `elevated` (Elevated) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "brandColor": "#53B95B", "imageCaption": "overlay", "hoverStyle": "lift", "heading": "Arbor Day planting", "subheading": "Sat, Oct 3 · 40 volunteers needed", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Volunteers planting saplings", "imageStyle": "elevated", "backgroundTexture": "crosshatch", "background": "#EEF1F4"}
```

### Image 04: Glow with tilt

**Use it when:** A standout story image on a dark page (a single event recap).

**Why it works:** imageStyle glow adds a gold halo and hoverStyle tilt gives a playful 3D tilt; badges add the facts.

**Content it needs:** one photo or screenshot; 2 badges; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `hoverStyle` | Motion: Hover | `tilt` (Tilt) |
| `imageAlt` | Media: Image Alt Text | `Volunteers walking the shoreline at sunset` |
| `imageCaption` | Image: Caption Style | `overlay` (Over the image) |
| `imageStyle` | Media: Image Style | `glow` (Brand Glow) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "background": "#032D60", "brandColor": "#F4BE45", "imageCaption": "overlay", "imageStyle": "glow", "hoverStyle": "tilt", "sectionLabel": "Spring cleanup", "heading": "Three miles of shoreline, one morning", "subheading": "Saturday, April 18 · gloves and bags provided", "badges": [{"title": "Family friendly", "style": "accent"}, {"title": "60 spots", "style": "neutral"}], "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Volunteers walking the shoreline at sunset"}
```

### Image 05: Outlined with ring

**Use it when:** A program photo with a call to action, on a mint page.

**Why it works:** An outlined frame and a ring on hover keep it light; the button turns the image into a link.

**Content it needs:** one photo or screenshot; 1 buttons; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#F3FAF4` |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `hoverStyle` | Motion: Hover | `ring` (Glow Ring) |
| `imageAlt` | Media: Image Alt Text | `Sunlight through a bamboo grove` |
| `imageCaption` | Image: Caption Style | `below` (Below the image) |
| `imageStyle` | Media: Image Style | `outlined` (Simple Border) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "background": "#F3FAF4", "brandColor": "#2E844A", "imageCaption": "below", "imageStyle": "outlined", "hoverStyle": "ring", "heading": "Urban canopy program", "subheading": "Every tree we plant is adopted by a neighbor who waters it for two summers.", "buttons": [{"label": "Adopt a tree", "url": "#", "style": "link"}], "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "Sunlight through a bamboo grove"}
```

### Image 06: Deep on spotlight

**Use it when:** A feature image in a dark, dramatic section (a retreat, a gala).

**Why it works:** imageStyle deep with a spotlight gradient gives the strongest depth; the left-aligned text reads like a caption.

**Content it needs:** one photo or screenshot; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `spotlight` (Spotlight) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `imageAlt` | Media: Image Alt Text | `Mountain meadow at sunset` |
| `imageCaption` | Image: Caption Style | `overlay` (Over the image) |
| `imageStyle` | Media: Image Style | `deep` (Deep Drop Shadow) |

JSON (the Configure Properties value):

```json
{"sectionType": "image", "background": "#032D60", "backgroundGradient": "spotlight", "brandColor": "#53B95B", "imageCaption": "overlay", "imageStyle": "deep", "hoverStyle": "lift", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "Retreat", "heading": "Board and staff retreat", "subheading": "Two days in the mountains to plan the next three years.", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "Mountain meadow at sunset"}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Image design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
