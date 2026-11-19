# Checking, traps and common mistakes

Moved from this skill's SKILL.md, read on demand: Check, write, verify, Traps, Common mistakes.

## Check, write, verify

1. **Check.** `python3 scripts/component.py check <component>.json --catalog <catalog.json> [--plan plan.json]` (give it a folder of custom metadata record files instead to check a metadata component). The same JSON is checked whatever the shape. It reports every field the org does not have (the package skips an unknown field silently, so the question just vanishes), keys and values outside their sets, missing section flags, rules that are referenced but missing or unlabelled, a Form Template Mapping that cannot save, text over 255 characters, and descriptions that miss the standard. Fix every error; read every warning.
2. **New fields first, then the component.** A component that names a field before it exists renders without that question.
3. **Write, in the chosen shape.** Record: the package's import (chat or Claude Code), then read the component back by `QualifiedApiName__c` to confirm its Id. Metadata: `scripts/component.py cmt`, `sf project deploy start`, then **Reset Form Cache** in the Form Builder's footer: configs are served from a platform cache, and a stale form looks exactly like a failed deploy. A metadata component build-template handed over (`action: build metadata`) is built under the name in the handoff, then build-template is run again to bind it. JSON: hand the checked JSON to build-template for the section, or give it to the person for the flow's or page's form component.
4. **Extend makes a new version, in the chosen shape; updating the shared component is its own question.** Extend: take the component's current JSON (the Export action on the record, or the catalog's copy if current), then `python3 scripts/component.py extend <original.json> --name <New_Name> --add <added-fields.json> --out <new.json>`. It copies the design under the new name, renames every section, field and rule after it, and adds the fields; import the result as a new record component (or, in the metadata shape, write it with `scripts/component.py cmt` and deploy it) and point only this section at it. The original keeps serving every template that uses it. Update the shared component: only after its own question, listing every template and component it reaches, was answered yes; then import the changed JSON under the **same** name (same Id, every template changes) ([references/record-path.md](record-path.md)).
5. **Bind.** build-template places the component in its page sections ([references/template-binding.md](template-binding.md)): a record component as `<Name>_v0`, a metadata component by its name. A header or footer component is built on **Form Template**, never on Form Submission.
6. **Walk it.** Open the template's **Preview Form** and walk every page: each field, each option word for word, each required marker, every rule both ways. For a public form, also open it as a guest: record components need a guest sharing rule giving Read on Form Component where the record type is Record Component, or the guest sees nothing. A form is not built until this walk passes. [references/fidelity-contract.md](fidelity-contract.md) says what a reviewed design can and cannot promise.

## Traps

| Trap | What to do |
|---|---|
| A field the org does not have | The package skips it with a console warning only. Run the check; deploy fields first |
| Scale fields (`Agreement_Question_N__c`, `Rating_N__c`, `Satisfaction`, `Frequency`, `Scale`) | They draw their fixed packaged scale and ignore option overrides. Only for questions that ask for that scale |
| Custom metadata `config__c` with `sections__r` or `fields__r` | Fatal: the form resolves to nothing. Metadata config is one flat record; `scripts/component.py cmt` writes it right |
| A redeploy shows the old form | Platform cache. Reset Form Cache in the Form Builder footer |
| Text over 255 characters in help text, labels or placeholders | Deploys, then breaks the first save in Form Builder. Use the `...Long__c` keys |
| `min__c`, `max__c`, `step__c` as numbers | They are text; quote them |
| A compound Address field | Its State and Country accept codes only, and turning on State and Country picklists is permanent (a check-only deploy cannot turn it on). Default to the packaged text address fields behind one Address section |
| A photo in a rich text field on a public form | A guest sees it only with read on both the record and the field; a refusal is a small placeholder image, not an error |
| A form in another language | Add the language in Translation Workbench and mark it Active; field and picklist translations show only after activation, custom labels at once |
| A component bound to the wrong field | Form Builder's **Change Field** points it at another field and keeps every setting still valid for the new type; rules and merges that name the old field are not rewritten, so fix those too |
| Searching metadata forms by the `fieldName__c` column | Form Builder stores a durable field Id pair there; the API name is in `config__c` |
| New fields with no field access | They deploy without field-level security, and the form and Form Builder see fields only through it. Grant read and edit in a permission set (and the guest's, for a public form) |
| A merge token naming a field that does not exist | Breaks the form. Merge only real fields, such as the template's `{{Name}}` and `{{FlowToolKit__Form_Template_Subtitle__c}}` in a header |

## Common mistakes

| Mistake | Instead |
|---|---|
| Reusing or copying a catalog component without asking | Ask reuse, extend or new, naming it and where it is used |
| Extending a component by importing it again under its own name | Extend is a new version under a new name; changing the original is "update the shared component", its own question |
| A component named for one form | Name it for its purpose |
| A header baked into the component | Header on the page section |
| Every question on Form Submission in a paid org | A component on the record's own object with Form Template Mapping |
| Creating `Form_Component__c` with a plain record insert | The package's import, which writes the sections and fields |
| Custom metadata attempted in chat | Say it needs Claude Code; ask whether to build a record component now or wait for Claude Code |
| Choosing metadata, record or JSON for the person, or building every component one way | Recommend a shape with the reason and ask; build the shape the person chose |
| JSON for a block the plan already places in several sections, Repeaters or forms | Every place must then be edited by hand; recommend one record component, built now and referenced by each, unless the person needs the questions fixed in each place |
| A shared record or metadata component for a section only one form asks | JSON on the section is the default; a shared shape only when reuse is known at design time |
| Saying a Form Template is reused | A template is one whole form; reuse is of components |
| A new Form Submission field for a question a packaged field or slot already holds | Walk the staging-field ladder first |
| `radiobuttons` for long or many options | `surveybuttons` |
| Rules labelled with API names, sections left untitled | A few plain words each |
| Calling it built after the deploy | After the Preview Form walk |
