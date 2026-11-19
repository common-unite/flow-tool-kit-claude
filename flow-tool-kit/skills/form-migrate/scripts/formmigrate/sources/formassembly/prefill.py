"""Parse a FormAssembly prefill (Salesforce Pull, event ``beforerender``) connector page.

A captured page mixes two layouts: lookups left open in edit mode (selects,
textareas, radios carrying the chosen options and Salesforce API names) and
lookups shown read-only (plain text). Both parse into the same model.
"""
from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field as dataclass_field

OUTCOME_TEXT = {
    "skip": "Skip prefilling",
    "abort": "End execution and log an error",
    "continue": "Prefill with this record",
    "pickrecentlymodified": "Pick the most recently modified record",
    "repeat": "Repeat fields (fill a repeating section)",
}
VALUE_KIND = {"unsafeparameter": "url_parameter", "formula": "formula", "mappingid": "lookup_result"}


@dataclass
class Condition:
    field_label: str
    field_api: str | None
    operator: str
    value_kind: str  # url_parameter | formula | lookup_result | text
    value: str


@dataclass
class Mapping:
    form_field_label: str
    source_kind: str  # salesforce_field | formula
    source: str


@dataclass
class PrefillLookup:
    order: str
    number: str
    sobject: str
    joiner: str
    conditions: list[Condition] = dataclass_field(default_factory=list)
    on_no_match: str = ""
    on_one_match: str = ""
    on_multiple_matches: str = ""
    repeat_section: str | None = None
    repeat_order: str | None = None
    mappings: list[Mapping] = dataclass_field(default_factory=list)


def _text(fragment: str) -> str:
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_lib.unescape(fragment)).strip()


def _selected(select_html: str) -> tuple[str, str]:
    option = re.search(r'<option[^>]*value="([^"]*)"[^>]*selected[^>]*>(.*?)</option>', select_html, re.S)
    option = option or re.search(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', select_html, re.S)
    return (option.group(1), _text(option.group(2))) if option else ("", "")


def _edit_conditions(segment: str) -> list[Condition]:
    conditions = []
    for row in re.finditer(r'<td class="leftOperandCell">(.*?)</td>\s*<td class="operatorCell">(.*?)</td>\s*<td class="rightOperandCell">(.*?)</td>', segment, re.S):
        left, operator, right = row.groups()
        api, label = _selected(left)
        type_select = re.search(r'class="predicateTypeSelect[^"]*"[^>]*>(.*?)</select>', right, re.S)
        kind = VALUE_KIND.get(_selected(type_select.group(1))[0], "text") if type_select else "text"
        textarea = re.search(r'<textarea[^>]*>(.*?)</textarea>', right, re.S)
        lookup = re.search(r'class="lookupSelect[^"]*"[^>]*>(.*?)</select>', right, re.S)
        value = html_lib.unescape(textarea.group(1)).strip() if textarea else (_selected(lookup.group(1))[1] if lookup else "")
        conditions.append(Condition(label, api or None, _selected(operator)[1], kind, value))
    return conditions


def _read_conditions(segment: str) -> list[Condition]:
    conditions = []
    for div in re.finditer(r'<div class="predicate" id="predicate-\d+">([^<]+(?:<span[^>]*>.*?</span>)?[^<]*)</div>', segment, re.S):
        text = _text(div.group(1).split('<span class="unsafeParameterWarning"')[0])
        text = re.sub(r"Caution: Make sure.*$", "", text).strip()
        parts = [part.strip() for part in re.split(r"\s{2,}|\xa0", html_lib.unescape(div.group(1).split("<span")[0])) if part.strip()]
        if len(parts) < 3:
            parts = text.split(" ", 2) if text.count(" ") >= 2 else [text, "", ""]
        label, operator, value = parts[0], parts[1], " ".join(parts[2:])
        value = re.sub(r"\s*Caution:.*$", "", value).strip()
        if value.lower().startswith("unsafe parameter"):
            kind, value = "url_parameter", value.split(":", 1)[1].strip()
        elif value.lower().startswith("formula:"):
            kind, value = "formula", value.split(":", 1)[1].strip()
        elif value.startswith("Lookup #"):
            kind = "lookup_result"
        else:
            kind = "text"
        conditions.append(Condition(label, None, operator, kind, value))
    return conditions


def _outcome(segment: str, css: str, name: str) -> str:
    block = re.search(rf'<div class="{css}">(.*?)</div>', segment, re.S)
    if not block:
        return ""
    checked = re.search(rf'name="[^"]*@{name}"[^>]*value="([^"]+)"[^>]*checked', block.group(1)) or re.search(rf'value="([^"]+)"[^>]*class="[^"]*"[^>]*checked', block.group(1))
    if checked:
        return OUTCOME_TEXT.get(checked.group(1), checked.group(1))
    labels = re.findall(r"<label>(.*?)</label>", block.group(1), re.S)
    return _text(labels[0]).rstrip(".") if len(labels) == 1 else "unclear"


def parse(page: str) -> list[PrefillLookup]:
    starts = [m.start() for m in re.finditer(r'<fieldset class="sobject"', page)]
    lookups = []
    for index, start in enumerate(starts):
        segment = page[start: starts[index + 1] if index + 1 < len(starts) else len(page)]
        title = re.search(r'<span class="sobjectSelected">\s*([\d.]+)\s*Lookup\s*<em>(\w+)</em>', segment)
        if not title:
            continue
        number = re.search(r'<span class="lookupNumber">#(\d+)</span>', segment)
        joiner = re.search(r'/@operator" class="predicateOperatorSelect[^"]*">\s*<option value="(and|or)"', segment)
        between = re.findall(r"</div>\s*(and|or)\s*<div class=\"predicate\"", segment)
        conditions = _edit_conditions(segment) or _read_conditions(segment)
        repeat = re.search(r'class="repeatLookupAssociation[^"]*"[^>]*>(.*?)</select>', segment, re.S)
        order = re.search(r'class="repeatLookupOrder[^"]*"[^>]*>(.*?)</select>', segment, re.S)
        mappings = []
        for row in re.finditer(r'<td class="sfieldCell">(.*?)</td>\s*<td class="sourceCell">(.*?)</td>', segment, re.S):
            target, source = _text(row.group(1)), _text(row.group(2))
            if source.lower().startswith("formula ="):
                mappings.append(Mapping(target, "formula", source.split("=", 1)[1].strip()))
            else:
                mappings.append(Mapping(target, "salesforce_field", re.sub(r"^a Salesforce field\s*", "", source)))
        lookups.append(PrefillLookup(
            order=title.group(1).rstrip("."),
            number=number.group(1) if number else "",
            sobject=title.group(2),
            joiner=(joiner.group(1) if joiner else (between[0] if between else "and")).upper(),
            conditions=conditions,
            on_no_match=_outcome(segment, "lookupNoMatch", "onempty"),
            on_one_match=_outcome(segment, "lookupOneMatch", "onmatch"),
            on_multiple_matches=_outcome(segment, "lookupDuplicateMatch", "onduplicate"),
            repeat_section=_selected(repeat.group(1))[1] if repeat else None,
            repeat_order=_selected(order.group(1))[1] if order else None,
            mappings=mappings,
        ))
    return lookups


def parse_file(path: str) -> list[PrefillLookup]:
    with open(path, encoding="utf-8") as handle:
        return parse(handle.read())
