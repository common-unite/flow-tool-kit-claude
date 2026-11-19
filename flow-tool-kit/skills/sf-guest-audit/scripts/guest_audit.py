#!/usr/bin/env python3
"""Guest exposure audit: what the public can reach through an org's Experience Cloud sites.

Read with your own access, as each site's guest user would be allowed.

Read only. It runs SELECT queries and, in Claude Code, retrieves sharing rule
metadata into a temporary folder. It never writes to the org and never reads
record data beyond counts.

The default view is this inside audit. An opt-in **outside probe** (`--probe`,
`scripts/probe.py`) confirms it from the public site URL, the way a visitor's
browser would, against a site you name and are allowed to test (a scratch org's
own site while building). The probe keeps counts, field names and Apex result
shapes only: it writes no record data and downloads no file. The findings file
marks which findings the probe proved from outside.

Commands (Python 3.9+, standard library only):

  queries [--snapshot FILE] [--site NAME ...] [--json]
      The next read-only SOQL queries to run, given what the snapshot already
      holds. In chat, run them through the Salesforce connector and store each
      result with `add`, then ask again until nothing is left.

  add --snapshot FILE --key KEY (--records FILE | --error TEXT)
      Store one query result (a JSON list of records, or a response with a
      "records" list) in the snapshot under its key.

  rules --snapshot FILE RULE_FILE [RULE_FILE ...]
      Read guest sharing rules from <Object>.sharingRules(-meta.xml) files into
      the snapshot.

  probe --snapshot FILE --site-url URL
      Run the outside probe against one public site URL and store its result in
      the snapshot. Opt-in, and only against a site you are allowed to test.

  collect --org ALIAS [--site NAME ...] [--probe URL ...] --snapshot FILE
      Claude Code only (runs the Salesforce CLI): every query, the guest sharing
      rules, and any --probe sites, into one snapshot file.

  analyze --snapshot FILE [--out DIR]
      Write findings.md (every finding with its fix) and findings.json.

  audit --org ALIAS [--site NAME ...] [--probe URL ...] [--out DIR]
      collect, then analyze. The snapshot is kept beside the findings.

Exit codes: 0 no HIGH finding, 1 at least one HIGH finding, 2 usage or input error.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SNAPSHOT_VERSION = 1
PACKAGE_NS = "FlowToolKit"
SEVERITIES = ("HIGH", "MEDIUM", "LOW", "INFO")
MD = "{http://soap.sforce.com/2006/04/metadata}"

# Objects whose records hold people's details, money or messages. Readable by a
# guest, with records shared, they are the first thing to close.
SENSITIVE_OBJECTS = {
    "Account", "Contact", "Lead", "User", "Individual", "Case", "CaseComment",
    "Opportunity", "OpportunityContactRole", "Contract", "Order", "Quote",
    "CampaignMember", "Task", "Event", "EmailMessage", "Note", "ContentNote",
    "Attachment", "Document", "ContentDocument", "ContentVersion",
    "ContactPointAddress", "ContactPointEmail", "ContactPointPhone",
    "ContactPointConsent", "AuthorizationFormConsent", "PartyConsent",
    "SurveyResponse", "SurveyInvitation", "SurveySubject",
    "npe01__OppPayment__c", "npe03__Recurring_Donation__c", "npo02__Household__c",
    "npe4__Relationship__c", "npe5__Affiliation__c", "npsp__Address__c",
    "npsp__Partial_Soft_Credit__c", "npsp__Account_Soft_Credit__c", "npsp__DataImport__c",
    "outfunds__Funding_Request__c", "outfunds__Disbursement__c", "outfunds__Funding_Award__c",
    "pmdm__ProgramEngagement__c", "pmdm__ServiceDelivery__c", "pmdm__ServiceParticipant__c",
    "ProgramEnrollment", "BenefitAssignment", "BenefitDisbursement", "GoalAssignment",
    "Referral", "GiftTransaction", "GiftCommitment", "GiftCommitmentSchedule",
    "PartyRelationshipGroup",
}
PII_FIELD = re.compile(r"email|phone|mobile|fax|ssn|social_?security|birth|dob|street|address|"
                       r"postal|zip|salary|income|tax_?id|passport|licen[cs]e|gender|race|"
                       r"ethnic|religio|disabilit|medical|health|diagnos", re.I)
# Setting-like fields that only look personal (an email template name, an opt-out flag).
NOT_PII_FIELD = re.compile(r"template|opt_?out|_type__c$|enabled?_|_enabled?__c$|disabled|format|label|selector|setting|"
                           r"(?:^|__)(?:has|is)_", re.I)

# Flow Tool Kit objects: the form setup a guest form must read, and the answers
# no guest should ever be shared.
FTK_CONFIG = {"Form_Template__c", "Form_Template_Page__c", "Form_Template_Page_Section__c",
              "Form_Component__c", "Form_Component_Utility__c", "Form_Template_Result__c",
              "Form_Template_Mapping__c", "Payment_Condition__c"}
FTK_ANSWERS = {"Form_Submission__c", "Form_Submission_Answer__c", "Form_Submission_Stage__c"}
FTK_GUEST_COPIES = {"Form_Submission_Upsert_Guest", "Form_Submission_Prefill_Guest"}
FTK_SETS = {"Form_Flow_User": "Form (Flow User)", "Form_Flow_Guest_User": "Form Flow (Guest User)"}

SET_PERMISSIONS = {
    "PermissionsViewAllData": ("HIGH", "View All Data", "reads every record in the org, whatever the sharing"),
    "PermissionsModifyAllData": ("HIGH", "Modify All Data", "can change every record in the org"),
    "PermissionsViewAllUsers": ("HIGH", "View All Users", "sees every user in the org"),
    "PermissionsQueryAllFiles": ("HIGH", "Query All Files", "reaches every file in the org"),
    "PermissionsViewSetup": ("MEDIUM", "View Setup and Configuration", "reads the org's setup"),
    "PermissionsApiEnabled": ("MEDIUM", "API Enabled", "lets anyone call Salesforce's APIs as the guest"),
    "PermissionsRunFlow": ("LOW", "Run Flows", "runs every flow that is not restricted"),
}
SITE_OPTIONS = {
    "OptionsAllowStandardSearch": ("MEDIUM", "standard lookup and search pages", "lets visitors use Salesforce's standard lookup and search pages on the site"),
    "OptionsAllowStandardLookups": ("MEDIUM", "standard lookup and search pages", "lets visitors use Salesforce's standard lookup and search pages on the site"),
    "OptionsAllowGuestSupportApi": ("MEDIUM", "Guest Access to the Support API", "lets visitors call the Support API as the guest"),
    "OptionsAllowGuestPaymentsApi": ("MEDIUM", "Guest Access to the Payments API", "lets visitors call the Payments API as the guest"),
}
MODE_WORDS = {"DefaultMode": "the default context", "SystemModeWithSharing": "system context with sharing",
              "SystemModeWithoutSharing": "system context without sharing", "inactive": "no active version"}
SKIP_OBJECT_SUFFIXES = ("__e", "__mdt", "__x", "__b", "ChangeEvent", "__Share", "__History", "__Feed")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- small helpers

def soql_list(values):
    return ", ".join("'%s'" % str(v).replace("\\", "\\\\").replace("'", "\\'") for v in sorted(set(values)))


def strip_ns(api_name):
    """FlowToolKit__Form_Template__c -> Form_Template__c; other names unchanged."""
    prefix = PACKAGE_NS + "__"
    return api_name[len(prefix):] if api_name.startswith(prefix) else api_name


def is_ftk(api_name):
    return api_name.startswith(PACKAGE_NS + "__")


def share_object(api_name):
    if api_name.endswith("__c"):
        return api_name[:-3] + "__Share"
    return api_name + "Share"


def auditable_object(api_name):
    return not api_name.endswith(SKIP_OBJECT_SUFFIXES)


def clean(value):
    """Drop the 'attributes' blocks sf and the API add to every record."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != "attributes"}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def get(record, path, default=None):
    """Read 'PermissionSet.Name' from a nested record, or from a flat dotted key."""
    if path in record:
        return record[path]
    current = record
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def truthy(value):
    return value is True or str(value).lower() == "true"


def count_of(rows):
    """COUNT(Id) n, expr0 or totalSize: whatever the runner returned."""
    if rows is None:
        return None
    if isinstance(rows, dict):
        rows = rows.get("records", [])
    if not rows:
        return 0
    row = rows[0]
    for key in ("n", "expr0", "totalSize", "count"):
        if key in row and row[key] is not None:
            return int(row[key])
    return len(rows)


def label_of(obj, entities):
    for e in entities:
        if e.get("QualifiedApiName") == obj:
            return e.get("Label") or obj
    return obj


# ---------------------------------------------------------------- the snapshot

def new_snapshot(sites=None):
    return {"snapshot_version": SNAPSHOT_VERSION, "site_filter": list(sites or []),
            "taken_on": datetime.date.today().isoformat(), "results": {}, "errors": {}}


