# Pitfalls

These are recorded from real builds of custom section components on Flow Tool Kit. Most fail without any message, or are easy to miss. Each row gives the symptom, the cause and the fix. The ones `scripts/check_lwc.py` catches are marked **checked**.

## The contract

| Symptom | Cause | Fix |
|---|---|---|
| The component looks fine but the form never gets the value | The event lacks `composed: true` (or `bubbles: true`) and stops at the renderer's shadow root | Send both, always. **Checked** |
| Works on a page section, does nothing in a Form Component section | The detail names the field `fieldName`; only page sections accept it | `fieldApiName`. **Checked** |
| Child rows never appear | `relatedrecordchange` sent from a Form Component section, where nothing listens | Child rows need a page section |
| Rows duplicate, or saved rows vanish without being deleted | The component edited `relatedRecords` itself | Send `add`, `update` or `remove` and let the section do the rest. **Checked** for in-place array changes |
| "Cannot assign to read only property" | Writing to `record`, `section` or a row | Copy first (`{...this.record}`), change the form through events. **Checked** |
| Two fields sent in one event, one is lost | The form takes one field per event | One `formfieldchange` per field |
| A calculation stops updating in a Form Component section | It runs in an `@api set record()` setter; that surface changes the record in place, so the setter never runs again | Derive in getters, react in `renderedCallback` |
| The page freezes, or the console reports a render loop | The component sends a value, the form hands it back, the component sends it again | Send only when the value differs from `record` and from the last value sent |
| The page freezes after one failed check | `validate()` assigns a new object or array to something the template reads; after a failed check a Form Component section revalidates on every render | Compare before assigning, or keep the result in a primitive |
| `validate()` never runs | It is not `@api` | `@api validate()`. **Checked** |
| An error shows as a vague "needs attention" line | `validate()` returned only `isValid: false` | Add `errorMessage`, and `invalidItems` for one summary line per problem |
| A required question hidden by a rule does not block the page | Hidden fields leave the page, so the form's `validate()` skips them | Expected: required means required while shown |
| Values written in review mode | The component ignores `review` and `disableAll` | Show values read-only and send nothing in either mode |
| `LWC1503` on an `@api` Boolean | A public Boolean initialized to `true` | Default it to `false` or leave it undefined and test `!== false` |
| `LWC1107` on a property | A public property name starting with `data` | Rename it (`valueLabels`, not `dataLabels`) |

## Names and namespaces

