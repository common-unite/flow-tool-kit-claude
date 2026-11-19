# FlowToolKit Site Blocks

The visual reference for designing whole Experience Cloud sites built with FlowToolKit. Implementation partners lay out a client's pages here, then hand the design to Claude Code, which builds them in the site with the real package. Every block here is the package's own component, so a design converts to block files with nothing to translate.

It extends the **FlowToolKit Forms** design system (__FTK_FORMS_DESIGN_SYSTEM_URL__). A page's forms and FlowToolKit components are designed there; here a `FormSlot` draws the real form where it sits in a column, with the Forms system's own bundle, built in from the same repository.

## What you are looking at

Unlike the Forms design system, which redraws each field, the blocks here are not redrawn. The bundle compiles the package's `siteDesignBlock` component straight from `force-app` with the LWC compiler, with small stand-ins for the Salesforce base components (`lightning-layout`, `lightning-formatted-rich-text`, `lightning-icon`, `lightning-button`) and nothing reaching an org. A block's markup, CSS and every option are therefore the site's own. The side-by-side check holds this to account: every design on the Testing Aura design library page is drawn here and on the live site, and compared pixel by pixel.

Aura is the base and LWR the second site type. Each has its own pinned stylesheet: `bundle.css` is what an Aura site loads (SLDS, the theme tokens and the Flexible Layout section rules from Testing Aura, the Customer Service theme and standard components from Testing CS); `bundle-lwr.css` is what a Build Your Own (LWR) site loads (SLDS, the `--dxp` styling hooks and the platform's own styles, from Testing LWR). The theme layouts, the standard components and the column layouts are checked side by side against the three sites the same way, at desktop and phone width.

## Aura and LWR

Design every page once, drawn as an Aura page; the cards have no site-type switch. The conversion scripts (`/design-to-blocks`, `/build-site-pages`, `tools/design_to_site.py`) place the same design on an Aura or an LWR site. `Page`'s `site` prop can still draw a page as LWR when a design must show LWR-only markup. Blocks are the same component with the same JSON on both. What differs is the page around them: LWR sections and columns instead of Flexible Layout, the Build Your Own (LWR) theme layout, the LWR names of the standard components, and theme hooks from the branding set. Each card's README ends with an **On LWR** section saying where that component differs.

## How a site page is drawn

| Layer | What it is | What a design can change |
| --- | --- | --- |
| SLDS | Grid, spacing, type, the reset | Nothing. |
| Theme layout | Aura: the Build Your Own or Customer Service theme, Flexible Layout Sections and their columns. LWR: the Build Your Own (LWR) layout and LWR sections | The Theme panel or branding set (brand, accent, fonts) and each Section's columns. |
| Blocks | Form (Design Block), one per part of the page | The block's JSON: its type, content and every Property Editor setting. |
| Forms | Form Templates and FlowToolKit components in a column | Designed in the Forms design system. |

Colors come in three layers: the site's branding (the `site-brand`, `site-accent`, `site-text` tokens, or `Page`'s `theme`), the `--ftk-site-*` tokens a site sets in its head, and a block's own colors. Leave a block's colors empty and it follows the site.

## Designing a page

**Read `Choosing blocks` first.** It is the design decision guide: the page pattern for what the page is for, the block for each section's job, the design that fits what the client can actually supply, and the background, motion and surface rhythm across the page, with a checklist a page must pass before handoff.

**Then start from the examples.** The demo sites' designs are here as cards, drawn by the package's own blocks on a test site:
- **Designs (134, inside the block cards):** each block card (Hero, Cards, Stats Bar, Record Card and the rest) shows every design the package offers for that block, hover one for its name (Hero 01 to Hero 29, Cards 01 to Cards 16), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. The block's README has a Designs section: when to use each design, why it works, the content it needs, its settings and its JSON.
- `Features*` (22): one setting's whole range across real designs: card surfaces, background gradients and textures, image styles, button styles, borders, width modes, icon styles, column ratios, dark backgrounds, stats options, motion, background photos.
- `Page*` (14): whole demo pages (funding, program, volunteer, image blocks, record cards, marketing) with their sections and column widths: the starting shape for a page of that kind.

A page made only of default variants is not finished. Every page should use the range: a photo hero with motion (`backgroundEffect: "kenburns"`, an `entrance` on the opening block only), a `parallax` photo band mid-page, attached stats (`attachToPrevious`), mixed column widths (7/5, 8/4), deep colour fields alternating with white and a light tint, record cards for anything that is a record, and the packaged photos and bears.

