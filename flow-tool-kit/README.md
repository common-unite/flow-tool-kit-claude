# Flow Tool Kit

Turn any form you already have into a working Salesforce form. Bring Flow Tool Kit a FormAssembly link, a PDF, a Word document, a Google Form or just a description, and Claude reads it, asks only what is missing, draws the design for your review, and builds the Form Template, the emails and the flows that save every answer to the right records. The same skills build record-page interfaces, Experience Cloud pages and sites, and advanced Flow screen solutions on Flow Tool Kit, in any Salesforce org. These are the skills the makers of Flow Tool Kit use in their own client work. They work with the free and paid editions.

## What you need

- **A Claude plan** with skills, and code execution turned on for claude.ai chat.
- **The Design feature on your claude.ai account** to see and comment on the review canvases. Without it the build still runs, and you get a plain review page instead of a canvas.
- **Claude Code and the Salesforce CLI** (`sf`) for deploys and anything that writes metadata to an org. In claude.ai chat, a Salesforce connector added to your account reads the org, and the skills hand over the files for the steps that need Claude Code.
- **A Salesforce org with Flow Tool Kit installed** (paid or free edition; Claude asks once per org which one). A scratch org or sandbox is the right place to start.
- Python 3. Node.js only for the optional headless render checks.

## Install in Claude Code

```bash
claude plugin marketplace add common-unite/flow-tool-kit-claude
claude plugin install flow-tool-kit@common-unite
```

Each skill then runs as `/flow-tool-kit:<skill-name>`, or Claude picks it up when your request matches.

## Install in claude.ai

A plugin added to your claude.ai account works in chat, in Cowork, and in Claude Code signed in to the same account. Install it from its marketplace:

1. Open **Customize > Plugins** and select **Add marketplace** (in the **Add** menu).
2. Paste `https://github.com/common-unite/flow-tool-kit-claude` and add it.
3. Select the **flow-tool-kit** plugin and select **Install**. Open it to check that its 26 skills are listed (25 that do the work, and ftk-design-system, the design-system library they read).

Updates come from the marketplace: select **Check for updates** on it to pull a new release, or turn on **Sync automatically**.

**Team and Enterprise:** an Owner may need to allow it. Members see the marketplace option in **Add** only while **User-created skills** is on in **Organization settings > Plugins & skills > Policy**, and an Owner can limit which marketplaces members add.

## The design systems

