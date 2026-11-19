# Section layout

The second Section card: the same `Section` component, shown for how sections open, divide and sit on the page. Every example holds at least five fields so each reads as a real group.

- **Accordion sections** (`sectionType__c` = `accordionSection`): closed by default, open on load only with `accordionOpen__c`. Theme with `accordionBackgroundColor__c`, `accordionFontColor__c` and `hideAccordionBorder__c`.
- **Divider headers** (`Header_Display__c` = `Divider`) and divider sections (`sectionType__c` = `dividerSection`). See `Divider` for all 12 styles.
- **Section width** (`widthLarge__c`, `widthMedium__c`, `widthSmall__c`): sections side by side inside a `SectionGrid`, stacking on phones.
- **Flow Action** (`flowApiName__c`, rarely used): a brand button on the section rich text that opens a screen flow in a modal; `flowButtonStyle__c` is CSS.

Props are documented in the `Section` README.
