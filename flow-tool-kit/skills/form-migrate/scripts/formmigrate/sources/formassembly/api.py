"""Read a FormAssembly form, and the list of its connectors, through the REST API.

For when you have API access to the FormAssembly account rather than exports.
Stdlib only. The token is read from the environment and never written to disk,
printed or put in an error message.

    CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN
                                the plugin's sensitive "FormAssembly access token"
                                setting, kept in secure storage, wherever Claude Code
                                passes it to the process; read first
    FORMASSEMBLY_ACCESS_TOKEN   the fallback: the OAuth access token of a user who can
                                see the form, set in this session's environment
    FORMASSEMBLY_API_BASE       optional; default https://app.formassembly.com/api_v1/
                                (Enterprise and other plans: https://<instance>.tfaforms.net/api_v1/)

Endpoints used (FormAssembly API reference, formassembly-api on GitHub):

    forms/view/<form id>.json          the form definition
    connectors/index/<form id>.json    the form's connectors
    admin/api_v1/connectors/view/<id>  one connector's definition (admin token only)

What is trusted: the form definition gives the form; the connector list gives
which connectors exist. The connector's field mapping is NOT trusted yet: until
a live run proves the API's connector definition carries the same detail as
the connector's read-only view page (objects, matching, field mappings), the
IR's connector coverage stays ``not_captured`` and the raw responses are only
saved beside the IR for a person to read.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

TOKEN_ENV = "FORMASSEMBLY_ACCESS_TOKEN"
# The plugin.json userConfig key formassembly_access_token (sensitive) reaches a
# process as this variable; it wins over TOKEN_ENV when both are set.
SETTING_ENV = "CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN"
TOKEN_SOURCES = (SETTING_ENV, TOKEN_ENV)
BASE_ENV = "FORMASSEMBLY_API_BASE"
DEFAULT_BASE = "https://app.formassembly.com/api_v1/"

_HTML_HINT = re.compile(r"<form|tfa_\d+|class=\"wForm", re.I)


class ApiError(RuntimeError):
    """An API call failed; the message never contains the token."""


def _base() -> str:
    base = os.environ.get(BASE_ENV) or DEFAULT_BASE
    return base if base.endswith("/") else base + "/"


def _admin_base(base: str) -> str:
    parts = urllib.parse.urlsplit(base)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/admin/api_v1/", "", ""))


def token_value() -> str:
    """The access token from the plugin setting, else the environment; "" when neither is set."""
    for name in TOKEN_SOURCES:
        token = os.environ.get(name, "").strip()
        if token:
            return token
    return ""


def _token() -> str:
    token = token_value()
    if not token:
        raise ApiError(
            "No FormAssembly access token. Save it in the plugin's FormAssembly access token "
            f"setting, or set {TOKEN_ENV} in this session's environment. Never paste the "
            "token into a file or the chat.")
    return token


def get(path: str, base: str | None = None, opener=None) -> bytes:
    """GET ``base + path`` with the access token; return the body.

    ``opener`` is ``urllib.request.urlopen`` unless a test passes another.
    The token travels as the ``access_token`` query parameter, as the
    FormAssembly API reference shows.
    """
    url = (base or _base()) + path
    query = urllib.parse.urlencode({"access_token": _token()})
    request = urllib.request.Request(
        f"{url}{'&' if '?' in url else '?'}{query}",
        headers={"User-Agent": "form-migrate", "Accept": "application/json"})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        error.close()
        hint = {
            401: "the token was refused; check it is current",
            403: "this token's user cannot open it (connector definitions need an admin token)",
            404: "not found; check the form id and FORMASSEMBLY_API_BASE for your plan",
        }.get(error.code, "")
        raise ApiError(f"GET {path} returned {error.code}" + (f": {hint}" if hint else "")) from None
    except urllib.error.URLError as error:
        raise ApiError(f"GET {path} failed: {error.reason}") from None


def _json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        return None


def find_form_html(node) -> str | None:
    """The rendered form markup, if the definition carries it anywhere."""
    if isinstance(node, str):
        return node if len(node) > 200 and _HTML_HINT.search(node) else None
    if isinstance(node, dict):
        node = list(node.values())
    if isinstance(node, list):
        for item in node:
            found = find_form_html(item)
            if found:
                return found
    return None


def connectors_from_index(data) -> list[dict]:
    """``[{id, name, type, status}]`` from the connector index, whatever its wrapper."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            keys = {k.lower(): k for k in node}
            if "id" in keys and ({"name", "type", "connector", "status"} & set(keys)):
                found.append({
                    "id": str(node[keys["id"]]),
                    "name": str(node.get(keys.get("name", ""), "") or ""),
                    "type": str(node.get(keys.get("type", ""), "") or node.get(keys.get("connector", ""), "") or ""),
                    "status": str(node.get(keys.get("status", ""), "") or ""),
                })
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return found


