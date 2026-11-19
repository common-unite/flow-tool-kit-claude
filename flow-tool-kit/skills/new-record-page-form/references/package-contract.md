# The package's form components

Everything this skill places is Flow Tool Kit's own record form. Admins meet it under two names: **Form (Component)** in Lightning App Builder and Experience Builder, and **Form (Dynamic Component)**, its site-only sibling with a richer settings panel. Both load a Form Component built in Form Builder, lay it out in SLDS, validate it and save the record without a Flow. This page lists every setting each one takes on the page and how the record form then behaves, read from the package source (release 5.3 and the 5.4 beta). A setting missing in an org means the org's Flow Tool Kit needs an upgrade.

## Form (Component): `FlowToolKit:lightningRecordForm`

Placed on Lightning record pages, app pages, the Home page and Experience Cloud pages (Aura and LWR). Its settings differ by page type: **R** a Lightning record page, **S** a site page, **A** an app or Home page.

| Setting (API name) | On | What it does |
|---|---|---|
| Form Qualified Api Name (`formQualifiedApiName`) | R S A | The Form Component to show: a record component by its version name, `<Name>_v0`; a metadata component by its plain name. On app and Home pages it is a picklist of the org's components |
| Record Id (`recordId`) | S | The record the form loads and saves. `{!recordId}` on a record page (Aura and LWR; `{!Route.recordId}` also works on LWR). Blank: the form creates a new record. On a Lightning record page the page supplies it |
| Form Object Api Name (`objectApiName`) | S A | The object the form is built on. Defaults to `{!objectApiName}` on a site page, which a page with no record does not pass: type the object (such as `Case`) there. On a Lightning record page the page supplies it |
| Confirmation Message (`confirmationMessage`) | S | Rich text shown after a new record is inserted, in place of the form |
| Read Only (`readOnly`) | R S A | Shows the record without allowing edits: every input disabled, and the form never creates a record, so it needs no Create on the object. With no record it renders the empty form, disabled |
| Hide Save Button (`hideButtons`) | R S A | Hides the Save button |
| Read only when the user cannot edit the record (`checkRecordAccess`) | R S A | On by default. Reads once whether the running user may edit the page's record, and renders it read only, with no buttons, when they may only read it |
| Hide Headers (`hideHeaders`) | R S A | Hides every section header in the form |
| Margin-Bottom (`bottomMargin`) | R S A | Space under the component, an SLDS margin from none to xx-large |
| Display buttons in docked footer (`dockedButtons`) | R S A | Puts the buttons in a footer fixed to the bottom of the view |
| Button Alignment (`buttonAlignment`) | R S A | Left (`start`), Center (`center`) or Right (`end`, the default) |
| Button Label (`buttonLabel`) | R S A | The Save button's text. Default "Save Record" |
| Prefill Values (`prefillObject`) | S A | JSON of field and value pairs that prefill a new record, such as `{"Origin": "Web"}` |
| Stamp FormQualifiedApiName On Save (`stampFormQualifiedApiName`) | R S A | When the object has a `FormQualifiedApiName__c` field, saves the form's name into it |
| Edit Related Record (`isAlternativeForm`) | R S | Edits the record this page's record looks up to, instead of the page's own. Name the lookup in Lookup Field API Name and pick a form built on that object |
| Lookup Field API Name (`relatedFieldApiName`) | R S | The lookup to follow, such as `AccountId` on a Contact page, or a path through a parent (`Account.ParentId`). A path starting with `User.` walks from the signed-in user instead and needs no Edit Related Record: `User.Contact.AccountId` shows a portal member their own Account |

The record form has a few more properties that are not settings on any page (`autoSave`, `formJsonConfig`, `themeOverrideName`, `hideSuccessToast`). Only a component that places the record form in its own template can set them: the fallback component below.

## Form (Dynamic Component): `FlowToolKit:lightningRecordFormDynamicDisplay`

Experience Cloud pages only (Aura and LWR). It takes **Record Id** (default `{!recordId}`), **Object Api Name** (default `{!objectApiName}`) and **Configure Flow Properties** (`properties`): one JSON string its own settings panel writes. In source, the keys are:

| Panel setting (keys) | What it does |
|---|---|
| Form Component Settings (`object`, `formSelectionMode`, `formQualifiedApiName`, `formJsonConfig`) | The object, then either a saved Form Component by name (`formSelectionMode: "component"`) or the form's JSON held in the setting itself (`"custom"`, with `formJsonConfig`). Custom JSON keeps the form in the site's source with no Form Component record in the org |
| Display Type (`displayType`) | `component` shows the form on the page; `button` and `modal` show a button that opens it in a modal |
| Read Only (`readOnly`) | As on Form (Component) |
| Survey Mode (`surveyMode`) | One question or row at a time, with more spacing and automatic advance for single-choice answers |
| Button and modal (`openModalButtonLabel`, `modalButtonAlignment`, `modalButtonVariant`, `buttonColor`, `modalButtonIcon`, `modalSize`, `hideModalHeader`) | For the button and modal display types: the opening button's label, alignment, variant, color and icon, and the modal's size (small to full) and header |
| Theme Override (`themeOverrideName`) | A Form Builder theme in place of the form's own |
| Enable Save Actions (`hideButtons`, inverted) | Off hides the Save button, for a form that only displays or only filters |
| Button Label, Button Alignment, Action Color, Dock Buttons (`buttonLabel`, `buttonAlignment`, `brandColor`, `dockedButtons`) | The Save button's text, alignment and color, and the docked footer |
| Confirmation Settings (`confirmationMessage`, `hideSuccessToast`) | The rich text shown after a new record is inserted; Hide Success Messages stops the success toast after a save (error and validation messages always show) |
| Auto Navigate (`autoNavigate`, `autoNavigationType`, `pageApiName`, `webPage`, `listObjectName`, `listFilterName`) | After a save, go to the record (`record`), a site page by its API name (`experience`), a web address (`webpage`) or an object's list view (`list`) |
| Style (`minHeight`, `horizontalPadding`, `verticalPadding`, `topMargin`, `bottomMargin`, `borderColor`, `borderColorOpacity`, `borderWidth`, `borderRadius`, `backgroundColor`, `backgroundOpacity`) | The box around the form |
| Live Filter Source (`filterSourceId`) | Lets this form's fields filter the records of a Form (Dynamic Repeater) on the same page |
| Visibility (`visibility`) | Shows the form only when a rule on the page's record holds |
| Record Context (`relatedFieldApiName`) | Parent Field Api Name: as Lookup Field API Name on Form (Component) |

