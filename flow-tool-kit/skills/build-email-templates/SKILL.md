---
name: build-email-templates
description: Builds the emails a Flow Tool Kit (FTK) Form Template sends, as branded Lightning Email Templates on Form Submission, sets them on the Form Template, and proves them with a test email read back from the org. Covers the confirmation email, the Save Progress email, the stages resume-link email, start invitations and staff notifications. Use after build-template, or when someone says "add a confirmation email to this form", "redo the thank-you email", "people need a link back to their saved form", "tell our staff when an application comes in" or "why didn't the confirmation send".
---

# Build Email Templates

Every real form needs a confirmation, and most need a way back to a saved draft. This skill turns the emails form-design drew (or a short brief) into Lightning Email Templates on Form Submission, so each email merges the respondent's own answers, wraps them in the organization's letterhead, names them on the Form Template, and sends one test to prove it.

| Email | Form Template field | Sent when |
|---|---|---|
| Confirmation, one per form | Email Template Name (Confirmation), with Send Confirmation Email on | A submission is received and converted |
| Save Progress, usually one shared | Email Template Name (Saved), with Send Save Progress Email on | A respondent saves an ordinary form (never in stages mode) |
| Resume link, usually the same shared one | Email Template Name (Resume Form) | A stages-mode respondent clicks Email me a resume link |
| Start invitation (optional) | Email Template Name (Start Form) | An admin's flow creates a draft with a token |
| Staff notification (optional) | None: a small flow this skill builds | A submission for that form is received |

The package's exact rules for each (who receives it, what it renders against, what happens when it cannot send) are in [references/package-behaviour.md](references/package-behaviour.md). Read it before promising anything about delivery.

## Where it runs

| Surface | What works |
|---|---|
| Claude Code (local or on the web) with the Salesforce CLI | Everything: build, deploy the templates as metadata, deploy the staff notification flow and the answers-PDF running user, set the Form Template fields, render without sending, test, read back |
| claude.ai chat with a Salesforce connector that can query and create records (such as Salesforce's hosted MCP server) | Build in code execution, create or update each template as an **EmailTemplate record**, set the Form Template fields, create a test submission and read the email back. Not possible in chat: the staff notification flow and the answers-PDF running user (both are metadata), and the image address check |
| Chat without a connector | Build and preview. Hand the person `build.json` and the template files, and say the deploy and test need a connector or Claude Code |

Say which steps need Claude Code before starting, not halfway through.

## Before building

1. **The project config**, `flow-tool-kit.json` (format: `_shared/standards/project-config.md`): the org, its edition and whether the person chose a brand kit. Read `_shared/standards/documentation.md` (section 6 is Naming): descriptions and names on templates and flows follow it.
2. **The plan.** form-design's `plan.json` for the form, with its `emails`, `template`, `style` and `assets`. The emails were reviewed on the canvas; build them as drawn and do not rewrite approved words. No plan (an existing form): read the Form Template from the org (Name, Stages Mode, Allow Save Progress, Send Save Progress Email, Attach PDF, Recipients, Web Form URL, and its pages' fields), then write the emails into `_forms/<slug>/emails.json` with the same keys. Format: [references/emails-format.md](references/emails-format.md).
3. **The brand**, only if the person chose one: org-catalog's catalog (`brand_kit`) or the saved `brand-kit.json`. None is fine: the letterhead falls back to Flow Tool Kit's neutral palette. Images must be Public Asset Files; how and why: [references/brand-and-images.md](references/brand-and-images.md).
4. **The org context**, `org.json`: org Id, My Domain URL, the Asset Files and the Form Submission field names (queries in references/emails-format.md). In Claude Code run them with `sf data query`; in chat, through the connector. With no org yet, build without it to review the words: the images are left out and the merges are not checked against the org. Build again once it is connected, before anything is deployed.

## Writing the words

When the plan has no emails yet, write them in the organization's voice (the brand kit's tone, the program page's words):

- **Confirmation**: a subject that names the form; a heading; at least two paragraphs: thanks with what was received (the key answers as merges, such as the project title and amount), what happens next and when, and who to contact. One button to something useful (the program page), never back to the form.
- **Save Progress and resume**: short. The button merges `{{FlowToolKit__Internal_Resume_Link__c}}`. Tell them the link works once and for seven days, and that they can ignore an email they did not ask for. One shared template per organization, worded for any form, since it cannot merge the form's name.
- **Staff notification**: who sent what (direct submission fields), and the submission number (`{{Name}}`) to find it.
- Merges are direct Form Submission fields only: [references/merge-fields.md](references/merge-fields.md). No em-dashes; unknown facts as `[placeholders]` the person fills before the build (the build refuses a placeholder).

