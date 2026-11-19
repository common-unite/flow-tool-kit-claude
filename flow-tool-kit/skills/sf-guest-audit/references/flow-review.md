# The flow review

Needs the flows' metadata. It finds, before anyone opens the site, the flows that send a visitor more than the form shows. The live pass ([live-pass.md](live-pass.md)) proves what actually arrived; the flow review names the flow, the element and the component to change.

## The pattern it looks for

A guest screen flow runs in **system context** (How to Run the Flow: System Context Without Sharing, or With Sharing), uses a standard **Get Records** that stores all fields, and passes the whole record into a screen component. In system context the flow ignores the guest's field access, so every field of the record (date of birth, internal notes, owner, anything on the object) goes to the browser. The form shows five of them; the rest sit in the page's data, readable in the developer console.

It is common because it is the quickest way to prefill a form for a known person, and it looks safe on screen.

## The fix, in order

1. **Pass the record through the FLS Record(s) Sanitizer before the form.** Flow Tool Kit ships the action FLS Record(s) Sanitizer (category Flow Tool Kit; in a flow's metadata `FlowToolKit__DataSanitizer_Invocable`). Add it right after the Get Records: pass the record into its **Record** input (a collection into **Record(s)**), and give the form component the action's **Record** output instead of the Get Records result. It runs `Security.stripInaccessible` for reading, so it removes every field the running user has not been granted. Guest access is then controlled the normal way, with the guest's profile and permission sets: if the guest can read only First Name and Last Name on Contact, that is all the form receives. The Form (Flow User) permission set already grants the guest the action.
2. **Keep the guest's field Read to what the form shows**, in the org's guest permission set. With the sanitizer in place this is the one list that decides what a visitor gets.
3. **Or query only the fields the form needs**: in the Get Records, Choose fields and let Salesforce do the rest, and pick them.
4. **Avoid system context where you can.** In the default context (User or System Context, Enforces User Permissions) the flow already respects field access; share the records the guest needs with a narrow guest sharing rule (flow-access-fix proposes it).
5. **Scope prefill templates and prefill flows.** A Form Template's Pre-fill Template (`Prefill_Template__c`, a Form Submission marked Is Pre-fill Template) and its Prefill Values reach every visitor: keep them to defaults, never a real person's values. A prefill flow (`Prefill_Flow_Api_Name__c`) returns `prefillRecord` to the browser: set only the fields the form shows on it, as the **Prefill From Mapped Record** action does (it copies only the sections mapped to the record).

The sanitizer strips **fields**, not **records**. If the flow looks the record up by an Id or value from the link, a visitor who edits the link gets another person's record, sanitized or not. That needs its own fix (below).

## What it checks

| Check | Flagged when | Severity |
|---|---|---|
| All fields, system context | The flow runs in system context; a Get Records stores all fields (Automatically store all fields, or no fields chosen); its record reaches a screen component input or an output variable through assignments or loops; the FLS Record(s) Sanitizer is not between them | HIGH when a guest runs the flow, MEDIUM when that is not known, LOW when it is known not to |
| Lookup by a visitor value | The flow runs in system context; a Get Records filters on a value the visitor controls (an input variable, which a page or link can set, or a Form (Get Url Parameters) output); its record reaches the screen or an output. A filter on a token field (a single-use token, as the resume link uses) is not flagged. The sanitizer does **not** clear this | HIGH when a guest runs the flow, as above otherwise |
| Chosen fields that look sensitive | System context, fields chosen, and one of them looks sensitive (birth date, notes, income, health, token and similar) | MEDIUM |
| All fields, default context | Default context and all fields: the guest's field access applies, but every field the guest can read is sent | LOW |

A record passed through the sanitizer reaches the component as the action's output, so it is not flagged for fields. Not flagged: a Get Records whose fields are assigned one by one to variables (only those values travel), and a record that reaches the screen only through another action (the Prefill From Mapped Record action copies only mapped sections). The org's own system-context copies for guest save and resume (`Form_Submission_Upsert_Guest`, `Form_Submission_Prefill_Guest`) are expected; a finding on them is capped at LOW, and passing the resumed submission through the sanitizer is still worth it.

Components it names: Form (Component) `FlowToolKit:flowForm` (input `record`, also `transformationRecord` and `compareRecord`), Form (Template) `FlowToolKit:formTemplate` (`formSubmission`, `relatedRecords`), Form (Repeater) `FlowToolKit:flowFormRepeat` and Form (Table) `FlowToolKit:flowDataTable` (`prefillRecords`, `recordTemplate`), Form (Merge Records) `FlowToolKit:mergeRecords`, the standard Data Table, and any other screen component by its name. Output variables count too: a screen flow's outputs and a prefill flow's `prefillRecord` and `prefillRelatedRecords` reach the page.

## Fix for a lookup by a visitor value

Never look a record up in system context by an Id or value from the link or a page input. Use a single-use token instead, as the Flow Tool Kit resume link does (`Internal_Unique_Token__c` on the Form Submission: random, cleared on use, expires), or put the form behind a sign-in. Or run the flow in the default context and share only the records a guest may read with a narrow guest sharing rule.

## Running it

**Claude Code**, with the Salesforce CLI signed in to the org:

```bash
# the flows a guest runs, from the inside audit's snapshot, retrieved and reviewed:
python3 scripts/flow_review.py review --org <org-alias> --flow Volunteer_Renewal --flow Volunteer_Prefill \
    --snapshot _audits/guest-exposure-<date>/snapshot.json --out _audits/guest-pass-<date>
```

The flows are retrieved (metadata only, no records) into `<out>/flows/`. `--snapshot` marks which flows are granted to a site's guest; `--guest-flow <name>` names one directly (a flow on a public page through Run Flows, or one the person names). Flow files already in the project work too: `python3 scripts/flow_review.py review force-app/main/default/flows --guest-flow <name>`.

**Chat:** a connector reads records, not flow metadata. Ask the person for the flow files (from their project, or retrieved with any metadata tool) and run the same command on the uploaded files. Without them, say the flow review was not done, and let the live pass stand.

Then join both into one report:

```bash
python3 scripts/exposure.py report --exposure _audits/guest-pass-<date>/exposure.json \
    --flows _audits/guest-pass-<date>/flow-review.json --out _audits/guest-pass-<date>
```

`guest-report.md` lists every form and flow with its severity, what is exposed and the first fix, and marks a flow finding "confirmed in the live pass" when the live pass saw that flow send fields the form did not show.
