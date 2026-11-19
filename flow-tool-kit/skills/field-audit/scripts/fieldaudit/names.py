"""Field-name normalization.

Three encodings of the same field coexist and must fold to one canonical
(object, field) pair before any matching:

* FieldDefinition and EntityParticle DurableIds: ``Account.Type``
* bare API names: ``FlowToolKit__Email__c`` (record mirrors, mappings)
* the namespace placeholder: ``*__Email__c`` (every stored config JSON)
"""

from __future__ import annotations

import re

from . import NAMESPACE, PAGE_OBJECT, SECTION_OBJECT, STAR, TEMPLATE_OBJECT

_MERGE_RE = re.compile(r"\{\{(.*?)\}\}")
_FORMAT_PREFIXES = ("$number.", "$currency.", "$date.", "$dateShort.", "$datetime.", "$time.")
_SUFFIX_RE = re.compile(r"\.(toFixed|replaceAll)\(.*\)$")

# {{$Template.X}}, {{$Page.X}} and {{$Section.X}} read the template, page or
# section record itself; every other $ token is a label or a computed value.
_CONTEXT_PREFIXES = {"$Template.": TEMPLATE_OBJECT, "$Page.": PAGE_OBJECT, "$Section.": SECTION_OBJECT}
_COMPUTED = {"Number", "Count"}  # {{$Page.Number}} and {{$Page.Count}} are positions, not fields
# an API name starts upper case (Name, FirstName) or carries __ (Email__c, ns__Email__c)
_FIELD_SHAPED = re.compile(r"^(?:[A-Z][A-Za-z0-9_]*|[A-Za-z][A-Za-z0-9]*__[A-Za-z0-9_]+)(?:\.[A-Za-z][A-Za-z0-9_]*)*$")


def fold_star(name: str) -> str:
    """``*__X__c`` is the placeholder the renderer rewrites to the package prefix."""
    name = (name or "").strip()
    if name.startswith(STAR):
        return NAMESPACE + name[len(STAR):]
    return name


def local(name: str) -> str:
    """Namespace-free form, for comparing across namespaces."""
    return fold_star(name).replace(NAMESPACE, "")


def split_durable(value: str, default_object: str | None = None) -> tuple[str | None, str]:
    """Split ``Object.Field`` DurableIds; bare names keep the default object.

    Relationship paths (more than one dot, or a ``__r`` hop) are not DurableIds
    and come back whole, so the caller can label them as paths.
    """
    value = fold_star(value)
    if value.count(".") == 1 and "__r" not in value.split(".", 1)[0]:
        obj, field = value.split(".", 1)
        return fold_star(obj), fold_star(field)
    return default_object, value


def is_path(value: str) -> bool:
    """In a field position (after the object is known), a dotted name is a
    relationship path (``Account.Name``, ``Owner:User.Email``), never one field."""
    return "." in (value or "")


def custom_field_id(durable_id: str) -> str:
    """The 15-character custom field Id at the end of a FieldDefinition DurableId
    (``Account.00N...`` or ``01I....00N...``), or "" for a standard field."""
    tail = (durable_id or "").rsplit(".", 1)[-1]
    return tail[:15] if tail.startswith("00N") else ""


def strip_key(key: str) -> str:
    """A config JSON key without its namespace or placeholder, for matching."""
    key = key or ""
    if key.startswith(STAR):
        return key[len(STAR):]
    if key.startswith(NAMESPACE):
        return key[len(NAMESPACE):]
    return key


def merge_tokens(text: str) -> list[tuple[str | None, str]]:
    """Every field-shaped ``{{token}}`` in a string, as (object or None, field).

    ``None`` means the record the text renders against (usually the Form
    Submission). ``$Template.``, ``$Page.`` and ``$Section.`` tokens name the
    template, page or section object. Formatting prefixes and chained suffixes
    are stripped, so ``{{$currency.X__c.toFixed(2)}}`` and ``{{X__c}}`` are the
    same binding. Labels and other ``$`` values are skipped.
    """
    found = []
    for raw in _MERGE_RE.findall(text or ""):
        token = raw.strip()
        for prefix in _FORMAT_PREFIXES:
            if token.startswith(prefix):
                token = token[len(prefix):]
                break
        token = _SUFFIX_RE.sub("", token)
        obj = None
        for prefix, context_object in _CONTEXT_PREFIXES.items():
            if token.startswith(prefix):
                obj, token = context_object, token[len(prefix):]
                break
        if not token or token.startswith("$") or (obj == PAGE_OBJECT and token in _COMPUTED):
            continue
        if not _FIELD_SHAPED.match(token):
            continue  # {{label}} and other template words
        found.append((obj, token))
    return found


# Email templates merge in three syntaxes: Lightning {{{Object.Field}}}, Classic
# {!Object.Field} and Visualforce {!relatedTo.Field} (inside a formula too).
_LIGHTNING_MERGE = re.compile(r"\{\{\{\s*([^{}]+?)\s*\}\}\}")
_CLASSIC_MERGE = re.compile(r"\{!([^}]*)\}")
_DOTTED = re.compile(r"(?<![A-Za-z0-9_$.'\"])([$A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)")
# the recipient, the sender, the org and global values: never a field of an audited object
_EMAIL_CONTEXTS = {"recipient", "sender", "organization", "receiving_user", "sending_user", "user"}


def email_merge_fields(text: str, related_object: str | None = None) -> list[tuple[str, str]]:
    """Every ``Object.Field`` an email template merges, as (object, field).

    ``relatedTo.X`` (Visualforce) is a field of the template's related object.
    The recipient, sender, organization and ``$`` globals are skipped. A field
    after the object can still be a path (``Form_Template__r.Name``)."""
    found = []
    expressions = _LIGHTNING_MERGE.findall(text or "") + _CLASSIC_MERGE.findall(text or "")
    for expression in expressions:
        for dotted in _DOTTED.findall(expression):
            head, rest = dotted.split(".", 1)
            if head.startswith("$") or head.lower() in _EMAIL_CONTEXTS:
                continue
            if head == "relatedTo":
                if related_object:
                    found.append((fold_star(related_object), fold_star(rest)))
                continue
            if head[0].islower():
                continue  # a Visualforce variable, not an object
            found.append((fold_star(head), fold_star(rest)))
    return found
