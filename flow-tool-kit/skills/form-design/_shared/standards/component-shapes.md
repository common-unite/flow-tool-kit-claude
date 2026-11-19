# Component shapes: metadata, record or JSON

Every skill that finds, designs, builds or binds a form's questions follows this page: org-catalog (it reports each shape and recommends one), form-design (the plan records the chosen shape), build-form-component (it builds all three) and build-template (it builds or binds each shape the plan names).

## The words

- A **Form Template** is the whole form, end to end: its pages, sections, header, settings and emails. A template is built for one form; it is not what gets reused.
- A **Form Component** is a block of questions that belong together, or of design and display content (Contact Details, Mailing Address, one Household Member, a satisfaction scale, a header). A **table** is a form component too, stored the same way; it renders through the Table component instead of the Flow Form component. A **Repeater** is not a component: it is a page section type, and a flow screen component, that repeats a form component. **Reuse is about components**: the same component placed in the sections and Repeaters of many Form Templates, in flows and on Lightning record pages.
- A form's questions are stored in one of **three shapes**. The shape decides where the questions live, who can change them, and how far one change reaches.

## The three shapes

| Shape | Stored as | Built how |
| :- | :- | :- |
| **Metadata** | Custom metadata: a Form (`Form__mdt`) with its sections, fields and conditional logic records. A page section names it by its API name | Files in a project folder, deployed with the Salesforce CLI (Claude Code). Version controlled, and deployable to every org |
| **Record** | A Form Component record (`Form_Component__c`) of record type Record Component (`Record_Component`). A page section names it `<Name>_v0` | Data, right in the org, through the package's import or Form Builder. No metadata deploy |
| **JSON** | Questions attached directly to one place: a page section's own form (stored in the section's Form Config JSON), the form component inside a flow, or a dynamic form component on an Experience Cloud page | Written into that one place |

A Form Component row of record type Metadata Component (`Metadata_Component`) only tracks a metadata component; it is not a fourth shape.

### JSON (the default)

Use for **every new section unless reuse is known at design time**: the questions are written right on that section. It is the easiest shape to build and change, and it cannot conflict with a shared component, because a change to any shared component never reaches it. It is also the shape when the questions **must stay fixed to that form, section or page** ("this page should always have only this").

- Trade-off: every edit is made in each place that carries the JSON. That is no cost while one place uses the questions. When the same questions turn out to be used in other places later, the repeated JSON sections are merged into one shared component then (consolidate-sections, a planned skill); nothing is made shared up front on a guess.

### Record components

Use when **reuse is known at design time**: the same block of questions is placed in more than one section, Repeater, Table or form, and the plan says so before anything is built. One form can be enough: a Contact block asked once as "Who is your main support contact?" and again inside a Repeater for additional contacts is one record component, and both the section and the Repeater reference it. It is built right away, straight in the org with no deploy, and every place that uses it names it. A record component is shared across flows, Form Templates and Lightning record page forms; it is not in metadata, so it is not version controlled and does not deploy with the project.

- Trade-off: it moves between orgs by Export and Import, not by deploy. Guests on a public site see it only through a guest sharing rule on Form Component (Read, where the record type is Record Component).
- Creating one through the package's import needs Flow Tool Kit 5.3 or later.

### Metadata components

Use when a shared component is **final** and should live in version control: one deployed update reaches every Form Template, flow and Lightning record page form that uses it, and the component deploys to every org with the rest of the project. New work does not start here: a prototype's record components and JSON sections become metadata through convert-to-metadata once they are final, or a component is built as metadata from the start only when the person asks for it.

- Trade-off: a change is a deploy. It needs Claude Code (or another way to deploy metadata), and the Form Builder platform cache must be reset after each deploy (**Reset Form Cache**).
- In claude.ai chat there is no deploy. Say so in one line and ask whether to build it as a record component now (it is shared the same way) or wait for Claude Code.

## Which shape to recommend

Work through these in order and stop at the first that fits:

1. **The block is reused as it is.** It keeps the shape it already has; there is nothing to choose.
2. **The block extends an existing component** (a new version of it): the original's shape. A new version of a metadata component stays in metadata, and of a record component stays a record.
3. **The block is new and its reuse is known at design time**: the plan places the same block in more than one place (a section and a Repeater on one form, several sections, or several forms), or the catalog shows the same questions already built in place on other templates that this work will join. Recommend **one record component**, built right away and referenced by every place that uses it.
4. **Otherwise: JSON on the section.** It is the easiest, and it cannot conflict with a shared component. A shared shape is never recommended on a guess that other places might use it one day; reuse found later is consolidated then.

Metadata is not recommended for new work. Offer it as the alternative when the person keeps forms in source control, and point to convert-to-metadata for when the work is final.

## Ask; never decide silently

The shape is the person's choice. Recommend one, give the reason in a few words, name the alternatives, and ask. Put it in the same message as the reuse, extend or new question, one numbered item per section:

> 3. 'Main support contact' and the 'Additional contacts' Repeater ask the same questions. I recommend one **record component**, Support_Contact, built now: the section and the Repeater both reference it, so one change reaches both. **JSON** on each would mean two copies to keep in step, and **metadata** can come later through convert-to-metadata once the form is final. Record, JSON or metadata?
>
> 4. 'Volunteer availability' is new, and nothing else in the plan asks it. I recommend **JSON on this section**: it is the simplest to build and change, and no shared component can change it. If other forms come to ask the same questions, they can be merged into one shared component then. A **record component** if you already know another place will use it. JSON or record?

- No answer means no shape. The next skill stops on that section until the person chooses; it never fills in its own default.
- Record the recommendation, the reason and the answer (form-design's `plan.json`: `shape` and `shape_asked`).
- Changing a component's shape later (record to metadata, JSON to a shared component) is a new decision with its own question, because it changes who can edit the questions and what one change reaches.
