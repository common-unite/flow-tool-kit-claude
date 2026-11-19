# FileUpload

A field that collects one or more files, drawn as Salesforce's file selector with each uploaded file in its own shaded box.

**Maps to:** a Long Text Area field with `longTextType__c` = `fileUpload`. Hand-written from `formFieldFileUpload` (`lightning-file-upload`) and `formFieldFileUploadDetail`.

## States
- **Empty:** the label, then a dashed drop zone with an **Upload Files** button (`utility:upload`, `brand` text) and "Or drop files". Required and missing turns the zone `error` and shows "Complete this field."
- **Uploaded:** each file sits in a `surface-muted` box with a 1px `border`, its doctype icon (pdf, excel, word, ppt, image, csv, zip, html, xml, txt, unknown, picked from the mime type), the file name trimmed to 36 characters, and a remove `utility:close`. Files run two to a row, one per row on narrow screens.
- **Single file** (default): once a file is in, the selector hides. **Multiple** (`uploadMultipleFiles__c`): the selector stays until `max` files are in.

## Props
- `label` (default "Upload File"), `value` / `defaultValue`: an array of `{ name, mimeType }`, `onChange(files)`.
- `multiple`: `uploadMultipleFiles__c`. `max`: the most files allowed with `multiple`.
- `acceptedFormats`: `acceptedFormats__c`, semicolon separated, for example `.pdf;.png;.jpg`.
- `fileNameFormat`: `fileNameFormat__c`; `{{label}}` and `{{filename}}` are replaced at upload.
- `preventFileDeletion`: `preventFileDeletion__c`, hides the remove button. `disablePreviewLink`: `disablePreviewLink__c`, shows names as plain text instead of links.
- `required`, `readOnly` (lists files, no upload or removal), `disabled`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`.

## Notes
Guest users and embedded forms upload with a guest token and never get preview links; design those file names as plain text (`disablePreviewLink`). The preview's Upload Files button really opens your file picker, but nothing leaves the browser.
