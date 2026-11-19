# Features: Inset band

One feature of the site design blocks shown across several designs: inset band. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

A section should read as a panel set into the page instead of a full-width band.

## The decision it settles

`width: "inset"`: an inset band with its own gradient and texture, for a featured group in the middle of a long page.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 1 block, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `cards` | 1 |

1 block on the site page is left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundGradient` | `diagonal` |
| `backgroundTexture` | `crosshatch` |
| `cardStyle` | `clean` |
| `columns` | `2` |
| `hoverStyle` | `lift` |
| `width` | `inset` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
