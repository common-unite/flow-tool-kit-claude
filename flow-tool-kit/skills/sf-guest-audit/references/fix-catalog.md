# Each finding and its fix

Every finding in `findings.md` has an id (H1, M2, L1, I1), the sites it applies to, the evidence the audit read, and a numbered fix. Findings that are the same on several sites (they usually share permission sets) are listed once with every site named. This page explains each kind, so the fix can be explained, adjusted or done by clicks.

Setup paths below:
- **Guest profile:** Setup, Digital Experiences, All Sites, Workspaces for the site, Administration, Pages, Go to Force.com, Public Access Settings. Or Experience Builder, Settings, General, Guest User Profile.
- **A permission set:** Setup, Permission Sets, the set, Object Settings (object and field access), Apex Class Access, Flow Access, System Permissions.
- **Sharing rules:** Setup, Sharing Settings, the object's Sharing Rules list.
- **Site preferences:** Workspaces for the site, Administration, Preferences.

## Records shared

| Finding | Severity | Why | Fix |
|---|---|---|---|
| Anyone on the internet can read N people's records (Contact, Account, Lead, Case, Opportunity, gifts, enrollments and similar) | HIGH | Guest rules share records that hold people's details | Decide which records, if any, the site must show. None: delete the rule and remove Read. Some: narrow the rule to a marker field the staff control (Show on Website). Remove field Read on personal fields the site does not show |
| Anyone on the internet can read people's form answers | HIGH | A guest rule shares Form Submissions other than Pre-fill Templates, or shares answers or stages | The only Form Submission rule a guest may have is Is Pre-fill Template equals True. A guest reopens their own draft only through a resume link and the system-mode resume flow (flow-access-fix) |
| Every record of an object is shared with the public | MEDIUM | The rule's criteria match everything, so every new record is public too | Add a field that marks the public records and build the rule on it |
| Personal-looking fields on shared records | MEDIUM | Email, phone, address, birth date and similar fields are readable on records anyone can read | Remove field Read on them unless the site displays them |
| A rule also shares records owned by high-volume community users | MEDIUM | Include records owned by high-volume community users is on, so members' records join the public set | Clear it, unless the site must list what members created |
| Anyone can read a child object on the parent records shared with guests | HIGH for people's data (Campaign Members on public Campaigns), MEDIUM for personal-looking fields | Master-detail children follow their parent's sharing, and Campaign Members follow their Campaign: a public Campaign makes its members public to a guest who can read Campaign Member | Remove Read on the child unless a form or page shows it; otherwise remove field Read on personal fields. Narrowing the parent's rule narrows the children too |
| A child object is readable wherever its parent is shared, and the parent could not be counted | MEDIUM | The parent link or its count was not available | The same fix, and check the parent's guest rules in Setup |
| A child object of people's data is readable, with no parent shared today | LOW | A rule added on the parent later exposes it at once | Remove Read unless a form or page shows it |
| The guest can read an object, and the audit could not count what is shared | MEDIUM (people's data only) | The count query was refused; the exposure is unknown | Check the object's guest rules in Setup, and remove Read if nothing needs it |
| The guest can read people's data, though nothing is shared today | LOW | One rule added later exposes it at once | Remove Read unless a page or flow reads it. Where Create is granted, Salesforce requires Read: keep the object out of every guest rule instead |
| A guest rule on an object the guest cannot read | LOW | Harmless today; granting Read later exposes it at once | Delete the rule if nothing needs it |

Records a guest creates are owned by the site's default record owner, so a guest never reads back what they submitted unless a rule shares it. That is why Create without any rule is safe.

## Object and system permissions

| Finding | Severity | Fix |
|---|---|---|
| Edit, Delete, View All or Modify All on an object | HIGH | Remove them. Salesforce no longer allows them for guests; a set that still has them predates that change. Guests save through the form's save flow, never through Edit |
| View All Data, Modify All Data, View All Users, Query All Files | HIGH | Remove from the profile or set |
| View Setup and Configuration, API Enabled | MEDIUM | Remove. API Enabled lets anyone call Salesforce's APIs as the guest |
| Run Flows | LOW | Remove, and grant each flow a guest runs in the guest's permission set instead (flow-access-fix) |

## Site settings

| Finding | Severity | Fix |
|---|---|---|
| Guests can see the site's members | MEDIUM | Preferences: turn off Let guest users see other members of this site |
| Standard lookup and search pages, Guest Access to the Support API or the Payments API | MEDIUM | Setup, Sites, the site: turn each off unless the site uses it |
| The site is not active but its guest user keeps its access | LOW | Remove the guest's sets and rules if the site is retired |
| Self-registration is on | INFO | Anyone can become a member with the self-registration profile: audit that profile as the portal audience |

Allow guest users to access public APIs and Let guest users view asset files are shown in the safe setup table, not as findings: Flow Tool Kit forms on LWR sites need the first, and forms with image assets need the second. The first does mean every record the guest can read is reachable through Salesforce's APIs, which is why the record findings above count what the guest can read.

## Flows

| Finding | Severity | Fix |
|---|---|---|
| A guest runs a flow in system context without sharing | HIGH | Read what it reads and writes. If it only needs records the guest may read, switch How to Run the Flow to the default (user permissions) and share those records with a narrow guest rule. If it truly needs system context, cut it down to one step that returns only the value the screen shows, never whole records, never a lookup by a value the visitor typed, and say why in its description |
| A guest runs a flow in system context with sharing | MEDIUM | The same review: it still ignores object and field access |

What such a flow sends to the browser is the flow review's job ([flow-review.md](flow-review.md)). Its first fix, wherever a system-context flow hands a whole record to a form: pass the record through the Flow Tool Kit action **FLS Record(s) Sanitizer** (`FlowToolKit__DataSanitizer_Invocable`) before the form component, so the guest's profile and permission sets decide which fields the form receives. Then narrow the guest's field Read, query only the needed fields, and leave system context where the flow does not need it.

The two system-mode copies a guest form uses for save and resume, `(Form) Upsert | Guest Override` and `(Form) Prefill | Guest Resume`, are expected and appear in the safe setup table. Keep them to their one job and compare them with the packaged flows after each upgrade.

## Apex

The audit reads the code of each class a guest can reach (granted in Apex Class Access, or the controller of a granted Visualforce page) and checks patterns. One finding per class, at the severity of its worst issue.

| Issue | Severity | Fix |
|---|---|---|
| Declared without sharing | HIGH | Declare with sharing (or inherited sharing); move a query that must reach past sharing into a small helper that returns only the value needed |
| A query or DML in system mode (WITH SYSTEM_MODE, AccessLevel.SYSTEM_MODE) | HIGH | Use WITH USER_MODE or AccessLevel.USER_MODE |
| Reads or writes records with no sharing keyword | MEDIUM | Declare with sharing |
| An inner class without sharing | MEDIUM | Check it never takes a record Id or search value from the visitor |
| A query built at run time (Database.query, Search.query) | MEDIUM | Bind every visitor value (Database.queryWithBinds); never join it into the query text |
| An @RestResource class | MEDIUM | Anyone can call it at the site's `/services/apexrest/` address: check every input, return only what a visitor may see |
| Reads or writes with no object or field access check | LOW | Add WITH USER_MODE and AccessLevel.USER_MODE |
| A test class, or a class with nothing a site can call | LOW | Remove it from Apex Class Access |
| Packaged classes whose code is hidden | INFO | Keep a package's guest permission sets only on sites that use its guest features |

The checks skip comments and the text inside strings. They are patterns, not a code review: a class with no finding still needs a read if it takes a record Id or a search value from a visitor and returns records.
