# From a design to blocks

How a section of a design becomes a block, what a listing and a record page are made of, and where each colour lives. Read the design system's `Choosing-blocks.md` first: the page pattern, each section's job, the design that fits what the organization can supply, and the rhythm of backgrounds, motion and surfaces.

## A design someone else drew

Screenshots, a page from another tool, the organization's current site, a sketch: write a numbered section list top to bottom (intent, copy, layout as full width, split or N across, media, buttons), with the copy taken from the organization's own sources and anything invented marked `[CONFIRM: ...]`. Then rework it with the house rules before mapping: a supplied design is a floor. Keep its content and order; improve its form. Then write `page.json` and draw the canvas as for any other page.

## Design shapes to blocks

| Design shape | Block | Notes |
|---|---|---|
| Opening banner over a photo | `hero`, `width: full`, `backgroundImageSource: asset`, `backgroundOverlay`, `blockHeight: tall` | `headingHighlight` renders in a brand-to-accent gradient |
| Number strip under the banner | `statsBar`, `attachToPrevious: true`, `countUp: true` | Count-up reads the first integer in each value |
| Text beside a photo | `hero`, `arrangement: split`, `imageSource: asset`, `reversed` for image left | Write `"backgroundGradient": "off"` or it renders the brand gradient band |
| Text beside a bullet list | the same `hero` with `bullets` and `showcaseItems: list` | |
| Photo beside copy and a checklist | the same `hero` with `imageSource`, `blockTitle`, `description` and `bullets` | With an image the bullets sit under the body; `heroMedia: bullets` puts them beside the copy in place of the image |
| A statement over a row of short points | `cards`, `headingStyle: statement`, `columns: auto`, `description` for the emphasis line | A `callout` is the statement alone: eyebrow, statement, supporting copy, emphasis line, buttons |
| Percentage breakdown | `facts`, `factsDisplay: bars` | One bar per item. One stacked bar of a whole is an HTML Editor ([html-editor.md](html-editor.md), the worked example) |
| N items across | `cards`, `columns: N` | `eyebrow: "01"` for step numerals; `cardMedia: cover` with `iconImage` for photo cards; `icon` plus `iconStyle: tile` for icon cards; `link` plus `linkLabel` for a card action |
| Numbered vertical list | `steps` | Vertical only. Four across is `cards` |
| Testimonial | `quote` | `description` is the quote; a dark band via `background` plus `backgroundGradient: spotlight` |
| Names or logos | `pills` | Two groups side by side are two items in one section |
| Closing band with buttons on the right | `hero`, `heroLayout: band`, `backgroundGradient: horizontal` | |
| Origin story | `timeline` | |
| A framed photo with a caption | `image`, `imageCaption: overlay` | |
| Tighter or looser room around one part | `headerGap`, `bodyGap`, `statsGap`, `bulletsGap`, `buttonsGap`, `badgesGap`, `footnoteGap` | Each takes the spacing scale (`none`, `xxx-small` 8px, `xx-small` 16px, `x-small` 24px, `small` 40px, `medium` 64px and up) and sets the room under its part; `footnoteGap` the room above the footnote. Body, stats and bullets are hero only |
| Something no block draws, with no behaviour and no record data | HTML Editor | Last resort, with a reason ([html-editor.md](html-editor.md)) |

Two independent things side by side are two items in one section, each in its own column; one block cannot hold two collections in two columns.

## Listing and record pages

A program portal always has these, and each follows one shape:

| Page | Rows |
|---|---|
| Listing | Band hero with inline stats; the Repeater (inline record-card form, photo-overlay cards) with an Action Card and Facts beside it; one explanatory `facts` block; a closing band with the two calls to action |
| Parent record (a program, a fund, an event) | Photo hero from the record's image field with `backgroundEffect: kenburns`, badges from picklists, heading `{{Name}}`; an attached `statsBar` of the record's numbers; a split `hero` with the record's story as `description` and `heroMedia: facts`; a Repeater of its children filtered on the lookup `eq {!recordId}`; a closing band naming the record |
| Child record (a session, a grant, a shift) | Photo hero from the parent's image (`{{Parent__r.Photo__c}}`), the parent's name as the eyebrow, badges for status; an attached facts strip; the description beside a facts card; a closing band |

What the org's platforms suggest (org-catalog finds them; `start_site.py` prints the suggestion): Outbound Funds, a funding listing and a funding program record page; Nonprofit Cloud, a program listing and a program record page; NPSP, campaign or volunteer pages. Applications go in a Form Slot, built with form-design and build-template.

On the free edition, blocks on a record page read records of Account, Contact, Case, Lead and Form Template only, and a Repeater's cards need an object free forms can use. A sandbox shows everything, so ask about the edition before designing a record page on another object.

## The palette, in three layers

Start from the brand kit: its brand, heading and accent colours, fonts, corner roundness and chosen photos (`start_site.py` writes them into `site.json`). Then decide where each colour lives:

1. **Site branding** (the LWR branding set, the Aura theme): the brand colour. Blocks read it through `--dxp-g-brand` (LWR) or `--lwc-brandPrimary` (Aura), so a block with no colour of its own is on brand.
2. **Design tokens in the site's head markup**: accent, scrim, radii, fonts. One `<style>` for every page, which build-site-pages writes.
3. **page.json**: only a section's own surface (a deep band, a tint band, a gradient). Refer to colours as `"$name"` from the palette; the build swaps them.

Blocks should carry as few colours as possible. A colour that appears in more than two blocks belongs in a higher layer.
