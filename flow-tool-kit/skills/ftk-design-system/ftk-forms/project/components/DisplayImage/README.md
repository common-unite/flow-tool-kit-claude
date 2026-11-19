# DisplayImage

A full-width picture on a form page, optionally tinted, with text over it, or as a parallax background.

**Maps to:** the `displayImage` component (Display Image in a section or on a Flow screen). Hand-written from `displayImage`.

## Props
- `src`: the picture. In the package this is `contentAssetName` (a Salesforce Content Asset) or `customImageLink`. `alt` text for people using screen readers. Draw with the packaged photos in `assets/Backgrounds` (the file name is the Content Asset API name), as the previews do, rather than a placeholder.
- `imageStyle`: CSS for the picture, as the package takes it, for example `height:220px; object-position:center bottom`. The picture always fills the width and crops to fit (`object-fit: cover`).
- `overlayHexColor` and `overlayOpacity` (0 to 1): a tint over the picture. With no color the tint is the `brand`.
- `customRichText`: the section's rich text (`richText__c`) laid over the picture. Its colors come from the rich text itself, so set white text in the editor when the tint is dark. Children work too.
- `overlayMode` (`viewAsPlainText__c`, the View As menu under the section's rich text in Form Builder):
  - `richtext` (View as Rich Text, the default): the text sits centered over the picture with 1rem padding (`slds-p-around_medium`).
  - `html` (View as Plain Text): the admin writes HTML in a plain text box, and it fills the whole picture (full height, no padding). The HTML sets its own layout, such as a headline pinned to the bottom left.
- `parallax` (`imageParallax__c`, the Parallax toggle on an image section): draws the picture as a fixed background (`background-attachment: fixed`, at least 100px tall) that the page scrolls over. Set its height with `imageStyle`, for example `min-height:200px`. The package sizes the picture to the section width plus 10%, centered in the browser window, so pick a picture that reads well at any slice. A landscape photo is only about half the section width tall, so in a tall window the section can scroll past the picture's edge and show a blank band; keep a parallax section near the middle of the page. Overlays and rich text work on top of it too.
- `topMargin` / `bottomMargin`: SLDS margin classes, for example `slds-m-top_medium`, `slds-m-bottom_large`.

## Notes
Text over a picture needs a tint dark enough to reach 4.5:1 for white text; navy (`#032d60`) at 0.55 or more works on most photos. Parallax is decorative: keep it out of forms people fill in on phones, where fixed backgrounds often don't hold.
