"""Read the Flow Tool Kit project config, ``flow-tool-kit.json``, that ftk-start writes.

ftk-start asks the setup questions once per org (edition, audiences, brand kit)
and saves the answers at the project root, each org keyed by its 18-character
org Id, because an alias differs between computers. Every other skill reads the
file and never asks those questions again. This module only reads it.

    {"config_version": 1,
     "orgs": {"00D000000000001AAA": {"name": "...", "alias": "<org-alias>",
                                     "edition": "paid", "edition_source": "asked",
                                     "audiences": ["guest"], "platforms": {...}}}}

Which org entry applies, in order: the org Id given (or read from the
Salesforce CLI for an alias), then an entry whose ``alias`` matches, then the
only entry when there is just one. Anything else is ambiguous and returns none,
so the caller asks rather than guessing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

FILE_NAME = "flow-tool-kit.json"


def find(start: str | None = None) -> str | None:
    """The nearest ``flow-tool-kit.json`` at or above ``start`` (default: the working directory)."""
    here = os.path.abspath(start or os.getcwd())
    if os.path.isfile(here):
        here = os.path.dirname(here)
    while True:
        candidate = os.path.join(here, FILE_NAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def load(path: str | None) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def org_id_from_cli(alias: str | None = None) -> str | None:
    """The org Id for an alias (or the CLI's default org), or None without a CLI or connection."""
    if not shutil.which("sf"):
        return None
    args = ["sf", "org", "display", "--json"] + (["-o", alias] if alias else [])
    done = subprocess.run(args, capture_output=True, text=True)
    try:
        return (json.loads(done.stdout or "{}").get("result") or {}).get("id")
    except ValueError:
        return None


def _same_org(left: str, right: str) -> bool:
    """15- and 18-character Ids of one org agree on their first 15 characters."""
    return bool(left and right) and left[:15] == right[:15]


def org_settings(config: dict, org_id: str | None = None, alias: str | None = None) -> dict:
    """The settings ftk-start saved for one org; ``{}`` when it cannot be told which."""
    orgs = config.get("orgs") or {}
    if org_id:
        for key, entry in orgs.items():
            if _same_org(key, org_id):
                return {"org_id": key, **entry}
    if alias:
        matches = [(key, entry) for key, entry in orgs.items() if entry.get("alias") == alias]
        if len(matches) == 1:
            return {"org_id": matches[0][0], **matches[0][1]}
    if len(orgs) == 1 and not org_id:
        key, entry = next(iter(orgs.items()))
        return {"org_id": key, **entry}
    return {}


def edition(settings: dict) -> str | None:
    value = (settings.get("edition") or "").lower()
    return value if value in ("paid", "free") else None


def resolve(start: str | None = None, config_path: str | None = None, org_id: str | None = None,
            alias: str | None = None, use_cli: bool = False) -> dict:
    """Find the config and pick this org's settings.

    ``use_cli`` reads the org Id for ``alias`` (or the default org) through the
    Salesforce CLI when no ``org_id`` is given. Returns the settings plus
    ``config_path``; empty settings when there is no file or no matching org.
    """
    path = config_path or find(start)
    config = load(path)
    if use_cli and not org_id:
        org_id = org_id_from_cli(alias)
    settings = org_settings(config, org_id, alias)
    return {**settings, "config_path": path or ""} if settings else {"config_path": path or ""}
