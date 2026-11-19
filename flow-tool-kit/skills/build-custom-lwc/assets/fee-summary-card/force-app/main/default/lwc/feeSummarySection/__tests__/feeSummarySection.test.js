import { createElement } from 'lwc';
import FeeSummarySection from 'c/feeSummarySection';
import { plotFee } from '../feeRules';

const PLOT_SIZE = 'Plot_Size__c';
const NUMBER_OF_PLOTS = 'Number_Of_Plots__c';
const SENIOR_OR_STUDENT = 'Senior_Or_Student__c';
const PLOT_FEE = 'Plot_Fee__c';
const SUBMISSION = 'FlowToolKit__Form_Submission__c';
const PAGE_SECTION = { Id: 'a0A000000000001AAA', FlowToolKit__FormQualifiedApiName__c: 'Garden_Plot_Details' };

function mount(props = {}) {
    const element = createElement('c-fee-summary-section', { is: FeeSummarySection });
    Object.assign(element, { objectApiName: SUBMISSION, ...props });
    const changes = [];
    element.addEventListener('formfieldchange', event => changes.push(event));
    document.body.appendChild(element);
    return { element, changes };
}

const settle = () => Promise.resolve().then(() => Promise.resolve());
const sectionForm = element => element.shadowRoot.querySelector('[data-section-form]');
const message = element => element.shadowRoot.querySelector('[data-message]');
const totalCell = element => element.shadowRoot.querySelector('[data-total] lightning-formatted-number');

afterEach(() => {
    while (document.body.firstChild) document.body.removeChild(document.body.firstChild);
});

describe('fee rules', () => {
    it('waits for both answers', () => {
        expect(plotFee({ plotSize: 'Small' })).toBeNull();
        expect(plotFee({ numberOfPlots: 2 })).toBeNull();
        expect(plotFee({ plotSize: 'Small', numberOfPlots: 0 })).toBeNull();
    });

    it('multiplies the rate and halves it for the concession', () => {
        expect(plotFee({ plotSize: 'Standard', numberOfPlots: 2 })).toMatchObject({ subtotal: 80, discount: 0, total: 80 });
        expect(plotFee({ plotSize: 'Raised Bed', numberOfPlots: 3, concession: true })).toMatchObject({ subtotal: 165, discount: 82.5, total: 82.5 });
    });

    it('marks a plot size with no rate as unpriced', () => {
        expect(plotFee({ plotSize: 'Orchard', numberOfPlots: 1 })).toEqual({ unpriced: true, plotSize: 'Orchard', plots: 1 });
    });
});

describe('Form Component section (no section record)', () => {
    it('asks for the answers until the fee can be priced, and sends nothing', async () => {
        const { element, changes } = mount({ record: { [PLOT_SIZE]: 'Small' } });
        await settle();
        expect(sectionForm(element)).toBeNull();
        expect(message(element).textContent).toBe('c.Fee_Summary_Incomplete');
        expect(changes).toHaveLength(0);
    });

    it('shows the total and writes it back as one bubbling, composed event', async () => {
        const { element, changes } = mount({ record: { [PLOT_SIZE]: 'Standard', [NUMBER_OF_PLOTS]: 2, [SENIOR_OR_STUDENT]: true } });
        await settle();
        expect(totalCell(element).value).toBe(40);
        expect(changes).toHaveLength(1);
        expect(changes[0].detail).toEqual({ fieldApiName: PLOT_FEE, value: 40 });
        expect(changes[0].bubbles).toBe(true);
        expect(changes[0].composed).toBe(true);
    });

    it('does not send the fee again when the form hands it back', async () => {
        const { element, changes } = mount({ record: { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1 } });
        await settle();
        element.record = { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1, [PLOT_FEE]: 25 };
        await settle();
        expect(changes.map(event => event.detail.value)).toEqual([25]);
    });

    it('sends a new total when an answer changes, and clears it when the answers are no longer complete', async () => {
        const { element, changes } = mount({ record: { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1 } });
        await settle();
        element.record = { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 3, [PLOT_FEE]: 25 };
        await settle();
        element.record = { [PLOT_SIZE]: 'Small', [PLOT_FEE]: 75 };
        await settle();
        expect(changes.map(event => event.detail.value)).toEqual([25, 75, null]);
    });

    it('never writes in review or read-only mode', async () => {
        const answers = { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1 };
        const review = mount({ record: answers, review: true });
        const readOnly = mount({ record: answers, disableAll: true });
        await settle();
        expect(totalCell(review.element).value).toBe(25);
        expect(review.changes).toHaveLength(0);
        expect(readOnly.changes).toHaveLength(0);
    });

    it('blocks the page for a plot size with no rate, as one line in the summary', async () => {
        const { element } = mount({ record: { [PLOT_SIZE]: 'Orchard', [NUMBER_OF_PLOTS]: 1 } });
        await settle();
        const result = element.validate();
        expect(result.isValid).toBe(false);
        expect(result.invalidItems).toEqual([{ label: 'c.Fee_Summary_Title', text: 'c.Fee_Summary_Unpriced' }]);
    });
});

