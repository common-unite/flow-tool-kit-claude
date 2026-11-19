# Checkbox

A yes-or-no field in FlowToolKit's Boolean treatments: a toggle (the package default), a checkbox, an attestation card, or two labeled choices (dropdown, radios or joined buttons).

**Maps to:** a Checkbox field and its `booleanType__c`. Hand-written from `flowFormCheckbox`.

| `variant` | `booleanType__c` | Renders |
| --- | --- | --- |
| `toggle` | `default` | `lightning-input` type toggle. Off is `toggle-off`; on fills `brand` with the knob's check in `brand` |
| `checkbox` | `checkbox` | A 16px box with the label beside it. Checked fills `brand` with an `on-brand` check (the FlowToolKit override; stock SLDS draws a blue tick on white) |
| `attestation` | `attestation` | A consent card that is clickable as a whole. Unchecked on `surface-muted` with a `+` mark; checked gets a `brand` border on `brand-wash` and a filled check; a missing required answer turns the card `error-strong` on `error-wash` |
| `picklist` | `picklist` | A two-option dropdown, as `Picklist · standard` |
| `radio` | `radio` | Two radio circles |
| `radiobuttons` | `radiobuttons` | Two joined buttons, as `Picklist · radiobuttons` |

## Props
- `label`, `checked` / `defaultChecked`, `onChange(checked)`.
- `variant`: `toggle` (default), `checkbox`, `attestation`, `picklist`, `radio`, `radiobuttons`.
- `booleanLabels`: `booleanPicklistTypeOverride__c`, the label pair for true and false. One of `True/False`, `Yes/No`, `Active/Inactive`, `Enabled/Disabled`, `Valid/Invalid`, `On/Off` (the first label is true). It applies to:
  - `picklist`, `radio` and `radiobuttons`: the two option labels. Left blank (`default`), all three show True / False.
  - a positioned toggle (`labelPosition` left or right): the state text beside the switch. Left blank, it shows Enabled / Disabled.
  - The standard toggle, `checkbox` and `attestation` show no state text, so the override has no effect there.
- `labelPosition` (toggle only): `top` (default, label above), `left` (question left, switch right) or `right`. Mirrors `labelVariant__c` = `left` / `right`. Use `left` for a run of yes/no questions with long labels: stack them, and every switch lines up in one column on the right while the questions read down the left.
- `activeMessage` / `inactiveMessage` (positioned toggle only): replace the state text from `booleanLabels` with your own words. Design only; the package always uses one of the six pairs.
- `attestationTitle` (optional, bold first line) and `attestationText` (the consent statement): attestation only. Builds as `Label_Rich_Text__c` with `labelVariant__c` `none` (the wording inside the card, no label above it); never `helpText__c`, which is capped at 255 characters and renders under the card.
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
Consent and authorization belong in `attestation`. Keep the statement's exact legal wording; don't paraphrase it in a design.