def load_snapshot(path):
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
    except FileNotFoundError:
        raise InputError("no snapshot at %s" % path)
    except json.JSONDecodeError as error:
        raise InputError("%s is not valid JSON: %s" % (path, error))
    if snap.get("snapshot_version") != SNAPSHOT_VERSION:
        raise InputError("%s is not a guest audit snapshot (snapshot_version %s)" % (path, SNAPSHOT_VERSION))
    snap.setdefault("results", {})
    snap.setdefault("errors", {})
    return snap


def save_snapshot(snap, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1, sort_keys=True)
        f.write("\n")


def rows(snap, key):
    return snap["results"].get(key) or []


def done(snap, key):
    return key in snap["results"] or key in snap["errors"]


def matches_site(site, wanted):
    if not wanted:
        return True
    names = {str(site.get(k) or "").lower() for k in ("Name", "MasterLabel", "UrlPathPrefix")}
    return any(w.lower() in names for w in wanted)


def guest_sites(snap):
    return [s for s in rows(snap, "sites") if s.get("GuestUserId") and matches_site(s, snap.get("site_filter"))]


def guest_ids(snap):
    return sorted({s["GuestUserId"] for s in guest_sites(snap)})


def set_ids(snap):
    return sorted({r["PermissionSetId"] for r in rows(snap, "assignments") if r.get("PermissionSetId")})


def readable_objects(snap):
    return sorted({r["SobjectType"] for r in rows(snap, "object_perms")
                   if truthy(r.get("PermissionsRead")) and auditable_object(r["SobjectType"])})


def grant_ids(snap, entity_type):
    return sorted({r["SetupEntityId"] for r in rows(snap, "grants") if r.get("SetupEntityType") == entity_type})


def sharing_models(snap):
    return {e["QualifiedApiName"]: e.get("ExternalSharingModel") for e in rows(snap, "entities")}


def controlled(model):
    """ControlledByParent, ControlledByCampaign and the like: the record follows another record's sharing."""
    return bool(model) and model.startswith("ControlledBy")


def parent_map(snap):
    """Child object -> its master-detail parent objects, from the `parents` query."""
    out = {}
    for r in rows(snap, "parents"):
        child = get(r, "EntityDefinition.QualifiedApiName")
        refs = get(r, "ReferenceTo.referenceTo", get(r, "ReferenceTo", []))
        if isinstance(refs, dict):
            refs = refs.get("referenceTo") or []
        if isinstance(refs, str):
            refs = [refs]
        if child:
            out.setdefault(child, [])
            out[child] += [p for p in refs if p not in out[child]]
    return out


def root_objects(snap, obj, depth=0):
    """The objects whose sharing decides who sees `obj`: itself, or its parents up the chain.

    None when a link is unknown (a parent the query did not return, or Lead or Contact
    control, which has two possible parents)."""
    model = sharing_models(snap).get(obj)
    if not controlled(model):
        return [obj]
    if depth > 4:
        return None
    if model == "ControlledByCampaign":
        parents = ["Campaign"]
    elif model == "ControlledByParent":
        parents = parent_map(snap).get(obj)
    else:
        parents = None
    if not parents:
        return None
    found = []
    for parent in parents:
        roots = root_objects(snap, parent, depth + 1)
        if roots is None:
            return None
        found += [r for r in roots if r not in found]
    return found


def plan(snap):
    """Every read-only query whose inputs are known and whose result is not stored yet.

    Returns [(key, soql)]. Running them all and asking again walks the whole audit;
    `collect` does exactly that with the Salesforce CLI, and chat does it through
    the connector, so both read the same things.
    """
    out = []

    def want(key, soql):
        if not done(snap, key):
            out.append((key, soql))

    want("org", "SELECT Id, Name, IsSandbox, OrganizationType, NamespacePrefix FROM Organization")
    want("sites", "SELECT Id, Name, MasterLabel, SiteType, Status, UrlPathPrefix, GuestUserId, GuestRecordDefaultOwnerId, "
                  "OptionsAllowStandardSearch, OptionsAllowStandardLookups, OptionsAllowGuestSupportApi, "
                  "OptionsAllowGuestPaymentsApi FROM Site WHERE GuestUserId != null")
    want("networks", "SELECT Id, Name, Status, UrlPathPrefix, OptionsGuestChatterEnabled, OptionsGuestFileAccessEnabled, "
                     "OptionsGuestMemberVisibility, OptionsSelfRegistrationEnabled, SelfRegProfileId FROM Network")
    if not done(snap, "sites"):
        return out
    guests = guest_ids(snap)
    if not guests:
        return out
    want("guest_users", "SELECT Id, Username, IsActive, UserType, ProfileId, Profile.Name FROM User WHERE Id IN (%s)" % soql_list(guests))
    want("guest_groups", "SELECT Id, DeveloperName, RelatedId FROM Group WHERE Type = 'GuestUserGroup' AND RelatedId IN (%s)" % soql_list(guests))
    want("assignments", "SELECT AssigneeId, PermissionSetId, PermissionSet.Name, PermissionSet.Label, PermissionSet.NamespacePrefix, "
                        "PermissionSet.IsOwnedByProfile, PermissionSetGroupId FROM PermissionSetAssignment WHERE AssigneeId IN (%s)" % soql_list(guests))
    if not done(snap, "assignments"):
        return out
    sets = set_ids(snap)
    if not sets:
        return out
    want("set_perms", "SELECT Id, Name, Label, NamespacePrefix, IsOwnedByProfile, %s FROM PermissionSet WHERE Id IN (%s)"
         % (", ".join(sorted(SET_PERMISSIONS)), soql_list(sets)))
    want("object_perms", "SELECT ParentId, SobjectType, PermissionsRead, PermissionsCreate, PermissionsEdit, PermissionsDelete, "
                         "PermissionsViewAllRecords, PermissionsModifyAllRecords FROM ObjectPermissions WHERE ParentId IN (%s)" % soql_list(sets))
    want("grants", "SELECT ParentId, SetupEntityType, SetupEntityId FROM SetupEntityAccess WHERE ParentId IN (%s) "
                   "AND SetupEntityType IN ('ApexClass', 'ApexPage', 'FlowDefinition')" % soql_list(sets))
    if done(snap, "object_perms"):
        readable = readable_objects(snap)
        if readable:
            want("entities", "SELECT QualifiedApiName, Label, InternalSharingModel, ExternalSharingModel FROM EntityDefinition "
                             "WHERE QualifiedApiName IN (%s)" % soql_list(readable))
            want("field_perms", "SELECT ParentId, SobjectType, Field FROM FieldPermissions WHERE ParentId IN (%s) "
                                "AND PermissionsRead = true AND SobjectType IN (%s)" % (soql_list(sets), soql_list(readable)))
        if done(snap, "entities"):
            models = sharing_models(snap)
            by_parent = [o for o in readable if models.get(o) == "ControlledByParent"]
            if by_parent:
                want("parents", "SELECT EntityDefinition.QualifiedApiName, QualifiedApiName, DataType, ReferenceTo FROM FieldDefinition "
                                "WHERE EntityDefinition.QualifiedApiName IN (%s) AND DataType LIKE 'Master-Detail%%'" % soql_list(by_parent))
        if done(snap, "entities") and done(snap, "guest_groups"):
            groups = [g["Id"] for g in rows(snap, "guest_groups")]
            models = sharing_models(snap)
            counted = {o for o in readable if not controlled(models.get(o))}
            if done(snap, "parents") or not any(models.get(o) == "ControlledByParent" for o in readable):
                for obj in readable:
                    counted.update(root_objects(snap, obj) or [])
            for obj in sorted(counted):
                if not groups:
                    break
                key = "guest_shares:" + obj
                want(key, "SELECT UserOrGroupId, COUNT(Id) n FROM %s WHERE RowCause = 'GuestRule' AND UserOrGroupId IN (%s) "
                          "GROUP BY UserOrGroupId" % (share_object(obj), soql_list(groups)))
                if done(snap, key) and sum(int(r.get("n") or r.get("expr0") or 0) for r in rows(snap, key)) > 0:
                    want("total:" + obj, "SELECT COUNT(Id) n FROM %s" % obj)
                    if strip_ns(obj) == "Form_Submission__c":
                        prefix = obj[:-len("Form_Submission__c")]
                        want("prefill_templates", "SELECT COUNT(Id) n FROM %s WHERE %sIsPrefillTemplate__c = true" % (obj, prefix))
    if done(snap, "grants"):
        classes = grant_ids(snap, "ApexClass")
        pages = grant_ids(snap, "ApexPage")
        flows = grant_ids(snap, "FlowDefinition")
        if classes:
            want("apex_classes", "SELECT Id, Name, NamespacePrefix, ApiVersion, Status, Body FROM ApexClass WHERE Id IN (%s)" % soql_list(classes))
        if pages:
            want("pages", "SELECT Id, Name, NamespacePrefix, ControllerType, ControllerKey FROM ApexPage WHERE Id IN (%s)" % soql_list(pages))
        if flows:
            want("flows", "SELECT DurableId, ApiName, NamespacePrefix, Label, ProcessType, IsActive, ActiveVersionId, OverriddenById, "
                          "OverriddenFlowId FROM FlowDefinitionView WHERE DurableId IN (%s)" % soql_list(flows))
        if done(snap, "pages"):
            controllers = sorted({p["ControllerKey"] for p in rows(snap, "pages") if p.get("ControllerKey")})
            if controllers:
                want("page_controllers", "SELECT Id, Name, NamespacePrefix, ApiVersion, Status, Body FROM ApexClass WHERE Name IN (%s)" % soql_list(controllers))
        if done(snap, "flows"):
            versions = sorted({f["ActiveVersionId"] for f in rows(snap, "flows") if f.get("ActiveVersionId")})
            if versions:
                want("flow_versions", "SELECT DurableId, FlowDefinitionViewId, RunInMode, Status FROM FlowVersionView WHERE DurableId IN (%s)" % soql_list(versions))
    return out


