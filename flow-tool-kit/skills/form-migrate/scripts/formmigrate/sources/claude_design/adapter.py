"""Design file source adapter (``.dc.html``).

For a form drawn as a ``.dc.html`` design file, the format a Claude design
canvas saves. The best-structured source this skill reads: a question is not
reconstructed from markup, it is declared::

    <dc-import name="Choices" label="What worked well?"
                options="Food|Music|Kids' activities" multi="{{ true }}">

No label-association guessing, no choice-group reconstruction - the two things
that make raw HTML fragile - and option sets arrive intact.

Getting the files is a session step, not a library one: save the form and every
component definition it imports into the project (download them from the canvas,
or read them through whatever design tool the session has), then parse them from
disk. See `references/sources/claude-design.md`.

Usage::

    from formmigrate.sources.claude_design import adapter
    document = adapter.build_from_files(
        "_forms/design-feedback/Post-Event Feedback.dc.html",
        ["_forms/design-feedback/Field.dc.html",
         "_forms/design-feedback/Choices.dc.html",
         "_forms/design-feedback/Scale.dc.html"],
        project_id="example-project")

Assemble parsed Claude Design components into the shared IR.

Classification is **prop-driven**. A component that accepts an ``options`` prop
is a choice question whether the kit calls it ``Choices``, ``Picker`` or
``MultiSelect``; one that accepts ``max`` plus a low/high label pair is a rating
scale. Component names are a tie-breaker and a hint, never the test - a name is
element kind, and branching on element kind is what this package's parsing
lesson exists to prevent.

Feed it the component definitions alongside the form and classification gets
sharper, because the definitions declare each prop's editor type and enum
values. Without them the adapter still works, inferring from the attributes the
form actually sets, and says so in a finding.
"""

from __future__ import annotations

from ... import ir
from . import parser as parser_module

# Props whose presence identifies what kind of question a component asks.
_CHOICE_PROP = "options"
_MULTI_PROP = "multi"
_MULTILINE_PROP = "multiline"
_SCALE_PROPS = ("max", "lowlabel", "highlabel", "kind")

# A scale rendered as stars is a rating; as numbers it is a numeric scale.
_STAR_KINDS = {"stars", "star", "hearts", "rating"}

# Label/placeholder wording that identifies a typed text field. HTML would carry
# type="email"; this format carries only prose, so the prose is the evidence.
_TYPE_HINTS = (
    ("email", ("email", "e-mail", "@example.com")),
    ("tel", ("phone", "mobile", "cell number", "telephone")),
    ("url", ("website", "url", "http")),
    ("date", ("date of", "birthdate", "birthday", "mm/dd", "dd/mm")),
    ("number", ("how many", "number of", "quantity", "amount", "zip", "age")),
)


