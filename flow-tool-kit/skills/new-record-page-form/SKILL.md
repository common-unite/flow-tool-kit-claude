---
name: new-record-page-form
description: Use when a page needs a simple form or a record display without a Flow or a custom Lightning web component: a Contact Us form on a site that creates a Case, a mailing-list signup that creates a Lead, Account or Campaign details on a site page, or a custom record-page layout inside Salesforce ("put the Volunteer Profile form on the Contact page", "add a contact form to the site", "show the member their account details"). The pattern is Flow Tool Kit's own form component, dropped onto a Lightning record page or an Experience Cloud page (Aura or LWR), configured on the page, SLDS styled, with no Dynamic Forms or code. Placed in Lightning App Builder or Experience Builder, or by Claude Code writing the FlexiPage or site page. Also when design-to-blocks or build-site-pages meets a site section needing a simple form or record display, or build-form-component hands over a component for a page. A small wrapper component is the fallback only for autosave or a form kept in source.
---

# New Record Page Form

Flow Tool Kit's form component goes straight onto a Lightning record page or an Experience Cloud page and is set up there, on the page: pick a Form Component built in Form Builder, tick a few settings, and the page shows the form in SLDS, loads the record, validates and saves it. No page layout, no Dynamic Forms, no Flow, no custom Lightning web component. With it a partner can build a complete custom experience, in Salesforce and on a site, out of forms admins keep editing in Form Builder.

This skill is the pattern guide for that: when to reach for it, which of the two package components fits, how to place and set it up (by hand, or as metadata in Claude Code), the access each audience needs, and the check. Writing a component of your own is the fallback, for the two things the page settings cannot do.

**Called by** design-to-blocks and build-site-pages, when a site section needs a simple form or a record display; build-form-component, when a component it built should show on a page; ftk-start, for "put this form on the page". Also directly. **Reads** the project's `flow-tool-kit.json` and the Form Component (or its JSON). **Hands off** guest access to flow-access-fix and sf-guest-audit, building the form itself to build-form-component, site pages to build-site-pages, and custom section components to build-custom-lwc.

## When to use it