def store(snap, key, records=None, error=None):
    if error is not None:
        snap["errors"][key] = str(error)[:500]
        snap["results"].pop(key, None)
        return
    if isinstance(records, dict):
        records = records.get("records", records.get("result", {}).get("records") if isinstance(records.get("result"), dict) else [])
    if not isinstance(records, list):
        raise InputError("records for %s must be a JSON list, or an object with a 'records' list" % key)
    snap["results"][key] = clean(records)
    snap["errors"].pop(key, None)


# ---------------------------------------------------------------- sharing rules

def parse_rule_file(path):
    """Guest sharing rules in one <Object>.sharingRules(-meta.xml) file."""
    obj = os.path.basename(path).split(".sharingRules")[0]
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise InputError("cannot read %s: %s" % (path, error))
    found = []
    for rule in root:
        guest = rule.find("%ssharedTo/%sguestUser" % (MD, MD))
        if guest is None:
            continue

        def text(name, element=rule):
            node = element.find(MD + name)
            return node.text if node is not None and node.text is not None else None

        criteria = [{"field": text("field", c), "operation": text("operation", c), "value": text("value", c) or ""}
                    for c in rule.findall(MD + "criteriaItems")]
        found.append({
            "object": obj, "name": text("fullName"), "label": text("label"), "guest_user": guest.text,
            "access": text("accessLevel"), "criteria": criteria, "boolean_filter": text("booleanFilter"),
            "include_hvu_owned": truthy(text("includeHVUOwnedRecords")), "description": text("description") or "",
        })
    return found


def cmd_rules(args):
    snap = load_snapshot(args.snapshot)
    found = []
    for path in args.files:
        found += parse_rule_file(path)
    have = {(r["object"], r["name"]) for r in found}
    kept = [r for r in snap.get("guest_rules") or [] if (r["object"], r["name"]) not in have]
    snap["guest_rules"] = kept + found
    snap["guest_rules_source"] = "metadata"
    save_snapshot(snap, args.snapshot)
    print("stored %d guest sharing rule(s) from %d file(s)" % (len(found), len(args.files)))
    return 0


# ---------------------------------------------------------------- Apex reading

def strip_code(body):
    """Remove comments, and empty every string literal (keeping its quotes)."""
    out, i, n = [], 0, len(body)
    while i < n:
        two = body[i:i + 2]
        if two == "/*":
            end = body.find("*/", i + 2)
            i = n if end < 0 else end + 2
            out.append(" ")
        elif two == "//":
            end = body.find("\n", i)
            i = n if end < 0 else end
        elif body[i] == "'":
            j = i + 1
            while j < n and body[j] != "'":
                j += 2 if body[j] == "\\" else 1
            out.append("''")
            i = j + 1
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def scan_apex(body):
    """Facts a reviewer needs about one guest-reachable class. None when the code is hidden."""
    if not body or body.strip() in ("(hidden)", ""):
        return None
    rest = re.search(r"@RestResource\s*\(\s*urlMapping\s*=\s*'([^']*)'", body, re.I)
    code = strip_code(body)
    decl = re.search(r"\b((?:(?:global|public|private|virtual|abstract|with\s+sharing|without\s+sharing|inherited\s+sharing)\s+)+)"
                     r"(class|interface|enum)\s+(\w+)", code, re.I)
    modifiers = decl.group(1).lower() if decl else ""
    kind = decl.group(2).lower() if decl else "class"
    sharing = None
    for word in ("without", "inherited", "with"):
        if re.search(r"\b%s\s+sharing\b" % word, modifiers):
            sharing = word
            break
    top_end = decl.end() if decl else 0
    inner_without = len(re.findall(r"\bwithout\s+sharing\b", code[top_end:], re.I))

    def count(pattern):
        return len(re.findall(pattern, code, re.I))

    return {
        "kind": kind,
        "sharing": sharing,
        "inner_without_sharing": inner_without,
        "is_test": bool(re.search(r"@isTest\b", code, re.I)),
        "aura_enabled": count(r"@AuraEnabled\b"),
        "invocable": count(r"@InvocableMethod\b"),
        "remote_action": count(r"@RemoteAction\b"),
        "webservice": count(r"\bwebservice\s+static\b"),
        "rest_mapping": rest.group(1) if rest else None,
        "system_mode": count(r"\bWITH\s+SYSTEM_MODE\b|\bAccessLevel\s*\.\s*SYSTEM_MODE\b"),
        "user_mode": count(r"\bWITH\s+USER_MODE\b|\bAccessLevel\s*\.\s*USER_MODE\b|\bWITH\s+SECURITY_ENFORCED\b|"
                           r"\bstripInaccessible\s*\(|\.\s*isAccessible\s*\(|\.\s*isCreateable\s*\(|\.\s*isUpdateable\s*\("),
        "static_queries": count(r"\[\s*(?:SELECT|FIND)\b"),
        "dynamic_queries": count(r"\bDatabase\s*\.\s*(?:query|countQuery|getQueryLocator)\s*\(|\bSearch\s*\.\s*query\s*\("),
        "bound_queries": count(r"\bDatabase\s*\.\s*(?:queryWithBinds|countQueryWithBinds|getQueryLocatorWithBinds)\s*\("),
        "escapes_input": count(r"\bString\s*\.\s*escapeSingleQuotes\s*\(|\.\s*escapeSingleQuotes\s*\("),
        "dml": count(r"\b(?:insert|update|upsert|delete|undelete|merge)\s+[\w(\[]|\bDatabase\s*\.\s*(?:insert|update|upsert|delete)\s*\("),
    }


def apex_entry_points(facts):
    parts = []
    for key, label in (("aura_enabled", "@AuraEnabled"), ("invocable", "@InvocableMethod"),
                       ("remote_action", "@RemoteAction"), ("webservice", "webservice")):
        if facts[key]:
            parts.append("%d %s" % (facts[key], label))
    if facts["rest_mapping"]:
        parts.append("@RestResource %s" % facts["rest_mapping"])
    return parts


# ---------------------------------------------------------------- analysis

class Findings:
    def __init__(self):
        self.items = []

    def add(self, severity, area, site, title, evidence, fix, obj=None, apex_class=None):
        self.items.append({"severity": severity, "area": area, "site": site, "title": title,
                           "evidence": list(evidence), "fix": list(fix), "obj": obj,
                           "apex_class": apex_class, "proved": False})

    def ordered(self):
        """Merge the same finding across sites (sites often share permission sets), then number them."""
        merged = {}
        for item in self.items:
            key = (item["severity"], item["area"], item["title"], tuple(item["evidence"]), tuple(item["fix"]))
            if key in merged:
                if item["site"] and item["site"] not in merged[key]["sites"]:
                    merged[key]["sites"].append(item["site"])
            else:
                merged[key] = dict(item, sites=[item["site"]] if item["site"] else [])
        for item in merged.values():
            item["site"] = ", ".join(item.pop("sites"))
            item.pop("obj", None)
            item.pop("apex_class", None)
        order = {s: i for i, s in enumerate(SEVERITIES)}
        items = sorted(merged.values(), key=lambda f: (order[f["severity"]], f["area"], f["title"], f["site"]))
        counters = {}
        for item in items:
            counters[item["severity"]] = counters.get(item["severity"], 0) + 1
            item["id"] = "%s%d" % (item["severity"][0], counters[item["severity"]])
        return items


def build_audiences(snap):
    """One audience per guest user: its sites, network, user, group and permission sets."""
    sites = guest_sites(snap)
    networks = rows(snap, "networks")
    users = {u["Id"]: u for u in rows(snap, "guest_users")}
    groups = {g["RelatedId"]: g for g in rows(snap, "guest_groups")}
    audiences = []
    for guest in guest_ids(snap):
        own = [s for s in sites if s["GuestUserId"] == guest]
        prefixes = {(s.get("UrlPathPrefix") or "").split("/")[0] for s in own}
        network = next((n for n in networks if (n.get("UrlPathPrefix") or "") in prefixes), None)
        names = sorted({s["Name"] for s in own})
        label = network["Name"] if network else (own[0].get("MasterLabel") or own[0]["Name"])
        assigned = [a for a in rows(snap, "assignments") if a.get("AssigneeId") == guest]
        audiences.append({
            "guest": guest, "label": label, "site_names": names, "sites": own, "network": network,
            "user": users.get(guest, {}), "group": (groups.get(guest) or {}).get("Id"),
            "sets": {a["PermissionSetId"]: a for a in assigned},
        })
    return audiences


