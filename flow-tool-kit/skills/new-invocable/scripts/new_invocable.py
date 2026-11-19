#!/usr/bin/env python3
"""Scaffold and check Invocable Action Apex classes for a project's own flows.

Usage:
    python3 new_invocable.py scaffold --name "Account Giving Summary" \\
        --label "Get Account Giving Summary" --description "Totals ..." \\
        --input "accountId|Id|Account ID|The account whose giving to total.|required" \\
        --output "totalAmount|Decimal|Total Amount|The sum of the won gifts in the year." \\
        [--object Account] [--saves] \\
        [--method getGivingSummary] [--category "Riverside Actions"] \\
        [--project <project-dir>] [--classes-dir <dir>] [--api-version 62.0]
    python3 new_invocable.py check <Class_Invocable.cls | classes-dir> [--test <Class_Test.cls>]

scaffold writes four files, always together: the class, its test class and
both -meta.xml files. Each --input and --output is "name|Type|Label|Description",
and an input may end in "|required". At least one of each: Apex refuses an
action whose request or result class has no @InvocableVariable. With --object,
every query (and with --saves every save) goes through a small data-access seam,
and the test class swaps it for an in-memory mock: the tests make no records,
run no query against org data and never use SeeAllData. Fill in the TODOs. It
never overwrites a file.

check reads a class (and its test class beside it) and reports ERROR and WARN
lines. Exit codes: 0 no errors, 1 errors found, 2 bad arguments or a file that
cannot be read. It is a pattern check, not a compiler: it cannot follow a call
into another class, so read the code too.

Python 3 standard library only; runs the same in Claude Code and in a chat
code sandbox.
"""
import argparse
import glob
import json
import os
import re
import string
import sys

MAX_CLASS_NAME = 40
SUFFIX = "_Invocable"
TEST_SUFFIX = "_Test"
USER_MODE_MIN_API = 57.0
EM_DASH = chr(0x2014)
ISSUE_NUMBER = re.compile(r"#\d+")
IDENTIFIER = re.compile(r"^[A-Za-z](?:[A-Za-z0-9]|_(?!_))*$")
OBJECT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*[A-Za-z0-9]$")
CONDITION = re.compile(r"^((?:\?!?\w+)+)(?: (.*))?$")
VARIABLE_TYPE = re.compile(r"^(?:List<\s*[A-Za-z][\w.]*\s*>|[A-Za-z][\w.]*)$")

# Templates are string.Template text ($name). A line starting "?flag " is kept
# only when the flag is on, "?!flag " only when it is off; see render().
CLASS_TEMPLATE = """public with sharing class $cls {

    public class $exception extends Exception {}
?required
?required     @TestVisible private static final String MISSING_INPUT = $missing_message;
?object
?object     // Every query and save goes through this seam, so the tests swap in a mock and touch no org data
?object     @TestVisible private static DataAccess dataAccess = new DatabaseAccess();

    @InvocableMethod($annotation)
    public static List<InvokedResult> $method(List<InvokedRequest> requests) {
?object         Set<Id> recordIdSet = new Set<Id>();
?required         for (InvokedRequest request : requests) {
?required             if (request.$key == null) throw new $exception(MISSING_INPUT);
?required             recordIdSet.add(request.$key);
?required         }
?object?!required         for (InvokedRequest request : requests) if (request.$key != null) recordIdSet.add(request.$key);
?object         Map<Id, $object> recordMap = new Map<Id, $object>(dataAccess.queryRecords(recordIdSet));
?object
        List<InvokedResult> results = new List<InvokedResult>();
?saves         List<$object> recordsToUpdate = new List<$object>();
?saves         for (InvokedRequest request : requests) results.add(process(request, recordMap, recordsToUpdate));
?saves         if (!recordsToUpdate.isEmpty()) dataAccess.updateRecords(recordsToUpdate);
?object?!saves         for (InvokedRequest request : requests) results.add(process(request, recordMap));
?!object         for (InvokedRequest request : requests) results.add(process(request));
        return results;
    }

?saves     private static InvokedResult process(InvokedRequest request, Map<Id, $object> recordMap, List<$object> recordsToUpdate) {
?object?!saves     private static InvokedResult process(InvokedRequest request, Map<Id, $object> recordMap) {
?!object     private static InvokedResult process(InvokedRequest request) {
        InvokedResult result = new InvokedResult();
?object         $object record = recordMap.get(request.$key);
?object         if (record == null) return result;
?object
?object         // TODO: set this request's outputs from the record. No query, save or callout here
?saves         // TODO: set only the fields that change on the record to save
?saves         recordsToUpdate.add(new $object(Id = record.Id));
?!object         // TODO: build this request's result from its inputs. To read or save records, add the data-access seam (references/pattern.md)
        return result;
    }
?object
?object     public interface DataAccess {
?object         List<$object> queryRecords(Set<Id> recordIdSet);
?saves         void updateRecords(List<$object> records);
?object     }
?object
?object     // The only code that reaches the database: one query or save per method, because the mock-only tests never run these lines
?object     private with sharing class DatabaseAccess implements DataAccess {
?object         public List<$object> queryRecords(Set<Id> recordIdSet) {
?object             // TODO: select the fields process reads
?object             return [SELECT Id FROM $object WHERE Id IN :recordIdSet WITH USER_MODE];
?object         }
?saves
?saves         public void updateRecords(List<$object> records) {
?saves             update as user records;
?saves         }
?object     }

    public class InvokedRequest {
$inputs
    }

    public class InvokedResult {
$outputs
    }
}
"""

