# Worked examples

Four Flow Sections, each for an invented organization. The first two are full specs: run `python3 scripts/flowsection.py scaffold examples/<spec> --out <project-dir>` to see the flow each one becomes. The flows both specs produce passed a check-only deploy to an org with Flow Tool Kit installed; neither has yet been walked in a live form. The last two are recipes for what the spec cannot express, built on top of a scaffolded flow; they have not been run in an org yet.

## 1. Household contact picker (one screen, the page drives)

`household-contact-picker.spec.json`, which scaffolds `Form_Section_Household_Contact_Picker`

Riverside Community Garden's plot renewal is filled in by signed-in members on their portal. The household Account is already on the Form Submission (set by the prefill flow). The section lists the household's Contacts and asks who the primary contact is; the chosen Contact goes back as **Contact 1**, so the conversion updates that person instead of creating a new Contact.

- One screen with a record choice (Contacts where Account is `{!record.FlowToolKit__Account__c}`, by last name). It is the first screen, so the choice is not required in Flow: Continue with nothing picked comes back to the screen with a message, and Back still leaves.
- Returns only Contact 1, on `New_Values`.
- The page's buttons drive: one bar, Continue validates the choice.
- The review shows the Contact's name (a Get Records on the review path), not its Id.
- Audience portal: the flow requires permission to run; flow-access-fix grants it in the members' permission set. The members see only the Contacts their sharing shows them, which is the point: check it as a member.

Why not native: the options are the org's own records for this household, which no static picklist can hold. Why not an LWC: nothing changes as they type.

## 2. Event registration in two steps (the section drives)

`event-registration-steps.spec.json`, which scaffolds `Form_Section_Event_Registration_Steps`

Example Food Bank's volunteer day registration, public (guests). One page section walks the registrant through their own details, then the guests they bring.

- Screen 1 carries the **Attendee Details** form component; Save Progress there is a screen action, so it saves without leaving the screen.
- Screen 2 carries the **Guest Details** repeater; rows start from the section's Prefill Template and come back to this section. A saved guest row the registrant removes goes back flagged Is Deleted, so it is deleted on save.
- `buttons: flow`: the section's own bar drives, so Back on screen 2 steps back to screen 1 and only screen 1's Back leaves the page.
- Audience guest: the flow requires permission to run; it reads no records beyond the Form Template, so no sharing rule is needed.

Before using it, build the two form components (build-form-component) under those names, or change the names in the spec.

## 3. A custom LWC inside a Flow Section (recipe)

When a step needs a widget no flow screen has, and that step sits among flow steps that need org data, place the custom component on the section's screen. If the widget is the whole section, put it straight in a Lightning Web Component page section instead (build-custom-lwc); a flow adds nothing there.

1. build-custom-lwc builds the component with the Flow Screen target: an input for what it needs (`{!record}`, or one value), and an output it updates with a flow attribute change event as the person works (for example `selectedPlotSize`).
2. Scaffold the section with a variable for the value (`"variables": [{"name": "Plot_Size", "type": "String", "description": "..."}]` and `"sets": [{"field": "Plot_Size__c", "value": "Plot_Size"}]`).
3. In the scaffolded screen, add the component above the buttons, named for what it asks (`Plot_Size_Picker`), with a description; bind its output to `Plot_Size` (or set `New_Values.Plot_Size__c` from `Plot_Size_Picker.selectedPlotSize` in `Assign_Outputs`).
4. If the screen must wait for the component to be valid, give the component a validate method that returns an error, so Next stays on the screen.
5. `flowsection.py check`, then the walk in SKILL.md step 8.

## 4. Packaged screen components inside a Flow Section (recipe)

The Flow Tool Kit screen components (the form, the repeater, the data table) work inside a Flow Section like anywhere else. Example: Example Food Bank's shift picker (`Form_Section_Shift_Picker`), which lists open shifts in a Flow Tool Kit data table and hands the chosen one back.

1. Scaffold with one screen, `"sets": [{"field": "Shift__c", "value": "Selected_Shift_Id", "review_object": "Volunteer_Shift__c"}]` and a variable `Selected_Shift_Id`.
2. Add `getOpenShifts` before the screen (Get Records on the shift object, Status equals Open, Start after today, the fields the table shows), with a description.
3. On the screen, add the **data table** component (`FlowToolKit:flowDataTable`): Object your shift object, a table form component on that object (build-form-component), Prefill Collection `{!getOpenShifts}`, Max Row Selection 1, Min 1.
4. In `Assign_Outputs`, set `Selected_Shift_Id` from the table's Selected Record (First Selected Row) Id before the `sets` line, or set `New_Values.Shift__c` from it directly.
5. Guests: a guest sharing rule on the shift object, read only, Status equals Open, plus field read for the columns shown (flow-access-fix proposes it). Never list shifts a guest must not see.
6. `flowsection.py check`, then the walk.
