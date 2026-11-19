# Carousel

Full-width slides, each a photo with its own heading, copy and buttons, advancing on a timer or by hand.

**Maps to:** a Form (Design Block) whose `sectionType` is `carousel` (Carousel in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `CarouselProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |

### Slides (`items`)

A list of slides. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `iconImage` | Slide Image | asset |
| `imageAlt` | Alt Text | text |
| `eyebrow` | Eyebrow | richtext |
| `title` | Headline | richtext |
| `link` | Link | text |
| `target` | Opens In | `same`, `new` |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `carouselInterval` | Items: Auto-advance | `0`, `4`, `5`, `8` |
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
| 01 | Left-aligned, light | A story told in three photos and captions (a day in the life). |
| 02 | Centered, no heading | Three slides that speak for themselves, inside a section that already has a heading. |
| 03 | Navy with gold | People profiles (the people behind the work) on a dark section. |
| 04 | Places on dots | A set of locations or sites, four slides. |
| 05 | Coral results | Where grants went: outcomes, one per slide. |
| 06 | Radial navy | Ways to get involved, four options as slides. |

### Carousel 01: Left-aligned, light

**Use it when:** A story told in three photos and captions (a day in the life).

**Why it works:** The heading and body sit left above the slides, so it reads as an article that happens to swipe.

**Content it needs:** 3 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `carouselInterval` | Items: Auto-advance | `5` (5 seconds) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "brandColor": "#2E844A", "sectionLabel": "From Past Shifts", "heading": "What a Saturday actually looks like.", "subheading": "Photos from the last three distributions. Nothing staged, and nobody had done this before their first shift either.", "headingAlign": "left", "bodyAlign": "left", "carouselInterval": "5", "items": [{"iconImage": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteers filling grocery boxes along a row of tables", "eyebrow": "The packing line", "title": "Four hundred boxes, one table at a time"}, {"iconImage": "FlowToolKit__Background_Volunteer_Build_Day", "imageAlt": "A volunteer crew working together outdoors on a build project", "eyebrow": "Load out", "title": "Boxes reach the pickup lane in under a minute"}, {"iconImage": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "Two volunteers talking with a shift lead before the shift starts", "eyebrow": "Orientation", "title": "Fifteen minutes, then you are on the line"}]}
```

### Carousel 02: Centered, no heading

**Use it when:** Three slides that speak for themselves, inside a section that already has a heading.

**Why it works:** The carousel alone: no heading, no background, so it nests under any section header.

**Content it needs:** 3 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `carouselInterval` | Items: Auto-advance | `5` (5 seconds) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "brandColor": "#53B95B", "carouselInterval": "5", "items": [{"iconImage": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteer team sorting donation boxes", "eyebrow": "Programs", "title": "Pathways: sixteen weeks to a first offer", "link": "#"}, {"iconImage": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "Sunlight through the forest canopy", "eyebrow": "Volunteer", "title": "Summer of Service: 5,000 neighbors by September", "link": "#"}, {"iconImage": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "Sunrise over the valley", "eyebrow": "Funding", "title": "Community Resilience Fund: applications open", "link": "#"}]}
```

### Carousel 03: Navy with gold

**Use it when:** People profiles (the people behind the work) on a dark section.

**Why it works:** Gold brand on navy makes the slide controls and captions warm against the dark ground.

**Content it needs:** 3 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `carouselInterval` | Items: Auto-advance | `8` (8 seconds) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "background": "#032D60", "brandColor": "#F4BE45", "carouselInterval": "8", "headingAlign": "left", "bodyAlign": "left", "sectionLabel": "Meet the crews", "heading": "The people behind every Saturday.", "items": [{"iconImage": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "Volunteers talking at a distribution table", "eyebrow": "Greeters", "title": "First faces, warmest welcome"}, {"iconImage": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteers packing boxes along tables", "eyebrow": "Packers", "title": "Four hundred boxes by noon"}, {"iconImage": "FlowToolKit__Background_Volunteer_Build_Day", "imageAlt": "A crew working together outdoors", "eyebrow": "Builders", "title": "Shelves, ramps and garden beds"}]}
```

### Carousel 04: Places on dots

**Use it when:** A set of locations or sites, four slides.

**Why it works:** A dotted light ground keeps a list of places from feeling like a gallery of the same photo.

**Content it needs:** 4 items; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `dots` (Dots) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `carouselInterval` | Items: Auto-advance | `0` (Off) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "background": "#EEF1F4", "backgroundTexture": "dots", "brandColor": "#2E844A", "carouselInterval": "0", "heading": "Places we work", "items": [{"iconImage": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Shoreline at sunset", "eyebrow": "Harbor", "title": "Shoreline cleanups, spring and fall"}, {"iconImage": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Volunteers planting saplings", "eyebrow": "City streets", "title": "Two hundred trees a year"}, {"iconImage": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "Farmland from the air", "eyebrow": "Partner farms", "title": "Gleaning days every harvest"}, {"iconImage": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "Sunlight through the forest", "eyebrow": "Trails", "title": "Trail crews on the second Sunday"}]}
```

### Carousel 05: Coral results

**Use it when:** Where grants went: outcomes, one per slide.

**Why it works:** A coral brand on white separates the results story from the rest of a green and navy site.

**Content it needs:** 3 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `brandColor` | Background: Brand Color | `#F26B4A` |
| `carouselInterval` | Items: Auto-advance | `5` (5 seconds) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "background": "#FFFFFF", "brandColor": "#F26B4A", "carouselInterval": "5", "sectionLabel": "Stories", "heading": "Where the grants went", "items": [{"iconImage": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "A bamboo grove", "eyebrow": "Environment", "title": "A school garden that feeds forty families", "link": "#"}, {"iconImage": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "People in conversation", "eyebrow": "Youth", "title": "Mentors who show up every week", "link": "#"}, {"iconImage": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "A mountain meadow", "eyebrow": "Rural health", "title": "A clinic van that reaches the valley", "link": "#"}]}
```

### Carousel 06: Radial navy

**Use it when:** Ways to get involved, four options as slides.

**Why it works:** A radial gradient focuses the center slide, making the carousel itself the feature of the section.

**Content it needs:** 4 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `radial` (Radial) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `carouselInterval` | Items: Auto-advance | `4` (4 seconds) |

JSON (the Configure Properties value):

```json
{"sectionType": "carousel", "background": "#032D60", "backgroundGradient": "radial", "brandColor": "#53B95B", "carouselInterval": "4", "sectionLabel": "Seasons of service", "heading": "There is always something to do.", "items": [{"iconImage": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "Fresh spring growth", "eyebrow": "Spring", "title": "Planting and trail repair"}, {"iconImage": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "Summer fields", "eyebrow": "Summer", "title": "Harvest gleaning and camps"}, {"iconImage": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Autumn tree planting", "eyebrow": "Fall", "title": "Street trees and food drives"}, {"iconImage": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Winter distribution", "eyebrow": "Winter", "title": "Holiday boxes and warm coats"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Carousel 06 | 1 of 3 | The centered display heading breaks inside words in 1 of 4 and at phone width ("somethin / g"). On a phone page use a shorter heading or another design. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
