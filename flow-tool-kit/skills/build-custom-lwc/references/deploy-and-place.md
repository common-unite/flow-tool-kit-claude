# Deploy, place and check

Deploying needs **Claude Code** (local or on the web) with the Salesforce CLI and a project folder. claude.ai chat can design the component, write every file and run `scripts/check_lwc.py` in its sandbox, but it cannot deploy a Lightning web component: hand the person the files and say that the deploy step needs Claude Code.

## 1. Before the first deploy

- **Lightning Web Security** is on in the org (Setup, Session Settings, "Use Lightning Web Security for Lightning web components"). Turning it on affects every component in the org: when it is off, ask the person before changing it.
- **The project.** The bundle goes in the project's own `force-app/main/default/lwc/<name>/`. Fields, labels and the permission set go beside it, as in the worked example.
- **Pull before you deploy.** Retrieve any file the deploy would overwrite (`sf project retrieve start --metadata LightningComponentBundle:<name> --target-org <org-alias>`), so a teammate's change in the org is not lost.

## 2. Test locally, then deploy

```bash
python3 <skill>/scripts/check_lwc.py force-app/main/default/lwc/<name>
npx sfdx-lwc-jest -- force-app/main/default/lwc/<name>
sf project deploy start --source-dir force-app/main/default/lwc/<name> --target-org <org-alias>
```

Jest needs `@salesforce/sfdx-lwc-jest` in the project and a stub for the package's form, because the real one exists only in an org: copy `assets/fee-summary-card/jest/` and the `moduleNameMapper` line from `assets/fee-summary-card/jest.config.js`. The template compiler lowercases the namespace, so the stub is mapped as `flowtoolkit/flowForm`.

Deploy fields and labels before the component that imports them: an import of a field the org does not have fails the deploy, which is the point of importing field names from `@salesforce/schema` rather than typing strings.

## 3. Access, for every audience

The form reads and writes as the person filling it in. Grant access in the same deploy as any new field: a field nobody has access to is hidden even from the admin who deployed it, so queries say "No such column", the form renders blank, and form fields and rules that use it seem to vanish.

**Ask which permission sets get the grants.** List the permission sets that already grant Form Submission field access in the org, with their assignments, and ask which ones to add to, per audience. Create a new permission set only when the person says so: an org's permission sets are a deliberate design, and a new one has to be found and assigned. The worked example's permission set stands for the grants, not for a set to create.

| What | Grant |
|---|---|
| Every field the component reads or writes | Read, and Edit for fields it writes, for each audience the project config lists (guest, portal, internal), plus the deploying admin and staff reviewers |
| An Apex class the component calls | Apex class access, same audiences |
| A custom metadata type it reads | Custom metadata type access, same audiences |
| The Flow Tool Kit objects and packaged fields | Already granted by the package's own permission sets; do not grant them again |

Before deploying a permission set, retrieve the org's copy and add to it; a local file deployed over it removes grants other work added.

**Apex the component calls** is `with sharing`, queries `WITH USER_MODE`, and is `@AuraEnabled(cacheable=true)` when it only reads. It takes structured input as a JSON string (`JSON.deserialize` in Apex), because a typed wrapper parameter can arrive with every field null. It ships with a test class. System mode only when reading data the person may not see is the point, with a comment saying why and the person's agreement; never to make an empty result appear for a guest.

For guests, run **flow-access-fix** after the deploy: it checks the guest user's sharing and access end to end, and test as the real guest on the site, never as an admin.

## 4. Point the section at the component

- **Page section:** Component Type **Lightning Web Component**, LWC Component Name `c:<name>`. build-template has already set these when it handed the section over; otherwise `scripts/point_section.py` does it, and also stores the admin's form ([house-pattern.md](house-pattern.md)).
- **Form Component section:** in Form Builder, Insert Section, **Lightning Web Component**, then the LWC Component name. For a component built as JSON (build-form-component), the section is `"*__sectionType__c": "lwcSection"`, `"isLwcSection": true`, `"*__lwcComponentName__c": "c:<name>"`.

## 5. Experience Cloud LWR sites

The form loads your component by name only, and an LWR site's publisher includes only components it can reach by a static reference. So on an LWR site your component is missing ("could not be loaded") until something on the site imports it:

1. Deploy a support component that imports each custom section component and renders nothing: `assets/fee-summary-card/force-app/main/default/lwc/customSectionsLwrSupport/`, with one `import 'c/<name>';` line per component.
2. In Experience Builder, put it in an empty column of the **Theme Footer**, beside Flow Tool Kit's own **FlowToolKit LWR Support** (which every LWR site with a form needs).
3. **Publish** the site. An LWR site serves what was last published: every later change to the component, and every Flow Tool Kit upgrade, needs another publish.

Aura sites load components on request and need neither step.

## 6. Check it in the org

A component is not done until each of these is seen, not assumed:

1. **The template's Preview Form**, desktop and phone width: the section renders, the admin's form inside it is styled like the other sections, and the card follows a change to the Brand color and the section corner radius in the template's Style Overrides.
2. **Each surface it is placed on**, and each audience: a guest on the site page, a portal user, an internal user.
3. **The data:** submit once and read the Form Submission back: every field the component writes holds the value shown.
4. **Review and read-only:** the review page shows the values and writes nothing.
5. **Validation:** a case `validate()` refuses blocks the page and shows its line in the validation summary.

Lightning can keep serving the previous build of a component for a while after a deploy. Before deciding a change did not work, reload with the cache cleared; in a sandbox you are iterating in, turn off "Enable secure and persistent browser caching" in Session Settings. A headless browser in Claude Code can do the preview checks; otherwise list them for the person.
