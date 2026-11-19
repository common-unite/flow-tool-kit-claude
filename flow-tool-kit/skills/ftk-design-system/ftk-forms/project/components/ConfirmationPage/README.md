# ConfirmationPage

What the respondent sees after submitting.

**Maps to:** `formTemplate` showConfirmationPage. `Confirmation_Page_Message__c` is the rich text message; without one the package shows "Your response has been submitted." (`Confirmation_Default`). `Skip_Confirmation_Page__c` skips it. `Confirmation_Page_Label__c` is stored but not drawn.

After a Stripe payment the page adds a brand **View Receipt** button with `utility:new_window`. With no receipt URL (some setup and subscription flows) nothing extra shows.

## Props
- `message` (HTML), `receiptUrl`, `receiptLabel`, `onViewReceipt`.

## Writing the message
Use the message to close the loop, not just to confirm: a short thank-you headline that names the person, what happens next and when (who will contact them, by when), and one or two lines on the impact of what they just did. Keep it to a heading, a short paragraph and at most three bullets.

## Merge fields
The message resolves `{{Field}}` tokens against the Form Submission (the same merge the stages overview uses), for example `{{FlowToolKit__Contact1_First_Name__c}}` or `{{FlowToolKit__Amount__c}}`. Every value a design shows in the message (a name, a garden, counts, amounts) must therefore live on a Form Submission field: write the token for each in the handoff, and when a value has no submission field (a total calculated on another object), map it back or leave it out. Watch Number fields with decimals (2 can print as 2.00) and write copy that reads right for one or many.

## Spacing
The package panel adds `slds-p-around_small` and `slds-p-bottom_large`, and `slds-m-bottom_x-large` (32px) under the message (`slds-m-bottom_medium` when a receipt button follows). The preview card trims that trailing space so the examples sit close together; a full-page design keeps it.
