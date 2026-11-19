# Reviewing the mappings

`plan_form.py` writes the plan as a file the reviewer edits, usually the org's admin. Their edits are read back on the next run and kept across every rerun. A file is the only thing that works the same in claude.ai chat, Claude Code on a computer and Claude Code on the web.

## The files

| File | For |
|---|---|
| `mappings.csv` | Any spreadsheet app or text editor |
| `mappings.json` | The same rows as JSON, with the how-to and the counts on top; for a script, an editor, or an artifact page |
| `decisions.json` | The edits lifted out of either file, keyed by field id. Kept across reruns; edit it by hand only for the richer decisions below |
| `name-overrides.json` | Judgment renames (`{"renames": {"<field id>": "Better_Name__c"}}`), applied after the mechanical clean-up |

Columns, in order: **Decision, Your Field Name, Your Notes** (the reviewer's), then Form Name, Section Path, **Field ID**, Field Label, Form Submission Field Name and Label, Built On, Reaches Target By, Verify In Org, Origin, Target Object, Target Field, Disposition, Confidence, Notes.

## What the reviewer writes

| Column | Write |
|---|---|
| Decision | `OK` to accept the row as proposed, `SKIP` to leave the question out. Common variants (yes, approve, no, drop) are understood |
| Your Field Name | A different API name to use instead |
| Your Notes | Anything else; carried into the row's notes |

Three behaviours are deliberate:

- **Blank means not reviewed.** An untouched file never reads as accepted; the row keeps its original confidence.
- **Anything else in Decision is flagged, never guessed.** "maybe?" leaves the row as it was, with a note asking what was meant.
- **Accepting a "Needs your decision" row settles it.** The confidence becomes confirmed and the row takes the proposed field, so the count of open decisions falls.

Tell the reviewer not to change Field ID: it is how each answer is matched back. Everything else may be sorted, filtered or reformatted.

## Reading edits back

Run `plan_form.py` on the folder again. It reads the newer of `mappings.json` and `mappings.csv` (or the file named with `--edits`), saves the edits into `decisions.json`, applies them, and writes fresh files that show them. CSV files are read with `utf-8-sig`, because many spreadsheet apps add a byte order mark that would otherwise corrupt the first column name.

## Richer decisions

Some decisions are said in words and recorded by hand in `decisions.json`:

```json
{"decisions": {
  "tfa_41": {"action": "extend_packaged", "field_name": "FlowToolKit__Race__c",
             "values": ["Value to add"], "note": "Fits except two values"},
  "tfa_52": {"action": "formula", "field_name": "Is_Member__c", "type": "Formula (Checkbox)", "note": ""},
  "tfa_60": {"action": "approve", "field_name": "", "type": "LongTextArea", "note": ""}
}}
```

- `extend_packaged`: the packaged picklist is the right field; add the listed values to it in this org (a subscriber org can add values to a restricted packaged picklist; map each new value to its controlling values when it is dependent).
- `formula`: a formula field instead of a stored answer.
- `approve` with `type`: accept the row and force its field type.

## The optional artifact

When the session can publish an artifact (claude.ai, or Claude Code with artifacts), publish a review page built from `mappings.json`: one table per section, the reviewer's three columns first, Verify In Org rows marked. It is for reading and sharing; the file stays the record.

If the page lets the reviewer edit (an artifact that keeps what people type), read the edits from it, write them into `mappings.json` under the same Field IDs, and run `plan_form.py` again. Never treat the page alone as the record: anything not written back to the file is lost on the next run. Without artifacts, the files are enough.
