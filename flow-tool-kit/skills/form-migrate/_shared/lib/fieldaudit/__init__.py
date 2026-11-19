"""Field usage audit for Flow Tool Kit (FTK) Form Templates.

Finds every place a field API name is stored in FTK configuration (section
forms in all three sources, rules, mappings, prefill, merge tokens, Form
Template Mapping) and in flows, joins the result with the org's own field
definitions, and writes a data dictionary with a verdict per custom field.

Modules:

* ``names``: folds the three encodings of a field name to one.
* ``walk``: one parser per stored shape (config JSON, rules, mappings).
* ``org``: Salesforce CLI helpers (query, describe). The Form Template
  extractor in form-migrate imports these too.
* ``queries``: what the audit reads, in passes, for the CLI and for a
  Salesforce connector in chat.
* ``sweep`` and ``flows``: references from templates and from flows.
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
