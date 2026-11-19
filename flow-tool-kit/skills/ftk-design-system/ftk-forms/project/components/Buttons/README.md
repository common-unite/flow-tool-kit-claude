# Buttons

The form's button bar (`buttonsCustom`): navigation (Back, Save Progress, Continue, Submit or Review) and action buttons. On a Form Template the template builds the navigation buttons; on a Flow screen the Buttons component also carries custom action buttons (Approve, Request changes, Withdraw and so on), the Additional Actions menu, groups, paths and confirm dialogs.

Use `FTK.Buttons` (`FTK.Navigation` is the same component under its old name).

**Maps to:** `buttonsCustom` as the Form Template draws it. `Buttons_Position__c` is the position (`Docked`, the default sticky bar; `Footer`; `Standard`, inline). `Button_Alignment__c` is the alignment (`start`, `center` default, `end`, `spread`, `space`).

The package builds the buttons like this, and the component does the same unless you pass `buttons`:
- **Back** (brand outline, `utility:back` on the left) is labelled with the previous page's Page Label.
- **Save Progress** (brand outline, `utility:save` on the right) appears when `Allow_Save_Progress__c` is on. Saving shows only the platform's "Saved Successfully!" toast, with no save-and-resume screen, so a design needs no extra state for it.
- **Continue** (brand, `utility:forward` on the right) uses the page's `Button_Label__c` (the picklist offers Continue, Next, Get Started, Apply Now and so on). House rule: Continue on every page, never Next; Learn More or Get Started only on an intro page, which is rare: mainly an About or Learn More page before a long-form application, never labelled "Welcome".
- On the last page it becomes `Submit_Button_Label__c` (Submit Form, Submit Application and so on) with `utility:save`. If a review screen follows, it becomes the review button (`Review_Page_Button_Label__c`, default Continue to Review) with `utility:forward`.
- With `spread` and only a forward button, the button lines up at the end.
- In Docked and Footer bars at narrow widths, the buttons stack full width.

## Footer or Docked
A form of one or two pages uses `position: 'Footer'`. A form of three or more pages uses `position: 'Docked'`, so the bar stays in reach on long pages (C1, 2026-11-17; the form-type rules table in the form-design skill's house preferences). The Footer bar is the bottom edge of the form card: place it as the card's last child with no wrapper padding or margin, so its grey band and top rule run flush to the card's left, right and bottom edges and its rounded bottom corners meet the card's. Never inset it inside the card's content padding; an inset Footer bar is wrong. A Standard bar is the one that sits inline under the last field, inside the content padding. Remember a submit label that changes with payment: when the template collects a payment, the last-page button reads Continue to Payment (package gap: the template has one Submit label; see the payment notes in the handoff).

Every button here is a `lightning-button` drawn with the package's button styles (`buttonHoverStyles`): `brand`, `brand-outline`, `neutral`, `destructive`, `base`. There is no separate button card; use these variants for any button a design needs.

## Where each option works
`buttonsCustom` runs in two places, and they expose different options. Design for the place the form will run.

**Form Template (external and internal forms built in Form Builder).** The template builds the buttons itself and passes only `footer`, `docked`, `buttonAlignment`, `numberOfButtonsToShow = 4` and its generated buttons (`formTemplate.currentPageButtons`). A design for a template can use:
- `position` (`Buttons_Position__c`), `alignment` (`Button_Alignment__c`, including `spread` and `space`).
- `backLabel`, `saveProgress` / `saveProgressLabel` (`Allow_Save_Progress__c`), `nextLabel` (`Button_Label__c`), `lastPage` with `submitLabel` (`Submit_Button_Label__c`), `reviewNext` with `reviewLabel` (`Review_Page_Button_Label__c`), `readOnly`.
- `children`, such as a `StageIndicator` with `type: 'footer base'`.

**Flow screen only (the Buttons component dropped on a Flow screen).** These are buttonsCustom's own Flow properties, so a Form Template cannot set them:
- `buttons`: custom buttons with their own `label`, `variant`, `iconName`, `iconPosition`, `type`, `disabled` (`1) Custom Buttons`, or the manual button properties).
- `numberOfButtonsToShow` (`3) Number of Button(s) to display`, default 3): the rest go in an "Additional Actions" menu; 0 = menu only. The last shown button joins the menu in a group. A lone Back always keeps Next beside it.
- `groupButtons` (`4) Group Buttons`): every shown button in one button group.
- `showAsPath`, `currentStage` (`Show As Path`, `Current Stage`): the buttons draw as a path.
- `confirmModal` (`enableModal` with `modalHeading`, `modalSubheading`, `modalBody`, `modalTheme`, confirm and cancel labels): the button asks first. A button in `buttons` can carry its own `confirmModal`.
- `infoText` (`dockedInfoDialog`): the info dialog above a docked bar. `disableButtons`, `buttonHeight`, `buttonWidth`.
- `onClick(button)` stands for `buttonClicked` / `buttonClickedLabel` / `buttonClickedValue`, the outputs the Flow branches on.

The examples on the card marked FLOW SCREEN ONLY use these.

## Notes
The Flow Tool Kit experience standard asks for split alignment (`spread`) when there's no Save, and centered grouping when Save Progress is on, with the bar docked on three or more pages. In a design, the Docked bar is drawn in place; in Salesforce it sticks to the bottom of the viewport.
