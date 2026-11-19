---
name: form-design
description: Use when a Flow Tool Kit form needs designing or redesigning before it is built, after form-migrate has read a source (FormAssembly, Google Forms, a PDF, a web page or an existing Form Template) or ftk-start's brief mode has turned a description into a form. Also when someone asks for a form mockup, a design review, a field audit or a handoff plan in the FlowToolKit Forms design system, or when a review changes a design that must be redrawn.
---

# Form Design

Turns what a source form asks (form-migrate's `ir.json`, or brief mode's) and what the person needs into two things that always agree:

1. **`plan.json`**, the design as data: pages, sections, components, every field with its control, widths, copy and Salesforce target, the template settings and the emails. build-template builds from it without interpretation. Format: [references/plan-format.md](references/plan-format.md).
2. **One review canvas**, a Design artifact drawn with the real FlowToolKit Forms components: an artboard per page and state, the confirmation messages, the emails and a field audit. Plus `field-audit.csv` beside the plan for the admin.

**Requirement: the Design feature on the person's claude.ai account.** Whatever Claude plan they are on, the review canvas is a Design artifact, so the person needs Design turned on for their claude.ai account (in an organization, an admin may have to enable it) to see the design and comment on it. Without it the build still runs from `plan.json`, but there is no visual canvas review, only the plain fallback page described under Where it runs. Say this at the start, before drawing.

The plan is the source of truth and the canvas is drawn from it by `scripts/draw_plan.py`. A change goes into the plan and the canvas is redrawn; nobody edits the drawing by hand, so the build never ships something the review did not see.

## Where it runs

| Runtime | What works |
|---|---|
| claude.ai chat (code execution on) | Everything: write `plan.json`, run `draw_plan.py --mode chat`, publish the canvas in calls of 16 files. Give the person `plan.json`, `field-audit.csv` and the canvas link. No render check (no browser): look at the canvas yourself before saying it is done |
| Claude Code, local or on the web | Everything, plus the headless render check (`check_render.cjs`) and server-side copying of the design system (`--mode code`) |

Without the Design type (some organizations turn it off) the run still writes `plan.json`, `field-audit.csv` and `design/review.html`, one self-contained page with the same components. That page is a fallback: it has passed a headless render in Claude Code, but it has not been tried as a published artifact in chat yet. Tell the person that when you hand it over.

## Before drawing

Before drawing anything (the project config, the catalog, the source, the design system, the rules, the brand and the gap interview), read [references/before-drawing.md](references/before-drawing.md) (Before drawing).

## Decisions, in the order they constrain each other

While deciding the form type, layout, components and copy, read [references/decisions.md](references/decisions.md) (Decisions, in the order they constrain each other).

## Drawing the canvas

```bash
python3 scripts/draw_plan.py _forms/<slug>/plan.json [more plans] [--mode chat]
```

It normalizes each plan (counted times, the row's settings, Continue buttons, section spacing, Style Editor tokens, rich text scaled to the Text size), checks it, and only then draws. Every error names its fix; correct `plan.json` and run again. Output and publishing: [references/publishing.md](references/publishing.md). What the canvas shows and why: [references/canvas.md](references/canvas.md). The checks: [references/checks.md](references/checks.md).

Start the canvas from the **Design** artifact type with the person's FlowToolKit Forms design system (the type's own instructions arrive with the create result), then publish the batches the run wrote. The canvas folder lives in the project beside `plan.json` (`_forms/<slug>/design/`), never in a temporary folder: anything a person reviews is a file in their project plus the canvas.

## Look at it before saying it is done

In Claude Code, run `node scripts/check_render.cjs _forms/<slug>/design --write-heights`, open every screenshot it writes under `design/render/`, and fix what you see before publishing. In chat, open the published canvas and look at every artboard. Check at least: every section full width and none nested; the banner as the template header with no page header repeating the title; card and option labels visible; Yes or No, never TRUE or FALSE; no field names or internal notes in respondent copy; frames fitting their content; utility icons only; every button bar inside its artboard. Recheck after every publish, the last small one included.

## During the review

Change `plan.json`, run `draw_plan.py` again and publish only the batches with changed files. Record each decision and its reason in the plan's `decisions`. Comments pinned on the canvas are the review: read every open one, apply each to the plan, then the canvas; read the artifact again right before publishing (a pinned comment makes a new version); resolve what you applied, and name every form a change touches when a shared block changes. When a comment states a general preference, propose it as a house rule.

## Done when

- `draw_plan.py` runs clean and `--check` passes: every page described, every section titled or deliberately headerless, every rule labelled, every catalog match answered, every new or extended component's shape recommended, asked and recorded.
- Every source field is in the plan, or in `dropped` with its reason; the plan has no more show/hide rules than the source; every required flag is the source's, or the person confirmed the change in `required_change`, and each Address row is required exactly when one of its parts is (Flow Tool Kit enforces the row's flag on every part).
- Every field has a target, a placement reason, a control with its stored variant name, widths at three sizes and a status; gaps are listed in `gaps`, not drawn as if they work.
- The canvas and the plan agree, the canvas has been looked at, and the person has `plan.json`, `field-audit.csv` and the canvas link.
- Flow Sections and custom LWCs are named for build-flow-section and build-custom-lwc; the next step is build-template.

## Common mistakes

| Mistake | Instead |
|---|---|
| Splitting a one-page form into several pages | Keep the page count; offer a change as a question |
| Reusing a catalog component without asking | Ask reuse, extend or new, naming it; record the answer |
| Choosing metadata, record or JSON for the person | Recommend a shape with the reason, ask, and record `shape` and `shape_asked` |
| Calling a Form Template reusable | A template is one whole form; reuse is of the Form Components placed in it |
| Every question on Form Submission in a paid org | Components on the record's own object with Form Template Mapping |
| Editing the canvas and forgetting the plan | Change the plan; the canvas is redrawn from it |
| Inventing variant names or styles | Only names from the design system README |
| A resume link built from `pv9` or `recordId` | Merge `{{FlowToolKit__Internal_Resume_Link__c}}` |
| Porting a source script line by line, or dropping it silently | Native control, Flow Section or custom LWC, offered as an add-on |
| Drawing an unsupported feature as finished | Mark it `gap` and list it |
| Pointing at someone else's design system | The person's own copy, installed by ftk-start |
| Asking what the source already says, or asking gap questions one at a time | One gap round, only what is missing, each with a default |
| Drawing with a missing confirmation idea, sender or Save Progress choice left unstated | Ask it in the gap round, or take the default and record it in `intake` |
