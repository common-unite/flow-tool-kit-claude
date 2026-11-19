# Badges

Small pills above the heading (`badgePosition: "top"`) or below the buttons (`"bottom"`), from the Badges pane.

**Maps to:** keys on any block, not a component of its own. The preview draws them on a bare Steps block so they are seen alone. Use them through a block's props: `<Hero badges={...} />`.

## Each item in `badges`

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `style` | Style | `neutral`, `brand`, `accent`, `outline` |
| `pulse` | Pulse | checkbox |

## Settings

| Prop | Property Editor | Values |
| --- | --- | --- |
| `badgeAlign` | Badges: Badge Alignment | `left`, `center`, `right` |
| `badgePosition` | Badges: Badge Position | `bottom`, `top` |
| `badgesGap` | Badges: Space Below Badges | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

## On LWR

The same keys draw the same part on an LWR site; see the Block card for where LWR differs.
