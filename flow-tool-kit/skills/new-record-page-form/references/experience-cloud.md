# Experience Cloud pages

Both package components work on Aura and LWR sites: **Form (Dynamic Component)** for most site forms, **Form (Component)** where Prefill Values are needed. Every setting is in [package-contract.md](package-contract.md). To place them as metadata rather than by hand, use build-site-pages: a `page.json` item of kind `component` (the shape is in SKILL.md, Step 4), which it turns into the page's view, deploys, publishes and checks logged out.

## A form that creates a record (Contact Us, a signup)

1. In Experience Builder, open (or create) the page, such as Contact Us.
2. Drag **Form (Dynamic Component)** on. Leave **Record Id** blank: with no record the form creates one.
3. **Configure Flow Properties:** the object (Case, Lead), the Form Component by name, Display Type Component (or Button or Modal to open it from a button), a **Confirmation Message**, or **Auto Navigate** to a thank-you page. Turn on **Hide Success Messages** when the confirmation says it all.
4. **Publish**.

With Form (Component) instead: type the object in **Form Object Api Name** (the `{!objectApiName}` default is empty on a page with no record), and use **Prefill Values** for a value the visitor does not type (`{"LeadSource": "Web"}`).

## A record shown on its page (Account or Campaign details)

1. **The object's pages.** **Pages**, **New Page**, **Object Pages**, choose the object, **Create**. Builder adds a detail page, a list page and a related list page. A site that already has them: open the detail page.
2. **Place the component** on the detail page, removing the standard record detail component if the form replaces it.
3. **Bind the record.** **Record Id** is `{!recordId}`, the default, on both kinds of site; on LWR `{!Route.recordId}` works too. A blank Record Id on a record page shows nothing, or a "Get Record Value(s) Error".
4. **Read Only** on for a display; off for members who may edit. The access check makes a read-only record read only either way.
5. **Publish**. The record's link is `https://<your site>/s/<object>/<Record Id>` on Aura, without the `/s` on LWR.

A signed-in member's own Account on any page: Form (Component), **Lookup Field API Name** `User.Contact.AccountId`, a form built on Account.

## LWR sites only

An LWR site serves the components bundled at its last publish, and Flow Tool Kit loads its forms by name, which the publisher cannot see.

- **FlowToolKit LWR Support**: drag it into an empty column of the **Theme Footer** (it renders nothing). Every LWR site that shows a Flow Tool Kit form needs it once. Without it the page fails to load (LWR3008).
- **Custom section components** a form names need their own support component beside it (build-custom-lwc ships one; the fallback script's `lwr-support` adds to the same one).
- **Publish** after every deploy, every change to the form or the page, and every Flow Tool Kit upgrade. Experience Builder's preview can look right while the live site still serves the last published version.

Aura sites load components on request and need none of this.

## Who uses it on a site

| Audience | What they get | What to set up |
|---|---|---|
| **Portal members** (signed in) | The form, editable on records they may edit, read only on the rest | Form (Flow User) for the package's Apex; Read and Edit on the object and the form's fields in the org's own portal permission set; the record shared to them through a sharing set (records tied to their Contact or Account) or a sharing rule |
| **Guests creating a record** (Contact Us, signup) | An empty form; Save creates the record, then the confirmation | Form (Flow User); Read and Create on the object and Edit on the form's fields, in a permission set for the site's guest user; the site's default guest record owner set. **flow-access-fix** sets this up and checks it end to end; **sf-guest-audit** then reviews everything the guest user can reach |
| **Guests viewing a record** | The form, read only, as a display of the record | Form (Flow User); Read on the object and the form's fields; a read-only guest sharing rule for exactly the records the page should show (flow-access-fix proposes the narrowest one) |
| Staff viewing the site | As on a Lightning page: editable when they may edit the record | Their usual staff permission sets |

A guest never edits an existing record: Salesforce does not let a guest hold Edit on records, and the form renders read only for a guest whenever there is a record.

A guest sharing rule makes the records it covers readable by anyone on the internet. Share only the records the page must show, by criteria, and only the fields the form needs through field access.

## Check it on the site

Never check a site as an admin in Builder. In a headless browser in Claude Code (build-site-pages' render check loads the published page logged out), or by the person:

1. A create form, as a guest in a new private window: fill it in, Save, see the confirmation (or the page it goes to), then find the record (`sf data query -q "SELECT Id, CreatedDate FROM <Object> ORDER BY CreatedDate DESC LIMIT 1"`).
2. A record page, as a portal member: change a field, Save, reload: saved. As a member who may only read the record: read only.
3. A record page on a public site, as a guest: read only, showing the record's values.
4. On an LWR site, a page that fails to load (the site's error page, LWR3008 in the browser console) or a section that "could not be loaded" means FlowToolKit LWR Support (or the custom sections support component) is missing from the Theme Footer, or the site was not published after the change.
