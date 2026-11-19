# The section spec

`scripts/flowsection.py scaffold` reads one JSON file per Flow Section. Keep it beside the form's other files (`_forms/<slug>/flow-sections/<api_name>.spec.json`), so the flow can be rebuilt and reviewed. Two complete specs are in [../examples/](../examples/).

```json
{
  "api_name": "Form_Section_Household_Contact_Picker",
  "label": "Form Section | Household Contact Picker",
  "description": "What it does, where it runs, what it hands back, what to edit to change it.",
  "audiences": ["portal"],
  "buttons": "page",
  "save_progress": true,
  "screens": [
    {
      "name": "Choose_Primary_Contact",
      "label": "Choose Primary Contact",
      "description": "What the screen asks and why.",
      "form": "My_Form_Component",
      "rows": "My_Rows_Form_Component",
      "picks": [
        {
          "name": "Household_Contacts",
          "label": "Who is the primary contact for this application?",
          "help": "Optional help under the question.",
          "object": "Contact",
          "display_field": "Name",
          "value_field": "Id",
          "sort_field": "LastName",
          "filters": [{"field": "AccountId", "reference": "record.FlowToolKit__Account__c"}],
          "control": "RadioButtons",
          "required": true,
          "required_message": "Pick the primary contact to continue.",
          "description": "Which records are listed, and who can see them."
        }
      ]
    }
  ],
  "sets": [
    {"field": "FlowToolKit__Contact_1__c", "value": "Household_Contacts", "review_label": "Primary contact",
     "review_object": "Contact", "review_field": "Name"}
  ],
  "variables": [
    {"name": "Seats_Left", "type": "Number", "description": "What it holds and who sets it."}
  ]
}
```

| Key | Rule |
|---|---|
| `api_name`, `label` | `Form_Section_<What_It_Does>` and `Form Section | <What it does>`; 80 characters at most |
| `description` | Required. The flow's description, to the documentation standard |
| `audiences` | Any of `guest`, `portal`, `internal`. Guest or portal makes the flow require permission to run |
| `buttons` | `page` (default): the page's buttons drive. `flow`: the section's own buttons drive |
| `save_progress` | Default true. Adds the Save Progress button (hidden when the template does not allow it) |
| `screens[].name`, `label`, `description` | One screen each, in order. `Pascal_Snake`, no `_Screen` suffix |
| `screens[].form` | A Flow Tool Kit form component on Form Submission, by API name. At most one screen. Its visible fields are handed back, and Save Progress on that screen is a screen action |
| `screens[].rows` | A form component for repeater rows. At most one screen. Rows start from the section's Prefill Template; a saved row the person removes goes back with `IsDeleted` true so it is deleted |
| `screens[].picks[]` | A required single choice from records (a record choice set): `object`, `display_field`, `value_field` (default `Id`), optional `sort_field`, `filters` (each `field` with `reference` to a flow resource or a fixed `value`, `operator` default `EqualTo`), `control` `RadioButtons` (default) or `DropdownBox`, `required` (default true), `required_message` (optional). On a later screen `required` marks the input required in Flow. **On the first screen** the input is never required in Flow, because Back there is a Next and Flow would hold it; a required pick is asked for on the forward path instead (`Switch_<Screen>_Answers`), with `required_message` (default "Answer this question to continue.") under the blank question ([buttons-and-saving.md](buttons-and-saving.md)) |
| `sets[]` | Each Form Submission field the section sets: `field` (API name, with the package prefix for packaged fields) and `value` (a pick's name or a variable). `review_object` and `review_field` make the review show that record's name instead of its Id |
| `variables[]` | Extra variables you will set in elements you add: `name`, `type` (Flow data type, default `String`), `object` for records, `collection`, `description` |

A spec must return something: a `form`, `rows`, or at least one `sets` entry.

Options: `--namespace` (default `FlowToolKit`, the package prefix in every org that installed it), `--api-version` (default the package's own, 68.0), `--draft` to write the flow as Draft, `--force` to overwrite an existing file (retrieve the org's copy first).
