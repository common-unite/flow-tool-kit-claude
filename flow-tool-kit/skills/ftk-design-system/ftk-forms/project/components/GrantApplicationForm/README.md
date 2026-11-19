# GrantApplicationForm

A grant application in Stages Mode, on its overview: the header Banner in its Split layout (title on a colored panel beside the photo), then one row per page with its status, time and next action, so an applicant can finish pages in any order.

**Maps to:** a Form Template (`formTemplate`, `Form_Template__c`) with `Stages_Mode__c` on, as the Grant Application | Demo template draws it. Built from `FormTemplate` (`stagesMode`, `view: 'overview'`), `Banner` and `StagesOverview`.

## Props
- `title`, `subtitle`: the Banner's. Default "Grant Application" and the save-and-return line.
- `stages`: the page rows (`StagesOverview` row shape). Default six pages, two done and one in progress.
- `image`, `scrimColor`: the Banner photo, and the color of the Split panel beside it.

## Using it on a site
The FlowToolKit Site Blocks design system shows this form in its Form Slot (`form: "Grant Application"`) on an application's record page, usually in the 8 of an 8/4 Section beside the application's status. See the FormTemplate and FormTemplatePages cards for the pages themselves.
