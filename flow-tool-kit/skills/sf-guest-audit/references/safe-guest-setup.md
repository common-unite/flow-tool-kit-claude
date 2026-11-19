# What a safe Flow Tool Kit guest setup has

The picture both this skill and flow-access-fix work to. flow-access-fix builds it; this audit checks it and reports each item in the "What a safe Flow Tool Kit guest setup has" table of `findings.md`. A missing item there breaks a guest form; it does not expose data, so it is not a finding.

## Who the guest is

- One guest user per site, running every public page and form. It holds the guest profile, **Form (Flow User)** from the package, and the org's own **Form Flow (Guest User)** (`Form_Flow_Guest_User`) for the org's own guest flows and Apex classes.
- No Edit, Delete, View All or Modify All on any object, and none of View All Data, Modify All Data, View All Users, Query All Files, View Setup, API Enabled or Run Flows.
- Every flow a guest runs requires permission to run and is granted in the guest's set; Run Flows is never the way in.

## What a guest can read

- Nothing, until a **guest sharing rule** shares it: criteria based, read only, one site. Each rule makes those records readable by anyone on the internet, through Salesforce's APIs as well as the site's pages.
- The package needs at most three rules of its own:

| Object | Criteria | When |
|---|---|---|
| Form Template | Active equals True | Every guest form |
| Form Submission | Is Pre-fill Template equals True | Only templates with a Pre-fill Template |
| Form Component | Record Type equals Record Component | Only templates with record components |

- **No other Form Submission is ever shared with guests**, and no Form Submission Answer or Stage. A guest reopens their own draft only through a resume link and the resume copy below.
- The org adds one narrow rule per kind of record its guest flows and forms read (open workshops, programs taking applications), built on a field the staff control. flow-access-fix proposes it from what the flow reads.
- Object Read, and field Read only on the fields the site shows. Where a form creates records (a Contact from a registration), Salesforce requires Read with Create: keep that object out of every guest rule, and records the guest creates stay with the site's default owner, unreadable to the guest.

## What a guest runs in system context

Only the org's own copies a guest form needs, and only when the form saves more than once or resumes:

| Copy | Runs as | For |
|---|---|---|
| (Form) Upsert \| Guest Override (`Form_Submission_Upsert_Guest`) | System context without sharing | Guest Save Progress, Stages, Autosave |
| (Form) Prefill \| Guest Resume (`Form_Submission_Prefill_Guest`) | System context without sharing | Guest resume links |

Each is kept to its one job and compared with the packaged flow after every Flow Tool Kit upgrade. Any other flow or Apex a guest reaches in system context is a finding.

Any record a system-context flow hands to a form goes through the **FLS Record(s) Sanitizer** action first, so the form receives only the fields the guest may read. A guest flow never looks a record up by an Id or value from the link; it uses a single-use token, as the resume link does.

## Site settings

| Setting | Safe value |
|---|---|
| Allow guest users to access public APIs | On for LWR sites with Flow Tool Kit forms (they do not load without it); remember it opens every guest-readable record to direct API calls |
| Let guest users view asset files and CMS content | On only when forms use image assets |
| Let guest users see other members of this site | Off |
| Standard lookup and search pages, Guest Access to the Support API and Payments API | Off unless used |

## For sensitive answers

A guest form that collects sensitive answers is safer behind a sign-in (the portal audience): a guest resume link opens the draft for whoever holds it. That is the person's choice: raise it whenever the form asks for such data.
