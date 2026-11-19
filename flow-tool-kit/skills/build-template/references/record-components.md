# Record components: how the build creates and extends them

A record Form Component is a component stored as records (Form Component with its sections, fields and rules) instead of metadata. Flow Tool Kit 5.3 and later create one from Form Builder's component JSON with a global method:

```apex
Id componentId = FlowToolKit.FormComponentImport.createRecordComponent(componentJson);
```

The build calls it through anonymous Apex (`scripts/recordcomponents.py`) for every record component the plan owns, **before** it touches the template: a failed call stops the build with the package's own message, and no template changed.

- **All or nothing.** The errors name the missing field or object, or the component that already owns a child name.
- **Same API name, same component.** Calling it again with the same name replaces the component's contents in place (same Id), so every template that uses it shows the change. Design settings left out of the JSON reset. A metadata component of that name is never overwritten.
- **Child names are unique across the org.** Every section, field and rule name starts with the component's name.
- **Where it is used.** A page section points at it in component mode: `FormQualifiedApiName__c` `<name>_v0`, `Form_Component__c` its Id, and `FormConfigJSON__c` `{"formSelectionMode":"component","object":"<object>","formQualifiedApiName":"<name>_v0"}`. A header uses `<name>_v0` in `FormQualifiedApiName_Header__c`. The plain name renders nothing.
- **Who can run it.** Form Builder (Administrator), or Form Builder (Manager) listed in the component's Form Managers to update it. Open a created component in Form Builder through the record's Edit.
- **Without Apex** (claude.ai chat): the same JSON goes in through Form Builder's Form Component **Import** button. The dry run writes each component's JSON.

## Extend: a new version, the original unchanged

When the reuse question was answered **extend** (an existing component plus fields), the build:

1. reads the named component's stored design from the org (its newest version), or from `components[].design_file` when the org's copy cannot be read (export it from Form Builder);
2. copies it under a new name from the template's family, dropping record Ids and version keys and renaming every section, field and rule, with every reference to them rewritten;
3. adds the plan's `add_fields`, with the design the plan gives them, after the last field of its last input section;
4. merges the plan's Form Template Mapping for the added fields into the component's own map;
5. creates it as a record component named `new_name` from the plan (else `<family><id>_<key>`), labelled "<original> with <added fields>", and points the section at it.

The original is never changed, so every template using it keeps it. A rule on a field inside the copy is not built from the plan: put it on the section. If the person wants the original itself to change everywhere it is used, that is `update`, a separate answered question (below).

## Update: the original changed, on purpose

`update` is the other answer: the shared component itself changes, in place, for every template and component that uses it. build-template never makes that change. It checks the plan records the update's own question, answered update and naming everything it reaches, refuses it on a packaged component, points the section at the component as it does for `reuse`, and lists the change as the report's first handoff to build-form-component, which imports the changed design under the same name.

## Shared components

A plan component becomes a record component when its shape is `record` (or, in a plan from before shapes, when it is `shared-new`, `shared-record` or `extend`). A metadata-shaped one is never created here: build-form-component writes and deploys it, and the build binds it by name. In records mode (`intake.build_mode: "records"`) a metadata-shaped component this plan builds is created as a record component instead, under the same name, and marked `built_shape: "record"` for convert-to-metadata. A reused component is never created or copied in either mode, only referenced. A `form-only` component in the record shape is a one-off record component named like the section's own form, filed with the template's components, carrying its field rules; a rebuild updates it in place.

`shared-new` (form-design: a new shared component) and `shared-record` (consolidate-sections' plan route: a promoted section) become one record component built from the section's design, filed in `<folder>/Shared` with the category Component(s), a description, and tags for what it holds. `shared-new` is created only when the org has no component by that name; otherwise the section points at the existing one.

Guests on a site read record components only through a guest sharing rule on Form Component (Read, Record Type Record Component).
