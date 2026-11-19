"""Parse a FormAssembly field alias export into a resolver.

The alias export is the only input that maps a ``tfa_*`` id to its label and,
crucially, tells you whether that id is a *field* or one of a field's *options*.
Connector formulas and form conditions both reference option ids directly, so
every other parser resolves through this module.

Export shape (tab- or multi-space separated), in two phases::

    Alias    Definition                      <- system alias table
    FORM_NAME    The name of your form.
    ...

    Field Aliases                            <- phase marker

    Alias    Form Field
    Hidden Section                           <- section path, no id
    tfa_7731    Prefill                      <- field
    tfa_7732      - prefill                  <- option of the field above
    Application/Primary Contact/Name         <- nested section path
    tfa_11766    First Name:

Section path lines carry no id and use ``/`` to express nesting. Option lines
are distinguished by a leading ``-`` on the label, and belong to the most
recently seen field.
"""

from __future__ import annotations

import re

from ...conditions import describe_option
from dataclasses import dataclass, field as dataclass_field
from html.parser import HTMLParser

# Splits an alias line into id and label: a tab, or two-or-more spaces.
_SEPARATOR_RE = re.compile(r"\t+| {2,}")

# An option label begins with a dash once leading whitespace is stripped.
_OPTION_LABEL_RE = re.compile(r"^-\s*")

# Marks the transition from the system alias table to the field alias table.
_FIELD_PHASE_MARKER = "field aliases"

# Column headers that appear inside either table and carry no data.
_HEADER_LINES = {"alias definition", "alias form field"}


@dataclass
class AliasOption:
    """One selectable choice belonging to a field."""

    alias_id: str
    label: str
    field_id: str


@dataclass
class AliasField:
    """One form field, with its section path and any options."""

    alias_id: str
    label: str
    section_path: str
    options: list[AliasOption] = dataclass_field(default_factory=list)


@dataclass
class AliasExport:
    """Parsed alias export plus the lookups every other parser needs."""

    fields: dict[str, AliasField] = dataclass_field(default_factory=dict)
    options: dict[str, AliasOption] = dataclass_field(default_factory=dict)
    system_aliases: dict[str, str] = dataclass_field(default_factory=dict)
    section_paths: list[str] = dataclass_field(default_factory=list)
    findings: list[str] = dataclass_field(default_factory=list)

    def resolve(self, alias_id: str) -> dict | None:
        """Describe an id as a field or an option, or None if unknown.

        This is the call every other module makes. Option results carry their
        parent field so a condition or formula can be rendered in business
        language rather than as opaque ids.
        """
        # Accepts tfa_1, #tfa_1 and the condition grammar's `#tfa_1`.
        alias_id = alias_id.strip().strip("`").strip().lstrip("#").strip()
        if alias_id in self.fields:
            found = self.fields[alias_id]
            return {
                "kind": "field",
                "id": found.alias_id,
                "label": found.label,
                "section_path": found.section_path,
            }
        if alias_id in self.options:
            option = self.options[alias_id]
            parent = self.fields.get(option.field_id)
            return {
                "kind": "option",
                "id": option.alias_id,
                "label": option.label,
                "field_id": option.field_id,
                "field_label": parent.label if parent else None,
                "section_path": parent.section_path if parent else None,
            }
        if alias_id in self.system_aliases:
            return {
                "kind": "system",
                "id": alias_id,
                "label": self.system_aliases[alias_id],
            }
        return None

    def describe(self, alias_id: str) -> str:
        """Render an id as human-readable text, falling back to the raw id."""
        found = self.resolve(alias_id)
        if not found:
            return alias_id
        if found["kind"] == "option":
            return describe_option(found["field_label"], found["label"])
        return found["label"] or alias_id


