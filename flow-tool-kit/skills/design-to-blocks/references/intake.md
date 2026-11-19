# Research and intake

Find out what the project, the org and the web already say before asking the person anything, then ask only what is left, in one message, with what you found filled in so they confirm rather than start from nothing ("I read the Funding page at example.org/grants: four funds, two open. Should the listing show only open funds?").

Write it all into `_site/<slug>/intake.md`. It is the record the design is checked against, and the place the deviations from the design are listed for the person at handoff.

## What the project already knows

| Source | What it gives the design | Written by |
|---|---|---|
| `flow-tool-kit.json` | The Site Blocks design system link; per org the edition (paid or free), the audiences (guest, portal, internal), the platforms and the catalog's path | ftk-start (format: `_shared/standards/project-config.md`) |
| `ftk-catalog/<org Id>/catalog.json` | Platforms (Outbound Funds, Nonprofit Cloud, NPSP, person accounts), the Form Templates a Form Slot can name, whether a brand kit is saved | org-catalog |
| `_brand/<slug>/brand-kit.json` and its `canvas/` images | Colours with their roles (already at 4.5:1 on white), fonts and their stacks, button corners, logo and photos by Asset File name, voice and sample headings | brand-kit (format: `_shared/standards/brand-kit.md`) |
| `_brand/<slug>/site-copy.md` | The organization's own words, page by page | brand-kit |

`start_site.py` reads the first three and writes `site.json`. Anything missing is a question, asked once: run ftk-start for the config, org-catalog for the catalog, brand-kit for the brand, or ask the edition and audience questions directly and record the answers in `flow-tool-kit.json`.

## Research

1. **The organization and its pages.** Its site, the pages being replaced (their addresses go in `site.json` pages as `currentUrl`), its programs and the records behind them. A client-rendered page (most LWR sites, most app-like pages) returns only its title to a plain fetch: read it with a headless browser in Claude Code, or the web fetch tool in chat, and save screenshots under `_site/<slug>/research/`.
2. **Three to five comparable organizations' pages, and three or four layouts worth borrowing.** For each: a screenshot and a short style brief (palette, white space, type, block rhythm), each part mapped to a Site Blocks design card ("their stats strip is Stats Bar 07").
3. **A copy deck.** Every claim names its source (the page it came from); every unknown is written `[CONFIRM: ...]`. No invented numbers, quotes or dates.

## The questions

Ask them in one message, each with what you found and your recommendation:

- **Pages and audiences.** Which pages, in what order, and who sees each: guests (anyone on the internet), portal users (signed in), or internal users. The audience decides what record data a page may show and what the HTML Editor may hold.
- **Records.** For each Repeater: the object, the filter (open funds only, this program's sessions), the sort, the card's fields and photo field, and the empty message. For each record page: the object and its photo field. A Repeater cannot be built without these. For guests, the records must be shared with the guest user (flow-access-fix).
- **Forms.** Which Form Template each Form Slot shows, or that one must be designed first (form-design).
- **Brand.** Use the saved kit, or which colours, fonts and photos to change for this site.
- **Photos.** Which the organization will send, and which stay package demo photos until then (listed on the Content to collect artboard).
- **Copy.** Who approves it, and which `[CONFIRM: ...]` items they can answer now.
- **Custom markup.** Anything in the design no block draws: name it, and say it would be an HTML Editor section (static markup, public to the page's audience) or, if it needs behaviour, a custom LWC.

Write each answer into `intake.md` in the person's words, with the date.

## The intake.md shape

```markdown
# <Organization> site: intake

## Pages
| Page | Route | Audience | Record object | Replaces |

## Records
<per Repeater: object, filter, sort, card fields, photo field, empty message>

## Brand
<kit used, and any change for this site>

## Research
<comparable sites, each with screenshots and the design cards it maps to>

## Copy deck
<each claim with its source; every unknown as [CONFIRM: ...]>

## Answers
<question, answer in the person's words, date>

## Where the build will differ from the design
<filled in during the review; the person sees it with the preview>
```
