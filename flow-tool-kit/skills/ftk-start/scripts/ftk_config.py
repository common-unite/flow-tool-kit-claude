#!/usr/bin/env python3
"""Read and write flow-tool-kit.json, the project config every Flow Tool Kit skill reads.

    python3 ftk_config.py show
    python3 ftk_config.py missing <org-id> [--site]
    python3 ftk_config.py set-org <org-id> [--name N] [--alias A] [--edition paid|free]
                                  [--edition-source asked|assumed] [--audiences guest,portal,internal]
                                  [--brand-kit use|update|new|none] [--brand-found TEXT]
                                  [--platform outbound_funds=true] [--catalog PATH]
    python3 ftk_config.py set-design-system forms|site_blocks --url URL [--kit-version V]
    python3 ftk_config.py validate

Every command takes --config PATH (default: flow-tool-kit.json in the current folder).
Python 3 standard library only, so it runs the same in claude.ai chat and Claude Code.
Format: references/project-config.md.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

CONFIG_VERSION = 1
EDITIONS = ("paid", "free")
EDITION_SOURCES = ("asked", "assumed")
AUDIENCES = ("guest", "portal", "internal")
BRAND_CHOICES = ("use", "update", "new", "none")
DESIGN_SYSTEMS = {"forms": "FlowToolKit Forms", "site_blocks": "FlowToolKit Site Blocks"}
_ID_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"


class ConfigError(ValueError):
    """A value or file that cannot be used as written."""


def to_18(record_id: str) -> str:
    """Return the 18-character form of a 15- or 18-character Salesforce Id."""
    record_id = (record_id or "").strip()
    if len(record_id) == 18 and record_id.isalnum():
        return record_id
    if len(record_id) != 15 or not record_id.isalnum():
        raise ConfigError(f"Not a Salesforce Id: {record_id!r}")
    suffix = ""
    for start in (0, 5, 10):
        bits = sum(1 << i for i, ch in enumerate(record_id[start:start + 5]) if ch.isupper())
        suffix += _ID_CHARS[bits]
    return record_id + suffix


def today() -> str:
    return datetime.date.today().isoformat()


def empty() -> dict:
    return {"config_version": CONFIG_VERSION, "design_systems": {}, "orgs": {}}


def load(path: str) -> dict:
    if not os.path.exists(path):
        return empty()
    with open(path, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    data.setdefault("config_version", CONFIG_VERSION)
    data.setdefault("design_systems", {})
    data.setdefault("orgs", {})
    return data


def save(path: str, data: dict) -> None:
    problems = validate(data)
    if problems:
        raise ConfigError("; ".join(problems))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def validate(data: dict) -> list[str]:
    """Every problem in the file, as plain sentences. Empty when the file is usable."""
    problems = []
    for key in data.get("design_systems", {}):
        if key not in DESIGN_SYSTEMS:
            problems.append(f"Unknown design system {key!r}; use one of {', '.join(DESIGN_SYSTEMS)}")
        elif not data["design_systems"][key].get("url"):
            problems.append(f"Design system {key!r} has no url")
    for org_id, org in data.get("orgs", {}).items():
        try:
            if to_18(org_id) != org_id:
                problems.append(f"Org {org_id} must be keyed by its 18-character Id")
        except ConfigError as exc:
            problems.append(str(exc))
        if org.get("edition") not in (None, *EDITIONS):
            problems.append(f"Org {org_id}: edition must be paid or free")
        if org.get("edition_source") not in (None, *EDITION_SOURCES):
            problems.append(f"Org {org_id}: edition_source must be asked or assumed")
        bad = [a for a in org.get("audiences", []) if a not in AUDIENCES]
        if bad:
            problems.append(f"Org {org_id}: unknown audiences {bad}")
        choice = (org.get("brand_kit") or {}).get("choice")
        if choice not in (None, *BRAND_CHOICES):
            problems.append(f"Org {org_id}: brand_kit.choice must be one of {', '.join(BRAND_CHOICES)}")
    return problems


def missing(data: dict, org_id: str, site: bool = False) -> list[str]:
    """What ftk-start still has to ask or install for this org and account."""
    org = data.get("orgs", {}).get(to_18(org_id), {})
    needs = []
    if org.get("edition") is None:
        needs.append("edition")
    if not org.get("audiences"):
        needs.append("audiences")
    if not (org.get("brand_kit") or {}).get("choice"):
        needs.append("brand_kit")
    systems = data.get("design_systems", {})
    if not systems.get("forms", {}).get("url"):
        needs.append("design_systems.forms")
    if site and not systems.get("site_blocks", {}).get("url"):
        needs.append("design_systems.site_blocks")
    return needs


def set_org(data: dict, org_id: str, **values) -> dict:
    org_id = to_18(org_id)
    org = data["orgs"].setdefault(org_id, {})
    for key in ("name", "alias", "edition", "edition_source", "catalog"):
        if values.get(key) is not None:
            org[key] = values[key]
    if values.get("edition") is not None and values.get("edition_source") is None:
        org.setdefault("edition_source", "asked")
    if values.get("audiences") is not None:
        audiences = [a.strip().lower() for a in values["audiences"] if a.strip()]
        org["audiences"] = [a for a in AUDIENCES if a in audiences] + [a for a in audiences if a not in AUDIENCES]
    if values.get("brand_kit") is not None or values.get("brand_found") is not None:
        kit = org.setdefault("brand_kit", {})
        if values.get("brand_kit") is not None:
            kit["choice"] = values["brand_kit"]
        if values.get("brand_found") is not None:
            kit["found"] = values["brand_found"]
    for pair in values.get("platforms") or []:
        name, _, flag = pair.partition("=")
        org.setdefault("platforms", {})[name.strip()] = flag.strip().lower() in ("1", "true", "yes")
    org["answered_on"] = today()
    return org


def set_design_system(data: dict, key: str, url: str, kit_version: str | None = None) -> dict:
    if key not in DESIGN_SYSTEMS:
        raise ConfigError(f"Unknown design system {key!r}; use one of {', '.join(DESIGN_SYSTEMS)}")
    entry = {"title": DESIGN_SYSTEMS[key], "url": url, "installed_on": today()}
    if kit_version:
        entry["kit_version"] = kit_version
    data["design_systems"][key] = entry
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="flow-tool-kit.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("validate")
    m = sub.add_parser("missing")
    m.add_argument("org_id")
    m.add_argument("--site", action="store_true", help="the request involves a site page")
    s = sub.add_parser("set-org")
    s.add_argument("org_id")
    s.add_argument("--name")
    s.add_argument("--alias")
    s.add_argument("--edition", choices=EDITIONS)
    s.add_argument("--edition-source", choices=EDITION_SOURCES)
    s.add_argument("--audiences", help="comma list: guest, portal, internal")
    s.add_argument("--brand-kit", choices=BRAND_CHOICES)
    s.add_argument("--brand-found")
    s.add_argument("--platform", action="append", help="name=true or name=false, repeatable")
    s.add_argument("--catalog")
    d = sub.add_parser("set-design-system")
    d.add_argument("key", choices=sorted(DESIGN_SYSTEMS))
    d.add_argument("--url", required=True)
    d.add_argument("--kit-version")
    a = ap.parse_args(argv)

    try:
        data = load(a.config)
        if a.cmd == "show":
            print(json.dumps(data, indent=2, ensure_ascii=False))
        elif a.cmd == "validate":
            problems = validate(data)
            for problem in problems:
                print(problem)
            print("ok" if not problems else f"{len(problems)} problem(s)")
            return 1 if problems else 0
        elif a.cmd == "missing":
            needs = missing(data, a.org_id, a.site)
            print(json.dumps({"org": to_18(a.org_id), "missing": needs}))
        elif a.cmd == "set-org":
            org = set_org(
                data, a.org_id, name=a.name, alias=a.alias, edition=a.edition,
                edition_source=a.edition_source,
                audiences=a.audiences.split(",") if a.audiences is not None else None,
                brand_kit=a.brand_kit, brand_found=a.brand_found, platforms=a.platform, catalog=a.catalog,
            )
            save(a.config, data)
            print(json.dumps(org, indent=2, ensure_ascii=False))
        elif a.cmd == "set-design-system":
            entry = set_design_system(data, a.key, a.url, a.kit_version)
            save(a.config, data)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
