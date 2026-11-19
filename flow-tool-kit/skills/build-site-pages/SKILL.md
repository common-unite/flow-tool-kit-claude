---
name: build-site-pages
description: Builds pages designed with the Flow Tool Kit (FTK) Site Blocks design system into a real Experience Cloud site (LWR first, Aura too) and proves they render. Turns design-to-blocks' page.json and site.json into the site's views and routes, applies the brand (branding set, head design tokens, web font) from the site file or the brand kit, puts FlowToolKit LWR Support in the Theme Footer, deploys, sets up guest access, publishes, and checks every page headless as a logged-out visitor at desktop and phone width. Use after design-to-blocks, when someone says "build these pages in our site", "put this design on the portal" or "publish the landing page", or whenever block JSON must reach a site without placing each block by hand in Experience Builder. Deploying and publishing need Claude Code.
---

# Build Site Pages

A page design in, a published site page that a visitor can load out. The design is data (`page.json`), so nothing is placed by hand in Experience Builder and a rerun with the same design writes the same files.

Four facts decide most of what goes wrong with an LWR site. Hold them through every step:

1. **An LWR site serves what it had at its last publish.** A deploy, a component change or a Flow Tool Kit upgrade is not on the site until the site is published again. Every change ends with a publish.
2. **Builder's preview is not proof.** It renders from the draft, signed in, inside a frame. The proof is the published page, loaded logged out (Step 7).
3. **FlowToolKit LWR Support goes in the Theme Footer of every LWR site that shows a form, then publish.** Since Winter '27 the LWR publisher bundles only components a page reaches by a static reference, and Flow Tool Kit loads its forms, modals and repeaters by name. Without it a form fails to load ("could not be loaded", LWR3008).
4. **Your own components that a form loads by name need their own support component beside it.** A custom section component (build-custom-lwc) is invisible to the publisher too: a small component that imports each one goes in the Theme Footer next to LWR Support.

## Where it runs

| Where | What this skill can do |
|---|---|
| Claude Code, local or on the web, with the Salesforce CLI and Node | Everything: pull the site, generate, deploy, guest access, publish, the headless render check |
| claude.ai chat | Read and check `page.json`, explain what the build will write, convert photos (`scripts/asset_files.py convert` runs in the sandbox), and generate the site files when the person attaches the retrieved site folder as a zip. Say plainly, in one line, that **deploying and publishing need Claude Code**, and hand over the files |

On Claude Code on the web, install what is missing first: `npm install --global @salesforce/cli`, sign in with `sf org login web` (or `sf org login sfdx-url` when no browser can open), and `npx -y playwright@1.47.2 install chromium` for the render check (allow the npm registry in the environment's network settings).

## Before you start

- **The design.** `_site/<slug>/site.json` and one `_site/<slug>/pages/<urlName>.json` per page, from design-to-blocks. A folder of block files (`blocks/<page>/NN-name.json`) also works. The format, and how each key reaches the site: [references/inputs.md](references/inputs.md).
- **The project config.** Read `flow-tool-kit.json` at the project root (`_shared/standards/project-config.md`): the org's edition and its audiences. A page for guests needs Step 5; a page only for signed-in members does not. Ask only what the file lacks, and save the answer there.
- **The brand.** `site.json` carries the palette and theme design-to-blocks drew with. When it does not, pass the brand kit's `brand-kit.json` (`_shared/standards/brand-kit.md`): its colors, fonts and button corners fill the gaps.
- **The site exists** in the org (Setup, All Sites), Flow Tool Kit is installed, and the person has named the org to build in. The skill builds in that org; it never chooses one. Experience Builder sites are created in Setup or with `sf community create --name "<Site name>" --template-name "Build Your Own (LWR)" --url-path-prefix <prefix> --target-org <org-alias>`.
- **Forms on the page.** A Form Slot builds only once its Form Template exists (form-design, then build-template). Until then the generator leaves it out and says so.
- **A simple form or a record display.** A Contact Us form creating a Case, a mailing-list signup creating a Lead, or Account or Campaign details on a page need no Form Template: follow new-record-page-form's pattern and place the package's Form (Dynamic Component) as a `component` item (`FlowToolKit:lightningRecordFormDynamicDisplay`, its settings under `properties`).

## Step 1: Pull the site and keep a copy

```bash
sf project retrieve start --metadata "DigitalExperienceBundle:site/<Site1>" --target-org <org-alias>
cp -R force-app/main/default/digitalExperiences _site/<slug>/backups/<yyyy-mm-dd>/
```

`<Site1>` is the bundle's folder name (the site's API name, usually the name with a `1`). First set `sourceApiVersion` in `sfdx-project.json` to the org's API version (`sf org display --target-org <org-alias>` shows it): a site pulled at an older version can carry properties that version's deploy refuses. People edit sites in Builder without source control, so the org is the only copy of their work: pull again right before the deploy and compare (`diff -rq`) the two pulls. For an Aura site the type is `ExperienceBundle:<Site1>`.

