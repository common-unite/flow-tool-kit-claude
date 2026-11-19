#!/usr/bin/env python3
"""Read a Word (.docx) form's text, tables and form controls in document order. Standard library only.

    python3 <skill>/scripts/docx_text.py <form.docx> <out_dir>

Writes <out_dir>/docx-text.txt: every paragraph and table in reading order, with each form control drawn
inline where it sits:

    # Heading                  a paragraph styled as a heading (## for Heading 2, and so on)
    - item                     a bulleted or numbered list item
    | cell | cell |            a table row
    [ ] / [x]                  a tick box (a content control, a legacy check box field, or a drawn box symbol)
    [text: Tag]                a text content control or legacy text field, with its title, tag or name
    [choice: A | B | C]        a drop-down or combo box with its entries
    [date: Tag]                a date picker

and <out_dir>/docx-controls.json with each control's kind, title, tag, choices, checked state and the
paragraph it sits in. Prints what it found.

A .docx is a zip of XML; only word/document.xml is read (headers, footers and comments are not). Use the
result the way pdf_text.py's is used: read docx-text.txt, transcribe the form into capture.json for the
manual adapter (platform "word"), and mark anything the document does not settle (single or several
answers for a list of boxes, required questions) as unknown in the capture. A .doc file (Word 97 to 2003)
is not a zip: open it in Word or another editor and save it as .docx first.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"

# Characters Word and most editors use to draw a tick box in plain text.
BOX_EMPTY = {"☐", "□", "❏", "⬜"}
BOX_TICKED = {"☑", "☒", "■", "✓", "✔", "✗"}
# Wingdings and Segoe UI Symbol code points for drawn boxes (w:sym w:char).
SYMBOL_BOXES = {"F06F": "[ ]", "F0A8": "[ ]", "F071": "[ ]", "F0FE": "[x]", "F078": "[x]", "F0FD": "[x]",
                "2610": "[ ]", "2611": "[x]", "2612": "[x]"}


class DocxError(ValueError):
    """The file is not a Word .docx document."""


def _attr(element, name: str, namespace: str = W) -> str:
    if element is None:
        return ""
    return element.get(namespace + name, "") or ""


class _Reader:
    def __init__(self):
        self.lines: list[str] = []
        self.controls: list[dict] = []
        self.paragraph_index = 0
        self.field_stack: list[dict | None] = []

    # --- controls -----------------------------------------------------------

    def _control(self, kind: str, title: str = "", tag: str = "", choices=None, checked=None) -> str:
        control = {"kind": kind, "title": title, "tag": tag, "choices": list(choices or []),
                   "paragraph": self.paragraph_index}
        if checked is not None:
            control["checked"] = checked
        self.controls.append(control)
        name = title or tag
        if kind == "checkbox":
            return "[x]" if checked else "[ ]"
        if kind == "choice":
            return f"[choice{': ' + name if name else ''}: {' | '.join(control['choices'])}]"
        return f"[{kind}{': ' + name if name else ''}]"

    def _sdt_marker(self, properties) -> str | None:
        """A content control's marker, or None for a plain (rich text or unknown) one."""
        title = _attr(properties.find(W + "alias"), "val")
        tag = _attr(properties.find(W + "tag"), "val")
        checkbox = properties.find(W14 + "checkbox")
        if checkbox is not None:
            checked = _attr(checkbox.find(W14 + "checked"), "val", W14) in ("1", "true")
            return self._control("checkbox", title, tag, checked=checked)
        for kind in ("dropDownList", "comboBox"):
            listing = properties.find(W + kind)
            if listing is not None:
                # An entry with an empty value is the "Choose an item." prompt, not a choice.
                choices = [_attr(item, "displayText") or _attr(item, "value")
                           for item in listing.findall(W + "listItem") if _attr(item, "value")]
                return self._control("choice", title, tag, choices=[c for c in choices if c])
        if properties.find(W + "date") is not None:
            return self._control("date", title, tag)
        if properties.find(W + "text") is not None or title or tag:
            return self._control("text", title, tag)
        return None

    def _legacy_field(self, form_data) -> str:
        """A legacy form field (FORMTEXT, FORMCHECKBOX, FORMDROPDOWN) from its w:ffData."""
        name = _attr(form_data.find(W + "name"), "val")
        checkbox = form_data.find(W + "checkBox")
        if checkbox is not None:
            default = checkbox.find(W + "default")
            checked = checkbox.find(W + "checked")
            state = checked if checked is not None else default
            ticked = state is not None and _attr(state, "val") in ("", "1", "true")
            if state is not None and checked is None and _attr(state, "val") in ("0", "false"):
                ticked = False
            return self._control("checkbox", name, checked=ticked)
        dropdown = form_data.find(W + "ddList")
        if dropdown is not None:
            choices = [_attr(entry, "val") for entry in dropdown.findall(W + "listEntry")]
            return self._control("choice", name, choices=choices)
        return self._control("text", name)

    # --- text ---------------------------------------------------------------

    def _runs(self, element) -> str:
        """The text of a paragraph or inline control, with controls drawn where they sit."""
        parts: list[str] = []
        for child in element:
            tag = child.tag
            if tag == W + "r":
                parts.append(self._run(child))
            elif tag == W + "sdt":
                properties = child.find(W + "sdtPr")
                marker = self._sdt_marker(properties) if properties is not None else None
                content = child.find(W + "sdtContent")
                inner = self._runs(content) if content is not None else ""
                # A control's marker replaces its placeholder text (and a tick box's own glyph).
                parts.append(marker or inner)
            elif tag in (W + "hyperlink", W + "smartTag", W + "ins", W + "fldSimple"):
                parts.append(self._runs(child))
        return "".join(parts)

    def _run(self, run) -> str:
        parts: list[str] = []
        for child in run:
            tag = child.tag
            if tag == W + "fldChar":
                kind = _attr(child, "fldCharType")
                if kind == "begin":
                    form_data = child.find(W + "ffData")
                    if form_data is not None:
                        parts.append(self._legacy_field(form_data))
                        self.field_stack.append({"hide": True})
                    else:
                        self.field_stack.append(None)
                elif kind == "end" and self.field_stack:
                    self.field_stack.pop()
                continue
            # The result text of a legacy form field (its five spaces or default) is replaced by the marker.
            if self.field_stack and self.field_stack[-1]:
                continue
            if tag == W + "t":
                text = child.text or ""
                for glyph in BOX_EMPTY:
                    text = text.replace(glyph, "[ ]")
                for glyph in BOX_TICKED:
                    text = text.replace(glyph, "[x]")
                parts.append(text)
            elif tag == W + "tab":
                parts.append("\t")
            elif tag in (W + "br", W + "cr"):
                parts.append("\n")
            elif tag == W + "sym":
                parts.append(SYMBOL_BOXES.get(_attr(child, "char").upper()[-4:], ""))
        return "".join(parts)

    def paragraph(self, element) -> str:
        self.paragraph_index += 1
        text = self._runs(element).strip()
        properties = element.find(W + "pPr")
        if properties is not None and text:
            style = _attr(properties.find(W + "pStyle"), "val").lower()
            if style.startswith("heading") and style[7:].isdigit():
                return "#" * int(style[7:]) + " " + text
            if style == "title":
                return "# " + text
            if properties.find(W + "numPr") is not None or style.startswith("list"):
                return "- " + text
        return text

    def table(self, element) -> list[str]:
        rows = []
        for row in element.findall(W + "tr"):
            cells = []
            for cell in row.findall(W + "tc"):
                texts = []
                for child in cell:
                    if child.tag == W + "p":
                        texts.append(self.paragraph(child))
                    elif child.tag == W + "tbl":
                        texts.append(" / ".join(self.table(child)))
                    elif child.tag == W + "sdt":
                        texts.extend(self.block(child))
                cells.append(" ".join(text for text in texts if text))
            rows.append("| " + " | ".join(cells) + " |")
        return rows

    def block(self, element) -> list[str]:
        """Lines for a body-level element: a paragraph, a table, or a block content control."""
        if element.tag == W + "p":
            return [self.paragraph(element)]
        if element.tag == W + "tbl":
            return self.table(element) + [""]
        if element.tag == W + "sdt":
            properties = element.find(W + "sdtPr")
            marker = self._sdt_marker(properties) if properties is not None else None
            content = element.find(W + "sdtContent")
            lines = []
            for child in (content if content is not None else []):
                lines.extend(self.block(child))
            if marker:
                lines = [marker] if not any(lines) else [marker + " " + " ".join(l for l in lines if l)]
            return lines
        return []


