# Page example: Record cards: every card type on real-looking records

A whole demo page, section by section with its column widths: record cards: every card type on real-looking records. Use it as the starting shape for a page of that kind.

## Use it when

A page lists Salesforce records (shifts, events, funds, people) and the card type is undecided.

## The decision it settles

Which `cardType` fits each kind of record: dateTile for events, progress for goals, profile for people, valueSpotlight for amounts, fieldList for detail, strip for long lists.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 56 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `recordCard` | 41 |
| `callout` | 15 |

1 block on the site page is left out here: a retired Call to Action (`cta`) or a stats look the package no longer offers. A new design uses a hero with `heroLayout` `band` instead. Retired `showcase` blocks are shown as the hero the package now draws them as, and old stat and layout keys as today's settings.

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `badgeStyle` | `accent`, `brand` |
| `bodyAlign` | `left` |
| `cardStyle` | `glow`, `outlined` |
| `cardType` | `countdown`, `dateTile`, `fieldList`, `headerBand`, `iconLead`, `mediaTop`, `photoOverlay`, `profile`, `progress`, `strip`, `valueSpotlight` |
| `headingAlign` | `left` |
| `iconStyle` | `tile` |
| `mediaHeight` | `medium`, `tall` |
| `overlayStyle` | `side` |
| `stripTone` | `error`, `success`, `warning` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
