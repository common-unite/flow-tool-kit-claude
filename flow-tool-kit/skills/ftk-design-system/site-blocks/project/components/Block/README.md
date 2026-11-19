# Block

Any block by its `sectionType`, and the settings every block shares.

**Maps to:** Form (Design Block), `siteDesignBlock`. Use the named components (Hero, Cards and the rest) when you design; `Block` is for a type chosen at run time. Every block is the package's own component compiled from `siteDesignBlock`.

## How a block is colored

Three layers, outermost first. Leave a layer empty and the one above shows through.

| Layer | Where it is set | Tokens |
| --- | --- | --- |
| 1. Site branding | Experience Builder Theme panel; here, `Page`'s `theme` prop | `site-brand`, `site-accent`, `site-text`, fonts |
| 2. Site head | `--ftk-site-*-override` tokens in the site's head markup | `--ftk-site-brand`, `--ftk-site-part-gap`, `--ftk-site-radius-shell` |
| 3. The block | `brandColor`, `accentColor`, `background` and the color props below | literal colors on this block only |

## Shared settings

Every key below is valid on every block type, though a type ignores a setting it does not draw. Enumerated values come from the package's 51 option lists in `siteDesignBlockConfig`.

### Arrangement

| Prop | Label | Values |
| --- | --- | --- |
| `arrangement` | Arrangement | `stacked`, `split` |
| `buttonPlacement` | Button Placement | `heading`, `copy` |
| `copyWidth` | Copy Width | `full`, `column` |
| `headerPlacement` | Heading Position | `column`, `above` |
| `heroLayout` | Button Placement | `stacked`, `band` |
| `splitRatio` | Column Ratio | `even`, `left`, `right` |
| `verticalAlign` | Vertical Alignment | `start`, `center`, `end`, `stretch` |

### Background

| Prop | Label | Values |
| --- | --- | --- |
| `accentColor` | Accent Color | color |
| `accentColorOpacity` | Accent Color Opacity | opacity |
| `background` | Background | color |
| `backgroundAccentColor` | Gradient End | color |
| `backgroundAccentOpacity` | Gradient End Opacity | opacity |
| `backgroundGradient` | Gradient | `off`, `banner`, `diagonal`, `vertical`, `horizontal`, `radial`, `spotlight`, `corner` |
| `backgroundMidColor` | Gradient Midpoint | color |
| `backgroundMidOpacity` | Gradient Midpoint Opacity | opacity |
| `backgroundOpacity` | Background Opacity | opacity |
| `backgroundTexture` | Texture | `off`, `crosshatch`, `stripes`, `dots`, `grid` |
| `brandColor` | Brand Color | color |
| `brandColorOpacity` | Brand Color Opacity | opacity |
| `cardBackgroundColor` | Card Background | color |
| `cardBackgroundOpacity` | Card Background Opacity | opacity |

### Badges

| Prop | Label | Values |
| --- | --- | --- |
| `badgeAlign` | Badge Alignment | `left`, `center`, `right` |
| `badgePosition` | Badge Position | `bottom`, `top` |
| `badgesGap` | Space Below Badges | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

### Body / Items / Card Style

| Prop | Label | Values |
| --- | --- | --- |
| `bodyAlign` | Alignment | `left`, `center`, `right` |

### Body

| Prop | Label | Values |
| --- | --- | --- |
| `blockTitleColor` | Block Title Color | color |
| `blockTitleColorOpacity` | Block Title Color Opacity | opacity |
| `bodyGap` | Space Below Body | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `textColor` | Text Color | color |
| `textColorOpacity` | Text Color Opacity | opacity |

### Border

| Prop | Label | Values |
| --- | --- | --- |
| `borderBottom` | Bottom | text |
| `borderColor` | Border Color | color |
| `borderColorOpacity` | Border Color Opacity | opacity |
| `borderLeft` | Left | text |
| `borderRight` | Right | text |
| `borderTop` | Top | text |
| `borderWidth` | Border Width (px) | text |

### Bullets / Card Style

