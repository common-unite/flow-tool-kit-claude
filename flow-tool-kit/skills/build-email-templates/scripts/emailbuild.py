#!/usr/bin/env python3
"""Build, check and prove the Lightning Email Templates a Flow Tool Kit Form Template sends.

    python3 emailbuild.py build  <plan.json> [more plans] [--org org.json] [--catalog catalog.json] [--brand brand-kit.json]
                                 [--source-dir force-app/main/default] [--out <dir>]
    python3 emailbuild.py check  <plan.json> [more plans] [same options]       checks only, writes nothing
    python3 emailbuild.py check-images <build.json>                            fetches every image address (needs network)
    python3 emailbuild.py render-apex <template DeveloperName> <Form Submission Id>   prints Apex that renders without sending
    python3 emailbuild.py verify <build.json> --template <DeveloperName> --emails rows.json [--logs rows.json] [--expect text ...]

Input: form-design's plan.json (its "emails", "template", "style", "assets" keys), or a small file with only those keys.
Output of build:
  <source-dir>/email/unfiled$public/<Name>.email and .email-meta.xml   the templates, for a metadata deploy
  <source-dir>/flows/<Flow>.flow-meta.xml                             a staff notification flow, only when emails.staff is set
  <out>/build.json        every template as a record too (for a Salesforce connector), the Form Template settings, problems
  <out>/preview.html      every email with the sample merge values, for review
Exit codes: 0 clean, 1 errors (nothing is written by build when there are errors), 2 bad input.
Python 3 standard library only.
"""
from __future__ import annotations

import argparse
import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import letterhead as lh  # noqa: E402

SUBMISSION = lh.SUBMISSION
EM_DASH = chr(0x2014)  # written as a code point so no editor rewrites it
STALE_RESUME = re.compile(r"pv9|[?&]recordId=", re.I)
PLACEHOLDER = re.compile(r"\[[^\]\n]{2,60}\]")
DEV_NAME = re.compile(r"^[A-Za-z](?:[A-Za-z0-9]|_(?!_))*$")
# A confirmation says what happens next and who to ask (the same measure form-design uses on the confirmation page)
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}|\bcontact\b|\bcall\b|\bemail\b|write to|reply|"
                     r"reach (?:us|out)|\bcorreo\b|\bll[aá]me|\bescrib|comun[ií]quese|\bcontacte", re.I)
NEXT = re.compile(r"\bnext\b|\bwill\b|\bwithin\b|we'll|\bexpect\b|\bsoon\b|\bsigue\b|\bpr[oó]xim", re.I)
ALWAYS_FIELDS = {"Name", "Id", "CreatedDate", "LastModifiedDate", "OwnerId"}

# Each kind of email: the Form Template field that names it, and what sends it
USES = {
    "confirmation": {"field": "Email_Template_Name_Confirmation__c", "what": "Confirmation email",
                     "sent": "sent once when a submission is received and converted, to the submission's Contact 1 or Lead 1"},
    "saved": {"field": "Email_Template_Name_Saved__c", "what": "Save Progress email",
              "sent": "sent when a respondent saves an ordinary (non-stages) form, at most once an hour, rendered against Contact 1"},
    "resume": {"field": "Email_Template_Name_Resume_Form__c", "what": "Resume link email (stages mode)",
               "sent": "sent when a respondent clicks Email me a resume link on a stages-mode form"},
    "start": {"field": "Email_Template_Name_Start_Form__c", "what": "Start form invitation",
              "sent": "sent when a draft submission is created with a token, inviting the person to start the form"},
    "staff": {"field": None, "what": "Staff notification",
              "sent": "sent to staff addresses by this form's own notification flow when a submission is received"},
}
LINK_USES = ("saved", "resume", "start")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- reading inputs

def read_json(path, what):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise InputError(f"{what} not found: {path}")
    except json.JSONDecodeError as e:
        raise InputError(f"{what} is not valid JSON ({path}): {e}")


