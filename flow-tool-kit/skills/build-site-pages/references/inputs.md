# What the build reads

design-to-blocks writes the design as data; this skill builds from that data and nothing else. Change the design in `page.json` (or `site.json`), never in the generated site files: the next run overwrites them.

## The project folder

```
_site/<slug>/
    site.json                 the site: pages, palette, brand, shared header and footer, site settings
    pages/<urlName>.json      one page.json per page
    photos.json               optional: photos to turn into public Asset Files (SKILL.md, Step 3)
    backups/<yyyy-mm-dd>/     the site as pulled before each build
    checks/<yyyy-mm-dd>/      render check screenshots
    notes.md                  what the build learned about this site
```

`<slug>` is the site's name in lowercase with hyphens (`riverside-garden`).

## page.json

| Key | What the build does with it |
|---|---|
| `title` | The page title and route title, unless `--title` is given. Builder refuses two pages with one title, so the generator stops on a clash |
| `sections[]` | `{attributes, columns[{width, items[]}]}`, top to bottom. One to four columns adding up to 12. `attributes` may set `sectionVerticalAlign`, `maxContentWidth`, `sectionColumnGutterWidth` |
| `theme` | `brand`, `accent`, `font`, `headingFont` become `--ftk-site-*` head tokens; `brand` also sets the branding set's accent; `text` the text color |
| `header`, `footerContent` | Sections for the theme layout's header and footer (Build Your Own (LWR) layout only) |
| `navItems` | The default navigation menu, links only to pages the site has |
| `site` | `lwr` or `aura`: the type the page was drawn for. A design drawn for the other type is converted and named as a deviation |
| `_design` | Review notes for the design canvas. The build ignores it |

Each item has a `kind`:

| `kind` | Becomes |
|---|---|
| `block` | Form (Design Block), `FlowToolKit:siteDesignBlock`, with `props` as its JSON. Collections (`items`, `buttons`, `badges`, `bullets`, `stats`, `tableColumns`, `columns`) may be arrays; the block stores them as JSON strings, so the generator turns them into strings |
| `divider` | `FlowToolKit:header` shown as a divider, `attributes` as written |
| `richText` | The standard Rich Content Editor (`richTextValue`) |
| `htmlEditor` | The standard HTML Editor. On LWR it is written as the site stores it: `community_builder:htmlEditor` with `richTextValue` (the markup) and `imageInfos: ""`; on Aura `forceCommunity:htmlBlock`. design-to-blocks has already checked the markup (no scripts, frames, forms or outside hosts); its `_design.reason` is not built |
| `search`, `languageSelector` | The standard search box and language picker |
| `tabs` | The standard Tabs component, each tab holding its own items |
| `formSlot` | Form (Template), `FlowToolKit:formTemplate`, once `formTemplate` holds the Form Template's record Id. Without it the slot is left out and named |
| `repeater` | Form (Dynamic Repeater) with an inline record card form ([listings-and-record-pages.md](listings-and-record-pages.md)) |
| `component` | Any other component: `definition` and its `attributes` |

An item may carry `recordId` to pin it to one record (a featured record on a page with no record of its own).

## site.json

design-to-blocks' `start_site.py` writes the first version from `flow-tool-kit.json` and the brand kit. The keys the build reads are below; it ignores the rest (`canvasTitle`, `canvasUrl`, `brand.colors`, `brand.tone`, `brand.copy`).