| Prop | Label | Values |
| --- | --- | --- |
| `cardStyle` | Card Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined` |

### Bullets

| Prop | Label | Values |
| --- | --- | --- |
| `bulletCheckColor` | Check Color | color |
| `bulletCheckColorOpacity` | Check Color Opacity | opacity |
| `bulletTextColor` | Description Color | color |
| `bulletTextColorOpacity` | Description Color Opacity | opacity |
| `bulletTitleColor` | Title Color | color |
| `bulletTitleColorOpacity` | Title Color Opacity | opacity |
| `bulletsGap` | Space Below Bullets | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

### Buttons

| Prop | Label | Values |
| --- | --- | --- |
| `buttonAlign` | Button Alignment | `left`, `center`, `right` |
| `buttonsGap` | Space Below Buttons | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

### Card Style

| Prop | Label | Values |
| --- | --- | --- |
| `cardLayout` | Card Layout | `stacked`, `inline`, `banner` |
| `cardMedia` | Card Media | `icon`, `cover` |

### Columns

| Prop | Label | Values |
| --- | --- | --- |
| `tableHeaderBackground` | Table Header Fill | color |
| `tableHeaderBackgroundOpacity` | Table Header Fill Opacity | opacity |
| `tableHeaderColor` | Table Header Text | color |
| `tableHeaderColorOpacity` | Table Header Text Opacity | opacity |

### Footnote

| Prop | Label | Values |
| --- | --- | --- |
| `footnoteAlign` | Footnote Alignment | `left`, `center`, `right` |
| `footnoteGap` | Space Above Footnote | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

### Heading

| Prop | Label | Values |
| --- | --- | --- |
| `headerGap` | Space Below Heading | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `headingAlign` | Heading Alignment | `left`, `center`, `right` |
| `headingStyle` | Heading Style | `standard`, `statement` |

### Image

| Prop | Label | Values |
| --- | --- | --- |
| `imageCaption` | Caption Style | `below`, `overlay`, `none` |

### Images

| Prop | Label | Values |
| --- | --- | --- |
| `backgroundEffect` | Photo Motion | `none`, `parallax`, `kenburns` |
| `backgroundOverlay` | Photo Overlay | `auto`, `none`, `bottom`, `side`, `tint`, `light`, `custom` |
| `backgroundOverlayColor` | Overlay Color | color |
| `backgroundParallaxSpeed` | Drift Speed | `0.15`, `0.25`, `0.4`, `0.6` |
| `blockHeight` | Block Height | `auto`, `band`, `standard`, `tall` |
| `contentPosition` | Content Position | `center`, `bottom`, `top` |

### Items / Bullets

| Prop | Label | Values |
| --- | --- | --- |
| `showcaseItems` | Item Display | `list`, `cards` |

### Items / Card Style

| Prop | Label | Values |
| --- | --- | --- |
| `columns` | Columns | `2`, `3`, `4`, `5` |
| `iconSize` | Icon Size | `xx-small`, `x-small`, `small`, `medium`, `large` |
| `iconStyle` | Icon Style | `plain`, `tile`, `circle` |

### Items / Stats

| Prop | Label | Values |
| --- | --- | --- |
| `countUp` |  | text |

### Items

| Prop | Label | Values |
| --- | --- | --- |
| `carouselInterval` | Auto-advance | `0`, `4`, `5`, `8` |
| `factsDisplay` | Display | `rows`, `bars`, `stacked`, `segmented` |
| `galleryLayout` | Layout | `mosaic`, `grid`, `masonry`, `filmstrip` |
| `iconColor` | Icon Color | color |
| `iconColorOpacity` | Icon Color Opacity | opacity |
| `itemTextColor` | Description Color | color |
| `itemTextColorOpacity` | Description Color Opacity | opacity |
| `labelColor` | Label Color | color |
| `labelColorOpacity` | Label Color Opacity | opacity |
| `labelSize` | Title Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `statsTreatment` | Stats Treatment | `row`, `tiles`, `spread` |
| `tableBadgeBackground` | Table Badge Fill | color |
| `tableBadgeBackgroundOpacity` | Table Badge Fill Opacity | opacity |
| `tableBadgeColor` | Table Badge Text | color |
| `tableBadgeColorOpacity` | Table Badge Text Opacity | opacity |
| `tableGridColor` | Table Grid Lines | color |
| `tableGridColorOpacity` | Table Grid Lines Opacity | opacity |
| `tableRowHighlight` | Highlighted Row Fill | color |
| `tableRowHighlightOpacity` | Highlighted Row Fill Opacity | opacity |
| `timelineBaseColor` | Marker Base | color |
| `timelineBaseColorOpacity` | Marker Base Opacity | opacity |
| `timelineMarkerInk` | Marker Ink | color |
| `timelineMarkerInkOpacity` | Marker Ink Opacity | opacity |
| `timelineOrientation` | Orientation | `horizontal`, `vertical` |
| `valueColor` | Value Color | color |
| `valueColorOpacity` | Value Color Opacity | opacity |
| `valueSize` | Value Size | ``, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

### Media / Image / Images

| Prop | Label | Values |
| --- | --- | --- |
| `imageAlt` | Image Alt Text | text |
| `imageBleed` | Image Bleed | `none`, `bottom`, `edge` |
| `imageFit` | Image Fit | `fill`, `fit`, `natural` |
| `imageStyle` | Image Style | `flat`, `outlined`, `elevated`, `deep`, `glow`, `topbar`, `siderule`, `gradient`, `ghost`, `inset`, `clean`, `joined`, `mascot` |

### Media

| Prop | Label | Values |
| --- | --- | --- |
| `heroMedia` | Media | `image`, `facts`, `timeline`, `bullets`, `none` |

### Motion

| Prop | Label | Values |
| --- | --- | --- |
| `entrance` | Entrance | ``, `rise`, `cascade`, `wipe`, `zoom`, `blur` |
| `hoverStyle` | Hover | ``, `lift`, `tilt`, `trace`, `ring`, `tint` |

### Spacing

| Prop | Label | Values |
| --- | --- | --- |
| `attachToPrevious` |  | text |
| `marginBottom` | Margin Bottom | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `marginTop` | Margin Top | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `overlapBottom` | Bottom | text |
| `overlapMargin` | Overlap Amount (px) | text |
| `overlapTop` | Top | text |
| `paddingBottom` | Padding Bottom | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `paddingLeft` | Padding Left | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `paddingRight` | Padding Right | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `paddingTop` | Padding Top | `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |
| `width` | Width | `contained`, `full`, `inset` |

### Stats

| Prop | Label | Values |
| --- | --- | --- |
| `statLabelColor` | Label Color | color |
| `statLabelColorOpacity` | Label Color Opacity | opacity |
| `statValueColor` | Value Color | color |
| `statValueColorOpacity` | Value Color Opacity | opacity |
| `statsGap` | Space Below Stats | `default`, `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large` |

## Rules

- A control steers only the part it sits under in the Property Editor.
- Offered means it visibly acts: a setting a type cannot draw is left off, not set to a value that does nothing.
- Color props offer tokens; leave them empty to follow the site.
- Blocks are drawn with SLDS and the package's own styles. Never add a class or a style of your own to a block.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
