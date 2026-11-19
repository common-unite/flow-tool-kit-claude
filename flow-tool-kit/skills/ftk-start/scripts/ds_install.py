#!/usr/bin/env python3
"""Get the full Flow Tool Kit design-system kits, check them, and prepare one for publishing to a Design System artifact.

    python3 ds_install.py status [--config flow-tool-kit.json]
    python3 ds_install.py fetch --kit ftk-forms [--dest DIR]          Claude Code: download the release zip
    python3 ds_install.py unpack --zip <file.zip> [--dest DIR]         chat (an attached zip) or any zip on disk
    python3 ds_install.py prepare --kit ftk-forms --out <dir> [--surface code|chat]
    python3 ds_install.py prepare --kit site-blocks --out <dir> --forms-url <FlowToolKit Forms link>
    python3 ds_install.py prepare --kit ftk-forms --out <dir> --from-artifact <link>   Claude Code, optional

The plugin ships only a slim kit (_shared/design-systems/: the READMEs, tokens, the Site Blocks schema and column
limits, and kits.json). The full kits (bundles, libraries, photos) are release assets, one zip per kit, named
flow-tool-kit-<plugin version>-<kit>.zip. kits.json names the release, each kit's version and the sha256 of every
file in its zip.

fetch downloads the zip for this plugin's own version: with `gh release download` when the GitHub CLI is signed in
(the kit repository, common-unite/flow-tool-kit-claude, may be private), else from the release's public URL. unpack (and fetch after it) refuses a zip whose
kit version or any file's checksum differs from kits.json, then puts the kit at <dest>/<kit>/ (default
$FTK_DESIGN_SYSTEMS_DIR, else ~/.flow-tool-kit/design-systems), where form-design and design-to-blocks look for it.
status compares what is unpacked, and the kit_version saved in flow-tool-kit.json for each installed design system,
with the versions this plugin expects.

prepare copies the kit's files into <dir>/project/ (Site Blocks also takes the libraries and package photos it
shares with Forms when they sit in a Forms kit beside it; a release zip already carries them), fills in the link to
the person's FlowToolKit Forms system where Site Blocks needs it, stamps the index (project/design-system.json) with
the time of this install, and writes <dir>/install-plan.json: the files to send, in batches the Artifact tool
accepts (255 paths a call from Claude Code, 16 from chat), each batch under 15 MiB, with the index alone in the last
call, and the kit_version to save in flow-tool-kit.json.

--from-artifact (Claude Code only, off unless kits.json's public_artifacts or the option names a link): the plan
copies every file server side from a published design system artifact ({"artifact", "path"} entries) instead of
sending local files, so no download is needed. Only the index is written here, from the slim kit. A Site Blocks copy
made this way keeps that artifact's own link to its Forms system.

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
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SLIM = os.path.normpath(os.path.join(HERE, "..", "_shared", "design-systems"))
KITS_JSON = os.path.join(SLIM, "kits.json")
DEFAULT_KITS = os.path.expanduser(os.environ.get("FTK_DESIGN_SYSTEMS_DIR") or "~/.flow-tool-kit/design-systems")
STAMP = "kit-version.json"
CONFIG_KEYS = {"ftk-forms": "forms", "site-blocks": "site_blocks"}
KITS = {"ftk-forms": "FlowToolKit Forms", "site-blocks": "FlowToolKit Site Blocks"}
SHARED_FROM_FORMS = ("components/lib", "assets")  # identical in both kits, shipped once in Forms
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


def _copy_tree(src: str, dst: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for name in filenames:
            if name.startswith("."):
                continue
            source = os.path.join(dirpath, name)
            target = os.path.join(dst, os.path.relpath(source, src))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, target)


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


def load_meta(path: str = KITS_JSON) -> dict:
    """kits.json from the slim kit: the release, each kit's version and every file's sha256."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read the slim kit's kits.json at {path}: {exc}")


