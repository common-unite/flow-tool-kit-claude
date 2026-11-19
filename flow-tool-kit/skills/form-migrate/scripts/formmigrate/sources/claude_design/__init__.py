"""Design file source adapter (``.dc.html``).

For a form drawn as a ``.dc.html`` design file, the format a Claude design
canvas saves. The best-structured source this skill reads: a question is not
reconstructed from markup, it is declared::

    <dc-import name="Choices" label="What worked well?"
                options="Food|Music|Kids' activities" multi="{{ true }}">

No label-association guessing, no choice-group reconstruction - the two things
that make raw HTML fragile - and option sets arrive intact.

Getting the files is a session step, not a library one: save the form and every
component definition it imports into the project (download them from the canvas,
or read them through whatever design tool the session has), then parse them from
disk. See `references/sources/claude-design.md`.

Usage::

    from formmigrate.sources.claude_design import adapter
    document = adapter.build_from_files(
        "_forms/design-feedback/Post-Event Feedback.dc.html",
        ["_forms/design-feedback/Field.dc.html",
         "_forms/design-feedback/Choices.dc.html",
         "_forms/design-feedback/Scale.dc.html"],
        project_id="example-project")
"""

from __future__ import annotations

from . import adapter, parser  # noqa: F401
