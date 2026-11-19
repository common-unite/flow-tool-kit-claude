# What the audit reads

Every read is a SELECT on setup data, or a count of records. Nothing is written to the org. `scripts/guest_audit.py queries` prints these with the real Ids filled in, in the order their inputs become known; this page explains them.

## The queries

| Key | Reads | Answers |
|---|---|---|
| `org` | Organization: name, sandbox or not, the org's own namespace | The heading, and how to match sharing rule files to objects |
| `sites` | Site: every site with a guest user, its status, path, and the standard lookup, search, Support API and Payments API options | Which guest users exist, and site settings that open extra doors |
| `networks` | Network: Allow guest users to access public APIs, Let guest users view asset files, Let guest users see other members, self-registration | The Experience Cloud guest settings (Workspaces, Administration, Preferences) |
| `guest_users` | User: each guest user, active or not, its profile | Who the public runs as |
| `guest_groups` | Group of type GuestUserGroup for each guest user | The group guest sharing rules share records with |
| `assignments` | PermissionSetAssignment for each guest user | The guest profile's own set and every permission set (or group) assigned |
| `set_perms` | PermissionSet: View All Data, Modify All Data, View All Users, Query All Files, View Setup, API Enabled, Run Flows | System permissions no guest should hold |
| `object_perms` | ObjectPermissions on those sets | Read, Create, Edit, Delete, View All, Modify All per object |
| `grants` | SetupEntityAccess on those sets, for Apex classes, Visualforce pages and flows | What code a guest can reach |
| `entities` | EntityDefinition for every object a guest can read | Its label, and whether its sharing follows a parent record |
| `field_perms` | FieldPermissions with Read, on those objects | Which fields a guest can read |
| `parents` | FieldDefinition: the master-detail fields of readable objects whose sharing follows a parent | Which parent's guest rules expose them (Volunteer Shift follows Volunteer Job, which follows Campaign) |
| `guest_shares:<Object>` | `SELECT UserOrGroupId, COUNT(Id) n FROM <Object>Share WHERE RowCause = 'GuestRule' ...` | How many records guest sharing rules share with each site, today |
| `total:<Object>` | `SELECT COUNT(Id) n FROM <Object>`, only for objects with records shared | Whether a rule shares every record |
| `prefill_templates` | Count of Form Submissions that are Pre-fill Templates | Whether the Form Submissions a guest can read are only Pre-fill Templates |
| `apex_classes`, `page_controllers` | ApexClass name, namespace and body, for granted classes and the controllers of granted pages | Sharing keyword, entry points, system mode, run-time queries. A managed package's body reads "(hidden)" |
| `pages` | ApexPage name and controller | Visualforce pages the guest can open |
| `flows`, `flow_versions` | FlowDefinitionView and FlowVersionView for granted flows | Which flows a guest runs, and in which context |

Guest sharing rules share records through share rows with the reason `GuestRule`, given to the site's guest user group. So the counts above are exactly what the rules expose now, with no need to read any record. An object whose sharing follows another record has no share rows of its own: a master-detail child follows its parent (up the chain to the first object with its own sharing), and Campaign Members follow their Campaign. The audit counts the shares on that parent instead, and a guest who can read the child sees it on every shared parent. A junction object with two parents counts the smaller of the two.

Not read: any field value of any record, user passwords or sessions, debug logs, and anything about signed-in members.

This page is the setup audit. The live guest pass ([live-pass.md](live-pass.md)) is different: it is a visitor, so it sees whatever values the site sends a visitor, keeps them only in the capture in the project folder, and reports field names and value kinds. The flow review ([flow-review.md](flow-review.md)) reads flow metadata only.

The opt-in outside probe (`references/outside-probe.md`) reads the public site the same way a visitor's browser would, and keeps counts, field names and Apex result shapes only. Its results, when present, sit in the snapshot under `probe` and are folded into the findings by `analyze`.

## Guest sharing rule criteria

Criteria are metadata; no query reaches them.

- **Claude Code:** `audit` and `collect` retrieve `SharingRules:<Object>` for each object a guest can read into a temporary folder, read the guest rules, and delete the folder. Rules from files you already have: `guest_audit.py rules --snapshot snapshot.json force-app/main/default/sharingRules/*.sharingRules-meta.xml`.
- **Chat:** ask the person to open Setup, Sharing Settings, and for each object the audit shows records shared, the Sharing Rules list for that object: the guest rules name the site under Shared With. A screenshot is enough. Write them into the snapshot as `guest_rules` (shape below), or skip them: the analysis then works from counts and says the criteria were not read.

```json
"guest_rules": [
  {"object": "Campaign", "name": "Guest_Active_Campaigns", "label": "Guest Active Campaigns",
   "guest_user": "Riverside_Garden", "access": "Read", "boolean_filter": null, "include_hvu_owned": false,
   "description": "", "criteria": [{"field": "IsActive", "operation": "equals", "value": "True"}]}
]
```

`guest_user` is the site's Name (the API name, as in the `sites` result).

## The chat path

1. `python3 scripts/guest_audit.py queries --snapshot snapshot.json` creates the snapshot and prints the first queries (`org`, `sites`, `networks`). Add `--site "<label>"` the first time to audit one site.
2. Run each query through the Salesforce connector exactly as printed. Save the records the connector returns to a file (a JSON list, or the whole response with its `records` list) and store it:
   `python3 scripts/guest_audit.py add --snapshot snapshot.json --key sites --records sites.json`
   If the connector refuses a query, store the message instead: `add --snapshot snapshot.json --key guest_shares:Account --error "<message>"`.
3. Run `queries` again. Each round prints the queries whose inputs are now known. Usually five or six rounds; the share counts come one per object.
4. When `queries` says nothing is left, add the sharing rule criteria if the person has them, then `analyze --snapshot snapshot.json --out <outputs folder>`.

Claude Code's `collect` runs exactly this loop with the Salesforce CLI, so both runtimes read the same things and produce the same findings.

## The snapshot

`snapshot.json` holds every result by key (`results`), every refused query (`errors`), the site filter and the date. `collect` replaces each Apex body with the facts the analysis needs (`facts`), so the snapshot carries no code. In chat the bodies arrive through the connector; `analyze` reads them, and the findings file holds none of it.
