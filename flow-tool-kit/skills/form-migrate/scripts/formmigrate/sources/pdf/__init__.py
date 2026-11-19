"""PDF forms: fillable (AcroForm) and flat (a printed or Word-exported form).

What a PDF gives up depends on how it was made:

    tagged flat PDF   Word and most modern authoring tools export a structure
                      tree: headings, paragraphs, lists and real tables with
                      header cells. Questions are recognised from their written
                      markers ("Label: ____", underscore answer lines, "Y/N",
                      drawn tick boxes) and the tree supplies reading order,
                      lists and tables. This is the common case and the one the
                      parser is built around.
    AcroForm PDF      has real widgets with names and types. Detected and
                      reported; widget extraction needs a PDF library that is
                      not bundled, so it is declared ``not_captured`` rather
                      than guessed from text.
    untagged flat PDF has no tree; only positioned text. Reported as a finding
                      and parsed from layout lines alone, with lower confidence.

What a PDF never carries: a Salesforce connector, validation beyond what the
wording states, and single- versus multiple-choice for drawn tick boxes (every
box looks the same). Those are declared in coverage and raised as findings so a
person decides them.

Requires poppler (``pdfinfo``, ``pdftotext``) on the PATH.
"""
