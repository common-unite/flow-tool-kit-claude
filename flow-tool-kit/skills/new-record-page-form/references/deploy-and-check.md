# Lightning pages: place, grant and check

Placing the package's form component by hand needs only Lightning App Builder. Placing it as metadata, and deploying the fallback wrapper, need **Claude Code** (local or on the web) with the Salesforce CLI and a project folder. In claude.ai chat, give the person the App Builder steps, or the files with one line saying the deploy needs Claude Code.

## 1. Before you start

- **The org has Flow Tool Kit installed**, and the Form Component exists in it (by name: `<Name>_v0` for a record component).
- **Pull before you deploy.** Retrieve the FlexiPage (or component) the deploy would overwrite, so a change someone made in App Builder is not lost: `sf project retrieve start --metadata FlexiPage:<Page_Name> --target-org <org-alias>`.

## 2. Place Form (Component) by hand

1. Open any record of the object, the gear, **Edit Page**.
2. Find **Form (Component)** under **Custom - Managed** and drag it where the form belongs.
3. Set **Form Qualified Api Name** to the Form Component's name. Leave **Read only when the user cannot edit the record** on. Set any other setting the job needs ([package-contract.md](package-contract.md) lists them all).
4. **Save**. On a page that is not yet in use, **Activate** it: as the org default, for an app, or for an app, record type and profile.

Several forms on one page each take their own Form (Component), each with its own form. App Builder's component visibility filters can show one only when a field has a value or for some profiles.

## 3. Place it as metadata

Add an item to a region of the object's record FlexiPage (`force-app/main/default/flexipages/<Page_Name>.flexipage-meta.xml`), one `componentInstanceProperties` per setting you change:

```xml
<itemInstances>
    <componentInstance>
        <componentInstanceProperties>
            <name>formQualifiedApiName</name>
            <value>Volunteer_Profile_v0</value>
        </componentInstanceProperties>
        <componentInstanceProperties>
            <name>checkRecordAccess</name>
            <value>true</value>
        </componentInstanceProperties>
        <componentName>FlowToolKit:lightningRecordForm</componentName>
        <identifier>FlowToolKit_lightningRecordForm_volunteerProfile</identifier>
    </componentInstance>
</itemInstances>
```

The `identifier` must be unique on the page. Deploy with `sf project deploy start --source-dir force-app/main/default/flexipages/<Page_Name>.flexipage-meta.xml --target-org <org-alias>` after `--dry-run`. A new page still needs activating in App Builder, unless the app's metadata already assigns it.

## 4. Access, for every audience

The form reads and writes as the person using it. Ask which permission sets get the grants; create a new one only when the person says so, and retrieve the org's copy before adding to it, so a local file does not remove grants other work added.

| What | Grant |
|---|---|
| The package's Apex for the form | **Form Builder Internal User** (or Manager, or Admin) for staff; **Form (Flow User)** for portal members and guests. Package sets: assign them, never edit them |
| The object | Read for everyone who sees the form; Edit for those who change it; Create for a form that creates records |
| Each field the form shows | Read, and Edit for fields people change. A field a user cannot read is left out of their form |
| The record | Sharing. Staff: the org's sharing model. Portal members: a sharing set or sharing rule. Guests: a read-only guest sharing rule (flow-access-fix) |
| Flows the form launches | A grant per audience (flow-access-fix) |

## 5. Check it in the org

It is not done until each of these is seen, not assumed. A headless browser in Claude Code can do them, signed in through `sf org open --url-only --path lightning/r/<Object>/<Record Id>/view --target-org <org-alias>`; otherwise list them for the person.

1. **The page:** the form renders inside the record page, styled like the org's other Flow Tool Kit forms, with its Save button unless it was hidden.
2. **A save:** change a field and press Save, then reload, or read it back (`sf data query -q "SELECT <Field> FROM <Object> WHERE Id = '<Record Id>'"`).
3. **A rule:** leave a required field blank or break a validation rule. Nothing saves until it is fixed, and the message shows.
4. **Read only:** as a user who may read but not edit the record, the form is read only.
5. **Each audience** on each page it is placed on: staff on the Lightning page; portal members and guests on the site ([experience-cloud.md](experience-cloud.md)).

With the autosave wrapper, step 2 is: change a typed field and stop typing; about a second later it is saved. A picklist, checkbox or date saves at once.

Lightning can keep serving the previous build of a page for a while after a deploy. Before deciding a change did not work, reload with the cache cleared; in a sandbox you are iterating in, turn off "Enable secure and persistent browser caching" in Session Settings.

## 6. The fallback wrapper: test and deploy

Only when the page component cannot do the job (autosave, or a baked form on a Lightning record page).

- **The org's namespace.** In an org with its own namespace (a partner's packaging org), the wrapper is `<namespace>:<name>`, not `c:<name>`. Check with `SELECT NamespacePrefix FROM Organization`.
- **Test, then deploy:**

  ```bash
  npx sfdx-lwc-jest -- force-app/main/default/lwc/<name>
  sf project deploy start --source-dir force-app/main/default/lwc/<name> --target-org <org-alias>
  ```

- The project's `.forceignore` must list `**/__tests__/**`, or the deploy sends the Jest test and fails with "LWC1702: Invalid LWC imported identifier". Jest needs `@salesforce/sfdx-lwc-jest` in the project and the stub for the package's record form, which `record_page_form.py write` adds (`jest/stubs/flowtoolkit/lightningRecordForm/` and the `moduleNameMapper` line). The template compiler lowercases the namespace, so the stub is mapped as `flowtoolkit/lightningRecordForm`.
- Deploy the LWR support component in the same deploy when `lwr-support` ran.
- Place it like the package component: it is listed under **Custom** on its object's record pages only, and takes no settings. As metadata, its `componentName` is `c:<name>`.
