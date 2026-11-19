"""Generic rendered-HTML source adapter.

For a form that is just HTML - a hand-built page, a Wufoo or Typeform export, a
WordPress form, a design Claude produced as an artifact, a legacy Visualforce
page saved to disk. There is no platform config to read, so this adapter sees
exactly what a browser sees and nothing more.

That is a real limitation and the adapter is loud about it. Compared with
FormAssembly you lose: the Salesforce mapping spec entirely, and any conditional
logic implemented in JavaScript rather than markup. What you gain is that HTML
input types are HONEST - ``type="email"`` means email - whereas FormAssembly
renders nearly everything as ``type="text"`` and hides the real type in a CSS
class.

Usage::

    from formmigrate.sources.html import adapter
    document = adapter.build_from_file("_forms/html-intake/form.html",
                                       form_name="Volunteer Intake")
"""

from __future__ import annotations

from . import adapter, parser  # noqa: F401
