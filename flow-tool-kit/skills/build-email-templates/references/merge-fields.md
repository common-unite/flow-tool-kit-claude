# Merge fields

Write merges in `plan.json` as `{{Field__c}}`; `emailbuild.py` writes the Lightning form into the template. Verified by rendering built templates in an org with the package's own render step.

| Written in the plan | In the template | What it shows |
|---|---|---|
| `{{FlowToolKit__Contact1_First_Name__c}}` | `{{{FlowToolKit__Form_Submission__c.FlowToolKit__Contact1_First_Name__c}}}` | A packaged Form Submission field: what the respondent typed |
| `{{Project_Title__c}}` | `{{{FlowToolKit__Form_Submission__c.Project_Title__c}}}` | The org's own Form Submission field |
| `{{Name}}` | `{{{FlowToolKit__Form_Submission__c.Name}}}` | The submission number, such as 000123 |
| `{{Recipient.FirstName}}` | `{{{Recipient.FirstName}}}` | The Contact or Lead the email renders against (the converted record, not the typed answer) |
| `{{FlowToolKit__Internal_Resume_Link__c}}` | `{{{FlowToolKit__Form_Submission__c.FlowToolKit__Internal_Resume_Link__c}}}` | Save Progress Resume Link: the single-use link back to a saved form |

## Rules

- **Direct Form Submission fields only.** A Lightning template cannot follow a relationship: `{{Form_Template__r.Name}}` or `{{Contact_1__r.Email}}` is refused when the template is saved ("The merge field ... doesn't look right"). The build stops on it before anything reaches the org. Write the form's name into the copy, or copy the value onto a Form Submission field first.
- **Every merged field must exist in the org.** `emailbuild.py` checks each one against the org's Form Submission fields (from org-catalog's catalog or the org context) and stops on a name it does not find.
- **The resume link** is only for the Save Progress, stages resume and start emails. In a confirmation it is blank (the link ends on submit). It arrived in Flow Tool Kit 5.3; on an older version the build stops and says to upgrade. Never build a link by hand with `pv9` or `recordId`.
- **`Recipient.*`** works in the confirmation (Contact 1 or Lead 1), the Save Progress email (Contact 1) and the stages email (a portal Contact, Contact 1 or the owner). Never in a staff notification: it renders with no recipient.
- **Dates, numbers and currency** render in the format of the user the email is rendered as: a Submission Date shows as `11/17/2026, 9:16 PM` for a US-English user. Do not add a currency symbol before a currency merge; check the test email for the exact format and write the words around it.
- **Blank answers** render as nothing. Write sentences that still read well when an optional answer is empty, or merge only required answers.
- **No field names in the words a respondent reads**, no em-dashes, and no `[placeholder]` left when building: the build stops on all three.

## Sample values for the preview

`emails.sample_merge` maps each merge to a realistic invented value for the preview and the review canvas (`"FlowToolKit__Contact1_First_Name__c": "Jordan"`). A merge with no sample shows as its label in brackets, which tells the reviewer a value goes there.