def set_name(assignment):
    if truthy(get(assignment, "PermissionSet.IsOwnedByProfile")):
        return "the guest profile"
    return get(assignment, "PermissionSet.Label") or get(assignment, "PermissionSet.Name") or assignment["PermissionSetId"]


def audience_object_access(snap, aud):
    access = {}
    for r in rows(snap, "object_perms"):
        if r.get("ParentId") not in aud["sets"] or not auditable_object(r["SobjectType"]):
            continue
        entry = access.setdefault(r["SobjectType"], {"read": [], "create": [], "edit": [], "delete": [], "view_all": [], "modify_all": []})
        who = set_name(aud["sets"][r["ParentId"]])
        for flag, key in (("PermissionsRead", "read"), ("PermissionsCreate", "create"), ("PermissionsEdit", "edit"),
                          ("PermissionsDelete", "delete"), ("PermissionsViewAllRecords", "view_all"),
                          ("PermissionsModifyAllRecords", "modify_all")):
            if truthy(r.get(flag)) and who not in entry[key]:
                entry[key].append(who)
    return access


def audience_fields(snap, aud):
    fields = {}
    for r in rows(snap, "field_perms"):
        if r.get("ParentId") in aud["sets"]:
            fields.setdefault(r["SobjectType"], set()).add(r["Field"].split(".", 1)[-1])
    return {k: sorted(v) for k, v in fields.items()}


def shared_count(snap, obj, group):
    key = "guest_shares:" + obj
    if key in snap["errors"]:
        return None
    if key not in snap["results"]:
        return None
    return sum(int(r.get("n") or r.get("expr0") or 0) for r in rows(snap, key) if r.get("UserOrGroupId") == group)


def rule_text(rule):
    if not rule["criteria"]:
        return "no criteria"
    parts = ["%s %s %s" % (c["field"], c["operation"], c["value"] or "(blank)") for c in rule["criteria"]]
    return (" / ".join(parts) + (" (logic %s)" % rule["boolean_filter"] if rule.get("boolean_filter") else ""))


def is_prefill_rule(rule):
    crit = rule["criteria"]
    return (len(crit) == 1 and strip_ns(crit[0]["field"] or "") == "IsPrefillTemplate__c"
            and crit[0]["operation"] == "equals" and str(crit[0]["value"]).lower() == "true")


def drop_read(label, perms):
    """The fix for Read a guest may not need. Salesforce requires Read wherever Create is granted."""
    holders = "; ".join(perms["read"])
    if perms["create"]:
        return ("Salesforce requires Read wherever Create is granted. If no guest form creates %s, remove Create and Read on it from %s; "
                "if one does, keep %s out of every guest sharing rule and give field Read only on the fields the form shows." % (label, holders, label))
    return "Remove Read on %s from %s unless a guest form or page shows it." % (label, holders)


SHARING_FIX = [
    "Setup, Sharing Settings, the object's Sharing Rules: edit the guest rule so its criteria match only the records the site must show (a Public or Show on Website checkbox works well), or delete it.",
    "To work out the narrowest rule from what the site's flows actually read, use flow-access-fix (its sharing proposal).",
    "Run this audit again: the count of shared records should drop to what you intend.",
]


def analyze_objects(snap, aud, findings, baseline, inventory):
    access = audience_object_access(snap, aud)
    fields = audience_fields(snap, aud)
    entities = rows(snap, "entities")
    models = sharing_models(snap)
    rules = [r for r in snap.get("guest_rules") or [] if r["guest_user"] in aud["site_names"]]
    rules_known = "guest_rules" in snap
    site = aud["label"]
    for obj in sorted(access):
        perms = access[obj]
        label = label_of(obj, entities)
        base = strip_ns(obj)
        shared = shared_count(snap, obj, aud["group"])
        total = count_of(rows(snap, "total:" + obj)) if ("total:" + obj) in snap["results"] else None
        pii = [f for f in fields.get(obj, []) if PII_FIELD.search(f) and not NOT_PII_FIELD.search(f)]
        obj_rules = [r for r in rules if r["object"] == obj]
        follows = None
        if controlled(models.get(obj)):
            roots, parent_shared = parent_exposure(snap, obj, aud["group"])
            follows = " and ".join(label_of(r, entities) for r in roots) if roots else "its parent"
            if parent_shared is not None:
                follows += " (%d shared)" % parent_shared
        inventory.append({"site": site, "object": obj, "label": label,
                          "access": ", ".join(k.replace("_", " ").title() for k in ("read", "create", "edit", "delete", "view_all", "modify_all") if perms[k]),
                          "shared": shared, "total": total, "model": models.get(obj), "follows": follows})

        broad = [(k, v) for k, v in perms.items() if k in ("edit", "delete", "view_all", "modify_all") and v]
        if broad:
            words = ", ".join("%s (from %s)" % (k.replace("_", " ").title(), "; ".join(v)) for k, v in broad)
            findings.add("HIGH", "Object access", site,
                         "The guest holds %s on %s" % (", ".join(k.replace("_", " ").title() for k, _ in broad), label),
                         ["%s: %s" % (obj, words), "Salesforce no longer lets a guest hold these; a set that still grants them is left from before that change, or from a profile clone."],
                         ["Remove these permissions from %s for %s." % ("; ".join(sorted({w for _, v in broad for w in v})), label),
                          "Guests save their own answers through the save flow, never through Edit."])
        if not perms["read"]:
            continue

        if is_ftk(obj) and base in FTK_ANSWERS:
            if controlled(models.get(obj)):
                baseline.append((site, "%s follows its Form Submission" % label, "yes",
                                 "Readable only on the submissions shared with the guest, which must be Pre-fill Templates alone"))
                continue
            if not shared:
                baseline.append((site, "No %s is shared with the guest" % label, "yes", "Guests create their answers but never read them back"))
                continue
            if base == "Form_Submission__c":
                prefill = count_of(rows(snap, "prefill_templates")) if "prefill_templates" in snap["results"] else None
                bad = [r for r in obj_rules if not is_prefill_rule(r)]
                if rules_known and obj_rules and not bad:
                    baseline.append((site, "Pre-fill Templates shared with the guest (%d records)" % shared, "yes",
                                     "Only Pre-fill Templates, which hold default answers, never anyone's submission"))
                    continue
                if not rules_known and prefill is not None and shared <= prefill:
                    baseline.append((site, "Form Submissions shared with the guest: %d, no more than the %d Pre-fill Templates" % (shared, prefill), "probably",
                                     "Read the rule's criteria to be sure: it must be Is Pre-fill Template equals True"))
                    continue
                evidence = ["%d Form Submission records are shared with the guest%s." % (shared, "" if prefill is None else ", and only %d are Pre-fill Templates" % prefill)]
                evidence += ["Rule %s: %s" % (r["label"] or r["name"], rule_text(r)) for r in bad]
                findings.add("HIGH", "Form answers", site,
                             "Anyone on the internet can read people's form answers", evidence,
                             ["Change the guest rule on Form Submission to the single criterion Is Pre-fill Template equals True, or delete it.",
                              "A guest reopens their own draft only through a resume link and the org's system-mode resume flow (flow-access-fix), never through sharing.",
                              "Then run this audit again: the shared count must equal the number of Pre-fill Templates."], obj=obj)
                continue
            findings.add("HIGH", "Form answers", site,
                         "Anyone on the internet can read %d %s records" % (shared, label),
                         ["%s holds people's answers or their progress through a form. No guest rule should share it." % label]
                         + ["Rule %s: %s" % (r["label"] or r["name"], rule_text(r)) for r in obj_rules],
                         ["Delete every guest sharing rule on %s (Setup, Sharing Settings, %s Sharing Rules)." % (label, label),
                          "Run this audit again: the shared count must be 0."], obj=obj)
            continue

        if is_ftk(obj) and base in FTK_CONFIG:
            if shared:
                baseline.append((site, "%s shared with the guest (%d records)" % (label, shared), "yes", "Form setup a guest form must read"))
            continue

        for r in obj_rules:
            if r["include_hvu_owned"]:
                findings.add("MEDIUM", "Sharing rule", site,
                             "Guest rule %s also shares %s records owned by high-volume community users" % (r["label"] or r["name"], label),
                             ["Rule %s on %s: %s, Include records owned by high-volume community users is on." % (r["name"], obj, rule_text(r))],
                             ["Edit the rule and clear Include records owned by high-volume community users, unless the site must show what members created."])

        if controlled(models.get(obj)):
            if obj in SENSITIVE_OBJECTS or pii:
                analyze_child(snap, aud, findings, obj, label, perms, pii)
            continue

        rule_lines = ["Rule %s: %s" % (r["label"] or r["name"], rule_text(r)) for r in obj_rules]
        if shared is None:
            error = snap["errors"].get("guest_shares:" + obj)
            if obj in SENSITIVE_OBJECTS:
                findings.add("MEDIUM", "Object access", site,
                             "Guests can read %s; the audit could not count what is shared" % label,
                             ["Read from %s." % "; ".join(perms["read"])] + (["Count failed: %s" % error] if error else []) + rule_lines,
                             [drop_read(label, perms),
                              "Then check its guest sharing rules in Setup, Sharing Settings."], obj=obj)
            continue
        if shared > 0 and obj in SENSITIVE_OBJECTS:
            findings.add("HIGH", "Records shared", site,
                         "Anyone on the internet can read %d %s records%s" % (shared, label, "" if total is None else " (of %d)" % total),
                         ["Read from %s; guest sharing rules share %d records." % ("; ".join(perms["read"]), shared)]
                         + rule_lines + (["Readable fields that look personal: %s" % ", ".join(pii[:12])] if pii else [])
                         + ["Every guest-readable record is open to anyone who calls the site's APIs directly, not only through your pages."],
                         ["Decide which %s records, if any, the site must show. If none: delete the guest rule and remove Read on %s from %s." % (label, label, "; ".join(perms["read"]))]
                         + SHARING_FIX[:2] + ["Remove field Read on every personal field the site does not display."] + SHARING_FIX[2:], obj=obj)
            continue
        if shared > 0 and total is not None and shared >= total:
            findings.add("MEDIUM", "Records shared", site,
                         "Every %s record (%d) is shared with the public" % (label, total),
                         ["Guest rules share all %d records, so the criteria do not narrow anything." % total] + rule_lines
                         + (["Readable fields that look personal: %s" % ", ".join(pii[:12])] if pii else []),
                         ["If every record really is public, add a field that marks it (a Public checkbox) so new records are not exposed by default."] + SHARING_FIX, obj=obj)
            continue
        if shared > 0 and pii:
            findings.add("MEDIUM", "Fields", site,
                         "Guests can read personal-looking fields on %d shared %s records" % (shared, label),
                         ["Readable fields: %s" % ", ".join(pii[:12])] + rule_lines,
                         ["Remove field Read on these fields from %s unless the site displays them." % "; ".join(perms["read"])], obj=obj)
            continue
        if shared == 0 and obj in SENSITIVE_OBJECTS:
            findings.add("LOW", "Object access", site,
                         "Guests can read %s, though no record is shared with them today" % label,
                         ["Read from %s. Nothing is exposed now; one guest rule added later would expose those records at once." % "; ".join(perms["read"])]
                         + (["Create is granted too. Records a guest creates belong to the site's default owner, so the guest cannot read them back unless a rule shares them."] if perms["create"] else []),
                         [drop_read(label, perms)], obj=obj)

    readable = {o for o, p in access.items() if p["read"]}
    for r in rules:
        if r["object"] not in readable:
            findings.add("LOW", "Sharing rule", site,
                         "Guest rule %s shares %s records the guest cannot read yet" % (r["label"] or r["name"], label_of(r["object"], entities)),
                         ["Rule %s on %s: %s. The guest has no Read on the object, so nothing shows today." % (r["name"], r["object"], rule_text(r))],
                         ["Delete the rule if nothing on the site needs it: granting Read later would expose these records at once."])


