#!/usr/bin/env python3
"""The Form Labels a plan's copy uses, as custom metadata to deploy before the template is built.

    python3 formlabels.py <plan.json> --out <project-dir>

A plan's words can hold Form Label tokens, `{{$Label.Plot_Rules_Intro}}`, so one wording is kept once and translated.
The package reads them from two custom metadata types: Form Label (`Form_Label__mdt`: Value, Is Rich Text, Group, Tag),
looked up as `$Label.<its API name>`, and Form Label Translation (`Form_Label_Translation__mdt`: Form Label, Language,
Value, Is Rich Text), which wins when its Language is the respondent's. A token with no Form Label shows as nothing.

The plan defines each label it creates under `form_labels`:

    "form_labels": {"Plot_Rules_Intro": {"value": "<p>Read the plot rules.</p>", "translations": {"es": "<p>Lea las reglas.</p>"}}}

(a plain string is the value alone). This writes one Form Label file per entry and one Form Label Translation file per
language, under force-app/main/default/customMetadata. Then deploy with the Salesforce CLI from Claude Code:

    sf project deploy start --source-dir <project-dir>/force-app/main/default/customMetadata --target-org <org-alias>

Custom metadata is a deploy, so a records-mode build lists these as a follow-up instead. Standard library only.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

N = "FlowToolKit__"
TOKEN = re.compile(r"\{\{\s*\$Label\.([A-Za-z0-9_]+)\s*\}\}")
DEVELOPER_NAME = re.compile(r"^[A-Za-z](?!.*__)[A-Za-z0-9_]*(?<!_)$")
LANGUAGE = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?$")  # Salesforce language keys: es, fr_CA, zh_CN, haw
NAME_LIMIT = 40
COPY_KEYS = ("template", "banner", "pages", "components")  # where a plan keeps the words the form shows


def tokens(plan: dict) -> list[str]:
    """Every Form Label the plan's copy names, in the order it first appears."""
    found: list[str] = []

    def walk(value) -> None:
        if isinstance(value, str):
            found.extend(TOKEN.findall(value))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for key in COPY_KEYS:
        walk(plan.get(key))
    return list(dict.fromkeys(found))


def entries(plan: dict) -> dict:
    """form_labels as {name: {value, rich_text, group, tag, translations}}; a plain string is the value."""
    out = {}
    for name, entry in (plan.get("form_labels") or {}).items():
        entry = {"value": entry} if isinstance(entry, str) else dict(entry or {})
        value = str(entry.get("value") or "")
        out[name] = {"value": value, "rich_text": bool(entry.get("rich_text", value.lstrip().startswith("<"))),
                     "group": entry.get("group"), "tag": entry.get("tag"), "translations": dict(entry.get("translations") or {})}
    return out


def translation_name(label: str, language: str) -> str:
    """A translation's API name: <label>_<language>, the label cut so the whole fits 40 characters."""
    suffix = "_" + language
    return label[:NAME_LIMIT - len(suffix)].rstrip("_") + suffix


def problems(plan: dict) -> list[str]:
    """What stops the build: a label name the package cannot store, an empty value, a language key it does not know."""
    out = []
    if plan.get("form_labels") is not None and not isinstance(plan.get("form_labels"), dict):
        return ["form_labels must be an object: {label name: value or {value, translations}}"]
    for name, entry in entries(plan).items():
        where = f"form_labels.{name}"
        if len(name) > NAME_LIMIT or not DEVELOPER_NAME.match(name):
            out.append(f"{where}: a Form Label name is at most {NAME_LIMIT} letters, digits and single underscores, starting with a letter")
        if not entry["value"].strip():
            out.append(f"{where}: no value")
        for language, text in entry["translations"].items():
            if not LANGUAGE.match(str(language)):
                out.append(f"{where}: translation language {language!r} is not a Salesforce language key (es, fr_CA, zh_CN)")
            if not str(text or "").strip():
                out.append(f"{where}: the {language} translation has no value")
    return out


