# Building from claude.ai chat

Chat has no Salesforce CLI and no anonymous Apex. With a Salesforce connector that can create, update, delete and query records, chat runs a **records-mode** build (`intake.build_mode: "records"`, SKILL.md, Build modes): the template, its pages, its sections and its new or extended components, all as records and JSON. Nothing is deployed. What needs a deploy is in the dry run's `follow_ups`: tell the person plainly and hand those to Claude Code with `plan.json`.

A plan in metadata mode with a metadata component cannot finish here. Say so in one line and ask whether to switch the plan to records mode (set `intake.build_mode` to `records`) or wait for Claude Code.

## Steps

1. Run the dry run in code execution, with the project config among the conversation's files:
   ```bash
   python3 scripts/buildtemplate.py plan.json --config flow-tool-kit.json --dry-run --out build-records.json
   ```
   It checks the plan exactly as a real build does, then writes `template`, `pages` and `sections` (each with its `page_key`), `components_to_create`, the header choice, `convert_later` and `follow_ups`. Every value of the brand is on the template's Style Overrides, and the logo on its Logo Override.
2. Check the org through the connector first: Form Template is there; every object and field the plan names exists (a query on FieldDefinition); every component a `reuse` names exists (Form Component by QualifiedApiName, and for a record component its Id); every Asset File the plan names exists. If a field the plan proposes (`new_field: true`, the `new fields` follow-up) is not in the org, run the dry run again with `--missing-fields <Field__c,...>`: the form leaves those fields, and their own rules, out until Claude Code creates them. A field the plan uses as existing must be in the org.
   **Reused components are never copied.** A section that reuses a component points at it: a metadata component by its API name, a record component as `<Name>_v0` with its Id. Do not export, import or recreate it.
3. **Record components** (`components_to_create`: a Compact or Split header, an extended, shared or one-off component, including the ones the plan marks metadata, which records mode builds as records; tell the person which ones, from `convert_later`): if the connector can run Apex, run `FlowToolKit.FormComponentImport.createRecordComponent` with each JSON. Otherwise give the person each JSON to paste into Form Builder's Form Component Import, one by one, and wait. Then query each one's Id (Form Component, `QualifiedApiName__c`, Record Type Record Component). An extend copy needs the original's exported JSON as `components[].design_file`.
4. **Template**: create the Form Template from `template` (or update the one in `build.template_id`). Flow Tool Kit gives a new template a Pre-fill Template, a Form Submission: query the template's `Prefill_Template__c` and save it as `build.prefill_template_id` unless the plan names its own. Save the template's Id into `plan.json` under `build.template_id`, with `build.key` and the `build.prefix` and `build.form_ids` the dry run wrote, and `built_shape: "record"` on each component `convert_later` names.
5. **Pages**: query the template's pages. Update the ones whose `ExternalId__c` matches a page in the file, create the others with the template's Id, and delete any page not in the file (the package adds a default page to a new template).
6. **Sections**: delete every section on the template's pages (the package adds a default section to every new page), then create each section from the file on the page its `page_key` names. Where a section points at a record component, put that component's Id in `Form_Component__c`.
7. Count what the org holds against the plan: pages, sections per page, and rules (page, section, and field rules inside each section's JSON). They must match.

If a step fails after a new template was created, delete the template and its Pre-fill Template (`build.prefill_template_id`), then start again; never patch it by hand.

## What needs Claude Code

The dry run's `follow_ups` name each of these that this plan needs, with the skill that does it. Hand them over by name; the build in chat is complete without them.

| Step | Why |
|---|---|
| New fields and their permission set (`newfields.py`), then a rebuild so the form shows them | Metadata deploy |
| Form Labels and translations the copy's `{{$Label.X}}` tokens need (`formlabels.py`) | Custom metadata deploy; until then the words show nothing where a token is |
| Section Tags the org's Data Conversion Tag(s) values lack, and an inactive or missing prefill flow | Setup and Flow Builder; the build leaves the tag off and names the flow |
| Converting the record components records mode built in place of metadata ones (`convert_later`) | convert-to-metadata, when the project moves to metadata |
| The add-only org styles and Default Logo | The protected setting; in chat the brand stays on the template. The person can save the org defaults in Form Builder's Global Styles tab |
| The PDF running user (`runninguser.py`) | Metadata deploy, then Suspend and Resume in Setup |
| The round trip (`roundtrip.py`) | It reads the org with the CLI; in chat, compare what the queries return with the plan by eye, page by page |
| Flow Sections, custom LWCs, email templates, conversion flows | Their own skills, which deploy metadata |
