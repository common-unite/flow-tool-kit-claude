"""Read a PDF into ordered blocks: paragraphs, tick-box options, list items and tables.

Three poppler views are combined:

    pdfinfo              page count, whether the PDF is tagged, AcroForm presence
    pdfinfo -struct-text the tagged structure tree, in reading order. Page
                         headers and footers are artifacts and never appear in
                         it, so no running-text stripping is needed.
    pdftotext -bbox-layout  positioned lines: indentation, which the structure
                         tree does not carry (nested options), and the running
                         footer, the same line at the foot of every page.

The marker that carries the meaning of a tick-box option is the drawn box
itself: Word emits it as an empty text run at the start of the paragraph. That
empty leading run, not indentation or wording, is what makes a block an option.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
from dataclasses import dataclass, field

_NODE_RE = re.compile(r'^(?P<type>[A-Za-z][A-Za-z0-9]*)(?: \((?P<mode>block|inline)\))?:?(?: \[(?P<alt>.*))?$')
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Block:
    """One reading-order unit of the form."""

    kind: str  # "heading" | "paragraph" | "option" | "list_item" | "table" | "figure"
    text: str = ""
    indent: float | None = None
    rows: list[list[dict]] = field(default_factory=list)  # tables: [[{"header": bool, "text": str}]]


@dataclass
class PdfFormModel:
    path: str
    pages: int
    tagged: bool
    form_type: str  # "none" | "AcroForm" | "XFA"
    title: str
    blocks: list[Block] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    # The line printed at the foot of every page (an organisation or revision line), or None.
    footer: str | None = None


@dataclass
class Line:
    """One positioned line from ``pdftotext -bbox-layout``."""

    x: float
    text: str
    page: int = 1
    y: float = 0.0
    page_height: float = 0.0

    def __getitem__(self, index):  # (x, text), the shape older callers index
        return (self.x, self.text)[index]


# A link annotation inside a tagged paragraph prints as "Object 54 0"; it is not text.
_OBJECT_REFERENCE_RE = re.compile(r"\bObject \d+ \d+\s*")


def normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", _OBJECT_REFERENCE_RE.sub("", text or "")).strip()


def poppler_available() -> bool:
    """Whether poppler's pdfinfo and pdftotext are on the PATH."""
    return bool(shutil.which("pdfinfo") and shutil.which("pdftotext"))


def _run(arguments: list[str]) -> str:
    return subprocess.run(arguments, capture_output=True, text=True, check=True).stdout


def read_info(path: str) -> dict:
    info = {}
    for line in _run(["pdfinfo", path]).splitlines():
        key, _, value = line.partition(":")
        info[key.strip()] = value.strip()
    return info


@dataclass
class _Node:
    type: str
    children: list = field(default_factory=list)  # _Node or str


def parse_struct_text(text: str) -> _Node:
    """Parse ``pdfinfo -struct-text`` output into a tree.

    The format is two-space indented node headers (``P (block)``) and quoted
    text runs. An alt text on a Figure (``Figure ["..."]``) can span lines.
    """
    root = _Node("Root")
    stack: list[tuple[int, _Node]] = [(-1, root)]
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        if not raw.strip():
            continue
        depth = len(raw) - len(raw.lstrip(" "))
        body = raw.strip()
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1]
        if body.startswith("/"):
            continue  # a node attribute line (/ListNumbering /Disc), not content
        if body.startswith('"'):
            string = body
            while not (len(string) > 1 and string.endswith('"')) and index < len(lines):
                string += "\n" + lines[index].strip()
                index += 1
            parent.children.append(string[1:-1])
            continue
        match = _NODE_RE.match(body)
        if not match:
            parent.children.append(body)
            continue
        node = _Node(match.group("type"))
        alt = match.group("alt")
        if alt is not None and not alt.endswith('"]'):
            while index < len(lines) and not lines[index].rstrip().endswith('"]'):
                index += 1
            index += 1
        parent.children.append(node)
        stack.append((depth, node))
    return root


