# The house pattern: the admin's form, plus behavior

A custom section component does not draw the fields. The fields stay in Form Builder, where an admin changes them without a deploy; the component adds only what is genuinely code: a calculation, a rule, a picker over data the form cannot list, a widget Flow Tool Kit has no control for.

Every `lightning-input` you write by hand throws away what the admin already configured: labels, help text, widths, order, picklist display, conditional logic, theme, translations and required-field checks. It also moves the field list into JavaScript. `scripts/check_lwc.py` warns on hand-built inputs for that reason; mark the template with `<!-- custom-lwc: allow-inputs -->` only for a widget with no Flow Tool Kit control at all (a map, a signature pad, a third-party picker).

## On a page section: render the section's form inside the component

The package's form is exposed to your org as `<FlowToolKit-flow-form>`. Render the form the page section names, inside your component:

```html
<FlowToolKit-flow-form
        is-extension
        data-section-form
        form-j-s-o-n={sectionFormConfig}
        form-qualified-api-name={sectionFormName}
        object={objectApiName}
        record={formRecord}
        transformation-record={derivedValues}
        review={review}
        disable-all={disableAll}
        onrecordchange={handleFormRecordChange}>
</FlowToolKit-flow-form>
```

| Attribute | Why |
|---|---|
| `is-extension` | The form reports each edit as a plain `recordchange` event carrying its whole record, instead of the Flow event it uses on a screen. Without it your component hears nothing |
| `form-qualified-api-name`, `form-j-s-o-n` | The section holds its form in either `FlowToolKit__FormQualifiedApiName__c` (a named form component) or `FlowToolKit__FormConfigJSON__c` (a form saved on the section, or a wrapper naming one). Pass both, read from `section`; the form works out which to use, as the package's own Field Set sections do |
| `object`, `record` | The submission it edits. Pass a **copy** of `record`, replaced only when a field value differs (treat `null` and `undefined` as equal). The admin's section preview rebuilds the record on every broadcast; handed straight through, the form reruns its rules, broadcasts again and the page freezes |
| `transformation-record` | Values your code derives, keyed by field API name. The form writes each one that differs from what it holds, so a read-only Plot Fee field placed on the admin's form shows your total. Assign a **new object** for each change; the form ignores values that arrive before it has rendered |
| `review`, `disable-all` | So the admin's form is read-only when the section is |
| `onrecordchange` | Pass each field that changed on to the host as one `formfieldchange` (compare with `record`, send only the differences), and call `event.stopPropagation()` |

`validate()` on your component calls the form's own `validate()` first, so the admin's required-field checks still block the page, then adds any rule only your code knows.

**The form inherits the template's styles by itself.** When it connects, the package's form asks the nearest Flow Tool Kit style owner for its styles with an event that crosses shadow boundaries; the Form Template (or, on a Form Component section, the surrounding form) answers. Every input, label, section and button inside then follows the template's Form Style settings and theme with no code from you. Anything else you draw uses the style variables: [style-variables.md](style-variables.md), Matching the form's look.

### Giving the section its form

The page section editor hides its form picker once Component Type is Lightning Web Component, and the form stays on the section when the type changes. So:

- **By hand:** on the section's Component tab, leave Component Type on **Field Set**, choose the form (or build it in the section's own Form Builder), then switch Component Type to **Lightning Web Component** and enter the component name. The form is kept.
- **From this skill:** `python3 scripts/point_section.py --section <Id> --component c:<name> --form <Form_Component_API_Name> --org <org-alias>`, or `--form-json <file>` for a form built as JSON for this section alone. It writes exactly what the editor writes. Without `--org` it prints the values for a Salesforce connector to save.
- **The form itself** is built by build-form-component from the section's design in `plan.json`: the plan's `custom-lwc` section carries the questions; this skill builds only the behavior.

## On a Form Component section: sit beside the admin's sections

A Form Component section has no section record, so there is no form to render. The admin's questions are the form's other sections, and your component's `record` is the whole form's record, kept current as the person answers. Place the component's section under the sections whose answers it uses, read them from `record`, and write derived values back with `formfieldchange`. The worked example does both: it renders the section's form when `section` names one, and otherwise shows only its card.

## Derived values

- **Shown to the person:** put the field on the admin's form as read-only and send the value through `transformation-record` (page sections), so it renders where the admin placed it, styled like every other field.
- **Saved on the submission:** send it with `formfieldchange` too. On a Form Component section that is the only channel.
- **Send only a change.** The form hands every value back down; compare with `record` and with the last value you sent, or the component loops. The worked example's Jest test fails if the guard is removed.
- **Never derive before your lookup data has loaded** (rates, a roster): an early "no value" overwrites the value already saved.
- **Hidden fields keep their values.** The form restores a hidden field's value, so clearing one through `transformation-record` does not stick; clear it in the conversion if it must not be saved.
- **Never trust a browser value with money or eligibility.** A person can change anything the browser sends. Show the fee here, and recalculate it where it counts: in the conversion flow (new-mapping-flow) or before payment.

## Titles and headers

The page section (or the Form Component section) carries the header, icon, subtitle, intro text, frame and conditional logic. Your component draws no title of its own for the section; a card title inside it, like "Your plot fee", is content, not the section header.
