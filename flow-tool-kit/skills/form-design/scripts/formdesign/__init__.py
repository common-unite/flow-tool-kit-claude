"""Draw a Flow Tool Kit form design (plan.json) as a review canvas, and keep the plan and the canvas in step.

Modules:
    planrules   form-type rules, counted times and the normalization that writes them into plan.json
    conditions  show/hide rules: the text the canvas shows beside a governed field, and branch grouping
    checks      the design checks that stop a plan the build would refuse or a reviewer would send back
    sensitive   the sensitive-information check: a question form-migrate marked sensitive is asked about, then decided
    requiredness the required-flag check: each placed question keeps the source's flag, or the person confirmed the change
    nodes       a small element tree, written out as Design canvas markup or as a React page
    boards      the artboards: pages, stages overview, review, confirmations, emails, field audit, brand, source
    letterhead  the email letterhead the email artboard draws
    tokens      Style Editor values to the saved --ftk- tokens the build applies
    publish     canvas.json, the publish batches, image uploads and the self-contained fallback page

Python 3 standard library only. Nothing here names a person, an org or a computer.
"""