## Step 2: Generate

Once per page, from the project root:

```bash
python3 <skill>/scripts/design_to_site.py _site/<slug>/pages/<urlName>.json \
  --bundle force-app/main/default/digitalExperiences/site/<Site1> --page <urlName> \
  --site-config _site/<slug>/site.json [--brand-kit _brand/<brand>/brand-kit.json]
```

Add `--entire-site` on one run (usually the home page) to write the site-wide parts: the header and footer, FlowToolKit LWR Support in the Theme Footer, the branding set, the head tokens and web font, public access and the navigation menu. Add `--footer-support c:<component>` for each support component of your own (fact 4). A page whose `site.json` entry has a `recordObject` is built as that object's record page; `--record-object <Object>` does the same for a page without one.

What it writes, and why:

- **The page's view and route.** Each section becomes an LWR section with its column widths, each item its component: a design block (`FlowToolKit:siteDesignBlock`), a divider, rich text, an HTML Editor, tabs, a form, a repeater. The page `home` fills the site's own Home page.
- **Record pages** get the object's detail, list and related-list routes together, because Builder deploys an object page only as that set. Every record-bound component reads `{!Route.recordId}`. [references/listings-and-record-pages.md](references/listings-and-record-pages.md).
- **The Theme Footer** holds FlowToolKit LWR Support once (and a Section to hold it, on a new site whose footer has none).
- **The brand.** The branding set's accent (and its darker shades) is the brand color the blocks read; the `--ftk-site-*` tokens go in one `<style>` in the head, the web font in one `<link>`; both are replaced on every run, never stacked.

It refuses, naming the section, a Repeater without its object and card and a section whose columns are not one to four adding to 12. It prints the files it wrote, how many Flow Tool Kit components the page should show (Step 7 checks that number), the page's audience from `site.json`, the images it names (the organization's own must be public Asset Files in the org), the deploy and publish commands, and each **Deviation**: something the site cannot take as drawn, including a record page or repeater the free edition will not show. Every deviation goes in the report.

## Step 3: Photos the page needs

Photos a guest loads must be public Asset Files. A brand kit's images already are. For new ones:

```bash
python3 <skill>/scripts/asset_files.py --manifest _site/<slug>/photos.json --assets-dir force-app/main/default/contentassets convert <photo folder>
```

The manifest is `{"folder": "<Asset Library folder>", "photos": [{"name", "label", "description", "source", "width"}]}`. Each photo becomes a progressive JPEG under 700 KB at its width, with metadata that makes it public. Deploy the folder with the site, then `finish --target-org <org-alias>` sets titles and descriptions and files them in the Asset Library folder, where the Flow Tool Kit image picker lists them. `upload --target-org <org-alias>` does both for an org you do not deploy source to. Record who owns each photo and where it came from.

## Step 4: Deploy

1. Compare the fresh pull with your copy (Step 1). If someone changed the site in between, merge their change into the bundle before going on.
2. Show the person what changes: `diff -rq _site/<slug>/backups/<date>/digitalExperiences force-app/main/default/digitalExperiences`, usually the page's view and route, plus the theme layout, branding set, head markup and site for an `--entire-site` run. Confirm the org they want it in.
3. Deploy with the command the generator printed, validating first with `--dry-run`. In an org with source tracking (a scratch org), a deploy can stop on "conflicts detected" when the org's copy changed since the pull. Pull again and compare: when only `_meta.json` files differ (a newer API version adds a `contentKey`), take the new `_meta.json` files and deploy with `--ignore-conflicts`; when content differs, merge it first.

