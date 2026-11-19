# Naming

Names for what the plugin's skills create. Flows and flow elements are named in [documentation.md](documentation.md), section 2; that section wins for anything about flows.

## Fields

- **Mirror the target field first.** A new Form Submission field that feeds a target field takes that field's API name where it is a good name (`Program_Interest__c` for `Program_Interest__c`), so the pair reads side by side. Then fix what a machine should get right: word boundaries, initialisms (`SMS`, not `Sms`), abbreviations, and widget words ("check all that apply" describes a control, not data).
- **Readable beats matching.** Never copy a target's naming problem into a new field; the mapping documents every pair.
- **Reuse, then org-wide, then form-specific.** A packaged field first; then an org-wide field named for its role (`Guardian_Phone__c`), named only after reading every form in the org; a field for one form last.
- **Shape it like its target**: the same type, and for a picklist the same values.
- **No type prefixes or suffixes** (`Contact_Record`, not `rec_contact`), and no issue numbers or dates in names.
- Labels read as the question is worded on the form (Form Submission) or as an admin knows the setting (Form Template).

## Form components and templates

- A **shared component** is named for its purpose, never for one form: `Contact_Details`, `Mailing_Address`, `Emergency_Contact`. A form-only section needs no component name.
- A **Form Template's Name** is the form's public title ("Community Program Registration"); it shows in the banner.
- A page is labelled for what it asks ("Your Details", "Release and Signature"), never "Page 2" or "Welcome".

## Files in a project

| File | Where |
|---|---|
| The project config | `flow-tool-kit.json` at the project root ([project-config.md](project-config.md)) |
| One form's work | `_forms/<slug>/`: the source files or `capture.json`, `ir.json`, `plan.json`, `field-audit.csv`, and `design/` for the canvas |
| One site's work | `_site/<slug>/`: `site.json`, `pages/<urlName>.json`, `photos.json`, `backups/<date>/` (the site as pulled before each build), `checks/<date>/` (render check screenshots) and `notes.md`. `<slug>` is the site's name in lowercase with hyphens |
| One brand's kit | `_brand/<slug>/`: the site crawl and stylesheet scan, `candidates.json`, the review (`brand-picker.html`, `brand-review.md`), `picks.json`, `brand-kit.json`, `assets/` and `canvas/`. `<slug>` is the brand's name in lowercase with hyphens |
| A FormAssembly account archive | `_formassembly/` at the project root: one folder per form, the summaries, `check-pass-report.md` and `pages/`. `_formassembly/raw/` holds API listings and browser bundles; keep it out of version control |
| An audit | `_audits/<audit>-<yyyy-mm-dd>/`, for example `_audits/guest-exposure-2026-01-15/` with `findings.md`, `findings.json` and `snapshot.json` |
| The org catalog | `ftk-catalog/<org Id>/`: `catalog.json`, `catalog.md` and (in Claude Code) `raw.json`; `ftk-catalog/no-org/` when no org is connected ([catalog-format.md](catalog-format.md)) |
| A field audit | `field-audit/<org Id>/`: `data-dictionary.md`, the four CSVs (`data_dictionary.csv`, `template_references.csv`, `flow_references.csv`, `coverage.csv`) and `raw.json` |
| `<slug>` (a form) | The form's name in lowercase with hyphens, prefixed by the source when there is one: `formassembly-4874954`, `google-volunteer-survey`, `brief-community-registration` |
| Metadata | The project's own `force-app/` |
