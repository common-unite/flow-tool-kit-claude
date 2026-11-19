# Source: FormAssembly

The richest source this skill reads, and the only common platform whose
Salesforce connector doubles as the migration spec. **The connector
configuration is not the obstacle - it is the specification.** It already
contains the object graph, execution order, matching predicates, skip
conditions, and field mappings.

## The three inputs

Collect all three per form. None is optional; each carries something the others
do not.

| Input | Where from | Carries |
| --- | --- | --- |
| `connector.html` | Connector config page, **read-only view** | Object graph, execution order, matching predicates, skip conditions, field mappings, connector options |
| `aliases.html` | Field alias page, **HTML** not text | Section paths, field ids, and every option id with its label |
| `form.html` | The public form URL | Section tree, input types, validation, dependent picklists, conditional visibility, images, custom scripts |

**Always ask for the read-only connector view.** The edit view repeats the org's
entire object and field list in a `<select>` for every node - roughly ten times
the bytes for zero extra information.

**Always take the alias page as HTML.** Its rows are explicitly classed
(`field-path`, `field-choice`), which removes every parsing heuristic the text
export needs. The text parser still exists as a fallback.

The alias export is the only thing that can resolve an option id, and both
connector formulas and form conditions reference option ids directly. Without
it, rules read as opaque `tfa_` strings.

## Public form only (no account, no exports)

A public form link has no alias export and no connector. `build_from_files` then builds the aliases from the page itself (`page_aliases`, which reads labels, option labels and titles and legends in any attribute order: selects with `aria-required` first, options carrying `data-conditionals`, matrix rows labelled by a `th`), and the connector is `not_captured`: prefill, lookups and mappings are unknown, not absent, so raise them as review questions.

```bash
python3 -I <skill>/scripts/capture_public.py <form_id> _forms/formassembly-<form_id> "<Form name>"   # downloads form.html if missing, writes ir.json
```

If the sandbox cannot reach the address, save the page (Save Page As, Web Page HTML only) and pass it with `--html`. With no scripts at all, read the page yourself: [../chat-extraction.md](../chat-extraction.md).

## API access

With an access token for the FormAssembly account, `formassembly_api.py` reads the form and its connector list through the REST API. Save the token in the plugin's **FormAssembly access token** setting (sensitive: masked, kept in the system's secure credential store, read as `CLAUDE_PLUGIN_OPTION_FORMASSEMBLY_ACCESS_TOKEN` where Claude Code passes it to the script). The fallback is the session's environment variable, which the setting wins over when both are set:

```bash
export FORMASSEMBLY_ACCESS_TOKEN=...      # fallback, in the session's environment only; never in a file or the chat
export FORMASSEMBLY_API_BASE=https://<instance>.tfaforms.net/api_v1/   # plans other than formassembly.com
python3 <skill>/scripts/formassembly_api.py <form_id> _forms/formassembly-<form_id> "<Form name>"
```

| Endpoint | Gives |
|---|---|
| `forms/view/<form id>.json` | The form definition, saved as `api-form.json`. When it carries the form markup, that becomes `form.html`; otherwise the public page is read |
| `connectors/index/<form id>.json` | Which connectors the form has, saved as `api-connectors.json` and listed in the findings |
| `admin/api_v1/connectors/view/<id>.json` | One connector's definition, saved as `api-connector-<id>.json`. Needs a token from an admin user |

The token travels as the `access_token` query parameter, as the FormAssembly API reference shows, and never reaches a file or an error message. **The connector mapping is not trusted from the API yet**: until a live run shows that the API's connector definition carries what the read-only view page shows (objects, order, matching, field mappings), connector coverage stays `not_captured`. Save the connector's read-only view page as `connector.html` beside the IR for the mapping.

## Capturing a whole account

When you can sign in to the organization's FormAssembly account, use the **formassembly-capture** skill instead of asking for exports. It captures every form, checks the capture is complete, and builds the archive with this parser.

## Running it

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from formmigrate import ir, validate
from formmigrate.sources.formassembly import adapter

