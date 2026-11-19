# The live guest pass

Open each form the way an anonymous visitor does, fill it in with fake data, and record what the browser **received**, not only what the page shows. A Flow Tool Kit form, table or repeater can be handed a whole record; every field of it then travels to the browser and can be read in the developer console, shown on screen or not. The pass lists each field the browser received and marks which were shown.

## Safety rules

The safety rules in [SKILL.md](../SKILL.md) apply to every pass, headless or by hand. In short: only a site you are authorized to test for your client, a sandbox first, fake data, no submit without a yes, never past a sign-in or a CAPTCHA, read only what the browser receives, and captures stay in the project folder while the report is redacted.

## Claude Code: the headless pass

Needs Node and Playwright with Chromium (`npx -y playwright@1.47.2 install chromium`, once). The script finds Playwright from the project, a global install or the npx cache.

1. Write the plan from the interview, `_audits/guest-pass-<yyyy-mm-dd>/guest-pass.json`:

```json
{
  "authorized": true,
  "sandbox": true,
  "forms": [
    {"name": "Volunteer sign-up", "url": "https://<sandbox site>/s/volunteer", "fill": true, "advance": 5, "submit": false},
    {"name": "Volunteer renewal", "url": "https://<sandbox site>/s/renewal", "fill": false, "advance": 0,
     "prefill": ["https://<sandbox site>/s/renewal?pv1=<test contact id>"]}
  ]
}
```

   `advance` is how many Next presses at most; `prefill` lists real prefill links (each opened as its own pass, named "(prefill link 1)" and so on); `submit` stays false unless the person said yes for that form.

2. Run it, then read the capture:

```bash
node scripts/guest_pass.cjs --plan _audits/guest-pass-<date>/guest-pass.json --out _audits/guest-pass-<date>/captures
python3 scripts/exposure.py analyze _audits/guest-pass-<date>/captures/capture.json \
    [--subject-id <test contact id>] --out _audits/guest-pass-<date>
```

What it records, per form, in a fresh logged-out browser (no cookies, service workers off):
- **Every data response from the site:** the Aura and LWR endpoints (`/sfsites/aura`, `/webruntime/`), UI API, Apex REST and GraphQL calls, and the page document itself, with the names of the Aura actions behind each (the flow or Apex method, never the values sent).
- **What each page showed:** the visible text and the values in visible inputs, read through every open shadow root (LWR components render inside them), after opening, after filling and after each Next.
- **The console:** messages and page errors.
- **Where it stopped:** the last page, a sign-in page, bot protection, or a page that would not open.

Component data is covered by the responses: everything a component holds reached the browser through one of them or through the page document.

`exposure.py` walks each response for records: Apex and flow records (`attributes.type`), UI API records (`apiName` with field values) and plain maps with an Id and field names, also inside JSON held as text. Framework metadata (labels, field definitions) is not a record. Each field value is compared with what the pages showed (a date shown as 4/12/1990 counts as shown).

## In chat: capture it with the browser's developer tools

Chat has no browser of its own, so the person captures the same thing and uploads it. Give them these steps, adjusted to their browser:

1. Open a **private or incognito window**, so they are a logged-out visitor.
2. Open the developer tools (F12, or right-click, Inspect) and the **Network** tab. Turn on **Preserve log**.
3. Open the form's address (or the prefill link). Fill it in with fake data and press Next through the pages. **Stop on the last page; do not submit** unless you agreed to.
4. Save the network log as a HAR: in Chrome or Edge, the download arrow in the Network tab, **Export HAR (sanitized)** (sanitized leaves out cookies, which the analysis does not need); in Firefox, the gear menu, **Save All As HAR**; in Safari, **Export** in the Network tab.
5. On each page, select all the page's text and copy it into one text file, `shown.txt`. This is how the analysis knows what was on screen. Without it the report says "not checked" instead of "not shown".
6. Optional: copy any red errors from the **Console** tab.
7. Upload the HAR and `shown.txt`. The HAR holds what the site sent, which may include personal data: on a sandbox with test records that is fine; for a live site, upload only where the client agreement allows it.

Then, in chat:

```bash
python3 scripts/exposure.py analyze form.har --shown shown.txt --form "Volunteer renewal" [--subject-id <test contact id>] --out <outputs folder>
```

The same parser reads a HAR and the headless capture, so both paths produce the same report.

## Reading the result

| Severity | When |
|---|---|
| HIGH | A field that looks sensitive reached the browser and was not shown: a date of birth, a government id, financial, health, a protected characteristic, an internal note, a secret or token. Or **another person's record** reached the browser (a person record whose Id is not the one in the prefill link or `--subject-id`; with no Id given, more than one person's record) |
| MEDIUM | Personal contact details, or owner and audit fields (owner, created by, modified dates), received and not shown |
| LOW | Other fields received and not shown: more than the form needs, nothing sensitive by name |
| CLEAN | Nothing beyond what the form shows |

"Looks sensitive" is by field name and by value shape (a Social Security number or card number pattern, an email address). Read the table for each form: a field named for the client's own business (a case worker's assessment, a household's income band) may need a human eye.

The fixes are in the report, in this order: pass the record through the **FLS Record(s) Sanitizer** action before the form, narrow the guest's field Read, query only the needed fields, avoid system context, scope prefill templates. The flow review ([flow-review.md](flow-review.md)) names the flow and element to change.
