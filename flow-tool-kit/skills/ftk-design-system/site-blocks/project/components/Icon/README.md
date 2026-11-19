# Icon

An SLDS icon as `lightning-icon` draws it: utility icons as glyphs in the text color, standard, action and custom icons on their colored tile.

**Maps to:** `lightning-icon`, which blocks use for card, stat, step and item icons (an item's `icon` key) and `siteDesignBlockIcon` wraps. Any SLDS 2.30.7 icon name works.

| Prop | Values |
| --- | --- |
| `iconName` | `utility:*`, `standard:*`, `action:*`, `custom:*`, `doctype:*` |
| `size` | `xx-small`, `x-small`, `small`, `medium`, `large` |

In a block, set the icon by name on the item (`icon: "utility:heart"`) and its color with the block's Icon Color; don't draw icons yourself.

## On LWR

No difference: both site types load the same SLDS icons.
