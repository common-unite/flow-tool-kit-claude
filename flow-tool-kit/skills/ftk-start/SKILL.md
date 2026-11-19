---
name: ftk-start
description: The front door for Flow Tool Kit (FTK) in Salesforce, and the skill to load first whenever someone wants a form built, converted, designed or changed, even when they never say Flow Tool Kit, Form Template or a skill name, and whenever a request names Flow Tool Kit. Use when: "let's add this form to Salesforce", "can we convert this form?", "build a form template out of this PDF", a Word document, screenshot or photo of a form, a FormAssembly, Jotform, Google Forms or other web form link, "can we build a new form template", "a new flow form" or "a form component", an intake, application, registration or sign-up form, a Repeater or Table, a screen flow for sign-ups, a page where people update their details, or a mockup before building. Reads the org, asks only what it cannot read (one plain question when the build approach is open), states a short plan and runs the other Flow Tool Kit skills itself, in order, without the person naming them. Works in claude.ai chat and Claude Code.
---

# FTK Start

The entry point for building on Flow Tool Kit, and the first skill to load for any form request, whether or not the person says Flow Tool Kit. A person asks in their own words; this skill reads the org, settles the few things only they can answer, states a short plan, and then runs the specialist skills in the right order itself. They never need to know, or be asked about, the other skill names.

It decides **what happens and in what order**. The specialist skills do the detailed work, and each one owns its own rules; never redo their steps here.

## Where it runs

| Surface | What works |
|---|---|
| claude.ai chat (code execution on) | Everything up to an approved design: org catalog (with a Salesforce connector), setup questions, design system install from the plugin's own files, reading a source or a brief, brand kit, `plan.json` and the review canvas. With a Salesforce connector that can create records, the Form Template records too |
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

Ask only when the project config has no answer for this org. On a clear request, do not stop for them: take each default, name the defaults in one line of the plan as assumptions the person can correct, and go on (nothing reaches the org before the person has seen the design). Otherwise ask all three in one message, each with what was found and a default, so the person can answer "yes" to all of it (see Confirm, don't ask):

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

form-design and design-to-blocks draw with the person's own copies of the **FlowToolKit Forms** and (when the request involves a site) **FlowToolKit Site Blocks** design systems. The kits ship inside the plugin, in its **ftk-design-system** skill: nothing to download or attach. If the project config has no link for one that this request needs, install it now, following [references/design-systems.md](references/design-systems.md). `scripts/ds_install.py status` reports the version this plugin ships, checks the bundled files, and compares the installed design system's version. `scripts/ds_install.py prepare` copies a kit out of the plugin and plans the calls for Claude Code or chat. Install Forms before Site Blocks, which links to it. Save each link to the project config. Never point at a design system on someone else's account.

### 5. Clarify an unclear request

If the request itself is unclear (which form, what it is for, who fills it in, what should happen to the answers), ask the clarifying questions now, before planning: all at once, each with your best guess as the default. A clear request skips this step.

### 6. Show the plan

Classify the request with the routing table below, then state a short plan in plain words: one line per step, what it produces, and where it runs (chat or Claude Code). The person does not need the skill names. On a clear request, state the plan and start step 7 in the same reply, inviting corrections without waiting for them. Wait for an answer only when the request is genuinely open (step 5, or the approach row in Routing), and then ask about the use case in plain words, never whether to use a skill. Example:

> Here's how I'll do it: read your FormAssembly form (every question, choice and rule), design it as a three-page form you can review before anything is built, then build the template, the conversion to Contact and Opportunity, and guest access in Claude Code. I'm assuming the paid edition and a public site form; tell me if either is wrong. Starting with the form now.

### 7. Run the skills in order

Run each step's skill and read that skill before starting it (load it as a skill; see The rest of this plugin). After each step, show what it produced in a few lines and carry on; stop for an answer only where the next step needs a decision only the person can make. Nothing reaches the org until the person has seen the design.

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
| The build approach is open ("a screen flow for sign-ups", "a new flow form", "we need a form for our food pantry in Salesforce", "a page where families update their info", with no source form) | Ask one plain question about the use case, with your recommendation and its reason, then route from the answer yourself: "Is this a form people fill in on its own, like an application or sign-up, or one step inside a process your team already runs as a flow?" A form on its own: a Form Template, through the route for its source or brief above (the default). A step in an existing flow: Flow Tool Kit form components on the flow's screen (build-form-component, and repeating-data for rows); a Flow Section inside a Form Template page is build-flow-section. A handful of staff-only fields with nothing Flow Tool Kit adds: say a standard Flow screen is enough and that no skill here builds standalone flows |
| A reusable block of questions, a Repeater or a Table ("can we build a form component?", "let families add everyone in the household", "show the shifts as a table") | org-catalog, then build-form-component, or repeating-data for repeating rows (it hands over to build-repeater or build-table) |
| Build, rebuild or check a Form Template from an approved design | org-catalog, build-template, then the steps after it above |
| One section of an existing form needs org data or a custom control ("applicants pick their school from our Accounts", "branch on whether they already have a membership", "a running total as people pick tickets") | org-catalog, then build-flow-section (records, branching, several steps) or build-custom-lwc (a live total, a widget) straight away; no redesign unless the form does not exist yet |
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

A request that matches two rows runs both, sharing their common steps once. When it is unclear whether the request is about a form or about a site, ask in plain words, for example "Is this a form or flow you want built in Salesforce, or more website, UX and UI design?", and pick the route from the answer.

## The rest of this plugin

Every other Flow Tool Kit skill is yours to use without the person naming it. Pick the next one from the conversation and load it yourself: in Claude Code with the Skill tool (`flow-tool-kit:<name>`); in chat, read its `SKILL.md` in the sibling skill folder. Never ask whether to use a skill, never name one in a question, and never offer one as a choice; when the request is genuinely unclear, ask about the use case in plain words (as above) and choose from the answer.

| Need | Skill |
|---|---|
| Read a source form or a brief | form-migrate (one form), formassembly-capture (a whole FormAssembly account) |
| Design the form, review canvas | form-design |
| Build the template | build-template |
| Reusable blocks, Repeaters, Tables | build-form-component, repeating-data, build-repeater, build-table |
| Logic in a section, custom controls | build-flow-section, build-custom-lwc, new-invocable |
| Answers to records, prefill | new-mapping-flow |
| Emails | build-email-templates |
| Brand, site pages | brand-kit, design-to-blocks, build-site-pages |
| A form on a record or site page | new-record-page-form |
| Access errors, guest exposure | flow-access-fix, sf-guest-audit |
| What the org has, where fields are used | org-catalog, field-audit |
| Source control, merging, metadata | pull-form, consolidate-sections, convert-to-metadata |

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
| Skipping the plan and running skills straight away | One short plan, stated in plain words, then carry on |
| Asking "should I use the form-migrate skill?" or waiting for a go-ahead on a clear request | Choose the skills yourself; ask only about an open use case, in plain words |
| Designing with the confirmation idea, senders, Save Progress or images unknown | The gap round after the source is read: only what is missing, each with a default |
| Planning a request you did not understand | Clarifying questions first, each with a best guess |
| Treating a sandbox's unlimited behaviour as proof of the paid edition | Ask; production's edition is what matters |
| Using another account's design system link | Install this account's own copy from the shipped files |
| Promising a deploy in chat | Say which steps need Claude Code and hand over the files |
