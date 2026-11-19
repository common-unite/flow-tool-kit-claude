"""An existing FlowToolKit Form Template as a migration source.

Used when a template is being cleaned up, redesigned or merged with others.
Unlike every other source, the questions already land on real Salesforce
fields, so the template itself is the mapping spec: each field carries its
current target and the connector is ``parsed``.

``extract.py`` pulls one template from an org through the sf CLI (reusing the
field-audit skill's describe-driven org helpers) into one export file.
``adapter.py`` turns that export into the IR with no org access, so it can be
rerun and tested offline.

Reads the template, its pages and sections, and every section form in all
three sources: Metadata (``Form__mdt`` tree), Record (``Form_Component__c``)
and JSON (inline ``FormConfigJSON__c``). Page rules, page-section rules and
component rules all become condition trees. Each section keeps its Component
Type (Field Set, Repeater, Table, Flow, Lightning Web Component, Display Text),
each mapped component its Submission Field Map, and the template its header
form, banners, header tags and logo.
"""
