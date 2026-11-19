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
"""

from __future__ import annotations

from . import adapter  # noqa: F401
