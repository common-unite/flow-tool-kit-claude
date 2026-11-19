# Features: Motion

One feature of the site design blocks shown across several designs: motion. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

You are deciding where motion goes on a page.

## The decision it settles

`entrance` (rise, cascade, wipe, zoom, blur), `hoverStyle` and `countUp`. One entrance above the fold, cascade only for lists, lift on anything clickable.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 13 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `cards` | 10 |
| `statsBar` | 1 |
| `pills` | 1 |
| `hero` | 1 |

2 blocks on the site page are left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `badgePosition` | `top` |
| `bodyAlign` | `left` |
| `cardStyle` | `elevated`, `outlined` |
| `columns` | `3` |
| `countUp` | `true` |
| `entrance` | `blur`, `cascade`, `rise`, `wipe`, `zoom` |
| `headingAlign` | `left` |
| `hoverStyle` | `lift`, `ring`, `tilt`, `tint`, `trace` |
| `imageFloat` | `true` |
| `imageStyle` | `mascot` |
| `statsTreatment` | `tiles` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
