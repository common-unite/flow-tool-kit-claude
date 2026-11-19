"""Parse a FormAssembly Salesforce connector configuration into an object graph.

The connector is the conversion spec: which records are touched, in what order,
how existing records are matched, what is skipped, and where every value comes
from.

Prefer the **read-only** view of the connector page. The edit view repeats the
org's entire object and field list inside a ``<select>`` for every node, which
inflates the page roughly tenfold and carries no information the read-only view
lacks.

Node shape::

    <div class="sobject readonly" id="sobject-8">
      <div class="collapsable-heading ...">  1 - Lookup Account record       </div>
      <div class="comment">IS Prefilled</div>
      <fieldset class="skipCondition"> <span class="formula">@IF(...)</span> </fieldset>
      <fieldset class="lookup">
        <legend>Lookup #3</legend>
        <div class="predicate" id="predicate-9"> ... </div>
        <table class="lookupErrorOptions"> no-match / one-match / multi-match </table>
      </fieldset>
      <fieldset class="sfields"> mapping rows </fieldset>
      ... nested child <div class="sobject"> nodes ...
    </div>

Child nodes nest inside their parent's element, and the heading's dotted path
("1", "1.1", "2.1.2") states the execution order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field
from html.parser import HTMLParser

# Heading text looks like "1.2 -  Update Contact record". Captures path,
# action word, and the remainder naming the object.
_HEADING_RE = re.compile(
    r"(?P<path>\d+(?:\.\d+)*)\s*-\s*(?P<action>Lookup|Update|Create new)\s+(?P<rest>.+)",
    re.IGNORECASE,
)

# "Update Account record" / "Create new Household_Membership_Application__c record"
_OBJECT_RE = re.compile(r"^(?P<object>\S+)\s+record\s*$", re.IGNORECASE)

# "Record ID of 1.2. Contact" - a reference to a prior node's created record.
_RECORD_ID_RE = re.compile(r"Record ID of\s+(?P<path>[\d.]+)\.?\s*(?P<object>.*)", re.I)

# Target field API names the page publishes for its own UI; used as a cross-check.
_MAPPED_FIELD_RE = re.compile(r'_MAPPED_SFIELDS\.push\("([^"]+)"\)')

_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Connector-level option checkboxes, keyed by the name attribute's suffix.
_OPTION_NAMES = {
    "assignment", "autoresponse", "otheremails", "useremails",
    "noblankout", "skipempty", "apiversion",
}


@dataclass
class FieldMapping:
    """One row of a node's field mapping table."""

    target_field_label: str
    source_kind: str  # form_field | formula | record_id | lookup_result | unknown
    source_value: str
    source_node_path: str | None = None
    flagged_invalid: bool = False


@dataclass
class Predicate:
    """A node in a lookup's matching criteria tree."""

    predicate_id: str
    operator: str | None = None  # and | or, for group nodes
    operands: list["Predicate"] = dataclass_field(default_factory=list)
    left_field: str | None = None
    comparison: str | None = None
    right_kind: str | None = None  # form_field | formula | record_id
    right_value: str | None = None

    @property
    def is_group(self) -> bool:
        return bool(self.operands)


@dataclass
class Lookup:
    """A node's matching configuration and its no/one/multiple-match behavior."""

    number: str | None = None
    predicate: Predicate | None = None
    on_no_match: str | None = None
    on_one_match: str | None = None
    on_multiple_matches: str | None = None


@dataclass
class ConnectorNode:
    """One object step in the connector."""

    node_id: str
    order_path: str = ""
    action: str = ""
    sobject: str = ""
    comment: str | None = None
    skip_if: str | None = None
    lookup: Lookup | None = None
    mappings: list[FieldMapping] = dataclass_field(default_factory=list)
    parent_node_id: str | None = None

    @property
    def sort_key(self) -> tuple[int, ...]:
        """Numeric ordering for the dotted path, so 1.10 follows 1.9."""
        try:
            return tuple(int(part) for part in self.order_path.split("."))
        except ValueError:
            return (999,)


@dataclass
class ConnectorModel:
    """The parsed connector."""

    nodes: dict[str, ConnectorNode] = dataclass_field(default_factory=dict)
    options: dict[str, str | bool] = dataclass_field(default_factory=dict)
    declared_target_fields: list[str] = dataclass_field(default_factory=list)
    findings: list[str] = dataclass_field(default_factory=list)

    def ordered_nodes(self) -> list[ConnectorNode]:
        """Nodes in execution order."""
        return sorted(self.nodes.values(), key=lambda node: node.sort_key)

    def branches(self) -> dict[str, list[ConnectorNode]]:
        """Nodes grouped by their top-level path segment.

        Connectors commonly carry mirrored branches (a prefilled path and a
        not-prefilled path) that duplicate most of their mappings.
        """
        grouped: dict[str, list[ConnectorNode]] = {}
        for node in self.ordered_nodes():
            root = node.order_path.split(".")[0]
            grouped.setdefault(root, []).append(node)
        return grouped


