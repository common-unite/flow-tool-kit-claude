"""The design checks: what the build would refuse, and what a reviewer would send back.

`check(plan, base, project)` returns (errors, warnings). An error stops the drawing; a warning is printed and kept.
Every check states its reason in the message, so the fix is clear without opening this file.
"""
from __future__ import annotations

import html
import json
import re

from . import conditions, planrules, requiredness, sensitive

CONTROLS = {"TextInput", "FormattedInput", "Picklist", "MultiPicklist", "Checkbox", "NumberInput", "TextArea", "Repeater",
            "Address", "DateInput", "SignaturePad", "ImageUpload", "FileUpload", "Lookup", "RichTextInput"}
STATUSES = ("supported", "verify", "gap")
PLACEMENTS = ("submission:", "source-object:", "mapped:")
DECISIONS = ("reuse", "extend", "update", "shared-new", "shared-record", "form-only", "flow-section", "custom-lwc")
# The answers that stand for each decision, as build-form-component's composition check reads them. update changes the shared
# component in place, so it is its own answer and never the default
ANSWERS = {"reuse": {"reuse"}, "extend": {"extend"}, "update": {"update", "update the shared component", "update shared"},
           "shared-new": {"new", "create", "build new"}, "form-only": {"new", "create", "build new"}}
NEW_DECISIONS = ("shared-new", "form-only")
# The component shapes standard: how a component's questions are stored. The person chooses it for a new or extended
# component (JSON on the section is the recommended default; a record component when reuse is known at design time); reuse and update keep the existing component's shape; a plan written before shapes has none, and
# build-template then builds it as it always did (LEGACY_SHAPE)
SHAPES = ("metadata", "record", "json")
CHOSEN_SHAPE = ("form-only", "shared-new", "extend")
LEGACY_SHAPE = {"form-only": "json", "shared-new": "record", "extend": "record", "shared-record": "record"}
BUILD_SKILL = {"flow-section": "build-flow-section", "custom-lwc": "build-custom-lwc"}
PAGE_BUTTONS = ("Continue", "Next", "Submit", "Save", "Submit Form", "Submit Application", "Save Proposal", "Apply Now", "Learn More",
                "Get Started", "Start Step")
SUBMIT_BUTTONS = ("Submit", "Submit Form", "Submit Survey", "Submit Application", "Submit Registration", "Submit Payment", "Save",
                  "Save Proposal", "Register", "Apply Now", "Update")
FREE_OBJECTS = ("Form_Submission__c", "Account", "Contact", "Lead", "Case")
PAGE_OF = re.compile(r"\bpage\s+\d+\s+of\s+\d+\b", re.I)
EM_DASH = chr(0x2014)  # written as a code point so no editor or hook rewrites it
# The parameters the package maps through URL Parameter Mapping; sourceId is read by the form itself and never mapped
URL_PARAMETERS = tuple(f"pv{i}" for i in range(1, 10)) + ("utm_source", "utm_content", "utm_medium", "utm_term", "utm_campaign", "payment_intent", "eventType")
STALE_RESUME = re.compile(r"pv9|[?&]recordId=", re.I)

# A confirmation says thanks, why it matters, what happens next and when, and who to ask: two or three paragraphs
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}|\[[^\]]{3,}\]|\bcontact\b|\bcall\b|\bemail\b|write to|"
                     r"reach (?:us|out)|\bcorreo\b|\bll[aá]me|\bescrib|comun[ií]quese|\bcontacte", re.I)
NEXT = re.compile(r"\bnext\b|\bwill\b|\bwithin\b|we'll|\bexpect\b|\bsoon\b|\bsigue\b|\bpr[oó]xim", re.I)


def plain(markup: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", markup or ""))


def sentences(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text.strip() + " "))


def confirmation_problems(markup: str | None) -> list[str]:
    blocks = [plain(b[1]) for b in re.findall(r"<(p|li)\b[^>]*>(.*?)</\1>", markup or "", re.S)]
    paragraphs = [b for b in blocks if len(b.split()) >= 4]
    text = " ".join(blocks) if blocks else plain(markup)
    count, n_sentences = len(text.split()), sentences(text)
    problems = []
    if len(paragraphs) < 2:
        problems.append(f"{len(paragraphs)} paragraph(s), at least 2 wanted")
    if n_sentences < 4 or count < 45:
        problems.append(f"{n_sentences} sentence(s), {count} words: too thin (thanks, why it matters, what happens next, a contact)")
    if not NEXT.search(text):
        problems.append("does not say what happens next")
    if not CONTACT.search(text):
        problems.append("no contact for questions (a name, mailbox or phone, or a [placeholder] listed in questions)")
    return problems


