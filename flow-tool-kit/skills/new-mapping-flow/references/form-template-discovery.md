# Drafting a field map from a built Form Template

Use when the Form Template is already built in the org but nobody has written a field-mapping document. The template, its pages and sections, the forms behind them and the object describes hold enough to draft the map as educated guesses, wire the core now, and give the user a short confirm list instead of a blank questionnaire.

Everything here is read-only: queries and describes through the `sf` CLI in Claude Code, or the Salesforce connector in chat. Prefer local metadata files when the project already has them; template, page and section records are data, so read those from the org.

**Check field existence with metadata, not describe.** `sf sobject describe` leaves out every field the running user cannot read, so a field you lack access to looks like a field that does not exist. Confirm with `sf org list metadata -m CustomField -o <org-alias>` or a Tooling API query on `FieldDefinition` before concluding a field is missing.

## Phase A: Pull the whole picture

Describe each object first, then query with the real field list: orgs add their own fields beside the packaged ones (in an installed org packaged names carry `FlowToolKit__`).

1. **The Form Template.** Capture Conversion Type, Conversion Rules (the enabled rules and their sub-rules are mapping requirements), every Conversion Map Flow and Flow API Name pair (which flows run today), the Account, Contact and Lead matching rules and Update Most Confident settings, the record type fields, Nullable Fields, the prefill template, the source, the prefill flow, URL Parameter Mapping and the email settings.
2. **Pages and sections.** For each section: label and order, the form behind it, Section Tag, Conversion Rule and Conversion Map Flow (which decide how repeater rows convert), Add to Account, Add to Campaign, section matching rules and record type overrides, Data Conversion Tags.
3. **The forms behind the sections.** For each form, its sections, fields and conditional logic (when visibility decides whether a field ever holds data). Per field: label, input type, required, and its target.
   - A form on **Form Submission** targets staging fields: that set is the source side of a free-edition map.
   - A form on **another object** (an Account form, an Opportunity form, a form on your own object) carries a **Form Template Mapping**: each of its fields mapped to a Form Submission field, applied to all records of the object or to one Form Submission lookup. On a paid org those rows are already handled by Apply Submission Field Maps; list them as "mapped by the form", not as Transform rows.
4. **The prefill template.** List its populated fields. Fixed seeds (a Campaign, a source, a default picklist value) become the tail of a fallback chain, not hard-coded values in the flow.
5. **Source and default configuration.** The Form Template Source records (which source objects feed this template and which submission lookup they stamp) and the Form Template Conversion Mapping Default records (which flow each rule runs by default). Flag a Conversion Map Flow that points at an Upsert engine instead of a Process step: the engine receives empty inputs when dispatched.
6. **Form Submission.** Every staging field: API name, label, type, length, picklist values, packaged or added by the org. This is the left column of every map.
7. **Each target object.** For every target the rules, sections and requirements imply: required createable fields with no default, types and lengths, picklist values, record types.

## Phase B: Educated guesses, in order of precedence

1. **Packaged mappings win.** The packaged staging fields already have known targets: Contact 1 and Contact 2 names, email, phones, title, birthdate and salutation to the Contact; Company to Account Name; Company Phone and Website to the Account; the shared Street, City, State, Postal Code and Country to the address blocks gated by the `👉 Set ... Address` sub-rules; Campaign to the Campaign Member.
2. **Form Template Mapping rows are done** (paid edition): they are filled by the action; the only question is whether the form is applied to the right lookup.
3. **Section meaning scopes the target.** "Organization" sections point at Account, "Contact" sections at Contact; a repeater's Conversion Rule decides its rows. A parent-organization section implies a second Account rule even if none exists yet.
4. **Name and type matching** for the org's own staging fields: an exact or near name with a compatible type is strong; picklist to picklist needs the value sets compared; text to shorter text flags truncation; a checkbox against a Yes/No picklist needs a formula.
5. **Prefill seeds become fallbacks**: the tail of a `BLANKVALUE(submission, prefill)` chain.
6. **Required fields close the loop.** Every required createable field on the target has a mapped source, a fallback chain, or a question. A map that cannot insert is a bug, not a draft.
7. **Conditional logic.** A field hidden by conditional logic can legitimately arrive blank: its mapping must be null-safe, never a required-field source.

Give each row a confidence tier:
- **High** (packaged mapping, a Form Template Mapping row, or an exact name and type match): wire it now.
- **Medium** (similar name, compatible type, or inferred from the section): wire it and put it on the confirm list.
- **Low** (unclear target, type friction, several candidates): a question only; do not wire it.

## Phase C: Outputs, as files in the project

1. **A draft field map**, one table per target object:

   | Source (Form Submission) | Target | How (form map, Transform row, formula, conditional) | When (create only, always) | Confidence | Reason or question |

2. **A core build list**: when the map is not confirmed, build the step with only the identity (`Id` from the lookup), `Latest_Form_Submission__c`, the required fields and fallbacks, and the High rows. Medium and Low rows land later in the Transform, or on a paid org as form maps: one place to edit, no rework.
3. **A confirm list**: the Medium rows ("we assumed X; confirm") and the Low questions ("which field feeds Y"). A short review replaces a mapping workshop. An optional claude.ai artifact can show the map for review; the files stay the record.

These feed the spec (build-deploy-and-prefill.md, Step 7): items 1 to 4 come from Phases A and B, items 5 to 7 from the mechanism choice.
