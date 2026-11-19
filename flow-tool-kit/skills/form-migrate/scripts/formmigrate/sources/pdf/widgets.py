"""Read a fillable PDF's form fields (AcroForm widgets) with pypdf, when it is installed.

pypdf is optional: nothing else in this skill needs it, and the standard
library cannot read a compressed PDF object graph. ``read`` returns None when
pypdf is missing, so a caller says so plainly instead of guessing the fields
from the printed text.

Each field comes back once, by its fully qualified name, however many widgets
draw it (a radio group is one field with one widget per choice):

    name       the field's full name (parent.child)
    label      the tooltip (/TU), which authoring tools fill with the question
               text; the name when there is none (label_source says which)
    kind       text, textarea, checkbox, radio, select, multiselect, list,
               signature or button
    required   the Required flag
    read_only  the ReadOnly flag (a calculated or prefilled box)
    choices    a drop-down or list's entries (display text), or a radio
               group's choice names, in widget order
    page       the page of its first widget
"""

from __future__ import annotations

# Field flag bits (PDF 32000-1, table 221 onward), zero-based.
_READ_ONLY = 1 << 0
_REQUIRED = 1 << 1
_MULTILINE = 1 << 12
_RADIO = 1 << 15
_PUSHBUTTON = 1 << 16
_COMBO = 1 << 17
_MULTISELECT = 1 << 21


def _pypdf():
    try:
        import pypdf  # type: ignore
    except ImportError:
        return None
    return pypdf


def available() -> bool:
    """Whether pypdf is installed here."""
    return _pypdf() is not None


def _inherited(field, key):
    """A field attribute, taken from the nearest ancestor that has it."""
    node = field
    for _ in range(32):
        if node is None:
            return None
        if key in node:
            return node[key]
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return None


def _full_name(field) -> str:
    parts = []
    node = field
    for _ in range(32):
        if node is None:
            break
        if "/T" in node:
            parts.append(str(node["/T"]))
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def _on_states(widget) -> list[str]:
    appearance = widget.get("/AP")
    appearance = appearance.get_object() if appearance is not None else {}
    normal = appearance.get("/N") if appearance else None
    normal = normal.get_object() if normal is not None else {}
    keys = normal.keys() if hasattr(normal, "keys") else []
    return [str(key).lstrip("/") for key in keys if str(key) != "/Off"]


def _option_labels(options) -> list[str]:
    labels = []
    for option in (options.get_object() if options is not None else []) or []:
        option = option.get_object() if hasattr(option, "get_object") else option
        if isinstance(option, list):
            labels.append(str(option[-1]))
        else:
            labels.append(str(option))
    return labels


def _has_script(node) -> bool:
    for key in ("/AA", "/A"):
        action = node.get(key)
        if action is None:
            continue
        text = str(action.get_object())
        if "/JavaScript" in text or "/JS" in text:
            return True
    return False


def read(path: str) -> dict | None:
    """``{"pages": n, "fields": [...], "scripts": n}``, or None when pypdf is not installed.

    ``scripts`` counts the JavaScript actions on fields plus document-level
    scripts: show-and-hide rules and calculations in a fillable PDF live there,
    and are not read.
    """
    pypdf = _pypdf()
    if pypdf is None:
        return None
    reader = pypdf.PdfReader(path)
    fields: dict[str, dict] = {}
    scripts = 0
    for number, page in enumerate(reader.pages, 1):
        for annotation in page.get("/Annots") or []:
            widget = annotation.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            # A widget is its own field when it carries a name; otherwise its parent is the field.
            field = widget if "/T" in widget else (widget["/Parent"].get_object() if "/Parent" in widget else widget)
            name = _full_name(field)
            if not name:
                continue
            scripts += _has_script(widget) or (field is not widget and _has_script(field))
            kind_name = str(_inherited(field, "/FT") or "")
            flags = int(_inherited(field, "/Ff") or 0)
            entry = fields.get(name)
            if entry is None:
                tooltip = str(field.get("/TU") or "").strip()
                entry = {
                    "name": name,
                    "label": tooltip or name,
                    "label_source": "tooltip" if tooltip else "name",
                    "kind": _kind(kind_name, flags),
                    "required": bool(flags & _REQUIRED),
                    "read_only": bool(flags & _READ_ONLY),
                    "choices": [],
                    "page": number,
                }
                if kind_name == "/Ch":
                    entry["choices"] = _option_labels(_inherited(field, "/Opt"))
                fields[name] = entry
            if entry["kind"] == "radio":
                for state in _on_states(widget):
                    if state not in entry["choices"]:
                        entry["choices"].append(state)
    root = reader.trailer["/Root"].get_object()
    names = root.get("/Names")
    names = names.get_object() if names is not None else {}
    if names and "/JavaScript" in names:
        scripts += 1
    return {"pages": len(reader.pages), "fields": list(fields.values()), "scripts": scripts}


def _kind(field_type: str, flags: int) -> str:
    if field_type == "/Tx":
        return "textarea" if flags & _MULTILINE else "text"
    if field_type == "/Btn":
        if flags & _PUSHBUTTON:
            return "button"
        return "radio" if flags & _RADIO else "checkbox"
    if field_type == "/Ch":
        if flags & _COMBO:
            return "select"
        return "multiselect" if flags & _MULTISELECT else "list"
    if field_type == "/Sig":
        return "signature"
    return field_type.lstrip("/").lower() or "unknown"
