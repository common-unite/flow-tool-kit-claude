# Tabset

Shows a form's sections as tabs, one section at a time. A carousel is its own component: see `Carousel`.

**Maps to:** a Flow Form whose `FlowToolKit__type__c` is `default`, `scoped` or `vertical` (flowForm `displayAsTabset`, `flowFormTabset.html`). Each tab is one form section: its label is the section title (markup stripped), its icon is the section's `FlowToolKit__iconName__c`, and a section with invalid fields shows the error indicator (`lightning-tab show-error-indicator`).

| `variant` | Renders |
| --- | --- |
| `default` | `lightning-tabset`: tabs on a 1px rule; the active tab is bold with a 3px `brand` underline |
| `scoped` | Tabs in a `surface-muted` bar over a bordered white panel |
| `vertical` | A 12rem tab rail on the left; the active tab is white with `brand` text. Stacks above the content in containers under 500px |

## Props
- Children: one `Tab` per section: `label`, `icon` (any SLDS name), `invalid`, and the section content as its children. Or pass `tabs: [{ label, value, icon, invalid, content }]`.
- `variant`: see the table. Default `default`.
- `value` / `defaultValue` (the active tab's `value`, default its label), `onChange(value)`.

## Notes
Tabs drop divider sections; put a divider inside a tab's content instead. Arrow keys move between tabs. The real tab labels can't hold rich text, so keep section titles plain when a form uses tabs.
