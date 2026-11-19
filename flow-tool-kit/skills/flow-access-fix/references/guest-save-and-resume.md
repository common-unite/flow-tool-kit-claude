# Guest Save Progress, Stages, Autosave and resume

Read from the Flow Tool Kit package's own flows, form code and documentation (5.3), and the copies proven by a deploy to a scratch org with 5.2 installed. The package ships every flow in default mode and never runs anything in system mode for you; the copies below are the org's own, and running them in system context is the org's decision.

## Why guests need copies

- A guest can **create** a Form Submission but never **update** one: Salesforce never lets a guest hold Edit, and guest-created records belong to the site's default owner, so the guest cannot even read the submission after the first save.
- The form saves every guest through the overridable flow **(Form) Upsert | Overridable** (`Form_Submission_Upsert`). Since 5.3 it starts that flow from Apex. Its inputs are the submission (`record`), the related rows, and the Stages progress (`stage`).
- A resume link carries a single-use token in the `resume` parameter. Opening it runs the template's **Prefill Flow** in the person's browser, or the packaged **(Form) Prefill | Template** (`Form_Submission_Prefill`) when the template is on Bypass, as the guest. In default mode the guest cannot read its draft, so the form opens a new submission with a notice.

## Which forms need which copy

| The guest form | What happens without a copy | The copy |
|---|---|---|
| Allow Save Progress, Enable Autosave | The second save is an update and is refused ("could not be updated with your current access"), or `DUPLICATE_VALUE` on Unique Id | Save override |
| Stages Mode | The same, and Stages progress is dropped without a message: the packaged flow ignores a refused stage save so the submission save stands | Save override |
| A URL parameter or prefill that fills a lookup to a record the guest cannot read (an Account or Contact) | Even the first save is refused ("linked to a record you do not have access to") | None: stop passing that record. On its own this is not a reason for the override |
| Resume links: the Save Progress email, or the Stages "Email me a resume link" button | The link opens a new form with a notice | Resume copy, named on the template |
| A single Submit and nothing else | Works: one insert | None. Leave the packaged flows in place and tell the person why |

`SELECT Name, FlowToolKit__Allow_Save_Progress__c, FlowToolKit__Stages_Mode__c, FlowToolKit__Enable_Autosave__c, FlowToolKit__Send_Save_Progress_Email__c, FlowToolKit__Prefill_Flow_Api_Name__c FROM FlowToolKit__Form_Template__c WHERE FlowToolKit__IsActive__c = true` lists the templates and what each needs (before 5.3, leave out Send Save Progress Email: the field arrived then); ask which of them guests use, and save those rows as JSON (a plain list, or the CLI's `--json` output). `guest-copy` reads them with `--templates` and builds a copy only when one of those templates needs it; otherwise it prints "not needed, so not built" and writes nothing.

**Activate the save override only when a guest form actually uses Save Progress, Stages or Autosave.** When none does, the packaged save flow stays in place, and the person hears why: each guest submits once, a single insert the packaged flow already handles.

### On Flow Tool Kit 5.3 and later

Started from Apex on the default run mode, the packaged save flow runs in system context, so guest saves can appear to work with no copy. Do not rely on that: the package's own upgrade guidance asks every org to choose the save flow's run mode explicitly, and recommends an override in **User Context, Enforces User Permissions** (API 68 or later) to keep each respondent's own access, with **System Context** only when guests must update their saved submissions. Only one override can be active, and it serves every save in the org. So:

| The org's forms | The save flow to activate |
|---|---|
| A guest form uses Save Progress, Stages or Autosave | The guest save override, System Context Without Sharing |
| No guest form does | No guest override. Leave the packaged flow in place, or, if the org wants each respondent's own access kept, an override in User Context, Enforces User Permissions (that is the org's run-mode choice, not a guest fix) |

## The save override: (Form) Upsert | Guest Override

| | |
|---|---|
| Label, API name | `(Form) Upsert \| Guest Override`, `Form_Submission_Upsert_Guest` |
| What it is | A flow override of `FlowToolKit__Form_Submission_Upsert`: while active, everything that names the packaged save flow runs this one instead, for every form and every user. Nothing needs pointing at it |
| How it runs | System Context Without Sharing. Requires permission to run |
| Granted by | Form Flow (Guest User) (`Form_Flow_Guest_User`) for the guest, and each other audience's set (an override serves their saves too) |

These are the names the Flow Tool Kit installer uses. On a first install from 4.46 its optional step "Install the Guest Save Override (inactive)" deploys both the override (inactive) and the set. **Check first:**

```sql
SELECT ApiName, IsActive, OverriddenFlowId FROM FlowDefinitionView WHERE ApiName = 'Form_Submission_Upsert_Guest'
SELECT Id, Name FROM PermissionSet WHERE Name = 'Form_Flow_Guest_User'
```

Found and inactive, and a guest form needs it: review it with the person, say what activating it means (below), activate it on their yes, grant and assign. Not needed: leave it inactive. An org installed before 4.46 may keep an older override of its own under another name: `OverriddenById` on the packaged flow names it.

