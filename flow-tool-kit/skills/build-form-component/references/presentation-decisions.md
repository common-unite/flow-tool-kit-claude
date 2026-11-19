# Presentation decisions before authoring a complete form

The house rules ([_shared/standards/form-house-rules.md](../_shared/standards/form-house-rules.md)) set the defaults: widths by expected answer, frames, headers, controls. This page covers the decisions behind them.

Component reuse, page structure, and field layout are separate decisions. Record all three before generating the preview or metadata.

- Preserve a source form's reasonable page structure. A logical question group or reusable component does not automatically become a page. Introduce a page break for a stated reason such as length, a real task transition, or an integration dependency. Keep payment as a separate step when that is the source workflow.
- Choose indicator visibility explicitly, from the form-type rules ([_shared/standards/form-type-rules.md](../_shared/standards/form-type-rules.md)). `Form_Template__c.Hide_Stage_Indicator__c` suppresses it; the single-card layout keeps a hidden indicator from leaving empty space.
- Record source row membership and responsive field widths (`widthSmall__c`, `widthMedium__c`, `widthLarge__c`). Use source proportions and expected answer length to choose supported twelve-column spans. Leave unused row space when appropriate. Do not default all inputs to 6/12 or replace that mistake with another universal column count.
- Configure `picklistColumnsSize__c` independently of field width. Source arrangement, label length, container size and control variant inform the option layout. Option count alone is insufficient.
- Prefer **Auto** (`picklistColumnsSize__c = none`) for small groups of short radio/checkbox labels. Auto uses content widths and natural wrapping; it is different from Grow and fixed columns. Do not distribute unused row space between a few choices.
- Use fixed columns when they improve scanning, such as many short numbered choices. For long mixed-length labels, compare Auto with fewer columns at the intended field width. Avoid excessive label wrapping; one column is a contextual option, not a universal mobile or desktop default. Render and inspect the alternatives before deciding.
- Preserve meaningful option order and stored values. Reorder only as an explicit presentation choice where sequence is not meaningful; never sort chronological or ranked options by label length.
- If a desired row crosses proposed component boundaries, revisit the component contract or use a supported composition. Do not assume arbitrary field interleaving across separate CMT components. A combined person-role profile can be appropriate, but it still needs catalog-fit and mapping validation.
- Test the intended page count, indicator visibility, row membership, field proportions and option layout, not just no-overflow and control-level fidelity. Check narrow containers as well as viewport sizes.

For a form described without a visual source, make these choices deliberately from the task and audience; do not invent source evidence. Record any meaningful deviation so a reviewed preview and its delivered configuration express the same decisions.

## Native controls and label fit

- Record which theme and styling the form runs with. The package's default styles and an org's Form Style values are different references; one checked input does not certify a whole form. Do not override the default radius, color or typography with unrelated org styling: a brand goes in Form Style values.
- Ordinary field width must fit the label as well as the expected answer. Preserve useful trailing whitespace; avoid squeezing labels into multiple lines on desktop. Do not globally prevent wrapping on phones or long questions.
- Use the package's hanging required marker so label text aligns with the input edge. Match standard numeric appearance without accidentally adding browser spinners; explicit stepper settings are separate.
- A short Boolean beside other inputs can use the default toggle and Shrink width, often at the end of the row. Choose a supported variant based on context; not every Boolean needs a toggle.
- Prefer the supported attestation card for consent/authorization when appropriate: complete wording inside a clickable card, no duplicate outer label, visible selected/error states and keyboard access. Preserve source wording and option identity; do not automatically rewrite consent language.
- Address sections need full available width and native address anatomy. If source city/ZIP dependencies cannot be represented by the native compound address, document a source-compatible custom composition and its unresolved delivery requirements. Do not claim a set of separate controls is a verified native address component.

## Stacked Boolean questions

For a stack of independent yes/no questions, consider the package's positioned toggle: question at the left, switches aligned on a common right edge, and explicit Yes/No state beneath each switch. The package setting **Left (toggle)** means the label is on the left (`labelVariant__c = left`), not that the switch is on the left. Use `booleanType__c = default` and `booleanPicklistTypeOverride__c = Yes/No`. The right label position reverses the arrangement.

Keep the switch a fixed width while long questions wrap in the remaining space on phones. Preserve source checked/unchecked semantics, requiredness, option identity and conditional follow-up fields. A source unchecked checkbox may be displayed as No; do not silently change it into a required answered/unanswered field. Test state messages, alignment and follow-up behavior. Inline checkboxes remain reasonable for dense lists; attestation cards remain appropriate for substantive consent. Choose contextually, not by blanket Boolean conversion.

## Numeric types and review modes

Resolve display type from the mapped Salesforce field and package formatter, not just the source HTML input type. Currency, percentages, decimals and counts have different display behavior. If the mapping is provisional, record the intended type, currency and locale explicitly and keep confirmation as an authoring prerequisite. Do not infer a confirmed mapping from a label such as Income.

Keep raw numeric values separate from display formatting. Currency should show its symbol, grouping and scale when unfocused and remain editable on focus; preserve source minimum, requiredness and precision rules. Reject malformed pasted values instead of silently stripping punctuation or rounding. Test formatting, edits, clearing, pasted amounts, validation and dependent calculations. Check any currency or locale other than USD and en-US in Preview Form before relying on it.

Visual question groups need not create reusable-component boundaries. Adjacent related questions can share a visual section while ownership stays explicit in the composition plan. Verify that the final package composition supports that arrangement before calling it deliverable.

The answers PDF prints at the printable page width whatever the screen width; inspect a generated PDF as well as the screen. Sections with nothing to show are left out of the PDF on their own.

## Template content versus reusable component content

When composing Form Templates, default form-specific titles, introductions, header messages, icons and dividers to the point of use: `Form_Template_Page_Section__c` records. `Show_Header__c`, `Header_Title__c`, `Header_Subtitle__c`, `Header_Text__c`, `Header_Icon_Name__c` and `Header_Display__c` configure the section header. `Header_Divider_Style__c` styles a divider-format header; it is distinct from the section's own `Field_Set_Show_Divider__c`, `Divider_Style__c` and `Divider_Position__c`. Standalone content can use a Display Text section with `Component_Section_Text__c`. Check the org's installed package has a setting before writing it.

A contact question component can appear as Primary contact or Garden coordinator without changing its metadata just to rename the section. Reusable components retain field labels, conditions, consent statements and instructions intrinsic to their contract. Internal component headers/dividers are appropriate when intrinsic to the component; avoid duplicating them with template headers. Do not move arbitrary field overrides to template records unless the runtime supports them.

Imported HTML often contains accidental fonts, colors, margins and empty wrappers. Default ordinary headings and instructional text to the target theme: extract text for simple titles, or normalize paragraphs, emphasis, lists and links for rich text. Preserve wording and meaningful structure. Keep intentional branded styling only as an explicit presentation decision that has been checked in Preview Form. Do not blindly paste source HTML or indiscriminately flatten meaningful formatting. Unsupported structures require review. Consent terms are not copy-editing opportunities.

Record content ownership beside question ownership and test it: changing a point-of-use heading must leave reusable field/component settings unchanged. Preview and template-record projection must consume the same content binding.
