# Cards

A grid of cards, each an icon or photo with a title, copy and an optional link.

**Maps to:** a Form (Design Block) whose `sectionType` is `cards` (Cards in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `CardsProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Rich text. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |
| `description` | Heading: Emphasis Line | Rendered larger, directly under the subheading. |

### Cards (`items`)

A list of cards. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `eyebrow` | Eyebrow | richtext |
| `title` | Title | richtext |
| `description` | Description | richtext |
| `meta` | Footer Note | richtext |
| `labelColor` | Eyebrow Color | color |
| `valueColor` | Title Color | color |
| `link` | Link | text |
| `target` | Opens In | `same`, `new` |
| `linkLabel` | Link Label | richtext |
| `iconType` | Icon Source | `icon`, `image` |
| `icon` | Icon | icon |
| `iconColor` | Icon Color | color |
| `iconImage` | Icon Image | asset |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `stacked`, `split` |
| `background` | Background: Background | color |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `cardBackgroundColor` | Background: Card Background | color |
| `cardBackgroundOpacity` | Background: Card Background Opacity | opacity |
| `cardLayout` | Card Style: Card Layout | `stacked`, `inline`, `banner` |
| `cardMedia` | Card Style: Card Media | `icon`, `cover` |
| `cardStyle` | Bullets / Card Style: Card Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined` |
| `footnoteAlign` | Footnote: Footnote Alignment | `left`, `center`, `right` |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `hoverStyle` | Motion: Hover | ``, `lift`, `tilt`, `trace`, `ring`, `tint` |
| `iconStyle` | Items / Card Style: Icon Style | `plain`, `tile`, `circle` |
| `verticalAlign` | Arrangement: Vertical Alignment | `start`, `center`, `end`, `stretch` |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

Each design's props, its Property Editor labels and its JSON (the Configure Properties value) are in `design-NN.md` beside this README (`design-01.md` for Cards 01). Read the table below, pick a design, then read only its file.

16 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Three roles, outlined | Choosing between options (roles, programs, ways to help). |
| 02 | Four cards, two by two, on crosshatch | Four short requirements or facts of equal weight (age, what to wear, accessibility). |
| 03 | Questions on diagonal navy | Three short questions and answers (a mini FAQ) on a dark section. |
| 04 | Category header cards | Programs or funds, each with a category, title, short description and link. |
| 05 | Ghost results with a button | Results or outcomes on a dark section with one action after them. |
| 06 | Centered icon cards | Comparing three options side by side, each with a symbol and a short verdict. |
| 07 | Split, two flat cards | A section where the heading and intro need room beside the cards. |
| 08 | Joined, three columns | Three parts of one idea (a problem in three parts). |
| 09 | Inline icons, four across | A long list of capabilities (eight) on a dark section, with one action after it. |
| 10 | Products with icons on navy | Three products or tools, each with a short description and a link, on a dark section. |
| 11 | Split, joined | A principle with three supporting points. |
| 12 | Outlined on mint | Honest, low-pressure points (what we will and won't do). |
| 13 | Split, flat, two by two | Four benefits beside a heading and intro. |
| 14 | Joined on stripes | Four short items as a band (four ingredients, four steps without numbers). |
| 15 | Split outlined with a footnote | Four points beside a heading, with a note below. |
| 16 | Five across, top bar | Five small items in one row (five places a component can be used). |

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Cards 04, Cards 06 | 1 of 3 | The centered display heading breaks inside words in 1 of 4 ("progra / m", "nonpro / fit"). |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
