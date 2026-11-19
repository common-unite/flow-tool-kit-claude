# Getting the forms: API, exports, and the browser step

Three ways in, in the order to offer them. The first two need no browser.

## 1. The FormAssembly API

**The token.** FormAssembly API tokens belong to a user and see what that user sees. A FormAssembly admin creates one through FormAssembly's API access (OAuth) for the account: see FormAssembly's own help page "Working with the FormAssembly API" and its API reference on GitHub (FormAssembly/formassembly-api). An admin user's token is needed for connector definitions and, on Enterprise plans, for `--admin` (every form in the instance, not just the user's).

**Where the token goes.** First choice: the plugin's **FormAssembly access token** setting. It is a sensitive setting: Claude Code asks for it when the plugin is enabled (or run `/plugin configure flow-tool-kit@<marketplace>`), masks what you type and keeps it in the system's secure credential store, never in `settings.json`. The scripts read it as `CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN` where Claude Code passes the setting to them.

Fallback, for the session only, and whenever a script says no token is set although the setting is saved:

```bash
export FORMASSEMBLY_ACCESS_TOKEN=...                          # typed in the terminal before starting Claude Code
export FORMASSEMBLY_API_BASE=https://<instance>.tfaforms.net/api_v1/   # only for plans not on app.formassembly.com
```

On Claude Code on the web, add the same two names to the cloud environment's environment variables. When both are set, the plugin setting wins. Never write the token into a file in the project, a settings file or the chat. When the capture is finished, the person can revoke the token in FormAssembly.

**What `collect.py api` calls.** Every call goes through form-migrate's reader (`formassembly_api.py` and `formmigrate.sources.formassembly.api`); the token travels as the `access_token` query parameter, as FormAssembly's API reference shows.

| Call | Gives | Saved as |
|---|---|---|
| `forms/index.json` (or `admin/api_v1/forms/index.json` with `--admin`) | Every form with its name, modified date and response counts | `raw/api-forms.json`, then `inventory.csv` |
| `forms/view/<form id>.json` | The form definition; its markup becomes `form.html`, otherwise the public form page is read | `archive/<id>/api-form.json`, `form.html` |
| `connectors/index/<form id>.json` | Which connectors the form has, with their event and status | `archive/<id>/api-connectors.json`, `connectors.json` |
| `admin/api_v1/connectors/view/<connector id>.json` | One connector's stored definition (admin token only) | `archive/<id>/api-connector-<id>.json`, kept for a person to read |
| `responses/export/<form id>.json?date_from=<window start>&page_size=1`, **only with `--response-check`** | Whether the form has a response in the 12-month window. The export returns whole responses (FormAssembly documents no count-only or date-only form of it), so this call is off by default and asked for first | Nothing: only the submission date is kept, in memory, and the rest is dropped at once |

**Not trusted from the API yet: the connector mapping.** The connector definition comes back as one stored mapping string whose contents FormAssembly does not document. Until a live run shows it carries what the read-only view page shows (objects, order, matching, field mappings), the mapping is read only from that page, and a form without it keeps connector coverage `not_captured`. If you run a capture and the saved `api-connector-<id>.json` does carry the full mapping, say so: it would remove the need for step 4 entirely.

**Also not in the API:** the field alias page (option labels then come from the form page itself, which is enough for most forms), and the processing and notification settings unless the definition carries them.

## 2. Exports

The person saves files from FormAssembly into one folder per form, named by the form id:

```
<exports>/
  forms.csv                         optional: form_id,name,completed,incomplete,last_response (YYYY-MM-DD)
  4100001/
    form.html                       the form page (not needed when the API run already saved it)
    aliases.html                    optional: the form's field alias page, saved as HTML
    connector-55.html               each Salesforce connector, read-only view, saved as HTML
    connector-56.html
```

- **Connector pages: the read-only view, never the edit view.** The edit view repeats the org's whole object and field list for every step: about ten times the size and nothing more. Open every object on the page before saving, or verify fails it as collapsed.
- **Save as HTML** (the browser's Save Page As, Web Page, HTML only). The connector id goes in the file name; the script tells prefill from submit pages by their content.
- **Prefill pages print a secret key** for secure parameters. The script blanks it on copy; the export folder itself still holds it, so keep it out of version control and delete it once the archive is final.
- **The alias page as HTML**, not text: its rows are classed, so option ids resolve without guessing.

Then `python3 -I <skill>/scripts/collect.py exports <exports>` and `verify.py`.

## 3. The browser step (ask first)

Only for connector pages, only after the person said yes, and only in Claude Code on their computer, where they can sign in to FormAssembly in a browser window themselves. Never type or ask for their password.

It needs a browser tool that can run a script against the signed-in page and save a download into the project: the Playwright MCP server (`browser_navigate`, `browser_evaluate`, `browser_run_code_unsafe`), which drives its own Chrome window. A browser extension that cannot save files to the project cannot run this step; use exports instead.

1. `browser_navigate` to `https://app.formassembly.com/forms` (or the plan's own host). The person signs in in that window.
2. Set the forms verify.py listed, in that tab, with `browser_evaluate`:
   `localStorage.setItem('faCaptureConfig', JSON.stringify({formIds: ["4100001"]}))`
   (add `host: "https://<instance>.tfaforms.net"` for plans not on app.formassembly.com).
3. The browser tool loads scripts only from inside the project: `mkdir -p .playwright-mcp && cp <skill>/scripts/capture_connectors.js .playwright-mcp/fa-connectors.js`, then `browser_run_code_unsafe` with `filename` set to that copy's absolute path. It returns `SIGN_IN_REQUIRED` until the person has signed in. It saves `_formassembly/raw/connectors-<time>.json`; a large account takes several minutes.
4. `python3 -I <skill>/scripts/unpack.py _formassembly/raw/connectors-<time>.json`, then `verify.py`. Any FAIL: set `formIds` to just those forms and run step 3 again.
5. Clean up: delete `.playwright-mcp/fa-connectors.js` and the downloaded `formassembly-connectors.json` the browser tool keeps beside it, and remove `faCaptureConfig` from the tab (`localStorage.removeItem('faCaptureConfig')`).

The script reads each listed form's connectors page, renders each Salesforce connector's setup page in a hidden frame, opens every object (they load their mappings only when opened), keeps only the selected values, blanks the secret key and saves the result. Payment connectors (Authorize.Net) are listed, never captured.
