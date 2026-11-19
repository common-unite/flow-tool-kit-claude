---
name: ftk-start
description: The front door for any Flow Tool Kit (FTK) work described in plain words. Use when someone wants a form built, moved or designed on Flow Tool Kit, for example "convert this FormAssembly form into a form template", "turn this Google Form or PDF into an FTK form", "turn this into a screen flow", "make these into form components", "design a grant application on Outbound Funds", "I need a three-page registration form with a signature", or "build a site page with this form". Reads the org first, asks the few setup questions once per org, shows a short plan, then runs the right Flow Tool Kit skills in order. Works in claude.ai chat and Claude Code.
---

# FTK Start

The entry point for building on Flow Tool Kit. A person asks in their own words; this skill reads the org, settles the few things only they can answer, shows a short plan, and then runs the specialist skills in the right order. They never need to know the other skill names.

It decides **what happens and in what order**. The specialist skills do the detailed work, and each one owns its own rules; never redo their steps here.

## Where it runs

| Surface | What works |
|---|---|
| claude.ai chat (code execution on) | Everything up to an approved design: org catalog (with a Salesforce connector), setup questions, design system install, reading a source or a brief, brand kit, `plan.json` and the review canvas. With a Salesforce connector that can create records, the Form Template records too |
| Claude Code (local or on the web) with the Salesforce CLI | All of the above, plus everything that deploys metadata: new fields, metadata form components, Flow Sections, custom LWCs, conversion flows, email templates, site pages, access fixes |

In chat, say plainly which steps of the plan need Claude Code, and hand over `plan.json` and the project config file: the same files build there without edits.

## The run

### 1. Read the project config

Read `flow-tool-kit.json` at the project root (format: `_shared/standards/project-config.md`). It holds the answers from earlier runs: the edition, audiences and brand kit choice for each org, and the links to this account's design systems. In chat, look for it among the files attached to the conversation or the claude.ai Project. Anything already answered is used, not asked again.

`scripts/ftk_config.py` reads and writes it the same way in chat and Claude Code: `missing <org-id> [--site]` lists what is still to ask or install, `set-org` saves the answers (it turns a 15-character org Id into the 18-character key), `set-design-system` saves a link, and `validate` checks the file.

### 2. Run org-catalog first, every time

Run the **org-catalog** skill before any planning or design, on every request, even when a catalog file exists: the org may have changed since. It lists the org's Form Components, Form Templates and their sections, the sections that repeat, the mapped forms per object, a saved brand kit, and the installed platforms (Outbound Funds, Nonprofit Cloud).

- No org connected (chat without a Salesforce connector): say so in one line, keep going, and mark every Salesforce target in the design `verify`. The design is still complete; the targets are checked when an org is connected.
- Record the org's Id and name in the project config before the questions.

### 3. Setup questions, once per org

