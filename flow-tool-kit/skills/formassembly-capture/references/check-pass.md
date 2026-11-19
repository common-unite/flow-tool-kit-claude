# Check pass (required after the summaries)

One fresh pass after every `summary.md` is written: a helper agent, or you once all summaries are done, reading them as a skeptic. In real captures this pass found about one claim in five false, all of them plausible, most of them two fields with the same label read as one.

## Task

For every `archive/<id>/summary.md`, find each statement that says something is a bug, broken, inverted, dead, wrong, duplicated, missing or reads the wrong field, and every row of the Rebuild checks table that is not "None found". Also confirm all 11 checks have a row. Check each against:

1. `logic.md` in the same folder (fields that share a name show their section).
2. The captured files when logic.md is not enough: formulas in `connector-*.html` use `%%tfa_NNNN%%`; `aliases.html` (when exported) and `form.html` map ids to fields and sections.

Limit: connector pages keep only the label for most field mappings, so when two fields share a label no capture can prove which one a mapping reads. Such a claim is "unclear", not confirmed and not false. A claim about a connector whose page was not captured is "unclear" too.

For each claim:

| Verdict | Do |
|---|---|
| Confirmed | Leave it; add the field ids if missing |
| False | Rewrite the sentence to describe what actually happens |
| Cannot tell | Reword as "unclear: ..." |

Edit only `summary.md` files. No em-dash and no section-symbol characters.

## Report back

Write the table to `_formassembly/check-pass-report.md` as well as in the reply: form id, claim (short), verdict, evidence (ids or logic.md line). Then the count of claims checked, confirmed, corrected and made unclear.
