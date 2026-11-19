import { LightningElement, api } from 'lwc';

// Stands in for Flow Tool Kit's record form in Jest; the real one exists only in an org with the package installed.
export default class LightningRecordForm extends LightningElement {
    @api recordId;
    @api objectApiName;
    @api formJsonConfig;
    @api formQualifiedApiName;
    @api autoSave = false;
    @api hideButtons = false;
    @api checkRecordAccess = false;
    @api readOnly = false;
}