It always checks record access (as `checkRecordAccess` on) and stamps the form's name on save.

## Which one where

| Page | Use |
|---|---|
| Lightning record page | Form (Component) |
| Lightning app or Home page | Form (Component), with Form Object Api Name set |
| Experience Cloud page, record or not | Form (Dynamic Component) for most site forms: the object picked in the panel, a confirmation or a page to go to after a save, button or modal display, a visibility rule, custom JSON. Form (Component) also works, and suits a page that needs Prefill Values |

## Create or update

- **A record on the page** (the page's record, a bound Record Id, or a lookup followed): the form loads it and saves changes to it.
- **No record**: the form is empty and Save creates a new record of its object, then shows the confirmation message, goes where Auto Navigate says, or (for staff, with neither set) opens the new record.
- A form never deletes a record.

## Who sees what

| Running user | What they get |
|---|---|
| Can edit the record | The form, editable, saving on Save |
| Can read but not edit the record (sharing, or no Edit on the object) | The form, read only. With the access check on (the default) the record form asks once (an Apex call); without it, a user with no Edit on the object still gets read only, but a user blocked only by sharing would see an editable form whose saves fail |
| Can neither create nor edit records of the object | Always read only |
| Cannot read the object's fields | "You do not have permission to view ... records." instead of the form |
| Cannot read a particular field | That field is left out of the form |
| A site guest, with a record | The form, read only: a guest never edits a record. No Apex call is made for the check |
| A site guest, with no record | An empty form that creates the record on Save, then the confirmation message. A guest cannot read the new record back, and the form treats that as a success |

## Autosave (only through the fallback component)

Autosave is a property of the record form, not a setting on either page component, so it needs the small component this skill's script writes. With it on:

- A change saves only when the whole form is valid. A required field left blank, or a value that fails a rule, holds the save until it is fixed.
- A typed field (text, number, email, phone, currency) saves about a second after the person stops typing. A picklist, checkbox, date or lookup saves at once.
- Only the fields that changed are sent, with no success message. A failed save shows the error Salesforce returns.
- It updates an existing record only and never creates one. A site guest never saves.
- The Save button is hidden (`hide-buttons`), since nothing is left for it to do.

## What the fallback component hands the record form

The component `scripts/record_page_form.py write` produces places `<flowtoolkit-lightning-record-form>` (the package namespace, a hyphen, then the component name in kebab case) and sets:

| Attribute | Default | With `--autosave` | What it does |
|---|---|---|---|
| `record-id` | The page's record | Same | Loads the record and saves to it |
| `object-api-name` | The form's object, fixed in the component | Same | Fixed rather than taken from the page, because a site page does not always pass it |
| `form-json-config` or `form-qualified-api-name` | The baked form, or a Form Component's name | Same | Baked JSON must name its object (`ObjectApiName__c`; the script adds it) and be JSON the org saved: hand-written JSON lacks the version and section layout keys a save adds, and renders with the wrong field widths |
| `check-record-access` | On | On | The access check above |
| `auto-save` | Off (not set) | On | Saves each valid change as it is made |
| `hide-buttons` | Off (not set): the Save button shows | On | No Save button; autosave does the saving |

## What it needs in the org

| Need | Granted by |
|---|---|
| The package's Apex for the form (its layout, styles, defaults, the access check) | The package's permission sets: **Form (Flow User)** for portal members and guests, **Form Builder Internal User** (or Manager, or Admin) for staff |
| Read on the object and every field the form shows; Edit on the fields people change; Create on the object for a form that creates records | The org's own permission sets, per audience. A guest's go in a permission set assigned to the site's guest user |
| The record itself | Sharing: the org's sharing model for staff; sharing sets or sharing rules for portal members; a read-only guest sharing rule for a record a guest views |
| Flows the form launches, Form Components it embeds, custom section components | Flows need a grant per audience (flow-access-fix); embedded components must exist in the org; custom sections need build-custom-lwc's support component on an LWR site |

A form loaded by name is served through the package, which on the free edition serves only the objects that edition covers: Account, Contact, Lead, Case, Campaign, Campaign Member and the package's own objects.

## Errors the person may see

| Message | Cause |
|---|---|
| "You do not have permission to view ... records." | No read on the object or any of its fields |
| "Get Record Value(s) Error" | The record cannot be read: sharing, or a site page whose Record Id is not bound |
| "No form assigned yet" or "Oops! No object assigned" (Form (Dynamic Component)) | No form picked in the panel, or no object |
| The component shows nothing | No form named, the JSON names no object, the form has no sections, or the page passes neither a record nor an object |
| "... Object Is Not Available Within the Free Version" | A form by name on an object the free edition does not cover |
| A save error naming a field | A validation rule, required field or duplicate rule on the object; the form shows Salesforce's own message |