The review canvases draw with two design systems, FlowToolKit Forms (form components) and FlowToolKit Site Blocks (site design blocks). Both ship inside this plugin, in its **ftk-design-system** skill, at the version that matches the plugin: there is nothing to download, attach or unpack, in Claude Code or in claude.ai chat (Team and Enterprise included), and each plugin update brings the matching kits. The first time a request needs one, ftk-start installs your own copy into your claude.ai account from those files. Ask Claude to "check my Flow Tool Kit design systems" to see the version this plugin ships and the one you have installed. Details: [The design systems](https://common-unite.gitbook.io/flow-tool-kit-or-form-and-table-builder/flow-tool-kit-for-claude/flow-tool-kit-for-claude#the-design-systems).

## Try it

Start with any of these. The first three need no org.

1. "Design a two-page volunteer sign-up form for a community garden with Flow Tool Kit: contact details, availability and a photo release. Show me the review canvas."
2. "Here is our paper registration form as a PDF. Read it and list every question, its answer type and where the answer should go in Salesforce." (Attach any PDF form.)
3. "Pull the logo, colors and fonts from our website, https://www.example.org, into a brand kit for our forms." (Use your own organization's site.)
4. "Map the Flow Tool Kit components and Form Templates already in my org, then build the volunteer form design as a draft Form Template." (Needs a connected org.)
5. "Check what an anonymous visitor can see on my Experience Cloud site." (Needs a connected org and a site you own.)

The **ftk-start** skill is the front door: describe the job in plain words and it runs the right skills in the right order.

## What it runs, sends and fetches

**No run-time download.** The design-system kits (FlowToolKit Forms and FlowToolKit Site Blocks: component bundles, libraries and the package photos) ship inside the plugin, in the ftk-design-system skill, so nothing is downloaded to draw a design. They are built for previews (minified, only the files the canvases, review pages, render checks and your own Design System use); their third-party licences are in that skill's `THIRD_PARTY_NOTICES.md`.

Everything runs in your own Claude session, against your own Salesforce org, your own accounts and the websites you name. The plugin has no server of its own. Nothing is sent anywhere other than the places listed here, and Common-Unite collects no data: no telemetry, no analytics, no usage reports.

**Across every skill**

- **Salesforce:** the Salesforce CLI (`sf`) and Salesforce APIs, run as you, against the org you signed in to (`*.salesforce.com`, `*.force.com`, `*.site.com`, `*.salesforce-sites.com`). In chat, the Salesforce connector you added does the same reads.
- **Review canvases:** published as Design artifacts in your own claude.ai account, from design systems installed into that same account. Never from or to anyone else's account.
- **Google Fonts:** the review canvases and review pages load their web fonts from `fonts.googleapis.com` and `fonts.gstatic.com`.
- **Optional tools, installed only if you choose to:** Playwright `1.47.2` (pinned, `npx -y playwright@1.47.2 install chromium`, which downloads Chromium from `playwright.azureedge.net`) for headless checks; Pillow for image resizing; `pypdf` or poppler's `pdftotext` for PDF forms; the Salesforce CLI from npm. Without them a skill skips that step and says so.

**By skill**

| Skill | What it runs, sends or fetches |
| :- | :- |
| brand-kit | Reads the public website you name (its pages, stylesheets, images and linked fonts), optionally renders those pages in headless Playwright to read colors and fonts, and saves the kit you confirm into your org as Asset Files and Form Style values through the Salesforce API. |
| form-migrate | Reads the source you give it: a public FormAssembly form page (`www.tfaforms.com` or your instance), the FormAssembly API with your own access token, a public Google Form (`docs.google.com`), or a web page you name. Reads your org's object and field definitions with `sf`. PDFs are read locally. |
| formassembly-capture | Calls the FormAssembly API with your own access token: the form list, each form's definition and connector list, and only with `--response-check` one response per form to read its submission date (the answers are dropped at once). An optional browser step saves the Salesforce connector pages from a FormAssembly window you signed in to yourself. |
| ftk-start, org-catalog, field-audit, repeating-data | Read your org's Flow Tool Kit records, metadata and object definitions with `sf`. ftk-start installs the design systems into your claude.ai account from the kits inside the plugin (nothing is downloaded). repeating-data only reads what the earlier skills wrote. |
| form-design, design-to-blocks | Draw the review canvas in your claude.ai account and, in Claude Code, check it with headless Playwright on your own computer. design-to-blocks may read pages of your organization's website that you name, with Claude's web fetch tool or a headless browser. |
| build-template, build-form-component, build-flow-section, build-repeater, build-table, convert-to-metadata, consolidate-sections, pull-form, new-mapping-flow, new-invocable | Read and write Flow Tool Kit records and metadata in your org with `sf` (queries, record updates, anonymous Apex, retrieves and deploys). |
| build-custom-lwc, new-record-page-form | Deploy and retrieve the component with `sf`, and run its Jest tests in your project with `npx sfdx-lwc-jest`. |
| build-email-templates | Deploys the templates and their flows with `sf`, and its image check requests each image address in the templates to confirm it loads. |
| build-site-pages | Retrieves, deploys and publishes your Experience Cloud site with `sf`, uploads its images as Files, and checks the live preview at desktop and phone width with headless Playwright. |
| flow-access-fix | Reads your org's flows, permissions and site settings with `sf`, deploys the fix you approve, and in Claude Code loads your form as a guest in a headless browser to prove it saves. |
| sf-guest-audit | Reads your org's sharing and site setup with `sf`. Its optional outside probe sends unauthenticated requests to the public address of a site you name, the way a visitor's browser would, and keeps only counts and names, never record values. An optional headless Playwright pass loads the same site as a guest. Run it only on a site you own or are engaged to test. |

**The FormAssembly token** is the plugin's one secret. Save it in the plugin's **FormAssembly access token** setting: it is marked sensitive, so Claude Code masks it and keeps it in your system's secure credential store, not in a settings file. The scripts read it from that setting where Claude Code passes it to them, and otherwise from the `FORMASSEMBLY_ACCESS_TOKEN` environment variable of your session. It is sent only to FormAssembly, never printed, never written to a file, and the capture's own check fails if any saved file contains it.

<!-- Screenshots to add (as committed images in this folder, shown with Markdown image syntax):
- The review canvas for a three-page form, desktop and phone artboards
- The field audit table beside the canvas
- A built Form Template in the org's Form Builder
- An Experience Cloud page built from site design blocks
- The brand kit picker
-->
