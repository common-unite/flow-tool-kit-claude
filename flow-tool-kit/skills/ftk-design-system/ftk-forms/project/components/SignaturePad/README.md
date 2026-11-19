# SignaturePad

A box people sign in with a mouse, pen or finger.

**Maps to:** a Rich Text Area field with `richTextType__c` = `signaturePad`. Hand-written from `signaturePad` (stroke thickness 3, pen color black, as `flowFormField` sets them).

## Anatomy
An `slds-input` style box at least 200px tall. A light grey `utility:close` X and a 3px `#e1e1e1` signing line sit 20% up from the bottom. A `utility:refresh` button, mirrored, top right, clears the signature. Focus draws the `brand` ring; a missing required signature turns the box `error` with "Complete this field."

## Props
- `label`, `value` / `defaultValue` (a PNG data URL of the signature), `onChange(dataUrl)`; clearing sends an empty string.
- `strokeThickness` (default 3), `penColor` (default `black`), `minHeight`.
- `sample` (boolean): draws an example signature, for mockups.
- `readOnly`: shows the saved signature image with no box. `required`, `disabled`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`.

## Notes
The package saves the signature as an image in the rich text field. There is no typed-name or date option in the package; if a design needs a printed name or signing date, add them as their own TextInput and DateInput fields beside the pad.
