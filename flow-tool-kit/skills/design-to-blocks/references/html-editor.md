# The HTML Editor: custom markup on a site page

The standard Experience Builder **HTML Editor** component shows markup exactly as written. It is the one way a page in this skill carries content the Site Blocks design system has no block for. It is an escape hatch, not a second design system: blocks first, always.

## What it is, and how a site stores it

| Site type | Component | Stored as |
|---|---|---|
| LWR | HTML Editor, `community_builder:htmlEditor` | In the page's view (`digitalExperiences/site/<Site>/sfdc_cms__view/<page>/content.json`): `{"definition": "community_builder:htmlEditor", "type": "component", "attributes": {"richTextValue": "<markup>", "imageInfos": ""}}` |
| Aura | HTML Editor, `forceCommunity:htmlBlock` | In the page's ExperienceBundle view: `componentName` `forceCommunity:htmlBlock`, `componentAttributes.richTextValue` |

In `page.json` it is one item, `{"kind": "htmlEditor", "richTextValue": "<markup>", "_design": {"reason": "..."}}`, in any column or tab. build-site-pages writes it in the site's own shape; the canvas draws it with the design system's `SB.HtmlEditor`, which renders the markup as the site does and puts a small **HTML** tag in the corner so reviewers see where custom markup sits.

What has been checked, and what has not:

- **Checked:** the LWR storage above, read from a retrieved LWR site's view (the template's own error pages are built with this component); the Aura storage and rendering, in the design system's Aura and LWR renders.
- **From Salesforce's LWR Sites developer guide:** which expressions the HTML Editor resolves (below); that enhanced LWR sites include HTML Editor content in site search and in the translation file; that a third-party script on an LWR site belongs in the head markup, in the privileged `<x-oasis-script>` tag, under Relaxed CSP with its host allowed, while new sites default to Strict CSP.
- **Not checked on a live LWR site:** what the LWR HTML Editor does with a `<script>`, frame or embed. An Aura site strips or blocks them, and the design system draws them that way. This skill never depends on the answer: its checker refuses all of them.

## When to use it

Use the HTML Editor only when no block, design or setting does the job, and say why in `_design.reason`:

- a visual the blocks do not draw: one stacked bar of a whole budget (Facts draws one bar per item), a two-axis schedule grid, a simple diagram made of styled boxes;
- an accessible table of fixed reference content with a caption and row headers, where the Table block's layout does not fit;
- a one-off shape of copy, such as an address card laid out like the organization's printed one;
- a small piece of static markup a partner tool asks for that has no script in it (a link button with exact text).

Do not use it for:

| Need | Use instead |
|---|---|
| Anything a block or one of its numbered designs does | That block. Start from the design card |
| Record data: names, amounts, dates, photos | A block's merge fields, a record card or a Repeater, which respect the org's sharing |
| A form, a sign-up, a search box | A Form Slot (a Flow Tool Kit form), the Search component |
| Behaviour: a calculator, a filter, a map, a video player, analytics | A custom LWC (build-custom-lwc), or, for a tag used on every page, the site's head markup, which its admin owns and reviews |
| The header, the navigation, the footer | The site's theme layout and the shared header and footer Sections in `site.json` |
| Formatted page copy (an intro, a policy) | The Rich Content Editor (`richText`) or a block's description |

A page carries at most two HTML Editors. The generator fails the handoff checklist when a page has more, or when one has no reason.

## The rules the checker enforces

`scripts/htmlcheck.py` runs on every HTML Editor and Rich Content item when the canvas is drawn, and on its own (`python3 -I scripts/htmlcheck.py <file.html> --audience guest`).

**Refused** (the generator stops, naming the page, section and line):

- `<script>`, and `<x-oasis-script>`: the HTML Editor is for markup; a privileged script runs outside the page's protections and belongs only in the head markup, under the site admin's review;
- `<iframe>`, `<frame>`, `<object>`, `<embed>`, `<applet>`: another document inside the page, with its own cookies and code;
- `<form>`, `<input>`, `<select>`, `<textarea>`, `<button>`: input that bypasses Flow Tool Kit's validation and sharing; use a Form Slot;
- `<base>`, `<meta>`, `<link>`: page-wide settings that belong in the head markup;
- any `on...` attribute (`onclick`, `onerror`, `onload`);
- a `javascript:`, `vbscript:` or `data:` address in `href`, `src`, `srcset`, `action` or `xlink:href`;
- a style that loads or runs something: `expression()`, `behavior:`, `@import`, `url(javascript:...)`;
- an address expression (`{!Route.term}`, `{!recordId}`) inside an attribute: Salesforce escapes `<`, `>` and `&` in it, which stops a tag but not a `javascript:` link or a broken quote. Show such a value as text, never in `href`, `src` or `style`;
- an image without `alt` (write `alt=""` for a decorative one).

**Warned** (listed on the Section jobs checklist, to fix or explain):

