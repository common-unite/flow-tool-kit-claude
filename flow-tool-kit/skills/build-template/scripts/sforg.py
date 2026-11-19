"""The org, through the Salesforce CLI (`sf`). Every build-template script talks to Salesforce only through this class.

    org = Org("<org-alias>")          # or Org(None) for the CLI's default org
    org.query("SELECT Id FROM Organization")

claude.ai chat has no `sf` CLI: there the build runs as a dry run that writes the records, and Claude saves them with the
Salesforce connector (references/chat-build.md). Python 3 standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile


class BuildError(RuntimeError):
    """A problem the person must fix; the message says what and how."""


def _target(alias: str | None) -> list[str]:
    return ["-o", alias] if alias else []


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["sf", *args], capture_output=True, text=True)
    except FileNotFoundError:
        raise BuildError("The Salesforce CLI (sf) is not installed here. In claude.ai chat, run the build with --dry-run "
                         "and save the records with the Salesforce connector (references/chat-build.md).")


def _sf(args: list[str]) -> dict:
    proc = _run([*args, "--json"])
    try:
        payload = json.loads(proc.stdout or "{}")
    except ValueError:
        raise BuildError(f"sf returned non-JSON: {proc.stdout[:300]} {proc.stderr[:300]}")
    if payload.get("status") not in (0, None) or ("result" not in payload and "status" in payload):
        raise BuildError(f"sf {' '.join(args[:3])} failed: {payload.get('message') or payload}")
    return payload.get("result", payload)


class Org:
    def __init__(self, alias: str | None):
        self.alias = alias
        info = _sf(["org", "display", *_target(alias)])
        self.version = "v" + str(info.get("apiVersion") or "62.0")
        self._describes: dict = {}

    def query(self, soql: str) -> list[dict]:
        return _sf(["data", "query", *_target(self.alias), "-q", soql]).get("records", [])

    def tooling_query(self, soql: str) -> list[dict]:
        return _sf(["data", "query", *_target(self.alias), "--use-tooling-api", "-q", soql]).get("records", [])

    def rest(self, method: str, path: str, body=None) -> object:
        args = ["api", "request", "rest", f"/services/data/{self.version}{path}", *_target(self.alias), "--method", method]
        if body is not None:
            args += ["--body", json.dumps(body)]
        proc = _run(args)
        out = (proc.stdout or "").strip()
        try:
            result = json.loads(out) if out else None
        except ValueError:
            raise BuildError(f"{method} {path}: {out[:400]} {proc.stderr[:300]}")
        if proc.returncode != 0:
            raise BuildError(f"{method} {path}: {out[:400]}")
        return result

    def describe(self, sobject: str) -> list[dict]:
        """The object's field describes the running user can see (empty when the object is not there)."""
        if sobject not in self._describes:
            try:
                self._describes[sobject] = self.rest("GET", f"/sobjects/{sobject}/describe")["fields"]
            except BuildError:
                self._describes[sobject] = []
        return self._describes[sobject]

    def fields(self, sobject: str) -> set[str]:
        """Every field API name the running user can see on an object (empty set when the object is not there)."""
        return {f["name"] for f in self.describe(sobject)}

    def picklist_values(self, sobject: str, field: str) -> set[str] | None:
        """The active values of a picklist field, or None when the field is not there."""
        for f in self.describe(sobject):
            if f["name"] == field:
                return {v["value"] for v in f.get("picklistValues") or [] if v.get("active", True)}
        return None

    def apex(self, code: str) -> dict:
        """Run anonymous Apex; raise BuildError with the compile problem or the exception message (the package's own text)."""
        with tempfile.NamedTemporaryFile("w", suffix=".apex", prefix="buildtemplate-", delete=False) as handle:
            handle.write(code)
        try:
            proc = _run(["apex", "run", "--file", handle.name, *_target(self.alias), "--json"])
        finally:
            os.unlink(handle.name)
        try:
            payload = json.loads(proc.stdout or "{}")
        except ValueError:
            raise BuildError(f"sf apex run returned non-JSON: {proc.stdout[:300]} {proc.stderr[:300]}")
        result = payload.get("result") or {}
        if result and not result.get("compiled", True):
            raise BuildError(f"Apex did not compile: {result.get('compileProblem')}")
        if not result or not result.get("success"):
            raise BuildError(result.get("exceptionMessage") or payload.get("message") or "anonymous Apex failed")
        return result

    def save(self, method: str, records: list[dict]) -> list[str]:
        """POST (create) or PATCH (update) records in chunks of 200, all or nothing per chunk."""
        ids = []
        for start in range(0, len(records), 200):
            chunk = records[start:start + 200]
            result = self.rest(method, "/composite/sobjects", {"allOrNone": True, "records": chunk})
            failed = [r for r in result or [] if not r.get("success")]
            if failed:
                # With allOrNone, every record but the bad one reports a rollback; report the real errors first.
                real = [r for r in failed if any(e.get("statusCode") != "ALL_OR_NONE_OPERATION_ROLLED_BACK" for e in r.get("errors") or [])]
                raise BuildError(f"{method} failed: {json.dumps(real or failed)[:800]}")
            ids += [r.get("id") for r in result]
        return ids

    def delete(self, ids: list[str]) -> None:
        for start in range(0, len(ids), 200):
            # The CLI rejects a DELETE without a body, hence the empty raw one.
            result = self.rest("DELETE", "/composite/sobjects?allOrNone=true&ids=" + ",".join(ids[start:start + 200]),
                               {"mode": "raw", "raw": ""})
            failed = [r for r in result or [] if not r.get("success")]
            if failed:
                raise BuildError(f"DELETE failed: {json.dumps(failed)[:800]}")


def quoted(values) -> str:
    """A SOQL IN list: 'a','b'. Single quotes in a value are escaped."""
    return ",".join("'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'" for v in values)
