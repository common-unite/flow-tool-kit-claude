# Worked example: a fee summary card under the admin's form

Riverside Community Garden registers members for garden plots with a Form Template, Garden Plot Registration. The Plot Details page section asks three questions the admin built in Form Builder: Plot size (Small, Standard or Raised Bed), How many plots?, and I qualify for the senior or student rate. The garden wants the fee shown as the person answers, and saved on the submission.

No Flow Tool Kit control calculates a fee from a rate table as the person types, and a Flow Section would rebuild the questions in a flow. So the section becomes a custom LWC section: the admin's three questions stay in Form Builder, and the component adds only the fee card under them.

```
Plot Details (page section, Component Type: Lightning Web Component, c:feeSummarySection)
  [ the admin's form: Plot size | How many plots? | senior or student rate ]   <- rendered by <FlowToolKit-flow-form is-extension>
  +--------------------------------------------+
  | Your plot fee                              |
  | 2 x Standard plot                  $80.00  |                               <- styled with --ftk- variables
  | Senior or student rate            -$40.00  |
  | ------------------------------------------ |
  | Total due                          $40.00  |
  +--------------------------------------------+
```

## What is here

| File | What it shows |
|---|---|
| `lwc/feeSummarySection/feeSummarySection.js` | The contract: all seven inputs, one `formfieldchange` per field (bubbles, composed), the admin's form given a copy of the record that changes only with a value, the fee sent only when it changes and handed back through the transformation record, read-only in review, `@api validate()` that runs the admin's checks first |
| `lwc/feeSummarySection/feeRules.js` | The part that is genuinely code: the rate table and the arithmetic, testable on its own |
| `lwc/feeSummarySection/feeSummarySection.html` | `<FlowToolKit-flow-form is-extension>` with both form attributes, then the card |
| `lwc/feeSummarySection/feeSummarySection.css` | Only Form Style variables, each with the package's own fallback chain |
| `lwc/feeSummarySection/__tests__/` | 15 Jest tests: both surfaces, the events, both loop guards (resending the fee, rebuilding the form's record), review mode, validation |
| `lwc/customSectionsLwrSupport/` | The LWR site support component: imports the section component so the site bundles it |
| `objects/FlowToolKit__Form_Submission__c/fields/` | The four answer fields, each with its description |
| `labels/CustomLabels.labels-meta.xml` | Every word the card shows, translatable |
| `permissionsets/Garden_Plot_Registration` | The field grants the form's users, reviewers and the guest user need. In a real org, add them to the permission sets the admin names rather than creating this one |
| `jest/`, `jest.config.js` | The stub for the package's form and the mapping Jest needs |

## The same component on both surfaces

- **Page section:** the section names its form (`FlowToolKit__FormQualifiedApiName__c` or `FlowToolKit__FormConfigJSON__c`), so the component renders it and the card under it, and also hands the total to the form through `transformation-record` in case the admin placed a read-only Plot fee field on it.
- **Form Component section:** there is no section record. Place the section under the sections that ask the three questions; the component shows only the card, reading the answers from the form's live record.

## Use it as a starting point

1. Copy the bundle into the project's `force-app/main/default/lwc/` under the new component's name, and rename the class, files and labels.
2. Replace `feeRules.js` with the new behavior and the field imports with the new fields. Keep the event, read-only, loop-guard and validate shapes as they are.
3. Rewrite the Jest tests for the new behavior; keep the contract tests (bubbles and composed, one event per change, nothing sent in review).
4. `python3 scripts/check_lwc.py force-app/main/default/lwc/<name>` until it reports no errors.

## What it deliberately does not do

- It does not keep the rates anywhere an admin can edit. When they change often, move them to custom metadata read by a cacheable Apex method, and grant the class and the metadata type to every audience: `references/examples.md` shows it, and `references/deploy-and-place.md` the grants.
- It does not charge anything. Plot fee is what the person was shown; recalculate it before payment.
