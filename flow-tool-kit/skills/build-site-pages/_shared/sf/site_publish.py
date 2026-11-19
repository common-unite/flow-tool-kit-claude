#!/usr/bin/env python3
"""Publish an Experience Cloud site and wait until the publish has finished.

    python3 site_publish.py "<site name>" [--target-org <org-alias>] [--timeout 600]

`sf community publish` only starts a publish job; this waits for the job (a BackgroundOperation record) to turn
Complete or Error and prints one line: "published <site> in Ns (<url>)" or the error. An LWR site serves what it had at
its last publish, so publish after every deploy the site shows and after every Flow Tool Kit upgrade.
Python 3 standard library only; needs the Salesforce CLI. Exit 0 when published, 1 otherwise.
"""
import argparse
import json
import subprocess
import sys
import time


def sf(*args):
    result = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    text = result.stdout[result.stdout.find("{"):] if "{" in result.stdout else "{}"
    return json.loads(text)


def address(site, org):
    """The site's public address: the publish returns the Network's own address, which for a Builder site is not where its pages live"""
    name = site.replace("\\", "\\\\").replace("'", "\\'")
    rows = (sf("data", "query", "--query", f"SELECT Domain.Domain, PathPrefix FROM DomainSite WHERE Site.SiteType = 'ChatterNetworkPicasso' AND (Site.MasterLabel = '{name}' OR Site.Name = '{name}') LIMIT 1", *org).get("result") or {}).get("records") or []
    return f"https://{rows[0]['Domain']['Domain']}{rows[0].get('PathPrefix') or ''}" if rows and rows[0].get("Domain") else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("site", help="the site's name as Setup, All Sites lists it")
    parser.add_argument("-o", "--target-org", help="org alias or username; the CLI's default org when left out")
    parser.add_argument("--timeout", type=int, default=600, help="seconds to wait (default 600)")
    args = parser.parse_args(argv)
    org = ["--target-org", args.target_org] if args.target_org else []
    started = time.time()
    published = sf("community", "publish", "--name", args.site, *org)
    result = published.get("result") or {}
    job = result.get("jobId")
    if not job:
        print(f"site_publish: {args.site}: {str(published.get('message', 'no publish job returned'))[:300]}")
        return 1
    while time.time() - started < args.timeout:
        rows = (sf("data", "query", "--query", f"SELECT Status, Error FROM BackgroundOperation WHERE Id = '{job}'", *org).get("result") or {}).get("records") or []
        status = rows[0].get("Status") if rows else None
        if status == "Complete":
            print(f"site_publish: published {args.site} in {time.time() - started:.0f}s ({address(args.site, org) or result.get('url', '')})")
            return 0
        if status in ("Error", "Canceled"):
            print(f"site_publish: {args.site} publish {status}: {(rows[0].get('Error') or '').strip()[:300]}")
            return 1
        time.sleep(5)
    print(f"site_publish: {args.site} still publishing after {args.timeout}s (job {job}); run again to wait longer")
    return 1


if __name__ == "__main__":
    sys.exit(main())