TEST_TEMPLATE = """@IsTest
private class $test {

    @IsTest
    static void processesOneRequest() {
?object         Id recordId = fakeId(1);
?object         MockDataAccess mock = useMock(new List<$object>{ new $object(Id = recordId) });
?object         // TODO: give the in-memory record the fields the action reads, and assert every output
?object
?object         List<$cls.InvokedResult> results = $cls.$method(new List<$cls.InvokedRequest>{ request(recordId) });
?!object         $cls.InvokedRequest request = new $cls.InvokedRequest();
?!object         // TODO: set the inputs, and assert every output
?!object
?!object         List<$cls.InvokedResult> results = $cls.$method(new List<$cls.InvokedRequest>{ request });

        Assert.areEqual(1, results.size());
?object         Assert.areEqual(1, mock.queryCount);
?object         Assert.areEqual(new Set<Id>{ recordId }, mock.queriedIdSet);
?saves         Assert.areEqual(1, mock.updatedRecords.size());
?saves         Assert.areEqual(recordId, mock.updatedRecords[0].Id);
    }
?object
?object     @IsTest
?object     static void recordNotFoundReturnsAnEmptyResult() {
?object         MockDataAccess mock = useMock(new List<$object>());
?object
?object         List<$cls.InvokedResult> results = $cls.$method(new List<$cls.InvokedRequest>{ request(fakeId(1)) });
?object
?object         Assert.areEqual(1, results.size());
?saves         Assert.areEqual(0, mock.updateCount, 'Nothing is saved when there is no record to change');
?object         // TODO: assert the outputs a request with no record returns, as their descriptions promise
?object     }
?required
?required     @IsTest
?required     static void missing${key_title}FailsTheRun() {
?required         MockDataAccess mock = useMock(new List<$object>());
?required         try {
?required             $cls.$method(new List<$cls.InvokedRequest>{ request(null) });
?required             Assert.fail($missing_assert);
?required         } catch ($cls.$exception error) {
?required             Assert.areEqual($cls.MISSING_INPUT, error.getMessage());
?required         }
?required         Assert.areEqual(0, mock.queryCount, 'Nothing is read for a run that fails');
?required     }

    @IsTest
    static void twoHundredRequestsTouchNoData() {
?object         List<$object> records = new List<$object>();
?object         List<$cls.InvokedRequest> requests = new List<$cls.InvokedRequest>();
?object         for (Integer i = 0; i < 200; i++) {
?object             records.add(new $object(Id = fakeId(i + 1)));
?object             requests.add(request(records[i].Id));
?object         }
?object         MockDataAccess mock = useMock(records);
?object         // TODO: give each record its own values, and assert each of the 200 results against its own record
?!object         List<$cls.InvokedRequest> requests = new List<$cls.InvokedRequest>();
?!object         for (Integer i = 0; i < 200; i++) requests.add(new $cls.InvokedRequest());
?!object         // TODO: give each request its own inputs, and assert each of the 200 results

        List<$cls.InvokedResult> results = $cls.$method(requests);

        Assert.areEqual(200, results.size());
?object         Assert.areEqual(1, mock.queryCount, 'One read for all 200 requests');
?object         Assert.areEqual(200, mock.queriedIdSet.size());
?saves         Assert.areEqual(1, mock.updateCount, 'One save for all 200 requests');
?saves         Assert.areEqual(200, mock.updatedRecords.size());
        Assert.areEqual(0, Limits.getQueries(), 'No query reaches the org');
        Assert.areEqual(0, Limits.getDmlStatements(), 'Nothing is written to the org');
    }
?object
?object     static $cls.InvokedRequest request(Id recordId) {
?object         $cls.InvokedRequest request = new $cls.InvokedRequest();
?object         request.$key = recordId;
?object         return request;
?object     }
?object
?object     static MockDataAccess useMock(List<$object> records) {
?object         MockDataAccess mock = new MockDataAccess();
?object         mock.records = records;
?object         $cls.dataAccess = mock;
?object         return mock;
?object     }
?object
?object     // A valid-looking $object Id. Nothing is saved, so no record has this Id in any org
?object     static Id fakeId(Integer index) {
?object         return Id.valueOf($object.SObjectType.getDescribe().getKeyPrefix() + String.valueOf(index).leftPad(12, '0'));
?object     }
?object
?object     // Stands in for the database: answers reads from the records a test gives it, keeps what the action would save, and counts the calls
?object     private class MockDataAccess implements $cls.DataAccess {
?object         public List<$object> records = new List<$object>();
?object         public Integer queryCount = 0;
?object         public Set<Id> queriedIdSet;
?saves         public Integer updateCount = 0;
?saves         public List<$object> updatedRecords = new List<$object>();
?object
?object         public List<$object> queryRecords(Set<Id> recordIdSet) {
?object             queryCount++;
?object             queriedIdSet = recordIdSet;
?object             List<$object> found = new List<$object>();
?object             for ($object record : records) if (recordIdSet.contains(record.Id)) found.add(record);
?object             return found;
?object         }
?saves
?saves         public void updateRecords(List<$object> changedRecords) {
?saves             updateCount++;
?saves             updatedRecords.addAll(changedRecords);
?saves         }
?object     }
}
"""

