# RichTextInput

A formatted-text answer: `lightning-input-rich-text` with its toolbar.

**Maps to:** a Rich Text Area field (`richTextType__c` = `standard`), drawn by `flowFormRichTextInput`, with `RichTextFormats__c` and `enableRichPlainTextToggle__c`. Hand-written from `flowFormRichTextInput` and `flowFormField`.

## Props
- `label`, `value` / `defaultValue` (HTML), `onChange(html)`, `placeholder`.
- `formats`: the toolbar, from `RichTextFormats__c` (semicolon list in the package). Default `font, size, color, bold, italic, underline, list, indent, align, link, image, clean`. Font and size always come together; strikethrough is never offered.
- `plainTextToggle` (`enableRichPlainTextToggle__c`): set in Form Builder on a Rich Text Area field whose Rich Text Display is Default, with the "Plain Text" toggle beside the toolbar formats ("When enabled users can toggle between plain and rich text input"). Not offered for Signature Pad or Image Upload. It adds the "View as Plain Text / View as Rich Text" switcher above, and the toolbar moves to the bottom. `toolbarPosition` (`top` | `bottom`) sets it directly.
- `minHeight` / `maxHeight` (CSS length): the same `textAreaMinHeight__c` and `textAreaMaxHeight__c` settings as TextArea, applied to the editing area. Use a minimum height for essay-style answers so people can see everything they write and know a full response is expected. Admins set these in Form Builder (Min Height / Max Height show for Rich Text Area fields), and the package applies them through the SLDS textarea sizing hooks, which `lightning-input-rich-text` reads for its editing area. Without them the area starts at 6rem and scrolls past 15rem; a minimum taller than 15rem still wins. Plain-text view starts at 146px, as in the package.
- `font`, `fontSize`: the labels on the font menus (default Salesforce Sans, 12).
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`.

## Notes
`richTextType__c` = `signaturePad` and `imageUpload` turn the same field into a signature pad or an image upload; see those components. The toolbar buttons here toggle their pressed state but don't format text.
