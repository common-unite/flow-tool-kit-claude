"""Turn everything the tool could not settle into plain-language client questions.

One rule governs this module: **a question is only worth asking if the answer
changes what gets built.** Everything else is a note, and notes belong in the
workbook, not in a list the client has to work through.

Each question carries a recommendation. Asking a nonprofit admin to choose
between options with no guidance is not consultation, it is offloading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field

from . import sensitive

ADDRESS_LABEL = re.compile(r"\b(address|street|city|state|province|zip|postal)\b", re.IGNORECASE)


@dataclass
class Question:
    number: int
    topic: str
    question: str
    why: str
    recommendation: str
    options: list[str] = dataclass_field(default_factory=list)
    evidence: list[str] = dataclass_field(default_factory=list)


def build(document: dict, proposals, validation: list[dict],
          edition: str | None = None, ladder_items=None) -> list[Question]:
    """Assemble the client question list from every unresolved decision.

    ``edition`` is the Flow Tool Kit edition ftk-start recorded ("paid" or
    "free"); when it is missing, the edition becomes the first question,
    because it decides where contact, organization and address questions are
    built. ``ladder_items`` is ``ladder.plan(document)``; custom code and
    calculations become one rebuild question with its recommendation.
    """
    questions: list[Question] = []

    def add(topic, question, why, recommendation, options=None, evidence=None):
        questions.append(
            Question(len(questions) + 1, topic, question, why, recommendation,
                     options or [], evidence or [])
        )

    # 0. Edition - decides where contact, organization and address questions are built.
    unplaced = [p for p in proposals if getattr(p, "placement", "") == "edition_unknown"]
    if edition not in ("paid", "free") and unplaced:
        add(
            "Flow Tool Kit edition",
            "Is the Flow Tool Kit installed in your org the paid edition or the free one?",
            "In the paid edition, contact, organization and address questions are built "
            "on Contact and Account forms and mapped onto the submission, so the forms "
            "you already use are reused and the packaged conversion fills the records. "
            "The free edition builds every question on the submission itself.",
            "Answer from Setup, Installed Packages, or from the answer you gave when "
            "this project started.",
            options=["Paid", "Free"],
            evidence=[f"{p.field_id} \"{p.label}\" -> {p.component_object}" for p in unplaced[:6]],
        )

    # 0b. Sensitive information - whether to collect it at all comes before where it is stored.
    flagged = [f for f in document["fields"] if f.get("sensitive")]
    if flagged:
        add(
            "Sensitive information",
            f"This form asks for {len(flagged)} piece(s) of sensitive information. Should the new form collect "
            "each one at all, and if so, how should it be stored?",
            "A government identifier, an account number, a health detail or a password saved on the submission is "
            "readable by everyone who can read that record, travels in confirmation emails and PDFs, and on a "
            "public (guest) form is typed by people nobody has verified. Not collecting it is the strongest "
            "protection.",
            "We recommend not collecting it on the form unless a law or your process requires it (ask for the last "
            "four digits, or collect it in person). If it is required: an encrypted field (Shield Platform "
            "Encryption, or an encrypted text field) that only the people who need it can read, left out of "
            "confirmation emails, PDFs and prefill, and a guest-access review before a public form goes live.",
            options=[
                "Do not collect it (recommended unless it is required)",
                "Collect it, in an encrypted field with restricted access",
                "Collect it in an ordinary field (not recommended)",
            ],
            evidence=[f"{f['id']} \"{sensitive.shown(f)}\": {f['sensitive']['kind']}" for f in flagged[:10]],
        )

    # 1. Address storage - decides the field type of every address, so it is asked before any plan.
    address_fields = [f for f in document["fields"] if ADDRESS_LABEL.search(f.get("label") or "")]
    if address_fields:
        add(
            "Address storage",
            "Does your Salesforce org have State and Country/Territory Picklists turned on, "
            "or do you plan to turn them on?",
            "A combined Salesforce address field only accepts state and country codes (MO, "
            "US). Filling it from existing records whose State and Country are typed text "
            "(Missouri, USA) needs a translation step for every mapping, and any value it "
            "misses makes the submission fail when it saves. Turning the picklists on is "
            "permanent, and a check-only deploy never turns the setting on, so every "
            "combined address field fails validation until it is on. Separate text fields "
            "accept whatever the existing records hold.",
            "We recommend separate Street, City, State, Postal Code and Country fields unless "
            "the picklists are already on or you are committed to turning them on.",
            options=[
                "Separate text fields (recommended unless the picklists are on)",
                "Combined address field - the picklists are on, or will be before launch",
            ],
            evidence=[f["label"] for f in address_fields[:6]],
        )

    # 2. Ambiguous source labels - the connector cannot say which field it reads.
    ambiguous = [f for f in validation
                 if f["check"] == "source-label" and "ambiguous" in f["message"]]
    if ambiguous:
        pairs = sorted({f["message"].split('from "')[1].split('"')[0] for f in ambiguous})
        add(
            "Repeated field names",
            f"Two or more questions on this form share the same name "
            f"({', '.join(pairs)}). Please confirm which question each mapping should read.",
            "The current setup records only the field name, not which section it came "
            "from, so the configuration alone cannot say. Getting this wrong would "
            "silently file one section's answers (a second address, say) as another's.",
            "We have matched each mapping to the section whose name fits it best; please "
            "confirm the pairs listed below.",
            evidence=[f["message"] for f in ambiguous[:4]],
        )

    # 3. Questions with no label that are nonetheless mapped.
    blank = [p for p in proposals if not p.label and p.targets]
    for proposal in blank:
        add(
            "Unlabelled question",
            f"One question on the form has no visible text but its answer is saved to "
            f"{', '.join(proposal.targets)}. Can you confirm what it asks?",
            "Without knowing what the question means we cannot name the field that "
            "replaces it, and it would be rebuilt as an unlabelled box.",
            "Its answer choices and where it is saved are listed below; tell us the "
            "question it asks.",
            evidence=[f"Internal reference {proposal.field_id}."],
        )

    # 4. Orphaned target mappings.
    orphans = [f for f in document["findings"]
               if "declares" in f["message"] and "mapping table" in f["message"]]
    for finding in orphans:
        add(
            "Unused configuration",
            "Some fields are configured to be filled but no step actually fills them. "
            "Should they be reinstated in the new process, or dropped?",
            "This is usually left over from a step that was deleted. Carrying it "
            "forward would rebuild something that has not worked in a long time.",
            "We recommend dropping them unless you recognise them as something that "
            "should be working.",
            evidence=[finding["message"]],
        )

    # 5. Multiple-match behaviour, which the new pipeline handles differently.
    multi = [f for f in document["findings"] if "multiple matches" in f["message"]]
    if multi:
        add(
            "Duplicate handling",
            "When more than one matching record is found, the current form updates one "
            "of them (or creates another). The new process stops and flags the "
            "submission for a person to resolve. Is that acceptable?",
            "Automatically updating one of several matches can silently write to the "
            "wrong record. Stopping is safer but means someone has to review those "
            "submissions.",
            "We recommend stopping and flagging. In practice these are rare, and a "
            "wrong merge is far more costly to unpick than a short review queue.",
            evidence=[f["message"] for f in multi],
        )

    # 6. Fields that drive form logic but are never saved. Only a connector that
    # was read can say a field is never saved; with none, the plan places them.
    connector_read = (document.get("source") or {}).get("coverage", {}).get("connector") in (
        "parsed", "hand_authored")
    coverage = [f for f in validation if f["check"] == "condition-coverage"] if connector_read else []
    for finding in coverage:
        add(
            "Unsaved answers",
            "A few questions control what the respondent sees but their answers are "
            "never saved. Should they be recorded on the submission record going forward?",
            "Saving them makes it possible to understand later why a respondent saw "
            "the form they did. Not saving them keeps the record smaller.",
            "We recommend saving them - they are cheap to store and they explain the "
            "shape of every submission.",
            evidence=[finding["message"]],
        )

    # 7. Custom code and calculations - the rebuild-direction decision (the ladder).
    items = list(ladder_items or [])
    if items or document["custom_scripts"]:
        stepped = [i for i in items if i.get("rung") != "native"]
        add(
            "Calculations and custom code",
            "Part of this form is worked out by calculations or custom code. How should "
            "that part be rebuilt?",
            "Each step up the ladder is harder to change later: a native setting your "
            "admins edit in the Form Builder, then a Flow Section they edit in Flow "
            "Builder, then a custom component only a developer changes. Values that "
            "change each year (fees, thresholds, dates) belong in a settings table your "
            "team updates without a developer.",
            "We recommend the lowest rung that does the job, as listed per item below."
            + (" Only the items marked Flow Section or custom component need more than "
               "configuration." if stepped else ""),
            options=[
                "Native: a formula or setting in the Form Builder (recommended where it fits)",
                "Flow Section: a screen flow inside the form, edited in Flow Builder",
                "Custom component: a Lightning Web Component, built and changed by a developer",
            ],
            evidence=[f"{i['element']}: {i['rung_label']} ({i['reason']})" for i in items[:8]]
            or [f"{len(document['custom_scripts'])} custom scripts found on the form."],
        )

    # 7b. Two questions that matched one field: never merged, always asked.
    shared = [p for p in proposals if getattr(p, "collided_with", "")]
    if shared:
        labels = {p.field_id: p.label for p in proposals}
        add(
            "Two questions, one field",
            f"{len(shared)} question(s) matched a field another question already uses. Which question should "
            "keep that field?",
            "Two questions saved to one field overwrite each other: the second answer replaces the first on "
            "every submission, and nothing says so.",
            "We kept the field for the closer match and proposed another field for the other question, listed "
            "below; confirm the pairs or swap them.",
            evidence=[f"{p.field_id} \"{p.label}\" shares with {p.collided_with} \"{labels.get(p.collided_with, '')}\"; "
                      f"proposed {p.staging_field}" for p in shared[:8]],
        )

    # 8. Staging fields the tool would not decide alone.
    asks = [p for p in proposals if p.disposition == "ask_client" and p.label]
    if asks:
        add(
            "Field reuse",
            f"{len(asks)} questions could reuse an existing field or get a new one. "
            "We would like to confirm each before building.",
            "Reusing the wrong field silently merges two different questions into one "
            "place, which is expensive to unpick after data has been collected.",
            "Our suggestion is listed per row in the mappings file; most are safe reuses.",
            evidence=[
                f"{p.field_id} \"{p.label}\" -> closest existing field: {p.staging_label}"
                for p in asks[:8]
            ],
        )

    # 9. Large option sets.
    big = [f for f in document["fields"] if len(f["options"]) > 50]
    if big:
        total = sum(len(f["options"]) for f in big)
        add(
            "Long lists",
            f"{len(big)} questions offer long lists ({total} choices between them). We "
            "plan to carry them across exactly as they are. Would you like them reviewed first?",
            "Long lists are rarely revisited and may hold choices you no longer use. "
            "Carrying them across unchanged is the safe default; cleaning them is "
            "separate work. City, state and postal code lists are the exception: an "
            "address section with Salesforce address checking replaces them.",
            "We recommend migrating them as-is now and reviewing them later, so the "
            "move does not also change what respondents can select.",
            evidence=[f"{f['label']}: {len(f['options'])} values" for f in big],
        )

    return questions


def to_markdown(form_name: str, questions: list[Question]) -> str:
    lines = [
        f"# Decisions We Need - {form_name}\n",
        "Each item below is a decision only your team can make. We have included what "
        "we recommend and why, so most should be a quick yes.\n",
        f"**{len(questions)} decisions.**\n",
    ]
    for q in questions:
        lines.append(f"\n## {q.number}. {q.topic}\n")
        lines.append(f"**{q.question}**\n")
        lines.append(f"{q.why}\n")
        lines.append(f"> **We recommend:** {q.recommendation}\n")
        if q.options:
            lines.append("\nOptions:\n")
            lines.extend(f"- {o}\n" for o in q.options)
        if q.evidence:
            lines.append("\n<details><summary>Detail</summary>\n\n")
            lines.extend(f"- {e}\n" for e in q.evidence)
            lines.append("\n</details>\n")
    return "".join(lines)