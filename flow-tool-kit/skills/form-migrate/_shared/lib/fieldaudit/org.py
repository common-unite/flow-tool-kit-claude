"""Salesforce CLI helpers: run a query, describe an object, list its fields.

A small, stable module that other skills import (form-migrate's Form Template
extractor reads an existing template through ``query`` and
``describe_fields``). The audit itself reads the org through the query passes
in ``queries.py``, so the same reads can run through a connector in chat.

Two facts every caller needs:

* ``describe_fields`` lists only the fields the running user can read. Use it
  to decide what to SELECT, never to decide whether a field exists: a field
  hidden by field-level security exists but is missing from the describe.
  ``field_definitions`` (Tooling API FieldDefinition) lists every field.
* Custom metadata types reject aggregate queries, and long text fields cannot
  be filtered: filter those rows in Python.

Python 3 standard library only; needs the ``sf`` CLI and a connected org.
"""

from __future__ import annotations

import json
import subprocess


class OrgError(RuntimeError):
    pass


def _sf(args: list[str], org: str | None) -> dict:
    cmd = ["sf", *args, "--json"]
    if org:
        cmd += ["--target-org", org]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        raise OrgError("the Salesforce CLI (sf) is not installed")
    except subprocess.TimeoutExpired:
        raise OrgError(f"sf {' '.join(args[:3])} timed out")
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        raise OrgError(f"sf returned non-JSON output: {proc.stdout[:300]} {proc.stderr[:300]}")
    if payload.get("status") != 0:
        message = payload.get("message") or payload.get("name") or proc.stderr[:300]
        raise OrgError(f"sf {' '.join(args[:3])} failed: {message}")
    return payload["result"]


def query(soql: str, org: str | None = None, tooling: bool = False) -> list[dict]:
    """Every row of a SOQL query (the CLI follows the pages)."""
    args = ["data", "query", "--query", soql]
    if tooling:
        args.append("--use-tooling-api")
    return _sf(args, org).get("records", [])


def describe_fields(sobject: str, org: str | None = None) -> dict[str, dict]:
    """Field API name to describe entry, for the fields the running user can read."""
    result = _sf(["sobject", "describe", "--sobject", sobject], org)
    return {f["name"]: f for f in result.get("fields", [])}


def field_definitions(sobject: str, org: str | None = None) -> list[dict]:
    """Every field on the object, including ones hidden from the running user."""
    return query(
        "SELECT QualifiedApiName, Label, DataType, Description, DurableId, "
        "SecurityClassification, ComplianceGroup, BusinessStatus "
        f"FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{sobject}'",
        org, tooling=True)


def instance_url(org: str | None = None) -> str:
    return (_sf(["org", "display"], org).get("instanceUrl") or "").rstrip("/")