def rows(data) -> list:
    """Rows as a connector or the sf CLI returns them: a list, {"records": [...]} or {"result": {"records": [...]}}."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("result"), dict):
            return rows(data["result"])
        if isinstance(data.get("records"), list):
            return data["records"]
    return []


def val(row: dict, key: str):
    for k in (key, "FlowToolKit__" + key):
        if k in row:
            return row[k]
    return None


def known_fields(org: dict, catalog: dict) -> set | None:
    names = set()
    for f in (org or {}).get("submission_fields") or []:
        names.add(f if isinstance(f, str) else (f.get("QualifiedApiName") or f.get("name") or ""))
    index = ((catalog or {}).get("fields_index") or {}).get(SUBMISSION) or {}
    names.update((index.get("fields") or {}).keys())
    names.discard("")
    return names or None


# ---------------------------------------------------------------- style, letterhead and images

def brand_from(catalog: dict, brand: dict) -> tuple[dict, dict, dict]:
    """(style, letterhead, assets) from a saved brand kit: the brand file wins over the org's Form Style defaults."""
    style, head, assets = {}, {}, {}
    kit = (catalog or {}).get("brand_kit") or {}
    defaults = kit.get("style_defaults") or {}
    if defaults.get("color_primary"):
        style["brand"] = defaults["color_primary"]
    if defaults.get("font_family"):
        style["font"] = defaults["font_family"]
    if defaults.get("font_family_heading"):
        style["heading_font"] = defaults["font_family_heading"]
    if defaults.get("default_logo"):
        assets["logo"] = defaults["default_logo"]
        if defaults.get("default_logo_alt_text"):
            head["logo_alt"] = defaults["default_logo_alt_text"]
    files = [f for f in kit.get("brand_files") or [] if f.get("read")]
    brand = brand or (files[0] if files else {})
    colors, fonts = brand.get("colors") or {}, brand.get("fonts") or {}
    for key, names in (("brand", ("primary", "brand")), ("heading_color", ("heading", "secondary", "dark")),
                       ("accent", ("accent", "tertiary")), ("background", ("background", "surface"))):
        for n in names:
            if isinstance(colors.get(n), str):
                style[key] = colors[n]
                break
    if isinstance(fonts.get("body"), str):
        style["font"] = fonts["body"]
    if isinstance(fonts.get("heading"), str):
        style["heading_font"] = fonts["heading"]
    brand_assets = brand.get("assets") or {}
    for role in ("logo", "banner"):
        if isinstance(brand_assets.get(role), str):
            assets[role] = brand_assets[role]
    if isinstance(brand_assets.get("logoAlt"), str):
        head["logo_alt"] = brand_assets["logoAlt"]
    name = brand.get("brandName") or brand.get("brand_name") or brand.get("name")
    if name:
        head["org"] = name
    return style, head, assets


def resolve_style(plan: dict, kit_style: dict) -> dict:
    """The same defaults form-design draws with, then the brand kit, then the plan's own style."""
    given = {**kit_style, **(plan.get("style") or {})}
    s = {**lh.DEFAULT_STYLE, **given}
    if given.get("font") and not given.get("font_css"):
        s["font_css"] = f"'{s['font']}', Arial, sans-serif"
    if given.get("heading_font") and not given.get("heading_font_css"):
        s["heading_font_css"] = f"'{s['heading_font']}', Georgia, serif"
    s["button_radius"] = s.get("Corner radius") or "4px"
    return s


def asset_url(name: str, org: dict, problems: list, where: str) -> str | None:
    """A Public Asset File's address, which any mail client can load: <instance>/file-asset-public/<name>?oid=<org Id>.
    The served name carries the namespace for a packaged asset (FlowToolKit__Background_Forest_Sunbeams)."""
    if not name:
        return None
    if re.match(r"https://", name):
        problems.append(("warning", f"{where}: {name} is used as given; it must load without signing in"))
        return name
    if name.startswith("asset:"):
        name = name[len("asset:"):]
    org = org or {}
    if not org.get("instance_url") or not org.get("org_id"):
        problems.append(("warning", f"{where}: asset {name!r} left out of the email: no org context (--org with instance_url and "
                                    "org_id), so its public address is unknown"))
        return None
    found = None
    for row in org.get("assets") or []:
        dev, ns = row.get("DeveloperName"), row.get("NamespacePrefix")
        served = f"{ns}__{dev}" if ns else dev
        if name in (dev, served):
            found = (served, row)
            break
    if org.get("assets") is not None and found is None:
        problems.append(("error", f"{where}: no Asset File named {name!r} in the org; load it into the Asset Library first "
                                  "(brand-kit does this), then build again"))
        return None
    served = found[0] if found else name
    if found and found[1].get("IsVisibleByExternalUsers") is False:
        problems.append(("error", f"{where}: Asset File {served!r} is not public (IsVisibleByExternalUsers is false), so mail "
                                  "clients cannot load it; make it a Public Asset File"))
    base = org["instance_url"].rstrip("/")
    return f"{base}/file-asset-public/{served}?oid={org['org_id']}"


# ---------------------------------------------------------------- checks