def parent_exposure(snap, obj, group):
    """(root objects, records of them shared with this guest), or (roots, None) when unknown."""
    roots = root_objects(snap, obj)
    if not roots:
        return roots, None
    counts = [shared_count(snap, r, group) for r in roots]
    if any(c is None for c in counts):
        return roots, None
    return roots, min(counts)


def analyze_child(snap, aud, findings, obj, label, perms, pii):
    """An object whose records follow another record's sharing (master-detail, or Campaign Members)."""
    site = aud["label"]
    entities = rows(snap, "entities")
    roots, shared = parent_exposure(snap, obj, aud["group"])
    parent = " and ".join(label_of(r, entities) for r in roots) if roots else "its parent"
    fields_line = ["Readable fields that look personal: %s" % ", ".join(pii[:12])] if pii else []
    follows = "%s takes its sharing from %s, so every guest rule there exposes these records too." % (label, parent)
    if shared is None:
        findings.add("MEDIUM", "Object access", site,
                     "Guests can read %s wherever %s is shared with them" % (label, parent),
                     [follows, "The audit could not count the %s records shared with the guest." % parent] + fields_line,
                     [drop_read(label, perms), "If it must stay, remove field Read on the personal fields, and check the guest rules on %s." % parent], obj=obj)
    elif shared > 0:
        findings.add("HIGH" if obj in SENSITIVE_OBJECTS else "MEDIUM", "Records shared", site,
                     "Anyone on the internet can read %s on the %d %s records shared with guests" % (label, shared, parent),
                     [follows, "Read on %s from %s." % (label, "; ".join(perms["read"]))] + fields_line,
                     [drop_read(label, perms),
                      "If the site must show them, remove field Read on every personal field it does not display.",
                      "Narrowing the guest rule on %s narrows these too (flow-access-fix proposes the narrowest rule)." % parent], obj=obj)
    else:
        findings.add("LOW", "Object access", site,
                     "Guests can read %s, though no %s record is shared with them today" % (label, parent),
                     [follows + " Nothing is exposed now; a guest rule added on %s later would expose them at once." % parent] + fields_line,
                     [drop_read(label, perms)], obj=obj)


def analyze_sets(snap, aud, findings):
    perms = {p["Id"]: p for p in rows(snap, "set_perms")}
    for set_id, assignment in sorted(aud["sets"].items()):
        p = perms.get(set_id)
        if not p:
            continue
        for field, (severity, label, effect) in sorted(SET_PERMISSIONS.items()):
            if truthy(p.get(field)):
                findings.add(severity, "System permission", aud["label"],
                             "The guest holds %s, which %s" % (label, effect),
                             ["Granted by %s." % set_name(assignment)],
                             ["Remove %s from %s." % (label, set_name(assignment))]
                             + (["Grant each flow a guest runs in the guest's own permission set instead (flow-access-fix)."] if field == "PermissionsRunFlow" else []))


def analyze_site(snap, aud, findings, baseline):
    site = aud["label"]
    user = aud["user"]
    if user and not truthy(user.get("IsActive")):
        findings.add("INFO", "Site", site, "The site's guest user is inactive",
                     ["%s is inactive, so the site serves no guest pages." % user.get("Username", aud["guest"])], ["Nothing to do unless the site should be public."])
    if all((s.get("Status") or "") != "Active" for s in aud["sites"]) and aud["sets"]:
        findings.add("LOW", "Site", site, "The site is not active, but its guest user keeps its access",
                     ["Site status: %s." % ", ".join(sorted({s.get("Status") or "?" for s in aud["sites"]}))],
                     ["If the site is retired, remove the guest's permission sets and guest sharing rules, so they cannot come back with a reactivation."])
    seen = set()
    for s in aud["sites"]:
        for field, (severity, label, effect) in SITE_OPTIONS.items():
            if truthy(s.get(field)) and label not in seen:
                seen.add(label)
                findings.add(severity, "Site setting", site, "%s is on" % (label[0].upper() + label[1:]),
                             ["Site %s %s." % (s["Name"], effect)],
                             ["Setup, Sites (or the site's Workspaces, Administration): turn off %s unless the site uses it." % label])
    net = aud["network"]
    if not net:
        return
    if truthy(net.get("OptionsGuestMemberVisibility")):
        findings.add("MEDIUM", "Site setting", site, "Guests can see the site's members",
                     ["Let guest users see other members of this site is on: visitors can look up member names and photos."],
                     ["Workspaces, Administration, Preferences: turn off Let guest users see other members of this site."])
    if truthy(net.get("OptionsSelfRegistrationEnabled")):
        findings.add("INFO", "Site setting", site, "Anyone can sign up as a site member",
                     ["Self-registration is on, so a visitor can create a member account and get the member profile's access."],
                     ["Check the self-registration profile's access like any signed-in audience; that is the portal audience, outside this guest audit."])
    baseline.append((site, "Allow guest users to access public APIs", "on" if truthy(net.get("OptionsGuestChatterEnabled")) else "off",
                     "Flow Tool Kit forms on LWR sites need it on. With it on, everything the guest can read is reachable by anyone through Salesforce's APIs, not only through your pages"))
    baseline.append((site, "Let guest users view asset files and CMS content", "on" if truthy(net.get("OptionsGuestFileAccessEnabled")) else "off",
                     "Needed when forms show image assets; it opens only files the site makes available"))


def flow_key(flow):
    return (flow.get("NamespacePrefix") + "__" if flow.get("NamespacePrefix") else "") + flow["ApiName"]


