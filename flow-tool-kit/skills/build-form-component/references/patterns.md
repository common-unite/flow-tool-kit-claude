# Patterns from forms built in Form Builder

A study of 229 forms built in Form Builder (229 forms, 634 sections, 1,078 fields, 128 rules, 166 conditions) shows the structure that works: widths, sections, logic and naming. It predates the newer controls (Likert, visual picker, option settings, preset amounts, stepper and slider, record picker), so take **structure** from here and **control choice** from SKILL.md and [authoring-cookbook.md](authoring-cookbook.md) Part 3.

## 1. What metadata forms really store

- `config__c` is the real payload on all five custom metadata types: a flat JSON copy of one Form Component record. The package reads `config__c`, not the separate columns. Keys such as `sectionType__c`, `picklistType__c` and the widths exist only inside it.
- Parent links: the `Form__c` and `Form_Section__c` columns hold the parent's record name; inside `config__c` the same keys hold the namespaced name.
- `fieldName__c`: in records saved by Form Builder the **column** holds a durable field Id pair, while `config__c` holds the plain API name. Hand-authored records may put the API name in the column; both resolve. When you compare or search records, read the API name from `config__c`.

## 2. Form archetypes

| Archetype | Share | Traits |
|---|---|---|
| Intake block (a reusable component) | about 15% | One input section, 2 to 8 Form Submission fields, placed in templates. Contact, address, organization, emergency contact |
| Registration or lead capture | about 9% | Contact and address sections with interest questions; show and hide rules |
| Donation or registration staging | about 4% | Several sections, image headers, a rich text total |
| Survey | about 7% | Choice controls per question with the question as `customLabel__c`; star ratings; a carousel for one question per slide |
| Settings editor | about 6% | Many small sections, `shrink` toggles, heavy logic, relabels such as "Enabled" |
| Table and its row form | about 10% | One table section, 3 to 7 columns with widths and wrapping; `Default_Table_Form__c` names the row form |
| Content panel (no fields) | about 17% | Only rich text, image and divider sections |
| Read-only review | about 3% | Read-only fields or embedded components |

Composition: a `formComponent` section embeds another component by name. That is how tabsets and settings editors nest reusable blocks.

## 3. How often each setting appears

- `sectionType__c`: inputSection 50%, richTextSection 13%, dividerSection 12%, imageSection 8%, formComponent 8%, addressSection 4%, tableSection 3%, flowScreen under 1%.
- A field's `displayType__c` is the rule's action: SHOW 93%, HIDE 4%, REQUIRED and READONLY about 1% each.
- `picklistType__c`: standard 77%, radiobuttons and radio 10%, iconbuttons, multiselectcheckbox, multiselectbadge, pathbuttons the rest.
- `booleanType__c`: default (toggle) 86%, radiobuttons 3%, checkbox under 1%. `booleanPicklistTypeOverride__c` Yes/No on 2%.
- `richTextType__c`: signaturePad and imageUpload on a few fields each; `longTextType__c: fileUpload` rare.
- `labelVariant__c`: standard 83%, none 6%, label-inline and label-hidden rare.
- `picklistColumnsSize__c`: none (Auto) 87%; size_1-of-3, size_1-of-1, size_1-of-5 for option grids.
- `addressFieldType__c`: every address section has exactly six parts.
- Field widths (small/medium/large): `12/12/12` 59%; then `12/6/6`, `12/5/5`, `12/3/3`, `12/4/4`, `12/12/shrink`, `12/7/7`, `12/8/8`. Small is always 12 (phones stack); medium and large carry the split; `shrink` (always a toggle) fits the content.

## 4. Option customization

- `picklistOptionOverrides__c` (a semicolon whitelist, such as `Completed;Canceled`, or a neighborhood list ending `;Other`) shows one form's slice of a shared value set.
- `customLabel__c` on a quarter of fields: question wording, short relabels ("Hide"), merges (`Select {{*__Component_Type__c}} Component`), `{{helptext}}` promoting help text to the label.
- `placeholder__c` on a tenth: input masks (`(###) ###-####`, `$0.00`) and merges.
- `fieldPrompt__c` (rich text above the input) and `disableHelpText__c` are common in settings editors.

