"""The plan checked against the components' type definitions (the FlowToolKit Forms kit's index.d.ts) before drawing.

`load(path)` reads index.d.ts into {component: {prop: type}}; `problems(plan, base, types)` returns (errors, warnings):
a control that is not a kit component, a banner key that is not a Banner prop, and every component the drawing would
place on the canvas with a prop the component does not have or a value of the wrong type, each named by where it sits
in the plan, the component and the prop. A misspelling gets a "did you mean". Python 3 standard library only.

The reader understands the TypeScript index.d.ts uses: interfaces with extends (and Omit), type aliases, string and
number literal unions, arrays, inline object types, indexed access (DividerProps['variant']) and functions. Anything
it cannot read (React nodes, callbacks, Record) accepts any value, so an unread type never raises a false error.
"""
from __future__ import annotations

import difflib
import re

from . import boards, nodes, planrules

ANY = ("any",)
# Keys a plan's banner holds for the run and build-template that are not Banner props: image false drops the photo,
# imageAsset and logoAsset name the Asset Files, shape is build-template's older name for layout (plan-format.md, banner)
BANNER_PLAN_KEYS = {"image": ("union", [("prim", "boolean"), ("prim", "string")]), "imageAsset": ("prim", "string"),
                    "logoAsset": ("prim", "string"), "shape": ("prim", "string")}


# ---------------------------------------------------------------- reading index.d.ts
def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"(?m)//[^\n'\"]*$", "", text)


def _close(text: str, i: int) -> int:
    """The index just past the bracket that closes the one at text[i]."""
    pairs = {"{": "}", "(": ")", "[": "]", "<": ">"}
    stack = []
    quote = None
    j = i
    while j < len(text):
        c = text[j]
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c in pairs:
            stack.append(pairs[c])
        elif stack and c == stack[-1] and not (c == ">" and text[j - 1] == "="):
            stack.pop()
            if not stack:
                return j + 1
        j += 1
    return len(text)


def _split(text: str, sep: str) -> list[str]:
    """Split at sep where no bracket or quote is open."""
    parts, depth, quote, start = [], 0, None, 0
    for j, c in enumerate(text):
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c in "{([<":
            depth += 1
        elif c in "})]" or (c == ">" and text[j - 1] != "="):
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:j])
            start = j + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _members(body: str) -> dict:
    members = {}
    for part in _split(body.replace("\n", ";"), ";"):
        for item in _split(part, ","):
            m = re.match(r"^(?:readonly\s+)?([A-Za-z_$][\w$]*)\??\s*:\s*(.+)$", item, re.S)
            if m:
                members[m.group(1)] = _type(m.group(2))
    return members


def _type(text: str):
    text = text.strip()
    alternatives = _split(text, "|")
    if len(alternatives) > 1:
        return ("union", [_type(a) for a in alternatives])
    if text.startswith("(") and _close(text, 0) == len(text):
        return _type(text[1:-1])
    if "=>" in text:
        return ANY
    if re.fullmatch(r"'[^']*'|\"[^\"]*\"", text):
        return ("lit", text[1:-1])
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return ("lit", float(text))
    if text in ("true", "false"):
        return ("lit", text == "true")
    if text in ("string", "number", "boolean"):
        return ("prim", text)
    if text.endswith("[]"):
        return ("array", _type(text[:-2]))
    m = re.fullmatch(r"Array<(.+)>", text, re.S)
    if m:
        return ("array", _type(m.group(1)))
    if text.startswith("{") and _close(text, 0) == len(text):
        return ("object", _members(text[1:-1]))
    m = re.fullmatch(r"(?:Partial|Readonly)<\s*([A-Za-z_]\w*)\s*>", text)
    if m:
        return ("ref", m.group(1), True)
    m = re.fullmatch(r"([A-Za-z_]\w*)\['([^']+)'\]", text)
    if m:
        return ("index", m.group(1), m.group(2))
    if re.fullmatch(r"[A-Za-z_]\w*", text) and text not in ("any", "unknown", "object", "null", "undefined"):
        return ("ref", text, False)
    return ANY  # React.ReactNode, JSX.Element, Record<...>, template literal types: anything goes


