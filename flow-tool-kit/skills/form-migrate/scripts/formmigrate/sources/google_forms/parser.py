"""Read ``FB_PUBLIC_LOAD_DATA_`` out of a saved Google Form page.

Positions used (each checked before it is read; a missing one is a finding):

    data[1][0]      form description
    data[1][1]      items, in page order
    data[1][8]      form title
    data[3]         document name (fallback title)

    item[0]         item id (section ids are what branches point at)
    item[1]         title
    item[2]         description (help text)
    item[3]         type code (TYPE_CODES)
    item[4]         answer entries: [entry_id, options, required, extra, ...]
                    a grid has one entry per row, its row label in extra[0]
    option[0]       choice label
    option[2]       the section item id a "go to section" choice jumps to;
                    a negative number means "submit form"
    option[4]       1 for the "Other" choice with a text box
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field as dataclass_field

TYPE_CODES = {
    0: "short_answer",
    1: "paragraph",
    2: "multiple_choice",
    3: "dropdown",
    4: "checkboxes",
    5: "linear_scale",
    6: "title_and_description",
    7: "grid",
    8: "section",
    9: "date",
    10: "time",
    11: "image",
    12: "video",
    13: "file_upload",
    18: "rating",
}

_VAR_RE = re.compile(r"FB_PUBLIC_LOAD_DATA_\s*=\s*", re.S)


class GoogleFormError(ValueError):
    """The page holds no readable form data."""


@dataclass
class Choice:
    label: str
    go_to: int | None = None
    is_other: bool = False


@dataclass
class Question:
    item_id: str
    entry_id: str
    title: str
    description: str
    kind: str
    required: bool
    choices: list[Choice] = dataclass_field(default_factory=list)
    row_label: str = ""
    scale_labels: list[str] = dataclass_field(default_factory=list)
    section: str = ""


@dataclass
class Section:
    item_id: str
    title: str
    description: str = ""


@dataclass
class GoogleFormModel:
    title: str = ""
    description: str = ""
    sections: list[Section] = dataclass_field(default_factory=list)
    questions: list[Question] = dataclass_field(default_factory=list)
    content_blocks: list[dict] = dataclass_field(default_factory=list)
    images: list[dict] = dataclass_field(default_factory=list)
    findings: list[str] = dataclass_field(default_factory=list)


def extract_data(page: str):
    """The decoded ``FB_PUBLIC_LOAD_DATA_`` array from the page text."""
    match = _VAR_RE.search(page)
    if not match:
        raise GoogleFormError(
            "No FB_PUBLIC_LOAD_DATA_ in this page. Save the public form page "
            "itself (the viewform address), not a fetched text version.")
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(page[match.end():])
    except ValueError as error:
        raise GoogleFormError(f"FB_PUBLIC_LOAD_DATA_ is not readable JSON: {error}") from error
    return data


def _at(node, *path):
    for index in path:
        if not isinstance(node, list) or index >= len(node):
            return None
        node = node[index]
    return node


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _choices(raw) -> list[Choice]:
    out = []
    for option in raw or []:
        if not isinstance(option, list) or not option:
            continue
        go_to = option[2] if len(option) > 2 and isinstance(option[2], int) else None
        is_other = bool(len(option) > 4 and option[4] == 1)
        label = _text(option[0]) or ("Other" if is_other else "")
        out.append(Choice(label=label, go_to=go_to, is_other=is_other))
    return out


def parse(page: str) -> GoogleFormModel:
    data = extract_data(page)
    model = GoogleFormModel()
    model.title = _text(_at(data, 1, 8)) or _text(_at(data, 3))
    model.description = _text(_at(data, 1, 0))
    items = _at(data, 1, 1)
    if not isinstance(items, list):
        raise GoogleFormError("The form data has no item list at data[1][1].")

    first = Section(item_id="", title=model.title or "Page 1", description=model.description)
    model.sections.append(first)
    current = first
    for item in items:
        if not isinstance(item, list) or len(item) < 4:
            model.findings.append(f"An item with too few parts was skipped: {str(item)[:80]}")
            continue
        item_id = str(item[0])
        title = _text(item[1])
        description = _text(item[2])
        code = item[3]
        kind = TYPE_CODES.get(code)
        if kind is None:
            model.findings.append(
                f"Item {item_id} \"{title}\" has unknown type code {code!r}; read as short text. "
                "Check it on the live form.")
            kind = "short_answer"
        if kind == "section":
            current = Section(item_id=item_id, title=title or f"Section {len(model.sections) + 1}",
                              description=description)
            model.sections.append(current)
            continue
        if kind == "title_and_description":
            model.content_blocks.append({"section": current.title, "title": title, "text": description})
            continue
        if kind in ("image", "video"):
            model.images.append({"id": item_id, "kind": kind, "title": title, "section": current.title})
            continue
        entries = item[4] if len(item) > 4 and isinstance(item[4], list) else []
        if not entries:
            model.findings.append(f"Question {item_id} \"{title}\" has no answer entry; skipped.")
            continue
        for entry in entries:
            if not isinstance(entry, list) or not entry:
                continue
            extra = _at(entry, 3)
            question = Question(
                item_id=item_id,
                entry_id=str(entry[0]),
                title=title,
                description=description,
                kind=kind,
                required=_at(entry, 2) == 1,
                choices=_choices(_at(entry, 1)),
                section=current.title,
            )
            if kind == "grid":
                question.row_label = _text(_at(extra, 0)) if isinstance(extra, list) else ""
            if kind == "linear_scale" and isinstance(extra, list):
                question.scale_labels = [_text(v) for v in extra if _text(v)]
            model.questions.append(question)
    return model
