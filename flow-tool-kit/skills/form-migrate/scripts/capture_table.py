#!/usr/bin/env python3
"""Read a spreadsheet of questions (saved as CSV) into capture.json and ir.json. Standard library only.

    python3 <skill>/scripts/capture_table.py <questions.csv> <out_dir> ["Form Name"] [--no-conditions]

One row per question; the columns are described in scripts/formmigrate/sources/table/adapter.py and
references/sources/table.md (Question is the only one needed). Writes <out_dir>/capture.json, the same
hand-written capture the manual adapter reads, so it can be corrected and rebuilt, and <out_dir>/ir.json.
--no-conditions declares that someone checked and the form has no show-and-hide rules; without it, a sheet
with no Show When column leaves conditions unknown. An .xlsx is not read: save the sheet as CSV first.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formmigrate import ir  # noqa: E402
from formmigrate.sources.manual import adapter as manual  # noqa: E402
from formmigrate.sources.table import adapter as table  # noqa: E402


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    no_conditions = "--no-conditions" in argv
    argv = [arg for arg in argv if arg != "--no-conditions"]
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path, out_dir = argv[0], argv[1]
    form_name = argv[2] if len(argv) == 3 else os.path.splitext(os.path.basename(path))[0]
    try:
        capture = table.to_capture(table.read_rows(path), form_name=form_name)
    except (table.TableError, OSError) as error:
        print(f"Not read: {error}", file=sys.stderr)
        return 1
    if no_conditions:
        capture.setdefault("coverage", {})["conditions"] = "none_exist"
    notes = capture.pop("table_notes", [])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "capture.json"), "w", encoding="utf-8") as handle:
        json.dump(capture, handle, indent=2, ensure_ascii=False)
    document = manual.build(capture)
    document["findings"].extend({"source": "table", "message": note} for note in notes)
    with open(os.path.join(out_dir, "ir.json"), "w", encoding="utf-8") as handle:
        handle.write(ir.to_json(document))
    for note in notes:
        print(f"NOTE: {note}", file=sys.stderr)
    print(f"{len(document['fields'])} questions on {len(document['structure'])} pages; "
          f"wrote capture.json and ir.json in {out_dir}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
