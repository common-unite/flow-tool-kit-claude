# Lookup

A lookup (reference) field: search for a record, pick it, and see it as the record's icon and name in the box.

**Maps to:** a Lookup field rendered by `flowFormField` through `lightning-input-field`, with `referenceFieldOverrideType__c` and `enableCustomLookup__c`. Hand-written from `flowFormField` and `flowFormLookup`.

| `variant` | Configuration | Renders |
| --- | --- | --- |
| `standard` | `referenceFieldOverrideType__c` = `standard` | The Salesforce lookup: "Search Accounts..." with a search icon; results show the object icon, the name (match in bold) and a secondary line |
| `customSearch` | `enableCustomLookup__c` = true (**Flow screen only**) | The same box with a `brand` search button beside it that opens the FlowToolKit lookup table in a modal (`customLookupHeader__c`, `customLookupSubheader__c`), plus a clear button |
| `recordpicker` | `referenceFieldOverrideType__c` = `recordpicker` | `lightning-record-picker`, which looks the same; the package also picks it for users who can update but not create the lookup |

## Props
- `label`, `options` (`{label, value, sublabel, icon}`), `value` / `defaultValue` (the record Id), `onChange(value)`.
- `variant`: see the table. Default `standard`.
- `objectLabel` (singular, e.g. `Account`) and `objectIcon` (any SLDS icon, default `standard:account`). The placeholder defaults to "Search Accounts...".
- `allowNew` and `newButtonLabel` (default `New`): the "+ New Account" action at the bottom of the results.
- `open` (boolean) and `searchValue`: show the results open, filtered, for mockups.
- `placeholder`, `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
The other overrides, `component` (an inline Form Component for the referenced record), `startnewform` and `vieweditsubmission`, replace the lookup with a nested form, so design them as sections. Selected records always show the object's own icon and color.

## Custom search (Flow screen only)
The custom lookup override works only when the form runs inside a Flow screen; a Form Template form cannot use it, so template designs use `standard` or `recordpicker`. With `enableCustomLookup__c` the search opens a results table with `customLookupHeader__c` and `customLookupSubheader__c` over it. Draw that table with `LookupSearchTable`.

Not drawn: the lookup overrides that start a new form or view and edit a submission (`referenceFieldOverrideType__c` = `startnewform`, `vieweditsubmission`).
