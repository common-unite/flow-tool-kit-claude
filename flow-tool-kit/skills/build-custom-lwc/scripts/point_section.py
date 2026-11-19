#!/usr/bin/env python3
"""Point a Form Template page section at a custom component, and give it the admin's form to render.

Usage:
    python3 point_section.py --section <page section Id> --component c:feeSummarySection
        [--form <form component API name> | --form-json <file with the form's JSON>]
        [--form-object <object>] [--org <org-alias>] [--dry-run]

Sets Component Type to Lightning Web Component and LWC Component Name on the section. With --form or
--form-json it also stores the form the component renders, exactly as the section editor stores it,
because the editor hides its form picker once a section's type is Lightning Web Component.

--dry-run (or no --org) prints the field values instead of saving them: in chat, write them with the
Salesforce connector. Saving needs the Salesforce CLI. Python 3 standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

NS = "FlowToolKit__"
SECTION_OBJECT = NS + "Form_Template_Page_Section__c"
SUBMISSION_OBJECT = NS + "Form_Submission__c"
API_VERSION = "v64.0"
COMPONENT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*:[a-z][A-Za-z0-9_]*$")
SECTION_ID = re.compile(r"^[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?$")


def section_fields(component, form=None, form_json=None, form_object=SUBMISSION_OBJECT):
    """The section field values to save; raises ValueError on a value the form could never load."""
    if not COMPONENT_NAME.match(component or ""):
        raise ValueError(f"{component!r} is not a full component name: write namespace:componentName, such as c:feeSummarySection")
    if form and form_json:
        raise ValueError("give --form or --form-json, not both")
    fields = {NS + "Component_Type__c": "Lightning Web Component", NS + "lwcComponentName__c": component}
    if form:
        fields[NS + "FormQualifiedApiName__c"] = form
        fields[NS + "FormConfigJSON__c"] = json.dumps({"formSelectionMode": "component", "formQualifiedApiName": form, "object": form_object})
    elif form_json is not None:
        try:
            parsed = json.loads(form_json)
        except json.JSONDecodeError as error:
            raise ValueError(f"the form JSON does not parse: {error}") from None
        if not isinstance(parsed, dict):
            raise ValueError("the form JSON must be one form component's configuration (an object)")
        fields[NS + "FormConfigJSON__c"] = json.dumps({"formSelectionMode": "custom", "object": form_object, "formJsonConfig": json.dumps(parsed)})
    return fields


def save(org, section_id, fields):
    url = f"/services/data/{API_VERSION}/sobjects/{SECTION_OBJECT}/{section_id}"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as body:
        json.dump(fields, body)
    try:
        result = subprocess.run(["sf", "api", "request", "rest", url, "--method", "PATCH", "--body", "@" + body.name, "--target-org", org],
                                capture_output=True, text=True)
    finally:
        os.unlink(body.name)
    if result.returncode != 0 or "errorCode" in result.stdout:
        raise RuntimeError((result.stdout + result.stderr).strip() or "the update failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--section", required=True, help="the page section's record Id")
    parser.add_argument("--component", required=True, help="the component's full name, such as c:feeSummarySection")
    parser.add_argument("--form", help="API name of the form component the custom component renders")
    parser.add_argument("--form-json", help="file holding the form's JSON (a form-only section)")
    parser.add_argument("--form-object", default=SUBMISSION_OBJECT, help="the object the form is built on (default Form Submission)")
    parser.add_argument("--org", help="org alias; without it nothing is saved")
    parser.add_argument("--dry-run", action="store_true", help="print the values, save nothing")
    args = parser.parse_args(argv)

    if not SECTION_ID.match(args.section):
        print(f"error: {args.section!r} is not a record Id", file=sys.stderr)
        return 2
    try:
        form_json = open(args.form_json, encoding="utf-8").read() if args.form_json else None
        fields = section_fields(args.component, args.form, form_json, args.form_object)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(json.dumps({"object": SECTION_OBJECT, "Id": args.section, "fields": fields}, indent=1))
    if args.dry_run or not args.org:
        print("Not saved. Save these values on the page section (connector, or rerun with --org).")
        return 0
    try:
        save(args.org, args.section, fields)
    except (OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("Saved. Open the template's Preview Form to see the section.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
