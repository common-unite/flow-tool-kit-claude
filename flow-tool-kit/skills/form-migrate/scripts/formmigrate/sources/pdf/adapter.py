"""PDF forms: fillable (AcroForm) and flat (a printed or Word-exported form).

What a PDF gives up depends on how it was made:

    tagged flat PDF   Word and most modern authoring tools export a structure
                      tree: headings, paragraphs, lists and real tables with
                      header cells. Questions are recognised from their written
                      markers ("Label: ____", underscore answer lines, "Y/N",
                      drawn tick boxes) and the tree supplies reading order,
                      lists and tables. This is the common case and the one the
                      parser is built around.
    AcroForm PDF      has real widgets with names and types. Detected and
                      reported; widget extraction needs a PDF library that is
                      not bundled, so it is declared ``not_captured`` rather
                      than guessed from text.
    untagged flat PDF has no tree; only positioned text. Reported as a finding
                      and parsed from layout lines alone, with lower confidence.

What a PDF never carries: a Salesforce connector, validation beyond what the
wording states, and single- versus multiple-choice for drawn tick boxes (every
box looks the same). Those are declared in coverage and raised as findings so a
person decides them.

Requires poppler (``pdfinfo``, ``pdftotext``) on the PATH.

Assemble a parsed PDF form into the shared IR.

A flat PDF has no field declarations, so every question is recognised from the
marker the author wrote for a human:

    Label: ______            a text answer (the underscores are the blank)
    a paragraph + ____ lines a long answer; "(150 words max)" becomes a limit
    Label: Y/N, "- Yes or No" a yes/no choice
    Label: Pre-population    a text answer the funder fills from its records
    paragraph + tick boxes   a choice; an indented box under a box is a follow-up
    (If X is [not] selected) the next answer is conditional on option X
    If yes, ... / If yes:    the next answer or group is conditional on "Yes"
    table, labelled rows     a matrix: one answer per row and column
    table, header only       a repeating group: one row per entry

Rule order matters and follows the contract: classify by the marker that
carries the meaning, never by block kind first. Anything inferred rather than
read (single vs multiple choice, a total, an implied reveal) is recorded as a
finding so a person confirms it.

A fillable (AcroForm) PDF declares its fields, so when pypdf is installed the
fields come from the widgets themselves (``widgets.py``): name, question text
from the tooltip, type, required flag and choices, all ``parsed``. Without
pypdf they are declared ``not_captured`` and the printed text is read as for a
flat PDF, with a finding that says how to close the gap.
"""

from __future__ import annotations

import re

from ... import conditions as conditions_module
from ... import ir
from . import parser as parser_module
from . import widgets as widgets_module

# How a widget kind lands in the IR's input-type vocabulary.
_WIDGET_INPUT = {
    "text": "text", "textarea": "textarea", "checkbox": "checkbox", "radio": "choice-group",
    "select": "select", "list": "select", "multiselect": "choice-group", "signature": "text",
}


class PdfToolsMissing(RuntimeError):
    """Neither poppler nor (for a fillable PDF) pypdf is available to read the file."""

_PAGE_RE = re.compile(r"^SECTION\s+(\d+)\s*:\s*(.+)$", re.I)
_SECTION_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")
_BLANKS_RE = re.compile(r"_{3,}")
_ONLY_BLANKS_RE = re.compile(r"^_{3,}$")
_YES_NO_RE = re.compile(r"^(?P<label>.+?)[:?]?\s*(?:Y/N|-\s*Yes or No)\s*$", re.I)
_PREFILL_RE = re.compile(r"^(?P<label>.+?):\s*Pre-?population\s*$", re.I)
_IF_SELECTED_RE = re.compile(r"^\(If (?P<option>.+?) is (?P<negated>not )?selected\)\s*(?P<rest>.*)$", re.I)
_IF_YES_INLINE_RE = re.compile(r"^If yes,\s*(?P<label>.+)$", re.I)
_IF_YES_GROUP_RE = re.compile(r"^If yes\s*:?\s*$", re.I)
_SPECIFY_NOTE_RE = re.compile(r"^If selected, please specify", re.I)
_WORDS_MAX_RE = re.compile(r"\((\d+)\s+words?\s+max\)", re.I)
_OPTIONAL_RE = re.compile(r"\(?\s*(?:optional|leave blank if not applicable|if applicable)\s*\)?", re.I)
_MULTI_RE = re.compile(r"select all|all that apply|check all|select a minimum|please select all|indicate all|(?:two|one) or more of the following", re.I)
_MINIMUM_RE = re.compile(r"minimum of (\d+)", re.I)
_TOTAL_RE = re.compile(r"\(This is the total of all (?P<what>.+?)\)", re.I)
_REQUIRED_UNLESS_RE = re.compile(r"required unless marked", re.I)
_NUMBER_LABEL_RE = re.compile(r"^(number of|#)\b", re.I)
_UPLOAD_RE = re.compile(r"^(upload|attach)\b", re.I)
_LABEL_AND_PROMPT_RE = re.compile(r"^(?P<label>[^:]{3,60}):\s+(?P<prompt>\S.+)$")
_OPTION_NOTE_RE = re.compile(r"\s+[–-]\s+(?P<note>NOTE:.+)$")


