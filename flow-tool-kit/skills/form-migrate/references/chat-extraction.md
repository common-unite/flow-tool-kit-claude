# Reading a form in chat, without scripts

Use this when the session cannot run this skill's scripts: claude.ai chat with code execution off, or a sandbox that cannot reach the form's address and has no saved copy. Use it too for any source no script reads: screenshots, phone photos of a paper form, a builder's preview. Claude is the parser. The result is the same as the scripts' result: a list the person confirms, then a `capture.json` for the manual adapter, with every claim's source stated.

If code execution is on, prefer the scripts: get the page or PDF into the sandbox (an upload, or the page saved by the person) and run them. Use this page for whatever the scripts cannot reach.

## 1. Get the source in

| Source | How |
|---|---|
| FormAssembly link (`tfaforms.com/<id>`, or an instance's `tfaforms.net` address) | Fetch the address with the session's web fetch. If the result shows HTML attributes (`id="tfa_12"`, `data-condition=`), read the markup. If it shows only rendered text, read what it shows, and ask for the saved page to capture the rest (step 4) |
| Google Form link (`docs.google.com/forms/...`) | Fetch the address. A fetch usually returns only the first section's text. The saved page source holds the whole form as data (`FB_PUBLIC_LOAD_DATA_`); if the fetch returns it, read it (positions below). Otherwise read the first section and ask for the saved page or a screenshot of each section |
| PDF | Read the uploaded PDF directly. Note whether it has fillable fields (boxes you can type in) or is flat |
| Word document | Read the uploaded document directly; tick boxes, drop-downs and text boxes in it are questions |
| Screenshots or photos | Ask for one image per page or section, in order, including the bottom of long pages. Read them as in [Reading from images](#reading-from-images) |
| Any other builder (Microsoft Forms, Jotform, Typeform, Wufoo, Cognito Forms and so on) | The builder's preview or its question export when the person can get one; otherwise a screenshot of each page. Its address usually returns no questions to a fetch, because the form is drawn by script |

Ask for the saved page this way: "Open the form in a browser, choose Save Page As, Web Page HTML only, and upload the file here." Nothing more.

## 2. Read every question

Read the whole source before writing anything. Keep the source's own words, typos included; note a suspected typo, never fix it.

### FormAssembly markup

| Marker | Means |
|---|---|
| `<fieldset>` and its `<legend>` | A section; nested fieldsets give the section path |
| `fieldset` with class `repeat` and `data-repeatlabel="..."` | A repeating section; the label is the add-another button text |
| `id="tfa_N"` on an `input`, `select`, `textarea`, or on the `span` or `table` wrapping a choice group | The question's id. Choice groups put the question id on the wrapper and each choice's id on its `input` |
| `<label for="tfa_N">` | The question text |
| `option` or `input type="radio"`/`"checkbox"` with its own `id="tfa_M"` | One choice, with its id |
| class `required` on the input or on its choice wrapper | Required. Read the wrapper too: the input may not say so |
| class names such as `validate-email`, `validate-date`, `validate-integer`, `validate-currency` | The real type. FormAssembly draws nearly every input as `type="text"`, so text alone means "unknown" |
| `data-condition="..."` | A show-and-hide rule on that element. Count with this exact attribute: `data-conditionals` is a different attribute (the list of elements a choice controls) |
| `formula=(...)` inside a class, and `calc-<name>` | A calculation and its variable name |
| `<div class="htmlSection" id="tfa_N">` | A text block (release, policy, instructions). Keep its formatting |
| `<script>` blocks inside the form | Custom scripts: list each, with what it seems to do |
| `<form action="...">` | Where the answers go. A Salesforce connector exists behind it but is not on the page |

Rules read as `` `#tfa_5` OR `#tfa_6` ``: each `#tfa_N` is a choice id, so the rule says "shown when Yearly or Each month is chosen". Translate each id into its question and choice.

### Google Form data (`FB_PUBLIC_LOAD_DATA_`)

It is a JSON array. Read only these positions:

| Position | Holds |
|---|---|
| `data[1][8]` | Form title (`data[3]` if empty); `data[1][0]` the description |
| `data[1][1]` | The items, in page order |
| `item[1]`, `item[2]`, `item[3]` | Title, help text, type code |
| `item[4]` | The answer entries; a grid has one entry per row with its row label in `entry[3][0]` |
| `entry[0]`, `entry[1]`, `entry[2]` | Entry id (the question id, written `entry.<id>`), choices, required (1 or 0) |
| `choice[0]`, `choice[2]`, `choice[4]` | Choice text; the section item id this choice jumps to (negative: submits the form); 1 when it is the Other choice with a text box |

Type codes: 0 short answer, 1 paragraph, 2 multiple choice, 3 dropdown, 4 checkboxes, 5 linear scale (end labels in `entry[3]`), 6 title and description (a text block), 7 grid, 8 section (a new page; its `item[0]` is what choices jump to), 9 date, 10 time, 11 image, 12 video, 13 file upload, 18 rating. Any other code: list it as unknown and confirm it on the live form.

A choice that jumps to a section is how Google Forms branches. Record it as a rule on that section: "shown when <question> is <choice>". A section can also be reached by continuing from the one before, so ask the person to confirm each rule.

### PDF

Use the markers in [sources/pdf.md](sources/pdf.md) ("What the parser reads as a question"): a label with a blank line is a text answer; drawn tick boxes under a question are its choices; "If yes" or "(If X is selected)" makes the next answer conditional; "Upload" or "Attach" is a file; a table with labelled rows and empty cells is one answer per row and column. A PDF never says whether a choice list allows one answer or several unless the wording does ("select all that apply"); list it as a question to confirm. A fillable PDF's boxes have names: list them beside the questions they belong to.

### Reading from images

Screenshots, phone photos of a paper form, a scan, a picture of a whiteboard sketch: Claude reads each image with its own vision. Nothing is installed and no text recognition tool is run.

1. **Put the images in order** and say how many there are. If a page looks missing (a jump in question numbers, "continued" with nothing before it, a section heading with no questions), ask for it before reading on.
2. **Read every image in full, top to bottom**, and list for each one: section headings, every question in the source's own words, its answer shape (a line, a box, a row of circles, a grid, a signature line), every choice, every required mark (an asterisk, "required", bold), help text under a question, and instructions that act as rules ("If you answered yes, go to section 3", "Office use only").
3. **Read the answer shape, not just the words.** Circles mean one answer; squares usually mean several, but say "select all that apply" only when the form says it. A long box is a long answer. A row of lines under "Address" is an address block, one answer per line label.
4. **Mark what you cannot read as unknown, never guess it.** Cut off at the edge, blurred, covered by a thumb, a drop-down shown closed, handwriting over the printed text: write what you can see and list the part you could not read in the field's `unknown` (`label`, `type`, `required`, `options`, `help`, `show_when`). A closed drop-down's choices are `"unknown": ["options"]`, not an empty list.
5. **Ignore what a respondent wrote.** A photo of a filled-in form shows answers; they are not part of the form. Never copy them into the capture, and do not repeat personal details from them in the reply.
6. **Confirm with the person** in the step 3 table, with the unknowns listed under it: "I could not read the choices under Tools, the photo is cut off; are there more than three?" Only what the images could not show is asked; everything else is stated for correction.

Coverage for an image read: sections, questions and choices `hand_authored`; validation `hand_authored` when every required mark was legible, otherwise `unknown`; conditions `hand_authored` when written rules were found, `unknown` when none were and nobody has said the form has none; connector `none_exist` for paper, `not_captured` for an online builder (it sends answers somewhere nobody has read).

## 3. Show the extraction for confirmation

Show one table, then the counts, then what could not be read. Keep it short enough to read on a phone.

| Section | Id | Question | Type | Required | Choices | Shown when | Formula |
|---|---|---|---|---|---|---|---|
| About You | tfa_1 | Service area | dropdown | yes | North District, South District | | |
| About You | tfa_8 | Other amount | text | no | | Payment plan is Yearly or Each month | |
| Order | tfa_30 | Total | number | no | | | unit price times quantity |

> 3 sections, 24 questions, 61 choices, 5 show-and-hide rules (counted from the 5 `data-condition` attributes), 1 formula, 1 custom script that looks up a postal code. Not visible on the page: where answers are saved in Salesforce (the connector), and any prefill. Correct anything that is wrong.

Count from the source, not from your table: the number of `data-condition=` attributes, of `tfa_` question ids, of choice items, of Google items by type. If the counts disagree with the table, find the difference before showing it.

## 4. Say how each part is known

Every part gets one state. Claude reading the page counts as a person transcribing it.

| Part | State when Claude read the full markup or data | State when only rendered text was read |
|---|---|---|
| sections, questions, choices | `hand_authored` | `hand_authored` (sections beyond what was shown: `not_captured`) |
| validation | `hand_authored` | `not_captured` |
| conditions | `hand_authored`, or `none_exist` when the markup or data was read in full and holds none | `not_captured` |
| connector | FormAssembly: `not_captured` (it exists, it is not on the page). Google Forms, PDF, brief: `none_exist` | same |
| images | `hand_authored` or `none_exist` | `not_captured` |
| custom scripts | `hand_authored` (listed), `none_exist` when the markup has none | `not_captured` |

Never write `none_exist` for something that was not read. Name every `not_captured` part in the confirmation message, with how to close it (the saved page, the connector's read-only view, the account's API access).

## 5. Write capture.json

After the person confirms, write the capture in the manual adapter's format ([sources/google-forms.md](sources/google-forms.md), "The capture format"). Set `platform` to the source (`formassembly`, `google-forms`, `pdf`, `word`, `microsoft-forms`, `jotform`, `photo`, `screenshot` and so on), keep the source's ids in each field's `id`, put rules in `show_when`, formulas in a field `note`, unreadable parts in a field's `unknown`, and the states from step 4 in `coverage`. Then hand over to **ftk-start**'s gap interview, which asks only what a complete Form Template still needs. Write it to a file when the session can (the outputs folder in chat), otherwise in the reply as a JSON block the person saves as `capture.json`.

## 6. Plan without scripts

With no scripts, give the plan as a table in the reply, in the same columns as the mappings file ([mapping-review.md](mapping-review.md)): question, Form Submission field, Built On, Reaches Target By, Verify In Org. Take the edition from the project config. Read Form Submission through a Salesforce connector when there is one; with no connector, use the packaged names you know and mark every row Verify In Org. The file and the scripts can produce the full plan later in Claude Code from the same `capture.json`.
