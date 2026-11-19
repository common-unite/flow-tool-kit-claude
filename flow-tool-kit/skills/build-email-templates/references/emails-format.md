# Input and output files

## Input: plan.json

The build reads form-design's `plan.json` as it is. It uses these keys and ignores the rest, so a form with no design can use a small file holding only them (`_forms/<slug>/emails.json`).

```json
{
 "slug": "brief-volunteer-application",
 "template": {"Name": "Volunteer Application", "Stages_Mode__c": false, "Allow_Save_Progress__c": true,
              "Recipients_Confirmation_Email__c": "Email", "Attach_PDF_Confirmation__c": false},
 "style": {"brand": "#2f6b3a", "heading_color": "#1d3b24", "background": "#f7f5ef", "font": "Lato"},
 "assets": {"logo": "Riverside_Logo", "banner": "Riverside_Banner"},
 "emails": {
  "letterhead": {"org": "Riverside Community Garden", "tagline": "Growing food and neighbors together.",
                 "address": "100 Garden Way, Riverside", "email": "hello@example.org",
                 "site": "https://www.example.org", "site_label": "example.org", "logo_alt": "Riverside Community Garden logo"},
  "sample_merge": {"FlowToolKit__Contact1_First_Name__c": "Jordan"},
  "confirmation": {"name": "Volunteer_Application_Confirmation",
                   "subject": "We received your volunteer application, {{FlowToolKit__Contact1_First_Name__c}}",
                   "heading": "Thank you for applying",
                   "body": ["...", "...", "..."],
                   "button": {"label": "See the volunteer calendar", "url": "https://www.example.org/volunteer"}},
  "saved": {"name": "Riverside_Resume_Link", "subject": "...", "heading": "...", "body": ["..."],
            "button": {"label": "Continue your form", "url": "{{FlowToolKit__Internal_Resume_Link__c}}"}},
  "staff": {"name": "Volunteer_Application_Staff_Notification", "to": ["coordinator@example.org"],
            "subject": "...", "heading": "...", "body": ["..."]}
 }
}
```

| Key | Rule |
|---|---|
| `template` | The Form Template's `Name` (how the build finds the record) and its settings that decide which emails apply: `Stages_Mode__c`, `Allow_Save_Progress__c`. Optional `Id` when known. `Recipients_Confirmation_Email__c` and `Attach_PDF_Confirmation__c` are carried into the settings |
| `emails.confirmation` | Every form that collects an email. Plain paragraphs or HTML strings in `body` |
| `emails.saved` | An ordinary form with Save Progress: the Save Progress email. Never with stages mode |
| `emails.resume` | A stages-mode form: the Email me a resume link email |
| `emails.start` | Optional: the start-form invitation an admin's flow sends |
| `emails.staff` | Optional: a staff notification, with `to` (one or more addresses). Builds a flow too |
| `name` | The template's developer name: letters, digits and single underscores, starting with a letter, at most 80 characters. Name it for the form and its job (`Volunteer_Application_Confirmation`); a shared one for the organization (`Riverside_Resume_Link`) |
| `label` | Optional display name; default "<form name> Confirmation" and so on, or the developer name with spaces for a shared template |
| `subject`, `heading`, `body`, `button` | The words. `button.url` is a full `https://` address or one merge |
| `no_email_reason` | Why a form has no confirmation (it collects no email, or it is anonymous) |

**Sharing a template.** The same `name` in several plans (or in `saved` and `resume`) builds one template when the emails are identical, and sets it on every Form Template that names it. Different emails under one name stop the build. One shared Save Progress and resume template per organization is the usual choice.

## Input: org context (`--org org.json`)

```json
{
 "org_id": "00D000000000001AAA",
 "instance_url": "https://riverside-sandbox.my.salesforce.com",
 "assets": [{"DeveloperName": "Riverside_Logo", "NamespacePrefix": null, "IsVisibleByExternalUsers": true}],
 "submission_fields": ["FlowToolKit__Contact1_First_Name__c", "Project_Title__c"]
}
```

- `org_id`: `SELECT Id FROM Organization`, 18 characters.
- `instance_url`: the My Domain URL (references/brand-and-images.md).
- `assets`: the ContentAsset rows, as the query returns them.
- `submission_fields`: `SELECT QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'FlowToolKit__Form_Submission__c'` (a Tooling or data query). Or pass org-catalog's catalog with `--catalog`, which carries the same list and the brand kit.

Rows can be pasted as a connector returns them: a list, `{"records": [...]}` or `{"result": {"records": [...]}}`.

## Output

| File | What it is |
|---|---|
| `force-app/main/default/email/unfiled$public/<name>.email` and `.email-meta.xml` | Each template as metadata: a Lightning template (`uiType` SFX, type custom) on Form Submission, in the public unfiled folder |
| `force-app/main/default/flows/Form_Submission_After_Save_Notify_Staff_<Form>.flow-meta.xml` | A staff notification flow, active, one per form that asks for one |
| `_forms/<slug>/emails/build.json` | Every template with its `record` (the same template as an EmailTemplate record, for a connector), the Form Template `settings` to set per form, the flows and the warnings |
| `_forms/<slug>/emails/preview.html` | Every email with the sample values, for review; publish it as an artifact if the person wants a link |

`--source-dir` moves the metadata (default `force-app/main/default`); `--out` moves `build.json` and `preview.html`.

**Why the unfiled public folder.** A Lightning template in its own folder needs a Lightning email template folder, which a metadata deploy does not reliably create: a new folder can land Hidden and the template deploy then fails with "Cannot find folder". `unfiled$public` (shown as Public Email Templates) always exists. A record created by a connector goes to the same place with `FolderId` set to the org Id.
