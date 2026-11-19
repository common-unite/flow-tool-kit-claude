# Brief: a three-page form with a release and signature

The worked example for a form described in plain words, with no source form and no org connected. All names and text are invented.

**The brief:** "A three-page form: page 1 an information screen; page 2 contact, demographic and organization information; page 3 a release with electronic signature."

**Copy it when** a request describes a short multi-page form that collects a person, optional demographics, an organization and a signed release: registrations, workshop sign-ups, program enrollments.

## Files

| File | What it is | Written by |
|---|---|---|
| `capture.json` | The brief as pages and fields, `platform: "brief"` | ftk-start brief mode |
| `ir.json` | The same document a converted form produces | form-migrate's manual adapter, from `capture.json` |
| `plan.json` | The design as data: pages, sections, controls, widths, copy and targets | form-design |

## What it shows

- **Form type.** Three pages, not an application or grant, counted at about 6 minutes: row 5 of the form-type rules. Base stage indicator, stages off, docked buttons that say Continue, no "Page N of M", Banner Overlay Small.
- **The information page.** Kept because the brief asks for it and it carries real information. Labelled for its purpose ("About the Program", never "Welcome"), button Get Started, visible to respondents only, so staff reviewing a submission land on the questions.
- **Packaged targets first.** Every answer lands on a packaged Form Submission field: the Contact 1 block, the mailing text fields behind one Address component, the demographic fields with their "prefer not to" values, the organization block, and the electronic signature block (signature pad, printed name, date). With no org connected, nothing else could be checked, and these fields exist in every Flow Tool Kit org.
- **Copy.** Every page has a description of at least two sentences, every section a title and subtitle, and the confirmation runs three paragraphs. Facts the brief does not give are bracketed placeholders listed in `questions`.
- **No invented logic.** The brief has no show-and-hide rules, so the capture says `"conditions": "none_exist"` and the plan has none.

## On a paid edition with an org connected

org-catalog may find an existing Contact or Account form. form-design then offers to reuse it, mapped to the same Contact 1 and organization fields with Form Template Mapping, and the packaged conversion flows create the Contact and Account.
