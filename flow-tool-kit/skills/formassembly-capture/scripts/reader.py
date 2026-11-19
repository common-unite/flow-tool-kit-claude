"""Find form-migrate's FormAssembly reader and parser, so this skill never keeps a second copy.

The account capture reads each form with the same code form-migrate uses for one
form: the REST API reader (``formassembly_api.py`` and ``formmigrate.sources.formassembly.api``)
and the parsers for the form page, the alias page and the connector pages. They are
found, in order, in:

1. this skill's ``_shared/lib/`` (the plugin's shared copy, once it ships there);
2. the form-migrate skill installed beside this one (``../form-migrate/scripts``);
3. the folder named by the ``FORM_MIGRATE_SCRIPTS`` environment variable.

Python 3 standard library only.
"""
from __future__ import annotations

import os
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = "FORM_MIGRATE_SCRIPTS"


def _candidates() -> list[str]:
    found = [os.path.join(SKILL, "_shared", "lib"), os.path.join(os.path.dirname(SKILL), "form-migrate", "scripts")]
    if os.environ.get(ENV):
        found.append(os.environ[ENV])
    return found


def scripts_dir() -> str:
    """The folder holding ``formmigrate/`` and ``formassembly_api.py``; puts it on sys.path."""
    for candidate in _candidates():
        if os.path.isdir(os.path.join(candidate, "formmigrate", "sources", "formassembly")) and os.path.exists(
                os.path.join(candidate, "formassembly_api.py")):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return candidate
    raise SystemExit(
        "form-migrate's FormAssembly reader was not found. Install the whole Flow Tool Kit plugin "
        f"(form-migrate sits beside this skill), or set {ENV} to form-migrate's scripts folder.")


scripts_dir()

import formassembly_api  # noqa: E402,F401  (form-migrate's one-form API reader)
from formmigrate import ir  # noqa: E402,F401
from formmigrate.sources.formassembly import adapter, api, connector, prefill  # noqa: E402,F401
