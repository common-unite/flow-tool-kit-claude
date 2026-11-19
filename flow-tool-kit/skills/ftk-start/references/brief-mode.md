# Brief mode: a form from a description

Use it when the request describes a form that does not exist yet ("a three-page form: an information page; contact, demographic and organization details; a release with an electronic signature"). It turns the brief into the same `ir.json` a conversion writes, through form-migrate's manual adapter, so form-design and the build skills run unchanged.

## 1. Read the brief, then ask up to five questions at once

First write down what the brief already says: purpose, pages, blocks, who signs. Then ask only what is missing, in one message, each with a default and a recommendation:

1. **Who fills it in**: guest, portal user, staff (skip if the project config has the audiences and the brief fits them).
2. **Platform**, only for a grant or application: Outbound Funds, Nonprofit Cloud, or neither. Check the org first (org-catalog's `platforms`) and confirm what was found instead of asking.
3. **One sitting or several**: decides Save Progress and stages for long forms.
4. **Who signs**: the respondent, a parent or guardian, an authorized officer.
5. **Which records it creates**: Contact, Account, Funding Request, Individual Application, your own object. Default from the platform and the blocks.

## 2. Pick the form type and the blocks

The form type (survey, simple single page, two pages, three or more short pages, long application in stages) sets the header, buttons, indicator and first page, as `_shared/standards/form-type-rules.md` says, and the defaults in `_shared/standards/form-house-rules.md` apply. A three-page form is long only when it is an application or grant, or its counted time reaches about 10 minutes; a generic three-page form is row 5 (base indicator, no stages).

Build each page from the pattern blocks: contact, address, organization, demographics, consent, signature, funding request, uploads. The blocks, their controls and the packaged fields to try first are in `_shared/examples/brief-patterns/README.md`.

## 3. Read the chosen objects from the org

Describe Form Submission and every target object live from the org (Salesforce connector in chat, `sf sobject describe` in Claude Code), never from local files: in chat there are none. For each field take, in order:

1. a field on the target object, when the edition is paid (it lands through Form Template Mapping);
2. a packaged Form Submission field (the Contact 1, Contact 2, address and organization blocks first);
3. a packaged generic slot on Form Submission.

Only when none fits, propose a new field as a question. With no org connected, mark every target `verify`; the design is still complete.

**Outbound Funds:** a Funding Program links to the Form Template, and the conversion creates the Funding Request with the converted Contact. **Nonprofit Cloud Individual Application:** there is no packaged conversion flow, which is the normal case: plan a custom conversion flow and a controller update (or a custom controller) with **new-mapping-flow**, and note that the application's account must be a person account.

## 4. Write capture.json and build ir.json

Write `_forms/<slug>/capture.json` with `"platform": "brief"`, then build the IR with form-migrate's manual adapter (form-migrate's Google Forms and manual source reference). Declare `"coverage": {"conditions": "none_exist"}` when the brief has no show-and-hide rules, and write a `note` on any field that needs a special control (an address block, a signature pad).

The worked example is `_shared/examples/form-3-page-release/`: the brief, its `capture.json`, the `ir.json` the adapter builds from it, and the `plan.json` form-design writes. Copy its shape.

## 5. Confirm, then hand to form-design

Show the pages, blocks, form type and targets in a few lines and ask to confirm or correct. Then run form-design with the `ir.json`, the catalog and the project config.