- **A simple site form with no complex process:** a Contact Us form that creates a Case, a mailing-list signup that creates a Lead. One form, one record, a confirmation message or a page to go to. A guest form still needs guest access set up and checked: **flow-access-fix** for the object, field and Create access, then **sf-guest-audit** for what the guest user can reach across the site.
- **A record shown on a site page:** Account details on the Account's site page, a Campaign's details on an event page, a signed-in member's own Account (through the `User.Contact.AccountId` path). Read Only, or editable for members who may edit.
- **A custom record-page experience inside Salesforce:** several forms on one Lightning record page, each a slice of the record (a Contact's volunteer profile, its emergency contact, its program details), laid out as the team wants rather than as one page layout, with the related record edited through Edit Related Record.

Not this: a multi-page process with stages, a submission record or a confirmation email is a **Form Template**. Logic that must run on save (create related records, call out) is a Form Template or a Flow, not a page form.

## Where it runs

| Runtime | What works |
|---|---|
| Claude Code, local or on the web, with the Salesforce CLI | Everything: write the FlexiPage or site page that places the component, deploy it, set up access and check it as each audience. Site pages go through build-site-pages |
| claude.ai chat, with or without a Salesforce connector | The plan and the click-by-click setup in Lightning App Builder or Experience Builder, the settings to tick, the access list. A connector that runs queries can find the Form Component's name. Placing it as metadata and deploying needs Claude Code, which the person hears in one line |

## Step 1: Pick the component

| Page | Component |
|---|---|
| A Lightning record page | **Form (Component)** (`FlowToolKit:lightningRecordForm`) |
| A Lightning app or Home page | **Form (Component)**, with Form Object Api Name set |
| An Experience Cloud page, with a record or without | **Form (Dynamic Component)** (`FlowToolKit:lightningRecordFormDynamicDisplay`): the object picked in its panel, a confirmation or a page to go to after a save, a button or modal display, a visibility rule. Form (Component) also works on a site, and suits a page that needs Prefill Values |

Every setting each one takes, with what it does, is in [references/package-contract.md](references/package-contract.md).

## Step 2: Have the form

The form is a Form Component in the org, built in Form Builder (or by build-form-component, which imports it). Get its name: a record component is named by its version, `<Name>_v0` (under its plain name it renders nothing); a metadata component by its plain name. With a connector that runs queries: `SELECT FlowToolKit__QualifiedApiName__c, FlowToolKit__Form_Object__c FROM FlowToolKit__Form_Component__c`. Read the audiences from the project config ([project-config](_shared/standards/project-config.md)): internal staff, portal members, site guests.

On the free edition, a form loaded by name works only on Account, Contact, Lead, Case, Campaign, Campaign Member and the package's own objects. All the examples above fit.

## Step 3: Set it up for the job

| Job | Settings |
|---|---|
| Contact Us creating a Case (site page, no record) | Form (Dynamic Component): object Case, the form by name, Record Id blank, a Confirmation Message, or Auto Navigate to a thank-you page. Hide Success Messages if the confirmation says it all |
| Mailing-list signup creating a Lead | The same, object Lead. Form (Component) with Prefill Values (`{"LeadSource": "Web"}`) stamps a value the visitor does not type |
| Account or Campaign details on a site page | On the object's record page, Record Id `{!recordId}` (LWR: `{!Route.recordId}` also works); Read Only on, or left off for members who may edit |
| A member's own Account on any page | Form (Component), Lookup Field API Name `User.Contact.AccountId`, a form built on Account |
| A slice of the record on a Lightning record page | Form (Component), the form by name, the access check left on (the default). Edit Related Record with a Lookup Field API Name to edit the parent (the Account from a Contact page) |

The Save button shows unless Hide Save Button is on (Enable Save Actions off on the Dynamic Component). Leave the **access check** on: people who may only read the record see it read only instead of an editable form whose saves fail.

## Step 4: Place it

**By hand.** Lightning: a record of the object, the gear, **Edit Page**, drag **Form (Component)** from the Custom - Managed list, set its settings, **Save**, **Activate** if the page is not yet in use. Site: Experience Builder, the page, drag **Form (Dynamic Component)** on, **Configure Flow Properties**, **Publish**. Click by click: [references/deploy-and-check.md](references/deploy-and-check.md) and [references/experience-cloud.md](references/experience-cloud.md).

**As metadata (Claude Code).** The placement then lives in the project's source and deploys to every org:

- **Lightning record page:** retrieve the object's FlexiPage, add a `componentInstance` with `<componentName>FlowToolKit:lightningRecordForm</componentName>` and one `componentInstanceProperties` per setting, deploy. The snippet is in [references/deploy-and-check.md](references/deploy-and-check.md). Activation stays in App Builder unless the app's metadata already assigns the page.
- **Site page:** an item in build-site-pages' `page.json`, which writes the view, deploys, publishes and checks it logged out:

  ```json
  {"kind": "component", "definition": "FlowToolKit:lightningRecordFormDynamicDisplay",
   "attributes": {"properties": {"object": "Case", "formSelectionMode": "component", "formQualifiedApiName": "Contact_Us_v0",
                                 "displayType": "component", "confirmationMessage": "<p>Thanks. We will reply within two business days.</p>"}}}
  ```

  On a page built as the object's record page, build-site-pages binds the Record Id to the page record. For a form kept in the site's source with no Form Component record in the org, use `"formSelectionMode": "custom"` with the form's JSON in `formJsonConfig`.

Retrieve whatever the deploy would overwrite first, so a change someone made in the org is not lost.

## Step 5: Access, for every audience

| Need | Granted by |
|---|---|
| The package's Apex | **Form Builder Internal User** (or Manager, or Admin) for staff; **Form (Flow User)** for portal members and guests |
| The object and fields | Read on the object and every field the form shows; Edit on fields people change; Create on the object for a form that creates records. In the org's own permission sets, per audience; a guest's in a permission set for the site's guest user |
| The record | Sharing: the org's model for staff, a sharing set or sharing rule for portal members, a read-only guest sharing rule for a record a guest views |

Ask which permission sets get the grants. A guest form: **flow-access-fix** sets up and checks the guest's Create, field access and sharing end to end, and **sf-guest-audit** then reviews everything the guest user can reach. Records a guest creates are owned by the site's default guest record owner (the site's Preferences in Experience Builder administration). A guest can create a record but never edit one: with a record, a guest always sees it read only.

## Step 6: Check it

As each audience, never only as yourself and never in Builder's preview:

1. **The page:** the form renders, styled like the org's other Flow Tool Kit forms, with its Save button (unless hidden).
2. **Saving:** change a field, press Save, reload: the value is there. A create form: submit it, see the confirmation (or the page it goes to), and find the new record (`sf data query`).
3. **A rule:** a required field left blank or a validation rule broken: nothing saves and the message shows.
4. **Read only:** as a user who may read but not edit the record, the form is read only.
5. **A site:** published, then loaded as a member and, for a public page, as a guest in a fresh private window. On LWR, **FlowToolKit LWR Support** must be in the Theme Footer and the site published after every change and every Flow Tool Kit upgrade, or the form fails to load.

## Fallback: a small wrapper component

Write a component of your own only when the page settings cannot do the job. Two things qualify:

- **Autosave.** Saving each change as it is made, with no Save button, is a property of the record form that neither page component exposes. Do not offer it unprompted: it is rarely wanted on a record page. It fits a profile-style form edited in place, one field at a time (a phone number, a note), and not a form whose fields should change together, since each valid change saves at once.
- **A form kept in source on a Lightning record page.** Form (Component) on a Lightning page takes only a Form Component's name, so the form has to exist as a record in every org. A wrapper with the form baked in deploys with the code and needs no Form Component record. (On a site page, Form (Dynamic Component)'s custom JSON already does this, so no wrapper is needed there.)

`scripts/record_page_form.py` writes the wrapper: a few lines that place the package's record form with the page's record, the object fixed, the access check on, and the form baked in (or named). The Save button shows by default; `--autosave` turns on autosave and hides the Save button together.

1. **The JSON, as the org saved it.** The Form Component's **Export** action (copy the whole token), or with a connector `SELECT FlowToolKit__FormConfigJSON__c FROM FlowToolKit__Form_Component__c WHERE FlowToolKit__QualifiedApiName__c = '<Name>'`. Save it to `_forms/<slug>/<slug>.json` ([naming](_shared/standards/documentation.md), section 6) exactly as given; never retype it. Only JSON the org saved renders right: hand-written JSON lacks the version and section layout keys a save adds, and field widths come out wrong. `inspect` warns when they are missing.
2. **Read it:** `python3 scripts/record_page_form.py inspect _forms/<slug>/<slug>.json` prints the object, the label in App Builder, the component name (`c:` plus the object and label), the fields, and what the form needs in the org (custom sections, flows, embedded components). `--name` and `--label` override.
3. **Write it:**

   ```bash
   python3 scripts/record_page_form.py write _forms/<slug>/<slug>.json \
       --lwc-dir force-app/main/default/lwc [--site] [--autosave]
   ```

   It writes the bundle (scoped to the one object, with a description in the [documentation](_shared/standards/documentation.md) shape), its Jest test, the Jest stub for the package's record form and the `jest.config.js` mapping when missing. `--component-name <Name>_v0 --object <Object> --label <text>` names a saved Form Component instead of baking JSON. `--force` replaces a component of the same name. For custom sections on an LWR site, `record_page_form.py lwr-support --lwc-dir force-app/main/default/lwc c:<section>` adds them to the site's support component.
4. **Test:** `npx sfdx-lwc-jest -- force-app/main/default/lwc/<name>`. The test fails if the save choice changes (the Save button shown and autosave off by default; autosave on and the Save button hidden with `--autosave`), if the access check or record binding is removed, or if the baked form stops parsing or names another object.
5. **Deploy and place** it like the package component (it appears in App Builder's Custom list on its object's pages only), then the same access and checks. With autosave, check by changing a typed field and waiting a moment instead of pressing Save.

A finished wrapper is in [assets/volunteer-profile/](assets/volunteer-profile/README.md).

## Report

Which component, where it was placed (by hand or as metadata, and the file), the form, the settings ticked, the access granted per audience and what the admin still has to do (assign permission sets, publish the site), the checks you saw pass, and anything left to check. For a wrapper: its files, `c:<name>`, baked or by name, Save button or autosave, and why the page component could not do it.

## Common mistakes

| Mistake | Instead |
|---|---|
| Writing a custom Lightning web component for a form on a page | The package's form component, set up on the page; a wrapper only for autosave or a baked form on a Lightning record page |
| A Flow for a Contact Us form or a signup | The form component on the site page creates the record itself |
| Turning autosave on without being asked | The Save button; autosave only when the person asks, through the wrapper |
| By name, `Volunteer_Profile` renders nothing | A Form Component record is `Volunteer_Profile_v0` |
| A site form with nothing in Form Object Api Name on a page with no record | Type the object, or use Form (Dynamic Component), whose panel holds the object |
| Record Id left blank on a site record page | `{!recordId}` (or `{!Route.recordId}` on LWR) |
| Turning the access check off | Leave it on; without it a user blocked by sharing sees an editable form whose saves fail |
| Expecting guests to edit a record | A guest creates records but sees an existing record read only |
| A guest form that fails to save | Guest Create and field access, checked with flow-access-fix; then sf-guest-audit |
| An LWR page that fails to load, or an old version showing | FlowToolKit LWR Support in the Theme Footer, then Publish; publish after every change |
| Calling it done from the deploy result | Save a value, reload, and see it saved, as each audience |
