# RichText

Read-only content on the form: instructions, headings, lists and message cards.

**Maps to:** a Rich Text block (`flowFormRichText`, a rich text section or page text, `Header_Text_Variant__c`). Hand-written from `flowFormRichText`.

| `variant` | Renders |
| --- | --- |
| `default` | Rich text on the field edge, 13px |
| `highlight` | A 4px `brand` rule on the left |
| `info`, `warning`, `error`, `success` | A message card: 8% tint of the accent, 5px accent edge, white icon tile with `utility:info`, `warning`, `error` or `success`. Info uses the SLDS info color (`--slds-g-color-info-base-40`, #5c5c5c, the grey of `slds-theme_info`). The package falls back to the brand only where SLDS 2 hooks are missing |

## Props
- `html` (a rich text string) or `children`.
- `variant`: see the table. Default `default`.

## Notes
Merge fields like `{!Account.Name}` resolve in the package; write sample values in a design. A rich text block can also carry a Flow button (`flowApiName`), which is not drawn here.
