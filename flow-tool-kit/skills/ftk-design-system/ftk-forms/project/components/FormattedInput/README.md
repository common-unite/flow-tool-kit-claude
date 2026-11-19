# FormattedInput

Phone, email and website fields with Salesforce's format checks.

**Maps to:** Phone, Email and URL fields drawn by `flowFormField` as `lightning-input` type `tel`, `email` and `url`, with `phoneMask__c` for phones. Hand-written from `flowFormField`.

| `type` | Renders |
| --- | --- |
| `phone` | Digits are formatted as you type by `phoneMask__c`; the placeholder shows the mask with `#`. A number that doesn't fill the mask shows "Format: (xxx) xxx-xxxx" |
| `email` | "You have entered an invalid format." for a malformed address |
| `url` | Placeholder `https://`, the same invalid-format message |

`phoneMask__c` values: `(xxx) xxx-xxxx` (default), `xxx-xxx-xxxx`, `xx xxxx xxxx`, `xxxx xxx xxx`, `none`.

## Props
- `type`: `phone` (default), `email`, `url`. `phoneMask`: see above.
- `label`, `value` / `defaultValue`, `onChange(value)` (the formatted value).
- `placeholder`, `maxLength`, `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.
