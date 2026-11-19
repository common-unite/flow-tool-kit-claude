"""Google Forms source adapter: a saved public form page.

A public Google Form page carries the whole form as data in a script variable,
``FB_PUBLIC_LOAD_DATA_``: every section, question, choice, required flag and
"go to section based on answer" branch, not just the first page a browser or a
text fetch shows. This adapter reads that variable from the saved page.

The variable is not a documented format. The parser reads only the positions it
is sure of, reports anything else as a finding, and never guesses a question
type: an unknown type becomes text with a finding. Check the result against the
live form (the sanity checks in ``references/sources/google-forms.md``).

What a Google Form never carries: a Salesforce connector (``connector`` is
``none_exist``), custom scripts, and response validation details beyond the
required flag.

Usage::

    from formmigrate.sources.google_forms import adapter
    document = adapter.build_from_file("_forms/google-volunteer/form.html")
"""

from __future__ import annotations

from . import adapter, parser  # noqa: F401