def analyze_flows(snap, aud, findings, baseline, inventory):
    granted = {r["SetupEntityId"] for r in rows(snap, "grants") if r.get("SetupEntityType") == "FlowDefinition" and r.get("ParentId") in aud["sets"]}
    modes = {v["DurableId"]: v.get("RunInMode") or "DefaultMode" for v in rows(snap, "flow_versions")}
    site = aud["label"]
    for flow in sorted(rows(snap, "flows"), key=flow_key):
        if flow["DurableId"] not in granted:
            continue
        mode = modes.get(flow.get("ActiveVersionId"), "DefaultMode" if flow.get("ActiveVersionId") else "inactive")
        inventory.append({"site": site, "flow": flow_key(flow), "label": flow.get("Label"), "mode": mode, "active": truthy(flow.get("IsActive"))})
        if not truthy(flow.get("IsActive")) or not mode.startswith("SystemMode"):
            continue
        if flow["ApiName"] in FTK_GUEST_COPIES:
            baseline.append((site, "%s runs in %s" % (flow.get("Label") or flow["ApiName"], MODE_WORDS.get(mode, mode)), "yes",
                             "The org's own system-mode copy for guest save or resume. Keep it to its one job and compare it with the packaged flow after each upgrade"))
            continue
        severity = "HIGH" if mode == "SystemModeWithoutSharing" else "MEDIUM"
        findings.add(severity, "Flow", site,
                     "Guests run %s in system context (%s)" % (flow.get("Label") or flow["ApiName"], "without sharing" if severity == "HIGH" else "with sharing, but ignoring object and field access"),
                     ["%s (%s) is granted to the guest and runs as %s: every Get Records and every create or update in it ignores the guest's access." % (flow_key(flow), flow.get("ProcessType"), mode)],
                     ["Open the flow and check what it reads and writes. It must never look up records by a value the visitor typed, or return whole records to the screen.",
                      "If it only needs records the guest may read, set How to Run the Flow to User or System Context, Enforces User Permissions (default), and share those records with a guest rule.",
                      "If it truly needs system context, keep it to one small step that returns only the value the screen shows, and say why in its description."])


def analyze_apex(snap, aud, findings, inventory):
    site = aud["label"]
    granted = {r["SetupEntityId"] for r in rows(snap, "grants") if r.get("SetupEntityType") == "ApexClass" and r.get("ParentId") in aud["sets"]}
    page_ids = {r["SetupEntityId"] for r in rows(snap, "grants") if r.get("SetupEntityType") == "ApexPage" and r.get("ParentId") in aud["sets"]}
    controllers = {p["ControllerKey"]: p["Name"] for p in rows(snap, "pages") if p["Id"] in page_ids and p.get("ControllerKey")}
    classes = [(c, "granted") for c in rows(snap, "apex_classes") if c["Id"] in granted]
    have = {c["Id"] for c, _ in classes}
    classes += [(c, "controller of page %s" % controllers[c["Name"]]) for c in rows(snap, "page_controllers")
                if c["Name"] in controllers and c["Id"] not in have]
    hidden = {}
    for cls, how in sorted(classes, key=lambda x: ((x[0].get("NamespacePrefix") or ""), x[0]["Name"])):
        name = (cls["NamespacePrefix"] + "." if cls.get("NamespacePrefix") else "") + cls["Name"]
        facts = cls.get("facts") or scan_apex(cls.get("Body"))
        if facts is None:
            hidden.setdefault(cls.get("NamespacePrefix") or "(no namespace)", []).append(cls["Name"])
            inventory.append({"site": site, "class": name, "how": how, "summary": "code not visible (managed package)"})
            continue
        entry = apex_entry_points(facts)
        inventory.append({"site": site, "class": name, "how": how,
                          "summary": "%s sharing; %s" % (facts["sharing"] or "no", ", ".join(entry) or "no guest entry points")})
        issues, fixes, severity = [], [], None

        def bump(level):
            nonlocal severity
            if severity is None or SEVERITIES.index(level) < SEVERITIES.index(severity):
                severity = level

        if facts["is_test"]:
            bump("LOW")
            issues.append("It is a test class: nothing in it should run for a visitor.")
            fixes.append("Remove the test class from the guest's Apex Class Access.")
        elif not entry and how == "granted":
            bump("LOW")
            issues.append("It has nothing a site can call (no @AuraEnabled, @InvocableMethod, @RemoteAction, webservice or @RestResource).")
            fixes.append("Remove it from the guest's Apex Class Access, unless another class the guest calls needs it.")
        if facts["sharing"] == "without":
            bump("HIGH")
            issues.append("Declared without sharing: every query in it reads past the guest's sharing.")
            fixes.append("Declare it with sharing (or inherited sharing), and move any query that must reach past sharing into a small private helper that returns only the value needed.")
        elif (facts["sharing"] is None and facts["kind"] == "class" and entry
              and (facts["static_queries"] or facts["dynamic_queries"] or facts["bound_queries"] or facts["dml"])):
            bump("MEDIUM")
            issues.append("Reads or writes records but declares no sharing keyword, so how it shares depends on what calls it.")
            fixes.append("Declare it with sharing.")
        if facts["inner_without_sharing"]:
            bump("MEDIUM")
            issues.append("%d inner class(es) declared without sharing." % facts["inner_without_sharing"])
            fixes.append("Check each inner class without sharing: it must never take a record Id or a search value from the visitor.")
        if facts["system_mode"]:
            bump("HIGH")
            issues.append("%d query or DML statement(s) run in system mode (WITH SYSTEM_MODE or AccessLevel.SYSTEM_MODE)." % facts["system_mode"])
            fixes.append("Use WITH USER_MODE (or AccessLevel.USER_MODE) in code a guest reaches.")
        if facts["dynamic_queries"]:
            bump("MEDIUM")
            issues.append("%d query(ies) built at run time (Database.query or Search.query)%s." % (facts["dynamic_queries"], ", with escapeSingleQuotes" if facts["escapes_input"] else ""))
            fixes.append("Pass every visitor value as a bind variable (Database.queryWithBinds), never by joining it into the query text.")
        if entry and (facts["static_queries"] or facts["dynamic_queries"] or facts["bound_queries"] or facts["dml"]) and not facts["user_mode"]:
            bump("LOW")
            issues.append("Reads or writes records with no object or field access check (no USER_MODE, SECURITY_ENFORCED or stripInaccessible).")
            fixes.append("Add WITH USER_MODE to its queries and AccessLevel.USER_MODE to its DML, so a guest never gets a field their access hides.")
        if facts["rest_mapping"]:
            bump("MEDIUM")
            issues.append("@RestResource %s: anyone can call it directly at the site's /services/apexrest/ address." % facts["rest_mapping"])
            fixes.append("Check every input it accepts; return only what a visitor may see.")
        if severity:
            findings.add(severity, "Apex", site, "Guest-reachable Apex %s: %s" % (name, issues[0].rstrip(".")),
                         ["Reached as: %s. Entry points: %s." % (how, ", ".join(entry) or "none")] + issues, fixes, apex_class=cls["Name"])
    for ns, names in sorted(hidden.items()):
        findings.add("INFO", "Apex", site, "%d packaged class(es) from %s are granted to the guest; their code is not visible" % (len(names), ns),
                     ["%s" % ", ".join(sorted(names)[:15]) + (" and %d more" % (len(names) - 15) if len(names) > 15 else "")],
                     ["Managed packages ship reviewed code; keep their guest permission sets only on sites that use that package's guest features."])


def analyze_ftk_baseline(snap, aud, baseline):
    names = {get(a, "PermissionSet.Name") for a in aud["sets"].values()}
    uses_ftk = any(n in FTK_SETS for n in names) or any(is_ftk(r["SobjectType"]) for r in rows(snap, "object_perms") if r.get("ParentId") in aud["sets"])
    if not uses_ftk:
        return
    site = aud["label"]
    for api, label in FTK_SETS.items():
        baseline.append((site, "Permission set %s assigned to the guest" % label, "yes" if api in names else "no",
                         "Every guest form" if api == "Form_Flow_User" else "Holds the org's own guest flows and classes"))
    if "guest_rules" not in snap:
        baseline.append((site, "Guest sharing rules for the form setup", "not read", "Retrieve the sharing rules (Claude Code) or read them in Setup"))
        return
    rules = [r for r in snap["guest_rules"] if r["guest_user"] in aud["site_names"] and is_ftk(r["object"])]
    for obj, what, why in (("Form_Template__c", "Form Template, Active equals True", "Every guest form; without it the form does not load"),
                           ("Form_Submission__c", "Form Submission, Is Pre-fill Template equals True", "Only templates with a Pre-fill Template"),
                           ("Form_Component__c", "Form Component, Record Type equals Record Component", "Only templates with record components")):
        found = [r for r in rules if strip_ns(r["object"]) == obj]
        baseline.append((site, "Guest rule: %s" % what, "yes" if found else "no", why))


def normalize_rules(snap):
    """A retrieve leaves the org's own namespace off file names (Form_Submission__c in an
    org whose namespace is FlowToolKit). Put it back where the object exists with it."""
    org_ns = (rows(snap, "org") or [{}])[0].get("NamespacePrefix")
    if not org_ns or "guest_rules" not in snap:
        return
    known = {r["SobjectType"] for r in rows(snap, "object_perms")}
    for rule in snap["guest_rules"]:
        obj = rule["object"]
        if obj.endswith("__c") and obj.count("__") == 1 and (org_ns + "__" + obj) in known:
            rule["object"] = org_ns + "__" + obj


