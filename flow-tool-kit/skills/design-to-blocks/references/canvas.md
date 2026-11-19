# The review canvas: create, upload, publish, check

## What a run writes

| File | What it is |
|---|---|
| `design/project/*.dc.html`, `design/project/canvas.json` | The artboards and the canvas layout |
| `design/project/sb-tokens.css`, `sb-site.js`, `sb-1280.js`, `sb-390.js` | The design system's tokens as CSS, the image map, and the two preview widths |
| `design/publish-batches.json` | The publish, in order, as `files` maps with `root` the `design/` folder, each within the per-call limit |
| `design/uploads.json`, `design/uploads/` | The images still to upload, staged in one folder so one call sends 25. Keep `uploads/` out of version control |
| `design/review.html` | The self-contained fallback page with every artboard |
| `design/heights.json` | The measured height of every artboard and section (Claude Code, with Playwright) |

Keep the whole `design/` folder in the project beside `site.json`, never in a temporary folder: the Artifact tool's `root` must sit inside the session's working folder, and anything a person reviews is a file in their project plus the canvas.

## How the canvas mounts the real components

Each page artboard loads the design system (`ds/sb/components/bundle.js` and its stylesheet, icons and illustrations) and mounts `<x-import component-from-global-scope="SB.Page">` > `SB.Section` > `SB.Column` > `SB.Block` (and `SB.Tabs`, `SB.RichContent`, `SB.HtmlEditor`, `SB.Repeater`, `SB.FormSlot`, `SB.Divider`), each one's props from `renderVals()` through `dc-props`. `sb-1280.js` and `sb-390.js` call `SB.previewAt(width)`, which settles the bundle's width media queries in JavaScript, so the phone artboard is a real 390px layout. Three details the generator handles: no whitespace between nested `x-import` tags (a text child makes `SB.Page` throw); the canvas wraps each mounted component in a `display: contents` element, so `sb-site.js` hands `SB.Section` its Columns directly; and `SB.assetBase` is absolute.

## Create the canvas, once per site

1. Artifact tool `quickstart` with intent `design`, then publish with the Design type's `type_url`, a `title` (`site.json` `canvasTitle`) and `auto_open: "after_first_write"`, naming the person's **FlowToolKit Site Blocks** design system (the link in `flow-tool-kit.json`) so the type does not fall back to another system. Follow the type's own instructions that come back with the create result.
2. Write the canvas link into `site.json` as `canvasUrl` and give it to the person. The canvas is private to them until they share it.

## Upload the images, then publish

The canvas serves an image only as an upload to it (`/_blob/<id>`), never as a file copied from a design system: a package photo copied into the canvas draws as a broken image there even though a local check passes. So every image an artboard draws, the packaged photos and logo as much as the organization's own, is uploaded:

1. Read `design/uploads.json`. `files` lists each image with no `blob` in `site.json` yet (`name`, `source` the kit's or the organization's copy, `file` the staged copy); `file_paths` holds them in batches of 25.
2. Upload each batch with one Artifact call: `publish`, `url` the canvas, `asset: true`, `file_paths` the batch (the canvas declares the `assets` capability).
3. Record what came back and redraw:

   ```bash
   python3 -I scripts/build_site_review.py --site _site/<slug> --record-blobs '{"Background_Farmland_Aerial.jpg": "/_blob/<id>", ...}'
   ```

   Map each uploaded file (or its `name` in `uploads.json`) to its `/_blob/` url exactly as returned. `uploads.json` should now list nothing.
4. Publish each batch of `design/publish-batches.json` in order: `url` the canvas, `root` and `files` as written. `canvas.json` is in the last batch, so the canvas opens on a complete set.
   - **Claude Code (`--mode code`):** the design system's bundle, stylesheet, libraries and `tokens.json` are copied server side from the person's own design system (`{"artifact": <link>, "path": ...}` entries), never its images. Up to 255 files a call, so usually one call.
   - **Chat (`--mode chat`):** chat cannot copy between artifacts, so the run writes those files from the Site Blocks kit the plugin ships (its ftk-design-system skill) into `design/project/ds/sb/`, and each batch holds at most 16 files.

Later redraws reuse the blobs in `site.json`: only an image a page newly draws is listed, so only it uploads. A changed image is a new upload: remove its `blob` from `site.json` and rerun.

Before every later publish, read the canvas first (`read`, `project/canvas.json`): a comment pinned on it makes a new version, and a publish must build on that version.

## Check it

**In Claude Code**, two headless checks (Node and Playwright):

- `node scripts/site_review.cjs check _site/<slug>/design` renders `review.html` at 1280 and 390, screenshots every artboard into `design/render/`, and fails on console errors, unknown components and broken images. It needs nothing from the canvas.
- After publishing, read the canvas's own runtime once (Artifact `read`, `path` `artifact-type/dc-runtime.js`), then `node scripts/site_review.cjs site _site/<slug>/design <dc-runtime.js> <screenshot folder>`. It plays every artboard at its frame size, serving uploads from `site.json` as the canvas serves `/_blob/` urls, and prints one line each: console errors, missing files, broken images, any image that is not an upload, unresolved components, clipped content, and whether each section's height matches the measured render. Every line must say `ok`.

Then open every screenshot and look. **In chat**, open the published canvas and look at every artboard at both widths, top to bottom. A canvas swapped while open can show a stale render; reload before judging. Check again after every publish, the last small one included.

## No Design type

Some organizations turn the Design and Design System types off. The run still writes `design/review.html`: the brand board, every page at the chosen width (a Desktop 1280 and Phone 390 switch at the top), the states, the Section jobs checklist and Content to collect, with React, the bundle, the styles, only the icons used and the images drawn inlined. Publish it as an ordinary artifact or hand it over as a file; the review then happens in comments on that artifact or in the conversation, and every change still goes into `page.json` first.
