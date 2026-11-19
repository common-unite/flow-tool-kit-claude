# StagesOverview

The Stages Mode overview screen: a progress banner and one row per page, each with its status, time and next action, so people can finish steps in any order.

**Maps to:** `formTemplateStages` and `formTemplateStageRow`, shown when the Form Template's `Stages_Mode__c` is on. `Stage_Mode_Layout__c` adjusts it (`Hide Progress Banner`, `Hide Completed Fields`, `Display Template Header`). Page values come from `Form_Template_Page__c`: `Page_Label__c` (title), `Description__c`, `Estimated_Time__c` (minutes), `Button_Label__c` (the Start label) and conditional logic (the Conditional badge).

| Stage `status` | Circle | Badge | Action |
| --- | --- | --- | --- |
| `done` | Teal with a check | Complete (outlined) | Review answers (brand outline) |
| `requires-correction` | Magenta with a warning | Needs attention | Fix errors (destructive), plus the correction note |
| `in-progress` (or `hasStarted`) | Number in a progress ring | In progress | Resume (brand) |
| `todo` | Number, grey ring | none | Start Step or the page's Button Label (brand) |
| `optional` | Number, dashed ring | Optional | Start Step (brand outline) |
| `locked` | Grey with a lock | Locked | Disabled; row dimmed |

## Props
- `title`, `subtitle`, `lastSaved` (the "Draft saved" line), `current` (the open page's title).
- `stages: [{ title, description, status, hasStarted, progress (0 to 1), time (minutes), meta: { fields, completedFields, errors }, substeps: [title or { title, description }], correctionDetails, conditional, action: { kind, label } | null, startLabel }]`.
- `layout` (Stage_Mode_Layout__c values) or `hideProgressBanner`, `hideCompletedFields`.
- `templateHeader` with `Display Template Header` in `layout` (or `displayTemplateHeader`): the Form Template's configured Header form, drawn in place of the title and subtitle (`formTemplateStages` fills its `templateHeader` slot with the template's header form). For a converted form that's its Banner: Overlay at Small height with `placement: 'header'`, the short banner the Banner card recommends for stages mode. The "Draft saved" line then floats over the header's top right (`save-absolute`). Use it whenever the template has a header: the plain title is for templates without one.
- `onSelect(stage)` for the row action.

When to use it: a long form (form-type rules row 6: an application or grant with three or more pages, or any form of three or more pages and about 10 minutes or more, long surveys included; G5, G7), with Save Progress, the vertical indicator, the review screen and a Docked bar. This is the one valid place for an intro page, and even here it is optional: an About or Learn More page of long-form information before the application, labelled for its purpose ("About the Program", "Learn More"), with Learn More or Get Started. Question stages are named for what they ask. Never a page labelled "Welcome". Rows already show position, so no "Page N of M".

## Notes
The package draws this screen with fixed Stages colors (teal success, magenta correction) rather than the brand, apart from the progress bar and buttons. Rows with sub-steps expand to list the page's sections. Desktop rows put the status, title, description, meta pills and correction box in the body, and the time and button in a column on the right. The correction box (`Correction_Details__c`) is an `slds-box` with a 3px error bar on the left, under the meta pills.

Under 600px of container (`NARROW_WIDTH` in `formTemplateStageRow`) the row switches to a narrow layout, so a phone never shows a squeezed desktop row. A collapsed narrow row shows only the status circle, title, time and fields count. It hides the description, badge, button, error and substep pills, and the correction box. Tapping a row expands it, and the button then drops to a full-width row under the body. This card draws the desktop rows (laid out at 900px); the narrow rows aren't drawn yet.

- Each stage also takes `optional` (`Is_Optional__c`, an Optional badge) and `visibility` (`Visibility__c`: `Internal Only` and `External Only` draw a badge; the package simply leaves the page out for the other audience).
