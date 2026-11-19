# Flow Tool Kit for Claude

The `flow-tool-kit` plugin gives Claude the skills, standards and worked examples the makers of Flow Tool Kit use in their own client work. Bring it a FormAssembly link, a PDF, a Word document, a Google Form or just a description, and Claude reads it, asks only what is missing, draws the design for your review, and builds the Form Template, the emails and the flows that save every answer to the right records. The same skills build record-page interfaces, Experience Cloud pages and advanced Flow screens on Flow Tool Kit.

It works against whichever Salesforce org you connect, on the free or paid Flow Tool Kit edition. Nothing in it names a particular org, computer or company, and it collects no data: everything runs in your own Claude session, against your own org and the websites you name.

**Version 2.0.0**, 25 skills. Start with **ftk-start**: describe the job in plain words and it runs the right skills in the right order. The others: org-catalog, form-migrate, formassembly-capture, brand-kit, form-design, build-template, build-form-component, repeating-data, build-repeater, build-table, convert-to-metadata, consolidate-sections, pull-form, field-audit, new-mapping-flow, flow-access-fix, new-invocable, build-flow-section, build-custom-lwc, design-to-blocks, build-site-pages, sf-guest-audit, new-record-page-form and build-email-templates.

## What you need

- A Claude plan with skills, and code execution turned on for claude.ai chat.
- Claude Code and the Salesforce CLI (`sf`) for deploys and anything that writes metadata to an org.
- A Salesforce org with Flow Tool Kit installed. A scratch org or sandbox is the right place to start.
- Python 3.

The plugin's own [README](flow-tool-kit/README.md) lists what each skill runs, sends and fetches, and how the one optional secret (a FormAssembly access token) is kept.

## Install in Claude Code

From your shell:

```bash
claude plugin marketplace add common-unite/flow-tool-kit-claude
claude plugin install flow-tool-kit@common-unite
```

or inside a session:

```text
/plugin marketplace add common-unite/flow-tool-kit-claude
/plugin install flow-tool-kit@common-unite
```

Each skill then runs as `/flow-tool-kit:<skill-name>`, or Claude picks it up when your request matches. If your computer has no GitHub SSH key, set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` so installs and updates clone over HTTPS.

**Turn on auto-update.** It is off for a marketplace you add yourself. Run `/plugin`, open **Marketplaces**, select `common-unite`, then **Enable auto-update**. An administrator can turn it on for everyone with `"autoUpdate": true` on the `common-unite` entry under `extraKnownMarketplaces` in managed settings. Without it, update with `/plugin marketplace update common-unite` in a session or `claude plugin update flow-tool-kit@common-unite` in your shell.

## Install in claude.ai

A plugin added to your claude.ai account works in chat, in Cowork, and in Claude Code signed in to the same account.

- **Add the marketplace:** in **Customize > Plugins**, select **Add > Add marketplace** and enter `common-unite/flow-tool-kit-claude`. Select **Check for updates** to pull a new release, or turn on **Sync automatically**.
- **Or upload it:** select **Add > Upload plugin** with a `.zip` of the `flow-tool-kit` folder. An upload is a copy of one release: upload the new zip for each release.

## The design systems

The review canvases draw with two design systems, FlowToolKit Forms and FlowToolKit Site Blocks. The plugin carries a slim copy; each [release](https://github.com/common-unite/flow-tool-kit-claude/releases) attaches the full kits as two zips, `flow-tool-kit-<version>-ftk-forms.zip` and `flow-tool-kit-<version>-site-blocks.zip`. The first time you need them, ftk-start downloads the zips for your plugin version (Claude Code) or asks you to attach them (claude.ai chat), checks every file against the checksums shipped in the plugin, and installs your own copy of each design system into your claude.ai account.

## Claude Code on the web

Cloud sessions load the skills enabled on your claude.ai account, so install the plugin in claude.ai first. Then, in your cloud environment, allow the Salesforce, FormAssembly, Google Fonts and GitHub release hosts the skills use, install the Salesforce CLI in the setup script, and sign in to your org from an environment variable you keep in your own environment. The [runtime standard](flow-tool-kit/skills/sf-guest-audit/_shared/standards/runtime.md) lists every host and the sign-in steps.

## How updates reach you

Every release raises `version` in `flow-tool-kit/.claude-plugin/plugin.json` and attaches the two design-system zips to the GitHub release `v<version>`. Claude Code gives you a new copy only when that version changes.

## License

Use the plugin with Flow Tool Kit in your own Salesforce orgs or your clients' orgs; what you build with it is yours. You may not copy, repackage, resell or redistribute the plugin. See [LICENSE](LICENSE).

This repository is a published copy of each release; the plugin is developed elsewhere, so pull requests here are not merged.