Ask only when the project config has no answer for this org. Ask all three in one message, each with what was found and a default, so the person can answer "yes" to all of it (see Confirm, don't ask):

1. **Edition.** "Is this org on the paid or the free Flow Tool Kit edition? This decides whether forms are built on the records' own objects (Contact, Account, your objects) with Form Builder field mapping, or directly on Form Submission." No default can be read from the org: sandboxes and scratch orgs always run without limits, so the edition that matters is production's. If they do not know, use **paid** and mark it `assumed` in the config; their license page or Flow Tool Kit support can confirm.
2. **Audiences.** "Who fills in forms in this org: the public on a site (guest), signed-in site users (portal), internal staff? Pick all that apply." Default from the request and the catalog (a template on a site page suggests guest).
3. **Brand kit.** If org-catalog found a saved kit (style defaults with a brand color or default logo, or a brand file in the Asset Library): "I found a saved brand kit: <colors, font, logo name>. Use it, update it, or ignore it?" Default: use it. If none: "Do you want a brand kit from the organization's website (logo, colors, fonts, tone)? It is optional." Default: no, the forms use Flow Tool Kit's default style.

Save the answers to the project config right away. What they drive:

| Answer | Drives |
|---|---|
| Edition | The mapping preference in form-migrate, form-design, build-form-component, build-template and new-mapping-flow. **Paid:** forms on the target object, mapped to Form Submission fields with Form Template Mapping, and the packaged conversion flows run Apply Submission Field Maps; hand-built Transform rows only for calculated or combined values, Campaign Members and record types. **Free:** forms on Form Submission fields (free forms work only on Account, Contact, Lead, Case, Campaign, Campaign Member and the Flow Tool Kit objects), and the conversion flow's Transform maps each answer. Full standard: `_shared/standards/mapping-preference.md` |
| Audiences | Guest: flow-access-fix for the guest user (and its system-mode copies for Save Progress, Stages and resume), sf-guest-audit, and the guest form rules below. Portal: flow-access-fix for the portal profile or permission set. Internal: no site steps |
| Brand kit | Use: form-design styles from the saved kit. Update or new: run **brand-kit** now, before design, so the kit is saved to the org when confirmed and never waits for the form. No: default style, no brand step |

### Guest and portal forms: payments and links

Carry these into the plan whenever a guest or portal audience is chosen:

- **Conditional payment.** A Form Template can require payment only when the answers match conditions (for example, Amount above zero and Fee Waived not checked): Form Template Settings, Payment Settings, Require payment when. It sets Payment Required and Payment Conditions on the template. Matching responses save as Pending Payment and go on to the payment step; others submit normally; a rule that cannot be read blocks submission rather than waiving payment. The guest (or portal) permission set needs read on the template's **Payment Conditions** field and on **every field a condition reads**, or the rule fails for that audience. Collecting payment needs the Stripe connector extension. Hand the permission set to flow-access-fix.
- **Links that fill in fields (URL parameters).** A **Time** field takes the 24-hour clock in a link: `9:30`, `09:30`, `14:05`, `09:30:15`, with an optional trailing `Z`; `9:30 PM`, `noon` or `25:00` are skipped and the field stays blank. For a **Lookup** or **Id** field, and for the reserved `sourceId` parameter, a 15-character record Id is turned into its 18-character form before any prefill flow sees it, so links built from email merge fields (which write 15 characters) work. Text and External Id fields are never converted, so a prefill flow that matches on a text field holding an Id must compare 18-character values itself.
- Any audience: on an LWR site, publish the site after every package upgrade or component change, so the site serves the new version.

### 4. Design systems, once per account

form-design and design-to-blocks draw with the person's own copies of the **FlowToolKit Forms** and (when the request involves a site) **FlowToolKit Site Blocks** design systems. If the project config has no link for one that this request needs, install it now, following [references/design-systems.md](references/design-systems.md). The plugin carries only the slim kit (`_shared/design-systems/kits.json`); the full kit is a release zip that Claude Code downloads (`scripts/ds_install.py fetch`) and that the person attaches in chat (`scripts/ds_install.py unpack`). `scripts/ds_install.py status` compares the installed version with the one this plugin expects. `scripts/ds_install.py prepare` builds the folder and a plan of calls sized for Claude Code or chat. Install Forms before Site Blocks, which links to it. Save each link to the project config. Never point at a design system on someone else's account.

### 5. Clarify an unclear request

If the request itself is unclear (which form, what it is for, who fills it in, what should happen to the answers), ask the clarifying questions now, before planning: all at once, each with your best guess as the default. A clear request skips this step.

### 6. Show the plan

Classify the request with the routing table below, then show a short plan before running anything: one line per step, the skill it uses, what it produces, and where it runs (chat or Claude Code). Ask to confirm or correct it, once. Example:

> Here is the plan. 1. Read your FormAssembly form (form-migrate): every question, choice and rule, then a short round on anything it does not say. 2. Brand kit: your saved kit, as you said. 3. Design (form-design): plan.json and a review canvas, three pages. 4. Build the template (build-template, needs a Salesforce connector or Claude Code). 5. Conversion flow to Contact and Opportunity (new-mapping-flow, Claude Code). 6. Guest access (flow-access-fix, Claude Code). Go ahead, or change anything?

### 7. Run the skills in order

Run each step's skill and read that skill before starting it. After each step, show what it produced in a few lines and ask to confirm or correct before the next step uses it. Nothing reaches the org until the person has seen the design.

### 8. The gap interview, after the source is read

Right after form-migrate (or brief mode) and before form-design, check what a complete Form Template still needs that the source, the brief, the org and the setup answers did not give, and ask **only** that, in one short round with a default for each, so the person can say "yes to all". The list and its defaults are form-design's (its references/before-drawing.md, step 7): the program the form serves (with its page address, so brand-kit can write in the program's voice); the build mode (metadata through Claude Code, or records and JSON for fast prototyping from chat, converted later by convert-to-metadata); the confirmation message's idea and tone; who the emails go to and come from, including any staff notice; Save Progress and the resume link; the logo and banner; who reviews submissions; anything else the build needs. Write the answers to the plan's `intake` (`intake.gap`, `intake.program`, `intake.build_mode`) so form-design does not ask again. Nothing missing: say so in a line and go on.

## Routing

