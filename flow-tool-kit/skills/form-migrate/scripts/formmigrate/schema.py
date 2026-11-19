"""Read the Form Submission field inventory: from the org, a describe file, ``force-app``, or a snapshot.

The Field Plan's first question is always "does a packaged field already cover
this?", so the packaged inventory has to be real metadata rather than a
hardcoded list - the package gains fields between releases, and a stale list
would quietly propose duplicates of fields that already exist.

Where the inventory comes from decides how far the plan can be trusted, so the
schema records it in ``source``:

    org            read live through the Salesforce CLI (``load_from_org``)
    describe-file  a describe saved from a Salesforce connector in chat (``load_from_describe_file``)
    force-app      field files retrieved into the project (``load_submission_schema``)
    snapshot       the packaged inventory shipped with this skill; may differ from
                   the installed version, so every proposal is marked "verify"

``load()`` picks the best one available. Only ``org`` and ``describe-file`` (and
``force-app`` when it holds the packaged fields) count as verified.

The org read pairs a describe with a ``FieldDefinition`` query because a
describe silently omits every field the running user cannot read: a field you
cannot see looks exactly like a field that does not exist. Fields found only by
the query are kept and flagged ``readable=False``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field as dataclass_field

_NAMESPACE = "FlowToolKit__"
_SUBMISSION_OBJECT = "FlowToolKit__Form_Submission__c"

_TAG_RE = re.compile(r"<(\w+)>([^<]*)</\1>")
_VALUE_RE = re.compile(r"<value>.*?<fullName>([^<]*)</fullName>.*?</value>", re.S)

# Role prefixes carved into the packaged schema. A form field that belongs to a
# role should land in that role's block rather than a new field.
_ROLE_PREFIXES = ("Contact1_", "Contact2_", "Company_", "Internal_", "Conversion_")

# Packaged fields that exist to be filled with anything - the escape hatch for
# questions with no natural role.
_GENERIC_PREFIXES = ("Long_Text_Question_", "Percent_", "File_Upload_")


@dataclass
class StagingField:
    """One field on ``Form_Submission__c``."""

    api_name: str
    label: str
    field_type: str
    picklist_values: list[str] = dataclass_field(default_factory=list)
    # False when the field exists but the user who read the schema cannot read it.
    readable: bool = True

    @property
    def local_name(self) -> str:
        """API name without the package namespace."""
        return self.api_name.replace(_NAMESPACE, "")

    @property
    def role(self) -> str | None:
        for prefix in _ROLE_PREFIXES:
            if self.local_name.startswith(prefix):
                return prefix.rstrip("_")
        return None

    @property
    def is_generic_slot(self) -> bool:
        return any(self.local_name.startswith(p) for p in _GENERIC_PREFIXES)

    @property
    def is_machinery(self) -> bool:
        """Conversion plumbing, internals and the standard fields (Name, the record number; OwnerId; the system
        stamps) are never mapping targets. A describe from the org lists the standard fields too."""
        return self.local_name.startswith(("Internal_", "Conversion_")) or not self.api_name.endswith("__c")


@dataclass
class SubmissionSchema:
    """The staging object's field inventory, packaged and subscriber alike."""

    fields: dict[str, StagingField] = dataclass_field(default_factory=dict)
    # Where the inventory came from; see the module docstring.
    source: str = "none"
    notes: list[str] = dataclass_field(default_factory=list)

    @property
    def verified(self) -> bool:
        """True when field names come from the org itself, not a snapshot."""
        return self.source in ("org", "describe-file", "force-app") and bool(self.fields)

    def packaged(self) -> list[StagingField]:
        return [f for f in self.fields.values() if f.api_name.startswith(_NAMESPACE)]

    def subscriber(self) -> list[StagingField]:
        return [f for f in self.fields.values() if not f.api_name.startswith(_NAMESPACE)]

    def mappable(self) -> list[StagingField]:
        """Everything a form field could legitimately be staged into."""
        return [f for f in self.fields.values() if not f.is_machinery]

    def by_role(self, role: str) -> list[StagingField]:
        return [f for f in self.mappable() if f.role == role]


