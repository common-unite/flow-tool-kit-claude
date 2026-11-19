# Source: Google Forms (and the capture format for anything with no export)

A Google Form has no export and no Salesforce connector, but its public page carries the whole form as data in a script variable, `FB_PUBLIC_LOAD_DATA_`: every section, question, choice, required flag and "go to section based on answer" branch. A browser or a text fetch shows only the first section; the data holds them all. `sources.google_forms` reads it.

## Reading a link

```bash
python3 <skill>/scripts/capture_google_form.py "<viewform address>" _forms/google-<slug>
python3 <skill>/scripts/capture_google_form.py "<viewform address>" _forms/google-<slug> --html saved-form.html
```

The first form downloads the page; the second reads a page the person saved (Save Page As, Web Page HTML only), for a sandbox that cannot reach the web. It writes `form.html` and `ir.json`.

| Read | How it lands in the IR |
|---|---|
| Sections (page breaks) | One structure entry and section path each; the first is the form's title |
| Questions | Field id `entry.<id>` (the id a prefilled link uses), label, help text, required, type |
| Grids | One question per row: "Question: Row" |
| Linear scales | Choices 1 to N, with the end labels in `scale_labels` |
| Title and description items | Content blocks, kept with their section |
| Images and videos | `images` |
| A choice that jumps to a section | A rule on that section: shown when that choice is chosen |
| A choice that submits the form, the Other choice | Findings: the rebuild needs the same early finish, or a text box shown when Other is chosen |

Coverage: structure, fields, options, conditions and images `parsed`; validation `not_captured` (only the required flag is read, not response validation); connector and custom scripts `none_exist`.

**The data format is not documented by Google.** The parser reads only positions it is sure of and reports anything else (an unknown type code is read as text with a finding). Check every result against the live form before trusting it:

- the section count matches the pages you click through;
- the question count per section matches;
- each branching question's choices and where they lead match the form's "go to section" settings.

Google branching is navigation, not visibility: a section can also be reached by continuing from the one before it. Every branch rule is listed for confirmation.

With no scripts, read the link yourself: [../chat-extraction.md](../chat-extraction.md).

## The capture format (manual adapter)

When a form gives up nothing machine-readable (Microsoft Forms, a paper form photographed on a phone, a PDF read without text tools, a page read in chat, a brief), a person or Claude writes `capture.json` and the manual adapter turns it into the same `ir.json` a parser would. Every aspect is declared `hand_authored`, so a reader always knows a person, not a parser, made the claim.

1. **Walk every page** of the live form; a form that branches shows different pages to different answers, so walk each path.
2. **Write `capture.json`.** Transcribe values letter for letter, suspected typos included: put the typo in `label` and the observation in `note`. A rebuild that quietly fixes wording cannot be compared with its original.
3. **Build the IR**, then treat it like any other source.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from formmigrate import ir
from formmigrate.sources.manual import adapter

D = "_forms/manual-volunteer-survey/"
document = adapter.build_from_file(D + "capture.json")
open(D + "ir.json", "w").write(ir.to_json(document))
```

```json
{
  "platform": "microsoft-forms",
  "form_name": "Riverside Garden Volunteer Survey",
  "source_url": "https://forms.example.org/volunteer-survey",
  "captured_by": "the person who walked the form",
  "captured_on": "2026-01-15",
  "coverage": { "conditions": "none_exist" },
  "pages": [
    {
      "name": "About You",
      "intro": "<p>Thank you for volunteering this season.</p>",
      "fields": [
        { "label": "First Name", "type": "text", "required": true },
        { "label": "What is your main role?", "type": "multiple_choice",
          "options": ["Grower", "Teacher", "Volunteer", "Other"] },
        { "label": "Please descibe", "type": "paragraph",
          "show_when": "What is your main role?::Other",
          "help": "A sentence or two is plenty.",
          "note": "Typo is in the source form; transcribed as shown, flagged for content review." }
      ]
    }
  ]
}
```

Everything mechanical is derived, because those are the things a person transcribing forty questions gets subtly wrong:

- **`id` is optional**: derived from the label and made unique. Keep a source id (`tfa_12`, `entry.2001`) when there is one.
- **`show_when` references fields by label**, resolved to ids for you. `"Field Label::Option Label"` means "that field is set to that option". Nest with `{"all": [...]}`, `{"any": [...]}` and `{"not": ...}`. Forward references work. A page may carry `show_when` too.
- **Option ids are made up** as `<field id>::<option label>`.
- **Types are read generously**: `multiple_choice`, `paragraph`, `linear_scale`, `checkboxes`, `dropdown`, `email`, `phone`, `date`, `currency`, `boolean`, `file` and their variants. An unknown type becomes text **and raises a finding**, never a silent guess.
- Page `intro` is kept as a content block; page `repeat: true` with `repeat_label` marks a repeating section; field `help` is help text.
- **`unknown` on a field lists what the source did not show**: any of `label`, `type`, `required`, `options`, `help`, `show_when` (a photo cut off at the edge, a drop-down shown closed). Each becomes a finding to confirm, and the field keeps the list, so a guess never reads as a fact. A `yes/no` question with no options gets Yes and No.
- **Coverage may be declared** for `options`, `validation`, `conditions`, `connector`, `images` and `custom_scripts`; set any of them to `unknown` when the source did not settle it.

### Declare whether conditions exist

With no `show_when` anywhere, the adapter cannot tell "no rules" from "nobody checked", so conditions stay `unknown` and a finding says so. Once every page has been walked and there is no branching, say so with `"coverage": { "conditions": "none_exist" }`. That is the difference between "checked and simple" and "unchecked".

## Improvements are decisions, never silent changes

List each one for the org's people; do not just make it:

- **A single Name split into First and Last**: Contact matching needs a last name.
- **A free-text State absorbed into an `addressSection`**: Salesforce address checking replaces the free text and any city list.
- **Newly required fields**: match keys the old form left optional.
- **A two-choice checkbox list used for a yes/no question** becomes a single choice.
- **Year-stamped wording** ("In 2025, how many acres...") goes into the field's custom label with the current year; the yearly relabel becomes an admin task, never a merge-field trick.

## What you do not get

There is no connector, so `coverage.connector` is `none_exist` and the IR carries no targets. The plan still proposes Form Submission fields by matching question text against the packaged list, but with no object graph to say which person a question describes, matches into the Contact 1, Contact 2 and organization blocks come back as questions with candidates attached (the section a question sits in breaks ties). Every mapping becomes a question for the org's people, settled in the mappings file and then in new-mapping-flow.
