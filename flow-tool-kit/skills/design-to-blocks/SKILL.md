---
name: design-to-blocks
description: Use when an organization needs an Experience Cloud page, landing page, donation or program page, program portal, funding or volunteer listing, record page, microsite or a whole new site designed with the FlowToolKit Site Blocks design system (Flow Tool Kit's site design blocks, record cards and dynamic repeater), before build-site-pages builds it: "can you build a page in the site?", "can you design a new site?", "could you build a donation landing page?", "can you update our Experience Cloud site?". Reads the brand kit, the org's edition, audiences and platforms, draws page.json as a Design canvas with the real Site Blocks components at desktop and phone width, takes the review as comments pinned on the canvas, and hands page.json to build-site-pages. Also when a design someone else drew must become site design blocks, or a page needs custom markup in the HTML Editor component. Runs ftk-start's setup and brand-kit itself when they are missing, without asking.
---

# Design to Blocks

Designs Experience Cloud pages the way form-design designs forms: research and intake, a design as data, one review canvas drawn from it with the real components, review by comments pinned on the canvas, then the handoff.

**Requirement: the Design feature on the person's claude.ai account.** Whatever Claude plan they are on, the review canvas is a Design artifact, so the person needs Design turned on for their claude.ai account (in an organization, an admin may have to enable it) to see the design and comment on it. Without it the build still runs from `page.json`, but there is no visual canvas review, only the plain fallback page described under Where it runs. Say this at the start, before drawing, so nobody finds out after the work is done.

| Forms (form-design) | Sites (this skill) |
|---|---|
| form-migrate's `ir.json`, brand-kit, org-catalog | Intake: `intake.md` from the brand kit, the project config and the org catalog |
| `plan.json`, the design as data | `site.json` plus one `page.json` per page ([references/page-json.md](references/page-json.md)) |
| `draw_plan.py` draws the canvas | `scripts/build_site_review.py` draws it |
| Design canvas with FlowToolKit Forms | Design canvas with FlowToolKit Site Blocks |
| build-template builds from `plan.json` | build-site-pages builds from `page.json` |

`page.json` is the source of truth and the canvas is drawn from it. In a review a change goes into the JSON and only the affected artboards are redrawn; if the drawing were the source, the build would ship something nobody approved. Nobody edits the drawing by hand, and an edit made on the canvas anyway is pulled back into the JSON before the next redraw ([references/review.md](references/review.md)).

The worked example is `examples/riverside-sample/` (an invented community fund): a funding listing and a fund record page drawn to every house rule, with record cards, tabs with an artboard per tab, an empty state and one HTML Editor section. Start new sites from its shape.

## Where it runs

| Runtime | What works |
|---|---|
| Claude Code, local or on the web | Everything: the generator, the headless measure of every artboard, the render checks, server-side copying of the design system into the canvas (`--mode code`) |
| claude.ai chat (code execution on) | The generator with `--mode chat` (the design system's files are written from the kit the plugin ships in its ftk-design-system skill and published 16 to a call), the uploads and the publish. No headless browser: look at the canvas yourself before saying it is done |
| No Design type (some organizations turn it off) | `design/review.html`, one self-contained page with the same components at both widths (about 6 MB with the photos). Publish it as an ordinary artifact or hand it over as a file. It passes a headless render in Claude Code; it has not yet been tried as a published artifact from chat, so say so |

Python 3 standard library for every script. Node and Playwright (`npx -y playwright@1.47.2 install chromium` once; on Claude Code on the web, allow the npm registry in the environment's network settings) for the measure and render checks; without them the generator estimates heights and says so. Run every script by its path in this skill's `scripts/` folder, with `python3 -I`.

## Before drawing

1. **The project config.** `flow-tool-kit.json` at the project root (in chat: among the conversation's or the claude.ai Project's files), written by ftk-start. It holds the link to the person's own **FlowToolKit Site Blocks** design system (`design_systems.site_blocks.url`) and, per org, the edition (paid or free), the audiences (guest, portal, internal), the platforms and the catalog. No Site Blocks link: run ftk-start's design system step, which installs the person's own copy from the plugin's files (Forms first, then Site Blocks). Never use a design system from anyone else's account. You can still write `page.json` and `review.html` meanwhile.
2. **The org catalog.** org-catalog's `catalog.json` names the platforms (Outbound Funds, Nonprofit Cloud, NPSP, person accounts), the org's Form Templates (a Form Slot names one) and the saved brand kit. No catalog (no org connected): say so in one line and mark every Form Slot and Repeater object as a question.
3. **The brand kit**, if the person chose one: brand-kit's `_brand/<slug>/brand-kit.json` and its `canvas/` images. `start_site.py` reads it. No kit is fine: the palette falls back to the design system's defaults and the brand board marks the tone and copy to confirm.
4. **The design system.** In Claude Code read the person's design system (`project/README.md` and `project/Choosing-blocks.md` of the artifact in the config); in chat read `site-blocks/project/README.md` and `Choosing-blocks.md` in the plugin's **ftk-design-system** skill (its folder in any install layout: `python3 _shared/lib/siblings.py ftk-design-system`, run from this skill's folder). Each block card lists its numbered designs (Hero 01 to Hero 29 and so on), column limits and phone behaviour. A block, design or prop the README does not name cannot be built.
5. **The rules.** [references/house-rules.md](references/house-rules.md) (rich block use is the norm), [references/mapping.md](references/mapping.md) (design shapes to blocks, page patterns, the palette), [references/html-editor.md](references/html-editor.md) (custom markup), and `_shared/standards/documentation.md` for anything the build will describe.

## 1. Research and intake

Write what you learn into `_site/<slug>/intake.md` before asking anything; the format and the questions are in [references/intake.md](references/intake.md). In short:

- the organization's own site and the pages being replaced (read client-rendered pages with a headless browser in Claude Code, or the web fetch tool; an LWR page fetched as plain HTML returns only its title);
- three to five comparable organizations' pages, each mapped to Site Blocks design cards ("their stats strip is Stats Bar 07");
- a copy deck where every claim names its source and every unknown is written `[CONFIRM: ...]`; never an invented number;
- then one message of questions with what you found already filled in, so the person confirms rather than starts from nothing: the pages and who sees each one, the Repeater objects, filters and card fields (a Repeater cannot be built without them), record pages and their objects, the photos to collect, and who approves copy.

## 2. Draw the canvas

1. **Start the site folder** from what the project already knows:

   ```bash
   python3 -I scripts/start_site.py --slug <slug> --title "<Organization>" --page home="Home" --page funding="Funding" \
       --page fund="Fund page:/funding/:recordId:<Object_API_Name>"
   ```

   It writes `_site/<slug>/site.json`: palette, fonts, logo and photos from the brand kit (the images listed in `assets` for upload), the edition, the audiences per page, and the navigation. It prints what it took from where and what is still open, including the pages the org's platforms suggest.
2. **Write one `page.json` per page** under `_site/<slug>/pages/` ([references/page-json.md](references/page-json.md)). Start each page from the closest Page example card in the design system; give every section its `_design.job` and `_design.designCard`; copy the block JSON from that design card and change only words, images and palette colours. Header and footer go in `site.json` `page`, so one comment changes them on every page.
3. **Generate:**

   ```bash
   python3 -I scripts/build_site_review.py --site _site/<slug> [--mode chat]
   ```

   It refuses, naming the section, an unknown block type, a column set that is not one to four adding to 12, a Repeater without its object and card, and HTML Editor or Rich Content markup that runs code or loads another document. It draws a Brand artboard, each page at 1280 and beside it at 390, each `_design.states` entry, a Section jobs artboard with the handoff checklist, and a Content to collect artboard; it writes `design/publish-batches.json`, `design/uploads.json` and `design/review.html`. Its one-line summary counts handoff fixes, items to collect and errors; read every indented line under it and fix the house misses before publishing. Exit 3 means it drew everything but has no design system link to publish with.
4. **Create the canvas, upload the images, publish**: [references/canvas.md](references/canvas.md). The canvas serves an image only as an upload to it, so every image an artboard draws is uploaded first and recorded with `--record-blobs`.

## 3. Look at it before saying it is done

In Claude Code: `node scripts/site_review.cjs check _site/<slug>/design` renders `review.html` at both widths and screenshots every artboard into `design/render/`; after publishing, `scripts/site_review.cjs site` plays the canvas's own artboards ([references/canvas.md](references/canvas.md)). Open every screenshot: the checks measure, they do not judge. In chat, open the published canvas and look at every artboard. Check at least: every artboard top to bottom at both widths; section tags readable; the header and footer on every page; nothing cut off at the bottom; the HTML tag on each HTML Editor section and its markup fitting the phone width. Recheck after every publish, the last small one included.

## 4. Review

Comments pinned on the canvas are the review. Each round: pull any edits made on the canvas back into `page.json`, apply every open comment to `page.json` (or `site.json` for the header, footer, palette or brand), regenerate, publish once, then resolve what you applied: [references/review.md](references/review.md). When a comment states a general preference, add it to [references/house-rules.md](references/house-rules.md) for this project.

## 5. Hand off

The approved `site.json` and `pages/*.json` go to **build-site-pages**, which converts each page for the org's site type (LWR first, Aura too), writes the views and block files, applies the palette through the site's branding and head tokens, deploys with the person's yes and checks every section on the live preview. Before handing off:

- every Form Slot names its Form Template (build it with form-design and build-template first);
- a section that needs only a simple form (a Contact Us form creating a Case, a mailing-list signup creating a Lead) or a record display (Account or Campaign details) uses new-record-page-form's pattern, the package's Form (Dynamic Component) set up on the page, not a Form Template;
- every Repeater has its object, card, filter, sort and empty message (the generator refuses one without object and card), and the guest audience can read those records (flow-access-fix sets guest sharing; sf-guest-audit checks the exposure);
- every HTML Editor has passed its check, names its reason, and holds nothing the guest audience must not see;
- `intake.md` lists where the build will differ from the design and why (no segmented bar in a block, one photo instead of a mosaic, placeholder photos until the organization sends its own). The person sees this list with the preview.

## The HTML Editor

The standard **HTML Editor** component (LWR `community_builder:htmlEditor`, Aura `forceCommunity:htmlBlock`, one `richTextValue`) is the escape hatch for content no block covers: a stacked bar, an accessible schedule grid, a custom callout shape, a static embed-free graphic. Blocks come first: a page holds at most two, each names in `_design.reason` why no block does the job, and the markup is static HTML and inline styles only. No script, frame, form, event handler or outside image, ever; anything that needs code is a custom LWC (build-custom-lwc), and anything site-wide belongs to the site's head markup, which its admin owns. Everything in it is public to everyone who can open the page. When to use it, how an LWR site stores it, the guest, LWR and security constraints, and the worked example: [references/html-editor.md](references/html-editor.md).

## Done when

- `build_site_review.py` runs clean: no errors, every handoff and house check passes, or each miss is named in the page's `_design.notes` with its reason.
- Every section names its job and design card; no block sits at its defaults; images are package demo photos or the organization's own, uploaded to the canvas.
- Every HTML Editor passes `htmlcheck.py` and names its reason.
- The canvas has been looked at at both widths after the last publish, and the person has the canvas link (or `review.html`), `site.json`, `pages/*.json` and `intake.md`.
- Open items are in Content to collect, not hidden: `[CONFIRM: ...]` copy, sample records, Repeater objects and filters, Form Templates to build.

## Common mistakes

| Mistake | Instead |
|---|---|
| Editing the canvas and forgetting `page.json` | Change `page.json`; redraw. Pull canvas edits back before a review round |
| A page of block defaults | Start from a numbered design card and change only words, images and colours |
| Hand-written cards for records | A Repeater or record card on live records |
| A photo copied into the canvas as a file | Upload it (`asset: true`) and record its `/_blob/` url |
| Custom HTML where a block exists | A block; the HTML Editor only with a named reason, at most two a page |
| A script, iframe or form in the HTML Editor | A custom LWC, a Form Slot, or the site's head markup owned by its admin |
| Personal or internal data in markup on a guest page | Markup is public; record data goes through blocks and the org's sharing |
| Pointing at someone else's design system | The person's own copy, installed by ftk-start |
| A record page or Repeater on a custom object in a free org | Ask about the edition. On the free edition, blocks read records of Account, Contact, Case, Lead and Form Template only, and a Repeater's cards need an object a free form can use. A sandbox shows everything, so the limit appears only in the live org |
