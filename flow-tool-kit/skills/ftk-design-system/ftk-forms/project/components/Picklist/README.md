# Picklist

A single-choice field in any of FlowToolKit's eight treatments: a dropdown, radio circles, joined buttons, separated buttons, survey cards, a path, an icon rating, or a visual picker.

**Maps to:** a Picklist field and its `picklistType__c`. Hand-written from `flowFormField` (`lightning-combobox`), `flowFormRadioCheckbox`, `flowFormResponsiveChoice`, `joinedChoiceStyles`, `flowFormPathPicklist`, `flowFormVisualPicker` and `separatedButtonStyles`.

| `variant` | Renders | Use it for |
| --- | --- | --- |
| `standard` | `lightning-combobox` dropdown, placeholder "Select an Option" | Long lists, or tight space |
| `radio` | FlowToolKit radio circles, `brand` dot when selected | Two to six short options people should see at once |
| `separatedbuttons` | Gap-separated pills that wrap onto rows. Selected is a `brand` fill, others show `brand` text on white | Short options like ranges, sizes or ratings |
| `surveybuttons` | Full-width stacked cards with a dot. Selected gets a `brand` border on `brand-soft` | One-question-at-a-time surveys and friendly public forms |
| `radiobuttons` | Joined `lightning-radio-group` buttons in one bordered strip. `brand` text; selected is a `brand` fill | Two to five short, parallel options (frequency, yes/no/maybe) |
| `pathbuttons` | SLDS path chevrons. Steps before the choice are complete (`#3ba755` with a check), the choice is current (navy), the rest incomplete (`surface-muted`) | Ordered stages; the package hides the path at phone width |
| `iconbuttons` | A row of `lightning-helptext` icons (default `utility:favorite`). Hovering or focusing an icon shows that option's label in a navy SLDS tooltip; icons up to the choice fill with `iconSelectorColor__c` (default #ffd602) | Ratings, usually 1 to 5, with a label per step |
| `visualpicker` | Bordered boxes that show only a large icon or image. On hover the icon fades to 12% and the bold label appears centered in the box; on phones the label sits under the box instead. Selected gets a `brand` border on a 10% tint and a `brand` icon | A few options that are easier to recognize than read |

## Props
- `label`, `options` (strings, or `{label, value}`), `value` / `defaultValue`, `onChange(value)`.
- `variant`: see the table. Defaults to `standard`.
- `columns`: `picklistColumnsSize__c` for `radio`, `separatedbuttons` and `visualpicker` (default 4, two at narrow widths). `none` (default) wraps options at their own width; a number (or `size_1-of-N`) gives N equal columns.
- `icon`, `iconColor`, `iconSize` (`iconbuttons` only): `iconSelectorIconName__c` (default `utility:favorite`), `iconSelectorColor__c` (default `#ffd602`) and `iconSelectorSize__c` (`small`, `medium`, `large`).
- Option `icon` or `image` (`visualpicker`): `{ label, value, icon: 'utility:home' }`. `captionAlways` (default false) draws the phone layout, with the label under the box instead of the hover reveal.
- `placeholder` (standard only).
- `open` (boolean, standard only): shows the dropdown open for mockups.
- `required`, `readOnly`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`, `focused`: as on `TextInput`.

## Notes
In the package, joined `radiobuttons` collapse to a dropdown at narrow widths and grids collapse to two columns; design the small layout accordingly. In an open dropdown the highlighted option is `brand-tint` and the selected one carries a `brand` check.

## More picklist types
- `columns` also takes `grow` (`picklistColumnsSize__c` = grow), which wraps at content width like `none`.
- `prepend` / `append` draw under the options at either end, the way the package labels the ends of a survey scale.
- Not drawn: grouped options (`comboBoxGrouped`) and the builder-only selector types (`iconselector`, `emailtemplateselector`, `imageassetselector`, `stylesheetselector`), skipped in #959.
