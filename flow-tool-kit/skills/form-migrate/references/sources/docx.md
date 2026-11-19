# Source: a Word document (.docx)

Many forms live as Word documents: printed and filled by hand, or filled in Word with tick boxes and drop-downs. `docx_text.py` lists everything in the document in reading order, with the standard library only, and Claude transcribes the list into `capture.json` for the manual adapter (the hand-written route, [hand-written.md](hand-written.md)).

```bash
python3 <skill>/scripts/docx_text.py form.docx _forms/word-intake
```

It writes two files:

| File | Holds |
|---|---|
| `docx-text.txt` | every paragraph and table in reading order: `#` headings, `-` list items, `| cell | cell |` table rows, and each form control drawn where it sits |
| `docx-controls.json` | each control's kind, title, tag, choices, checked state and paragraph number |

The controls it recognises, all drawn inline in the text:

| In the document | Drawn as |
|---|---|
| A tick box content control, a legacy check box field, or a box symbol (a typed box character or a Wingdings box) | `[ ]`, or `[x]` when ticked |
| A plain text content control, or a legacy text field | `[text: Title]` (the control's title, tag or field name) |
| A drop-down list or combo box content control, or a legacy drop-down field | `[choice: Title: A | B | C]` (the "Choose an item." prompt is dropped) |
| A date picker content control | `[date: Title]` |

## Reading the result into a capture

- A line ending in `[text: ...]`, a colon followed by blank underscores, or a table row whose second cell is empty or a control is one text question; the label is the text before it.
- Lines of `[ ]` boxes under a question are its choices. A Word document never says whether one or several may be ticked unless the wording does ("tick all that apply"): write the likely type and `"unknown": ["type"]`.
- Required marks are rarely in a Word form. Declare `"coverage": {"validation": "unknown"}` unless the document marks them.
- "If yes, ..." or "Office use only" are rules and sections, as in a PDF ([pdf.md](pdf.md), "What the parser reads as a question").
- Set `"platform": "word"`.

## Limits

- Only the main body (`word/document.xml`) is read. Text boxes floating over the page, headers, footers and comments are not; if the document uses floating text boxes for questions, read the document directly as well.
- A `.doc` file (Word 97 to 2003) is not a zip of XML and is refused: save it as `.docx` first.
- Track changes are read as the current text plus any inserted text; check the document has no pending changes.
- In chat with code execution off, read the uploaded document directly ([../chat-extraction.md](../chat-extraction.md)).
