# Access: guest, portal and internal users

A Flow Section runs **as the person filling the form**: a site guest on a public form, a community user on a portal, a staff member inside Salesforce. Plan its access per audience (the project config's `audiences`), and hand each guest or portal audience to **flow-access-fix**.

## Running the flow at all

| Audience | What it needs |
|---|---|
| Internal users with Run Flows | Nothing more |
| Internal users without Run Flows, portal users, site guests | Two things, together: the flow **requires permission to run** (in Flow Builder, Advanced: "Override default behavior and restrict access to enabled profiles or permission sets"; in the file, `isAdditionalPermissionRequiredToRun` true), and a permission set assigned to them **grants the flow** (Flow Access). Either one alone does nothing |

Without both, the section shows "You do not have the level of access necessary to perform the operation you requested", and a debug log stops at `FLOW_CREATE_INTERVIEW_BEGIN`. The scaffold sets the first part for guest and portal audiences; flow-access-fix does the second, in the org's own permission set for that audience. The package's own permission sets cannot grant your flow, and you cannot edit them.

The packaged save flow that Save Progress runs is already granted by the package's Form (Flow User) permission set, which every form user needs anyway.

## What the flow may read

The flow's Get Records and record choice sets read with the running user's access.

- **Internal and portal users** see what their sharing and field access give them. A portal household member picking from their household's Contacts works when their sharing shows those Contacts; check it as a portal user, not as an admin.
- **Guests see no records** of an object until a **guest sharing rule** shares them (criteria based, read only), plus object and field read in the guest's permission set. For records meant to be public (open shifts, upcoming events, programs taking applications), that is the right answer: share exactly those records, by a criterion such as "Status equals Open". flow-access-fix proposes the rule from what the flow reads.
- **A System Mode read goes through the FLS Record(s) Sanitizer, by default.** When a guest or portal user must be shown a record their sharing cannot reach (a prefill of their own Contact, say), read it in System Mode filtered to exactly that record, pass the result through the Flow Tool Kit action **FLS Record(s) Sanitizer** (`FlowToolKit__DataSanitizer_Invocable`), and give the form component or screen only the sanitized record. The action strips every field the running user's profile and permission sets cannot read, so a guest who can read only First Name and Last Name on Contact receives only those. It strips fields, not records: the Get Records filter still decides which records are shown. Details and the metadata shape: [contract.md](contract.md), "Guest prefill". `flowsection.py check` warns when a System Mode read reaches a screen without it.
- **Never read for a guest what a guest must not see.** If the screen needs one value from a record a guest cannot be given (whether a code is valid, a remaining seat count), the last resort is a small autolaunched subflow set to run in system context that takes the one input, returns only the one value the screen shows, and is itself restricted and granted like the section. Write in its description why it runs in system context and what it returns. Never hand a guest a System Mode record that has not been through the sanitizer, and never list records by a value a guest typed in.
- The read of the Form Template at the start works for every audience that can already open the form.

## Writing

A Flow Section never writes records except through Save Progress (the packaged save flow). The form saves the submission, and the conversion, which runs on its own after submit, creates and updates records. A guest that could write records through your flow is a hole; `flowsection.py check` warns on any write.

## After a change

- A new or renamed Flow Section: flow-access-fix again for every guest and portal audience (the grant names the flow).
- A new object or field the flow reads: field read for that audience, and for guests the sharing rule.
- Walk the section as each audience (SKILL.md step 8). An admin's walk proves nothing about a guest.