**Do**
- Build a page as `Page` > `Section` > `Column` > blocks, the way Experience Builder stacks it.
- Use columns wherever content sits side by side: copy beside a form, facts beside an application, cards three across. Columns add up to 12, one to four of them.
- Pick blocks by what the content is: a Hero opens the page, Facts and Stats Bar give figures, Steps explain a process, Cards and Pricing compare, a Callout asks for one thing.
- Set props with the block's own keys and only the package's values. The props check fails on anything else.
- Use the packaged photos in `assets/Backgrounds`, `assets/People` and `assets/Bears` by their Asset File names (`backgroundImageAsset: "FlowToolKit__Background_Forest_Sunbeams"`).
- Put forms in a `FormSlot` and design them in the Forms design system.
- Use the standard components where a client's site already does: Tabs for a record's detail, Rich Content for a page's own copy, the HTML Editor only for an embed or one-off markup.

**Don't**
- Don't add classes or styles to a block, or wrap one in your own markup. A look a block can't give is a design question to raise.
- Don't use the soft-retired Heading and CTA types; a Hero without media opens a page, and a Callout asks for an action.
- Don't use em dashes in copy.

## Components

| Group | Components |
| --- | --- |
| Page layout | `Page`, `ThemeLayout` (the Customer Service layout), `Section`, `Column`, `Divider`, `FormSlot`, `Repeater` |
| Standard components | `Tabs`, `RichContent` (Rich Content Editor), `HtmlEditor`, `Search`, `LanguageSelector` |
| Examples | `ExampleListingPage`, `ExampleParentRecordPage`, `ExampleChildRecordPage`: the three page shapes a client site is built from |

| Features | `FeaturesMotion`, `FeaturesBackgroundPhotos`, `FeaturesEveryImageStyle` and the rest: one setting's whole range |
| Page examples | `PageVolunteer`, `PageFundingExamples` and the rest: whole demo pages |
| Blocks | Every design in each block's card, with column widths and phone width: `Hero`, `StatsBar`, `Facts`, `Timeline`, `Quote`, `ActionCard`, `Carousel`, `Image`, `Gallery`, `Cards`, `Steps`, `Pricing`, `Callout`, `Table`, `Pills`, `RecordCard`, and `Block` for any type plus the shared settings |
| Shared parts | `SectionHeader`, `Buttons`, `Badges`, `Footnote`, `Icon` |

## From design to site

A page designed here is built by the Flow Tool Kit plugin, nothing translated: the design-to-blocks skill reads the design back into `page.json` (sections, columns, every block's JSON, standard components, tabs, Form Slots, the Page's theme and navigation), and the build-site-pages skill writes the page's view and route for an Aura or an LWR site plus one block file per block, deploys the page on its own or with the whole site (theme layout, branding, navigation menu), publishes the site and checks the live page against the design. A Form Slot becomes the real Form Template once that form is built from the Forms design system. A Repeater must carry its `object` and `card` (with `filter`, `sortField` and `emptyMessage` as the page needs): The build refuses a page whose Repeater has only sample records, naming the section.

The generator's other inputs, for an LWR site:

| Option | What it does |
|---|---|
| `--record-object <Object>` | Builds the page as that object's record page: the detail route and view, plus the list and related-list routes Experience Builder deploys with it (a missing one gets a one-block stub page; an existing one is kept). Every record-bound component reads `{!Route.recordId}`. Route types follow Builder: a standard object's key prefix (`detail-001` for Account), a custom object's API name (`detail-FlowToolKit__Form_Template__c`). The key comes from the object's route in the bundle, then the standard objects (Account, Asset, Contact, Opportunity, Case), then `--record-prefix`, then a custom object's API name. A page title another page already uses is refused. |
| `--blocks <dir>` | Also writes the page as a block folder: `NN-type.json` per item, numbered by section (`04a` and `04b` share section 4), and `_sections.json` with each section's widths and settings. The folder is an output; given back as the design (`design_to_site.py <dir> ...`) it rebuilds the same view. |
| `--entire-site --site-config site.json` | Writes the design's Page theme as `--ftk-site-*` head tokens (`brand`, `accent`, `font`, `headingFont`; `text` goes to the branding set), plus the site config's `title`, `branding` values, extra `headTokens` and `authenticationType`. Works on any theme layout; on one that is not Build Your Own's, the header and footer are left as they are and listed as a deviation. |
| `--palette palette.json` | Named colours: any `"$name"` value in the design or the site config becomes the colour. |

build-site-pages also takes `--brand-kit brand-kit.json` (colors, fonts and button corners from a saved brand kit) and `--footer-support c:<component>`, and prints the `sf project deploy start` command for the page's folders and the `site_publish.py` command (one of the plugin's shared `sf` helpers) that publishes the site.

## Built from

The Flow Tool Kit package's own site components and block option lists, and the Aura and LWR stylesheets of a working test site.
