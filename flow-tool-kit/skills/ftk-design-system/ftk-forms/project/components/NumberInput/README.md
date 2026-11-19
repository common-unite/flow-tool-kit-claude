# NumberInput

A number, currency or percent field, typed or chosen with a stepper, a slider or preset amounts.

**Maps to:** a Number, Currency or Percent field (`flowFormField` drawing `lightning-input` type number with `formatter` currency or percent) and `numberType__c` from `flowFormNumberInput`.

| `variant` | `numberType__c` | Renders |
| --- | --- | --- |
| `standard` | `standard` | A text box. Shows the formatted value ($1,250.00, 35%) and edits the raw number |
| `stepper` | `stepper` | Border-filled `utility:dash` and `utility:add` icon buttons around a centered box |
| `slider` | `slider` | `lightning-slider` in `brand`, with the formatted value at the right |
| `presetamounts` | `presetamounts` | Joined buttons of fixed amounts plus Other; Other reveals a box for any amount |

## Props
- `label`, `value` / `defaultValue` (a number), `onChange(number)`.
- `format`: `number` (default), `currency` (USD) or `percent`. Applies in every variant. Percent values are whole numbers (35 means 35%).
- `min`, `max`, `step`: the field's min and max. Slider defaults to 0 to 100.
- `presets` (`presetamounts`): the amounts in order, e.g. `[25, 50, 100, 250]`. `allowCustom` (default true) adds Other; `customPlaceholder` labels its box.
- `placeholder`, `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
Use `presetamounts` for gifts and fees, a `stepper` for small counts (tickets, people) and a `slider` only when an approximate value is fine. Give the slider's range in the handoff.
