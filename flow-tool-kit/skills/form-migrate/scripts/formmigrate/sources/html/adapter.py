"""Assemble a parsed HTML form into the shared IR.

The coverage declaration is the interesting part of this adapter. Raw HTML shows
structure and fields honestly, but says nothing about where the data goes and
only sees conditional logic if it happens to be in markup rather than script.
Declaring that plainly is what stops a downstream reader treating an empty
``conditions`` list as "this form has no conditional logic".
"""

from __future__ import annotations

from ... import conditions as conditions_module
from ... import ir
from . import parser as parser_module


def build(
    form_model,
    form_id: str = "",
    form_name: str = "",
    source_url: str = "",
    conditions_are_complete: bool = False,
) -> dict:
    """Turn an :class:`~.parser.HtmlFormModel` into an IR document.

    ``conditions_are_complete`` is the caller's assertion that a human has read
    the page's scripts and confirmed there is no hidden show/hide logic. It
    defaults to False, so an unreviewed HTML form declares its conditions
    ``not_captured`` rather than claiming none exist. That default is the whole
    point: the parser genuinely cannot tell the two apart.
    """
    document = ir.new_document(
        platform="html",
        form_id=form_id,
        form_name=form_name,
        source_url=source_url,
        coverage={
            "structure": "parsed",
            "fields": "parsed",
            "options": "parsed",
            "validation": "parsed",
            "conditions": "none_exist" if conditions_are_complete else "not_captured",
            # An HTML form POSTs somewhere. If it names an endpoint, a receiving
            # system exists that we have not seen - a hole, not an absence.
            "connector": "not_captured" if form_model.form_action else "none_exist",
            "images": "parsed",
            "custom_scripts": "parsed",
        },
    )

    fields = form_model.ordered_fields()
    document["form"]["section_paths"] = sorted(
        {field.section_path for field in fields if field.section_path}
    )
    document["fields"] = [_build_field(field) for field in fields]
    document["structure"] = _build_structure(fields)
    document["images"] = list(form_model.images)
    document["custom_scripts"] = [
        {"index": index, "length": len(body), "body": body}
        for index, body in enumerate(form_model.custom_scripts)
    ]
    document["findings"] = [
        {"source": "html", "message": message} for message in form_model.findings
    ]

    if form_model.form_action:
        document["findings"].append(
            {
                "source": "adapter",
                "message": f"The form posts to {form_model.form_action!r} "
                f"({(form_model.form_method or 'get').upper()}). Whatever receives "
                "that request is the real mapping spec and has NOT been read; the "
                "Field Plan cannot propose Salesforce targets without it.",
            }
        )

    return ir.finalize(document, resolver=_resolver(fields))


def _resolver(fields) -> conditions_module.LabelResolver:
    """A resolver over field ids and synthesized option ids.

    Nothing references these today - HTML conditions are not parsed - but the
    resolver is built anyway so that a caller who hand-adds conditions to this
    IR gets its references checked instead of silently accepted.
    """
    field_labels = {field.field_id: field.label for field in fields}
    option_labels = {
        f"{field.field_id}::{option.label}": (option.label, field.label)
        for field in fields
        for option in field.options
    }
    return conditions_module.LabelResolver(field_labels, option_labels)


def _build_field(field) -> dict:
    """One IR field entry.

    ``validation`` carries the constraint vocabulary the Field Plan reads to
    infer a staging type. HTML expresses those as the input type plus a couple
    of attributes, so they are translated into the same token list the
    FormAssembly parser produces from CSS classes.
    """
    validation = []
    if field.input_type in ("email", "tel", "url", "number", "date", "datetime-local"):
        validation.append(
            {"tel": "phone", "datetime-local": "datetime"}.get(
                field.input_type, field.input_type
            )
        )
    if field.pattern:
        validation.append("pattern")
    if field.max_length:
        validation.append(f"maxlength-{field.max_length}")

    return {
        "id": field.field_id,
        "label": field.label,
        "section_path": field.section_path,
        "input_type": field.input_type,
        "tag": field.tag,
        "required": field.required,
        "validation": validation,
        "default_value": field.default_value,
        "present_in_rendered_form": True,
        "options": [
            {"id": f"{field.field_id}::{option.label}", "label": option.label}
            for option in field.options
        ],
    }


def _build_structure(fields) -> list[dict]:
    """Section entries derived from the section paths fields carry.

    HTML has no reliable section element, so the tree is reconstructed from the
    paths themselves: every prefix of every path is a section, and its parent is
    the prefix one segment shorter.
    """
    paths: dict[str, str | None] = {}
    for field in fields:
        if not field.section_path:
            continue
        segments = field.section_path.split("/")
        for depth in range(len(segments)):
            path = "/".join(segments[: depth + 1])
            parent = "/".join(segments[:depth]) or None
            paths.setdefault(path, parent)

    return [
        {
            "id": path,
            "tag": "section",
            "layout": [],
            "parent_id": parent,
            "has_condition": False,
        }
        for path, parent in paths.items()
    ]


def build_from_file(
    path: str,
    form_id: str = "",
    form_name: str = "",
    source_url: str = "",
    conditions_are_complete: bool = False,
) -> dict:
    """Parse an HTML file and assemble its IR in one call."""
    return build(
        parser_module.parse_file(path),
        form_id=form_id,
        form_name=form_name,
        source_url=source_url,
        conditions_are_complete=conditions_are_complete,
    )
