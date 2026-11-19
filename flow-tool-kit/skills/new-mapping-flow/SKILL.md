---
name: new-mapping-flow
description: Plan and build the flows that turn a submitted Flow Tool Kit Form Submission into Salesforce records, and the prefill flows that fill a form from existing records. Covers the shared mapping preference (packaged conversion flows plus Form Template Mapping on paid orgs, Transform rows on free orgs), when to override a packaged conversion flow and when to build a new one from the package's templates, wiring a new flow to Form Templates and sections through the Conversion Map Flow picklists, and building a new conversion rule with its controller when the package has no flow for the target object (for example a Nonprofit Cloud Individual Application). Use when build-template hands over a built form, or when someone asks to map a form's answers to Contacts, Accounts, Opportunities, Cases or their own objects, to add a conversion step, to fix a conversion that runs but writes nothing, or to write a prefill flow.
---

# New Mapping Flow

Builds Flow Tool Kit conversion flows the way the package expects: on the platform-event pattern, with the packaged Setup and Log actions, a logged outcome on every path and a dedicated return to the controller.

**Where it runs.** Building and deploying flows needs Claude Code with the Salesforce CLI (`sf`) connected to the org. In claude.ai chat this skill explains, plans and drafts: it reads the org through a connected Salesforce connector when one is present, runs `scripts/mapping_plan.py` in the code sandbox, writes the spec, the field map and the flow plan as files, and hands the deploy to Claude Code.

**Called by** build-template (its last handover, after the template is built), ftk-start, form-migrate and formassembly-capture, and directly. **Hands over** to flow-access-fix for every prefill flow (or other flow a person runs), once per audience, and to new-invocable for any mapping step that needs Apex.

Read on demand, beside this file:
- [references/work-list.md](references/work-list.md): what `scripts/mapping_plan.py` reads from the plan, the catalog and the project config, this skill's own `mapping-spec.json`, and the work list it writes.
- [references/pipeline-architecture.md](references/pipeline-architecture.md): the event chain, the controller, the Setup and Log actions, rules and statuses, override mechanisms and the packaged flow inventory.
- [references/exemplar-flows.md](references/exemplar-flows.md): how the packaged conversion flows are built, element by element, with excerpts of the Opportunity flow (the fullest current pattern).
- [references/extension-patterns.md](references/extension-patterns.md): one engine with form-agnostic utilities, the post-save router, hold-back ordering, deferred work, record writing, and repointing packaged custom metadata safely.
- [references/new-object-rule.md](references/new-object-rule.md): the full path when no packaged conversion flow exists for the target object, and the worked example for a Nonprofit Cloud Individual Application.
- [references/traps.md](references/traps.md): the Flow Builder round-trip traps, the Automated Process user, namespaces, record types and duplicate rules, and the fixes a cloned flow must carry forward after an upgrade.
- [references/form-template-discovery.md](references/form-template-discovery.md): draft a field map from a built Form Template when no mapping document exists.
- `scripts/wiring_check.py`: checks a new flow's Conversion Map Flow values (value = the flow's API name) and the template and section settings that select them (Step 6, in references/build-deploy-and-prefill.md).
- Plugin standards: `_shared/standards/mapping-preference.md`, `_shared/standards/documentation.md` (section 2, Flows: names, elements and descriptions), `_shared/standards/naming.md`, `_shared/standards/plan-format.md`, `_shared/standards/catalog-format.md`, `_shared/standards/project-config.md`. Where this skill and a standard disagree, the standard wins.

## Step 0: Start from what exists

1. **What the chain already decided.** When the form came through form-design, never ask again what its files answer. Run:
   ```bash
   python3 scripts/mapping_plan.py _forms/<slug>/plan.json --out _forms/<slug>/mapping-work.json
   ```
   It reads `plan.json` (each component's `form_template_mapping`, each field's `placement`, `intake`, `url_parameters`, and `build.template_id` once build-template has built it), org-catalog's `catalog.json` (the map saved on a reused component, the org's other mapped forms, the Form Submission fields that exist) and `flow-tool-kit.json` (the edition and the audiences), plus build-template's report with `--report`. Out comes the work list: the Conversion Rules values, per object the packaged flow to keep or a new object rule, the form maps, the few Transform rows, the fields that stay on the submission, the handoffs and the questions only the person can settle. Your own answers the plan has no key for (calculated values, record types, Campaign Members, free-edition targets, prefill flows) go in `_forms/<slug>/mapping-spec.json`; run it again after each. Formats: [references/work-list.md](references/work-list.md). A catalog over 24 hours old stops it: run org-catalog again.
2. **The edition**, when step 1 had no plan. ftk-start asks once per org whether it runs the paid or the free Flow Tool Kit edition and saves it in `flow-tool-kit.json` (`_shared/standards/project-config.md`). Use that answer. If it is missing, ask the same single question and save the answer there. The edition decides the mapping approach (Step 1, in references/mechanism-and-contract.md).
3. **A Form Template**, when no plan exists (built by hand, or before this plugin). Ask: "Do you have a Form Template record to base this on?" If yes, run the discovery in [form-template-discovery.md](references/form-template-discovery.md): the template and its settings, its pages and sections, the forms behind each section, the prefill template, the source configuration and the describes of Form Submission and every target object. Output: a draft field map with confidence tiers, a build list of what can be wired now, and a short list for the user to confirm. If no, go to the spec questions (Step 7, in references/build-deploy-and-prefill.md) and collect source, target and field answers before building.
4. **A migrated form.** When form-migrate converted the form from another platform, read its output (the IR and the workbook of what the old form did). Read `source.coverage.connector` before assuming anything: `parsed` means the old connector's mappings are evidence; `none_exist` or `not_captured` means there are none. Reconcile the old form's behavior with what the new template does; every disagreement is a finding. A source that matched "most recent" on multiple matches needs a decision, because this pipeline stops instead (see Matching in Step 4).
5. **A whole account moving off FormAssembly.** When formassembly-capture wrote a flow plan, build from it, not form by form: each conversion rule once, each form's Conversion Rules column as listed, one decision for any object planned two ways, order conflicts resolved with a side-record subflow or an update in the later rule (never by reordering the controller), and one prefill flow per entry record.
6. **What the org already has.** List the active conversion flows, overrides and clones before building anything new: `sf data query -q "SELECT ApiName, Label, IsActive, NamespacePrefix FROM FlowDefinitionView WHERE ApiName LIKE '%Convert%'" -o <org-alias>`. Rows with no namespace prefix are the org's own clones and steps. Reuse an existing clone before making a second one, and check each packaged flow in Setup for an active override. In chat, run the same query through the Salesforce connector.

## The preference, the mechanism and the family contract

Before choosing how to build a mapping, and while building a new conversion flow, read [references/mechanism-and-contract.md](references/mechanism-and-contract.md) (Step 1: The mapping preference (paid and free), Step 2: Choose the mechanism, Step 3: The family contract for a new conversion flow).

## The hard parts, deploying, the spec, prefill and naming

While building, before deploying, before writing the spec, for any prefill flow and when naming, read [references/build-deploy-and-prefill.md](references/build-deploy-and-prefill.md) (Step 4: The hard parts, Step 5: Run-as, debugging and recovery, Step 6: Deploy, wire, activate and check, Step 7: The spec, before building, Step 8: Prefill flows, Naming and descriptions).

