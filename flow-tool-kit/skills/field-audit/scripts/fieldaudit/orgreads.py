"""The org-reading helpers this skill shares with org-catalog.

org-catalog already reads Flow Tool Kit configuration through one query list
that both the Salesforce CLI and a chat connector can run. The audit uses its
helpers rather than a second copy:

* ``ocutil``: ``val`` (reads a row whether the CLI nested it or a connector
  flattened it), ``records``, ``ran``, ``failed``, ``parse_json``, ``soql_list``;
* ``ocqueries``: ``MISSING_COLUMN`` and ``without_missing_column`` (drop a
  column an older package version does not have);
* ``catalog``: ``sf``, ``run_query`` (the CLI runner with the tooling fallback),
  ``rows_from`` (rows from whatever a connector returned), ``load``, ``save``.
  Once shared, these move to their own module, ``ocrunner``, which is used
  when present.

They are found in this skill's ``_shared/lib/orgreads/`` when the plugin ships
them there, otherwise in the org-catalog skill installed beside this one.
Set ``FTK_ORGREADS_DIR`` to point at another copy (tests do).
"""

from __future__ import annotations

import os
import pathlib
import sys

_SKILL = pathlib.Path(__file__).resolve().parents[2]
_CANDIDATES = [os.environ.get("FTK_ORGREADS_DIR") or "",
               str(_SKILL / "_shared" / "lib" / "orgreads"),
               str(_SKILL.parent / "org-catalog" / "scripts")]


def _find():
    for candidate in _CANDIDATES:
        if candidate and (pathlib.Path(candidate) / "ocutil.py").is_file():
            return candidate
    return None


FOUND = _find()
if FOUND is None:
    raise ImportError(
        "field-audit reads the org through org-catalog's helpers (ocutil.py, ocqueries.py, catalog.py), "
        "and they were not found. Install the whole Flow Tool Kit plugin, which ships the org-catalog "
        "skill beside this one, then run this again.")
if FOUND not in sys.path:
    sys.path.insert(0, FOUND)

try:  # the runner on its own, once it is shared
    import ocrunner as catalog  # noqa: E402,F401
except ImportError:  # org-catalog's command-line script, which holds it today
    import catalog  # noqa: E402,F401
import ocqueries  # noqa: E402,F401
import ocutil  # noqa: E402,F401
