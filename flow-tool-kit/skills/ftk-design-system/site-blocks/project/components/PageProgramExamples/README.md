# Page example: Program pages

A whole demo page, section by section with its column widths: program pages. Use it as the starting shape for a page of that kind.

## Use it when

A program or service needs its own page.

## The decision it settles

Program page shape: hero variants for different programs, attached stats, facts for logistics.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 11 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `hero` | 6 |
| `cards` | 2 |
| `facts` | 2 |
| `statsBar` | 1 |

1 block on the site page is left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `attachToPrevious` | `true` |
| `backgroundEffect` | `parallax` |
| `backgroundGradient` | `off` |
| `backgroundOverlay` | `tint` |
| `badgePosition` | `top` |
| `bodyAlign` | `left` |
| `cardLayout` | `banner` |
| `columns` | `2`, `3` |
| `countUp` | `true` |
| `entrance` | `cascade`, `rise`, `wipe` |
| `factsDisplay` | `bars` |
| `headingAlign` | `left` |
| `heroMedia` | `facts` |
| `hoverStyle` | `lift` |
| `statsTreatment` | `tiles` |
| `width` | `full` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
