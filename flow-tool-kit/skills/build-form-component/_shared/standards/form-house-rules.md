# House rules for Flow Tool Kit forms

Defaults for every form: apply them on the first run, and depart from one only when the person asks or the source gives a clear reason, saying so in the plan's notes. The form-type rules (header, buttons, indicator, first page) are in [form-type-rules.md](form-type-rules.md).

## Structure

- **Keep the source's page structure.** A one-page source stays one page. Offer a different structure as a question, never as the design.
- **Keep the source's blocks.** Each block in the source (a fieldset, a titled text block, a consent) is its own page section with its own title. Combine two only when it adds real value, and say why. Unrelated blocks (a photo request and an emergency text opt-in) never share a section.
- **One block, one page section.** Each framed block is its own page section with its own frame, title and icon, so an admin edits it in one place and the build makes it a separate section.
- **One consent, one section.** Its text goes in the section's rich text above the choice, never in help text under the field, which renders too small.
- **A form of consents and terms closes with the electronic signature**, even when the source records agreement only by submitting: a last Signature section with Printed Name (`Electronic_Signature_Print__c`), Date (`Electronic_Signature_Date__c`) and the signature pad (`Electronic_Signature__c`). When the source signs with a typed name, add the pad and the date under it in the same section. Note it as an addition in the plan's notes.
- **A follow-up question sits right under the field it qualifies.** If that field is in a shared block, the follow-up gets its own clean section right after the block, with no header, the source's question as the section text and the source's own option label.
- **Every source text block stays on the form**, the closing "what happens next" block too; never move one to the confirmation message.

## Words

- **Use the source's own words, in full**: instructions, notes and long labels word for word. Leave out only a line the rebuild makes untrue (a date-format note above a date picker), and say so.
- **Legal and policy text keeps the source's formatting**: headings, numbering, indented items, underlines and blank lines, inside a 16px body.
- **No em-dashes in copy.** Use a colon, a comma or a new sentence.
- **Rich text a respondent reads is 16px or larger**, set inside the rich text itself (`<p style="font-size: 16px; line-height: 1.5">`, the same on `<li>`). The stored copy is scaled by the form's Text size (24px at 150%), because the package's font scale reaches labels and inputs but not an inline size; draw_plan.py does this.
- **Dividers carry a title, a subtitle that explains the next block, and an icon.** Leave out a divider with nothing to say.

## Frames and headers

- **Every section that holds fields has a frame** (`box`). `clean` is only for a headerless section: a follow-up, a lone question on a highlight bar, or a standalone note on a highlight bar.
- **Framed sections use the Outlined header** (title on the border), the icon at the large size, transparent behind it.
- **Inside a frame:** 20px from the border to the fields and header text, even left and right, 24px under the last field; title, subtitle and fields share one left edge.
- **Section frames sit 68px apart**, border to border: Top Margin `xx-large` on every page section and Bottom Margin `none` (a bottom margin lands inside a framed section, under its last field).
- **A question with a long label, or a note that stands alone, may go without a section header**: the source's text in the section text, the field's label hidden. A note uses the rich text `highlight` variant (a brand bar on the left), never an info message card.
- **One field under the section's own text hides its label** (`label-hidden`); the label stays for screen readers. A plain checkbox keeps its label, which is the option beside the box.
- **Two long questions, two sections**, each with its paragraph as the section text and the label hidden.
- **Icons are always `utility:` icons**, never `standard:`, `custom:`, `action:` or `doctype:`, and not the same icon on neighboring sections.

## Controls and widths

- **Width fields by their expected answer**: first name narrower than last name, email wider than phone. Phones span 12. A field whose label runs more than a few words, and any choice under it, spans 12.
- **Addresses use the Address component** (it has address search), never separate text fields, for every address, a second one too. On Text address fields the canvas draws no country list. Every address is its row and all five parts, Country included: the package draws one blank box for an address missing a part.
- **Use pickers that enforce the rule** rather than the source's workaround (a Primary/Alternate checkbox grid becomes a required primary choice plus an optional alternate).
- **Counts use the number stepper. Money uses currency;** calculated amounts are read-only with the rate in help text.
- **Joined radio buttons only for short option sets.** **Multi-select options stack one per row.**
- **An answer that may run past one line** (allergies, medications, accommodations) is a text area.
- **One photo uses Image Upload** (a Rich Text Area field with the image upload type; `Contact1_Profile_Photo__c` is the packaged home for a person's photo). File Upload is for documents or several files.
- **Draw only what the live form shows, in the state it opens in**: an image upload empty, a signature pad blank, a picker unchosen. Every setting on the canvas must exist in the package, or the plan marks it a gap.

## Style

- **Inputs need edges people can find**: Style Editor Borders `#8A8A8A` and Border thickness 150% on every first run. Section frames keep their brand border through the section tokens, so this changes inputs only.
- **Text and inputs at 150%, field spacing 125%** unless the brand kit says otherwise.
- **Templates keep the default theme.** The brand goes in Form Style values, never a new Form Theme record.
- **Sample images come from the package's photos** (the design system's `assets/`), never an empty image slot or an outside photo; the organization's own photos replace them once chosen. The canvas shows an image only as an upload to the canvas.

## The banner is the template header

Every form gets a banner in the Form Template header, not a logo row and not a page header repeating the title. It carries the form's title and a one-line subtitle in the organization's voice, up to three tags (season, time to complete, audience), a background photo with a scrim so the text stays readable, and the logo on a white card at the right.

- **Single-page form:** layout Compact, height Small, placement `singleCardHeader`, unless the person asks for another.
- **No vertical indicator** (one or two pages, or three or more with the base indicator): the banner sits flush on the form card with square bottom corners, placement `singleCardHeader`.
- **Vertical indicator or stages mode:** Overlay at Small height, placement `header`, rounded on all corners; the scrim is the brand color, with one or two tags.
- **Split** only for a very simple title, never the default. Medium and Large only for a form that features its photo.
- The banner does not show on the confirmation or inactive screens (package behavior), so the canvas does not draw it there.
