"""Parse FormAssembly's conditional-visibility grammar into the shared tree.

wForms emits conditional logic declaratively into the rendered form as
``data-condition`` attributes. The grammar is small and closed, so it gets a
hand-written recursive-descent parser rather than a general expression library::

    `#tfa_11847` AND `#tfa_11841`
    `#tfa_11848` OR (`#tfa_11847` AND `#tfa_11840`)
    NOT (`#tfa_11158`)
    NOT (`#tfa_6895`) AND (`#tfa_6935` OR `#tfa_6936`)

References are backtick-quoted ``#id`` values and are usually *option* ids, not
field ids - which is why rendering a rule in business language requires the
alias export.

This module is FormAssembly-only. The tree it produces, and the ``references``
/ ``describe`` helpers that read one, belong to ``formmigrate.conditions``,
which every source shares. A platform that hands you structured JSON logic
should build the tree with those constructors instead of formatting a string
here to parse back out.
"""

from __future__ import annotations

import re

from ... import conditions as shared

# Re-exported so a caller that only imports this module can still catch the
# error type without reaching across to the shared module.
ConditionSyntaxError = shared.ConditionSyntaxError

# One token: a backtick-quoted #reference, a parenthesis, or a bare word.
_TOKEN_RE = re.compile(r"`\s*#?([^`]+?)\s*`|([()])|([A-Za-z]+)")

_OPERATORS = {"AND", "OR", "NOT"}


def tokenize(expression: str) -> list[tuple[str, str]]:
    """Split an expression into ``(kind, value)`` tokens.

    Kinds are ``ref``, ``paren``, and ``op``. Anything unrecognized raises,
    because silently dropping a token would change a rule's meaning.
    """
    tokens: list[tuple[str, str]] = []
    position = 0
    for match in _TOKEN_RE.finditer(expression):
        gap = expression[position : match.start()].strip()
        if gap:
            raise ConditionSyntaxError(f"Unexpected text {gap!r} in {expression!r}")
        position = match.end()

        reference, paren, word = match.groups()
        if reference is not None:
            tokens.append(("ref", reference.strip()))
        elif paren is not None:
            tokens.append(("paren", paren))
        else:
            upper = word.upper()
            if upper not in _OPERATORS:
                raise ConditionSyntaxError(f"Unknown operator {word!r}")
            tokens.append(("op", upper))

    trailing = expression[position:].strip()
    if trailing:
        raise ConditionSyntaxError(f"Unexpected trailing text {trailing!r}")
    return tokens


class _Parser:
    """Recursive-descent parser over the token list."""

    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.index = 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise ConditionSyntaxError("Unexpected end of expression")
        self.index += 1
        return token

    def parse_expression(self) -> dict:
        """expression := term (OR term)*"""
        operands = [self.parse_term()]
        while (token := self.peek()) and token == ("op", "OR"):
            self.take()
            operands.append(self.parse_term())
        return shared.any_of(operands)

    def parse_term(self) -> dict:
        """term := factor (AND factor)*"""
        operands = [self.parse_factor()]
        while (token := self.peek()) and token == ("op", "AND"):
            self.take()
            operands.append(self.parse_factor())
        return shared.all_of(operands)

    def parse_factor(self) -> dict:
        """factor := NOT factor | '(' expression ')' | ref"""
        kind, value = self.take()
        if (kind, value) == ("op", "NOT"):
            return shared.negate(self.parse_factor())
        if (kind, value) == ("paren", "("):
            inner = self.parse_expression()
            closing = self.take()
            if closing != ("paren", ")"):
                raise ConditionSyntaxError("Expected closing parenthesis")
            return inner
        if kind == "ref":
            return shared.ref(value)
        raise ConditionSyntaxError(f"Unexpected token {value!r}")


def parse(expression: str) -> dict:
    """Parse a ``data-condition`` expression into a shared condition tree."""
    parser = _Parser(tokenize(expression))
    tree = parser.parse_expression()
    if parser.peek() is not None:
        raise ConditionSyntaxError(f"Trailing tokens in {expression!r}")
    return tree
