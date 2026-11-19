"""Assemble the three FormAssembly exports into the shared IR.

FormAssembly is the richest source this skill reads: it is the only common
platform that publishes its Salesforce connector, and the connector is not an
obstacle - **it is the specification**, carrying the object graph, execution
order, matching predicates, skip conditions, and field mappings.

That makes it the reference adapter. A new source implements the same
``build(...) -> dict`` shape; the parts it cannot supply it declares in
``coverage`` rather than leaving silently empty.
"""

from __future__ import annotations

from ... import ir


def build(
    alias_export,
    form_model,
    connector_model=None,
    form_id: str = "",
    connector_id: str = "",
    form_name: str = "",
    source_url: str = "",
) -> dict:
    """Combine the parsed FormAssembly inputs into one IR document.

    ``connector_model`` is optional only because a form is occasionally exported
    before its connector is available. When it is absent the connector aspect is
    declared ``not_captured`` - an acknowledged hole - never ``none_exist``,
    because a FormAssembly form that writes to Salesforce definitely has one.
    """
    document = ir.new_document(
        platform="formassembly",
        form_id=form_id,
        connector_id=connector_id,
        form_name=form_name,
        source_url=source_url,
        coverage={
            "structure": "parsed",
            "fields": "parsed",
            "options": "parsed",
            "validation": "parsed",
            "conditions": "parsed",
            "connector": "parsed" if connector_model is not None else "not_captured",
            "images": "parsed",
            "custom_scripts": "parsed",
        },
    )

    document["form"]["section_paths"] = list(alias_export.section_paths)
    document["fields"] = _build_fields(alias_export, form_model)
    document["structure"] = _build_structure(form_model)
    document["conditions"] = _build_conditions(form_model)
    document["dependent_picklists"] = form_model.dependent_picklists()
    # Every htmlSection text block with its tfa_ id, so each one stays on the rebuilt form.
    document["form"]["content_blocks"] = [
        {"id": block["id"], "section": block["section"], "title": "", "text": block["text"]}
        for block in form_model.text_blocks
    ]
    document["images"] = list(form_model.images)
    document["custom_scripts"] = [
        {"index": index, "length": len(body), "body": body}
        for index, body in enumerate(form_model.custom_scripts)
    ]
    if connector_model is not None:
        document["connector"] = _build_connector(connector_model, alias_export)

    document["findings"] = _collect_findings(alias_export, form_model, connector_model)

    # finalize resolves condition references and derives branch analysis against
    # the alias export, which is the only thing that can turn a tfa_ id into a
    # business label.
    return ir.finalize(document, resolver=alias_export)


def _build_fields(alias_export, form_model) -> list[dict]:
    """One entry per form field, with options and whatever the form declares."""
    entries = []
    for alias_id, field in alias_export.fields.items():
        rendered = form_model.inputs.get(alias_id)
        entries.append(
            {
                "id": alias_id,
                "label": field.label,
                "section_path": field.section_path,
                "section_id": rendered.section_id if rendered else None,
                "input_type": rendered.input_type if rendered else None,
                "tag": rendered.tag if rendered else None,
                "required": rendered.required if rendered else None,
                "validation": rendered.validation if rendered else [],
                "default_value": rendered.default_value if rendered else None,
                "present_in_rendered_form": rendered is not None,
                "calculation": rendered.calculation if rendered else None,
                "variable": rendered.variable if rendered else None,
                "options": [
                    {"id": option.alias_id, "label": option.label}
                    for option in field.options
                ],
            }
        )
    return entries


def _build_structure(form_model) -> list[dict]:
    """Section tree, in document order, with layout preserved."""
    return [
        {
            "id": section.element_id,
            "tag": section.tag,
            "layout": section.layout,
            "parent_id": section.parent_id,
            "has_condition": section.condition is not None,
            "repeat": section.repeat,
            "repeat_label": section.repeat_label,
            # A one-question repeat names the question it repeats.
            **({"repeats_field": section.repeats_field} if section.repeats_field else {}),
        }
        for section in form_model.sections.values()
    ]


