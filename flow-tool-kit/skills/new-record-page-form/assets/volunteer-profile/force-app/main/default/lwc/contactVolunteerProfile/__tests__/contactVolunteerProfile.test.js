import { createElement } from 'lwc';
import ContactVolunteerProfile from 'c/contactVolunteerProfile';
import FORM_CONFIG from '../contactVolunteerProfileConfig';

const OBJECT_API_NAME = 'Contact';
const RECORD_ID = '001000000000001AAA';

function mount(recordId = RECORD_ID) {
    const element = createElement('c-contact-volunteer-profile', { is: ContactVolunteerProfile });
    element.recordId = recordId;
    document.body.appendChild(element);
    return element.shadowRoot.querySelector('flowtoolkit-lightning-record-form');
}

describe('c-contact-volunteer-profile', () => {
    afterEach(() => {
        while (document.body.firstChild) document.body.removeChild(document.body.firstChild);
    });

    it('hands the page record and its object to the Flow Tool Kit record form', () => {
        const form = mount();
        expect(form).not.toBeNull();
        expect(form.recordId).toBe(RECORD_ID);
        expect(form.objectApiName).toBe(OBJECT_API_NAME);
    });

    it('shows the Save button and saves only when it is pressed', () => {
        const form = mount();
        expect(form.hideButtons).toBe(false);
        expect(form.autoSave).toBe(false);
    });

    it('asks the record form to check edit access, so people who may only read the record and site guests see it read only', () => {
        expect(mount().checkRecordAccess).toBe(true);
    });

    it('follows the page when the record changes', async () => {
        const element = createElement('c-contact-volunteer-profile', { is: ContactVolunteerProfile });
        element.recordId = RECORD_ID;
        document.body.appendChild(element);
        element.recordId = '001000000000002AAA';
        await Promise.resolve();
        expect(element.shadowRoot.querySelector('flowtoolkit-lightning-record-form').recordId).toBe('001000000000002AAA');
    });

    it('hands over the baked form, built on this object, as JSON the package can read', () => {
        const form = mount();
        expect(form.formJsonConfig).toBe(FORM_CONFIG);
        const parsed = JSON.parse(FORM_CONFIG.replaceAll('*__', 'FlowToolKit__'));
        expect(parsed.FlowToolKit__ObjectApiName__c).toBe(OBJECT_API_NAME);
        expect(Array.isArray(parsed.FlowToolKit__sections__r)).toBe(true);
        expect(parsed.FlowToolKit__sections__r.length).toBeGreaterThan(0);
    });
});
