# PDF forms

`sources.pdf` reads a PDF form into the IR. Two optional tools, each used when present:

| Tool | Reads | Without it |
|---|---|---|
| poppler (`pdfinfo`, `pdftotext`) | the printed text: questions from written markers, sections, instructions | a fillable PDF is still read from its fields; a flat PDF raises `PdfToolsMissing` with the next step |
| pypdf (`pip install pypdf`) | a fillable PDF's own fields: name, question text (the box's tooltip), type, required flag and choices, all `parsed` | the fields are declared `not_captured` and a finding says so plainly; questions come from the printed text |

```python
from formmigrate.sources.pdf import adapter
document = adapter.build_from_file(
    "_forms/pdf-community-grant/form.pdf", form_id="community-grant",
    form_name="Community Grant Application",
    exclude_pages=(3,), exclude_reason="the budget table is collected by a separate budget form",
)
```

## When poppler is missing (a chat sandbox, a bare machine)

```bash
python3 <skill>/scripts/pdf_text.py form.pdf _forms/pdf-community-grant
```

It writes `pdf-text.txt` with whatever is there (pdftotext, else the pypdf library) and, when pypdf is installed, `pdf-fields.json` with each fillable field's name, question text, kind, required flag, choices and page. When pypdf is missing it prints that a fillable PDF's boxes were not read. Read both, transcribe the form into `capture.json` for the manual adapter ([google-forms.md](google-forms.md), the capture format) using the markers below, and declare coverage `hand_authored`. With no code execution, read the uploaded PDF directly: [../chat-extraction.md](../chat-extraction.md).

## First, find out what kind of PDF it is

Run `pdfinfo form.pdf` and read two lines:

| `Tagged` | `Form` | What you get |
| --- | --- | --- |
| yes | none | **The common case** (Word, Google Docs, InDesign exports). Structure tree with headings, lists and real tables; questions recognised from the written markers. Best result. |
| no | none | Printed or scanned-then-OCR'd. Positioned lines only: tables and option lists are reconstructed from layout. Check every table and list by hand. |
| any | AcroForm | Real form fields exist. With pypdf, each field becomes a question (`parsed`), grouped by page, with its tooltip as the question text; read the printed text for section headings and regroup the pages in form-design. Without pypdf, the fields are `not_captured` and the questions come from the printed text. An AcroForm with no fields (common in Word exports) is read as a flat PDF. |
| any | XFA | A dynamic LiveCycle form. The PDF usually renders only a "please wait" page; ask for the original form or a flattened print. |

## What the parser reads as a question

| Written marker | Becomes |
| --- | --- |
| `Label: ______` | text answer; label is the text before the blank, anything after is help text |
| paragraph, then lines of `____` | long answer; `(150 words max)` becomes `maxwords-150` |
| `Label: Y/N`, `... - Yes or No` | Yes/No choice |
| `Label: Pre-population` | text answer the organisation's own record fills (`prefill_hint`) |
| question, then drawn tick boxes | choice; options are the boxed lines |
| a tick box indented under a tick box | a follow-up choice shown when the parent box is ticked |
| `(If X is [not] selected)` | the next answer is conditional on option X |
| `If yes, ...` / `If yes:` | the next answer, or the next table group, is conditional on Yes |
| `If yes, please give your details.` (a sentence, no blank), then labels | the labelled answers under it, up to the next question or list, are conditional on Yes; recorded `"inferred": true` with the sentence in `source_text` |
| `Upload...` / `Attach...` | file upload |
| table with labelled rows and empty cells | matrix: one long answer per row and column |
| table of labels only, no answer rows | repeating group, one entry per row |
| paragraphs and tables before the first `SECTION` heading | information, not questions: the rebuild's first page, as HTML in the page `Details__c` (build-form-component covers page details). The parser does not capture bold or colour runs, so read the rendered page for emphasis and table styling |
| long disclosure paragraphs above consent or authorization questions | the wrap-up page body (`Details__c`), with the consent questions in a component |
| the same line at the foot of every page (funder, organisation or copyright line) | `form.footer_text` in the IR (found by position, in the bottom of every page, never in the page text), then the template footer: `FormQualifiedApiName_Footer__c` = `FlowToolKit__Form_Footer_Demo`, text in `Template_Footer_Text__c`. Never page body text. Drop it from page 1's body too |

The option marker is the drawn box itself: Word writes it as an empty text run at the start of the paragraph. That, not indentation, is what makes a line an option. Indentation is only used to nest follow-up options.

## Fillable fields: what is checked

With pypdf, the read reports as findings: fields with no tooltip (the question text is then the internal name; read the printed label beside the box), radio groups whose choices are codes (`Choice1`, `0`), signature fields (rebuilt as the form's signature step, never a text box), push buttons (skipped), JavaScript actions (calculations and show-and-hide rules live there and are not read, so conditions are `not_captured`), and the number of questions the printed text alone suggests, to compare with the fields. Read-only boxes are kept with `"read_only": true`: they are usually calculated or prefilled.

The printed text is read alongside the boxes (when poppler is installed), so what the boxes do not carry survives:

- **The "If yes" rule.** A printed `If yes, ...` after a yes/no question is tied to the boxes: the question to the radio group or check box whose tooltip matches it, and each printed label under the rule to the box after it whose tooltip matches. Each becomes a condition with `"inferred": true` and `source_text`. `coverage.conditions` is `parsed` then, `not_captured` when a stated rule cannot be tied to a box or the PDF has JavaScript, and `none_exist` only when the printed text states no rule and no script exists. Without pypdf the fields are unread, so a stated rule is `not_captured` too, never `parsed` with nothing in it.
- **Select-all lists.** A fillable PDF draws each choice as its own check box. Boxes in a row whose tooltips share a prefix (`Days available: Monday`) or whose tooltips are the choice lines printed under a `select all that apply` question become one multi-select question (`choice-group`, validation `checkbox`), labelled with the printed question, each option keeping its box's `pdf_field_name` (the group lists them in `pdf_field_names`).
- **The footer.** The line at the foot of every page is `form.footer_text`.

## What a PDF can never tell you (always raised as findings)

- **Single or multiple choice.** Every tick box is drawn the same. Lists are multi-select when the wording says so ("select all", "two or more of the following", "a minimum of 2"), otherwise single choice with a finding to confirm.
- **Where the data goes.** There is no connector; the Field Plan proposes staging fields from labels alone.
- **Totals.** "(This is the total of all ...)" is flagged as a calculation candidate, not built as one.
- **Implied reveals.** An answer box right under a tick box is conditional on that box, recorded with `"inferred": true`.

## Sanity checks before trusting the IR

Count from the source, not from the parser:

```bash
pdfinfo -struct-text form.pdf > struct.txt
grep -c '^ *Table (block)' struct.txt           # every table is a matrix, repeat group or content
pdftotext -layout form.pdf layout.txt
grep -E '_{3,}' layout.txt | grep -vE '^\s*_+\s*$' | wc -l   # inline blanks = text answers (+ Pre-population ones)
```

Tick boxes: count paragraphs whose first run is `""` with more text after it, **outside tables** (empty runs inside table cells are formatting, not boxes). For example, 191 boxes plus 6 synthesised Yes/No options give 197 IR options.

Exclusions (`exclude_pages`) are counted and reported in findings, never silently dropped.