describe('Form Template page section (renders the admin form)', () => {
    it('renders the section form as an extension with the live record', async () => {
        const record = { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1 };
        const { element } = mount({ record, section: PAGE_SECTION });
        await settle();
        const form = sectionForm(element);
        expect(form).not.toBeNull();
        expect(form.isExtension).toBe(true);
        expect(form.formQualifiedApiName).toBe('Garden_Plot_Details');
        expect(form.object).toBe(SUBMISSION);
        expect(form.record).toEqual(record);
        expect(form.transformationRecord).toEqual({ [PLOT_FEE]: 25 });
    });

    it('hands the form a new record only when a value changes, so a rebuilt record cannot loop', async () => {
        const { element } = mount({ record: { [PLOT_SIZE]: 'Small', [PLOT_FEE]: null }, section: PAGE_SECTION, review: true });
        await settle();
        const first = sectionForm(element).record;
        element.record = { [PLOT_SIZE]: 'Small' };
        await settle();
        expect(sectionForm(element).record).toBe(first);
        element.record = { [PLOT_SIZE]: 'Standard' };
        await settle();
        expect(sectionForm(element).record).not.toBe(first);
        expect(sectionForm(element).record).toEqual({ [PLOT_SIZE]: 'Standard' });
    });

    it('sends the fee once while the host has not handed it back yet', async () => {
        const { changes } = mount({ record: { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 1 }, section: PAGE_SECTION });
        await settle();
        await settle();
        expect(changes.map(event => event.detail)).toEqual([{ fieldApiName: PLOT_FEE, value: 25 }]);
    });

    it('renders a form saved on the section itself', async () => {
        const wrapper = JSON.stringify({ formSelectionMode: 'custom', object: SUBMISSION, formJsonConfig: '{}' });
        const { element } = mount({ record: {}, section: { FlowToolKit__FormConfigJSON__c: wrapper } });
        await settle();
        expect(sectionForm(element).formJSON).toBe(wrapper);
    });

    it('passes on only the fields the person changed, one event each', async () => {
        const { element, changes } = mount({ record: { [PLOT_SIZE]: 'Small' }, section: PAGE_SECTION });
        await settle();
        sectionForm(element).dispatchEvent(new CustomEvent('recordchange', {
            detail: { [PLOT_SIZE]: 'Small', [NUMBER_OF_PLOTS]: 2, [SENIOR_OR_STUDENT]: '' }
        }));
        expect(changes.map(event => event.detail)).toEqual([
            { fieldApiName: NUMBER_OF_PLOTS, value: 2 },
            { fieldApiName: SENIOR_OR_STUDENT, value: null }
        ]);
    });

    it('lets the admin form block the page with its own checks', async () => {
        const { element } = mount({ record: {}, section: PAGE_SECTION });
        await settle();
        sectionForm(element).validationResult = ({ isValid: false, errorMessage: 'Plot size is required', invalidItems: [{ label: 'Plot size', text: 'Plot size is required' }] });
        expect(element.validate()).toEqual({ isValid: false, errorMessage: 'Plot size is required', invalidItems: [{ label: 'Plot size', text: 'Plot size is required' }] });
    });
});