def _build_conditions(form_model) -> list[dict]:
    """Every conditional rule and its tree.

    References, unresolved references, and the readable rendering are filled in
    by ``ir.finalize``, so every source resolves them the same way.
    """
    return [
        {
            "element_id": rule.element_id,
            "governs": rule.governs,
            "tag": rule.tag,
            "expression": rule.expression,
            "tree": rule.tree,
            "references": [],
            "unresolved_references": [],
        }
        for rule in form_model.conditional_rules()
    ]


def _build_connector(connector_model, alias_export) -> dict:
    """Connector nodes in execution order, plus options and declared fields."""
    nodes = []
    for node in connector_model.ordered_nodes():
        nodes.append(
            {
                "node_id": node.node_id,
                "order_path": node.order_path,
                "action": node.action,
                "sobject": node.sobject,
                "parent_node_id": node.parent_node_id,
                "comment": node.comment,
                "skip_if": node.skip_if,
                "skip_if_tokens": ir.resolve_tokens(node.skip_if, alias_export),
                "lookup": _build_lookup(node.lookup),
                "mappings": [
                    {
                        "target_field_label": mapping.target_field_label,
                        "source_kind": mapping.source_kind,
                        "source_value": mapping.source_value,
                        "source_node_path": mapping.source_node_path,
                        "formula_tokens": ir.resolve_tokens(
                            mapping.source_value, alias_export
                        )
                        if mapping.source_kind == "formula"
                        else [],
                    }
                    for mapping in node.mappings
                ],
            }
        )

    return {
        "nodes": nodes,
        "options": dict(connector_model.options),
        "declared_target_fields": list(connector_model.declared_target_fields),
        "branches": [],
    }


def _build_lookup(lookup) -> dict | None:
    if lookup is None:
        return None
    return {
        "number": lookup.number,
        "on_no_match": lookup.on_no_match,
        "on_one_match": lookup.on_one_match,
        "on_multiple_matches": lookup.on_multiple_matches,
        "predicate": _predicate_to_dict(lookup.predicate),
    }


def _predicate_to_dict(predicate) -> dict | None:
    if predicate is None:
        return None
    if predicate.is_group:
        return {
            "operator": predicate.operator,
            "operands": [_predicate_to_dict(child) for child in predicate.operands],
        }
    return {
        "left_field": predicate.left_field,
        "comparison": predicate.comparison,
        "right_kind": predicate.right_kind,
        "right_value": predicate.right_value,
    }


def _collect_findings(alias_export, form_model, connector_model) -> list[dict]:
    """All findings, tagged by which input produced them."""
    findings = []
    sources = [("aliases", alias_export.findings), ("form", form_model.findings)]
    if connector_model is not None:
        sources.append(("connector", connector_model.findings))
    else:
        findings.append(
            {
                "source": "adapter",
                "message": "No connector export supplied. The object graph, "
                "matching rules and field mappings are UNKNOWN, not absent - "
                "the Field Plan cannot propose targets without it.",
            }
        )
    for source, items in sources:
        findings.extend({"source": source, "message": message} for message in items)
    return findings


def build_from_files(
    directory: str,
    form_id: str = "",
    connector_id: str = "",
    form_name: str = "",
    source_url: str = "",
) -> dict:
    """Parse ``aliases.html``, ``form.html`` and ``connector.html`` from a folder.

    Public-only path: with no ``aliases.html`` (a prospect's public form, no account access), the aliases are built
    from the rendered page itself (``page_aliases``), and the IR's findings say so. The connector is then
    ``not_captured``: unknown, never absent."""
    import os

    from . import aliases as aliases_module
    from . import connector as connector_module
    from . import form as form_module
    from . import page_aliases

    connector_path = os.path.join(directory, "connector.html")
    aliases_path = os.path.join(directory, "aliases.html")
    form_path = os.path.join(directory, "form.html")
    return build(
        aliases_module.parse_file(aliases_path) if os.path.exists(aliases_path) else page_aliases.parse_file(form_path),
        form_module.parse_file(form_path),
        connector_module.parse_file(connector_path)
        if os.path.exists(connector_path)
        else None,
        form_id=form_id,
        connector_id=connector_id,
        form_name=form_name,
        source_url=source_url,
    )
