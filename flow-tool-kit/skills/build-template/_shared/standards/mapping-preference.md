# Mapping preference: how a form's answers reach their records

Every skill that places a field, builds a form component or builds a conversion flow follows this page: form-migrate (the field plan), form-design (placement), build-form-component and build-template (the components and their maps), new-mapping-flow (the flows), org-catalog (which existing forms to offer).

## The edition decides it

ftk-start asks once per org whether it runs the **paid** or the **free** Flow Tool Kit edition and saves the answer in `flow-tool-kit.json` (`orgs.<org id>.edition`, see [project-config.md](project-config.md)). Read it there; if it is missing, ask the same one question and save the answer. Sandboxes, scratch orgs and Developer Edition orgs always run without the free limits, so the answer that matters is the edition of the org the forms will run in for real.

## Paid edition (the default)

- **Build on the record's own object.** A question about a Contact, an Account, an Opportunity or your own object goes on a form built on that object (reuse one org-catalog found first), placed in the Form Template's page section.
- **Map each field to a Form Submission field** on the Form Builder's **Form Template Mapping** tab. Choose **Apply these mappings to**: all records of that object, or one Form Submission lookup when a submission creates two records of the same object (two Contacts, two Accounts). The map is saved on the form, so every template that uses the form gets it; prefill and live updates then flow through the submission.
- **Keep the packaged conversion flow** for the object. It runs **Form Submission | Apply Submission Field Maps** after its Transform, which fills every field the Transform left empty from those maps. A new field is then a Form Builder change, never a flow change.
- **Hand-build Transform rows only for what a map cannot express:**
  - calculated or combined values (a name built from two answers, a date from a formula);
  - Campaign Members (the maps do not apply to Campaign Member conversion yet);
  - record types (Form Submission's record type fields are never offered as map targets).
- A page section cannot override a form's map; use a second form, or a second lookup, when two templates need different targets.

## Free edition

- Forms and form components work only on Account, Contact, Lead, Case, Campaign, Campaign Member and the Flow Tool Kit objects. A form on Opportunity or on your own object shows "Object Is Not Available Within the Free Version". Site design blocks that show a record (record cards, repeaters, record pages) are narrower on the free edition: Account, Contact, Case, Lead and Form Template only; on any other object they show a notice instead of their content.
- So answers land on **Form Submission fields** (the packaged blocks first), and the conversion flow's **Transform** maps each one to its target.
- A mapped form on Account, Contact, Lead or Case may still work on the free edition, since those objects are allowed. Confirm it in that org before relying on it.

## Both editions

- Every conversion flow you build or clone keeps **Apply Submission Field Maps** right after the Transform and before **Remove Null Values**, with its Record output assigned back to the record variable.
- Pass the template's **Nullable Fields** to Remove Null Values, so only the fields it names may be cleared by a blank answer. By default a blank answer never overwrites a value.
- The source record links to its submission through the **Latest Form Submission** lookup, so answers kept on the submission stay one hop away for reports and record pages.

## Where each answer lands

| The field | Goes on | Why |
|---|---|---|
| Already exists on the target object (Contact email, Account name) | That object's form, mapped (paid), or the packaged Form Submission field the conversion reads (free) | Someone already reports on or works from it |
| Drives the form, a long answer, rich text, a survey response, rarely reported | Form Submission | Read once in context; on a core object it becomes a field nobody maintains |

When a field is new, take in order: a field on the target object (paid), a packaged Form Submission field (the Contact 1, Contact 2, address, organization, demographic, consent and signature blocks), a packaged generic slot, and only then a new field, proposed as a question.
