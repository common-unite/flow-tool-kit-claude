"""Field usage audit for Flow Tool Kit (FTK).

Before an admin deletes, relabels or changes picklist values on a Form
Submission landing field: every place FTK stores the field's name (Form
Templates, page sections, Form Components in all three sources, rules,
URL parameters, prefill values and prefill templates, merge tokens, the email
templates a template names, Form Template Mapping) and every FTK flow that uses it
(conversion and prefill flows, the screen flows Flow Sections show, flows
with FTK actions or screen components, and their subflows), joined with the org's own field definitions into a data
dictionary with a verdict per custom field. General metadata (Apex, reports,
page layouts, other flows) is left to Setup's Where is this used?.

Modules:

* ``names``: folds the three encodings of a field name to one.
* ``walk``: one parser per stored shape (config JSON, rules, mappings).
* ``org``: Salesforce CLI helpers (query, describe). The Form Template
  extractor in form-migrate imports these too.
* ``queries``: what the audit reads, in passes, for the CLI and for a
  Salesforce connector in chat.
* ``sweep`` and ``flows``: references from templates and from FTK flows.
* ``dictionary`` and ``report``: the data dictionary, verdicts and files.

Python 3 standard library only.
"""

NAMESPACE = "FlowToolKit__"
STAR = "*__"
SUBMISSION_OBJECT = NAMESPACE + "Form_Submission__c"
TEMPLATE_OBJECT = NAMESPACE + "Form_Template__c"
PAGE_OBJECT = NAMESPACE + "Form_Template_Page__c"
SECTION_OBJECT = NAMESPACE + "Form_Template_Page_Section__c"
COMPONENT_OBJECT = NAMESPACE + "Form_Component__c"
