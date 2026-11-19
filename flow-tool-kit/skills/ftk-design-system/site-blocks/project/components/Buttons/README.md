# Buttons

The calls to action a block draws in its Buttons pane: Brand, Accent, Outline, Light, Link and the full-width Panel, opening a link, a Form Template, a Flow or a record form.

**Maps to:** keys on any block, not a component of its own. The preview draws them on a bare Steps block so they are seen alone. Use them through a block's props: `<Hero buttons={...} />`.

## Each item in `buttons`

| Key | Label | Values |
| --- | --- | --- |
| `label` | Label | richtext |
| `description` | Subtitle | text |
| `type` | Type | `url`, `formTemplate`, `formSubmission`, `flow`, `recordForm` |
| `url` | URL | text |
| `target` | Opens In | `same`, `new` |
| `templateId` | Fallback Form Template | combobox |
| `flowApiName` | Flow | flow |
| `recordSource` | Record | record |
| `formMode` | Mode | `edit`, `readOnly` |
| `recordField` | Lookup Field | recordLookup |
| `formQualifiedApiName` | Form Component | formComponent |
| `modalWidth` | Modal Size | `small`, `medium`, `large`, `full` |
| `modalHeader` | Modal Title | text |
| `modalSubheader` | Modal Subtitle | text |
| `style` | Style | `brand`, `light`, `accent`, `outline`, `link`, `panel` |
| `backgroundColor` | Background Color | color |
| `textColor` | Font Color | color |

## Settings

| Prop | Property Editor | Values |
| --- | --- | --- |
| `buttonAlign` | Buttons: Button Alignment | `left`, `center`, `right` |
| `buttonsGap` | Buttons: Space Below Buttons | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

## On LWR

The same keys draw the same part on an LWR site; see the Block card for where LWR differs.
