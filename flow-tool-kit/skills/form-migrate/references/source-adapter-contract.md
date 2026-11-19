# The source adapter contract

Read this before adding a platform. It is short on purpose: the contract is
narrow, and everything not in it is deliberately not an adapter's business.

A form in front of you never waits for an adapter: read it by the hand-written
route ([sources/hand-written.md](sources/hand-written.md)). Write an adapter
only for a platform that will be read again and again, where a parser beats
transcription.

## The one rule

**An adapter's only job is to produce an IR document. Nothing downstream may
learn what platform it came from.**

The Field Plan, the validator, the questions, the mappings file, and the
`build-form-component` skill all read `ir.json`. When you find yourself wanting
to teach `fieldplan.py` about Jotform, the knowledge belongs in the Jotform
adapter, expressed in IR terms. A second copy of platform knowledge downstream
is how this package rots.

## Where a new source goes

```
scripts/formmigrate/sources/<platform>/      no __init__.py: a namespace package, imported as formmigrate.sources.<platform>
    parser.py       source file -> a model  (skip if the export is already JSON)
    adapter.py      model -> IR, via ir.new_document() and ir.finalize(); its docstring opens with
                    what the platform gives up, and what it does not
references/sources/<platform>.md    how to obtain the export; what to check
```

`adapter.build(...) -> dict` and a `build_from_file(s)(...)` convenience are the
whole public surface. Copy `sources/formassembly/adapter.py`; it is the
reference implementation because FormAssembly gives up the most.

## Coverage: the part everyone gets wrong

Every adapter declares, per aspect, **how it knows what it claims**:

| State | Meaning |
| --- | --- |
| `parsed` | read from a machine-readable source. Trustworthy. |
| `hand_authored` | a person transcribed it. True as of when they looked. |
| `none_exist` | the platform has no such concept. A Google Form's connector. |
| `not_captured` | it exists and nobody captured it. **An acknowledged hole.** |
| `unknown` | the adapter did not say. Treated as `not_captured`, and reported. |

Aspects: `structure`, `fields`, `options`, `validation`, `conditions`,
`connector`, `images`, `custom_scripts`.

This exists because **an empty list has three incompatible meanings and only one
is safe**. `"conditions": []` means the platform has no conditional logic, or
the parser read the form and found none, or nobody looked. Identical JSON,
opposite consequences: act on the third and you ship a form missing every
show/hide rule, and nothing in the output ever said so.

Two consumers depend on it, and both would silently mislead without it:

- **`validate.py` skips a check whose input was never captured** and says it
  skipped. A clean bill of health computed over missing evidence is worse than
  no check, because it reads as verification.
- **`fieldplan.py` only treats "no mapping" as evidence when a connector was
  actually read.** Otherwise every question on a Google Form reports as
  `not_mapped`, which a reviewer reads as a decision somebody made.

**Never declare `none_exist` to make output look clean.** If a form POSTs to an
endpoint you have not read, that is `not_captured` - something receives that
request and it is the real mapping spec.

## What an adapter must fill

`ir.new_document()` returns the skeleton; fill these and call `ir.finalize()`.

| Key | Notes |
| --- | --- |
| `fields[]` | `id`, `label`, `section_path`, `input_type`, `required`, `validation[]`, `options[]`, `present_in_rendered_form` |
| `structure[]` | `id`, `parent_id`, `layout[]`, `has_condition` |
| `conditions[]` | `element_id`, `governs` (`section`/`field`/`element`), `tree` |
| `connector` | only when the platform has one; otherwise leave empty and declare it |
| `findings[]` | `{"source": ..., "message": ...}` - anything a human must decide |

Optional keys (schema 2.1), for a source that knows what a Flow Tool Kit page
section draws. `validate_document()` checks their shape:

| Key | Holds |
| --- | --- |
| `structure[].section` | `component_type` (Field Set, Repeater, Table, Flow, Lightning Web Component, Display Text) and what that type needs: `form` for the first three, `flow_api_name`, `lwc_component_name` or `text` for the others |
| `structure[].repeat` | true on a Repeater or Table section (with `repeat_label`) |
| `fields[].repeat_section` | the Repeater or Table section a field repeats in; it must point at a node marked `repeat` |
| `fields[].submission_landing` | the Form Submission fields a component's Submission Field Map lands this answer on |

`finalize()` derives condition references, unresolved references, `reads_as`,
and branch analysis, then appends contract violations to `findings`. Deriving
those centrally is what stops a new source getting them subtly wrong.

### Conditions

Build trees with `conditions.ref/all_of/any_of/negate`, never dict literals - a
mistyped key produces a tree that looks valid and evaluates to something else.
`validate_tree()` catches the classic hand-authoring slip (`operand` singular on
an `and`, which reads as an empty AND and matches nothing).

A `ref` is whatever id identifies the thing being tested. Use the platform's
option id when it has one; synthesize `<field_id>::<option label>` when it does
not. Pass a resolver to `finalize()` - the platform's own, or
`conditions.LabelResolver` - so unresolvable references get reported rather than
passing because "no resolver" was mistaken for "nothing to check".

### Types

`validation[]` is the vocabulary the Field Plan reads to infer a staging type:
`email`, `phone`, `date`, `datetime`, `number`, `currency`, `integer`,
`checkbox`. Emit them however your platform expresses type.

**A bare `text` means "unknown", never "this is a string".** FormAssembly renders
almost everything as `type="text"` and hides the real type in a CSS class;
treating that as evidence of a string demotes every correct date, email and
phone match. HTML input types, by contrast, are honest.

## The verification standard

> Seven bugs in the first FormAssembly parser shared one shape: **parse by the marker that
> carries the meaning, then classify - never branch on element kind first.**
> Every one was silent. The output looked plausible and was missing data.

Two of those recurred verbatim while writing the HTML adapter, which is why this
section is not optional:

- A radio/checkbox **group** is ONE field; the shared `name` is the marker and
  the individual inputs are its options. Per-input parsing gives you forty
  yes/no questions instead of eight picklists.
- Option ids must live **on the option**. Pushing them onto the field's id list
  shifted every option's label by one, so the last option silently inherited the
  second-to-last one's text. Counts were right; content was wrong.

Before trusting a new adapter, **count independently from the source** and
confirm the parsed result matches:

- conditional rules captured == conditions in the source
- every condition reference resolves
- every field the source declares appears in `fields[]`
- option counts per field match the source

Take the count with a command that cannot be fooled by a near-miss. On one real
FormAssembly form, `grep -c data-condition` returns 44 and the parser correctly
finds 25, because 19 of those are `data-conditionals`, a different attribute. Match the attribute, not the substring:

```bash
grep -oE 'data-condition="[^"]+"' form.html | wc -l     # 25, the real count
```

## Registering it

1. Add the module under `sources/<platform>/`.
2. Note it in `sources/__init__.py` and in the docstring at the top of its `adapter.py`.
3. Write `references/sources/<platform>.md`: how to obtain the export, what it
   does and does not carry, and the source-specific sanity checks.
4. Add a row to the source table in `SKILL.md`, and a test with an invented
   fixture under `tests/`.
