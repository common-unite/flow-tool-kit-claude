"""Turn a hand-written capture document into the shared IR.

The capture document is deliberately the smallest thing a person can write
accurately from screenshots. Everything mechanical - ids, section trees,
condition reference resolution, option id synthesis - is derived here, because
those are exactly the things a human transcribing forty questions gets subtly
wrong.

Capture shape (JSON)::

    {
      "platform": "google-forms",
      "form_name": "Riverside Garden Volunteer Survey",
      "source_url": "https://docs.google.com/forms/d/e/EXAMPLE/viewform",
      "captured_by": "the person who walked the form",
      "captured_on": "2026-01-15",
      "pages": [
        {
          "name": "Contact Information",
          "fields": [
            {"label": "First Name", "type": "text", "required": true},
            {"label": "Email", "type": "email", "required": true},
            {"label": "How did you hear about us?", "type": "radio",
             "options": ["A friend", "Social media", "Other"]},
            {"label": "Please tell us more", "type": "textarea",
             "show_when": "How did you hear about us?::Other"}
          ]
        }
      ]
    }

``id`` is optional on a field and is derived from the label when omitted.
``help`` on a field carries its help text. ``unknown`` on a field lists the parts
of that question the source did not show clearly (``label``, ``type``,
``required``, ``options``, ``help``, ``show_when``): a photo with a cut-off
edge, a smudged tick box, a screenshot that hides the choices. Each becomes a
finding to confirm, and the field keeps the list, so a guess never reads as a
fact. A page may carry ``intro`` (text
shown above its questions, kept as a content block), and ``repeat: true`` with
``repeat_label`` for a section that repeats once per record (a Repeater).
``platform: "brief"`` marks a form described in a brief rather than captured
from a live form; nothing about it was observed, so every aspect stays
``hand_authored`` and the connector ``none_exist``.
``show_when`` accepts a bare reference, or ``{"all": [...]}``, ``{"any": [...]}``
and ``{"not": ...}`` nested freely. A reference is either a field id/label, or
``<field>::<option label>`` to mean "that field is set to that option" - the
convention documented in ``formmigrate.conditions``.

**Values are transcribed letter-for-letter, including suspected typos.** A typo
is flagged for the client's content review, never silently corrected: a form
rebuild that quietly fixes wording is a rebuild the client cannot diff against
their original.
"""

from __future__ import annotations

import json
import re

from ... import conditions as conditions_module
from ... import ir

# Types a capture may declare, normalized onto the IR's input-type vocabulary.
_TYPE_ALIASES = {
    "text": "text", "short": "text", "shorttext": "text", "short_answer": "text",
    "textarea": "textarea", "paragraph": "textarea", "long": "textarea",
    "email": "email", "phone": "tel", "tel": "tel", "url": "url",
    "number": "number", "integer": "number", "currency": "number",
    "date": "date", "datetime": "datetime", "time": "time",
    "radio": "choice-group", "multiplechoice": "choice-group",
    "multiple_choice": "choice-group", "single_select": "choice-group",
    "checkbox": "choice-group", "checkboxes": "choice-group",
    "multiselect": "choice-group", "multi_select": "choice-group",
    "select": "select", "dropdown": "select",
    "short_text": "text", "single_line": "text", "long_text": "textarea",
    "long_answer": "textarea", "multi_line": "textarea", "multiline": "textarea",
    "single_choice": "choice-group", "choice": "choice-group",
    "multiple_select": "choice-group", "multi_choice": "choice-group",
    "select_all": "choice-group", "check_all": "choice-group",
    "boolean": "checkbox", "yesno": "choice-group", "yes_no": "choice-group",
    "yes/no": "choice-group", "rating": "choice-group", "ranking": "choice-group",
    "signature": "text", "address": "textarea",
    "scale": "choice-group", "linear_scale": "choice-group", "likert": "choice-group",
    "file": "file", "upload": "file",
    "hidden": "hidden",
}

# Types that are multi-answer, which the Field Plan needs in order to propose a
# MultiselectPicklist rather than a Picklist.
_MULTI_TYPES = {
    "checkbox", "checkboxes", "multiselect", "multi_select", "multiple_select",
    "multi_choice", "select_all", "check_all",
}

# A yes/no question written without its choices gets them, so it never reaches
# the plan as a choice with nothing to choose.
_YES_NO_TYPES = {"yesno", "yes_no", "yes/no"}

# The parts of a question a capture may mark as not read.
_UNKNOWN_PARTS = ("label", "type", "required", "options", "help", "show_when")

class CaptureError(ValueError):
    """Raised when a capture document cannot be read as written."""


# Shared with every other source whose questions are identified by their text.
_derive_id = ir.derive_field_id


