"""FormAssembly source adapter.

Three exports, none optional, each carrying something the others do not:

    aliases.html    the resolver - section paths, field ids, and every option id
                    with its label. Nothing else can resolve an option id, and
                    both connector formulas and form conditions reference option
                    ids directly.
    form.html       the rendered form - section tree, input types, validation,
                    dependent picklists, conditional logic, images, and any
                    custom injected JavaScript.
    connector.html  the Salesforce connector - object graph, execution order,
                    matching predicates, skip conditions, field mappings, and
                    connector-level options. This is the migration spec.

Usage::

    from formmigrate.sources.formassembly import adapter
    document = adapter.build_from_files("_forms/formassembly-1234567/",
                                        form_id="1234567", connector_id="7654321")
"""

from __future__ import annotations

from . import adapter, aliases, conditions, connector, form  # noqa: F401
