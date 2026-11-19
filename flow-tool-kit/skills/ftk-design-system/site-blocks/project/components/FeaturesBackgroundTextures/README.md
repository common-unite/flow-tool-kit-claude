# Features: Background textures

One feature of the site design blocks shown across several designs: background textures. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

A light or dark section sits between two similar ones and needs separating without a new color.

## The decision it settles

Which `backgroundTexture` (crosshatch, dots, grid, stripes): grid for schedules and maps, dots for friendly copy, crosshatch for statements, stripes for dates.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 1 block, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `cards` | 1 |

5 blocks on the site page are left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundTexture` | `grid` |
| `cardStyle` | `outlined` |
| `columns` | `2` |
| `hoverStyle` | `lift` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
