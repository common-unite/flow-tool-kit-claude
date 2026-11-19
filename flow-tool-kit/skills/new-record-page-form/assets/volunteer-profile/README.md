# Worked example: the fallback wrapper, a Volunteer Profile on the Contact page

Riverside Community Garden keeps its volunteers as Contacts. Its volunteer coordinator built a small Form Component, **Volunteer Profile**, in Form Builder: How to reach you (Email, Mobile) and About you (Occupation, Notes for the volunteer coordinator). Volunteers fill it in as part of the sign-up form. The coordinator wants the same form on the Contact page, so staff can correct a phone number or add a note, and signed-in volunteers should see and update their own profile on the garden's member site.

Usually that is the package's Form (Component), dropped on the page with the form's name. Here the garden's admin keeps every change in source and deploys from a sandbox, and wants the form to arrive with the code rather than as a Form Component record in each org. On a Lightning record page Form (Component) can only name a saved component, so this is the case for the fallback wrapper: the form baked in, with the record form's Save button. (Had the coordinator asked for each change to save as it is typed, `--autosave` would add autosave and hide the Save button.)

## What is here

| File | What it shows |
|---|---|
| `volunteer-profile.json` | The form as Form Builder saved it (`*__` keys, with the version and section layout keys the save adds, no record Ids), the input to `record_page_form.py` |
| `force-app/main/default/lwc/contactVolunteerProfile/` | The bundle `record_page_form.py write ... --site` produced from it, unchanged |
| `.../contactVolunteerProfile.html` | The package's record form with the page's record, the baked form and `check-record-access`; no `auto-save` or `hide-buttons`, so the Save button shows |
| `.../contactVolunteerProfile.js` | The object fixed as Contact, the record from the page, the form from the config module. No logic |
| `.../contactVolunteerProfileConfig.js` | The form, as readable JSON, turned into the string the record form takes |
| `.../contactVolunteerProfile.js-meta.xml` | Contact record pages only, plus Experience Cloud pages with a Record Id property |
| `.../__tests__/contactVolunteerProfile.test.js` | 5 Jest tests: record and object handed over, the Save button shown and autosave off, the access check, following a record change, the baked form parses and names Contact |
| `jest/`, `jest.config.js` | The stub for the package's record form and the mapping Jest needs |

## How it was made

```bash
python3 scripts/record_page_form.py inspect assets/volunteer-profile/volunteer-profile.json
python3 scripts/record_page_form.py write assets/volunteer-profile/volunteer-profile.json \
    --lwc-dir force-app/main/default/lwc --site
npx sfdx-lwc-jest
```

## Then, in the org

1. Deploy `force-app/main/default/lwc/contactVolunteerProfile`.
2. Lightning: a Contact record, Edit Page, drag **Volunteer Profile** into the main column, Save, Activate.
3. Member site (LWR): FlowToolKit LWR Support in the Theme Footer, the Contact detail page, drag **Volunteer Profile** on, Record Id `{!recordId}`, Publish.
4. Access: staff hold Form Builder Internal User and Edit on Contact's Email, Mobile, Title and Description; members hold Form (Flow User), the same field access in the garden's portal permission set, and their own Contact through a sharing set.
5. Check: change Mobile, press Save, reload: saved. As a read-only user: read only.
