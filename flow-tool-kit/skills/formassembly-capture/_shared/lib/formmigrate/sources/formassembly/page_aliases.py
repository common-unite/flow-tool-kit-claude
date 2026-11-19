"""Build an alias export from the public form page alone.

Use when the form owner's alias export is not available, such as prospect
research on public forms. The page carries every label, option and section
legend; it lacks only the system aliases, so ``FORM_NAME`` style ids stay
unresolved. Prefer the real alias export whenever it exists.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .aliases import AliasExport, AliasField, AliasOption

_TFA_RE = re.compile(r"^tfa_\d+$")


class _PageAliasParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.labels: dict[str, str] = {}
        self.field_order: list[str] = []
        self.option_parent: dict[str, str] = {}
        self.option_order: list[str] = []
        self.section_titles: dict[str, str] = {}
        self.section_parent: dict[str, str | None] = {}
        self.field_section: dict[str, str | None] = {}
        self.stack: list[tuple[str, str | None]] = []
        self.capture: str | None = None
        self.capture_text: list[str] = []
        self.select_id: str | None = None
        self.choices: list[tuple[str, int]] = []  # open <span class="choices" id="tfa_N"> groups and their stack depth, innermost last
        self.titles: dict[str, str] = {}      # an option's title attribute: the only label a matrix cell carries

    def _current_section(self) -> str | None:
        for tag, section_id in reversed(self.stack):
            if section_id: return section_id
        return None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id") or ""
        classes = (attributes.get("class") or "").split()
        section_id = None
        if tag in ("div", "fieldset") and "section" in classes and _TFA_RE.match(element_id):
            section_id = element_id
            self.section_parent[element_id] = self._current_section()
        if tag not in ("input", "br", "img", "hr", "meta", "link"): self.stack.append((tag, section_id))
        if tag == "span" and "choices" in classes and _TFA_RE.match(element_id): self.choices.append((element_id, len(self.stack) - 1))
        if tag in ("legend", "h2", "h3") and self._current_section() and self._current_section() not in self.section_titles:
            self._start_capture("section:" + self._current_section())
        if tag == "label":
            target = attributes.get("for") or attributes.get("data-tfa-check-label-for") or ""
            label_id = element_id[:-2] if element_id.endswith("-L") else ""
            target = target or label_id
            if _TFA_RE.match(target): self._start_capture("label:" + target)
        if tag == "select" and _TFA_RE.match(element_id):
            self.select_id = element_id
            self._add_field(element_id)
        if tag == "option" and self.select_id and _TFA_RE.match(element_id):
            self._add_option(element_id, self.select_id)
            self._start_capture("label:" + element_id)
        if tag in ("input", "textarea") and _TFA_RE.match(element_id):
            parent = attributes.get("data-tfa-parent-id")
            # Older forms leave data-tfa-parent-id off; the group is then the enclosing <span class="choices"> (seen on older live forms)
            if attributes.get("type") in ("radio", "checkbox") and not parent and self.choices: parent = self.choices[-1][0]
            if attributes.get("type") in ("radio", "checkbox") and attributes.get("title"): self.titles[element_id] = attributes["title"]
            if attributes.get("type") in ("radio", "checkbox") and parent:
                self._add_field(parent)
                self._add_option(element_id, parent)
            else:
                self._add_field(element_id)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "select": self.select_id = None
        if tag == "span" and self.choices:
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index][0] == "span":
                    if index == self.choices[-1][1]: self.choices.pop()
                    break
        if self.capture and tag in ("label", "option", "legend", "h2", "h3"): self._finish_capture()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.capture: self.capture_text.append(data)

    def _start_capture(self, key):
        if self.capture: self._finish_capture()
        self.capture, self.capture_text = key, []

    def _finish_capture(self):
        kind, _, target = self.capture.partition(":")
        text = " ".join("".join(self.capture_text).split())
        if text:
            if kind == "section": self.section_titles[target] = text
            elif target not in self.labels: self.labels[target] = text
        self.capture, self.capture_text = None, []

    def _add_field(self, field_id):
        if field_id in self.field_order: return
        self.field_order.append(field_id)
        self.field_section[field_id] = self._current_section()

    def _add_option(self, option_id, field_id):
        if option_id in self.option_parent: return
        self.option_parent[option_id] = field_id
        self.option_order.append(option_id)


def _section_path(parser: _PageAliasParser, section_id: str | None) -> str:
    names = []
    while section_id:
        names.append(parser.section_titles.get(section_id, section_id))
        section_id = parser.section_parent.get(section_id)
    return "/".join(reversed(names))


def parse(html_text: str) -> AliasExport:
    parser = _PageAliasParser()
    parser.feed(html_text)
    export = AliasExport()
    for field_id in parser.field_order:
        if field_id in parser.option_parent: continue
        path = _section_path(parser, parser.field_section.get(field_id))
        export.fields[field_id] = AliasField(field_id, parser.labels.get(field_id, ""), path)
        if path and path not in export.section_paths: export.section_paths.append(path)
    for option_id in parser.option_order:
        option = AliasOption(option_id, parser.labels.get(option_id) or parser.titles.get(option_id, ""), parser.option_parent[option_id])
        export.options[option_id] = option
        if option.field_id in export.fields: export.fields[option.field_id].options.append(option)
    export.findings.append("Aliases built from the public form page; system aliases are not available.")
    return export


def parse_file(path: str) -> AliasExport:
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read())