def merge_probe(snap, findings):
    """Fold the outside probe's results into the findings: mark the inside findings it
    proved, and add findings for anything only the probe reached. Returns a summary for
    the report. The probe holds counts, field names and Apex shapes only, no record data."""
    probes = [p for p in snap.get("probe") or [] if p.get("reachable")]
    summary = {"ran": bool(snap.get("probe")), "sites": []}
    for p in snap.get("probe") or []:
        summary["sites"].append({"site": p.get("site"), "host": p.get("host"), "reachable": bool(p.get("reachable")),
                                 "note": p.get("note"),
                                 "objects": len(p.get("objects") or []),
                                 "apex_reachable": len([a for a in p.get("apex") or [] if a["verdict"].startswith("EXPOSED")]),
                                 "flows": len(p.get("flows") or [])})
    if not probes:
        return summary

    object_counts, apex_data, apex_callable, flows = {}, {}, {}, set()
    for p in probes:
        host = p.get("host") or p.get("site")
        for item in p.get("objects") or []:
            prev = object_counts.get(item["object"])
            if prev is None or (item.get("count") or 0) > (prev.get("count") or 0):
                object_counts[item["object"]] = {"count": item.get("count"), "host": host, "fields": len(item.get("fields") or [])}
        for a in p.get("apex") or []:
            name = ".".join(x for x in a["ref"] if x)
            if a["verdict"] == "EXPOSED-DATA":
                apex_data.setdefault(name, {"shape": a.get("detail"), "host": host, "class": a["ref"][1]})
            elif a["verdict"] == "EXPOSED-NEEDS-PARAMS":
                apex_callable.setdefault(name, {"host": host, "class": a["ref"][1]})
        flows.update(p.get("flows") or [])
    summary["flows"] = sorted(flows)

    matched_objects, matched_classes = set(), set()
    for item in findings.items:
        obj = item.get("obj")
        if obj and obj in object_counts and (object_counts[obj]["count"] or 0) > 0:
            seen = object_counts[obj]
            item["evidence"].append("Confirmed from outside: an anonymous visitor queried %d %s on %s."
                                    % (seen["count"], obj, seen["host"]))
            item["proved"] = True
            matched_objects.add(obj)
        cls = item.get("apex_class")
        if cls and (cls in {v["class"] for v in apex_data.values()} or cls in {v["class"] for v in apex_callable.values()}):
            where = next((n for n, v in apex_data.items() if v["class"] == cls), None)
            if where:
                item["evidence"].append("Confirmed from outside: an anonymous call to this class returned data (%s)." % apex_data[where]["shape"])
            else:
                item["evidence"].append("Confirmed from outside: an anonymous visitor can call this class.")
            item["proved"] = True
            matched_classes.add(cls)

    for name, info in sorted(apex_data.items()):
        if info["class"] in matched_classes:
            continue
        findings.add("HIGH", "Apex (probe)", None,
                     "An anonymous call to %s returned records" % name,
                     ["The outside probe called %s with no parameters on %s and it returned data (%s)."
                      % (name, info["host"], info["shape"]),
                      "A guest reaching records through Apex bypasses the sharing model, so object counts do not show it."],
                     ["Remove the class from the guest profile's Enabled Apex Classes unless it must be public.",
                      "If it must stay, declare it with sharing and enforce object and field access (WITH USER_MODE or stripInaccessible) on every query."])
    for name, info in sorted(apex_callable.items()):
        if info["class"] in matched_classes:
            continue
        findings.add("MEDIUM", "Apex (probe)", None,
                     "An anonymous visitor can call %s" % name,
                     ["The outside probe reached %s on %s: it ran but wanted arguments, which is the injection and exfiltration target."
                      % (name, info["host"])],
                     ["Check what the class accepts and returns; remove it from the guest profile's Enabled Apex Classes unless it must be public."])
    for obj, seen in sorted(object_counts.items()):
        if obj in matched_objects or (seen["count"] or 0) == 0:
            continue
        if is_ftk(obj) and strip_ns(obj) in (FTK_CONFIG | FTK_ANSWERS):
            continue
        high = obj in SENSITIVE_OBJECTS
        findings.add("HIGH" if high else "MEDIUM", "Records shared (probe)", None,
                     "An anonymous visitor can read %d %s records the inside audit did not flag" % (seen["count"], obj),
                     ["The outside probe queried %d %s records on %s as the guest." % (seen["count"], obj, seen["host"]),
                      "The inside audit did not flag this object, so check that the audit read every guest permission set and sharing rule."],
                     ["Confirm whether the site must show %s to the public. If not, remove Read and any guest sharing rule on it." % obj],
                     obj=obj)
    return summary


def analyze(snap):
    normalize_rules(snap)
    findings = Findings()
    baseline, objects, flows, classes = [], [], [], []
    audiences = build_audiences(snap)
    for aud in audiences:
        analyze_site(snap, aud, findings, baseline)
        analyze_sets(snap, aud, findings)
        analyze_objects(snap, aud, findings, baseline, objects)
        analyze_flows(snap, aud, findings, baseline, flows)
        analyze_apex(snap, aud, findings, classes)
        analyze_ftk_baseline(snap, aud, baseline)
    probe_summary = merge_probe(snap, findings)
    org = (rows(snap, "org") or [{}])[0]
    return {
        "org": {"id": org.get("Id"), "name": org.get("Name"), "sandbox": org.get("IsSandbox")},
        "taken_on": snap.get("taken_on"),
        "sites": [{"site": a["label"], "site_names": a["site_names"], "guest_user": a["user"].get("Username"),
                   "permission_sets": sorted(set_name(s) for s in a["sets"].values())} for a in audiences],
        "findings": findings.ordered(),
        "baseline": [{"site": s, "item": i, "status": st, "why": w} for s, i, st, w in baseline],
        "objects": objects, "flows": flows, "apex": classes,
        "probe": probe_summary,
        "rules_read": "guest_rules" in snap,
        "query_errors": snap.get("errors", {}),
    }


# ---------------------------------------------------------------- the findings file

def md_cell(text):
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def by_site(items):
    """Collapse rows that are the same on every site into one row naming all the sites."""
    merged = {}
    for item in items:
        key = json.dumps({k: v for k, v in item.items() if k != "site"}, sort_keys=True, default=str)
        if key in merged:
            merged[key]["site"] += ", " + item["site"]
        else:
            merged[key] = dict(item)
    return list(merged.values())


