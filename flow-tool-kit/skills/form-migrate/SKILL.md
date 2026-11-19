---
name: form-migrate
description: Read any existing form, whatever shape it is in, into one normalized form description (ir.json) and a reviewable field plan for the Flow Tool Kit (FTK) Form Template framework. Use for FormAssembly (link, export or API access) and PDF forms (fillable or flat), a brief for a form that does not exist yet, a Word document, a custom web form by address or saved page, Google Forms, Microsoft Forms, Jotform, Typeform, Wufoo, Cognito or any other builder, screenshots or photos of a paper form, a spreadsheet of questions, a .dc.html design file, or an existing Form Template being cleaned up. Records how it knows each claim, plans where each question is built by FTK edition, lists the decisions only the org's people can make, and hands the result to form-design. Works in claude.ai chat (with or without code execution) and Claude Code.
---

# Form Migrate

This skill answers one question about a form: **what does it actually do?** It reads whatever the source gives up, normalizes it into one `ir.json`, and turns that into files a person can review: a mappings file, the questions only they can answer, and a discovery report. Designing the rebuild, building it and converting submissions belong to other skills (see The relay in references/conversion-rules.md).

**Bring us whatever form you have.** FormAssembly and PDF forms get the deepest read (FormAssembly is the only source that also carries its Salesforce mapping). A brief for a form that does not exist yet works the same way. So do a Word document, a custom web form by its address or a saved page, any other form builder, screenshots or phone photos of a paper form, and a spreadsheet listing the questions. When no reader fits, Claude reads the form itself and writes down every question faithfully, marking what it cannot see as unknown; **ftk-start**'s gap interview then asks only what a complete Form Template still needs, each with a default. No source is turned away for lack of an adapter.

It is usually run by **ftk-start**, which reads the org first and records the setup answers. It can also be run on its own.

## Where it runs

| Surface | What works |
|---|---|
| claude.ai chat, code execution off | Claude reads the source (a page, a PDF, a document, screenshots or photos) and lists every question, choice, rule and formula for confirmation, then writes `capture.json` and a mappings table in the reply. Follow [references/chat-extraction.md](references/chat-extraction.md) |
| claude.ai chat, code execution on | Everything below except the Salesforce CLI. The sandbox may not reach the web: fetch the page with the session's web tools or ask for the saved page, then run the scripts on the file. Read the org through a Salesforce connector and save its describe to a file |
| Claude Code, local or on the web | Everything, including reading the org and an existing Form Template through the Salesforce CLI (`sf`) |

Say which runtime you are in when it limits the result (for example, "no org connected, so every Form Submission field is marked verify").

## Before you start

1. **Read the project config.** ftk-start writes `flow-tool-kit.json` at the project root, one entry per org keyed by its org Id (in chat, look in the files attached to the conversation or the claude.ai Project). Take the org's **edition** (`paid` or `free`) and its platforms from it, and never ask those again. The scripts read it themselves; `--edition` overrides it. If the edition is missing, the plan leaves those questions unplaced and asks it first.
2. **Know which org you can read.** In order of trust: the org through the Salesforce CLI, a describe of Form Submission saved from a Salesforce connector, retrieved metadata in `force-app`, or nothing. With nothing, the plan uses the packaged field list shipped with this skill and marks every row **Verify In Org**. The plan is still complete; the names are checked when an org is connected.

## Sources, files, running it and where each question is built

To pick the source's reader, run the readers and the planner, and place each question, read [references/sources-and-running.md](references/sources-and-running.md) (Pick a source, Where files go, Running it, Reading the org, Where each question is built: the mapping preference).

## The one thing that matters most

**An empty list has three incompatible meanings.** `"conditions": []` means the platform has no conditional logic, or the form was read and has none, or nobody looked. Identical JSON, opposite consequences.

So every source declares, per aspect (structure, fields, options, validation, conditions, connector, images, custom scripts), **how it knows what it claims**:

| State | Meaning |
|---|---|
| `parsed` | read by a parser from a machine-readable source |
| `hand_authored` | transcribed by a person, or by Claude reading the page or PDF |
| `none_exist` | the source has no such thing (a Google Form's connector) |
| `not_captured` | it exists and was not read: a known gap |
| `unknown` | nobody said; treated as `not_captured` and reported |

The checks skip whatever was not captured and say so, and an absent mapping counts as "not saved today" only when a connector was actually read. Never declare `none_exist` to make output look clean: a form that posts to an endpoint nobody has read is `not_captured`.

## Show what you extracted, then confirm

Before any plan, show the person what was read, in a few lines, and ask them to confirm or correct it. Do not ask them for what the source already says.

> Your form has 3 pages and 24 questions. Page 2 shows the fiscal sponsor questions only when "Registered nonprofit?" is No. The total on page 3 is a formula (amount times quantity). I could not see the connector, so where answers are saved is unknown. Correct?

Every count in that message comes from the source, taken independently of the parser (each reference lists its counting commands), and every gap is named with its coverage state.

## Reviewing the plan

The reviewer edits `mappings.csv` or `mappings.json` (first three columns: Decision, Your Field Name, Your Notes), or a review page published as an artifact when the session can publish one; then run `plan_form.py` again and the edits come back, keyed by field id. Blank means not reviewed, never accepted. Details: [references/mapping-review.md](references/mapping-review.md).

## Rules that govern the conversion, and the relay

Before planning any conversion and before handing over to new-mapping-flow, read [references/conversion-rules.md](references/conversion-rules.md) (Rules that govern the conversion, The relay).

## Common mistakes

| Mistake | Instead |
|---|---|
| Asking how many pages or rules the form has | Read them and ask to confirm |
| Declaring `none_exist` for something nobody read | `not_captured`, named in the confirmation |
| Asking the edition again when the project config has it | Read `flow-tool-kit.json` |
| Treating names from the shipped list as checked | Rows stay Verify In Org until an org is read |
| A custom LWC where a formula would do | Lowest rung first; explain why a rung does not fit before climbing |
| Treating a blank row in the mappings file as accepted | Blank means not reviewed |
| A new field because a packaged picklist lacks values | Add the values in this org, when the field otherwise fits |