class KitTypes:
    """The components index.d.ts declares and the props of each."""

    def __init__(self, text: str):
        text = _strip_comments(text)
        self.interfaces, self.aliases, self._extends, self.components = {}, {}, {}, {}
        for m in re.finditer(r"(?:export\s+)?interface\s+(\w+)\s*(?:extends\s+([^{]+))?\{", text):
            end = _close(text, m.end() - 1)
            self.interfaces[m.group(1)] = _members(text[m.end():end - 1])
            self._extends[m.group(1)] = _split(m.group(2) or "", ",")
        for m in re.finditer(r"(?:export\s+)?type\s+(\w+)\s*=\s*", text):
            start = m.end()
            self.aliases[m.group(1)] = _type(_split(text[start:], ";")[0])
        for m in re.finditer(r"export\s+declare\s+function\s+([A-Z]\w*)\s*\(\s*props\s*:\s*", text):
            start = m.end()
            if text[start] == "{":
                end = _close(text, start)
                self.components[m.group(1)] = _members(text[start + 1:end - 1])
            else:
                name = re.match(r"\w+", text[start:]).group(0)
                self.components[m.group(1)] = self.props_of(name)
        # FormStyle wraps the canvas in the brand: the kit exports it with its props interface but no declare line
        for name in self.interfaces:
            component = name[:-5]
            if name.endswith("Props") and component not in self.components and component[:1].isupper() and component != "FieldBase":
                self.components[component] = self.props_of(name)

    def props_of(self, name: str, seen=None) -> dict:
        seen = set() if seen is None else seen
        if name in seen or name not in self.interfaces:
            return {}
        seen.add(name)
        props = {}
        for parent in self._extends.get(name, []):
            m = re.fullmatch(r"Omit<\s*(\w+)\s*,\s*(.+)>", parent, re.S)
            if m:
                dropped = {t[1] for t in [_type(a) for a in _split(m.group(2), "|")] if t[0] == "lit"}
                props.update({k: v for k, v in self.props_of(m.group(1), seen).items() if k not in dropped})
            else:
                props.update(self.props_of(re.sub(r"<.*", "", parent), seen))
        props.update(self.interfaces[name])
        return props

    def resolve(self, spec, depth: int = 0):
        if depth > 8:
            return ANY
        if spec[0] == "ref":
            if spec[1] in self.aliases:
                return self.resolve(self.aliases[spec[1]], depth + 1)
            if spec[1] in self.interfaces:
                return ("object", self.props_of(spec[1]))
            return ANY
        if spec[0] == "index":
            return self.resolve(self.props_of(spec[1]).get(spec[2], ANY), depth + 1)
        return spec


def load(path) -> KitTypes:
    with open(path, encoding="utf-8") as fh:
        return KitTypes(fh.read())


# ---------------------------------------------------------------- checking values
def _describe(spec, types: KitTypes) -> str:
    spec = types.resolve(spec)
    kind = spec[0]
    if kind == "lit":
        value = spec[1]
        return f"{value!r}" if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else f"{value:g}"
    if kind == "prim":
        return spec[1]
    if kind == "array":
        return f"a list of {_describe(spec[1], types)}"
    if kind == "object":
        return "an object"
    if kind == "union":
        return " or ".join(dict.fromkeys(_describe(s, types) for s in spec[1]))
    return "anything"


def _literals(spec, types: KitTypes) -> list:
    spec = types.resolve(spec)
    if spec[0] == "lit":
        return [spec[1]]
    if spec[0] == "union":
        return [v for s in spec[1] for v in _literals(s, types)]
    return []


def _fits(value, spec, types: KitTypes, path: str, out: list) -> bool:
    """True when value fits spec; problems inside an object or list are added to out with their path."""
    spec = types.resolve(spec)
    kind = spec[0]
    if kind == "any" or value is None:
        return True
    if value is nodes.BRAND:
        value = "#000000"  # the canvas brand control: a colour string
    if kind == "union":
        alternatives = [types.resolve(s) for s in spec[1]]
        if not isinstance(value, (dict, list)):
            return any(_fits(value, a, types, path, []) for a in alternatives)
        containers = [a for a in alternatives if a[0] == "any" or a[0] == ("object" if isinstance(value, dict) else "array")]
        if not containers:
            return False
        return _fits(value, containers[0], types, path, out)  # one object or list shape per union in index.d.ts
    if kind == "lit":
        if isinstance(spec[1], float):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) == spec[1]
        return value == spec[1] and type(value) is type(spec[1])
    if kind == "prim":
        if spec[1] == "string":
            return isinstance(value, str)
        if spec[1] == "boolean":
            return isinstance(value, bool)
        # a number: the canvas passes a plain attribute as text, so a numeric string draws the same
        return (isinstance(value, (int, float)) and not isinstance(value, bool)) or (
            isinstance(value, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip()) is not None)
    if kind == "array":
        if not isinstance(value, list):
            return False
        for n, item in enumerate(value):
            if not _fits(item, spec[1], types, f"{path}[{n}]", out):
                out.append(f"{path}[{n}] is {_shown(item)}; it takes {_describe(spec[1], types)}")
        return True
    if kind == "object":
        if not isinstance(value, dict):
            return False
        out += prop_problems(spec[1], value, types, path)
        return True
    return True


