# Site house rules

The design defaults for every site page, the twin of the form house rules. Apply them on every first draw; depart from one only when the organization asks or the content gives a clear reason, and say so in the page's `_design.notes`. When a canvas comment states a general preference, add it here for the project, with the date and the reviewer's words.

**Rich block use is the norm.** Site Blocks can do a lot; a page of plain blocks reads as a document. The worked sample `examples/riverside-sample/` shows every rule. The generator checks the rules marked *Checked*: it prints a line per miss and shows it as Fix in the Section jobs handoff checklist. Read every line before publishing.

## Blocks

- **Start from a design card, never from a block's defaults.** Copy the block JSON of the numbered design (Hero 14, Cards 04, Quote 03) and change words, images and colours; keep its surface, gradient, texture, layout and hover settings. *Checked:* a block that sets nothing beyond words, palette and alignment.
- **Heroes use their range.** A hero can carry tags (`badges`, one with `pulse` for a deadline), a longer description (a `subheading` of two sentences or more), primary and secondary buttons, a secondary pop-up image (`imageAsset` with `imageStyle` `elevated` over the background photo, as Hero 21 does) and facts or stats (`heroMedia: "facts"` with `items`, or inline `stats` with `countUp`). The opening hero uses at least three of the five and usually four; any other hero at least two; a closing band (`heroLayout: "band"`) is exempt. *Checked.*
- **The opening hero sits on a photo with a scrim.** `backgroundImageAsset` from the Flow Tool Kit demo photos (`FlowToolKit__Background_*`, listed in the design system's `assets/Backgrounds/README.md`, and without the full kit in `_shared/design-systems/images.json` with thumbnails in `_shared/design-systems/images.html`) until the organization sends its own, `backgroundOverlay` `side`, `tint` or `bottom`, and `blockHeight` `tall`. On a dark photo set the hero's `brandColor` to the accent, so the eyebrow, outline button and footnote read. *Checked.*
- **Sample and placeholder images come from the Flow Tool Kit package's demo photos.** Until the organization sends its own (listed in `site.json` `assets`), every hero background, pop-up image, Image, Carousel or Gallery item and record card photo is one of the package images the design system ships: `Backgrounds/` for hero, band and record card photos (`FlowToolKit__Background_*`), `People/` and `Bears/` for profile cards and mascot images, or a `resource:` file the kit ships. Never an outside photo. Every sample record in a Repeater whose card draws a photo (`mediaTop`, `photoOverlay`, `dateTile`, `profile`) carries one, so no card shows an empty image slot. Name the image with its source: `imageSource: "asset"` beside `imageAsset`, and `backgroundImageSource: "asset"` beside `backgroundImageAsset`; without it the block or card draws no photo at all. On a record page, and in record cards, the photo may be the record's own field: `imageSource: "url"` with `imageUrl: "{{Photo__c}}"` (or `backgroundImageSource` and `backgroundImageUrl`); it counts as the photo for the hero and photo band checks, and the canvas draws a package image in its place (`_design.photoStandIn`). A record-field photo on a page with no record is flagged. *Checked.*
- **Every page has a full-bleed photo band below the hero.** One mid-page block (a Quote, a Stats Bar, a Callout) at `width: "full"` on a photo with a scrim and `backgroundEffect: "parallax"`. *Checked.*
- **Tabs carry rich content, never a line of text.** Each tab holds at least one block or Repeater: record cards, Facts (bars for a rubric), Cards, a hero with bullets and a framed photo, a Callout checklist. Draw every tab: add a `_design.states` entry `{id, title, section, activeTab}` for each tab after the first. *Checked.*
- **Vary designs down the page**, following `Choosing-blocks.md`'s rhythm: alternate deep, white, tint and photo grounds, mix block types (a page uses at least five), and never repeat a design card on one page. *Checked:* a repeated design card, and two neighbours on the same ground.
- **The thing they came to do sits high.** On a listing page the records come straight after the hero, with the next deadline or action beside them (an Action Card and a Facts card in a 4 column beside an 8 column Repeater). The audience the organization names first gets the first screen.
- **Records come from record cards on live records** (a Repeater, or `sectionType: recordCard`), never hand-written cards. Pick the card type for the data: `mediaTop` or `photoOverlay` with photos, `valueSpotlight` for an award amount, `dateTile` or `countdown` for dates, `profile` for people.
- **Custom markup is the last resort.** The HTML Editor only where no block does the job, with `_design.reason`, at most two a page, static markup only ([html-editor.md](html-editor.md)). *Checked.*

## What "bland" looks like

- A hero with a heading, one sentence and nothing else on a plain gradient.
- A record page hero with no photo.
- Record cards with an empty image slot: `imageAsset` set without `imageSource: "asset"`.
- A tab whose content is one rich text paragraph.
- A Callout or Facts block left at its defaults: white, no texture, no surface, no layout choice.
- A closing Callout where a closing band (Hero 27 to 29) belongs.
- Flat colour bands one after another and no photo below the hero.

## Layout, motion and colour

- A supplied design is a floor, not a ceiling. Use the package's photos and motion, record cards, dividers and mixed columns, and look at well-made sites in the organization's field for the mix of colour, white space and type.
- One photo band with motion: Ken Burns on the hero, parallax on a mid-page band. One entrance on the opening block only; none below it. A block with an entrance stays hidden until it scrolls into view, and on a phone every block fills the screen, so entrances on every block read as content disappearing and fading back at every scroll. Ken Burns, parallax and count-up are not scroll-gated and are fine. At most two loops per page. *Checked:* at most one entrance.
- Dividers between chapters (a Flow Tool Kit header with `displayAsDivider`, style `icon`), each with a label and a subtitle worth reading.
- Unequal columns for copy beside media (7/5, 5/7, 8/4); a page of all 12-column sections reads as a document. *Checked:* widths vary somewhere.
- Big confident colour fields: a deep colour for the serious sections, one bright accent, generous padding (`x-large` top and bottom for full sections, `medium` for strips and paired blocks), large display type. Alternate white, tint, deep and photo bands.
- Header and footer come from the design system's sections or the site's standard theme header, menu and footer; no custom component for them.
- Every page ends with a closing band or an Action Card. *Checked.*
- Buttons point to `#` until their target page exists: a link to a page that does not exist fails in the preview.

## Copy and numbers

- Numbers that may be blank or zero go through a text formula field on the object, so an unset amount shows nothing rather than `$0.00`.
- A number, quote or date the organization has not confirmed is written in place as `[CONFIRM: ...]`; the canvas lists every one.
- Copy comes from the organization's own pages and the brand kit's voice; nothing invented is presented as fact.
- No em dashes in copy.
