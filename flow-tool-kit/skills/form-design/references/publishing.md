# Publishing the canvas

## What a run writes

| File | What it is |
|---|---|
| `_forms/<slug>/plan.json` | Updated in place with the rule-decided values (each change printed) |
| `_forms/<slug>/field-audit.csv` | One row per field, for the admin |
| `design/project/*.dc.html`, `design/project/canvas.json` | The artboards and the canvas layout |
| `design/publish-batches.json` | The publish, in order, as `files` maps (root `design/`), each within the per-call limit |
| `design/uploads.json` | Images still to upload to the canvas |
| `design/review.html` | The self-contained fallback page |
| `design/render/*.png`, `design/render-check.json` | From the render check (Claude Code) |

## Claude Code (`--mode code`, the default)

1. Create the canvas from the **Design** artifact type, naming the person's **FlowToolKit Forms** design system (the link in `flow-tool-kit.json`) so the type does not fall back to another system. Follow the type's instructions that come back with the create result. Record the canvas link in the plan as `canvas_url` (later runs and the review use it) and give it to the person.
2. Upload the images in `uploads.json` (`file_paths`, 25 a call), record each url in `design/blobs.json`, run `draw_plan.py` again.
3. Run the render check and look at every screenshot (below).
4. Publish each batch of `publish-batches.json` in order, with `root` set to the `design/` folder. The five design system files are copied server side from the person's own design system (`{"artifact": <link>, "path": ...}`); `canvas.json` goes in the last batch so the canvas opens on a complete set.
5. Before every later publish, read the canvas first: a comment pinned on it makes a new version, and a publish must build on that version.

## claude.ai chat (`--mode chat`)

Chat cannot copy files between artifacts, so the run copies the five design system files from the full FlowToolKit Forms kit (the release zip the person attaches, unpacked by ftk-start's `ds_install.py unpack`) into `design/project/ds/ftk/` and lists them in the batches as local files. Each batch holds at most 16 files, the most one chat call takes. Publish the batches in order, the same way, then give the person the canvas link, `plan.json` and `field-audit.csv` (as files they download, or add to their claude.ai Project).

## No Design type

Some organizations turn the Design and Design System types off. The run still writes `design/review.html`: one page holding every artboard with the same components (React, the kit's bundle and styles, the base tokens and only the icons the boards use, about 1.5 MB with the package photo). Publish it as an ordinary artifact or hand it over as a file. It has passed a headless render in Claude Code; publishing it as an artifact from chat has not been tried yet, so say so.

## The render check (Claude Code)

```bash
node scripts/check_render.cjs _forms/<slug>/design --write-heights
```

It renders `review.html` headless, screenshots every artboard into `design/render/`, and compares each board's real content height with its frame. A board whose content is taller than its frame fails (its button bar would be cut off); `--write-heights` records the measured heights in `design/measured-heights.json`, and the next `draw_plan.py` run uses them. Console errors and unknown components fail too. Open every screenshot and look at it: the check measures, it does not judge. Needs Node and Playwright's Chromium (`npx -y playwright@1.47.2 install chromium` once). On Claude Code on the web, allow the npm registry in the environment's network settings.
