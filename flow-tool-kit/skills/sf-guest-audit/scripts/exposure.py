#!/usr/bin/env python3
"""What reached the browser: the "received but not shown" list per guest form.

Reads what a logged-out visitor's browser received while opening a form, and lists
every record field that arrived, marking which were shown on screen and which were
not, and flagging the likely sensitive ones. Python 3.9+, standard library only.

Input, either:
  - the capture written by scripts/guest_pass.cjs (Claude Code, headless), which
    also holds the text shown on each page, or
  - a HAR file saved from the browser's developer tools (chat, or any browser),
    with an optional --shown file holding the page's text (select all, copy, paste).

Commands:

  analyze INPUT [INPUT ...] [--shown FILE] [--form NAME] [--subject-id ID ...]
          [--out DIR] [--json]
      Write exposure.md and exposure.json: per form, the records and fields the
      browser received, which were shown, and a severity with the fix. Values are
      never written to the report: each is reduced to its kind and length.

  report --exposure FILE [--flows FILE] [--out DIR]
      Join the live pass (exposure.json) and the flow review (flow-review.json,
      from scripts/flow_review.py) into one report, guest-report.md: per form or
      flow, what is exposed, how serious, and the exact fix.

Exit codes: 0 no HIGH, 1 at least one HIGH, 2 usage or input error.
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import urllib.parse

SEVERITIES = ("HIGH", "MEDIUM", "LOW", "INFO")
RANK = {s: i for i, s in enumerate(SEVERITIES)}
SF_ID = re.compile(r"^[a-zA-Z0-9]{3}[a-zA-Z0-9]{12}(?:[a-zA-Z0-9]{3})?$")
ID_SHAPE = re.compile(r"^(?=.*\d)[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?$")
FIELD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
# Anti-hijacking prefixes Salesforce and other frameworks put before JSON.
SECURE_PREFIX = "/" + "*-secure-"
JSON_PREFIXES = ("while(1);", "for(;;);", ")]}'", SECURE_PREFIX)

# Key prefixes of the record kinds that hold a person.
PERSON_PREFIX = {"003": "Contact", "00Q": "Lead", "005": "User", "0PK": "Individual", "00v": "CampaignMember"}
KNOWN_PREFIX = dict(PERSON_PREFIX, **{"001": "Account", "500": "Case", "006": "Opportunity", "701": "Campaign"})
PERSON_TYPES = {"Contact", "Lead", "User", "Individual", "CampaignMember", "PersonAccount"}
PERSON_FIELDS = {"FirstName", "LastName", "PersonEmail", "Birthdate", "PersonBirthdate", "IsPersonAccount"}
STANDARD_FIELDS = {"Name", "FirstName", "LastName", "Email", "Phone", "MobilePhone", "Birthdate", "Title",
                   "OwnerId", "CreatedDate", "CreatedById", "LastModifiedDate", "LastModifiedById",
                   "AccountId", "RecordTypeId", "Description", "MailingStreet", "MailingCity",
                   "MailingPostalCode", "Status", "Subject", "Amount", "StageName", "CloseDate"}
SKIP_KEYS = {"attributes", "Id", "id", "sobjectType", "apiName"}

AUDIT_FIELDS = {"OwnerId", "CreatedById", "LastModifiedById", "CreatedDate", "LastModifiedDate",
                "SystemModstamp", "LastActivityDate", "LastViewedDate", "LastReferencedDate",
                "IsDeleted", "MasterRecordId", "LastCURequestDate", "LastCUUpdateDate"}
# (category, severity, pattern on the field name without namespace and __c). First match wins.
CATEGORIES = [
    ("secret or token", "HIGH", r"token|password|secret|session|api_?key|private_?key|resume_?link|access_?code|passcode"),
    ("government id", "HIGH", r"ssn|social_?security|tax_?id|taxpayer|(?:^|_)itin(?:_|$)|(?:^|_)ein(?:_|$)|national_?id|"
                              r"passport|driver_?s?_?licen|licen[cs]e_?(?:number|no)|alien|immigration|visa_?(?:number|status)"),
    ("date of birth", "HIGH", r"birth|(?:^|_)dob(?:_|$)"),
    ("health", "HIGH", r"health|medical|diagnos|medication|allerg|disabilit|insurance|mental|pregnan|treatment|clinical|"
                       r"symptom|accommodation|(?:^|_)condition"),
    ("financial", "HIGH", r"bank|routing|iban|swift|account_?number|card_?number|credit_?card|cvv|income|salary|wage|"
                          r"net_?worth|revenue|payment_?method|giving|donation|gift|pledge|amount"),
    ("protected characteristic", "HIGH", r"gender|race|ethnic|religio|sexual|orientation|veteran|citizenship|marital|pronoun"),
    ("internal note", "HIGH", r"note|comment|internal|staff|private|confidential|case_?worker|risk|flag|reason|"
                              r"assessment|background_?check|description"),
    ("personal contact", "MEDIUM", r"email|phone|mobile|fax|street|address|postal|zip|city|mailing|latitude|longitude"),
]
CATEGORIES = [(c, s, re.compile(p, re.I)) for c, s, p in CATEGORIES]
SSN_VALUE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
EMAIL_VALUE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- reading inputs

def strip_prefix(text):
    text = text.lstrip()
    for prefix in JSON_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            if prefix == SECURE_PREFIX:
                text = text.rstrip()
                text = text[:-2] if text.endswith("*" + "/") else text
            return text.lstrip()
    if text.startswith("*" + "/"):
        return text[2:].lstrip()
    return text


def parse_json_text(text):
    """JSON from a response body, or None. Also reads JSON blocks inside an HTML page."""
    if not text:
        return None
    body = strip_prefix(text)
    if body[:1] in "{[":
        try:
            return json.loads(body)
        except ValueError:
            pass
    if "<script" in text.lower():
        blocks = []
        for match in re.finditer(r"<script[^>]*type=[\"']application/(?:ld\+)?json[\"'][^>]*>(.*?)</script>", text, re.I | re.S):
            try:
                blocks.append(json.loads(match.group(1)))
            except ValueError:
                continue
        return blocks or None
    return None


def action_labels(post_text):
    """Names of the Aura actions in a request body (descriptor, Apex class and method, flow name). No values."""
    if not post_text or "message=" not in post_text:
        return []
    try:
        fields = urllib.parse.parse_qs(post_text)
        message = json.loads(fields.get("message", ["{}"])[0])
    except ValueError:
        return []
    labels = []
    for action in message.get("actions") or []:
        params = action.get("params") or {}
        if params.get("classname") and params.get("method"):
            labels.append("Apex %s.%s" % (params["classname"], params["method"]))
        elif params.get("flowDevName") or params.get("flowName"):
            labels.append("Flow %s" % (params.get("flowDevName") or params.get("flowName")))
        elif action.get("descriptor"):
            labels.append(action["descriptor"].split("/")[-1].replace("ACTION$", ""))
    return labels


def form_from_har(har, name, shown_text):
    entries = (har.get("log") or {}).get("entries") or []
    pages = (har.get("log") or {}).get("pages") or []
    first_url = entries[0]["request"]["url"] if entries else ""
    responses = []
    for entry in entries:
        request, response = entry.get("request") or {}, entry.get("response") or {}
        content = response.get("content") or {}
        text = content.get("text") or ""
        if content.get("encoding") == "base64":
            try:
                text = base64.b64decode(text).decode("utf-8", "replace")
            except ValueError:
                text = ""
        responses.append({"url": request.get("url", ""), "status": response.get("status"),
                          "contentType": content.get("mimeType", ""), "body": text,
                          "actions": action_labels((request.get("postData") or {}).get("text"))})
    page_url = next((e["request"]["url"] for e in entries if (e.get("_resourceType") == "document")), first_url)
    title = name or (pages[0].get("title") if pages else "") or page_url or "Form"
    steps = [{"label": "page text", "url": page_url, "shown": [shown_text], "inputs": []}] if shown_text is not None else []
    return {"name": title, "url": page_url, "steps": steps, "responses": responses, "console": [],
            "notes": [] if shown_text is not None else ["no page text given, so shown or not shown was not checked"],
            "screen_checked": shown_text is not None}


def load_forms(paths, shown_path=None, name=None):
    shown_text = None
    if shown_path:
        with open(shown_path, encoding="utf-8", errors="replace") as f:
            shown_text = f.read()
    forms = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, ValueError) as error:
            raise InputError("cannot read %s: %s" % (path, error))
        if isinstance(data, dict) and data.get("tool") == "guest_pass":
            for form in data.get("forms") or []:
                form = dict(form)
                form["screen_checked"] = bool(form.get("steps"))
                if shown_text is not None:
                    form.setdefault("steps", []).append({"label": "page text", "shown": [shown_text], "inputs": []})
                    form["screen_checked"] = True
                forms.append(form)
        elif isinstance(data, dict) and "log" in data:
            forms.append(form_from_har(data, name if len(paths) == 1 else None, shown_text))
        else:
            raise InputError("%s is neither a HAR file nor a guest_pass capture" % path)
    return forms


# ---------------------------------------------------------------- finding records

def object_of(record_id, declared=None):
    if declared:
        return declared
    if record_id and SF_ID.match(str(record_id)):
        return KNOWN_PREFIX.get(str(record_id)[:3], "record (key prefix %s)" % str(record_id)[:3])
    return "record"


def scalar(value):
    return isinstance(value, (str, int, float, bool))


def looks_like_fields(obj):
    keys = [k for k, v in obj.items() if k not in SKIP_KEYS and FIELD_NAME.match(k) and scalar(v)]
    custom = [k for k in keys if k.endswith("__c")]
    standard = [k for k in keys if k in STANDARD_FIELDS]
    return keys if (len(custom) + len(standard)) >= 2 else []


def extract_records(node, found, source, depth=0):
    """Walk any JSON and collect record-like objects: Apex and flow records (attributes.type),
    UI API records (apiName and fields with value), and plain maps with an Id and field names."""
    if depth > 60:
        return
    if isinstance(node, str):
        stripped = node.strip()
        if len(stripped) > 20 and stripped[:1] in "{[":
            try:
                extract_records(json.loads(stripped), found, source, depth + 1)
            except ValueError:
                pass
        return
    if isinstance(node, list):
        for item in node:
            extract_records(item, found, source, depth + 1)
        return
    if not isinstance(node, dict):
        return
    fields = None
    rtype = None
    rid = None
    ui_fields = node.get("fields")
    if isinstance(node.get("apiName"), str) and isinstance(ui_fields, dict) and \
            any(isinstance(v, dict) and "value" in v for v in ui_fields.values()):
        rtype, rid = node["apiName"], node.get("id")
        fields = {}
        for key, cell in ui_fields.items():
            if isinstance(cell, dict) and "value" in cell:
                if scalar(cell["value"]) or cell["value"] is None:
                    fields[key] = cell["value"]
                else:
                    extract_records(cell["value"], found, source, depth + 1)
    elif isinstance(node.get("attributes"), dict) and node["attributes"].get("type"):
        rtype, rid = node["attributes"]["type"], node.get("Id")
        fields = {k: v for k, v in node.items() if k not in SKIP_KEYS and (scalar(v) or v is None)}
    elif isinstance(node.get("Id"), str) and ID_SHAPE.match(node["Id"]) and looks_like_fields(node):
        rid = node["Id"]
        fields = {k: v for k, v in node.items() if k not in SKIP_KEYS and (scalar(v) or v is None)}
    elif looks_like_fields(node):
        fields = {k: v for k, v in node.items() if k not in SKIP_KEYS and (scalar(v) or v is None)}
    if fields is not None:
        key = (object_of(rid, rtype), str(rid)[:15] if rid else "new:" + ",".join(sorted(fields))[:200])
        record = found.setdefault(key, {"object": key[0], "id": rid, "fields": {}, "sources": []})
        for name, value in fields.items():
            if name not in record["fields"] or record["fields"][name] in (None, ""):
                record["fields"][name] = value
        if source not in record["sources"]:
            record["sources"].append(source)
    for key, value in node.items():
        if key == "fields" and fields is not None and rtype and isinstance(ui_fields, dict):
            continue
        if isinstance(value, (dict, list, str)):
            extract_records(value, found, source, depth + 1)


# ---------------------------------------------------------------- classifying

def bare(name):
    name = name.split(".")[-1]
    name = re.sub(r"__c$|__r$", "", name)
    return re.sub(r"^[A-Za-z0-9]+__", "", name)


def classify(name, value):
    if name in AUDIT_FIELDS or name.split(".")[0] in ("Owner", "CreatedBy", "LastModifiedBy"):
        return "owner or audit", "MEDIUM"
    stem = bare(name)
    for category, severity, pattern in CATEGORIES:
        if pattern.search(stem):
            return category, severity
    if isinstance(value, str):
        if SSN_VALUE.match(value.strip()):
            return "government id", "HIGH"
        digits = re.sub(r"[ -]", "", value)
        if digits.isdigit() and 13 <= len(digits) <= 19 and luhn(digits):
            return "financial", "HIGH"
        if EMAIL_VALUE.match(value.strip()):
            return "personal contact", "MEDIUM"
    return "other", "LOW"


def luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def describe(value):
    """A value reduced to its kind and length, so the report holds no personal data."""
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, (int, float)):
        return "number"
    text = str(value)
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return "date"
    if ID_SHAPE.match(text):
        return "record id"
    if EMAIL_VALUE.match(text):
        return "email address"
    return "text, %d characters" % len(text)


def normalize(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def screen_text(form):
    parts = []
    for step in form.get("steps") or []:
        parts += [str(s) for s in step.get("shown") or []]
        parts += [str(s) for s in step.get("inputs") or []]
    return normalize(" \n ".join(parts))


def was_shown(value, screen):
    if isinstance(value, bool):
        return False
    text = normalize(value)
    if len(text) < 2:
        return False
    if text in screen:
        return True
    # A date the page shows in another format
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if match:
        y, m, d = match.groups()
        for shape in ("%d/%d/%s" % (int(m), int(d), y), "%s/%s/%s" % (m, d, y), "%d/%d/%s" % (int(d), int(m), y)):
            if shape in screen:
                return True
    return False


def subject_ids(form, extra):
    ids = {str(i)[:15] for i in extra or []}
    for step in form.get("steps") or []:
        urls = [step.get("url") or ""]
        for url in urls + [form.get("url") or ""]:
            for values in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).values():
                ids.update(v[:15] for v in values if ID_SHAPE.match(v))
    for value in (form.get("query") or {}).values():
        if isinstance(value, str) and ID_SHAPE.match(value):
            ids.add(value[:15])
    return ids


def is_person(record):
    if record["object"] in PERSON_TYPES:
        return True
    if record["object"] == "Account" and PERSON_FIELDS & set(record["fields"]):
        return True
    return False


def is_guest_user(record):
    return record["object"] == "User" and any(isinstance(v, str) and "guest" in v.lower() for v in record["fields"].values())


# ---------------------------------------------------------------- analysis

FIXES = {
    "sanitize": "In the flow that loads this record, pass it through the Flow Tool Kit action FLS Record(s) Sanitizer "
                "(FlowToolKit__DataSanitizer_Invocable) before the form component, and give the form the action's Record "
                "output. It removes every field the guest cannot read, so the guest's profile and permission sets decide "
                "what the form receives.",
    "fls": "Grant the guest Read only on the fields the form shows (the org's guest permission set), and remove Read on the "
           "rest: %s.",
    "query": "Or query only the fields the form needs: in the Get Records element choose the fields instead of storing all fields.",
    "mode": "Run the flow in the default context (user permissions) unless it truly needs system context.",
    "prefill": "If the values come from a Pre-fill Template or a prefill flow, keep the template to defaults only and let the "
               "prefill flow set only the fields the form shows (the Prefill From Mapped Record action copies only mapped sections).",
    "person": "Another person's record reached the browser. Never look a record up by an Id or value from the link in system "
              "context: use a single-use token (as the Flow Tool Kit resume link does) or require sign-in. The sanitizer "
              "strips fields, not records, so it does not fix this on its own.",
}


def analyze_form(form, extra_subjects=None):
    found = {}
    sources = []
    for response in form.get("responses") or []:
        data = parse_json_text(response.get("body") or "")
        if data is None:
            continue
        label = ", ".join(response.get("actions") or []) or urllib.parse.urlparse(response.get("url") or "").path or "response"
        if label not in sources:
            sources.append(label)
        extract_records(data, found, label)
    screen = screen_text(form)
    checked = bool(form.get("screen_checked")) and bool(screen)
    subjects = subject_ids(form, extra_subjects)
    records = []
    people = [r for r in found.values() if is_person(r) and not is_guest_user(r) and r["id"]]
    for record in found.values():
        if is_guest_user(record):
            continue
        rows = []
        for name, value in sorted(record["fields"].items()):
            if value in (None, ""):
                continue
            category, severity = classify(name, value)
            shown = was_shown(value, screen) if checked else None
            rows.append({"field": name, "kind": describe(value), "category": category, "severity": severity,
                         "shown": shown})
        if not rows:
            continue
        other_person = False
        if is_person(record) and record["id"]:
            rid = str(record["id"])[:15]
            if subjects:
                other_person = rid not in subjects
            elif len(people) > 1:
                other_person = record is not people[0]
        records.append({"object": record["object"], "id": record["id"], "sources": record["sources"],
                        "other_person": other_person, "fields": rows})
    return summarize(form, records, checked, sources, subjects)


def summarize(form, records, checked, sources, subjects):
    hidden = [(r, f) for r in records for f in r["fields"] if f["shown"] is not True]
    severity = None
    exposed = []
    for record, field in hidden:
        if field["severity"] in ("HIGH", "MEDIUM"):
            exposed.append("%s.%s (%s)" % (record["object"], field["field"], field["category"]))
            if severity is None or RANK[field["severity"]] < RANK[severity]:
                severity = field["severity"]
    others = [r for r in records if r["other_person"]]
    if others:
        severity = "HIGH"
    if severity is None and hidden:
        severity = "LOW"
    plain = sorted({f["field"] for _, f in hidden})
    fixes = []
    if others:
        fixes.append(FIXES["person"])
    if hidden:
        fixes += [FIXES["sanitize"], FIXES["fls"] % ", ".join(plain[:12]) + ("" if len(plain) <= 12 else " and %d more" % (len(plain) - 12)),
                  FIXES["query"], FIXES["mode"], FIXES["prefill"]]
    what = []
    if others:
        what.append("%d other person's record%s reached the browser (%s)" % (
            len(others), "" if len(others) == 1 else "s", ", ".join(sorted({r["object"] for r in others}))))
    if hidden:
        what.append("%d field value%s received but %s on screen%s" % (
            len(hidden), "" if len(hidden) == 1 else "s", "not shown" if checked else "not checked against what is",
            (", sensitive: " + "; ".join(exposed[:8]) + ("" if len(exposed) <= 8 else "; and %d more" % (len(exposed) - 8))) if exposed else ""))
    return {"name": form.get("name") or form.get("url") or "Form", "url": redact_url(form.get("url") or ""),
            "severity": severity or "CLEAN", "screen_checked": checked, "subject_ids": len(subjects),
            "what": "; ".join(what) or "nothing beyond what the form shows", "fixes": fixes,
            "records": records, "sources": sources, "notes": list(form.get("notes") or []),
            "stopped": form.get("stopped"), "console_errors": sum(1 for c in form.get("console") or [] if c.get("type") == "error")}


def redact_url(url):
    """Keep the address and parameter names; replace each parameter value with a placeholder."""
    parts = urllib.parse.urlparse(url)
    if not parts.query:
        return url
    query = "&".join("%s=<%s>" % (k, "id" if ID_SHAPE.match(v) else "value") for k, v in urllib.parse.parse_qsl(parts.query))
    return urllib.parse.urlunparse(parts._replace(query=query))


# ---------------------------------------------------------------- writing

def md(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_exposure(result):
    lines = ["# What reached the browser", "",
             "Generated %s. Each form was opened as a logged-out guest. Field values are reduced to their kind; "
             "no value is written here." % result["generated"], ""]
    lines += ["| Form | Severity | What is exposed |", "|---|---|---|"]
    for form in result["forms"]:
        lines.append("| %s | %s | %s |" % (md(form["name"]), form["severity"], md(form["what"])))
    for form in result["forms"]:
        lines += ["", "## %s: %s" % (form["severity"], form["name"]), "", "Address: `%s`" % form["url"]]
        if form.get("stopped"):
            lines.append("Stopped: %s." % form["stopped"])
        for note in form.get("notes") or []:
            lines.append("Note: %s." % note)
        if form["sources"]:
            lines.append("Data came from: %s." % ", ".join(form["sources"][:10]))
        for record in form["records"]:
            lines += ["", "**%s**%s" % (record["object"], " (another person's record)" if record["other_person"] else ""), "",
                      "| Field | Value kind | Shown on screen | Looks like |", "|---|---|---|---|"]
            for field in record["fields"]:
                shown = {True: "yes", False: "**no**", None: "not checked"}[field["shown"]]
                look = field["category"] if field["category"] == "other" else "**%s** (%s)" % (field["category"], field["severity"])
                lines.append("| %s | %s | %s | %s |" % (md(field["field"]), field["kind"], shown, look))
        if form["fixes"]:
            lines += ["", "Fix, in this order:", ""] + ["%d. %s" % (i, fix) for i, fix in enumerate(form["fixes"], 1)]
    return "\n".join(lines) + "\n"


def write(out_dir, name, text):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def cmd_analyze(args):
    forms = load_forms(args.inputs, args.shown, args.form)
    if not forms:
        raise InputError("no form found in the input")
    result = {"generated": datetime.date.today().isoformat(),
              "forms": [analyze_form(form, args.subject_id) for form in forms]}
    if args.json:
        print(json.dumps(result, indent=1))
    out = args.out or "."
    write(out, "exposure.json", json.dumps(result, indent=1) + "\n")
    path = write(out, "exposure.md", render_exposure(result))
    if not args.json:
        print("exposure: %s" % path)
        for form in result["forms"]:
            print("  %s %s: %s" % (form["severity"], form["name"], form["what"]))
    return 1 if any(f["severity"] == "HIGH" for f in result["forms"]) else 0


def render_report(exposure, flows):
    rows = []
    for form in (exposure or {}).get("forms") or []:
        rows.append({"kind": "Form (live)", "name": form["name"], "severity": form["severity"], "what": form["what"],
                     "fix": form["fixes"][0] if form["fixes"] else "Nothing to change.", "sources": form["sources"]})
    for finding in (flows or {}).get("findings") or []:
        confirmed = [f["name"] for f in (exposure or {}).get("forms") or []
                     if any("Flow " + finding["flow"] in s.split(", ") for s in f["sources"]) and f["severity"] != "CLEAN"]
        rows.append({"kind": "Flow", "name": "%s, %s" % (finding["flow"], finding["element"]), "severity": finding["severity"],
                     "what": finding["title"] + (" (confirmed in the live pass: %s)" % ", ".join(confirmed) if confirmed else ""),
                     "fix": finding["fix"][0], "sources": []})
    rows.sort(key=lambda r: (RANK.get(r["severity"], 9), r["kind"], r["name"]))
    high = sum(1 for r in rows if r["severity"] == "HIGH")
    lines = ["# Guest forms and flows: what a visitor receives", ""]
    lines.append(("%d form%s or flow%s send data a visitor should not have." % (high, "" if high == 1 else "s", "" if high == 1 else "s"))
                 if high else "No form or flow sends a visitor a sensitive field or another person's record.")
    lines += ["", "| Kind | Form or flow | Severity | What is exposed | First fix |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s |" % (row["kind"], md(row["name"]), row["severity"], md(row["what"]), md(row["fix"])))
    lines += ["", "Every fix in full: exposure.md (live pass) and flow-review.md (flow review). "
              "Values are reduced to their kind; the raw captures stay in the project folder and are not part of this report."]
    return "\n".join(lines) + "\n"


def cmd_report(args):
    def read(path):
        if not path:
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    exposure, flows = read(args.exposure), read(args.flows)
    path = write(args.out or ".", "guest-report.md", render_report(exposure, flows))
    print("report: %s" % path)
    severities = [f["severity"] for f in (exposure or {}).get("forms") or []] + [f["severity"] for f in (flows or {}).get("findings") or []]
    return 1 if "HIGH" in severities else 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("inputs", nargs="+", help="a guest_pass capture.json or a .har file")
    p.add_argument("--shown", help="a text file of what the page showed (for a HAR)")
    p.add_argument("--form", help="the form's name (for a single HAR)")
    p.add_argument("--subject-id", action="append", help="the record Id the prefill link is for")
    p.add_argument("--out")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("report")
    p.add_argument("--exposure")
    p.add_argument("--flows")
    p.add_argument("--out")
    p.set_defaults(func=cmd_report)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as error:
        print("exposure: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
