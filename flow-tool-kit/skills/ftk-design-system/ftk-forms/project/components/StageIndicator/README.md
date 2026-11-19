# StageIndicator

The page progress indicator for a multi-page form template.

**Maps to:** `formStageIndicator`, driven by the Form Template's `Stage_Indicator_Type__c` (`base`, `path`, `vertical`, `footer base`, `footer path`) and `Hide_Stage_Indicator__c`. The package only shows it when the template has 3 or more pages.

Which type (form-type rules, in the form-design skill's house preferences): `base` for a form of three or more pages that is not long, because it shows on phones; `vertical` with Stages mode for a long form, an application or grant with three or more pages or any form of three or more pages and about 10 minutes or more; hidden on one or two pages. `path` hides on phones, so a Form Template page does not use it, and the footer types are not used either. No "Page N of M" heading beside it.

| `type` | Renders |
| --- | --- |
| `base` | `lightning-progress-indicator` type base above the page: completed pages show a `brand` success check, the current page a `brand` ring, later pages a grey dot; a 2px rule fills in `brand` up to the current page. Hover or focus a marker for the page label. `hasError` swaps the current marker for `utility:error` |
| `path` | SLDS path chevrons: complete, current (navy), incomplete. Hidden on phones by the package |
| `vertical` | `slds-progress_vertical`, a page list for a side rail. On a phone the package falls back to `base` |
| `footer base`, `footer path` | The same indicators drawn inside the docked button bar, `variant` shaded. Put the indicator in a `Buttons` as its child |

Stages Mode (`stageSteps: [{ label, status }]`, `status` one of `done`, `in-progress`, `requires-correction`, `locked`) draws the vertical list with status markers instead: edit on the current page (brand), check (success green), clock (brand), warning (orange) and lock (grey). Locked steps and the current step aren't clickable.

## Props
- `stages` (page labels in order), `current`, `complete` (labels; default every page before `current`), `hasError`.
- `type`, `variant` (`base` or `shaded`; footer types default to shaded).
- `stageSteps` (vertical Stages Mode), `onSelect(label)` when a page is clicked.
- `showLabels: 'current'` keeps the current page's label tooltip open on `base`, for mockups.
