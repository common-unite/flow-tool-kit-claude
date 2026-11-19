# More worked examples

The full, tested example is the fee calculator in [../assets/fee-summary-card/](../assets/fee-summary-card/README.md). The examples below are shorter: each shows the one thing it adds, for an invented organization. Copy the fee summary card's shape (inputs, events, read-only modes, the resend guard, tests) and take only the new part from here. Every field name here is invented; in a real org, import each one from `@salesforce/schema` as the card does.

## 1. Fee calculator with the rates in custom metadata

The card keeps its rates in JavaScript, so a rate change needs a deploy. When the garden office changes rates every season, keep them in a custom metadata type an admin edits (`Plot_Rate__mdt`: `Plot_Size__c`, `Annual_Rate__c`) and read them through Apex.

```apex
public with sharing class PlotRateController {
    @AuraEnabled(cacheable=true)
    public static Map<String, Decimal> rates() {
        Map<String, Decimal> rateBySize = new Map<String, Decimal>();
        for (Plot_Rate__mdt rate : Plot_Rate__mdt.getAll().values()) {
            rateBySize.put(rate.Plot_Size__c, rate.Annual_Rate__c);
        }
        return rateBySize;
    }
}
```

```javascript
import rates from '@salesforce/apex/PlotRateController.rates';

rateBySize;
@wire(rates)
wiredRates({ data, error }) {
    if (data) this.rateBySize = data;
    else if (error) this.rateError = true;
}

syncFee() {
    // Until the rates arrive every fee looks incomplete, and sending that would clear a fee already saved.
    if (this.isReadOnly || !this.rateBySize) return;
    // ...the card's guard and send, unchanged
}
```

Adds to the outputs: the Apex class and its test class, **Apex class access** and **custom metadata type access** for every audience (guest included), and a rate table an admin can change without a deploy.

## 2. Roster-driven picker (options from org data)

A youth soccer league's registration asks the family to choose a coach, but only coaches with open spots this season. Flow Tool Kit's picklists are static. Climb the ladder first: a **Record Picker** on a Coach lookup with a filter covers "coaches for this season". Build a component only when the list needs logic a filter cannot express, such as the open spots counted from other registrations.

```apex
public with sharing class CoachRosterController {
    @AuraEnabled(cacheable=true)
    public static List<RosterOption> openCoaches(String season) {
        List<RosterOption> options = new List<RosterOption>();
        for (Contact coach : [
            SELECT Id, Name, Open_Spots__c FROM Contact
            WHERE Coach_Season__c = :season AND Open_Spots__c > 0
            WITH USER_MODE ORDER BY Name LIMIT 200
        ]) {
            options.add(new RosterOption(coach.Name, coach.Id));
        }
        return options;
    }

    public class RosterOption {
        @AuraEnabled public String label;
        @AuraEnabled public String value;
        RosterOption(String label, String value) {
            this.label = label;
            this.value = value;
        }
    }
}
```

```javascript
import openCoaches from '@salesforce/apex/CoachRosterController.openCoaches';
import SEASON from '@salesforce/schema/FlowToolKit__Form_Submission__c.Season__c';
import COACH from '@salesforce/schema/FlowToolKit__Form_Submission__c.Coach__c';

options = [];
get season() {
    return (this.record || {})[SEASON.fieldApiName];
}
// Does not run until Season has a value.
@wire(openCoaches, { season: '$season' })
wiredCoaches({ data, error }) {
    if (data) this.options = data;
    else if (error) this.loadError = true;
}
get coach() {
    return (this.record || {})[COACH.fieldApiName] || null;
}
handleCoachChange(event) {
    this.dispatchEvent(new CustomEvent('formfieldchange', {
        detail: { fieldApiName: COACH.fieldApiName, value: event.detail.value || null },
        bubbles: true,
        composed: true
    }));
}
```

```html
<!-- custom-lwc: allow-inputs (Flow Tool Kit has no control for options computed from org data) -->
<lightning-combobox label={label.coach} options={options} value={coach}
        disabled={isReadOnly} onchange={handleCoachChange}></lightning-combobox>
```