def render(result):
    org = result["org"]
    out = ["# Guest exposure: %s" % (org.get("name") or "Salesforce org"), "",
           "Read-only audit of what the public can reach through each site's guest user, taken %s%s." % (
               result["taken_on"], "" if org.get("sandbox") is None else (" in a sandbox" if truthy(org["sandbox"]) else " in production")),
           "It read permission sets, sharing, site settings, flows and Apex that guests can reach, and only counts of records. It changed nothing.", ""]
    findings = result["findings"]
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    out += ["| Severity | Findings |", "|---|---|"] + ["| %s | %d |" % (s, counts[s]) for s in SEVERITIES] + [""]
    if not result["sites"]:
        out += ["No site in this org has a guest user, so nothing is public through a site.", ""]
    else:
        out += ["## Sites", "", "| Site | Guest user | Permission sets |", "|---|---|---|"]
        out += ["| %s | %s | %s |" % (md_cell(s["site"]), md_cell(s["guest_user"]), md_cell(", ".join(s["permission_sets"]))) for s in result["sites"]]
        out.append("")
    if not result["rules_read"]:
        out += ["Guest sharing rule criteria were not read, so record exposure below comes from counts alone. "
                "Retrieve the sharing rules (Claude Code) or read them in Setup, Sharing Settings, to see each rule's criteria.", ""]
    out += ["## Findings", ""]
    if not findings:
        out += ["No findings.", ""]
    for f in findings:
        out += ["### %s. %s" % (f["id"], f["title"]), "",
                "%s, %s%s%s" % (f["severity"], f["area"], ", " + f["site"] if f["site"] else "",
                                " (proved by the outside probe)" if f.get("proved") else ""), ""]
        out += ["- %s" % e for e in f["evidence"]]
        out += ["", "Fix:", ""] + ["%d. %s" % (i + 1, x) for i, x in enumerate(f["fix"])] + [""]
    if result["baseline"]:
        out += ["## What a safe Flow Tool Kit guest setup has", "",
                "These are expected, not findings. A missing item breaks a guest form rather than exposing data; flow-access-fix sets each one up.", "",
                "| Site | Item | Status | Why |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % tuple(md_cell(b[k]) for k in ("site", "item", "status", "why")) for b in by_site(result["baseline"])]
        out.append("")
    if result["objects"]:
        out += ["## Objects the guest can reach", "", "| Site | Object | Access | Shared with guest | Records in org | Sharing |", "|---|---|---|---|---|---|"]
        for o in by_site(result["objects"]):
            shared = ("follows " + o["follows"]) if o.get("follows") else ("not counted" if o["shared"] is None else o["shared"])
            out.append("| %s | %s | %s | %s | %s | %s |" % tuple(md_cell(x) for x in (o["site"], o["label"], o["access"], shared, "" if o["total"] is None else o["total"], o["model"] or "")))
        out.append("")
    if result["flows"]:
        out += ["## Flows the guest can run", "", "| Site | Flow | Runs as | Active |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % tuple(md_cell(x) for x in (f["site"], f["label"] or f["flow"], MODE_WORDS.get(f["mode"], f["mode"]), "yes" if f["active"] else "no")) for f in by_site(result["flows"])]
        out.append("")
    if result["apex"]:
        out += ["## Apex the guest can reach", "", "| Site | Class | How | Summary |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % tuple(md_cell(x) for x in (c["site"], c["class"], c["how"], c["summary"])) for c in by_site(result["apex"])]
        out.append("")
    probe = result.get("probe") or {}
    if probe.get("ran"):
        out += ["## Outside probe", "",
                "Each site below was reached from its public URL as an anonymous visitor, to confirm the inside audit. "
                "The probe kept counts, field names and Apex result shapes only: no record data was read or written.", "",
                "| Site | Reached | Objects a visitor queried | Apex reachable | Flows referenced | Note |", "|---|---|---|---|---|---|"]
        for s in probe.get("sites", []):
            out.append("| %s | %s | %s | %s | %s | %s |" % tuple(md_cell(x) for x in (
                s.get("host") or s.get("site"), "yes" if s["reachable"] else "no",
                s["objects"] if s["reachable"] else "", s["apex_reachable"] if s["reachable"] else "",
                s["flows"] if s["reachable"] else "", s.get("note") or "")))
        out.append("")
        if probe.get("flows"):
            out += ["Flows the pages reference, for manual review (the probe never runs a flow): "
                    + ", ".join(probe["flows"]) + ".", ""]
        out += ["Findings marked *proved by the outside probe* were reached both ways.", ""]
    if result["query_errors"]:
        out += ["## Queries that failed", ""] + ["- %s: %s" % (k, v) for k, v in sorted(result["query_errors"].items())] + [""]
    out += ["## Not covered", "",
            "- Signed-in members (the portal audience) and staff: this audit covers site guests only.",
            "- Records a guest reaches through Apex or a system-mode flow: the Apex and Flow findings point at the code to review; read it before you call it safe.",
            "- Apex checks are pattern checks on the code. A class with no finding still deserves a read if it takes a record Id or a search value from the visitor.",
            "- The outside probe is opt-in and covers Aura-template sites (LWR sites serve no /sfsites/aura). Without it, the findings come from the inside audit alone.", ""]
    return "\n".join(out)


def write_outputs(result, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "findings.md"), "w", encoding="utf-8") as f:
        f.write(render(result))
    with open(os.path.join(out_dir, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
        f.write("\n")


# ---------------------------------------------------------------- the Salesforce CLI (Claude Code)

def sf_json(cmd, timeout=600):
    try:
        done_ = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise InputError("the Salesforce CLI (sf) is not installed. In chat, use `queries` and the Salesforce connector instead.")
    text = done_.stdout
    try:
        return json.loads(text[text.find("{"):]) if "{" in text else {}
    except json.JSONDecodeError:
        return {"status": 1, "message": (done_.stderr or text).strip()[:300]}


def sf_query(org, soql):
    if not soql.lstrip().upper().startswith("SELECT"):
        raise InputError("refusing a statement that is not a SELECT")
    data = sf_json(["sf", "data", "query", "--json", "-q", soql, "-o", org])
    if data.get("status", 1) != 0:
        raise RuntimeError((data.get("message") or "query failed").strip())
    return (data.get("result") or {}).get("records") or []


def retrieve_guest_rules(org, objects):
    """Retrieve SharingRules for the given objects into a temporary folder, parse, delete."""
    if not objects:
        return []
    tmp = tempfile.mkdtemp(prefix="guest-audit-")
    try:
        cmd = ["sf", "project", "retrieve", "start", "--json", "--target-metadata-dir", tmp, "--unzip", "-o", org]
        for obj in objects:
            cmd += ["-m", "SharingRules:" + obj]
        data = sf_json(cmd)
        if data.get("status", 1) != 0:
            raise RuntimeError((data.get("message") or "retrieve failed").strip())
        found = []
        for path in glob.glob(os.path.join(tmp, "**", "*.sharingRules*"), recursive=True):
            found += parse_rule_file(path)
        return found
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_site_probe(url, log=print):
    """Run the opt-in outside probe against one site URL, degrading to a note on any
    failure (no network in the sandbox, not an Aura site, could not reach it)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        from probe import run_probe
    except Exception as error:
        return {"site": url, "reachable": False, "note": "the probe module is unavailable: %s" % str(error)[:120]}
    try:
        return run_probe(url)
    except Exception as error:
        log("  probe %s: %s" % (url, str(error)[:160]))
        return {"site": url, "reachable": False, "note": "the probe could not run: %s" % str(error)[:160]}


def collect(org, sites, snapshot_path, query=sf_query, rules=retrieve_guest_rules, log=print,
            probe_urls=None):
    snap = new_snapshot(sites)
    snap["org_alias"] = org
    while True:
        batch = plan(snap)
        if not batch:
            break
        for key, soql in batch:
            try:
                store(snap, key, query(org, soql))
            except RuntimeError as error:
                store(snap, key, error=error)
                log("  %s: %s" % (key, str(error)[:160]))
    try:
        snap["guest_rules"] = rules(org, readable_objects(snap))
        snap["guest_rules_source"] = "metadata"
    except RuntimeError as error:
        snap["errors"]["guest_rules"] = str(error)[:500]
    for cls in rows(snap, "apex_classes") + rows(snap, "page_controllers"):
        # Keep the facts, not the code: the snapshot sits beside the findings.
        cls["facts"] = scan_apex(cls.pop("Body", None))
    for url in probe_urls or []:
        snap.setdefault("probe", []).append(run_site_probe(url, log=log))
    save_snapshot(snap, snapshot_path)
    return snap


# ---------------------------------------------------------------- commands

def default_out():
    return os.path.join("_audits", "guest-exposure-%s" % datetime.date.today().isoformat())


def cmd_queries(args):
    snap = load_snapshot(args.snapshot) if args.snapshot and os.path.exists(args.snapshot) else new_snapshot(args.site)
    if args.site:
        snap["site_filter"] = args.site
    if args.snapshot:
        save_snapshot(snap, args.snapshot)
    batch = plan(snap)
    if args.json:
        print(json.dumps([{"key": k, "soql": q} for k, q in batch], indent=1))
    elif not batch:
        print("-- nothing left to query. Next: analyze --snapshot %s" % (args.snapshot or "<file>"))
    else:
        for key, soql in batch:
            print("-- %s" % key)
            print(soql)
    return 0


def cmd_add(args):
    snap = load_snapshot(args.snapshot)
    if args.error is not None:
        store(snap, args.key, error=args.error)
    else:
        try:
            with open(args.records, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            raise InputError("cannot read records from %s: %s" % (args.records, error))
        store(snap, args.key, data)
    save_snapshot(snap, args.snapshot)
    left = plan(snap)
    print("stored %s. %d quer%s ready next." % (args.key, len(left), "y" if len(left) == 1 else "ies"))
    return 0


def cmd_collect(args):
    snap = collect(args.org, args.site, args.snapshot, probe_urls=args.probe)
    print("snapshot: %s (%d results, %d errors, %d guest rules, %d probes)" % (
        args.snapshot, len(snap["results"]), len(snap["errors"]), len(snap.get("guest_rules") or []), len(snap.get("probe") or [])))
    return 0


def cmd_probe(args):
    snap = load_snapshot(args.snapshot)
    snap.setdefault("probe", []).append(run_site_probe(args.site_url))
    save_snapshot(snap, args.snapshot)
    last = snap["probe"][-1]
    if last.get("reachable"):
        print("probe stored for %s: %d objects a visitor queried, %d Apex reachable, %d flows referenced" % (
            last.get("host"), len(last.get("objects") or []),
            len([a for a in last.get("apex") or [] if a["verdict"].startswith("EXPOSED")]), len(last.get("flows") or [])))
    else:
        print("probe stored for %s: not reached (%s)" % (args.site_url, last.get("note")))
    return 0


def report(result, out_dir):
    write_outputs(result, out_dir)
    counts = {s: sum(1 for f in result["findings"] if f["severity"] == s) for s in SEVERITIES}
    print("findings: %s" % os.path.join(out_dir, "findings.md"))
    print("  " + ", ".join("%s %d" % (s, counts[s]) for s in SEVERITIES))
    for f in result["findings"]:
        if f["severity"] in ("HIGH", "MEDIUM"):
            print("  %s %s" % (f["id"], f["title"]))
    return 1 if counts["HIGH"] else 0


def cmd_analyze(args):
    snap = load_snapshot(args.snapshot)
    return report(analyze(snap), args.out or default_out())


def cmd_audit(args):
    out_dir = args.out or default_out()
    snap = collect(args.org, args.site, os.path.join(out_dir, "snapshot.json"),
                   probe_urls=args.probe)
    return report(analyze(snap), out_dir)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("queries")
    p.add_argument("--snapshot")
    p.add_argument("--site", action="append")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_queries)

    p = sub.add_parser("add")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--key", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--records")
    group.add_argument("--error")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("rules")
    p.add_argument("--snapshot", required=True)
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("probe")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--site-url", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("collect")
    p.add_argument("--org", required=True)
    p.add_argument("--site", action="append")
    p.add_argument("--probe", action="append", help="a public site URL to confirm from outside (opt-in)")
    p.add_argument("--snapshot", required=True)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("analyze")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("audit")
    p.add_argument("--org", required=True)
    p.add_argument("--site", action="append")
    p.add_argument("--probe", action="append", help="a public site URL to confirm from outside (opt-in)")
    p.add_argument("--out")
    p.set_defaults(func=cmd_audit)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as error:
        print("guest_audit: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
