# Matching a section against the catalog

How `catalog.py match` decides that a section of a new design looks like something the org already has, and what it hands form-design. The code is `scripts/ocmatch.py`; its tests are in `tests/`.

## The measure

For two sections, take the fields both have and divide by the size of the larger section. Count it twice:

- **with labels**: a field counts only when object, field and label all agree;
- **by field**: labels ignored, so a field the other section relabelled still counts.

A pair is a match at **80%** on either count (`--threshold` changes it). Both numbers are reported, so the person sees why.

| Design | Existing | By field | With labels | Match? |
|---|---|---|---|---|
| First name, Last name, Email, Phone | the same four, Phone labelled Business Phone | 100% | 75% | Yes |
| Street, City, State, ZIP, Neighborhood (new field) | Street, City, State, ZIP | 80% | 0% (all relabelled) | Yes, extend |
| Three emergency contact fields | four, one of them extra | 75% | 75% | No |

Rules that keep it honest:

- **Fields are compared by object and field**, ignoring the package prefix and its `*__` placeholder, so `Form_Submission__c.Email__c` in a plan equals `FlowToolKit__Form_Submission__c.FlowToolKit__Email__c` in the org. The one exception is a twin pair (your Submitted_By__c beside the packaged FlowToolKit__Submitted_By__c): those stay two different fields.
- **A generic answer slot** on Form Submission (Text Question 1, Yes No Question 3 and the like) holds a different question on every form, so its label stays part of its identity even when labels are ignored.
- **A new field** (a design field with no Salesforce field yet) counts toward the larger section and never matches.
- **A hidden record Id field** is plumbing and is left out of both sides.
- **Layout and styling are never scored.** A design is never changed to force a match.

## What a component is compared on

- **Its own fields plus the components placed inside it**, up to three levels, so a Volunteer Profile that places Mailing Address is compared on both.
- **Its Form Template Mapping**, when it has one: the Form Submission fields the map writes, each with the label of the field that feeds it. This is how a free-edition design (questions on Form Submission fields) finds a Contact form mapped to those same fields. `compared_on` says which view matched.

## What it hands form-design

`match.json`, one entry per design section:

| Key | What |
|---|---|
| `candidates` | Up to three components, best first (one that covers every design field before one that would need extending; then the higher score). Each has `component`, `label`, `kind`, `packaged`, `object`, `compared_on`, `by_field`, `exact`, `fit`, `fields`, `design_adds`, `existing_only`, `relabelled`, `lookup_field`, `templates`, `inside_components`, `where_used` |
| `fit` | `covers`: the component has every field the section needs (reuse fits). `extend`: the section adds fields (`design_adds`), so reuse would drop them and extend would put them in a new version of the component |
| `similar_sections` | Repeated template sections (built in place, not as components) that match this section |
| `question` | The sentence to ask, naming the component, its fields, its shape and where it is used, then the shape question. Empty when nothing matches and nothing repeats; `catalog.md`'s Questions then asks the shape question alone |
| `shape` | `{recommended, why, question, answer}`: the shape (metadata, record or JSON) recommended for this section if it is extended or built new, the reason, and the question. `answer` is always empty: the person chooses |
| `also_in_design` | The titles of the other sections in the same design that ask these questions (the same fields at the threshold, or the same plan `component` key): reuse known at design time |
| `decision` | Always empty. The person decides |

## Asking

Ask every question at once, in one message, numbered, each with a recommendation for reuse, extend or new and for the shape. Record each answer in the design plan (the shape in `shape` and `shape_asked`); never default to reuse because the score is high. There is no default: a question with no answer stays unanswered, and form-design and build-form-component stop on that section until the person chooses.

- **Reuse**: the section shows the existing component.
- **Extend**: a new version of the named component with `design_adds` added, used by this section. The original is never changed, so everything in `where_used` keeps working as before; the question names those places so the person sees what stays as it is.
- **New**: build the section on its own.

## Recommending a shape

Every section also gets a shape recommendation, from the component shapes standard (`_shared/standards/component-shapes.md`):

| Section | Recommended | Why |
|---|---|---|
| Matches a component it can reuse as is | As for a new section (the rows below) | Reuse keeps the component's own shape, and the question says which; the recommendation is for building new instead |
| Matches a component it would extend | The original's shape | A new version stays in the original's shape: a metadata component's new version stays version controlled, and one deploy still reaches every form that uses it |
| New, and the same design asks the same questions elsewhere (another section or a Repeater with the same fields, or a section the plan points at the same `component` key) | Record | Reuse is known at design time: one record component, built now and referenced by every place, keeps them in step (`also_in_design` lists the other places) |
| New, and the same questions are already built in place on other templates | Record | The org already repeats them, so one record component built now can be referenced by each |
| New, and nothing else asks it | JSON on the section | The default: simplest to build and change, and no shared component can conflict with it. Reuse found later is consolidated then |

Metadata is never recommended for a new section: it comes later through convert-to-metadata once the work is final, or when the person asks for it. The question always offers the other two shapes, and the answer is the person's. Changing an existing component's shape is a separate question.

When a section has no component match but `similar_sections` shows the same design built in place on other templates, ask whether to build it new here or make one shared record component that all of them use. The recommendation is the record component, because the reuse is already known; building it in place as JSON here is still the person's call, and the existing copies can be consolidated later.
