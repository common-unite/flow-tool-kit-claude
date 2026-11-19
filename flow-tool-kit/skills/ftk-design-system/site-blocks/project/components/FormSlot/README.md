# FormSlot

Where a form or another FlowToolKit component sits in a column, drawn as the real form.

**The Forms design system owns how forms look.** Design the form there: __FTK_FORMS_DESIGN_SYSTEM_URL__. Its bundle ships inside this one, taken from the same repository at build time, and Form Slot draws the form with it under the Forms system's own tokens. When the Forms system changes, this system is rebuilt and republished; the bundle records the Forms bundle's hash so a stale copy shows.

**Maps to:** the component placed in the column on the site: a Form Template (`formTemplate`), a Flow with FlowToolKit screens, a Record Card form, or another FlowToolKit component.

| Prop | Notes |
| --- | --- |
| `form` | The form's name as the client knows it: Contact Us, Volunteer Application. |
| `kind` | `Form Template`, `Flow`, `Record Card form` or `FlowToolKit component`. |
| `component` | The Forms design system card that draws it, such as `FormTemplate`, `FormTemplatePages` or `FormTemplateReview`. |
| `description` | One line on what the form asks. |
| `formProps` | Props for a site form, such as `{ title }` for Contact Us. |
| `componentProps` | With `component`, draws that Forms component (`FTK[component]`) with these props, for any other form. |
| `formStyle` | A saved Form Style's values, as the Forms `FormStyle` takes them, for the client's look. |
| `frame` | `true` draws the labelled frame instead of the form. |
| `height` | The frame's height in pixels, when the frame is drawn. |
| `href` | A different link, such as a client's own form design. |

## Site forms drawn by name
- **Contact Us** (`ContactUsForm`): a one-page Form Template, usually in the 8 of an 8/4 Section beside a Callout with how to reach the team.
- **Volunteer Application** (`VolunteerApplicationForm`): a four-page Form Template on its first page, full width or in an 8.
- **Grant Application** (`GrantApplicationForm`): a Stages Mode Form Template on its overview, on an application's record page.

Any other form draws the labelled frame, unless `component` and `componentProps` name a Forms component to draw it with.

## SLDS
`slds-file-selector__dropzone` (the dashed frame), `slds-grid_vertical`, `slds-badge`, `slds-text-heading_medium`, and the form's SLDS icon.

## On LWR

A form draws the same on both site types. An LWR site that shows a FlowToolKit form needs **FlowToolKit LWR Support** in its Theme Footer, then a Publish: the LWR publisher bundles nothing that is only loaded on demand.
