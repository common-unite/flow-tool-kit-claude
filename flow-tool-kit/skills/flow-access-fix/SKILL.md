---
name: flow-access-fix
description: Fix "You do not have the level of access necessary to perform the operation you requested" (FLOW_ACCESS_RESTRICTED) on a screen flow, Flow Section or Flow Tool Kit form, for site guests, portal users and internal users, and wire every new flow so it never happens. Also sets up what a guest form needs around its flows - a read-only guest sharing rule for the records a guest flow or form reads (events, public Campaigns, programs), and the org's own system-mode copies of the save and prefill flows for guest Save Progress, Stages, Autosave and resume links. Use first whenever that message appears near a flow or form, a debug log stops at FLOW_CREATE_INTERVIEW_BEGIN, a guest cannot save progress or resume, a guest picker shows no records, or another skill hands over a flow and its audiences.
---

# Flow Access Fix

One message, "You do not have the level of access necessary to perform the operation you requested", covers most access failures on Flow Tool Kit forms. It nearly always has the same two causes, checked in this order before anything else:

1. **The flow does not require permission to run.** Without that setting a flow runs only for users with Run Flows, which guests and portal users never have, and a permission set grant to it does nothing.
2. **No permission set the running user holds grants the flow.** Once the flow is restricted, everyone who runs it needs a grant, a System Administrator included.

This skill fixes both for each audience in the project (guest, portal, internal), then the access around the flow: the records it reads, and for guest forms, the save and resume flows.

**Called by** build-flow-section and build-custom-lwc (once per audience, with the flow or component they built), build-template (its `setup` list for guests), build-site-pages, new-mapping-flow, ftk-start ("access errors on a form or flow"), and directly: "the public form says I do not have access", "guests cannot save progress", "the event picker is empty on the site". **Hands over** to build-email-templates for the Save Progress email a guest receives, and to sf-guest-audit to check the other direction: what guests can see that they should not.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat, no Salesforce connector | Diagnose from what the person shares: the message, the flow file or a screenshot of its settings. Run `scripts/flowaccess.py` in the code sandbox on uploaded files (`inspect`, `restrict`, `grant`, `sharing-proposal`, `sharing-rule`) to produce corrected files, and give the Setup steps in [references/setup-clicks.md](references/setup-clicks.md). |
| claude.ai chat, with a Salesforce connector | All of the diagnosis: run the read-only queries from `flowaccess.py queries` through the connector. If the connector can write records, it can also make the grant (a SetupEntityAccess record) and assign permission sets. Restricting a flow, the system-mode copies and sharing rules are metadata: **chat cannot deploy them.** Say so in one line, then either hand the files to Claude Code or walk the person through the Setup steps. |
| Claude Code, local or on the web, with the Salesforce CLI | Everything: `flowaccess.py diagnose`, retrieve, edit, deploy, and the check in a new guest session with a headless browser. |

Read on demand, beside this file:
- [references/diagnosis.md](references/diagnosis.md): every message a form shows and its cause, the queries, how to read a debug log, and the order to look further.
- [references/audiences.md](references/audiences.md): what guests, portal users and internal users each need, and which permission sets carry it.
- [references/guest-sharing.md](references/guest-sharing.md): proposing the narrowest guest sharing rule from what the flow or form reads.
- [references/guest-save-and-resume.md](references/guest-save-and-resume.md): the system-mode copies for guest Save Progress, Stages, Autosave and resume, verified against the package.
- [references/setup-clicks.md](references/setup-clicks.md): the same fixes as clicks in Setup and Flow Builder, for chat or a person.
- [references/worked-example.md](references/worked-example.md): one public form fixed end to end, with the commands.
- `scripts/flowaccess.py --help`: the helper. Editing commands change nothing without `--write`.
- Plugin standards: `_shared/standards/documentation.md` (flow names and descriptions; section 6, Naming), `_shared/standards/project-config.md` (the audiences). Where this skill and a standard disagree, the standard wins.

## 1. Who runs it, and which flow

1. **The audiences.** Read `flow-tool-kit.json` (`_shared/standards/project-config.md`). No audiences saved: ask ftk-start's one question ("Who fills this form in: the public without signing in, signed-in community members, staff, or a mix?") and save the answer. A handover from another skill names the audience; fix each one it names.
2. **The flow.** A Flow Section: the section's Flow API Name. A flow on a page: the flow component's API name, or `flowDevName` in the failing request. "You do not have permission to run this form's save process": the save flow, `(Form) Upsert | Overridable`. A form that fails as it opens: the template's Prefill Flow. Then the flow that **really runs**: an active override replaces a packaged flow for everyone, so check the override, not the packaged flow.
3. **The running user.** Guest: the site's guest user (`Site.GuestUserId`). Portal: one real member, by username. Internal: one real staff user, never your own admin login.