def _parse_field_file(path: str) -> StagingField | None:
    """Read one ``.field-meta.xml``.

    Only the header - everything before ``<valueSet>`` - describes the field.
    Each picklist value repeats ``<fullName>`` and ``<label>``, so reading the
    whole document and taking the last match names the field after its final
    picklist value. That silently loses every picklist field, and worse, several
    collapse together when they happen to end on the same value ("Other").
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        raw = handle.read()

    header = raw.split("<valueSet>", 1)[0]
    values: dict[str, str] = {}
    for tag, value in _TAG_RE.findall(header):
        values.setdefault(tag, value)  # first occurrence wins

    api_name = values.get("fullName")
    if not api_name:
        return None

    return StagingField(
        api_name=api_name,
        label=values.get("label", ""),
        field_type=values.get("type", ""),
        picklist_values=_VALUE_RE.findall(raw),
    )


def load_object_fields(force_app_path: str, object_name: str) -> dict[str, StagingField]:
    """Load one object's fields, keyed by both API name and label.

    A new staging field should mirror the shape of the target field it will
    eventually feed - same type, same picklist values - so the staging record and
    the object it converts into stay in step. Reading the target's real metadata
    is the only way to do that without guessing.
    """
    fields_dir = os.path.join(
        force_app_path, "main", "default", "objects", object_name, "fields"
    )
    found: dict[str, StagingField] = {}
    if not os.path.isdir(fields_dir):
        return found

    for entry in sorted(os.listdir(fields_dir)):
        if not entry.endswith(".field-meta.xml"):
            continue
        parsed = _parse_field_file(os.path.join(fields_dir, entry))
        if not parsed:
            continue
        found[parsed.api_name] = parsed
        if parsed.label:
            # Labels are not unique on every object; first wins, which matches
            # how the connector displays them.
            found.setdefault(f"label:{parsed.label.strip().lower()}", parsed)
    return found


def load_submission_schema(force_app_path: str) -> SubmissionSchema:
    """Load every field defined on ``Form_Submission__c`` in the project."""
    objects_dir = os.path.join(force_app_path, "main", "default", "objects")
    fields_dir = os.path.join(objects_dir, _SUBMISSION_OBJECT, "fields")
    # The base package's own source names the object without its namespace; its
    # fields ARE the packaged ones, so they take the namespace a subscriber sees.
    package_dir = os.path.join(objects_dir, _SUBMISSION_OBJECT.replace(_NAMESPACE, ""), "fields")
    in_package_source = not os.path.isdir(fields_dir) and os.path.isdir(package_dir)
    schema = SubmissionSchema()
    if in_package_source:
        fields_dir = package_dir
    if not os.path.isdir(fields_dir):
        return schema

    for entry in sorted(os.listdir(fields_dir)):
        if not entry.endswith(".field-meta.xml"):
            continue
        parsed = _parse_field_file(os.path.join(fields_dir, entry))
        if parsed:
            if in_package_source and not parsed.api_name.startswith(_NAMESPACE):
                parsed.api_name = _NAMESPACE + parsed.api_name
            schema.fields[parsed.api_name] = parsed
    return schema


# --- Live org, describe files and the shipped snapshot -----------------------

# Describe API types onto the metadata type names the Field Plan compares.
_DESCRIBE_TYPES = {
    "string": "Text", "textarea": "TextArea", "boolean": "Checkbox",
    "picklist": "Picklist", "multipicklist": "MultiselectPicklist",
    "email": "Email", "phone": "Phone", "date": "Date", "datetime": "DateTime",
    "time": "Time", "double": "Number", "int": "Number", "long": "Number",
    "currency": "Currency", "percent": "Percent", "url": "Url",
    "reference": "Lookup", "address": "Address", "id": "Id",
}

# FieldDefinition.DataType text ("Text(255)", "Picklist (Multi-Select)") onto the same names.
_DATATYPE_PREFIXES = (
    ("Picklist (Multi-Select)", "MultiselectPicklist"), ("Picklist", "Picklist"),
    ("Long Text Area", "LongTextArea"), ("Rich Text Area", "Html"),
    ("Text Area", "TextArea"), ("Text", "Text"), ("Checkbox", "Checkbox"),
    ("Date/Time", "DateTime"), ("Date", "Date"), ("Time", "Time"),
    ("Email", "Email"), ("Phone", "Phone"), ("Number", "Number"),
    ("Currency", "Currency"), ("Percent", "Percent"), ("URL", "Url"),
    ("Lookup", "Lookup"), ("Master-Detail", "Lookup"), ("Address", "Address"),
    ("Formula", "Formula"),
)

_SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                         "form-submission-fields.json")


class OrgUnavailable(RuntimeError):
    """The Salesforce CLI is missing or the org could not be read."""


def _metadata_type(raw: str, long_length: bool = False) -> str:
    if raw in _DESCRIBE_TYPES:
        kind = _DESCRIBE_TYPES[raw]
        return "LongTextArea" if kind == "TextArea" and long_length else kind
    for prefix, kind in _DATATYPE_PREFIXES:
        if (raw or "").startswith(prefix):
            return kind
    return raw or ""


def fields_from_describe(describe) -> dict[str, StagingField]:
    """Read fields out of an sObject describe, in any of the shapes it arrives in.

    Accepts the REST describe (``{"fields": [...]}``), the Salesforce CLI's
    ``--json`` wrapper (``{"result": {"fields": [...]}}``), a bare list of field
    entries, or ``FieldDefinition`` query rows (``QualifiedApiName``, ``Label``,
    ``DataType``). A Salesforce connector in chat returns one of these; save it
    to a file and pass it here unchanged.
    """
    if isinstance(describe, dict):
        if "result" in describe:
            describe = describe["result"]
        if isinstance(describe, dict) and "records" in describe:
            describe = describe["records"]
        elif isinstance(describe, dict):
            describe = describe.get("fields", [])
    found: dict[str, StagingField] = {}
    for entry in describe or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("QualifiedApiName") or entry.get("api_name")
        if not name:
            continue
        raw_type = entry.get("type") or entry.get("DataType") or entry.get("field_type") or ""
        values = entry.get("picklistValues")
        if values is None:
            values = entry.get("picklist_values") or []
        found[name] = StagingField(
            api_name=name,
            label=entry.get("label") or entry.get("Label") or name,
            field_type=_metadata_type(raw_type, (entry.get("length") or 0) > 255),
            picklist_values=[
                (v.get("value") or v.get("label")) if isinstance(v, dict) else str(v)
                for v in values
                if not isinstance(v, dict) or v.get("active", True)
            ],
            readable=entry.get("readable", True),
        )
    return found


def _sf_json(args: list[str]) -> dict:
    if not shutil.which("sf"):
        raise OrgUnavailable("The Salesforce CLI (sf) is not installed here.")
    completed = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    try:
        payload = json.loads(completed.stdout or "{}")
    except ValueError as error:
        raise OrgUnavailable(f"sf {' '.join(args[:2])} did not return JSON.") from error
    if completed.returncode != 0 or payload.get("status", 0) != 0:
        raise OrgUnavailable(payload.get("message") or completed.stderr.strip() or "sf failed")
    return payload


def load_object_fields_from_org(sobject: str, org: str | None = None) -> dict[str, StagingField]:
    """One object's fields from the org, keyed by API name and by ``label:<label>``.

    The same shape ``load_object_fields`` returns from ``force-app``, so the
    Field Plan can shape a new field like its target from either source.
    """
    target = ["-o", org] if org else []
    described = fields_from_describe(
        _sf_json(["sobject", "describe", "-s", sobject, *target]))
    query = (f"SELECT QualifiedApiName, Label, DataType FROM FieldDefinition "
             f"WHERE EntityDefinition.QualifiedApiName = '{sobject}'")
    try:
        defined = fields_from_describe(
            _sf_json(["data", "query", "-q", query, *target]))
    except OrgUnavailable:
        defined = {}
    for name, entry in defined.items():
        if name not in described:
            entry.readable = False
            described[name] = entry
    found: dict[str, StagingField] = {}
    for parsed in described.values():
        found[parsed.api_name] = parsed
        if parsed.label:
            found.setdefault(f"label:{parsed.label.strip().lower()}", parsed)
    return found


def _schema_from(fields: dict[str, StagingField], source: str) -> SubmissionSchema:
    schema = SubmissionSchema(source=source)
    for name, entry in fields.items():
        if name.startswith("label:"):
            continue
        schema.fields[entry.api_name] = entry
    hidden = sorted(f.api_name for f in schema.fields.values() if not f.readable)
    if hidden:
        schema.notes.append(
            f"{len(hidden)} Form Submission fields exist but the user who read the "
            f"schema cannot read them (for example {', '.join(hidden[:3])}). They "
            "count as existing, so no duplicate is proposed; grant read access "
            "before a form uses them.")
    return schema


def load_from_org(org: str | None = None) -> SubmissionSchema:
    """The live Form Submission inventory, through the Salesforce CLI.

    ``org`` is an alias or username; ``None`` uses the CLI's default org.
    Raises ``OrgUnavailable`` when there is no CLI or no connection.
    """
    return _schema_from(load_object_fields_from_org(_SUBMISSION_OBJECT, org), "org")


def load_from_describe_file(path: str) -> SubmissionSchema:
    """The inventory from a describe a Salesforce connector returned, saved to ``path``."""
    with open(path, encoding="utf-8") as handle:
        return _schema_from(fields_from_describe(json.load(handle)), "describe-file")


def load_snapshot() -> SubmissionSchema:
    """The packaged inventory shipped with the skill. Never verified: names can
    differ from the installed version, so every proposal built on it says so."""
    with open(_SNAPSHOT, encoding="utf-8") as handle:
        data = json.load(handle)
    schema = _schema_from(fields_from_describe(data.get("fields", [])), "snapshot")
    schema.notes.append(
        "No org was read: Form Submission fields come from the snapshot shipped "
        f"with this skill ({data.get('generated_from', 'package source')}). Verify "
        "each name in the org before building.")
    return schema


def load(force_app: str | None = None, org: str | None = None,
         use_org: bool = False, describe_file: str | None = None) -> SubmissionSchema:
    """The best Form Submission inventory available, in order of trust.

    1. ``describe_file``: a describe saved from a Salesforce connector.
    2. The org through the CLI, when ``org`` is given or ``use_org`` is true.
    3. ``force_app``, when it holds the packaged fields. Subscriber-only field
       files are merged over the snapshot, and the result is unverified.
    4. The shipped snapshot, unverified.

    A failed org read is recorded in ``notes`` and falls through, never raised:
    the plan is still built, marked "verify".
    """
    notes: list[str] = []
    if describe_file:
        return load_from_describe_file(describe_file)
    if org or use_org:
        try:
            return load_from_org(org)
        except OrgUnavailable as error:
            notes.append(f"The org could not be read ({error}); using the next source.")
    if force_app:
        local = load_submission_schema(force_app)
        if local.packaged():
            local.source = "force-app"
            local.notes = notes
            return local
        if local.fields:
            merged = load_snapshot()
            merged.fields.update(local.fields)
            merged.source = "force-app+snapshot"
            merged.notes = notes + merged.notes
            return merged
    snapshot = load_snapshot()
    snapshot.notes = notes + snapshot.notes
    return snapshot