def plain(markup: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", markup or ""))).strip()


def paragraphs(body: list) -> int:
    n = 0
    for p in body or []:
        p = str(p)
        n += max(1, len(re.findall(r"<(?:p|li)\b", p))) if p.strip().startswith("<") else (1 if p.strip() else 0)
    return n


def template_flags(plan: dict) -> dict:
    t = plan.get("template") or {}
    return {"stages": bool(t.get("Stages_Mode__c")), "save": bool(t.get("Allow_Save_Progress__c")),
            "anonymous": any(str(f.get("field", "")).endswith("Anonymous__c") for f in iter_fields(plan)),
            "collects_email": any(re.search(r"(?:Contact1_Email|(?<![A-Za-z])Email)__c$", str(f.get("field", "")))
                                  for f in iter_fields(plan))}


def iter_fields(plan: dict):
    for page in plan.get("pages") or []:
        for section in page.get("sections") or []:
            for field in section.get("fields") or []:
                yield field


def check_email(use: str, email: dict, plan: dict, fields: set | None) -> list:
    out = []
    where = f"emails.{use}"
    name = email.get("name") or ""
    if not DEV_NAME.match(name) or name.endswith("_") or len(name) > 80:
        out.append(("error", f"{where}.name {name!r}: a developer name is letters, digits and single underscores, starts with a "
                             "letter, does not end with an underscore, at most 80 characters"))
    if len(email.get("label") or "") > 80:
        out.append(("error", f"{where}.label: at most 80 characters"))
    if not email.get("subject"):
        out.append(("error", f"{where}.subject is empty"))
    elif len(plain(email["subject"])) > 120:
        out.append(("warning", f"{where}.subject is over 120 characters; mail apps cut it short"))
    if not email.get("heading"):
        out.append(("error", f"{where}.heading is empty"))
    button = email.get("button") or {}
    texts = [email.get("subject", ""), email.get("heading", ""), *map(str, email.get("body") or []),
             button.get("label", ""), button.get("url", "")]
    joined = " ".join(texts)
    if EM_DASH in joined:
        out.append(("error", f"{where}: an em-dash; use a colon, a comma or a new sentence"))
    for ph in sorted(set(PLACEHOLDER.findall(plain(joined)))):
        out.append(("error", f"{where}: placeholder {ph} is still in the copy; ask for the real words, then build"))
    if STALE_RESUME.search(joined):
        out.append(("error", f"{where}: a pv9 or recordId address; merge {lh.RESUME_LINK} (Save Progress Resume Link) instead"))
    if button.get("url") and not (button["url"].startswith(("https://", "http://", "mailto:", "tel:")) or lh.MERGE.fullmatch(button["url"])):
        out.append(("error", f"{where}.button.url: a full https:// address or one merge field"))
    if button.get("url") and not button.get("label"):
        out.append(("error", f"{where}.button: a url with no label"))
    if use in LINK_USES and lh.RESUME_LINK_FIELD not in button.get("url", ""):
        out.append(("error", f"{where}: the button must merge {lh.RESUME_LINK}, the single-use link back to the form"))
    if use in ("confirmation", "staff") and lh.RESUME_LINK_FIELD in joined:
        out.append(("error", f"{where}: the resume link ends when the form is submitted, so it is blank in this email"))
    for m in sorted(set(lh.merges(joined))):
        try:
            lh.lightning_token(m)
        except lh.MergeError as e:
            out.append(("error", f"{where}: {e}"))
            continue
        if m.startswith(lh.GLOBAL_PREFIXES):
            if use == "staff":
                out.append(("error", f"{where}: {{{{{m}}}}}: a staff notification renders with no recipient; merge submission fields only"))
            elif m.startswith("Sender."):
                out.append(("warning", f"{where}: {{{{{m}}}}} is the user the email is sent as, not a person at the organization"))
            continue
        if fields is not None and m not in fields and m not in ALWAYS_FIELDS:
            if m == lh.RESUME_LINK_FIELD:
                out.append(("error", f"{where}: this org has no Save Progress Resume Link field ({m}); it arrived in Flow Tool Kit "
                                     "5.3, so upgrade the package before building resume emails"))
            else:
                out.append(("error", f"{where}: {{{{{m}}}}} is not a Form Submission field in this org"))
    if use == "confirmation":
        text = plain(" ".join([email.get("heading", ""), *map(str, email.get("body") or [])]))
        if paragraphs(email.get("body")) < 2:
            out.append(("error", f"{where}: at least two paragraphs (thanks and what was received, then what happens next and who to ask)"))
        if not NEXT.search(text):
            out.append(("error", f"{where}: say what happens next and when"))
        if not CONTACT.search(text) and not (plan.get("emails") or {}).get("letterhead", {}).get("email"):
            out.append(("error", f"{where}: give a contact for questions (a mailbox or phone in the body or the letterhead)"))
    if use == "staff":
        to = email.get("to") or []
        if isinstance(to, str):
            to = [to]
        if not to or not all(re.fullmatch(r"[^@\s,]+@[^@\s,]+\.[^@\s,]+", a) for a in to):
            out.append(("error", f"{where}.to: one or more staff email addresses"))
    return out


def check_plan_uses(plan: dict, emails: dict) -> list:
    out = []
    flags = template_flags(plan)
    if emails.get("saved"):
        if flags["stages"]:
            out.append(("error", "emails.saved: stages mode never sends the Save Progress email; design emails.resume for the "
                                 "Email me a resume link button instead"))
        elif not flags["save"]:
            out.append(("error", "emails.saved: the template does not allow Save Progress (Allow_Save_Progress__c)"))
    if emails.get("resume") and not flags["stages"]:
        out.append(("error", "emails.resume serves only the stages-mode Email me a resume link button; on an ordinary form with "
                             "Save Progress, design it as emails.saved"))
    if flags["stages"] and not emails.get("resume"):
        out.append(("warning", "stages mode with no emails.resume: the package sends its built-in resume email"))
    if flags["save"] and not flags["stages"] and not emails.get("saved"):
        out.append(("warning", "Save Progress is on with no emails.saved: the package sends its built-in Save Progress email"))
    if emails.get("confirmation"):
        if flags["anonymous"]:
            out.append(("warning", "an anonymous submission gets no confirmation email: the package skips it when Anonymous is ticked"))
        if plan.get("pages") and not flags["collects_email"]:
            out.append(("warning", "no Contact 1 Email or Email field in the plan: the confirmation goes to the converted Contact 1 or "
                                   "Lead 1, so the form must collect an address the conversion uses"))
    elif not plan.get("no_email_reason"):
        out.append(("warning", "no confirmation email: every form gets one unless it collects no email (give the reason in no_email_reason)"))
    return out


def check_contrast(style: dict, where: str) -> list:
    out = []
    for key, what in (("brand", "the brand bar and button"), ("heading_color", "the footer")):
        try:
            ratio = lh.contrast(style[key], "#ffffff")
        except (ValueError, KeyError):
            out.append(("warning", f"{where}: style.{key} {style.get(key)!r} is not a #rrggbb color; contrast not checked"))
            continue
        if ratio < 4.5:
            out.append(("warning", f"{where}: white text on {style[key]} ({what}) is {ratio:.1f}:1, under 4.5:1; use a darker shade "
                                   "for that color in the plan's style"))
    return out


# ---------------------------------------------------------------- building

def default_label(form: str, use: str, name: str) -> str:
    base = {"confirmation": "Confirmation", "saved": "Save Progress", "resume": "Resume Link", "start": "Invitation",
            "staff": "Staff Notification"}[use]
    label = f"{form} {base}" if form else name.replace("_", " ")
    return label[:80]


FIELD_LABELS = {"confirmation": "Email Template Name (Confirmation)", "saved": "Email Template Name (Saved)",
                "resume": "Email Template Name (Resume Form)", "start": "Email Template Name (Start Form)"}


def description(uses: list, forms: list) -> str:
    """Summary first, then what uses it and its limits (the plugin's documentation standard). One template can serve the
    Save Progress and the stages resume fields at once, since both merge the same link."""
    where = f" for {', '.join(forms)}" if forms else ""
    whats = " and ".join(USES[u]["what"] for u in uses)
    sent = "; ".join(USES[u]["sent"] for u in uses)
    named = [FIELD_LABELS[u] for u in uses if u in FIELD_LABELS]
    tail = (f" Named in the Form Template's {' and '.join(named)} field{'s' if len(named) > 1 else ''}." if named
            else " Rendered by the form's staff notification flow.")
    return (f"{whats}{where}: {sent}.{tail} Merges direct Form Submission fields only; the images are Public Asset Files.")[:1000]


def meta_xml(t: dict) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<EmailTemplate xmlns="http://soap.sforce.com/2006/04/metadata">\n'
            "    <available>true</available>\n"
            f"    <description>{xml_escape(t['description'])}</description>\n"
            "    <encodingKey>UTF-8</encodingKey>\n"
            f"    <name>{xml_escape(t['label'])}</name>\n"
            f"    <relatedEntityType>{SUBMISSION}</relatedEntityType>\n"
            "    <style>none</style>\n"
            f"    <subject>{xml_escape(t['subject'])}</subject>\n"
            "    <type>custom</type>\n"
            "    <uiType>SFX</uiType>\n"
            "</EmailTemplate>\n")