Show the person the subject and words of each email, and confirm them in one message before building ("Here is the confirmation. Reply yes, or tell me what to change").

## The run

1. **Build and check.**

   ```bash
   python3 scripts/emailbuild.py build _forms/<slug>/plan.json [more plans] --org org.json [--catalog catalog.json] [--brand brand-kit.json]
   ```

   It writes nothing until every check passes: developer names, every merge against the org's fields, no relationship merges, the resume link where it belongs (and only there), the confirmation's next step and contact, the email that fits the form's mode (Save Progress for ordinary pages, Resume Form for stages), public images and contrast. Each message names its fix in the plan. Several plans at once share templates with the same name. Outputs: the templates under `force-app/main/default/email/unfiled$public/`, any staff flow under `force-app/main/default/flows/`, and `build.json` and `preview.html` beside the plan.
2. **Look at it.** Open `preview.html` yourself and check every email: the letterhead, the merges' sample values, the button. In Claude Code also run `python3 scripts/emailbuild.py check-images _forms/<slug>/emails/build.json`. Give the person the preview (as an artifact if they want a link).
3. **Put the templates in the org.**
   - **Claude Code:** tell the person which templates and flows go to which org, then `sf project deploy start --source-dir force-app/main/default/email --target-org <org-alias>` (add the flows folder when there is a staff flow). Metadata keeps the templates in the project, so the same files deploy to the next org after a build with that org's context.
   - **Chat with a connector:** for each template in `build.json`, query `SELECT Id FROM EmailTemplate WHERE DeveloperName = '<name>'`. Found: update that record with the `record` values. Not found: create an EmailTemplate record with them. `FolderId` is the org Id, which files it under Public Email Templates. Never create a second template with an existing developer name: the most recently changed one wins, so an old copy can quietly take over.
4. **Set the Form Template.** Write each form's `settings` from `build.json` onto its Form Template (found by `Name`, or the `id` when given): the template names, Send Confirmation Email, Send Save Progress Email, Recipients and Attach PDF. In Claude Code use `sf data update record --sobject FlowToolKit__Form_Template__c --record-id <Id> --values "..."`; in chat, the connector's update tool. Field names take the `FlowToolKit__` prefix.
5. **Answers PDF, if Attach PDF is on.** The conversion needs a running user that can open the PDF page. Deploy the Platform Event Subscriber Config and have the person Suspend and Resume the trigger (references/package-behaviour.md). Claude Code only; from chat, hand over the file and the steps.
6. **Prove it**: a test email, read back and checked with `emailbuild.py verify`. Steps, queries and every log message's fix: [references/proving.md](references/proving.md).
7. **Record it.** In the plan's `decisions`, note which templates were built, for which org, and the test result. A template built for a sandbox carries that sandbox's image addresses: build again with the next org's context before deploying there.

## Done when

- `emailbuild.py build` ran clean; the person has seen the preview.
- Every template is in the org once, by its developer name, on Form Submission, in Public Email Templates.
- Each Form Template names its templates, and the email switches match the form's mode.
- A test email arrived and `verify` passed: merges filled, images in place, the PDF attached when asked. The Conversion Log shows the send.
- The person knows what still needs Claude Code (a staff flow, the PDF running user) when the work happened in chat.

## Common mistakes

| Mistake | Instead |
|---|---|
| `{{Form_Template__r.Name}}` or any relationship merge | Direct Form Submission fields; write the form's name into the words |
| A resume link built with `pv9` or `recordId` | Merge `{{FlowToolKit__Internal_Resume_Link__c}}` |
| A Save Progress email on a stages-mode form | Stages sends the Resume Form email; Save Progress never sends there |
| A template in a new custom folder | `unfiled$public` (Public Email Templates); a new folder can deploy Hidden and break the deploy |
| Images from the site, Lightning or a static resource | Public Asset Files at their `file-asset-public` address, built per org |
| Deploying a sandbox build to another org | Build again with that org's context: the image addresses carry the org |
| Expecting the branded Save Progress email for a guest with no Contact 1 | That guest gets the built-in email by design. Tell the person |
| Testing the confirmation on a form that creates no Contact or Lead | The confirmation needs Contact 1 or Lead 1 after conversion |
| Calling it done after the deploy | A test email read back is the proof |
| Attach PDF on, no running user | Deploy the subscriber config, then Suspend and Resume the trigger |