class _AliasHtmlParser(HTMLParser):
    """Parse the alias page's HTML, which marks every row's role explicitly.

    The HTML export is preferable to the plain-text one: section paths carry
    ``class="field-path"`` and options carry ``class="field-choice"``, so no
    indentation or dash-prefix heuristics are needed. Path segments are split by
    ``<span class="path-separator">``.
    """

    def __init__(self, export: AliasExport):
        super().__init__(convert_charrefs=True)
        self.export = export
        self.in_field_phase = False
        self.heading: list[str] | None = None
        self.cells: list[tuple[str, list[str]]] | None = None
        self.cell_classes = ""
        self.cell_text: list[str] | None = None
        self.path_segments: list[str] = []
        self.in_path_separator = False
        self.current_field: AliasField | None = None
        self.current_section = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "h4":
            self.heading = []
        elif tag == "tr":
            self.cells = []
        elif tag in ("td", "th") and self.cells is not None:
            self.cell_classes = attributes.get("class", "")
            self.cell_text = []
            self.path_segments = []
        elif tag == "span" and "path-separator" in attributes.get("class", ""):
            # Segment break inside a section path - close the current segment.
            # The span's own "/" text is discarded on the closing tag, since a
            # segment can legitimately contain a slash ("Confirmation/Payment:").
            if self.cell_text is not None:
                self.path_segments.append("".join(self.cell_text).strip())
                self.cell_text = []
                self.in_path_separator = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h4":
            if self.heading is not None:
                title = "".join(self.heading).strip().lower()
                if title == _FIELD_PHASE_MARKER:
                    self.in_field_phase = True
            self.heading = None
        elif tag == "span" and self.in_path_separator:
            self.cell_text = []
            self.in_path_separator = False
        elif tag in ("td", "th") and self.cell_text is not None:
            self.cells.append((self.cell_classes, self.cell_text))
            self.cell_text = None
            self.cell_classes = ""
        elif tag == "tr" and self.cells is not None:
            self._finish_row(self.cells)
            self.cells = None

    def handle_data(self, data: str) -> None:
        if self.heading is not None:
            self.heading.append(data)
        elif self.cell_text is not None:
            self.cell_text.append(data)

    def _finish_row(self, cells: list[tuple[str, list[str]]]) -> None:
        if not cells:
            return

        classes, first_text = cells[0]

        # Section path row: one merged cell, segments split by the separator
        # spans that handle_starttag already flushed into path_segments.
        if "field-path" in classes:
            segments = list(self.path_segments) + ["".join(first_text).strip()]
            self.current_section = "/".join(
                segment for segment in segments if segment
            )
            self.export.section_paths.append(self.current_section)
            return

        if len(cells) < 2:
            return

        alias_id = "".join(first_text).strip()
        label_classes, label_text = cells[1]
        label = _clean_label("".join(label_text))
        if not alias_id or alias_id.lower() == "alias":
            return

        if not self.in_field_phase:
            self.export.system_aliases[alias_id] = label
            return

        if "field-choice" in label_classes:
            option_label = _OPTION_LABEL_RE.sub("", label).strip()
            if self.current_field is None:
                self.export.findings.append(
                    f"Option {alias_id} appears before any field; skipped."
                )
                return
            option = AliasOption(alias_id, option_label, self.current_field.alias_id)
            self.current_field.options.append(option)
            self.export.options[alias_id] = option
            return

        if alias_id in self.export.fields:
            self.export.findings.append(f"Duplicate field alias id {alias_id}.")
        # Labels are kept verbatim apart from whitespace normalization - some
        # fields genuinely have a blank label and are still mapped downstream.
        self.current_field = AliasField(alias_id, label, self.current_section)
        self.export.fields[alias_id] = self.current_field

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _clean_label(raw: str) -> str:
    """Normalize a label cell: strip non-breaking spaces and collapse runs."""
    return " ".join(raw.replace("\xa0", " ").split())


def parse_html(html_text: str) -> AliasExport:
    """Parse the alias page's HTML into an :class:`AliasExport`."""
    export = AliasExport()
    parser = _AliasHtmlParser(export)
    parser.feed(html_text)
    parser.close()
    return export


def parse(text: str) -> AliasExport:
    """Parse an alias export, detecting HTML or plain text automatically."""
    if "<td" in text or "field-choice" in text:
        return parse_html(text)
    return parse_text(text)


def parse_text(text: str) -> AliasExport:
    """Parse the plain-text alias export into an :class:`AliasExport`."""
    export = AliasExport()
    in_field_phase = False
    current_field: AliasField | None = None
    current_section = ""

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        normalized = " ".join(line.split()).lower()
        if normalized == _FIELD_PHASE_MARKER:
            in_field_phase = True
            continue
        if normalized in _HEADER_LINES:
            in_field_phase = in_field_phase or normalized == "alias form field"
            continue

        parts = _SEPARATOR_RE.split(line.strip(), maxsplit=1)
        alias_id = parts[0].strip()
        label = parts[1].strip() if len(parts) > 1 else ""

        # A line with no separator is a section path, not an alias.
        if len(parts) == 1:
            if in_field_phase:
                current_section = alias_id
                export.section_paths.append(current_section)
            continue

        if not in_field_phase:
            export.system_aliases[alias_id] = label
            continue

        # Options are indented with a leading dash and attach to the field above.
        if _OPTION_LABEL_RE.match(parts[1].lstrip()):
            option_label = _OPTION_LABEL_RE.sub("", parts[1].strip()).strip()
            if current_field is None:
                export.findings.append(
                    f"Option {alias_id} appears before any field; skipped."
                )
                continue
            option = AliasOption(alias_id, option_label, current_field.alias_id)
            current_field.options.append(option)
            export.options[alias_id] = option
            continue

        if alias_id in export.fields:
            export.findings.append(f"Duplicate field alias id {alias_id}.")
        current_field = AliasField(alias_id, label, current_section)
        export.fields[alias_id] = current_field

    return export


def parse_file(path: str) -> AliasExport:
    """Parse an alias export from disk."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read())