def build(
    form_model,
    form_id: str = "",
    form_name: str = "",
    source_url: str = "",
    exclude_pages: tuple[int, ...] = (),
    exclude_reason: str = "",
    widgets: dict | None = None,
) -> dict:
    """Turn a :class:`~.parser.PdfFormModel` into an IR document.

    ``exclude_pages`` lists SECTION numbers the caller does not want converted
    (for example a budget section another component already covers). Excluded
    content is counted and reported, never silently dropped.

    ``widgets`` is :func:`widgets.read`'s result for a fillable PDF, or None
    when pypdf was not available to read it.
    """
    builder = _Builder(form_model, exclude_pages, exclude_reason)
    builder.run()

    fillable = form_model.form_type == "AcroForm"
    if fillable and widgets and widgets["fields"]:
        return _build_from_widgets(form_model, widgets, builder, form_id, form_name, source_url)
    findings = list(form_model.findings)
    if fillable and widgets is None:
        findings.append(
            "The PDF is fillable (AcroForm), but pypdf is not installed here, so its fields were NOT read: "
            "questions were recognised from the printed text instead and coverage.fields is not_captured. "
            "Install pypdf (pip install pypdf) and run this again, or run scripts/pdf_text.py where pypdf "
            "is available and compare its pdf-fields.json with these questions."
        )
    elif fillable:
        findings.append(
            "The PDF declares a form (AcroForm) but has no fillable fields in it, which Word exports often "
            "do; the questions come from the printed text."
        )
    elif form_model.form_type == "XFA":
        findings.append(
            "The PDF is an XFA (LiveCycle) form, which neither poppler nor pypdf reads; ask for the original "
            "form or a flattened print."
        )
    fields_read = form_model.form_type == "none" or (fillable and widgets is not None)
    # "If yes, please give ..." with no answer blank on its line: match the labels under it to the questions read.
    stated = printed_rules(builder.blocks)
    for rule in stated:
        if rule["kind"] == "sentence":
            builder.apply_printed_rule(rule)
    # The builder reads "If yes, name: ____" and "If yes:" itself; only a sentence rule can be left untied.
    unmatched = [rule for rule in stated if rule["kind"] == "sentence" and not rule.get("applied")]
    rules_read = fields_read and not unmatched
    if unmatched:
        findings.append(
            f"The printed text states {len(unmatched)} show-and-hide rule(s) that could not be tied to a question "
            f"({'; '.join(rule['sentence'][:60] for rule in unmatched[:3])}): coverage.conditions is not_captured; "
            "write each rule in form-design after confirming which question it governs."
        )

    document = ir.new_document(
        platform="pdf",
        form_id=form_id,
        form_name=form_name or form_model.title,
        source_url=source_url,
        coverage={
            "structure": "parsed" if form_model.tagged else "hand_authored",
            "fields": "parsed" if fields_read else "not_captured",
            "options": "parsed",
            # Required flags and word limits are read from wording; types beyond
            # that (email, phone) are only what the label says.
            "validation": "parsed",
            # Rules are read from the printed wording; with the fields unread, or a stated rule not tied to a
            # question, they are a known gap rather than an empty list.
            "conditions": "parsed" if rules_read else "not_captured",
            # A PDF carries no Salesforce mapping. Nothing to read.
            "connector": "none_exist",
            "images": "parsed",
            "custom_scripts": "none_exist",
        },
    )
    document["form"]["section_paths"] = builder.section_paths()
    _footer(document, form_model, findings)
    document["fields"] = builder.fields
    document["structure"] = builder.structure
    document["conditions"] = builder.conditions
    document["images"] = builder.images
    document["findings"] = [
        {"source": "pdf", "message": message} for message in findings + builder.findings
    ]
    return ir.finalize(document, resolver=builder.resolver())


