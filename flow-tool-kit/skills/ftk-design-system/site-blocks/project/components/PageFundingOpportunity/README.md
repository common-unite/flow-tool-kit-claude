# Page example: One funding opportunity's page

A whole demo page, section by section with its column widths: one funding opportunity's page. Use it as the starting shape for a page of that kind.

## Use it when

One grant or fund needs its own page that sells it and gets people to apply.

## The decision it settles

The order that gets people from interest to applying: promise, proof, what it funds, eligibility, steps, a quote, the ask.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 10 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `cards` | 3 |
| `hero` | 2 |
| `statsBar` | 2 |
| `callout` | 1 |
| `steps` | 1 |
| `quote` | 1 |

1 block on the site page is left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundEffect` | `parallax` |
| `backgroundGradient` | `off` |
| `backgroundOverlay` | `side`, `tint` |
| `badgePosition` | `top` |
| `blockHeight` | `standard`, `tall` |
| `bodyAlign` | `left` |
| `buttonAlign` | `left`, `right` |
| `cardStyle` | `clean`, `ghost`, `outlined` |
| `columns` | `3`, `4` |
| `contentPosition` | `center` |
| `countUp` | `false`, `true` |
| `entrance` | `rise`, `wipe`, `zoom` |
| `footnoteAlign` | `center` |
| `headingAlign` | `left` |
| `heroMedia` | `facts` |
| `hoverStyle` | `lift` |
| `imageFit` | `natural` |
| `imageStyle` | `elevated` |
| `reversed` | `true` |
| `statsTreatment` | `row`, `spread` |
| `width` | `full` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
