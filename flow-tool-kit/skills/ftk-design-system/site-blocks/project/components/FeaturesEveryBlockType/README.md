# Features: Every block type

One feature of the site design blocks shown across several designs: every block type. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

You are starting a page and want to see every block type side by side.

## The decision it settles

Which block does each section's job (see `Choosing blocks`, section 2).

How this fits the whole page: `Choosing blocks`.

**From a test site:** 11 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `hero` | 2 |
| `statsBar` | 1 |
| `cards` | 1 |
| `callout` | 1 |
| `steps` | 1 |
| `table` | 1 |
| `pricing` | 1 |
| `pills` | 1 |
| `carousel` | 1 |
| `image` | 1 |

1 block on the site page is left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundGradient` | `banner`, `off` |
| `backgroundTexture` | `crosshatch` |
| `cardStyle` | `clean`, `elevated`, `outlined` |
| `columns` | `3` |
| `countUp` | `true` |
| `entrance` | `blur`, `cascade` |
| `footnoteAlign` | `center` |
| `headingAlign` | `center` |
| `hoverStyle` | `lift` |
| `iconStyle` | `tile` |
| `imageFit` | `natural` |
| `imageStyle` | `elevated` |
| `reversed` | `true` |
| `statsTreatment` | `tiles` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
