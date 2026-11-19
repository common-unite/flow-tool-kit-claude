# What the org needs after the build

The build's report lists, under `setup`, only the items this template needs. Each one in full:

## The answers PDF: the conversion's running user

With **Attach PDF to Confirmation Email** on (a long form that sends a confirmation), each confirmation email carries a PDF of the answers, also saved in the submission's Files. The email is sent by the conversion, which runs on the **Form Submission Convert** platform event trigger. Salesforce runs that trigger as the **Automated Process** user unless a running user is named, and Automated Process cannot be given access to the page that draws the PDF. Without a running user the email goes **without** the PDF, the submission still converts, and its Conversion Log carries a warning saying so.

Set it once per org:

1. Pick an active user with the System Administrator profile who will stay active.
2. Write the config (it checks the user when given the org):
   ```bash
   python3 scripts/runninguser.py --user <username> --out <project-dir> --org <org-alias>
   ```
   It writes `platformEventSubscriberConfigs/Form_Submission_Convert_Running_User.platformEventSubscriberConfig-meta.xml`, consumer `FlowToolKit__Form_Submission_Convert`. Salesforce has no Setup screen that creates one.
3. Deploy it, once the person agrees: `sf project deploy start --source-dir <project-dir>/force-app/main/default/platformEventSubscriberConfigs --target-org <org-alias>`.
4. Setup, Platform Events, **Form Submission Convert**, Subscriptions, **Manage** next to `Form_Submission_Convert`: **Suspend** and confirm, then **Resume** and confirm. Without this Salesforce can take an unspecified time to use the new user; Resume processes any event that arrived meanwhile.
5. Check: the Subscriptions list shows the user in the User column, and a test submission's confirmation arrives with the PDF.

What changes: records the conversion creates show that user as Created By and owner, and the Conversion Log rows are created by that user. The trigger still runs in system context. If the user is deactivated, run the steps again with another.

If the org overrides the send flow `(Form Submission) Convert | Utility | Send Email | Overridable`, its override gets no PDF until the new steps are copied in; new-mapping-flow covers that.

## Save Progress and resume emails

- **Save Progress email** (ordinary pages with Save Progress on): set where the form lives, with **Open Web Form** or **Change Web Form Address** on the template, or the org's Default Web Form URL. Without an address no email is sent and a Conversion Log row says how to fix it.
- **Stages mode** never sends the Save Progress email; the **Email me a resume link** button sends the resume email (Email Template Name Resume Form).
- Both are sent from the org's **Default Workflow User**, whose email address must be verified.
- A guest who opens a resume link sees a new form with a notice unless the org lets guests resume (a system-mode copy of the prefill flow): that is the org's own security decision, and flow-access-fix explains it.

## Guests (a public site)

| The template uses | The guest needs |
|---|---|
| Any record component (a created Compact or Split header, an extended or shared component) | A guest sharing rule on Form Component: Read, where Record Type is Record Component. Without it the header or section is blank and the form shows an error |
| Conditional payment | Read on Form Template's Payment Conditions, and on every field the rule reads. An unreadable rule blocks submission rather than waiving payment |
| URL parameters | Edit on every Form Submission field a parameter fills |
| Your own Form Template fields in the header (Brand_Color__c) | Read on them |
| New fields | The permission set newfields.py wrote, assigned to the guest user |

flow-access-fix sets these up; sf-guest-audit checks what guests can see.

## The prefill flow

A template whose plan names `prefill.flow` carries it in **Prefill Flow API Name**. The flow must be active before anyone opens the form, or the form says its default answers could not be loaded. It takes the input `record` (the Form Submission, already holding the Prefill Template, source and URL parameter values) and returns `prefillRecord`; to fill a repeater or table section with related rows it also returns `prefillRelatedRecords`, built by the **Form Submission | Prefill From Mapped Record** action in **Related Records** mode with the section's **Section Tag**. The report lists the step when the flow is missing or inactive.

Section Tag is a restricted picklist sharing the **Data Conversion Tag(s)** value set (Default, Contacts, Tasks, Cases, Opportunities as shipped). A tag the org lacks stops a metadata-mode build; records mode leaves it off and lists it. Add the value in Setup, Picklist Value Sets, Data Conversion Tag(s), then rebuild. Each tag is used once per template.

## Email templates

The template names its confirmation, Save Progress and resume emails as the plan designed them. Until build-email-templates builds them, the package sends its built-in emails; the report lists the names the org does not have yet.

## Removing a draft build

To take a prototype or a test build out of the org, delete what the build added, using the Ids in the report and in `plan.json` `build`:

1. The Form Template (`template_id`). Its pages and sections go with it.
2. Its **Pre-fill Template**: the Form Submission Flow Tool Kit created with the template (`prefill_template_id`, marked Is Pre-fill Template, auto-named). Deleting the template does not delete it. Delete it only when no other template or section names it in its Pre-fill Template field. For a template built before the report named it, read the template's Pre-fill Template field before deleting the template.
3. The record components in the report's `components` (each with its Id), once no other template or section uses them: a header or a shared component often serves other templates too. Never a component the plan reused.

Leave `build` in `plan.json`: a later build finds the template gone, builds a new one under the same names, and deletes the old Pre-fill Template if it is still there and unused.

## After any change

Reset Form Cache in Form Builder after a metadata change, then open Preview Form from the template record. On an Experience Cloud LWR site, the site serves its last publish: publish it again after a package upgrade or component change.
