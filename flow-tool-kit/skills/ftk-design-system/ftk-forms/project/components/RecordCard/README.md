# RecordCard

A record shown as a card: one of the package's 11 card types, each a fixed arrangement of slots (image, eyebrow, title, value, rows, buttons and so on).

**Maps to:** `recordCard` with its types and slots from `recordCardConfig`. Used in forms (`standalone`) and Site Design Blocks.

| `cardType` | Package label | Layout |
| --- | --- | --- |
| `mediaTop` (default) | Media Top | Photo above (`mediaHeight` short 170, medium 210, tall 260), badge on the photo, inline rows, value and buttons in a split footer |
| `photoOverlay` | Photo Overlay | Copy over a full photo with a scrim (`overlayStyle` bottom, side, tint, light, none; `scrimColor`) |
| `dateTile` | Date Tile | A month, day and weekday tile from `date`, beside the title (or riding the photo when there is an `image`) |
| `progress` | Progress | `progressCurrent` of `progressTotal`, a percent and a brand bar; full-width buttons |
| `headerBand` | Header Band | A brand band with `eyebrow` left and `cornerTag` right, then title, description and tags |
| `strip` | Strip | One band: a tone icon or thumbnail, the title and subtitle in a line, buttons at the right (`stripTone` info, warning, success, error; `stripIcon`) |
| `countdown` | Countdown | Day, hour and minute tiles to `date` (`countdownUnits` dhm, dhms, d; `countdownDirection` down, up; `countdownEnded`) |
| `iconLead` | Icon Lead | A 56px avatar (photo, icon or initials) beside the title, grid rows |
| `profile` | Centered Profile | A centered 72px avatar, tags and stat rows |
| `fieldList` | Field List | A title over label and value rows |
| `valueSpotlight` | Value Spotlight | One big value, its details and full-width buttons |

## Props
- Slots: `image`, `imageAlt`, `badge`, `badgeStyle` (`neutral`, `brand`, `accent`, `outline`), `cornerTag`, `eyebrow`, `title`, `subtitle`, `description`, `rows` (`[{ label, value }]`), `tags` (strings or `{ label, style }`), `value`, `valueSuffix`, `meta` (footer note), `buttons` (`[{ label, url, style }]`, style `brand`, `light`, `accent`, `outline`, `link`), `date`, `progressCurrent`, `progressTotal`, `link` (makes the whole card clickable).
- Options: `cardStyle` (`elevated` default, `outlined`, `flat`), `mediaHeight`, `imageFrame`, `overlayStyle`, `scrimColor`, `avatarType` (`initials`, `image`, `icon`), `icon`, `iconStyle` (`circle`, `tile`), `stripTone`, `stripIcon`, `countdownUnits`, `countdownDirection`, `countdownEnded`, `now` (pins the countdown clock for a mockup).
- Selection: `allowSelect` (set when the card is the repeated form of a Form Repeater with Allow Selection on), `isSelected`, `preventNewSelection` (the repeater is at its Max Selection Size), `selectLabels` (`{ off, on, hover }`, the repeater's label overrides; defaults Select, Selected, Unselect), `onSelect`. The card adds its own brand stateful Select button first in its buttons, so one card design serves a repeater that selects and one that does not; selected, it reads Selected with a check (Unselect on hover). `picker` (the section is a visual picker that wraps the card): the whole card selects and its link is dropped; the visual picker frame itself is not drawn. With Max Selection Size 1, selecting a card clears the others. The repeater hands the choice to the Flow as `selectedRecords` and `selectedRecordsIds`, which is how a Flow section picks one related record (a primary contact, say) without a picklist.
- `sample`: fills every empty slot with the package's own sample for that type, the copy the card builder starts with.

## Notes
Cards stretch to the height of their grid row (`recordCard` sets `:host` and `.rc` to `height: 100%`), so a row of cards lines up its footers. Show at most two cards per row on a form page, and put cards of one type in a row; mixing a tall type (Media Top, Photo Overlay) with a short one (Date Tile, Icon Lead) leaves the short cards mostly empty space. The catalog at the top of the card shows each type at its natural height. Only slots the type draws appear; an empty slot leaves no gap. The card's corners follow `--ftk-radius-medium` (16px by default).