- The rest of the section (season, the child's details) stays the admin's form, rendered as in the card.
- A choice is a deliberate single selection, so it is sent on change. A typed value would be sent on blur.
- **Guests.** `with sharing` and `WITH USER_MODE` mean a guest sees only the Contacts a guest sharing rule shares, and only the fields they can read. Choose that on purpose with the person. Do not reach for system mode to make an empty list appear.
- The spot may be gone by the time the form is submitted, so check it again in the conversion flow.
- Pass anything structured to Apex as a JSON string and `JSON.deserialize` it. A typed wrapper parameter can arrive with every field null.

## 3. Volunteer shift selector (child rows)

A food bank's volunteer sign-up lets one person sign up a group: one row per volunteer, each with a shift chosen from a grid that shows which shifts are full. Each row is a child Form Submission of this page section, so this needs a **page section**: a Form Component section has no child rows. If the rows needed more than a name and a shift, a Repeater section would draw them from the admin's form, and the component would keep only the shift grid.

```javascript
import VOLUNTEER_NAME from '@salesforce/schema/FlowToolKit__Form_Submission__c.Volunteer_Name__c';
import SHIFT from '@salesforce/schema/FlowToolKit__Form_Submission__c.Shift__c';

get rows() {
    return (this.relatedRecords || []).map(row => ({
        key: row._Id || row.Id,
        row,
        name: row[VOLUNTEER_NAME.fieldApiName] || '',
        shift: row[SHIFT.fieldApiName] || ''
    }));
}

changeRows(action, record) {
    this.dispatchEvent(new CustomEvent('relatedrecordchange', {
        detail: { action, record },
        bubbles: true,
        composed: true
    }));
}

handleAdd() {
    this.changeRows('add', { [SHIFT.fieldApiName]: null });
}
handleShiftChoice(event) {
    const { row } = this.rows.find(item => item.key === event.target.dataset.key);
    this.changeRows('update', { ...row, [SHIFT.fieldApiName]: event.target.value });
}
handleRemove(event) {
    const { row } = this.rows.find(item => item.key === event.target.dataset.key);
    this.changeRows('remove', row);
}

@api validate() {
    const missing = this.rows.filter(item => !item.shift);
    if (!missing.length) return { isValid: true };
    return {
        isValid: false,
        errorMessage: SHIFT_REQUIRED,
        invalidItems: missing.map(item => ({ label: item.name || NEW_VOLUNTEER, text: SHIFT_REQUIRED }))
    };
}
```

- Send only your own fields. The section adds `recordTemplate` underneath, the keys, the parent, the page and the section.
- Update by spreading the row, so its keys survive. Remove by handing the row back.
- A removed row that was already saved is deleted the next time the submission's conversion runs, not at once.
- Shift capacity read in the browser is a hint: two people can take the last spot at the same moment. Check it again in the conversion flow.

## 4. The full contract in one skeleton

Flow Tool Kit's documentation names a reference implementation, `demoLwcSection`, which shows every event. It hand-writes its inputs to keep the demonstration small, so copy its events, not its shape. This skeleton shows the same contract and is a starting point for any section component.

```javascript
import { LightningElement, api } from 'lwc';

export default class SectionSkeleton extends LightningElement {
    // Set by the form; never assign to them.
    @api record;
    @api objectApiName;
    @api review = false;
    @api disableAll = false;
    // Page sections only; these defaults on a Form Component section.
    @api relatedRecords = [];
    @api recordTemplate = {};
    @api section = {};

    get isReadOnly() {
        return this.review === true || this.disableAll === true;
    }

    // One field, one event, bubbles and composed.
    sendField(fieldApiName, value) {
        if (this.isReadOnly) return;
        this.dispatchEvent(new CustomEvent('formfieldchange', {
            detail: { fieldApiName, value: value === '' || value === undefined ? null : value },
            bubbles: true,
            composed: true
        }));
    }

    // Page sections only: 'add' with your fields, 'update' with the spread row, 'remove' with the row.
    sendRow(action, record) {
        if (this.isReadOnly) return;
        this.dispatchEvent(new CustomEvent('relatedrecordchange', { detail: { action, record }, bubbles: true, composed: true }));
    }

    // Optional. Blocks the page when isValid is false; each invalidItems entry is one line in the summary.
    @api validate() {
        return { isValid: true };
    }
}
```

In `validate()` and anything it calls, never assign a fresh object or array to a property the template reads. In a Form Component section, after one failed check the form validates again on every render, calling your `validate()` each time, so a new object on each call re-renders forever. Compare first, or keep the result in a primitive.