def flow_name(form: str) -> str:
    words = re.sub(r"[^A-Za-z0-9]+", "_", form).strip("_") or "Form"
    return ("Form_Submission_After_Save_Notify_Staff_" + words)[:80].rstrip("_")


def soql_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def staff_flow_xml(form: str, template: str, to: list) -> str:
    """A record-triggered flow on Form Submission: after a submission is received (Status becomes Submitted with a Submission
    Date, not a child row) for this Form Template, it renders the template with the package's Render Email Template action and
    sends it to the staff addresses. It runs after the respondent's save is committed, so a failed email never fails a submit."""
    label = f"Form Submission (After Save --> Notify Staff, {form})"[:80]
    addresses = ", ".join(to)
    entry = ("AND(\n    ISPICKVAL({!$Record.FlowToolKit__Status__c}, 'Submitted'),\n"
             "    NOT(ISBLANK({!$Record.FlowToolKit__Submission_Date__c})),\n"
             "    ISBLANK({!$Record.FlowToolKit__Parent_Form_Submission__c}),\n"
             f"    {{!$Record.FlowToolKit__Form_Template__r.Name}} = '{soql_text(form)}'\n)")
    desc = (f"Emails staff ({addresses}) when a {form} submission is received, using the {template} email template rendered "
            "against the submission. Runs after the save is committed, so the respondent's submit never waits on or fails with the "
            "email. A failed render or send is logged on the submission's Conversion Log. To change who is told, edit the "
            "addresses in Send Staff Notification.")
    e = xml_escape
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <actionCalls>
        <description>Merges the submission's fields into the {e(template)} template. It needs no recipient, so the template merges only Form Submission fields.</description>
        <name>Render_Email_Template</name>
        <label>Render Email Template</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>FlowToolKit__Flow_RenderEmailTemplate_Invocable</actionName>
        <actionType>apex</actionType>
        <connector>
            <targetReference>Switch_Render</targetReference>
        </connector>
        <faultConnector>
            <targetReference>Fault_Render_Email_Template</targetReference>
        </faultConnector>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>emailTemplate</name>
            <value>
                <stringValue>{e(template)}</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>relatedRecordId</name>
            <value>
                <elementReference>$Record.Id</elementReference>
            </value>
        </inputParameters>
        <nameSegment>FlowToolKit__Flow_RenderEmailTemplate_Invocable</nameSegment>
        <offset>0</offset>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </actionCalls>
    <actionCalls>
        <description>Sends the rendered subject and body to the staff addresses from the org's Default Workflow User.</description>
        <name>Send_Staff_Notification</name>
        <label>Send Staff Notification</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>emailSimple</actionName>
        <actionType>emailSimple</actionType>
        <faultConnector>
            <targetReference>Fault_Send_Staff_Notification</targetReference>
        </faultConnector>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>emailAddresses</name>
            <value>
                <stringValue>{e(addresses)}</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>senderType</name>
            <value>
                <stringValue>DefaultWorkflowUser</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>emailSubject</name>
            <value>
                <elementReference>Render_Email_Template.renderedSubject</elementReference>
            </value>
        </inputParameters>
        <inputParameters>
            <name>emailBody</name>
            <value>
                <elementReference>Render_Email_Template.renderedHtmlBody</elementReference>
            </value>
        </inputParameters>
        <inputParameters>
            <name>sendRichBody</name>
            <value>
                <booleanValue>true</booleanValue>
            </value>
        </inputParameters>
        <nameSegment>emailSimple</nameSegment>
        <offset>0</offset>
    </actionCalls>
    <actionCalls>
        <description>Logs why the template could not be rendered on the submission's Conversion Log. Log Only: the submission is not changed.</description>
        <name>Fault_Render_Email_Template</name>
        <label>Log Error</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>FlowToolKit__FormSubmission_LogEvent_Invocable</actionName>
        <actionType>apex</actionType>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>record</name>
            <value>
                <elementReference>$Record</elementReference>
            </value>
        </inputParameters>
        <inputParameters>
            <name>logOnly</name>
            <value>
                <booleanValue>true</booleanValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>status</name>
            <value>
                <stringValue>Error</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>conversionStatus</name>
            <value>
                <stringValue>Error</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>flowLabel</name>
            <value>
                <stringValue>{e(label)}</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>message</name>
            <value>
                <stringValue>Staff notification not sent: the email template could not be rendered. {{!Render_Email_Template.errorMessage}}</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>faultMessage</name>
            <value>
                <elementReference>$Flow.FaultMessage</elementReference>
            </value>
        </inputParameters>
        <nameSegment>FlowToolKit__FormSubmission_LogEvent_Invocable</nameSegment>
        <offset>0</offset>
    </actionCalls>
    <actionCalls>
        <description>Logs why the email could not be sent on the submission's Conversion Log. Log Only: the submission is not changed.</description>
        <name>Fault_Send_Staff_Notification</name>
        <label>Log Error</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>FlowToolKit__FormSubmission_LogEvent_Invocable</actionName>
        <actionType>apex</actionType>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>record</name>
            <value>
                <elementReference>$Record</elementReference>
            </value>
        </inputParameters>
        <inputParameters>
            <name>logOnly</name>
            <value>
                <booleanValue>true</booleanValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>status</name>
            <value>
                <stringValue>Error</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>conversionStatus</name>
            <value>
                <stringValue>Error</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>flowLabel</name>
            <value>
                <stringValue>{e(label)}</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>message</name>
            <value>
                <stringValue>Staff notification not sent</stringValue>
            </value>
        </inputParameters>
        <inputParameters>
            <name>faultMessage</name>
            <value>
                <elementReference>$Flow.FaultMessage</elementReference>
            </value>
        </inputParameters>
        <nameSegment>FlowToolKit__FormSubmission_LogEvent_Invocable</nameSegment>
        <offset>0</offset>
    </actionCalls>
    <apiVersion>62.0</apiVersion>
    <decisions>
        <description>The render action reports a failure on Has Error instead of stopping the flow, so it is checked here.</description>
        <name>Switch_Render</name>
        <label>Switch</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <defaultConnector>
            <targetReference>Send_Staff_Notification</targetReference>
        </defaultConnector>
        <defaultConnectorLabel>Rendered</defaultConnectorLabel>
        <rules>
            <name>Render_Failed</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>Render_Email_Template.hasError</leftValueReference>
                <operator>EqualTo</operator>
                <rightValue>
                    <booleanValue>true</booleanValue>
                </rightValue>
            </conditions>
            <connector>
                <targetReference>Fault_Render_Email_Template</targetReference>
            </connector>
            <label>Render failed</label>
        </rules>
    </decisions>
    <description>{e(desc)}</description>
    <environments>Default</environments>
    <interviewLabel>{e(label)} {{!$Flow.CurrentDateTime}}</interviewLabel>
    <label>{e(label)}</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value>
            <stringValue>LightningFlowBuilder</stringValue>
        </value>
    </processMetadataValues>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value>
            <stringValue>AUTO_LAYOUT_CANVAS</stringValue>
        </value>
    </processMetadataValues>
    <processType>AutoLaunchedFlow</processType>
    <start>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <doesRequireRecordChangedToMeetCriteria>true</doesRequireRecordChangedToMeetCriteria>
        <filterFormula>{e(entry)}</filterFormula>
        <object>FlowToolKit__Form_Submission__c</object>
        <recordTriggerType>CreateAndUpdate</recordTriggerType>
        <scheduledPaths>
            <connector>
                <targetReference>Render_Email_Template</targetReference>
            </connector>
            <pathType>AsyncAfterCommit</pathType>
        </scheduledPaths>
        <triggerType>RecordAfterSave</triggerType>
    </start>
    <status>Active</status>
