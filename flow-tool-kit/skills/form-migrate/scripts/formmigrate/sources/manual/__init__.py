"""Hand-authored source adapter, for platforms with no export at all.

Any form no parser reads lands here: Microsoft Forms, Jotform, Typeform and
every other builder, a Word document listed by docx_text.py, screenshots, a
paper form photographed on a phone, a PDF read in chat with no text tools, a
Google Form whose saved page could not be parsed, a spreadsheet of questions
(through the table adapter), and a brief that describes a form that does not
exist yet (brief mode). A person, or Claude reading the page,
transcribes every page into a capture document.

The point of routing those through an adapter rather than leaving them as a
markdown table is that they then produce the SAME ``ir.json`` as a parsed
FormAssembly form. `build-form-component` gets exactly one input contract,
`validate.py` can check the capture against force-app, and the mapping workbook
works identically - none of which is true for prose.

What changes is honesty about provenance: every aspect is declared
``hand_authored`` rather than ``parsed``, so a reader always knows a person, not
a parser, is the source of the claim.

Usage::

    from formmigrate.sources.manual import adapter
    document = adapter.build_from_file("_forms/manual-volunteer-survey/capture.json")
"""

from __future__ import annotations

from . import adapter  # noqa: F401