def _build_from_widgets(form_model, widgets, builder, form_id, form_name, source_url) -> dict:
    """A fillable PDF: one IR field per AcroForm field, grouped by the page it is on."""
    used: set[str] = set()
    fields = []
    weak, buttons, signatures, coded = [], [], [], []
    for widget in widgets["fields"]:
        if widget["kind"] == "button":
            buttons.append(widget["name"])
            continue
        field_id = ir.derive_field_id(widget["name"], used)
        input_type = _WIDGET_INPUT.get(widget["kind"], "text")
        validation = ["checkbox"] if widget["kind"] == "multiselect" else []
        if widget["label_source"] == "name":
            weak.append(widget["name"])
        if widget["kind"] == "signature":
            signatures.append(widget["name"])
        if widget["kind"] == "radio" and any(choice.isdigit() or choice.lower().startswith("choice")
                                             for choice in widget["choices"]):
            coded.append(widget["name"])
        entry = {
            "id": field_id,
            "label": widget["label"],
            "section_path": f"Page {widget['page']}",
            "input_type": input_type,
            "tag": "pdf-widget",
            "required": widget["required"],
            "validation": validation,
            "default_value": None,
            "present_in_rendered_form": True,
            "options": [{"id": f"{field_id}::{choice}", "label": choice} for choice in widget["choices"]],
            "help_text": "",
            "pdf_field_name": widget["name"],
        }
        if widget["read_only"]:
            entry["read_only"] = True
        fields.append(entry)

    boxes = len(fields)
    groups = _group_checkboxes(fields, builder.blocks, used)
    rules = printed_rules(builder.blocks)
    conditions = []
    for rule in rules:
        conditions.extend(_widget_rule(rule, fields))
    unmatched = [rule for rule in rules if not rule.get("applied")]
    # Other printed rules ("(If Other is selected) ...", a box under a box) are not tied to the boxes yet.
    other_rules = [c for c in builder.conditions if not str((c.get("tree") or {}).get("ref", "")).endswith("::Yes")]

    scripts = widgets.get("scripts", 0)
    document = ir.new_document(
        platform="pdf",
        form_id=form_id,
        form_name=form_name or form_model.title,
        source_url=source_url,
        coverage={
            # Pages are real; the form's own sections are only in the printed text.
            "structure": "parsed",
            "fields": "parsed",
            "options": "parsed",
            "validation": "parsed",
            # Show-and-hide in a fillable PDF is JavaScript on its fields, which is not read; a rule written on
            # the page ("If yes, ...") is read from the printed text and recorded as inferred. none_exist only when
            # neither is there.
            "conditions": ("not_captured" if scripts or unmatched or other_rules
                           else ("parsed" if conditions else "none_exist")),
            "connector": "none_exist",
            "images": "parsed" if form_model.tagged else "not_captured",
            "custom_scripts": "not_captured" if scripts else "none_exist",
        },
    )
    pages = sorted({field["section_path"] for field in fields}, key=lambda path: int(path.split()[-1]))
    document["form"]["section_paths"] = pages
    document["fields"] = fields
    document["structure"] = [
        {"id": page, "tag": "page", "label": page, "layout": [], "parent_id": None, "has_condition": False}
        for page in pages
    ]
    document["conditions"] = conditions
    document["images"] = builder.images
    findings = list(form_model.findings)
    _footer(document, form_model, findings)
    findings.append(
        f"Read {boxes} fillable fields from the PDF itself (pypdf)"
        + (f", {len(fields)} questions once the check boxes of each select-all list are one question" if groups else "")
        + ", grouped by page. Their question "
        "text is each box's tooltip; the form's own section headings are in the printed text, so regroup "
        "the pages into sections in form-design."
    )
    if builder.fields:
        findings.append(
            f"The printed text alone reads as {len(builder.fields)} questions. Compare the two lists: a printed "
            "question with no box (answered on paper only) or a box with no printed question is a finding "
            "to confirm."
        )
    if weak:
        findings.append(
            f"{len(weak)} field(s) have no tooltip, so their question text is the internal field name: "
            f"{', '.join(weak[:10])}{'...' if len(weak) > 10 else ''}. Read the printed label beside each box."
        )
    if coded:
        findings.append(
            f"Radio group(s) {', '.join(coded)} name their choices with codes (Choice1, 0, 1); read the printed "
            "choice text beside each button."
        )
    if signatures:
        findings.append(
            f"Signature field(s) {', '.join(signatures)}: rebuild as the form's signature step or a typed name "
            "with a date, never a text box that claims to be a signature."
        )
    if buttons:
        findings.append(f"Push button(s) skipped, not questions: {', '.join(buttons)}.")
    if groups:
        findings.append(
            f"{sum(len(g['options']) for g in groups)} check boxes read as {len(groups)} multi-select question(s), "
            "one box per choice: " + "; ".join(f"{g['label']} ({len(g['options'])})" for g in groups) + "."
        )
    if conditions:
        findings.append(
            f"{len(conditions)} show-and-hide rule(s) read from the printed text and marked inferred: "
            + "; ".join(f"{c['source_text'][:60]} -> {c['element_id']}" for c in conditions[:6])
            + ". Confirm which questions each one governs."
        )
    if other_rules:
        findings.append(
            f"The printed text states {len(other_rules)} other show-and-hide rule(s) (\"If ... is selected\", a box "
            "under a box); write them as conditions in form-design after confirming which box each one governs."
        )
    if unmatched:
        findings.append(
            f"The printed text states {len(unmatched)} show-and-hide rule(s) that could not be tied to a box "
            f"({'; '.join(rule['sentence'][:60] for rule in unmatched[:3])}): coverage.conditions is not_captured; "
            "write each rule in form-design after confirming which box it governs."
        )
    if scripts:
        findings.append(
            f"{scripts} JavaScript action(s) found on fields or in the document: calculations and show-and-hide "
            "rules live there and were not read. Open the PDF's form editor to read them."
        )
    document["findings"] = [{"source": "pdf", "message": message} for message in findings]
    return ir.finalize(document, resolver=_resolver(fields))


# --- printed text read alongside the fillable fields --------------------------------------------

_LABEL_STOP = {"the", "a", "an", "of", "your", "you", "please", "is", "are", "do", "does", "in", "to", "for", "and",
               "or", "this", "that", "if", "yes", "s", "select", "all", "apply", "which", "what", "give", "details"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _LABEL_STOP}


def _overlap(printed: str, label: str) -> float:
    """How much of the printed text's meaningful words the label holds (0 to 1)."""
    a, b = _words(printed), _words(label)
    return len(a & b) / len(a) if a and b else 0.0


def _is_heading(text: str) -> bool:
    return bool(_PAGE_RE.match(text) or (_SECTION_RE.match(text) and text.upper() == text))


def printed_rules(blocks) -> list[dict]:
    """The show-and-hide rules the printed wording states: an "If yes" after a yes/no question.

    Each is ``{"kind", "question", "sentence", "labels"}``: ``kind`` is ``inline`` ("If yes, name: ____", the
    answer on the same line), ``group`` ("If yes:" heading the lines under it) or ``sentence`` ("If yes, please
    give your license details." with the labels on the lines under it); ``labels`` are the printed labels the rule
    governs, read until the next question, choice list or heading.
    """
    rules = []
    question = None
    for index, block in enumerate(blocks):
        text = block.text
        if _is_heading(text):
            question = None
            continue
        inline = _IF_YES_INLINE_RE.match(text)
        group = _IF_YES_GROUP_RE.match(text)
        if (inline or group) and question:
            labels = []
            if inline and _BLANKS_RE.search(text):
                kind = "inline"
                labels.append(_split_blanks(inline.group("label"))[0])
            else:
                kind = "group" if group else "sentence"
                for following in blocks[index + 1:index + 12]:
                    line = following.text
                    if (_is_heading(line) or following.kind == "option" or "?" in line or _MULTI_RE.search(line)
                            or _YES_NO_RE.match(line) or _IF_YES_INLINE_RE.match(line) or _IF_YES_GROUP_RE.match(line)
                            or not (line.rstrip().endswith(":") or _BLANKS_RE.search(line))):
                        break
                    # One printed line can hold several labels ("Make: ____  Size: ____").
                    labels.extend(part.strip() for part in re.findall(r"([^:_]+):", line) or [_split_blanks(line)[0]])
            rules.append({"kind": kind, "question": question, "sentence": text, "labels": [l for l in labels if l]})
            continue
        yes_no = _YES_NO_RE.match(text)
        if yes_no:
            question = yes_no.group("label")
        elif "?" in text and not _MULTI_RE.search(text):
            question = text.split("?")[0] + "?"
    return rules


