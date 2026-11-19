#!/usr/bin/env python3
"""Brand styles and the logo, added to the org's Form Style defaults only where they are blank.

The org's Form Style defaults (the Form Builder's Global Styles tab, stored in the Form Style Defaults custom setting)
are the styles every Form Template inherits. A brand kit belongs there, so every form in the org shares it. The rule is
add-only, for each brand value:

    org value blank          the brand value is added to the org defaults
    org value the same       nothing
    org value different      the org value stays; the brand value goes on this template's Style Overrides only

Only brand values go org-wide (colors, fonts, corner radius), and only when the project config says the brand kit is
the org's own (brand kit choice use, update or new). Layout values from the house rules (text and input size,
spacing, borders) and every value of a form without a brand kit stay on the template, so building one form never
restyles the others.

The logo works the same way: the org Default Logo when it is blank, otherwise the template's Logo Override.

Writing the setting through the API was tested in a subscriber org (Flow Tool Kit 5.2, a system administrator): insert,
update and read all worked. If an org refuses the write, nothing is lost: the brand values go on the template, and
global-styles-import.json is written for the person to paste into Global Styles, Import. Import replaces every saved
org style, so that file always holds the org's current values plus the additions.

    python3 brandstyles.py merge --export <exported.json> --additions <global-styles-additions.json> --out <import.json>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from sforg import BuildError

N = "FlowToolKit__"
SETTING = N + "Form_Style_Defaults__c"
BRAND_TOKENS = ("--ftk-color-primary", "--ftk-color-primary-hover", "--ftk-color-primary-active", "--ftk-color-on-primary",
                "--ftk-font-family", "--ftk-font-family-heading", "--ftk-font-weight-heading",
                "--ftk-radius-small", "--ftk-radius-medium", "--ftk-radius-large", "--ftk-input-radius", "--ftk-button-radius")
ORG_WIDE_CHOICES = ("use", "update", "new")
LOGO = {"logo": "Default_Logo__c", "logoAlt": "Default_Logo_Alt_Text__c"}
TEMPLATE_LOGO = {"logo": "Logo_Override__c", "logoAlt": "Logo_Alt_Text_Override__c"}
IMPORT_FILE = "global-styles-import.json"
ADDITIONS_FILE = "global-styles-additions.json"


def style_field(token: str) -> str:
    """--ftk-color-primary -> FlowToolKit__Color_Primary__c (every Global Styles token follows this pattern)."""
    return N + "_".join(part.capitalize() for part in token.removeprefix("--ftk-").split("-")) + "__c"


def token_of(field: str) -> str:
    return "--ftk-" + field.removeprefix(N).removesuffix("__c").replace("_", "-").lower()


def org_wide(brand_kit_choice: str | None) -> bool:
    return (brand_kit_choice or "").lower() in ORG_WIDE_CHOICES


def split(tokens: dict, brand_kit_choice: str | None) -> tuple[dict, dict]:
    """(candidates for the org defaults, template-only values)."""
    if not org_wide(brand_kit_choice):
        return {}, dict(tokens)
    candidates = {t: v for t, v in tokens.items() if t in BRAND_TOKENS}
    return candidates, {t: v for t, v in tokens.items() if t not in BRAND_TOKENS}


def add_only(candidates: dict, current: dict, known: set) -> tuple[dict, list, dict]:
    """(fields to add org-wide, tokens already the same, tokens kept as template overrides). current is the org row."""
    to_add, same, overrides = {}, [], {}
    for token, value in candidates.items():
        field = style_field(token)
        if field not in known:
            overrides[token] = value
            continue
        existing = str(current.get(field) or "").strip()
        if not existing:
            to_add[field] = value
        elif existing.lower() == str(value).strip().lower():
            same.append(token)
        else:
            overrides[token] = value
    return to_add, same, overrides


def current_tokens(row: dict, known: set) -> dict:
    """The org row's saved styles as Global Styles JSON (token names), logo excluded."""
    logo_fields = {N + f for f in LOGO.values()}
    return {token_of(f): str(v) for f, v in sorted(row.items()) if f in known and f.endswith("__c") and f not in logo_fields and v not in (None, "")}


def merged_import(current: dict, additions: dict) -> dict:
    """Add-only: the org's values win; an addition only fills a token that is not saved."""
    out = dict(current)
    for token, value in additions.items():
        out.setdefault(token, value)
    return dict(sorted(out.items()))


