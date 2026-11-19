# What the canvas shows

`draw_plan.py` draws every artboard from `plan.json`. This page says what each one shows and why, so a reviewer's comment can be traced to the plan key that changes it.

## Layout

- A brand artboard on the left when the plan has `brand_board`: only what was chosen (logo, colors with their roles, fonts, tone, general copy), never every candidate a site scan found.
- Single-page forms side by side in the first row; each multi-page form in its own row: the original form, the stages overview (stages mode), every page, the review screen (stages mode), and its design notes.
- Then the confirmation messages, the emails and the field audit.

## Every form artboard

- **The real components.** Every field and section is a FlowToolKit Forms component with the plan's stored names and settings, never a look-alike. A control the package cannot draw is shown as a red gap card.
- **A source line above the card**: the source form's name, platform and id, linked to `source.url`, plus page and part numbers. A brief says it has no source form. Reviewers compare the rebuild with the form it replaces.
- **Every branch drawn and marked.** A field with its own rule carries a dark tag ("Shows when “Pronouns” is “Other”"); a governed section sits in a dashed frame with the same tag. Nothing is hidden, so every field can be reviewed.
- **The component decision and shape above each section**: "Reuses Contact_Details · record component", "Extends Organization_Details with 1 field · metadata component", "Record component, this form only", "Flow Section, built by build-flow-section", and "on Account, mapped to Form Submission" for a mapped component. A section whose questions are JSON on that section carries no note. The reuse and shape answers are visible where they apply.
- **Flow Sections and custom LWCs as dashed placeholders** naming the flow or component and what it does; their skills build them after the template.
- **The banner** in the header, the indicator the row picks, the button bar the row picks (a Footer bar flush with the card's bottom on one or two pages, Docked on three or more, Return / Save Progress / Mark Complete in a stages step).
- **The state the live form opens in**: empty inputs, a blank signature pad, an empty image upload, unchosen pickers.

## Size

The Design canvas takes artboards up to 8000px tall. A taller page is split at section boundaries into numbered parts (`<slug>-p2.dc.html`, `<slug>-p2-part2.dc.html`); a section taller than a part is split between its fields, its title repeated with "(continued)". The first part keeps the page's own file name, so a comment pinned to it stays. Estimates are generous on purpose (a frame a little too tall beats a clipped button bar); `check_render.cjs --write-heights` measures the real content and the next run uses it.

## The other artboards

- **Original form**: the source's screenshot once uploaded (cut into windows under the cap), else its questions in order with the link. Not drawn for a brief.
- **Stages overview**: each stage's label, description and counted minutes, and its titled sections when there are two or more.
- **Review screen**: every page's questions by section, answers empty, then the real submit.
- **Confirmation messages**: each form's message with sample merge values, at 16px.
- **Emails**: each email as it arrives, with its developer name and subject line: the confirmation, the Save Progress email or the stages resume email. One letterhead for the organization.
- **Field audit**: one row per field (repeater columns included) with source id, label, control, object and field, component decision and shape, placement, status and page. Yellow is verify, red is a gap. The same rows are in `field-audit.csv` beside each plan, for the admin.

## Images

The canvas shows an image only as an upload to the canvas. The run lists every image that has none yet in `design/uploads.json`: the plan's logo and banner, each source screenshot and, when there is no banner, the package's forest photo. Upload them to the canvas as assets, write each returned url with its listed sha1 into `design/blobs.json` (`{"banner": {"url": "<returned url>", "sha1": "<listed sha1>"}}`) and run again. Until then the banner draws in the brand color and the brand board shows a labelled placeholder; nothing is drawn with an empty image. A changed file (new sha1) is listed again.

## What a person drew

Notes and shapes a person added on the canvas are kept across runs, and so are canvas keys the run does not own. Artboards the run no longer writes (a page split or renamed) are removed from the folder and published as removals.
