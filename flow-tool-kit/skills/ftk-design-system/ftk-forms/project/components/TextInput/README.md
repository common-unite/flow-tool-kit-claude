# TextInput

A single-line text field, drawn the way FlowToolKit renders a String field: `flowFormField` wrapping `lightning-input`, with the FlowToolKit label.

**Maps to:** a Text, Email, Phone or URL field with `stringType__c` = `standard`. Hand-written from `flowFormField` and `flowFormFieldLabel`.

## When to use
Short answers: names, emails, phone numbers, IDs. For more than a sentence use `TextArea`.

## Props
- `label` (string): the field label.
- `value` / `defaultValue` (string), `onChange(value)`.
- `placeholder` (string).
- `type`: `text` (default), `email`, `tel`, `url`, `number`.
- `required` (boolean): adds the outside asterisk. An empty required field shows "Complete this field." after it loses focus.
- `readOnly` (boolean): `displayType__c` = `READONLY`. Drawn as the disabled SLDS input (`surface-muted` fill, `label` text).
- `error` (string): forces the error state with this message.
- `helpText` (string) and `helpTextDisplay`: `Hover Bubble` (default), `Below Label`, `Below Field`.
- `labelSize`: one of the `slds-text-*` classes from `labelSize__c`. `labelHidden` hides the label but keeps it for screen readers.
- `maxLength` (number).
- `focused` (boolean): shows the focus state without interaction, for mockups.
- `prepend` / `append` (`prepend__c`, `append__c`): short text beside the input, such as `$`, `%` or `years`. Drawn as `.flow-form-affix`: 0.65rem, line-height 1.5, grey (`--slds-g-color-neutral-base-60`). Before and After sit on the bottom edge of the input box and stay there when an error or help line shows under the input. Package gap: `.flow-form-affix-row` uses `align-items: baseline`, which puts them on the input's text line instead; change it to align on the input's bottom edge to match.

## Options every field shares
Every field component (TextInput, TextArea, Picklist, Checkbox, NumberInput, DateInput, MultiPicklist, Lookup, Address, FormattedInput, RichTextInput, FileUpload, ImageUpload, SignaturePad) takes these `flowFormField` options. A field with none of them set renders exactly as before.
- `labelVariant` (`labelVariant__c`): `standard` (default), `label-stacked`, `label-inline` (label in a column left of the control, which stacks again under 500px of container width), `label-hidden`, `none` (no label and no label space). `inlineLabelWidth` (`inlineLabelWidth__c`) sets the label column, default 33%. **Not recommended for most forms:** inline labels squeeze long labels and the control, and they stack anyway on phones. Use them only for short, dense admin-style forms, and keep labels above the field everywhere else.
- `topMargin`, `bottomMargin` (`topMargin__c`, `bottomMargin__c`): an SLDS margin class.
- `alignCenter` (`alignAbsoluteCenter__c`).
- `plainText` (`viewAsPlainText__c`): the label over the value as text.
- `disableHelpText` (`disableHelpText__c`), `customValidationMessage` (`customValidationMessage__c`, shown when `error` is `true`).
- `labelRichText` (`Label_Rich_Text__c`): an HTML label with links or bold, common on consent questions.
- `prepend` / `append`: beside the input on TextInput, NumberInput (standard) and FormattedInput; under the options at either end on choice fields, like the ends of a scale.
## States
Default, focus (`brand` border plus `focus-ring`), error (`error` border plus `error-ring` and message), read only.

## What the consumer supplies
The label and copy, and the column span in the handoff. Width always comes from the 12-column grid, never from the input.
