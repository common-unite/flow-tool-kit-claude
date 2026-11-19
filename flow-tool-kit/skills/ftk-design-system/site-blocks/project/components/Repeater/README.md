# Repeater

A list of records drawn as record cards: one card per record, in columns.

**Maps to:** Form (Dynamic Repeater), `formDynamicRepeater`, showing a Record Card form. Each card is the package's own `recordCard`, compiled from the package, with the record's values typed in.

| Prop | Notes |
| --- | --- |
| `cardType` | The Record Card type every record uses: `mediaTop`, `photoOverlay`, `dateTile`, `progress`, `headerBand`, `strip`, `countdown`, `iconLead`, `profile`, `fieldList`, `valueSpotlight`. |
| `columns` | Cards across at desktop width, 1 to 4 (the component's `largeColumns`). Two across on a tablet, one on a phone, unless `mediumColumns` or `smallColumns` set otherwise. |
| `records` | One object per record, keyed as a Record Card block is (`eyebrow`, `title`, `subtitle`, `badge`, `items`, `buttons` and the rest; see the RecordCard card). `imageAsset` takes a packaged image name. |

## Notes
The cards and the grid are the package's: each card is `recordCard` mounted standalone, as a form's Record Card section mounts it (the elevated frame: 1px border, 16px corners, a soft shadow), and the grid is `flowFormRepeat`'s (a 2rem gap between columns, none between rows, each card `(100% + 2rem) / 12 * span - 2rem` wide, the span changing at 480, 768 and 1024px). Both are checked against a live repeater on the Testing Aura and Testing LWR `/live-repeater` pages, at desktop, tablet and phone width, with the cards drawn from the records the live query returns. Use the Repeater for a listing page (all open opportunities); for one record, use a RecordCard block.

## On LWR

The same component (`FlowToolKit:formDynamicRepeater`) and cards. In an LWR column it is spaced like any other component.