def fetch(form_id: str, out_dir: str, read_connectors: bool = True, opener=None) -> dict:
    """Save the API responses for one form into ``out_dir``; return what was found.

    Writes ``api-form.json``, and ``form.html`` when the definition carries the
    form markup and no ``form.html`` is there yet. With ``read_connectors``,
    writes ``api-connectors.json`` and one ``api-connector-<id>.json`` per
    connector the token may open.
    """
    os.makedirs(out_dir, exist_ok=True)
    report = {"form_id": form_id, "form_html": False, "connectors": [], "notes": []}

    raw = get(f"forms/view/{form_id}.json", opener=opener)
    with open(os.path.join(out_dir, "api-form.json"), "wb") as handle:
        handle.write(raw)
    definition = _json(raw)
    markup = find_form_html(definition) if definition is not None else None
    page = os.path.join(out_dir, "form.html")
    if markup and not os.path.exists(page):
        with open(page, "w", encoding="utf-8") as handle:
            handle.write(markup)
        report["form_html"] = True
    elif not markup:
        report["notes"].append(
            "The form definition did not carry the form markup; build the IR from the "
            "public page (capture_public.py) and keep api-form.json beside it.")

    if not read_connectors:
        return report
    try:
        raw = get(f"connectors/index/{form_id}.json", opener=opener)
    except ApiError as error:
        report["notes"].append(f"Connector list not read: {error}")
        return report
    with open(os.path.join(out_dir, "api-connectors.json"), "wb") as handle:
        handle.write(raw)
    report["connectors"] = connectors_from_index(_json(raw))
    admin = _admin_base(_base())
    for connector in report["connectors"]:
        try:
            body = get(f"connectors/view/{connector['id']}.json", base=admin, opener=opener)
        except ApiError as error:
            report["notes"].append(f"Connector {connector['id']} not read: {error}")
            continue
        with open(os.path.join(out_dir, f"api-connector-{connector['id']}.json"), "wb") as handle:
            handle.write(body)
        connector["definition_saved"] = True
    return report


def annotate(document: dict, report: dict) -> dict:
    """Record what the API showed on an IR built from the form page.

    The connector list becomes a finding; the connector coverage is left
    ``not_captured`` (the mapping detail is unproven), never ``parsed``.
    """
    document["source"]["api"] = {
        "connectors": report.get("connectors", []),
        "notes": report.get("notes", []),
    }
    connectors = report.get("connectors", [])
    if connectors:
        listed = "; ".join(f"{c['name'] or c['id']} ({c['type'] or 'type unknown'}"
                           f"{', ' + c['status'] if c['status'] else ''})" for c in connectors)
        document["findings"].append({
            "source": "formassembly-api",
            "message": f"The API lists {len(connectors)} connector(s): {listed}. Their field "
                       "mappings are not read from the API yet; read each connector's read-only "
                       "view page for the mapping spec. Connector coverage stays not_captured."})
    for note in report.get("notes", []):
        document["findings"].append({"source": "formassembly-api", "message": note})
    return document
