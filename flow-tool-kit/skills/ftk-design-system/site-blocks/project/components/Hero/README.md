# Hero

The page opener: badges, a heading, copy and buttons beside a photo, a facts or timeline panel, or a checklist.

**Maps to:** a Form (Design Block) whose `sectionType` is `hero` (Hero in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `HeroProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |
| `sectionLabel` | Heading: Section Label | Small uppercase eyebrow above the heading. |
| `heading` | Heading: Heading | Rich text. |
| `subheading` | Heading: Subheading | Rich text. |
| `blockTitle` | Body: Body Title | Optional title above the body copy. Most useful with Heading Position set to Across the top. |
| `description` | Body: Body Copy | Optional paragraph under the body title. |
| `footnote` | Footnote: Footnote | Small line rendered below the section content. |

### Facts (`items`)

A list of facts, up to 6. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `value` | Value | richtext |

With `heroMedia: "facts"` each item takes `title`, `value`.

With `heroMedia: "timeline"` each item takes `title`, `meta`, `state`.

### Bullets (`bullets`)

A list of bullets. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Title | richtext |
| `description` | Description | richtext |

### Inline Stats (`stats`)

A list of stats, up to 5. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `value` | Value | richtext |

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | color |
| `background` | Background: Background | color |
| `backgroundAccentColor` | Background: Gradient End | color |
| `backgroundEffect` | Images: Photo Motion | `none`, `parallax`, `kenburns` |
| `backgroundGradient` | Background: Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundOverlay` | Images: Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.15`, `0.25`, `0.4`, `0.6` |
| `backgroundTexture` | Background: Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `badgeAlign` | Badges: Badge Alignment | `left`, `center`, `right` |
| `badgePosition` | Badges: Badge Position | `bottom`, `top` |
| `blockHeight` | Images: Block Height | `auto`, `band`, `standard`, `tall` |
| `bodyAlign` | Body / Items / Card Style: Alignment | `left`, `center`, `right` |
| `brandColor` | Background: Brand Color | color |
| `buttonAlign` | Buttons: Button Alignment | `left`, `center`, `right` |
| `cardBackgroundColor` | Background: Card Background | color |
| `contentPosition` | Images: Content Position | `center`, `bottom`, `top` |
| `countUp` | Items / Stats: countUp | text |
| `entrance` | Motion: Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `footnoteAlign` | Footnote: Footnote Alignment | `left`, `center`, `right` |
| `headingAlign` | Heading: Heading Alignment | `left`, `center`, `right` |
| `heroLayout` | Arrangement: Button Placement | `stacked`, `band` |
| `heroMedia` | Media: Media | `image`, `facts`, `timeline`, `bullets`, `none` |
| `imageAlt` | Media / Image / Images: Image Alt Text | text |
| `imageBleed` | Media / Image / Images: Image Bleed | `none`, `bottom`, `edge` |
| `imageFit` | Media / Image / Images: Image Fit | `fill`, `fit`, `natural` |
| `imageStyle` | Media / Image / Images: Image Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined`, `mascot` |
| `showcaseItems` | Items / Bullets: Item Display | `list`, `cards` |
| `splitRatio` | Arrangement: Column Ratio | `even`, `left`, `right` |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

Each design's props, its Property Editor labels and its JSON (the Configure Properties value) are in `design-NN.md` beside this README (`design-01.md` for Hero 01). Read the table below, pick a design, then read only its file.

29 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Mascot over a navy gradient | A volunteer or event landing page that should feel warm and human, with a clear sign-up action. |
| 02 | Location with detail cards, mascot left | A where-to-go or visit-us section: address, parking, transit, accessibility. |
| 03 | Campaign with counting stats | A campaign or season launch where the numbers are the story (shifts filled, meals served, volunteers). |
| 04 | Navy facts panel | A service people apply for, where eligibility, schedule and cost decide whether they keep reading. |
| 05 | Photo facts with parallax | The same apply-for-help page as the navy facts panel, when you have a strong photo of the place or people. |
| 06 | Crosshatch statement | A program with no single action yet (mentoring, a pilot), where the promise itself is the content. |
| 07 | Static photo facts | An apply-for-help page where motion would feel out of place (legal, medical, crisis services). |
| 08 | Light tinted photo facts | A class or recurring program with simple logistics (days, times, cost, location). |
| 09 | Statement on a photo | An about or mission page that opens with one strong sentence and a short paragraph, with nothing to click yet. |
| 10 | Eligibility quick check | A grant or benefit page where the first question is whether to apply at all. |
| 11 | Fund name on a diagonal gradient | A fund or program detail page that needs a clean title band before the details below it. |
| 12 | Emergency fund facts | An urgent or rapid-response fund where speed and limits must be clear immediately. |
| 13 | Capital grant facts, light | A capital or equipment grant page with several eligibility facts and a long description below. |
| 14 | Tall photo, side overlay | The top of a funder's main grant page, where you want one cinematic moment before the details. |
| 15 | Gradient split, framed photo right | A values or approach statement with three supporting points and a good landscape photo. |
| 16 | Tall photo, text at the bottom | A mission or impact page that should open on a full-bleed photograph. |
| 17 | Framed photo on a brand gradient | A team or organization section with a short headline, one action and a real photo. |
| 18 | Ken Burns banner | A campaign or event page that wants motion without a video. |
| 19 | Mascot on dots | A playful marketing or product page, where personality matters more than facts. |
| 20 | Framed illustration on a vertical gradient | A product or feature page with a screenshot or illustration to show. |
| 21 | Photo split with stats and crosshatch | A demo or how-it-works section that pairs a claim with three proof numbers. |
| 22 | Problem statement with a mascot | The opening of a page that names the reader's problem before the solution. |
| 23 | Brand gradient with key points and a mascot | A capability section with three short labelled points (not numbers) and one action. |
| 24 | Coral gradient split | A section that must feel different from the rest of a navy and green site (a problem, a warning, another audience). |
| 25 | Mint grid with a mascot | A closing or reassurance section near the end of a services page. |
| 26 | Radial gradient with bullets | A capabilities section that lists six things on one screen. |
| 27 | Closing band, diagonal | The last block on a page: one sentence and the two actions you most want taken. |
| 28 | Closing band, green with dots | A gentle closing nudge with one action, after a light section. |
| 29 | Closing band, spotlight gold | A closing band that must win attention (a deadline, a talk-to-us action). |

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

| Design | Narrowest column | Why |
| --- | --- | --- |
| Hero 03, Hero 21, Hero 23 | 1 of 3 | The inline stats squeeze into three narrow columns in 1 of 4; numbers and labels break ("100 / %", "Multi- / step"). |
| Hero 05, Hero 07, Hero 08, Hero 10, Hero 12, Hero 13, Hero 14 | 1 of 3 | The facts or checklist panel stacks label over value in 1 of 4, the outline button wraps, and photo text loses contrast in the narrow crop. |

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
