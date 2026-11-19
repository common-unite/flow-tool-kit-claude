# Page example: Funding pages: listing, fund detail and application patterns

A whole demo page, section by section with its column widths: funding pages: listing, fund detail and application patterns. Use it as the starting shape for a page of that kind.

## Use it when

A funder's site needs a fund listing page, a fund detail page or an application landing page.

## The decision it settles

The section order for funding pages: hero with facts, attached stats, eligibility, timeline, action card beside the details.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 25 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `hero` | 8 |
| `facts` | 5 |
| `cards` | 3 |
| `statsBar` | 2 |
| `pills` | 2 |
| `timeline` | 2 |
| `quote` | 1 |
| `callout` | 1 |
| `actionCard` | 1 |

7 blocks on the site page are left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

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
| `cardLayout` | `inline` |
| `cardStyle` | `clean`, `flat` |
| `columns` | `1`, `2` |
| `countUp` | `true` |
| `entrance` | `wipe`, `zoom` |
| `factsDisplay` | `bars`, `stacked` |
| `headingAlign` | `left` |
| `heroMedia` | `facts` |
| `hoverStyle` | `lift` |
| `iconSize` | `small` |
| `iconStyle` | `circle` |
| `statsTreatment` | `tiles` |
| `timelineOrientation` | `horizontal`, `vertical` |
| `width` | `full` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
