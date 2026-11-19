# The three audiences

The project config's `audiences` (`_shared/standards/project-config.md`) names who fills in the org's forms. Each audience runs the same flows as a different user and needs its access from a different place.

## The package's permission sets

| Set | Who | What it gives |
|---|---|---|
| **Form (Flow User)** (`Form_Flow_User`) | Everyone who fills in a form: guests, portal users, staff | Read and Create on the form objects, the packaged flows and Apex actions. **No Edit** on Form Submission or Form Submission Stage, so it stays assignable to guests. No Campaign access |
| Form Builder Internal User | Staff who fill in or review forms | Full access to submissions, plus Campaign filters in Form Analytics |
| Form Builder Manager, Form Builder Admin | Staff who build forms | Everything above, and the builder |

You cannot add your own flows, classes or objects to these sets. Put them in a set of the org's own for each audience, and assign it beside the package's set.

## Guests (a public form on an Experience Cloud site)

- **Who runs it:** the site's guest user, one per site: `SELECT GuestUserId FROM Site WHERE Name = '<Site_Name>'`, or Experience Builder, Settings, General, Guest User Profile, View Users.
- **Sets:** Form (Flow User), and **Form Flow (Guest User)** (`Form_Flow_Guest_User`) for everything of the org's own: its flows and Flow Sections, its Apex classes, Read on the objects and fields its flows and form read, Create where a flow creates, and Edit on every Form Submission field a URL parameter fills. The Flow Tool Kit installer creates this set on a first install (with the save override, below); extension installers add their guest grants to it; if the org lacks it, create it with that name and label.
- **Never:** Edit or Delete on any object (Salesforce refuses to assign such a set to a guest), View All, Modify All, or a broad Read on records that hold people's answers.
- **Records:** only through guest sharing rules, read only ([guest-sharing.md](guest-sharing.md)). The package needs up to three of its own; the org adds one for each kind of record its flows and form read.
- **Saving more than once, and resuming:** the system-mode copies ([guest-save-and-resume.md](guest-save-and-resume.md)).
- **Restricted flows:** every flow and subflow a guest runs requires permission to run. Guests never hold Run Flows.
- **Sensitive data:** a public form that collects sensitive answers is better behind a sign-in (the portal audience), because a guest resume link opens the draft for whoever holds it. Say so when the form asks for such data; the choice is the person's.

## Portal users (signed-in Experience Cloud members)

- **Who runs it:** a member's user, with a community license, profile and sets. Check with one real member: `diagnose --user <username>`.
- **Sets:** Form (Flow User), and an org set (for example "Form Portal User") that grants **Edit on Form Submission and Form Submission Stage** (Form (Flow User) leaves Edit out, and field access is already in it), the org's flows and classes, and Read on what its flows read. Without the Edit, Save Progress fails with "An error occurred while trying to update the record" and Submit saves nothing.
- **Records:** the object's external sharing model, then sharing sets (records related to the member's account or contact) and sharing rules. Form Template and Form Component are readable externally; **Form Submission is private externally**, so a member updates the submissions they own. A second member resuming someone else's submission needs a sharing rule, a sharing set or Apex sharing for that case.
- **Restricted flows:** granted in the org set, like guests.
- **Campaigns:** some community licenses cannot reach Campaign at all; a form that reads Campaigns for portal users needs a license that can.

## Internal users (staff inside Salesforce)

- **Who runs it:** the staff member. Test as one, never as your own admin.
- **Sets:** Form Builder Internal User (or Manager or Admin) for submissions. Form (Flow User) alone has no Edit and fails on Save Progress.
- **Restricted flows:** once a flow is restricted, staff need a grant too, Run Flows no longer covers it, and a System Administrator is refused like anyone else (seen in a scratch org: an admin with no grant was refused a restricted flow started from Apex, and ran it once a set granted it). Add the flow to the org's staff set, or to a set every staff role holds.
- **Unrestricted flows:** run for anyone with Run Flows. Leave a staff-only flow unrestricted only if no guest or portal user will ever run it.

## When the save flow is overridden

An active override of `(Form) Upsert | Overridable` replaces the packaged save flow for **every** form and **every** user. Guests always save through it; signed-in users do too when the form is embedded in another website, when a page has repeater or table rows waiting to be saved, and when a Flow Section's Save Progress runs. So grant the override in each audience's set, not only the guest's, or those saves fail with "You do not have permission to run this form's save process". Seen in a scratch org: with the override active, a user without its grant was refused the save flow, and the same call ran once a set granted it.