def _yes_reference(field: dict) -> str | None:
    """The reference that reads "the answer is Yes": the Yes choice, or a single check box itself."""
    for option in field.get("options") or []:
        if option["label"].strip().lower() in ("yes", "y"):
            return option["id"]
    if field.get("input_type") == "checkbox":
        return field["id"]
    return None


def _widget_rule(rule: dict, fields: list[dict]) -> list[dict]:
    """Tie one printed rule to the fillable fields: the yes/no box it reads and the boxes it governs."""
    scored = [(round(_overlap(rule["question"], f["label"]), 3), -position, f) for position, f in enumerate(fields)
              if _yes_reference(f)]
    best = max(scored, key=lambda item: item[:2], default=None)
    if not best or best[0] < 0.6:
        return []
    control = best[2]
    after = fields[fields.index(control) + 1:]
    governed = []
    for label in rule["labels"]:
        options = [(round(_overlap(label, f["label"]), 3), -position, f) for position, f in enumerate(after)
                   if f not in governed]
        match = max(options, key=lambda item: item[:2], default=None)
        if match and match[0] >= 0.5:
            governed.append(match[2])
    guessed = not governed and bool(after)
    if guessed:
        governed = after[:1]
    rule["applied"] = bool(governed)
    note = ("the box right after the question, by position: no printed label under the rule matched a box"
            if guessed else "the boxes whose question text matches the printed labels under the rule")
    return [{
        "element_id": f["id"], "governs": "field", "tag": "pdf-widget",
        "tree": conditions_module.ref(_yes_reference(control)), "references": [], "unresolved_references": [],
        "inferred": True, "source_text": rule["sentence"], "note": f"Inferred from the printed text; governs {note}.",
    } for f in governed]


def _resolver(fields: list[dict]):
    field_labels = {field["id"]: field["label"] for field in fields}
    option_labels = {option["id"]: (option["label"], field["label"]) for field in fields for option in field["options"]}
    return conditions_module.LabelResolver(field_labels, option_labels)


def _select_all_lists(blocks) -> list[tuple[str, set[str]]]:
    """Each printed "select all that apply" question with the choice lines printed under it."""
    lists = []
    for index, block in enumerate(blocks):
        if not _MULTI_RE.search(block.text):
            continue
        choices = set()
        for following in blocks[index + 1:index + 40]:
            line = following.text
            if _is_heading(line) or "?" in line or _MULTI_RE.search(line) or line.rstrip().endswith(":") or len(line) > 60:
                break
            choices.add(line.strip().lower())
        lists.append((block.text, choices))
    return lists


def _question_text(text: str) -> tuple[str, str]:
    """A printed select-all question without its instruction, and the instruction as help text."""
    instruction = re.search(r"\(([^)]*(?:all that apply|select all|check all)[^)]*)\)", text, re.I)
    label = re.sub(r"\s+", " ", text.replace(instruction.group(0), "") if instruction else text).strip()
    return label, (instruction.group(1).strip().capitalize().rstrip(".") + "." if instruction else "Select all that apply.")


def _group_checkboxes(fields: list[dict], blocks, used: set[str]) -> list[dict]:
    """Merge the check boxes of one select-all question into one multi-select question, in place.

    A fillable PDF draws each choice of a "select all that apply" list as its own check box. Two patterns tie them:
    tooltips that share a prefix ("Days available: Monday", "Days available: Friday"), or box labels that are the
    choice lines printed under a select-all question. Each group keeps every box's name on its option.
    """
    printed = _select_all_lists(blocks)
    runs, run = [], []
    for field in fields + [None]:
        key = None
        if field is not None and field["input_type"] == "checkbox" and ":" in field["label"]:
            key = ("prefix", field["label"].split(":", 1)[0].strip())
        elif field is not None and field["input_type"] == "checkbox":
            key = next((("printed", question) for question, choices in printed
                        if field["label"].strip().lower() in choices), None)
        if run and key == run[0][0]:
            run.append((key, field))
            continue
        if len(run) >= 2:
            runs.append(run)
        run = [(key, field)] if key else []
    groups = []
    for run in runs:
        kind, name = run[0][0]
        members = [field for _, field in run]
        if kind == "prefix":
            question = max(printed, key=lambda item: _overlap(name, item[0]), default=None)
            matched = question and _overlap(name, question[0]) >= 0.6
            label, help_text = _question_text(question[0]) if matched else (name, "Select all that apply.")
            choice = lambda field: field["label"].split(":", 1)[1].strip()  # noqa: E731
        else:
            label, help_text = _question_text(name)
            choice = lambda field: field["label"].strip()  # noqa: E731
        group_id = ir.derive_field_id(name if kind == "prefix" else label.rstrip("?"), used)
        group = {
            **{key: members[0][key] for key in ("section_path", "tag", "default_value", "present_in_rendered_form")},
            "id": group_id,
            "label": label,
            "input_type": "choice-group",
            "required": any(field["required"] for field in members),
            "validation": ["checkbox"],
            "options": [{"id": f"{group_id}::{choice(field)}", "label": choice(field),
                         "pdf_field_name": field["pdf_field_name"]} for field in members],
            "help_text": help_text,
            "pdf_field_names": [field["pdf_field_name"] for field in members],
        }
        start = fields.index(members[0])
        fields[start:start + len(members)] = [group]
        groups.append(group)
    return groups


def _footer(document: dict, form_model, findings: list[str]) -> None:
    """The line at the foot of every page becomes the template footer, never page text."""
    footer = getattr(form_model, "footer", None)
    if not footer:
        return
    document["form"]["footer_text"] = footer
    findings.append(
        f"'{footer}' is printed at the foot of every page: it becomes the template footer "
        "(Template_Footer_Text__c), never page body text."
    )