In Claude Code, one command answers all three and steps two and three below:

```bash
python3 scripts/flowaccess.py diagnose --org <org-alias> --flow <Flow_Api_Name> --site <Site_Name>
python3 scripts/flowaccess.py diagnose --org <org-alias> --flow FlowToolKit__Form_Submission_Upsert --user <username>
```

In chat, `python3 scripts/flowaccess.py queries --flow <Flow_Api_Name> --site <Site_Name>` prints the same checks as SOQL for the connector.

## 2. Step one: the flow requires permission to run

The flow file must contain, at the top level between `<interviewLabel>` and `<label>`:

```xml
    <isAdditionalPermissionRequiredToRun>true</isAdditionalPermissionRequiredToRun>
```

In Flow Builder it is the advanced setting "Override default behavior and restrict access to enabled profiles or permission sets". Every flow a guest or portal user runs needs it, and so does every subflow it calls. `flowaccess.py restrict <file> --write` sets it; retrieve the flow from the org first, so the fix lands on the version that runs. Saving the flow makes a new version: activate it.

## 3. Step two: the running user's permission set grants it

The permission set must contain:

```xml
    <flowAccesses>
        <enabled>true</enabled>
        <flow>Flow_Api_Name</flow>
    </flowAccesses>
```

Use the org's own permission set for that audience ([references/audiences.md](references/audiences.md)). The package's permission sets grant only the package's own flows, and you cannot add yours to them. For guests, the set is **Form Flow (Guest User)** (`Form_Flow_Guest_User`): the Flow Tool Kit installer may already have created it; if not, create it with that name, and assign it to the guest user beside Form (Flow User).

- **Claude Code:** retrieve the set, `flowaccess.py grant <permset file> --flow <Flow_Api_Name> --write` (add `--apex <Class>` for an Apex action the flow calls), deploy the set. Never deploy a permission set file you did not retrieve first: write into the org's current copy.
- **Chat with a connector that writes records:** create a `SetupEntityAccess` record with `ParentId` = the permission set's Id and `SetupEntityId` = the flow's `DurableId` from `FlowDefinitionView` (an Id starting 300). It adds the grant and changes nothing else.

## 4. Test in a new session

A guest session keeps the access it started with: a grant or an activation never reaches a page that is already open, and the save keeps failing. Test in a new private window, or sign the guest out at `https://<site domain>/<site path>/secur/logout.jsp` and load the form again. Test as the real audience: a guest in a private window, a portal member, a staff user. An admin's test proves nothing about anyone else. In Claude Code, do the guest walk with a headless browser; otherwise give the person the steps.

## 5. Only then look further

Both steps are in place and the error stays. Check, in this order ([references/diagnosis.md](references/diagnosis.md)):

1. **Subflows** the flow calls: each needs both steps for the same audience (`flowaccess.py inspect` lists them).
2. **Apex actions**: a custom invocable needs Apex Class Access in the same set. Packaged actions come with Form (Flow User).
3. **Object and field access** on everything the flow reads, creates and receives as input.
4. **Record access**: the rows themselves. Guests: section 6. Portal users: the external sharing model, sharing sets and sharing rules.

## 6. Guest forms: the records a guest reads

