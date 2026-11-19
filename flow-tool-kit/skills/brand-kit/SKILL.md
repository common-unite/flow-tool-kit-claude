---
name: brand-kit
description: Builds an organization's optional brand kit for Flow Tool Kit (FTK) forms and sites from its website (logos, colors, fonts, corner style, photos and tone of voice), has the person pick from everything found, and saves the confirmed kit in their Salesforce org for reuse: images as public Asset Files in the Asset Library, the brand's style values in the org's Form Style defaults (only where blank), and brand-kit.json beside them. Use when ftk-start's brand kit question gets a yes, when a saved kit needs updating because the website or brand changed, or when someone asks to "pull the branding from this website", "scan our site for colors and logos", "set up our brand for forms" or "use a different brand for this form". Works in Claude Code and in claude.ai chat.
---

# Brand Kit

The look and voice of one organization, gathered once from its website, chosen by a person, and saved in the org so every later form, email and site page starts from it. It is **optional**: without a kit, forms use Flow Tool Kit's default style and nothing here runs.

The kit is saved **the moment it is confirmed**, in one step, before any form is designed. It never waits for a form. Its format and where each part lives are in `_shared/standards/brand-kit.md`; this skill is the one that writes it.

## Where it runs

| Surface | What it does |
|---|---|
| Claude Code, on your computer or on the web | Everything: the whole-site crawl and stylesheet scan, an optional headless scan of the rendered page, thumbnails for the picker, the downloads, and the save to the org through the Salesforce CLI |
| claude.ai chat with code execution | Everything the scripts do without reaching the site. The website is read with the web fetch tool when the sandbox cannot reach it ([references/site-scan.md](references/site-scan.md), "In chat"). The review is a file or an artifact. The save goes through a Salesforce connector that can create and update records; the scripts write each call for it |
| No org connected | The kit is built and confirmed as files; save it to the org later with the same step |

Python 3. `site_crawl.py`, `site_styles.py`, `brandkit.py`, `make_site_copy.py` and `orgsave.py` use the standard library only. Thumbnails, format conversion and the banner crop use Pillow (`pip install pillow`); without it the scripts say what they skipped. Run every script by its path in this skill's `scripts/` folder.

## Before you start

1. **Was it chosen?** ftk-start asks once per org and saves the answer in `flow-tool-kit.json` (`orgs.<org Id>.brand_kit.choice`: `use`, `update`, `new` or `none`; format in `_shared/standards/project-config.md`). Run this skill for `new` and `update`, or when the person asks directly. For `use`, nothing runs: the other skills read the saved kit.
2. **Is a kit already saved?** org-catalog's catalog says (`brand_kit.found`: `saved`, `partial`, `logo only` or `none`). For an update, start from the saved `brand-kit.json` (`--previous`), so the person changes only what changed.
3. **The two addresses**: the organization's main website, and the page for the program the form serves (the program page's words lead the form's copy). Ask only for what you do not have. Confirm what you found rather than asking open questions: "I'll read www.example.org and its Volunteer page at /volunteer/. Right?"

Work in the project folder `_brand/<slug>/`, where `<slug>` is the brand's name in lowercase with hyphens (`_brand/riverside-community-garden/`). One folder per brand; an org with several brands has several folders. If the project is under version control, keep `brand-kit.json`, `picks.json` and `site-copy.md`, and leave out the generated `brand-picker.html` (it embeds every thumbnail), `canvas/` and the crawl files.

## 1. Read the website

```bash
python3 scripts/site_crawl.py https://www.example.org/ --program https://www.example.org/volunteer/ --out _brand/<slug>/site-crawl.json
python3 scripts/site_styles.py --crawl _brand/<slug>/site-crawl.json --out _brand/<slug>/site-styles.json
python3 scripts/make_site_copy.py _brand/<slug>/site-crawl.json _brand/<slug>/site-copy.md
```

- **The whole site, never a sample.** The crawl follows every page the navigation links to (header and footer menus, every level) and keeps every image, tagged with its page, measured, grouped (logo, banners, site photos, people, partner logos, icons, documents) and given a size fit (banner, tile, square). Never trim the page list to "the important ones"; the picker is where the list narrows.
- **Colors and fonts from the stylesheets, no browser.** `site_styles.py` reads the site's own CSS: where each color is used, the fonts by role, button and input corners, heading weight. It leaves out a site platform's untouched preset palette and lists what it left out.
- **A rendered-page scan is optional and asked first**: "Do you want exact colors and fonts from the rendered page? That needs a headless browser in Claude Code (or a browser tool you allow)." Only on a yes; how: [references/site-scan.md](references/site-scan.md).
- **Exit code 3** from either script means the site cannot be reached from here (usual in a chat sandbox). Use the web fetch path in [references/site-scan.md](references/site-scan.md).
- A site that answers slowly or with 429 is crawled more slowly by itself; a 403 on images means bot protection, handled at the download step.