## 5. Conditional logic

- `conditionType__c`: AND 86%, OR 14%; CUSTOM is supported but rare.
- `operation__c`: `==` most often, then TRUE, NOTBLANK, BLANK, CONTAINS, `<`, `!=`, `>=`, `>`, FALSE.
- Shape: four in five rules have one condition; a few have two to six.
- An element's own `displayType__c` is the action. SHOW is a reveal, HIDE a suppress, REQUIRED and READONLY apply while matching. Hidden elements have their values cleared.
- Typical: a rule "Show Work Email" (`Preferred_Email__c == Work`) reveals the work email, one rule per option; `Preferred_Phone__c == Home` makes Home Phone REQUIRED; a five-condition OR hides an action for several record kinds.

## 6. Naming

- Hand-crafted components use purpose names in `PascalCase_With_Underscores` (`Volunteer_Primary_Contact`, `Form_Template_Settings`), with children that start with the parent's name (`Volunteer_Primary_Contact_First_Name`).
- Form Builder generates opaque names (`Form_<random>_FS...` for sections, `_FF` fields, `_FL` rules, `_FC` conditions) and puts the human name in the label.
- Either works; be consistent within a component, and always give sections and rules plain-words labels.

## 7. Layout recipes

1. **Single-column stack** (the most common): an input section with 1 to 4 fields at 12/12/12.
2. **Header band with inputs**: `showHeader__c` with `iconName__c` (`utility:user`, `utility:location`, `utility:company`, `utility:edit_form`), optionally collapsible.
3. **Pairs on one row**: consecutive fields at 6/6 on medium and large (first and last name, phone and email), or 5/7 and 7/5, or 8/4.
4. **Address**: an address section with six parts in order (the compound row, Street, City, State, Postal Code, Country), all width 12.
5. **Content sandwich**: a rich text intro, input sections, styled dividers between them; an image section with an overlay for a banner.
6. **Settings toggle row**: a Boolean at 12/12/shrink with a one-word `customLabel__c`, often gating the fields after it.

## 8. Traps

- Unset options are absent keys; `config__c` never holds `null` or empty strings. Author the same way.
- Older builder versions wrote about 35 default keys on every field. The current builder writes only what is set. Expect the long form in old records; do not copy it.
- **The path matters more than any key.** The component JSON and metadata `config__c` differ:

  | | Component JSON ([anatomy.md](anatomy.md)) | Metadata `config__c` |
  |---|---|---|
  | `QualifiedApiName` | Required | Absent (the record's own name carries it) |
  | `*__fields__r` / `*__sections__r` | Required, present even when `[]` | **Never. Fatal** |
  | `is*Section` flags | Required | Absent |
  | Spacing class strings | Authored | Absent |
  | `attributes` | Absent | Present, naming the record's type |
  | Widths | `"12"` may be left out | **Required** on root, section and field, or the form renders as one column |

  The children arrays are the fatal one: an empty `sections__r` tells the package the form has no sections, overriding the child records. The Form Builder then fails on open and leaves stray divider sections behind. Ground truth is one query: build one form in Form Builder and read its `config__c`:

  ```
  sf data query -o <org-alias> -q "SELECT DeveloperName, FlowToolKit__config__c FROM FlowToolKit__Form__mdt WHERE DeveloperName = '<name>'"
  ```

- Mixed JSON types: widths are strings, positions numbers, booleans real, `maxDays__c` a number, `minute__c` a string.
- `required__c` is both a column and a key in `config__c`; keep them equal.
- `Delete__c` is a soft delete: deleted rows can remain and must be filtered out.
- A section's `title__c` is always present, even on dividers; whether it shows is `showHeader__c`.
- `Default_Table_Form__c` may hold a record Id or a name; both resolve.
