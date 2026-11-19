# Worked example: a public workshop registration form

Invented: Riverside Community Garden runs a guest site, `Riverside_Garden`. Its workshop registration form has a Flow Section, **Form Section | Workshop Picker** (`Form_Section_Workshop_Picker`), that lists open workshops, and the template has Allow Save Progress and the Save Progress email on. Visitors see "You do not have the level of access necessary" when the picker loads. The flow file is in `tests/fixtures/flows/`.

## 1. Diagnose

```bash
python3 scripts/flowaccess.py diagnose --org <org-alias> --flow Form_Section_Workshop_Picker --site Riverside_Garden
```

```
Form_Section_Workshop_Picker (runs: Form_Section_Workshop_Picker, DefaultMode)
  restricted NO  NOT restricted: guests and portal users can never run it, and a grant does nothing until it is
  granted    NO  granted by: nothing; restrict it first
fix the steps marked NO, then test in a new session
```

## 2. What the flow needs for guests

```bash
python3 scripts/flowaccess.py inspect force-app/main/default/flows/Form_Section_Workshop_Picker.flow-meta.xml --audience guest
```

It reports: not restricted; a subflow, `Utility_Check_Workshop_Capacity`, that needs the same two steps; an Apex action, `WorkshopDateFormatter`, whose class needs Apex Class Access; reads of Campaign and Program; one Get that stores every field; and an **Update Campaign** element a guest can never run. The update goes back to build-flow-section: a Flow Section hands values back to the form instead of writing records.

## 3. Steps one and two

```bash
python3 scripts/flowaccess.py restrict force-app/main/default/flows/Form_Section_Workshop_Picker.flow-meta.xml --write
python3 scripts/flowaccess.py restrict force-app/main/default/flows/Utility_Check_Workshop_Capacity.flow-meta.xml --write
sf project retrieve start -m "PermissionSet:Form_Flow_Guest_User" -o <org-alias>
python3 scripts/flowaccess.py grant force-app/main/default/permissionsets/Form_Flow_Guest_User.permissionset-meta.xml \
  --flow Form_Section_Workshop_Picker --flow Utility_Check_Workshop_Capacity --apex WorkshopDateFormatter --write
```

## 4. Guest sharing

```bash
sf project retrieve start -m "SharingRules:Campaign" -m "SharingRules:Program__c" -o <org-alias>
python3 scripts/flowaccess.py sharing-proposal force-app/main/default/flows/Form_Section_Workshop_Picker.flow-meta.xml \
  --site Riverside_Garden --existing force-app/main/default/sharingRules/Campaign.sharingRules-meta.xml
```

```
Campaign (read by getOpenWorkshops, getChosenWorkshop)
  existing rule Guest_Campaign_Active (Read): IsActive equals True
  already covered by Guest_Campaign_Active: Guest_Campaign_IsActive_Type, Read Only, criteria: IsActive equals True; Type equals Workshop (for getOpenWorkshops)
  note: getChosenWorkshop finds Campaign records by a value that changes per person; ...
Program__c (read by Open_Programs)
  no guest rule for site Riverside_Garden in the files given
  propose: Guest_Program_Accepting_Applications, Read Only, criteria: Accepting_Applications__c equals True (for Open_Programs)
```

What Claude says: "Guests see no records without a guest sharing rule. Campaigns are already shared: every active Campaign, which is broader than this picker needs, so check with sf-guest-audit that nothing private is active. Programs are not. I propose one rule: Program, where Accepting Applications is checked, read only. That makes every program taking applications readable by anyone on the internet. Add it?" On yes:

```bash
python3 scripts/flowaccess.py sharing-rule --object Program__c --site Riverside_Garden \
  --name Guest_Program_Accepting_Applications --label "Guest Program Accepting Applications" \
  --criterion Accepting_Applications__c:equals:True \
  --description "Lets the public workshop registration form list programs taking applications. Read only." \
  --out force-app/main/default --write
```

Read on Program and its Name field goes into the guest set too.

## 5. Save Progress and resume

The registration template has Allow Save Progress and the Save Progress email on, so the guest needs both copies. The org has neither (the installer step was skipped). The guest templates' settings come from the query in guest-save-and-resume.md, saved as `guest-templates.json`. Had every guest template submitted once, `guest-copy` would print "not needed, so not built" and the packaged flows would stay.

```bash
sf project retrieve start -m "Flow:FlowToolKit__Form_Submission_Upsert" -m "Flow:FlowToolKit__Form_Submission_Prefill" \
  --output-dir packaged-source -o <org-alias>
sf project retrieve start -m "CustomField:FlowToolKit__Form_Template__c.FlowToolKit__Prefill_Flow_Api_Name__c" -o <org-alias>
python3 scripts/flowaccess.py guest-copy upsert packaged-source/flows/FlowToolKit__Form_Submission_Upsert.flow-meta.xml \
  --templates guest-templates.json --out force-app/main/default --write
python3 scripts/flowaccess.py guest-copy prefill packaged-source/flows/FlowToolKit__Form_Submission_Prefill.flow-meta.xml \
  --templates guest-templates.json --out force-app/main/default --write
python3 scripts/flowaccess.py grant force-app/main/default/permissionsets/Form_Flow_Guest_User.permissionset-meta.xml \
  --flow Form_Submission_Upsert_Guest --flow Form_Submission_Prefill_Guest --write
```

Add the `Form_Submission_Prefill_Guest` value to the Prefill Flow field file (every existing value kept), and deploy the two flows, the permission set and the field. The copies arrive inactive. Before asking, Claude says: "Once this override is active, every save in the org runs through it in system mode: guests, portal users and staff, on every form, not only this one." Then what each copy exposes (guest-save-and-resume.md), and on the person's yes activates both, grants the save override in the staff and portal sets as well, and sets Prefill Flow on the registration template.

## 6. Check

In a new private window: the picker lists open workshops and programs, Save Progress saves twice, the emailed link opens the draft in another new private window, and the form submits. Change list for the person:

- Workshop Picker and its capacity subflow now require permission to run; Form Flow (Guest User) grants both and the date formatter class.
- New guest rule: Program, Accepting Applications equals True, read only.
- New and active: (Form) Upsert | Guest Override and (Form) Prefill | Guest Resume, both in system context, granted to guests (the override also to staff and portal sets); the registration template's Prefill Flow is the resume copy.
- Left for build-flow-section: remove Update Campaign from the picker.
