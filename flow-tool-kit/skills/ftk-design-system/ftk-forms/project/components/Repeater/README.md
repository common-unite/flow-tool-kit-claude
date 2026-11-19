# Repeater

Repeating records: the Form Repeater (`flowFormRepeat`) shows one copy of a form component per record, so people can add, clone, reorder, edit and delete records.

**Maps to:** `flowFormRepeat`. Each record renders the repeated form component (`c-flow-form`) with that record's values, so the fields inside a record are ordinary FlowToolKit fields on the 12-column grid. In a design, `columns` stands for the fields of that repeated form component.

The repeater is not a table. An editable table of records is a different package component (`flowDataTable`, the Table section) and is not drawn in this design system yet; `layout: 'table'` is kept only so older mockups still render, and should not be used for new designs.

| Part | Renders |
| --- | --- |
| Record | The repeated form's fields, a rule between records (`hideDivider` removes it), an optional heading (`recordTitle`) |
| Record buttons | Bottom right of each record (or above with `displayRepeaterButtonsAbove`): one brand-outline group of Edit, Import, New and Clone, then Move Up / Move Down, then Delete |
| Header (`showHeader`) | The repeater's own `c-header` (title, subtitle, icon, rule). With the header on, Import and New move out of the records into the header, right-aligned in a brand-outline group |

Where New goes is decided by `flowFormRepeat`: `showImportAndNewOnRows` is true whenever the header is off, so a repeater with no header shows New (and Import) on every record next to Clone. Turn the header on to get a single New in the header instead. New, Import and Clone hide once there are `max` records; on a small container the record buttons become icon-only.

## Props
- `columns`: the repeated form's fields, `{ field, label, type, options, required, editable, widths, placeholder, helpText, defaultValue }`.
  - `type`: `text` (default), `email`, `url`, `textarea`, `number`, `currency`, `percent`, `picklist` (with `options`).
  - `widths`: `[large, medium, small]` spans. Default `[6, 6, 12]`.
- `rows` / `defaultRows`, `onChange(rows)`.
- `min` (default 1) and `max` (default 5), the package defaults. New, Import and Clone hide at `max`; Delete hides at `min`; Move Up and Move Down show only with more than one record.
- `allowNew` (default true), `allowDelete` (default true), `allowClone`, `allowReposition`, `allowEdit`, and `newButtonLabel` (New), `deleteButtonLabel` (Delete), `cloneButtonLabel` (Clone), `editButtonLabel` (Edit).
- `showHeader` with `title`, `subtitle`, `icon`, `headerHelpText` (the repeater's header: `showHeader`, `title`, `subtitle`, `iconName`, `helpText` in its configuration): draws the header and puts Import and New in it.
- `recordTitle`: a heading per record, `{n}` is the record number, for example `'Member {n}'`.

### More settings
- `allowImport` with `importButtonLabel` (default Import): a brand-outline Import button with `utility:record_lookup` beside New, on each record or in the header.
- `recordWidths: [large, medium, small]` puts records side by side; `featured` makes every record full width.
- `recordSpacing`, `recordSpacingBottom`, `recordSpacingHorizontal` (`Repeater_Record_Spacing__c`): `none`, `xxx-small` to `xx-large`, the space above, below and between records. `hideDivider` is `Repeater_Hide_Divider__c`.
- `showSelectedOnly`: only rows marked `selected: true` show.
- Edit modal: `allowEdit` adds Edit to each record. Clicking it opens the edit form in a medium `c-modal` that covers the screen, not under the repeater, with `editModalHeading`, `editModalSubheading` and a Return button (`editReturnButtonLabel`). `editOpen` (row index) opens it for a mockup. The card draws it covering the repeater (`modalInline: 'cover'`, the default); `modalInline: false` draws it over the whole page.
- `label`, `helpText`, `helpTextDisplay`, `required`; `readOnly` / `review` / `disableAll` hide every button and lock the cells.

## Pagination
`flowFormRepeat` is the only component that uses the package's paginator (`flowPagination`). It appears when more records are showing than `max` and `showSelectedOnly` is off (`displayPagination`). In practice, that means a Prefill Collection larger than `max`, often a repeater of record cards. The records then page `max` at a time, and New, Clone and Import stay hidden because the count is already past `max`. The row reads "Viewing 1-4 of 7" on the left, with the previous and next chevrons and page numbers on the right. The current page is a disabled base button. Past 10 pages it shows 1 to 8, an ellipsis, then the last page. The paginator has an autoplay (pause/play) mode, but nothing in the package turns it on, so it isn't drawn. `renderRecord(row, index)` draws a record's content in place of the columns grid, for a repeated form component that holds a `RecordCard`.

## Notes
The package draws no record count or totals row under a repeater. The custom lookup's search table is its own card, `LookupSearchTable`. Not drawn: the repeater carousel autoplay, the dynamic (query-driven) repeater, filter panels and the record card edit modal.