A guest sees no record of any object until a **guest sharing rule** shares it: criteria based, read only, for that site's guest user. Object and field read in the guest's set are needed too, and are not enough alone. Whenever a guest flow or form reads records (open events, public Campaigns, programs taking applications, volunteer shifts, a Record Picker's Accounts), remind the person of this, check the org for a rule, and propose the narrowest one for the records the flow actually reads:

```bash
python3 scripts/flowaccess.py sharing-proposal <flow file> --site <Site_Name> --existing sharingRules/<Object>.sharingRules-meta.xml
```

It reads the flow's own filters (Active equals True, Type equals Workshop) as the rule's criteria, says when an existing rule already covers them, and asks when no fixed filter exists. Propose each rule as object, criteria and Read Only, with what it exposes ("every active workshop Campaign, to anyone on the internet"), and write it only on the person's yes (`sharing-rule ... --write`). The package's own guest rules (Form Template, Pre-fill Templates, record components) are in [references/guest-sharing.md](references/guest-sharing.md). Never share Form Submission records with guests, except Pre-fill Templates.

## 7. Guest forms: Save Progress, Stages, Autosave and resume

A guest can create a Form Submission but never update one, and cannot read it once saved. So a guest form that saves more than once needs the org's own **system-mode copies** of two packaged flows, verified against the package in [references/guest-save-and-resume.md](references/guest-save-and-resume.md). Build them **only when a guest form actually needs them**:

| A guest form uses | It needs |
|---|---|
| Allow Save Progress, Stages Mode or Enable Autosave | **(Form) Upsert \| Guest Override** (`Form_Submission_Upsert_Guest`): a flow override of `(Form) Upsert \| Overridable` in System Context Without Sharing |
| Resume links (the Save Progress email, or the Stages "Email me a resume link" button) | **(Form) Prefill \| Guest Resume** (`Form_Submission_Prefill_Guest`): a copy of `(Form) Prefill \| Template` in System Context Without Sharing, added to the Prefill Flow picklist and chosen as the Prefill Flow on every such template |
| None of these: each guest submits once | Nothing. Leave the packaged flows in place and tell the person why: a single submit is one insert, which the packaged save flow already handles for guests |

1. **Decide from the templates.** Query the guest templates' Save Progress, Stages and Autosave settings (the query is in the reference) and save the rows as JSON. `flowaccess.py guest-copy upsert|prefill <retrieved file> --templates <rows.json> --out <dir> --write` builds a copy only when a template needs it, names the templates and settings that need it, and otherwise prints "not needed, so not built" and writes nothing. A guest save refused because a URL parameter or prefill passes a record the guest cannot read is not a reason for the override: stop passing that record.
2. **Check the org first:** the installer may have deployed the save override already, inactive.
3. **Build and deploy inactive** from the packaged flow retrieved from the same org.
4. **Before asking for the yes**, say plainly: "Once this override is active, every save in the org runs through it in system mode: guests, portal users and staff, on every form, not only this one." Then say what each copy exposes (the reference has the words) and ask. Running these copies in system context is the org's own security decision.
5. **On the yes**, activate it and grant it (step two) to **every** audience that saves, since the override serves their saves too.

## 8. Portal and internal users

- **Saving.** Form (Flow User) grants Create and Read on Form Submission and Form Submission Stage, never Edit, so it stays assignable to guests. A portal or staff user who has only that set cannot save progress or submit: give portal users an org set with Edit on both objects, and staff Form Builder Internal User. Never give the Edit set to the guest user.
- **Restricted flows.** Once a flow is restricted, staff need the grant too: Run Flows no longer covers it.
- **Portal record access.** Form Submission is private to external users: a member updates submissions they own. Another member resuming it needs a sharing rule or sharing set.

## 9. Wiring a new flow

When another skill hands over a new flow (a Flow Section, a screen flow on a site page, a subflow), do in the same change, for each audience it names: restrict it, grant it in that audience's set, its subflows and Apex classes likewise, object and field read on what it reads, and for guests the sharing proposal. Then the walk in a new session. A renamed flow needs its grant again: the grant names the flow.

## Done when

- The message is gone for every audience, tested in a new session as that audience.
- Every flow a guest or portal user runs, and every subflow, requires permission to run and is granted in the org's own set for that audience.
- Every record a guest flow or form reads is shared by a read-only guest rule the person agreed to, with criteria, and nothing more.
- A guest form with Save Progress, Stages, Autosave or resume has its active system-mode copies, granted to every audience that saves, and a resume walk passed in a new private window. An org whose guest forms each submit once keeps the packaged flows, and the person was told why.
- Everything created carries a description in the shape `_shared/standards/documentation.md` sets: what it is for and, for system mode, why.
- The person has a short list of what changed and why.

## Common mistakes

| Mistake | Instead |
|---|---|
| Granting the flow and stopping | Restrict it too: a grant does nothing on an unrestricted flow |
| Restricting the flow and stopping | Grant it to every audience, staff included |
| Debugging object access, field access or Apex first | The two steps first, every time |
| Testing in the guest session that was already open | A new private window, or the logout address |
| Checking the packaged save flow when an override is active | Check and grant the flow that runs |
| Adding your flow to a packaged permission set | The org's own set for that audience |
| A guest sharing rule with no criteria, or sharing Form Submission | Criteria from what the flow reads; Form Submission only for Pre-fill Templates |
| A system-mode copy built from an old file or from source | Retrieve the packaged flow from the same org first |
| Activating a system-mode copy without the person's yes | Deploy it inactive, say that every audience's saves will run through it in system mode, activate on their yes |
| Building the save override for a guest form that submits once | Only Save Progress, Stages or Autosave need it; otherwise the packaged flow stays |
| An Edit permission set for the guest user | Guests save through the save override; Salesforce blocks Edit for guests |
