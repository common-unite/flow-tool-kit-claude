#!/usr/bin/env python3
"""Report the design-system kits this plugin ships, and prepare one for publishing to the person's Design System artifact.

    python3 ds_install.py status [--config flow-tool-kit.json]
    python3 ds_install.py prepare --kit ftk-forms --out <dir> [--surface code|chat]
    python3 ds_install.py prepare --kit site-blocks --out <dir> --forms-url <FlowToolKit Forms link>

The kits ship inside the plugin, in the ftk-design-system skill beside this one (kits.json names each kit's version and
content checksum). Nothing is downloaded or attached. The skill is found with _shared/lib/siblings.py, as
`ftk-design-system/` or `<plugin>:ftk-design-system/`; --kits-dir or $FTK_DESIGN_SYSTEMS_DIR points at another copy.

status prints, per kit, the version this plugin ships, whether its files match kits.json, and the kit_version saved in
flow-tool-kit.json for the person's installed design system, with what to do when that one is older.

prepare copies the kit's files into <dir>/project/ (Site Blocks also takes the libraries and package photos it shares
with Forms from the Forms kit beside it), fills in the link to the person's FlowToolKit Forms system where Site Blocks
needs it, stamps the index (project/design-system.json) with the time of this install, and writes
<dir>/install-plan.json: the files to send, in batches the Artifact tool accepts (255 paths a call from Claude Code, 16
from chat), each batch under 15 MiB, with the index alone in the last call, and the kit_version to save in
flow-tool-kit.json. The skill folder may be read-only: files are copied by content, never with their permissions.

Every file, images included, is published at its path under project/: the components' previews and the Site Blocks
bundle load pictures by those relative paths.

Python 3 standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL_DIR, "_shared", "lib"))
import siblings  # noqa: E402

LIBRARY = "ftk-design-system"
KITS_ENV = "FTK_DESIGN_SYSTEMS_DIR"
CONFIG_KEYS = {"ftk-forms": "forms", "site-blocks": "site_blocks"}
KITS = {"ftk-forms": "FlowToolKit Forms", "site-blocks": "FlowToolKit Site Blocks"}
SHARED_FROM_FORMS = ("components/lib", "assets")  # Site Blocks reads these from the Forms kit beside it
FORMS_URL_PLACEHOLDER = "__FTK_FORMS_DESIGN_SYSTEM_URL__"
INDEX = "project/design-system.json"
TEXT_EXT = {".md", ".html", ".js", ".css", ".json", ".ts", ".txt"}
BATCH = {"code": 255, "chat": 16}
MAX_FILE = 15 * 1024 * 1024
MAX_CALL = 15 * 1024 * 1024


class InstallError(ValueError):
    """A kit or option that cannot be installed as given."""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kits_root(given: str | None = None, skill_dir: str = SKILL_DIR) -> str:
    """The folder holding ftk-forms/ and site-blocks/: --kits-dir, else $FTK_DESIGN_SYSTEMS_DIR, else the
    ftk-design-system skill beside this one, in any install layout."""
    if given:
        return os.path.abspath(given)
    try:
        return siblings.find(skill_dir, LIBRARY, markers=["ftk-forms/project"], env=KITS_ENV)
    except siblings.NotFound as missing:
        raise InstallError(str(missing))


def _copy_tree(src: str, dst: str) -> None:
    """Copy file contents only (copyfile, not copy2): the kit may be mounted read-only, and copied permission bits would
    make the stamped index and the filled-in Forms link unwritable."""
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for name in filenames:
            if name.startswith("."):
                continue
            source = os.path.join(dirpath, name)
            target = os.path.join(dst, os.path.relpath(source, src))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)


def _files(root: str) -> list[str]:
    found = []
    for dirpath, _dirs, filenames in os.walk(os.path.join(root, "project")):
        for name in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    return sorted(found)


def batches(paths: list[str], root: str, per_call: int) -> list[list[str]]:
    """Group paths into calls of at most per_call paths and MAX_CALL bytes."""
    out, current, size = [], [], 0
    for path in paths:
        bytes_ = os.path.getsize(os.path.join(root, path))
        if bytes_ > MAX_FILE:
            raise InstallError(f"{path} is {bytes_} bytes; a design system file must be 15 MiB or less")
        if current and (len(current) >= per_call or size + bytes_ > MAX_CALL):
            out.append(current)
            current, size = [], 0
        current.append(path)
        size += bytes_
    if current:
        out.append(current)
    return out


def load_meta(kits_dir: str) -> dict:
    """kits.json beside the kits: each kit's version and content checksum."""
    path = os.path.join(kits_dir, "kits.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read the kits' kits.json at {path}: {exc}")


def _kit_hashes(kits_dir: str, kit: str) -> dict:
    hashes = {}
    root = os.path.join(kits_dir, kit)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for name in filenames:
            if name.startswith(".") or name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            with open(full, "rb") as handle:
                hashes[os.path.relpath(full, root).replace(os.sep, "/")] = hashlib.sha256(handle.read()).hexdigest()
    return hashes


def kit_intact(kits_dir: str, kit: str, entry: dict) -> bool:
    """True when the kit's files hash to kits.json's content checksum (sha256 over sorted 'path<TAB>sha256' lines)."""
    hashes = _kit_hashes(kits_dir, kit)
    lines = "".join(f"{p}\t{hashes[p]}\n" for p in sorted(hashes))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest() == entry.get("content_sha256")


