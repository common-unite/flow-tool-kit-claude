# ImageUpload

A single picture field: an image picker that turns into a file card once a picture is chosen, with a preview window to review or remove it.

**Maps to:** a Rich Text Area field with `richTextType__c` = `imageUpload`. Hand-written from `imgUpload`.

## States
- **Empty:** a full-width dashed drop zone (at least 50px tall) with **Upload Files** and "Or drop files". Accepts png, jpg and jpeg.
- **Chosen:** an SLDS file card with a drop shadow: the picture in a 16:9 crop and a `surface-muted` title bar with `doctype:image` and the file name.
- **Preview:** clicking the card opens a modal headed by the file name, with **Return** (`action:back`) and a destructive **Remove Image** (`action:delete`) that clears the field.

## Props
- `label`, `value` / `defaultValue` (an image URL or data URL), `fileName`, `onChange(src)`.
- `open` (boolean): draws the preview window open, in place, for mockups.
- `required`, `readOnly`, `disabled`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`.

## Notes
The package compresses the picture to at most 600px on its long side (smaller inside a repeater) and stores it in the rich text field, so it is for photos, not documents. Use `FileUpload` for documents or several files.
