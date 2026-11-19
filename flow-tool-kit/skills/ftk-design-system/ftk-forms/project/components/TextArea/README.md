# TextArea

A multi-line text box, drawn the way FlowToolKit renders a long text answer: `lightning-textarea` with the package's character counter under its right edge.

**Maps to:** a String field with `stringType__c` = `textarea`, or a Long Text Area field with `longTextType__c` = `default`. Hand-written from `flowFormField` (`.textAreaCount`).

## When to use
Descriptions, notes and anything longer than a sentence. For essay questions (a narrative, a statement of need, "tell us about..."), set `minHeight` so the box is sized to the answer you expect.

## Props
- `label`, `value` / `defaultValue`, `onChange(value)`, `placeholder`.
- `maxLength` (number): turns on the counter. The counter reads `typed / max` once something is typed, in `field-counter` at 50% opacity, and hides when read only.
- `minHeight` / `maxHeight` (CSS length): mirror `textAreaMinHeight__c` and `textAreaMaxHeight__c`. Admins set a minimum height for essay-style questions: the taller box lets people see their whole answer and signals that a full response is expected. Typical values are 150px to 300px.
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
The box resizes vertically only. The counter sits 20px below the box, so leave that space under a text area in a layout.
