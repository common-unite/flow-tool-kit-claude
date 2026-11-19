import { LightningElement, api } from 'lwc';

// Stands in for Flow Tool Kit's form in Jest; the real one exists only in an org with the package.
export default class FlowForm extends LightningElement {
    @api isExtension = false;
    @api formJSON;
    @api formQualifiedApiName;
    @api object;
    @api record;
    @api transformationRecord;
    @api review = false;
    @api disableAll = false;
    @api validationResult = { isValid: true };
    @api validate() {
        return this.validationResult;
    }
}