class _ConnectorParser(HTMLParser):
    """Walks the connector page, tracking node and predicate nesting."""

    def __init__(self, model: ConnectorModel):
        super().__init__(convert_charrefs=True)
        self.model = model
        # (tag, node_id, predicate_id, scope). Scopes close when their own
        # element closes - a heading wraps a nested caret <div>, so keying off
        # the tag name alone would end the heading at the wrong tag.
        self.element_stack: list[tuple[str, str | None, str | None, str | None]] = []
        self.text_buffer: list[str] = []
        self.capture_depth = 0

        self.node_stack: list[str] = []
        self.predicate_stack: list[Predicate] = []
        self.current_fieldset: str | None = None
        self.current_lookup: Lookup | None = None

        self.in_formula = False
        self.in_legend = False
        self.in_match_table = False
        self.match_labels: list[str] = []
        self.row_cells: list[tuple[str, str]] = []
        self.cell_classes = ""
        self.cell_chunks: list[tuple[str, str]] | None = None
        self.pending_em: list[str] = []
        self.leaf_marks: list[str] = []

    # -- helpers -----------------------------------------------------------

    @property
    def current_node(self) -> ConnectorNode | None:
        if not self.node_stack:
            return None
        return self.model.nodes.get(self.node_stack[-1])

    def _text(self) -> str:
        return " ".join("".join(self.text_buffer).split())

    def _reset_text(self) -> None:
        self.text_buffer = []

    # -- tag handling ------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        classes = attributes.get("class", "").split()
        element_id = attributes.get("id", "")

        node_id = None
        predicate_started = False
        scope = None

        if "sobject" in classes and element_id.startswith("sobject-"):
            node_id = element_id.split("-", 1)[1]
            self.model.nodes[node_id] = ConnectorNode(
                node_id=node_id,
                parent_node_id=self.node_stack[-1] if self.node_stack else None,
            )
            self.node_stack.append(node_id)

        elif "predicate" in classes and element_id.startswith("predicate-"):
            self._flush_predicate_text()
            predicate = Predicate(predicate_id=element_id.split("-", 1)[1])
            if self.predicate_stack:
                self.predicate_stack[-1].operands.append(predicate)
            elif self.current_lookup is not None:
                self.current_lookup.predicate = predicate
            self.predicate_stack.append(predicate)
            predicate_started = True
            self._reset_text()
            self.leaf_marks = []
            self.pending_em = []

        elif tag == "fieldset":
            for name in ("skipCondition", "lookup", "sfields"):
                if name in classes:
                    self.current_fieldset = name
                    if name == "lookup":
                        self.current_lookup = Lookup()
                        if self.current_node:
                            self.current_node.lookup = self.current_lookup
                    break

        elif tag == "div" and "collapsable-heading" in classes:
            scope = "heading"
            self._reset_text()
        elif tag == "div" and "comment" in classes:
            scope = "comment"
            self._reset_text()
        elif tag == "span" and "formula" in classes:
            self.in_formula = True
            self._reset_text()
        elif tag == "legend":
            self.in_legend = True
            self._reset_text()
        elif tag == "table" and "lookupErrorOptions" in classes:
            self.in_match_table = True
            self.match_labels = []
        elif tag == "tr":
            self.row_cells = []
        elif tag == "td":
            self.cell_classes = attributes.get("class", "")
            self.cell_chunks = []
            self._reset_text()
        elif tag == "em" and self.predicate_stack:
            self._flush_predicate_text()
            self.pending_em = []
        elif tag == "i":
            # Leaf marker: cloud = Salesforce field, clipboard = form field.
            if "fa-cloud" in classes:
                self._flush_predicate_text()
                self.leaf_marks.append("cloud")
            elif "fa-clipboard" in classes:
                self._flush_predicate_text()
                self.leaf_marks.append("clipboard")
        elif tag == "input" and attributes.get("type") == "checkbox":
            self._record_option(attributes)
        elif tag == "option" and "selected" in attributes:
            self._record_selected_option(attributes)

        if tag not in _VOID_TAGS:
            self.element_stack.append(
                (tag, node_id, element_id if predicate_started else None, scope)
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "input" and attributes.get("type") == "checkbox":
            self._record_option(attributes)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self.in_formula:
            self._finish_formula()
        elif tag == "legend" and self.in_legend:
            self._finish_legend()
        elif tag == "td":
            self._finish_cell()
        elif tag == "tr":
            self._finish_row()
        elif tag == "table" and self.in_match_table:
            self.in_match_table = False
        elif tag == "fieldset":
            self.current_fieldset = None

        # Unwind the element stack to the matching open tag, popping any node or
        # predicate scopes that close with it.
        for depth in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[depth][0] != tag:
                continue
            # Close innermost-first so a heading finishes against its own node.
            for _, closing_node, closing_predicate, closing_scope in reversed(
                self.element_stack[depth:]
            ):
                if closing_scope == "heading":
                    self._finish_heading()
                elif closing_scope == "comment":
                    self._finish_comment()
                if closing_predicate and self.predicate_stack:
                    self._finish_predicate()
                if closing_node and self.node_stack and self.node_stack[-1] == closing_node:
                    self.node_stack.pop()
            del self.element_stack[depth:]
            return

    def handle_data(self, data: str) -> None:
        self.text_buffer.append(data)
        if self.predicate_stack and data.strip():
            stripped = data.strip()
            # Operators appear as bare text in the read-only view.
            if stripped.lower() in ("and", "or"):
                self.predicate_stack[-1].operator = stripped.lower()

    # -- finishers ---------------------------------------------------------

    def _finish_heading(self) -> None:
        node = self.current_node
        text = self._text()
        self._reset_text()
        if node is None:
            return
        match = _HEADING_RE.search(text)
        if not match:
            self.model.findings.append(f"Unparsed node heading: {text[:80]!r}")
            return
        node.order_path = match.group("path")
        node.action = match.group("action").lower().replace("create new", "create")
        rest = match.group("rest").strip()
        object_match = _OBJECT_RE.match(rest)
        node.sobject = object_match.group("object") if object_match else rest

    def _finish_comment(self) -> None:
        text = self._text()
        self._reset_text()
        if self.current_node and text:
            self.current_node.comment = text

    def _finish_formula(self) -> None:
        self.in_formula = False
        formula = self._text()
        self._reset_text()
        if self.current_fieldset == "skipCondition" and self.current_node:
            self.current_node.skip_if = formula
        elif self.predicate_stack:
            self.predicate_stack[-1].right_kind = "formula"
            self.predicate_stack[-1].right_value = formula
        elif self.cell_chunks is not None:
            self.cell_chunks.append(("formula", formula))

    def _finish_legend(self) -> None:
        self.in_legend = False
        text = self._text()
        self._reset_text()
        if self.current_lookup is not None and text.lower().startswith("lookup"):
            number = text.split("#", 1)
            if len(number) == 2:
                self.current_lookup.number = number[1].strip()

    def _finish_cell(self) -> None:
        text = self._text()
        self._reset_text()
        chunks = self.cell_chunks or []
        self.cell_chunks = None
        self.row_cells.append((self.cell_classes, text))
        if chunks:
            # Remember formula chunks against the cell just closed.
            self.row_cells[-1] = (self.cell_classes + " has-formula", chunks[-1][1])
        self.cell_classes = ""

    def _finish_row(self) -> None:
        cells = self.row_cells
        self.row_cells = []
        if not cells:
            return

        if self.in_match_table and self.current_lookup is not None:
            labels = [text for _, text in cells if text]
            if len(labels) >= 3:
                self.current_lookup.on_no_match = labels[0]
                self.current_lookup.on_one_match = labels[1]
                self.current_lookup.on_multiple_matches = labels[2]
            return

        if self.current_fieldset != "sfields" or self.current_node is None:
            return

        target = next((text for cls, text in cells if "sfieldCell" in cls), None)
        source_cell = next(
            ((cls, text) for cls, text in cells if "sourceCell" in cls), None
        )
        if target is None or source_cell is None:
            return

        source_classes, source_text = source_cell
        kind, value, node_path = _classify_source(source_classes, source_text)
        self.current_node.mappings.append(
            FieldMapping(
                target_field_label=target,
                source_kind=kind,
                source_value=value,
                source_node_path=node_path,
            )
        )

    def _flush_predicate_text(self) -> None:
        """Attach buffered text to the predicate currently being built."""
        if not self.predicate_stack:
            return
        text = self._text()
        self._reset_text()
        predicate = self.predicate_stack[-1]
        if text.lower() in ("and", "or") and predicate.operands:
            predicate.operator = text.lower()
            return
        if not text or text.lower() in ("and", "or"):
            return
        if self.leaf_marks and self.leaf_marks[-1] == "cloud" and not predicate.left_field:
            predicate.left_field = text
        elif self.leaf_marks and self.leaf_marks[-1] == "clipboard":
            predicate.right_kind = "form_field"
            predicate.right_value = text
        elif predicate.left_field and not predicate.comparison:
            predicate.comparison = text
        elif predicate.comparison and predicate.right_value is None:
            # "= Record ID of <em>1. Account</em>": the value is an earlier step's record
            predicate.right_kind = "record_id" if predicate.comparison.endswith("Record ID of") else "text"
            predicate.right_value = text

    def _finish_predicate(self) -> None:
        self._flush_predicate_text()
        self.predicate_stack.pop()

    def _record_option(self, attributes: dict) -> None:
        name = attributes.get("name", "")
        key = name.rsplit("@", 1)[-1]
        if key in _OPTION_NAMES:
            self.model.options[key] = "checked" in attributes

    def _record_selected_option(self, attributes: dict) -> None:
        # The API version selector is the only meaningful <select> in this view.
        value = attributes.get("value", "")
        if value.isdigit() and "apiversion" not in self.model.options:
            return
        if value.isdigit():
            self.model.options["apiversion"] = value


def _classify_source(classes: str, text: str) -> tuple[str, str, str | None]:
    """Work out where a mapped value comes from."""
    if "has-formula" in classes:
        return "formula", text, None

    record_match = _RECORD_ID_RE.search(text)
    if record_match:
        return "record_id", text.strip(), record_match.group("path").rstrip(".")

    if text.strip().lower().startswith("formula ="):
        return "formula", text.split("=", 1)[1].strip(), None

    if not text.strip():
        # A blank source is legitimate - some questions have empty labels.
        return "form_field", "", None

    return "form_field", text.strip(), None


def _reconcile_declared_fields(model: ConnectorModel) -> None:
    """Compare parsed mappings against the page's own declared target fields.

    The page publishes ``_MAPPED_SFIELDS`` for its own UI. Comparing per object
    catches mappings the rendered tables do not show - usually orphans left
    behind when a node was deleted, which are worth reporting because they are
    dead configuration in the client's live integration.
    """
    if not model.declared_target_fields:
        return

    declared_by_object: dict[str, list[str]] = {}
    for entry in model.declared_target_fields:
        sobject, _, field = entry.partition(".")
        declared_by_object.setdefault(sobject, [])
        if field not in declared_by_object[sobject]:
            declared_by_object[sobject].append(field)

    parsed_by_object: dict[str, int] = {}
    for node in model.nodes.values():
        parsed_by_object[node.sobject] = parsed_by_object.get(node.sobject, 0) + len(
            node.mappings
        )

    for sobject, fields in declared_by_object.items():
        # Declared entries repeat once per branch; compare against the distinct
        # count, and against how many rows the branches actually rendered.
        declared_total = sum(
            1 for entry in model.declared_target_fields if entry.startswith(f"{sobject}.")
        )
        parsed = parsed_by_object.get(sobject, 0)
        if parsed >= declared_total:
            continue
        model.findings.append(
            f"{sobject}: the page declares {declared_total} mapped field(s) but only "
            f"{parsed} appear in a mapping table. Declared fields are "
            f"{', '.join(sorted(fields))} - the unrendered ones are likely orphaned "
            "configuration from a deleted node and should be confirmed with the client."
        )


def parse(html_text: str) -> ConnectorModel:
    """Parse connector configuration HTML into a :class:`ConnectorModel`."""
    model = ConnectorModel()
    parser = _ConnectorParser(model)
    parser.feed(html_text)
    parser.close()

    model.declared_target_fields = _MAPPED_FIELD_RE.findall(html_text)

    _reconcile_declared_fields(model)

    for node in model.nodes.values():
        if not node.order_path:
            model.findings.append(f"Node {node.node_id} has no order path.")
        if node.lookup and node.lookup.on_multiple_matches:
            behavior = node.lookup.on_multiple_matches.lower()
            if "most recent" in behavior or "create" in behavior:
                model.findings.append(
                    f"Node {node.order_path} ({node.sobject}) handles multiple "
                    f"matches by '{node.lookup.on_multiple_matches}' - FlowToolKit "
                    "halts instead; this needs an explicit client decision."
                )
    return model


def parse_file(path: str) -> ConnectorModel:
    """Parse a connector export from disk."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse(handle.read())
