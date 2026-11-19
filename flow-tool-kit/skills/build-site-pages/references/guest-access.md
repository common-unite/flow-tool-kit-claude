# Guest access for site pages

A page a logged-out visitor sees runs as the site's guest user. Everything it shows must be granted to that user, and a page that works for you signed in proves nothing about a guest. For a form, **flow-access-fix** checks the guest's access end to end and proposes the narrowest grants; use it before going public. The steps below cover what the pages themselves need.

## 1. Field and object access

- Grant the guest profile read on each object and field a block, card or repeater shows, and nothing more. Find the profile with `SELECT Profile.Name FROM User WHERE UserType = 'Guest'`.
- Write the grants into the project's own profile file under `force-app/`, then deploy a package holding only the changed entries. A profile retrieved on its own comes back with only part of its settings, and deploying a whole profile file can overwrite newer changes in the org; a profile deploy changes only the settings it is given.
- **Staff need access too.** A field deployed through the Metadata API has no access for anyone until a profile or permission set grants it. Mirror an existing field's grants: `SELECT Parent.Label, Parent.Profile.Name, PermissionsEdit FROM FieldPermissions WHERE Field = '<Object>.<Sibling_Field__c>'`. A grantee of type Group is a permission set group: grant on a member set and the group inherits it. A permission set retrieved on its own is complete, so retrieve, add, deploy.

## 2. Guest sharing rules

Guests see a record only through a guest sharing rule (`sharingGuestRules` in `<Object>.sharingRules-meta.xml`). Its `guestUser` is the guest user's nickname (`SELECT CommunityNickname FROM User WHERE UserType = 'Guest'`), not the site name. Child objects set to Controlled by Parent follow their parent's rule. Share only the records the page lists, with a criteria rule (Status equals Open, Published is true), never all records.

```xml
<sharingGuestRules>
    <fullName>Open_Programs_for_Guests</fullName>
    <accessLevel>Read</accessLevel>
    <label>Open Programs for Guests</label>
    <sharedTo>
        <guestUser>Riverside_Garden</guestUser>
    </sharedTo>
    <criteriaItems>
        <field>Status__c</field>
        <operation>equals</operation>
        <value>Open</value>
    </criteriaItems>
    <includeHVUOwnedRecords>false</includeHVUOwnedRecords>
</sharingGuestRules>
```

## 3. Images and files

- Photos a guest loads are public Asset Files (`isVisibleByExternalUsers` true), as `scripts/asset_files.py` writes them. Blocks use them by name; to check one by hand, a logged-out request to `https://<domain>/<prefix>/sfsites/c/file-asset/<Name>?v=1` returns the image.
- Files attached to records reach guests only with **guest file access** on the site's Network (`enableGuestFileAccess` true in the Network metadata).
- An image inside a rich text field reaches a guest through the site's own address (`/<prefix>/sfsites/c/servlet/rtaImage?...`), which the design block writes; the raw file address does not load for a guest.

## 4. The site and the guest user

- Public access on the site: `authenticationType` `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED` (in `site.json`, written by the `--entire-site` run).
- The site must be active (Status Live), or its public address sends visitors to a login page. Activate it in Setup, All Sites, or deploy its Network (`networks/<Site name>.network-meta.xml`, retrieved as `Network:<Site name>`) with `<status>Live</status>` and `<sendWelcomeEmail>false</sendWelcomeEmail>`, so members get no welcome email when it goes live. Guest file access (`enableGuestFileAccess`) is set in the same file.
- The guest user needs Flow Tool Kit's flow permission set once a form or repeater is on a page: `FlowToolKit__Form_Flow_User`, plus any guest permission set the org's own setup added (an org set up with Flow Tool Kit's installer may have **Form Flow (Guest User)**). `_shared/sf/guest_site_setup.py` assigns what the guest lacks, deploys the guest sharing rules from `--sharing`, then publishes.

## 5. Prove it

Publish, then run the render check (SKILL.md, Step 7) against the public address. A guest who lacks access rarely sees an error page. A repeater on an object the guest cannot read still renders, showing "Records are unavailable", with an `HTTP 401` on `ui-api/object-info` under the table; a block bound to a record it cannot read shows no content. Read the failed requests, compare the component count with the generator's number, and look at the screenshots.
