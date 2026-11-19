"""A small element tree for the artboards, written out two ways from the same data.

    el("FTK.TextInput", {"label": "First name", "required": True})   a design system component (camelCase props)
    el("div", {"style": "display: flex"}, child, ...)                 a plain HTML element
    raw("<p>...</p>")                                                  markup kept as it is

`to_dc` writes Design canvas markup: each component is an <x-import component-from-global-scope="FTK.X"> with kebab-case
attributes; a value that is not a plain string (a number, a list, a boolean, text holding "{{") is bound through the
board's script (`{{v3}}`), and BRAND binds to the canvas's brand color control. `to_react` writes the same tree as JSON
for the self-contained fallback page, which mounts the components with React.
"""
from __future__ import annotations

import html
import json
import re


class _Brand:
    """The brand color, editable on the canvas (the board's `brand` property)."""

    def __repr__(self):
        return "BRAND"


BRAND = _Brand()


def el(tag: str, props: dict | None = None, *children) -> dict:
    flat = []
    for child in children:
        if child is None or child == "":
            continue
        flat.extend(child) if isinstance(child, list) else flat.append(child)
    return {"t": tag, "p": {k: v for k, v in (props or {}).items() if v is not None}, "c": flat}


def raw(markup: str) -> dict:
    return {"raw": markup}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def kebab(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name).lower()


class Vals:
    """The values a board binds by name; equal values share one name."""

    def __init__(self):
        self.values, self._keys = {}, {}

    def bind(self, value) -> str:
        if value is BRAND:
            return "brand"
        key = json.dumps(value, sort_keys=True, default=str)
        if key not in self._keys:
            name = f"v{len(self._keys) + 1}"
            self._keys[key] = name
            self.values[name] = value
        return self._keys[key]


def _brandless(value, brand: str):
    if value is BRAND:
        return brand
    if isinstance(value, dict):
        return {k: _brandless(v, brand) for k, v in value.items()}
    if isinstance(value, list):
        return [_brandless(v, brand) for v in value]
    return value


def to_dc(node, vals: Vals, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, str):
        return pad + esc(node)
    if "raw" in node:
        return pad + node["raw"]
    tag, props, children = node["t"], node["p"], node["c"]
    inner = "\n".join(to_dc(c, vals, indent + 1) for c in children)
    if tag.startswith("FTK."):
        attrs = []
        for key, value in props.items():
            if isinstance(value, str) and "{{" not in value:
                attrs.append(f'{kebab(key)}="{esc(value)}"')
            else:
                attrs.append(f'{kebab(key)}="{{{{{vals.bind(value)}}}}}"')
        open_tag = f'<x-import component-from-global-scope="{tag}"' + ("" if not attrs else " " + " ".join(attrs)) + ">"
        return pad + open_tag + (f"\n{inner}\n{pad}" if inner else "") + "</x-import>"
    attrs = "".join(f' {key}="{esc(value)}"' for key, value in props.items())
    return pad + f"<{tag}{attrs}>" + (f"\n{inner}\n{pad}" if inner else "") + f"</{tag}>"


def to_react(node, brand: str):
    """The tree as JSON for the fallback page: {"t", "p", "c"} with BRAND resolved, raw markup as {"raw"}."""
    if isinstance(node, str) or "raw" in node:
        return node
    return {"t": node["t"], "p": _brandless(node["p"], brand), "c": [to_react(c, brand) for c in node["c"]]}


def components_used(node, found: set | None = None) -> set:
    found = set() if found is None else found
    if isinstance(node, dict) and "t" in node:
        if node["t"].startswith("FTK."):
            found.add(node["t"])
        for child in node["c"]:
            components_used(child, found)
    return found


def icons_used(node, found: set | None = None) -> set:
    """Every utility: icon name in the tree, props and raw markup alike, for the fallback page's icon subset."""
    found = set() if found is None else found
    text = json.dumps(node, default=str)
    found.update(re.findall(r"utility:[a-z0-9_]+", text))
    return found
