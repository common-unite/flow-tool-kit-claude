# MultiPicklist

A field that takes several answers, as checkbox columns, buttons, badges, a searchable dropdown or a dual listbox.

**Maps to:** a Multi-Select Picklist field and its `picklistType__c`. Hand-written from `flowFormMultiselectCheckbox`, `comboBox` and `lightning-dual-listbox`.

| `variant` | Renders | Use it for |
| --- | --- | --- |
| `multiselectcheckbox` (default) | FlowToolKit checkboxes, wrapped or in columns. Checked fills `brand` | Most multi-select questions |
| `selectallmultiselectcheckbox` | The same, plus a bold Select All entry | Long lists where "all of these" is common |
| `separatedbuttons` | Separated buttons; each selected one is a `brand` fill | Short options like days of the week |
| `multiselectbadge` | `slds-badge` pills, bold 12px; selected are `brand` with `on-brand` text | Interests and tags |
| `combobox` | A searchable dropdown showing "N Option(s) Selected", selected options carry `brand` checks | Long lists in tight space |
| `visualpicker` | Visual picker boxes (icon only, label on hover); several can be selected | A few recognizable options |
| `standard` | `lightning-dual-listbox` with `disable-reordering`: "Available" and "Chosen" lists (labels `Available`, `Chosen`), with the two move buttons stacked at the top of the middle column, as SLDS `slds-dueling-list` places them | Staff-facing forms; avoid on public forms |

## Props
- `label`, `options` (strings, or `{label, value}`; `icon` for `visualpicker`), `value` / `defaultValue` (array), `onChange(values)`.
- `variant`: see the table.
- `columns`: `picklistColumnsSize__c` (1 to 12) for checkboxes, separated buttons and visual picker. Two to four columns suit most checkbox lists on a desktop form. In the package each option gets `slds-size_1-of-N` with the same large and medium size plus `slds-small-size_1-of-1`, so the columns hold from 768px up, drop to one per row between 480px and 767px, and keep N columns again below 480px. `grow` lets options take their own width.
- `max`: the most answers allowed. A "2 of 2 selected" line appears, and the rest are disabled once it is reached.
- `open` (`combobox`): shows the list open. `placeholder` (`combobox`).
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Exclusive answers: "None of the above"
Some values are exclusive. Selecting one clears every other answer and disables the rest until it's unchecked. The values are `None of the above`, `None`, `Prefer not to say`, `Prefer not to answer`, `Prefer not to disclose`, `Not applicable` and `N/A`, matched on the stored value (not the label) in any letter case.
- To use it, make sure one of those values is among the field's options. If the field uses `picklistOptionOverrides__c` (Picklist Option Overrides, the ordered list of included values), the exclusive value has to be in that list too, or it won't show.
- The rule is on the value, so relabeling it with `picklistOptionLabels__c` (for example to "I don't need any of these") keeps the behavior.
- `All of the above` works the other way: it selects every non-exclusive option.
- When an exclusive option is present, `selectallmultiselectcheckbox` leaves out its Select All entry (it also drops Select All when `max` is set). Select All never selects the exclusive value.
- It applies to every variant except `standard` (the dual listbox).

## Notes
Salesforce stores the answers as one semicolon-separated value. Keep option labels short; long labels break badge and button rows.
