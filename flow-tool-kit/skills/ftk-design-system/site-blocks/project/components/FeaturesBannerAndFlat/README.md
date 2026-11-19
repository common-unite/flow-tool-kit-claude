# Features: Banner and flat

One feature of the site design blocks shown across several designs: banner and flat. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

A short title band or a plain section is needed and you are choosing between a brand banner gradient and flat color.

## The decision it settles

`backgroundGradient: "banner"` for a brand title band, `off` for a quiet section that lets the content lead.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 3 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `hero` | 2 |
| `cards` | 1 |

4 blocks on the site page are left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundGradient` | `banner`, `off` |
| `cardStyle` | `clean` |
| `columns` | `2` |
| `hoverStyle` | `lift` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
