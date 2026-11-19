# Guest sharing: what a guest may read

## How guest record access works

- A site guest sees **no record** of any object until a **guest sharing rule** shares it. The object's sharing model does not change that: Salesforce keeps guest access private.
- A guest rule is **criteria based** and **read only**, and it shares with one site's guest user (`<sharedTo><guestUser>` is the site's `Name`).
- Rules add up: a record any rule shares is visible. Within one rule, every criterion must hold.
- A rule is not enough alone: the guest's set also needs Read on the object and on each field the flow or form shows or filters on.
- **A guest rule makes those records readable by anyone on the internet**, not only through your form. Share exactly the records the form needs, and say so in those words when proposing one.

## When to check

Every time a guest flow or form reads records:
- a Flow Section or site flow with Get Records or a record choice set (open shifts, upcoming events, public Campaigns, programs taking applications, locations);
- a form's lookup or Record Picker (its Accounts, Programs, Campaigns);
- the form itself (the package's rules below);
- a flow in system context reads without sharing: the rule still matters for everything else the guest reads.

## The package's own guest rules

| Object | Criteria | When |
|---|---|---|
| Form Template | Active (`FlowToolKit__IsActive__c`) equals True | Every guest form. Without it the form does not load |
| Form Submission | Is Pre-fill Template (`FlowToolKit__IsPrefillTemplate__c`) equals True | Only templates with a Pre-fill Template. Key it on that checkbox, never on a record type. Without it the form opens without its default answers |
| Form Component | Record Type (`RecordTypeId`) equals Record Component | Templates that use record components, created headers included. Without it the header or section is blank |

These three are the only Flow Tool Kit records a guest reads through sharing. **Never share any other Form Submission with guests**: a guest reopens its own draft only through the resume copy ([guest-save-and-resume.md](guest-save-and-resume.md)).

## Proposing the rule from what the flow reads

```bash
python3 scripts/flowaccess.py sharing-proposal <flow file> --site <Site_Name> --existing <retrieved sharingRules files>
```

It groups the flow's reads by object and:
1. Takes each read's **fixed filters** as criteria (Active equals True, Status equals Open, Type equals Workshop). Those already describe exactly the records the flow shows, so they are the narrowest honest rule.
2. Proposes **one rule per distinct set of criteria**, dropping any that a broader one already covers.
3. Marks a proposed rule **already covered** when an existing rule for the same site shares the same records or more.
4. Notes a read that finds records by a value that changes per person (`Id equals {!record.Campaign__c}`): it finds only what the other rules share, which is right when the record is always one the form offered.
5. **Asks** when no read has a fixed filter: never propose sharing every record. Suggest a field that marks the public records (a Show on Website checkbox, a Public picklist value) and build the rule on it.
6. Lists the fields the guest set needs Read on, and warns when a Get stores every field.
7. Refuses Form Submission (Pre-fill Templates aside).

What a rule's criteria cannot do, and what to propose instead:
- **A value that changes per person** (the current record, the guest's own answer): share the set it comes from.
- **Relative dates** (today, next 30 days): share by a stable marker (Status, Active), and keep the date filter in the flow.
- **A formula**: a field Setup does not offer in the criteria list cannot be used; add a checkbox or picklist that the flow and the rule both use.
- **Custom filter logic (OR)** in the Get: one rule per branch, since rules add up.

## Checking the org for a rule

- **Claude Code:** `sf project retrieve start -m "SharingRules:<Object>" -o <org-alias>` and pass the file to `--existing`.
- **Chat:** no query reaches sharing rules. Ask the person to open Setup, Sharing Settings, the object's Sharing Rules list, and read the guest rules for the site (name, criteria, access); or ask for a screenshot.

## Writing the rule

On the person's yes:

```bash
python3 scripts/flowaccess.py sharing-rule --object Campaign --site Riverside_Garden \
  --name Guest_Campaign_Workshops --label "Guest Campaign Workshops" \
  --criterion IsActive:equals:True --criterion Type:equals:Workshop \
  --description "Lets the public workshop registration form list active workshop Campaigns. Read only." \
  --out <project-dir>/force-app/main/default --write
```

It merges into the retrieved file (other rules kept; the same name replaced), always Read Only, and refuses a rule with no criteria. Values are written as Setup shows them: `True` for a checkbox, the value's API name for a picklist, the record type's name for `RecordTypeId`. Give it a description that names the form it serves (`_shared/standards/documentation.md`). Deploy it; Salesforce then recalculates sharing, which on a large object can take a while before the guest sees the records. In chat, give the clicks in [setup-clicks.md](setup-clicks.md).

## Worked proposals (invented)

| The guest flow reads | Proposed rule |
|---|---|
| Active Campaigns of type Workshop, for a registration picker | Campaign: Active equals True, Type equals Workshop. Read Only |
| Programs where Accepting Applications is checked | Program: Accepting Applications equals True. Read Only |
| Volunteer shifts by date, from today | Shift: Status equals Open. Read Only. The flow keeps "Start on or after today" |
| One Account, the one chosen in a Record Picker | The picker's list: Account: Show in Partner Directory equals True. Read Only. Never all Accounts |
| The guest's own submission | Refuse. Resume copy instead |

## When a rule is the wrong answer

If the screen needs one value from a record no guest should read (a seat count, whether a code is valid), do not share the record. The last resort is a small autolaunched subflow in system context that takes the one input and returns only the one value the screen shows, restricted and granted like any guest flow, with a description saying why it runs in system context and what it returns. Never return whole records to a guest, and never look records up by a value the guest typed.

To check the other direction, what guests can read that they should not, use sf-guest-audit.
