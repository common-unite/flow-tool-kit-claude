# The section contract

How Flow Tool Kit hosts a custom Lightning web component, read from the package source (release 5.3). Your component talks to the form through public properties and plain events only: nothing to import from the package, no base class, no package version to depend on.

## Two surfaces, one renderer

Both surfaces load your component by name through the package's section renderer, which imports it when the section first shows and passes the same properties down. A component that declares every input below works in both.

| | Form Component section | Form Template page section |
|---|---|---|
| Where the admin sets it | Form Builder: Insert Section, **Lightning Web Component**, then the **LWC Component** name | The page section's Component tab: Component Type **Lightning Web Component**, then **LWC Component Name** |
| Stored as | Section type `lwcSection`, name in `lwcComponentName__c` (in the component's JSON or metadata) | `Component_Type__c` = `Lightning Web Component`, name in `lwcComponentName__c` on the page section |
| `record` is | The form's record, whatever object the form is on | The Form Submission |
| Sits among | The form's other sections, which collect the answers | Other page sections; the component draws its own section |
| Related records, `section` | Not available (defaults) | Available |
| Header, intro text, frame, conditional logic, widths | The section's own settings | The page section's settings (titles live there, never inside your component) |

The name is always the full name: `c:feeSummarySection` in an org with no namespace, `ns:feeSummarySection` in an org with namespace `ns`. A bare `feeSummarySection` never loads, and the section shows "Component 'feeSummarySection' could not be loaded".

## Inputs

Set by the form. Treat every one as read-only: they arrive wrapped in Lightning's read-only proxy. Copy before changing (`{...this.record}`), and change the form's data only through the events below.

| Property | Type | Surface | What it holds |
|---|---|---|---|
| `record` | Object | both | The current record, keyed by field API name, packaged fields with `FlowToolKit__`. Updated on load and on every change |
| `objectApiName` | String | both | The object the form works on |
| `review` | Boolean | both | True on the review page |
| `disableAll` | Boolean | both | True when the form is read-only |
| `relatedRecords` | Array | page sections | This section's child Form Submission rows, already filtered to the section, with rows marked for deletion removed |
| `recordTemplate` | Object | page sections | A blank child row with every key a new row needs |
| `section` | Object | page sections | The page section record as the admin configured it, keyed by API name: `FlowToolKit__FormQualifiedApiName__c`, `FlowToolKit__FormConfigJSON__c`, `FlowToolKit__Section_Tag__c` and the rest. Passed down, so a guest needs no access to the section object |

On a Form Component section the last three keep their defaults (`[]`, `{}`, `{}`). Declare all seven with those defaults.

**How `record` changes differs by surface.** A page section hands down a new object after each change. A Form Component section changes the same object in place: your template re-renders, but an `@api set record()` setter is not called again. Derive values in getters and act on changes in `renderedCallback`, never only in a setter (the worked example does this).

## Outputs

| Event | Detail | Surface |
|---|---|---|
| `formfieldchange` | `{ fieldApiName, value }` | both |
| `relatedrecordchange` | `{ action: 'add' \| 'update' \| 'remove', record }` | page sections |

Both are sent with `bubbles: true` **and** `composed: true`. Your component sits inside the renderer's shadow root; without `composed` the event stops at the first boundary, and nothing throws or logs.

`formfieldchange`:
- One event per field. Batching several fields into one event is not supported.
- Name the field `fieldApiName`. A page section also accepts `fieldName`, a Form Component section does not.
- Send `null` for a cleared value. A Form Component section turns empty strings into `null`; a page section passes them through.
- The form treats it like a person's edit: validation, formulas, conditional logic, autosave and the record output all follow. On a Form Component section, add `triggerFormulaRecalculation: true` to the detail to recalculate the form's formula fields at once.

`relatedrecordchange` (page sections only; on a Form Component section nothing listens and the event is lost):
- **add**: send only your own fields; `recordTemplate` goes underneath and the keys are generated. Adding an existing row makes a copy.
- **update**: spread the row and change what you need: `{ ...row, Diet__c: 'Vegetarian' }`. The row is matched on `_Id`, then the upsert key, then `Id`.
- **remove**: hand the row back. An unsaved row disappears; a saved row is marked and deleted when the submission's conversion next runs.
- `_Id` is the stable key for a row across renders. Your changes only ever touch your own section's rows.

## `validate()`, optional

```javascript
@api validate() {
    return { isValid: false, errorMessage: 'Choose a shift for every volunteer', invalidItems: [{ label: 'Shifts', text: 'Choose a shift for every volunteer' }] };
}
```

The form calls it when the person moves on. `isValid: false` blocks the page. `invalidItems` (`{ label, text }`) lists one line each in the template's validation summary; without them the section shows as one line with `errorMessage`. Without `validate()` the section always counts as valid. A Form Component section skips a section hidden by conditional logic. The method must be public (`@api`).

## Prerequisites in the org

- **Lightning Web Security** on (Setup, Session Settings). Loading a component by name needs it; under Lightning Locker the section cannot load your component.
- The component deployed to the same org, and `isExposed` true: the renderer lives in Flow Tool Kit's namespace and loads yours from another.
- Field access for every field the component reads or writes, for every audience (guest, portal, internal): see [deploy-and-place.md](deploy-and-place.md).

## What the section shows when something is wrong

| Situation | The section shows |
|---|---|
| No component name | "LWC Component Name is not configured for this section" |
| A name that does not load (not full, not deployed, not exposed, Locker on, an LWR site that never bundled it) | "Component 'c/name' could not be loaded" |
| The component throws while rendering | Lightning's own error handling; the rest of the form keeps working |