</Flow>
"""


def build(plans: list, org: dict, catalog: dict, brand: dict) -> dict:
    fields = known_fields(org, catalog)
    kit_style, kit_head, kit_assets = brand_from(catalog, brand)
    problems, templates, forms, flows = [], {}, [], []
    for path, plan in plans:
        slug = plan.get("slug") or os.path.basename(os.path.dirname(os.path.abspath(path))) or "form"
        tpl = plan.get("template") or {}
        form = tpl.get("Name") or slug
        emails = plan.get("emails") or {}
        style = resolve_style(plan, kit_style)
        head = {**kit_head, **(emails.get("letterhead") or {})}
        assets = {**kit_assets, **(plan.get("assets") or {})}
        local = []
        images = {role: asset_url(assets.get(role), org, local, f"{slug}: assets.{role}") for role in ("logo", "banner")}
        local += check_plan_uses(plan, emails)
        local += check_contrast(style, slug)
        settings = {}
        for use in USES:
            email = emails.get(use)
            if not email:
                continue
            if not isinstance(email, dict):
                local.append(("error", f"emails.{use} must be an object"))
                continue
            local += check_email(use, email, plan, fields)
            name = email.get("name") or ""
            markup = lh.html(email, images, head, style)
            sample = emails.get("sample_merge") or {}
            entry = {"name": name, "label": email.get("label") or default_label(form, use, name), "use": use,
                     "label_given": bool(email.get("label")),
                     "subject": "", "html": "", "preview": lh.merge_sample(lh.inner_body(markup), sample),
                     "preview_subject": lh.merge_sample(_html.escape(email.get("subject", "")), sample),
                     "images": [u for u in images.values() if u], "forms": [form], "uses": [use]}
            try:
                entry["subject"] = lh.merge_lightning(email.get("subject", ""))
                entry["html"] = lh.merge_lightning(markup)
            except lh.MergeError:
                pass  # check_email has reported it, and errors stop the build
            prior = templates.get(name)
            if prior:
                if (prior["subject"], prior["html"]) != (entry["subject"], entry["html"]) or (use == "staff") != ("staff" in prior["uses"]):
                    local.append(("error", f"emails.{use}.name {name!r} is already used by a different email ({', '.join(prior['forms'])}); "
                                           "give one of them another name, or make them identical to share one template"))
                else:
                    if form not in prior["forms"]:
                        prior["forms"].append(form)
                    if use not in prior["uses"]:
                        prior["uses"].append(use)
            else:
                templates[name] = entry
            if USES[use]["field"]:
                settings[USES[use]["field"]] = name
            if use == "confirmation":
                settings["Send_Confirmation__c"] = True
                if tpl.get("Recipients_Confirmation_Email__c"):
                    settings["Recipients_Confirmation_Email__c"] = tpl["Recipients_Confirmation_Email__c"]
                if tpl.get("Attach_PDF_Confirmation__c"):
                    settings["Attach_PDF_Confirmation__c"] = True
            if use == "saved":
                settings["Send_Save_Progress_Email__c"] = True
            if use == "staff":
                to = email.get("to") or []
                to = [to] if isinstance(to, str) else to
                flows.append({"name": flow_name(form), "form": form, "template": name, "to": to})
        problems += [(level, f"{slug}: {msg}" if not msg.startswith(slug) else msg) for level, msg in local]
        forms.append({"slug": slug, "form_template": form, "id": tpl.get("Id"), "settings": settings,
                      "attach_pdf": bool(tpl.get("Attach_PDF_Confirmation__c"))})
    for t in templates.values():
        t["description"] = description(t["uses"], t["forms"])
        if len(t["forms"]) > 1 and not t["label_given"]:
            t["label"] = t["name"].replace("_", " ")[:80]  # shared by several forms: named for itself, not the first form
    return {"templates": templates, "forms": forms, "flows": flows, "problems": problems, "org": org or {}}


def record_for(t: dict, org: dict) -> dict:
    """The same template as an EmailTemplate record, for a Salesforce connector that creates records. FolderId set to the
    org Id files it in the public, unfiled Lightning folder (Public Email Templates)."""
    return {"Name": t["label"], "DeveloperName": t["name"], "FolderId": (org or {}).get("org_id") or "<the org's 18-character Id>",
            "TemplateType": "custom", "UiType": "SFX", "RelatedEntityType": SUBMISSION, "Subject": t["subject"],
            "HtmlValue": t["html"], "IsActive": True, "Description": t["description"]}


def preview_page(result: dict) -> str:
    cards = []
    for t in result["templates"].values():
        cards.append(f'<section style="margin: 0 0 48px"><h2 style="font: 600 20px Arial, sans-serif; margin: 0 0 4px">'
                     f'{_html.escape(" and ".join(USES[u]["what"] for u in t["uses"]))}: {_html.escape(", ".join(t["forms"]))}</h2>'
                     f'<p style="font: 14px Arial, sans-serif; margin: 0 0 12px; color: #444">Template {_html.escape(t["name"])} · '
                     f'Subject: {t["preview_subject"]}</p><div style="border: 1px solid #ddd">{t["preview"]}</div></section>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Email preview</title></head><body style="margin: 0; padding: 24px 16px; background: #ffffff; color: #181818">'
            '<main style="max-width: 680px; margin: 0 auto"><h1 style="font: 600 24px Arial, sans-serif">Email preview</h1>'
            '<p style="font: 14px Arial, sans-serif">Sample values stand in for the merge fields. The deployed templates merge each '
            'submission\'s own answers.</p>' + "".join(cards) + "</main></body></html>")


def write_if_changed(path: str, text: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def report(problems: list) -> int:
    errors = [m for lvl, m in problems if lvl == "error"]
    for lvl, m in problems:
        print(f"{lvl.upper()}: {m}")
    return len(errors)


def cmd_build(a, write: bool) -> int:
    plans = [(p, read_json(p, "plan")) for p in a.plans]
    org = read_json(a.org, "org context") or {}
    for key in ("assets", "submission_fields"):
        if key in org and not isinstance(org[key], list):
            org[key] = rows(org[key])
    catalog = read_json(a.catalog, "catalog") or {}
    brand = read_json(a.brand, "brand file") or {}
    result = build(plans, org, catalog, brand)
    errors = report(result["problems"])
    if errors:
        print(f"{errors} error(s); nothing written. Fix plan.json (or the org context) and run again.")
        return 1
    if not write:
        print(f"check passed: {len(result['templates'])} template(s), {len(result['flows'])} flow(s)")
        return 0
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.plans[0])), "emails")
    src = a.source_dir
    written = []
    for t in result["templates"].values():
        base = os.path.join(src, "email", "unfiled$public", t["name"])
        if write_if_changed(base + ".email", t["html"]):
            written.append(base + ".email")
        if write_if_changed(base + ".email-meta.xml", meta_xml(t)):
            written.append(base + ".email-meta.xml")
    for f in result["flows"]:
        path = os.path.join(src, "flows", f["name"] + ".flow-meta.xml")
        if write_if_changed(path, staff_flow_xml(f["form"], f["template"], f["to"])):
            written.append(path)
    summary = {
        "build_version": 1,
        "org": {k: result["org"].get(k) for k in ("org_id", "instance_url") if result["org"].get(k)},
        "templates": [{"name": t["name"], "label": t["label"], "uses": t["uses"], "forms": t["forms"], "images": t["images"],
                       "file": os.path.join(src, "email", "unfiled$public", t["name"] + ".email"),
                       "record": record_for(t, result["org"])} for t in result["templates"].values()],
        "form_templates": result["forms"],
        "flows": [{**f, "file": os.path.join(src, "flows", f["name"] + ".flow-meta.xml")} for f in result["flows"]],
        "warnings": [m for lvl, m in result["problems"] if lvl == "warning"],
    }
    for name, text in (("build.json", json.dumps(summary, indent=1) + "\n"), ("preview.html", preview_page(result))):
        if write_if_changed(os.path.join(out, name), text):
            written.append(os.path.join(out, name))
    print(f"built {len(result['templates'])} template(s), {len(result['flows'])} flow(s); {len(written)} file(s) written")
    for w in written:
        print("  " + w)
    return 0


# ---------------------------------------------------------------- proving

def cmd_check_images(a) -> int:
    summary = read_json(a.build, "build.json")
    bad = 0
    urls = sorted({u for t in summary.get("templates") or [] for u in t.get("images") or []})
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "email-image-check"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                kind = resp.headers.get("Content-Type", "")
                ok = resp.status == 200 and kind.startswith("image/")
                print(f"{'OK' if ok else 'BAD'} {resp.status} {kind} {url}")
                bad += 0 if ok else 1
        except (urllib.error.URLError, OSError) as e:
            print(f"BAD {e} {url}")
            bad += 1
    if not urls:
        print("no images to check")
    return 1 if bad else 0


def cmd_render_apex(a) -> int:
    name, sub = soql_text(a.template), soql_text(a.submission)
    print(f"""// Renders without sending: run with  sf apex run --file <this file> --target-org <org-alias>