def respondent_text(plan: dict):
    """(where, text) for everything a respondent reads."""
    template = plan.get("template") or {}
    for key in ("Confirmation_Page_Message__c", "Offline_Message__c"):
        yield f"template.{key}", template.get(key) or ""
    banner = template.get("banner") or {}
    for key in ("title", "subtitle", "tags"):
        yield f"template.banner.{key}", str(banner.get(key) or "")
    for p, page in enumerate(planrules.pages(plan)):
        for key in ("Page_Label__c", "Description__c"):
            yield f"pages[{p}].{key}", page.get(key) or ""
        for s, section in enumerate(page.get("sections") or []):
            for key in ("Header_Title__c", "Header_Subtitle__c", "rich_text"):
                yield f"pages[{p}].sections[{s}].{key}", section.get(key) or ""
            for field in section.get("fields") or []:
                for key in ("label", "help", "attestation_text"):
                    yield f"pages[{p}].sections[{s}] field {field.get('label', '')!r}.{key}", field.get(key) or ""


def check(plan: dict, base=None, project: dict | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    template = plan.get("template") or {}
    long_form = planrules.is_long(plan)
    n_pages = len(planrules.pages(plan))
    intake = plan.get("intake") or {}
    edition = (intake.get("edition") or (project or {}).get("edition") or "").lower()

    if not template.get("Name"):
        errors.append("template.Name is missing: the form's title")
    if planrules.kind(plan) not in planrules.FORM_KINDS:
        warnings.append(f"form_kind {plan.get('form_kind')!r} is not one of {', '.join(planrules.FORM_KINDS)}; the form-type row treats it as other")
    if not n_pages:
        errors.append("the plan has no pages")
    if not (plan.get("source") or {}).get("url") and (plan.get("source") or {}).get("platform") not in ("brief", "pdf"):
        warnings.append("source.url is missing: reviewers compare the design with the live source form; give its link or the captured file")

    # Copy
    problems = confirmation_problems(template.get("Confirmation_Page_Message__c"))
    if problems:
        errors.append("confirmation message too thin (two or three tailored paragraphs: thanks, why it matters, what happens next, a contact): "
                      + "; ".join(problems))
    if not template.get("Offline_Message__c"):
        warnings.append("template.Offline_Message__c is empty: say the form is closed and how to reach the organization")
    for where, text in respondent_text(plan):
        if EM_DASH in text:
            errors.append(f"{where}: an em-dash in respondent copy; use a colon, a comma or a new sentence")
        if re.search(r"\b\w+__c\b", plain(text)) and "{{" not in text:
            warnings.append(f"{where}: an API name in respondent copy; respondents never see field names")
    submit = template.get("Submit_Button_Label__c")
    if submit and submit not in SUBMIT_BUTTONS:
        errors.append(f"template.Submit_Button_Label__c {submit!r} is not in the package's list: {', '.join(SUBMIT_BUTTONS)}")

    # Pages and sections
    for p, page in enumerate(planrules.pages(plan)):
        where = f"page {p + 1} ({page.get('Page_Label__c') or 'no label'})"
        label = page.get("Page_Label__c") or ""
        if not label:
            errors.append(f"{where}: Page_Label__c is missing")
        elif label.strip().lower() == "welcome":
            errors.append(f"{where}: never a page labelled Welcome; name it for its purpose (About the Program, Learn More)")
        description = plain(page.get("Description__c"))
        if sentences(description) < 2:
            errors.append(f"{where}: the page description needs at least two sentences (what the page asks, then why or what to have ready)")
        button = page.get("Button_Label__c")
        if button and button not in PAGE_BUTTONS:
            errors.append(f"{where}: Button_Label__c {button!r} is not in the package's list: {', '.join(PAGE_BUTTONS)}")
        if button == "Next" and not long_form:
            errors.append(f"{where}: the forward button reads Continue, never Next")
        header = page.get("header") or {}
        if header.get("title") and PAGE_OF.search(header["title"]):
            errors.append(f"{where}: no 'Page N of M' heading; the indicator or the stage list already shows position")
        for s, section in enumerate(page.get("sections") or []):
            sw = f"{where}, section {s + 1} ({section.get('Header_Title__c') or section.get('Title__c') or 'untitled'})"
            fields = section.get("fields") or []
            titled = bool(section.get("Header_Title__c"))
            if titled and not section.get("Header_Subtitle__c"):
                errors.append(f"{sw}: every titled section has a one-line description (Header_Subtitle__c)")
            if not titled and fields and section.get("Section_Frame__c") not in (None, "clean"):
                warnings.append(f"{sw}: a section without a header is a follow-up or a note on a highlight bar; give it the clean frame or a title")
            if titled and fields and section.get("Section_Frame__c") == "clean":
                warnings.append(f"{sw}: every section that holds fields has a frame (box)")
            if not titled and not fields and not section.get("rich_text") and section.get("Component_Type__c") not in ("Flow", "Lightning Web Component"):
                errors.append(f"{sw}: an empty section with no title, text or fields")
            icon = section.get("Header_Icon_Name__c")
            if icon and not icon.startswith("utility:"):
                errors.append(f"{sw}: icon {icon!r}: icons are always utility: icons")
            if section.get("Component_Type__c") == "Flow" and not section.get("FlowApiName__c"):
                errors.append(f"{sw}: a Flow section needs FlowApiName__c (the flow build-flow-section builds)")
            if section.get("Component_Type__c") == "Lightning Web Component" and not section.get("lwcComponentName__c"):
                errors.append(f"{sw}: a custom LWC section needs lwcComponentName__c (the component build-custom-lwc builds)")
            for field in fields:
                errors += field_problems(f"{sw}, field {field.get('label', '')!r}", field)
            for kind, run in planrules.addressparts.groups(fields):
                if kind == "address":  # the package draws an address only with its row and all five parts
                    errors += planrules.addressparts.group_problems(run, sw)
            if (section.get("inner_type") == "likertSection" and fields and not conditions.options_of(fields[0])
                    and section.get("matrix") != "ranking" and section.get("Likert_Mode__c") != "Number"):
                errors.append(f"{sw}: a Likert section reads its scale from the first row's options; give that row its options")
    if planrules.kind(plan) == "survey" and n_pages == 1:
        sections = [s for p in planrules.pages(plan) for s in p.get("sections") or [] if s.get("fields")]
        if sections and not any(s.get("Survey_Section__c") for s in sections):
            warnings.append("a one-page survey shows each question section as a Survey Section (Survey_Section__c true)")

    # Rules
    count = 0
    for where, rule in conditions.iter_rules(plan):
        count += 1
        errors += conditions.rule_problems(where, rule)
    ir = planrules.load_ir(plan, base)
    if ir:
        coverage = ((ir.get("source") or {}).get("coverage") or {}).get("conditions")
        source_rules = len(ir.get("conditions") or [])
        if coverage not in ("not_captured", "unknown") and count > source_rules:
            errors.append(f"{count} show/hide rules in the plan, {source_rules} in the source: never add a rule the source does not have")
        elif coverage not in ("not_captured", "unknown") and count < source_rules:
            warnings.append(f"{count} show/hide rules in the plan, {source_rules} in the source: check each source rule is kept or dropped on purpose")
        used = {f.get("source_id") for _, _, f in conditions.iter_fields(plan)}
        used |= {c.get("source_id") for _, _, f in conditions.iter_fields(plan) for c in (f.get("repeater") or {}).get("columns") or []}
        dropped = {d.get("source_id") for d in plan.get("dropped") or []}
        for f in ir.get("fields") or []:
            if f.get("input_type") == "hidden" or f.get("present_in_rendered_form") is False or not f.get("label"):
                continue
            if f.get("id") not in used and f.get("id") not in dropped:
                errors.append(f"source field {f.get('id')} ({f.get('label')!r}) is neither in the plan nor in dropped with its reason")
        # Sensitive questions form-migrate marked: asked about, then decided (sensitive.py)
        found = sensitive.problems(plan, ir)
        errors += found[0]
        warnings += found[1]
        # Required flags kept as the source has them, or the change confirmed by the person (requiredness.py)
        found = requiredness.problems(plan, ir)
        errors += found[0]
        warnings += found[1]

    # Payment and URL parameters, as build-template writes them onto the template
    payment = plan.get("payment")
    if payment is not None:
        if not isinstance(payment, dict):
            errors.append("payment is {\"required\": true, \"condition\": <a rule>}")
        else:
            if "required" in payment and not isinstance(payment["required"], bool):
                errors.append("payment.required is true or false")
            if payment.get("condition"):
                errors += conditions.rule_problems("payment condition", payment["condition"])
    seen = set()
    for i, p in enumerate(plan.get("url_parameters") or [], 1):
        param = p.get("param")
        if param == "sourceId":
            errors.append(f"url_parameters[{i}]: sourceId is never mapped; the form reads it by itself")
        elif param not in URL_PARAMETERS:
            errors.append(f"url_parameters[{i}]: {param!r} is not a parameter the package reads ({', '.join(URL_PARAMETERS)})")
        if param in seen:
            errors.append(f"url_parameters[{i}]: {param} is mapped twice")
        seen.add(param)
        if not p.get("field"):
            errors.append(f"url_parameters[{i}]: no Form Submission field to fill")

    # Components: the reuse question, Flow and LWC sections, the mapping preference
    components = {c.get("key"): c for c in plan.get("components") or []}
    catalog = intake.get("catalog") or (project or {}).get("catalog")
    for key, comp in components.items():
        cw = f"component {key!r}"
        decision = comp.get("decision")
        if decision not in DECISIONS:
            errors.append(f"{cw}: decision {decision!r} is not one of {', '.join(DECISIONS)}")
        match = comp.get("catalog_match")
        if match and not (comp.get("asked") or {}).get("answer"):
            errors.append(f"{cw}: matches {match.get('name')!r} in the org catalog but the reuse question was never answered; "
                          "ask reuse, extend or new, naming the component, and record it in asked")
        answer = str((comp.get("asked") or {}).get("answer") or "").strip().lower()
        if match and answer and decision in ANSWERS and answer not in ANSWERS[decision]:
            errors.append(f"{cw}: the person answered {answer!r} but the decision is {decision}")
        if decision in ("reuse", "extend", "update") and not (comp.get("name") or (match or {}).get("name")):
            errors.append(f"{cw}: {decision} needs the existing component's name")
        if decision == "extend" and comp.get("new_name") and comp["new_name"] == (comp.get("name") or (match or {}).get("name")):
            errors.append(f"{cw}: extend builds a new version under its own new_name, never the original; changing the original is update")
        if decision == "update":
            errors += update_problems(cw, comp)
        if comp.get("design_file"):
            design = (base / comp["design_file"]) if base is not None else None
            if decision != "extend":
                warnings.append(f"{cw}: design_file is read only for extend")
            elif design is not None and not design.exists():
                errors.append(f"{cw}: design_file {comp['design_file']!r} is not there; export the component from Form Builder and save it beside the plan")
            elif design is not None:
                try:
                    json.loads(design.read_text())
                except ValueError:
                    errors.append(f"{cw}: design_file {comp['design_file']!r} is not JSON; save Form Builder's Export as it comes")
        if decision == "extend" and not comp.get("add_fields"):
            warnings.append(f"{cw}: extend lists no add_fields; list the fields the existing component gains")
        errors_, warnings_ = shape_problems(cw, comp, decision, match)
        errors += errors_
        warnings += warnings_
        if decision in BUILD_SKILL and comp.get("build") != BUILD_SKILL[decision]:
            errors.append(f"{cw}: a {decision} component is built by {BUILD_SKILL[decision]}; set build to {BUILD_SKILL[decision]!r}")
        if not catalog and decision in NEW_DECISIONS and comp.get("reason") != "no catalog":
            warnings.append(f"{cw}: no org catalog was read, so reuse is unchecked; set reason 'no catalog' and list it in questions")
        obj = comp.get("object") or "Form_Submission__c"
        if edition == "paid" and obj not in ("Form_Submission__c", "FlowToolKit__Form_Submission__c") and decision != "reuse":
            if not comp.get("form_template_mapping"):
                errors.append(f"{cw}: on {obj} in a paid org, map each field to the Form Submission field it stands for "
                              "(form_template_mapping), so prefill, live updates and Apply Submission Field Maps work")
        if edition == "free" and obj not in FREE_OBJECTS and not obj.startswith("FlowToolKit__"):
            warnings.append(f"{cw}: on {obj}; the free edition keeps forms to Form Submission, Account, Contact, Lead and Case: mark it verify")
    for p, page in enumerate(planrules.pages(plan)):
        for s, section in enumerate(page.get("sections") or []):
            key = section.get("component")
            if key and key not in components:
                errors.append(f"page {p + 1}, section {s + 1}: component {key!r} is not in components[]")
            comp = components.get(key) or {}
            want = {"flow-section": "Flow", "custom-lwc": "Lightning Web Component"}.get(comp.get("decision"))
            if want and section.get("Component_Type__c") != want:
                errors.append(f"page {p + 1}, section {s + 1}: a {comp['decision']} component sits in a section with Component_Type__c {want!r}")

    # Gaps are listed, not drawn as if they work
    gap_features = " ".join(str(g.get("feature", "")) for g in plan.get("gaps") or [])
    for _, _, field in conditions.iter_fields(plan):
        if field.get("status") == "gap" and str(field.get("label")) not in gap_features and str(field.get("source_id")) not in gap_features:
            errors.append(f"field {field.get('label')!r} is a gap but is not listed in gaps (feature, needed, evidence)")

    # Emails: the resume link merges the Save Progress Resume Link field, never a hand-built pv9 address
    emails = plan.get("emails") or {}
    for key, email in emails.items():
        if not isinstance(email, dict) or key in ("letterhead", "sample_merge"):
            continue
        url = (email.get("button") or {}).get("url", "") + " ".join(email.get("body") or [])
        if STALE_RESUME.search(url):
            errors.append(f"emails.{key}: a pv9 or recordId resume address; merge {{{{FlowToolKit__Internal_Resume_Link__c}}}} "
                          "(Save Progress Resume Link) instead")
        if key in ("saved", "resume") and "Internal_Resume_Link__c" not in url:
            errors.append(f"emails.{key}: the button must merge {{{{FlowToolKit__Internal_Resume_Link__c}}}}, the link back to the draft")
        if "__r." in url + email.get("subject", ""):
            errors.append(f"emails.{key}: Lightning email merges cannot follow a relationship; use direct Form Submission fields")
    if template.get("Send_Save_Progress_Email__c") and not long_form and not emails.get("saved"):
        warnings.append("Save Progress email is on: design emails.saved (Email_Template_Name_Saved__c) or the package sends its built-in email")
    if long_form and not emails.get("resume"):
        warnings.append("stages mode: design emails.resume for the Email me a resume link button (Email_Template_Name_Resume_Form__c), "
                        "or the package sends its built-in email")
    if planrules.sends_confirmation(plan) is False and not plan.get("no_email_reason"):
        warnings.append("no confirmation email designed: every form gets one unless it collects no email (give the reason in no_email_reason)")

    # Anonymous surveys
    fields = [f for _, _, f in conditions.iter_fields(plan)]
    if any(str(f.get("field", "")).endswith("Anonymous__c") for f in fields):
        for key in ("Allow_Save_Progress__c", "Enable_Autosave__c", "Send_Save_Progress_Email__c"):
            if template.get(key):
                errors.append(f"anonymous survey: {key} is on; a partial save records who saved and emails a named address, so leave it off")
        if any(f.get("control") in ("FileUpload", "ImageUpload") for f in fields):
            warnings.append("anonymous survey: a file upload can identify the respondent; leave it off or tell respondents")
        if (intake.get("audience") or "").lower() not in ("guest", "guests", "public guests", "public"):
            warnings.append("anonymous survey: only a public site's guest link keeps respondents anonymous; signed-in users are recorded as Created By")
    return errors, sorted(set(warnings), key=warnings.index)


def is_packaged(comp: dict) -> bool:
    match = comp.get("catalog_match") or {}
    return bool(comp.get("packaged") or match.get("packaged") or match.get("editable") is False
                or str(comp.get("name") or match.get("name") or "").startswith("FlowToolKit__"))


def shape_problems(where: str, comp: dict, decision, match) -> tuple[list[str], list[str]]:
    """The component's shape (metadata, record or JSON) is the person's answer to a recommendation, never a silent default.

    JSON is fixed to one section, so only a form-only component can be JSON. reuse and update keep the existing
    component's shape. A plan written before shapes has none: it still draws and builds as before, with a warning."""
    errors, warnings = [], []
    shape = comp.get("shape")
    if shape is not None and shape not in SHAPES:
        errors.append(f"{where}: shape {shape!r} is not one of {', '.join(SHAPES)}")
        return errors, warnings
    if decision in BUILD_SKILL:
        if shape:
            errors.append(f"{where}: a {decision} section is built by {BUILD_SKILL[decision]} and has no shape; remove shape")
        return errors, warnings
    if shape == "json" and decision != "form-only":
        errors.append(f"{where}: JSON is fixed to one section, so only a form-only component can be JSON; a {decision} component "
                      "is a metadata or record component")
    if decision == "shared-record" and shape not in (None, "record"):
        errors.append(f"{where}: build-template's review pass promotes a section to a record component; shape must be record")
    existing = (match or {}).get("shape") or (match or {}).get("kind")
    if decision in ("reuse", "update") and shape and existing and shape != existing:
        errors.append(f"{where}: {decision} keeps the existing component's shape ({existing}); changing a component's shape is its "
                      "own question")
    if decision in CHOSEN_SHAPE:
        asked = comp.get("shape_asked") or {}
        if not shape:
            warnings.append(f"{where}: no shape recorded, so build-template builds it as {LEGACY_SHAPE[decision]}, as plans before "
                            "shapes did. Recommend a shape with the reason (JSON on the section by default, a record component when reuse is "
                            "known at design time), ask, and record shape and shape_asked "
                            "(the component shapes standard)")
        elif not str(asked.get("answer") or "").strip():
            errors.append(f"{where}: shape {shape!r} was never asked; recommend a shape with the reason, ask, and record the answer "
                          "in shape_asked")
        elif str(asked["answer"]).strip().lower() != shape:
            errors.append(f"{where}: the person answered shape {asked['answer']!r} but shape is {shape!r}")
    return errors, warnings


def update_problems(where: str, comp: dict) -> list[str]:
    """update changes a shared component in place, for every template and component using it. It needs its own question,
    answered update, that names every one of them; a complete usage list; the reason and the diff; and a component the org
    can edit. A packaged component is extended into a new version instead."""
    problems = []
    asked = comp.get("asked") or {}
    question = str(asked.get("question") or "")
    if str(asked.get("answer") or "").strip().lower() not in ANSWERS["update"]:
        problems.append(f"{where}: updating the shared component in place needs its own question, answered update; it is never the default")
    usage = comp.get("usage") or {}
    if usage.get("status") != "complete":
        problems.append(f"{where}: usage.status must be complete: find every template and component that uses it first")
    consumers = [str(c) for c in usage.get("consumers") or []]
    unnamed = [c for c in consumers if c not in question]
    if unnamed:
        problems.append(f"{where}: the update question must name every template and component it reaches; missing {unnamed}")
    if not comp.get("shared_change_reason") or not comp.get("changes"):
        problems.append(f"{where}: explain the shared change (shared_change_reason) and give its diff (changes)")
    if is_packaged(comp):
        problems.append(f"{where}: a packaged component cannot be updated; extend it into a new version")
    return problems


def field_problems(where: str, field: dict) -> list[str]:
    problems = []
    control = field.get("control")
    if control not in CONTROLS and field.get("status") != "gap":
        problems.append(f"{where}: control {control!r} is not a design system control ({', '.join(sorted(CONTROLS))}); mark it gap")
    widths = field.get("widths")
    if not planrules.is_address_part(field) and not (isinstance(widths, list) and len(widths) == 3 and all(isinstance(w, int) and 1 <= w <= 12 for w in widths)):
        problems.append(f"{where}: widths must be three column counts from 1 to 12 (large, medium, small)")
    if field.get("status") not in STATUSES:
        problems.append(f"{where}: status must be supported, verify or gap")
    placement = str(field.get("placement") or "")
    if not placement.startswith(PLACEMENTS):
        problems.append(f"{where}: placement starts with submission:, source-object: or mapped: and gives the reason")
    if not field.get("field") and field.get("status") != "gap":
        problems.append(f"{where}: no Salesforce field (field)")
    if control in ("Picklist", "MultiPicklist") and not conditions.options_of(field) and field.get("status") != "gap":
        problems.append(f"{where}: a choice field with no options")
    if control == "Repeater" and not (field.get("repeater") or {}).get("columns"):
        problems.append(f"{where}: a Repeater lists its columns in repeater.columns")
    return problems