def _paste_files(out_dir: pathlib.Path, additions: dict, current: dict | None) -> dict:
    """The files for a person to paste when the org refuses the write. With the org's current values known, the import
    file is complete; without them, the additions file is merged with the person's own Export by the merge command."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if current is not None:
        path = out_dir / IMPORT_FILE
        path.write_text(json.dumps(merged_import(current, additions), indent=2) + "\n")
        steps = ("Form Builder, Global Styles tab, Import: paste the file's contents, Preview import, then Save org defaults. "
                 "Import replaces every saved org style; this file already holds the org's current values plus the brand.")
    else:
        path = out_dir / ADDITIONS_FILE
        path.write_text(json.dumps(additions, indent=2) + "\n")
        steps = ("Form Builder, Global Styles tab, Export: save the JSON as exported.json. Then run brandstyles.py merge --export "
                 f"exported.json --additions {path.name} and paste {IMPORT_FILE} into Import, Preview import, Save org defaults.")
    return {"file": str(path), "steps": steps + " Set the Default Logo in the same tab's Logo group with Select Image."}


def apply(org, tokens: dict, logo: dict, brand_kit_choice: str | None, report: dict, out_dir: pathlib.Path,
          has_logo_fields: bool, logo_on_banner: bool = False) -> tuple[dict, dict]:
    """Write the add-only org styles and logo. Returns (template style overrides, template logo fields, unprefixed).
    logo_on_banner: an org without the Logo fields whose header carries the logo itself (header.py), so nothing is lost."""
    candidates, template_only = split(tokens, brand_kit_choice)
    logo = {k: v for k, v in (logo or {}).items() if v}
    styles = report.setdefault("styles", {})
    styles["org_wide"] = org_wide(brand_kit_choice)
    if not has_logo_fields and logo:
        if not logo_on_banner:
            report["warnings"].append("This org's Flow Tool Kit has no Logo fields on Form Template yet, so no logo was set. "
                                      "Upgrade Flow Tool Kit and rebuild to show the logo in the banner.")
        logo = {}
    as_template_logo = lambda keys: {TEMPLATE_LOGO[k]: logo[k] for k in keys}
    if not org_wide(brand_kit_choice):
        styles.update(template_only=sorted(template_only), note="no brand kit saved for this org: every value stays on this template")
        return template_only, as_template_logo(logo)

    known = org.fields(SETTING)
    try:
        if not known:
            raise BuildError("the setting is not visible to this user")
        org_id = org.query("SELECT Id FROM Organization")[0]["Id"]
        readable = sorted(f for f in known if f.endswith("__c"))
        rows = org.query(f"SELECT Id, {', '.join(readable)} FROM {SETTING} WHERE SetupOwnerId = '{org_id}'")
    except BuildError as error:
        additions = dict(candidates)
        styles.update(paste=_paste_files(out_dir, additions, None), reason=str(error)[:200], template_only=sorted(template_only))
        return {**template_only, **candidates}, as_template_logo(logo)
    current = rows[0] if rows else {}
    to_add, same, overrides = add_only(candidates, current, known)
    template_logo: dict = {}
    for key, value in logo.items():
        field = N + LOGO[key]
        existing = str(current.get(field) or "").strip()
        if field in known and not existing:
            to_add[field] = value
        elif field not in known or existing != value:
            template_logo[TEMPLATE_LOGO[key]] = value
    logo_fields = {N + f for f in LOGO.values()}
    added = sorted(token_of(f) for f in to_add if f not in logo_fields) + sorted(f.removeprefix(N) for f in to_add if f in logo_fields)
    if to_add:
        try:
            if current.get("Id"):
                org.rest("PATCH", f"/sobjects/{SETTING}/{current['Id']}", to_add)
            else:
                org.rest("POST", f"/sobjects/{SETTING}", {"SetupOwnerId": org_id, **to_add})
        except BuildError as error:
            # Refused: the form still shows the brand through its own overrides, and the person pastes the org part.
            additions = {token_of(f): v for f, v in to_add.items() if f not in logo_fields}
            overrides.update(additions)
            template_logo.update({TEMPLATE_LOGO[k]: to_add[N + LOGO[k]] for k in LOGO if N + LOGO[k] in to_add})
            styles.update(paste=_paste_files(out_dir, additions, current_tokens(current, known)), reason=str(error)[:200])
            added = []
    styles.update(added_org_wide=added, already_same=sorted(same), kept_org_value_template_override=sorted(overrides),
                  template_only=sorted(template_only))
    return {**template_only, **overrides}, template_logo


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge brand additions into a Global Styles export, add-only, for Import")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="the org's exported Global Styles JSON plus the additions, org values first")
    merge.add_argument("--export", required=True, help="the JSON copied from Global Styles, Export (an empty file when nothing is saved)")
    merge.add_argument("--additions", required=True, help=f"the build's {ADDITIONS_FILE}")
    merge.add_argument("--out", default=IMPORT_FILE)
    args = parser.parse_args(argv)
    text = pathlib.Path(args.export).read_text().strip()
    current = json.loads(text) if text else {}
    additions = json.loads(pathlib.Path(args.additions).read_text())
    merged = merged_import(current, additions)
    pathlib.Path(args.out).write_text(json.dumps(merged, indent=2) + "\n")
    added = sorted(set(merged) - set(current))
    print(json.dumps({"out": args.out, "added": added, "kept_org_values": sorted(set(additions) & set(current))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
