"""Find form-migrate's FormAssembly reader and parser, so this skill never keeps a second copy.

The account capture reads each form with the same code form-migrate uses for one
form: the REST API reader (``formassembly_api.py`` and ``formmigrate.sources.formassembly.api``)
and the parsers for the form page, the alias page and the connector pages. They are
used in place, never copied, so the capture always runs form-migrate's current parser.
They are found by ``_shared/lib/siblings.py``: the folder named by the
``FORM_MIGRATE_SCRIPTS`` environment variable when it is set, else the ``scripts``
folder of the form-migrate skill of this same plugin, whether its folder is called
``form-migrate`` (Claude Code, chat with plugins) or ``<plugin name>:form-migrate``
(chat in some organizations, under ``/mnt/skills/plugins/``).

Python 3 standard library only.
"""
from __future__ import annotations

import os
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = "FORM_MIGRATE_SCRIPTS"


def scripts_dir() -> str:
    """The folder holding ``formmigrate/`` and ``formassembly_api.py``; puts it on sys.path."""
    shared = os.path.join(SKILL, "_shared", "lib")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        import siblings
    except ImportError:
        raise SystemExit("This skill's _shared/lib/siblings.py is missing: install the whole Flow Tool Kit plugin.")
    try:
        found = siblings.find(SKILL, "form-migrate", subdir="scripts", env=ENV,
                              markers=[os.path.join("formmigrate", "sources", "formassembly"), "formassembly_api.py"])
    except siblings.NotFound as missing:
        raise SystemExit("form-migrate's FormAssembly reader was not found. %s" % missing)
    if found not in sys.path:
        sys.path.insert(0, found)
    return found


scripts_dir()

import formassembly_api  # noqa: E402,F401  (form-migrate's one-form API reader)
from formmigrate import ir  # noqa: E402,F401
from formmigrate.sources.formassembly import adapter, api, connector, prefill  # noqa: E402,F401