def _normalize_options(raw) -> list[dict]:
    """Options as ``{"label": ...}``, accepting bare strings or objects."""
    options = []
    for entry in raw or []:
        if isinstance(entry, str):
            options.append({"label": entry})
        elif isinstance(entry, dict):
            label = entry.get("label", entry.get("value", ""))
            options.append({"label": label, "value": entry.get("value", label)})
        else:
            raise CaptureError(f"Option must be a string or object, got {entry!r}")
    return options


def _build_condition(raw, label_to_id: dict[str, str]) -> dict:
    """Turn a ``show_when`` clause into a shared condition tree."""
    if isinstance(raw, str):
        return conditions_module.ref(_resolve_reference(raw, label_to_id))
    if not isinstance(raw, dict):
        raise CaptureError(f"show_when must be a string or object, got {raw!r}")

    if "all" in raw:
        return conditions_module.all_of(
            [_build_condition(item, label_to_id) for item in raw["all"]]
        )
    if "any" in raw:
        return conditions_module.any_of(
            [_build_condition(item, label_to_id) for item in raw["any"]]
        )
    if "not" in raw:
        return conditions_module.negate(_build_condition(raw["not"], label_to_id))
    raise CaptureError(f"show_when object needs one of all/any/not, got {sorted(raw)}")


def _resolve_reference(reference: str, label_to_id: dict[str, str]) -> str:
    """Map a label-or-id reference onto the id the IR will carry.

    Accepts ``Field Label``, ``field_id``, ``Field Label::Option``, or
    ``field_id::Option``. Resolving labels here rather than making the author
    write ids is the difference between a capture a person can write correctly
    and one they cannot.
    """
    if "::" in reference:
        field_part, option_part = reference.split("::", 1)
        field_id = label_to_id.get(field_part.strip(), field_part.strip())
        return f"{field_id}::{option_part.strip()}"
    return label_to_id.get(reference.strip(), reference.strip())


