# SectionHeader

The header every block draws from the same keys: eyebrow (`sectionLabel`), `heading`, `subheading`, an optional highlighted phrase and the Statement style. `siteDesignBlockSectionHeader` draws it.

**Maps to:** keys on any block, not a component of its own. The preview draws them on a bare Steps block so they are seen alone. Use them through a block's props: `<Hero headingAlign={...} />`.

## Settings

| Prop | Property Editor | Values |
| --- | --- | --- |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `headingStyle` | Heading: Heading Style | `standard`, `statement` |
| `headerGap` | Heading: Space Below Heading | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `headingHighlight` | Heading | rich text |

## On LWR

The same keys draw the same part on an LWR site; see the Block card for where LWR differs.
