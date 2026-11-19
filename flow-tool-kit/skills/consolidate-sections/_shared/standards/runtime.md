# Runtime

Where the skills run, how each place signs in to Salesforce, what the skills fetch from the internet, and the optional tools. Every skill follows this page; a skill's own page says only what it needs beyond it.

## Signing in to Salesforce

| Where | How | Never |
|---|---|---|
| Claude Code on your computer | The Salesforce CLI: `sf org login web --alias <org-alias>` once, in a browser on that computer. Then `--target-org <org-alias>` on each command, or the project's saved alias from `flow-tool-kit.json` ([project-config.md](project-config.md)) | |
| Claude Code on the web (a cloud session) | The Salesforce CLI, signed in from a secret in the cloud environment, because the session has no browser. Either an SFDX auth URL: on a computer already signed in, `sf org display --target-org <org-alias> --verbose --json` shows `sfdxAuthUrl`; put it in the environment's variables as `SFDX_AUTH_URL`, and the session runs `echo "$SFDX_AUTH_URL" \| sf org login sfdx-url --sfdx-url-stdin --alias <org-alias> --set-default`. Or a JWT login (`sf org login jwt --client-id <consumer key> --jwt-key-file <key file> --username <user> --instance-url https://<your-domain>.my.salesforce.com --alias <org-alias>`) with the key file written from a secret at the start of the session | `sf org login web`: no browser can open there. Never paste the auth URL or a key into the chat or a project file. Anyone who uses an environment can read its variables, so keep the secret in your own environment, never a shared one, and sign in again when it is revoked |
| claude.ai chat (and voice) | A Salesforce connector added to the account. Its query tool reads the org; each skill says which of its steps the connector can do and which need Claude Code | The CLI: chat has no shell that can reach the org. A skill that needs a deploy says so and hands over the files |

Without any sign-in, a skill still designs and writes files, marks every Salesforce name it could not check as to be verified, and says what to run once an org is connected.

## What the skills fetch

On Claude Code on the web, choose **Limited** network access, keep **Allow package managers** on (npm and PyPI, for the Salesforce CLI, Playwright and Pillow), and allow these domains. On your computer and in chat nothing needs setting up.

| Domains | Fetched by | For |
|---|---|---|
| `*.salesforce.com`, `*.force.com`, `*.site.com`, `*.salesforce-sites.com` | Every skill that reads or deploys to the org; build-site-pages and flow-access-fix for the live site check | The org, its sites and their files |
| `*.formassembly.com`, `*.tfaforms.com`, `*.tfaforms.net` | form-migrate, formassembly-capture | FormAssembly forms and their API |
| `docs.google.com` | form-migrate | A public Google Form |
| `fonts.googleapis.com`, `fonts.gstatic.com` | form-design, design-to-blocks, build-site-pages, brand-kit | Web fonts in the drawings and the headless checks |
| The organization's own website | brand-kit, design-to-blocks | Logos, colors, fonts and wording, read once with the person's agreement |
| `playwright.azureedge.net`, `playwright-akamai.azureedge.net`, `playwright-verizon.azureedge.net` | The headless browser install, once per session | The Chromium download for Playwright 1.47 |

## Optional tools

| Tool | Version | Used by | Without it |
|---|---|---|---|
| Playwright with Chromium (Node) | `playwright@1.47.2`, installed once with `npx -y playwright@1.47.2 install chromium` (or `chromium-headless-shell`) | form-design, design-to-blocks, build-site-pages, brand-kit and flow-access-fix, for headless render checks | The skill skips the render check and says so; the files it writes are the same |
| Pillow (Python) | Any current version, `pip install Pillow` | brand-kit (thumbnails, format conversion, the banner crop), build-site-pages (`asset_files.py convert`) | Images are used as they are; the skill names the steps it skipped. Their tests skip the Pillow cases |
| poppler (`pdftotext`), or the `pypdf` library | Any | form-migrate, for PDF forms | form-migrate's `pdf_text.py` tries poppler, then pypdf; with neither, the form is transcribed by hand into a capture file and marked as hand-authored |
| The Salesforce CLI | Current | Every step that reads or writes the org from Claude Code | Chat uses a connector; with neither, see the last line of the sign-in section |

Every other script is Python 3 standard library only. Nothing needs a local web server, a desktop browser or a tool that runs only on one operating system: browser checks run headless, and a page for review is a file in the project (or an artifact where chat offers one).
