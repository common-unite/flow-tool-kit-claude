# Any other form: the hand-written route

For every form no script reads: Microsoft Forms, Jotform, Typeform, Wufoo, Cognito Forms, Formstack, SurveyMonkey and any other builder; a Word document once `docx_text.py` has listed it; screenshots; phone photos or scans of a paper form; a form someone describes from memory. Nothing is turned away for lack of an adapter.

The route has three steps, and it is the same in chat and in Claude Code:

1. **Read the form faithfully.** Claude is the parser. List every section, question (in the source's own words, typos included), answer type, choice, required mark, help text and written rule. Mark whatever the source does not show as `unknown`, per question, never guessed.
2. **Confirm, then write `capture.json`** in the manual adapter's format ([google-forms.md](google-forms.md), "The capture format"), and build `ir.json` from it. Every aspect is `hand_authored`.
3. **Hand over to ftk-start's gap interview.** It reads the capture and asks only what a complete Form Template still needs, each with a default the person can accept; the unknowns are among its questions.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from formmigrate import ir
from formmigrate.sources.manual import adapter
document = adapter.build_from_file("_forms/jotform-volunteer/capture.json")
open("_forms/jotform-volunteer/ir.json", "w").write(ir.to_json(document))
```

## Getting the form in front of Claude

| Source | Best input, in order |
|---|---|
| **Microsoft Forms** | The form's preview, one screenshot per section (branching shows as "Go to section" on each choice in the builder). The responses workbook (Open in Excel) has one column per question: save it as CSV and use [table.md](table.md) for the question list, then add choices from the screenshots |
| **Jotform** | The form's own address (form.jotform.com/...) saved as a page and read with `capture_html.py`; it often holds the questions. Otherwise screenshots of each page, and the Conditions list from the builder's Settings |
| **Typeform** | Screenshots of each question (one per screen), and of the builder's Logic panel for the branching |
| **Wufoo, Formstack, Cognito Forms, Gravity Forms** | Try `capture_html.py` on the form's own address or a saved page first; a form drawn by script is reported and the script stops. Then screenshots of each page |
| **Word document** | `docx_text.py`, then this route ([docx.md](docx.md)) |
| **Spreadsheet of questions** | `capture_table.py` ([table.md](table.md)): it writes the capture for you |
| **Paper form** | A photo or scan of every page, flat and in good light. A blank copy is better than a filled-in one |
| **Screenshots** | One per page or section, in order, including the bottom of long pages |

Read images as [Reading from images](../chat-extraction.md#reading-from-images) describes.

## What to mark unknown

| The source does not show | Write |
|---|---|
| The choices (a drop-down shown closed, a list cut off) | the choices you can see, and `"unknown": ["options"]` |
| Whether a question is required | `"unknown": ["required"]`, or declare `"coverage": {"validation": "unknown"}` when no question's requirement can be seen |
| One answer or several (square boxes with no instruction) | the type you think likely, and `"unknown": ["type"]` |
| The question text (smudged, covered) | what you can read, and `"unknown": ["label"]` |
| Whether the form has show-and-hide rules | leave `coverage.conditions` undeclared: it stays `unknown` and is reported |
| Where an online builder sends its answers | `"coverage": {"connector": "not_captured"}` |

Every unknown becomes a finding, and the gap interview asks about it. Never fill a gap to make the capture look complete.

## Tips from builders

- **Branching is per choice in most builders** ("Go to section 3" on a choice). Record it as a rule on the section it leads to: shown when that question has that choice.
- **Calculated fields** (Jotform, Cognito) are a formula in a field `note`; the plan places them on the escalation ladder.
- **Payment fields** are never transcribed as questions: payments move to Flow Tool Kit's payment step. Note that the form takes a payment.
- **File uploads, signatures, ratings and matrices** have capture types (`file`, `signature`, `rating`, a grid row per question as Google Forms does); an unfamiliar widget is written as `text` with a `note` saying what it was.
