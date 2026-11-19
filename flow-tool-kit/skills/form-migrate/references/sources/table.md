# Source: a spreadsheet of questions

For a form kept as a list: a question bank in Excel or Google Sheets, a survey drafted in a sheet, a builder's question export, or the responses workbook of a form builder whose columns are the questions. One row per question.

```bash
python3 <skill>/scripts/capture_table.py questions.csv _forms/sheet-intake "Program Intake" [--no-conditions]
```

It writes `capture.json` (the manual adapter's format, so it can be corrected by hand and rebuilt) and `ir.json`. From Python:

```python
from formmigrate.sources.table import adapter
document = adapter.build_from_file("_forms/sheet-intake/questions.csv", form_name="Program Intake")
```

**CSV only.** An `.xlsx` (or `.xls`, `.ods`, `.numbers`) is refused with the instruction to save it as CSV: Excel, File, Save As, CSV UTF-8; Google Sheets, File, Download, Comma-separated values. Save each sheet that holds questions. No spreadsheet library is needed.

## Columns

Headers are matched ignoring case, spaces and punctuation, so `Question Text`, `question_text` and `QUESTION TEXT?` are the same. Only a question column is needed.

| Role | Header aliases |
|---|---|
| Question | Question, Label, Question Text, Field, Field Label, Prompt, Item, Title |
| Page | Page, Step, Screen, Tab |
| Section | Section, Group, Heading, Part, Block |
| Type | Type, Question Type, Field Type, Answer Type, Input Type, Format |
| Choices | Choices, Options, Answers, Answer Options, Values, Picklist Values, List |
| Required | Required, Mandatory, Req, Must Answer |
| Help | Help, Help Text, Description, Hint, Instructions |
| Id | Id, Field Id, Key, Name, API Name, Variable |
| Show when | Show When, Shown When, Condition, Display When, Visible When, Depends On, Logic |
| Note | Note, Notes, Comment, Comments |

Columns it does not recognise are listed in a finding, never silently used.

- **Choices** are split on `|`, `;` or a line break inside the cell, never on commas ("Yes, I agree" is one choice).
- **Required** is true for yes, y, true, 1, x, required or mandatory. With no Required column at all, validation coverage is `unknown` and a finding says to ask.
- **Type** takes the capture's type words (`short text`, `long text`, `email`, `phone`, `date`, `number`, `dropdown`, `radio`, `checkboxes`, `yes/no`, `file` and the rest). A row with no type is a choice when it has choices and text otherwise, marked `"unknown": ["type"]`. An unrecognised type word becomes text with a finding.
- **Show when** uses the capture's form: `Question label::Choice`, for example `Have you taken a class with us before?::Yes`.
- **Pages** follow the sheet's order: by Page, then Section under it (`Page/Section`). A row with both cells blank stays on the page above, the way merged cells read. With neither column, every question goes on one page named after the form.

Without a Show When column the sheet cannot say whether the form has rules, so conditions stay `unknown`; pass `--no-conditions` only when someone has checked that it has none. Everything is `hand_authored`: a person wrote the sheet. Hand the result to **ftk-start**'s gap interview like any other capture.
