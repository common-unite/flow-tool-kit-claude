# DateInput

A date, time or date and time field, drawn as `lightning-input` with its calendar or time list.

**Maps to:** a Date, Time or Date/Time field (`flowFormField` drawing `lightning-input` type date, time or datetime), with `minDateType__c` / `maxDateType__c` limits.

| `type` | Renders |
| --- | --- |
| `date` (default) | A box with `utility:event`. Opens the SLDS datepicker; the chosen day is a `brand` circle, today is bold on `surface-muted`, days outside min and max are disabled |
| `time` | A box with `utility:clock` and a 15-minute list (8:00 AM to 6:00 PM in the preview) |
| `datetime` | Date and Time sub-inputs side by side under one label, as Salesforce draws them |

## Props
- `label`, `value` / `defaultValue` (ISO: `2026-10-24`, `14:00`, or `2026-10-24T14:00`), `onChange(iso)`.
- `type`: see the table.
- `min`, `max` (ISO dates): the resolved limit. In the package these come from `minDateType__c` / `maxDateType__c` (`specificDate`, `today`, `fieldValue`, `specific` with before or after). Say which in the handoff, for example "min: today".
- `today` (ISO): pins today's date for a mockup.
- `open` (boolean): shows the datepicker or time list open.
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
Dates display as "Oct 24, 2026" (the en-US Salesforce default); the real field follows the user's locale.
