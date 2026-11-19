# Listings, record pages and forms on a page

## A listing is a repeater, not a block

A list of records (programs, plots, events) is a Form (Dynamic Repeater) showing each record as a card. In `page.json` it is an item of kind `repeater`:

```json
{"kind": "repeater", "object": "Program__c", "cardType": "photoOverlay", "columns": 3, "pageSize": 6,
 "card": {"title": "{{Name}}", "eyebrow": "{{Season__c}}", "imageSource": "url", "imageUrl": "{{Photo__c}}", "link": "/program/{{Id}}"},
 "filter": {"conditionType": "AND", "conditions": [{"position": 1, "fieldApiName": "Status__c", "operator": "eq", "value": "Open"}]},
 "sortField": "Start_Date__c", "sortDirection": "ASC", "emptyMessage": "No programs are open right now. Check back in the spring."}
```

- The generator writes the repeater's settings as the component stores them: an inline form on the object with one record card section, the card as a JSON string inside it, and the column counts (`columns` on desktop, at most 2 on a tablet, 1 on a phone).
- Card slots take `{{Field}}` and parent paths (`{{Account.Name}}`). `link: "/{{Id}}"` style links resolve to the object's page on the site.
- A repeater without `object` and `card` stops the build, naming its section: a listing drawn only from sample records would otherwise vanish from the page.
- A color set on the repeater (`brandColor`, `accentColor`) reaches every card.
- **Blank numbers.** A `$number.` or `$currency.` token turns a blank into 0, so an unset price shows `$0.00`. A text formula on the object (`IF(ISBLANK(Price__c) || Price__c <= 0, "", "$" & TEXT(FLOOR(Price__c)))`) shows nothing instead.
- On the free edition, a block or card bound to a record of any object other than Account, Contact, Case, Lead or Form Template shows a notice instead of its content. Check the edition in `flow-tool-kit.json` before designing a listing on a custom object.
- Guests need read access to the object and every field a card shows, and a guest sharing rule that shares the records ([guest-access.md](guest-access.md)).

## Record pages (LWR)

`--record-object <Object>` builds the page as that object's record page.

- **Three routes go together.** Builder deploys an object page only with its detail, list and related-list routes. The generator fills the detail view with the design, keeps a list or related-list route the site already has, and writes a missing one with a one-block stub page.
- **Route names follow Builder.** A standard object's routes are keyed by its record Id prefix (`detail-001` for Account), a custom object's by its API name (`detail-Program__c`). The key comes from the object's route in the site, then the built-in standard objects (Account, Asset, Contact, Opportunity, Case), then `--record-prefix` (the first three characters of one of its record Ids), then a custom object's API name.
- **Page titles are unique across the site.** A record page titled "Home" is refused; pass `--title`.
- **Bindings.** Every record-bound component reads `{!Route.recordId}`. LWR rewrites the address to `/<prefix>/<record Id>/<slug>`.
- **A repeater of the page record's children** filters on the lookup with value `{!recordId}`. Builder expands `{!...}` inside a text setting, so the generator stores it escaped and the repeater resolves it at run time. A `{!recordId}` typed into a block's own text (a button link) is left as written.
- A page with no record of its own can still show one record: give the item a `recordId`.

On an Aura site, record pages for Form Templates and Form Submissions come from the packaged **Form Template Detail** and **Form Submission Detail** page variations: create the object pages in Builder from those templates, so every template has its own link and a resume link has a page to land on.

## Forms on a page

- A Form Slot becomes Form (Template) bound to its Form Template's record Id, once the template exists. Until then the generator leaves it out and names it.
- A form saving records for guests needs guest access set up (**flow-access-fix**) and LWR Support in the Theme Footer.
- **Form (Dynamic Component)** on a site shows a success message after each save. To turn it off for one form: in Builder, the component's **Confirmation Settings**, check **Hide Success Messages**, then publish. Error and validation messages still show.
- A form that loads a custom section component also needs that component's support component in the Theme Footer (`--footer-support c:<name>`; build-custom-lwc ships one).

## Navigation

`navItems` becomes the site's default navigation menu. Salesforce refuses a menu item whose page the site does not have, so the generator leaves those out and names them: build the page, then run `--entire-site` again. Deploy the menu after the pages it links to.

## Dividers and standard components

- A divider between chapters is `FlowToolKit:header` with `displayAsDivider: true` and a `dividerStyle`.
- Tabs, Rich Content and the HTML Editor become the LWR standard components; their Aura names are converted.
