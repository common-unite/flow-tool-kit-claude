---
name: sf-guest-audit
description: Check your client's guest exposure on the Experience Cloud sites you build for them. One interview picks the forms, prefill links and guest flows; a live guest pass opens each form logged out (headless in Claude Code, from a browser HAR in chat), fills it with fake data and lists every field the browser received but the page did not show, flagging the sensitive ones; with the org's metadata, a flow review flags guest flows in system context that pass a whole Get Records record to a form without the FLS Record(s) Sanitizer, and a setup audit reads guest profiles, permission sets, sharing rules, site settings, flows and Apex. Reports per form or flow what is exposed, how serious, and the exact fix. Never writes to the org. Use when someone asks whether a client's public site, guest forms or prefilled Form Templates expose data, before or after a guest form goes public, after guest sharing or permission changes, or when flow-access-fix hands over.
---

# Guest Exposure Audit

Check your client's guest exposure: what anyone on the internet receives, reads, runs or calls through each Experience Cloud site in an org you build for them, and what to change. Three parts, run in this order after one interview:

1. **The live guest pass.** Open each form as a logged-out visitor, fill it in with fake data, follow the prefill links, and list every field the browser **received**, marked shown on screen or not. A form can be handed a whole record; every field of it then reaches the browser and is readable in the developer console, even though the page shows five of them.
2. **The flow review** (needs the flows' metadata). Finds the flow behind it: a guest flow in system context whose Get Records stores all fields and passes the whole record into a form or record component, with no FLS Record(s) Sanitizer in between.
3. **The setup audit** (needs the org). What each site's guest can read, run or call: profiles, permission sets, guest sharing rules and their counts, site settings, guest flows, Apex. Read only, counts never record data. An opt-in outside probe confirms it from the public URL.

Nothing here writes to the org. The live pass is a visitor; it may create a test record only where the form saves as it goes, and only with the person's yes.

**Called by** ftk-start ("is the client's site exposing data", "check the guest access", "is this prefilled form safe"), flow-access-fix (it hands over after wiring guest access, to check the other direction), build-site-pages and build-template once a guest form or site is ready, and directly. **Hands over** to flow-access-fix for any change to a guest flow, a guest permission set's flow grants or a guest sharing rule.

## Where it runs

| Runtime | Live guest pass | Flow review | Setup audit |
|---|---|---|---|
| Claude Code, local or on the web | Headless: `scripts/guest_pass.cjs` (Node and Playwright with Chromium) | Retrieves the guest flows with the Salesforce CLI | One command with the Salesforce CLI, sharing rule criteria included |
| claude.ai chat, with a Salesforce connector | No browser here: the person captures a HAR with their browser's developer tools and uploads it; the same parser reads it | Only on flow files the person uploads (a connector reads records, not flow metadata) | Query by query through the connector; sharing rule criteria from Setup or a screenshot |
| claude.ai chat, no connector | The HAR path, as above | Uploaded flow files | Only from screenshots or files the person shares. Tell them plainly the audit needs the org |

Read on demand, beside this file:
- [references/live-pass.md](references/live-pass.md): the plan file, what the headless pass records, the developer tools steps for chat, and how to read the result.
- [references/flow-review.md](references/flow-review.md): the risky pattern, each check, the sanitizer fix, and how to run it.
- [references/what-it-reads.md](references/what-it-reads.md): every setup audit query, the snapshot, and the chat path.
- [references/fix-catalog.md](references/fix-catalog.md): each setup audit finding, its severity and its fix with the Setup clicks.
- [references/safe-guest-setup.md](references/safe-guest-setup.md): what a safe Flow Tool Kit guest setup has.
- [references/outside-probe.md](references/outside-probe.md): the opt-in outside probe.
- Scripts: `guest_pass.cjs` (Node), and `exposure.py`, `flow_review.py`, `guest_audit.py`, `probe.py` (Python 3 standard library). Each takes `--help`.
- Plugin standards: `_shared/standards/project-config.md` (which org), `_shared/standards/documentation.md` (section 6, Naming: where files go), `_shared/standards/runtime.md` (installing Playwright, network access on the web). Where this skill and a standard disagree, the standard wins.

## Safety rules for the live pass

Say these to the person before the first pass, and keep to them.

1. **Only a site you are authorized to test for your client.** The person confirms it in the interview; the plan file records `"authorized": true`, and the script refuses to run without it.
2. **Prefer a sandbox site,** with test records. Test a live site only when the client asks, and then only with test records.
3. **Ask before submitting a form.** The default is to fill in and step through to the last page, then stop without submitting. Offer that first. Submitting needs the person's yes for that form, `"submit": true` in the plan and `--allow-submit` on the command.
4. **Obviously fake test data only** (`Guest Check`, `guest.check@example.com`, `555-0100`). Never payment, card, password or file fields. A form that saves as you go (Autosave, Save Progress, a flow that saves between screens) can create a test record even without a submit: say so, and name it for the client to delete.
5. **Never try to bypass a sign-in, a CAPTCHA or bot protection.** The pass stops there and says so.
6. **Read only what the browser receives.** Use each prefill link exactly as given, for a test record the person chose. Never edit a link or guess a record Id to reach someone else's record.
7. **Keep captured payloads in the project folder, and redact personal data in the report.** Captures go to `_audits/guest-pass-<yyyy-mm-dd>/captures/`, out of version control, and are deleted once the fix is confirmed. The reports hold field names and the kind of each value, never the value, and replace link parameter values with placeholders.

## 1. Interview (one round)

Ask everything at once, numbered, each with its default, and go on with the defaults the person accepts:

1. **The site, and authorization.** Which site, and are you authorized by your client to test it? Default: the site of the org in `flow-tool-kit.json`. No live pass without a yes.
2. **Sandbox or live.** Default: the sandbox site.
3. **The forms.** The public addresses of the forms to test. Default: none until named; offer the guest flows the setup audit lists as a hint.
4. **Prefill links and templates.** Real prefill links with their parameters (`?pv1=<test record id>`, a resume link), each for a test record, and which Form Templates use a Pre-fill Template or a prefill flow. Default: none; the pass tests each form blank.
5. **Guest flows to review.** Default: every flow granted to a site's guest (from the setup audit), plus any the person names.
6. **What Claude can read.** In Claude Code with the Salesforce CLI signed in: the metadata, so all three parts run. In chat: the live pass by HAR, the flow review on uploaded flow files, the setup audit through a connector. Default: what this runtime can do, naming the parts it leaves out.
7. **Fill, step, submit.** Default: fill with fake data, step to the last page, never submit.
8. **Where captures go.** Default: `_audits/guest-pass-<yyyy-mm-dd>/captures/`, kept out of version control (offer the `.gitignore` line).

## 2. The live guest pass

**Claude Code:** write the plan (`guest-pass.json`, shape in [references/live-pass.md](references/live-pass.md)) from the answers, then:

```bash
node scripts/guest_pass.cjs --plan _audits/guest-pass-<date>/guest-pass.json --out _audits/guest-pass-<date>/captures
python3 scripts/exposure.py analyze _audits/guest-pass-<date>/captures/capture.json --out _audits/guest-pass-<date>
```

Each form opens in a fresh logged-out browser. The script records every data response from the site (Aura and LWR endpoints, UI API, Apex REST, GraphQL, the page document), the names of the flow or Apex actions behind them, the console, and the text and input values each page showed, through shadow roots. Fields are filled with fake data and Next is pressed up to `advance` times; it stops at the last page, a sign-in page or bot protection.

**Chat:** give the person the developer tools steps in [references/live-pass.md](references/live-pass.md) (private window, Network tab, Preserve log, fill and step through, stop before submit, export the HAR, copy each page's text into `shown.txt`), then:

```bash
python3 scripts/exposure.py analyze form.har --shown shown.txt --form "<form name>" --out <outputs folder>
```

Either way, `exposure.md` lists per form every record and field the browser received, shown or not, what each looks like (date of birth, government id, financial, health, protected characteristic, internal note, secret or token, personal contact, owner or audit), and whether another person's record arrived. `--subject-id <id>` names the record a prefill link is for, when the link does not carry it.

## 3. The flow review and the setup audit (metadata)

Run when the org's metadata is readable (Claude Code with the CLI), or on uploaded flow files.

```bash
# the setup audit (and, opt-in, the outside probe against a site you may test):
python3 scripts/guest_audit.py audit --org <org-alias> [--site "<Site label>"] [--probe "https://<site>/s"] \
    --out _audits/guest-exposure-<date>
# the flow review of the guest flows it found, plus any the person named:
python3 scripts/flow_review.py review --org <org-alias> --flow <Flow_Api_Name> [--flow ...] \
    --snapshot _audits/guest-exposure-<date>/snapshot.json --out _audits/guest-pass-<date>
```

In chat with a connector, the setup audit runs query by query ([references/what-it-reads.md](references/what-it-reads.md), "The chat path"), and the flow review runs on uploaded files: `python3 scripts/flow_review.py review <flow files> --guest-flow <name>`.

The flow review flags, per flow, naming the flow, the element, the component and the fix ([references/flow-review.md](references/flow-review.md)):
- **System context, all fields, to a form, no sanitizer:** a Get Records storing all fields whose record reaches a screen component (Form (Component) `record`, Form (Template) `formSubmission`, Form (Table) or Form (Repeater) `prefillRecords`, any other) or an output such as a prefill flow's `prefillRecord`, without the FLS Record(s) Sanitizer between them. HIGH when a guest runs it. **Not** flagged when the record goes through the sanitizer first.
- **A lookup by a value the visitor controls,** in system context (an input variable or a URL parameter), whose record reaches the screen: anyone who edits the link reads another person's record. HIGH when a guest runs it, sanitizer or not.
- **Chosen fields that look sensitive,** in system context: MEDIUM. **All fields in the default context:** LOW.

## 4. Report it

Join both parts into one report, then lead with the outcome:

```bash
python3 scripts/exposure.py report --exposure _audits/guest-pass-<date>/exposure.json \
    --flows _audits/guest-pass-<date>/flow-review.json --out _audits/guest-pass-<date>
```

`guest-report.md` has one row per form or flow: what is exposed, the severity, and the first fix; a flow finding the live pass saw in action is marked confirmed. Put it to the person in one sentence first ("The renewal form sends each visitor the contact's birth date and case notes; one flow to fix"), then each HIGH and MEDIUM row, consequence first, then the setup audit's `findings.md` the same way, then the file paths. Every report holds field names and value kinds only, so it can go to the client; it describes how to reach their data, so keep it out of public places. In claude.ai the report can also be shown as an artifact page for the client.

**The fix for a flow sending whole records, in order:**
1. **The FLS Record(s) Sanitizer.** In the system-context flow: Get the record, pass it through the Flow Tool Kit action **FLS Record(s) Sanitizer** (`FlowToolKit__DataSanitizer_Invocable`, inputs Record and Record(s)), then pass the action's Record output into the form component. It removes every field the running user has not been granted, so guest access is controlled the normal way, by the guest's profile and permission sets: if the guest can read only First Name and Last Name on Contact, that is all the form receives.
2. **Keep the guest's field Read** to the fields the form shows.
3. **Query only the needed fields** in the Get Records.
4. **Avoid system context** where the flow does not need it.
5. **Scope prefill templates and prefill flows:** a Pre-fill Template holds defaults only, and a prefill flow sets only the fields the form shows.

A lookup by a value from the link needs a single-use token or a sign-in instead; the sanitizer strips fields, not records.

## 5. Fixing

This skill changes nothing. Then:
- **Guest flows, flow grants, guest sharing rules, the guest save and resume flows:** flow-access-fix makes those changes and checks a guest form still works afterwards. Change in this order: narrow (add the sanitizer, narrow field Read), test the form as a guest, then remove the rest.
- **Object and field access, system permissions, site settings, Apex:** the person changes them in Setup ([references/fix-catalog.md](references/fix-catalog.md)), or asks for the metadata change as separate work.
- **Run the pass and the review again** after the fixes: each finding should be gone, and each form should receive only what it shows.

## How severity is decided

| Severity | Means | Examples |
|---|---|---|
| HIGH | Anyone can read or change data they should not, today | A form receives a hidden date of birth, government id, financial, health or internal note field, or another person's record; a guest flow in system context passes a whole record to a form without the sanitizer, or looks a record up by a link value; people's records shared with guests; Edit, View All or Modify All for a guest; guest flows or Apex without sharing |
| MEDIUM | Exposure wider than needed, or one step from HIGH | Hidden contact details or owner and audit fields; chosen sensitive fields in a system-context flow; a flow whose guest use is not known; every record of an object shared; API Enabled; guest member visibility |
| LOW | Least privilege | Other hidden fields (more than the form needs); all fields in a default-context flow; Read on Contact with nothing shared; a class with nothing to call granted |
| INFO | Worth knowing | Packaged code a guest reaches; self-registration on |

A guest-readable record can be fetched by anyone through the site's own data services, not only seen on its pages. And whatever a flow hands a component reaches the browser in full, whatever the component shows. So the audit counts what the guest *can* read, and the pass lists what the browser *did* receive.

## Done when

- The interview answers are recorded in the plan, with authorization confirmed.
- Every named form and prefill link has a row in `exposure.md`, or a note why it could not run (sign-in, bot protection, no browser).
- With metadata: `flow-review.md` covers every guest flow, and `findings.md` exists for the org.
- `guest-report.md` gives each form or flow its severity and exact fix, the sanitizer first where a flow sends whole records, and every HIGH and MEDIUM was put to the person, consequence first.
- Anything not run or not read is said, not guessed. After fixes, a second pass shows the findings gone.

## Common mistakes

| Mistake | Instead |
|---|---|
| Judging a form by what it shows | List what the browser received: a hidden field is one console command away |
| Recommending "query fewer fields" first | The FLS Record(s) Sanitizer first: then the guest's permission sets decide, the normal way |
| Treating the sanitizer as a fix for a lookup by a link value | It strips fields, not records. Use a single-use token or a sign-in |
| Submitting a form to see what happens | Stop at the last page. Submit only with a yes, on a sandbox, with fake data |
| Editing a prefill link to test someone else's record | Never. The flow review finds that pattern from the metadata |
| Pasting captured values into the report | Field names and value kinds only. Captures stay in the project folder |
| Reading records to "see what is exposed" in the setup audit | Counts only. The object, the rule's criteria and the count say enough |
| Treating the package's guest rules or the guest save copy as findings | They are the expected setup ([references/safe-guest-setup.md](references/safe-guest-setup.md)) |
| Removing guest access before the form has been tested without it | Narrow, test as a guest, then remove |
| "0 findings, so it is safe" | The checks are patterns. A pass with no prefill link never sees a prefilled record; the flow review needs every guest flow |
| Pointing the pass or the probe at a site you are not authorized to test | Only your client's site, named, with their authorization; a sandbox first |
