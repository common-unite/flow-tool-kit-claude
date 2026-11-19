# LookupSearchTable

**Flow screen only.** The custom lookup override (`enableCustomLookup__c`) and this search table are available only when the form runs inside a Flow screen. A Form Template form (external or internal) cannot use them, so don't draw this in a template design; use the standard `Lookup` there.

The search table a custom lookup opens: a large modal with the lookup's heading, a single-select table of records, an optional New button, and Save once a record is picked.

**Maps to:** `flowFormLookup`, which opens when a Lookup field has `enableCustomLookup__c` = true (the `customSearch` variant of `Lookup`). The modal is `c-modal` at size large with `customLookupHeader__c` as the heading and `customLookupSubheader__c` under it. Inside is a `flowDataTable` in lookup mode: checkbox column on, `max-row-selection` 1 (so the rows show radios), the filter box, and the table form's columns. The footer has Cancel, and Save once a row is selected.

## Props
- `header` (`customLookupHeader__c`) and `subheader` (`customLookupSubheader__c`).
- `columns` and `rows`: the lookup's table form, using `Repeater` column options (`alignment`, `iconName`, `wrapText`, `displayType`, number digits). Cells are read only.
- `selectedIndex`: the row that starts selected.
- `enableFilter` (default true), `allowNew` with `newButtonLabel`, `showRowNumberColumn`, `tableRowStyle`, `hideTableHeader`, `hideTableFooter`, `displayAsDataTree` with `hierarchyFieldName`: the same table settings the lookup passes through.
- `inline` (default true) keeps the modal inside the design; `false` draws it over the page.
- `open` (default true), `onSave(row)`, `onCancel()`.

## Notes
Use it next to a `Lookup` with `variant="customSearch"` when a design needs to show what the search button opens. A lookup that opens another form instead (`referenceFieldOverrideType__c` = `startnewform` or `vieweditsubmission`) is not drawn here.
