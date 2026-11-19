# Gallery

A set of photos as a mosaic, grid, masonry or filmstrip, opening into a full-screen viewer.

**Maps to:** a Form (Design Block) whose `sectionType` is `gallery` (Image Gallery in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `GalleryProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the photos. |

### Photos (`items`)

A list of photos. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `image` | Photo | imageSource |
| `imageAlt` | Caption | text |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `galleryLayout` | Items: Layout | `mosaic`, `grid`, `masonry`, `filmstrip` |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

4 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Mosaic | A season or event recap with many photos (twelve). |
| 02 | Grid | A tidy set of photos of equal importance (nine). |
| 03 | Masonry | Photos of different shapes (portrait and landscape). |
| 04 | Filmstrip | A sequence over time (twelve months). |

### Image Gallery 01: Mosaic

**Use it when:** A season or event recap with many photos (twelve).

**Why it works:** galleryLayout mosaic mixes large and small tiles, so a big set feels curated, not a grid of thumbnails.

**Content it needs:** 12 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `galleryLayout` | Items: Layout | `mosaic` (Mosaic) |

JSON (the Configure Properties value):

```json
{"sectionType": "gallery", "galleryLayout": "mosaic", "sectionLabel": "Gallery", "heading": "A season of Saturdays", "items": [{"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteers filling grocery boxes along a row of tables"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "The morning briefing before a shift"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Planting day on the east ridge"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Shoreline cleanup at sunset"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Build_Day", "imageAlt": "Build day, framing the first wall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Solar_Panel_Install", "imageAlt": "Panels going up on the community hall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "A walk through the bamboo grove"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Green_Leaves_Banner", "imageAlt": "New growth in the nursery"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "First light in the old forest"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "The high meadow at the end of the day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Wind_Turbine_Sky", "imageAlt": "The ridge turbines on a clear day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "The valley farms from above"}]}
```

### Image Gallery 02: Grid

**Use it when:** A tidy set of photos of equal importance (nine).

**Why it works:** galleryLayout grid gives every photo the same size: orderly and fair.

**Content it needs:** 9 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `galleryLayout` | Items: Layout | `grid` (Grid) |

JSON (the Configure Properties value):

```json
{"sectionType": "gallery", "galleryLayout": "grid", "sectionLabel": "On the ground", "heading": "What the work looks like", "items": [{"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Planting day on the east ridge"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Shoreline cleanup at sunset"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Build_Day", "imageAlt": "Build day, framing the first wall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Solar_Panel_Install", "imageAlt": "Panels going up on the community hall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "A walk through the bamboo grove"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Green_Leaves_Banner", "imageAlt": "New growth in the nursery"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "First light in the old forest"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "The high meadow at the end of the day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Wind_Turbine_Sky", "imageAlt": "The ridge turbines on a clear day"}]}
```

### Image Gallery 03: Masonry

**Use it when:** Photos of different shapes (portrait and landscape).

**Why it works:** galleryLayout masonry keeps each photo's own proportions in columns.

**Content it needs:** 12 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `galleryLayout` | Items: Layout | `masonry` (Masonry) |

JSON (the Configure Properties value):

```json
{"sectionType": "gallery", "galleryLayout": "masonry", "sectionLabel": "Field notes", "heading": "Where your hours go", "items": [{"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Build_Day", "imageAlt": "Build day, framing the first wall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Solar_Panel_Install", "imageAlt": "Panels going up on the community hall"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "A walk through the bamboo grove"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Green_Leaves_Banner", "imageAlt": "New growth in the nursery"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "First light in the old forest"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "The high meadow at the end of the day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Wind_Turbine_Sky", "imageAlt": "The ridge turbines on a clear day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "The valley farms from above"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteers filling grocery boxes along a row of tables"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "The morning briefing before a shift"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Planting day on the east ridge"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Shoreline cleanup at sunset"}]}
```

### Image Gallery 04: Filmstrip

**Use it when:** A sequence over time (twelve months).

**Why it works:** galleryLayout filmstrip lays photos in a scrolling strip, so order matters.

**Content it needs:** 10 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `galleryLayout` | Items: Layout | `filmstrip` (Filmstrip) |

JSON (the Configure Properties value):

```json
{"sectionType": "gallery", "galleryLayout": "filmstrip", "sectionLabel": "This year", "heading": "Twelve months, one valley", "items": [{"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "imageAlt": "A walk through the bamboo grove"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Green_Leaves_Banner", "imageAlt": "New growth in the nursery"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Forest_Sunbeams", "imageAlt": "First light in the old forest"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageAlt": "The high meadow at the end of the day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Wind_Turbine_Sky", "imageAlt": "The ridge turbines on a clear day"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Farmland_Aerial", "imageAlt": "The valley farms from above"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Tables", "imageAlt": "Volunteers filling grocery boxes along a row of tables"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "imageAlt": "The morning briefing before a shift"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Planting day on the east ridge"}, {"imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "imageAlt": "Shoreline cleanup at sunset"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Image Gallery design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
