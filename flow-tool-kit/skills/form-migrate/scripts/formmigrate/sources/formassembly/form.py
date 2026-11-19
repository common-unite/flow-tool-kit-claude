"""Parse a rendered FormAssembly form into a structure model.

The public form URL is the form-side spec: page and section tree with layout
hints, input types, validation, dependent picklists, images, and - the reason
this input matters most - the complete conditional-visibility ruleset, which
wForms emits declaratively as ``data-condition`` attributes.

Stdlib ``html.parser`` with an element stack; no third-party HTML library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field
from html.parser import HTMLParser

from . import conditions

# Elements that can carry form data.
_INPUT_TAGS = {"input", "select", "textarea"}

# HTML void elements never appear on the open-element stack.
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Inline scripts shorter than this are FormAssembly's own bootstrap wiring
# rather than client customization worth reporting as residue.
_MIN_CUSTOM_SCRIPT_LENGTH = 200

# Section wrappers carry a "section" class; the remaining classes are layout
# variants (group, column, inline) that the rebuild should preserve.
_SECTION_LAYOUTS = {"group", "column", "inline"}

# Validation hints ride along as CSS classes, e.g. "validate-integer".
_VALIDATION_CLASS_RE = re.compile(r"\bvalidate-([\w-]+)\b")

# Scripts served from FormAssembly's own libraries are infrastructure, not
# client customization - anything else is residue a human must rebuild.
_VENDOR_SCRIPT_HOSTS = ("tfaforms.com", "authorize.net", "google", "gstatic")

# Input types that never become staging fields - the gateway owns them.
_PAYMENT_FIELD_HINTS = (
    "card number",
    "name on card",
    "security code",
    "cvv",
    "expiration",
)


_FORMULA_CLASS_RE = re.compile(r"formula=(.*?)(?=\s+(?:readonly|calc-[\w-]+|validate-[\w-]+|required)\b|\s*$)")


@dataclass
class FormSection:
    """A section, section group, or other container in the form tree."""

    element_id: str
    tag: str
    layout: list[str] = dataclass_field(default_factory=list)
    parent_id: str | None = None
    condition: str | None = None
    condition_tree: dict | None = None
    repeat: bool = False
    repeat_label: str | None = None
    # A single question that repeats on its own ("Add another transcript"): FormAssembly
    # marks the question's oneField wrapper, not a section, with ``repeat``.
    repeats_field: str | None = None


@dataclass
class FormInput:
    """One input, select, or textarea on the form."""

    element_id: str
    tag: str
    input_type: str | None = None
    required: bool = False
    validation: list[str] = dataclass_field(default_factory=list)
    default_value: str | None = None
    section_id: str | None = None
    condition: str | None = None
    condition_tree: dict | None = None
    filter_control: str | None = None
    filter_dependent: str | None = None
    css_classes: list[str] = dataclass_field(default_factory=list)
    calculation: str | None = None
    variable: str | None = None


@dataclass
class ConditionalRule:
    """One ``data-condition`` and the element it governs.

    Conditions attach at three levels - whole section, choice-group wrapper, and
    individual input - and the level must be preserved. Collapsing a section
    rule onto its children changes behavior when the section is later edited.
    """

    element_id: str
    tag: str
    governs: str
    expression: str
    tree: dict | None
    css_classes: list[str] = dataclass_field(default_factory=list)


@dataclass
class FormModel:
    """Everything the rendered form yields."""

    sections: dict[str, FormSection] = dataclass_field(default_factory=dict)
    inputs: dict[str, FormInput] = dataclass_field(default_factory=dict)
    conditions: list[ConditionalRule] = dataclass_field(default_factory=list)
    images: list[str] = dataclass_field(default_factory=list)
    custom_scripts: list[str] = dataclass_field(default_factory=list)
    findings: list[str] = dataclass_field(default_factory=list)
    # Each htmlSection text block, in page order: {"id", "section", "text"}.
    text_blocks: list[dict] = dataclass_field(default_factory=list)

    def conditional_rules(self) -> list[ConditionalRule]:
        """Every parsed condition, whatever element carried it."""
        return self.conditions

    def dependent_picklists(self) -> list[dict]:
        """Controlling/dependent picklist pairs declared on the form."""
        pairs = []
        for entry in self.inputs.values():
            if entry.filter_control or entry.filter_dependent:
                pairs.append(
                    {
                        "element_id": entry.element_id,
                        "controlled_by": entry.filter_control,
                        "controls": entry.filter_dependent,
                    }
                )
        return pairs

    def payment_inputs(self) -> list[str]:
        """Inputs that look like card collection - excluded from staging."""
        return [
            entry.element_id
            for entry in self.inputs.values()
            if entry.input_type == "password"
            or any(hint in " ".join(entry.css_classes).lower() for hint in _PAYMENT_FIELD_HINTS)
        ]


class _FormParser(HTMLParser):
    """Walks the document, tracking an element stack for section nesting."""

    def __init__(self, model: FormModel):
        super().__init__(convert_charrefs=True)
        self.model = model
        # Every open non-void element, as (tag, section_id or None). Tracking
        # all elements - not just sections - is what keeps a nested <div> from
        # popping its enclosing section when it closes.
        self.element_stack: list[tuple[str, str | None]] = []
        self.script_attrs: dict | None = None
        self.script_buffer: list[str] = []
        # The open htmlSection text block and the stack depth it opened at.
        self.text_block: dict | None = None
        self.text_depth = 0
        self.text_buffer: list[str] = []

    @property
    def section_stack(self) -> list[str]:
        """Ids of the currently open sections, outermost first."""
        return [
            section_id for _, section_id in self.element_stack if section_id is not None
        ]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}

        if tag == "script":
            self.script_attrs = attributes
            self.script_buffer = []
            self.element_stack.append((tag, None))
            return

        if tag == "img":
            source = attributes.get("src", "").strip()
            if source:
                self.model.images.append(source)
            return

        classes = attributes.get("class", "").split()
        element_id = attributes.get("id", "").strip()

        # Record conditions from any element, not just sections and inputs.
        # Choice groups wrap their options in a <table> or <span> and carry the
        # condition there, so branching on element kind first loses those rules.
        if "data-condition" in attributes:
            self._record_condition(tag, element_id, classes, attributes)

        # A question that repeats on its own carries "repeat" on its oneField wrapper
        # (id tfa_N-D, data-repeatlabel): a one-question Repeater, kept as its own section.
        is_section = bool(element_id) and ("section" in classes or ("repeat" in classes and "oneField" in classes))
        if self.text_block is not None and tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.text_buffer.append(" ")  # a block boundary inside a text block is a word boundary
        if tag == "div" and "htmlSection" in classes and element_id and self.text_block is None:
            self.text_block = {"id": element_id, "section": self.section_stack[-1] if self.section_stack else None}
            self.text_depth = len(self.element_stack)
            self.text_buffer = []
        if is_section:
            self._start_section(tag, element_id, classes, attributes)
        elif tag in _INPUT_TAGS and element_id:
            self._record_input(tag, element_id, classes, attributes)
        elif "choices" in classes and element_id:
            # A checkbox or radio group carries the *field* id on its wrapper
            # (a <table> or <span>); the individual <input>s inside carry the
            # option ids. Without this the field looks absent from the form.
            self._record_input(
                tag, element_id, classes, attributes, input_type="choice-group"
            )

        if tag not in _VOID_TAGS:
            self.element_stack.append((tag, element_id if is_section else None))

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._finish_script()

        # Unwind to the matching open tag. Malformed markup that never closes an
        # element would otherwise strand the stack and mis-parent every section
        # that follows.
        for depth in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[depth][0] == tag:
                del self.element_stack[depth:]
                break
        if self.text_block is not None and len(self.element_stack) <= self.text_depth:
            self._finish_text_block()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "img":
            source = attributes.get("src", "").strip()
            if source:
                self.model.images.append(source)
            return
        classes = attributes.get("class", "").split()
        element_id = attributes.get("id", "").strip()
        if "data-condition" in attributes:
            self._record_condition(tag, element_id, classes, attributes)
        if tag in _INPUT_TAGS and element_id:
            self._record_input(tag, element_id, classes, attributes)

    def handle_data(self, data: str) -> None:
        if self.script_attrs is not None:
            self.script_buffer.append(data)
        elif self.text_block is not None:
            self.text_buffer.append(data)

    def _finish_text_block(self) -> None:
        text = " ".join("".join(self.text_buffer).split())
        if text:
            self.model.text_blocks.append({**self.text_block, "text": text})
        self.text_block = None
        self.text_buffer = []

    def _start_section(
        self, tag: str, element_id: str, classes: list[str], attributes: dict
    ) -> None:
        expression = attributes.get("data-condition", "").strip()
        section = FormSection(
            element_id=element_id,
            tag=tag,
            layout=[name for name in classes if name in _SECTION_LAYOUTS],
            parent_id=self.section_stack[-1] if self.section_stack else None,
            condition=expression or None,
            condition_tree=self._parse_condition(expression, element_id),
            repeat="repeat" in classes,
            repeat_label=attributes.get("data-repeatlabel", "").strip() or None if "repeat" in classes else None,
            repeats_field=element_id[:-2] if "oneField" in classes and element_id.endswith("-D") else None,
        )
        self.model.sections[element_id] = section

    def _record_input(
        self,
        tag: str,
        element_id: str,
        classes: list[str],
        attributes: dict,
        input_type: str | None = None,
    ) -> None:
        expression = attributes.get("data-condition", "").strip()
        validation = _VALIDATION_CLASS_RE.findall(" ".join(classes))
        # FormAssembly stores a calculated field's formula and variable name in its class attribute.
        formula = _FORMULA_CLASS_RE.search(attributes.get("class", ""))
        variable = next((name[5:] for name in classes if name.startswith("calc-")), None)
        self.model.inputs[element_id] = FormInput(
            element_id=element_id,
            tag=tag,
            # A select or textarea has no type attribute; its tag is its type.
            input_type=input_type or attributes.get("type") or (tag if tag in ("select", "textarea") else None),
            required="required" in attributes
            or attributes.get("aria-required") == "true",
            validation=validation,
            default_value=attributes.get("data-default-value") or None,
            section_id=self.section_stack[-1] if self.section_stack else None,
            condition=expression or None,
            condition_tree=self._parse_condition(expression, element_id),
            filter_control=attributes.get("data-filter-control") or None,
            filter_dependent=attributes.get("data-filter-dependent") or None,
            css_classes=classes,
            calculation=formula.group(1).strip() if formula else None,
            variable=variable,
        )

    def _record_condition(
        self, tag: str, element_id: str, classes: list[str], attributes: dict
    ) -> None:
        expression = attributes.get("data-condition", "").strip()
        if not expression:
            return
        if not element_id:
            self.model.findings.append(
                f"Condition on <{tag}> with no id, cannot be attributed: {expression}"
            )
            return

        if "section" in classes:
            governs = "section"
        elif tag in _INPUT_TAGS or "choices" in classes:
            governs = "field"
        else:
            governs = "element"

        self.model.conditions.append(
            ConditionalRule(
                element_id=element_id,
                tag=tag,
                governs=governs,
                expression=expression,
                tree=self._parse_condition(expression, element_id),
                css_classes=classes,
            )
        )

    def _parse_condition(self, expression: str, element_id: str) -> dict | None:
        if not expression:
            return None
        try:
            return conditions.parse(expression)
        except conditions.ConditionSyntaxError as error:
            self.model.findings.append(
                f"Could not parse condition on {element_id}: {error}"
            )
            return None

    def _finish_script(self) -> None:
        if self.script_attrs is None:
            return
        source = self.script_attrs.get("src", "")
        body = "".join(self.script_buffer).strip()
        self.script_attrs = None
        self.script_buffer = []

        # An external src is a library, not client customization.
        if source:
            if not any(host in source for host in _VENDOR_SCRIPT_HOSTS):
                self.model.findings.append(f"Third-party script referenced: {source}")
            return

        # Inline blocks are candidate residue. FormAssembly's own bootstrap is
        # short and only wires up its libraries, so ignore trivial blocks.
        if len(body) >= _MIN_CUSTOM_SCRIPT_LENGTH:
            self.model.custom_scripts.append(body)


def parse(html_text: str) -> FormModel:
    """Parse rendered form HTML into a :class:`FormModel`."""
    model = FormModel()
    parser = _FormParser(model)
    parser.feed(html_text)
    parser.close()

    if model.custom_scripts:
        model.findings.append(
            f"{len(model.custom_scripts)} custom script block(s) found - these "
            "cannot be migrated declaratively and need a rebuild decision."
        )
    return model


def parse_file(path: str) -> FormModel:
    """Parse a rendered form from disk."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read())
