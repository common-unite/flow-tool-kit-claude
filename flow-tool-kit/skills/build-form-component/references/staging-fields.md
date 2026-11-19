# Answers that land on Form Submission: reuse before you create

Read this when a component is built on Form Submission: every component on the free edition, and on the paid edition the answers that belong on the submission (long answers, rich text, survey responses, fields that drive the form). On the paid edition a block about a Contact, Account or other record is built on that object instead ([_shared/standards/mapping-preference.md](../_shared/standards/mapping-preference.md)).

## Form Submission is a landing pad, not a schema per form

A Form Submission field holds an answer until the conversion copies it to its real home. The question's wording lives on the component (`customLabel__c`, `helpText__c`), never in a new field. A second `Gender__c` beside the packaged `Contact1_Gender__c`, or a `Volunteer_Hours__c` when `Number_Question_1__c` is free, is the most common mistake in a build: it bloats the object, splits reporting and forces a second conversion mapping.

**Before creating any field, walk this ladder and stop at the first step that fits:**

1. **A packaged field for this exact concept.** Reuse it with its companion fields, adding picklist values only if they are really missing. This is almost always the case for people and organizations: name, email and phone (`Contact1_...`, `Contact2_...`); gender (`Contact1_Gender__c` with `Contact1_Gender_Other__c`); race and ethnicity (`Contact1_Race_Ethnicity_Multiselect__c`, a multi-select because people are multiracial, with `Contact1_Hispanic__c` and `Contact1_Other_Race__c`); pronouns, preferred language, birthdate, age range (`Age_Range__c`), income (`Income_Range__c`, `Household_Income__c`), occupation, organization (`Company__c`, `Company_Phone__c`, `Company_Email__c`, `Website__c`), mailing address (`Mailing_Street__c` and the rest), email opt-out, newsletter opt-in, consent (`Agree_Consent__c`, `Liability_Waiver_Agreement__c`), signature (`Electronic_Signature__c`, `Electronic_Signature_Print__c`, `Electronic_Signature_Date__c`), a person's photo (`Contact1_Profile_Photo__c`).
2. **A generic slot of the right type.** Put the real wording on the component.
   - Short text and "Other, please say" companions: `Text_Question_1__c` to `Text_Question_10__c`.
   - Paragraphs: `Long_Text_Question_1__c` to `_5__c`.
   - Numbers: `Number_Question_1__c` to `_5__c`, then `Quantity__c` and `Percent_1__c` to `_3__c`.
   - Yes or No: `Yes_No_Question_1__c` to `_10__c` (a picklist that can tell an explicit No from no answer); a plain checkbox: `Boolean_Question_1__c` to `_5__c`.
   - Dates: `Date_Question_1__c` to `_3__c`. Web addresses: `Url_Question_1__c`, `_2__c`.
   - A question that asks for a standard scale: the matching scale family, `Agreement_Question_N__c`, `Satisfaction_Question_N__c`, `Frequency_Question_N__c`, `Importance_Question_N__c`, `Likelihood_Question_N__c`, `Confidence_Question_N__c`, `Ease_Question_N__c`, `Usefulness_Question_N__c`, `Familiarity_Question_N__c`, `Expectations_Question_N__c`, `Change_Question_N__c`, `Scale_Question_N__c`, `Rating_N__c`. Totals go in `Total_Score_1__c` to `_3__c`.
3. **Start generic even for a question that looks unique.** Another form will likely ask something like it. Go specific (a named field) only with a stated reason: a value tracked on its own downstream, such as an opt-in that becomes Campaign membership.
4. **The existing field has a different shape from the question** (a single-select question against the packaged multi-select race field; a checkbox question that needs an explicit No). That is a point to confirm with the person, not a reason to fork: state the preferred design and ask before diverging.
5. **The real gaps get a new field:**
   - a single-select question with **its own options** (household size bands, program track, shirt size): a new picklist field with exactly those values. The scale families cannot take arbitrary options (below);
   - a multi-select question: there is no generic multi-select slot, so a form's own multi-selects (programs of interest, days available) get their own fields.

New fields follow [_shared/standards/naming.md](../_shared/standards/naming.md) (mirror the target field's name; shape it like its target) and carry a description from the moment they are created ([_shared/standards/documentation.md](../_shared/standards/documentation.md), section 4: a description always; inline help only when a respondent needs it, in their words).

## How one field serves many forms

The per-form view is set on the component, not the field. `customLabel__c` and `helpText__c` give this form's wording; `picklistOptionOverrides__c` shows only this form's subset of the field's values; `picklistOptionSettings__c` relabels and explains stored values. The field's value set is the union across every form that uses it, and each form shows its own slice. That is why `Text_Question_1__c` can be one question here and another there.

## The scale fields do not work that way

`Agreement_Question_N__c`, `Rating_N__c` and every other scale family draw their own packaged scale (Strongly Disagree to Strongly Agree, and so on) and ignore option overrides and option labels. Putting your own buckets on one renders the packaged scale, not your options, even though the configuration looks right. Use a scale field only for a question that asks for that scale; for anything else create a picklist field with the question's values.

## Values that differ are not a reason to fork

`Contact1_Gender__c` ships a set of values; a form that needs another wording reuses the field and either adds the missing value (the packaged picklists accept values you add) or relabels a stored value with `picklistOptionSettings__c`. Only stored values matter to reports and conversion. Reuse, then relabel; never fork.

## When you create picklist fields with a twin

When a new picklist lives on both the Form Submission and its conversion target (a Contact field and its staging twin), consider a Global Value Set so the two never drift and a yearly change is one edit. Global value sets are always restricted, which suits a twin pair. An existing inline picklist cannot be switched to a Global Value Set: either extend its values or create a differently named field on the set, and put that choice to the person, since it changes the data model.

A field on Form Submission whose API name matches a packaged field without the prefix (your `Submitted_By__c` beside `FlowToolKit__Submitted_By__c`) is left out of the record the conversion hands its flow. Never name a new field after a packaged one. Before creating any field, run org-catalog's `name-check` (it answers free, exists or twin).

## Confirm the inventory in the org

The packaged inventory grows with each release. Read the org catalog's Form Submission fields, or ask the org:

```
sf data query -o <org-alias> -q "SELECT QualifiedApiName, DataType FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'FlowToolKit__Form_Submission__c'"
```

Prefer a FieldDefinition query or a metadata listing over `sf sobject describe`, which leaves out fields the running user cannot read and so makes an existing field look missing.
