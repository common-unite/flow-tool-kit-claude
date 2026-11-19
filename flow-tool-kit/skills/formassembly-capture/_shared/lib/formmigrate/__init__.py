"""External form to Flow Tool Kit migration.

Turns whatever a legacy form platform will give up into one normalized
intermediate representation (IR) that skills and generators consume instead of
raw source files. The IR is the contract; everything else is either a source
adapter feeding it or a consumer reading it.

    sources/           ONE PER PLATFORM. The only code that knows what a
                       particular form builder looks like.
      formassembly/    three exports incl. the Salesforce connector - the
                       reference adapter, and the only common platform whose
                       connector doubles as the migration spec
      claude_design/   .dc.html design files; each question
                       is a declared <dc-import>, nothing is reconstructed
      google_forms/    a saved public Google Form page; reads the form data
                       the page embeds, every section, choice and branch
      html/            any rendered HTML form; structure and fields only
      pdf/             a PDF form, fillable or flat
      formtemplate/    an existing Flow Tool Kit Form Template, from an org
      manual/          a hand-authored capture doc: no export, a page read in
                       chat, or a brief for a form that does not exist yet

    ir.py              THE CONTRACT. Document shape, coverage semantics, branch
                       analysis, and the structural validator every adapter runs.
    conditions.py      the conditional-logic tree all sources normalize onto,
                       plus its constructors, resolver protocol and validator.

    fieldplan.py       propose a Form Submission field per form field, where the
                       question is built and how it converts (by edition)
    fieldmeta.py       render approved proposals as deployable field metadata
    schema.py          the Form Submission inventory: org, describe file,
                       force-app, or the shipped snapshot (marked verify)
    projectconfig.py   this org's entry in flow-tool-kit.json (edition and more)
    validate.py        check an IR against force-app; report gaps and ambiguity
    ladder.py          place calculations and scripts on the escalation ladder
    questions.py       the decisions only the org's people can make
    mappings.py        the mappings file (CSV or JSON) a reviewer edits
    decisions.py       read the reviewer's edits back in, keyed by field id
    review.py          mechanical naming fixes a machine should always get right

Stdlib only, with no third-party HTML library and nothing to install. The package
ships inside the skill and is imported directly from ``scripts/``, so it runs in
any Salesforce project, and in a chat sandbox that has the skill folder.

Usage::

    import sys; sys.path.insert(0, "<skill>/scripts")
    from formmigrate import ir, validate
    from formmigrate.sources.formassembly import adapter

    document = adapter.build_from_files("_forms/formassembly-1234567/",
                                        form_id="1234567")
    open("_forms/formassembly-1234567/ir.json", "w").write(ir.to_json(document))
"""

from __future__ import annotations
