"""Parse a Claude Design ``.dc.html`` file.

The format is unusually good to migrate from, because a question is not
reconstructed from markup - it is **declared**::

    <dc-import name="Choices" label="What worked well? Choose all that apply."
                options="Food and drinks|Music|Kids' activities"
                multi="{{ true }}"></dc-import>

Every field is one `<dc-import>` carrying its label, options, and flags as
attributes. There is no label-association guessing and no choice-group
reconstruction, which are the two things that make raw HTML fragile.

Two file kinds live in a project and both matter:

* **Component definitions** (``Field.dc.html``, ``Choices.dc.html``) declare a
  prop schema in the ``data-props`` attribute of their ``<script
  type="text/x-dc">`` block. That schema is the authoritative vocabulary.
* **Form instances** (``01 Post-Event Feedback.dc.html``) import those
  components with real values.

**Classify by props, never by component name.** ``Field``/``Choices``/``Scale``
is one project's vocabulary; the next kit calls them ``TextInput``/``Picker``/
``Rating``. A component that accepts ``options`` is a choice question whatever
it is called. Branching on the name is branching on element kind, which is the
mistake that produced seven silent bugs in the FormAssembly parser.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field as dataclass_field
from html.parser import HTMLParser

# {{ true }} / {{ false }} / {{ 5 }} - a literal binding in an attribute value.
_BINDING_RE = re.compile(r"^\s*\{\{\s*(.*?)\s*\}\}\s*$")

# Attributes that are preview/layout hints for the design canvas, not form data.
_HINT_ATTR_PREFIX = "hint-"

# Props every component in this family shares; not distinguishing evidence.
_COMMON_PROPS = {"label", "hint", "required", "placeholder", "name"}

# Options are pipe-delimited, matching the components' own split('|').
_OPTION_SEPARATOR = "|"


@dataclass
class DcComponent:
    """A component definition and its declared prop schema."""

    name: str
    props: dict = dataclass_field(default_factory=dict)

    @property
    def prop_names(self) -> set[str]:
        return {key for key in self.props if not key.startswith("$")}

    def enum_values(self, prop: str) -> list[str]:
        entry = self.props.get(prop) or {}
        return list(entry.get("options") or [])


@dataclass
class DcField:
    """One `<dc-import>` - a single question on the form."""

    component: str
    attributes: dict = dataclass_field(default_factory=dict)
    condition_group: str | None = None

    def attr(self, name: str, default=None):
        """Read an attribute case-insensitively.

        ``html.parser`` LOWERCASES every attribute name, so a camelCase prop
        like ``lowLabel`` is stored as ``lowlabel``. Looking it up by its source
        spelling silently returns None, and the scale end labels vanish -- which
        is exactly what tells an agreement battery apart from a satisfaction
        scale, and therefore whether the packaged Agreement_Question slots fit.
        """
        return self.attributes.get(name.lower(), default)

    @property
    def label(self) -> str:
        return str(self.attr("label") or "").strip()

    @property
    def options(self) -> list[str]:
        raw = self.attr("options")
        if not isinstance(raw, str) or not raw.strip():
            return []
        return [part.strip() for part in raw.split(_OPTION_SEPARATOR) if part.strip()]


@dataclass
class DcModel:
    """Everything one .dc.html file yields."""

    title: str = ""
    eyebrow: str = ""
    description: str = ""
    fields: list[DcField] = dataclass_field(default_factory=list)
    images: list[str] = dataclass_field(default_factory=list)
    scripts: list[str] = dataclass_field(default_factory=list)
    component: DcComponent | None = None
    condition_groups: dict[str, int] = dataclass_field(default_factory=dict)
    findings: list[str] = dataclass_field(default_factory=list)

    @property
    def is_component_definition(self) -> bool:
        """A file that declares props and imports nothing is a definition."""
        return self.component is not None and not self.fields


def _coerce(value: str):
    """Turn an attribute value into a Python value.

    ``multi="{{ true }}"`` is a binding to a literal, and reading it as the
    STRING "{{ true }}" makes every boolean flag truthy - including the ones
    explicitly set to false.
    """
    if value is None:
        return None
    match = _BINDING_RE.match(value)
    if not match:
        return value
    inner = match.group(1)
    if inner in ("true", "false"):
        return inner == "true"
    if inner.lstrip("-").isdigit():
        return int(inner)
    # A binding to an expression, not a literal: its value is only known at
    # render time, so report the expression rather than inventing a value.
    return {"__binding__": inner}


class _DcParser(HTMLParser):
    """Walks a .dc.html file, tracking sc-if nesting around dc-imports."""

    def __init__(self, model: DcModel):
        super().__init__(convert_charrefs=True)
        self.model = model
        self.condition_stack: list[str] = []
        self.script_attrs: dict | None = None
        self.script_buffer: list[str] = []
        self.text_blocks: list[str] = []
        self.text_buffer: list[str] | None = None
        self.depth_in_header = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}

        if tag == "script":
            self.script_attrs = attributes
            self.script_buffer = []
            return

        if tag == "img":
            source = attributes.get("src", "").strip()
            if source:
                self.model.images.append(source)
            return

        if tag == "sc-if":
            # The sc-if's `value` names the flag that governs it. Keep the whole
            # binding: `isForm` and `isDone` are the form/thank-you state
            # toggle, while anything else is candidate field logic.
            self.condition_stack.append(str(attributes.get("value", "")).strip())
            return

        if tag == "dc-import":
            self._record_import(attributes)
            return

        # Header prose: the eyebrow, title and intro live in plain divs.
        if tag == "div" and self.text_buffer is None:
            self.text_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._finish_script()
            return
        if tag == "sc-if" and self.condition_stack:
            self.condition_stack.pop()
            return
        if tag == "div" and self.text_buffer is not None:
            text = " ".join("".join(self.text_buffer).split())
            self.text_buffer = None
            if text and len(self.text_blocks) < 8:
                self.text_blocks.append(text)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "img":
            source = attributes.get("src", "").strip()
            if source:
                self.model.images.append(source)
        elif tag == "dc-import":
            self._record_import(attributes)

    def handle_data(self, data: str) -> None:
        if self.script_attrs is not None:
            self.script_buffer.append(data)
        elif self.text_buffer is not None:
            self.text_buffer.append(data)

    def _record_import(self, attributes: dict) -> None:
        component = str(attributes.get("name") or "").strip()
        values = {
            key: _coerce(value)
            for key, value in attributes.items()
            if key != "name" and not key.startswith(_HINT_ATTR_PREFIX)
        }
        group = self.condition_stack[-1] if self.condition_stack else None
        if group:
            self.model.condition_groups[group] = (
                self.model.condition_groups.get(group, 0) + 1
            )
        self.model.fields.append(
            DcField(component=component, attributes=values, condition_group=group)
        )

    def _finish_script(self) -> None:
        if self.script_attrs is None:
            return
        raw_props = self.script_attrs.get("data-props")
        body = "".join(self.script_buffer).strip()
        is_dc = "data-dc-script" in self.script_attrs
        self.script_attrs = None
        self.script_buffer = []

        if raw_props:
            try:
                self.model.component = DcComponent(name="", props=json.loads(raw_props))
            except json.JSONDecodeError as error:
                self.model.findings.append(f"Could not read data-props: {error}")
        if is_dc and body:
            self.model.scripts.append(body)


def parse(html_text: str, name: str = "") -> DcModel:
    """Parse one .dc.html file into a :class:`DcModel`."""
    model = DcModel()
    parser = _DcParser(model)
    parser.feed(html_text)
    parser.close()

    if model.component is not None:
        model.component.name = name

    # The header's first prose blocks are eyebrow / title / description, in
    # document order. Only a form instance has them.
    blocks = [text for text in parser.text_blocks if text]
    if model.fields and blocks:
        model.eyebrow = blocks[0] if len(blocks) > 0 else ""
        model.title = blocks[1] if len(blocks) > 1 else ""
        model.description = blocks[2] if len(blocks) > 2 else ""

    _assess_conditions(model)
    return model


def _assess_conditions(model: DcModel) -> None:
    """Decide whether any sc-if is real field logic or just a state toggle.

    A single sc-if wrapping EVERY field is the form-versus-thank-you toggle that
    every form in this family uses; reading it as conditional visibility would
    report the whole form as conditional on itself. An sc-if wrapping a SUBSET
    is real branching, and its predicate lives in the component's JavaScript
    where this parser cannot follow it.
    """
    if not model.fields:
        return
    total = len(model.fields)
    for group, count in model.condition_groups.items():
        if count == total:
            model.findings.append(
                f"All {total} fields sit inside one sc-if ({group}) - the "
                "form/thank-you state toggle, not conditional visibility."
            )
            continue
        model.findings.append(
            f"{count} of {total} field(s) are wrapped in sc-if ({group}). That "
            "is real conditional visibility, and its predicate lives in the "
            "component's JavaScript. A human must read it; it is NOT captured."
        )


def has_partial_conditions(model: DcModel) -> bool:
    """True when some sc-if governs only part of the form."""
    total = len(model.fields)
    return any(count != total for count in model.condition_groups.values())


def parse_file(path: str, name: str = "") -> DcModel:
    """Parse a .dc.html file from disk."""
    import os

    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read(), name or os.path.basename(path).split(".")[0])
