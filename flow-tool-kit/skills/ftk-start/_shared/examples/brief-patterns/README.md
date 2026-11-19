# Brief patterns

The pattern library brief mode builds from when a form is described rather than supplied. One entry per form type, per block and per platform. Nothing here names a particular org: every target is a packaged Flow Tool Kit field or is read from the connected org at run time.

## Form types

The form-type rules set the header, buttons, indicator and first page; these entries add the usual pages and blocks.

| Type | Typical pages | Blocks | Form-type row |
|---|---|---|---|
| Grant application | About the Program (optional), Applicant, Request, Financial Need, Release and Signature | contact, organization, address, funding request, uploads, consent, signature | 6: long, stages, Save Progress, review screen |
| Registration | Your Details, Choices, Release (optional) | contact, address, demographics, consent | 3 to 5 by page count and time |
| Intake | About You, Household, Needs, Consent | contact, address, demographics, uploads, consent, signature | 5, or 6 when about 10 minutes or more |
| Release | Participant, Release and Signature | contact, consent, signature | 4 |
| Survey | one page, or one page per topic | survey questions, optional contact | 1 or 2 |
| Request | one page | contact, request details, uploads | 3 |

## Blocks

| Block | Fields and controls | Packaged targets to try first |
|---|---|---|
| Contact | First and Last Name (text), Email (email), Phone (tel) | Contact 1 block: `Contact1_First_Name__c`, `Contact1_Last_Name__c`, `Contact1_Email__c`, `Contact1_Phone__c` |
| Second person (guardian, co-applicant) | Same as Contact | Contact 2 block |
| Address | One Address component, never separate text fields | `Mailing_Street__c`, `Mailing_City__c`, `Mailing_State_Province__c`, `Mailing_Postal_Code__c`, `Mailing_Country__c` |
| Organization | Name, Phone, Website | `Company__c`, `Company_Phone__c`, `Company_Email__c`, `Website__c` |
| Demographics | Age range (separated buttons), gender, race and ethnicity (multi-select), each with a "prefer not to" value, all optional | `Age_Range__c`, `Contact1_Gender__c`, `Contact1_Race_Ethnicity_Multiselect__c`, `Household_Size__c`, `Household_Income__c` |
| Consent | Every consent as an attestation in one section, the full text above it | `Agree_Consent__c`, `Liability_Waiver_Agreement__c`, `Photo_Video_Consent__c`, `Agreement_Question_1__c` and on |
| Signature | Signature pad, printed name, date; last on the form | `Electronic_Signature__c`, `Electronic_Signature_Print__c`, `Electronic_Signature_Date__c` |
| Funding request | Amount requested (currency), project title, description (long text) | The platform's own fields (below) |
| Uploads | File upload with accepted formats and a limit | Files on the submission |

## Platforms

- **Outbound Funds.** A Funding Program links to the Form Template. The conversion creates the Funding Request with the converted Contact and its amount and question fields. Read the Funding Request fields from the org before placing answers.
- **Nonprofit Cloud.** An Individual Application has no packaged conversion flow, which is the normal case: plan a custom conversion flow and a controller update or custom controller with new-mapping-flow. The application's account must be a person account.

## Worked examples

| Example | Status |
|---|---|
| `form-3-page-release`: information page, contact, demographics and organization, release with signature | Written |
| Riverbend Arts Fund grant (Outbound Funds): long, stages; About the Program, Applicant, Project and Budget, Release and Signature | To write |
| Northgate Youth Scholarship (Nonprofit Cloud): long, stages; Individual Application through a custom conversion flow | To write |
| Lakeside Camp release: two pages, participant then release with guardian signature | To write |
| Harbor Food Bank volunteer sign-up: one page, simple | To write |
| Maple Clinic intake: three short pages, base indicator | To write |
| Program feedback survey: one page with survey sections | To write |
