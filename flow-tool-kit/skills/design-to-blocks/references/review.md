# The review: comments pinned on the canvas

Reviewers pin comments on the canvas. A comment pins to a section; the id on the section's tag (`s03-detail`) names the section in `page.json`. Apply a round of comments at once, when the person says the round is ready, not one at a time: each publish makes a new version, and publishes count against a daily limit for the account.

## Each round

1. **Read every open comment.** The comment tools list the threads sent to Claude. A comment pinned without being sent to Claude may not show there, so ask the person to send each one to Claude, or to read them out, and confirm the count before you start.
2. **Pull canvas edits first.** Someone may have changed the canvas itself: the properties panel, or the Claude inside the canvas answering a comment by editing an artboard. Read every `project/*.dc.html` from the canvas (Artifact `read`, `paths`, `out_dir` a folder in the project), then:

   ```bash
   python3 -I scripts/pull_canvas_edits.py --site _site/<slug> --live <that folder> --dry-run
   ```

   It lists every edit the canvas has and `page.json` lacks: block props (colours back as palette names), section and column changes, removed items, HTML Editor and Rich Content markup, repeater settings (a change made the same way on every sample card also goes on the build's card template), the shared header and footer, and an extra artboard kept as a `_design.states` entry. Read the list, run it again without `--dry-run`, name the job of any new section it marks, then regenerate and check the redrawn desktop artboards match the canvas. Without this step the redraw wipes those edits and the build ships something nobody approved. Markup edited on the canvas is checked again on the redraw: a script added there stops the run.
3. **Apply each comment** to `page.json` (or `site.json` for the header, footer, palette or brand), then regenerate. When a comment states a general preference, add it to [house-rules.md](house-rules.md) for this project.
4. **Publish once per round**: read the canvas right before publishing (`read`, `project/canvas.json`) and publish against that version, every changed file in one call (and any new image upload before it). If a publish is refused for the rate limit, stop publishing until it resets and tell the person.
5. **Check for new comments again** before resolving: one can arrive while you work.
6. **Resolve each applied comment** on the canvas. Leave a comment open only when it asks a question you cannot answer, and say which.
7. **Report the round** to the person: each comment with what changed, and every page a change touches (the header, footer and anything in `site.json` `page` change every page). Add any new difference between the design and what the build will do to `intake.md`.
