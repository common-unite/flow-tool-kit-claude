"""The conditional-logic tree that every source adapter must produce.

Source platforms express conditional visibility in incompatible ways -
FormAssembly emits a boolean expression *string*, Jotform and Gravity Forms emit
nested *JSON*, and a Google Form has nothing machine-readable at all. This module
owns the one shape they all normalize onto, so everything downstream reads
conditions without caring where they came from.

The tree::

    {"ref": "tfa_6935"}                                          a reference
    {"op": "and", "operands": [{"ref": "a"}, {"ref": "b"}]}       all must hold
    {"op": "or",  "operands": [{"ref": "a"}, {"ref": "b"}]}       any may hold
    {"op": "not", "operand": {"ref": "a"}}                        negation

A ``ref`` is whatever id the source uses to identify the thing being tested. On
FormAssembly that is usually an *option* id rather than a field id, which is why
rendering a rule in business language needs a resolver. Adapters for platforms
that test a field against a value should reference the option id when the
platform has one, and synthesize a stable ``<field_id>::<value>`` ref when it
does not - the id only has to be resolvable by that source's own resolver.

Grammar parsing lives with the source that needs it (see
``sources/formassembly/conditions.py``); nothing here knows any platform's
syntax. Adapters that receive structured logic should build trees with the
constructors below rather than formatting a string to re-parse.
"""

from __future__ import annotations


class ConditionSyntaxError(ValueError):
    """Raised when a source's condition expression cannot be parsed.

    Defined here rather than in a source module so callers can catch one
    exception type regardless of which adapter produced the tree.
    """


# --- Constructors -----------------------------------------------------------
#
# Adapters for platforms with structured logic should use these instead of
# building dicts by hand: a typo in a key produces a tree that looks valid and
# silently evaluates to something else.


def ref(reference_id: str) -> dict:
    """A single reference to an option or field id."""
    return {"ref": reference_id}


def all_of(operands: list[dict]) -> dict:
    """AND across operands, collapsing the single-operand case."""
    return operands[0] if len(operands) == 1 else {"op": "and", "operands": operands}


def any_of(operands: list[dict]) -> dict:
    """OR across operands, collapsing the single-operand case."""
    return operands[0] if len(operands) == 1 else {"op": "or", "operands": operands}


def negate(operand: dict) -> dict:
    """NOT around a single operand."""
    return {"op": "not", "operand": operand}


# --- Inspection -------------------------------------------------------------


def references(tree: dict) -> list[str]:
    """Every id referenced by a condition tree, in order."""
    if "ref" in tree:
        return [tree["ref"]]
    if tree.get("op") == "not":
        return references(tree["operand"])
    found: list[str] = []
    for operand in tree.get("operands", []):
        found.extend(references(operand))
    return found


TICKED = " is ticked"


def describe_option(field_label: str, option_label: str) -> str:
    """How a condition on one choice reads. A choice with no label (a lone checkbox) reads as ticked, never as empty."""
    if not (option_label or "").strip():
        return f"{field_label or '?'}{TICKED}"
    return f'{field_label or "?"} is "{option_label}"'


def describe(tree: dict, resolver=None) -> str:
    """Render a condition tree as a readable sentence.

    ``resolver`` is anything exposing ``describe(id) -> str`` - a FormAssembly
    :class:`~.sources.formassembly.aliases.AliasExport`, or the
    :class:`LabelResolver` below for sources whose ids are already labels.
    Without one the raw ids are used, which is correct but unreadable.
    """
    if "ref" in tree:
        return resolver.describe(tree["ref"]) if resolver else tree["ref"]
    if tree.get("op") == "not":
        inner = describe(tree["operand"], resolver)
        if "ref" in tree["operand"] and inner.endswith(TICKED):
            return inner[: -len(TICKED)] + " is not ticked"
        return f"NOT ({inner})"

    joiner = " and " if tree.get("op") == "and" else " or "
    parts = []
    for operand in tree.get("operands", []):
        rendered = describe(operand, resolver)
        # Parenthesize nested groups so precedence stays visible when read.
        if "operands" in operand:
            rendered = f"({rendered})"
        parts.append(rendered)
    return joiner.join(parts)


def validate_tree(tree, path: str = "condition") -> list[str]:
    """Structural problems with a tree, as messages. Empty means valid.

    Hand-authored adapters are the reason this exists. A parser either produces
    a well-formed tree or raises; a human transcribing a Google Form's logic
    into JSON can write ``{"op": "and", "operand": ...}`` - the singular key on
    a group operator - which reads as an empty AND and silently matches nothing.
    """
    problems: list[str] = []
    if not isinstance(tree, dict):
        return [f"{path}: expected an object, got {type(tree).__name__}"]

    if "ref" in tree:
        if not isinstance(tree["ref"], str) or not tree["ref"].strip():
            problems.append(f"{path}: 'ref' must be a non-empty string")
        if len(tree) > 1:
            extra = sorted(key for key in tree if key != "ref")
            problems.append(f"{path}: a ref node carries extra keys {extra}")
        return problems

    operator = tree.get("op")
    if operator not in ("and", "or", "not"):
        problems.append(f"{path}: expected 'ref' or op in and/or/not, got {tree!r}")
        return problems

    if operator == "not":
        if "operand" not in tree:
            problems.append(f"{path}: 'not' requires a single 'operand'")
            return problems
        return problems + validate_tree(tree["operand"], f"{path}.operand")

    operands = tree.get("operands")
    if not isinstance(operands, list) or not operands:
        problems.append(f"{path}: '{operator}' requires a non-empty 'operands' list")
        return problems
    for index, operand in enumerate(operands):
        problems.extend(validate_tree(operand, f"{path}.operands[{index}]"))
    return problems


class LabelResolver:
    """A resolver for sources whose condition refs are already human-readable.

    Hand-authored captures (Google Forms, a screenshotted PDF) have no id
    system, so the adapter references fields and options by a synthesized id.
    This gives ``describe()`` and the IR's reference-resolution check something
    to answer against, so an unresolvable reference is still reported rather
    than passing silently because "no resolver" was mistaken for "nothing to
    check".
    """

    def __init__(self, fields: dict[str, str], options: dict[str, tuple[str, str]]):
        # fields:  id -> label.  options: id -> (option label, parent field label)
        self.fields = dict(fields)
        self.options = dict(options)

    def resolve(self, reference_id: str) -> dict | None:
        if reference_id in self.fields:
            return {"kind": "field", "id": reference_id,
                    "label": self.fields[reference_id]}
        if reference_id in self.options:
            label, parent = self.options[reference_id]
            return {"kind": "option", "id": reference_id, "label": label,
                    "field_label": parent}
        return None

    def describe(self, reference_id: str) -> str:
        found = self.resolve(reference_id)
        if not found:
            return reference_id
        if found["kind"] == "option":
            return describe_option(found["field_label"], found["label"])
        return found["label"] or reference_id
