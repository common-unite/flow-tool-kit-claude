#!/usr/bin/env python3
"""Check a custom section component against the Flow Tool Kit section contract and style rules.

Usage:
    python3 check_lwc.py <bundle-folder> [<bundle-folder> ...] [--json]

A bundle folder is lwc/<componentName>. Prints one line per finding,
"error|warning <file>:<line>: <message>", and exits 1 when any error is found.
Python 3 standard library only, so it runs in chat's code sandbox too.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(HERE, "style_tokens.json")

INPUTS = ("record", "objectApiName", "review", "disableAll", "relatedRecords", "recordTemplate", "section")
REQUIRED_INPUTS = ("record", "objectApiName")
CONTRACT_EVENTS = ("formfieldchange", "relatedrecordchange")
HAND_BUILT_INPUTS = ("lightning-input", "lightning-input-field", "lightning-combobox", "lightning-textarea",
                     "lightning-radio-group", "lightning-checkbox-group", "lightning-dual-listbox")
ALLOW_INPUTS_MARK = "custom-lwc: allow-inputs"


def load_style_names():
    with open(TOKENS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {t["name"] for t in data["tokens"]}, set(data.get("theme_variables", {})), data.get("private_prefix", "--_ftk-")


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def strip_comments(js):
    """Blank out comments but keep every newline, so line numbers still match."""
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))
    return re.sub(r"/\*.*?\*/|//[^\n]*", blank, js, flags=re.S)


def call_body(text, open_paren):
    """The text inside the parentheses that start at open_paren, or the rest of the text."""
    depth = 0
    for i in range(open_paren, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1:i]
    return text[open_paren + 1:]


def check_js(path, findings):
    raw = open(path, encoding="utf-8").read()
    js = strip_comments(raw)
    name = os.path.basename(path)
    is_main = name == os.path.basename(os.path.dirname(path)) + ".js"

    for match in re.finditer(r"""import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""", js):
        module = match.group(1)
        if module.lower().startswith("flowtoolkit/"):
            findings.append(("error", path, line_of(js, match.start()),
                             f"imports {module}: Flow Tool Kit's modules are internal to the package. Use the <FlowToolKit-flow-form> tag in the template and the --ftk- style variables instead"))

    for match in re.finditer(r"new\s+CustomEvent\s*\(\s*['\"]([a-z]+)['\"]", js):
        event = match.group(1)
        body = call_body(js, js.index("(", match.start()))
        line = line_of(js, match.start())
        if event in CONTRACT_EVENTS:
            for flag in ("bubbles", "composed"):
                if not re.search(rf"\b{flag}\s*:\s*true\b", body):
                    findings.append(("error", path, line, f"{event} needs {flag}: true, or it never leaves the component and the form never hears it"))
        if event == "formfieldchange" and re.search(r"\bfieldName\s*:", body) and not re.search(r"\bfieldApiName\b", body):
            findings.append(("error", path, line, "formfieldchange detail must name the field as fieldApiName; a Form Component section ignores fieldName"))
        if event == "relatedrecordchange" and not re.search(r"\baction\b", body):
            findings.append(("warning", path, line, "relatedrecordchange detail needs action ('add', 'update' or 'remove') and record"))
    if re.search(r"new\s+CustomEvent\s*\(\s*([A-Za-z_$][\w$]*)\s*,", js):
        findings.append(("warning", path, 1, "an event name held in a variable cannot be checked; make sure formfieldchange and relatedrecordchange are sent with bubbles and composed"))

    if not is_main:
        return
    declared = set(re.findall(r"@api\s+(?:get\s+|set\s+)?([A-Za-z_$][\w$]*)", js))
    for prop in REQUIRED_INPUTS:
        if prop not in declared:
            findings.append(("error", path, 1, f"declare @api {prop}: the form sets it on every section component"))
    missing = [p for p in INPUTS if p not in REQUIRED_INPUTS and p not in declared]
    if missing:
        findings.append(("warning", path, 1, "declare every input the form can set (" + ", ".join(missing) +
                         "), with defaults, so one component works on both surfaces"))
    if re.search(r"\bvalidate\s*\(\s*\)\s*\{", js) and "validate" not in declared:
        findings.append(("error", path, 1, "validate() must be public (@api validate()) or the form never calls it"))
    for prop in ("record", "relatedRecords", "section"):
        assigned = re.search(rf"this\.{prop}\b\s*(?:\[[^\]]*\]|\.[\w$]+)?\s*=(?!=)", js)
        if assigned:
            findings.append(("error", path, line_of(js, assigned.start()),
                             f"never assign to this.{prop}: the form owns it. Send a change event, or copy it first ({{...this.{prop}}})"))
    mutated = re.search(r"this\.relatedRecords\s*\.\s*(?:push|splice|pop|shift|unshift|sort|reverse)\s*\(", js)
    if mutated:
        findings.append(("error", path, line_of(js, mutated.start()), "never change relatedRecords in place: send relatedrecordchange with add, update or remove"))


def check_html(path, findings):
    html = open(path, encoding="utf-8").read()
    if ALLOW_INPUTS_MARK not in html:
        for tag in HAND_BUILT_INPUTS:
            for match in re.finditer(rf"<{tag}[\s>]", html):
                findings.append(("warning", path, line_of(html, match.start()),
                                 f"<{tag}> draws an input by hand. Render the admin's form with <FlowToolKit-flow-form is-extension> and keep code for behavior; "
                                 f"if the widget truly has no Flow Tool Kit control, add the comment <!-- {ALLOW_INPUTS_MARK} -->"))
    for match in re.finditer(r"<FlowToolKit-flow-form\b([^>]*)>", html, flags=re.I):
        attributes = match.group(1)
        line = line_of(html, match.start())
        if not re.search(r"\bis-extension\b", attributes):
            findings.append(("error", path, line, "<FlowToolKit-flow-form> needs is-extension, or it reports changes to Flow instead of to this component"))
        if "onrecordchange" not in attributes:
            findings.append(("error", path, line, "<FlowToolKit-flow-form> needs onrecordchange, to pass each changed field on as a formfieldchange"))
        if "form-qualified-api-name" not in attributes and "form-j-s-o-n" not in attributes:
            findings.append(("error", path, line, "<FlowToolKit-flow-form> needs form-qualified-api-name and form-j-s-o-n from the section, or it has no form to draw"))
        elif "form-j-s-o-n" not in attributes or "form-qualified-api-name" not in attributes:
            findings.append(("warning", path, line, "pass both form-qualified-api-name and form-j-s-o-n: a section holds its form in either field"))
        if re.search(r"\brecord\s*=\s*\{record\}", attributes):
            findings.append(("warning", path, line, "give <FlowToolKit-flow-form> a copy of record replaced only when a value changes: the admin's section preview rebuilds the record on every broadcast, and passing it straight through loops"))
        for flag in ("review", "disable-all"):
            if not re.search(rf"\b{flag}\s*=", attributes):
                findings.append(("warning", path, line, f"pass {flag} to <FlowToolKit-flow-form>, so the admin's form is read-only when the section is"))


def check_css(path, findings, tokens, theme_vars, private_prefix):
    css = strip_comments(open(path, encoding="utf-8").read())
    for match in re.finditer(r"var\(\s*(--[\w-]+)\s*(,)?", css):
        name, has_fallback = match.group(1), match.group(2)
        line = line_of(css, match.start())
        if name.startswith(private_prefix):
            findings.append(("error", path, line, f"{name} is private to the package and can change in any release; use a Form Style variable"))
            continue
        if name.startswith("--ftk-") and name not in tokens:
            findings.append(("error", path, line, f"{name} is not a Form Style setting; it is internal to the package. See references/style-variables.md"))
            continue
        if (name in tokens or name in theme_vars) and not has_fallback:
            findings.append(("error", path, line, f"var({name}) needs a fallback: the variable exists only where an admin or a theme set it"))


def check_meta(path, findings):
    meta = open(path, encoding="utf-8").read()
    if not re.search(r"<isExposed>\s*true\s*</isExposed>", meta):
        findings.append(("warning", path, 1, "set isExposed to true: Flow Tool Kit loads the component from its own namespace"))
    if not re.search(r"<description>\s*\S", meta):
        findings.append(("warning", path, 1, "add a description: what the component shows, and where an admin places it"))
    if re.search(r"<capability>\s*lightning__dynamicComponent", meta):
        findings.append(("warning", path, 1, "a section component needs no lightning__dynamicComponent capability; Flow Tool Kit's renderer has it"))


def check_bundle(folder, tokens, theme_vars, private_prefix):
    findings = []
    folder = os.path.normpath(folder)
    name = os.path.basename(folder)
    if not os.path.isdir(folder):
        return [("error", folder, 1, "not a folder")]
    main_js = os.path.join(folder, name + ".js")
    meta = os.path.join(folder, name + ".js-meta.xml")
    if not os.path.isfile(main_js):
        findings.append(("error", folder, 1, f"missing {name}.js: the folder name and the file names must match"))
    if not os.path.isfile(meta):
        findings.append(("error", folder, 1, f"missing {name}.js-meta.xml"))
    else:
        check_meta(meta, findings)
    for entry in sorted(os.listdir(folder)):
        path = os.path.join(folder, entry)
        if entry.endswith(".js"):
            check_js(path, findings)
        elif entry.endswith(".html"):
            check_html(path, findings)
        elif entry.endswith(".css"):
            check_css(path, findings, tokens, theme_vars, private_prefix)
    tests = os.path.join(folder, "__tests__")
    if not (os.path.isdir(tests) and any(f.endswith(".test.js") for f in os.listdir(tests))):
        findings.append(("warning", folder, 1, "no Jest test in __tests__: test the events, the read-only modes and validate()"))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundles", nargs="+", help="lwc/<componentName> folders")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    args = parser.parse_args(argv)
    tokens, theme_vars, private_prefix = load_style_names()
    findings = []
    for bundle in args.bundles:
        findings += check_bundle(bundle, tokens, theme_vars, private_prefix)
    errors = sum(1 for f in findings if f[0] == "error")
    if args.json:
        print(json.dumps([{"level": l, "file": p, "line": n, "message": m} for l, p, n, m in findings], indent=1))
    else:
        for level, path, line, message in findings:
            print(f"{level} {path}:{line}: {message}")
        print(f"{errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
