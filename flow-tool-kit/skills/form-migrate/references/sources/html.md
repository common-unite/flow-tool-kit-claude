# Source: a custom web form (rendered HTML)

For a form that is just HTML: a hand-built page, a WordPress or Gravity Forms
page, a design produced as an HTML artifact, a legacy Visualforce page saved to
disk, or any platform whose "export" is really just View Source.

## By address or saved page: capture_html.py

```bash
python3 <skill>/scripts/capture_html.py "https://www.example.org/volunteer" _forms/html-volunteer "Volunteer Intake"
python3 <skill>/scripts/capture_html.py saved-page.html _forms/html-volunteer "Volunteer Intake"
```

An address is fetched once with a plain GET: a 20 second timeout, no cookies,
no sign-in, and an address carrying a user name or password is refused. A page
behind a sign-in is saved from the person's browser (File, Save Page As, Web
Page HTML only) and read from the file. The script saves the page as
`form.html`, writes `ir.json`, and prints the counts to confirm.

**A form drawn by script is reported, not guessed.** Many builders (Typeform,
Jotform, Cognito Forms, Microsoft Forms, Wufoo and Formstack embeds, HubSpot,
Tally) put a placeholder in the page and draw the questions after it loads, so
the page holds no questions. The script names the builder it recognises, says
what to use instead (screenshots, the builder's export, or the form's own
address), writes no `ir.json` and exits with code 3. The same happens for a
`<form>` element with no fields in it. Then take the hand-written route
([hand-written.md](hand-written.md)). In chat with code execution off, read the
page as [../chat-extraction.md](../chat-extraction.md) describes.

Pass `--conditions-complete` only after a person has read the page's scripts
(see below).

## From Python

The adapter sees exactly what the saved markup holds and nothing more.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from formmigrate import ir
from formmigrate.sources.html import adapter

D = "_forms/html-volunteer-intake/"
document = adapter.build_from_file(D + "form.html", form_name="Volunteer Intake")
open(D + "ir.json", "w").write(ir.to_json(document))
```

## What you gain and lose versus a platform export

**Gained: input types are honest.** `type="email"` means email, `required` means
required, `maxlength` is a real constraint. FormAssembly renders nearly
everything as `type="text"` and hides the real type in a CSS class, so raw HTML
is in one respect a *better* signal.

**Lost: the mapping spec, and any logic written in JavaScript.** There is no
config to read. Conditional visibility implemented in script - which is how most
hand-built forms do it - is invisible. The adapter reports every inline script
block it finds and declares `coverage.conditions` as `not_captured`.

Only pass `conditions_are_complete=True` once a human has read the page's
scripts and confirmed there is no hidden show/hide logic:

```python
adapter.build_from_file(path, conditions_are_complete=True)
```

The default is False on purpose. The parser genuinely cannot tell "no
conditional logic" from "conditional logic I can't see", and the safe default is
to admit it.

## The endpoint is the real spec

If the `<form>` names an `action`, the adapter records a finding: **something
receives that POST and it is the actual mapping specification.** Coverage is
`not_captured`, not `none_exist` - a hole, not an absence. Find out what is on
the other end before treating the Field Plan's target column as complete.

Only a form with no `action` at all gets `none_exist`.

## How fields are recovered

**A radio or checkbox group is ONE field.** The shared `name` attribute is the
grouping marker; the individual inputs are its options. A `<label>` wrapping one
radio or tick box names that choice, never the group's question. Per-input parsing would
give you forty yes/no questions instead of eight picklists.

**Labels resolve by rank, not by whichever appears first.** A weaker source never
overwrites a stronger one, whatever order the markup happens to use:

| Rank | Source | |
| --- | --- | --- |
| 100 | `<label for="...">` | authoritative |
| 90 | `aria-label` | authoritative |
| 80 | wrapping `<label>` | authoritative |
| 75 | the text beside a lone tick box ("I agree to ...") | authoritative |
| 70 | bare `<label>` above the field | how a choice GROUP gets its question text |
| 50 | `placeholder` | **weak - confirm against the live form** |
| 30 | nearest heading | **weak** |
| 10 | `name` attribute | **weak** |

Anything below rank 70 is reported in a finding listing the affected fields.
Those question texts must be confirmed before they reach the mappings file - a
label recovered from a placeholder is a guess with a plausible shape.

**A `<select>` option with an empty `value` is the "-- choose --" prompt**, not a
choice. It is dropped and kept as the field's placeholder. Testing the visible
text instead of the value lets the prompt through into the new picklist.

**Skipped automatically**: submit/button/reset/image inputs, and hidden inputs
whose names look like anti-forgery or analytics plumbing (`csrf`, `__VIEWSTATE`,
`utm_`, `recaptcha`, and friends).

**Card fields are flagged, never staged.** Anything matching card number, CVV,
expiry or name-on-card raises a finding. Payment moves to Flow Tool Kit's own
payment step.

## Sanity checks

Count independently from the source and confirm:

```bash
grep -oE '<(input|select|textarea)\b' form.html | wc -l   # upper bound on fields
grep -oE 'name="[^"]+"' form.html | sort -u | wc -l       # distinct field keys
grep -c '<option' form.html                               # options incl. prompts
```

Distinct `name` values is the number to trust - it is the number of fields,
because that is exactly how the adapter groups them. A parsed field count higher
than the distinct-name count means a group was split apart.

Then read the weak-label finding and resolve every field in it.
