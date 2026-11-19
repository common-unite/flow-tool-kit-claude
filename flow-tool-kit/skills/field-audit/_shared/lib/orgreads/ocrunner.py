"""The org-reading runner shared by org-catalog and field-audit.

Split out of org-catalog's ``catalog.py`` so that a skill can read the org with
only its own folder present (claude.ai chat copies only that folder):

* ``sf``: run the Salesforce CLI with ``--json``; (ok, result or error message);
* ``run_query``: one query from the query list, with the tooling fallback and the
  missing-column retry (a column an older package version lacks is dropped and
  recorded);
* ``rows_from``: the rows from whatever a chat connector returned;
* ``load`` and ``save``: JSON files.

Python 3 standard library only. ``ocqueries`` and ``ocutil`` sit beside this file.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ocqueries import MISSING_COLUMN, without_missing_column  # noqa: E402


# ---- files -----------------------------------------------------------------------------------------------------------

def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, data):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ---- the Salesforce CLI runner ---------------------------------------------------------------------------------------

def sf(args):
    """Run the sf CLI with --json; (ok, result or error message)."""
    try:
        done = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return False, "the Salesforce CLI (sf) is not installed"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    try:
        data = json.loads(done.stdout or "{}")
    except ValueError:
        return False, (done.stderr or done.stdout or "no output").strip()[:400]
    if data.get("status") not in (0, None) or done.returncode:
        return False, str(data.get("message") or data.get("name") or done.stderr)[:400]
    return True, data.get("result")


def run_query(query, org):
    """Run one query. A tooling query falls back to the data API; a column an older package lacks is dropped and the
    query rerun, and the dropped columns are recorded."""
    soql, dropped = query["soql"], []
    for _ in range(10):
        args = ["data", "query", "--query", soql, "--target-org", org]
        ok, result = sf(args + (["--use-tooling-api"] if query.get("tooling") else []))
        if not ok and query.get("tooling"):
            ok, result = sf(args)  # FieldDefinition also answers through the data API
        if ok:
            entry = {"records": (result or {}).get("records") or []}
            return dict(entry, dropped_columns=dropped) if dropped else entry
        retry = without_missing_column(soql, result)
        if retry is None:
            return dict({"error": result}, dropped_columns=dropped) if dropped else {"error": result}
        dropped.append(MISSING_COLUMN.search(str(result)).group(1))
        soql = retry
    return {"error": "too many missing columns", "dropped_columns": dropped}


# ---- the connector path (chat) ---------------------------------------------------------------------------------------

def rows_from(data):
    """Rows from whatever a connector returned: a list, {records: [...]}, or {result: {records: [...]}}."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "result", "data"):
            if key in data:
                return rows_from(data[key])
    return []
