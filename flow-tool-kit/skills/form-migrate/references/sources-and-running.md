# Sources, files, running it and where each question is built

Moved from this skill's SKILL.md, read on demand: Pick a source, Where files go, Running it, Reading the org, Where each question is built: the mapping preference.

## Pick a source

| Source | How it is read | Reference |
|---|---|---|
| **FormAssembly**: exports, a public link, or API access | `sources.formassembly`; `capture_public.py` for a public link; `formassembly_api.py` with an access token | [formassembly.md](sources/formassembly.md) |
| **PDF form**, fillable or flat | `sources.pdf`: fillable fields from the PDF itself when pypdf is installed, printed questions through poppler; `pdf_text.py` when neither full read can run | [pdf.md](sources/pdf.md) |
| **Brief** for a form that does not exist yet | `sources.manual` with `"platform": "brief"` | [brief.md](sources/brief.md) |
| **Word** document (.docx) | `docx_text.py` lists paragraphs, tables and form controls in order; Claude writes `capture.json` | [docx.md](sources/docx.md) |
| **Custom web form**, by address or a saved page (hand-built, WordPress, Gravity Forms, Visualforce) | `capture_html.py` fetches or reads the page and warns when the form is drawn by script | [html.md](sources/html.md) |
| **Google Forms** link | `capture_google_form.py` reads the form data the saved page carries: every section, choice and branch | [google-forms.md](sources/google-forms.md) |
| **Spreadsheet** of questions (CSV; save an .xlsx as CSV) | `capture_table.py` (`sources.table`): one row per question | [table.md](sources/table.md) |
| **Microsoft Forms, Jotform, Typeform, Wufoo, Cognito Forms** and any other builder | The hand-written route: Claude reads the builder's preview, export or screenshots and writes `capture.json` (`sources.manual`) | [hand-written.md](sources/hand-written.md) |
| **Screenshots or photos** of a form, paper included | The hand-written route, reading each image as in [Reading from images](chat-extraction.md#reading-from-images) | [hand-written.md](sources/hand-written.md) |
| **Existing Form Template** (clean-up, redesign, merge) | `sources.formtemplate` | [formtemplate.md](sources/formtemplate.md) |
| **Design file** (`.dc.html`) | `sources.claude_design` | [claude-design.md](sources/claude-design.md) |
| **Anything else** | The hand-written route: read the form faithfully, mark what you cannot see as unknown, then the gap interview | [hand-written.md](sources/hand-written.md) |

Every hand-written capture is declared `hand_authored`, and whatever a question did not show (its choices, whether it is required, a rule) is marked `unknown` rather than guessed. After the capture, **ftk-start**'s gap interview asks only what a complete Form Template still needs. A new adapter is worth writing only when the same platform will be read again and again ([source-adapter-contract.md](source-adapter-contract.md)); it is never the answer for a form in front of you.

Read the source's reference before collecting inputs: several have a "get this export, not that one" rule that costs a round trip if missed.

**Only FormAssembly and an existing Form Template carry a Salesforce mapping.** Every other source is form-side only, so every target and matching rule becomes a question for the org's people. Budget for that conversation.

## Where files go

Everything is written into the person's project, never into the plugin:

```
_forms/<source>-<form-id>/
    <source inputs>              form.html, exports, capture.json, api-*.json
    ir.json                      the form description
    mappings.csv  mappings.json  decisions.json
    questions.md  discovery-report.md  validation.json
```

In chat, write these to the outputs folder (or into the reply when files cannot be written), and suggest adding them to the claude.ai Project so the next chat has them.

## Running it

Python 3 standard library only; nothing to install. Two optional tools widen the PDF read: poppler (`pdfinfo`, `pdftotext`) for printed questions and pypdf (`pip install pypdf`) for a fillable PDF's own fields; each script says plainly what it could not read without them. Run the scripts by their path in this skill folder.

```bash
# 1. Read the source into _forms/<slug>/ir.json (one of)
python3 scripts/capture_public.py 1234567 _forms/formassembly-1234567 "Volunteer Application"
python3 scripts/formassembly_api.py 1234567 _forms/formassembly-1234567 "Volunteer Application"
python3 scripts/capture_google_form.py "<viewform address>" _forms/google-volunteer [--html <saved page>]
python3 scripts/pdf_text.py form.pdf _forms/pdf-grant      # when the pdf adapter cannot run
python3 scripts/docx_text.py form.docx _forms/word-intake  # then write capture.json from docx-text.txt
python3 scripts/capture_html.py "<page address or saved .html>" _forms/html-intake "Volunteer Intake"
python3 scripts/capture_table.py questions.csv _forms/sheet-intake "Program Intake"

# 2. Plan: mappings, questions, discovery report (edition from flow-tool-kit.json)
python3 scripts/plan_form.py _forms/<slug> --use-default-org          # Claude Code with the sf CLI
python3 scripts/plan_form.py _forms/<slug> --describe-file fs.json    # chat, describe from a connector
python3 scripts/plan_form.py _forms/<slug>                            # no org: rows marked verify
```

For the other adapters and checks, import the package:

```python
import sys; sys.path.insert(0, "<this skill>/scripts")
from formmigrate import ir
from formmigrate.sources.manual import adapter     # or .pdf, .html, .table, .formtemplate, .claude_design
document = adapter.build_from_file("_forms/brief-arts-fund/capture.json")
open("_forms/brief-arts-fund/ir.json", "w").write(ir.to_json(document))
```

| Module | Role |
|---|---|
| `ir.py`, `conditions.py` | **The contract**: document shape, coverage, condition trees, the structural check |
| `sources/` | One adapter per platform, plus `manual` (any hand-written capture) and `table` (a spreadsheet of questions); the only code that knows what a source looks like |
| `schema.py` | The Form Submission field list: org, describe file, `force-app`, or the shipped snapshot |
| `projectconfig.py` | Reads this org's entry in `flow-tool-kit.json` |
| `fieldplan.py` | A Form Submission field per question, where it is built and how it converts, with a confidence |
| `ladder.py` | Places every calculation and custom script on the escalation ladder |
| `validate.py` | Checks the form description against the org or `force-app`; reports skipped checks |
| `questions.py` | The decisions only the org's people can make, each with a recommendation |
| `mappings.py`, `decisions.py` | The mappings file, and reading the reviewer's edits back |
| `review.py` | Mechanical naming fixes |
| `fieldmeta.py` | Field metadata for new Form Submission fields, with descriptions |
| `componentcheck.py`, `configcheck.py` | Checks on a built component (see The relay) |

## Reading the org

Read Form Submission and every target object live whenever an org is connected: the Salesforce CLI in Claude Code (`--org <org-alias>` or `--use-default-org`), a Salesforce connector in chat. Through a connector, describe `FlowToolKit__Form_Submission__c`, save the result as JSON in the form folder, and pass it with `--describe-file`.

A describe silently leaves out every field the reading user cannot see, so a hidden field looks like a missing one. The CLI read also queries `FieldDefinition` and keeps such fields, flagged; with a connector, run the same query (`SELECT QualifiedApiName, Label, DataType FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'FlowToolKit__Form_Submission__c'`) and add its rows to the saved file. Never propose a field whose name already exists, visible or not.

**Read the org's real field types before choosing any input type.** A form can draw a stored field as a different input (FormAssembly and Flow Tool Kit both do), so the source alone never tells you the storage type. A Boolean shown as yes/no uses Flow Tool Kit's Boolean-as-radio display, which stays empty until answered and so can be required; a Yes/No picklist stays a picklist; a plain "I agree" box is a checkbox. Without the org, field types are guesses: mark them so.

## Where each question is built: the mapping preference

The edition decides it (full standard: `_shared/standards/mapping-preference.md`):

- **Paid**: contact, organization and address questions are built as a form on their own object (a Contact or Account form) placed in the page section, with Form Builder field mapping (the Form Template Mapping tab) landing each answer on an existing Form Submission field, packaged first (the Contact 1, Contact 2, address and organization blocks). The packaged conversion flows apply those maps (Apply Submission Field Maps) for Account, Contact, Lead, Case and Opportunity. Transform rows stay only for calculated or combined values, Campaign Members and record types.
- **Free**: every question is on a Form Submission form and reaches its target through the conversion flow's Transform, as before.

The mappings file shows both choices per row (Built On, Reaches Target By). With no connector, which person or organization a question describes is a guess from its section; those rows stay questions.