| Key | What the build does with it |
|---|---|
| `title` | The site's `<title>` in the head markup |
| `palette` | Named colors: `"$name"` anywhere in a page or in `site.json` becomes the color |
| `brand.theme` | The theme every page gets unless the page sets its own |
| `brand.fonts.body_css`, `brand.fonts.heading_css` | The font stacks, as the theme's `font` and `headingFont` when `brand.theme` does not set them |
| `brand.fonts.href` | The web font stylesheet, linked once in the head. The site needs the font's hosts as Trusted URLs (style-src and font-src), or it falls back to the next font in the stack |
| `page` | Settings every page shares: `header`, `footerContent`, `navItems`, `theme`, `siteName`. A page's own value wins |
| `branding` | Branding set values written as given (`ButtonBorderRadius`, `TextColor` and the rest) |
| `headTokens` | More `--ftk-site-*` tokens for the head, such as `--ftk-site-radius-card` |
| `authenticationType` | `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED` opens the site to guests; `AUTHENTICATED` keeps it to signed-in members |
| `pages[]` | Per page, matched by `urlName` to `--page`: `title` (when the page has none), `recordObject` (builds the object's record page, as `--record-object` would; the command line wins), `audience` (`guest`, `portal`, `internal`: who sees it). `route` and `currentUrl` are for the canvas |
| `edition` | `paid` or `free`, from `flow-tool-kit.json`. On `free`, a record page or repeater on any object other than Account, Contact, Case, Lead or Form Template is named as a deviation: it shows a notice instead of its content |
| `audiences` | The default audience for pages without their own. A page a guest sees gets the reminder to set up guest access (SKILL.md, Step 5); a members-only page should land on the login page in the logged-out render check |
| `assets` | Ignored by the build. Its `file` entries are the review canvas's copies (for the brand kit's images, the cropped copies in `_brand/<slug>/canvas/`) and `blob` the canvas uploads. The site uses the images already in the org, by Asset File name |

## brand-kit.json

With `--brand-kit`, the brand kit fills only what `site.json` and the page leave empty (the page wins, then `site.json`, then the kit):

| Brand kit key | Becomes |
|---|---|
| `colors.primary` | Palette `$primary` and `$brand`; the theme's brand (branding set accent, `--ftk-site-brand-override`) |
| `colors.accent` | Palette `$accent`; `--ftk-site-accent-override` |
| `colors.heading`, `colors.background` | Palette `$heading`, `$background` |
| `fonts.bodyStack`, `fonts.headingStack` | `--ftk-site-font-override`, `--ftk-site-heading-font-override` (the family name when no stack is saved) |
| `fonts.href` | The web font link |
| `style.buttonRadius` | The branding set's `ButtonBorderRadius` |

The kit's primary and heading colors already pass 4.5:1 against white, so text in them stays readable on white.

## Images

Blocks name images by Asset File name (`backgroundImageAsset`, `imageAsset`, `iconImage`, `logo`), never by file. The generator lists every name a page uses: packaged ones (`FlowToolKit__Background_Farmland_Aerial`) are in every org with Flow Tool Kit; the organization's own must already be public Asset Files in the org. brand-kit saved the originals there; the files in `_brand/<slug>/canvas/` are only cropped review copies for the canvas, so never upload those. New photos go through `scripts/asset_files.py` (SKILL.md, Step 3).

## A folder of block files

The generator also reads a folder instead of `page.json`, and `--blocks <folder>` writes one:

- `NN-name.json` per item, in page order. Files with the same number (`04a`, `04b`) share section 4, one column each.
- `_sections.json`: per number, `widths` out of 12 (`{"04": {"widths": ["7", "5"]}}`), `attributes`, and `columns` when a column stacks several files.
- A design block's file is its props. `_component` names another component (its other keys are attributes), `_kind` another item kind, `_recordId` pins it to a record.

The folder is an output of `page.json`: a hand edit there is overwritten the next time the page is generated from `page.json`.

## The format, and design-to-blocks

This is the format design-to-blocks writes (its `references/page-json.md`). `tests/skills/build-site-pages/fixtures/riverside-sample/` in the plugin repository is a copy of its worked example, and the tests build it unchanged. Two things that example shows:

- **Every listing arrives with its card.** Each Repeater carries its object, `card`, filter, sort and empty message, so the example builds as it is. A Repeater drawn only from sample records, with no `card`, is refused, naming the section: design-to-blocks refuses it too.
- **A design drawn for Aura builds on LWR.** The sample's record page is drawn as `site: aura`; on an LWR site its sections and standard components are converted and the generator says so. Its `layout: customerService` and `footer` are Aura-only and named as deviations on LWR.

A key the build does not know is ignored, so check a new key reaches the site before relying on it.
