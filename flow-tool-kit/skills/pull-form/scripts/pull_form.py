#!/usr/bin/env python3
"""Pull one Flow Tool Kit metadata form, and everything it needs, from an org into a Salesforce project.

Commands:
    python3 pull_form.py list [--target-org <org-alias>] [--catalog catalog.json] [--search <text>] [--json]
    python3 pull_form.py pull <form> [--target-org <org-alias>] [--catalog catalog.json] [--package-dir <path>]
                              [--with-dependencies] [--overwrite] [--clear-managers] [--clear-prefill]
                              [--allow-org-ids] [--dry-run] [--json]

<form> is the form's API name (with or without the FlowToolKit__ prefix) or its label as Form Builder shows it.

A pull takes the form record and every record that belongs to it: sections, fields, conditional logic rules, their
conditions, and the Form Labels its text uses with their translations. It lists what the form points at outside
itself (component forms placed in its sections, table forms, forms a Record Card button opens, its Form Object and
Theme, the image files it shows, the flows it runs and the Lightning web components its LWC sections load);
--with-dependencies pulls the org's own ones too. Files are retrieved with the Salesforce CLI into a staging folder inside the project,
checked, and only then copied into the project's own package directory (from sfdx-project.json).

Run it from inside the Salesforce project (any folder below sfdx-project.json). Python 3 standard library only.

Exit codes: 0 done; 1 error; 2 the name matched no form or several; 3 nothing to pull (a packaged form or a record
component); 4 files in the project would change (rerun with --overwrite once the person agrees); 5 org-specific Ids
that could not be fixed (rerun with --allow-org-ids to land them anyway).
"""
import argparse
import difflib
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys
import uuid

NS = "FlowToolKit__"
NS_NAME = "FlowToolKit"

# Every custom metadata type a pull can land, in report order.
TYPES = ["Form", "Form_Section", "Form_Field", "Form_Conditional_Logic", "Form_Conditional_Logic_Condition",
         "Form_Label", "Form_Label_Translation", "Form_Object", "Form_Theme"]
TYPE_LABELS = {"Form": "Form", "Form_Section": "Form Section", "Form_Field": "Form Field",
               "Form_Conditional_Logic": "Conditional Logic", "Form_Conditional_Logic_Condition": "Condition",
               "Form_Label": "Form Label", "Form_Label_Translation": "Form Label Translation",
               "Form_Object": "Form Object", "Form_Theme": "Theme", "ContentAsset": "Image file (Asset File)",
               "Flow": "Flow", "LightningComponentBundle": "Lightning web component"}

# Columns that point at another form: a component placed in a section, a section's table forms, a lookup's form.
FORM_REFS = {"Form_Section": ["formComponent__c", "Default_Table_Form__c", "Default_Table_Form_bulk__c"],
             "Form_Field": ["referenceFormComponent__c"]}
FORM_REF_WORDS = {"formComponent__c": "component placed in a section", "Default_Table_Form__c": "table form",
                  "Default_Table_Form_bulk__c": "bulk edit table form",
                  "referenceFormComponent__c": "form shown for a lookup"}

# Metadata outside custom metadata that a form shows or runs, named inside config__c (see outside_refs), and the
# folder the Salesforce CLI keeps each in.
FILE_TYPES = ["ContentAsset", "Flow", "LightningComponentBundle"]
FILE_FOLDERS = {"ContentAsset": "contentassets", "Flow": "flows", "LightningComponentBundle": "lwc"}
FOLDER_TYPES = {folder: kind for kind, folder in FILE_FOLDERS.items()}
# How Flow Tool Kit reads a typed image setting (flowFormHelper.resolveImageUrl): a bare name or asset:<name> is an
# Asset File, and so is a site's /file-asset/<name> address.
ASSET_NAME_RE = re.compile(r"^[A-Za-z]\w*$")
ASSET_ADDRESS_RE = re.compile(r"^(?:/[^/?#]+)*?/(?:file-asset-public|file-asset|sfsites/c/file-asset)/([^/?#]+)/?(?:[?#].*)?$",
                              re.I)
RECORD_TYPE_PREFIX = "012"

# Columns whose value names a record, object or field. An org Id here deploys nowhere else.
REFERENCE_COLUMNS = {"Form__c", "Form_Section__c", "conditionalLogic__c", "Form_Object__c", "Theme__c",
                     "Form_Label__c", "Object__c", "fieldName__c", "Alternative_Object__c", "Alternative_Field__c",
                     "formComponent__c", "Default_Table_Form__c", "Default_Table_Form_bulk__c",
                     "referenceFormComponent__c"}
# Long text that is checked separately (labels, managers, prefill), never for Ids.
FREE_TEXT_COLUMNS = {"config__c", "prefill__c", "Description__c", "Value__c"}

LABEL_RE = re.compile(r"\{\{\s*\$Label\.(\w+)\s*\}\}")
FILE_RE = re.compile(r"^(?:FlowToolKit__)?(Form(?:_Section|_Field|_Conditional_Logic_Condition|_Conditional_Logic"
                     r"|_Label_Translation|_Label|_Object|_Theme)?)\.(.+)\.md-meta\.xml$")
VALUES_RE = re.compile(r"(<values>\s*<field>)([^<]+)(</field>\s*)(<value(?:\s[^>]*)?/>|<value(?:\s[^>]*)?>.*?</value>)"
                       r"(\s*</values>)", re.S)
NO_COLUMN_RE = re.compile(r"No such column '([^']+)'|Didn't understand relationship '([^']+)'")
NIL = '<value xsi:nil="true"/>'
ID_SUFFIX = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"


