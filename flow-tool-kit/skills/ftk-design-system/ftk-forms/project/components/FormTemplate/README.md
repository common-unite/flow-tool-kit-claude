# FormTemplate

The shell a Form Template draws around its pages: header form, stage indicator, the page, the read-only footer form and the buttons. Use it to show a whole multi-page form, or one of its states.

**Maps to:** `formTemplate` and `Form_Template__c`.

## States (`state`)
- `active` (default): the page you pass as children.
- `loading`: `LoadingStencil`, shown while the template's prefill flow runs.
- `inactive`: `IsActive__c` is off, or today is outside `Start_Date__c` / `Close_Date__c`. Title "`<Name>` | Not Available", message `Offline_Message__c`.
- `confirmation`: after submit, unless `Skip_Confirmation_Page__c`. Message `Confirmation_Page_Message__c`, plus View Receipt after a Stripe payment.
- `error` with `errorType`: `loadError`, `noForm`, `missingRecord`, `prefillError`, `paymentError`, `prefillTemplate`.

## Stages Mode (the Grant Application | Demo pattern)
`stagesMode` (`Stages_Mode__c`) with `view`:
- `overview` (default): the header form card, then `StagesOverview` built from `stageRows` (or `stages`; same row shape as `StagesOverview`, from each page's `Page_Label__c`, `Description__c`, `Estimated_Time__c`, `Button_Label__c` and `Is_Optional__c`). The docked bar shows only Save Progress. Pass `overview` for other `StagesOverview` props.
- `step`: inside a page. The template swaps Back and Next for **Return** (`utility:back`) and **Mark Complete** (`utility:check`), with Save Progress between them. Earlier pages are not marked complete; pass `completeStages` for the ones that are.

The template draws its parts as separate cards: the header form on top, a vertical indicator in its own card at the left, and the page in a card beside it. The Grant demo also shows the common field-set section header: `Header_Display__c` = Divider with `Divider_Style__c` = compact (icon, title and a fading rule) and the subtitle under it.

## Props
- `header`: the header form (`FormQualifiedApiName_Header__c`, or `Template_Header_Text__c`). A converted form's header is a `Banner`. `placement: 'header'` (rounded on all corners) only when the vertical page indicator sits beside the card, which is Stages Mode: Overlay, Small. Every other form, whatever its page count, takes `singleCardHeader`: flush on the card with square bottom corners, Compact for a single page, Overlay for a multi-page form with no indicator or the `base` indicator. The previews show it.
- `footer`: the footer form (`FormQualifiedApiName_Footer__c`, or `Template_Footer_Text__c`). The package always renders it read only (`disable-all`).
- `stages`, `currentStage`, `stageIndicator` (`Stage_Indicator_Type__c` and other StageIndicator props), `hideStageIndicator` (`Hide_Stage_Indicator__c`). A vertical indicator sits in a left column; footer types sit inside the button bar.
- `pageHeader`: the current page's header (`PageHeader` props, from the page's `Show_Header__c` and `Header_*` fields). Only for a page that needs its own title, never "Page N of M".
- Theme: a template or recipe we ship keeps the default theme on the Form Template, with no theme per template and no new packaged Form Theme records; a client org may still use its own theme.
- `buttonsPosition` (`Buttons_Position__c`: `Footer` on one or two pages, `Docked` on three or more, C1, 2026-11-17), `buttonAlignment` (`Button_Alignment__c`), `navigation` (any `Buttons` props). The template shows up to 4 buttons before the overflow menu. `buttons: false` hides the bar.
- `readOnly`: the whole form read only, as on a submitted form.
- `blockingSpinner`: the brand spinner over the template while it saves.
- `toasts`: toasts to show under the template.

More pages: the **Form Template pages** card (Project Details, an optional Supporting Documents step) and the **Form Template review** card (Continue to Review, then the review page).

## Settings with no visual
- **Autosave** (`Enable_Autosave__c`, `Autosave_Mode__c` = `Upon Change`, `Every 10 Seconds`, `Every 30 Seconds`; page `Auto_Save__c`). The package saves quietly and shows no status; it even holds back the "Saved Successfully!" toast during an autosave. Put it in the handoff, not the drawing. In Stages Mode, `StagesOverview` shows "Draft saved".
- **Save Progress** (`Allow_Save_Progress__c`): a Save Progress button, then the `progressSaved` toast. There is no save-and-resume screen. With `Send_Save_Progress_Email__c` the respondent also gets the resume email ("Resume link sent" toast in Stages Mode).
- **Non-linear navigation** (`Non_Linear_Navigation__c`): the stage indicator becomes clickable in any order. Draw it the same; note it in the handoff.
- **Print** (`Do_Not_Print__c` on a page or page section): left out of the printed form. Note it on the page or section in the handoff.

## Error states the package shows
Besides Inactive (shown on the card), `formTemplate` swaps the page for a `display-illustration` panel when setup or data is broken. Partners don't design these; name them in a handoff only when a form's setup could trigger one.

| State | Illustration | Title and message |
| --- | --- | --- |
| Inactive | Not Available, large | "`<Form Template Name>` \| Not Available", `Offline_Message__c` |
| Prefill error | Base, large | "Prefill Flow Error", the flow's error |
| Payment error | Not Available, large | "Payment Unavailable" (see `PaymentStep`) |
| Load error | Maintenance, small | "Form Load Error" |
| No form | No Content, small | "No Form Found" |
| Missing record | No Content, small | "Choose a form record" |
| Pre-fill template | No Content, small | "This is a Pre-fill Template" |

