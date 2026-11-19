# Pitfalls

Each one with what you see and what to do. `flowsection.py check` catches the ones marked *checked*.

| Pitfall | What you see | What to do |
|---|---|---|
| **The template is never active** | The packaged template is not in the section's Flow picklist; a test or a section that names it runs nothing | Create your own flow from it (or scaffold one). *Checked*: a file still marked as a template is an error |
| **The flow is not active, or lacks an output** | The flow is missing from the Flow picklist | Activate it; keep `isValid`, `buttonClickedLabel` and `record`, each available for output. Reload the page after activating. *Checked* |
| **The form's cache of the flow's inputs** | You added `buttonTriggerName` or `section`, and the form still behaves as before (two bars, rows untagged) | **Reset Form Cache** in the Form Builder footer. The form caches which inputs a flow declares, per flow name |
| **The stale launch record** (before Flow Tool Kit 5.3) | Answers changed on another section go back to their old values after the section finishes | From 5.3 the form keeps only the fields that differ from the copy it passed in, so setting fields on `record` is safe. On earlier versions the whole launch copy goes back: set them on `New_Values` and assign `record = New_Values` last, which is safe on every version. *Checked* as a warning |
| **A section cannot clear a field** | Setting a field to blank in the section has no effect | The form drops blank values from the returned record. Clear it with a formula or rule on the form instead, or have the conversion handle it |
| **Back and Finish are routed by label** | Back submits the form, or Save Progress moves to the next page | Bind Back, Save Progress and the last screen's Finish to their `buttonLabel_` variables and return `buttonClickedLabel` exactly as received. A middle screen's Next may carry its own words. *Checked* |
| **Back carries half-finished edits** | Going back and forward again shows edits the person abandoned | On the first screen, Back must skip the outputs (the scaffold's Switch does) |
| **Two button bars** | The page's buttons and the section's both show | Declare `buttonTriggerName` and `hidePageButtons`, bind the buttons' Trigger Listener Name to `buttonTriggerName`, and add the hide formulas. *Checked* as a warning |
| **`recordId` is blank** | A Get Records by `recordId` finds nothing on a new form | A new submission has no Id yet. Read from `record`, which carries every earlier answer |
| **Duplicate value on External Id** | `duplicate value found: FlowToolKit__ExternalId__c` on the second Save Progress | Put the saved Ids back onto the record and rows after every mid-flow save (buttons-and-saving.md) |
| **Names differing only in case** | Deploy fails with "Duplicate developer name" (a screen named `Review` beside the `review` variable) | Flow names ignore case. The scaffold's review screen is `Section_Review`. *Checked* |
| **A rename missed a reference** | Deploys fine and fails at run time | Update connectors, references and every `{!...}` in formulas and text. *Checked* |
| **Guest reads need sharing** | The guest sees an empty list where staff see records | A guest sharing rule for the records meant to be public; system context only for one returned value, never whole records (access.md) |
| **The access message** | "You do not have the level of access necessary..." | The flow must require permission to run and be granted by the user's permission set: flow-access-fix. *Checked* for guest and portal audiences |
| **A decision with no outcomes** | Deploy fails: "Required field is missing: rules" | Remove the decision and connect straight through; the scaffold adds a Switch only where a button can end the section |
| **The sample form left in** | The section shows an organization's details form nobody designed | Replace the template's sample form and repeater with your own component, or remove them. *Checked* |
| **A required question on the first screen** | Back from the section's first screen does nothing while the question is blank | Back there is a Next, and Flow holds a Next on an empty required native input whatever the buttons say. Leave it not required and ask on the forward path (the scaffold's `Switch_<Screen>_Answers`, with a message under the question). *Checked* as a warning |
| **Removed rows come back** | A row the person removed is still there after the next save, or the record it converted to stays | A saved row left out of `relatedRecords` is never deleted. Keep it with `IsDeleted` true; the repeater's output and the scaffold already do. *Checked* as a warning |
| **A required input on a later screen and the page drives** | Continue seems to do nothing | The section's screen holds the person until the input is answered, which is right; make sure the error shows on that screen |
| **A hand edit of the section after a plan build** | The flow disappears from the section after the next rebuild | Put the flow name in `plan.json` and rebuild; build-template recreates sections from the plan |
| **A Flow Builder round trip** | After saving in Flow Builder the file differs (raw ids, removed outputs) | Open, save, retrieve and diff once before handing over |
| **The form's contract traps** | Back held by a required input, a spinner that never ends, a page click that runs two sections, a guest shown unsanitized fields, rows that never delete | The full list, each with its source in the package: [contract.md](contract.md), "Traps" |
