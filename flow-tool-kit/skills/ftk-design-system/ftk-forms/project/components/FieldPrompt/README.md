# FieldPrompt

A tip that appears above a field while someone is answering it.

**Maps to:** `fieldPrompt__c` on a form field, drawn by `flowFormPrompt`, with `promptDisplayType__c` (`prompt` | `richtext`), `promptDisplayValue__c` (`custom` | `helptext`), `promptColor__c` and `promptFontColor__c`. Hand-written from `flowFormPrompt`.

| `displayType` | Renders |
| --- | --- |
| `prompt` | An SLDS popover with a bottom-left nubbin pointing at the field, white by default |
| `richtext` | Plain rich text above the field |

## Props
- `message` (text) or `html`; `field`: the field the prompt belongs to, drawn under it.
- `displayType`: see the table. `color` and `fontColor`: the theme's prompt colors.

## Notes
Prompts show while the field has focus, or always when the user has turned prompts on from the form's prompt toggle. `promptDisplayValue__c` = `helptext` reuses the field's help text as the prompt.
