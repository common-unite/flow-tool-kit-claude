# Form Template pages

More pages of the Grant Application | Demo template in Stages Mode, drawn with `FormTemplate` (`view: 'step'`). The FormTemplate card has the overview and Organization Info; this card adds two more steps.

- **Project Details**: a required step with Grant Information and Organization Info complete (`completeStages`). Field-set sections with compact divider headers: text, a counted text area, dates, a 3-column multi-select, a stepper, a picklist, separated buttons and a toggle.
- **Supporting Documents**: an optional step (`Is_Optional__c`) of `FileUpload` fields, each with its `acceptedFormats__c`, one already uploaded, and one taking several files.

Inside any step the bar reads **Return**, **Save Progress** and **Mark Complete** (`utility:check`), as `formTemplate` relabels Back and Next in Stages Mode.

Props are documented in the `FormTemplate` README.
