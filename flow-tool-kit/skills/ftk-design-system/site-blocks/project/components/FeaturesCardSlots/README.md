# Features: Card slots

One feature of the site design blocks shown across several designs: card slots. From the demo site's showcase home page, where each chapter shows one setting's whole range.

## Use it when

Cards have more than a title and body (an eyebrow, an icon, a link, a value) and you are choosing how they lay out.

## The decision it settles

`cardLayout` (stacked, inline, banner) and which slots each card fills. Inline for many short items, stacked for fewer, longer ones.

How this fits the whole page: `Choosing blocks`.

**From a test site:** 2 blocks, drawn by the package's own `siteDesignBlock` exactly as stored on the site.

## Blocks

| Type | Count |
| --- | --- |
| `cards` | 2 |

## Settings these designs use

The values on this card. Start a design from these, not from a block's defaults.

| Setting | Values used |
| --- | --- |
| `cardLayout` | `inline` |
| `cardStyle` | `joined`, `outlined` |
| `columns` | `3`, `4` |
| `hoverStyle` | `lift` |

## Use it

Copy a section into a page design and change the words and images; keep the settings that give it its look. Every block key and value here is valid in the package (the props check passes on this card).
