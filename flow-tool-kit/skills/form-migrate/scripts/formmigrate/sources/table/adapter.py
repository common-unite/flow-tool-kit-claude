"""Spreadsheet source adapter: a table of questions, one row per question.

For a form that lives as a list rather than a page: a question bank kept in a
spreadsheet, a survey drafted in Excel or Google Sheets, a builder's "export
questions" file. Saved as CSV (Excel and Google Sheets both save CSV; an
.xlsx is not read, so no library is needed), each row becomes one question.

Columns are matched by header, ignoring case, spaces and punctuation, with
common aliases (``Question`` or ``Label``, ``Choices`` or ``Options``, and so
on). The rows are turned into a hand-written capture and assembled by the
manual adapter, so the result is the same ``ir.json`` with every aspect
``hand_authored``: a person wrote the sheet, a parser only read it.

Usage::

    from formmigrate.sources.table import adapter
    document = adapter.build_from_file("_forms/sheet-intake/questions.csv",
                                       form_name="Program Intake")

Read a CSV table of questions into a capture, then into the shared IR.

One row per question. Recognised columns (header case, spaces and punctuation
are ignored; the first matching alias wins):

    page        page, step, screen, tab
    section     section, group, heading, part, block
    question    question, label, question text, field, field label, prompt, item, title
    type        type, question type, field type, answer type, input type, format
    choices     choices, options, answers, answer options, values, picklist values, list
    required    required, mandatory, req, must answer
    help        help, help text, description, hint, instructions
    id          id, field id, key, name, api name, variable
    show_when   show when, shown when, condition, display when, visible when, depends on, logic
    note        note, notes, comment, comments

Only ``question`` is needed. Choices are split on ``|``, ``;`` or a line break
inside the cell, never on commas ("Yes, I agree" is one choice). Required is
true for yes, y, true, 1, x, required or mandatory. A row with no type is a
choice when it has choices and text otherwise, and a finding says so.

Rows are grouped into pages in sheet order: by ``page``, then ``section``
under it (written ``Page/Section``). A row with both cells blank stays on the
page above it, the way merged cells read. With neither column, every question
goes on one page named after the form.
"""

from __future__ import annotations

import csv
import io
import re

from ..manual import adapter as manual

_ALIASES = {
    "page": ("page", "step", "screen", "tab"),
    "section": ("section", "group", "heading", "part", "block"),
    "question": ("question", "label", "questiontext", "field", "fieldlabel", "prompt", "item", "title"),
    "type": ("type", "questiontype", "fieldtype", "answertype", "inputtype", "format"),
    "choices": ("choices", "options", "answers", "answeroptions", "values", "picklistvalues", "list"),
    "required": ("required", "mandatory", "req", "mustanswer"),
    "help": ("help", "helptext", "description", "hint", "instructions"),
    "id": ("id", "fieldid", "key", "name", "apiname", "variable"),
    "show_when": ("showwhen", "shownwhen", "condition", "displaywhen", "visiblewhen", "dependson", "logic"),
    "note": ("note", "notes", "comment", "comments"),
}

_TRUE = {"yes", "y", "true", "1", "x", "required", "mandatory", "✓", "✔"}
_SPLIT_RE = re.compile(r"\s*(?:\||;|\r?\n)\s*")


class TableError(ValueError):
    """The table cannot be read as a list of questions."""


def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (header or "").lower())


def match_columns(headers: list[str]) -> dict[str, int]:
    """Which column holds each role, by header. Each column serves one role at most."""
    keys = [_key(header) for header in headers]
    found: dict[str, int] = {}
    taken: set[int] = set()
    for role, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in keys and keys.index(alias) not in taken:
                found[role] = keys.index(alias)
                taken.add(found[role])
                break
    return found


def _choices(cell: str) -> list[str]:
    return [part for part in _SPLIT_RE.split(cell.strip()) if part] if cell.strip() else []


