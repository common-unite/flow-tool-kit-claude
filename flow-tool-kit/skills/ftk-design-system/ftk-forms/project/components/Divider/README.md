# Divider

A section divider in any of FlowToolKit's 12 divider styles, used on its own as a divider section or as a section's header.

**Maps to:** `formSectionDivider` and `Divider_Style__c`. As its own section it is `sectionType__c` = `dividerSection`; as a header it is `Header_Display__c` = `Divider` on any section (use `Section` with `headerDisplay="Divider"`, which draws this component). Hand-written from `formSectionDivider` and `header`.

| `variant` | Builder label | Draws |
| --- | --- | --- |
| `line` | Simple Line (default) | One rule. No label or subtitle |
| `compact` | Compact (icon + label) | Icon and label, then a rule that fades out |
| `centered` | Centered Label | Rule, label, rule |
| `label` | Caps Label + Rule | Label left, rule trailing |
| `bookmark` | Bookmark | A `brand` tag with a notched right edge, into a rule |
| `ornament` | Ornamental Dots | Three dots with the label under them; an icon replaces the middle dot |
| `pill` | Pill Label | A `brand` pill centered on a rule |
| `chevron` | Chevron Flank | Rule, chevron, label, chevron, rule |
| `double` | Double Rule | Label left, two stacked rules trailing |
| `icon` | Centered Icon | Label above, the icon in a tinted circle between two rules |
| `fade` | Gradient Fade | Label above a rule that fades out |
| `tag` | Tag | A rounded tinted tag with a dot (or the icon), into a rule |

## Props
- `variant`: see the table.
- `label`: keeps the case it is typed in; type capitals for the caps look.
- `subtitle`: centered under `centered`, `ornament`, `pill`, `chevron` and `icon`; indented to the label under the rest. `line` never shows one.
- `icon`: an SLDS icon name such as `utility:location` or `standard:contact`, drawn in the icon color.
- Theme overrides: `brandColor` (`brandColor__c`), `borderColor` (`borderColor__c`, the rules), `labelColor` (`headingFontColor__c`), `iconColor` (`headingIconColor__c`), `subtitleColor` (`headingSubtitleFontColor__c`), `ruleSize` (`borderSize__c`, px; default 2).

## Notes
Defaults: rules `divider-rule`, label `heading`, subtitle `divider-subtitle-text`, fills and icons `brand`. Below 320px of width the gaps and tracking tighten and subtitles stop indenting.
