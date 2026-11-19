# plan.json

The design as data, at `_forms/<slug>/plan.json`. It uses real Salesforce API names and the stored values the design system README gives, so build-template (and later an in-package converter) can build it without interpretation. Keys a reader does not know are ignored: add rather than rename.

You write the design part. `draw_plan.py` writes the rule-decided part (marked *written by the run* below) and reports every value it changes. A value you set on purpose that the run would otherwise change goes in `keep`.

In the plugin repository (not installed with the plugin), a complete, invented three-page example is `tests/skills/form-design/fixtures/three-page-application/plan.json`; a converted two-page form with its `ir.json` is `tests/skills/form-design/fixtures/converted-two-page/`; an anonymous one-page survey is `tests/skills/form-design/fixtures/survey-one-page/plan.json`.

```json
{
 "plan_version": "1",
 "slug": "volunteer-application",
 "form_kind": "application",
 "source": {"ir": "ir.json", "platform": "formassembly", "form_id": "1234567", "form_name": "Volunteer Application", "url": "https://www.tfaforms.com/1234567", "screenshot": "sources/screenshot.jpg"},
 "intake": {"org_id": "00D000000000001AAA", "audience": "public guests", "edition": "paid", "catalog": "catalog.json", "objects": ["Contact", "Account"], "build": "Form Template", "workstream": "Volunteers",
            "build_mode": "records",
            "program": {"name": "Community Garden Volunteers", "url": "https://www.example.org/volunteer/", "voice": "_brand/riverside-community-garden/programs/garden-volunteers.md"},
            "gap": {"asked": ["confirmation", "emails"], "defaults_taken": ["save_progress", "header"],
                    "confirmation": {"idea": "...", "tone": "..."},
                    "emails": {"confirmation_to_respondent": true, "from": "...", "reply_to": "...", "staff_notice": {"on": false, "to": []}},
                    "save_progress": true, "header": {"logo": "brand kit", "banner": "brand kit"}, "reviewers": "...", "other": [{"item": "...", "answer": "..."}]}},
 "template": {
  "Name": "Volunteer Application",
  "Confirmation_Page_Message__c": "<p style=\"font-size: 16px; line-height: 1.5\">Thank you, {{FlowToolKit__Contact1_First_Name__c}}. ...</p>",
  "Offline_Message__c": "<p>Applications are closed right now. ...</p>",
  "banner": {"subtitle": "Join the growing team for the 2027 season.", "tags": "2027 season; About 10 minutes"}
 },
 "style": {"brand": "#2f6b3a", "heading_color": "#1d3b24", "accent": "#f2c14e", "background": "#f7f5ef", "font": "Source Sans 3", "heading_font": "Merriweather",
           "fonts_href": "https://fonts.googleapis.com/css2?family=Source+Sans+3&family=Merriweather", "Corner radius": "8px"},
 "images": {"logo": "brand/logo.png", "banner": "brand/banner.jpg"},
 "assets": {"logo": "Riverside_Logo", "banner": "Riverside_Banner", "logo_alt": "Riverside Community Garden", "banner_alt": "Volunteers planting"},
 "components": [
  {"key": "contact", "decision": "reuse", "name": "Contact_Details", "object": "Contact",
   "catalog_match": {"name": "Contact_Details", "why": "same object and the same five fields"},
   "asked": {"question": "Reuse Contact Details as is, extend it, or build new?", "answer": "reuse"}, "reason": "Catalog match on its definition",
   "shape": "metadata"}
 ],
 "pages": [
  {"Page_Label__c": "Your Details", "Description__c": "Tell us who you are. We use it to place you on a team.", "Button_Label__c": "Continue", "condition": null,
   "sections": [
    {"Header_Title__c": "Contact information", "Header_Subtitle__c": "How our coordinator reaches you.", "Header_Icon_Name__c": "utility:user",
     "Section_Frame__c": "box", "Header_Style__c": "outlined", "component": "contact",
     "fields": [
      {"source_id": "tfa_12", "label": "First name", "object": "Contact", "field": "FirstName", "control": "TextInput", "variant": "standard",
       "widths": [5, 5, 12], "required": true, "help": "", "options": [], "placement": "source-object: existing Contact component", "status": "supported", "condition": null}
     ]}
   ]}
 ],
 "emails": {"letterhead": {}, "sample_merge": {}, "confirmation": {}, "saved": {}, "resume": {}},
 "questions": [{"ask": "...", "why": "..."}],
 "notes": ["Design notes shown beside the form on the canvas"],
 "dropped": [{"source_id": "tfa_99", "reason": "no longer collected"}],
 "gaps": [{"feature": "...", "needed": "the exact behavior", "evidence": "source reference"}],
 "decisions": [{"what": "...", "why": "...", "when": "2026-01-15"}],
 "keep": []
}
```

