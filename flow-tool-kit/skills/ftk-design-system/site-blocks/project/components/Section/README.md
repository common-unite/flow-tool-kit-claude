# Section

An Experience Builder Section: one to four columns whose widths add up to 12, with the Section's own background and height.

**Maps to:** `forceCommunity:section`. Props are its `componentAttributes`, named as the Testing Aura ExperienceBundle stores them; the columns are its `sectionConfig.columns`.

| Prop | Builder setting | Notes |
| --- | --- | --- |
| `background` | Section background | Any CSS background. Default transparent. Blocks usually carry their own background instead. |
| `backgroundOverlay` | Background overlay | A color over the background image. |
| `contentAreaWidth` | Content Area Width | Percent of the content area, default 100. |
| `sectionHeight` | Section Height | The row's minimum height in pixels, 32 at least (Builder refuses less). Builder stores 300; set 32 for a Section that hugs its content. Aura applies it, and Content Area Width, only when the page loads wider than 1024px; on tablets and phones the Section is as tall as its content. |
| `showGrid` | (design aid) | Draws the faint 12-column grid and labels each column's width. Not site markup. |

## Column

`Column` is one of the Section's columns. `columnWidth` is 1 to 12. Columns sit side by side from 1024px up (`slds-large-size_N-of-12`) and stack full width below it, in their order, so put the column a phone visitor should see first on the left. Each child of a Column sits in its own `ui-widget`, 24px (`--lwc-uiWidgetMarginBottom`) below the one before. Column padding is 16px at the outer edges and 8px between columns, as Aura draws it.

## Checks
A Section with more than four columns, or columns that don't add up to 12, logs an error and fails the preview check.

## SLDS
`slds-grid`, `slds-wrap`, `slds-large-nowrap`, `slds-size_12-of-12`, `slds-max-medium-size_12-of-12`, `slds-large-size_N-of-12`, and Aura's own `cb-section` markup.

## On LWR

The same Section and Column draw `community_layout:section` and its columns, as Testing LWR renders them, with the same column widths (`sectionConfig.columns`, keyed `col1`, `col2` and on).

- `background`, `backgroundOverlay`, `contentAreaWidth` and `sectionHeight` are Aura settings; an LWR section ignores them. Color a band with a block's own background instead.
- `sectionVerticalAlign` (`flex-start`, `center`, `flex-end`) is LWR's: how columns of different heights line up.
- Columns are separated by the site's column spacer (1rem of padding on each side of it at Builder's default) and stack at 1024px wide and narrower, as on Aura.
- Every component in a column but the last is spaced by the component spacer, 1.5rem at Builder's default.
