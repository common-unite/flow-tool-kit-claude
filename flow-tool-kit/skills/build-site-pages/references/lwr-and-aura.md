# LWR and Aura sites

The same blocks, with the same JSON, render on both. What differs is the page around them. The generator reads the site type from the retrieved folder and converts a design drawn for the other type.

| Concern | LWR | Aura |
|---|---|---|
| Metadata | `DigitalExperienceBundle`: `sfdc_cms__*` folders, each with `content.json` and `_meta.json` | `ExperienceBundle`: `views/*.json`, `routes/*.json`, `themes/*.json` |
| Deploy unit | One page alone (its view and route folders), or the whole site | The whole site |
| Component in the page JSON | `definition` and `attributes` | `componentName` and `componentAttributes` |
| Page record binding | `{!Route.recordId}` | `{!recordId}` |
| Section | `community_layout:section` | `forceCommunity:section` |
| Brand | Branding set values, read by blocks as `--dxp-g-*` | Theme, read as `--lwc-*` |
| Custom CSS and tokens | Head markup: one `<style>` | Theme `customCss` |
| Head markup | Editable, holds the `<title>`. It accepts only some tags and attributes: a `data-` attribute on a `<link>` is refused, so the generator marks its font link with a comment | Not exposed |
| Flow Tool Kit support | FlowToolKit LWR Support in the Theme Footer, required | Not needed |
| Your own components a form loads by name | A support component that imports them, in the Theme Footer | Not needed |
| Record pages | The object's detail, list and related-list pages together | The detail page alone; Form Template Detail and Form Submission Detail page variations for Flow Tool Kit records |
| Publish | Serves the code and pages of the last publish; publish after every change and upgrade | Changes show without the freeze, but a publish still makes them public |
| Guest access | The site's public access setting, plus profile, field access and a guest sharing rule | Profile, field access and a guest sharing rule |

## Why LWR needs the support components

An LWR site is compiled when it is published. Since Winter '27 the publisher includes only components a page reaches by a static reference. Flow Tool Kit renders forms, modals, repeaters and custom section components by name at run time, so the publisher cannot see them. FlowToolKit LWR Support imports the package's own; a support component of yours imports yours (build-custom-lwc ships one). Each renders nothing and sits in an empty column of the Theme Footer, which is on every page. After adding or changing either, publish.

## After a Flow Tool Kit upgrade

An upgraded package is not on an LWR site until the site is published again. When a form on a site looks blank after an upgrade, check in this order: the last publish date against the upgrade date, then LWR Support in the theme layout, then the page itself. Read code last.

## The Builder canvas

- Builder's canvas and preview render the draft, signed in, in a frame. They are useful for placing things and never proof that a visitor sees them.
- A block with an entrance animation is invisible until it scrolls into view, and may never appear in the canvas.
- A "Something went wrong" dialog (LWR3008) for a design component can appear once on the first canvas load after a deploy. Refresh; if it does not come back, carry on. If it appears on the published page, LWR Support is missing or the site was not published after the change.
- To open Builder for a site from the CLI: `sf org open --target-org <org-alias> --url-only --path "/sfsites/picasso/core/config/commeditor.jsp?siteId=<Site Id>"`, where the Site Id is the 15-character `0DM` Id from `SELECT Id FROM Site WHERE Name = '<Site1>'` (the Network Id, `0DB`, is refused).
