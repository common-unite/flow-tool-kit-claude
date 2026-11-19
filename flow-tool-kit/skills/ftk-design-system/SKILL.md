---
name: ftk-design-system
description: The Flow Tool Kit plugin's design-system library, used by its other skills. Holds the FlowToolKit Forms and FlowToolKit Site Blocks kits (component bundles, stylesheets, tokens, block cards, the block schema and the packaged images) that form-design, design-to-blocks and ftk-start read to draw review canvases, write review pages, run render checks and install a person's own Design System. Those skills open its files themselves. Load it directly only when someone asks what the Flow Tool Kit design systems contain, which version this plugin ships, or how one of its tokens, block cards or packaged images is defined.
---

# Flow Tool Kit design systems

The files the other skills draw with. Nothing to download or attach: the kits ship inside the plugin, at the version that matches it.

| Folder or file | What it holds |
|---|---|
| `ftk-forms/project/` | **FlowToolKit Forms**: `README.md` (every component and variant, how a Form Theme and Form Style change the look), `tokens.json`, `design-system.json` (the index), `components/` (the bundle, its stylesheet, `index.d.ts` and one card per component), `components/lib/` (React, the SLDS icons and illustrations), `assets/` (the packaged photos, mascots and FlowToolKit logos) |
| `site-blocks/project/` | **FlowToolKit Site Blocks**: `README.md`, `Choosing-blocks.md` (how to pick blocks for a page), `tokens.json`, the index, `components/` (the bundle, the Aura and LWR stylesheets, `index.d.ts`, one card per block), `assets/resources/` (the volunteer art). Its libraries and photos are the Forms kit's, read from `ftk-forms/project/` |
| `site-blocks/tools/` | `schema.json` (every block type, field and collection) and `column_limits.json` (the narrowest column each design holds up in) |
| `kits.json` | Each kit's version and content checksum, and the plugin version they ship with |
| `images.json`, `images.html` | The packaged images by Content Asset name and preview size, and a contact sheet of the photos to show the person |
| `THIRD_PARTY_NOTICES.md` | The licences of the bundled code and art |

## Finding this folder from another skill

The plugin's skills sit side by side, but the folder names differ by surface: `ftk-design-system/` in Claude Code and in claude.ai with the whole plugin, `<plugin name>:ftk-design-system/` where claude.ai mounts each skill on its own (Team and Enterprise chat). Each skill that reads the kits carries the shared sibling finder, `siblings.py`, in its shared library folder, and prints this folder's path in every layout by running it from its own folder with the argument `ftk-design-system`.

The scripts that read the kits (ftk-start's `ds_install.py`, form-design's `draw_plan.py`, design-to-blocks' `build_site_review.py` and `site_review.cjs`) find it the same way, and take `--kit` or `FTK_DESIGN_SYSTEMS_DIR` to point at another copy.

## Reading the kits

- Start a form design from `ftk-forms/project/README.md`, a site page from `site-blocks/project/README.md` and `Choosing-blocks.md`. A component, block, design or prop they do not name cannot be built.
- A block card holds the props, the rules and a table of numbered designs. The larger cards (Hero, Cards) keep each design's settings and JSON in `design-NN.md` beside the card: read the table, pick a design, then read only that file.
- Each token in `tokens.json` has a `layer` and `set_by`: `theme-field` and `site-token` values change through the Form Theme, Form Style or site field that `set_by` names; `block-setting` through one block's setting; `derived` follows the value it names; `slds-fixed`, `package-fixed` and `platform-fixed` never change in a design.
- Name an image by its Content Asset name from `images.json` (`FlowToolKit__Background_Forest_Sunbeams` and so on). Show `images.html` when the person wants to see the photos.

## Rules

- This folder may be read-only. Never write into it: copy a file out before changing it (ds_install.py and the canvases already do).
- The kits are previews of what the package renders, not the package. Production forms and pages come from the Flow Tool Kit components in the org.
- Each person installs their own Design System from these files (ftk-start's design system step). Never point anyone at a design system on another account.
