# Buttons and saving

How to wire a section's buttons and Save Progress. Why each piece works the way it does, with the package source behind it, is in [contract.md](contract.md) ("The button handoff", "Save Progress and navigation").

## Choose who drives

| The flow | Who drives |
|---|---|
| Declares the text input `buttonTriggerName`, `hidePageButtons` false | The page. Its forward, Back and Save Progress run the section's buttons; forward validates the section, Back and Save Progress skip the Flow Tool Kit forms' validation. On several screens, forward moves one screen and Back steps back one; only the first screen's Back leaves the page. The section's own bar hides itself |
| Sets its output `hidePageButtons` to true | The section. The page hides its buttons on that page and the section's docked bar drives, finishing with the clicked label. It can be set at the start or changed on any screen. The review page always keeps its Submit |
| Neither | Both bars show (flows built before Flow Tool Kit 5.2) |

**Choose:** one screen, the page drives (the default). Several screens, or a Save Progress that must keep the person on their screen: the section drives (`"buttons": "flow"` in the spec). With the page driving, the page's forward button keeps the page's own words on every screen of the section (Submit, on the last page), while each click only moves one screen.

What makes it work, in each screen's Flow Tool Kit buttons component:
- **Trigger Listener Name** bound to `{!buttonTriggerName}`, so the page's clicks reach it; one listening buttons component per screen;
- Next and Finish hidden by `Hide_Docked_Buttons` (true while the page drives), Back by `Hide_Back_Button` (also true on the form's first page, where no Back label is passed), Save Progress by `Hide_Save_Progress_Button` (also true when the template does not allow it).

## Labels, screen by screen

| Screen | Back | Forward | Save Progress |
|---|---|---|---|
| First | Bound to `buttonLabel_Back`, type left as Next, skip validation on. It ends the section with the Back label and the page goes to its previous page (Return in Stages mode). Never type Back here: Flow has no earlier screen and would hide it | Next bound to `buttonLabel_Next` (or its own words, if this is not also the last screen) | Bound to `buttonLabel_SaveProgress` |
| Middle | Type Back: a real step back a screen | Its own words are fine: the form never sees a middle screen's label | Bound to `buttonLabel_SaveProgress`, with a Switch outcome that hands back the outputs and ends |
| Last | Type Back (or as the first screen, when it is the only screen) | Finish bound to `buttonLabel_Finish`, which carries the page's forward label, so the last screen matches the page | Bound to `buttonLabel_SaveProgress` |

The form learns only `buttonClickedLabel` when the section finishes, and compares it with the labels it passed in: the Back label goes back, the Save Progress label saves and stays, anything else moves forward (submits on the last page). So a typed Back or Save Progress label always counts as forward, and a Back that hands back its outputs carries half-finished edits into the form. The scaffold puts a Switch after each screen where a button can end the section:
- **first screen**: Back ends the section without assigning outputs;
- **any screen but the last**, with Save Progress on: Save Progress assigns the outputs and ends the section;
- otherwise the next screen, and after the last screen `Assign_Outputs`.

Every path that finishes sets `buttonClickedLabel` from the buttons component's output: a finish without it is ignored by the page, and the person is left on a spinner.

**The first screen's Back must never be held.** Back there is a Next under the hood. Flow Tool Kit form components on the screen skip their own checks for it (and a repeater does when the section drives), but the Flow runtime holds a Next on any empty native input marked required, whatever the buttons component says. So, by default, the first screen's native inputs are not required in Flow, and the scaffold checks them on the forward path instead:
- the Switch after the screen ends the section on Back first;
- its forward path goes to `Switch_<Screen>_Answers`, which skips Save Progress and sends a blank answer to `Set_<Screen>_Answer_Missing`;
- that assignment turns on `<Screen>_Answer_Missing` and returns to the screen, where `<Pick>_Required_Message` shows under each unanswered question (the spec's `required_message`, or "Answer this question to continue.").

Later screens keep native required inputs: their Back is a real Flow Back, which never validates.

## Save Progress

Two ways, chosen per screen by the scaffold:
- **Beside a Flow Tool Kit form component: a screen action.** The Save Progress button is an Action button; clicking it stamps the click time, and the screen runs the packaged save flow (`FlowToolKit__Form_Submission_Upsert`, inputs `record` from the form's visible fields, `relatedRecords` from the repeater when it is on the same screen, `stage`, `SaveProgress` true, `LastTriggeredDateTime` from the click). It runs only when no save is in progress and the click is newer than the last completed save, so double clicks save once. The person stays on the screen. The saved record goes back into the form component through its Transformation Record input, so the form shows what was saved. This is the section's own button: when the page drives, the page's Save Progress arrives as a Next with the Save Progress label and ends the section through the Switch instead.
- **On any other screen: finish and let the page save.** The button carries the Save Progress label, the Switch hands back the outputs and ends the section, the page saves, and the section starts again (at its first screen) with the saved values.

**Hand saved Ids back.** Any step that saves mid-flow must put the returned Ids back onto what it saves next time: `record.Id`, and each row's Id in `relatedRecords`. The form stamps a unique upsert key on every row; a second save of a row that still has no Id is an insert, and the database refuses it with `duplicate value found: FlowToolKit__ExternalId__c`. The screen action above does this for the record. If your flow saves rows itself, add an Assignment after the save that copies the saved rows (the save flow's `upsertedRelatedRecords` output) back onto your rows collection.

## Removing rows

A row the person or the flow removes goes back flagged, never just left out. A saved row (it has an Id) stays in `relatedRecords` with `IsDeleted` true, so the save and the conversion delete it; a row with no Id was never saved and is simply dropped. The repeater's `prefillRecords` output already does this, and the scaffold hands it back unchanged. In your own logic (a loop that removes rows the person unticked, say), flag before you leave a row out:

```xml
<assignments>
    <description>Flags a saved row the person removed, so the save and the conversion delete it; a row left out of the collection would stay as a child of the submission.</description>
    <name>Flag_Removed_Row</name>
    <label>Flag Removed Row</label>
    <assignmentItems>
        <assignToReference>Loop_Rows.IsDeleted</assignToReference>
        <operator>Assign</operator>
        <value><booleanValue>true</booleanValue></value>
    </assignmentItems>
    <assignmentItems>
        <assignToReference>Rows_To_Return</assignToReference>
        <operator>Add</operator>
        <value><elementReference>Loop_Rows</elementReference></value>
    </assignmentItems>
</assignments>
```

`flowsection.py check` warns when `relatedRecords` is set from anything but the repeater's output, or shrunk with a Remove operator, and nothing sets `IsDeleted` true.

## Several screens in one section

- Name each screen for what it asks; the progress indicator at the top shows the step.
- Only one screen carries the record's form component (each form hands back only its own visible fields). Put other questions on that screen, or ask them with plain screen inputs and set the fields on `New_Values`.
- Only one screen carries rows.
- Assign `record` and `relatedRecords` only on the forward finish: the form reads them on every new screen, so an earlier assignment reaches the form before the person finishes, and Back cannot take it back.
- With the page driving, Save Progress restarts the section at its first screen; that is why several screens usually let the section drive.
