# VolunteerApplicationForm

The volunteer application clients put on a site's Volunteer page: four pages (About you, Availability, Interests, Background check), shown on its first page with the path indicator.

**Maps to:** a four-page Form Template (`formTemplate`, `Form_Template__c`) with `Stage_Indicator_Type__c` = path. Built from `FormTemplate`, `StageIndicator`, `Section`, `TextInput`, `FormattedInput`, `DateInput`, `Picklist` and `Checkbox`.

## Props
- `currentStage`: the page to show the indicator on. Default "About you". The fields drawn are the first page's.

## Using it on a site
The FlowToolKit Site Blocks design system shows this form in its Form Slot (`form: "Volunteer Application"`), full width or in the 8 of an 8/4 Section. A long application often suits Stages Mode instead; see the FormTemplate card.

## Predates the form-type rules
This example was drawn before the 2026-11-17 form-type rules. By them a four-page application is a long form (row 6): Stages Mode with the vertical indicator, Save Progress, the review screen and a Docked bar; a shorter three-or-more-page form that is not an application would use the `base` indicator, never `path`. The drawing (path indicator, Standard bar for a site embed) is kept until it is redrawn; do not copy its indicator into a Form Template.
