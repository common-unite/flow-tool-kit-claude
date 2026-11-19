#!/usr/bin/env python3
"""Read a PDF form's text and fillable fields with whatever this machine or sandbox has.

    python3 <skill>/scripts/pdf_text.py <form.pdf> <out_dir>

Writes <out_dir>/pdf-text.txt (the page text, page by page) and, when the PDF has fillable fields and pypdf is
installed, <out_dir>/pdf-fields.json (each field's name, question text, kind, required flag, choices and page).
Prints which tools it used, and says plainly when pypdf is missing, because a fillable PDF's boxes are then
not read at all.

Order: poppler's pdftotext, then the pypdf library. Use this when the pdf adapter cannot run (no poppler and
no fillable fields, common in a chat sandbox): read pdf-text.txt and pdf-fields.json, transcribe the form
into capture.json for the manual adapter, and declare coverage hand_authored. The pdf adapter reads fillable
fields itself whenever pypdf is installed, with or without poppler.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate.sources.pdf import widgets  # noqa: E402


def text_with_poppler(path: str) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    done = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def _pypdf():
    try:
        import pypdf  # type: ignore
        return pypdf
    except ImportError:
        return None


def text_with_pypdf(path: str) -> str | None:
    pypdf = _pypdf()
    if pypdf is None:
        return None
    reader = pypdf.PdfReader(path)
    return "\f".join((page.extract_text() or "") for page in reader.pages)


def fillable_fields(path: str) -> list[dict] | None:
    """Fillable fields: name, question text, kind, required, choices and page. None when pypdf is missing."""
    read = widgets.read(path)
    return None if read is None else read["fields"]


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    path, out_dir = argv
    os.makedirs(out_dir, exist_ok=True)
    text, tool = text_with_poppler(path), "pdftotext"
    if text is None:
        text, tool = text_with_pypdf(path), "pypdf"
    if text is None:
        print("No PDF text tool here (neither poppler nor pypdf). In chat, read the PDF directly and "
              "transcribe it into capture.json; declare coverage hand_authored.", file=sys.stderr)
        return 1
    with open(os.path.join(out_dir, "pdf-text.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)
    fields = fillable_fields(path)
    if fields:
        with open(os.path.join(out_dir, "pdf-fields.json"), "w", encoding="utf-8") as handle:
            json.dump(fields, handle, indent=1)
    print(f"text: {tool}; fillable fields: "
          + ("NOT READ: pypdf is not installed, so a fillable PDF's boxes are missing from this read "
             "(pip install pypdf, then run again)" if fields is None else str(len(fields)))
          + f"; poppler for the full pdf adapter: {'yes' if shutil.which('pdfinfo') else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