- a `<style>` tag: it may be removed, or style the whole page; use `style` attributes, or ask the site admin to put shared CSS in the head markup;
- an image or media file from an outside host: the site's Content Security Policy must trust that host, and every visitor's browser calls it. Load the file as an Asset File instead;
- a fixed width wider than a phone (390px) without `max-width: 100%`;
- an `h1`: the opening hero holds the page's one `h1`, so markup starts at `h2`;
- a Site Blocks merge field (`{{Name}}`): the HTML Editor shows it as typed;
- `{!User.Record.Field}` or `{!User.userId}` on a page guests see: it shows the guest user's own value;
- a colour outside the site palette.

## Guest, LWR and security constraints

**Everything in the markup is public to anyone who can open the page.** On a guest page that is the whole internet; on a portal page every portal user. So:

- no personal data, internal notes, record Ids, Setup links, staff email addresses the organization has not published, or draft copy;
- record data never goes in markup by hand: blocks and Repeaters read records through the org's sharing, so a guest sees only what guest sharing allows (flow-access-fix sets it; sf-guest-audit checks it);
- images must be reachable by guests: the organization's public Asset Files (brand-kit loads them public in the Asset Library) or the site's CMS images. A private file shows as broken to guests and works for the admin, so check it as a guest;
- links to other sites open the way the person expects: `target="_blank"` only with `rel="noopener"`.

**Expressions the HTML Editor resolves on an LWR site** (Salesforce's LWR Sites developer guide): `{!Route.param}` and `{!param}` (from the address, escaped for `<`, `>` and `&`), `{!Site.basePath}` (safe in a link: `href="{!Site.basePath}/apply"`), `{!User.userId}`, `{!User.isGuest}` and `{!User.Record.Field}` (the signed-in user; the guest user on a guest page), `{!Item.field}` only when the editor sits inside a data-bound component or on a CMS content page or record detail page, and `{!cmsMedia.contentKey}` on enhanced LWR sites. `{!CurrentUser...}` is not supported on LWR.

**Styling on LWR:**

- inline `style` attributes, and the site's own colour and font hooks with a palette fallback: `background: var(--dxp-g-brand, #2e844a)`, `font-family: var(--dxp-g-heading-font-family, inherit)`. CSS variables reach into the component, so the markup follows the site's branding when it changes;
- no list bullets you did not ask for: the site's rich text styles can add markers to `<ul>` and `<li>`; build a legend from `<div>` and `<span>` (the worked example does);
- every width relative or capped (`max-width: 960px; margin: 0 auto`), so it fits a 390px phone.

**After any change** on an LWR site, the change reaches visitors only when the site is published again; build-site-pages publishes and checks the live page.

**Security, in one line:** markup only, no code, no frames, no outside hosts, nothing private. If the design needs any of those, it is not an HTML Editor; it is a custom LWC (build-custom-lwc) or a site-level setting the site admin owns.

## Worked example: a stacked bar of a whole budget

The Riverside funding page (`examples/riverside-sample/pages/funding.json`, section `s03b-split`) shows how last year's grants were spent as one bar. Facts draws one bar per item, so this is the page's one HTML Editor:

```json
{
  "attributes": {"contentAreaWidth": 100, "sectionHeight": 32},
  "columns": [{"width": "12", "items": [{
    "kind": "htmlEditor",
    "richTextValue": "<div style=\"max-width: 960px; margin: 0 auto; padding: 48px 16px;\"><h2 style=\"margin: 0 0 8px; font-size: 2rem; line-height: 1.2;\">Where last year's grants went</h2><p style=\"margin: 0 0 24px; max-width: 640px;\">Grantees told us how they spent every dollar. Most of it paid the people doing the work. [CONFIRM: the split from last year's grant reports]</p><div role=\"img\" aria-label=\"Staff 48 percent, Programs 27 percent, Rent and utilities 15 percent, Equipment 10 percent\" style=\"display: flex; height: 32px; max-width: 100%; border-radius: 8px; overflow: hidden;\"><div style=\"flex: 48; background: var(--dxp-g-brand, #2e844a);\"></div><div style=\"flex: 27; background: #032D60;\"></div><div style=\"flex: 15; background: #F4BE45;\"></div><div style=\"flex: 10; background: #EEF1F4;\"></div></div><div style=\"display: flex; flex-wrap: wrap; gap: 8px 32px; margin: 16px 0 0;\">...one span per segment: a swatch and its label...</div></div>",
    "_design": {"reason": "One segmented bar of the whole budget: the Facts block draws one bar per item and has no single stacked bar."}
  }]}],
  "_design": {"id": "s03b-split", "job": "How each grant dollar was spent, at a glance", "designCard": "HTML Editor"}
}
```

Why it passes:

- static markup and inline styles only; nothing loads from outside the site;
- the bar is one `role="img"` with an `aria-label` that reads the whole split, so a screen reader hears the numbers the picture shows, and the legend repeats them as text;
- the first colour is the site's brand hook with the palette's hex as fallback; the others are palette colours;
- capped at 960px and centred; the legend wraps on a phone;
- the numbers are marked `[CONFIRM: ...]`, so the Content to collect artboard lists them until the organization confirms them;
- `_design.reason` says why no block does it; `designCard` is `HTML Editor`, which the "designs vary" check allows more than once.

On the canvas it draws with the real `SB.HtmlEditor` at 1280 and 390, tagged HTML. build-site-pages writes it into the LWR view as `community_builder:htmlEditor` with the same `richTextValue`.
