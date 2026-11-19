# ContactUsForm

The Contact Us form clients put on a site's Contact page: one page with name, email, phone, a topic, the message and an opt-in line, sent with one button.

**Maps to:** a one-page Form Template (`formTemplate`, `Form_Template__c`) whose page holds one section. Built from `FormTemplate`, `Section`, `TextInput`, `FormattedInput`, `Picklist` (`separatedbuttons`), `TextArea` and `Checkbox`.

## Props
- `title`, `subtitle`: the section header. Default "Contact us" and the reply promise.
- `submitLabel`: the one button. Default "Send message".

## Using it on a site
The FlowToolKit Site Blocks design system shows this form in its Form Slot (`form: "Contact Us"`), usually in the 8 of an 8/4 Section beside a Callout that says how else to reach the team. Wrap it in `FormStyle` with the client's saved Form Style for their look.
