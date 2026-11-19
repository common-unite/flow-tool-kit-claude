# What it builds, the brand and the handoffs

Moved from this skill's SKILL.md, read on demand: What it builds, The header, the logo and the brand, Setup and handoffs, Optional: offer consolidate-sections once, Know the org you are building in.

## What it builds

The full plan-to-record table is in [references/plan-keys.md](plan-keys.md). The parts that need judgment:

- **Components, as the reuse question was answered, in the shape the person chose** (org-catalog asked both; form-design recorded `decision`, `shape` and `shape_asked`). Reuse is about components, never about templates. The shapes:
  - **JSON** (`shape: json`, only for `form-only`): the questions as component JSON on the section, fixed to this form; a change to any shared component never reaches them.
  - **Record** (`shape: record`): a Form Component record created (or updated in place, same name) through the package's import before the template is touched, and the section points at `<Name>_v0`. A `form-only` component in this shape is a one-off record component named like the section's own form, carrying its field rules.
  - **Metadata** (`shape: metadata`): the build does not deploy metadata (in records mode it builds a record component instead; see Build modes). The report's first handoff names the component for **build-form-component**, which writes and deploys it (Claude Code), then Reset Form Cache and rebuild; the section points at the plain name. A real build stops, with nothing written, while the org does not have it as a metadata component. Its field rules are deployed with it and checked in the Preview walk, not counted here.
  - A shape the plan sets without an answered `shape_asked`, or JSON on anything but `form-only`, stops the build: the shape is recommended and asked, never decided silently. A plan from before shapes builds as it always did (`form-only` as JSON, `shared-new`, `extend` and `shared-record` as record components) and the report says so.
- **The decisions:**
  - `form-only`: questions only this form asks, in the shape above (JSON unless the plan says record or metadata).
  - `reuse`: the section points at the named component. The build stops if the org does not have it.
  - `extend`: a **new version** of the named component: the component copied as it is, plus the `add_fields`, under its own name, as a record component (or handed to build-form-component under `new_name` when the shape is metadata). The original is never changed, so every template already using it keeps it. A field rule inside an extended or reused component cannot be built from the plan: put the rule on the section.
  - `update`: the named shared component is changed in place, and with it every template and component that uses it. Never the default: the plan must record its own question, answered update, naming everything it reaches (build-form-component's keys: `asked`, `usage.status` complete, `usage.consumers`, `shared_change_reason`, `changes`), or the build stops. A packaged component can never be updated. build-template only points the section at the component; **build-form-component** makes the change, first (the report's first handoff), and the build warns while the component still lacks the planned fields.
  - `shared-new` and `shared-record`: one component several templates share. As a record component it is created (or updated in place) before the template is touched; `shared-new` as a metadata component is handed to build-form-component. A failed create stops the build with the package's own message and nothing changed.
  - `flow-section` and `custom-lwc`: the section names the flow or Lightning web component; **build-flow-section** and **build-custom-lwc** build them after the template (see Handoffs).
