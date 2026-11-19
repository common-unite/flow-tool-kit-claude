# The files and what each column means

CSV files are UTF-8 with a byte-order mark, so Excel and Google Sheets open them with accents intact. Link columns hold Lightning addresses when the org's address is known (always in Claude Code; in chat, pass `--instance-url` to `build`), and are blank otherwise.

## data_dictionary.csv and data-dictionary.md

One row per field. Every custom field of an audited object (Form Submission, plus each `--object`) gets a row; a field of any other object gets one only when something uses it. With `--template`, only the fields that template uses.

| Column | Meaning |
|---|---|
| Object, Field Label, API Name, Type | From FieldDefinition and EntityParticle |
| Description, Help Text | The field's own, as Setup shows them |
| Security Classification, Compliance Group, Business Status | Salesforce's governance fields (Data Classification and Field Usage in Setup) |
| Sections, Rules, Mappings, Prefill, URL, Merge, Flows | How many uses of each kind (see Buckets) |
| Total Refs | Their sum |
| Surfaces | Each surface that uses it, by name (`Section Form; Form Template Mapping; Flow Action`), so a field the Mappings bucket counts shows whether a Form Template Mapping, a source or a nullable list uses it |
| Used In | The templates (or forms, or Flow Tool Kit flows) that use it, six at most |
| Mapped With | Its partner in a Form Template Mapping, with the form's name: `Account.Phone (Partner Organization)` on the Form Submission landing field, the landing field on the source field |
| Verdict | See Verdicts; custom fields only |
| Documentation | What the field lacks under the documentation standard, fields the org owns only |
| Field Link | The field in Object Manager |

A row with no label and the note `not a field on this object` is a reference to a field that does not exist: renamed, deleted, or misspelled in a config. Fix the config.

### Buckets

| Bucket | Surfaces |
|---|---|
| Sections | Section Form, Header Form, Footer Form, Table Form |
| Rules | Page Rule, Section Rule, Payment Rule |
| Mappings | Form Template Mapping, Source Mapping, Source Config, Nullable |
| Prefill | Prefill Values |
| URL | URL Parameter |
| Merge | Merge Token |
| Flows | Flow Screen Form, Flow Element, Flow Formula, Flow Action |

## Verdicts

The verdict answers one question: does Flow Tool Kit reference this field? It is never based on records (the audit reads no Form Submission data), and never on Apex, reports, page layouts or flows outside Flow Tool Kit, which Setup's **Where is this used?** lists.

| Verdict | When |
|---|---|
| Active | Referenced or mapped in Flow Tool Kit: a Form Template, page, page section, Form Component (metadata, record or JSON), rule, mapping, prefill, URL parameter, merge token, or a Flow Tool Kit flow (conversion, prefill, the screen flow a Flow Section shows, one using a Flow Tool Kit action or screen component, or their subflows). The places are listed in Surfaces, Used In and the reference files. A Form Template Mapping counts: a landing field used only through one is Active |
| Unreferenced | No Flow Tool Kit place references it. A field used only in a flow outside Flow Tool Kit is Unreferenced here; Where is this used? shows that flow |

Only custom fields get a verdict. A field with the org's own namespace (a namespaced development org) belongs to the org. An unreferenced field an installed package owns is marked Packaged in `data-dictionary.md`: a subscriber cannot delete it.

## Documentation checks

From the plugin's documentation standard ([_shared/standards/documentation.md](../_shared/standards/documentation.md)), on custom fields the org owns:

| Gap | Rule |
|---|---|
| `no description` | Every custom field ships with a description |
| `no help text (a Form Template field needs two sentences)`, `help text is one sentence (...)` | Form Template fields are read by the people who build templates, so their help is required and at least two sentences |
| `help text over 255 characters` | Inline help is 255 characters at most |
| `... cites an issue number`, `... has an em-dash` | Descriptions and help stand alone: no ticket numbers, no em-dashes |

Form Submission fields need no help text (it can show to respondents), so its absence is not a gap.

## template_references.csv

One row per place a template or form uses a field: Object, Field Label, Field API Name, Surface, Role, Form Template, Page, Section, Component Type (`Metadata`, `Record` or `JSON` for a form built in place, `Email Template`, `Prefill Template`), Component, Snippet, and links to the field, template, page, section and component. The Snippet shows the context: a rule's operator and value, a mapping's partner, the merge text, a prefill value, the email template part a merge field is in. For a prefill template it names the field set, never the value.

Roles include: `input field`, `rule operand` (page, section and payment rules, and the field and section rules inside a Form Component), `min-date bound`, `max-date bound`, `related-field override / score target`, `column class driver`, `merge token` (inside a form), `merge token in <place>` (such as `merge token in confirmation message` or `merge token in page header text`), `merge field in the <email> template`, `URL parameter target`, `prefill value key`, `prefill template sets it`, `merge token in a prefill template value`, `may be cleared by a blank answer`, `keeps a mapped answer`, `mapped to Form Submission`, `mapping lookup`, `source pointer (<setting>)`, `mapping target`, `mapping source path` (`(live)` when the source keeps the answer in step).

## flow_references.csv

One row per place a Flow Tool Kit flow uses a field: Flow, Flow API Name, Flow Type, Flow Tool Kit Role, Element, Element Type, Surface (`URL Parameter` for a field given a Get URL Parameters output, with the role `URL parameter target (pv1)`), and a Resolution of `parsed` or `not captured` (a form chosen at run time, or a field set whose members are not expanded).

Flow Tool Kit Role says why the flow is listed, each reason once: `conversion flow (Contact1) of template <name>`, `conversion flow of section <title>`, `prefill flow of template <name>`, `Flow Section screen flow of section <title>`, `uses the Flow Tool Kit action <name>`, `uses the Flow Tool Kit screen component <name>`, `calls the Flow Tool Kit flow <name>`, `subflow of <flow>`. A flow with none of these is never listed.

## coverage.csv

| Status | Meaning |
|---|---|
| parsed | Read, with counts |
| not_captured | Deliberately or necessarily not read: Flow Tool Kit's own default conversion flows and other package flows (an org does not serve their metadata), a flow whose metadata could not be read, prefill template records or email templates when that read failed, a store an older package lacks |
| unparseable | Stored JSON that could not be read; the Detail names the template, page or section |
| missing | A form, flow, email template or prefill template that resolves to nothing (a template naming a conversion flow the org does not have, an email template you cannot read), or a read that failed |