On LWR a page deploys on its own: its view and route folders change only that page, and pages your folder lacks stay in the org. Never deploy an incomplete whole-site folder (`DigitalExperienceBundle:site/<Site1>` or the site folder as a source dir): that sends every file, so every file must be there. An Aura site deploys as one bundle, so the whole pulled and compared folder goes. The navigation menu deploys after the pages it links to.

## Step 5: Guest access (pages a guest sees)

Skip for a site only signed-in members use. Otherwise, in order:

1. Field and object access for the guest profile, a guest sharing rule on each object a page shows, and the Network's guest file access. [references/guest-access.md](references/guest-access.md) has each change; **flow-access-fix** checks a form's guest access end to end.
2. Public access on the site: `"authenticationType": "AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED"` in `site.json`, written by the `--entire-site` run.
3. The guest user's permission sets, the guest sharing rules and the publish, in one helper:

```bash
python3 <skill>/_shared/sf/guest_site_setup.py "<Site name>" --permsets FlowToolKit__Form_Flow_User[,<more>] \
  [--sharing force-app/main/default/sharingRules] --target-org <org-alias>
```

## Step 6: Publish

```bash
python3 <skill>/_shared/sf/site_publish.py "<Site name>" --target-org <org-alias>
```

It waits for the publish job and prints one line with the site's public address (where its pages live, `https://<domain>/<prefix>`). `sf community publish` alone only starts the job; never treat it as done. Publish after every deploy the site shows, after every Flow Tool Kit upgrade and after any component change (fact 1). The site must also be active (Status Live in Setup, All Sites), or its public address sends visitors to a login page.

## Step 7: Check the published page

```bash
node <skill>/scripts/render_check.cjs https://<site domain>/<prefix>/<urlName> [more pages] --expect <n>[,<n>] --shots _site/<slug>/checks/<yyyy-mm-dd>
```

Point it at the public address, never the Builder or live-preview address. Each page loads in a fresh headless browser with no cookies (a logged-out guest) at 1440 and 390 px wide. It reports the width the page really applied, sideways scroll, broken images, console errors, failed requests, a landing on the login page, a component that failed to load, the Flow Tool Kit components rendered against `--expect` (the generator's number), empty ones, and whether LWR Support is on the page. Exit 1 on any FAIL. [references/render-check.md](references/render-check.md).

Then look at the screenshots, every page at both widths, top to bottom: each section is there, in order, in the brand, and nothing is cut off or overlapping. A FAIL row is fixed (and the site published again) or named as a deviation. Say "checked as a guest" only with this table. A page behind a login reports the login page; checking it as a member needs a person to sign in as a test member, so ask before doing that.

## Step 8: Report

- The pages built, with their public addresses, and the render check table.
- Each deviation the generator printed, and each FAIL left open with its reason.
- What the person still owns: content to collect (photos, copy marked `[CONFIRM: ...]`), Trusted URLs for a web font, and that every later change or upgrade needs a publish.
- Anything new learned about the site (a value a block refused, a step done by hand twice) in `_site/<slug>/notes.md`, so the next build does not rediscover it.

## LWR and Aura

LWR is the default and the shape everything above describes. An Aura site takes the same blocks with different metadata, no publish freeze and no LWR Support: [references/lwr-and-aura.md](references/lwr-and-aura.md).

## Files

| File | What it is |
|---|---|
| `scripts/design_to_site.py`, `scripts/site_views.py` | The generator: `page.json` or a block folder to the site's metadata |
| `scripts/render_check.cjs` | The headless render check, and (at its top) how it finds Playwright and Chromium |
| `scripts/asset_files.py` | Photos to public Asset Files |
| `_shared/sf/site_publish.py`, `_shared/sf/guest_site_setup.py` | Publish and wait; the guest user's permission sets, sharing rules and publish |
| `_shared/standards/` | Naming, documentation, the project config and the brand kit keys |
| `tests/skills/build-site-pages/` (plugin repository only) | `python3 tools/run-skill-tests.py build-site-pages` from the repository root |