def to_capture(rows: list[list[str]], form_name: str = "", platform: str = "spreadsheet") -> dict:
    """Turn the table's rows (header first) into a manual-adapter capture."""
    rows = [row for row in rows if any((cell or "").strip() for cell in row)]
    if not rows:
        raise TableError("The table is empty.")
    headers = rows[0]
    columns = match_columns(headers)
    if "question" not in columns:
        raise TableError(
            "No question column. Name one column Question (or Label, Field, Prompt); found: "
            + ", ".join(header for header in headers if header)
        )

    def cell(row, role):
        index = columns.get(role)
        return (row[index] if index is not None and index < len(row) else "").strip()

    notes: list[str] = []
    ignored = [headers[i] for i in range(len(headers)) if i not in columns.values() and headers[i].strip()]
    if ignored:
        notes.append(f"Columns not read: {', '.join(ignored)}.")

    pages: list[dict] = []
    by_name: dict[str, dict] = {}
    default_page = form_name or "Questions"
    for number, row in enumerate(rows[1:], start=2):
        label = cell(row, "question")
        if not label:
            notes.append(f"Row {number} has no question text and was skipped.")
            continue
        page = cell(row, "page")
        section = cell(row, "section")
        name = "/".join(part for part in (page, section) if part) or (pages[-1]["name"] if pages else default_page)
        if name not in by_name:
            by_name[name] = {"name": name, "fields": []}
            pages.append(by_name[name])

        field: dict = {"label": label}
        choices = _choices(cell(row, "choices"))
        declared = cell(row, "type")
        if declared:
            field["type"] = declared
        else:
            field["type"] = "radio" if choices else "text"
            field["unknown"] = ["type"]
        if choices:
            field["options"] = choices
        if cell(row, "required"):
            field["required"] = cell(row, "required").lower() in _TRUE
        for role, key in (("help", "help"), ("id", "id"), ("show_when", "show_when"), ("note", "note")):
            if cell(row, role):
                field[key] = cell(row, role)
        by_name[name]["fields"].append(field)

    if not pages:
        raise TableError("The table has a question column but no questions.")
    capture = {"platform": platform, "form_name": form_name, "captured_by": "a spreadsheet of questions",
               "pages": pages}
    if "required" not in columns:
        # The sheet never said which questions are required: a gap, not "none are".
        capture["coverage"] = {"validation": "unknown"}
        notes.append("No Required column: which questions are required is unknown; ask before planning.")
    if notes:
        capture["table_notes"] = notes
    return capture


def read_rows(path: str) -> list[list[str]]:
    """The CSV's rows. Comma, semicolon or tab separated; a UTF-8 byte order mark is ignored."""
    if path.lower().endswith((".xlsx", ".xlsm", ".xls", ".ods", ".numbers")):
        raise TableError(
            f"{path} is a workbook, which is not read here. Save the sheet of questions as CSV "
            "(Excel: File, Save As, CSV UTF-8; Google Sheets: File, Download, Comma-separated values) "
            "and pass the .csv file."
        )
    with open(path, encoding="utf-8-sig", newline="") as handle:
        text = handle.read()
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(io.StringIO(text), dialect))


def build(rows: list[list[str]], form_name: str = "", platform: str = "spreadsheet",
          coverage: dict | None = None) -> dict:
    """Assemble the table into an IR document through the manual adapter."""
    capture = to_capture(rows, form_name=form_name, platform=platform)
    if coverage:
        capture["coverage"] = {**capture.get("coverage", {}), **coverage}
    notes = capture.pop("table_notes", [])
    document = manual.build(capture)
    document["findings"].extend({"source": "table", "message": note} for note in notes)
    return document


def build_from_file(path: str, form_name: str = "", platform: str = "spreadsheet",
                    coverage: dict | None = None) -> dict:
    """Read a CSV of questions and assemble its IR in one call."""
    return build(read_rows(path), form_name=form_name, platform=platform, coverage=coverage)