- **Paid and free editions** (`_shared/standards/mapping-preference.md`). Paid: a form on another object (Contact, Account, your own) carries its **Form Template Mapping**, each of its fields mapped to the Form Submission field it stands for, and the build writes that map onto the form. A paid-edition form on another object without a mapping stops the build, because nothing it collects would reach the submission. Free: forms stay on Form Submission (free forms show only on Form Submission, Account, Contact, Lead, Case, Campaign and Campaign Member), and new-mapping-flow maps each answer.
- **Form-type settings** come from the plan's form-type row (`_shared/standards/form-type-rules.md`). A long form gets stages mode, Save Progress and the review screen, and the answers PDF when it sends a confirmation email. **Stages mode never turns on the Save Progress email**: a stages template never sends it; its "Email me a resume link" button sends the resume email instead.
- **Rules are built exactly.** Every page, section and field rule needs a label (its purpose in plain words, at most 40 characters), a field, an operator the package evaluates and a value. After the build, the rules in the org are counted by level and must equal the plan's, or the build fails.
- **The header, the logo and the brand**: next section.
- **Choice options**: every Picklist and MultiPicklist shows exactly the plan's options, in its order, with its labels (the field's option subset and option settings), never every value the field holds. The build checks them against the field's values for the record type the form uses and names any the org lacks, because the package drops such a value without a word; the round trip compares the options the form draws with the plan's.
- **Addresses**: each address is built as its own address section (flagged `isAddressSection` in a section's JSON), split out of a section of other fields in its place, with its Address row and all five parts (Street, City, State, PostalCode, Country), and its planned label as the section's header and on the row. The package draws an address only that way: a part left out draws one blank box, and a row among other fields a plain field. The row's Required is what the form enforces on every part, so the row must be required exactly when a part is. A plan address without its row or a part, or whose row and parts disagree on required, stops the build, and the round trip fails on one in the org (`_shared/lib/addressparts.py`).
- **Long wording**: a label, help text or placeholder past 255 characters goes whole into the package's long field (`customLabelLong__c`, `helpTextLong__c`, `placeholderLong__c`), never cut.
- **Prefill** (`prefill.flow`, `sections[].section_tag`): the template's Prefill Flow API Name, and each tagged section's Section Tag, so the flow's Prefill From Mapped Record step in Related Records mode has a section to fill. A tag must be a Data Conversion Tag(s) value in the org (after-the-build.md).
- **Conditional payment** (`payment`): Payment Required, and Payment Conditions as a rule ("require payment when..."). **URL parameters** (`url_parameters`): the template's URL Parameter Mapping. Both are in [references/plan-keys.md](plan-keys.md); what guests need for them is in the setup report.

## The header, the logo and the brand

Details and reasons: [references/headers-and-brand.md](headers-and-brand.md).

- **The header is Flow Tool Kit's own Banner header.** A form with two or more pages uses the packaged Header (Banner) (Overlay). A one-page form uses a Compact Banner, and a plan that names Split uses a Split one: the package ships only Overlay, so the build creates each of those once per org as a record component on Form Template, with the packaged Banner settings and only the layout changed, and reuses it after that. Nothing in a header is specific to one form.
- **Each template supplies its own words and images**: the template name is the title, then the subtitle, the Header Tags (pills) and the banner image (the plan's banner asset, or the package's banner photo when the plan has none).
- **Logo**: the Banner reads the template's **Logo** field, which is the template's **Logo Override** when set and otherwise the org's **Default Logo** (Global Styles tab). With a brand kit saved for the org, the build sets the Default Logo when it is blank; otherwise, or when the org already has a different default, it sets this template's Logo Override. On Flow Tool Kit 5.3, which has no Logo fields, the logo goes on the Banner's own logo image setting in a header named after the logo.
- **Colors**: the banner fills with the brand color from the styles below. An org that keeps a color per template in its own Form Template text field `Brand_Color__c` gets it merged into the Compact and Split headers' Background Color, and the build fills it from the plan's brand color.
- **Brand styles go add-only into the org's Form Style defaults**: blank, the brand value is added; the same, nothing; different, the org keeps its value and the brand goes on this template's Style Overrides. Only brand values (colors, fonts, corner radius) go org-wide, and only when the project config says the brand kit is the org's own; layout values and every value of a form without a brand kit stay on the template. Writing the setting through the API works in a tested subscriber org; if an org refuses, the build writes `global-styles-import.json` with the org's current values plus the brand, and the person pastes it into Form Builder, Global Styles, Import.
- The template always keeps the packaged default theme, so an admin can still change everything in the Style Editor. Never create a Form Theme for a brand.

## Setup and handoffs

The report's `setup` lists what this template still needs in the org, with the exact steps ([references/after-the-build.md](after-the-build.md)):

- **Answers PDF**: with Attach PDF to Confirmation Email on, the Form Submission Convert trigger needs a running user, or the email goes without the PDF. `python3 scripts/runninguser.py --user <admin username> --out <project-dir> --org <org-alias>` writes the Platform Event Subscriber Config; deploy it, then Suspend and Resume the trigger in Setup.
- **Save Progress and resume emails**: a web form address on the template or the org, and a verified Default Workflow User.
- **Guests**: a guest sharing rule on Form Component for every record component the template uses (headers included), Read on Payment Conditions and every field a payment rule reads, Edit on every field a URL parameter fills. **flow-access-fix** sets these up.

Then hand over, in this order:

1. **build-form-component** for each metadata component the plan names and the org does not have yet (`action: build metadata`), and for an approved `update` to a shared component, then a rebuild, so the section shows it.
2. **build-flow-section** and **build-custom-lwc** for each section the report's `handoffs` names.
3. **build-email-templates** for the confirmation, Save Progress and resume emails the plan designs (the template already names them).
4. **new-mapping-flow** for the conversion to records.

## Optional: offer consolidate-sections once

A section of questions only one form asks (`form-only`) belongs to that form, as JSON on the section. When an org has several templates, some of those sections may turn out to ask the same questions. Merging them into one shared component is **optional** and is the **consolidate-sections** skill's job, not this one's: not every consultant or organization will use it. After a build, when the org has two or more templates, offer it **once**, in one line, and move on whatever the answer: *"Some sections may repeat across your templates. Would you like me to check, and merge any that do into one shared component? It is optional; nothing changes without your yes."* Never run it as a step of the build, and never offer it again in the same session after a no.

On a yes, run org-catalog again (so its catalog knows this build), then hand over to consolidate-sections: in Claude Code, `/flow-tool-kit:consolidate-sections`; in chat, ask for it by name ("check which sections repeat across our templates"). Pass this template's `plan.json` along. It works on the whole org, shows each group and every difference before anything changes, and records any merged section in this template's `plan.json` (`build --plan`) so the next rebuild keeps the shared component.

## Know the org you are building in

- In an org that installed Flow Tool Kit, every package object and field carries `FlowToolKit__` (`FlowToolKit__Form_Submission__c`, `FlowToolKit__Contact1_Email__c`); your own fields keep their names (`Grade__c`). The plan writes packaged fields with the prefix and its objects as `Form_Submission__c`; the build checks every object and field against the org first.
- A field on Form Submission named like a packaged one without the prefix (your `Submitted_By__c` beside `FlowToolKit__Submitted_By__c`) is left out of what the conversion hands a flow. Never create one; org-catalog's `name-check` catches it.
- What the package does that the build works around (the default page and section, section Ids that change on every save, headers hidden by default, a header built on the wrong object): [references/package-behavior.md](package-behavior.md).
- To put a finished form in another org, run build-template there with the same `plan.json`: it finds no template with the saved Id in that org, creates one, and keeps every generated name.
