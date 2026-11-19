# Plan component boundaries before authoring

Use this for a whole form, a migration, or any change that moves a component boundary. A small edit inside an established component keeps its boundary; note that in one line. This planning step decides design; it never asks for permission to run anything.

## Decision process

1. **Read the source and its coverage.** form-migrate's `ir.json` (or the plan's pages). Inventory questions, content, rules, repeated groups, prefill, calculations and payment. Source pages are presentation, not component boundaries. Use stable source ids, never label text, as identity.
2. **Read the org catalog first**, including the org's own components. Compare by purpose and data role, object, actual fields, cardinality, options, requiredness, rules, storage path and dependencies. A name only shortlists a candidate; read its full definition before calling it a fit. Then put each match to the person by name: reuse, extend (a new version; the original and its users unchanged) or new.
3. **Propose cohesive blocks** around information that shares a record and a lifecycle. Keep a conditional follow-up with the question it qualifies, and keep the fields of a repeated record together. Separate roles that are reusable on their own: primary contact, mailing address, demographics, consent. A one-field consent block can be useful; a component per arbitrary question is not. No field count or similarity score decides a boundary.
4. **Separate the form's composition from the shared component.** Page order, introductions, headers, disclosure and confirmation belong to the template. A different label, required flag, option subset or hidden field is not automatically something a page section can override; check that the package supports the override before relying on it.
5. **Choose reuse, extend or create, then the shape.** Prefer an unchanged compatible component. Extend when this form needs a little more than a component has: a new version under its own name, the original and everything using it unchanged. Updating the shared component in place is a separate action, never a default: only when the change belongs to everything that uses it, you know everything that uses it, and the person said yes to a question listing all of it. Create for a real gap, or for behavior that must differ here and no supported override expresses. Consider composing smaller existing blocks before building a large replacement. Names describe purpose, never the source form, campaign or page number. For every create and extend, recommend a shape with its reason and ask (`_shared/standards/component-shapes.md`): JSON on the section by default; one record component, built right away and referenced by every place, when reuse is known at design time (the plan places the block in more than one section, Repeater or form, even within one form); metadata only when the person asks, or later through convert-to-metadata once the work is final. An extend keeps the original's shape. Reuse and update keep the selected component's shape.
6. **Check storage, not just looks.** Two address blocks that write the same fields on the same submission overwrite each other. Distinct records, roles or answer slots need a real runtime binding (a second Form Submission lookup, a repeater row); a renamed scope in JSON is not one. Check generic-slot collisions across the whole template, not only inside one block.
7. **Account for every source item.** Respondent questions belong to blocks; hidden prefill ids belong to the prefill flow; existing-record facts and computed totals can belong to template content; card numbers and gateway tokens belong to the payment integration. Never drop one silently or turn every hidden field into a staging field. Track images, instructions, consent text and confirmation separately: question coverage alone is not form coverage.
8. **Review rules at their original scope.** A section rule is not the same as a rule on each child field. Option ids resolve to the question that owns them. Record cross-block reads, dependent picklists, repeated records, external calculations and copy-address behavior. When the mechanism is unknown, keep it as an open decision; never invent support.

You propose boundaries and explain the alternatives. The checker below verifies structure and declared evidence. It does not prove the design means the same as the source, that the evidence is true, or that the form works; `scripts/component.py check` and the Preview Form walk still follow.

## Files

Write them into the form's folder (`_forms/<slug>/`), never into the skill:

- `ir.json`: form-migrate's IR, version 2. Fields keep `section_id` for scope analysis. Optional `repeat_groups`: `[{id, source_ids}]`. No repeat metadata does not prove the source has no repeats.
- `catalog.json`: org-catalog's file, read as it is. `scripts/composition.py` takes from it the org Id, package version and time it was taken, and per component its name, object, fields, and whether it can be edited (packaged components cannot). A catalog marked partial or `no org` makes every reuse finding a pending one.
- `composition-plan.json`: your decisions, in the contract below.
- `composition-plan.md` and `composition-validation.json`: written by the checker for review.

```sh
python3 scripts/composition.py --ir _forms/<slug>/ir.json --catalog <catalog.json> \
  --plan _forms/<slug>/composition-plan.json --output _forms/<slug>
```

Exit 0: the plan passes these checks. 1: findings remain. 2: an input is malformed. An unresolved plan is still a useful review file; it is just not ready to author.

## Plan contract, version 1.0

| Field | Meaning |
| --- | --- |
| `schema_version` | `1.0` |
| `org_id` | The catalog's org Id |
| `source_fingerprint`, `catalog_fingerprint` | `composition.fingerprint()` of the exact documents supplied, so a changed source or catalog is caught |
| `record_contexts` | Map of scope id to `{object, kind, status, implementation}`; kind is `submission`, `related_record` or `repeated_record` |
| `blocks` | The proposed components and service responsibilities |
| `dependencies` | One review for each edge `composition.dependency_edges(ir)` derives |
| `open_issues` | Unresolved decisions; never cleared just to pass |

Each block has `id`, `purpose`, `boundary_reason`, `source_ids`, `status` (`resolved` or `unresolved`) and `action`: `reuse`; `extend` (a new version of `component_id` under `new_name`, plus `proposed_fields`; the original is untouched); `update` (update the shared component in place, a separate answer, never the default); `create`; or `service`. Each question has exactly one owning block.

Component blocks also have:

- `object`, `record_scope`: the real record the block writes;
- `component_id`: the catalog component's name, for reuse, extend and update;
- `new_name`: for extend, the new version's name (a purpose name not already in the catalog);
- `search_evidence`: what you searched in the catalog and what you found;
- `candidates`: `{id, fit, reason}`, fit `compatible`, `partial` or `incompatible` (partial is never treated as compatible);
- `asked`: `{question, answer}`, the reuse question put to the person and their answer, whenever there is a candidate;
- `shape`: `metadata`, `record` or `json`, and `shape_asked`: `{recommended, why, question, answer}`, required for create and extend (the answer equals `shape`). JSON is never an extend. For reuse and update, `shape`, when given, must equal the selected component's shape in the catalog;
- `mappings`: `{source_id, target_field}` for every question the block owns;
- `proposed_fields`: fields a create, extend or update would add (not permission to create them; check them against the field plan and the org);
- `extra_fields`: the selected component's fields the source does not ask, each with what happens to it. Never add required questions silently;
- `differences`: `{placement, evidence}`, placement `template`, `binding` or `shared_component`. Unchanged reuse cannot carry a shared change;
- for update: `shared_change_reason`, `changes` (the diff to review), `usage: {status, consumers, evidence}` (every template and component that uses it), and an `asked` question that names every consumer and an answer of `update`.

Service blocks carry `implementation` instead of a component: a prefill, content, calculation or payment responsibility, never a hidden stand-in for ordinary questions.

Each dependency review has `id`, `status`, the sorted `blocks` its questions touch, and `implementation`. A rule that governs only content gets an explicit scope finding: add the content and resolve the behavior rather than calling it nonexistent.

## Review output

Lead with the proposed boundaries, the reusable candidates (by name, with where they are used), near matches you rejected and why, and open decisions. Explain why each split earns reuse and which neighboring questions stay together. Give a coverage count and list every shared update with the forms it reaches. Never describe a proposed component as already built. When a catalog holds only field lists, say compatibility is pending a full read of the definition.

For a pattern that repeats across several forms, change the shared component deliberately rather than collecting near-identical copies. After the build, reconcile the template against the plan, including every rule path and every source-to-field mapping.