def _texts(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    runs = []
    for child in node.children:
        runs.extend(_texts(child))
    return runs


def _flatten(node: _Node, blocks: list[Block]) -> None:
    """Walk the tree in reading order and emit blocks by structure type."""
    for child in node.children:
        if isinstance(child, str):
            continue
        if child.type == "Table":
            rows = []
            for row in _descendants(child, "TR"):
                rows.append([
                    {"header": cell.type == "TH", "text": normalize(" ".join(_texts(cell)))}
                    for cell in row.children if isinstance(cell, _Node) and cell.type in ("TH", "TD")
                ])
            blocks.append(Block("table", rows=rows))
        elif child.type == "L":
            for item in child.children:
                if isinstance(item, _Node) and item.type == "LI":
                    body = [n for n in item.children if isinstance(n, _Node) and n.type == "LBody"]
                    text = normalize(" ".join(_texts(body[0] if body else item)))
                    if text:
                        blocks.append(Block("list_item", text=text))
        elif child.type in ("P", "H", "H1", "H2", "H3", "H4", "H5", "H6"):
            runs = _texts(child)
            text = normalize(" ".join(runs))
            if not text:
                continue
            # The drawn tick box is an empty leading run: that is the option marker.
            is_option = child.type == "P" and runs and runs[0] == "" and len(runs) > 1
            kind = "option" if is_option else ("heading" if child.type.startswith("H") else "paragraph")
            blocks.append(Block(kind, text=text))
        elif child.type == "Figure":
            blocks.append(Block("figure", text=normalize(" ".join(_texts(child)))))
        else:
            _flatten(child, blocks)


def _descendants(node: _Node, node_type: str) -> list[_Node]:
    found = []
    for child in node.children:
        if isinstance(child, _Node):
            if child.type == node_type:
                found.append(child)
            else:
                found.extend(_descendants(child, node_type))
    return found


def read_lines(path: str) -> list[Line]:
    """Positioned lines in page order: x for indentation lookup, page and y for the running footer."""
    return parse_bbox(_run(["pdftotext", "-bbox-layout", path, "-"]))


def parse_bbox(text: str) -> list[Line]:
    lines = []
    page, height = 0, 0.0
    for match in re.finditer(r'<page\b[^>]*height="([\d.]+)"|<line xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>(.*?)</line>', text, re.S):
        if match.group(1) is not None:
            page, height = page + 1, float(match.group(1))
            continue
        words = re.findall(r"<word[^>]*>(.*?)</word>", match.group(4), re.S)
        lines.append(Line(float(match.group(2)), normalize(html.unescape(" ".join(words))), max(page, 1),
                          float(match.group(3)), height))
    return lines


# A running footer sits in the bottom part of the page.
_FOOTER_BAND = 0.88


def running_footer(lines: list[Line], pages: int) -> str | None:
    """The line printed at the foot of every page, when the PDF has two pages or more.

    The same text on every page and in the bottom band of each one: an organisation, form name or revision line.
    A label that happens to repeat ("Phone:") sits higher up the page and is never taken for it.
    """
    if pages < 2:
        return None
    seen: dict[str, set[int]] = {}
    for line in lines:
        if len(line.text) >= 8 and line.page_height and line.y >= _FOOTER_BAND * line.page_height:
            seen.setdefault(line.text, set()).add(line.page)
    every = [text for text, on in seen.items() if len(on) == pages]
    return max(every, key=len) if every else None


def _assign_indents(blocks: list[Block], lines: list[Line]) -> None:
    """Give each option and paragraph the x position of its first line.

    Matching walks forward with a cursor so repeated labels (the same "Towns
    not listed" option under six regions) each find their own line.
    """
    cursor = 0
    for block in blocks:
        if block.kind not in ("option", "paragraph", "list_item") or not block.text:
            continue
        probe = block.text[:40]
        for position in range(cursor, len(lines)):
            if lines[position][1] and (lines[position][1].startswith(probe[: len(lines[position][1])]) or probe.startswith(lines[position][1][:40])):
                block.indent = lines[position][0]
                cursor = position + 1
                break


def parse_file(path: str) -> PdfFormModel:
    info = read_info(path)
    form_type = info.get("Form", "none") or "none"
    model = PdfFormModel(
        path=path,
        pages=int(info.get("Pages", "0") or 0),
        tagged=info.get("Tagged", "no") == "yes",
        form_type=form_type,
        title=info.get("Title", ""),
    )
    if model.tagged:
        root = parse_struct_text(_run(["pdfinfo", "-struct-text", path]))
        _flatten(root, model.blocks)
    else:
        model.findings.append(
            "The PDF is not tagged, so there is no structure tree: lists and tables are "
            "reconstructed from positioned lines only. Check every table and option list by hand."
        )
    lines = read_lines(path)
    model.footer = running_footer(lines, model.pages)
    if not model.tagged:
        for line in lines:
            if model.footer is None or line.text != model.footer:
                model.blocks.append(Block("paragraph", text=line.text, indent=line.x))
    _assign_indents(model.blocks, lines)
    return model