| Symptom | Cause | Fix |
|---|---|---|
| "Component 'feeSummarySection' could not be loaded" | A bare name | The full name: `c:feeSummarySection` |
| Loads in one org, not another | The other org has a namespace (a partner's own packaging org, say) | `ns:feeSummarySection` there. Check `SELECT NamespacePrefix FROM Organization` before writing any name |
| `record` lacks the field the code reads | Packaged fields carry `FlowToolKit__` in an org with the package; your own fields carry your namespace in a namespaced org | Import field names from `@salesforce/schema` and use `.fieldApiName`. The platform supplies the right prefix, and a wrong name fails the deploy instead of the form |
| `import ... from 'FlowToolKit/...'` fails to deploy | The package's JavaScript and style modules are not exposed | Use only the `<FlowToolKit-flow-form>` tag and the style variables. **Checked** |
| Jest: "Cannot find module 'flowtoolkit/flowForm'" | The package's form exists only in an org, and the compiler lowercases the namespace | Map `^flowtoolkit/flowForm$` to a stub, as the worked example's `jest.config.js` does |

## The admin's form inside the component

| Symptom | Cause | Fix |
|---|---|---|
| The section's record page freezes in the admin's preview | The record was bound straight to the wrapped form; the preview rebuilds it on every broadcast, the form reruns its rules and broadcasts again | Give the form a copy, replaced only when a value differs (the worked example's `formRecord`). **Checked** (warning) |
| The inner form is empty | The section names no form: the section editor hides its form picker for this Component Type | Choose the form while the section is a Field Set, then switch the type (the form is kept), or `scripts/point_section.py --form` |
| The inner form is empty for a form-only section | Only `form-qualified-api-name` was passed; this section keeps its form in `FlowToolKit__FormConfigJSON__c` | Pass `form-j-s-o-n` as well. **Checked** |
| The component hears no edits from the inner form | `is-extension` missing, so the form reports to Flow instead | Add it. **Checked** |
| A derived value never shows in the inner form | The same object was reassigned, or the value was set before the form rendered | Assign a new object for each change, from `renderedCallback` or a change handler |
| A value cleared through `transformation-record` comes back | The form keeps the values of hidden fields and restores them | Leave hidden values alone; clear them in the conversion if they must not be saved |
| A saved value is wiped when the page opens | The component derived a value before its lookup data (rates, a roster) loaded, and sent "nothing" | Send nothing until the data has loaded |
| Hand-built inputs drift from the rest of the form | They ignore Form Builder's labels, widths, help, rules and styles | Render the admin's form; code adds behavior. **Checked** (warning) |
| A typed value saves on every keystroke and the cursor jumps | A widget's own text input sends on `change` | Send typed values on blur, only when changed; send choices on change |

## Access and data

| Symptom | Cause | Fix |
|---|---|---|
| New fields deploy, then the form renders blank, a query says "No such column", and form fields or rules that use them seem to vanish | Fields deploy with no field-level access, even for the admin who deployed them; without it every describe, query and the form engine skip them | Grant access in the same deploy and assign it at once: to the deploying admin, staff reviewers, portal users and the site guest |
| Works for the admin, blank for a reviewer | The reviewer's permission sets lack the fields | Add the fields to the permission set the person names for that audience |
| A deploy removes access other teams added | A local permission set file overwrote the org's copy | Retrieve the org's copy first and add to it |
| A new permission set nobody assigns | One was invented for the build | Ask which existing permission sets get the grants; create one only when told to |
| A guest sees blanks or "insufficient access" | No field, Apex class or custom metadata access for the guest user | Grant every one; **flow-access-fix** for guests |
| An Apex wrapper parameter arrives with every field null | The typed wrapper deserializer drops its fields | Pass `JSON.stringify(...)` and `JSON.deserialize` it in Apex |
| An empty roster for guests "fixed" with system mode | The Apex now shows data the person may not see | Keep `with sharing` and `WITH USER_MODE`; give the guest a sharing rule on purpose |
| A page-section component misses an answer given in another section on the same page | The page section keeps its own copy of the record once it has reported a change (read in the package source; confirm in your org) | Put the questions the calculation needs in the section's own form, or read them on a later page |
| A browser-calculated fee is trusted | Anything the browser sends can be changed | Recalculate it in the conversion flow or before payment, and write it to the field the payment step reads |

## Sites, devices and caching

| Symptom | Cause | Fix |
|---|---|---|
| Works in Preview Form, "could not be loaded" on an LWR site | The site's publisher never bundled a component loaded only by name | A support component that imports it, in the Theme Footer beside FlowToolKit LWR Support, then publish |
| A deployed change does not show on an LWR site | The site serves its last publish | Publish after every component change and every package upgrade |
| A deployed change does not show in Lightning, even after a hard reload | Lightning keeps serving the previous build for several minutes | Wait a few minutes before deciding a fix failed; in a sandbox you iterate in, turn off "Enable secure and persistent browser caching" |
| No custom section loads anywhere in the org | Lightning Web Security is off | Turn it on, after asking: it affects every component in the org |
| The component breaks in internal Lightning but works on the site | It imports `@salesforce/community/Id` | Read the site context another way |
| The layout is wrong in a narrow column on a desktop | It used `@salesforce/client/formFactor`, which reports the device, not the space | Measure the component's own width |
| A third-party library never loads | It was loaded from a CDN | A static resource and `loadScript`, never a CDN |
| Tested as an admin, broken for the public | Admin access hides guest gaps | Test as the real guest on the site, on each site type the form is on |

## Style

| Symptom | Cause | Fix |
|---|---|---|
| The card ignores the template's brand | Hard-coded colors | `var(--ftk-color-primary, <fallback>)` |
| The card has no border or the wrong font in an org with no Form Style settings | A variable used with no fallback | Always a fallback. **Checked** |
| The look breaks after a package upgrade | A private `--_ftk-` name or an internal `--ftk-` name from the inspector | Only the Form Style settings in [style-variables.md](style-variables.md). **Checked** |
| Text is enormous | A scale setting used as a length | `calc(1rem * var(--ftk-font-scale, 1))` |
| The admin's color looks wrong | The component darkened, lightened or mixed it | Use an admin's color exactly; when it is unreadable as text, use plain dark or white text and keep the color for fills and borders |
| A component recolors the whole template | It tried to set the template's brand from its own data | Keep a component's colors inside its own card |
| A rich text field shows `&amp;` and tags | It was printed with `{value}` | `lightning-formatted-rich-text` |