def build(capture: dict) -> dict:
    """Assemble a capture document into an IR document."""
    platform = capture.get("platform") or "manual"
    pages = capture.get("pages")
    if not isinstance(pages, list) or not pages:
        raise CaptureError("A capture needs a non-empty 'pages' list.")

    # Pass 1: assign ids and index labels, so conditions in ANY page can
    # reference a field defined in any other. A single pass would silently drop
    # a forward reference.
    used_ids: set[str] = set()
    entries: list[tuple[dict, dict, str]] = []
    label_to_id: dict[str, str] = {}
    for page in pages:
        section_path = (page.get("name") or "").strip()
        for raw_field in page.get("fields") or []:
            if not isinstance(raw_field, dict):
                raise CaptureError(f"Each field must be an object, got {raw_field!r}")
            label = raw_field.get("label", "")
            field_id = raw_field.get("id") or _derive_id(label, used_ids)
            used_ids.add(field_id)
            if label:
                label_to_id.setdefault(label.strip(), field_id)
            label_to_id.setdefault(field_id, field_id)
            entries.append((raw_field, {"id": field_id}, section_path))

    fields: list[dict] = []
    conditions: list[dict] = []
    findings: list[dict] = []
    has_conditions = False

    for raw_field, assigned, section_path in entries:
        field_id = assigned["id"]
        declared_type = str(raw_field.get("type", "text")).lower().replace(" ", "_")
        input_type = _TYPE_ALIASES.get(declared_type)
        if input_type is None:
            input_type = "text"
            findings.append(
                {
                    "source": "capture",
                    "message": f"Field {field_id!r} declares unknown type "
                    f"{raw_field.get('type')!r}; treated as text. Known types: "
                    f"{', '.join(sorted(set(_TYPE_ALIASES)))}.",
                }
            )

        options = _normalize_options(raw_field.get("options"))
        if declared_type in _YES_NO_TYPES and not options:
            options = [{"label": "Yes"}, {"label": "No"}]
        validation = list(raw_field.get("validation") or [])
        if input_type in ("email", "tel", "number", "date", "datetime", "url"):
            validation.append({"tel": "phone"}.get(input_type, input_type))
        if declared_type in _MULTI_TYPES:
            validation.append("checkbox")

        fields.append(
            {
                "id": field_id,
                "label": raw_field.get("label", ""),
                "section_path": section_path,
                "input_type": input_type,
                "tag": "input",
                "required": bool(raw_field.get("required", False)),
                "validation": validation,
                "default_value": raw_field.get("default"),
                "present_in_rendered_form": True,
                "options": [
                    {"id": f"{field_id}::{option['label']}", "label": option["label"]}
                    for option in options
                ],
                "help_text": raw_field.get("help", ""),
            }
        )

        if raw_field.get("note"):
            findings.append(
                {"source": "capture", "message": f"{field_id}: {raw_field['note']}"}
            )

        unknown = raw_field.get("unknown") or []
        if isinstance(unknown, str):
            unknown = [unknown]
        if unknown:
            parts = [str(part) for part in unknown]
            strange = [part for part in parts if part not in _UNKNOWN_PARTS]
            fields[-1]["unknown"] = parts
            findings.append(
                {
                    "source": "capture",
                    "message": f"{field_id}: could not read {', '.join(parts)} from the "
                    "source. Confirm with the person before planning; whatever is "
                    "written for it is a guess.",
                }
            )
            if strange:
                findings.append(
                    {
                        "source": "capture",
                        "message": f"{field_id}: unknown part(s) {', '.join(strange)} are not "
                        f"one of {', '.join(_UNKNOWN_PARTS)}.",
                    }
                )

        if "show_when" not in raw_field:
            continue
        has_conditions = True
        tree = _build_condition(raw_field["show_when"], label_to_id)
        conditions.append(
            {
                "element_id": field_id,
                "governs": "field",
                "tag": "input",
                "expression": json.dumps(raw_field["show_when"], ensure_ascii=False),
                "tree": tree,
                "references": [],
                "unresolved_references": [],
            }
        )

    # A page (section) may be conditional too: "show_when" on the page itself.
    for page in pages:
        if "show_when" not in page:
            continue
        has_conditions = True
        name = (page.get("name") or "").strip()
        conditions.append(
            {
                "element_id": name,
                "governs": "section",
                "tag": "page",
                "expression": json.dumps(page["show_when"], ensure_ascii=False),
                "tree": _build_condition(page["show_when"], label_to_id),
                "references": [],
                "unresolved_references": [],
            }
        )

    # Conditions are hand_authored when some were written down. When none were,
    # the capture must SAY whether the form has none or nobody looked - the
    # adapter refuses to guess, because those look identical here.
    declared = dict(capture.get("coverage") or {})
    if has_conditions:
        conditions_state = "hand_authored"
    else:
        conditions_state = declared.get("conditions", "unknown")

    document = ir.new_document(
        platform=platform,
        form_id=capture.get("form_id", ""),
        form_name=capture.get("form_name", ""),
        source_url=capture.get("source_url", ""),
        coverage={
            "structure": "hand_authored",
            "fields": "hand_authored",
            # A dropdown photographed closed hides its choices: the capture
            # may say so rather than claim an empty list was read.
            "options": declared.get("options", "hand_authored"),
            "validation": declared.get("validation", "hand_authored"),
            "conditions": conditions_state,
            # A hand-captured form has no config to read. If the client says a
            # system receives these responses, the capture declares it.
            "connector": declared.get("connector", "none_exist"),
            "images": declared.get("images", "not_captured"),
            "custom_scripts": declared.get("custom_scripts", "none_exist"),
        },
    )

    document["source"]["captured_by"] = capture.get("captured_by", "")
    document["source"]["captured_on"] = capture.get("captured_on", "")
    document["form"]["section_paths"] = [
        (page.get("name") or "").strip() for page in pages if page.get("name")
    ]
    document["fields"] = fields
    document["conditions"] = conditions
    document["structure"] = [
        {
            "id": (page.get("name") or "").strip(),
            "tag": "page",
            "layout": [],
            "parent_id": None,
            "has_condition": bool(page.get("show_when")),
            **({"repeat": True, "repeat_label": page.get("repeat_label", "")}
               if page.get("repeat") else {}),
        }
        for page in pages
    ]
    document["form"]["content_blocks"] = [
        {"section": (page.get("name") or "").strip(), "title": "", "text": page["intro"]}
        for page in pages if page.get("intro")
    ]
    document["images"] = list(capture.get("images") or [])
    document["findings"] = findings

    if conditions_state == "unknown":
        document["findings"].append(
            {
                "source": "adapter",
                "message": "No conditional logic was captured and the capture "
                "does not say whether the form has any. Set coverage.conditions "
                "to 'none_exist' once someone has walked every page and "
                "confirmed it, or leave it to be reported as a gap.",
            }
        )

    resolver = conditions_module.LabelResolver(
        {field["id"]: field["label"] for field in fields},
        {
            option["id"]: (option["label"], field["label"])
            for field in fields
            for option in field["options"]
        },
    )
    return ir.finalize(document, resolver=resolver)


def build_from_file(path: str) -> dict:
    """Read a capture document from disk and assemble its IR."""
    with open(path, encoding="utf-8") as handle:
        return build(json.load(handle))
