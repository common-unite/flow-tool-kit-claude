#!/usr/bin/env python3
"""The answers PDF's running user: the Platform Event Subscriber Config the confirmation email needs.

    python3 runninguser.py --user <username> --out <project-dir> [--org <org-alias>]

With Attach PDF to Confirmation Email on, the confirmation email is sent by the conversion, which runs on the Form
Submission Convert platform event trigger. Salesforce runs that trigger as the Automated Process user unless a running
user is named, and Automated Process cannot open the page that draws the PDF. The email then goes without the PDF and
the submission's Conversion Log says so. Naming a regular user fixes it; nothing else in the conversion changes except
that records it creates show that user as creator and owner.

Salesforce has no Setup screen that creates the config: it is deployed as metadata. This script writes the file, checks
the user (with --org: active, and a System Administrator), and prints the remaining steps:

    1. Deploy it: sf project deploy start --source-dir <project-dir>/force-app/main/default/platformEventSubscriberConfigs --target-org <org-alias>
    2. Setup, Platform Events, Form Submission Convert, Subscriptions, Manage next to Form_Submission_Convert:
       Suspend and confirm, then Resume and confirm. Resume processes any event that arrived meanwhile.
    3. Check: the Subscriptions list shows the user in the User column, and a test submission's confirmation arrives
       with the PDF attached.

If that user is ever deactivated, run this again with another one.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sforg import BuildError, Org  # noqa: E402

CONSUMER = "FlowToolKit__Form_Submission_Convert"
NAME = "Form_Submission_Convert_Running_User"


def config_xml(username: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<PlatformEventSubscriberConfig xmlns="http://soap.sforce.com/2006/04/metadata">\n'
            "    <masterLabel>Form Submission Convert Running User</masterLabel>\n"
            f"    <platformEventConsumer>{CONSUMER}</platformEventConsumer>\n"
            f"    <user>{html.escape(username)}</user>\n</PlatformEventSubscriberConfig>\n")


def check_user(org, username: str) -> list[str]:
    rows = org.query(f"SELECT IsActive, Profile.Name FROM User WHERE Username = '{username}'")
    if not rows:
        return [f"No user {username} in this org."]
    problems = []
    if not rows[0].get("IsActive"):
        problems.append(f"{username} is not active.")
    if (rows[0].get("Profile") or {}).get("Name") != "System Administrator":
        problems.append(f"{username} has the {(rows[0].get('Profile') or {}).get('Name')} profile; the docs ask for a System Administrator.")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the Form Submission Convert running user config")
    parser.add_argument("--user", required=True, help="an active System Administrator's username who will stay active")
    parser.add_argument("--out", required=True, help="the SFDX project folder")
    parser.add_argument("--org", help="check the user in this org first")
    args = parser.parse_args(argv)
    if args.org:
        try:
            problems = check_user(Org(args.org), args.user)
        except BuildError as error:
            problems = [str(error)]
        if problems:
            sys.exit("runninguser: " + " ".join(problems))
    path = pathlib.Path(args.out) / "force-app" / "main" / "default" / "platformEventSubscriberConfigs" / f"{NAME}.platformEventSubscriberConfig-meta.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_xml(args.user))
    print(json.dumps({"written": str(path), "next": [
        f"sf project deploy start --source-dir {path.parent} --target-org <org-alias>",
        "Setup, Platform Events, Form Submission Convert, Subscriptions, Manage: Suspend, then Resume",
        "Check the User column shows the user, then submit a test form and open the confirmation email's PDF"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