**Building it (Claude Code):**
1. Retrieve the packaged flow from the same org into a folder outside the deploy folder, since it is only the source: `sf project retrieve start -m "Flow:FlowToolKit__Form_Submission_Upsert" --output-dir packaged-source -o <org-alias>` (the folder must sit inside the project; the file lands in `packaged-source/flows/`). The copy then matches the installed version and keeps the `FlowToolKit__` prefix on every object and field. The upsert's external-id field must keep its prefix, or the save fails with "does not match an External ID". The script refuses a source without prefixes.
2. `python3 scripts/flowaccess.py guest-copy upsert packaged-source/flows/FlowToolKit__Form_Submission_Upsert.flow-meta.xml --templates guest-templates.json --out <project-dir>/force-app/main/default --write`. It builds nothing unless a guest template uses Save Progress, Stages or Autosave, and names those templates. It changes only: label and interview label, the description, run mode to System Context Without Sharing, status Draft, removes the overridable flag, adds `<overriddenFlow>FlowToolKit__Form_Submission_Upsert</overriddenFlow>`, and keeps "requires permission to run".
3. Deploy it with the permission set (`grant ... --flow Form_Submission_Upsert_Guest`, `--create --label "Form Flow (Guest User)"` when the org has none). A deployed flow may arrive inactive; that is intended here.
4. Say plainly, before asking: "Once this override is active, every save in the org runs through it in system mode: guests, portal users and staff, on every form, not only this one." Then what it exposes (below), and activate it on their yes: Flow Builder, or redeploy with `guest-copy ... --status Active`.
5. Grant it to every audience that saves; assign Form Flow (Guest User) to each site's guest user.

**Building it in Setup:** [setup-clicks.md](setup-clicks.md).

## The resume copy: (Form) Prefill | Guest Resume

| | |
|---|---|
| Label, API name | `(Form) Prefill \| Guest Resume`, `Form_Submission_Prefill_Guest` |
| What it is | A plain copy of `(Form) Prefill \| Template` (that flow is a template, not an override target). It runs only where a Form Template names it |
| How it runs | System Context Without Sharing. Requires permission to run. Started in the guest's browser, so the guest needs its grant |
| Where it is named | A value of the Form Template field **Prefill Flow** (`FlowToolKit__Prefill_Flow_Api_Name__c`), chosen on every template whose guests resume. A template on Bypass keeps running the packaged flow, which cannot open a guest's draft |

**Building it (Claude Code):**
1. Retrieve `Flow:FlowToolKit__Form_Submission_Prefill` from the org the same way, into `packaged-source`.
2. `python3 scripts/flowaccess.py guest-copy prefill packaged-source/flows/FlowToolKit__Form_Submission_Prefill.flow-meta.xml --templates guest-templates.json --out <project-dir>/force-app/main/default --write`: new label and description, System Context Without Sharing, status Draft, the template flag removed, "requires permission to run" kept.
3. Add the picklist value: retrieve `CustomField:FlowToolKit__Form_Template__c.FlowToolKit__Prefill_Flow_Api_Name__c`, add a value whose API name is exactly `Form_Submission_Prefill_Guest` and label `(Form) Prefill | Guest Resume`, keep every existing value, and deploy the field with the flow. (Proven in a scratch org: an installed org can add a value to this packaged picklist by deploy.) Or add it in Setup.
4. Grant it to the guest (`grant ... --flow Form_Submission_Prefill_Guest`) and deploy.
5. Activate on the person's yes, then set **Prefill Flow** on each template whose guests resume (a record update; in chat, through the connector).

**A template that already names its own prefill flow:** that flow runs instead of the packaged one, so it needs the same treatment: the org's own copy of *that* flow in system context, restricted and granted. It must still match the token **and** the Form Template, and clear the token once used; never weaken that match.

## What to tell the person before activating

Say it plainly, then ask; it is the org's security decision:
- **The save override, first:** "Once this override is active, every save in the org runs through it in system mode: guests, portal users and staff, on every form, not only this one." It runs without sharing for anyone who can open any form in the org. It saves only the submission the form hands it, and should stay that way: no extra lookups or writes added to it.
- **The resume copy** lets whoever holds a valid resume link open that one draft. The token is 128-bit random, used once, matched with its Form Template, cleared on submit and after 7 days, and each email carries a new one. A forwarded link still opens the draft for the first person who clicks it.
- For forms that collect sensitive answers, a sign-in (portal users) is safer than guest resume links.

## Related emails

- A guest who typed only an email address has no Contact 1, so the Save Progress email is the package's built-in email with the link, not the branded template. That is by design. A branded email for them needs an override of `(Form) Send Resume Link | Overridable`, which is also the org's security decision; build-email-templates covers the email itself.
- The emails need a web form address on the template or the org, and a verified Default Workflow User (build-template and build-email-templates set these up).

## After a Flow Tool Kit upgrade

The copies keep the logic of the version they were made from. After an upgrade, retrieve the packaged flows again and compare: copy in what changed, or rebuild the copy and review it again. Two known cases: a save override made before 4.46 ends a refused save as "Submitted successfully" (point the Form Submission upsert's fault path at the error assignment, or rebuild); and from 5.3 an override that builds its own record must also save Send Resume Link (`FlowToolKit__Internal_Send_Resume_Link__c`), or no Save Progress email goes out.

## The check

In a new private window: open the form as a guest, fill in a page, Save Progress (or move between stages), change an answer, save again, and submit. For resume: save, open the link from the email in another new private window, see the saved answers, change one and submit. In Claude Code, walk it with a headless browser; otherwise give the person these steps. A refusal after everything is in place: the session started before the change.