def read_stamp(kit_dir: str) -> dict | None:
    try:
        with open(os.path.join(kit_dir, STAMP), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _member_problems(names: list[str], read, kit: str, expected: dict) -> list[str]:
    """Every file named in kits.json is present with its sha256, and nothing else is (the stamp aside)."""
    have = {}
    for name in names:
        rel = name[len(kit) + 1:]
        if rel and rel != STAMP:
            have[rel] = hashlib.sha256(read(name)).hexdigest()
    problems = [f"{rel} is missing" for rel in sorted(set(expected) - set(have))]
    problems += [f"{rel} is not part of the kit" for rel in sorted(set(have) - set(expected))]
    problems += [f"{rel} differs from its checksum" for rel in sorted(set(have) & set(expected))
                 if have[rel] != expected[rel]]
    return problems


def unpack(zip_path: str, dest: str = DEFAULT_KITS, meta: dict | None = None) -> dict:
    """Check a release zip against kits.json and put its kit at <dest>/<kit>/, replacing an older copy."""
    meta = meta or load_meta()
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise InstallError(f"{zip_path} is not a readable zip: {exc}")
    try:
        return _unpack_archive(archive, zip_path, dest, meta)
    except (zlib.error, zipfile.BadZipFile, EOFError, NotImplementedError) as exc:
        # damage inside a member's compressed data (or a CRC mismatch) surfaces while reading it
        raise InstallError(f"{os.path.basename(zip_path)} is damaged and cannot be read ({exc}). Nothing was installed. "
                           "Download the zip again from the release and retry (attach it again in chat).")


def _unpack_archive(archive: zipfile.ZipFile, zip_path: str, dest: str, meta: dict) -> dict:
    with archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) != 1 or next(iter(tops)) not in KITS:
            raise InstallError(f"{os.path.basename(zip_path)} is not a Flow Tool Kit design-system zip "
                               f"(expected one folder named {' or '.join(KITS)})")
        kit = next(iter(tops))
        for name in names:
            parts = name.split("/")
            if name.startswith("/") or ".." in parts or "\\" in name:
                raise InstallError(f"{os.path.basename(zip_path)} holds an unsafe path: {name}")
        try:
            stamp = json.loads(archive.read(f"{kit}/{STAMP}"))
        except (KeyError, ValueError):
            raise InstallError(f"{os.path.basename(zip_path)} has no {kit}/{STAMP}: not a release zip")
        expected = meta["kits"][kit]
        if stamp.get("version") != expected["version"]:
            raise InstallError(f"{os.path.basename(zip_path)} holds {expected['title']} {stamp.get('version')}; this "
                               f"plugin expects {expected['version']}: use {expected['asset']}")
        problems = _member_problems(names, archive.read, kit, expected["sha256"])
        if problems:
            raise InstallError(f"{os.path.basename(zip_path)} fails its checksum check: " + "; ".join(problems[:5])
                               + (f" and {len(problems) - 5} more" if len(problems) > 5 else ""))
        os.makedirs(dest, exist_ok=True)
        staging = tempfile.mkdtemp(prefix=f".{kit}-", dir=dest)
        try:
            for name in names:
                target = os.path.join(staging, *name.split("/"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as handle:
                    handle.write(archive.read(name))
            final = os.path.join(dest, kit)
            if os.path.exists(final):
                shutil.rmtree(final)
            os.replace(os.path.join(staging, kit), final)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return {"kit": kit, "title": expected["title"], "version": stamp["version"], "path": final,
            "files": expected["files"]}


def _gh_ready(run=subprocess.run) -> bool:
    if not shutil.which("gh"):
        return False
    try:
        return run(["gh", "auth", "status"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def fetch(kit: str, dest: str = DEFAULT_KITS, meta: dict | None = None, run=subprocess.run,
          urlopen=urllib.request.urlopen) -> dict:
    """Download this plugin version's release zip for one kit (gh when signed in, else the public URL), then unpack it."""
    if kit not in KITS:
        raise InstallError(f"Unknown kit {kit!r}; use one of {', '.join(KITS)}")
    meta = meta or load_meta()
    entry, tag, repo = meta["kits"][kit], meta["release_tag"], meta["repository"]
    url = meta["asset_url"].format(repository=repo, tag=tag, asset=entry["asset"])
    with tempfile.TemporaryDirectory() as tmp:
        path, tried = os.path.join(tmp, entry["asset"]), []
        if _gh_ready(run):
            done = run(["gh", "release", "download", tag, "--repo", repo, "--pattern", entry["asset"], "--dir", tmp],
                       capture_output=True, text=True, timeout=600)
            if done.returncode == 0 and os.path.isfile(path):
                return dict(unpack(path, dest, meta), source="gh release download")
            tried.append("gh release download: " + (done.stderr or done.stdout or "failed").strip().splitlines()[-1])
        try:
            with urlopen(url, timeout=120) as response, open(path, "wb") as handle:
                shutil.copyfileobj(response, handle)
            return dict(unpack(path, dest, meta), source=url)
        except InstallError:
            raise
        except Exception as exc:  # network refused, 404 on a private release, proxy
            tried.append(f"{url}: {exc}")
    raise InstallError(f"Could not download {entry['asset']} ({'; '.join(tried)}). Nothing was installed. In Claude Code, "
                       f"sign in with `gh auth login` (the releases of {repo} may still be private) and run fetch again. "
                       f"Otherwise download the zip from release {tag} of {repo} and run `unpack --zip <file>` "
                       "(Claude Code), or attach the zip to the chat and unpack it there.")


def status(kits_dir: str = DEFAULT_KITS, config: str | None = None, meta: dict | None = None) -> list[dict]:
    """One row per kit: the version this plugin expects, the unpacked kit's, and the installed design system's."""
    meta = meta or load_meta()
    systems = {}
    if config and os.path.isfile(config):
        with open(config, encoding="utf-8") as handle:
            systems = (json.load(handle).get("design_systems") or {})
    rows = []
    for kit, entry in meta["kits"].items():
        stamp = read_stamp(os.path.join(kits_dir, kit)) or {}
        installed = systems.get(CONFIG_KEYS[kit]) or {}
        row = {"kit": kit, "expects": entry["version"], "unpacked": stamp.get("version"),
               "unpacked_at": os.path.join(kits_dir, kit) if stamp else None,
               "installed": installed.get("kit_version") if installed.get("url") else None,
               "installed_url": installed.get("url")}
        row["full_kit"] = ("ok" if row["unpacked"] == row["expects"] else
                           "missing: fetch it (Claude Code) or attach " + entry["asset"] + " (chat)" if not stamp else
                           f"old ({row['unpacked']}): fetch or attach " + entry["asset"])
        row["design_system"] = ("not installed" if not row["installed_url"] else
                                "ok" if row["installed"] == row["expects"] else
                                f"installed {row['installed'] or 'unknown version'}, plugin expects {row['expects']}: "
                                "offer to reinstall")
        rows.append(row)
    return rows


def _index_and_paths(kit: str, out: str, meta: dict) -> tuple[dict, list[str]]:
    """For a server-side copy: the index from the slim kit (written locally) and every other project file's path."""
    entry = meta["kits"][kit]
    index_src = os.path.join(SLIM, kit, INDEX)
    project = os.path.join(out, "project")
    if os.path.exists(project):
        raise InstallError(f"{project} already exists; use an empty folder")
    os.makedirs(project)
    with open(index_src, encoding="utf-8") as handle:
        index = json.load(handle)
    paths = sorted(p for p in entry["sha256"] if p.startswith("project/") and p != INDEX)
    return index, paths


def prepare(kit: str, out: str, kits_dir: str = DEFAULT_KITS, surface: str = "code",
            forms_url: str | None = None, title: str | None = None, from_artifact: str | None = None,
            meta: dict | None = None) -> dict:
    if kit not in KITS:
        raise InstallError(f"Unknown kit {kit!r}; use one of {', '.join(KITS)}")
    if surface not in BATCH:
        raise InstallError("surface must be code or chat")
    if from_artifact:
        if surface != "code":
            raise InstallError("--from-artifact needs Claude Code: chat cannot copy files between artifacts")
        meta = meta or load_meta()
        index, paths = _index_and_paths(kit, out, meta)
        calls = [paths[i:i + BATCH["code"]] for i in range(0, len(paths), BATCH["code"])]
        return _finish(kit, out, index, title, surface, [], {
            "kit_version": meta["kits"][kit]["version"],
            "copy_from": from_artifact,
            "files": len(paths) + 1,
            "bytes": meta["kits"][kit]["bytes"],
            # each batch is a `files` map for one publish: published path -> the same path in the source artifact
            "batches": [{p: {"artifact": from_artifact, "path": p} for p in call} for call in calls],
        })
    kit_dir = os.path.join(kits_dir, kit, "project")
    forms_dir = os.path.join(kits_dir, "ftk-forms", "project")
    if not os.path.isdir(kit_dir):
        raise InstallError(f"Kit files not found at {kit_dir}: get the full kit first (`fetch --kit {kit}` in Claude "
                           "Code, or `unpack --zip <attached zip>` in chat)")
    stamp = read_stamp(os.path.join(kits_dir, kit))
    kit_version = stamp.get("version") if stamp else None
    if stamp and os.path.isfile(KITS_JSON):
        wanted = load_meta()["kits"][kit]["version"]
        if kit_version != wanted:
            raise InstallError(f"The kit at {os.path.join(kits_dir, kit)} is version {kit_version}; this plugin expects "
                               f"{wanted}. Fetch or attach the matching zip first")
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
    s.add_argument("--kits-dir", default=DEFAULT_KITS)
    f = sub.add_parser("fetch")
    f.add_argument("--kit", required=True, choices=sorted(KITS))
    f.add_argument("--dest", default=DEFAULT_KITS)
    u = sub.add_parser("unpack")
    u.add_argument("--zip", required=True)
    u.add_argument("--dest", default=DEFAULT_KITS)
    p = sub.add_parser("prepare")
    p.add_argument("--kit", required=True, choices=sorted(KITS))
    p.add_argument("--out", required=True, help="an empty folder; chat: the system's own folder")
    p.add_argument("--surface", default="code", choices=sorted(BATCH))
    p.add_argument("--forms-url", help="the person's FlowToolKit Forms link (Site Blocks needs it)")
    p.add_argument("--title")
    p.add_argument("--kits-dir", default=DEFAULT_KITS)
    p.add_argument("--from-artifact", nargs="?", const="config",
                   help="Claude Code: copy server side from this design system link (bare: kits.json public_artifacts)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "status":
            for row in status(a.kits_dir, a.config):
                print(f"{row['kit']}: plugin expects {row['expects']}; full kit {row['full_kit']}; "
                      f"design system {row['design_system']}")
            return 0
        if a.cmd in ("fetch", "unpack"):
            done = fetch(a.kit, a.dest) if a.cmd == "fetch" else unpack(a.zip, a.dest)
            print(f"{done['title']} {done['version']}: {done['files']} files checked and unpacked at {done['path']}")
            return 0
        source = a.from_artifact
        if source == "config":
            source = (load_meta().get("public_artifacts") or {}).get(a.kit)
            if not source:
                raise InstallError(f"kits.json names no public artifact for {a.kit}; fetch or attach the zip instead")
        plan = prepare(a.kit, a.out, a.kits_dir, a.surface, a.forms_url, a.title, from_artifact=source)
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{plan['title']}: {plan['files']} files, {plan['bytes'] // 1024} KB, "
          f"{len(plan['batches'])} call(s) then the index, kit {plan.get('kit_version') or 'unstamped'}. "
          f"Plan: {os.path.join(a.out, 'install-plan.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
