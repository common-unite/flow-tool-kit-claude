---
name: formassembly-capture
description: Capture every form in an organization's FormAssembly account at once, to archive it or convert it to Flow Tool Kit (FTK). Reads each form's design, field aliases, calculations, show/hide rules and its Salesforce prefill and submit connectors, checks the capture is complete, and turns it into a readable archive, an account map (hand-offs, objects, shared sections), one shared conversion and prefill flow plan, checked plain-language summaries and review pages. Use when an organization is leaving FormAssembly with more than a few forms, or someone asks to archive, inventory or bulk-convert a FormAssembly account. Works from the FormAssembly API and saved exports with no browser; a browser sign-in is offered only for connector mappings, and only after asking. Runs in Claude Code, on your computer or on the web. For one form, or in claude.ai chat, use form-migrate.
---

# FormAssembly account capture

Capture every form in a FormAssembly account into the project, prove the capture is complete, and turn it into what a rebuild needs: one readable folder per form, a map of how the forms connect, one flow plan for the whole account, a checked plain-language summary per form, and review pages.

This is the bulk companion to **form-migrate**. Both read FormAssembly with the same reader and parsers (form-migrate's `formassembly_api.py` and its FormAssembly source), so a form captured here and a form read by form-migrate give the same `ir.json`. Use form-migrate for one form; use this skill for an account.

## Where it runs

| Surface | What works |
|---|---|
| Claude Code on your computer | Everything: the API, exports, and the optional browser step for connector pages, where the person signs in themselves |
| Claude Code on the web | The API and exports. No browser step: nobody can sign in to a browser on the cloud machine, so connector pages come as exports |
| claude.ai chat | No account capture: there is no shell for the API and no folder to build the archive in. Say so in one line: "In chat I can read one exported FormAssembly form (its page, alias page and connector read-only view) and explain what it does and how it maps to Salesforce; that is form-migrate's job." Then follow **form-migrate** for that form |

## Before you start

1. **The plugin is installed whole.** The scripts import form-migrate's reader from `_shared/lib/` or from the form-migrate skill beside this one; `scripts/reader.py` stops with a clear message when neither is there.
2. **Read the project config.** ftk-start writes `flow-tool-kit.json` at the project root ([_shared/standards/project-config.md](_shared/standards/project-config.md)). Take the org's edition (paid or free) from it: the flow plan's packaged rules take their answers through Form Template Mapping on a paid org and through the flow's Transform on a free one ([_shared/standards/mapping-preference.md](_shared/standards/mapping-preference.md)).
3. **Output goes in the project**, under `_formassembly/` at its root. Add `_formassembly/raw/` to `.gitignore`: it holds API listings and browser bundles, and the archive folders carry the same content.
4. **Ask which access the person has**, in one question, and say what each gives:
   - **A FormAssembly API access token** (the default): every form, its markup, its connector list and the response counts, with no browser and no respondents' answers. Connector mappings still need step 4.
   - **Exports**: one folder per form with the saved form page and each Salesforce connector's read-only view page. Works without a token, and fills in the connector mappings the API does not give.
   - **Both** (the most complete without a browser): the API first, then exports for the connector pages.

**The token.** Give it in one of two ways. First choice: the plugin's **FormAssembly access token** setting, which is marked sensitive, so Claude Code masks it and keeps it in the system's secure credential store, never in `settings.json` (it is asked for when the plugin is enabled, or with `/plugin configure`). The scripts read it as `CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN` where Claude Code passes the setting to them. Fallback: the session's environment variable `FORMASSEMBLY_ACCESS_TOKEN`, set in the terminal before Claude Code starts on your computer, or in the environment's variables for Claude Code on the web; use it when a script says no token is set although the setting is saved. Never in a file (no `.env`, no settings file, no notes) and never in the chat. The scripts send it to FormAssembly and nowhere else, never print it, and never put it in an error message; `verify.py` fails if any file in `_formassembly/` holds it. If someone pastes a token into the chat, do not use it: tell them to revoke it in FormAssembly and create a new one. Plans not on app.formassembly.com set `FORMASSEMBLY_API_BASE` (`https://<instance>.tfaforms.net/api_v1/`). How to get a token and how to save exports: [references/getting-the-forms.md](references/getting-the-forms.md).

## The run

All paths are relative to the project root; `<skill>` is this skill's folder. `-I` runs Python isolated from the environment's Python paths, because the scripts read files downloaded from another system.

| # | Step | How | Stop when |
|---|---|---|---|
| 1 | Collect through the API | `python3 -I <skill>/scripts/collect.py api` (`--admin` with an admin token lists every form in an Enterprise instance; `--forms 101,102` limits the run). Writes `inventory.csv` and `archive/<id>/` | It prints `error:` (token missing or refused): fix the access, never work around it |
| 2 | Collect from exports | `python3 -I <skill>/scripts/collect.py exports <folder>`. Alone, or after step 1 to add connector pages. A run updates only the forms it reads | |
| 3 | Verify | `python3 -I <skill>/scripts/verify.py`. FAIL lines are lost data or a kept secret; GAP lines are Salesforce connectors whose mapping is not captured yet | Any FAIL: fix that form (re-save its export, or rerun steps 1 to 2 with `--forms`), verify again |
| 4 | Connector gaps | Show the GAP list and ask how to fill it (below). Default: exports | |
| 5 | Keep list | Show the status counts and the "keep too?" lines verify printed (forms a likely kept form sends people to). Ask which statuses and which suggested forms to keep, once. Default: active + check + the suggestions. Many forms at `check` means last use is unknown, not that they are in use (Status and the keep list below) | |
| 6 | Build | `python3 -I <skill>/scripts/build.py --title "<Organization> FormAssembly archive" --status active,check --forms <suggested ids>`. Writes `kept.txt`; everything after reads only those forms | A form prints `FAILED`: read its error, fix the capture, rebuild |
| 7 | Account map and flow plan | `python3 -I <skill>/scripts/account_map.py`, then `python3 -I <skill>/scripts/flow_plan.py` (it also scans `force-app*` for controller clones the org already has) | |
| 8 | Summaries | One `archive/<id>/summary.md` per built form, following [references/summary-outline.md](references/summary-outline.md). For more than about ten forms, split the forms between two helper agents; otherwise write them yourself | |
| 9 | Check pass | Required, never skipped: a fresh pass (a helper agent, or you after the summaries are done) following [references/check-pass.md](references/check-pass.md). Its table goes in `_formassembly/check-pass-report.md` | A claim it cannot prove stays "unclear" |
| 10 | Pages | Rerun step 6 with the same options (so the index links the summaries), then `python3 -I <skill>/scripts/render_pages.py --title "<Organization> FormAssembly archive"`. Open `_formassembly/pages/index.html` from the folder, or publish `pages/` as one multi-file page where your Claude Code has an artifact tool (`index.html` plus every `forms/<id>.html` at the same path) | |
| 11 | Hand off | Below | |

Steps 6, 7 and 10 are deterministic and rerunnable, and none of them touches `summary.md`: rerun them after any recapture.

### Filling the connector gaps (step 4)

The API lists every connector but returns its mapping as one stored definition that no one has shown to carry the objects, matching rules and field mappings in readable form, so the mapping is taken only from the connector's **read-only view page**. Offer, in this order:

1. **Exports (default, works everywhere).** The person opens each listed connector in its read-only view and saves the page into `<exports>/<form id>/connector-<connector id>.html`; then step 2 and step 3 again. verify.py prints the form ids to fill.
2. **The browser step (Claude Code on your computer only, ask first).** Ask: "Do you also want me to capture the Salesforce connectors (prefill and submit) for these forms in a browser? That needs a browser window where you sign in to FormAssembly yourself; I never type your password." Only on a yes, follow [references/getting-the-forms.md](references/getting-the-forms.md), "The browser step". It reads only the connector pages of the listed forms.
3. **Go on without them.** The archive is still built; each form without its connector pages carries connector coverage `not_captured` (unknown, never "none"), and its summary says so.

### Hand off

| What | Goes to |
|---|---|
| Each kept form's `archive/<id>/ir.json` | **form-design** (through ftk-start), as form-migrate's output would; run **form-migrate**'s planning on it first when you want the field plan and the questions for the org |
| `flow-plan.md` | **new-mapping-flow**, Step 0, "a whole account moving off FormAssembly": each conversion rule once, each prefill flow once |
| `account-map.md`, Shared component candidates | **org-catalog** (does the org already have it?) and **build-form-component** (one shared component per candidate) |
| The pages and summaries | The people deciding the rebuild: what each form did, checked |

FormAssembly runs one prefill and one submit connector per form; Flow Tool Kit shares conversion flows per object and prefill flows per entry record. The flow plan is where that translation happens: twenty-odd submit connectors with almost as many different object sequences typically become a few dozen shared rules, several of them packaged, and the prefill connectors collapse to a handful of prefill flows.

## What each step writes

| File | From | Holds |
|---|---|---|
| `inventory.csv` | collect.py | Every form: responses, last modified, last response when known, status and its basis, connectors |
| `archive/<id>/form.html`, `aliases.html` | collect.py | The form markup (API definition, public page or export) and the alias page when exported |
| `archive/<id>/connectors.json`, `connector-<type>-<id>.html` | collect.py, unpack.py | The connector list, and each Salesforce connector's read-only page when captured |
| `archive/<id>/api-*.json`, `settings.json` | collect.py (form-migrate's reader) | The API responses, and the settings the definition carries (the after-submit redirect, notifications) |
| `kept.txt` | build.py | The forms built in the last build |
| `archive/<id>/logic.md` | build.py | Settings, prefill lookups (match rule, outcomes, repeating section filled), calculations with variables shown as fields, repeating sections, every Salesforce step with match rule and field sources, show/hide rules. Field ids replaced by labels; fields that share a label carry their section |
| `archive/<id>/mapping.csv` | build.py | Every prefill and submit mapping, one row each |
| `archive/<id>/ir.json` | build.py | form-migrate's form description (with calculations and repeat flags) plus prefill lookups, extra submit connectors and settings |
| `account-map.md` / `.json` | account_map.py | Form-to-form hand-offs with the parameters passed, the URL parameters each prefill expects, which forms read, create and update each object, shared component candidates |
| `flow-plan.md` / `.json` | flow_plan.py | The account's conversion rules in controller order (packaged, new, related rows, side records, payment), the forms using each, match rules, record types, order conflicts and steps to drop; the controller choice; each form's rules; shared prefill flows by entry record with each form's extra lookups |
| `archive/<id>/summary.md` | step 8 | Purpose, plain rules and the rebuild checks, checked |
| `pages/` | render_pages.py | Account overview and one analysis page per kept form |

## Status and the keep list

Capture every form; the keep list only decides what gets built and summarized. A form's status uses a 12-month window ending on `--today` (default: the day of the run), so the same capture always gives the same list:

| Status | Meaning |
|---|---|
| active | At least one response in the window: from `forms.csv` in an export, or through the API with `--response-check` |
| inactive | Responses, none in the window |
| never used | No responses at all (from the response counts, which carry no answers) |
| check | Has responses, and when it was last used is not known. Through the API this is the default for every used form |

**Respondents' answers are never read unless the person turns it on.** A response in an organization's FormAssembly account is its respondents' personal data, and an archive of form designs and connectors does not need any of it. The API gives each form's response counts without answers, but no last-response date; the only dated call, the response export, returns whole responses, and FormAssembly documents no count-only or date-only version of it. So by default `collect.py api` reads counts only: a form with no responses is "never used" and every other form is "check", which the default keep list keeps.

When the person wants active and inactive told apart, ask once: "To tell which forms were used in the last 12 months, I can read one response from each used form, keep only its submission date, and discard the rest straight away. Nothing from it is saved. Shall I?" Only on a yes, run `collect.py api --response-check`. The alternative that reads no answers: ask the person for each form's last response date (from FormAssembly's own response list) in a `forms.csv`, and run `collect.py exports` with it.

## Why it is shaped this way

| Constraint | Consequence |
|---|---|
| The API's connector definition is one stored string whose contents are not documented | Connector mappings come from the read-only view page; the API list only tells which connectors exist |
| A connector page loads each object's mappings only when it is opened | The browser step opens every object before saving; an exported page saved with objects collapsed fails verify |
| Prefill setup pages print the secure-parameter secret key | Every capture blanks it; verify fails if one remains |
| A plain fetch of a connector page looks complete and is not | verify fails a connector under 2 KB or with objects left collapsed |
| FormAssembly's error page is a normal 200 response | The browser step counts a page as failed only when its title says so |
| The token must never reach a file | It is read from the plugin setting or the environment per request; verify scans every captured file for it |
| Responses are respondents' personal data | None is read by default. With `--response-check`, one row per used form, of which only the submission date is kept, in memory |

## Checks verify.py enforces

A form page with no fields; show/hide rule counts that changed on disk; a Salesforce connector with no page (GAP, or FAIL with `--require-connectors`), with objects still collapsed, under 2 KB while enabled, or with a capture error; any secret key; the access token in any file. These are the ways a capture loses data without an error.

## Common mistakes

| Mistake | Instead |
|---|---|
| Asking for the token in the chat, or saving it to a file "for next time" | The plugin's sensitive setting, or the environment variable; a pasted token is revoked and replaced |
| Opening a browser without asking | The API and exports first; the browser only on a yes, only for connector pages, only where the person can sign in |
| Trusting a capture because the parser ran without error | Run `verify.py`; it is the only completeness check |
| Reading "no connector page" as "no connector" | Coverage stays `not_captured`; the summary says the steps are unknown |
| Archiving only active forms | Capture all; the keep list only decides what gets built |
| Typing the keep list by hand | Use the statuses and the "keep too?" lines |
| Skipping the check pass because the summaries read well | Run it: in real captures about one claim in five was false and plausible, most of them two fields with the same label read as one |
| Counting steps or mappings by hand for a page | Use the rendered page |
| Removing a helper field that existed only as the old connector's match key | List it as a retirement candidate (rebuild check 11); the org decides, after its other users are listed |

Naming and descriptions for anything built from this archive follow [_shared/standards/naming.md](_shared/standards/naming.md) and [_shared/standards/documentation.md](_shared/standards/documentation.md).