| The request | Steps, in order |
|---|---|
| Convert a FormAssembly form (link, export, or a whole account) | org-catalog, form-migrate (one form) or formassembly-capture (whole account), brand-kit if chosen, form-design, build-template, build-form-component where a section needs a component, new-mapping-flow, build-email-templates, flow-access-fix for guest or portal |
| Convert a Google Form, Microsoft Form, PDF or web page | org-catalog, form-migrate, then as above from brand-kit |
| A described form, no source ("a three-page form with...", "design a grant application on Outbound Funds") | org-catalog, **brief mode** ([references/brief-mode.md](references/brief-mode.md)) which writes `ir.json` through form-migrate's manual adapter, then as above from brand-kit |
| Clean up, redesign or merge existing Form Templates | org-catalog, form-migrate (Form Template source), form-design, build-template, field-audit |
| Make forms into reusable form components | org-catalog, form-migrate per form, build-form-component (boundaries and reuse), build-template's review pass |
| Turn this into a screen flow | Say plainly that no skill here builds a standalone screen flow. A Flow Section (a screen flow that runs inside one section of a Form Template page) is built by build-flow-section. Otherwise offer the form as a Form Template through the route for its source above |
| Save answers to records, fix a conversion | org-catalog, new-mapping-flow |
| Build a site page with this form | org-catalog, the form route above if the form is not built yet, design-to-blocks, build-site-pages, flow-access-fix and sf-guest-audit for guest |
| A form on a record page | org-catalog, new-record-page-form |
| "Access" errors on a form or flow | flow-access-fix |
| Document what a template uses | field-audit |
| Put a Form Builder metadata form or component into the project (version it, review it, move it to another org) | org-catalog, pull-form |
| A step a flow cannot do well (aggregate totals, parsing, matching many records, an outside call) | new-invocable, from build-flow-section or new-mapping-flow when one of their flows needs it, or on its own |
| Only a brand kit (collect, update or save the organization's look) | org-catalog (finds a saved kit), brand-kit |
| Only emails for a form that is already built (confirmation, Save Progress, resume link, staff notice) | org-catalog, build-email-templates |
| Check a client's guest exposure (what the public can reach through their sites) | sf-guest-audit |
| A site page with no form (a landing page, program page or listing) | org-catalog, brand-kit if chosen, design-to-blocks, build-site-pages, sf-guest-audit when guests see records |

A request that matches two rows runs both, sharing their common steps once.

## Confirm, don't ask

Show what you extracted or planned and ask the person to confirm or correct it. Do not ask them to supply what you can read from the source, the org or the brief.

- Good: "Your form has 3 pages and 24 questions. Page 2 shows the fiscal sponsor block only when 'Registered nonprofit?' is No. Correct?"
- Not this: "How many pages does your form have? Does it have any conditional logic?"
- Apply house standards without asking: button labels (Continue, never Next), page descriptions of at least two sentences, a title on every section, counted estimated times, a multi-paragraph confirmation message. Asking implies they are open to negotiation.
- Ask only what only the person can know: the edition, the audiences, which records the answers create, who signs, decisions between two valid designs. Each question carries a default and a recommendation, all at once in one message.

## Building practices

- **Look before building.** org-catalog runs first; every section in the design is marked reuse (an existing component, named), extend (an existing component plus fields) or new, and the person chooses. Never reuse silently.
- **Sections local first.** Each section starts as its own section on its page; a shared component is made only when the design really repeats across forms (build-template's review pass proposes it).
- **Draw before building.** The design is drawn with the FlowToolKit Forms design system and reviewed before anything is built, so it can be seen and changed cheaply.
- **Flow Sections and custom LWCs.** form-design marks a section `flow-section` when it needs logic a flow does better (lookups, branching on org data, calculations across records) and `custom-lwc` when it needs an interaction no control covers (a live total over a table, a drawing). Hand each such section to **build-flow-section** or **build-custom-lwc**, after the template is built. Both need Claude Code; in chat, say so and list the sections.
- **Describe everything you create** as `_shared/standards/documentation.md` says: a description on every field, flow and element when it is created.

## Done when

- The plan was shown and confirmed, and every step in it ran or was handed over with the reason (for example, "needs Claude Code").
- The gap round ran once after the source was read (or was skipped because nothing was missing), and its answers are in the plan's `intake`.
- The project config holds this org's edition, audiences and brand kit choice, and this account's design system links.
- In chat: the person has `plan.json`, the canvas link, the project config file, and a list of the remaining Claude Code steps.

## Common mistakes

| Mistake | Instead |
|---|---|
| Designing before org-catalog ran | Catalog first, every time, even with a catalog file present |
| Asking the setup questions again for an org already in the config | Read the config; ask only what is missing |
| Asking a question the source or org answers | Show what you found and ask to confirm |
| Skipping the plan and running skills straight away | One short plan, confirmed once |
| Designing with the confirmation idea, senders, Save Progress or images unknown | The gap round after the source is read: only what is missing, each with a default |
| Planning a request you did not understand | Clarifying questions first, each with a best guess |
| Treating a sandbox's unlimited behaviour as proof of the paid edition | Ask; production's edition is what matters |
| Using another account's design system link | Install this account's own copy from the shipped files |
| Promising a deploy in chat | Say which steps need Claude Code and hand over the files |
