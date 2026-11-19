"""Find a date asked as separate Month, Day and Year questions, and say which date it is.

Some forms ask one date as three questions, often three lists labelled only Month, Day and Year under a heading or a
text block that names the date ("Date of Birth:"). Read one at a time they are three unrelated questions: the plan
proposes three new fields, and a date of birth is never recognised as sensitive. ``groups(document)`` finds each
trio by its labels and grouping, never by a source's ids, and names the date from the nearest context, first found:

1. words the three labels share besides the part ("Birth Month", "Birth Day", "Birth Year");
2. the parts' help text, when it names a date;
3. the trio's own section title, when it names a date (a "Date of Birth" fieldset);
4. a short text block that names a date, in the trio's section or the section around it: the first of the two that
   holds any text block decides, and only when it holds exactly one such block and no other trio.

A trio is three questions next to each other in one section: one Month, one Day and one Year, in any order. Only a
context that says birth makes it a date of birth; any other trio is just a date, and one with no context is "Date".
``sensitive.py`` flags a date of birth trio like a single date of birth question, and ``fieldplan.py`` plans each
trio as one date question on its first part, with the other two folded into it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field

PARTS = ("Month", "Day", "Year")
_PART_WORDS = {"month": "Month", "mo": "Month", "mm": "Month", "day": "Day", "dd": "Day",
               "year": "Year", "yr": "Year", "yy": "Year", "yyyy": "Year"}
# Words that say nothing about which date: "Select the month", "Date of Birth (Day)".
_FILLER = {"the", "of", "your", "a", "an", "select", "choose", "enter", "please", "pick", "date", "s"}
_NOT_A_PART = {"textarea", "file", "checkbox", "hidden", "password"}
_WORD = re.compile(r"[a-z0-9]+")
_NAMES_A_DATE = re.compile(r"\b(dates?|birth|birthday|born|dob)\b", re.I)
BIRTH = re.compile(r"\bbirth(day|date)?\b|\bdob\b|\bborn\b", re.I)
_MAX_CONTEXT_WORDS = 8
_ID_SEGMENT = re.compile(r"^(tfa_\d+|page \d+)$", re.I)


@dataclass
class DateGroup:
    """One date asked in parts. ``ids`` in form order; the first is the question the plan keeps."""

    ids: list[str]
    parts: dict[str, str]
    title: str
    birth: bool
    context: str = ""
    labels: list[str] = dataclass_field(default_factory=list)

    @property
    def anchor(self) -> str:
        return self.ids[0]

    @property
    def folded(self) -> list[str]:
        return self.ids[1:]

    @property
    def question(self) -> str:
        """How the date reads in findings and questions: the date, then how the source asks it."""
        return f"{self.title} (asked as {', '.join(self.labels[:-1])} and {self.labels[-1]})"


def _part(entry: dict) -> tuple[str, tuple[str, ...]] | None:
    """(part, the label's other words) when the question asks one part of a date, else None."""
    if (entry.get("input_type") or "") in _NOT_A_PART:
        return None
    words = _WORD.findall((entry.get("label") or "").lower())
    parts = [w for w in words if w in _PART_WORDS]
    if len(parts) != 1:
        return None
    rest = tuple(w for w in words if w not in _PART_WORDS and w not in _FILLER)
    return (_PART_WORDS[parts[0]], rest) if len(rest) <= 4 else None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).strip(" :*-")


def _names_a_date(text: str) -> bool:
    text = _clean(text)
    return bool(text) and len(text.split()) <= _MAX_CONTEXT_WORDS and bool(_NAMES_A_DATE.search(text))


def _trios(fields: list[dict]) -> list[tuple[list[dict], tuple[str, ...]]]:
    found = []
    index = 0
    while index + 3 <= len(fields):
        window = fields[index:index + 3]
        read = [_part(entry) for entry in window]
        same_section = len({entry.get("section_path") or "" for entry in window}) == 1
        if all(read) and same_section and {r[0] for r in read} == set(PARTS):
            qualifiers = {r[1] for r in read if r[1]}
            if len(qualifiers) <= 1:
                found.append((window, next(iter(qualifiers), ())))
                index += 3
                continue
        index += 1
    return found


def _section_title(path: str) -> str:
    named = [segment for segment in (path or "").split("/") if segment and not _ID_SEGMENT.match(segment)]
    return named[-1] if named else ""


def _text_block_contexts(document: dict, trios: list[list[dict]]) -> dict[int, str]:
    """Trio index -> the text block that names its date: the last way a date is named, in the module docstring."""
    parents = {node.get("id"): node.get("parent_id") for node in document.get("structure") or []}
    blocks: dict[str, list[dict]] = {}
    for block in (document.get("form") or {}).get("content_blocks") or []:
        blocks.setdefault(block.get("section"), []).append(block)
    claims: dict[str, list[int]] = {}
    for index, trio in enumerate(trios):
        section = trio[0].get("section_id")
        for _ in range(2):
            if not section:
                break
            here = blocks.get(section) or []
            if here:
                naming = [b for b in here if _names_a_date(b.get("text") or b.get("title") or "")]
                if len(naming) == 1:
                    claims.setdefault(naming[0].get("id"), []).append(index)
                break
            section = parents.get(section)
    by_id = {b.get("id"): b for group in blocks.values() for b in group}
    return {owners[0]: _clean(by_id[block_id].get("text") or by_id[block_id].get("title") or "")
            for block_id, owners in claims.items() if len(owners) == 1}


def groups(document: dict) -> list[DateGroup]:
    """Every date the form asks as Month, Day and Year, in form order."""
    trios = _trios(document.get("fields") or [])
    from_blocks = _text_block_contexts(document, [trio for trio, _ in trios])
    found = []
    for index, (trio, qualifier) in enumerate(trios):
        help_text = next((_clean(e.get("help_text") or "") for e in trio if _names_a_date(e.get("help_text") or "")),
                         "")
        section = _section_title(trio[0].get("section_path") or "")
        context = (" ".join(qualifier) or help_text or (section if _names_a_date(section) else "")
                   or from_blocks.get(index, ""))
        birth = bool(BIRTH.search(context))
        if birth:
            title = "Date of Birth"
        elif context:
            title = context.title() if context == " ".join(qualifier) else context
            title = title if re.search(r"\bdates?\b", title, re.I) else f"{title} Date"
        else:
            title = "Date"
        found.append(DateGroup(
            ids=[e["id"] for e in trio], parts={_part(e)[0]: e["id"] for e in trio}, title=title, birth=birth,
            context=context, labels=[(e.get("label") or "").strip() for e in trio]))
    return found


def as_date_question(entry: dict, group: DateGroup) -> dict:
    """The kept part read as the one date question it stands for: the date's name, a date input, no options."""
    return {**entry, "label": group.title, "input_type": "date", "validation": ["date"], "options": []}
