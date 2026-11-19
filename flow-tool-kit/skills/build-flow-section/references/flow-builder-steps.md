# Building a Flow Section by hand in Flow Builder

For when Claude Code is not available: in claude.ai chat, Claude designs the section and writes these steps for the person, filled in with the section's own names. The result matches what `scripts/flowsection.py scaffold` writes. Claude cannot do these clicks from chat; the person does them in Setup.

## Create it

1. **Setup, Flows, New Flow**, the **Templates** tab (All + Templates), choose **(Form) Flow Section | Template**, **Create**.
2. **Save As** a new flow: Label `Form Section | <What it does>`, API Name `Form_Section_<What_It_Does>`, and the description Claude wrote. Never edit or activate the template itself.

## Change the template's sample parts

3. On **Final Screen**: rename it for what it asks (`Choose_Primary_Contact` / "Choose Primary Contact"), and give it the description Claude wrote.
4. Replace the sample form (DemoFormCMP) and repeater (DemoRepeaterCMP): either point them at your own form components (Form, then the component's API name) or delete them and add the screen's own inputs (for a choice from records: a Radio Buttons or Picklist input with a **record choice set**, filtered by `{!record.<field>}`). Rename each component `<Screen>_Form`, `<Screen>_Rows` or for what it asks. **On the first screen, leave every native input not required** (Back there is a Next, and Flow holds it on an empty required input). To insist on an answer, add after the Switch's default outcome a Decision labelled Switch: when the input Is Null and `{!buttonClickedLabel}` does not equal `{!buttonLabel_SaveProgress}`, an Assignment turns on a Boolean variable and connects back to the screen, where a Display Text under the question, visible while that variable is true and the input is blank, asks for it.
5. If you deleted the form component, open the screen's **Save Progress** screen action and the triggers that run it, and remove them; Save Progress then finishes the section and the page saves.
6. Do the same on **Review Screen** (rename it `Section_Review`; never just `Review`, which clashes with the `review` variable): read-only copies of your forms with Review set to `{!review}`, or display text showing what the section set, by name.

## Hand back only what the section set

7. Create a record variable `New_Values` (Form Submission, not input, not output) with a description.
8. In **Assign Outputs**: first `New_Values` equals your form's Visible Fields output (if you kept a form), then one line per field the section sets (`New_Values.<Field>` equals your input), then `record` equals `New_Values` last. On Flow Tool Kit 5.3 and later a field set on `record` is also safe (the form keeps only changed fields); `New_Values` keeps the flow safe on every version.
9. Keep the second assignment (rename its label to "Set Clicked Label") and the **Switch** after the screen, with its Back outcome skipping Assign Outputs. Keep `relatedRecords` set from the repeater's output: a saved row the person removed is in it with Is Deleted true, so it gets deleted. If your own logic removes rows, set the row's Is Deleted to true and keep it in the collection instead of leaving it out.

## Buttons

10. On the buttons component: Trigger Listener Name `{!buttonTriggerName}`; labels bound to `{!buttonLabel_Back}`, `{!buttonLabel_SaveProgress}`, `{!buttonLabel_Next}`, `{!buttonLabel_Finish}`. Never type the Back, Save Progress or Finish label: the form routes the finish by them. Only a middle screen's Next may carry its own words.
11. To let the section's buttons drive the page, set the default value of `hidePageButtons` to true. Leave it false to let the page's buttons drive.
12. Several screens are easier from the scaffold in Claude Code: each screen needs its own buttons component (Back type **Back** after the first screen), its own assignment of the clicked label into `buttonClickedLabel`, and its own Switch. By hand, follow the two-step example in `../examples/` element by element.

## Finish

13. For a public or portal form: **Advanced**, "Override default behavior and restrict access to enabled profiles or permission sets". Then run flow-access-fix.
14. Add a description to every element and variable you added, then **Save** and **Activate**.
15. Point the page section at the flow (Customize on the section, Component Type **Flow**, pick the flow), and **Reset Form Cache** in the Form Builder footer.
16. Paste the flow's details back into the chat (or export it with Claude Code later) so Claude can check it; walk it in the form as SKILL.md step 8 says.