class _Builder:
    def __init__(self, model, exclude_pages, exclude_reason):
        self.blocks = model.blocks
        self.exclude_pages = set(exclude_pages)
        self.exclude_reason = exclude_reason
        self.fields: list[dict] = []
        self.structure: list[dict] = []
        self.conditions: list[dict] = []
        self.images: list[dict] = []
        self.findings: list[str] = []
        self.used_ids: set[str] = set()
        self.order = 0
        self.page = None
        self.section = None
        self.group = None
        self.page_number = None
        self.excluded: dict[int, dict] = {}
        self.pending_group_condition = None
        self.last_choice = None
        # A "select all" instruction paragraph governs the choice lists that follow it.
        self.select_all_instruction = False
        self.specify_options: dict[str, list[str]] = {}
        # Capitalised words used inside ordinary sentences are acronyms (LOA, CBSS) and stay capitalised.
        self.acronyms = frozenset(
            word for block in self.blocks if not block.text.isupper()
            for word in re.findall(r"\b[A-Z]{2,6}\b", block.text)
        )
        self.default_required = any(_REQUIRED_UNLESS_RE.search(block.text) for block in self.blocks)
        if self.default_required:
            self.findings.append(
                "The form states every question is required unless marked Optional; answers are "
                "required by default and optional where the wording says Optional, 'if applicable' "
                "or 'leave blank if not applicable'."
            )

    # --- output helpers ---------------------------------------------------

    def _next_order(self) -> int:
        self.order += 1
        return self.order

    def _path(self) -> str:
        parts = [node["label"] for node in (self.page, self.section, self.group) if node]
        return "/".join(parts)

    def _parent_id(self):
        for node in (self.group, self.section, self.page):
            if node:
                return node["id"]
        return None

    def _node(self, tag, label, layout=None, text=None, parent_id=None):
        node = {
            "id": f"{tag}-{len(self.structure) + 1}",
            "tag": tag,
            "label": label,
            "layout": layout or [],
            "parent_id": parent_id if parent_id is not None else self._parent_id(),
            "has_condition": False,
            "order": self._next_order(),
        }
        if text is not None:
            node["text"] = text
        self.structure.append(node)
        return node

    def _content(self, text):
        if _MULTI_RE.search(text):
            self.select_all_instruction = True
        self._node("content", text[:60], text=text)

    def _field(self, label, input_type, *, help_text="", validation=None, options=None,
               required=None, multi=False, extra=None):
        clean_label, optional, notes = _clean_label(label)
        split = _LABEL_AND_PROMPT_RE.match(clean_label)
        if input_type == "textarea" and split and split.group("label").strip().upper() != "NOTE":
            clean_label = split.group("label").strip()
            help_text = " ".join(part for part in (split.group("prompt"), help_text) if part)
        clean_label = clean_label[:1].upper() + clean_label[1:]
        if input_type in ("text", "textarea"):
            self.select_all_instruction = False
        field_id = ir.derive_field_id(clean_label, self.used_ids)
        self.used_ids.add(field_id)
        if required is None:
            required = self.default_required and not optional and not self._section_optional()
        tokens = list(validation or [])
        if multi and "checkbox" not in tokens:
            tokens.append("checkbox")
        entry = {
            "id": field_id,
            "label": clean_label,
            "section_path": self._path(),
            "input_type": input_type,
            "tag": "pdf",
            "required": bool(required),
            "validation": tokens,
            "default_value": None,
            "present_in_rendered_form": True,
            "options": [
                {"id": f"{field_id}::{option}", "label": option} for option in (options or [])
            ],
            "help_text": " ".join(part for part in (notes, help_text) if part).strip(),
            "parent_id": self._parent_id(),
            "section_id": (self.section or self.page or {}).get("id"),
            "order": self._next_order(),
        }
        if extra:
            entry.update(extra)
        self.fields.append(entry)
        if self.pending_group_condition:
            self._condition(entry, self.pending_group_condition, "field")
        return entry

    def _condition(self, target, tree, governs, inferred=False):
        self.conditions.append({
            "element_id": target["id"],
            "governs": governs,
            "tree": tree,
            "inferred": inferred,
        })
        target["has_condition"] = True

    def apply_printed_rule(self, rule: dict) -> None:
        """A "sentence" rule on a flat PDF: the questions under it whose labels match are shown on Yes."""
        control = next((f for f in reversed(self.fields) if _overlap(rule["question"], f["label"]) >= 0.6
                        and _yes_reference(f)), None)
        if control is None:
            return
        after = self.fields[self.fields.index(control) + 1:]
        for label in rule["labels"]:
            match = next((f for f in after if _overlap(label, f["label"]) >= 0.5 and not f.get("has_condition")), None)
            if match:
                self.conditions.append({"element_id": match["id"], "governs": "field",
                                        "tree": conditions_module.ref(_yes_reference(control)), "inferred": True,
                                        "source_text": rule["sentence"]})
                match["has_condition"] = True
                rule["applied"] = True

    def _section_optional(self) -> bool:
        return any(node and "optional" in node["label"].lower() for node in (self.page, self.section, self.group))

    def section_paths(self):
        return sorted({field["section_path"] for field in self.fields if field["section_path"]})

    def resolver(self):
        field_labels = {field["id"]: field["label"] for field in self.fields}
        option_labels = {
            option["id"]: (option["label"], field["label"])
            for field in self.fields for option in field["options"]
        }
        return conditions_module.LabelResolver(field_labels, option_labels)

    # --- the pass ---------------------------------------------------------

    def run(self):
        index = 0
        while index < len(self.blocks):
            index = self._step(index)
        for option, lists in self.specify_options.items():
            self.findings.append(
                f"Option '{option}' in {len(lists)} list(s) ({', '.join(lists[:3])}{'...' if len(lists) > 3 else ''}) asks the "
                "respondent to specify in the text box after the lists: consider a conditional text answer."
            )
        for number, counts in sorted(self.excluded.items()):
            self.findings.append(
                f"SECTION {number} was excluded at the caller's request"
                + (f" ({self.exclude_reason})" if self.exclude_reason else "")
                + f": {counts['tables']} tables, {counts['options']} tick boxes and "
                f"{counts['blanks']} answer blanks were not converted."
            )

    def _step(self, index):
        block = self.blocks[index]
        text = block.text

        page_match = _PAGE_RE.match(text)
        if page_match:
            self.page_number = int(page_match.group(1))
            self.page = self.section = self.group = None
            self.pending_group_condition = None
            if self.page_number not in self.exclude_pages:
                self.page = self._node("page", f"Section {page_match.group(1)}: {_title(page_match.group(2), self.acronyms)}", parent_id=None)
            return index + 1

        if self.page_number in self.exclude_pages:
            counts = self.excluded.setdefault(self.page_number, {"tables": 0, "options": 0, "blanks": 0})
            counts["tables"] += block.kind == "table"
            counts["options"] += block.kind == "option"
            counts["blanks"] += bool(_BLANKS_RE.search(text))
            return index + 1

        section_match = _SECTION_RE.match(text)
        if section_match and text.upper() == text:
            self.section = self._node("section", f"{section_match.group(1)} {_title(section_match.group(2), self.acronyms)}",
                                      parent_id=self.page["id"] if self.page else None)
            self.group = None
            self.pending_group_condition = None
            self.select_all_instruction = False
            return index + 1

        if block.kind == "figure":
            self.images.append({"alt": text, "order": self._next_order()})
            return index + 1
        if block.kind == "table":
            return self._table(index)
        if block.kind == "option":
            # Options reached without a question: the preceding content paragraph is the question.
            return self._choice(index, self._pop_content_label() or "Please select")

        if _IF_YES_GROUP_RE.match(text) and self.last_choice:
            self.pending_group_condition = self._yes_tree(self.last_choice)
            return index + 1

        inline = _IF_YES_INLINE_RE.match(text)
        if inline and _BLANKS_RE.search(text) and self.last_choice:
            label, after = _split_blanks(inline.group("label"))
            field = self._field(label, "text", help_text=after)
            self._condition(field, self._yes_tree(self.last_choice), "field")
            return index + 1

        prefill = _PREFILL_RE.match(text)
        if prefill:
            self._field(prefill.group("label"), "text", extra={"prefill_hint": "Pre-population"})
            self.pending_group_condition = None
            return index + 1

        yes_no = _YES_NO_RE.match(text)
        if yes_no and not _BLANKS_RE.search(text):
            self.pending_group_condition = None
            self.group = None
            self.last_choice = self._field(yes_no.group("label"), "choice-group", options=["Yes", "No"])
            return index + 1

        if _ONLY_BLANKS_RE.match(text):
            return self._long_answer(index, self._pop_content_label())

        if _BLANKS_RE.search(text) or block.kind == "list_item" and _BLANKS_RE.search(text):
            label, after = _split_blanks(text)
            self._blank_field(label, after)
            return index + 1

        if _UPLOAD_RE.match(text):
            self.group = None
            details = []
            while index + 1 < len(self.blocks) and self.blocks[index + 1].kind == "paragraph" and not _PAGE_RE.match(self.blocks[index + 1].text) and not _SECTION_RE.match(self.blocks[index + 1].text):
                index += 1
                details.append(self.blocks[index].text)
            label = re.sub(r"^\d+\.\d+\s+", "", self.section["label"]) if self.section else text
            self._field(label, "file", help_text=" ".join([text] + details))
            return index + 1
        following = self.blocks[index + 1] if index + 1 < len(self.blocks) else None
        if following is not None and following.kind == "option":
            return self._choice(index + 1, text)
        if following is not None and _ONLY_BLANKS_RE.match(following.text):
            self.pending_group_condition = None
            return self._long_answer(index + 1, text)
        if following is not None and len(text) <= 90 and _BLANKS_RE.search(following.text) and not _ONLY_BLANKS_RE.match(following.text):
            # A short line that introduces a run of blanks is a group heading.
            self.group = self._node("group", text.rstrip(": "), parent_id=(self.section or self.page or {}).get("id"))
            return index + 1
        if block.kind == "list_item":
            self._content("• " + text)
            return index + 1
        self._content(text)
        return index + 1

    # --- rules --------------------------------------------------------------

    def _pop_content_label(self):
        for position in range(len(self.structure) - 1, -1, -1):
            node = self.structure[position]
            if node["tag"] != "content":
                return None
            self.structure.pop(position)
            return node["text"]
        return None

    def _blank_field(self, label, after):
        validation = []
        lower = label.lower()
        if "email" in lower:
            validation.append("email")
        elif "telephone" in lower or "phone" in lower or lower.startswith("fax"):
            validation.append("phone")
        elif "website" in lower or "facebook" in lower or "instagram" in lower or "linkedin" in lower or "twitter" in lower or "youtube" in lower:
            validation.append("url")
        elif _NUMBER_LABEL_RE.search(label) or (self.group and self.group["label"].startswith("#")):
            validation.append("integer")
        extra = {}
        total = _TOTAL_RE.search(label)
        if total:
            members = [field["id"] for field in self.fields if field.get("parent_id") == (self.group or {}).get("id") and "integer" in field["validation"]]
            extra["calculation"] = {"sum_of": members, "described_as": total.group("what")}
            self.findings.append(f"'{_clean_label(label)[0]}' is described as a total of {total.group('what')}; it can be a calculated field instead of a typed answer.")
            if "integer" not in validation:
                validation.append("integer")
        self._field(label, "text", help_text=after, validation=validation, extra=extra)

    def _long_answer(self, index, label):
        """A question followed by underscore lines: one long answer."""
        self.group = None
        while index < len(self.blocks) and _ONLY_BLANKS_RE.match(self.blocks[index].text):
            index += 1
        if not label and self.structure and self.structure[-1] is self.section:
            label = re.sub(r"^\d+\.\d+\s+", "", self.section["label"])
        if not label:
            self.findings.append("An answer area had no question text before it; it was skipped.")
            return index
        validation = []
        words = _WORDS_MAX_RE.search(label)
        if words:
            validation.append(f"maxwords-{words.group(1)}")
        self._field(label, "textarea", validation=validation)
        return index

    def _choice(self, index, question):
        """Tick-box options after a question, with follow-ups, notes and per-option answers."""
        self.group = None
        multi = bool(_MULTI_RE.search(question)) or self.select_all_instruction
        minimum = _MINIMUM_RE.search(question)
        field = self._field(question, "choice-group", multi=multi,
                            validation=[f"minselect-{minimum.group(1)}"] if minimum else [])
        if not multi and not re.fullmatch(r"(?i)yes|no", self.blocks[index].text.strip()):
            self.findings.append(
                f"'{field['label']}': every option is a drawn tick box, which cannot say whether one or "
                "several answers are allowed. Treated as single choice; confirm with the client."
            )
        base_indent = self.blocks[index].indent
        last_option = None
        pending_condition = None
        while index < len(self.blocks):
            block = self.blocks[index]
            text = block.text
            if _PAGE_RE.match(text) or (_SECTION_RE.match(text) and text.upper() == text):
                break
            if block.kind == "option":
                indent_gap = (block.indent or 0) - (base_indent or 0)
                if last_option is not None and indent_gap > 12:
                    # An option indented under an option is a follow-up choice revealed by it.
                    index = self._follow_up(index, field, last_option)
                    continue
                note = _OPTION_NOTE_RE.search(text)
                label, _, _ = _clean_label(_OPTION_NOTE_RE.sub("", text).rstrip(":"))
                option = {"id": f"{field['id']}::{label}", "label": label}
                if note:
                    option["help"] = note.group("note")
                field["options"].append(option)
                last_option = label
                index += 1
                continue
            if last_option and block.kind == "paragraph" and not _IF_SELECTED_RE.match(text) and (text.startswith("(") or text[:1].islower()):
                # A description under an option, or its continuation across a page break.
                option = field["options"][-1]
                option["help"] = " ".join(part for part in (option.get("help"), text.strip("()")) if part)
                index += 1
                continue
            if _SPECIFY_NOTE_RE.match(text) and last_option:
                self.specify_options.setdefault(last_option, []).append(field["label"])
                index += 1
                continue
            if _ONLY_BLANKS_RE.match(text) and last_option:
                # An answer area straight after an option: describe that option. Shown when it is ticked.
                while index < len(self.blocks) and _ONLY_BLANKS_RE.match(self.blocks[index].text):
                    index += 1
                self.group = None
                prompt = "Describe the other service" if last_option.lower() == "other" else f"How {last_option} is offered"
                answer = self._field(prompt, "textarea", help_text=field["options"][-1].get("help", ""))
                self._condition(answer, conditions_module.ref(f"{field['id']}::{last_option}"), "field", inferred=True)
                continue
            selected = _IF_SELECTED_RE.match(text)
            if selected:
                option = self._match_option(field, selected.group("option"))
                tree = conditions_module.ref(f"{field['id']}::{option}") if option else None
                if tree is not None and selected.group("negated"):
                    tree = conditions_module.negate(tree)
                if option is None:
                    self.findings.append(f"Condition '{text[:80]}' names an option not found in '{field['label']}'.")
                pending_condition = (tree, selected.group("rest"))
                index += 1
                continue
            if pending_condition and not _ONLY_BLANKS_RE.match(text):
                # The note paragraph(s) under a condition are the conditional question.
                tree, rest = pending_condition
                label_parts = [part for part in (rest, text) if part]
                index += 1
                while index < len(self.blocks) and self.blocks[index].kind == "paragraph" and not _ONLY_BLANKS_RE.match(self.blocks[index].text) and not _IF_SELECTED_RE.match(self.blocks[index].text) and self.blocks[index].kind != "option":
                    label_parts.append(self.blocks[index].text)
                    index += 1
                while index < len(self.blocks) and _ONLY_BLANKS_RE.match(self.blocks[index].text):
                    index += 1
                answer = self._field(" ".join(label_parts), "textarea")
                if tree is not None:
                    self._condition(answer, tree, "field")
                pending_condition = None
                continue
            break
        self.last_choice = field
        if not field["options"]:
            self.findings.append(f"'{field['label']}' looked like a choice but no options were found.")
        return index

    def _follow_up(self, index, parent_field, parent_option):
        """Indented tick boxes under an option: a separate choice shown when that option is ticked."""
        base = self.blocks[index].indent
        follow = self._field(parent_option, "choice-group", multi=True)
        self._condition(follow, conditions_module.ref(f"{parent_field['id']}::{parent_option}"), "field", inferred=True)
        while index < len(self.blocks) and self.blocks[index].kind == "option" and (self.blocks[index].indent or 0) >= (base or 0) - 2:
            label, _, _ = _clean_label(self.blocks[index].text.rstrip(":"))
            follow["options"].append({"id": f"{follow['id']}::{label}", "label": label})
            index += 1
        return index

    def _match_option(self, field, name):
        wanted = name.lower().replace("/", " ").split()
        for option in field["options"]:
            words = option["label"].lower().replace("/", " ")
            if all(word.rstrip("s") in words for word in wanted[:3]):
                return option["label"]
        return None

    def _yes_tree(self, choice_field):
        return conditions_module.ref(f"{choice_field['id']}::Yes")

    def _table(self, index):
        """Classify a table by its empty cells: matrix, repeating group, or content."""
        tables = [self.blocks[index]]
        index += 1
        while index < len(self.blocks) and self.blocks[index].kind == "table":
            tables.append(self.blocks[index])
            index += 1
        rows = [row for table in tables for row in table.rows if row]
        header = rows[0] if rows and all(cell["header"] for cell in rows[0]) else None
        body = rows[1:] if header else rows
        answer_cells = [cell for row in body for cell in row[1:]]
        labels_only = all(len(cell["text"]) <= 60 for row in rows for cell in row) and len(rows) <= 3
        if self.page is None:
            self._content_table(rows)
        elif header and body and all(row and row[0]["text"] for row in body) and all(not cell["text"] for cell in answer_cells):
            self._matrix(tables, header, body)
        elif labels_only and any(not cell["text"] for row in rows for cell in row) or (header and all(not cell["text"] for row in body for cell in row)):
            self._repeat(tables)
        else:
            self._content_table(rows)
        return index

    def _matrix(self, tables, header, body):
        # A matrix split across pages repeats in two tables; later tables add rows only.
        extra_rows = [row for table in tables[1:] for row in table.rows if row and not all(cell["header"] for cell in row)]
        rows = body + [row for row in extra_rows if row not in body]
        columns = [cell["text"] for cell in header[1:]]
        instruction = self._pop_content_label()
        group = self._node("matrix", instruction or header[0]["text"], layout=["matrix"])
        group["columns"] = columns
        group["rows"] = [row[0]["text"] for row in rows]
        previous_group, self.group = self.group, group
        for row in rows:
            for column in columns:
                self._field(f"{row[0]['text']} - {column}", "textarea", required=False)
        self.group = previous_group
        at_least = re.search(r"(\d+) or more", instruction or "")
        self.findings.append(
            f"Table '{group['label'][:70]}' is a matrix of {len(rows)} rows x {len(columns)} answer columns"
            + (f"; the form asks for at least {at_least.group(1)} rows to be completed, so no single cell is required." if at_least else ".")
        )

    def _repeat(self, tables):
        # Every labelled cell is a column; a second label row (an address block) continues the first.
        columns = [cell["text"] for table in tables for row in table.rows for cell in row if cell["text"]]
        instruction = self._pop_content_label()
        group = self._node("repeat", instruction or "Entries", layout=["repeat"])
        if self.pending_group_condition:
            self.conditions.append({"element_id": group["id"], "governs": "section", "tree": self.pending_group_condition, "inferred": False})
            group["has_condition"] = True
        previous_group, self.group = self.group, group
        saved_condition, self.pending_group_condition = self.pending_group_condition, None
        for column in columns:
            validation = []
            lower = column.lower()
            if "email" in lower:
                validation.append("email")
            elif "amount" in lower:
                validation.append("currency")
            self._field(column, "text", validation=validation, required=False)
        self.group = previous_group
        self.findings.append(
            f"Table '{group['label'][:70]}' has headers and empty rows only: a repeating group with {len(columns)} "
            "columns (one row per entry)."
        )

    def _content_table(self, rows):
        text = "\n".join(" | ".join(cell["text"] for cell in row) for row in rows if any(cell["text"] for cell in row))
        if text:
            node = self._node("content", text[:60], text=text)
            node["table_rows"] = [[cell["text"] for cell in row] for row in rows]