def status(kits_dir: str | None = None, config: str | None = None, meta: dict | None = None) -> list[dict]:
    """One row per kit: the version this plugin ships, whether its files are whole, and the installed design system's."""
    kits_dir = kits_root(kits_dir)
    meta = meta or load_meta(kits_dir)
    systems = {}
    if config and os.path.isfile(config):
        with open(config, encoding="utf-8") as handle:
            systems = (json.load(handle).get("design_systems") or {})
    rows = []
    for kit, entry in meta["kits"].items():
        installed = systems.get(CONFIG_KEYS[kit]) or {}
        row = {"kit": kit, "ships": entry["version"], "path": os.path.join(kits_dir, kit),
               "installed": installed.get("kit_version") if installed.get("url") else None,
               "installed_url": installed.get("url")}
        row["bundled"] = ("ok" if kit_intact(kits_dir, kit, entry) else
                          "damaged: its files differ from kits.json; reinstall or update the Flow Tool Kit plugin")
        row["design_system"] = ("not installed" if not row["installed_url"] else
                                "ok" if row["installed"] == row["ships"] else
                                f"installed {row['installed'] or 'unknown version'}, plugin ships {row['ships']}: "
                                "offer to install the new version")
        rows.append(row)
    return rows


def prepare(kit: str, out: str, kits_dir: str | None = None, surface: str = "code",
            forms_url: str | None = None, title: str | None = None, meta: dict | None = None) -> dict:
    if kit not in KITS:
        raise InstallError(f"Unknown kit {kit!r}; use one of {', '.join(KITS)}")
    if surface not in BATCH:
        raise InstallError("surface must be code or chat")
    kits_dir = kits_root(kits_dir)
    kit_dir = os.path.join(kits_dir, kit, "project")
    forms_dir = os.path.join(kits_dir, "ftk-forms", "project")
    if not os.path.isdir(kit_dir):
        raise InstallError(f"Kit files not found at {kit_dir}: install the whole Flow Tool Kit plugin, which ships them "
                           f"in its {LIBRARY} skill, or pass --kits-dir")
    if meta is None and os.path.isfile(os.path.join(kits_dir, "kits.json")):
        meta = load_meta(kits_dir)
    kit_version = ((meta or {}).get("kits") or {}).get(kit, {}).get("version")
    project = os.path.join(out, "project")
    if os.path.exists(project):
        raise InstallError(f"{project} already exists; use an empty folder")

    if kit != "ftk-forms":
        for shared in SHARED_FROM_FORMS:
            if os.path.isdir(os.path.join(forms_dir, shared)):
                _copy_tree(os.path.join(forms_dir, shared), os.path.join(project, shared))
    _copy_tree(kit_dir, project)  # a kit's own file wins over a shared one

    placeholders = []
    for path in _files(out):
        if os.path.splitext(path)[1] not in TEXT_EXT:
            continue
        full = os.path.join(out, path)
        with open(full, encoding="utf-8") as handle:
            text = handle.read()
        if FORMS_URL_PLACEHOLDER in text:
            placeholders.append(path)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(text.replace(FORMS_URL_PLACEHOLDER, forms_url or ""))
    if placeholders and not forms_url:
        raise InstallError(
            f"{kit} links to the person's FlowToolKit Forms system: install Forms first and pass --forms-url"
        )

    with open(os.path.join(out, INDEX), encoding="utf-8") as handle:
        index = json.load(handle)
    paths = [p for p in _files(out) if p != INDEX]
    return _finish(kit, out, index, title, surface, placeholders, {
        "kit_version": kit_version,
        "files": len(paths) + 1,
        "bytes": sum(os.path.getsize(os.path.join(out, p)) for p in paths + [INDEX]),
        "batches": batches(paths, out, BATCH[surface]),
    })


def _finish(kit: str, out: str, index: dict, title: str | None, surface: str, placeholders: list, extra: dict) -> dict:
    """Stamp and write the index, then write install-plan.json."""
    index_path = os.path.join(out, INDEX)
    stamp = now()
    index["createdOnFiles"] = {"v": 1, "at": stamp}
    index.pop("convertedFrom", None)
    index["title"] = title or KITS[kit]
    index["lastChange"] = {"by": "Claude", "at": stamp, "via": "Claude Code" if surface == "code" else "claude.ai chat",
                           "note": f"Installed {index['title']} from the Flow Tool Kit plugin"}
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    plan = {
        "kit": kit,
        "title": index["title"],
        "surface": surface,
        "root": os.path.abspath(out),
        **extra,
        "last_call": [INDEX],
        "forms_url_filled_in": placeholders,
    }
    with open(os.path.join(out, "install-plan.json"), "w", encoding="utf-8") as handle:
        json.dump(plan, handle, indent=2)
        handle.write("\n")
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--config", default="flow-tool-kit.json")
    s.add_argument("--kits-dir", help="the folder holding ftk-forms/ and site-blocks/ (default: the ftk-design-system skill)")
    p = sub.add_parser("prepare")
    p.add_argument("--kit", required=True, choices=sorted(KITS))
    p.add_argument("--out", required=True, help="an empty folder; chat: the system's own folder")
    p.add_argument("--surface", default="code", choices=sorted(BATCH))
    p.add_argument("--forms-url", help="the person's FlowToolKit Forms link (Site Blocks needs it)")
    p.add_argument("--title")
    p.add_argument("--kits-dir", help="the folder holding ftk-forms/ and site-blocks/ (default: the ftk-design-system skill)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "status":
            for row in status(a.kits_dir, a.config):
                print(f"{row['kit']}: plugin ships {row['ships']}; bundled kit {row['bundled']}; "
                      f"design system {row['design_system']}")
            return 0
        plan = prepare(a.kit, a.out, a.kits_dir, a.surface, a.forms_url, a.title)
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{plan['title']}: {plan['files']} files, {plan['bytes'] // 1024} KB, "
          f"{len(plan['batches'])} call(s) then the index, kit {plan.get('kit_version') or 'unstamped'}. "
          f"Plan: {os.path.join(a.out, 'install-plan.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
