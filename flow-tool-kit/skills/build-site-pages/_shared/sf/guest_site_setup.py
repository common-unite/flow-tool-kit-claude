#!/usr/bin/env python3
"""Give an Experience Cloud site's guest user what its pages and forms need, then publish.

    python3 guest_site_setup.py "<site name>" --permsets <PermSet>[,<PermSet>] [--sharing <metadata path>]
        [--target-org <org-alias>] [--no-publish]

One line per step, stopping at the first failure (exit 1):
1. find the site's guest user (Site.GuestUserId);
2. assign each permission set it does not hold yet (a packaged one with its namespace, FlowToolKit__<Name>);
3. deploy the guest sharing rules at --sharing (an <Object>.sharingRules-meta.xml or a folder of them);
4. publish the site and wait (site_publish.py, beside this file).
The site's own public access setting and the Network's guest file access go in the site deploy, not here.
Python 3 standard library only; needs the Salesforce CLI.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def sf(*args):
    result = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    text = result.stdout[result.stdout.find("{"):] if "{" in result.stdout else "{}"
    return json.loads(text)


def query(soql, org):
    return (sf("data", "query", "--query", soql, *org).get("result") or {}).get("records") or []


def quoted(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("site", help="the site's name or label")
    parser.add_argument("--permsets", default="", help="comma-separated permission set API names for the guest user")
    parser.add_argument("--sharing", help="guest sharing rules to deploy: a sharingRules file or a folder of them")
    parser.add_argument("-o", "--target-org", help="org alias or username; the CLI's default org when left out")
    parser.add_argument("--no-publish", action="store_true", help="skip the publish")
    args = parser.parse_args(argv)
    org = ["--target-org", args.target_org] if args.target_org else []
    sites = query(f"SELECT GuestUserId, GuestUser.Username FROM Site WHERE MasterLabel = {quoted(args.site)} OR Name = {quoted(args.site)} LIMIT 1", org)
    if not sites or not sites[0].get("GuestUserId"):
        print(f"guest_site_setup: no site or guest user named {args.site!r}", flush=True)
        return 1
    guest_id, guest = sites[0]["GuestUserId"], sites[0]["GuestUser"]["Username"]
    print(f"guest_site_setup: guest user {guest}", flush=True)
    wanted = [name.strip() for name in args.permsets.split(",") if name.strip()]
    if wanted:
        names = ", ".join(quoted(name.split("__")[-1]) for name in wanted)
        held = {row["PermissionSet"]["Name"] for row in query(f"SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '{guest_id}' AND PermissionSet.Name IN ({names})", org)}
        missing = [name for name in wanted if name.split("__")[-1] not in held]
        for name in missing:
            assigned = sf("org", "assign", "permset", "--name", name, "--on-behalf-of", guest, *org)
            failures = (assigned.get("result") or {}).get("failures") or []
            if assigned.get("status", 0) != 0 or failures:
                print(f"guest_site_setup: assigning {name} failed: {str((failures[0] if failures else assigned).get('message', ''))[:300]}", flush=True)
                return 1
        print(f"guest_site_setup: permission sets: {len(wanted) - len(missing)} already held, {len(missing)} assigned", flush=True)
    if args.sharing:
        deployed = sf("project", "deploy", "start", "--source-dir", args.sharing, "--wait", "30", *org)
        if deployed.get("status", 0) != 0:
            print(f"guest_site_setup: deploying {args.sharing} failed: {str(deployed.get('message', ''))[:300]}", flush=True)
            return 1
        print(f"guest_site_setup: guest sharing rules deployed from {args.sharing}", flush=True)
    if args.no_publish:
        return 0
    return subprocess.run([sys.executable, str(HERE / "site_publish.py"), args.site, *org]).returncode


if __name__ == "__main__":
    sys.exit(main())