## Top level

| Key | Rule |
|---|---|
| `slug` | The form's short name; the artboard file names start with it. Default: the plan's folder name |
| `form_kind` | `survey`, `application`, `grant`, `registration`, `intake`, `release`, `request`, `feedback` or `other`. With the page count and the counted minutes it picks the form-type row |
| `stages` | Optional. `true` or `false` only when the person chose stages mode against the row; it wins over the row |
| `source.url` | The live source the reviewer opens to compare. No public link: the captured file's path. A brief has `platform` `brief` and no link |
| `source.ir` | form-migrate's `ir.json`, relative to the plan. With it the run checks every source field is in the plan or `dropped`, and that the plan has no more rules than the source |
| `source.screenshot` | Optional full-page screenshot of the source, drawn beside the redesign (uploaded to the canvas like any image) |
| `intake.edition` | `paid` or `free`, from the project config. Decides the mapping preference |
| `intake.catalog` | org-catalog's file. Missing: every component carries `reason: "no catalog"` and a question |
| `intake.build_mode` | `metadata` (default when absent) or `records`, from the gap round: records mode builds the template and its new or extended components as records and JSON only, with no metadata deploy, so it can run from chat with a Salesforce connector (build-template) |
| `intake.program` | The program the form serves, from the gap round: `name`, `url` and `voice` (brand-kit's program voice file). Its words lead the form's copy; absent, the organization's general voice does |
| `intake.gap` | The gap interview's answers (before-drawing.md, step 7): `asked` and `defaults_taken` list the items by name; `confirmation`, `emails`, `save_progress`, `header`, `reviewers` and `other` hold what was settled. The copy, the emails and the row settings are written from it. Written once; ftk-start may write it before form-design runs |
| `intake.workstream` | The form's program or area ("Volunteers", "Grants"); build-template files components under it |
| `style` | Colors, fonts and corner radius as the canvas draws them. `form_style` (Style Editor Basic values) defaults to Borders `#8A8A8A`, Border thickness, Text size and Input size 150%, Field spacing 125% |
| `images` | Local image files the canvas shows, relative to the plan: `logo`, `banner`. No banner: the package photo stands in |
| `assets` | The Asset File names build-template uses for the logo and banner |
| `emails` | See Emails below |
| `payment` | `{"required": true, "condition": <a rule>}`: the template's Payment Required and Payment Conditions. Without `condition`, every submission pays. The rule has the page-rule shape, on Form Submission fields. The canvas draws a marked payment placeholder after the last page (on the review screen in stages mode); guests need Read on Payment Conditions and every field the rule reads |
| `url_parameters` | `[{"param": "pv1", "field": "Shift__c"}]`: the template's URL Parameter Mapping, so a link can fill a field. Parameters: `pv1` to `pv9`, `utm_source`, `utm_content`, `utm_medium`, `utm_term`, `utm_campaign`, `payment_intent`, `eventType`. Never `sourceId`: the form reads it by itself. Never a resume link: the package reads `resume` on its own. Listed in the canvas's design notes; guests need Edit on each field |
| `no_email_reason` | Why a form has no confirmation email (it collects no email, or it is anonymous) |
| `canvas_url` | The review canvas's link, recorded once the canvas is created |
| `brand_board` | Optional: `headline`, `tone`, `copy` (paragraphs), `swatches` ([name, color, role]) for the brand artboard |
| `notes`, `questions`, `dropped`, `gaps`, `decisions` | As named. `questions` holds anything only the person can settle: proposed new fields, placeholders, add-ons, structure changes |
| `keep` | Names the run must not change: Form Template field API names, `banner.layout`, `banner.placement`, `Estimated_Time__c`, `Button_Label__c` |
| `form_type`, `styleTokens`, `rich_text_scale` | *Written by the run.* `long` or `short` for build-template's switches; the saved `--ftk-` tokens; the factor stored rich text is scaled by |

## Template

| Key | Rule |
|---|---|
| `Name` | The form's title, shown in the banner |
| `Confirmation_Page_Message__c` | Two or three paragraphs at 16px (`<p style="font-size: 16px; line-height: 1.5">`). The run stores it scaled by the Text size (24px at 150%) because the package's font scale does not reach an inline size; the canvas draws it back at 16px |
| `Submit_Button_Label__c` | One of: Submit, Submit Form, Submit Survey, Submit Application, Submit Registration, Submit Payment, Save, Save Proposal, Register, Apply Now, Update. Default from the kind |
| `banner` | `subtitle`, `tags` ("2027 season; About 10 minutes": a time is replaced by the counted range), optional `image: false`. *Written by the run:* `layout` (compact for one page, overlay otherwise; `split` only when named), `placement` (`header` beside the vertical indicator, else `singleCardHeader`, square bottom corners), `height` small, `title` |
| Row settings | *Written by the run:* `Stages_Mode__c`, `Allow_Save_Progress__c`, `Enable_Review_Screen__c`, `Send_Save_Progress_Email__c`, `Attach_PDF_Confirmation__c`, `Buttons_Position__c`, `Button_Alignment__c`, `Hide_Stage_Indicator__c`, `Stage_Indicator_Type__c`, `Stage_Mode_Layout__c` |
| Email names | *Written by the run* from `emails`: `Email_Template_Name_Confirmation__c`, `Send_Confirmation__c`, `Recipients_Confirmation_Email__c`, `Email_Template_Name_Saved__c` (ordinary pages with Save Progress), `Email_Template_Name_Resume_Form__c` (stages mode) |
| `Enable_Form_Analytics__c` | Set it when the organization wants answer charts and reports (surveys) |

## Pages and sections

| Key | Rule |
|---|---|
| `Page_Label__c` | Meaningful, never Welcome |
| `Description__c` | At least two sentences |
| `Button_Label__c` | Ordinary pages: Continue (written by the run). Stages mode: the overview row's start label (empty means Start Step; Learn More or Get Started for an About page). Allowed: Continue, Submit, Save, Submit Form, Submit Application, Save Proposal, Apply Now, Learn More, Get Started, Start Step |
| `Estimated_Time__c` | *Written by the run*, counted from the questions |
| `header` | Only for a page that needs its own title: `{title, subtitle, icon, style}`. Never "Page N of M" |
| Section `Header_*`, `Section_Frame__c`, `Divider_*` | Form Template Page Section fields (frame `box`, `shadow`, `clean`; header `outlined`, `classic`, `classicSpread`, `card`, `hero`). A section with fields has a frame; `clean` only for a headerless follow-up or note. *Written by the run when missing:* `Title__c`, `Show_Header__c` false for untitled, `Header_Style__c` outlined, `Top_Margin__c` `slds-m-top_xx-large` and `Bottom_Margin__c` `slds-m-bottom_none` (frames 68px apart) |
| `component` | The key of its entry in `components` |
| `rich_text`, `rich_text_variant` | The section's own text above its fields (`default` or `highlight` for a note with a brand bar) |
| `inner_type` | `likertSection` (rows are the fields, the scale is the first field's options; `matrix: "ranking"` or `Likert_Mode__c: "Number"` for numbers) |
| `Survey_Section__c` | `true`: each question as a survey card |
| `Component_Type__c` | `Flow` with `FlowApiName__c`, or `Lightning Web Component` with `lwcComponentName__c` (the LWC exposes `@api record` and `@api objectApiName`) |

## Fields

| Key | Rule |
|---|---|
| `object`, `field` | Full API names: `Form_Submission__c` (build-template adds the namespace), packaged fields as `FlowToolKit__Contact1_First_Name__c`, the org's own as `Grade__c` |
| `new_field` | `true` for a proposed new field (listed in `questions`, status `verify`) |
| `required_change` | On a field whose `required` differs from the source's (`ir.json` `fields[].required`): the person's confirmed answer and reason in a few words ("the person keeps it optional: some volunteers never give it"). Until answered, a question in `questions` names the source id |
| `sensitive` | `{category, answer}` on a field form-migrate marked sensitive (`ir.json` `fields[].sensitive`). `answer`: `not collected` (the field goes to `dropped` instead), `encrypted` (an encrypted field only the people who need it can read, kept out of emails, PDFs and prefill) or `ordinary`; until answered, a question in `questions` names the source id |
| `control` / `variant` | Exactly as the design system README writes them: TextInput, FormattedInput (`email`, `phone`, `url`), Picklist (`standard`, `radio`, `radiobuttons`, `separatedbuttons`, `surveybuttons`, `visualpicker` ...), MultiPicklist, Checkbox (`attestation` for a consent), NumberInput (`currency`), TextArea, DateInput, Address (variant `Address` is the row that draws the component: the compound field, or `Id` for an address kept in separate fields. It needs all five parts after it, variants `Street`, `City`, `State`, `PostalCode` and `Country`, each on its field, which are not drawn on their own: without them the package draws no address or one blank box. The row's `required` is what the form enforces on every part (Flow Tool Kit never reads a part's own flag), so the row is required exactly when a part is. draw_plan.py adds the parts of a standard address field such as `MailingAddress`; build-template builds an address in a section of other fields as its own address section), Repeater, SignaturePad, ImageUpload (one photo), FileUpload (documents), Lookup |
| `widths` | Columns at large, medium, small |
| `options` | Stored values as strings, or `{"label", "value"}`. `option_descriptions`: `{value: explanation}`, only when the source supplies the words |
| `attestation_text` | A consent's statement beside its checkbox |
| `repeater` | `{columns: [{source_id, label, type, options, required, widths}], newButtonLabel, recordTitle, max}` |
| `config` | Package settings for the field (`acceptedFormats__c`, `referenceTo`, `objectLabel` ...) |
| `placement` | Starts `source-object:`, `mapped:` or `submission:` with the reason in a few words |
| `status` | `supported`, `verify` or `gap` (a gap is also in `gaps`) |
| `label_hidden` | `true` when the section's text asks the question |

## Rules

Every page, section and field rule has the shape build-template builds exactly:

```json
{"label": "Other pronouns chosen", "show_when": "Pronouns is Other", "object": "Form_Submission__c", "mode": "showWhen", "type": "AND",
 "conditions": [{"field": "FlowToolKit__Contact1_Pronouns__c", "operator": "==", "value": "Other", "source_id": "b7"}]}
```

- `label`: the purpose in plain words, at most 40 characters, never an API name. Form Builder lists rules by it.
- Operators: `==`, `!=`, `CONTAINS`, `INCLUDES`, `EXCLUDES`, `<`, `>`, `<=`, `>=`, and `TRUE`, `FALSE`, `BLANK`, `NOTBLANK` (no value).
- One condition per allowed value, joined by `OR`; `INCLUDES` for a multi-select controller; `TRUE` for a checkbox. Two controlling questions ("Other in either list"): one condition per field and value, `OR`. Mixed logic: `type` `CUSTOM` with `custom` `"(1 OR 2) AND 3"`.
- A rule that governs a whole section goes on the section, not on each field.
- Only the source's rules: never add one the source does not have.

## Components

| Key | Rule |
|---|---|
| `decision` | `reuse` (an existing component, `name`), `extend` (a new version of `name` under its own `new_name`, plus `add_fields`; the original is untouched), `update` (changes `name` in place for everyone using it; see below), `shared-new` (a new shared component, built first), `form-only` (questions only this form asks: JSON on its section, or a one-off component when `shape` says `record` or `metadata`), `flow-section` and `custom-lwc` (with `build`), `shared-record` (written only by build-template's review pass) |
| `shape` | How the component's questions are stored (the component shapes standard, `component-shapes.md`): `metadata` (a custom metadata component), `record` (a Form Component record) or `json` (questions on this section only). The person's choice: `json` only with `form-only`; `shared-new` and `extend` are `metadata` or `record`; `reuse` and `update` keep the existing component's shape (the catalog's `shape`); `shared-record` is `record`; `flow-section` and `custom-lwc` have none. A plan written before shapes has none: readers then build `form-only` as `json` and `shared-new`, `extend` and `shared-record` as `record`, and say so |
| `shape_asked` | `{recommended, why, question, answer}`: the shape question put to the person, the recommendation with its reason, and the answer. Required whenever `shape` is set on `form-only`, `shared-new` or `extend`; `answer` equals `shape` |
| `catalog_match` | `{name, why}` whenever the org catalog has a matching component |
| `asked` | `{question, answer}`: the reuse question and the person's answer. Required with `catalog_match`. The answer matches the decision: reuse, extend, update (or "update the shared component"), or new for `shared-new` and `form-only` |
| `usage` | For `update`: `{"status": "complete", "consumers": [every template and component that uses it]}`. The update question names every consumer |
| `shared_change_reason`, `changes` | For `update`: why the shared component changes, and the change itself (its diff) |
| `packaged` | `true` for a packaged component (also read from `catalog_match.packaged` or `editable: false`). A packaged component is never updated, only extended |
| `object` | The object the component is built on |
| `form_template_mapping` | Paid orgs, a component on another object: `{"apply_to": "<all records, or a Form Submission lookup such as FlowToolKit__Account__c>", "fields": {"<field>": "<Form Submission field>"}}` |
| `build` | `build-flow-section` or `build-custom-lwc` for those decisions |
| `design_file` | For `extend`: the component's export from Form Builder (Export), saved beside the plan, when the org's copy cannot be read (chat with no org connector). build-template builds the extended copy from it |
| `what_it_does` | For a Flow Section or custom LWC: one sentence the canvas shows |

## Emails

```json
"emails": {
 "letterhead": {"org": "Riverside Community Garden", "tagline": "...", "address": "...", "email": "volunteer@example.org", "site": "https://www.example.org", "site_label": "example.org"},
 "sample_merge": {"FlowToolKit__Contact1_First_Name__c": "Jordan"},
 "confirmation": {"name": "Volunteer_Application_Confirmation", "subject": "We received your application, {{FlowToolKit__Contact1_First_Name__c}}",
                  "heading": "Thank you for applying", "body": ["...", "..."], "button": {"label": "See the volunteer calendar", "url": "https://www.example.org/volunteer"}},
 "resume": {"name": "Volunteer_Application_Resume", "subject": "...", "heading": "...", "body": ["..."],
            "button": {"label": "Continue your application", "url": "{{FlowToolKit__Internal_Resume_Link__c}}"}}
}
```

`saved` has the same shape as `resume` and is used on an ordinary form with Save Progress on. Merge fields are `{{Field__c}}` on the Form Submission; the template gets Lightning merges and the canvas the sample values. No relationship merges (`Form_Template__r.Name`).
