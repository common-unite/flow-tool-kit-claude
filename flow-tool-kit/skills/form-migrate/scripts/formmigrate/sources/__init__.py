"""Source adapters: one per form platform, all emitting the same IR.

A source adapter is the ONLY part of this package that knows what a particular
form builder looks like. Its contract is narrow and total:

    build(...) -> dict conforming to formmigrate.ir

Everything after the IR - the Field Plan, validation, client questions, the
mapping workbook, and the `build-form-component` skill that authors the
rebuild - is source-agnostic and must stay that way. When you find yourself
wanting to teach `fieldplan.py` about a platform, the knowledge belongs in that
platform's adapter instead, expressed in IR terms.

Adapters differ mainly in how much they can see:

    formassembly   three exports, including the Salesforce connector. The
                   richest source and the reference implementation.
    claude_design  .dc.html design files. The best-STRUCTURED
                   source: each question is a declared <dc-import>, so nothing
                   is reconstructed from markup.
    html           any rendered HTML form. Structure and fields only; no
                   platform config exists to read.
    pdf            a PDF form. Tagged flat PDFs (Word exports) give headings,
                   lists and tables; questions come from the written markers
                   ("Label: ____", tick boxes, Y/N). A fillable PDF's own fields
                   are read when pypdf is installed. No connector exists.
    formtemplate   an existing FlowToolKit Form Template, pulled from an org.
                   The only source that already writes to Salesforce, so each
                   field carries its current target and the connector is parsed.
    google_forms   a saved public Google Form page. The page embeds the whole
                   form as data, so every section, choice and "go to section"
                   branch is parsed, not just page 1.
    manual         a hand-authored capture document, for every source no
                   parser reads: other builders, a Word document, screenshots
                   and photos, a page read in chat, or a brief. A human (or
                   Claude reading the page) is the parser; what the source did
                   not show is marked unknown per question.
    table          a spreadsheet of questions saved as CSV, one row per
                   question, assembled through the manual adapter's builder.

What an adapter cannot see it must DECLARE, via the coverage block, rather than
leave as an empty list. See `references/source-adapter-contract.md`.
"""

from __future__ import annotations