def _shown(value) -> str:
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _suggest(name: str, options) -> str:
    close = difflib.get_close_matches(name, list(options), n=1, cutoff=0.6)
    if not close:
        close = [o for o in options if str(o).lower() == str(name).lower()]
    return f" (did you mean {close[0]}?)" if close else ""


def prop_problems(props: dict, values: dict, types: KitTypes, where: str, extra: dict | None = None) -> list[str]:
    """Each value checked against its prop; a key with no prop is reported with the closest prop name."""
    found = []
    known = {**props, **(extra or {})}
    for key, value in values.items():
        if key not in known:
            found.append(f"{where}: no prop {key!r}{_suggest(key, known)}")
            continue
        inner = []
        if not _fits(value, known[key], types, f"{where} {key}", inner):
            literal = _suggest(value, _literals(known[key], types)) if isinstance(value, str) else ""
            found.append(f"{where} {key} is {_shown(value)}; it takes {_describe(known[key], types)}{literal}")
        found += inner
    return found


def node_problems(node, types: KitTypes, where: str) -> list[str]:
    """Every design system component in a drawn tree: the component exists, and each prop and value fits."""
    found = []
    if not isinstance(node, dict) or "t" not in node:
        return found
    tag = node["t"]
    if tag.startswith("FTK."):
        name = tag[4:]
        if name not in types.components:
            found.append(f"{where}: {name} is not a component in the kit{_suggest(name, types.components)}")
        else:
            found += prop_problems(types.components[name], node["p"], types, f"{where}: {name}")
    for child in node["c"]:
        found += node_problems(child, types, where)
    return found


# ---------------------------------------------------------------- the plan
def problems(plan: dict, base, types: KitTypes) -> tuple[list[str], list[str]]:
    errors, reported = [], set()
    fields = [(p, s, f) for p, page in enumerate(planrules.pages(plan)) for s, section in enumerate(page.get("sections") or [])
              for f in section.get("fields") or []]
    for p, s, field in fields:
        if field.get("status") == "gap" or planrules.is_address_part(field):
            continue
        where = f"page {p + 1}, section {s + 1}, field {field.get('label', '')!r}"
        control = field.get("control")
        if control not in types.components:
            errors.append(f"{where}: control {control!r} is not a component in the kit{_suggest(str(control), types.components)}")
            continue
        try:
            node = boards.control_node(field)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue  # a malformed field: the design checks name it, and the drawing waits for the fix
        if node is not None:
            variant = field.get("variant")
            for problem in node_problems(node, types, where):
                reported.add(problem.split(": ", 1)[-1])
                errors.append(problem + ("; the value is the field's variant" if variant and f" is {variant!r};" in problem else ""))
    for owner, banner in (("template.banner", (plan.get("template") or {}).get("banner")), ("banner", plan.get("banner"))):
        if isinstance(banner, dict):
            errors += prop_problems(types.components.get("Banner", {}), banner, types, owner, BANNER_PLAN_KEYS)
    try:
        ctx = boards.Ctx(plan, {}, plan.get("slug") or "form", planrules.load_ir(plan, base))
        drawn = boards.form_boards(ctx) + [boards.confirmations_board([ctx])]
    except (TypeError, ValueError, KeyError, AttributeError, IndexError) as error:
        return errors, [f"the drawn components were not checked against the kit's types: the plan cannot be drawn yet ({error!r})"]
    for board in drawn:
        for problem in node_problems(board["tree"], types, board.get("title") or board["name"]):
            if problem.split(": ", 1)[-1] not in reported:
                reported.add(problem.split(": ", 1)[-1])
                errors.append(problem)
    return errors, []
