# LikertMatrix

A set of statements rated on one shared scale. Rows are the questions; columns are the scale. Put it inside a `Section`, since in the package it is a section type (Likert Matrix).

**Maps to:** a Form Template section with section type Likert Matrix, hand-written from `flowFormLikertMatrix` and `likertScaleEditor`. Each row is one field in the section.

| Option | Package setting | Renders |
| --- | --- | --- |
| `mode: 'Picklist'` (default) | `Likert_Mode__c` = Picklist | Columns are the first field's picklist values, in the order its Included list sets. Every row stores a picklist value |
| `mode: 'Number'` | `Likert_Mode__c` = Number, `Likert_Scale__c` | Columns come from the scale JSON (`label`, numeric `value`, optional `help`). Every row stores a number |
| `showTotal`, `totalLabel` | `Show_Total_Score__c`, `Total_Score_Label__c` | A card under the grid with the sum, "N of M answered", and an amber Partial pill until every row has an answer |
| `layout: 'auto'` (default) | none: the package decides | The grid on desktop and tablet. The stacked layout is the **mobile version**: the package switches to it on a phone (`FORM_FACTOR` = Small), and only falls back to it on a larger screen when the matrix is squeezed into a column under 480px. In stacked, each row becomes its own Survey Buttons question |

## Props
- `scale`: strings, or `{ label, value, help }`. A column's `help` shows on hovering its header (dotted underline).
- `rows`: strings, or `{ id, label, required, helpText, helpTextDisplay, readOnly }`. Without `id`, rows are keyed `row0`, `row1` and so on.
- `values` / `defaultValues`: `{ rowId: value }`. `onChange(values, rowId)`.
- `layout`: `auto`, `grid` or `stacked`. Use `stacked` only to show the phone version of a design; desktop mockups use the grid.
- `showErrors`: draws the required-row error as it looks after Next or Submit. In the package, `flowForm` calls the matrix's `reportValidity()`, which flags every required row that has no answer. Each flagged row turns pink (`#fddde0`) with a 3px `#ba0517` bar on its left edge, and a line under it reads "Please select an answer to continue." (`Likert_Row_Error`, with `utility:error`). Answering a row clears its error right away. The form also raises one validation toast for the whole matrix, "<section title>: is required". Optional rows never show the error.
- `readOnly` / `review`: answers show, nothing is clickable.
- `label`: the group's accessible name (the section title in the package).

## Notes
In the grid, rows alternate `surface-muted`, the chosen cell takes a 12% brand tint with a brand dot, and a required row that is still empty turns pink with an `error-strong` bar. Row help shows on hovering the label (`Hover Bubble`) or as a two-line note under it. Keep statements short; the label column is 260px wide.