class PullError(Exception):
    """A stop with a message for the person, and the exit code that goes with it."""

    def __init__(self, message, code=1, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


# ---- the Salesforce CLI ----------------------------------------------------------------------------------------------

def run_sf(args, cwd=None):
    """Run an sf command with --json and return its result, or raise PullError with the CLI's own message."""
    try:
        proc = subprocess.run(["sf"] + args + ["--json"], capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError:
        raise PullError("The Salesforce CLI (sf) is not installed or not on the PATH. Install it, sign in to the org "
                        "(sf org login web, or sf org login sfdx-url where no browser is available) and run this again.")
    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError:
        data = {}
    if not data:
        raise PullError((proc.stderr or out or "sf returned nothing").strip()[:600])
    if data.get("status", 1) != 0:
        raise PullError(str(data.get("message") or data.get("name") or "sf failed").strip())
    return data.get("result") or {}


def soql_str(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def soql_list(values):
    return "(" + ", ".join(soql_str(v) for v in sorted(values)) + ")"


def chunks(values, size=150):
    values = sorted(values)
    for i in range(0, len(values), size):
        yield values[i:i + size]


def rel(column, target="QualifiedApiName"):
    """A relationship column in a SELECT: formComponent__c -> FlowToolKit__formComponent__r.QualifiedApiName."""
    return f"{NS}{column[:-3]}__r.{target}"


def rel_value(record, column, target="QualifiedApiName"):
    node = record.get(f"{NS}{column[:-3]}__r")
    return node.get(target) if isinstance(node, dict) else None


def bare(name):
    """A record or field name without the package prefix."""
    name = name or ""
    return name[len(NS):] if name.startswith(NS) else name


class Org:
    """The org the form is pulled from. alias None means the Salesforce CLI's default org."""

    def __init__(self, alias=None, project=None, sf=run_sf):
        self.alias = alias
        self.project = project
        self.sf = sf
        self.dropped = []

    def args(self):
        return ["--target-org", self.alias] if self.alias else []

    def query(self, soql, tooling=False):
        result = self.sf(["data", "query", "--query", soql] + (["--use-tooling-api"] if tooling else []) + self.args(),
                         cwd=self.project)
        return result.get("records") or []

    def select(self, columns, rest, optional=()):
        """SELECT columns FROM rest. A column an older Flow Tool Kit version lacks is dropped when it is optional."""
        columns = list(columns)
        while True:
            try:
                return self.query(f"SELECT {', '.join(columns)} FROM {rest}")
            except PullError as error:
                match = NO_COLUMN_RE.search(str(error))
                missing = (match.group(1) or match.group(2)) if match else None
                gone = [c for c in columns if missing and c in optional and c.split(".")[0] == missing.split(".")[0]]
                if not gone:
                    raise
                for column in gone:
                    columns.remove(column)
                    if column not in self.dropped:
                        self.dropped.append(column)

    def info(self):
        rows = self.query("SELECT Id, Name, NamespacePrefix, IsSandbox FROM Organization")
        row = rows[0] if rows else {}
        alias = self.alias
        if not alias:
            try:
                found = self.sf(["config", "get", "target-org"], cwd=self.project)
                found = found if isinstance(found, list) else [found]
                alias = next((item.get("value") for item in found if isinstance(item, dict) and item.get("value")), None)
            except PullError:
                alias = None
        return {"id": row.get("Id"), "name": row.get("Name"), "namespace": row.get("NamespacePrefix"),
                "is_sandbox": row.get("IsSandbox"), "alias": alias or "the default org"}


# ---- the project -----------------------------------------------------------------------------------------------------

def find_project(start="."):
    here = pathlib.Path(start).resolve()
    for folder in [here] + list(here.parents):
        if (folder / "sfdx-project.json").is_file():
            return folder
    raise PullError("No sfdx-project.json in this folder or above it. Run the pull from inside the Salesforce project "
                    "the form should land in, or create one first (sf project generate --name <project-name>).")


def read_project(project):
    try:
        data = json.loads((project / "sfdx-project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PullError(f"Cannot read sfdx-project.json: {error}")
    dirs = [d for d in data.get("packageDirectories") or [] if isinstance(d, dict) and d.get("path")]
    if not dirs:
        raise PullError("sfdx-project.json lists no packageDirectories, so there is nowhere to put the files.")
    return data, dirs


def norm_dir(path):
    return str(pathlib.PurePosixPath(str(path).replace("\\", "/"))).strip("/")


def package_root(project, dirs, chosen=None):
    """The chosen (or default) package directory."""
    if chosen:
        match = [d for d in dirs if norm_dir(d["path"]) == norm_dir(chosen)]
        if not match:
            listed = ", ".join(d["path"] for d in dirs)
            raise PullError(f"--package-dir {chosen} is not one of the project's package directories ({listed}).")
        package = match[0]
    else:
        package = next((d for d in dirs if d.get("default")), dirs[0])
    return project / norm_dir(package["path"])


def destination(project, dirs, chosen=None):
    """The customMetadata folder new files go to: in the chosen (or default) package directory, the folder the
    project already keeps custom metadata in, else <package dir>/main/default/customMetadata."""
    root = package_root(project, dirs, chosen)
    existing = sorted(p for p in root.rglob("customMetadata") if p.is_dir()) if root.is_dir() else []
    if existing:
        with_forms = [p for p in existing if any(FILE_RE.match(f.name) for f in p.glob("*.md-meta.xml"))]
        return (with_forms or existing)[0]
    return root / "main" / "default" / "customMetadata"


def project_files(project, dirs):
    """Every Flow Tool Kit custom metadata file already in the project's package directories, by file name."""
    found = {}
    for package in dirs:
        root = project / norm_dir(package["path"])
        if not root.is_dir():
            continue
        for path in root.rglob("*.md-meta.xml"):
            if path.parent.name == "customMetadata" and FILE_RE.match(path.name):
                found.setdefault(path.name, []).append(path)
    return found


# ---- record files ----------------------------------------------------------------------------------------------------

class RecordFile:
    """One retrieved custom metadata record file, edited in place so the CLI's own formatting is kept."""

    def __init__(self, name, text):
        match = FILE_RE.match(name)
        if not match:
            raise ValueError(f"not a Flow Tool Kit record file: {name}")
        self.file_name = name
        self.type, self.name = match.groups()
        self.text = text
        self.changes = []

    def columns(self):
        """{column without prefix: (column as written, value or None)}."""
        out = {}
        for m in VALUES_RE.finditer(self.text):
            field, value = m.group(2), m.group(4)
            out[bare(field)] = (field, None if value.endswith("/>") else html.unescape(
                re.sub(r"^<value(?:\s[^>]*)?>|</value>$", "", value, flags=re.S)))
        return out

    def get(self, column):
        return self.columns().get(column, (None, None))[1]

    def label(self):
        found = re.search(r"<label>(.*?)</label>", self.text, re.S)
        return html.unescape(found.group(1)) if found else self.name

    def config(self):
        raw = self.get("config__c")
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def set(self, column, value):
        """Set a column to a string, or to nil with None. Keeps its xsi:type."""
        def swap(m):
            if bare(m.group(2)) != column:
                return m.group(0)
            if value is None:
                new = NIL
            else:
                kind = re.search(r'xsi:type="([^"]+)"', m.group(4))
                new = f'<value xsi:type="{kind.group(1) if kind else "xsd:string"}">{escape(value)}</value>'
            return m.group(1) + m.group(2) + m.group(3) + new + m.group(5)
        self.text = VALUES_RE.sub(swap, self.text)

    def drop_config_keys(self, columns):
        """Remove keys from config__c (the package reads config__c, so a cleared column must leave it too)."""
        data = self.config()
        if data is None:
            return False
        keys = [k for k in data if bare(k) in columns]
        if not keys:
            return False
        for key in keys:
            del data[key]
        colon = " : " if '" : ' in (self.get("config__c") or "") else ": "  # keep the org's own JSON style
        self.set("config__c", json.dumps(data, indent=2, ensure_ascii=False, separators=(",", colon)))
        return True


def escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            .replace("'", "&apos;"))


def checksum_ok(value):
    """True when an 18-character value ends in the case checksum Salesforce puts on record Ids."""
    suffix = ""
    for i in range(3):
        bits = sum(1 << j for j, c in enumerate(value[i * 5:i * 5 + 5]) if "A" <= c <= "Z")
        suffix += ID_SUFFIX[bits]
    return value[15:] == suffix


def looks_like_id(value):
    """A Salesforce record or field Id: 15 characters with digits in them, or 18 with a valid checksum."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", value):
        return False
    if len(value) == 18:
        return checksum_ok(value)
    return value.startswith("00N") or sum(c.isdigit() for c in value) >= 3


def id_parts(value):
    return [part for part in str(value).split(".") if looks_like_id(part)]


def fix_org_ids(record):
    """Replace org Ids in reference columns from the record's own config__c, which keeps the API names.

    Salesforce sometimes writes a field reference as an Id, or half-resolved as Object.00N..., and such a file
    deploys only in the org it came from. Returns (fixed, unfixed, warnings) lists of dicts."""
    fixed, unfixed, warnings = [], [], []
    config = record.config() or {}
    for column, (written, value) in record.columns().items():
        if value is None or column in FREE_TEXT_COLUMNS or not id_parts(value):
            continue
        where = {"file": record.file_name, "column": column, "value": value}
        is_reference = column in REFERENCE_COLUMNS or column.endswith(("FieldName__c", "FieldReference__c"))
        if not is_reference:
            warnings.append(dict(where, message="looks like a record Id, which means something only in this org "
                                                "and its sandboxes; check it before the form goes elsewhere"))
            continue
        saved = config.get(written, config.get(NS + column, config.get(column)))
        if isinstance(saved, str) and saved and not id_parts(saved):
            if not written.startswith(NS):
                saved = ".".join(bare(part) for part in saved.split("."))
            prefix, _, tail = value.rpartition(".")
            new = f"{prefix}.{saved.rpartition('.')[2]}" if prefix and not looks_like_id(prefix) else saved
            record.set(column, new)
            fixed.append(dict(where, new=new))
        else:
            unfixed.append(where)
    return fixed, unfixed, warnings


# ---- what a configuration names outside the form -------------------------------------------------------------------

def as_json(value, kind=dict):
    """A setting the package keeps as JSON text (or already parsed), or an empty dict or list."""
    if isinstance(value, kind):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return kind()
        return parsed if isinstance(parsed, kind) else kind()
    return kind()


def cfg(config, column):
    """A column's value inside config__c, which keeps the package's prefix on its keys."""
    return config.get(NS + column, config.get(column))


def typed_asset(value):
    """The Asset File a typed image setting names, or None for a merge field, a link or nothing."""
    text = str(value or "").strip()
    if not text or "{{" in text:
        return None
    tag = re.search(r"<img[^>]+src\s*=\s*[\"']([^\"']+)[\"']", text, re.I)
    if tag:
        text = html.unescape(tag.group(1))
    elif "<" in text:
        return None
    if text.lower().startswith("asset:"):
        text = text[6:].strip()
    address = ASSET_ADDRESS_RE.match(text)
    if address:
        return address.group(1)
    return text if ASSET_NAME_RE.match(text) else None


def outside_refs(kind, config):
    """What a section's or field's config__c shows or runs outside custom metadata, as (type, name, use).

    The keys are the ones Flow Tool Kit 5.4 renders from: a section's contentAssetName__c (image section),
    flowApiName__c (flow section, or a flow button on its text), lwcComponentName__c (LWC section), Banner__c
    (imageAsset, logoAsset, or an asset typed in image or logo) and Record_Card__c (imageAsset or a typed image, and
    buttons of type flow with flowApiName or recordForm with formQualifiedApiName); a field's picklistOptionSettings__c
    (each option's asset), or the older picklistVisualPickerOptions__c while the new one is empty."""
    refs = []

    def asset(name, use):
        if isinstance(name, str) and name.strip():
            refs.append(("ContentAsset", name.strip(), use))

    if kind == "Form_Field":
        settings = cfg(config, "picklistOptionSettings__c")
        options = as_json(settings) if settings else as_json(cfg(config, "picklistVisualPickerOptions__c"))
        for option in options.values():
            if isinstance(option, dict) and option.get("type") != "icon":
                asset(option.get("asset"), "a visual picker option image")
        return refs
    section_type = cfg(config, "sectionType__c")

    def shown(type_name):
        return not section_type or section_type == type_name

    if shown("imageSection"):
        asset(cfg(config, "contentAssetName__c"), "an image section")
    if shown("bannerSection"):
        banner = as_json(cfg(config, "Banner__c"))
        asset(banner.get("imageAsset"), "a banner background")
        asset(typed_asset(banner.get("image")), "a banner background")
        asset(banner.get("logoAsset"), "a banner logo")
        asset(typed_asset(banner.get("logo")), "a banner logo")
    if shown("recordCardSection"):
        card = as_json(cfg(config, "Record_Card__c"))
        asset(card.get("imageAsset"), "a Record Card image")
        asset(typed_asset(card.get("image")), "a Record Card image")
        for button in as_json(card.get("buttons"), list):
            if not isinstance(button, dict):
                continue
            if button.get("type") == "flow" and button.get("flowApiName"):
                refs.append(("Flow", button["flowApiName"], "a Record Card button"))
            if button.get("type") == "recordForm" and button.get("formQualifiedApiName"):
                refs.append(("Form", button["formQualifiedApiName"], "form a Record Card button opens"))
    flow = cfg(config, "flowApiName__c")
    if isinstance(flow, str) and flow.strip():
        refs.append(("Flow", flow.strip(), "a flow section" if section_type == "flowScreen" else "a flow button"))
    component = cfg(config, "lwcComponentName__c")
    if shown("lwcSection") and isinstance(component, str) and component.strip():
        refs.append(("LightningComponentBundle", component.strip(), "an LWC section"))
    return refs


def file_member(kind, written, org_namespace):
    """(name, namespace) of a file a configuration names: the retrieve member name for the org's own, as written for
    another package's. An LWC is written c:name, c/name or ns:name; an Asset File or Flow ns__Name."""
    if kind == "LightningComponentBundle":
        namespace, _, name = written.replace(":", "/").rpartition("/")
        namespace = None if namespace in ("", "c") else namespace
    else:
        head, sep, tail = written.partition("__")
        namespace, name = (head, tail) if sep and tail else (None, written)
    return (name, None) if own(namespace, org_namespace) else (written, namespace)


def find_lwr_support(org, names, org_namespace):
    """{LWC: [the org's own components that import it by name]}, or None when the org could not be searched.

    An LWC section's component is loaded with import() when the form runs, and an LWR site's publisher bundles only
    what some component on the site imports by name, so on an LWR site one of the org's own components has to."""
    try:
        rows = org.query("SELECT FilePath, Source FROM LightningComponentResource WHERE Format = 'js'", tooling=True)
    except PullError:
        return None
    prefixes = "|".join(re.escape(p) for p in ["c"] + ([org_namespace] if org_namespace else []))
    found = {name: [] for name in names}
    for row in rows:
        parts = (row.get("FilePath") or "").split("/")
        if len(parts) < 3 or parts[0] != "lwc":
            continue
        for name in names:
            static = rf"\bimport\s+(?:[^'\";]*?\s+from\s+)?['\"](?:{prefixes})/{re.escape(name)}['\"]"
            if parts[1] != name and parts[1] not in found[name] and re.search(static, row.get("Source") or ""):
                found[name].append(parts[1])
    return {name: sorted(found[name]) for name in names}


def describe_record_types(org, warnings):
    """Say which record type each Record Type Id in a warning is, and how to map it in another org."""
    ids = sorted({w["value"] for w in warnings if str(w["value"]).startswith(RECORD_TYPE_PREFIX)})
    if not ids:
        return
    try:
        rows = org.query(f"SELECT Id, DeveloperName, SobjectType FROM RecordType WHERE Id IN {soql_list(ids)}")
    except PullError:
        rows = []
    known = {row["Id"][:15]: row for row in rows if row.get("Id")}
    for warning in warnings:
        if not str(warning["value"]).startswith(RECORD_TYPE_PREFIX):
            continue
        row = known.get(warning["value"][:15])
        if row:
            warning["record_type"] = {"name": row.get("DeveloperName"), "object": row.get("SobjectType")}
            where = (f"SELECT Id FROM RecordType WHERE SobjectType = '{row.get('SobjectType')}' "
                     f"AND DeveloperName = '{row.get('DeveloperName')}'")
            what = f"is the Id of the {row.get('DeveloperName')} record type of {row.get('SobjectType')} in this org"
        else:
            where = "SELECT Id, DeveloperName FROM RecordType WHERE SobjectType = '<object>'"
            what = "is a Record Type Id"
        warning["message"] = (f"{what}. Record Type Ids differ between orgs that are not sandboxes of one another: "
                              f"find the same record type's Id in the target org ({where}) and put it in this "
                              "condition's value, in Form Builder after deploying or in the file before")


# ---- finding the form ------------------------------------------------------------------------------------------------

def own(namespace, org_namespace):
    return not namespace or namespace == org_namespace


def load_catalog(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PullError(f"Cannot read the catalog {path}: {error}")


def catalog_match(catalog, wanted):
    """Components in org-catalog's catalog.json that the name or label could mean, best match first."""
    comps = catalog.get("components") or []
    key = bare(wanted).lower()
    for test in (lambda c: bare(c.get("name")).lower() == key,
                 lambda c: any(bare(r).lower() == key for r in c.get("refs") or [c.get("ref") or ""]),
                 lambda c: (c.get("label") or "").lower() == wanted.lower(),
                 lambda c: key in bare(c.get("name")).lower() or wanted.lower() in (c.get("label") or "").lower()):
        hits = [c for c in comps if test(c)]
        if hits:
            return hits
    return []


def resolve(org, wanted, org_namespace, catalog=None):
    """The form's QualifiedApiName, label and namespace, or a PullError with code 2 or 3."""
    if catalog:
        hits = catalog_match(catalog, wanted)
        records = [c for c in hits if c.get("kind") == "record"]
        metadata = [c for c in hits if c.get("kind") != "record"]
        if records and not metadata:
            c = records[0]
            raise PullError(f"{c.get('label') or c.get('name')} is a record component (a Form Component record), "
                            "not a metadata form. A record component moves as JSON: the Export action on its "
                            "record, then Import Form Component in the other org.", code=3)
        if len(metadata) > 1 and len({bare(c.get("name")) for c in metadata}) > 1:
            raise PullError(f"'{wanted}' matches several forms in the catalog; name one.", code=2,
                            details={"candidates": [{"name": c.get("name"), "label": c.get("label"),
                                                     "object": c.get("object")} for c in metadata]})
        if metadata:
            wanted = metadata[0].get("name") or wanted
    columns = ["QualifiedApiName", "DeveloperName", "MasterLabel", "NamespacePrefix", f"{NS}Delete__c"]
    rows = org.select(columns, f"{NS}Form__mdt WHERE DeveloperName = {soql_str(bare(wanted))}",
                      optional=(f"{NS}Delete__c",))
    if not rows:  # custom metadata SOQL takes no OR, so the label is a second query
        rows = org.select(columns, f"{NS}Form__mdt WHERE MasterLabel = {soql_str(wanted)}",
                          optional=(f"{NS}Delete__c",))
    if len(rows) > 1:
        mine = [r for r in rows if own(r.get("NamespacePrefix"), org_namespace)]
        rows = mine if len(mine) == 1 else rows
    if len(rows) > 1:
        raise PullError(f"'{wanted}' matches several forms; name one by its API name.", code=2,
                        details={"candidates": [{"name": r["QualifiedApiName"], "label": r.get("MasterLabel")}
                                                for r in rows]})
    if not rows:
        record = None
        try:
            found = org.query(f"SELECT Id, Name FROM {NS}Form_Component__c "
                              f"WHERE {NS}QualifiedApiName__c = {soql_str(bare(wanted))} LIMIT 1")
            record = found[0] if found else None
        except PullError:
            record = None
        if record:
            raise PullError(f"{record.get('Name') or wanted} is a record component (a Form Component record), not a "
                            "metadata form. A record component moves as JSON: the Export action on its record, then "
                            "Import Form Component in the other org.", code=3)
        raise PullError(f"No metadata form named '{wanted}' in this org. List the forms with the list command.",
                        code=2)
    row = rows[0]
    if not own(row.get("NamespacePrefix"), org_namespace):
        raise PullError(f"{row.get('MasterLabel')} ({row['QualifiedApiName']}) ships with Flow Tool Kit. Every org "
                        "with the package already has it, and a packaged form cannot be deployed as your own. To "
                        "change it, build your own component from it.", code=3)
    return row


# ---- planning what to retrieve ---------------------------------------------------------------------------------------

class Plan:
    def __init__(self):
        self.members = {t: set() for t in TYPES}
        self.forms = []            # forms planned, the asked one first
        self.dependencies = {}     # (type, name) -> {"type", "name", "packaged", "uses": set}
        self.labels_missing = set()
        self.labels_packaged = set()
        self.files = {t: set() for t in FILE_TYPES}  # the org's own files to retrieve beside the records
        self.lwr_support = {}      # an LWC section's component -> the org's own components that import it

    def add_dependency(self, kind, name, packaged, use, namespace=None):
        entry = self.dependencies.setdefault((kind, name), {"type": kind, "name": name, "packaged": packaged,
                                                            "uses": set()})
        if packaged and namespace and namespace != NS_NAME:
            entry["namespace"] = namespace
        entry["uses"].add(use)

    def count(self):
        return sum(len(v) for v in self.members.values())


def plan_form(org, qname, org_namespace, plan):
    """Add one form and its own records to the plan. Returns the org's own forms and records it points at."""
    q = soql_str(qname)
    where = f"WHERE {NS}Form__r.QualifiedApiName = {q}"
    pointers = []  # (type, name) of the org's own records outside this form
    texts = []

    def note(kind, name, namespace, use):
        if not name or (kind == "Form" and name == qname):
            return
        packaged = not own(namespace, org_namespace)
        plan.add_dependency(kind, name, packaged, use, namespace)
        if not packaged:
            pointers.append((kind, name))

    optional_form = [rel("Theme__c"), rel("Theme__c", "NamespacePrefix")]
    form_cols = ["QualifiedApiName", f"{NS}config__c", rel("Form_Object__c"), rel("Form_Object__c", "NamespacePrefix")]
    for row in org.select(form_cols + optional_form, f"{NS}Form__mdt WHERE QualifiedApiName = {q}",
                          optional=optional_form):
        texts.append(row.get(f"{NS}config__c"))
        note("Form_Object", rel_value(row, "Form_Object__c"), rel_value(row, "Form_Object__c", "NamespacePrefix"),
             "the object it is built on")
        note("Form_Theme", rel_value(row, "Theme__c"), rel_value(row, "Theme__c", "NamespacePrefix"), "its theme")
    plan.members["Form"].add(qname)

    rules = set()
    named_forms = {}  # forms a configuration names (a Record Card button), checked below -> their uses
    for kind in ("Form_Section", "Form_Field"):
        refs = FORM_REFS[kind] + (["Theme__c"] if kind == "Form_Section" else [])
        optional = [c for r in refs for c in (rel(r), rel(r, "NamespacePrefix"))] + [rel("conditionalLogic__c")]
        if kind == "Form_Section":
            optional.append(f"{NS}contentAssetName__c")
        rows = org.select(["QualifiedApiName", f"{NS}config__c"] + optional, f"{NS}{kind}__mdt {where}",
                          optional=optional)
        for row in rows:
            plan.members[kind].add(row["QualifiedApiName"])
            texts.append(row.get(f"{NS}config__c"))
            if rel_value(row, "conditionalLogic__c"):
                rules.add(rel_value(row, "conditionalLogic__c"))
            for column in refs:
                kind_of = "Form_Theme" if column == "Theme__c" else "Form"
                use = "a section theme" if column == "Theme__c" else FORM_REF_WORDS[column]
                note(kind_of, rel_value(row, column), rel_value(row, column, "NamespacePrefix"), use)
            config = as_json(row.get(f"{NS}config__c"))
            if row.get(f"{NS}contentAssetName__c") and not cfg(config, "contentAssetName__c"):
                config[f"{NS}contentAssetName__c"] = row[f"{NS}contentAssetName__c"]
            for kind_of, written, use in outside_refs(kind, config):
                if kind_of == "Form":
                    named_forms.setdefault(written, set()).add(use)
                else:
                    name, namespace = file_member(kind_of, written, org_namespace)
                    note(kind_of, name, namespace, use)

    found = {}
    for batch in chunks(named_forms):
        for row in org.select(["QualifiedApiName", "NamespacePrefix"],
                              f"{NS}Form__mdt WHERE QualifiedApiName IN {soql_list(batch)}"):
            found[row["QualifiedApiName"]] = row.get("NamespacePrefix")
    for name, uses in sorted(named_forms.items()):
        for use in sorted(uses):
            if name in found:
                note("Form", name, found[name], use)
            elif name != qname:  # not a metadata form here: a record component, or one deleted since
                plan.add_dependency("Form", name, False, use)
                plan.dependencies[("Form", name)]["missing"] = True

    for row in org.select(["QualifiedApiName", f"{NS}config__c"], f"{NS}Form_Conditional_Logic__mdt {where}"):
        rules.add(row["QualifiedApiName"])
        texts.append(row.get(f"{NS}config__c"))
    plan.members["Form_Conditional_Logic"].update(rules)

    conditions = org.select(["QualifiedApiName", f"{NS}config__c"], f"{NS}Form_Conditional_Logic_Condition__mdt {where}")
    for batch in chunks(rules):  # a condition may name only its rule, so ask by rule too (no OR in this SOQL)
        conditions += org.select(["QualifiedApiName", f"{NS}config__c"],
                                 f"{NS}Form_Conditional_Logic_Condition__mdt "
                                 f"WHERE {NS}conditionalLogic__r.QualifiedApiName IN {soql_list(batch)}")
    for row in conditions:
        plan.members["Form_Conditional_Logic_Condition"].add(row["QualifiedApiName"])
        texts.append(row.get(f"{NS}config__c"))

    plan_labels(org, texts, org_namespace, plan)
    return pointers


def plan_labels(org, texts, org_namespace, plan):
    names = {bare(n) for t in texts if t for n in LABEL_RE.findall(t)}
    names -= {bare(n) for n in plan.members["Form_Label"]} | plan.labels_packaged
    if not names:
        return
    found = []
    for batch in chunks(names):
        found += org.select(["QualifiedApiName", "DeveloperName", "NamespacePrefix"],
                            f"{NS}Form_Label__mdt WHERE DeveloperName IN {soql_list(batch)}")
    mine = set()
    for row in found:
        if own(row.get("NamespacePrefix"), org_namespace):
            mine.add(row["QualifiedApiName"])
        else:
            plan.labels_packaged.add(row["DeveloperName"])
    plan.labels_missing |= names - {r["DeveloperName"] for r in found}
    plan.members["Form_Label"] |= mine
    for batch in chunks(mine):
        for row in org.select(["QualifiedApiName"], f"{NS}Form_Label_Translation__mdt "
                                                    f"WHERE {NS}Form_Label__r.QualifiedApiName IN {soql_list(batch)}"):
            plan.members["Form_Label_Translation"].add(row["QualifiedApiName"])


def build_plan(org, form, org_namespace, with_dependencies=False):
    plan = Plan()
    queue, seen = [form], set()
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        plan.forms.append(name)
        for kind, target in plan_form(org, name, org_namespace, plan):
            if not with_dependencies:
                continue
            if kind == "Form":
                queue.append(target)
            elif kind in FILE_TYPES:
                plan.files[kind].add(target)
            else:
                plan.members[kind].add(target)
    sections_lwc = sorted(name for (kind, name), dep in plan.dependencies.items()
                          if kind == "LightningComponentBundle" and not dep["packaged"])
    if sections_lwc:
        plan.lwr_support = find_lwr_support(org, sections_lwc, org_namespace)
        if with_dependencies:
            plan.files["LightningComponentBundle"].update(n for names in (plan.lwr_support or {}).values() for n in names)
    pulled = {("Form", f) for f in plan.forms} | {(k, n) for k in ("Form_Object", "Form_Theme")
                                                   for n in plan.members[k]} | {(k, n) for k in FILE_TYPES
                                                                                for n in plan.files[k]}
    for key in list(plan.dependencies):
        if key in pulled:
            del plan.dependencies[key]
    return plan


# ---- retrieve, check, land -------------------------------------------------------------------------------------------

def manifest_xml(members, api_version=None, files=None):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<Package xmlns="http://soap.sforce.com/2006/04/metadata">',
             "    <types>"]
    for kind in TYPES:
        for name in sorted(members.get(kind) or ()):
            lines.append(f"        <members>{escape(NS + kind)}.{escape(name)}</members>")
    lines += ["        <name>CustomMetadata</name>", "    </types>"]
    for kind in FILE_TYPES:
        names = sorted((files or {}).get(kind) or ())
        if names:
            lines += ["    <types>"] + [f"        <members>{escape(n)}</members>" for n in names]
            lines += [f"        <name>{kind}</name>", "    </types>"]
    if api_version:
        lines.append(f"    <version>{escape(api_version)}</version>")
    lines += ["</Package>", ""]
    return "\n".join(lines)


def retrieve(org, project, plan, stage, api_version=None):
    """Retrieve every planned record and file into the staging folder.

    Returns ({file name: RecordFile}, {path from the type's folder, such as flows/X.flow-meta.xml: bytes}, failures)."""
    stage.mkdir(parents=True)
    manifest = stage / "package.xml"
    manifest.write_text(manifest_xml(plan.members, api_version, plan.files), encoding="utf-8")
    out = stage / "out"
    result = org.sf(["project", "retrieve", "start", "--manifest", str(manifest.relative_to(project)),
                     "--output-dir", str(out.relative_to(project)), "--wait", "30"] + org.args(), cwd=project)
    entries = result.get("files") or [] if isinstance(result, dict) else []
    failures = [{"member": e.get("fullName"), "error": e.get("error")} for e in entries if e.get("state") == "Failed"]
    records, files = {}, {}
    for path in sorted(out.rglob("*")) if out.is_dir() else []:
        if not path.is_file():
            continue
        if FILE_RE.match(path.name):
            records[path.name] = RecordFile(path.name, path.read_text(encoding="utf-8"))
            continue
        parts = path.relative_to(out).parts
        start = next((i for i, part in enumerate(parts[:-1]) if part in FOLDER_TYPES), None)
        if start is not None:
            files["/".join(parts[start:])] = path.read_bytes()
    return records, files, failures


def review(records, plan, clear_managers=False, clear_prefill=False):
    """Fix and inspect the retrieved files before anything lands. Returns the report sections."""
    report = {"fixed_ids": [], "unfixed_ids": [], "id_warnings": [], "attention": [], "soft_deleted": {},
              "labels_not_pulled": []}
    used_labels = set()
    for record in records.values():
        fixed, unfixed, warnings = fix_org_ids(record)
        report["fixed_ids"] += fixed
        report["unfixed_ids"] += unfixed
        report["id_warnings"] += warnings
        used_labels |= {bare(n) for n in LABEL_RE.findall(html.unescape(record.text))}
        if record.get("Delete__c") == "true":
            report["soft_deleted"][record.type] = report["soft_deleted"].get(record.type, 0) + 1
        if record.type != "Form":
            continue
        managers = [m for m in re.split(r"[;,\s]+", record.get("Form_Managers__c") or "") if m]
        if managers:
            if clear_managers:
                record.set("Form_Managers__c", None)
                record.drop_config_keys({"Form_Managers__c"})
                report["attention"].append(f"{record.name}: cleared Form Managers ({len(managers)} user Ids).")
            else:
                report["attention"].append(
                    f"{record.name}: Form Managers lists {len(managers)} user Id(s). They name the same people only "
                    "in this org and sandboxes copied from it; deploying the file elsewhere writes these Ids there. "
                    "Clear them with --clear-managers when the target is not this org's family.")
        if (record.get("prefill__c") or "").strip():
            if clear_prefill:
                record.set("prefill__c", None)
                record.drop_config_keys({"prefill__c"})
                report["attention"].append(f"{record.name}: cleared the Form Builder preview data (prefill).")
            else:
                report["attention"].append(
                    f"{record.name}: carries Form Builder preview data (prefill), which can hold names or text copied "
                    "from a real record. Read it, and clear it with --clear-prefill before the files go into a "
                    "shared repository.")
        if not (record.get("Description__c") or "").strip():
            report["attention"].append(f"{record.name}: has no Description. Add one in Form Builder (what the "
                                       "form collects and where it is used) so whoever deploys it knows what it is.")
    pulled = {bare(n) for n in plan.members["Form_Label"]}
    report["labels_not_pulled"] = sorted(used_labels - pulled - plan.labels_packaged - plan.labels_missing)
    return report


def file_places(project, dirs, tail):
    """Where the project already holds a file, by its path from the type's folder (flows/X.flow-meta.xml)."""
    found = []
    for package in dirs:
        root = project / norm_dir(package["path"])
        if root.is_dir():
            found += [p for p in root.rglob(pathlib.PurePosixPath(tail).name) if p.as_posix().endswith("/" + tail)]
    return sorted(found)


def file_target(root, dest, tail):
    """Where a new file goes: the type's folder the package directory already has, else beside customMetadata."""
    folder, _, rest = tail.partition("/")
    existing = sorted(p for p in root.rglob(folder) if p.is_dir()) if root.is_dir() else []
    return (existing[0] if existing else dest.parent / folder) / rest


def land(records, project, dirs, dest, overwrite=False, dry_run=False, pulled_forms=(), pulled_rules=(),
         pulled_labels=(), files=None, root=None):
    """Copy staged files into the project. Changed files need overwrite; nothing is ever deleted."""
    existing = project_files(project, dirs)
    plan = {"new": [], "updated": [], "unchanged": [], "conflicts": [], "duplicates": [], "only_in_project": [],
            "diffs": {}}
    writes = []
    for name, record in sorted(records.items()):
        places = existing.get(name) or []
        if len(places) > 1:
            plan["duplicates"].append({"file": name, "paths": [str(p.relative_to(project)) for p in places]})
            continue
        target = places[0] if places else dest / name
        rel_target = str(target.relative_to(project))
        if not places:
            plan["new"].append(rel_target)
        elif target.read_text(encoding="utf-8") == record.text:
            plan["unchanged"].append(rel_target)
            continue
        else:
            plan["updated"].append(rel_target)
            plan["diffs"][rel_target] = diff(target.read_text(encoding="utf-8"), record.text)
            if not overwrite:
                plan["conflicts"].append(rel_target)
        writes.append((target, record.text))
    for tail, data in sorted((files or {}).items()):
        places = file_places(project, dirs, tail)
        if len(places) > 1:
            plan["duplicates"].append({"file": tail, "paths": [str(p.relative_to(project)) for p in places]})
            continue
        target = places[0] if places else file_target(root or dest.parent, dest, tail)
        rel_target = str(target.relative_to(project))
        if not places:
            plan["new"].append(rel_target)
        elif target.read_bytes() == data:
            plan["unchanged"].append(rel_target)
            continue
        else:
            plan["updated"].append(rel_target)
            try:
                plan["diffs"][rel_target] = diff(target.read_text(encoding="utf-8"), data.decode("utf-8"))
            except UnicodeDecodeError:
                plan["diffs"][rel_target] = ["(a binary file: the org's copy differs)"]
            if not overwrite:
                plan["conflicts"].append(rel_target)
        writes.append((target, data))
    forms = {bare(f) for f in pulled_forms}
    rules = {bare(r) for r in pulled_rules}
    labels = {bare(n) for n in pulled_labels}
    for name, places in sorted(existing.items()):
        if name in records:
            continue
        for path in places:
            try:
                local = RecordFile(name, path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            owner = (local.type == "Form" and bare(local.name) in forms) \
                or bare(local.get("Form__c") or "") in forms \
                or (local.type == "Form_Conditional_Logic_Condition" and bare(local.get("conditionalLogic__c") or "") in rules) \
                or (local.type == "Form_Label_Translation" and bare(local.get("Form_Label__c") or "") in labels)
            if owner:
                plan["only_in_project"].append(str(path.relative_to(project)))
    if plan["duplicates"]:
        raise PullError("The project holds more than one copy of some of these files, so it is unclear which to "
                        "update. Keep one copy of each and pull again.", code=1, details={"duplicates": plan["duplicates"]})
    if plan["conflicts"] or dry_run:
        return plan
    for target, content in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
    return plan


def diff(old, new, limit=40):
    """The lines that differ, project first and org second, at most limit lines."""
    lines = [line.rstrip("\n") for line in difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                                 "project", "org", n=0)]
    return lines[:limit] + ([f"... {len(lines) - limit} more lines"] if len(lines) > limit else [])


def counts(records, files=None):
    out = {}
    for record in records.values():
        out[record.type] = out.get(record.type, 0) + 1
    members = {}
    for tail in files or {}:
        folder, _, rest = tail.partition("/")
        kind = FOLDER_TYPES[folder]
        members.setdefault(kind, set()).add(rest.split("/")[0] if kind == "LightningComponentBundle"
                                            else rest.split(".")[0])
    out.update({kind: len(names) for kind, names in members.items()})
    return {TYPE_LABELS[t]: out[t] for t in TYPES + FILE_TYPES if t in out}


def pull(args, sf=run_sf, cwd="."):
    project = find_project(cwd)
    data, dirs = read_project(project)
    dest = destination(project, dirs, args.package_dir)
    root = package_root(project, dirs, args.package_dir)
    org = Org(args.target_org, str(project), sf)
    info = org.info()
    catalog = load_catalog(args.catalog) if args.catalog else None
    notes = []
    if catalog and (catalog.get("org") or {}).get("id") not in (None, info["id"]):
        notes.append("The catalog was taken from another org than the one being pulled from; names were checked "
                     "against this org.")
    form = resolve(org, args.form, info["namespace"], catalog)
    if str(form.get(f"{NS}Delete__c")).lower() == "true":
        notes.append(f"{form['MasterLabel']} is marked deleted in Form Builder.")
    plan = build_plan(org, form["QualifiedApiName"], info["namespace"], args.with_dependencies)
    stage = project / f".pull-form-{uuid.uuid4().hex[:8]}"
    try:
        records, files, failures = retrieve(org, project, plan, stage, data.get("sourceApiVersion"))
        if not any(r.type == "Form" for r in records.values()):
            raise PullError(f"The org returned no file for {form['QualifiedApiName']}.", details={"failures": failures})
        report = review(records, plan, args.clear_managers, args.clear_prefill)
        describe_record_types(org, report["id_warnings"])
        if report["unfixed_ids"] and not args.allow_org_ids:
            raise PullError("Some references hold org Ids that the record's own configuration cannot replace, so "
                            "these files would deploy only to this org. Nothing was copied into the project. Open "
                            "each field in Form Builder, choose the field again, save, and pull again.", code=5,
                            details={"unfixed_ids": report["unfixed_ids"]})
        landed = land(records, project, dirs, dest, args.overwrite, args.dry_run, plan.forms,
                      plan.members["Form_Conditional_Logic"], plan.members["Form_Label"], files, root)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    result = {
        "form": {"name": form["QualifiedApiName"], "label": form.get("MasterLabel")},
        "org": info,
        "project": str(project),
        "destination": str(dest.relative_to(project)),
        "forms": plan.forms,
        "records": counts(records, files),
        "files": landed,
        "landed": not landed["conflicts"] and not args.dry_run,
        "dry_run": bool(args.dry_run),
        "dependencies": [dict(d, uses=sorted(d["uses"])) for d in plan.dependencies.values()],
        "retrieved_files": {kind: sorted(names) for kind, names in plan.files.items() if names},
        "lwr_support": plan.lwr_support,
        "labels_missing": sorted(plan.labels_missing),
        "retrieve_failures": failures,
        "dropped_columns": org.dropped,
        "notes": notes,
        **report,
    }
    return result, (4 if landed["conflicts"] else 0)


def list_forms(args, sf=run_sf, cwd="."):
    if args.catalog:
        catalog = load_catalog(args.catalog)
        comps = [c for c in catalog.get("components") or [] if c.get("kind") == "metadata" and not c.get("packaged")]
        rows = [{"name": c.get("name"), "label": c.get("label"), "object": c.get("object"),
                 "templates": c.get("templates", 0), "active": c.get("active")} for c in comps]
        skipped = sum(1 for c in catalog.get("components") or [] if c.get("kind") == "record")
        source = "catalog"
    else:
        project = None
        try:
            project = str(find_project(cwd))
        except PullError:
            pass
        org = Org(args.target_org, project, sf)
        info = org.info()
        cols = ["QualifiedApiName", "MasterLabel", "NamespacePrefix", f"{NS}Active__c", f"{NS}Delete__c",
                rel("Form_Object__c")]
        optional = [f"{NS}Active__c", f"{NS}Delete__c"]
        found = org.select(cols, f"{NS}Form__mdt ORDER BY MasterLabel", optional=optional)
        rows = [{"name": r["QualifiedApiName"], "label": r.get("MasterLabel"),
                 "object": bare(rel_value(r, "Form_Object__c") or ""), "active": r.get(f"{NS}Active__c")}
                for r in found if own(r.get("NamespacePrefix"), info["namespace"])
                and str(r.get(f"{NS}Delete__c")).lower() != "true"]
        skipped = None
        source = "org"
    if args.search:
        needle = args.search.lower()
        rows = [r for r in rows if needle in (r["name"] or "").lower() or needle in (r["label"] or "").lower()]
    return {"source": source, "forms": rows, "record_components": skipped}


# ---- output ----------------------------------------------------------------------------------------------------------

def print_pull(result):
    form, org, files = result["form"], result["org"], result["files"]
    verb = "Would pull" if result["dry_run"] or files["conflicts"] else "Pulled"
    print(f"{verb} {form['label']} ({form['name']}) from {org['alias']} ({org.get('name') or 'org'}).")
    if len(result["forms"]) > 1:
        print("Forms: " + ", ".join(result["forms"]))
    print("Records: " + ", ".join(f"{k} {v}" for k, v in result["records"].items()))
    print(f"Into {result['destination']}: {len(files['new'])} new, {len(files['updated'])} updated, "
          f"{len(files['unchanged'])} unchanged.")
    if files["conflicts"]:
        print("\nThese files in the project differ from the org. Nothing was copied. Ask before replacing them, then "
              "run again with --overwrite:")
        for path in files["conflicts"]:
            print(f"  {path}")
            for line in files["diffs"].get(path, []):
                print(f"    {line}")
    if files["only_in_project"]:
        print("\nIn the project but no longer in the org (left as they are; deleting them from another org needs a "
              "destructive deploy):")
        for path in files["only_in_project"]:
            print(f"  {path}")
    for fix in result["fixed_ids"]:
        print(f"Fixed an org Id: {fix['file']} {fix['column']} {fix['value']} -> {fix['new']}")
    for item in result["unfixed_ids"]:
        print(f"Org Id left in place: {item['file']} {item['column']} {item['value']}")
    for item in result["id_warnings"]:
        print(f"Check: {item['file']} {item['column']} {item['value']}: {item['message']}")
    if result["dependencies"]:
        print("\nOutside this form:")
        for dep in result["dependencies"]:
            if dep.get("missing"):
                whose = ("not a metadata form in this org: a record component moves as JSON (Export on its record, "
                         "then Import Form Component in the other org)")
            elif dep["packaged"]:
                whose = f"ships with the {dep['namespace']} package" if dep.get("namespace") else "ships with Flow Tool Kit"
            else:
                whose = "the org's own: needed in any org it goes to"
            print(f"  {TYPE_LABELS[dep['type']]} {dep['name']} ({', '.join(dep['uses'])}): {whose}")
    if result["lwr_support"] is None:
        print("\nOn an LWR site an LWC section's component loads only when some component on the site imports it by "
              "name. The org's components could not be searched for one that does; check before the form goes to an "
              "LWR site.")
    for name, importers in sorted((result["lwr_support"] or {}).items()):
        if importers:
            print(f"\nOn an LWR site, c/{name} loads only because {', '.join(importers)} imports it by name. Pull it "
                  "with the form (--with-dependencies), keep it in the Theme Footer of every LWR site that shows the "
                  "form, beside FlowToolKit LWR Support, and publish the site.")
        else:
            print(f"\nOn an LWR site, c/{name} is loaded on demand, and the site's publisher bundles only what a "
                  "component on the site imports by name. No component of the org's own imports it: before the form "
                  f"goes on an LWR site, add an exposed component that does (import 'c/{name}';) to the Theme Footer, "
                  "beside FlowToolKit LWR Support, and publish the site.")
    if result["labels_missing"]:
        print("\nText uses labels that are not Form Labels in this org: " + ", ".join(result["labels_missing"]) +
              ". Flow Tool Kit fills {{$Label.Name}} only from Form Labels (never from a Salesforce custom label), "
              "so the form leaves that text empty, here and in any org it goes to. Create each as a Form Label in "
              "Form Builder, then pull again.")
    if result["labels_not_pulled"]:
        print("Labels named in the files but not pulled: " + ", ".join(result["labels_not_pulled"]))
    if result["soft_deleted"]:
        print("Marked deleted in Form Builder (pulled as they are): " +
              ", ".join(f"{TYPE_LABELS[k]} {v}" for k, v in result["soft_deleted"].items()))
    for line in result["attention"] + result["notes"]:
        print(f"Note: {line}")
    for failure in result["retrieve_failures"]:
        print(f"Not retrieved: {failure['member']}: {failure['error']}")
    if result["dropped_columns"]:
        print("This Flow Tool Kit version lacks: " + ", ".join(result["dropped_columns"]))


def main(argv=None, sf=run_sf, cwd="."):
    parser = argparse.ArgumentParser(description="Pull a Flow Tool Kit metadata form into a Salesforce project.")
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list", help="the org's own metadata forms")
    ls.add_argument("--target-org", help="org alias or username; the Salesforce CLI's default org when left out")
    ls.add_argument("--catalog", help="org-catalog's catalog.json, instead of reading the org")
    ls.add_argument("--search", help="only names or labels containing this text")
    ls.add_argument("--json", action="store_true")
    pl = sub.add_parser("pull", help="pull one form into the project")
    pl.add_argument("form", help="API name (with or without FlowToolKit__) or label")
    pl.add_argument("--target-org")
    pl.add_argument("--catalog", help="org-catalog's catalog.json, to find the form by its label")
    pl.add_argument("--package-dir", help="the package directory to put new files in; the project's default if left out")
    pl.add_argument("--with-dependencies", action="store_true",
                    help="also pull the org's own forms, Form Objects, Themes, image files, flows and Lightning "
                         "web components this form points at")
    pl.add_argument("--overwrite", action="store_true", help="replace project files that differ from the org")
    pl.add_argument("--clear-managers", action="store_true", help="remove Form Managers user Ids from the files")
    pl.add_argument("--clear-prefill", action="store_true", help="remove Form Builder preview data from the files")
    pl.add_argument("--allow-org-ids", action="store_true", help="land files even when an org Id could not be fixed")
    pl.add_argument("--dry-run", action="store_true", help="retrieve and compare, but copy nothing into the project")
    pl.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result, code = list_forms(args, sf, cwd), 0
            if not args.json:
                for row in result["forms"]:
                    print(f"{row['name']:45} {row.get('label') or '':40} {row.get('object') or ''}")
                print(f"{len(result['forms'])} metadata form(s) from the {result['source']}.")
                if result["record_components"]:
                    print(f"{result['record_components']} record component(s) are not listed: they are not metadata.")
        else:
            result, code = pull(args, sf, cwd)
            if not args.json:
                print_pull(result)
    except PullError as error:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(error), "code": error.code, **error.details}, indent=1, default=sorted))
        else:
            print(str(error), file=sys.stderr)
            for key, value in error.details.items():
                print(f"{key}: {json.dumps(value, indent=1)}", file=sys.stderr)
        return error.code
    if args.json:
        print(json.dumps(result, indent=1, default=sorted))
    return code


if __name__ == "__main__":
    sys.exit(main())
