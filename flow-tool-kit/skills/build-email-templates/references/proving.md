# Proving the emails work

A template is done when a real email has been sent and read back with every merge filled in. A deployed template with no test proves nothing: the commonest failures (no Contact 1, an unverified sender, sandbox deliverability, a stale developer name on the Form Template) only show when something sends.

## 1. Before sending: the org is ready

```sql
SELECT Name, FlowToolKit__Send_Confirmation__c, FlowToolKit__Email_Template_Name_Confirmation__c,
       FlowToolKit__Email_Template_Name_Saved__c, FlowToolKit__Email_Template_Name_Resume_Form__c,
       FlowToolKit__Send_Save_Progress_Email__c, FlowToolKit__Stages_Mode__c, FlowToolKit__Web_Form_URL__c,
       FlowToolKit__Conversion_Type__c
FROM FlowToolKit__Form_Template__c WHERE Name = 'Volunteer Application'
```

- Each Email Template Name field holds exactly the developer name the build wrote.
- Save Progress or resume emails: Web Form URL is not blank (set it with Open Web Form or Change Web Form Address, or the org's Default Web Form URL).
- Conversion Type is not Bypass, or no confirmation will send.
- `SELECT Id, DeveloperName, LastModifiedDate FROM EmailTemplate WHERE DeveloperName = 'Volunteer_Application_Confirmation'` returns one row.
- In a sandbox, Deliverability is All Email; the Default Workflow User's address is verified (references/package-behaviour.md).

**A render with no email (Claude Code).** Before any test submission, render a template against an existing submission that has a Contact 1. Nothing is sent:

```bash
python3 scripts/emailbuild.py render-apex Volunteer_Application_Confirmation <Form Submission Id> > render.apex
sf apex run --file render.apex --target-org <org-alias>
```

The debug lines show the merged subject and HTML. Any `{{{` left, or an error, is a merge problem to fix in the plan.

## 2. Send a test

**The confirmation.** Either:
- **Through the form** (best): the person submits it once in Preview or on the site, with an email address they can read. This proves the whole path, including the conversion that creates Contact 1.
- **By a record**, when nobody can submit right now: create a Form Submission with the Form Template, the Contact 1 first name, last name and email (an address the person reads), a Submission Date of now and Status Submitted. Creating it with Status Submitted starts the real conversion, so it creates the same Contact and records a respondent would; remove them afterwards if the org should stay clean. In Claude Code use `sf data create record`; in chat, the connector's create-record tool.

The conversion runs in the background; allow a minute before reading back.

**Save Progress and stages resume.** These send only when a respondent saves or clicks the button, so test through the form. The branded Save Progress email needs a Contact 1 on the draft (a portal user, or a form that prefills Contact 1); anyone else gets the package's built-in email by design.

## 3. Read it back

```sql
SELECT Id, FlowToolKit__Status__c, FlowToolKit__Contact_1__c, FlowToolKit__Lead_1__c,
       FlowToolKit__Internal_Confirmation_Last_Sent__c, FlowToolKit__Conversion_Status__c
FROM FlowToolKit__Form_Submission__c WHERE Id = '<Form Submission Id>'

SELECT FlowToolKit__Status__c, FlowToolKit__Log_Message__c, CreatedDate
FROM FlowToolKit__Form_Submission_Conversion_Log__c
WHERE FlowToolKit__Form_Submission__c = '<Form Submission Id>' ORDER BY CreatedDate

SELECT Subject, ToAddress, CcAddress, Status, HasAttachment, HtmlBody, CreatedDate
FROM EmailMessage WHERE RelatedToId = '<Form Submission Id>' ORDER BY CreatedDate DESC
```

A confirmation to a Contact is linked to the submission. To a Lead it is not: find it by `ToAddress` and today's date instead. Save the rows to files and check them:

```bash
python3 scripts/emailbuild.py verify _forms/<slug>/emails/build.json --template Volunteer_Application_Confirmation \
  --emails emails.json --logs logs.json --expect "Jordan" --expect "Saturday mornings"
```

It fails on an unmerged field, a missing image, expected text that is absent, a missing PDF with `--attachment`, and any Conversion Log error, with the fix. Then tell the person to look at the email in their inbox too: the read-back proves the content, the inbox proves delivery and how the mail client draws it.

## Conversion Log messages and their fixes

| Message | Cause | Fix |
|---|---|---|
| Confirmation Email Sent Successfully | Sent | Nothing |
| Email Template not found (<name>) | No template by that developer name on Form Submission | Deploy it; match the Form Template field to the developer name exactly |
| No primary contact or lead assigned | The conversion set no Contact 1 or Lead 1 | Check the form collects Contact 1 name and email and the conversion creates the Contact or Lead |
| Email Template Render Failed: ... | A merge field is wrong or unreadable | Build again with the org's field list; the message names the field |
| Send Email Message Failed | The send was refused | Deliverability, the Default Workflow User's verified address, or the daily email limit |
| Save Progress email didn't send | No web form address, no recipient, or a refused send | The row's detail says which |
| The confirmation email was sent without the PDF ... | The conversion runs as Automated Process | Set the running user (references/package-behaviour.md), then send again |
| Staff notification not sent | The staff flow could not render or send | The row's detail says which |

To send a confirmation again for the same submission, clear its Confirmation Last Sent and Reprocess it.
