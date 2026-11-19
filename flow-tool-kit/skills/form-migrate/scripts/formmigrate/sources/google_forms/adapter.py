"""Google Forms source adapter: a saved public form page.

A public Google Form page carries the whole form as data in a script variable,
``FB_PUBLIC_LOAD_DATA_``: every section, question, choice, required flag and
"go to section based on answer" branch, not just the first page a browser or a
text fetch shows. This adapter reads that variable from the saved page.

The variable is not a documented format. The parser reads only the positions it
is sure of, reports anything else as a finding, and never guesses a question
type: an unknown type becomes text with a finding. Check the result against the
live form (the sanity checks in ``references/sources/google-forms.md``).

What a Google Form never carries: a Salesforce connector (``connector`` is
``none_exist``), custom scripts, and response validation details beyond the
required flag.

Usage::

    from formmigrate.sources.google_forms import adapter
    document = adapter.build_from_file("_forms/google-volunteer/form.html")

Assemble a parsed Google Form into the shared IR."""

from __future__ import annotations

from ... import conditions as conditions_module
from ... import ir
from . import parser as parser_module

_INPUT_TYPES = {
    "short_answer": "text", "paragraph": "textarea", "multiple_choice": "choice-group",
    "dropdown": "select", "checkboxes": "choice-group", "linear_scale": "choice-group",
    "grid": "choice-group", "date": "date", "time": "time", "file_upload": "file",
    "rating": "choice-group",
}


def _field_id(question) -> str:
    """``entry.<id>``: the name Google uses for the answer in a prefilled link."""
    return f"entry.{question.entry_id}"


def build(model, form_id: str = "", form_name: str = "", source_url: str = "") -> dict:
    document = ir.new_document(
        platform="google-forms",
        form_id=form_id,
        form_name=form_name or model.title,
        source_url=source_url,
        coverage={
            "structure": "parsed",
            "fields": "parsed",
            "options": "parsed",
            # Only the required flag is read; response validation rules are not.
            "validation": "not_captured",
            # Branching is "go to section based on answer"; parsed when present.
            "conditions": "parsed",
            "connector": "none_exist",
            "images": "parsed",
            "custom_scripts": "none_exist",
        },
    )
    fields, option_labels = [], {}
    for question in model.questions:
        field_id = _field_id(question)
        label = question.title
        if question.kind == "grid":
            label = f"{question.title}: {question.row_label}" if question.row_label else question.title
        validation = []
        if question.kind == "checkboxes":
            validation.append("checkbox")
        if question.kind in ("date",):
            validation.append("date")
        options = []
        for choice in question.choices:
            option_id = f"{field_id}::{choice.label}"
            options.append({"id": option_id, "label": choice.label})
            option_labels[option_id] = (choice.label, label)
        entry = {
            "id": field_id,
            "label": label,
            "section_path": question.section,
            "input_type": _INPUT_TYPES.get(question.kind, "text"),
            "tag": "input",
            "required": question.required,
            "validation": validation,
            "default_value": None,
            "present_in_rendered_form": True,
            "options": options,
            "help_text": question.description,
            "source_type": question.kind,
        }
        if question.scale_labels:
            entry["scale_labels"] = question.scale_labels
        fields.append(entry)
        if any(choice.is_other for choice in question.choices):
            document["findings"].append({
                "source": "google-forms",
                "message": f"{field_id} \"{label}\" has an Other choice with its own text box; "
                           "the rebuild needs a text field shown when Other is chosen."})

    document["fields"] = fields
    document["form"]["section_paths"] = [s.title for s in model.sections]
    document["form"]["content_blocks"] = list(model.content_blocks)
    document["structure"] = [
        {"id": s.title, "tag": "page", "layout": [], "parent_id": None,
         "has_condition": False, "item_id": s.item_id, "description": s.description}
        for s in model.sections
    ]
    document["images"] = list(model.images)
    document["conditions"] = _branches(model, document)
    document["findings"] += [{"source": "google-forms", "message": m} for m in model.findings]

    resolver = conditions_module.LabelResolver(
        {f["id"]: f["label"] for f in fields}, option_labels)
    return ir.finalize(document, resolver=resolver)


def _branches(model, document) -> list[dict]:
    """Each section reached by "go to section" choices, as a section condition.

    Google Forms branching is navigation: a choice sends the respondent to a
    section. A section with incoming jumps is shown when one of those choices was
    made. A section can also be reached by simply continuing from the section
    before it, so every rule is reported for confirmation.
    """
    by_id = {s.item_id: s for s in model.sections if s.item_id}
    jumps: dict[str, list[str]] = {}
    for question in model.questions:
        for choice in question.choices:
            if choice.go_to is None:
                continue
            if choice.go_to < 0:
                document["findings"].append({
                    "source": "google-forms",
                    "message": f"Choosing \"{choice.label}\" on \"{question.title}\" submits the form "
                               "straight away; the rebuild needs the same early finish."})
                continue
            target = by_id.get(str(choice.go_to))
            if target is None:
                document["findings"].append({
                    "source": "google-forms",
                    "message": f"\"{choice.label}\" on \"{question.title}\" jumps to unknown section "
                               f"{choice.go_to}."})
                continue
            jumps.setdefault(target.title, []).append(f"{_field_id(question)}::{choice.label}")
    conditions = []
    for title, references in jumps.items():
        tree = (conditions_module.ref(references[0]) if len(references) == 1
                else conditions_module.any_of([conditions_module.ref(r) for r in references]))
        conditions.append({
            "element_id": title, "governs": "section", "tag": "page",
            "expression": " OR ".join(references), "tree": tree,
            "references": [], "unresolved_references": []})
        for entry in document["structure"]:
            if entry["id"] == title:
                entry["has_condition"] = True
    if not conditions:
        document["findings"].append({
            "source": "google-forms",
            "message": "The form data was read in full and no choice jumps to a section: "
                       "this form has no branching."})
    else:
        document["findings"].append({
            "source": "google-forms",
            "message": "Branching in Google Forms is navigation (go to section), read here as "
                       "section conditions. A section can also be reached by continuing from the "
                       "one before it; confirm each rule before the rebuild."})
    return conditions


def build_from_file(path: str, form_id: str = "", form_name: str = "", source_url: str = "") -> dict:
    with open(path, encoding="utf-8", errors="replace") as handle:
        model = parser_module.parse(handle.read())
    return build(model, form_id=form_id, form_name=form_name, source_url=source_url)
