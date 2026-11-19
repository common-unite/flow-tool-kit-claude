# Installing the design systems, once per account

form-design draws with **FlowToolKit Forms**; design-to-blocks with **FlowToolKit Site Blocks**. Each person installs their own copy into their claude.ai account, so nothing depends on another account. Install Site Blocks only when a request involves a site, and always after Forms: Site Blocks links to the Forms system.

Both kits ship inside the plugin, in the **ftk-design-system** skill, at the version that matches the plugin: the bundles, stylesheets, tokens, block cards and packaged photos. There is nothing to download or attach, in Claude Code or in chat. `ds_install.py` finds that skill beside this one in every install layout (`ftk-design-system/`, or `<plugin>:ftk-design-system/` where claude.ai mounts each skill on its own). The skill's folder may be read-only: `prepare` copies the files out before it changes anything.

1. **Check first.** `python3 <this skill>/scripts/ds_install.py status --config flow-tool-kit.json` prints, per kit, the version this plugin ships, whether the bundled files match their checksum, and the `kit_version` saved for the installed design system. If the project config has a link, read that system's `project/README.md`; if it opens, it is installed. Otherwise list the person's artifacts made from the Design System type and look for the title. Reuse one that exists and save its link. When status says the installed system is older than the plugin ships, tell the person in one line and offer to install the new version (a new artifact, then save its link); never replace it without asking. A bundled kit reported damaged means the plugin install is incomplete: ask the person to update or reinstall the plugin.
2. **Create.** Find the Design System type in the Artifact types listing and create one artifact from it with the title `FlowToolKit Forms` (or `FlowToolKit Site Blocks`) and no files. The create result carries the type's own instructions; follow them where this page is silent.
3. **Prepare the folder.**
   - Claude Code: `python3 <this skill>/scripts/ds_install.py prepare --kit ftk-forms --out <scratch folder> --surface code`.
   - Chat: the same with `--surface chat` and `--out` set to the system's own folder that the type's instructions name (an empty folder for that artifact).
   - Site Blocks: `--kit site-blocks --forms-url <the person's FlowToolKit Forms link>`.

   It copies the kit's files into `<out>/project/`, fills in the Forms link, stamps the index with this install's time, and writes `<out>/install-plan.json` with the `kit_version` to save.
4. **Send the files** in the plan's `batches`, one call per batch: Claude Code with `root` set to `<out>` (up to 255 paths a call); chat with absolute paths, one `file_path` plus up to 15 more. Pictures are sent as files at their paths like everything else, because the previews and the Site Blocks bundle load them by relative path. Nothing needs the asset store.
5. **Send the index last**: `project/design-system.json` alone, in the final call.
6. **Save** the link and the version with `scripts/ftk_config.py set-design-system forms --url <link> --kit-version <the plan's kit_version>` (or `site_blocks`), and give the person the link. Read its `project/README.md` once to confirm it opens.

Sizes: Forms is 139 files and about 6 MB (9 calls from chat, one from Claude Code); Site Blocks 226 files and about 10 MB, its own files plus the Forms libraries and photos it takes with it (15 calls from chat, one from Claude Code).

form-design and design-to-blocks read the same bundled kits for the chat canvas, the fallback page and the render checks, so they work before a design system is installed; only the canvas link needs the installed copy.

If the account has no Design System or Design type (some organizations turn them off), say so and continue: form-design can still write `plan.json` and `review.html`, and the canvas waits until the type is available.
