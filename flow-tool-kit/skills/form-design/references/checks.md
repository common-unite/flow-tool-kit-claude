# The design checks

`draw_plan.py` runs these on every plan before it draws. An **error** stops the run and nothing is drawn; a **warning** is printed and the run goes on. Each message says what to change in `plan.json`. `--check` runs them without changing anything, for a plan someone else edited.

## Errors

| Check | Why |
|---|---|
| A confirmation message under two paragraphs, four sentences or 45 words, or with no next step or no contact | Respondents need thanks, why it matters, what happens next and who to ask |
| A page label of Welcome, a page description under two sentences, a titled section with no subtitle, an empty section | Stage cards and the stages accordion show these words |
| A button label outside the package's lists, or Next on an ordinary multi-page form | A label outside the restricted picklist fails the build; the forward button reads Continue |
| A "Page N of M" page heading | The indicator or stage list already shows position |
| An em-dash anywhere a respondent reads | House style |
| A section icon that is not a `utility:` icon | House style; other icon sets draw inconsistently |
| A rule with no label, a label over 40 characters or an API name, a condition missing its field, operator or value, an operator the package does not evaluate, a value holding a second question | build-template builds rules exactly; Form Builder lists them by label |
| More show/hide rules than the source has (when `ir.json` captured its conditions) | Only the source's rules |
| A visible source field neither in the plan nor in `dropped` | Every source question is kept or dropped on purpose. A part form-migrate folded into one date question (a date asked as Month, Day and Year) goes in `dropped`, and the kept part is one date control |
| A source field form-migrate marked `sensitive` (a government id, an account number, health information, a password, a date of birth with the name) whose plan field has no `sensitive` mark, or no `answer` and no question naming it; an answer `not collected` with the field still on a page | Whether to collect it at all, and how to store it, is the person's decision. An `ordinary` answer leaves a warning |
| A placed source field whose `required` differs from the source's (`ir.json` `fields[].required`, either way) with no `required_change` and no question naming it; asked but unanswered leaves a warning | Keep requiredness exactly: making a question optional or required is the person's decision, recorded on the field |
| A field with no Salesforce field, an unknown control not marked gap, widths that are not three numbers from 1 to 12, a bad status or placement, a choice field with no options, a repeater with no columns | The build needs every one |
| A gap field not listed in `gaps` | Gaps are reported, not drawn as if they work |
| A catalog match with no answer in `asked`, or an answer that does not match the decision | Never reuse, extend or duplicate a component silently |
| An `update` without its own question answered update, without a complete `usage` list named in that question, without `shared_change_reason` and `changes`, or on a packaged component; an `extend` whose `new_name` is the original's | Updating a shared component changes every form that uses it; extend never touches the original |
| `reuse` or `extend` without the component's name; a Flow Section or custom LWC without its `build` skill, flow name or component name, or in a section of the wrong type | The build and the follow-on skills need them |
| A component on another object in a paid org without `form_template_mapping` | The mapping preference: prefill, live updates and Apply Submission Field Maps need it |
| An email linking with `pv9` or `recordId`, a Save Progress or resume email without `{{FlowToolKit__Internal_Resume_Link__c}}`, a relationship merge | Since the Save Progress Resume Link field, the package builds the link; Lightning merges cannot follow relationships |
| A payment rule that fails the rule checks; `payment.required` not true or false | build-template writes Payment Conditions exactly |
| A URL parameter the package does not read, `sourceId`, a parameter mapped twice, or one with no field | build-template writes URL Parameter Mapping exactly; the form reads `sourceId` by itself |
| A `shape` other than metadata, record or json; a shape set on `form-only`, `shared-new` or `extend` with no answered `shape_asked`, or an answer that differs; `json` on anything but `form-only`; a `reuse` or `update` whose shape differs from the existing component's; a shape on a Flow Section or custom LWC | The shape is recommended and asked, never decided silently; JSON is fixed to one section; reuse keeps the component as it is (`_shared/standards/component-shapes.md`) |
| An `extend` component's `design_file` missing or not JSON | build-template builds the extended copy from it when the org's copy cannot be read |
| An address without its Address row, or missing one of its five parts (Street, City, State, PostalCode, Country), or with one twice | The package draws an address only with its row and all five parts: without them it draws nothing or one blank box. A lone row on a standard address field (MailingAddress) is not an error: normalize adds its parts |
| A required address part under an optional Address row, or a required row over parts that are all optional | Flow Tool Kit takes every part's required flag from the row: under an optional row the source's required street, city, state and zip show as optional. Make the row required (the form then requires every part, Country included), or make the parts optional with `required_change` |
| An anonymous survey with Save Progress, Autosave or the Save Progress email on | A partial save records who saved and emails a named address |

## Warnings

- No source link; no inactive message; an API name in respondent copy.
- A headerless section with a frame, or a titled section with fields and no frame.
- A one-page survey with no Survey Section.
- Fewer rules than the source.
- No org catalog read; a component on an object the free edition does not cover.
- A `form-only`, `shared-new` or `extend` component with no `shape` (a plan written before shapes): it still draws, and build-template builds it as before (`form-only` as JSON, the others as record components). Recommend a shape, ask, and record it.
- Save Progress email or stages mode on with no saved or resume email designed (the package sends its built-in one).
- No confirmation email and no `no_email_reason`.
- An anonymous survey with a file upload, or an audience other than public guests.
