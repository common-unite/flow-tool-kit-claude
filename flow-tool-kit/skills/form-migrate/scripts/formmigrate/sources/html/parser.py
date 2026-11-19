"""Parse a rendered HTML form into a structure model.

Stdlib ``html.parser`` with an element stack, matching the FormAssembly parser's
approach. The lesson that produced seven bugs in that parser applies here too:
**parse by the marker that carries the meaning, then classify - never branch on
element kind first.**

Two things that make generic HTML harder than a known platform:

1. **A radio or checkbox GROUP is one field, not N fields.** The grouping marker
   is the shared ``name`` attribute, and the individual inputs are its options.
   Treating each ``<input type="radio">`` as its own field produces a form with
   forty yes/no questions instead of eight picklists.
2. **Labels attach four different ways** and no single one is reliable:
   ``<label for>``, a wrapping ``<label>``, ``aria-label``/``aria-labelledby``,
   or nothing but a heading above. Resolution walks them in that order and
   records which one won, because a label recovered from a placeholder is
   materially weaker evidence than one from a ``for`` attribute.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field
from html.parser import HTMLParser

_INPUT_TAGS = {"input", "select", "textarea"}

_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Inputs that never become questions: submit buttons and framework plumbing.
_NON_QUESTION_TYPES = {"submit", "button", "reset", "image"}

# Hidden inputs whose names look like anti-forgery or analytics plumbing.
_PLUMBING_NAME_RE = re.compile(
    r"csrf|xsrf|authenticity|nonce|recaptcha|captcha|utm_|__viewstate|__eventtarget"
    r"|__eventargument|__requestverification|honeypot",
    re.I,
)

# Card collection is the gateway's job and is never staged in Salesforce.
_PAYMENT_NAME_RE = re.compile(
    r"card[\s_-]?number|cardnum|ccnum|cvv|cvc|security[\s_-]?code"
    r"|exp(iry|iration)?[\s_-]?(date|month|year)?|name[\s_-]?on[\s_-]?card",
    re.I,
)

# Containers that plausibly delimit a section, best marker first.
_SECTION_TAGS = ("fieldset", "section")
_SECTION_CLASS_RE = re.compile(r"\b(section|fieldset|form-group|page|step)\b", re.I)

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "legend"}

_MULTILINE_TAGS = {"textarea"}


# How much a label source is worth. A weaker source NEVER overwrites a stronger
# one, whatever order the markup happens to present them in - the bug this
# replaces let a section heading beat the input's own placeholder.
_LABEL_RANK = {
    "label-for": 100,
    "aria-label": 90,
    "wrapping-label": 80,
    # A lone tick box ("I agree to ...") has no caption of its own: the text
    # beside its one box is the question.
    "single-choice-label": 75,
    "bare-label": 70,
    "placeholder": 50,
    "heading": 30,
    "name-attribute": 10,
    "": 0,
}

# Below this, the label is a guess and the question text must be confirmed
# against the live form before it reaches a client workbook.
_WEAK_LABEL_RANK = 70


@dataclass
class HtmlOption:
    """One selectable choice: an <option>, or a radio/checkbox in a group."""

    value: str
    label: str
    element_id: str = ""


@dataclass
class HtmlField:
    """One question. A radio/checkbox group is ONE field with many options."""

    field_id: str
    name: str = ""
    label: str = ""
    label_source: str = ""
    input_type: str = ""
    tag: str = ""
    required: bool = False
    default_value: str | None = None
    placeholder: str | None = None
    max_length: str | None = None
    pattern: str | None = None
    section_path: str = ""
    options: list[HtmlOption] = dataclass_field(default_factory=list)
    is_hidden: bool = False
    element_ids: list[str] = dataclass_field(default_factory=list)

    def offer_label(self, text: str, source: str) -> None:
        """Take this label only if its source outranks the one already held."""
        if not text:
            return
        if _LABEL_RANK.get(source, 0) <= _LABEL_RANK.get(self.label_source, 0):
            return
        self.label = text
        self.label_source = source


@dataclass
class HtmlFormModel:
    """Everything a rendered HTML form yields."""

    fields: dict[str, HtmlField] = dataclass_field(default_factory=dict)
    sections: list[dict] = dataclass_field(default_factory=list)
    images: list[str] = dataclass_field(default_factory=list)
    custom_scripts: list[str] = dataclass_field(default_factory=list)
    form_action: str | None = None
    form_method: str | None = None
    findings: list[str] = dataclass_field(default_factory=list)

    def ordered_fields(self) -> list[HtmlField]:
        """Fields in document order, which is the order a user meets them."""
        return list(self.fields.values())


class _HtmlFormParser(HTMLParser):
    """Walks the document, tracking sections, labels, and choice grouping."""

    def __init__(self, model: HtmlFormModel):
        super().__init__(convert_charrefs=True)
        self.model = model
        self.element_stack: list[tuple[str, str | None]] = []

        # Deferred label resolution. <label for="x"> frequently appears AFTER
        # the input it names, so labels are collected and applied at the end.
        self.labels_for: dict[str, str] = {}
        self.pending_label: list[str] | None = None
        self.pending_label_for: str | None = None
        # ("field", key) or ("option", key, option index): what an open <label> wraps.
        self.wrapping_label_targets: list[tuple] = []

        self.heading_buffer: list[str] | None = None
        self.last_heading = ""
        # A <label> that points at nothing and wraps nothing - how a radio or
        # checkbox group is captioned. Consumed by the next field created.
        self.last_bare_label = ""

        self.select_field_id: str | None = None
        self.option_buffer: list[str] | None = None
        self.option_value: str | None = None

        self.script_attrs: dict | None = None
        self.script_buffer: list[str] = []
        self.in_form = False

    # --- section tracking ---------------------------------------------------

    @property
    def section_path(self) -> str:
        names = [name for _, name in self.element_stack if name]
        return "/".join(names)

    def _section_name(self, tag: str, attributes: dict) -> str | None:
        """Whether this element opens a section, and what to call it.

        Named after its legend/heading when one turns up; the placeholder is
        replaced in ``handle_data`` once the text arrives.
        """
        if tag in _SECTION_TAGS:
            return ""
        if _SECTION_CLASS_RE.search(attributes.get("class", "")):
            return ""
        return None

    # --- HTMLParser hooks ---------------------------------------------------

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

        if tag == "form":
            self.in_form = True
            self.model.form_action = attributes.get("action") or None
            self.model.form_method = (attributes.get("method") or "get").lower()

        if tag in _HEADING_TAGS:
            self.heading_buffer = []

        if tag == "label":
            self.pending_label = []
            self.pending_label_for = attributes.get("for") or None
            self.wrapping_label_targets = []

        if tag == "option":
            self.option_buffer = []
            self.option_value = attributes.get("value")
            if "selected" in attributes and self.select_field_id:
                field = self.model.fields.get(self.select_field_id)
                if field and field.default_value is None:
                    field.default_value = attributes.get("value", "")

        if tag in _INPUT_TAGS:
            self._record_input(tag, attributes)

        section_name = self._section_name(tag, attributes)
        if tag not in _VOID_TAGS:
            self.element_stack.append((tag, section_name))

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._finish_script()

        if tag in _HEADING_TAGS and self.heading_buffer is not None:
            text = " ".join("".join(self.heading_buffer).split())
            self.heading_buffer = None
            if text:
                self.last_heading = text
                self._name_current_section(text)

        if tag == "label" and self.pending_label is not None:
            self._finish_label()

        if tag == "option" and self.option_buffer is not None:
            self._finish_option()

        if tag == "select":
            self.select_field_id = None

        if tag == "form":
            self.in_form = False

        for depth in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[depth][0] == tag:
                del self.element_stack[depth:]
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "img":
            source = attributes.get("src", "").strip()
            if source:
                self.model.images.append(source)
            return
        if tag in _INPUT_TAGS:
            self._record_input(tag, attributes)

    def handle_data(self, data: str) -> None:
        if self.script_attrs is not None:
            self.script_buffer.append(data)
            return
        if self.heading_buffer is not None:
            self.heading_buffer.append(data)
        if self.option_buffer is not None:
            self.option_buffer.append(data)
        elif self.pending_label is not None:
            self.pending_label.append(data)

    # --- fields -------------------------------------------------------------

    def _record_input(self, tag: str, attributes: dict) -> None:
        input_type = (attributes.get("type") or "").lower()
        if tag == "input" and input_type in _NON_QUESTION_TYPES:
            return

        name = (attributes.get("name") or "").strip()
        element_id = (attributes.get("id") or "").strip()

        if input_type == "hidden" and _PLUMBING_NAME_RE.search(name or element_id):
            return

        # Radio and checkbox inputs sharing a name are ONE field. Everything
        # else keys on its own name, then id - a field with neither cannot be
        # submitted, so it is reported rather than invented.
        is_choice = input_type in ("radio", "checkbox")
        key = name or element_id
        if not key:
            self.model.findings.append(
                f"<{tag} type={input_type!r}> has neither name nor id and cannot "
                "be identified; skipped."
            )
            return

        if is_choice and key in self.model.fields:
            self._add_choice_option(key, attributes, element_id)
            return

        if key in self.model.fields and not is_choice:
            self.model.findings.append(
                f"Duplicate field key {key!r}; the later input was merged into "
                "the earlier one."
            )
            self.model.fields[key].element_ids.append(element_id)
            return

        field = HtmlField(
            field_id=key,
            name=name,
            input_type="textarea" if tag in _MULTILINE_TAGS else (input_type or "text"),
            tag=tag,
            required="required" in attributes
            or attributes.get("aria-required") == "true",
            default_value=attributes.get("value") or None,
            placeholder=attributes.get("placeholder") or None,
            max_length=attributes.get("maxlength") or None,
            pattern=attributes.get("pattern") or None,
            section_path=self.section_path,
            is_hidden=input_type == "hidden",
            element_ids=[element_id] if element_id else [],
        )

        # Offer every candidate and let rank decide. A bare <label> just above
        # the input is how a choice GROUP is captioned, and it must beat the
        # section heading; the heading is the last resort before the name.
        field.offer_label(self.last_heading, "heading")
        field.offer_label(self.last_bare_label, "bare-label")
        field.offer_label((attributes.get("aria-label") or "").strip(), "aria-label")
        # One bare label captions one field, so it must not leak to the next.
        self.last_bare_label = ""

        if is_choice:
            field.input_type = "choice-group"
            field.default_value = None
            self._add_choice_option(key, attributes, element_id, field=field)

        if tag == "select":
            field.input_type = "multiselect" if "multiple" in attributes else "select"
            self.select_field_id = key

        self.model.fields[key] = field

        # A label wrapping a radio or tick box names that CHOICE, never the
        # group's question (handled in _add_choice_option). Anything else it
        # wraps, with or without an id, is named by it.
        if self.pending_label is not None and not is_choice:
            self.wrapping_label_targets.append(("field", key))

    def _add_choice_option(
        self, key: str, attributes: dict, element_id: str, field=None
    ) -> None:
        """Attach one radio/checkbox to its group as an option.

        The option carries its OWN element id. Pushing it onto the field's
        ``element_ids`` instead - which an earlier version did - put the first
        input's id in the list twice and shifted every option's label by one,
        so the last option silently inherited the second-to-last one's text.
        """
        field = field or self.model.fields[key]
        value = attributes.get("value", "")
        field.options.append(
            HtmlOption(value=value, label=value, element_id=element_id)
        )
        # The option's visible text is usually in a label that has not been
        # read yet: a wrapping label fills it in when it closes, a
        # <label for> in the label pass, by element id.
        if self.pending_label is not None:
            self.wrapping_label_targets.append(("option", key, len(field.options) - 1))

    # --- labels and options -------------------------------------------------

    def _finish_label(self) -> None:
        text = " ".join("".join(self.pending_label or []).split())
        target = self.pending_label_for
        self.pending_label = None
        self.pending_label_for = None
        wrapping = self.wrapping_label_targets
        self.wrapping_label_targets = []

        if not text:
            return
        if target:
            self.labels_for[target] = text
            return
        # A label with no `for` names whatever it wraps.
        if wrapping:
            for entry in wrapping:
                field = self.model.fields.get(entry[1])
                if field is None:
                    continue
                if entry[0] == "option":
                    field.options[entry[2]].label = text
                else:
                    field.offer_label(text, "wrapping-label")
            return
        # A label that neither points at nor wraps anything still captions
        # something: it is how a radio or checkbox GROUP gets its question text,
        # since the group has no element of its own to point at.
        self.last_bare_label = text

    def _finish_option(self) -> None:
        text = " ".join("".join(self.option_buffer or []).split())
        value = self.option_value
        self.option_buffer = None
        self.option_value = None
        if self.select_field_id is None:
            return
        field = self.model.fields.get(self.select_field_id)
        if field is None:
            return
        # An empty VALUE is the HTML idiom for "nothing selected" - the
        # "-- choose --" prompt. Its visible text is non-empty, so testing the
        # text instead lets the prompt through as a real choice and it ends up
        # in the client's picklist.
        if not value:
            if text and field.placeholder is None:
                field.placeholder = text
            return
        field.options.append(HtmlOption(value=value, label=text or value))

    def _name_current_section(self, text: str) -> None:
        """Give the innermost unnamed open section this heading's text."""
        for depth in range(len(self.element_stack) - 1, -1, -1):
            tag, name = self.element_stack[depth]
            if name == "":
                self.element_stack[depth] = (tag, text)
                return

    def _finish_script(self) -> None:
        if self.script_attrs is None:
            return
        source = self.script_attrs.get("src", "")
        body = "".join(self.script_buffer).strip()
        self.script_attrs = None
        self.script_buffer = []
        if source:
            self.model.findings.append(f"External script referenced: {source}")
            return
        if len(body) >= 200:
            self.model.custom_scripts.append(body)


