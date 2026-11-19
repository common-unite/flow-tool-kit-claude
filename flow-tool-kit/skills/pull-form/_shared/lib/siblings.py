"""Find another skill of the same plugin, whatever its folder is called where the plugin is installed.

A skill that uses a sibling skill's files in place (never a copy) finds the sibling's folder with ``find``. The
places the plugin runs name the skill folders differently:

* Claude Code and claude.ai chat with plugins: ``<plugins folder>/<skill>/``, for example ``.../form-migrate/``;
* claude.ai chat in some organizations: ``/mnt/skills/plugins/<plugin name>:<skill>/``, for example
  ``.../flow-tool-kit:form-migrate/``, where the plugin name is whatever the plugin was uploaded as.

So a sibling is the folder in the same parent named ``<skill>`` or ``<anything>:<skill>``. When several match, the
one with this skill's own plugin prefix wins, then the plain name, then the rest in name order. An environment
variable, when the caller names one and it is set, is tried first and points straight at the folder wanted.

    import siblings
    scripts = siblings.find(SKILL_DIR, "form-migrate", subdir="scripts",
                            markers=["formassembly_api.py"], env="FORM_MIGRATE_SCRIPTS")

From a shell, in a skill folder that carries this file, it prints the sibling's folder:

    python3 _shared/lib/siblings.py build-form-component --subdir scripts

Python 3 standard library only.
"""
from __future__ import annotations

import argparse
import os
import sys


class NotFound(Exception):
    """No folder for the sibling skill: the message says where it looked and how to fix it."""


def _prefix(folder_name: str) -> str | None:
    return folder_name.rsplit(":", 1)[0] if ":" in folder_name else None


def candidates(skill_dir: str, name: str) -> list[str]:
    """The sibling folders named ``name`` or ``<anything>:name`` beside skill_dir, best first."""
    skill_dir = os.path.abspath(skill_dir)
    parent = os.path.dirname(skill_dir)
    own_prefix = _prefix(os.path.basename(skill_dir))
    try:
        entries = sorted(os.listdir(parent))
    except OSError:
        return []
    found = [e for e in entries if (e == name or e.rsplit(":", 1)[-1] == name and ":" in e)
             and os.path.isdir(os.path.join(parent, e))]

    def rank(entry: str) -> tuple:
        return (0 if own_prefix is not None and _prefix(entry) == own_prefix else 1 if entry == name else 2, entry)

    return [os.path.join(parent, e) for e in sorted(found, key=rank)]


def find(skill_dir: str, name: str, subdir: str = "", markers: list[str] | tuple = (), env: str | None = None) -> str:
    """The folder ``subdir`` of the sibling skill ``name`` that holds every one of ``markers``.

    ``env``, when set in the environment, names that folder directly and is tried first."""
    tried = []
    places = []
    if env and os.environ.get(env):
        places.append(os.environ[env])
    places += [os.path.join(c, subdir) if subdir else c for c in candidates(skill_dir, name)]
    for place in places:
        if os.path.isdir(place) and all(os.path.exists(os.path.join(place, m)) for m in markers):
            return os.path.abspath(place)
        tried.append(place)
    parent = os.path.dirname(os.path.abspath(skill_dir))
    looked = ", ".join(tried) if tried else "no folder named %s or <plugin>:%s in %s" % (name, name, parent)
    hint = " or set %s to its %s folder" % (env, subdir or "skill") if env else ""
    raise NotFound("The %s skill was not found beside this one (looked at: %s). Install the whole Flow Tool Kit "
                   "plugin, which ships %s with this skill%s." % (name, looked, name, hint))


def main(argv=None) -> int:
    """Print the sibling's folder; the skill is the one whose _shared/lib/ holds this file, unless --skill says."""
    ap = argparse.ArgumentParser(description="Print the folder of another skill of the same plugin.")
    ap.add_argument("name", help="the sibling skill, such as build-form-component")
    ap.add_argument("--subdir", default="", help="a folder inside it, such as scripts")
    ap.add_argument("--marker", action="append", default=[], help="a file or folder that must be there (repeatable)")
    ap.add_argument("--skill", help="this skill's folder (default: the skill that carries this file)")
    args = ap.parse_args(argv)
    skill = args.skill or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        print(find(skill, args.name, subdir=args.subdir, markers=args.marker))
    except NotFound as missing:
        print(missing, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