def _title(text: str, acronyms: frozenset = frozenset()) -> str:
    """Title-case an all-caps heading, keeping words the document writes in capitals in its sentences."""
    text = parser_module.normalize(text)
    if not text.isupper():
        return text
    titled = re.sub(r"\((\w)\)", lambda match: f"({match.group(1).lower()})", text.title())
    return " ".join(word.upper() if word.upper() in acronyms else word for word in titled.split(" "))


def _split_blanks(text: str) -> tuple[str, str]:
    """Label before the blank, and any hint written after it."""
    parts = _BLANKS_RE.split(text, maxsplit=1)
    before = parts[0]
    after = parts[1] if len(parts) > 1 else ""
    return before.strip().rstrip(":").strip(), after.strip().strip("_").strip()


def _clean_label(label: str) -> tuple[str, bool, str]:
    """Strip optional markers and word limits into help text; return (label, optional, notes)."""
    text = parser_module.normalize(label).lstrip("*").strip()
    optional = bool(_OPTIONAL_RE.search(text))
    notes = []
    words = _WORDS_MAX_RE.search(text)
    if words:
        notes.append(f"{words.group(1)} words max.")
        text = _WORDS_MAX_RE.sub("", text)
    if optional:
        text = _OPTIONAL_RE.sub("", text)
        notes.insert(0, "Optional.")
    total = _TOTAL_RE.search(text)
    if total:
        notes.append(total.group(0).strip("()") + ".")
        text = _TOTAL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\s,]+\)", ")", text)
    text = re.sub(r"[\s,(–-]+$", "", text).rstrip(":").strip()
    if text.count("(") > text.count(")"):
        text += ")"
    return text, optional, " ".join(notes)


