# The plan route (the review pass)

Optional, like the rest of this skill. Use it instead of `consolidate.py` when the templates are built and rebuilt by build-template from `plan.json` files in the project: the change goes into the plans, and the next rebuild makes the shared component and points the sections at it, so a rebuild never puts the old JSON back.

A `form-only` section belongs to its own form, with its own words, as JSON on the section or a one-off component, in the shape the person chose. Sharing a component across templates is earned: once an organization's templates are built, this pass looks for the sections that really repeat and proposes which to share. It changes nothing on its own.

## What it reads

It never reads the org or measures sections itself. org-catalog does both, with one measure (the fields two sections share over the larger set, counted with and without labels, 80% on either):

1. Run **org-catalog** again after the builds, so its catalog knows them. Its `repeated_sections` groups local sections that match across templates.
2. For each plan, run org-catalog's `catalog.py match <catalog.json> <plan.json> --out <match.json>`: the existing components each section matches, with `fit` covers (the component already has every field) or extend.

```bash
python3 scripts/reviewpass.py review --catalog ftk-catalog/<org Id>/catalog.json \
  --plan _forms/application/plan.json=_forms/application/match.json --plan _forms/sign-up/plan.json --out review
```

Only `form-only` sections are proposed; a section that already reuses or shares a component is left alone. The catalog must be under a day old.

## What it proposes

| Proposal | When |
|---|---|
| **switch** | An existing component already has every field the section needs. Existing components come first |
| **promote** | The same design is on two or more templates (`--promote-at`, default 2): make one shared record component every one of them uses, named for its purpose (`Shirt_Size`, never a name the org already has) |
| **keep** | It repeats on fewer templates than `--promote-at` |

`review/review.md` is the report: each proposal with its sections, the templates outside this review that have the same design, and for a switch, the component's labels that differ from the section's (switching shows the component's). For a promote it names, per member, where its questions differ from the section the shared component is built from: a question one has and another lacks, a label, required, or options.

## Marking it up

`review/review-decisions.csv` has one row per proposal and an empty `decision` column. The person writes **promote**, **switch** or **keep** in it, or leaves it empty, in any spreadsheet or text editor; any other word is refused. Then:

```bash
python3 scripts/reviewpass.py apply review/review-decisions.csv --plan _forms/application/plan.json --plan _forms/sign-up/plan.json
```

It changes only the plans of rows marked promote or switch:

- **promote**: a `shared-record` component (shape `record`) built from the first member's section design, with its Form Template Mapping; every member that asks exactly the same questions points at it. A member that differs stays local and is named in the output, so a form's questions never change silently. To bring it in, settle the difference in its plan first (or use `consolidate.py`, which asks per difference). With fewer than two templates left, nothing is applied.
- **switch**: a `reuse` component naming the existing one; every member section points at it.

Rebuild each changed plan with build-template. A promoted component is created before its first template is rebuilt, and rebuilding the others reuses it. A form's design is never changed to force a match. When the person wants the shared component as metadata instead (one deployed update reaching every form), record it as `shared-new` with shape `metadata` and hand it to build-form-component, or convert it later with convert-to-metadata.
