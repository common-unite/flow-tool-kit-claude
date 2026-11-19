# When Flow Tool Kit sends each email

What the package does with each email template, read from the package's own flows and fields (Flow Tool Kit 5.3). Build to this, and explain it to the person in these words when they ask why an email did or did not arrive.

## The emails at a glance

| Email | Form Template settings | When it sends | Who gets it | Renders against | When it cannot send |
|---|---|---|---|---|---|
| **Confirmation** | Send Confirmation Email on, Email Template Name (Confirmation) | Once, when a submission is received and converted | The primary address (below), plus the Recipients (Confirmation Email) choices as copies | Contact 1, or Lead 1 when there is no Contact 1, with the submission as the related record | A Conversion Log row on the submission; the conversion still finishes |
| **Save Progress** | Allow Save Progress, Send Save Progress Email on, Email Template Name (Saved) | When a respondent saves an ordinary (non-stages) form, at most once an hour | Contact 1's email unless it bounced, then the Contact 1 Email answer, then the Email answer | Contact 1 | No Contact 1, no template by that name, or any other fault: the package's built-in email goes instead. If that fails too, a Conversion Log row |
| **Resume link (stages)** | Stages Mode, Email Template Name (Resume Form) | When the respondent clicks **Email me a resume link** | Contact 1 Email answer, then Email, then Contact 1's email, then the owner's email | The owner's portal Contact, then Contact 1, then the owner | Any fault: the built-in email goes instead; if that fails, a Conversion Log row |
| **Start invitation** | Email Template Name (Start Form) | When a draft submission is created with a token already set (an admin's invitation flow) | The owner's email when the owner is a portal user, otherwise the Contact 1 Email answer, then Email | The owner's portal Contact, then Contact 1, then the owner | Blank setting: nothing is sent |
| **Staff notification** | None: this skill's flow | When a submission for that form is received | The staff addresses in the flow | Nothing but the submission | A Conversion Log row; the respondent's submit is never affected |

## Confirmation in detail

- The conversion sends it only when **all** of these hold: Send Confirmation Email is on; Email Template Name (Confirmation) is set; the submission has a Contact 1 or a Lead 1 after conversion; the submission is not Anonymous; and its Confirmation Last Sent is blank. So a template whose Conversion Type is Bypass (nothing converts) sends no confirmation, and a form that never creates a Contact or Lead sends none either.
- **Without a template name nothing is sent.** Email Template Body (Confirmation) is read by the package's own Visualforce template, not by a Lightning template.
- The template is found by its developer name **and** its object, Form Submission. When several templates share a developer name, the most recently modified one wins, so an older copy in another folder can quietly take over. Keep one template per name.
- **Primary address:** the Contact 1 Email answer, then the Contact 1 record's email, then Lead 1's email (what the respondent just typed wins). **Copies:** Recipients (Confirmation Email) adds the Email answer, the Email (Company) answer and the alternate Contact or Lead's email, skipping blanks, duplicates and the primary address.
- It is rendered in Apex against Contact 1 or Lead 1 with the submission as the related record, then sent as a rich-text email from the org's **Default Workflow User**. That is why a Lead recipient merges Form Submission fields too.
- It is logged on the recipient's activity timeline. For a Contact the email is also linked to the submission; for a Lead it is not (Salesforce refuses that link for Leads).
- **Sent once.** Confirmation Last Sent is stamped after the send. Clear it on a submission to make a Reprocess send the confirmation again.
- **Answers PDF:** with Attach PDF to Confirmation Email on, the email carries a PDF of the answers, also saved in the submission's Files. The conversion needs a running user that can open the PDF page (below). Without it the email still sends, with no PDF and a warning on the Conversion Log.

## Save Progress and resume in detail

- **The link is a field.** Save Progress Resume Link (`FlowToolKit__Internal_Resume_Link__c`) is the template's web form address plus `resume=` and the submission's token. The form reads `resume` itself: no URL Parameter Mapping and no `pv9`. The link works once, stops on submit, and expires after 7 days; each email carries a new link and only the latest one works.
- **It needs a web form address**: the template's own (Open Web Form or Change Web Form Address on the Form Template) or the org's Default Web Form URL. With neither, the link is blank and no Save Progress email is sent; a Conversion Log row says how to fix it.
- **Stages mode never sends the Save Progress email**, even with the setting on. Its **Email me a resume link** button sends the Resume Form email instead. One template can serve both fields, since both merge the same link.
- **The branded Save Progress email needs a Contact 1.** A guest who has only typed an email address gets the package's built-in email (the form's name, a short note and the link). That is expected, not a fault. A site guest usually cannot read a saved draft; whether guests may resume is the org's choice (flow-access-fix covers it).
- Only the main submission sends: child rows (repeaters and related records) never do.
- Both are sent by the packaged flow **(Form) Send Resume Link | Overridable**, from the Default Workflow User.

## Start invitations

An admin's own flow creates draft submissions with a token for people to start a form. The packaged **(Form) Send Start Link | Overridable** flow sends the template named in Email Template Name (Start Form) after each such insert. Merge the Save Progress Resume Link into its button: it carries the same token. Tokens expire after 7 days, so an invitation program with a longer window needs its own token refresh. This path has not been run against a Lightning template built by this skill yet: prove it with one test invitation before relying on it.

## Staff notifications

The package sends no staff alert. This skill builds one per form when the plan asks (`emails.staff`): a record-triggered flow on Form Submission that runs when a submission for that Form Template is received (Status becomes Submitted with a Submission Date, not a child row). It renders the staff template with the package's **Render Email Template** action, which needs no recipient, so a staff template merges Form Submission fields only. It sends from the Default Workflow User to the listed addresses, and runs after the respondent's save is committed, so a failed email never fails a submit. A failure is written to the submission's Conversion Log. Flows are metadata: Claude Code deploys it.

## One-time org setup

| What | Why | Where |
|---|---|---|
| Deliverability set to **All Email** | Sandboxes start on System Email Only, which blocks every one of these emails | Setup, Deliverability |
| The **Default Workflow User** has a verified email address | Every email here is sent from that user; an unverified address refuses the send | Setup, Process Automation Settings |
| The conversion's **running user** (only for the answers PDF) | The default Automated Process user cannot open the PDF page | A Platform Event Subscriber Config, below |

The running user is set by deploying this file (Claude Code, or any Metadata API deploy tool; there is no Setup screen that creates it), with an active system administrator's username:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PlatformEventSubscriberConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Form Submission Convert Running User</masterLabel>
    <platformEventConsumer>FlowToolKit__Form_Submission_Convert</platformEventConsumer>
    <user>admin.user@example.org</user>
</PlatformEventSubscriberConfig>
```

Save it as `platformEventSubscriberConfigs/Form_Submission_Convert_Running_User.platformEventSubscriberConfig-meta.xml` in the project's metadata folder and deploy it. Then the person goes to **Setup, Platform Events, Form Submission Convert, Subscriptions, Manage**, clicks **Suspend**, then **Resume**, so the new user takes effect at once. Records the conversion creates then show that user as Created By. If that user is ever deactivated, set another the same way.

## Sending from an organization address

The packaged flows send from the Default Workflow User. To send from an Org-Wide Email Address instead, the org overrides **(Form Submission) Convert | Utility | Send Email | Overridable** (and the resume flow, for Save Progress). An override replaces the packaged flow and must copy its newer steps, including the answers PDF ones; new-mapping-flow covers overrides.