def build_from_file(path: str, form_id: str = "", form_name: str = "", source_url: str = "",
                    exclude_pages: tuple[int, ...] = (), exclude_reason: str = "") -> dict:
    """Parse a PDF and assemble its IR in one call.

    Uses poppler for the printed text and pypdf for fillable fields, each when
    present. Raises :class:`PdfToolsMissing` when neither can read the file.
    """
    widgets = widgets_module.read(path)
    if parser_module.poppler_available():
        model = parser_module.parse_file(path)
    elif widgets and widgets["fields"]:
        model = parser_module.PdfFormModel(path=path, pages=widgets["pages"], tagged=False,
                                           form_type="AcroForm", title="")
        model.findings.append(
            "poppler is not installed, so the printed text (instructions, section headings, questions "
            "answered on paper only) was not read; only the fillable fields were."
        )
    else:
        raise PdfToolsMissing(
            "This PDF cannot be read here: poppler (pdfinfo, pdftotext) is not installed"
            + (" and pypdf is not installed either" if widgets is None else " and the PDF has no fillable fields")
            + ". Run scripts/pdf_text.py for whatever text this machine can get, or read the PDF directly "
            "and write capture.json for the manual adapter."
        )
    return build(model, form_id=form_id, form_name=form_name, source_url=source_url,
                 exclude_pages=exclude_pages, exclude_reason=exclude_reason,
                 widgets=widgets if model.form_type == "AcroForm" else None)
