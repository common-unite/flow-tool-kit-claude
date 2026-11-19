import { LightningElement, api } from 'lwc';
import FORM_CONFIG from './contactVolunteerProfileConfig';

// The form is built on Contact; the component is placed only on its record pages.
const OBJECT_API_NAME = 'Contact';

// Flow Tool Kit's record form loads the record, lays out the form, validates and saves; this component only hands it the record and the form.
export default class ContactVolunteerProfile extends LightningElement {
    @api recordId; // set by the record page; on a site page, bound in Experience Builder

    objectApiName = OBJECT_API_NAME;
    formConfig = FORM_CONFIG;
}