D = "_forms/formassembly-1234567/"
document = adapter.build_from_files(D, form_id="1234567", connector_id="7654321")
open(D + "ir.json", "w").write(ir.to_json(document))
```

Then plan with `plan_form.py` (references/sources-and-running.md, Running it).

| Module | Role |
| --- | --- |
| `aliases.py` | The resolver. Auto-detects HTML or text. `resolve()` and `describe()` turn ids into business language. |
| `conditions.py` | Recursive-descent parser for the `data-condition` boolean grammar. |
| `form.py` | Rendered form: sections, inputs, conditions, dependent picklists, images, custom scripts. |
| `connector.py` | Object graph, predicates, mappings, options, and behavioral-gap findings. |
| `prefill.py` | Prefill (`salesforce_pull`) connectors: each lookup's match conditions (URL parameter, fixed value, earlier lookup), outcomes, the repeating section it fills, and its field mappings. Reads both the edit-mode and read-only layouts. |
| `adapter.py` | Assembles the three into the IR. |

The connector is optional to the adapter only because a form is occasionally
exported before its connector is available. When it is missing, coverage is
`not_captured` - never `none_exist` - because a FormAssembly form that writes to
Salesforce definitely has one.

## Sanity checks that must pass

Before trusting any output, and before showing the extraction for confirmation, check the parsed result:

- Conditional rules captured **equals** the count of `data-condition` attributes.
- Every condition reference resolves against the alias export.
- Every `%%token%%` in every formula and skip condition resolves.
- Alias fields absent from the rendered form is **zero**.

A non-zero count on the last one usually means choice-group fields are being
missed, not that the form has calculated fields.

**Take the condition count with a command that matches the attribute, not the
substring.** On the reference form, `grep -c data-condition` returns 44 while
the parser correctly finds 25 - the other 19 are `data-conditionals`, an
unrelated attribute. The naive grep makes a correct parse look broken:

```bash
grep -oE 'data-condition="[^"]+"' form.html | wc -l     # 25, the real count
```

## What the parser reports on its own

- **Multiple-match behavior gaps.** FormAssembly offers "update the most recent
  record" and "create a new record instead"; the Flow Tool Kit controller halts.
  Every node not set to skip or abort is an explicit decision for the org.
- **Orphaned target mappings.** The page publishes `_MAPPED_SFIELDS`; fields
  declared there but rendered by no node are dead configuration worth raising.
- **Ambiguous source labels.** The connector records sources by *label*, and
  labels repeat across sections - a form with two addresses has two `City`
  fields. A label alone never identifies a field; carry the id.
- **Mirrored branches.** Prefilled and not-prefilled paths usually duplicate most
  of their mappings. Report the overlap so the rebuild plans one pipeline, not
  two.
- **Custom JavaScript**, which is the only genuinely non-migratable input.

## Helper fields that exist only for the old connector

Some orgs carry fields that exist only to give the FormAssembly connector an exact match key (a `Lookup_Email__c` on Contact, say). List them as retirement candidates once matching rules cover them, but never remove one without the org's decision, and list every other user of the field first (flows, Apex, layouts, list views, reports).

## Prefill belongs in a prefill screen flow, not in staging

FormAssembly forms carry hidden prefill plumbing - an `IsPrefill` flag, a
`ContactFound` flag, and a block of fields showing an existing record ("current
membership app: name, date, status, number"). None of it is form data. In
FlowToolKit that job is a prefill screen flow keyed on the record id, so these
fields are skipped from the Field Plan, not staged. Expect a reviewer to `SKIP`
them in bulk; the workbook should make that easy.

## Parsing lessons, learned the hard way

**Text blocks keep their formatting.** Releases, waivers and policies sit in `htmlSection` blocks (`<div class="htmlSection" id="tfa_N">`). Carry them with `formmigrate.sourcetext.block_html(form.html, "tfa_N")`: the source's own markup (centered headings, numbering, indents, underlines, blank lines) in a 16px body, never re-flowed plain paragraphs. `block_ids()` lists every block with its fieldset legend, so each stays its own section. A consent's text block becomes that consent section's rich text, not help text. The IR lists every block in `form.content_blocks` (`id` is the `tfa_N`, `section` the enclosing section's id, `text` the plain text), the public read included, so form-design can check each one stays on the form.

**Repeating sections.** A `fieldset` with class `repeat section` and `data-repeatlabel` ("Register another child") repeats for each record; FormAssembly gives no limit on the page. The IR marks it on the structure entry (`repeat`, `repeat_label`) so form-design draws a Repeater. A single question can repeat on its own: its `oneField` wrapper (`id="tfa_N-D"`) carries `repeat` and `data-repeatlabel` ("Add another transcript"). The IR gives it its own structure entry (`id` `tfa_N-D`, `repeat`, `repeat_label`, `repeats_field` `tfa_N`) and the question's `section_id` points at it: a one-question Repeater. A prefill lookup set to "Repeat fields" fills one copy per record; `prefill.py` names the section.

**Calculations.** A calculated field keeps its formula in its class attribute (`formula=(unitprice*tqty).toFixed(2)`) and its variable name as `calc-<name>`. The IR carries them on the field (`calculation`, `variable`). A variable used by several fields (one per repeated row) is summed across rows.

**Required choice groups.** The `required` class can sit only on the choice wrapper (`<span id="tfa_53" class="choices vertical required">`), and the IR then reports `required: false`. Read the wrapper's class too.


Seven bugs in the first sprint shared one shape: **parse by the marker that
carries the meaning, then classify - never branch on element kind first.**

Conditions sit on choice-group wrappers as well as sections and inputs. Field
ids sit on `<table>`/`<span>` wrappers while option ids sit on the `<input>`s
inside. Section paths split only on separator spans, because segment names
legitimately contain slashes. A field with a blank label is still a mapped field.

Every one of those bugs was silent - the output looked plausible and was missing
data. Verify against a count taken independently from the source.
