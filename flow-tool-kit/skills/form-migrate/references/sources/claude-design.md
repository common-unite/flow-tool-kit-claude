# Source: design file (`.dc.html`)

A form drawn as a `.dc.html` design file, the format a Claude design canvas saves. **The best-structured source this
skill reads**: a question is not reconstructed from markup, it is declared:

```html
<dc-import name="Choices" label="What worked well? Choose all that apply."
           options="Food and drinks|Music and performances|Kids' activities"
           multi="{{ true }}"></dc-import>
```

No label-association guessing, no choice-group reconstruction, no prompt-option
ambiguity: the three things that make raw HTML fragile. Option sets arrive
intact and in order.

## Getting the files

Download the form file and every component file it imports from the canvas, or read them through whatever
design tool the session has; Python cannot fetch them itself. Save the form **and every component definition it imports** into
`_forms/design-<slug>/`, then parse from disk:

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from formmigrate import ir
from formmigrate.sources.claude_design import adapter

D = "_forms/design-feedback/"
document = adapter.build_from_files(
    D + "Post-Event Feedback.dc.html",
    [D + "Field.dc.html", D + "Choices.dc.html", D + "Scale.dc.html"],
    project_id="example-project")
open(D + "ir.json", "w").write(ir.to_json(document))
```

**Always fetch the component definitions too.** The adapter works without them -
it infers from the attributes each instance sets - but every field then carries a
"no component definition found" finding, because a prop the form never sets is
invisible. A definition declares the full prop schema, its editor types, enum
values and defaults.

`support.js` and `.png` assets do not need parsing; note the images for
self-hosting.

## The two file kinds

| Kind | Marker | Carries |
| --- | --- | --- |
| **Component definition** (`Field.dc.html`) | `data-props` on its `<script type="text/x-dc">`, no `<dc-import>` | the authoritative prop schema: editor type, default, enum values |
| **Form instance** (`Post-Event Feedback.dc.html`) | one or more `<dc-import>` | real labels, options and flags |

## Classification is prop-driven, never name-driven

`Field` / `Choices` / `Scale` is *one project's* vocabulary. The next kit calls
them `TextInput` / `Picker` / `Rating`. A component that accepts an `options`
prop is a choice question whatever it is named - branching on the name is
branching on element kind, the exact mistake that produced seven silent bugs in
the FormAssembly parser.

| Evidence | Reads as |
| --- | --- |
| accepts `options` | choice question; `multi` makes it multi-select |
| accepts `max` / `lowLabel` / `highLabel` / `kind`, and NOT `options` | a bounded scale; `kind` in stars/hearts/rating → rating, else numeric |
| `multiline` is true | paragraph text |
| only the common props (`label`, `hint`, `required`, `placeholder`) | single-line text |
| none of the above | **unclassified - reported, staged as text, human decides** |

**Typed text is inferred from wording and flagged as such.** HTML would carry
`type="email"`; this format carries only prose, so `placeholder="you@example.com"`
is the evidence. Every such inference raises a finding telling the reviewer to
confirm it.

## Conditions: one sc-if is not conditional logic

Every form in this family wraps its whole body in
`<sc-if value="{{ isForm }}">` with a matching `{{ isDone }}` thank-you panel.
**That is a state toggle, not conditional visibility.** Reading it as a condition
reports the entire form as conditional on itself.

The adapter distinguishes them by counting:

- an `sc-if` containing **every** field → the form/thank-you toggle. Noted, and
  `coverage.conditions` stays `none_exist`.
- an `sc-if` containing **a subset** → real branching. Its predicate lives in the
  component's JavaScript (`class Component extends DCLogic`), which this parser
  does not evaluate, so `coverage.conditions` becomes `not_captured` and a human
  must read the script.

## There is no connector, by definition

A design is a design - nothing receives a submission, so `coverage.connector` is
`none_exist` and there are no target mappings to derive. Every mapping decision
moves to the mappings file and then new-mapping-flow. The plan still proposes
Form Submission fields from question text, with matches into the Contact and
organization blocks returned as questions, because no object graph exists to
tell which person a question describes.

Budget for that conversation: of what new-mapping-flow needs (references/conversion-rules.md, The relay),
only the source fields and sections come free from this source.

## What the design tells the rebuild

The IR carries the source's *intent*, which `build-form-component` translates
under its own modernization directive. It teaches structure, never feature
selection - but the mapping is unusually direct here, because the design already
thinks in question types:

| The design says | What it means for the rebuild |
| --- | --- |
| `Scale kind="stars"` | a rating question, not a picklist of "1".."5" |
| `Scale kind="numbers" max="10"` with end labels | a 0-10 NPS-shaped scale; the end labels are real copy to preserve |
| `Choices multi` | multi-select; the package has no generic multi-select answer slot, so a multi-select needs its own field |
| `Choices` with 4+ options or long labels | single-select that must not render as a segmented bar |
| `Choices layout="stack"` | the designer already chose stacked full-width rows |
| `Field multiline` | paragraph text |
| a header `<img>` | a banner needing self-hosting as a public ContentAsset |

Section headers, intro copy and the thank-you panel are page/section data on the
Form Template, not form config - capture them, or they are lost when the template
is recreated.

## Sanity checks

```bash
grep -c '<dc-import' "Post-Event Feedback.dc.html"      # field count
grep -o 'name="[^"]*"' "Post-Event Feedback.dc.html" | sort -u   # components used
grep -c '<sc-if' "Post-Event Feedback.dc.html"          # conditional wrappers
```

Confirm: the parsed field count equals the `dc-import` count; every component
name has a definition file fetched alongside; and each field's option count
equals the pipe-separated count in its `options` attribute. Then read the
findings - every inferred type and every unclassified component is listed there.