EmailTemplate t = [SELECT Id FROM EmailTemplate WHERE DeveloperName = '{name}' ORDER BY LastModifiedDate DESC LIMIT 1];
{SUBMISSION} s = [SELECT Id, FlowToolKit__Contact_1__c, FlowToolKit__Lead_1__c FROM {SUBMISSION} WHERE Id = '{sub}'];
Id who = s.FlowToolKit__Contact_1__c != null ? s.FlowToolKit__Contact_1__c : s.FlowToolKit__Lead_1__c;
Messaging.SingleEmailMessage m = Messaging.renderStoredEmailTemplate(t.Id, who, s.Id);
System.debug('RENDER SUBJECT ' + m.getSubject());
System.debug('RENDER HTML ' + m.getHtmlBody());""")
    return 0


LOG_HINTS = (
    ("Email Template not found", "no template by that developer name on Form Submission: deploy it, and check the Form Template field matches"),
    ("No primary contact or lead", "the conversion set no Contact 1 or Lead 1, so there is no one to send to: check the form maps "
                                   "Contact 1 name and email, and the conversion"),
    ("Render Failed", "a merge field the template names is wrong or not readable: build again with the org's field list"),
    ("Send Email Message Failed", "the send was refused: in a sandbox set Deliverability to All Email, and verify the Default "
                                  "Workflow User's email address"),
    ("didn't send", "the Save Progress or resume email did not go out: the log row says why (no web form address, no recipient, "
                    "the daily limit)"),
    ("without the PDF", "set the Form Submission Convert trigger's running user (references/package-behaviour.md), then send again"),
)


def cmd_verify(a) -> int:
    summary = read_json(a.build, "build.json")
    template = next((t for t in summary.get("templates") or [] if t["name"] == a.template), None)
    if not template:
        print(f"ERROR: {a.template} is not in {a.build}")
        return 2
    emails = rows(read_json(a.emails, "email rows"))
    logs = rows(read_json(a.logs, "log rows")) if a.logs else []
    fails = []
    for row in logs:
        msg = str(val(row, "Log_Message__c") or "")
        status = str(val(row, "Status__c") or "")
        if status == "Error" or "without the PDF" in msg:
            hint = next((h for k, h in LOG_HINTS if k.lower() in msg.lower()), "read the full log message")
            fails.append(f"Conversion Log: {msg[:200]} -> {hint}")
    if not emails:
        fails.append("no EmailMessage found: the email was not sent or not logged (read the Conversion Log rows)")
    else:
        latest = sorted(emails, key=lambda r: str(r.get("CreatedDate") or r.get("MessageDate") or ""))[-1]
        body, subject = str(latest.get("HtmlBody") or ""), str(latest.get("Subject") or "")
        print(f"email: {subject!r} to {latest.get('ToAddress')} (cc {latest.get('CcAddress') or 'none'}), status {latest.get('Status')}, "
              f"attachment {latest.get('HasAttachment')}")
        for token in ("{{{", "{!"):
            if token in body or token in subject:
                fails.append(f"an unmerged field ({token}...) is in the sent email")
        for url in template.get("images") or []:
            if _html.escape(url) not in body and url not in body:
                fails.append(f"image missing from the sent email: {url}")
        for text in a.expect or []:
            if text not in body and text not in subject:
                fails.append(f"expected text not in the sent email: {text!r}")
        if a.attachment and str(latest.get("HasAttachment")).lower() != "true":
            fails.append("no attachment: the answers PDF did not attach (see the Conversion Log)")
    for f in fails:
        print("FAIL: " + f)
    if not fails:
        print("PASS: the email arrived with every merge resolved, the images in place and the expected text")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "check"):
        p = sub.add_parser(name)
        p.add_argument("plans", nargs="+")
        p.add_argument("--org", help="org context JSON: org_id, instance_url, assets (ContentAsset rows), submission_fields")
        p.add_argument("--catalog", help="org-catalog's catalog.json (brand kit and Form Submission fields)")
        p.add_argument("--brand", help="a brand-kit.json file (colors, fonts, assets, voice)")
        p.add_argument("--source-dir", default=os.path.join("force-app", "main", "default"))
        p.add_argument("--out", help="where build.json and preview.html go (default: an emails folder beside the first plan)")
    p = sub.add_parser("check-images")
    p.add_argument("build")
    p = sub.add_parser("render-apex")
    p.add_argument("template")
    p.add_argument("submission")
    p = sub.add_parser("verify")
    p.add_argument("build")
    p.add_argument("--template", required=True)
    p.add_argument("--emails", required=True, help="EmailMessage rows (Subject, HtmlBody, ToAddress, CcAddress, Status, HasAttachment)")
    p.add_argument("--logs", help="Form Submission Conversion Log rows (Status__c, Log_Message__c)")
    p.add_argument("--expect", action="append", help="text the sent email must contain, such as a merged answer")
    p.add_argument("--attachment", action="store_true", help="the email must carry the answers PDF")
    a = ap.parse_args(argv)
    try:
        if a.cmd in ("build", "check"):
            return cmd_build(a, write=a.cmd == "build")
        return {"check-images": cmd_check_images, "render-apex": cmd_render_apex, "verify": cmd_verify}[a.cmd](a)
    except InputError as e:
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
