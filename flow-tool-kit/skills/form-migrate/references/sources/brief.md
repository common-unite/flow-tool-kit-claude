# Source: a brief

A brief describes a form that does not exist yet: "a three-page form: an information page; contact, demographic and organization details; a release with an electronic signature." Brief mode turns it into the same `ir.json` a conversion writes, so form-design and the build skills run unchanged.

**ftk-start runs brief mode** (its brief-mode reference): it reads the brief, asks the few things only the person can answer, picks the form type and the blocks, and reads the target objects from the org. This page is the input contract it writes to: a `capture.json` for the manual adapter.

## The capture

Write `_forms/brief-<slug>/capture.json`:

```json
{
  "platform": "brief",
  "form_name": "Riverside Arts Fund Grant Application",
  "captured_by": "brief",
  "coverage": {"conditions": "hand_authored", "images": "none_exist"},
  "pages": [
    {"name": "About the Program", "intro": "<p>What the fund supports, who can apply and the deadline.</p>", "fields": []},
    {"name": "Applicant", "fields": [
      {"label": "First Name", "type": "text", "required": true},
      {"label": "Last Name", "type": "text", "required": true},
      {"label": "Email", "type": "email", "required": true},
      {"label": "Organization Name", "type": "text"},
      {"label": "Age Range", "type": "radio",
       "options": ["Under 18", "18 to 64", "65 or older", "Prefer not to answer"]},
      {"label": "Requested Amount", "type": "currency", "help": "Up to 5,000"}
    ]},
    {"name": "Parent or Guardian", "show_when": "Age Range::Under 18", "fields": [
      {"label": "Guardian Name", "type": "text", "required": true}
    ]},
    {"name": "Program Sites", "repeat": true, "repeat_label": "Add another site", "fields": [
      {"label": "Site Name", "type": "text"}
    ]},
    {"name": "Release and Signature", "intro": "<p>The release text, in full.</p>", "fields": [
      {"label": "I agree to the release above", "type": "boolean", "required": true},
      {"label": "Signature", "type": "textarea", "required": true,
       "note": "Electronic signature: a rich text field drawn with the signature pad."},
      {"label": "Date", "type": "date", "required": true}
    ]}
  ]
}
```

| Key | Use |
|---|---|
| `platform: "brief"` | Marks a described form: nothing was observed, so every aspect is `hand_authored` and the connector `none_exist` |
| page `intro` | Text shown above the page's questions; kept as a content block |
| page `show_when` | The page shows only when the rule holds (same syntax as a field's) |
| page `repeat`, `repeat_label` | The section repeats once per record (a Repeater) |
| field `help`, `note` | Help text for the respondent; a note for the builder |
| `coverage.conditions` | `none_exist` when the brief has no show-and-hide rules; otherwise the rules make it `hand_authored` |

Types, `show_when` syntax and ids follow the capture format in [google-forms.md](google-forms.md).

## Then

```bash
python3 scripts/plan_form.py _forms/brief-<slug>        # plus --use-default-org or --describe-file when an org is readable
```

What differs from a conversion:

- **No connector, so no derived targets.** Which records the answers create comes from the person (ftk-start asks once) and from the platforms found in the org.
- **Every field still lands on a real Form Submission field.** Packaged first (the Contact 1, Contact 2, address and organization blocks, then the generic answer slots), a new field only when none fits, and then as a question. In a paid org, contact, organization and address questions are built on their own object's form with Form Template Mapping.
- **With no org connected**, every target is marked Verify In Org. The design is still complete.
- **Grant platforms.** Outbound Funds: a Funding Program links to the Form Template, and the conversion creates the Funding Request with the converted Contact. Nonprofit Cloud Individual Application: there is no packaged conversion, so keep the answers on Form Submission, mark the link to the application as a gap, and plan the conversion with new-mapping-flow (the application's account must be a person account).
