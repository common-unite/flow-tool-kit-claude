# Features: Background photos

One feature of the site design blocks shown across several designs: background photos. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

A section needs a photo behind it and you are choosing how the photo moves and how text stays readable.

## The decision it settles

Photo motion (`backgroundEffect`: none, parallax or Ken Burns) and the overlay (`backgroundOverlay`: tint, side, bottom). One photo motion above the fold; pick the overlay by where the text sits.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 17 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `hero` | 12 |
| `image` | 3 |
| `callout` | 1 |
| `statsBar` | 1 |

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `backgroundEffect` | `kenburns`, `parallax` |
| `backgroundGradient` | `off` |
| `backgroundOverlay` | `bottom`, `light`, `side`, `tint` |
| `blockHeight` | `band`, `standard`, `tall` |
| `bodyAlign` | `left` |
| `buttonAlign` | `left` |
| `cardStyle` | `clean` |
| `contentPosition` | `bottom`, `center`, `top` |
| `countUp` | `true` |
| `headingAlign` | `left` |
| `hoverStyle` | `lift` |
| `imageStyle` | `elevated` |
| `statsTreatment` | `row` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
