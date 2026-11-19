# ReviewPage, ReviewSection, ReviewField

Review mode: answers shown as label and value rows, grouped by page and section, each section with an Edit link.

**Maps to:**
- `ReviewPage`: the Form Template review screen (`Enable_Review_Screen__c`). The page title comes from `Review_Page_Label__c` (default Review) and the subtitle from `Review_Page_Subtitle__c`. Each page's Page Label is a bold heading, followed by its sections. The review page's own button is the true submit (`Submit_Button_Label__c`).
- `ReviewSection`: `flowFormReview.html`. A rule, the bold section title, and an Edit link on the right; the link reads View when the form is Read Only (`disableAll`). A section that failed validation on submit gets a red border on a light red ground. A repeater section shows "(2 of 3)" after its title.
- `ReviewField`: `flowFormFieldReview`. The label takes 4 of 12 columns and the value 8 (both full width under 500px).

Values are formatted by data type, as the package does:

| `type` | Shows |
| --- | --- |
| `boolean` | TRUE or FALSE |
| `multipicklist` | Values joined with commas |
| `currency`, `percent`, `double` | Formatted numbers ($1,250.00, 42%) |
| `date`, `datetime`, `time` | Apr 12, 1988 · Nov 3, 2026, 2:00 PM · 9:30 AM |
| `email`, `tel`, `url` | Links |
| `reference` | The related record's name (`relatedName`). A guest never sees a raw Id: that row is hidden |
| `fileupload` | File names, as a list when there are several |
| empty | Not provided, in `placeholder` grey |

## Props
- `ReviewPage`: `title`, `subtitle`, `pages: [{ label, sections: [ReviewSection props] }]`, `readOnly`, `onEdit(page, section)`, `children` (put a `Navigation` after it).
- `ReviewSection`: `title`, `showHeader`, `fields: [ReviewField props]`, `readOnly`, `editLabel`, `invalid`, `repeaterIndex`, `repeaterTotal`, `onEdit`, `children`.
- `ReviewField`: `label`, `value`, `type`, `relatedName`, `guest`.

## Notes
The package's empty-answer text is "not provided" wrapped in em dashes; this system shows "Not provided" because its copy rules exclude em dashes. Review mode (`reviewMode` on a Lightning page or Flow screen) shows only the review page, with no indicators or button bar outside Flow.
