# Column

One field's place on a section's 12-column grid, at the three container widths FlowToolKit lays fields out at.

**Maps to:** a field's `widthLarge__c`, `widthMedium__c` and `widthSmall__c`. Follows the package's presentation contract for field widths.

## Props
- `large`: columns at full width (default 12), or `shrink` (`widthLarge__c` = shrink): the field takes its content width and the next field follows on the same row. Use it for short controls such as a toggle or a two-digit number.
- `medium`: columns once the section is under 800px wide (default 12).
- `small`: columns once the section is under 500px wide (default 12).
- `children`: one field.

## Notes
Width is measured from the section's container, not the screen, so a form in a narrow page column behaves as small on a desktop monitor. A field always spans whole columns. Columns sit 16px apart with 12px between rows.
