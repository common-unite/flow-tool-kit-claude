# Build modes

Moved from this skill's SKILL.md, read on demand: Build modes.

## Build modes

ftk-start and form-design ask once, in their gap round: "Build as metadata, or load as records for fast prototyping?" The answer is `intake.build_mode` in `plan.json`: `metadata` or `records`. A plan without it (every plan written before modes) builds as `metadata`, exactly as before.

| Mode | When | What it builds |
|---|---|---|
| **metadata** (default) | The forms live in source control and move between orgs by deploy; work in Claude Code | Every component in the shape the plan names; a metadata component is handed to build-form-component and bound by name once deployed |
| **records** | Quick design, review and change: a draft people click through today, changed in seconds during a review, from claude.ai chat or Claude Code | The Form Template, its pages and sections, and its **new or extended** components as records and JSON sections only. No metadata deploy, ever |

Records mode is a first-class way to build, not a fallback. Everything in it can be done from claude.ai chat with a Salesforce connector ([references/chat-build.md](chat-build.md)); in Claude Code the same run uses the Salesforce CLI and anonymous Apex for the record components.

**The reference rule (both modes).** A component org-catalog's review marked **reuse** (an existing metadata or record component) is only **referenced**, never copied into a new record or JSON: a metadata component by its qualified API name, a record component as `<Name>_v0` with its record Id (the package's version 0). The catalog already knows its fields and shape, and form-design checked it meets the design. Only new or extended pieces are created. An `update` is also only referenced here; build-form-component makes the change.

**In records mode:**

- A component this plan builds that the plan marks `metadata` (a `form-only` one-off, a `shared-new`, an `extend` copy) is built as a **record component** instead, under the same name. The build says so in its warnings, writes `components[].built_shape: "record"` into `plan.json` and lists it under the report's `convert_later`, so **convert-to-metadata** can convert it when the project moves to metadata. A later build in metadata mode hands it to build-form-component as planned and clears `built_shape`.
- What cannot be done without a metadata deploy is never attempted and never fails the build: it is listed in the report's `follow_ups`, each with the skill that does it from Claude Code:

| Follow-up | Why it needs Claude Code | Meanwhile |
|---|---|---|
| **New custom fields** the plan proposes (`new_field: true`) and their permission set (`newfields.py`) | Custom fields are metadata | The form leaves them out (the report's `left_out`) with their own rules; rebuild once they are deployed. A page, section or field rule that reads one is never written (a rule on a field the object lacks stops its section from drawing): it is listed in `left_out` and the follow-up "rules waiting for new fields", and what it governs always shows until the rebuild |
| **Form Labels** and their translations the copy's `{{$Label.X}}` tokens need (`formlabels.py`) | Form Labels are custom metadata | The words show nothing where a token is |
| **Picklist values** a planned option needs that the field, or the form's record type, does not offer | A picklist value is metadata (Setup) | The form leaves that option out; it already lists it, so it shows once added, with no rebuild. The round trip lists it as waiting for Setup, not as a mismatch |
| **Section Tags** the org's picklist lacks, and the **prefill flow** when it is missing or inactive | A picklist value (Setup) and a flow | The section has no tag; the form says its default answers could not be loaded |
| **Flow Sections** (build-flow-section) and **custom LWCs** (build-custom-lwc) | Flows and Lightning web components are metadata | The section already names them |
| **Email templates** (build-email-templates) | When the email templates need a deploy | The package sends its built-in emails |
| **The answers PDF running user** (`runninguser.py`) | A Platform Event Subscriber Config is metadata | The confirmation email goes without the PDF |
| **An approved update to a shared metadata component** (build-form-component) | A deploy | The section shows the component as it is |