META_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/09/metadata">
    <apiVersion>{api}</apiVersion>
    <status>Active</status>
</ApexClass>
"""


class UsageError(Exception):
    pass


def render(template, flags, **values):
    """Keep each "?flag " line only when the flag is on ("?!flag " when off), then fill $names."""
    lines = []
    for line in template.split("\n"):
        m = CONDITION.match(line) if line.startswith("?") else None
        if m:
            conditions = m.group(1).split("?")[1:]
            if not all((c[1:] not in flags) if c.startswith("!") else (c in flags) for c in conditions):
                continue
            line = m.group(2) or ""
        lines.append(line)
    return string.Template("\n".join(lines)).substitute(values)


# ---------------------------------------------------------------- names

def class_name(raw):
    """'Account Giving Summary' or 'Account_Giving_Summary_Invocable' -> 'Account_Giving_Summary_Invocable'."""
    words = [w for w in re.split(r"[\s_\-]+", raw.strip()) if w]
    if words and words[-1].lower() == "invocable":
        words = words[:-1]
    if not words:
        raise UsageError("--name is empty")
    base = "_".join(w[0].upper() + w[1:] for w in words)
    name = base + SUFFIX
    if not IDENTIFIER.match(name):
        raise UsageError("%r is not a valid Apex class name: letters, digits and single underscores, starting with a letter" % name)
    if len(name + TEST_SUFFIX) > MAX_CLASS_NAME:
        raise UsageError("%s%s is %d characters; Apex allows %d. Shorten --name (the base can be at most %d characters)"
                         % (name, TEST_SUFFIX, len(name + TEST_SUFFIX), MAX_CLASS_NAME,
                            MAX_CLASS_NAME - len(SUFFIX) - len(TEST_SUFFIX)))
    return name


def exception_name(cls):
    return cls[: -len(SUFFIX)] + "_Exception"


def method_name(label):
    """'Get Account Giving Summary' -> 'getAccountGivingSummary'."""
    words = re.findall(r"[A-Za-z0-9]+", label)
    if not words:
        raise UsageError("cannot make a method name from %r; pass --method" % label)
    name = words[0].lower() + "".join(w[0].upper() + w[1:].lower() for w in words[1:])
    if not IDENTIFIER.match(name):
        raise UsageError("%r is not a valid Apex method name; pass --method" % name)
    return name


def text_problems(text):
    problems = []
    if EM_DASH in text:
        problems.append("contains an em-dash; use a colon, a comma or a new sentence")
    if ISSUE_NUMBER.search(text):
        problems.append("contains an issue number; describe what it does now")
    return problems


def variable_spec(text, kind):
    """'accountId|Id|Account ID|The account to total.|required' -> (name, type, label, description, required)."""
    parts = [p.strip() for p in text.split("|")]
    required = len(parts) == 5 and parts[4].lower() == "required"
    if len(parts) != 4 and not required:
        raise UsageError("--%s %r: write name|Type|Label|Description%s" % (kind, text, "[|required]" if kind == "input" else ""))
    if required and kind == "output":
        raise UsageError("--output %r: only inputs can be required" % text)
    name, type_, label, description = parts[:4]
    if not IDENTIFIER.match(name):
        raise UsageError("--%s %r: %r is not a valid Apex variable name" % (kind, text, name))
    if not VARIABLE_TYPE.match(type_):
        raise UsageError("--%s %r: %r is not an Apex type such as Id, String, Decimal, Date, Account or List<Id>" % (kind, text, type_))
    if not label or not description:
        raise UsageError("--%s %r: the label and the description are both required" % (kind, text))
    for problem in text_problems(label) + text_problems(description):
        raise UsageError("--%s %r %s" % (kind, text, problem))
    return name, type_, label, description, required


def variable_lines(specs):
    blocks = []
    for name, type_, label, description, required in specs:
        attributes = "Label=%s Description=%s" % (apex_string(label), apex_string(description))
        if required:
            attributes += " Required=true"
        blocks.append("        @InvocableVariable(%s)\n        public %s %s;" % (attributes, type_, name))
    return "\n\n".join(blocks)


def apex_string(text):
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---------------------------------------------------------------- project

def read_project(project):
    path = os.path.join(project, "sfdx-project.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def default_classes_dir(project, config):
    package_path = "force-app"
    if config:
        dirs = config.get("packageDirectories") or []
        chosen = next((d for d in dirs if d.get("default")), dirs[0] if dirs else None)
        if chosen and chosen.get("path"):
            package_path = chosen["path"]
    return os.path.join(project, package_path, "main", "default", "classes")


def existing_categories(classes_dir):
    found = {}
    for path in glob.glob(os.path.join(classes_dir, "*.cls")):
        code, raw = load_masked(path)
        for start, end in annotation_spans(code, "InvocableMethod"):
            category = annotation_attributes(raw[start:end]).get("category")
            if category:
                found[category] = found.get(category, 0) + 1
    return found


def data_access(args, inputs, label):
    """The template flags and values for the data-access seam: none without --object."""
    if args.saves and not args.object:
        raise UsageError("--saves needs --object: the object whose records the action saves")
    if not args.object:
        return set(), {"object": "", "key": "", "key_title": "", "missing_message": "", "missing_assert": ""}
    object_name = args.object.strip()
    if not OBJECT_NAME.match(object_name):
        raise UsageError("--object %r is not an object API name such as Contact or Gift__c" % object_name)
    keys = [spec for spec in inputs if spec[1] == "Id"]
    if not keys:
        raise UsageError("--object %s needs an input of type Id: the ID of the record each request is about" % object_name)
    key, _, key_label, _, key_required = keys[0]
    flags = {"object"}
    if key_required:
        flags.add("required")
    if args.saves:
        flags.add("saves")
    return flags, {
        "object": object_name,
        "key": key,
        "key_title": key[0].upper() + key[1:],
        "missing_message": apex_string("%s needs %s %s on every request. Check the value the flow passes in."
                                      % (label, "an" if key_label[:1].lower() in "aeiou" else "a", key_label)),
        "missing_assert": apex_string("A request with no %s must fail the run" % key_label),
    }


def scaffold(args):
    cls = class_name(args.name)
    test = cls + TEST_SUFFIX
    label = args.label.strip()
    description = args.description.strip()
    if not label or not description:
        raise UsageError("--label and --description are both required: they are what an admin reads in Flow Builder")
    for field, text in (("--label", label), ("--description", description), ("--category", args.category or "")):
        for problem in text_problems(text):
            raise UsageError("%s %s" % (field, problem))
    if not args.input or not args.output:
        raise UsageError("give at least one --input and one --output: Apex refuses an action whose request or result class has no @InvocableVariable")
    inputs = [variable_spec(t, "input") for t in args.input]
    outputs = [variable_spec(t, "output") for t in args.output]
    for kind, specs in (("input", inputs), ("output", outputs)):
        names = [spec[0].lower() for spec in specs]
        if len(set(names)) != len(names):
            raise UsageError("two %ss share a name" % kind)
    method = args.method or method_name(label)
    if not IDENTIFIER.match(method):
        raise UsageError("--method %r is not a valid Apex method name" % method)

    project = os.path.abspath(args.project)
    config = read_project(project)
    api = args.api_version or (config or {}).get("sourceApiVersion")
    if not api:
        raise UsageError("no sfdx-project.json with sourceApiVersion in %s; pass --api-version (the org's version, such as 62.0)" % project)
    if float(api) < USER_MODE_MIN_API:
        raise UsageError("API version %s is below %.1f, the first that compiles WITH USER_MODE; use a newer version" % (api, USER_MODE_MIN_API))
    classes_dir = os.path.abspath(args.classes_dir) if args.classes_dir else default_classes_dir(project, config)

    annotation = "Label=%s Description=%s" % (apex_string(label), apex_string(description))
    if args.category:
        annotation += " Category=%s" % apex_string(args.category.strip())
    flags, values = data_access(args, inputs, label)
    values.update(cls=cls, test=test, exception=exception_name(cls), annotation=annotation, method=method,
                  inputs=variable_lines(inputs), outputs=variable_lines(outputs))
    # The class and its test class are always written together: an action never ships without its tests
    files = {
        cls + ".cls": render(CLASS_TEMPLATE, flags, **values),
        cls + ".cls-meta.xml": META_TEMPLATE.format(api=api),
        test + ".cls": render(TEST_TEMPLATE, flags, **values),
        test + ".cls-meta.xml": META_TEMPLATE.format(api=api),
    }
    clashes = [n for n in files if os.path.exists(os.path.join(classes_dir, n))]
    if clashes:
        raise UsageError("already exists, nothing written: %s. Retrieve the org's copy and edit it, or pick another --name"
                         % ", ".join(os.path.join(classes_dir, n) for n in clashes))

    categories = existing_categories(classes_dir) if os.path.isdir(classes_dir) else {}
    os.makedirs(classes_dir, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(classes_dir, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote %s" % os.path.join(classes_dir, name))
    print("class %s, method %s, API %s" % (cls, method, api))
    others = {c: n for c, n in categories.items() if c != (args.category or "").strip()}
    if others:
        listed = ", ".join("%r (%d)" % (c, n) for c, n in sorted(others.items(), key=lambda kv: -kv[1]))
        print("note: other actions in this project use the category %s; use the same one so they group together" % listed)
    findings = check_class(os.path.join(classes_dir, cls + ".cls"), None)
    report(findings)
    return 1 if any(f[0] == "ERROR" for f in findings) else 0


# ---------------------------------------------------------------- reading Apex

def mask(source):
    """Blank comments and string contents, keeping every offset and newline, so
    patterns match code only. Quotes stay, contents become spaces."""
    out = list(source)
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if source[k] != "\n":
                    out[k] = " "
            i = j
        elif c == "'":
            j = i + 1
            while j < n and source[j] != "'":
                j += 2 if source[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                if source[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def load_masked(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        raise UsageError("cannot read %s: %s" % (path, e))
    return mask(raw), raw


def matching(code, open_index, opener="(", closer=")"):
    depth = 0
    for i in range(open_index, len(code)):
        if code[i] == opener:
            depth += 1
        elif code[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    return len(code) - 1


def line_of(code, index):
    return code.count("\n", 0, index) + 1


def annotation_spans(code, name):
    spans = []
    for m in re.finditer(r"@%s\b\s*" % name, code, re.IGNORECASE):
        start = m.end()
        if start < len(code) and code[start] == "(":
            spans.append((start, matching(code, start) + 1))
        else:
            spans.append((start, start))
    return spans


def annotation_attributes(text):
    return {k.lower(): v.replace("\\'", "'")
            for k, v in re.findall(r"(\w+)\s*=\s*'((?:\\.|[^'\\])*)'", text)}


def block_after(code, index):
    """The statement or braced block that starts at or after index."""
    i = index
    while i < len(code) and code[i].isspace():
        i += 1
    if i < len(code) and code[i] == "{":
        return i, matching(code, i, "{", "}") + 1
    depth = 0
    for j in range(i, len(code)):
        if code[j] in "([{":
            depth += 1
        elif code[j] in ")]}":
            depth -= 1
        elif code[j] == ";" and depth == 0:
            return i, j + 1
    return i, len(code)


SOQL = re.compile(r"\[\s*SELECT\b", re.IGNORECASE)
DYNAMIC_QUERY = re.compile(r"\bDatabase\s*\.\s*(query|queryWithBinds|countQuery|countQueryWithBinds|getQueryLocator|getQueryLocatorWithBinds)\s*\(", re.IGNORECASE)
DML_STATEMENT_ANY = re.compile(r"(?:^|[;{})]|\belse\b)\s*(insert|update|upsert|delete|undelete|merge)\s", re.IGNORECASE | re.MULTILINE)
DATABASE_DML = re.compile(r"\bDatabase\s*\.\s*(insert|update|upsert|delete|undelete|merge)\s*\(", re.IGNORECASE)
CALLOUT = re.compile(r"\bnew\s+Http\s*\(|\.send\s*\(\s*\w+\s*\)", re.IGNORECASE)
DESCRIBE = re.compile(r"\.getDescribe\s*\(|\bSchema\s*\.\s*describeSObjects\s*\(|\bSchema\s*\.\s*getGlobalDescribe\s*\(", re.IGNORECASE)
LOOP = re.compile(r"\b(for|while)\s*\(", re.IGNORECASE)
DO_LOOP = re.compile(r"\bdo\s*\{", re.IGNORECASE)


def per_request_work(code, start, end):
    """(kind, index) for each query, DML, callout or describe in code[start:end]."""
    found = []
    segment = code[start:end]
    for m in SOQL.finditer(segment):
        found.append(("a SOQL query", start + m.start()))
    for m in DYNAMIC_QUERY.finditer(segment):
        found.append(("a Database query", start + m.start()))
    for m in DML_STATEMENT_ANY.finditer(segment):
        found.append(("a DML statement", start + m.start(1)))
    for m in DATABASE_DML.finditer(segment):
        found.append(("a Database DML call", start + m.start()))
    for m in CALLOUT.finditer(segment):
        found.append(("a callout", start + m.start()))
    for m in DESCRIBE.finditer(segment):
        found.append(("a describe", start + m.start()))
    return found


def loop_bodies(code):
    bodies = []
    for m in LOOP.finditer(code):
        header_end = matching(code, m.end() - 1)
        bodies.append(block_after(code, header_end + 1))
    for m in DO_LOOP.finditer(code):
        brace = m.end() - 1
        bodies.append((brace, matching(code, brace, "{", "}") + 1))
    return bodies


def method_body(code, name):
    """(start, end) of the body of the method declared as name(...) { ... }, or None."""
    for m in re.finditer(r"\b%s\s*\(" % re.escape(name), code):
        close = matching(code, m.end() - 1)
        rest = code[close + 1:]
        stripped = rest.lstrip()
        if stripped.startswith("{"):
            brace = close + 1 + len(rest) - len(stripped)
            return brace, matching(code, brace, "{", "}") + 1
    return None


QUERY_KINDS = ("a SOQL query", "a Database query")
DML_KINDS = ("a DML statement", "a Database DML call")
LOAD_DATA = re.compile(r"\bTest\s*\.\s*loadData\s*\(", re.IGNORECASE)
CREATE_STUB = re.compile(r"\bTest\s*\.\s*createStub\s*\(", re.IGNORECASE)


def data_access_seam(code):
    """(interface names, spans of the classes implementing one): the seam every query and save goes through."""
    interfaces = set(re.findall(r"\binterface\s+(\w+)", code))
    spans = []
    for m in re.finditer(r"\bclass\s+\w+\s+implements\s+([\w.,\s]+?)\s*\{", code):
        names = {n.strip().split(".")[-1] for n in m.group(1).split(",")}
        if names & interfaces:
            brace = m.end() - 1
            spans.append((brace, matching(code, brace, "{", "}") + 1))
    return interfaces, spans


def api_version(class_path):
    meta = class_path + "-meta.xml"
    if not os.path.isfile(meta):
        return None
    with open(meta, encoding="utf-8") as f:
        m = re.search(r"<apiVersion>\s*([\d.]+)\s*</apiVersion>", f.read())
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- check

def check_class(path, test_path):
    findings = []

    def add(severity, code_id, index, message):
        findings.append((severity, code_id, line_of(code, index) if index is not None else None, message, path))

    code, raw = load_masked(path)
    name = os.path.basename(path)[:-4]

    if len(name) > MAX_CLASS_NAME:
        add("ERROR", "N1", None, "class name %s is %d characters; Apex allows %d" % (name, len(name), MAX_CLASS_NAME))
    if not name.endswith(SUFFIX):
        add("WARN", "N2", None, "class name does not end in %s; the suffix keeps every action class together in the class list" % SUFFIX)

    for m in re.finditer(r"\bglobal\b", code):
        add("ERROR", "S1", m.start(), "global: classes in your own org are public; global is only for managed packages")
    header = re.search(r"\bclass\s+%s\b" % re.escape(name), code)
    head_text = code[: header.start()] if header else code[:200]
    if re.search(r"\bwithout\s+sharing\b", head_text):
        add("ERROR", "S2", header.start() if header else 0, "without sharing: an action runs for the person in the flow; declare with sharing")
    elif not re.search(r"\bwith\s+sharing\b", head_text):
        add("ERROR", "S2", header.start() if header else 0, "the class does not declare with sharing")

    methods = annotation_spans(code, "InvocableMethod")
    if not methods:
        add("ERROR", "A1", None, "no @InvocableMethod")
    elif len(methods) > 1:
        add("ERROR", "A1", methods[1][0], "more than one @InvocableMethod; Apex allows one per class")
    for start, end in methods:
        attributes = annotation_attributes(raw[start:end])
        for key in ("label", "description"):
            if not attributes.get(key, "").strip():
                add("ERROR", "A2", start, "@InvocableMethod has no %s; it is what an admin reads in the Flow Builder action list" % key.capitalize())
        for key in ("label", "description", "category"):
            for problem in text_problems(attributes.get(key, "")):
                add("ERROR", "A4", start, "@InvocableMethod %s %s" % (key.capitalize(), problem))
    for start, end in annotation_spans(code, "InvocableVariable"):
        attributes = annotation_attributes(raw[start:end])
        missing = [k.capitalize() for k in ("label", "description") if not attributes.get(k, "").strip()]
        if missing:
            add("ERROR", "A3", start, "@InvocableVariable has no %s; admins see both when they map the action's inputs and outputs" % " or ".join(missing))
        for key in ("label", "description"):
            for problem in text_problems(attributes.get(key, "")):
                add("ERROR", "A4", start, "@InvocableVariable %s %s" % (key.capitalize(), problem))

    for inner in ("InvokedRequest", "InvokedResult"):
        declared = re.search(r"\bclass\s+%s\b[^{]*\{" % inner, code)
        if not declared:
            add("ERROR", "P1", None, "no inner class %s; inputs and outputs live in InvokedRequest and InvokedResult" % inner)
        elif not re.search(r"@InvocableVariable\b", code[declared.end():matching(code, declared.end() - 1, "{", "}")], re.IGNORECASE):
            add("ERROR", "P4", declared.start(), "%s has no @InvocableVariable; Apex refuses to save an action whose request or result class has none" % inner)
    if not re.search(r"\bInvokedResult\s+process\s*\(", code):
        add("WARN", "P2", None, "no process method; each request's result is built in private static InvokedResult process(...)")
    if not re.search(r"\bclass\s+\w*Exception\s+extends\s+Exception\b", code):
        add("WARN", "P3", None, "no inner custom exception; failures the flow should see get one, named <Base>_Exception")

    uses_user_mode = False
    for m in SOQL.finditer(code):
        close = matching(code, m.start(), "[", "]")
        query = code[m.start():close]
        if re.search(r"\bWITH\s+USER_MODE\b", query, re.IGNORECASE):
            uses_user_mode = True
        elif re.search(r"\bWITH\s+SYSTEM_MODE\b", query, re.IGNORECASE):
            add("WARN", "M2", m.start(), "WITH SYSTEM_MODE: reads past the person's access. Keep it only if the user agreed, return only the fields the flow needs, and say why in a comment above it")
        else:
            add("ERROR", "M1", m.start(), "query without WITH USER_MODE; every query declares its access mode")
    for m in DYNAMIC_QUERY.finditer(code):
        close = matching(code, m.end() - 1)
        if "USER_MODE" in code[m.start():close]:
            uses_user_mode = True
        elif "SYSTEM_MODE" in code[m.start():close]:
            add("WARN", "M2", m.start(), "AccessLevel.SYSTEM_MODE: keep it only if the user agreed, and say why in a comment above it")
        else:
            add("ERROR", "M1", m.start(), "Database query without AccessLevel.USER_MODE")
    for m in DML_STATEMENT_ANY.finditer(code):
        after = code[m.end(1):m.end(1) + 30]
        if re.match(r"\s+as\s+user\b", after, re.IGNORECASE):
            uses_user_mode = True
        elif re.match(r"\s+as\s+system\b", after, re.IGNORECASE):
            add("WARN", "M2", m.start(1), "%s as system: keep it only if the user agreed, and say why in a comment above it" % m.group(1))
        else:
            add("ERROR", "M1", m.start(1), "%s without as user; write %s as user ..." % (m.group(1), m.group(1)))
    for m in DATABASE_DML.finditer(code):
        close = matching(code, m.end() - 1)
        if "USER_MODE" in code[m.start():close]:
            uses_user_mode = True
        elif "SYSTEM_MODE" not in code[m.start():close]:
            add("ERROR", "M1", m.start(), "Database.%s without AccessLevel.USER_MODE" % m.group(1))

    api = api_version(path)
    if api is None:
        add("WARN", "V1", None, "no %s-meta.xml beside the class, or no apiVersion in it" % os.path.basename(path))
    elif uses_user_mode and api < USER_MODE_MIN_API:
        add("ERROR", "V1", None, "API version %.1f does not compile user mode; use %.1f or later" % (api, USER_MODE_MIN_API))

    reported = set()
    for start, end in loop_bodies(code):
        for kind, index in per_request_work(code, start, end):
            if index not in reported:
                reported.add(index)
                severity = "WARN" if kind == "a describe" else "ERROR"
                add(severity, "B1", index, "%s inside a loop; gather keys into Sets, run it once, and read the results from a Map" % kind)
    body = method_body(code, "process") if re.search(r"\bInvokedResult\s+process\s*\(", code) else None
    if body:
        for kind, index in per_request_work(code, body[0], body[1]):
            if index not in reported:
                reported.add(index)
                add("ERROR", "B2", index, "%s in process, which runs once per request; move it before the loop and pass the results in" % kind)

    interfaces, seam_spans = data_access_seam(code)
    for kind, index in per_request_work(code, 0, len(code)):
        if kind in QUERY_KINDS + DML_KINDS and not any(start <= index < end for start, end in seam_spans):
            add("ERROR", "D1", index, "%s outside the data-access seam; put every query and save in a class that implements the seam's interface, so the tests can swap it for a mock" % kind)

    for m in re.finditer(r"\bTODO\b", raw):
        add("WARN", "T1", m.start(), "TODO left in the class")
    if EM_DASH in raw:
        add("WARN", "W1", raw.index(EM_DASH), "em-dash in the file")

    test_path = test_path or os.path.join(os.path.dirname(path), name + TEST_SUFFIX + ".cls")
    if not os.path.isfile(test_path):
        findings.append(("ERROR", "T2", None, "no test class %s%s.cls beside the class" % (name, TEST_SUFFIX), path))
        return findings
    findings.extend(check_test(test_path, name, interfaces if seam_spans else ()))
    return findings


def check_test(test_path, class_name_, seam_interfaces=()):
    findings = []
    code, raw = load_masked(test_path)

    def add(severity, code_id, index, message):
        findings.append((severity, code_id, line_of(code, index) if index is not None else None, message, test_path))

    if not re.search(r"@IsTest\b", code, re.IGNORECASE):
        add("ERROR", "T3", None, "the test class has no @IsTest")
    for m in re.finditer(r"SeeAllData\s*=\s*true", code, re.IGNORECASE):
        add("ERROR", "T4", m.start(), "SeeAllData=true: tests build their own records")
    if class_name_ not in code:
        add("ERROR", "T5", None, "the test class never calls %s" % class_name_)
    if not re.search(r"\b200\b", code):
        add("ERROR", "T6", None, "no bulk test: call the action with 200 requests in one call and assert every result")
    if "Limits.getQueries()" not in code:
        add("WARN", "T7", None, "the bulk test does not check Limits.getQueries(); show that no query reaches the org")
    for kind, index in per_request_work(code, 0, len(code)):
        if kind in DML_KINDS:
            add("ERROR", "T8", index, "%s in the test; tests make no records: build them in memory, let the mock take each save and assert what it was given" % kind)
        elif kind in QUERY_KINDS:
            add("ERROR", "T9", index, "%s in the test; tests read no org data: build records in memory and let the mock answer each read" % kind)
    for m in LOAD_DATA.finditer(code):
        add("ERROR", "T8", m.start(), "Test.loadData inserts records; build them in memory instead")
    if seam_interfaces and not CREATE_STUB.search(code) and not any(
            re.search(r"\bimplements\s+%s\s*\.\s*%s\b" % (re.escape(class_name_), re.escape(i)), code) for i in seam_interfaces):
        add("ERROR", "T10", None, "the tests never swap the data-access seam; add a mock class that implements %s.%s and set it before calling the action"
            % (class_name_, sorted(seam_interfaces)[0]))
    for m in re.finditer(r"\bTODO\b", raw):
        add("WARN", "T1", m.start(), "TODO left in the test class")
    if EM_DASH in raw:
        add("WARN", "W1", raw.index(EM_DASH), "em-dash in the file")
    return findings


def report(findings):
    order = {"ERROR": 0, "WARN": 1}
    for severity, code_id, line, message, path in sorted(findings, key=lambda f: (order[f[0]], f[4] or "", f[2] or 0)):
        where = os.path.basename(path or "")
        if line:
            where += ":%d" % line
        print("%-5s %s %s: %s" % (severity, code_id, where, message))
    errors = sum(1 for f in findings if f[0] == "ERROR")
    warnings = len(findings) - errors
    print("%d error(s), %d warning(s)" % (errors, warnings))


def check(args):
    target = args.path
    if os.path.isdir(target):
        candidates = [p for p in sorted(glob.glob(os.path.join(target, "*.cls")))
                      if not os.path.basename(p)[:-4].endswith(TEST_SUFFIX)
                      and annotation_spans(load_masked(p)[0], "InvocableMethod")]
        if not candidates:
            raise UsageError("no class with @InvocableMethod in %s" % target)
        if args.test and len(candidates) > 1:
            raise UsageError("--test needs a single class, not a folder")
    elif os.path.isfile(target) and target.endswith(".cls"):
        candidates = [target]
    else:
        raise UsageError("%s is not a .cls file or a folder" % target)
    findings = []
    for path in candidates:
        findings.extend(check_class(path, args.test))
    report(findings)
    return 1 if any(f[0] == "ERROR" for f in findings) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scaffold", help="write a new action class, its test class and both meta files")
    s.add_argument("--name", required=True, help="what the class is about, such as 'Account Giving Summary'; _Invocable is added")
    s.add_argument("--label", required=True, help="the action's name in Flow Builder, a verb phrase such as 'Get Account Giving Summary'")
    s.add_argument("--description", required=True, help="summary-first text an admin reads in Flow Builder")
    s.add_argument("--input", action="append", help="an input as name|Type|Label|Description[|required]; repeat for each")
    s.add_argument("--output", action="append", help="an output as name|Type|Label|Description; repeat for each")
    s.add_argument("--method", help="the @InvocableMethod name, a verb such as getGivingSummary (default: from --label)")
    s.add_argument("--category", help="optional group in the Flow Builder action list; match the project's other actions")
    s.add_argument("--object", help="the object whose records the action reads, such as Contact; adds the data-access seam and its mock (needs an input of type Id)")
    s.add_argument("--saves", action="store_true", help="the action also updates those records; adds a save to the seam and to its mock")
    s.add_argument("--project", default=".", help="the project folder holding sfdx-project.json (default: current folder)")
    s.add_argument("--classes-dir", help="where to write (default: <default package>/main/default/classes)")
    s.add_argument("--api-version", help="API version for the meta files (default: sourceApiVersion in sfdx-project.json)")

    c = sub.add_parser("check", help="check a class against the pattern")
    c.add_argument("path", help="the action's .cls file, or a classes folder to check every action in it")
    c.add_argument("--test", help="the test class, when it is not <Class>_Test.cls beside the class")

    args = parser.parse_args(argv)
    try:
        return scaffold(args) if args.command == "scaffold" else check(args)
    except UsageError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
