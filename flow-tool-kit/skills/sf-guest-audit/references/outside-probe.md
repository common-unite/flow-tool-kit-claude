# The outside probe

The inside audit reads what the org's setup allows a guest. The outside probe confirms it from the public site URL, the way a visitor's browser would, so a finding is proven, not only inferred. It is `scripts/probe.py`, run on its own or through `guest_audit.py` (`audit --probe`, or `probe` then `analyze`).

## When to turn it on

- Only against a site you own or are engaged to test, and name. While building, that is a scratch org's own site. Never point it at a site you do not own or administer, and never at a third party's site.
- Worth it when you want proof a specific exposure is reachable by a real anonymous visitor (a record count, an Apex method that returns data), or to catch something the setup read could miss (an Apex controller that returns records the sharing model would never allow).
- Leave it off when the inside audit is enough, when the machine has no outbound network, or when the site is LWR (it has no probeable endpoint).

## What it does

1. Requests the site's landing URL logged out and reads its Aura context. An LWR site has no `/sfsites/aura`, so the probe reports that cleanly and stops; the inside audit still covers the site.
2. As the anonymous guest (`aura.token=null`), tries each object in `objects/standard.txt` and `objects/nonprofit.txt`, plus any custom object named in the page markup, through the `uiapi` GraphQL endpoint, and keeps the ones the guest can query with their record count and the field names the guest can read.
3. Scrapes the served JavaScript for the `@AuraEnabled` Apex methods and the Flows the pages reference. It read-only invokes each Apex method with empty parameters and classifies it: `EXPOSED-DATA` (returned records to an anonymous call), `EXPOSED-NEEDS-PARAMS` (ran but wants arguments, so it is callable), or no access. It never runs a Flow (flows have side effects); it lists them for manual review.

## What it keeps, and what it never keeps

- **Counts and names only.** How many records the guest can query per object, the field names, and the shape of an Apex result (a list of N, the keys). These prove reach without holding anyone's data.
- **No record value, ever.** It does not dump records, and `analyze` writes none to the findings or the snapshot.
- **No file download.** A file object (Attachment, ContentVersion, ContentDocument, Document) the guest can query is reported as a count and the fact that file metadata is reachable. The probe does not fetch a file body.

This is the deliberate reduction from a raw black-box scanner: proof of reach, never a copy of the data.

## How it merges

`analyze` folds the probe into the one findings file:
- An inside finding about an object the probe could query, or an Apex class the probe reached, is marked **proved by the outside probe**, with a line naming what the visitor reached.
- An Apex method that returned data to an anonymous call, or that is callable, becomes its own finding (area "Apex (probe)") when the inside audit did not already name that class, since a guest reaching records through Apex bypasses the sharing model and the object counts do not show it.
- An object the probe could query that the inside audit did not flag becomes a finding too, with the note to check that the audit read every guest permission set and sharing rule.
- The "Outside probe" section lists each site: reached or not, how many objects a visitor queried, how many Apex methods were reachable, the Flows referenced, and the reason when a site could not be probed.

## Running it

```bash
# As part of the audit, one --probe per site:
python3 scripts/guest_audit.py audit --org <org-alias> \
    --probe "https://<host>.my.site.com/<prefix>/s" --out _audits/guest-exposure-<date>

# Against an existing snapshot:
python3 scripts/guest_audit.py probe --snapshot snapshot.json \
    --site-url "https://<host>.my.site.com/<prefix>/s"

# Standalone, writing just the probe result:
python3 scripts/probe.py "https://<host>.my.site.com/<prefix>/s" --out probe.json
```

The landing URL is the one that renders the community, usually ending in `/s` (`https://<host>.my.site.com/<prefix>/s`). The probe always verifies the site's TLS certificate and offers no way to turn that off: Salesforce sites, scratch org sites included, serve valid certificates. If a certificate does not verify, the probe stops and says so, and the inside audit stands.

## Limits

- **Aura-template sites only.** LWR sites serve no `/sfsites/aura`.
- **Dictionary bounded.** A custom object not in `objects/*.txt` and not named in the page markup is not tried. Extend the dictionaries when a client has objects they do not cover.
- **Apex harvest is scrape bounded.** It sees the Apex descriptors that appear in the served page and its static bundles. A site that loads page code dynamically may hand the harvest fewer references, so "no Apex found" means "not found by this method", not "no guest-reachable Apex". The inside audit's read of the guest profile's Enabled Apex Classes is the complete list.
- **No network, no probe.** In a sandbox with no outbound access the probe notes it could not run; the inside audit stands alone.
