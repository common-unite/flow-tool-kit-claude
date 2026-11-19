# Form Template review

The end of a Stages Mode template with a review screen (`Enable_Review_Screen__c`), drawn with `FormTemplate` and `ReviewPage`.

- **Overview, ready for review**: once every required stage is done, the overview adds **Continue to Review** (`Review_Page_Button_Label__c`, default label `Stages_Continue_To_Review`, `utility:forward`) beside Save Progress. Every row reads Complete with a Review answers button.
- **Review page**: the review screen is the last step. It is added to the stage indicator and is never clickable. It shows `Review_Page_Label__c` and `Review_Page_Subtitle__c`, then every page that has fields, each section with Edit. A section that failed validation is outlined in error. Its button is the real submit: `Submit_Button_Label__c` (default Submit) with `utility:save`, after Return and Save Progress.

Without Stages Mode, the last page's Next opens the review page instead, and the same review layout follows. See the `ReviewPage` card.
