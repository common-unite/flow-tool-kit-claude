import { LightningElement, api } from 'lwc';
import CURRENCY from '@salesforce/i18n/currency';

import PLOT_SIZE from '@salesforce/schema/FlowToolKit__Form_Submission__c.Plot_Size__c';
import NUMBER_OF_PLOTS from '@salesforce/schema/FlowToolKit__Form_Submission__c.Number_Of_Plots__c';
import SENIOR_OR_STUDENT from '@salesforce/schema/FlowToolKit__Form_Submission__c.Senior_Or_Student__c';
import PLOT_FEE from '@salesforce/schema/FlowToolKit__Form_Submission__c.Plot_Fee__c';
import SECTION_FORM_NAME from '@salesforce/schema/FlowToolKit__Form_Template_Page_Section__c.FlowToolKit__FormQualifiedApiName__c';
import SECTION_FORM_CONFIG from '@salesforce/schema/FlowToolKit__Form_Template_Page_Section__c.FlowToolKit__FormConfigJSON__c';

import TITLE from '@salesforce/label/c.Fee_Summary_Title';
import PLOTS_LINE from '@salesforce/label/c.Fee_Summary_Plots';
import CONCESSION_LINE from '@salesforce/label/c.Fee_Summary_Concession';
import TOTAL from '@salesforce/label/c.Fee_Summary_Total';
import INCOMPLETE from '@salesforce/label/c.Fee_Summary_Incomplete';
import UNPRICED from '@salesforce/label/c.Fee_Summary_Unpriced';

import { plotFee } from './feeRules';

const sameValue = (left, right) => left === right || (left == null && right == null);
const differs = (current, next) => [...new Set([...Object.keys(current), ...Object.keys(next)])].some(key => !sameValue(current[key], next[key]));

// Renders the section's own form (page sections) and a live fee card under it; writes the total to Plot Fee.
export default class FeeSummarySection extends LightningElement {
    @api
    get record() {
        return this._record;
    }
    set record(value) {
        this._record = value;
        // The admin's preview rebuilds the record on every broadcast; handing that straight to the form loops, so it gets a copy only on a real change.
        const next = value || {};
        if (!this.formRecord || differs(this.formRecord, next)) this.formRecord = { ...next };
    }
    _record;
    formRecord;

    @api objectApiName;
    @api review = false;
    @api disableAll = false;
    @api relatedRecords = [];
    @api recordTemplate = {};
    @api section = {};

    label = { title: TITLE, concession: CONCESSION_LINE, total: TOTAL, incomplete: INCOMPLETE };
    currencyCode = CURRENCY;

    // Values this component derives, handed to the admin's form so a Plot Fee field placed on it shows the total.
    derivedValues = {};
    lastSentFee;

    get isReadOnly() {
        return this.review === true || this.disableAll === true;
    }

    // The admin's form for this section: a named form component, or a form saved on the section itself.
    get sectionFormName() {
        return (this.section || {})[SECTION_FORM_NAME.fieldApiName] || undefined;
    }
    get sectionFormConfig() {
        return (this.section || {})[SECTION_FORM_CONFIG.fieldApiName] || undefined;
    }
    get hasSectionForm() {
        return !!(this.sectionFormName || this.sectionFormConfig);
    }

    get fee() {
        const record = this.record || {};
        return plotFee({
            plotSize: record[PLOT_SIZE.fieldApiName],
            numberOfPlots: record[NUMBER_OF_PLOTS.fieldApiName],
            concession: record[SENIOR_OR_STUDENT.fieldApiName]
        });
    }
    get isPriced() {
        return !!this.fee && !this.fee.unpriced;
    }
    get isUnpriced() {
        return !!this.fee && this.fee.unpriced;
    }
    get hasDiscount() {
        return this.isPriced && this.fee.discount > 0;
    }
    get plotsLine() {
        const fee = this.fee || {};
        return PLOTS_LINE.replace('{0}', fee.plots).replace('{1}', fee.plotSize);
    }
    get unpricedMessage() {
        return UNPRICED.replace('{0}', (this.fee || {}).plotSize);
    }
    get negativeDiscount() {
        return this.hasDiscount ? -this.fee.discount : 0;
    }

    // The record can change in place (Form Component sections) or as a new object (page sections), so the fee is
    // compared after every render rather than in a property setter, which an in-place change never calls.
    renderedCallback() {
        this.syncFee();
    }

    syncFee() {
        if (this.isReadOnly) return;
        const total = this.isPriced ? this.fee.total : null;
        const saved = (this.record || {})[PLOT_FEE.fieldApiName] ?? null;
        // Only a real change is sent: the form hands the value straight back, and sending it again would loop.
        if (total === saved || total === this.lastSentFee) return;
        this.lastSentFee = total;
        this.derivedValues = { [PLOT_FEE.fieldApiName]: total };
        this.sendFieldChange(PLOT_FEE.fieldApiName, total);
    }

    // The admin's form reports its whole record; pass on only the fields that changed, one event each.
    handleFormRecordChange(event) {
        event.stopPropagation();
        const changed = event.detail || {};
        const previous = this.record || {};
        Object.keys(changed)
            .filter(fieldApiName => changed[fieldApiName] !== previous[fieldApiName])
            .forEach(fieldApiName => this.sendFieldChange(fieldApiName, changed[fieldApiName]));
    }

    sendFieldChange(fieldApiName, value) {
        this.dispatchEvent(new CustomEvent('formfieldchange', {
            detail: { fieldApiName, value: value === '' || value === undefined ? null : value },
            bubbles: true,
            composed: true
        }));
    }

    // Runs when the person moves on: the admin's own required-field checks first, then the one rule only code knows.
    @api validate() {
        const form = this.template.querySelector('[data-section-form]');
        const formResult = form && typeof form.validate === 'function' ? form.validate() || { isValid: true } : { isValid: true };
        if (!this.isUnpriced) return formResult;
        const item = { label: TITLE, text: this.unpricedMessage };
        return {
            isValid: false,
            errorMessage: formResult.isValid === false ? formResult.errorMessage : item.text,
            invalidItems: [...(formResult.invalidItems || []), item]
        };
    }
}