def _as_int(value) -> int | None:
    """An integer from an int or a numeric attribute string, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _looks_like(text: str, needles: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(needle in lowered for needle in needles)


def _typed_text_kind(field) -> str | None:
    """Infer a typed text field from its wording, or None to leave it text."""
    haystack = f"{field.label} {field.attr('placeholder') or ''} " \
               f"{field.attr('hint') or ''}"
    for kind, needles in _TYPE_HINTS:
        if _looks_like(haystack, needles):
            return kind
    return None


def classify(field, definitions: dict) -> dict:
    """Decide what one dc-import collects, and on what evidence.

    Returns the IR input_type, validation tokens, options, and a note when the
    decision rested on something weaker than a declared prop.
    """
    definition = definitions.get(field.component)
    declared = {name.lower() for name in (definition.prop_names if definition else ())}
    present = {key.lower() for key in field.attributes}
    known = declared or present
    notes: list[str] = []

    if not definition:
        notes.append(
            f"No component definition found for '{field.component}'; its type was "
            "inferred from the attributes this form happens to set. Import the "
            f"'{field.component}.dc.html' definition for a firmer reading."
        )

    # A scale: bounded numeric range with end labels.
    if _CHOICE_PROP not in known and any(prop in known for prop in _SCALE_PROPS):
        kind = str(field.attr("kind") or "").lower()
        if not kind and definition:
            enum = [value.lower() for value in definition.enum_values("kind")]
            kind = enum[0] if enum else ""
        # max arrives as a plain attribute (max="10"), not a {{ }} binding, so
        # it is a STRING. Reading it as "not an int" silently fell back to the
        # component's default of 5 and turned a 0-10 NPS question into 1-5.
        maximum = _as_int(field.attr("max"))
        if maximum is None and definition:
            maximum = _as_int((definition.props.get("max") or {}).get("default"))
        maximum = maximum if maximum else 5
        options = [{"label": str(step)} for step in range(1, maximum + 1)]
        return {
            "input_type": "rating" if kind in _STAR_KINDS else "scale",
            "validation": ["integer", f"max-{maximum}"],
            "options": options,
            "scale": {
                "kind": kind or "numbers",
                "max": maximum,
                "low_label": field.attr("lowLabel"),
                "high_label": field.attr("highLabel"),
            },
            "notes": notes,
        }

    # A choice question: it accepts an option list.
    if _CHOICE_PROP in known:
        options = field.options
        is_multi = field.attr(_MULTI_PROP) is True
        if not options:
            notes.append(
                "Declares an options prop but this instance sets none, so the "
                "value set is unknown - it cannot be reproduced from the design."
            )
        return {
            "input_type": "choice-group",
            "validation": ["checkbox"] if is_multi else [],
            "options": [{"label": option} for option in options],
            "layout": field.attr("layout"),
            "notes": notes,
        }

    # Free text, single or multi line.
    if field.attr(_MULTILINE_PROP) is True:
        return {"input_type": "textarea", "validation": [], "options": [],
                "notes": notes}

    if _MULTILINE_PROP in known or not known - _COMMON_LOWER:
        typed = _typed_text_kind(field)
        return {
            "input_type": typed or "text",
            "validation": [{"tel": "phone"}.get(typed, typed)] if typed else [],
            "options": [],
            "notes": notes + ([f"Type inferred from the question's wording, not a "
                               f"declared prop - confirm it is really {typed}."]
                              if typed else []),
        }

    notes.append(
        f"Component '{field.component}' could not be classified from its props "
        f"({', '.join(sorted(known)) or 'none'}). Staged as text; a human must "
        "decide what it actually collects."
    )
    return {"input_type": "text", "validation": [], "options": [], "notes": notes}


_COMMON_LOWER = {name.lower() for name in parser_module._COMMON_PROPS}


def build(
    form_model,
    definitions: dict | None = None,
    form_id: str = "",
    form_name: str = "",
    source_url: str = "",
    project_id: str = "",
) -> dict:
    """Turn a parsed form instance into an IR document."""
    definitions = definitions or {}

    # A partial sc-if is real branching whose predicate lives in JavaScript this
    # parser cannot follow. A single sc-if around everything is the standard
    # form/thank-you toggle and means nothing about field visibility.
    partial = parser_module.has_partial_conditions(form_model)

    document = ir.new_document(
        platform="claude-design",
        form_id=form_id or project_id,
        form_name=form_name or form_model.title or form_model.eyebrow,
        source_url=source_url,
        coverage={
            "structure": "parsed",
            "fields": "parsed",
            "options": "parsed",
            "validation": "parsed",
            "conditions": "not_captured" if partial else "none_exist",
            # A design is a design. Nothing behind it receives a submission.
            "connector": "none_exist",
            "images": "parsed",
            "custom_scripts": "parsed",
        },
    )
    document["source"]["project_id"] = project_id
    document["source"]["components"] = sorted(
        {field.component for field in form_model.fields}
    )

    section = form_model.eyebrow or form_model.title or "Form"
    used_ids: set[str] = set()
    fields: list[dict] = []
    findings = [
        {"source": "claude-design", "message": message}
        for message in form_model.findings
    ]

    for field in form_model.fields:
        shape = classify(field, definitions)
        field_id = ir.derive_field_id(field.label or field.component, used_ids)
        options = shape.get("options") or []
        fields.append(
            {
                "id": field_id,
                "label": field.label,
                "section_path": section,
                "input_type": shape["input_type"],
                "tag": "dc-import",
                "required": field.attr("required") is True,
                "validation": [token for token in shape["validation"] if token],
                "default_value": None,
                "present_in_rendered_form": True,
                "help_text": field.attr("hint") or None,
                "placeholder": field.attr("placeholder") or None,
                "component": field.component,
                "options": [
                    {"id": f"{field_id}::{option['label']}", "label": option["label"]}
                    for option in options
                ],
            }
        )
        if shape.get("scale"):
            fields[-1]["scale"] = shape["scale"]
        if shape.get("layout"):
            fields[-1]["layout"] = shape["layout"]
        for note in shape.get("notes") or []:
            findings.append({"source": "claude-design", "message": f"{field_id}: {note}"})

    document["fields"] = fields
    document["form"]["section_paths"] = [section]
    document["structure"] = [
        {"id": section, "tag": "section", "layout": [], "parent_id": None,
         "has_condition": partial}
    ]
    document["images"] = list(form_model.images)
    document["custom_scripts"] = [
        {"index": index, "length": len(body), "body": body}
        for index, body in enumerate(form_model.scripts)
    ]

    findings.append(
        {
            "source": "adapter",
            "message": "A Claude Design file is a DESIGN - nothing receives a "
            "submission, so there is no mapping spec by definition. Every target "
            "decision moves to new-mapping-flow discovery.",
        }
    )
    if form_model.images:
        findings.append(
            {
                "source": "adapter",
                "message": f"{len(form_model.images)} image(s) reference project "
                "assets. Self-host each as a ContentAsset marked publicly "
                "available, or guest users cannot render them.",
            }
        )
    document["findings"] = findings
    return ir.finalize(document)


def build_from_files(
    form_path: str,
    definition_paths: list[str] | None = None,
    form_id: str = "",
    form_name: str = "",
    source_url: str = "",
    project_id: str = "",
) -> dict:
    """Parse a form and any component definitions beside it, then assemble."""
    import os

    definitions = {}
    for path in definition_paths or []:
        name = os.path.basename(path).split(".")[0]
        model = parser_module.parse_file(path, name)
        if model.component is not None:
            definitions[name] = model.component

    return build(
        parser_module.parse_file(form_path),
        definitions,
        form_id=form_id,
        form_name=form_name,
        source_url=source_url,
        project_id=project_id,
    )
