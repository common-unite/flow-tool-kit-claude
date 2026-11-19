"""Small helpers shared by the org-catalog scripts. Python 3 standard library only.

Rows can come from the Salesforce CLI (nested relationship objects with an "attributes" key) or from a Salesforce
connector in chat (sometimes flattened to dotted keys, sometimes with different key case). val() reads both.
"""
from __future__ import annotations

import html
import json
import re

NS = "FlowToolKit__"

# Flow Tool Kit objects a plan may name without the package prefix (plan.json writes Form_Submission__c)
FTK_OBJECTS = {"Form_Submission__c", "Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c",
               "Form_Component__c", "Form_Submission_Stage__c", "Form_Submission_Answer__c"}
SUBMISSION = NS + "Form_Submission__c"


def ns(text):
    """The '*__' placeholder that component JSON uses for the package prefix, written out."""
    return text.replace("*__", NS) if isinstance(text, str) else text


def bare(name):
    """A name without the package prefix (or its '*__' placeholder)."""
    return ns(name or "")[len(NS):] if ns(name or "").startswith(NS) else (name or "")


def canonical_object(name):
    """Full object API name: Form_Submission__c and *__Form_Submission__c both become FlowToolKit__Form_Submission__c."""
    name = ns(name or "").strip()
    return NS + name if name in FTK_OBJECTS else name


def _same(key, wanted):
    return key.lower() == wanted.lower() or bare(key).lower() == bare(wanted).lower()


def val(row, path, default=None):
    """Read 'A.B.C' from a row, nested or flattened, ignoring case and the package prefix on each segment."""
    if row is None:
        return default
    if isinstance(row, dict):
        for key, value in row.items():
            if _same(key, path):
                return value
    head, _, rest = path.partition(".")
    if not rest or not isinstance(row, dict):
        return default
    for key, value in row.items():
        if _same(key, head) and isinstance(value, dict):
            return val(value, rest, default)
    return default


def records(raw, key):
    """The rows a query returned, or [] when it was not run or failed."""
    entry = (raw.get("queries") or {}).get(key) or {}
    rows = entry.get("records")
    return rows if isinstance(rows, list) else []


def ran(raw, key):
    entry = (raw.get("queries") or {}).get(key)
    return isinstance(entry, dict) and ("records" in entry or "error" in entry)


def failed(raw, key):
    entry = (raw.get("queries") or {}).get(key)
    return isinstance(entry, dict) and "error" in entry


def parse_json(text):
    """A dict from a JSON string, {} when blank or unreadable."""
    if isinstance(text, dict):
        return text
    if not text or not isinstance(text, str):
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def plain(text):
    """Visible text of a rich-text value: tags removed, entities decoded, spaces collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def norm_label(text):
    """A label as compared: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", " ", plain(text).lower()).strip()


def soql_list(values):
    """A SOQL IN list of quoted strings."""
    return ", ".join("'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'" for v in values)