## 2. The review

```bash
python3 scripts/make_picker.py _brand/<slug> [--rendered render-home.json] [--previous <saved brand-kit.json>]
```

It writes `candidates.json` (every candidate and a best guess for each pick), `brand-picker.html` and `brand-review.md`. Hand the person whichever fits where they are:

- **`brand-picker.html`**: one self-contained page with every image embedded as a thumbnail. In Claude Code, tell them to open the file in their browser (it needs no server); where artifacts can be published, it can also be published as one. They pick, then **Copy my picks** (paste it back) or **Download picks** (`picks.json`).
- **`brand-review.md`**: the same choices as a numbered list, for chat and voice: "logo 3, banner 12, brand color 2, heading font 1".

The picks: logo, alternate logo, favicon, banner, tile, more photos to load, brand color, heading color, accent, background tint, body and heading fonts, corner roundness, button corners, and tone of voice. Details, and the picks file format: [references/review-and-picks.md](references/review-and-picks.md).

Write the **voice** yourself from `site-copy.md` (a few adjectives, three or four "do" and "avoid" lines, sample headings and button labels in the site's own words) and show it with the picks for the person to correct. Never invent wording the site does not support.

## 3. Confirm the kit

```bash
python3 scripts/brandkit.py confirm _brand/<slug>/candidates.json _brand/<slug>/picks.json --out _brand/<slug>/brand-kit.json [--previous <saved brand-kit.json>]
```

It writes `brand-kit.json` in the shared format and `picked-files.json` (each picked image's address), and prints notes to pass on:

- **Contrast.** The brand color and the heading color must reach **4.5:1 against white**, because white text sits on buttons and the banner and headings sit on white. A lighter color is darkened in the same hue until it does; the original is kept as the accent, unless the person picked an accent. Say so: "Your green #7fbf6a is too light for button text, so buttons use #3d6f31; #7fbf6a stays as the accent."
- **People in photos.** A picked photo of an identifiable person needs the organization's permission before it goes public. Ask.
- **Fonts.** A web font shows only where the page loads it. On an Experience Cloud site, add the font link to the site's head markup; in Lightning pages the fallback in the stack (Arial or Georgia) shows. The kit stores the full stack for that reason.

Show the person a short summary (name, colors with their roles, fonts, which images, tone) and ask "Save this kit to your org?". `brandkit.py validate` must pass before saving.

## 4. Download the images

```bash
python3 scripts/brand_assets.py _brand/<slug> [--file logo=<path>]
```

Only the picked files, into `assets/`, converted to PNG or JPEG when the site serves WebP (the Flow Tool Kit image picker lists PNG, JPG and SVG only), at most 2000px wide, with an MD5 for each. `canvas/` gets the review copies a design canvas uploads (the banner cropped to 3:1 around its focal point, SVG fills written inline). A site that refuses downloads (403): ask the person for the file and pass `--file role=path`. In chat, files the person uploads go in the same way.

## 5. Save to the org, in one step

Claude Code:

```bash
python3 scripts/orgsave.py collect --org <org-alias> --out _brand/<slug>/org-state.json
python3 scripts/orgsave.py plan _brand/<slug> --state _brand/<slug>/org-state.json
python3 scripts/orgsave.py apply _brand/<slug> --org <org-alias> --state _brand/<slug>/org-state.json
```

Show the plan before applying: which images are new and which the org already has, which Form Style fields get the brand, which keep the org's own value, and the brand file. Apply when the person says go ahead. In chat with a Salesforce connector: `orgsave.py queries` lists the reads, `orgsave.py plan ... --inline` gives every write as a REST call to run in order. The details, and what was proven in an org: [references/saving-to-the-org.md](references/saving-to-the-org.md).

What it does:

1. **Images** become **public Asset Files** in the org's **Asset Library**, labelled so a person recognizes them, never static resources. An image the org already has (same file checksum) is reused, made public and filed in the library if it is not. Only then can the FTK image picker list it. When the library uses folders, the images go in a folder named for the brand, which the picker shows as a group.
2. **Style values** go into the org's **Form Style defaults** (Form Builder's Global Styles), **add-only**: a blank field takes the brand's value, the same value does nothing, a different value stays and is reported. Only for the org's default brand (`orgDefault`). The logo goes into **Default Logo** and its alt text the same way, so every template without its own logo shows it.
3. If the org refuses that write, the brand is not lost: `global-styles-import.json` is written for Form Builder, Global Styles, **Import**, with the org's current values first, because Import replaces every saved org style. The person also sets Default Logo there with Select Image.
4. **`brand-kit.json`** is saved last, with the real asset names, as a private file in the Asset Library titled `brand-kit` (`brand-kit-<slug>` for a brand that is not the org default). Saving again adds a version.

Then record the choice in `flow-tool-kit.json` (`brand_kit.choice` and `found`), and check the result as the image picker does: `SELECT ContentAsset.DeveloperName FROM ContentDocument WHERE Id IN (SELECT ContentDocumentId FROM ContentWorkspaceDoc WHERE ContentWorkspace.Name = 'Asset Library') AND ContentAsset.IsVisibleByExternalUsers = TRUE AND FileType IN ('PNG','JPG','JPEG','SVG') AND Owner.UserType = 'Standard'` lists every new asset.

## 6. Hand off

- **form-design**: `python3 scripts/brandkit.py plan-style _brand/<slug>/brand-kit.json --plan-dir _forms/<form-slug>` prints the `style`, `assets`, `images` and `brand_board` keys for `plan.json`, in its key names. The program voice (`programs/<program-slug>.md`) sets the form's words when there is one: page descriptions, section subtitles, question labels, help text and the confirmation message; otherwise the kit's voice and `site-copy.md` do.
- **build-template** reads the plan's style and puts any value the org kept differently on that template's Style Overrides, and the logo on Logo Override when the org's Default Logo is another brand's.
- **build-email-templates** reads `brand-kit.json` (colors, fonts, logo and banner names, brand name) for the letterhead.
- **design-to-blocks** and **build-site-pages** use the same colors, fonts and Asset Files on a site.

## Program voice, per form

The brand kit is the organization's look and general voice, saved once per org. Each form also serves a **program**, and ftk-start's gap round asks for it: "What program is this form for?", with the program page's address if they have one. When they name one, write that program's voice so the form, its emails and any site blocks sound like the program, not only like the organization:

1. **Read the program page.** If the kit's crawl already has it (`site-copy.md`, "Program page, in full"), use that. Otherwise read the page with the web fetch path in [references/site-scan.md](references/site-scan.md), or, for a page on the organization's site, crawl again with `--program <address>` and rerun `make_site_copy.py`.
2. **Write `_brand/<slug>/programs/<program-slug>.md`**: the program's own name and the names it uses for people, steps and things (applicants or participants, sessions or shifts); three or four "do" and "avoid" lines; and sample copy in its words for an intro description, a short blurb, a site or form block heading, question labels and help text, and a confirmation message. Quote or closely follow the page; never invent claims, dates, prices or contacts it does not state.
3. **Show it** with the gap round's other answers, for the person to correct, then record its path in the plan's `intake` (`program`).

No program named, or no page for it: the forms use the organization's general voice from the kit, and without a kit, warm and plain. This needs no saved kit: a program voice can be written for an org that chose no brand kit.

## Several brands in one org

The org's Form Style defaults hold one brand, the org default. Every other brand gets its own folder and its own saved `brand-kit-<slug>` file with `orgDefault: false`: its images are loaded and its file saved, but it changes no org style. A form for that brand gets its colors, fonts and logo on the template (Style Overrides, Logo Override) from build-template, never from a new Form Theme.

## Common mistakes

| Mistake | Fix |
|---|---|
| Home page only, or a handful of pages | Every page in the navigation; the picker is where it narrows |
| A platform's preset palette taken as the brand | `site_styles.py` leaves untouched presets out and lists them in the review |
| A light brand color on white buttons | Darkened to 4.5:1 by `confirm`; the original kept as the accent |
| Waiting for a form before saving the kit | Save at confirmation, in one step; a confirmed kit never waits |
| Brand images as static resources, or uploaded but outside the Asset Library | Public Asset Files in the Asset Library; check with the image picker's query |
| Loading an image the org already has | `orgsave.py` matches checksums and reuses it |
| Overwriting the org's style values | Add-only; a different org value stays and is reported |
| A new Form Theme for a brand | Never: the default theme yields to the style values; a theme of its own would freeze them |
| A web font that never shows | Load it in the site's head markup; the stack's fallback shows elsewhere |
| A photo of identifiable people used without asking | Ask for the organization's permission first |