def wanted(plan: dict) -> dict:
    """{label: [languages]} every token and form_labels entry needs in the org."""
    defined = entries(plan)
    out = {name: sorted(defined.get(name, {}).get("translations", {})) for name in tokens(plan)}
    for name, entry in defined.items():
        out.setdefault(name, sorted(entry["translations"]))
    return out


def missing(org, plan: dict) -> tuple[dict, list[str]]:
    """(the labels and translations the org lacks, as {label: [languages]}, the tokens neither the org nor the plan defines)."""
    need = wanted(plan)
    if not need:
        return {}, []
    names = ",".join("'" + n + "'" for n in sorted(need))
    have = {r["DeveloperName"] for r in org.query(f"SELECT DeveloperName FROM {N}Form_Label__mdt WHERE DeveloperName IN ({names})")}
    have_translations = {((r.get(N + "Form_Label__r") or {}).get("DeveloperName"), r.get(N + "Language__c"))
                         for r in org.query(f"SELECT DeveloperName, {N}Language__c, {N}Form_Label__r.DeveloperName FROM "
                                            f"{N}Form_Label_Translation__mdt WHERE {N}Form_Label__r.DeveloperName IN ({names})")}
    defined = entries(plan)
    lacking, undefined = {}, []
    for name, languages in need.items():
        absent = [lang for lang in languages if (name, lang) not in have_translations]
        if name not in have and name not in defined:
            undefined.append(name)
        elif name not in have or absent:
            lacking[name] = absent if name in have else languages
    return lacking, undefined


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def record_xml(label: str, values: list[tuple[str, str, object]]) -> str:
    rows = "".join(f"    <values>\n        <field>{field}</field>\n        <value xsi:type=\"xsd:{kind}\">"
                   f"{esc(str(value).lower() if kind == 'boolean' else value)}</value>\n    </values>\n" for field, kind, value in values)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n'
            f"    <label>{esc(label[:NAME_LIMIT])}</label>\n    <protected>false</protected>\n{rows}</CustomMetadata>\n")


def write(plan: dict, out_dir: pathlib.Path) -> list[str]:
    """Write the Form Label and translation files for every form_labels entry (a deploy updates a label already there)."""
    folder = out_dir / "force-app" / "main" / "default" / "customMetadata"
    folder.mkdir(parents=True, exist_ok=True)
    form = (plan.get("template") or {}).get("Name") or "Form Template"
    written = []
    for name, entry in entries(plan).items():
        values = [(N + "Group__c", "string", entry["group"] or form), (N + "Tag__c", "string", entry["tag"] or (plan.get("intake") or {}).get("workstream") or form),
                  (N + "Value__c", "string", entry["value"]), (N + "isRichText__c", "boolean", entry["rich_text"])]
        path = folder / f"{N}Form_Label.{name}.md-meta.xml"
        path.write_text(record_xml(name, values))
        written.append(str(path))
        for language, text in sorted(entry["translations"].items()):
            developer_name = translation_name(name, language)
            values = [(N + "Form_Label__c", "string", name), (N + "Language__c", "string", language), (N + "Value__c", "string", text),
                      (N + "isRichText__c", "boolean", entry["rich_text"])]
            path = folder / f"{N}Form_Label_Translation.{developer_name}.md-meta.xml"
            path.write_text(record_xml(developer_name, values))
            written.append(str(path))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the Form Labels and translations a plan defines, to deploy before the build")
    parser.add_argument("plan")
    parser.add_argument("--out", required=True, help="the project folder; files go under force-app/main/default/customMetadata")
    args = parser.parse_args(argv)
    plan = json.loads(pathlib.Path(args.plan).read_text())
    found = problems(plan)
    undefined = [t for t in tokens(plan) if t not in entries(plan)]
    if found:
        sys.exit("formlabels: " + "\n  ".join(found))
    written = write(plan, pathlib.Path(args.out))
    print(json.dumps({"written": written, "tokens": tokens(plan),
                      "not_defined_here": undefined,
                      "deploy": f"sf project deploy start --source-dir {args.out}/force-app/main/default/customMetadata --target-org <org-alias>"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
