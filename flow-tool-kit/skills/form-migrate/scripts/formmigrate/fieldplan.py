"""Propose a Form Submission staging field for every mapped form field.

FormAssembly writes straight from the form to Account/Contact/custom objects.
FlowToolKit inserts a staging record in between, so every mapping needs a
Form Submission field to land in. This module proposes one and says how sure it
is; it never decides silently.

Three-tier disposition, in order of preference:

1. ``reuse_packaged``  - a packaged field already covers this role.
2. ``create_org_canonical`` - a role-shaped field the package lacks, named for
   the role so every later form reuses it.
3. ``create_form_specific`` - a question with no reusable role.

A field whose IR entry already carries a ``target`` (a source that writes to
Salesforce today, such as an existing Form Template) becomes ``keep_target``:
it already has a home, and proposing a staging field for it would move data
off the object it is reported from.

Anything the evidence does not settle becomes ``ask_client`` with candidates
attached. The code proposes; a human reviews. It is deliberately conservative:
a wrong "reuse" silently merges two different questions into one field, which is
far more expensive to unpick than an unnecessary new field.

Every proposal also says WHERE the question is built and HOW its answer reaches
the target record, which depends on the Flow Tool Kit edition (the mapping
preference, ``_shared/standards/mapping-preference.md``):

* **Paid**: contact, organization and address questions are built as a form on
  the source object (a Contact or Account form) placed in the page section, with
  Form Builder field mapping (the Form Template Mapping tab) landing each answer
  on an existing Form Submission field, packaged first. The packaged conversion
  flows apply those maps (Apply Submission Field Maps); Transform rows are kept
  for calculated or combined values, Campaign Members and record types.
* **Free**: every question is on a Form Submission form and reaches its target
  through the conversion flow's Transform, as before.

When the schema did not come from the org (a snapshot, or nothing), every
proposal carries ``verify=True``: the names are right for the package, but not
yet checked against the org the form will run in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field

from . import dateparts

# Which role a connector node implies. Node order decides slot 1 vs slot 2 when
# a form collects two people.
_PERSON_OBJECTS = {"Contact", "Lead"}

# Words that carry no distinguishing meaning when comparing labels. "applicant" and "electronic" only say whose
# or what kind ("Applicant Signature", "Electronic Signature"); "s" is a possessive ("Contact's Email").
_STOPWORDS = {
    "the", "a", "an", "of", "your", "you", "please", "select", "enter",
    "is", "are", "do", "does", "did", "in", "to", "for", "and", "or", "this",
    "i", "my", "have", "read", "s", "applicant", "electronic", "mm", "dd", "yy", "yyyy",
}

# Meanings a word-by-word overlap misses. When a label matches ``detect`` (and ``also``, if given), the concept
# token replaces the words in ``absorbs``, so "Date of Birth" reads as Birthdate and never as the generic Date, and
# "I agree to the Photo and Media Release" reads as Photo/Video Consent. Applied to the question and to every
# packaged label alike.
_CONCEPTS = [
    ("birthdate", re.compile(r"\bdate of birth\b|\bbirth\s*date\b|\bbirthday\b|\bdob\b", re.I), None,
     {"date", "birth", "birthdate", "birthday", "dob"}),
    ("signaturedate", re.compile(r"\b(signature|signed|sign)\b", re.I), re.compile(r"\bdate\b", re.I),
     {"signature", "signed", "sign", "date"}),
    ("photoconsent", re.compile(r"\b(photo|photograph|picture|media|video)s?\b", re.I),
     re.compile(r"\b(release|consent|permission|agree|authori[sz]e)", re.I),
     {"photo", "photos", "photograph", "picture", "media", "video", "release", "consent", "permission", "agree",
      "agreement", "authorize", "authorise"}),
    ("liabilitywaiver", re.compile(r"\bliability\b|\bwaiver\b|\bhold harmless\b", re.I), None,
     {"liability", "waiver", "release", "participation", "agree", "agreement", "consent", "hold", "harmless"}),
    ("company", re.compile(r"\b(organi[sz]ation|company|business|agency|employer)\b", re.I), None,
     {"organization", "organisation", "company", "business", "agency", "employer", "referring", "school", "name"}),
    ("phone", re.compile(r"\b(phone|telephone)\b", re.I), None, {"number", "no"}),
    ("email", re.compile(r"\be-?mail\b", re.I), None, {"address"}),
]

_WORD_RE = re.compile(r"[a-z0-9]+")

# Confidence thresholds for label similarity.
_HIGH = 0.85
_MEDIUM = 0.5

# Field-type families, so a proposal never lands a date in a text slot.
_TYPE_FAMILY = {
    "Email": "email", "Phone": "phone", "Date": "date", "DateTime": "datetime",
    "Currency": "number", "Number": "number", "Percent": "number",
    "Checkbox": "boolean", "Picklist": "choice", "MultiselectPicklist": "choice",
    "Text": "text", "TextArea": "text", "LongTextArea": "text", "Url": "text",
}

# FormAssembly renders almost every field as type="text" and carries the real
# type in a validation class instead. Read the class first; the input type is
# only a fallback, and bare "text" means "unknown", never "this is a string".
_VALIDATION_FAMILY = {
    "datecal": "date", "date": "date", "datetime": "datetime",
    "email": "email", "phone": "phone", "usphone": "phone",
    "integer": "number", "number": "number", "currency": "number",
    "float": "number", "alphanum": "text",
}

_INPUT_TYPE_FAMILY = {
    "email": "email", "tel": "phone", "date": "date", "number": "number",
    "checkbox": "boolean", "radio": "choice", "choice-group": "choice",
    "textarea": "text",
}


# --- Address handling -------------------------------------------------------
#
# Addresses are the one place where large option sets are NOT reproduced.
# Salesforce has native address verification and search, so a municipal picklist
# adds annual maintenance without adding meaning. The rebuild uses an
# `addressSection` with typed subfields; the option lists are dropped.
#
# This is an address-specific exception. Program and survey option sets still
# migrate faithfully, because those encode business meaning and drive reporting.

_ADDRESS_ROLE_PATTERNS = [
    ("Street", re.compile(r"\b(street|address\s*line|addr)\b", re.I)),
    ("PostalCode", re.compile(r"\b(zip|postal)\b", re.I)),
    ("State", re.compile(r"\b(state|province)\b", re.I)),
    ("City", re.compile(r"\bcity\b", re.I)),
    ("Country", re.compile(r"\bcountry\b", re.I)),
]

# The package ships two address blocks, so a form with two addresses needs no
# new fields at all. Keyed by address role.
_MAILING_BLOCK = {
    "Street": "Mailing_Street__c", "City": "Mailing_City__c",
    "State": "Mailing_State_Province__c", "PostalCode": "Mailing_Postal_Code__c",
    "Country": "Mailing_Country__c",
}
_SECONDARY_BLOCK = {
    "Street": "Street__c", "City": "City__c",
    "State": "State_Province__c", "PostalCode": "Postal_Code__c",
    "Country": "Country__c",
}

# A section whose path says "mailing" or "home" owns the Mailing_* block.
_MAILING_SECTION_RE = re.compile(r"\b(mailing|home)\b", re.I)

# Billing addresses are collected by the payment gateway and never staged in
# Salesforce, so they must not compete for an address block. Leaving them in
# lands billing on the same fields as the form's second real address.
_GATEWAY_SECTION_RE = re.compile(r"\b(billing|payment|card)\b", re.I)


def _address_role(label: str) -> str | None:
    """Which part of an address a question collects, if any."""
    for role, pattern in _ADDRESS_ROLE_PATTERNS:
        if pattern.search(label or ""):
            return role
    return None


_ADDRESS_WORDS = {"street", "address", "line", "addr", "city", "town", "state", "province", "zip", "postal", "code",
                  "country", "the", "of", "your", "you", "and", "or", "1", "2"}


def _address_qualifier(label: str) -> str:
    """What sets one address apart in its labels ("Physical", "Mailing"), or "" when the label names only the part."""
    return " ".join(w for w in _WORD_RE.findall((label or "").lower()) if w not in _ADDRESS_WORDS)


def _address_blocks(document: dict) -> list[list[dict]]:
    """The form's address blocks, in form order: each a run of address parts, resolved by position.

    A block is the run of address questions that follow each other on the form. A new block starts when a part
    repeats (a second Street), when the label's qualifier changes (Physical City, then Mailing Street), or when an
    unrelated question from another section comes between. Grouping by section alone is not enough: a form that
    puts the street in one section and the city, state and zip in a nested one, twice, would land both streets on
    one field. A lone part ("Country of Origin") is not a block. Billing and payment sections are left out.
    """
    blocks: list[list[dict]] = []
    current: list[dict] | None = None
    roles: set[str] = set()
    qualifier = ""
    last_path = None
    for entry in document["fields"]:
        path = entry.get("section_path") or ""
        if _GATEWAY_SECTION_RE.search(path):
            current = None
            continue
        role = _address_role(entry.get("label") or "")
        if not role:
            if current is not None and path != last_path:
                current = None
            continue
        own = _address_qualifier(entry.get("label") or "")
        if current is None or role in roles or (own and qualifier and own != qualifier):
            current, roles, qualifier = [], set(), ""
            blocks.append(current)
        current.append(entry)
        roles.add(role)
        qualifier = qualifier or own
        last_path = path
    return [block for block in blocks if len(block) >= 2]


def _ordered_address_blocks(document: dict) -> list[list[dict]]:
    """Address blocks with the mailing or home one first: it owns the packaged Mailing_* block."""
    blocks = _address_blocks(document)
    def is_mailing(block):
        return any(_MAILING_SECTION_RE.search(entry.get("section_path") or "") or
                   _MAILING_SECTION_RE.search(_address_qualifier(entry.get("label") or "")) for entry in block)
    return [b for b in blocks if is_mailing(b)] + [b for b in blocks if not is_mailing(b)]


def _block_title(block: list[dict], index: int) -> str:
    qualifier = next((_address_qualifier(e.get("label") or "") for e in block if _address_qualifier(e.get("label") or "")), "")
    if qualifier:
        return qualifier.title()
    tail = (block[0].get("section_path") or "").split("/")[-1]
    return tail if tail and not re.fullmatch(r"tfa_\d+", tail) else ("Mailing" if index == 0 else f"Address {index + 1}")


def _compound_address_assignments(document: dict) -> dict[str, tuple[str, str, str]]:
    """Collapse each address block onto ONE compound Address field.

    When an org uses State and Country picklists, individual Text fields cannot
    hold a state or country - only a compound Address field integrates with
    those picklists. Staging an address as four Text fields there means the
    values never match the target's picklist and conversion fails.

    Returns ``field id -> (compound field api name, address part, block label)``.
    """
    assignments: dict[str, tuple[str, str, str]] = {}
    for index, block in enumerate(_ordered_address_blocks(document)):
        title = _block_title(block, index)
        words = [w.capitalize() for w in _WORD_RE.findall(title.lower()) if w != "address"]
        compound = f"{'_'.join(words[:2]) or ('Mailing' if index == 0 else f'Address_{index + 1}')}_Address__c"
        for entry in block:
            assignments[entry["id"]] = (compound, _address_role(entry["label"]), title)
    return assignments


def _address_assignments(document: dict) -> dict[str, tuple[str, str]]:
    """Map each address field id to (staging api name, which block).

    Blocks resolve by position (``_address_blocks``): the first (mailing or home first) takes the packaged
    Mailing_* fields, the second the packaged Street__c block, and any further block gets new fields named for
    its qualifier, so no two addresses ever share a field.
    """
    assignments: dict[str, tuple[str, str]] = {}
    for index, block in enumerate(_ordered_address_blocks(document)):
        if index < 2:
            packaged = _MAILING_BLOCK if index == 0 else _SECONDARY_BLOCK
            name = "Mailing" if index == 0 else "secondary"
        else:
            title = _block_title(block, index)
            stem = "_".join(w.capitalize() for w in _WORD_RE.findall(title.lower()) if w != "address") or f"Address_{index + 1}"
            packaged = {role: f"{stem}_{part}__c" for role, part in (
                ("Street", "Street"), ("City", "City"), ("State", "State_Province"), ("PostalCode", "Postal_Code"),
                ("Country", "Country"))}
            name = title
        for entry in block:
            target = packaged.get(_address_role(entry["label"]))
            if target:
                assignments[entry["id"]] = (target, name)
    return assignments


@dataclass
class FieldProposal:
    """One row of the Field Plan."""

    field_id: str
    label: str
    section_path: str
    origin: str
    disposition: str
    staging_field: str | None
    staging_label: str | None
    confidence: str
    evidence: str
    targets: list[str] = dataclass_field(default_factory=list)
    candidates: list[str] = dataclass_field(default_factory=list)
    notes: list[str] = dataclass_field(default_factory=list)
    proposed_type: str = ""
    proposed_values: list[str] = dataclass_field(default_factory=list)
    # Where the question is built: "form_submission" (a Form Submission form),
    # "source_object" (a form on component_object, mapped with Form Template
    # Mapping) or "edition_unknown" (decided once the edition is known).
    placement: str = ""
    component_object: str = ""
    # How the answer reaches its target: "submission_field_maps",
    # "transform", "existing" (already saved there) or "" (not converted).
    conversion: str = ""
    # True when the Form Submission field name was not checked in the org.
    verify: bool = False
    # How well the question matched its packaged field, and the other packaged fields that matched (score,
    # field), best first: what resolve_collisions reads. Not written to the mappings file.
    match_score: float = 0.0
    ranked: list = dataclass_field(default_factory=list, repr=False)
    # The other question this one would have shared a field with, when it was moved.
    collided_with: str = ""
    # What kind of sensitive information the question collects (sensitive.py), or "".
    sensitive: str = ""


# Words that mean the same thing on a form and in the packaged field labels.
_SYNONYMS = {
    "organization": "company", "organisation": "company", "business": "company",
    "agency": "company", "employer": "company", "zip": "postal",
    "telephone": "phone", "cell": "mobile", "e": "email", "mail": "email",
    "agree": "consent", "agreement": "consent",
}

# "Name" appears in a dozen packaged labels; on its own it says little about
# which one is meant, so it counts for less than the word beside it.
_WEAK = {"name": 0.3}


def _tokens(text: str) -> set[str]:
    raw = set(_WORD_RE.findall((text or "").lower()))
    concepts = set()
    for concept, detect, also, absorbs in _CONCEPTS:
        if detect.search(text or "") and (also is None or also.search(text or "")):
            concepts.add(concept)
            raw -= absorbs
    words = {_SYNONYMS.get(w, w) for w in raw} | concepts
    return {w for w in words if w not in _STOPWORDS}


def _score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    weight = lambda words: sum(_WEAK.get(w, 1.0) for w in words)  # noqa: E731
    return weight(a & b) / weight(a | b)


def _similarity(left: str, right: str) -> float:
    """Weighted Jaccard overlap on meaningful words and concepts. Cheap, and good enough here."""
    return _score(_tokens(left), _tokens(right))


# A label this bare says what kind of answer, not about what: "Date" under a signature, "Other:" after a choice.
_BARE_WORDS = {"date", "other", "specify", "signed", "explain", "describe", "details", "if", "please", "yes", "no"}
_ID_SEGMENT = re.compile(r"^(tfa_\d+|page \d+)$", re.I)


def _match_labels(document: dict) -> dict[str, str]:
    """The text each question is matched on: its label, read with the question before it when the label is bare.

    "Date" right after "Applicant Signature" is the signature date, and "Other:" right after "Gender Identity" is
    the gender's Other answer; matched alone, the first lands on the generic Date and the second on another
    question's Other field.
    """
    labels: dict[str, str] = {}
    previous: dict[str, str] = {}
    for entry in document["fields"]:
        label = (entry.get("label") or "").strip()
        path = entry.get("section_path") or ""
        words = set(_WORD_RE.findall(label.lower())) - _STOPWORDS
        if label and words <= _BARE_WORDS and previous.get(path):
            labels[entry["id"]] = f"{previous[path]} {label}"
        if label:
            previous[path] = label
    return labels


def _section_words(path: str) -> set[str]:
    """The words of a question's own section title ("Parent or Guardian").

    In a person's section they say whose answer it is, not what: matching "Parent or Guardian First Name" on them
    too keeps it from every packaged First Name.
    """
    named = [segment for segment in (path or "").split("/") if segment and not _ID_SEGMENT.match(segment)]
    return _tokens(named[-1]) if named else set()


# Which role block wins a tie when the section says nothing: the first person, then a field with no role, then the
# organization, then the second person.
_ROLE_PREFERENCE = {"Contact1": 3, None: 2, "Company": 1, "Contact2": 0}


_PERSON_NAME = re.compile(r"\b(first|last|given|family|sur)\s*name\b", re.I)
_ORG_NAME = re.compile(r"\b(organi[sz]ation|company|business|agency|employer)\b", re.I)


def section_roles(document: dict) -> dict[str, str]:
    """Which packaged role each section reads as, for forms with no connector.

    With no object graph, "Email" matches Contact1_Email and Company_Email
    equally. The section it sits in breaks the tie: a section asking for a
    first and last name is a person (the first such section Contact1, the next
    Contact2); one asking for an organization's name, and no person's, is the
    Company. The role stays a guess, so the row is still a question.
    """
    roles: dict[str, str] = {}
    people = 0
    by_section: dict[str, list[str]] = {}
    for entry in document["fields"]:
        by_section.setdefault(entry.get("section_path") or "", []).append(entry.get("label") or "")
    for section, labels in by_section.items():
        if any(_PERSON_NAME.search(label) for label in labels):
            people += 1
            if people <= 2:
                roles[section] = f"Contact{people}"
        elif any(_ORG_NAME.search(label) for label in labels):
            roles[section] = "Company"
    # A nested section ("Your Information/tfa_936": gender, phone, email) shares the role of its sibling that asks
    # the name, through their common parent; a page (a one-segment path) never takes a role this way.
    for section, role in list(roles.items()):
        parent = section.rsplit("/", 1)[0] if "/" in section else ""
        if "/" in parent and parent not in roles:
            roles[parent] = role
    return roles


_ORG_CONTACT = re.compile(r"\bcontact\b|'s\b|\btheir\b|\b(organi[sz]ation|company|agency|employer)\b", re.I)


def organization_followers(document: dict) -> dict[str, str]:
    """Questions about an organization asked right after its name: "Contact's Email" after "Referring Organization".

    In a section that also asks the respondent's own name, the section reads as Contact1, so the organization's
    email and phone would compete with the respondent's. Each question after the organization's name, in the same
    section, that says whose it is (contact, their, the organization) reads as the Company's instead.
    """
    roles: dict[str, str] = {}
    after_org: set[str] = set()
    for entry in document["fields"]:
        label = entry.get("label") or ""
        path = entry.get("section_path") or ""
        if _ORG_NAME.search(label):
            after_org.add(path)
            continue
        if _PERSON_NAME.search(label):
            after_org.discard(path)
        elif path in after_org and _ORG_CONTACT.search(label):
            roles[entry["id"]] = "Company"
    return roles


def role_of(section_path: str, roles: dict[str, str]) -> str | None:
    """The role of a section, or of the nearest parent section that has one."""
    path = section_path or ""
    while path:
        if path in roles:
            return roles[path]
        path = path.rsplit("/", 1)[0] if "/" in path else ""
    return None


def _role_for_node(node: dict, person_slots: dict[str, int]) -> str | None:
    """Map a connector node onto a packaged role prefix."""
    sobject = node.get("sobject", "")
    if sobject in _PERSON_OBJECTS:
        slot = person_slots.get(node["order_path"], 1)
        return f"Contact{slot}"
    if sobject == "Account":
        return "Company"
    return None


def _assign_person_slots(nodes: list[dict]) -> dict[str, int]:
    """Decide which person node is slot 1 and which is slot 2.

    Mirrored branches mean the same person appears twice under different paths,
    so slots are assigned per top-level branch rather than per node.
    """
    slots: dict[str, int] = {}
    seen_by_branch: dict[str, int] = {}
    for node in nodes:
        if node.get("sobject") not in _PERSON_OBJECTS:
            continue
        branch = node["order_path"].split(".")[0]
        seen_by_branch[branch] = seen_by_branch.get(branch, 0) + 1
        slots[node["order_path"]] = seen_by_branch[branch]
    return slots


def _field_family(field) -> str:
    return _TYPE_FAMILY.get(field.field_type, "text")


def _input_family(entry: dict) -> str | None:
    """The form field's type family, or None when the form does not say.

    Returning None matters: a bare ``text`` input on a FormAssembly form is an
    absence of information, not evidence that the field holds a string. Treating
    it as "text" demotes every correct date, email and phone match.
    """
    if entry.get("options"):
        return "choice"
    for rule in entry.get("validation") or []:
        family = _VALIDATION_FAMILY.get(rule.lower())
        if family:
            return family
    return _INPUT_TYPE_FAMILY.get(entry.get("input_type") or "")


def _condition_driver_ids(document: dict) -> set[str]:
    """Fields whose answer decides what the applicant sees.

    These need a landing place even when the old connector never saved them:
    the rebuilt form's conditional logic reads the staging record, so a field
    with nowhere to land cannot drive visibility at all.
    """
    option_parent = {
        option["id"]: field["id"]
        for field in document["fields"]
        for option in field["options"]
    }
    drivers: set[str] = set()
    for condition in document["conditions"]:
        for reference in condition["references"]:
            drivers.add(option_parent.get(reference, reference))
    return drivers


def _target_shape(force_app: str | None, sobject: str, target_label: str, cache: dict,
                  org: str | None = None):
    """The real metadata of the Salesforce field a mapping ultimately feeds.

    Read from the org when one is given (the Salesforce CLI), else from
    ``force_app``. An org that cannot be read falls back to ``force_app``.
    """
    if (not force_app and org is None) or not sobject or not target_label:
        return None
    if sobject not in cache:
        from . import schema as schema_module

        found = {}
        if org is not None:
            try:
                found = schema_module.load_object_fields_from_org(sobject, org or None)
            except schema_module.OrgUnavailable:
                found = {}
        if not found and force_app:
            found = schema_module.load_object_fields(force_app, sobject)
        cache[sobject] = found
    return cache[sobject].get(f"label:{target_label.strip().lower()}")


def _origin(entry: dict, computed_ids: set[str]) -> str:
    """Where a value comes from, in terms the client's admin will recognise.

    Hidden plumbing must never read as "user-entered" - an admin who sees that
    next to `IsPrefill` stops trusting the whole workbook, and rightly so.
    """
    if entry["id"] in computed_ids:
        return "component-computed"
    if (entry.get("input_type") or "") == "hidden":
        return "system"
    if "hidden" in (entry.get("section_path") or "").lower():
        return "system"
    if not entry.get("present_in_rendered_form"):
        return "system"
    return "user-entered"


def _propose_kept_target(entry: dict) -> FieldProposal:
    target = entry["target"]
    obj, field = target["object"], target["field"]
    on_submission = obj.endswith("Form_Submission__c")
    # A component on another object may already land the answer on Form
    # Submission through its Submission Field Map; that field is its staging home.
    landing = [] if on_submission else list(entry.get("submission_landing") or [])
    if landing:
        evidence = (f"Already saved to {obj}.{field} and landed on Form Submission "
                    f"{', '.join(landing)} by the component's Submission Field Map.")
    elif on_submission:
        evidence = f"Already saved to {obj}.{field}."
    else:
        evidence = (f"Already saved to {obj}.{field}; keep it on that object's component "
                    "(a Submission Field Map links it to the submission).")
    return FieldProposal(
        field_id=entry["id"], label=entry["label"], section_path=entry.get("section_path", ""),
        origin="existing", disposition="keep_target",
        staging_field=field if on_submission else (landing[0] if landing else None),
        staging_label=entry["label"] if on_submission or landing else None, confidence="high",
        evidence=evidence, targets=[f"{obj}.{field}"],
        notes=[f"Also landed on Form Submission {extra}." for extra in landing[1:]])


def build(document: dict, schema, computed_ids: set[str] | None = None,
          force_app: str | None = None,
          compound_address: bool = False,
          edition: str | None = None,
          org: str | None = None) -> list[FieldProposal]:
    """Propose a staging field for every field the form collects.

    ``edition`` is the Flow Tool Kit edition of the target org, ``"paid"`` or
    ``"free"`` (the answer ftk-start recorded); ``None`` leaves placement open.
    ``org`` is a Salesforce CLI alias used to read target objects' fields
    (``""`` for the CLI's default org); leave it ``None`` to read them from
    ``force_app`` only.
    """
    computed_ids = computed_ids or set()
    nodes = document["connector"]["nodes"]
    person_slots = _assign_person_slots(nodes)

    # Whether an absent mapping is EVIDENCE (the connector was read and does not
    # write this field) or merely SILENCE (there is no connector to read). The
    # two produce an identical empty `hits` list and mean opposite things.
    connector_is_authoritative = (
        (document.get("source") or {}).get("coverage", {}).get("connector", "parsed")
        in ("parsed", "hand_authored")
    )

    # Index every mapping by the form-field label it reads.
    label_targets: dict[str, list[tuple[dict, dict]]] = {}
    for node in nodes:
        for mapping in node["mappings"]:
            if mapping["source_kind"] != "form_field":
                continue
            key = (mapping["source_value"] or "").strip()
            label_targets.setdefault(key, []).append((node, mapping))

    # Labels are ambiguous when two fields share one; carry the id.
    label_to_ids: dict[str, list[str]] = {}
    for entry in document["fields"]:
        label = (entry["label"] or "").strip()
        if label:
            label_to_ids.setdefault(label, []).append(entry["id"])

    # Addresses stage on the packaged Text address blocks by default. A compound
    # Address field has only StateCode/CountryCode picklists, so prefill and
    # conversion from ordinary text addresses fail on names like "Missouri".
    # Pass compound_address=True only when the client confirms State and
    # Country/Territory Picklists are on (the "Address storage" client question).
    compound = _compound_address_assignments(document) if compound_address else {}
    addresses = {} if compound_address else _address_assignments(document)
    condition_drivers = _condition_driver_ids(document)
    shape_cache: dict = {}
    roles_by_section = {} if connector_is_authoritative else section_roles(document)
    match_labels = _match_labels(document)
    org_roles = {} if connector_is_authoritative else organization_followers(document)

    # A date asked as Month, Day and Year is one date question on its first part; the other two fold into it.
    date_groups = {}
    for group in dateparts.groups(document):
        for part_id in group.ids:
            date_groups[part_id] = group

    proposals = []
    for entry in document["fields"]:
        label = (entry["label"] or "").strip()
        if (entry.get("target") or {}).get("field"):
            proposals.append(_propose_kept_target(entry))
            continue
        group = date_groups.get(entry["id"])
        if group and entry["id"] != group.anchor:
            proposals.append(_propose_folded_date_part(entry, group, label_targets.get(label, []), computed_ids))
            continue
        # Look up by label even when it is empty: a blank-labelled question is
        # still a mapped question, and treating "" as "no label to match on"
        # silently reclassifies it as unmapped.
        hits = label_targets.get(label, [])
        if entry["id"] in compound:
            proposals.append(_propose_compound_address(entry, hits, compound))
            continue
        if entry["id"] in addresses:
            proposals.append(_propose_address(entry, hits, addresses, schema))
            continue
        asked = dateparts.as_date_question(entry, group) if group else entry
        proposal = _propose(
            asked, hits, schema, person_slots, label_to_ids, computed_ids,
            connector_is_authoritative,
            org_roles.get(entry["id"]) or role_of(entry.get("section_path") or "", roles_by_section),
            None if group else match_labels.get(entry["id"]),
        )
        _apply_target_shape(proposal, hits, force_app, shape_cache, org)
        if group:
            _apply_date_group(proposal, group)
        else:
            _apply_form_option_fallback(proposal, entry)
        _apply_condition_landing(proposal, asked, condition_drivers)
        proposals.append(proposal)

    # A sensitive question is never decided alone: whether to collect it, and how to store it, is the person's.
    sensitive_kinds = {f["id"]: f["sensitive"]["kind"] for f in document["fields"] if f.get("sensitive")}
    for proposal in proposals:
        kind = sensitive_kinds.get(proposal.field_id)
        if not kind:
            continue
        proposal.sensitive = kind
        if proposal.disposition in ("reuse_packaged", "create_org_canonical", "create_form_specific"):
            proposal.disposition = "ask_client"
        proposal.notes.append(
            f"Sensitive: {kind}. Decide whether to collect it at all and, if so, store it in an encrypted field "
            "with restricted access, never in emails, PDFs or prefill (questions.md, Sensitive information).")

    # Two questions never share one field: the weaker claim is moved and asked about.
    resolve_collisions(proposals, schema)
    # Names are truncated question text, so two questions that open the same way
    # collide. Resolving it here means no caller can forget to.
    deduplicate_names(proposals, schema)

    calculated = computed_ids | {f["id"] for f in document["fields"] if f.get("calculation")}
    for proposal in proposals:
        apply_mapping_preference(proposal, edition, calculated)
    if not getattr(schema, "verified", True):
        for proposal in proposals:
            if proposal.staging_field and proposal.disposition not in ("keep_target", "skipped"):
                proposal.verify = True
    return proposals


def _apply_date_group(proposal: FieldProposal, group) -> None:
    """The kept part of a date asked as Month, Day and Year: one Date field, and a note on what replaced what."""
    if proposal.disposition.startswith("create") and proposal.proposed_type in ("", "Text"):
        proposal.proposed_type = "Date"
    proposal.notes.append(
        f"One question: the source asks {group.title} as {', '.join(group.labels[:-1])} and {group.labels[-1]} "
        f"({', '.join(group.ids)}); build it as one date control, and leave {' and '.join(group.folded)} out of "
        "the new form (the plan's dropped list).")


def _propose_folded_date_part(entry: dict, group, hits: list, computed_ids: set[str]) -> FieldProposal:
    """A part of a date asked as Month, Day and Year that is not kept: its answer is part of the one date question."""
    targets = sorted({f"{n['sobject']}.{m['target_field_label']}" for n, m in hits})
    return FieldProposal(
        field_id=entry["id"], label=(entry.get("label") or "").strip(), section_path=entry.get("section_path", ""),
        origin=_origin(entry, computed_ids), disposition="folded", staging_field=None, staging_label=None,
        confidence="high",
        evidence=(f"Part of {group.title}, which the source asks as {', '.join(group.labels[:-1])} and "
                  f"{group.labels[-1]}: folded into {group.anchor} \"{group.title}\", one date control."),
        targets=targets,
        notes=[f"Not a question of its own on the new form: list it in the plan's dropped list "
               f"(\"{group.title}: folded into one date control\")."])


def _apply_target_shape(proposal, hits, force_app, cache, org=None) -> None:
    """Shape a NEW staging field like the Salesforce field it will feed.

    Keeping the staging field the same type - and, for picklists, the same value
    set - is what keeps the submission record and the object it converts into in
    step. A Text staging field feeding a Picklist target silently accepts values
    the target will reject at conversion time, which surfaces as a failed
    conversion long after the form was filled in.
    """
    if not proposal.disposition.startswith("create"):
        return
    for node, mapping in hits:
        shape = _target_shape(force_app, node["sobject"], mapping["target_field_label"], cache, org)
        if not shape:
            continue
        proposal.proposed_type = shape.field_type
        proposal.proposed_values = list(shape.picklist_values)

        # Name it after the target too, not merely shape it like the target.
        # A name built from question text truncates mid-phrase
        # ("Is_Any_Member_Of_Your__c") and drifts from the field it feeds;
        # mirroring keeps the pair readable side by side.
        mirrored = _mirror_target_name(shape.api_name, proposal.staging_field)
        if mirrored and mirrored != proposal.staging_field:
            proposal.notes.append(
                f"Named after its target field so the pair reads together - the "
                f"question text alone would have truncated to {proposal.staging_field}."
            )
            proposal.staging_field = mirrored

        proposal.notes.append(
            f"Shape it to match {node['sobject']}.{shape.api_name} "
            f"({shape.field_type}"
            + (f", {len(shape.picklist_values)} values" if shape.picklist_values else "")
            + ") so the staging record and the target object stay in step."
        )
        return


def _mirror_target_name(target_api_name: str, current: str | None) -> str | None:
    """Derive a staging field name from the target field's API name.

    Keeps any role prefix already decided (Contact1_, Company_), strips the
    package or client namespace off the target, and normalizes casing. Returns
    None when the target name is not usable as-is.
    """
    if not target_api_name:
        return None
    local = target_api_name.split("__")[-2] + "__c" if target_api_name.count("__") > 1 \
        else target_api_name
    stem = local.replace("__c", "")
    if not stem or stem.lower() in ("name", "id"):
        return None
    stem = "_".join(w.capitalize() for w in stem.split("_") if w)

    prefix = ""
    for role in ("Contact1_", "Contact2_", "Company_"):
        if current and current.startswith(role):
            prefix = role
            break
    return f"{prefix}{stem}__c"


def _apply_form_option_fallback(proposal, entry) -> None:
    """When a new picklist-shaped field has no target values, use the form's.

    A form question that is a picklist or multiselect but whose target is not a
    picklist (a record-type router, say) would otherwise be created as a naked
    Text field, silently dropping every option. The form's own option labels are
    the right value set in that case.
    """
    if not proposal.disposition.startswith("create"):
        return
    # Only fill in a type we do not already have. A Checkbox/Number/Date target
    # has no picklist values, and must not be mistaken for "needs options".
    if proposal.proposed_type not in ("", "Text"):
        return
    options = [o["label"] for o in entry.get("options", []) if o["label"]]
    if not options:
        # No options and no known type: a plain free-text field.
        proposal.proposed_type = proposal.proposed_type or "Text"
        return
    if len(options) == 1:
        # A lone "Yes" is a checkbox, not a one-value picklist.
        proposal.proposed_type = "Checkbox"
        proposal.notes.append("Single yes/no option - staged as a Checkbox.")
        return
    is_multi = _looks_multiselect(entry)
    proposal.proposed_type = "MultiselectPicklist" if is_multi else "Picklist"
    proposal.proposed_values = options
    proposal.notes.append(
        f"Picklist values taken from the form's own options ({len(options)}); "
        "the target field is not itself a picklist."
    )


def _looks_multiselect(entry) -> bool:
    """A checkbox group is multi-select; a radio group is single."""
    classes = " ".join(entry.get("validation") or [])
    return "check" in (entry.get("label") or "").lower() or "checkbox" in classes


def _apply_condition_landing(proposal, entry, condition_drivers) -> None:
    """A field that drives visibility needs somewhere to land, mapped or not."""
    if proposal.field_id not in condition_drivers:
        return
    if proposal.disposition != "not_mapped":
        proposal.notes.append("Also drives conditional visibility on the form.")
        return
    proposal.disposition = "create_form_specific"
    proposal.staging_field = _suggest_name(proposal.label or proposal.field_id, None)
    proposal.staging_label = (proposal.label or proposal.field_id)[:40]
    proposal.confidence = "high"
    # Type from the form field: a lone toggle is a Checkbox, options make a
    # picklist, everything else is text. Landing runs after the shape pass, so
    # it has to infer its own type or it defaults to Text.
    _apply_form_option_fallback(proposal, entry)
    proposal.evidence = (
        "Never written to Salesforce by the old connector, but its answer decides "
        "what the applicant sees. The rebuilt form reads conditional logic off the "
        "submission record, so it needs a landing field regardless."
    )


# --- Mapping preference ------------------------------------------------------
#
# Objects the packaged conversion flows apply Form Template Mapping maps to.
# Any other target object needs its own mapping flow.
_MAPPED_OBJECTS = ("Account", "Contact", "Lead", "Case", "Opportunity")

# Role prefixes of the packaged Form Submission blocks, and the object whose form
# carries them in a paid org.
_ROLE_OBJECT = {"Contact1_": "Contact", "Contact2_": "Contact", "Company_": "Account"}

# Targets the Transform keeps even in a paid org.
_TRANSFORM_ONLY_TARGET = re.compile(r"record\s*type|campaign\s*member", re.I)


def _component_object(proposal: FieldProposal) -> str:
    """The source object whose form should carry this question, or ""."""
    for target in proposal.targets:
        sobject = target.split(".", 1)[0]
        if sobject in _MAPPED_OBJECTS:
            return sobject
    local = (proposal.staging_field or "").replace("FlowToolKit__", "")
    for prefix, sobject in _ROLE_OBJECT.items():
        if local.startswith(prefix):
            return sobject
    if local.startswith("Mailing_"):
        return "Contact"
    if proposal.proposed_type == "Address" or "address block" in proposal.evidence:
        return "Contact"
    return ""


def apply_mapping_preference(proposal: FieldProposal, edition: str | None,
                             calculated_ids: set[str] = frozenset()) -> None:
    """Set where the question is built and how its answer is converted.

    Paid: contact, organization and address questions go on a form on their
    source object with Form Template Mapping onto Form Submission fields, and
    convert through Apply Submission Field Maps. Calculated or combined values,
    record types and Campaign Members still use Transform rows. Free: a Form
    Submission form and Transform rows, the edition's existing approach.
    """
    if proposal.disposition in ("keep_target",):
        proposal.placement = "existing"
        proposal.conversion = "existing"
        return
    if proposal.disposition in ("skipped", "not_mapped") or not proposal.staging_field:
        proposal.placement = "form_submission" if proposal.disposition == "not_mapped" else ""
        proposal.conversion = ""
        return

    sobject = _component_object(proposal)
    converted = bool(proposal.targets) or bool(sobject)
    transform_only = (
        proposal.field_id in calculated_ids
        or proposal.origin == "component-computed"
        or any(_TRANSFORM_ONLY_TARGET.search(t) for t in proposal.targets)
    )

    if not sobject:
        proposal.placement = "form_submission"
        proposal.conversion = "transform" if proposal.targets else ""
        return
    if edition not in ("paid", "free"):
        proposal.placement = "edition_unknown"
        proposal.component_object = sobject
        proposal.conversion = ""
        proposal.notes.append(
            f"Where this question is built depends on the Flow Tool Kit edition: "
            f"paid orgs put it on a {sobject} form with Form Template Mapping, "
            "free orgs on a Form Submission form.")
        return
    if edition == "free":
        proposal.placement = "form_submission"
        proposal.conversion = "transform" if converted else ""
        return

    proposal.placement = "source_object"
    proposal.component_object = sobject
    if transform_only:
        proposal.conversion = "transform"
        proposal.notes.append(
            "Calculated, combined, record type or Campaign Member values keep a "
            "Transform row in the conversion flow, even in a paid org.")
    elif sobject in _MAPPED_OBJECTS:
        proposal.conversion = "submission_field_maps"
        proposal.notes.append(
            f"Build it on a {sobject} form and map the field to "
            f"{proposal.staging_field} on the Form Template Mapping tab; the "
            "packaged conversion flow applies the map.")
    else:
        proposal.conversion = "transform"


def _propose_compound_address(entry, hits, compound) -> FieldProposal:
    """Every part of one address lands in a single compound Address field."""
    api_name, part, block_label = compound[entry["id"]]
    targets = sorted({f"{n['sobject']}.{m['target_field_label']}" for n, m in hits})
    notes = [
        f"Part of the \"{block_label}\" address. Staged as the {part} component of "
        f"one compound Address field, not as a separate field.",
        "Compound Address was chosen because the client confirmed State and "
        "Country/Territory Picklists are on: its state and country accept codes "
        "only (MO, US), so every prefill and conversion mapping must supply codes.",
    ]
    if entry.get("options"):
        notes.append(
            f"The {len(entry['options'])} dropdown values are not migrated: the "
            "address component supplies state and country, and Salesforce address "
            "verification handles the rest."
        )
    return FieldProposal(
        field_id=entry["id"], label=entry["label"], section_path=entry["section_path"],
        origin="user-entered", disposition="create_org_canonical",
        staging_field=api_name, staging_label=f"{block_label} ({part})",
        confidence="high",
        evidence=(
            "Address block. One compound Address field covers every part, so this "
            "address needs a single new field rather than four."
        ),
        targets=targets, notes=notes, proposed_type="Address",
    )


def _propose_address(entry, hits, addresses, schema) -> FieldProposal:
    """Address parts resolve by position in their block, never by label match.

    Two addresses on one form share every label, so label matching cannot tell
    them apart - and matching both to the same field is worse than not matching
    at all, because the second silently overwrites the first.
    """
    local_name, block = addresses[entry["id"]]
    api_name = next(
        (f.api_name for f in schema.mappable() if f.local_name == local_name), None
    )
    targets = sorted({f"{n['sobject']}.{m['target_field_label']}" for n, m in hits})

    notes = [
        f"Part of the {block} address block, resolved by its position in that "
        "section rather than by its label."
    ]
    if entry.get("options"):
        notes.append(
            f"The {len(entry['options'])} dropdown values are deliberately NOT "
            "migrated: the rebuild uses an address section with Salesforce address "
            "verification, so no municipal list needs maintaining."
        )

    return FieldProposal(
        field_id=entry["id"], label=entry["label"], section_path=entry["section_path"],
        origin="user-entered",
        disposition="reuse_packaged" if api_name else "create_org_canonical",
        staging_field=api_name or local_name,
        staging_label=local_name.replace("__c", "").replace("_", " "),
        confidence="high",
        evidence=(
            "Address block field. The package ships two address blocks, so a form "
            "with two addresses needs no new fields."
        ),
        targets=targets, notes=notes,
    )


def _propose(entry, hits, schema, person_slots, label_to_ids, computed_ids,
             connector_is_authoritative: bool = True,
             section_role: str | None = None,
             match_label: str | None = None) -> FieldProposal:
    label = (entry["label"] or "").strip()
    targets = [f"{n['sobject']}.{m['target_field_label']}" for n, m in hits]
    notes: list[str] = []

    if len(label_to_ids.get(label, [])) > 1:
        others = [i for i in label_to_ids[label] if i != entry["id"]]
        notes.append(
            f'Label "{label}" is shared with {", ".join(others)} - the connector '
            "records sources by label, so which field each mapping reads must be "
            "confirmed by id."
        )

    # "Never mapped" is only a fact when a connector was actually read. A source
    # with no connector to read (a Google Form, a bare HTML page) would otherwise
    # report EVERY question as deliberately unmapped, which reads to a client as
    # a decision somebody made rather than evidence nobody has.
    if not hits and connector_is_authoritative:
        return FieldProposal(
            field_id=entry["id"], label=label, section_path=entry["section_path"],
            origin=_origin(entry, computed_ids),
            disposition="not_mapped", staging_field=None, staging_label=None,
            confidence="n/a",
            evidence="Collected by the form but never written to Salesforce by the connector.",
            targets=[], notes=notes + [
                "Decide whether the rebuild still needs this as a staging field."],
        )

    if not label:
        return FieldProposal(
            field_id=entry["id"], label="", section_path=entry["section_path"],
            origin=_origin(entry, computed_ids),
            disposition="ask_client", staging_field=None, staging_label=None,
            confidence="low",
            evidence=f"Mapped to {', '.join(sorted(set(targets)))} but the question has no label.",
            targets=sorted(set(targets)),
            notes=notes + ["Identify this question by id before building the mapping."],
        )

    # Prefer the role implied by the node this field feeds.
    role = next(
        (r for r in (_role_for_node(n, person_slots) for n, _ in hits) if r), None
    )
    wanted = _input_family(entry)
    if role:
        pool = schema.by_role(role)
    elif connector_is_authoritative:
        pool = [
            f for f in schema.mappable() if f.role is None and not f.is_generic_slot
        ]
    else:
        # With no connector there is no node to say WHICH person a question
        # describes, so the role-scoped pools cannot be chosen between. Search
        # all of them and make the client confirm the slot - matching "First
        # Name" against nothing is worse than matching it against Contact1 and
        # asking.
        pool = [f for f in schema.mappable() if not f.is_generic_slot]
        notes.append(
            "No connector exists for this source, so the person/role slot could "
            "not be derived from an object graph. Confirm the slot (Contact 1 vs "
            "Contact 2, etc.) before this mapping is built."
            + (f" Its section reads as {section_role}, so that slot was preferred."
               if section_role else "")
        )

    # What the question is about: its label (read with the question before it when bare), less the title words
    # of a section that reads as a person or organization, when something is left: those words say whose answer
    # it is ("Parent or Guardian Email" in "Parent or Guardian" is the second person's Email).
    asked = _tokens(match_label or label)
    if section_role:
        asked = (asked - _section_words(entry.get("section_path") or "")) or asked
    if match_label:
        notes.append(f'Matched as "{match_label}": the label alone says too little.')

    ranked = []
    for candidate in pool:
        score = _score(asked, _tokens(candidate.label))
        # A mapped target field name is often a better clue than the question text.
        for _, mapping in hits:
            score = max(score, _similarity(mapping["target_field_label"], candidate.label))
        # Demote only when the form actually states a conflicting type.
        if wanted and _field_family(candidate) != wanted:
            score *= 0.6  # plausible but type-mismatched; demote, never exclude
        # With no connector, the section's role breaks ties between role blocks.
        if section_role and candidate.role:
            score *= 1.1 if candidate.role == section_role else 0.9
        if score > 0:
            ranked.append((round(score, 6), _ROLE_PREFERENCE.get(candidate.role, 2), candidate))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2].api_name))
    best, best_score = (ranked[0][2], ranked[0][0]) if ranked else (None, 0.0)

    candidates = sorted(
        (c.local_name for c in pool if _score(asked, _tokens(c.label)) >= _MEDIUM)
    )[:5]

    if best and best_score >= _HIGH:
        # A strong LABEL match to a ROLE-BEARING field is still only a guess
        # about the role when no connector said which person this question
        # describes. "Email" matches Company_Email and Contact1_Email about
        # equally well, and picking silently merges two different people.
        role_is_a_guess = not connector_is_authoritative and best.role is not None
        proposal = FieldProposal(
            field_id=entry["id"], label=label, section_path=entry["section_path"],
            origin=_origin(entry, computed_ids),
            disposition="ask_client" if role_is_a_guess else "reuse_packaged",
            staging_field=best.api_name,
            staging_label=best.label,
            confidence="medium" if role_is_a_guess else "high",
            evidence=(
                f"Question text matches packaged field '{best.label}', but with no "
                f"connector to say which role this question belongs to, the "
                f"{best.role} slot is inferred from wording alone."
                if role_is_a_guess
                else f"Packaged {role or 'root'} field '{best.label}' matches this question."
            ),
            targets=sorted(set(targets)), candidates=candidates, notes=notes,
        )
        return _ranked(proposal, ranked, best_score)

    if best and best_score >= _MEDIUM:
        proposal = FieldProposal(
            field_id=entry["id"], label=label, section_path=entry["section_path"],
            origin=_origin(entry, computed_ids),
            disposition="ask_client", staging_field=best.api_name,
            staging_label=best.label, confidence="medium",
            evidence=(
                f"Closest packaged field is '{best.label}', but the match is not "
                "strong enough to merge two questions into one field on its own."
            ),
            targets=sorted(set(targets)), candidates=candidates, notes=notes,
        )
        return _ranked(proposal, ranked, best_score)

    disposition = "create_org_canonical" if role else "create_form_specific"
    proposal = FieldProposal(
        field_id=entry["id"], label=label, section_path=entry["section_path"],
        origin=_origin(entry, computed_ids),
        disposition=disposition, staging_field=_suggest_name(match_label or label, role),
        staging_label=label[:40], confidence="medium" if role else "high",
        evidence=(
            f"No packaged {role} field covers this; it is role-shaped, so name it "
            "for the role and every later form reuses it."
            if role else
            "No packaged field covers this and it has no reusable role."
        ),
        targets=sorted(set(targets)), candidates=candidates, notes=notes,
    )
    return _ranked(proposal, ranked, best_score)


def _ranked(proposal: FieldProposal, ranked: list, score: float) -> FieldProposal:
    """Keep the scored candidates on the proposal, so a collision can move it to its next best field."""
    proposal.match_score = score
    proposal.ranked = [(value, candidate) for value, _, candidate in ranked if value >= _MEDIUM]
    return proposal


def _suggest_name(label: str, role: str | None, word_limit: int = 5) -> str:
    """Build a field name from a question label.

    Split camelCase *before* lowercasing. Hidden FormAssembly fields are named
    like `ContactFound` and `IsPrefill`, and lowercasing first destroys the only
    word boundary they have, yielding `Contactfound__c`.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", label or "")
    words = [w.capitalize() for w in _WORD_RE.findall(spaced.lower())][:word_limit]
    stem = "_".join(words) or "Field"
    return f"{role}_{stem}__c" if role else f"{stem}__c"


_CONFIDENCE_RANK = {"high": 2, "medium": 1, "low": 0}


def resolve_collisions(proposals, schema=None) -> list[str]:
    """Give every question its own field: two questions that land on one field are a question, never a merge.

    The stronger claim keeps the field (an address placed by position, then the higher confidence and match score,
    then the earlier question). Each other claimant moves to its next best packaged field that nobody holds, or to
    a new field named for it, and becomes ``ask_client`` with a note naming the question it would have shared with.
    Returns one line per move.
    """
    claims: dict[str, list[FieldProposal]] = {}
    for proposal in proposals:
        if proposal.staging_field and proposal.disposition not in ("keep_target", "skipped", "not_mapped"):
            claims.setdefault(proposal.staging_field, []).append(proposal)
    taken = {p.staging_field for p in proposals if p.staging_field}
    if schema is not None:
        taken.update(f.local_name for f in schema.mappable())
    order = {id(p): i for i, p in enumerate(proposals)}
    moved: list[str] = []
    for field, claimants in claims.items():
        if len(claimants) < 2:
            continue
        claimants.sort(key=lambda p: (-("address block" in p.evidence.lower()), -_CONFIDENCE_RANK.get(p.confidence, 0),
                                      -p.match_score, order[id(p)]))
        keeper = claimants[0]
        for loser in claimants[1:]:
            free = next((c for _, c in loser.ranked if c.api_name not in taken and c.api_name != field), None)
            if free is not None:
                loser.staging_field, loser.staging_label = free.api_name, free.label
                where = f"the next closest packaged field, {free.label} ({free.api_name})"
            else:
                name = _suggest_name(loser.label or loser.field_id, None)
                suffix = 2
                while name in taken:
                    name = f"{_suggest_name(loser.label or loser.field_id, None)[:-3]}_{suffix}__c"
                    suffix += 1
                loser.staging_field, loser.staging_label = name, (loser.label or loser.field_id)[:40]
                where = f"a new field, {name}"
            taken.add(loser.staging_field)
            loser.disposition = "ask_client"
            loser.confidence = "low"
            loser.collided_with = keeper.field_id
            loser.notes.append(
                f"{field} is also the best match for {keeper.field_id} \"{keeper.label}\"; two questions never "
                f"share one field, so this one is proposed on {where}. Confirm which question {field} belongs to."
            )
            moved.append(f"{loser.field_id} \"{loser.label}\": {field} -> {loser.staging_field} "
                         f"(kept by {keeper.field_id})")
    return moved


def deduplicate_names(proposals, schema=None) -> list[str]:
    """Make every proposed field name unique. Returns the names it changed.

    Names are built by truncating a question to its first few words, so two
    genuinely different questions collide whenever they open the same way:
    "How long have you been participating?" and "How long have you been
    connected to this neighborhood?" both reduce to How_Long_Have_You_Been__c.

    This is the most expensive silent failure in the package. Two different
    questions land on one field, and every downstream count still looks
    plausible -- the plan says 61 fields, the emitter writes 58, and nothing
    says which three answers are about to overwrite each other.

    Collisions are resolved by lengthening the name until it is distinct, which
    keeps it readable, and only falling back to a numeric suffix when even the
    full label cannot separate them.
    """
    taken = set()
    if schema is not None:
        taken.update(field.api_name for field in schema.mappable())
        taken.update(field.local_name for field in schema.mappable())

    renamed: list[str] = []
    for proposal in proposals:
        if not proposal.disposition.startswith("create"):
            continue
        name = proposal.staging_field
        if not name:
            continue
        if name not in taken:
            taken.add(name)
            continue

        original = name
        role = None
        for candidate in ("Contact1", "Contact2", "Company"):
            if name.startswith(f"{candidate}_"):
                role = candidate
                break

        for word_limit in range(6, 13):
            longer = _suggest_name(proposal.label, role, word_limit)
            if longer not in taken:
                name = longer
                break
        else:
            suffix = 2
            stem = original.replace("__c", "")
            while f"{stem}_{suffix}__c" in taken:
                suffix += 1
            name = f"{stem}_{suffix}__c"

        taken.add(name)
        proposal.staging_field = name
        proposal.notes.append(
            f"Renamed from {original} -- that name was already taken by a "
            "different question, and merging the two would silently combine "
            "their answers in one field."
        )
        renamed.append(f"{original} -> {name} ({proposal.label})")
    return renamed


def summarize(proposals: list[FieldProposal]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proposal in proposals:
        counts[proposal.disposition] = counts.get(proposal.disposition, 0) + 1
    return dict(sorted(counts.items()))