def read(path: str) -> tuple[str, list[dict]]:
    """The document's text in reading order, and its form controls."""
    try:
        with zipfile.ZipFile(path) as archive:
            data = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as error:
        raise DocxError(
            f"{path} is not a Word .docx document ({error}). A .doc file must be saved as .docx first."
        ) from error
    # Word never writes a DOCTYPE; refusing one rules out entity expansion tricks in a file from elsewhere.
    if b"<!DOCTYPE" in data[:4096].upper() or b"<!ENTITY" in data.upper():
        raise DocxError(f"{path} declares a DOCTYPE or entities, which a Word document never does; not read.")
    body = ElementTree.fromstring(data).find(W + "body")
    reader = _Reader()
    lines: list[str] = []
    for element in (body if body is not None else []):
        lines.extend(reader.block(element))
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n", reader.controls


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    path, out_dir = argv
    try:
        text, controls = read(path)
    except DocxError as error:
        print(str(error), file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "docx-text.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)
    with open(os.path.join(out_dir, "docx-controls.json"), "w", encoding="utf-8") as handle:
        json.dump(controls, handle, indent=1, ensure_ascii=False)
    kinds: dict[str, int] = {}
    for control in controls:
        kinds[control["kind"]] = kinds.get(control["kind"], 0) + 1
    summary = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items())) or "none"
    print(f"lines: {len(text.splitlines())}; form controls: {summary}. "
          "Next: transcribe docx-text.txt into capture.json (platform \"word\").")
    return 0


if __name__ == "__main__":
    sys.exit(main())