def _resolve_labels(model: HtmlFormModel, parser: _HtmlFormParser) -> None:
    """Apply `<label for=...>` text, which often appears after its input."""
    for field in model.fields.values():
        # A choice group's own <label for> would point at one of its options,
        # not the group, so only non-group fields take a label this way.
        if field.input_type != "choice-group":
            for element_id in field.element_ids:
                field.offer_label(parser.labels_for.get(element_id, ""), "label-for")

        # Each option resolves against the id it actually carries.
        for option in field.options:
            text = parser.labels_for.get(option.element_id)
            if text:
                option.label = text

        if field.input_type == "choice-group" and len(field.options) == 1:
            field.offer_label(field.options[0].label, "single-choice-label")
        field.offer_label(field.placeholder or "", "placeholder")
        field.offer_label(field.name or field.field_id, "name-attribute")


def parse(html_text: str) -> HtmlFormModel:
    """Parse rendered HTML into an :class:`HtmlFormModel`."""
    model = HtmlFormModel()
    parser = _HtmlFormParser(model)
    parser.feed(html_text)
    parser.close()
    _resolve_labels(model, parser)

    weak = [
        field.field_id
        for field in model.fields.values()
        if _LABEL_RANK.get(field.label_source, 0) < _WEAK_LABEL_RANK
    ]
    if weak:
        model.findings.append(
            f"{len(weak)} field(s) have no proper <label> and were named from a "
            f"placeholder, heading or name attribute: {', '.join(sorted(weak)[:10])}"
            f"{'...' if len(weak) > 10 else ''}. Confirm these question texts "
            "against the live form before they reach a client workbook."
        )

    payment = [
        field.field_id
        for field in model.fields.values()
        if _PAYMENT_NAME_RE.search(f"{field.name} {field.label}")
    ]
    if payment:
        model.findings.append(
            f"{len(payment)} field(s) look like card collection "
            f"({', '.join(sorted(payment))}). Payment is always a Stripe "
            "Connector handoff; card data is never staged in Salesforce."
        )

    if model.custom_scripts:
        model.findings.append(
            f"{len(model.custom_scripts)} inline script block(s) found. Any "
            "conditional logic or calculation implemented in JavaScript is "
            "INVISIBLE to this parser and must be read by a human."
        )
    return model


def parse_file(path: str) -> HtmlFormModel:
    """Parse a rendered HTML form from disk."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read())
