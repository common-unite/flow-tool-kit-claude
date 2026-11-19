# Divider

A titled rule between parts of a page: Form (Header) placed on the site with Display as Divider on, in any of its twelve Divider Styles.

**Maps to:** `header` (Form (Header)) with `displayAsDivider` true. It draws through `formSectionDivider`, the same divider FlowToolKit forms use. The preview is the package's own component.

| Prop | Builder property | Values |
| --- | --- | --- |
| `dividerStyle` | Divider Style | `line`, `compact`, `centered`, `label`, `bookmark`, `ornament`, `pill`, `chevron`, `double`, `icon`, `fade`, `tag` |
| `title` | Title | text |
| `subtitle` | Subtitle | text |
| `iconName` | Icon Name | any SLDS icon name, such as `utility:knowledge_base` |
| `richText` | Rich Text | rich text under the divider |
| `topMargin` | Top Margin | `slds-m-top_none` to `slds-m-top_xx-large` |
| `bottomMargin` | Bottom Margin | `slds-m-bottom_none` to `slds-m-bottom_xx-large` |

The divider's colors follow the site brand. Use it inside a column, between blocks or above a form; don't use it as a block heading, which every block draws itself.

## On LWR

The same component (`FlowToolKit:header`) with the same settings. In an LWR column it is spaced like any other component.
