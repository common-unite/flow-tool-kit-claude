#!/usr/bin/env python3
"""Read-only checks for a proposed Flow Tool Kit component composition plan.

Nothing here guesses a grouping. The inputs are form-migrate's IR (version 2), org-catalog's catalog.json and an
explicit plan (references/component-composition.md). It writes nothing to an org. Python 3 standard library only.

    python3 composition.py --ir ir.json --catalog catalog.json --plan composition-plan.json --output <dir>

Exit 0 when the plan passes, 1 when findings remain, 2 when an input is malformed.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

NS = 'FlowToolKit__'
# extend is a new version, the original untouched; update changes the shared component in place, a separate answer
ASK_WORDS = {'reuse': {'reuse'}, 'extend': {'extend'}, 'update': {'update', 'update the shared component', 'update shared'},
             'create': {'new', 'create', 'build new'}}
# The component shapes standard: how a block's questions are stored. Chosen by the person for create and extend, after a
# recommendation with its reason (JSON on the section by default; a record component when reuse is known at design time);
# reuse and update keep the selected component's shape. JSON is fixed to one place.
SHAPES = ('metadata', 'record', 'json')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def bare(name):
    """An object or field name without the package prefix, so Form_Submission__c and FlowToolKit__Form_Submission__c
    compare equal."""
    name = (name or '').replace('*__', NS)
    return name[len(NS):] if name.startswith(NS) else name


def catalog_view(catalog):
    """The catalog as this checker reads it.

    org-catalog's catalog.json (it has catalog_version) is read as it is: the org Id, package version and time taken,
    and per component its name, object, field names and whether it can be edited (a packaged component cannot). The
    older hand-written shape ({org_id, package_version, observed_at, components: [{id, object, fields, ...}]}) is
    accepted unchanged."""
    if 'catalog_version' not in catalog:
        return catalog
    complete = catalog.get('status') == 'ok'
    components = []
    for c in catalog.get('components') or []:
        components.append({
            'id': c.get('name'),
            'object': c.get('object'),
            'fields': [f.get('field') for f in c.get('fields') or [] if f.get('field')],
            'definition_complete': complete and bool(c.get('fields') or c.get('sections')),
            'editable': not c.get('packaged', False),
            'shape': c.get('shape') or c.get('kind'),
            'evidence': f"org-catalog, taken {catalog.get('taken_at')}",
            'used_in': [u.get('template') for u in c.get('used_in') or []],
        })
    return {'org_id': (catalog.get('org') or {}).get('id'), 'package_version': (catalog.get('package') or {}).get('version'),
            'observed_at': catalog.get('taken_at'), 'status': catalog.get('status'), 'components': components}


def dependency_edges(document):
    """Resolve option references to questions and section rules to their descendants."""
    fields = {f['id']: f for f in document['fields']}
    owners = {o['id']: f['id'] for f in fields.values() for o in f.get('options', [])}
    parents = {s['id']: s.get('parent_id') for s in document.get('structure', [])}

    def under(field, section):
        node = field.get('section_id')
        seen = set()
        while node and node not in seen:
            if node == section:
                return True
            seen.add(node)
            node = parents.get(node)
        return False

    edges = []
    for i, rule in enumerate(document.get('conditions', [])):
        refs = [owners.get(ref, ref) for ref in rule.get('references', [])]
        target = rule['element_id']
        targets = [target] if target in fields else [f['id'] for f in fields.values() if under(f, target)]
        edges.append({'id': f'condition:{i}', 'kind': 'condition', 'governs': rule.get('governs'), 'element_id': target,
                      'sources': refs, 'targets': targets, 'unresolved': [x for x in refs if x not in fields]})
    pairs = set()
    for pair in document.get('dependent_picklists', []):
        child, parent = pair['element_id'], (pair.get('controlled_by') or '').lstrip('#')
        if parent:
            pairs.add((parent, child))
        if pair.get('controls'):
            pairs.add((child, pair['controls'].lstrip('#')))
    for parent, child in sorted(pairs):
        edges.append({'id': f'picklist:{parent}:{child}', 'kind': 'dependent_picklist', 'sources': [parent], 'targets': [child],
                      'unresolved': [x for x in (parent, child) if x not in fields]})
    return edges


def validate(document, catalog, plan):
    findings = []

    def add(code, message, severity='error'):
        findings.append({'severity': severity, 'code': code, 'message': message})

    view = catalog_view(catalog)
    if str(document.get('schema_version', '')).split('.')[0] != '2' or plan.get('schema_version') != '1.0':
        add('version', 'Expected migration IR v2 and composition plan 1.0.')
    for key, actual in [('source_fingerprint', fingerprint(document)), ('catalog_fingerprint', fingerprint(catalog))]:
        if plan.get(key) != actual:
            add('snapshot-drift', f'{key} does not match the supplied input.')
    if view.get('status') in ('no org', 'no package'):
        add('catalog-no-org', f"The catalog says {view.get('status')}, so there is nothing to reuse and every decision is pending until a Flow Tool Kit org is read.", 'warning')
    elif view.get('status') == 'partial':
        add('catalog-partial', 'Some catalog reads were refused; a component missing from it may still exist.', 'warning')
    if view.get('status') not in ('no org', 'no package'):
        if not view.get('org_id') or plan.get('org_id') != view.get('org_id'):
            add('org-mismatch', 'Plan and catalog must identify the same org.')
        if not view.get('package_version') or not view.get('observed_at'):
            add('catalog-provenance', 'Catalog needs the package version and the time it was taken.')
    for aspect in ('structure', 'fields', 'options', 'conditions', 'validation'):
        state = document.get('source', {}).get('coverage', {}).get(aspect, 'unknown')
        if state not in ('parsed', 'hand_authored', 'none_exist'):
            add('source-incomplete', f'{aspect}: {state}.')
    fields = {f['id']: f for f in document.get('fields', [])}
    if not fields or len(fields) != len(document.get('fields', [])):
        add('source-fields', 'Source questions must have nonempty, unique IDs.')
    components = {c['id']: c for c in view.get('components', [])}
    if len(components) != len(view.get('components', [])):
        add('catalog-identity', 'Duplicate component identities in catalog.')
    blocks = plan.get('blocks', [])
    contexts = plan.get('record_contexts', {})
    ids = [b.get('id') for b in blocks]
    if not all(ids) or len(ids) != len(set(ids)):
        add('block-identity', 'Block IDs must be nonempty and unique.')
    assignments = defaultdict(list)
    writes = defaultdict(set)
    for block in blocks:
        bid = block.get('id', '?')
        source_ids = block.get('source_ids', [])
        for sid in source_ids:
            assignments[sid].append(bid)
        if not source_ids or not block.get('purpose') or not block.get('boundary_reason'):
            add('boundary-evidence', f'{bid}: explain purpose, source coverage and why this boundary is reusable.')
        if block.get('status') != 'resolved':
            add('unresolved-block', f'{bid}: proposal is not resolved.')
        action = block.get('action')
        if action not in ('reuse', 'extend', 'update', 'create', 'service'):
            add('action', f'{bid}: invalid action {action!r}.')
            continue
        if action == 'service':
            if not block.get('implementation'):
                add('service-contract', f'{bid}: prefill/payment/content needs an implementation decision.')
            continue
        if not block.get('record_scope') or not block.get('object'):
            add('storage-context', f'{bid}: object and record scope are required.')
        context = contexts.get(block.get('record_scope'), {})
        if bare(context.get('object')) != bare(block.get('object')) or context.get('status') != 'resolved' or not context.get('implementation'):
            add('unproven-record-context', f'{bid}: a distinct scope name is not proof of an independent runtime record context.')
        candidates = block.get('candidates', [])
        if not block.get('search_evidence'):
            add('reuse-not-investigated', f'{bid}: record the catalog search before choosing an action.')
        for candidate in candidates:
            if candidate.get('id') not in components or not candidate.get('reason') or candidate.get('fit') not in ('compatible', 'partial', 'incompatible'):
                add('candidate-evidence', f'{bid}: invalid candidate assessment.')
        if any(c.get('fit') in ('compatible', 'partial') for c in candidates):
            asked = block.get('asked') or {}
            answer = str(asked.get('answer') or '').strip().lower()
            if not asked.get('question') or not answer:
                add('reuse-not-asked', f'{bid}: a catalog component matches; ask reuse, extend or new by name and record the answer in asked.')
            elif answer not in ASK_WORDS[action]:
                add('answer-mismatch', f'{bid}: the person answered {answer!r} but the action is {action}.')
        if action == 'create' and any(c.get('fit') == 'compatible' for c in candidates) and not block.get('asked'):
            add('unnecessary-create', f'{bid}: a compatible reusable candidate remains.')
        selected = components.get(block.get('component_id'))
        if action in ('reuse', 'extend', 'update'):
            if not selected:
                add('missing-component', f'{bid}: selected component does not exist in the catalog.')
            else:
                if bare(selected.get('object')) != bare(block.get('object')):
                    add('object-mismatch', f'{bid}: selected component targets a different object.')
                if not selected.get('definition_complete'):
                    add('definition-incomplete', f'{bid}: full hierarchy/behavior inspection is incomplete.')
                if not selected.get('evidence'):
                    add('definition-evidence', f'{bid}: cite the inspected definition snapshot.')
                if not any(c.get('id') == block.get('component_id') for c in candidates):
                    add('selection-unexplained', f'{bid}: selected component has no compatibility assessment.')
                if action == 'reuse' and not any(c.get('id') == block.get('component_id') and c.get('fit') == 'compatible' for c in candidates):
                    add('partial-reuse', f'{bid}: partial or incompatible candidates cannot be declared unchanged reuse.')
        if action == 'extend':
            new_name = block.get('new_name')
            if not new_name or bare(new_name) == bare(block.get('component_id')) or new_name in components:
                add('extend-name', f'{bid}: extend builds a new version under its own name (new_name), never the original; '
                    'changing the original is update, a separate answer.')
            if not block.get('proposed_fields'):
                add('extend-fields', f'{bid}: list the fields the new version adds in proposed_fields.')
        if action == 'update':
            asked = block.get('asked') or {}
            question = str(asked.get('question') or '')
            if str(asked.get('answer') or '').strip().lower() not in ASK_WORDS['update']:
                add('update-not-asked', f'{bid}: updating the shared component in place needs its own question, answered update; '
                    'it is never the default.')
            unnamed = [c for c in block.get('usage', {}).get('consumers', []) if str(c) not in question]
            if unnamed:
                add('update-consumers-unnamed', f'{bid}: the update question must name every template and component it reaches; '
                    f'missing {unnamed}.')
            if not block.get('shared_change_reason') or not block.get('changes'):
                add('shared-update', f'{bid}: explain the shared change and supply its diff.')
            if not selected or selected.get('editable') is not True:
                add('editability', f'{bid}: editability is not established (a packaged component cannot be updated; extend it into a new version).')
            if block.get('usage', {}).get('status') != 'complete':
                add('usage-incomplete', f'{bid}: shared-consumer discovery is incomplete.')
        shape = block.get('shape')
        shape_answer = str((block.get('shape_asked') or {}).get('answer') or '').strip().lower()
        if shape is not None and shape not in SHAPES:
            add('shape', f'{bid}: shape {shape!r} is not one of {", ".join(SHAPES)}.')
        elif action in ('create', 'extend'):
            if not shape:
                add('shape-not-chosen', f'{bid}: no shape. Recommend one with the reason (JSON on the section by default, a record component when reuse is known at design time), ask, and record shape '
                    'and shape_asked; never decide it silently.')
            elif shape_answer != shape:
                add('shape-not-asked', f'{bid}: shape {shape!r} has no matching answer in shape_asked.')
            if shape == 'json' and action == 'extend':
                add('shape-json', f'{bid}: an extended component is a new shared version, a metadata or record component; '
                    'JSON is fixed to one place.')
        elif shape and selected and selected.get('shape') and shape != selected.get('shape'):
            add('shape-change', f"{bid}: {action} keeps {selected['id']}'s shape ({selected['shape']}); changing a component's "
                'shape is its own question.')
        mappings = block.get('mappings', [])
        mapped = [m.get('source_id') for m in mappings]
        if Counter(mapped) != Counter(source_ids):
            add('mapping-coverage', f'{bid}: map every assigned question exactly once.')
        proposed_fields = {bare(f) for f in block.get('proposed_fields', [])}
        available = {bare(f) for f in selected.get('fields', [])} if selected else set(proposed_fields)
        if action in ('extend', 'update'):
            available |= proposed_fields
        for mapping in mappings:
            target = bare(mapping.get('target_field'))
            if not target or target not in available:
                add('field-incompatible', f"{bid}: target {mapping.get('target_field')!r} is absent from selected/proposed fields.")
            else:
                writes[(block.get('record_scope'), bare(block.get('object')), target)].add(mapping.get('source_id'))
        if selected and action == 'reuse':
            extras = {bare(f) for f in selected.get('fields', [])} - {bare(m.get('target_field')) for m in mappings}
            dispositions = {bare(k): v for k, v in block.get('extra_fields', {}).items()}
            if any(not dispositions.get(field) for field in extras):
                add('extra-fields', f'{bid}: account for existing component fields not requested by the source.')
        for difference in block.get('differences', []):
            if difference.get('placement') not in ('template', 'binding', 'shared_component') or not difference.get('evidence'):
                add('difference-placement', f'{bid}: explain where each form-specific difference belongs and the supported mechanism.')
            if difference.get('placement') == 'shared_component' and action in ('reuse', 'extend'):
                add('hidden-update', f'{bid}: {action} cannot alter the shared component; that is update, a separate answer.')
    for sid in fields:
        if len(assignments[sid]) != 1:
            add('question-coverage', f'{sid}: assigned {len(assignments[sid])} times; expected exactly one owner.')
    for sid in assignments.keys() - fields.keys():
        add('unknown-question', f'{sid}: not in source IR.')
    for target, source_ids in writes.items():
        if len(source_ids) > 1:
            add('storage-collision', f'{target}: distinct questions would overwrite one another: {sorted(source_ids)}.')
    for group in document.get('repeat_groups', []):
        touched = sorted({b for sid in group.get('source_ids', []) for b in assignments[sid]})
        if not group.get('source_ids') or any(sid not in fields for sid in group.get('source_ids', [])):
            add('repeat-scope', f"{group.get('id')}: missing or unknown repeated questions.")
        if len(touched) > 1:
            add('split-repeat', f"{group.get('id')}: repeated questions span {touched}; keep them in one repeated record block.")
        for block in blocks:
            if block.get('id') in touched and contexts.get(block.get('record_scope'), {}).get('kind') != 'repeated_record':
                add('repeat-context', f"{group.get('id')}: requires a declared repeated-record context.")
    reviews = plan.get('dependencies', [])
    counts = Counter(r.get('id') for r in reviews)
    reviewed = {r.get('id'): r for r in reviews}
    edges = dependency_edges(document)
    for edge in edges:
        review = reviewed.get(edge['id'], {})
        touched = sorted({b for sid in edge['sources'] + edge['targets'] for b in assignments[sid]})
        if edge['unresolved']:
            add('unresolved-reference', f"{edge['id']}: {edge['unresolved']}.")
        if not edge['targets']:
            add('empty-condition-scope', f"{edge['id']}: no question descendants; explicitly review non-question content at {edge.get('element_id')}.")
        if counts[edge['id']] != 1 or review.get('status') != 'resolved' or not review.get('implementation') or review.get('blocks') != touched:
            add('dependency-unresolved', f"{edge['id']}: review implementation and affected blocks {touched}; preserve original rule scope.")
    for key in reviewed.keys() - {e['id'] for e in edges}:
        add('unknown-dependency', f'{key}: not derived from source IR.')
    for issue in plan.get('open_issues', []):
        add('open-decision', str(issue))
    return {'ready_for_authoring': not any(f['severity'] == 'error' for f in findings),
            'questions': len(fields), 'blocks': len(blocks), 'dependencies': len(edges), 'findings': findings,
            'limit': 'Checks declared evidence and structural consistency; does not prove semantic equivalence, runtime behavior, or deployment readiness.'}


def render(document, plan, result, catalog=None):
    labels = {f['id']: f.get('label', '') for f in document['fields']}
    used = {c['id']: c.get('used_in') or [] for c in catalog_view(catalog or {}).get('components', [])}
    lines = ['# Component composition plan', '', 'Ready for authoring: ' + str(result['ready_for_authoring']), '',
             '| Block | Action | Purpose and boundary | Questions |', '| --- | --- | --- | --- |']
    for block in plan['blocks']:
        cells = [block['id'], block['action'], block['purpose'] + ': ' + block['boundary_reason'], str(len(block['source_ids']))]
        lines.append('| ' + ' | '.join(c.replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |')
    for block in plan['blocks']:
        lines += ['', '## ' + block['id'], '', block['purpose'], '', block['boundary_reason'], '',
                  'Selected component: ' + str(block.get('component_id') or 'None selected'), '']
        if block.get('asked'):
            lines += [f"Asked: {block['asked'].get('question')} Answer: {block['asked'].get('answer')}", '']
        lines += [f"- {sid}: {labels.get(sid, '?')}" for sid in block['source_ids']]
        lines += ['', 'Candidates:']
        for c in block.get('candidates', []):
            where = used.get(c['id'])
            lines.append(f"- {c['id']} ({c['fit']}): {c['reason']}" + (f" Used in: {', '.join(where)}." if where else ''))
    lines += ['', '## Findings', ''] + [f"- {f['severity']} {f['code']}: {f['message']}" for f in result['findings']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('ir', 'catalog', 'plan', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        doc, catalog, plan = [json.loads(p.read_text(encoding='utf-8')) for p in (args.ir, args.catalog, args.plan)]
        result = validate(doc, catalog, plan)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'composition-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        (args.output / 'composition-plan.md').write_text(render(doc, plan, result, catalog), encoding='utf-8')
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        parser.exit(2, f'Invalid composition input: {type(error).__name__}: {error}\n')
    print(json.dumps({'ready_for_authoring': result['ready_for_authoring'], 'questions': result['questions'], 'blocks': result['blocks'], 'findings': len(result['findings'])}))
    return 0 if result['ready_for_authoring'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
