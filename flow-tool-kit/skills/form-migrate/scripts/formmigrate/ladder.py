"""Place every calculation and custom script on the escalation ladder.

A legacy form's calculations and injected JavaScript are the parts that do not
migrate as configuration. Each one is rebuilt on the lowest rung that does the
job, because each rung up is harder for the org's admins to change later:

1. **Native**: Flow Tool Kit configuration. A calculation becomes a formula
   field on Form Submission, with Trigger Formula Recalculations
   (``triggerFormulaRecalculation__c``) switched on for each input that feeds it,
   so it updates live as the respondent types. Show/hide logic becomes
   conditional logic; choices become a picklist display type.
2. **Flow Section**: a screen flow inside the page section (section type
   ``flowScreen``, flow named in ``flowApiName__c``). For logic that needs org
   data (lookups, eligibility checks against records) or several steps. Built
   with the build-flow-section skill.
3. **Custom LWC**: a Lightning Web Component in the section (section type
   ``lwcSection``, component named in ``lwcComponentName__c``). For interaction
   no native control or screen flow can draw (drawing, drag and drop, a live
   widget). Built with the build-custom-lwc skill.

Section type ``formComponent`` is NOT a rung: it embeds another Form Builder form
in a section, which is how a reusable calculator built natively is shared.

This module only proposes. The reviewer confirms each item's rung; a script the
heuristics cannot read stays at "review" with the evidence that put it there.
"""

from __future__ import annotations

import re

RUNGS = {
    "native": {
        "label": "Native (formula field and Trigger Formula Recalculations)",
        "section_type": "inputSection",
        "config": ["triggerFormulaRecalculation__c"],
        "skill": "build-form-component",
    },
    "flow_section": {
        "label": "Flow Section",
        "section_type": "flowScreen",
        "config": ["flowApiName__c"],
        "skill": "build-flow-section",
    },
    "custom_lwc": {
        "label": "Custom LWC",
        "section_type": "lwcSection",
        "config": ["lwcComponentName__c"],
        "skill": "build-custom-lwc",
    },
    "review": {
        "label": "Review: read the script, then pick the lowest rung that works",
        "section_type": "",
        "config": [],
        "skill": "",
    },
}

# Arithmetic over form values, which a formula field reproduces.
_ARITHMETIC = re.compile(r"^[\w\s.+\-*/(),%<>=!&|?:'\"]+$")
# Signals that a script needs org data or a server round trip.
_SERVER = re.compile(r"\b(ajax|fetch|XMLHttpRequest|\$\.get|\$\.post|sforce|salesforce|lookup|api)\b", re.I)
# Signals of interaction a native control cannot draw.
_INTERACTIVE = re.compile(r"\b(canvas|drag|drop|signature|getContext|requestAnimationFrame|mousemove|touchmove)\b", re.I)
# Signals of show/hide or simple value setting, which native configuration covers.
_DECLARATIVE = re.compile(r"\b(show|hide|display|toggle|disabled|required|value\s*=)\b", re.I)


def _item(element: str, kind: str, rung: str, reason: str, evidence: str = "") -> dict:
    spec = RUNGS[rung]
    return {
        "element": element,
        "kind": kind,
        "rung": rung,
        "rung_label": spec["label"],
        "section_type": spec["section_type"],
        "config": list(spec["config"]),
        "skill": spec["skill"],
        "reason": reason,
        "evidence": evidence[:200],
    }


def classify_calculation(field: dict) -> dict:
    """A calculated field: native unless the formula reaches outside the form."""
    formula = field.get("calculation")
    text = formula if isinstance(formula, str) else str(formula or "")
    element = f"{field.get('id')} \"{field.get('label', '')}\""
    if isinstance(formula, dict) or _ARITHMETIC.match(text.replace("Math.", "").replace(".toFixed", "")):
        return _item(element, "calculation", "native",
                     "arithmetic over form values: a Form Submission formula field recalculated live", text)
    if _SERVER.search(text):
        return _item(element, "calculation", "flow_section",
                     "the calculation reads data outside the form", text)
    return _item(element, "calculation", "review", "formula not read with confidence", text)


def classify_script(script: dict) -> dict:
    """An injected script: interactive UI, org data, simple show/hide, or unknown."""
    body = script.get("body") or ""
    element = f"custom script {script.get('index', '?')} ({script.get('length', len(body))} characters)"
    if _INTERACTIVE.search(body):
        return _item(element, "custom_script", "custom_lwc",
                     "draws or handles interaction no native control or screen flow provides", body)
    if _SERVER.search(body):
        return _item(element, "custom_script", "flow_section",
                     "reads or writes data on a server: a screen flow can query the org", body)
    if _DECLARATIVE.search(body) and len(body) < 2000:
        return _item(element, "custom_script", "native",
                     "shows, hides or sets values: conditional logic and field settings cover it", body)
    return _item(element, "custom_script", "review", "script purpose not clear from its text", body)


def plan(document: dict) -> list[dict]:
    """Every calculation and custom script in the IR, each placed on a rung."""
    items = [classify_calculation(f) for f in document.get("fields", []) if f.get("calculation")]
    items += [classify_script(s) for s in document.get("custom_scripts", [])]
    return items


def to_markdown(items: list[dict]) -> str:
    """A table for the discovery report: element, rung, section type, skill, reason."""
    if not items:
        return "No calculations or custom scripts were found.\n"
    lines = ["| Element | Rung | Section type | Build with | Why |", "|---|---|---|---|---|"]
    for item in items:
        lines.append(
            f"| {item['element']} | {item['rung_label']} | {item['section_type'] or '-'} "
            f"| {item['skill'] or '-'} | {item['reason']} |")
    return "\n".join(lines) + "\n"
