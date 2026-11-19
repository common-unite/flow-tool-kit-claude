# Installing the design systems, once per account

form-design draws with **FlowToolKit Forms**; design-to-blocks with **FlowToolKit Site Blocks**. Each person installs their own copy, so nothing depends on another account. Install Site Blocks only when a request involves a site, and always after Forms: Site Blocks links to the Forms system.

The plugin carries only the **slim kit** (`_shared/design-systems/`): `kits.json` (the release, each kit's version and the checksum of every file) and each system's index. The **full kits** (bundles, libraries, the packaged photos and logos) are release assets, one zip per kit, named `flow-tool-kit-<plugin version>-<kit>.zip` (`kits.json` has the exact names and the release tag). Each zip is self-contained: Site Blocks' zip carries the libraries and photos it shares with Forms.

1. **Check first.** `python3 <this skill>/scripts/ds_install.py status --config flow-tool-kit.json` prints, per kit, the version this plugin expects, whether the full kit is unpacked here, and the `kit_version` saved for the installed design system. If the project config has a link, read that system's `project/README.md`; if it opens, it is installed. Otherwise list the person's artifacts made from the Design System type and look for the title. Reuse one that exists and save its link. When status says the installed system is older than the plugin expects, tell the person in one line and offer to install the new version (a new artifact, then save its link); never replace it without asking.
2. **Get the full kit** (skip when status says it is unpacked at the expected version).
   - **Claude Code:** `python3 <this skill>/scripts/ds_install.py fetch --kit ftk-forms`. It downloads the zip for this plugin's own version from `common-unite/flow-tool-kit-claude` with `gh release download` when the GitHub CLI is signed in (the repository may be private), else from the release's public address, checks every file against `kits.json`, and unpacks it at `~/.flow-tool-kit/design-systems/<kit>/` (or `$FTK_DESIGN_SYSTEMS_DIR`). On Claude Code on the web, allow `github.com` and `release-assets.githubusercontent.com` in the environment's network settings. A download that fails says why: sign in with `gh auth login`, or download the zip from the release page and use `unpack` below.
   - **claude.ai chat:** ask the person to attach `flow-tool-kit-<version>-<kit>.zip` (the exact name is in `kits.json`; the plugin's release page or their Flow Tool Kit contact has it). If the zip is already among the claude.ai Project's files, use it without asking. Then `python3 <this skill>/scripts/ds_install.py unpack --zip <path to the zip>`. No network is needed. Suggest adding the zip to the Project's files, so later conversations find it.
   - **Optional, Claude Code only:** when `kits.json` names a public design system artifact for the kit (`public_artifacts`, off by default), `prepare ... --from-artifact` copies every file server side from it and nothing is downloaded. A Site Blocks copy made this way keeps that artifact's link to its own Forms system.

   `unpack` refuses a zip whose kit version or any file's checksum differs from what this plugin expects, and says which.
3. **Create.** Find the Design System type in the Artifact types listing and create one artifact from it with the title `FlowToolKit Forms` (or `FlowToolKit Site Blocks`) and no files. The create result carries the type's own instructions; follow them where this page is silent.
4. **Prepare the folder.**
   - Claude Code: `python3 <this skill>/scripts/ds_install.py prepare --kit ftk-forms --out <scratch folder> --surface code`.
   - Chat: the same with `--surface chat` and `--out` set to the system's own folder that the type's instructions name (an empty folder for that artifact).
   - Site Blocks: `--kit site-blocks --forms-url <the person's FlowToolKit Forms link>`.

   It copies the kit's files into `<out>/project/`, fills in the Forms link, stamps the index with this install's time, and writes `<out>/install-plan.json` with the `kit_version` to save.
5. **Send the files** in the plan's `batches`, one call per batch: Claude Code with `root` set to `<out>` (up to 255 paths a call); chat with absolute paths, one `file_path` plus up to 15 more. Pictures are sent as files at their paths like everything else, because the previews and the Site Blocks bundle load them by relative path. Nothing needs the asset store. With `--from-artifact`, each batch is already a `files` map of server-side copies.
6. **Send the index last**: `project/design-system.json` alone, in the final call.
7. **Save** the link and the version with `scripts/ftk_config.py set-design-system forms --url <link> --kit-version <the plan's kit_version>` (or `site_blocks`), and give the person the link. Read its `project/README.md` once to confirm it opens.

Sizes: Forms is about 140 files and 6 MB (a 4 MB zip; about 9 calls from chat, one from Claude Code); Site Blocks about 185 files and 11 MB (a 6 MB zip; about 12 calls from chat, one from Claude Code).

The full kit stays unpacked for form-design and design-to-blocks, which use it to write the chat canvas, the fallback page and the render checks. In chat it lasts for the conversation: a new conversation unpacks the zip again.

If the account has no Design System or Design type (some organizations turn them off), say so and continue: form-design can still write `plan.json`, and the canvas waits until the type is available.
