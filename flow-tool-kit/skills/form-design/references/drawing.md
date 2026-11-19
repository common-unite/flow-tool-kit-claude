# Drawing the canvas: what it shows, the checks and publishing

What `draw_plan.py` draws and why, the checks it runs before drawing, and how the canvas is published and checked.

## What the canvas shows

`draw_plan.py` draws every artboard from `plan.json`. This page says what each one shows and why, so a reviewer's comment can be traced to the plan key that changes it.

### Layout

- A brand artboard on the left when the plan has `brand_board`: only what was chosen (logo, colors with their roles, fonts, tone, general copy), never every candidate a site scan found.
- Single-page forms side by side in the first row; each multi-page form in its own row: the original form, the stages overview (stages mode), every page, the review screen (stages mode), and its design notes.
- Then the confirmation messages, the emails and the field audit.

### Every form artboard

- **The real components.** Every field and section is a FlowToolKit Forms component with the plan's stored names and settings, never a look-alike. A control the package cannot draw is shown as a red gap card.
- **A source line above the card**: the source form's name, platform and id, linked to `source.url`, plus page and part numbers. A brief says it has no source form. Reviewers compare the rebuild with the form it replaces.
- **Every branch drawn and marked.** A field with its own rule carries a dark tag ("Shows when “Pronouns” is “Other”"); a governed section sits in a dashed frame with the same tag. Nothing is hidden, so every field can be reviewed.
- **The component decision and shape above each section**: "Reuses Contact_Details · record component", "Extends Organization_Details with 1 field · metadata component", "Record component, this form only", "Flow Section, built by build-flow-section", and "on Account, mapped to Form Submission" for a mapped component. A section whose questions are JSON on that section carries no note. The reuse and shape answers are visible where they apply.
- **Flow Sections and custom LWCs as dashed placeholders** naming the flow or component and what it does; their skills build them after the template.
- **The banner** in the header, the indicator the row picks, the button bar the row picks (a Footer bar flush with the card's bottom on one or two pages, Docked on three or more, Return / Save Progress / Mark Complete in a stages step).
- **The state the live form opens in**: empty inputs, a blank signature pad, an empty image upload, unchosen pickers.

### Size

The Design canvas takes artboards up to 8000px tall. A taller page is split at section boundaries into numbered parts (`<slug>-p2.dc.html`, `<slug>-p2-part2.dc.html`); a section taller than a part is split between its fields, its title repeated with "(continued)". The first part keeps the page's own file name, so a comment pinned to it stays. Estimates are generous on purpose (a frame a little too tall beats a clipped button bar); `check_render.cjs --write-heights` measures the real content and the next run uses it.

### The other artboards

- **Original form**: the source's screenshot once uploaded (cut into windows under the cap), else its questions in order with the link. Not drawn for a brief.
- **Stages overview**: each stage's label, description and counted minutes, and its titled sections when there are two or more.
- **Review screen**: every page's questions by section, answers empty, then the real submit.
- **Confirmation messages**: each form's message with sample merge values, at 16px.
- **Emails**: each email as it arrives, with its developer name and subject line: the confirmation, the Save Progress email or the stages resume email. One letterhead for the organization.
- **Field audit**: one row per field (repeater columns included) with source id, label, control, object and field, component decision and shape, placement, status and page. Yellow is verify, red is a gap. The same rows are in `field-audit.csv` beside each plan, for the admin.

### Images

The canvas shows an image only as an upload to the canvas. The run lists every image that has none yet in `design/uploads.json`: the plan's logo and banner, each source screenshot and, when there is no banner, the package's forest photo. Upload them to the canvas as assets, write each returned url with its listed sha1 into `design/blobs.json` (`{"banner": {"url": "<returned url>", "sha1": "<listed sha1>"}}`) and run again. Until then the banner draws in the brand color and the brand board shows a labelled placeholder; nothing is drawn with an empty image. A changed file (new sha1) is listed again.

### What a person drew

Notes and shapes a person added on the canvas are kept across runs, and so are canvas keys the run does not own. Artboards the run no longer writes (a page split or renamed) are removed from the folder and published as removals.

## The design checks

`draw_plan.py` runs these on every plan before it draws. An **error** stops the run and nothing is drawn; a **warning** is printed and the run goes on. Each message says what to change in `plan.json`. `--check` runs them without changing anything, for a plan someone else edited.

### Errors

| Check | Why |
|---|---|
| A confirmation message under two paragraphs, four sentences or 45 words, or with no next step or no contact | Respondents need thanks, why it matters, what happens next and who to ask |
| A page label of Welcome, a page description under two sentences, a titled section with no subtitle, an empty section | Stage cards and the stages accordion show these words |
| A button label outside the package's lists, or Next on an ordinary multi-page form | A label outside the restricted picklist fails the build; the forward button reads Continue |
| A "Page N of M" page heading | The indicator or stage list already shows position |
| An em-dash anywhere a respondent reads | House style |
| A section icon that is not a `utility:` icon | House style; other icon sets draw inconsistently |
| A rule with no label, a label over 40 characters or an API name, a condition missing its field, operator or value, an operator the package does not evaluate, a value holding a second question | build-template builds rules exactly; Form Builder lists them by label |
| More show/hide rules than the source has (when `ir.json` captured its conditions) | Only the source's rules |
| A visible source field neither in the plan nor in `dropped` | Every source question is kept or dropped on purpose. A part form-migrate folded into one date question (a date asked as Month, Day and Year) goes in `dropped`, and the kept part is one date control |
| A source field form-migrate marked `sensitive` (a government id, an account number, health information, a password, a date of birth with the name) whose plan field has no `sensitive` mark, or no `answer` and no question naming it; an answer `not collected` with the field still on a page | Whether to collect it at all, and how to store it, is the person's decision. An `ordinary` answer leaves a warning |
| A placed source field whose `required` differs from the source's (`ir.json` `fields[].required`, either way) with no `required_change` and no question naming it; asked but unanswered leaves a warning | Keep requiredness exactly: making a question optional or required is the person's decision, recorded on the field |
| A field with no Salesforce field, an unknown control not marked gap, widths that are not three numbers from 1 to 12, a bad status or placement, a choice field with no options, a repeater with no columns | The build needs every one |
| A gap field not listed in `gaps` | Gaps are reported, not drawn as if they work |
| A catalog match with no answer in `asked`, or an answer that does not match the decision | Never reuse, extend or duplicate a component silently |
| An `update` without its own question answered update, without a complete `usage` list named in that question, without `shared_change_reason` and `changes`, or on a packaged component; an `extend` whose `new_name` is the original's | Updating a shared component changes every form that uses it; extend never touches the original |
| `reuse` or `extend` without the component's name; a Flow Section or custom LWC without its `build` skill, flow name or component name, or in a section of the wrong type | The build and the follow-on skills need them |
| A component on another object in a paid org without `form_template_mapping` | The mapping preference: prefill, live updates and Apply Submission Field Maps need it |
| An email linking with `pv9` or `recordId`, a Save Progress or resume email without `{{FlowToolKit__Internal_Resume_Link__c}}`, a relationship merge | Since the Save Progress Resume Link field, the package builds the link; Lightning merges cannot follow relationships |
| A payment rule that fails the rule checks; `payment.required` not true or false | build-template writes Payment Conditions exactly |
| A URL parameter the package does not read, `sourceId`, a parameter mapped twice, or one with no field | build-template writes URL Parameter Mapping exactly; the form reads `sourceId` by itself |
| A `shape` other than metadata, record or json; a shape set on `form-only`, `shared-new` or `extend` with no answered `shape_asked`, or an answer that differs; `json` on anything but `form-only`; a `reuse` or `update` whose shape differs from the existing component's; a shape on a Flow Section or custom LWC | The shape is recommended and asked, never decided silently; JSON is fixed to one section; reuse keeps the component as it is (`_shared/standards/component-shapes.md`) |
| An `extend` component's `design_file` missing or not JSON | build-template builds the extended copy from it when the org's copy cannot be read |
| An address without its Address row, or missing one of its five parts (Street, City, State, PostalCode, Country), or with one twice | The package draws an address only with its row and all five parts: without them it draws nothing or one blank box. A lone row on a standard address field (MailingAddress) is not an error: normalize adds its parts |
| A required address part under an optional Address row, or a required row over parts that are all optional | Flow Tool Kit takes every part's required flag from the row: under an optional row the source's required street, city, state and zip show as optional. Make the row required (the form then requires every part, Country included), or make the parts optional with `required_change` |
| An anonymous survey with Save Progress, Autosave or the Save Progress email on | A partial save records who saved and emails a named address |
| A text colour on its background under WCAG AA's 4.5:1 for body text and buttons: the button text (Brand text) on the brand, links in the brand on the card, field labels on the card, typed answers on the input, the banner subtitle in white on its fill or scrim. The message gives the measured ratio and the nearest passing shade of the plan's colour (`_shared/lib/contrast.py`, the measure brand-kit uses) | Unreadable buttons, checks and links reach the client otherwise; the scrim is measured solid, so look at the drawn banner over its photo too |
| A control that is not a component of the kit, a key in `banner` that is not a Banner prop, or any component the drawing would place with a prop it does not have or a value of the wrong type (a variant or option the kit does not list, a number where it takes text). Each names the page, section and field or the board, the component and the prop, with the closest name when it looks like a typo. Read from the kit's `index.d.ts`, `ftk-forms/project/components/index.d.ts` in the plugin's ftk-design-system skill | Caught in the plan, before the canvas, instead of as a red Unknown component box or a control drawn in its default look |

### Warnings

- No source link; no inactive message; an API name in respondent copy.
- A headerless section with a frame, or a titled section with fields and no frame.
- A one-page survey with no Survey Section.
- Fewer rules than the source.
- No org catalog read; a component on an object the free edition does not cover.
- A `form-only`, `shared-new` or `extend` component with no `shape` (a plan written before shapes): it still draws, and build-template builds it as before (`form-only` as JSON, the others as record components). Recommend a shape, ask, and record it.
- Save Progress email or stages mode on with no saved or resume email designed (the package sends its built-in one).
- No confirmation email and no `no_email_reason`.
- An anonymous survey with a file upload, or an audience other than public guests.
- A heading colour or the banner title under 3:1 (large text, WCAG AA), with the ratio and a passing shade; a plan colour that is not `#rrggbb`, so it was not measured; no `index.d.ts` found, so the type check did not run.

## Publishing the canvas

### What a run writes

| File | What it is |
|---|---|
| `_forms/<slug>/plan.json` | Updated in place with the rule-decided values (each change printed) |
| `_forms/<slug>/field-audit.csv` | One row per field, for the admin |
| `design/project/*.dc.html`, `design/project/canvas.json` | The artboards and the canvas layout |
| `design/publish-batches.json` | The publish, in order, as `files` maps (root `design/`), each within the per-call limit |
| `design/uploads.json` | Images still to upload to the canvas |
| `design/review.html` | The self-contained fallback page |
| `design/render/*.png`, `design/render-check.json` | From the render check (Claude Code) |

### Claude Code (`--mode code`, the default)

1. Create the canvas from the **Design** artifact type, naming the person's **FlowToolKit Forms** design system (the link in `flow-tool-kit.json`) so the type does not fall back to another system. Follow the type's instructions that come back with the create result. Record the canvas link in the plan as `canvas_url` (later runs and the review use it) and give it to the person.
2. Upload the images in `uploads.json` (`file_paths`, 25 a call), record each url in `design/blobs.json`, run `draw_plan.py` again.
3. Run the render check and look at every screenshot (below).
4. Publish each batch of `publish-batches.json` in order, with `root` set to the `design/` folder. The five design system files are copied server side from the person's own design system (`{"artifact": <link>, "path": ...}`); `canvas.json` goes in the last batch so the canvas opens on a complete set.
5. Before every later publish, read the canvas first: a comment pinned on it makes a new version, and a publish must build on that version.

### claude.ai chat (`--mode chat`)

Chat cannot copy files between artifacts, so the run copies the five design system files from the FlowToolKit Forms kit the plugin ships (its ftk-design-system skill) into `design/project/ds/ftk/` and lists them in the batches as local files. Each batch holds at most 16 files, the most one chat call takes. Publish the batches in order, the same way, then give the person the canvas link, `plan.json` and `field-audit.csv` (as files they download, or add to their claude.ai Project).

### No Design type

Some organizations turn the Design and Design System types off. The run still writes `design/review.html`: one page holding every artboard with the same components (React, the kit's bundle and styles, the base tokens and only the icons the boards use, about 1.5 MB with the package photo). Publish it as an ordinary artifact or hand it over as a file. It has passed a headless render in Claude Code; publishing it as an artifact from chat has not been tried yet, so say so.

### The render check (Claude Code)

```bash
node scripts/check_render.cjs _forms/<slug>/design --write-heights
```

It renders `review.html` headless, screenshots every artboard into `design/render/`, and compares each board's real content height with its frame. A board whose content is taller than its frame fails (its button bar would be cut off); `--write-heights` records the measured heights in `design/measured-heights.json`, and the next `draw_plan.py` run uses them. Console errors and unknown components fail too. Open every screenshot and look at it: the check measures, it does not judge. Needs Node and Playwright's Chromium (`npx -y playwright@1.47.2 install chromium` once). On Claude Code on the web, allow the npm registry in the environment's network settings.
