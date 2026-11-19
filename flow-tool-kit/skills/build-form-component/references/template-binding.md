# How a page section draws a component

build-template writes the page sections; this page is what a component author needs to know about them, so the component works where it is placed.

## The page section fields that matter

- **`Component_Type__c`** (required, default `Field Set`): `Field Set` (one record), `Repeater` (repeated rows), `Table` (an editable table), `Flow` (a Flow Section, built by build-flow-section), `Lightning Web Component` (built by build-custom-lwc), `Display Text` (rich text only).
- **`FormQualifiedApiName__c`**: the component a Field Set, Repeater or Table draws. A record component is named `<Name>_v0`; a metadata component by its name (`FlowToolKit__` is added automatically only in an org that has its own namespace). Ignored for Flow, LWC and Display Text.
- **`FormConfigJSON__c`**: the section editor's wrapper, `{"formSelectionMode": "component" | "custom", "object": "...", "formQualifiedApiName": "...", "formJsonConfig": "..."}`. In `component` mode the wrapper's name wins over the column; in `custom` mode the inline JSON is drawn in the browser with no lookup. Empty: the column's name is used.
- **`Form_Component__c`**: a lookup kept for reference; the form never reads it.
- **Table sections**: `Alternate_FormQualifiedApiName__c` (the row's New and Edit form), `Bulk_FormQualifiedApiName__c` (editing several rows).
- **Repeater and table sections**: `Min__c`, `Max__c`, the New, Edit, Clone and Delete actions with their labels, `Repeater_Record_Spacing__c`, `Repeater_Hide_Divider__c`, `Prefill_Template__c` (default rows), and `Section_Tag__c` (the stable id a prefill flow uses to put rows in this section).
- **The header**: `Show_Header__c`, `Header_Title__c`, `Header_Subtitle__c`, `Header_Icon_Name__c`, `Header_Style__c`, `Section_Frame__c`, `Divider_*`. This is where a shared component gets a form-specific header.
- **`Component_Section_Text__c`**: the body of a Display Text section, or text above the form otherwise (`{{merge}}` tokens allowed).

## How a name resolves

1. The template reads each page section and draws it by `Component_Type__c`.
2. For a Field Set, Repeater or Table: the wrapper in `FormConfigJSON__c` decides. `component` mode loads by name; `custom` mode draws the inline JSON.
3. A name ending `_v0` loads a **record component**: the newest active Form Component with that `VersionId__c`, with its child records. Any other name loads a **metadata component**: an active `Form__mdt` with that name and its child records, `config__c` included.
4. Configs are served from a platform cache first. After any metadata redeploy, use **Reset Form Cache** in the Form Builder footer, or the old form keeps drawing.

## Rules for components that will be placed

- **Body components are on Form Submission**, or on the record's own object with a Form Template Mapping on the paid edition. A component on another object with no mapping is reported on the Form Template record page: nothing it collects reaches the submission.
- **A header or footer component is on Form Template** and goes in the template's `FormQualifiedApiName_Header__c` or `FormQualifiedApiName_Footer__c`. A record component is named `<Name>_v0` there too; the plain name draws nothing.
- **Public forms read record components as the guest.** Give the guest site's users Read on Form Component records whose record type is Record Component, through a guest sharing rule. Without it a guest gets no header and no shared section, and the console shows `Form VersionId is Not Valid (<Name>_v0)`. Components are designs, never answers, so this exposes nothing a respondent typed.
- **A page section cannot change a component's Form Template Mapping.** When two templates need different targets, use a second component.

## Prefill from records

A prefill flow fills the submission and its repeater or table rows from records it fetched, with the **Form Submission | Prefill From Mapped Record** action. The section's component map decides which fields copy, so the flow carries no field-by-field mapping.

- **Single Record** (default): one call per record (Account, parent Account, Contact), chained by passing each call's Form Submission to the next. Pick the Form Submission lookup the record stands for, so two records of one object use their own sections. A value on the record wins; a blank never clears.
- **Related Records**: pass the collection and the repeater or table section's `Section_Tag__c`. Each record becomes one row; add the action's Related Records output to the flow's `relatedRecords` output.
- **Auto**: for users who may read the source records (internal users, signed-in site users). Set the lookups on the submission and pass only it; the action reads each mapped lookup's record for the fields the user can read.
- Fetch every mapped field in the flow's Get Records: fields not on the passed record are skipped and listed.
- It works for guests: the flow's Get Records runs in the flow's context.
- A section takes part only when its component is on that object and carries a map; custom JSON sections on another object count.

## Records a template creates for you

Inserting a Form Template creates a default page; inserting any page creates a default Field Set section bound to the packaged `Primary_Contact_Default`. A script that builds a template repurposes those records rather than adding beside them, and sets `IsActive__c` true: an inactive template's preview shows "Not Available", which looks like a binding failure and is not. build-template handles this.
