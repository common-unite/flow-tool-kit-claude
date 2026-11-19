# Repeater properties

Every property a Repeater uses, read from the Flow Tool Kit package source: the Form Template Page Section fields, the form's section renderer that hands them to the repeater, and the **Form (Repeater)** flow screen component's metadata and code. Names are written without the `FlowToolKit__` prefix; add it in an org (`FlowToolKit__Min__c`, extension `FlowToolKit:flowFormRepeat`). Before a build, read the org's own list once (a describe of `FlowToolKit__Form_Template_Page_Section__c` through the connector, or `sf sobject describe`) and compare: an org on an older Flow Tool Kit can lack a field, and a newer one can add one. `scripts/repeater.py` checks a spec against the lists below. The shared rules (minimum and maximum, labels, prefill, deleting rows, conversion) are in [_shared/standards/repeating-rows.md](../_shared/standards/repeating-rows.md).

## Page section fields

### The section and its component

| Property | What it does | When to set it |
|---|---|---|
| `Component_Type__c` | What the section shows; `Repeater` repeats the component row by row | Always `Repeater` (the script writes it) |
| `Title__c` | The section's name in Form Builder; never shown on the form | Always: a few words naming what the rows are |
| `FormQualifiedApiName__c` | The row component by name: a record component as `<Name>_v0`, a metadata component by its name | A component by name (build-template writes it from the plan's component) |
| `FormConfigJSON__c` | The section editor's wrapper: `component` mode names the row component, `custom` mode carries the row's JSON fixed to this section | Written for you: by build-template from the plan, or by `section --format record` |
| `Form_Component__c` | A lookup to the row's Form Component record, kept for reference; the form never reads it | With a record component, its Id (`component_id` in the spec) |
| `Component_Section_Text__c` | Rich text shown above the rows; merge fields such as `{{FirstName}}` resolve against the live submission | An instruction above the rows, when the header text is not enough |

### Rows

| Property | What it does | When to set it |
|---|---|---|
| `Min__c` | The fewest rows. That many empty rows are created when there are none, and Delete stops at it. Field default 1; a blank on a saved section is 0 | Always, on purpose: 0 when rows are optional, 1 or more when at least one is required |
| `Max__c` | The most rows. New and Clone stop at it; prefilled rows beyond it are paged. Field default 5; 0 or a cleared value is read as 10 | Always, on purpose; never below `Min__c` |
| `Prefill_Template__c` | A Form Submission marked as a prefill template; its values seed every new row (and the starting empty rows) | When new rows need defaults, such as a relationship or a role. Guests need read on that record |
| `Section_Tag__c` | The section's stable identifier; a prefill flow's Prefill From Mapped Record step (Related Records) puts rows in by it. A Data Conversion Tag(s) value, unique within the template | Whenever a prefill flow will fill the rows |

### Actions

| Property | What it does | When to set it |
|---|---|---|
| `Enable_New_Action__c` | Shows New, which adds a row; hidden once `Max__c` is reached | When people add their own rows (almost always) |
| `New_Action_Button_Label__c` | New's button text: New, Add, Create or Insert | When "New" reads wrong for the rows ("Add" for people) |
| `Enable_Clone_Action__c` | Shows Clone on each row, which copies it into a new row; hidden at `Max__c` | When rows are mostly alike (shifts, line items) |
| `Clone_Action_Button_Label__c` | Clone's button text: Clone, Copy or Duplicate | With Clone on |
| `Enable_Delete_Action__c` | Shows Delete on each row; hidden at `Min__c`. A removed saved row goes back flagged `IsDeleted` and is deleted when the form saves | When people may remove rows |
| `Delete_Action_Button_Label__c` | Delete's button text: Delete, Remove or Clear | With Delete on ("Remove" for people) |
| `Enable_Edit_Action__c` | Has no effect on a Repeater section: the section never hands the repeater an edit form, and the repeater shows Edit only with one. Rows are edited in place | Leave off. Rows that need an Edit window are a Table |
| `Edit_Action_Button_Label__c` | Edit's button text: Edit, Update or Change. Not shown on a Repeater section (above) | Leave blank |
| `Edit_Action_Modal_Title__c` | The edit window's title. Not shown on a Repeater section (above) | Leave blank |
| `Edit_Action_Modal_Subtitle__c` | The edit window's subtitle. Not shown on a Repeater section (above) | Leave blank |

### Layout

| Property | What it does | When to set it |
|---|---|---|
| `Repeater_Record_Spacing__c` | Space above every row, including the first: none, xxx-small, xx-small, x-small, small, medium, large, x-large, xx-large. Blank is the standard spacing | When rows feel cramped or too far apart |
| `Repeater_Hide_Divider__c` | Hides the line between rows | Short rows that read better as one list |
| `Bottom_Margin__c` | Space below the whole section: `slds-m-bottom_none` to `slds-m-bottom_xx-large` | Only when the page's spacing needs it |

### Conversion (decided by new-mapping-flow)

| Property | What it does | When to set it |
|---|---|---|
| `Conversion_Rule__c` | What each row converts into: Bypass (default), Contact1, Contact2 (each also with Set Mailing Address and Set Other Address), Lead1, Lead2, Case | When the rows become records |
| `Conversion_Map_Flow__c` | The flow for this section's rows, dependent on the rule. Default runs the rule's packaged default flow, not the template's | Default, or the flow's API name new-mapping-flow added and wired |
| `Add_to_Account__c` | Links each converted Contact to the Account the conversion produced | Contacts who belong to the submitting organization |
| `Add_to_Campaign__c` | Adds each converted Contact or Lead to the submission's Campaign | Event and campaign sign-ups |
| `Contact_Matching_Rules__c` | Matching rules used to find existing Contacts for the rows; blank checks every active rule | When the rows should match by a particular rule |
| `Lead_Matching_Rules__c` | The same for Leads | Lead rows |
| `Update_Most_Confident_Contact__c` | With several Contact matches, update the most confident instead of stopping for a person | When a best guess is acceptable |
| `Update_Most_Confident_Lead__c` | The same for Leads | Lead rows |
| `Contact_Record_Type__c` | Record type for Contacts created from the rows; blank uses the converting user's default | Orgs with Contact record types |
| `Case_Record_Type__c` | Record type for Cases created from the rows | Case rows in orgs with Case record types |
| `Data_Conversion_Tag_s__c` | Tags stamped on each row for your own record-triggered flows; no packaged flow reads them | Only when your own automation branches on them |

### Header and frame (every section type has these; build-template sets them from the plan)

| Property | What it does | When to set it |
|---|---|---|
| `Show_Header__c` | Shows the header above the rows; off by default, which hides a planned title | Whenever the section has a title on the form |
| `Header_Title__c` | The header's title (rich text) | The title people read ("Additional contacts") |
| `Header_Subtitle__c` | The line under the title | A one-line explanation |
| `Header_Icon_Name__c` | An SLDS icon beside the title (`standard:contact`) | When the page's other headers have icons |
| `Header_Text__c` | Rich text inside the header, under the title and subtitle | Longer guidance |
| `Header_Text_Variant__c` | Shows the header text as plain text or an info, warning, error or success card | A note that must stand out |
| `Header_Display__c` | The header as the standard header or as a divider | With the page's header style |
| `Header_Divider_Style__c` | The divider style when the header shows as a divider | With `Header_Display__c` Divider |
| `Header_Style__c` | Where the title sits: classic (inside the frame) or outlined (on the frame's border) | With a framed section |
| `Header_Top_Margin__c` | Space above the header | Rarely |
| `Header_Kicker__c` | Stacked style: a short line above the title | Stacked headers only |
| `Header_Lead__c` | Stacked style: the body under the title | Stacked headers only |
| `Header_Tags__c` | Stacked style: pills, separated by semicolons | Stacked headers only |
| `Header_Tags_Position__c` | Stacked style: where the pills sit | Stacked headers only |
| `Header_Footer__c` | Stacked style: the header's last line | Stacked headers only |
| `Header_Bottom_Margin__c` | Stacked style: the gap between the header and the first row | Stacked headers only |
| `Section_Frame__c` | The box round the section: clean, box or shadow | As the plan's frame |
| `Top_Margin__c` | Space above the whole section | As the plan's spacing |
| `Field_Set_Show_Divider__c` | Shows the section's own divider (drawn round a Repeater section) | When the plan asks for one |
| `Divider_Style__c` | That divider's style | With the divider on |
| `Divider_Position__c` | Above or below the section | With the divider on |
| `Divider_Title__c` | Text on the divider | With the divider on |
| `Divider_Subtitle__c` | Second line on the divider | With the divider on |
| `Divider_Icon_Name__c` | Icon on the divider | With the divider on |
| `Divider_Vertical_Margin__c` | Extra space above and below the divider | With the divider on |
| `Conditional_Logic__c` | The rule that shows or hides the whole section, frame and header included | A section only some people answer |
| `Do_Not_Print__c` | Leaves the section out of the answers PDF. An empty Repeater is already left out | Screen-only content |

### Never written

| Property | What it does | When to set it |
|---|---|---|
| `isRepeater__c` | A formula, checked when the type is Repeater | Never: the package calculates it |
| `FlowApiName_Related__c` | A formula: the flow the rows will run, from the rule and the map flow | Never: read it to confirm the wiring |
| `editModalReturnOnSelect__c` | Deprecated: a section repeater has no Select button, so nothing reads it | Never: leave it unchecked |

## Flow screen properties

The **Form (Repeater)** component on a screen. Every input is optional unless the row says otherwise. `scripts/repeater.py flow-screen` writes the common ones from the spec; any other goes in `flow.properties` by name.

### The component and its rows

| Property | What it does | When to set it |
|---|---|---|
| `object` | The rows' object API name | Always (the script writes it): `FlowToolKit__Form_Submission__c`, `Contact`, your own object |
| `formQualifiedApiName` | The row component by name | A component by name |
| `formJSON` | The row component's JSON, fixed to this screen | JSON shape |
| `formJsonEnabled` | Reads the row from `formJSON` instead of a name | With `formJSON` |
| `dynamicFormSelectorEnabled` | Lets a text variable choose the component at run time | One screen that shows different row components |
| `prefillRecords` | Rows in and out: the record collection the repeater shows and hands back changed, removed saved rows flagged `IsDeleted` | Always bind it to a record collection variable, so rows survive Back |
| `recordTemplate` | A record whose values seed every new row | New rows need defaults (a parent Id, a role) |
| `recordTypeOptions` | Record types offered for new rows | Rows of an object with record types |
| `min` | The fewest rows; that many empty rows start the screen. Default 1 | Always, on purpose |
| `max` | The most rows; New, Clone and Import stop at it, more rows are paged. Default 5 (0 is read as 5) | Always, on purpose |
| `stampFormQualifiedApiName` | Writes the row component's name onto each new row (the object's FormQualifiedApiName field) | Rows that must remember which form made them |
| `languageOverride` | Shows the rows in this language instead of the person's | A form in a fixed language |

### Actions

| Property | What it does | When to set it |
|---|---|---|
| `allowNew` | Shows New | People add rows |
| `newButtonLabel` | New's text (default New) | Wording such as "Add someone" |
| `allowClone` | Shows Clone on each row | Rows mostly alike |
| `cloneButtonLabel` | Clone's text (default Clone) | With Clone on |
| `allowDelete` | Shows Delete on each row; hidden at `min` | People remove rows |
| `deleteButtonLabel` | Delete's text (default Delete) | With Delete on |
| `allowEdit` | Shows Edit on each row; only with an edit form | Rows that open a fuller form in a window |
| `editButtonLabel` | Edit's text (default Edit) | With Edit on |
| `editFormQualifiedApiName` | The edit window's form, by name (a record or metadata component, never JSON). Without it Edit never shows | With Edit on |
| `editModalHeading` | The edit window's title | With Edit on |
| `editModalSubheading` | The edit window's subtitle | With Edit on |
| `editModalReturnOnSelect` | Selecting a record inside the edit window closes it and returns | Edit windows that pick a record |
| `editReturnButtonLabel` | The edit window's return button text (default Return) | With Edit on |
| `allowImport` | Shows Import, which adds rows from existing records; Lookup Import lists only records not already added | People bring in records they already have |
| `importButtonLabel` | Import's text (default Import) | With Import on |
| `allowReposition` | Shows move up and down buttons; needs `repositionFieldApiName` | Rows in an order people choose |
| `repositionFieldApiName` | The number field that stores each row's position | With reposition on |
| `navigateOnReposition` | Moves the flow forward after a move | Rarely |
| `displayRepeaterButtonsAbove` | Puts the row buttons above each row instead of below | Long rows |

### Viewing and selecting rows

| Property | What it does | When to set it |
|---|---|---|
| `allowViewDetails` | Shows View Details on rows that have a value in `viewDetailsUrlField` | Rows that link to their record |
| `viewDetailsButtonLabel` | View Details' text | With View Details on |
| `viewDetailsTarget` | Where the link opens (default `_blank`) | With View Details on |
| `viewDetailsUrlField` | The field holding the link (default Id) | With View Details on |
| `viewDetailsNavigateOnSelect` | Moves the flow forward when View Details is clicked | Rarely |
| `allowSelect` | Shows Select on each row, filling the selection outputs | A screen where people pick rows |
| `hideSelectButton` | Rows control selection: the row's component provides the control, with the same limits and outputs | A custom row that selects itself |
| `maxSelection` | How many rows may be selected (default 1) | With selection on |
| `navigateOnSelect` | Moves the flow forward on selection | One-click choices |
| `navigateToRecordOnSelect` | Opens the selected record | Rarely |
| `showSelectedOnly` | Shows only the selected rows | A review of choices |
| `selectionReturnFieldValue` | The field whose values fill the Selected Value(s) outputs (default Id) | With selection on |
| `selectLabelWhenOff` | Select's text when not selected | With selection on |
| `selectLabelWhenOn` | Select's text when selected | With selection on |
| `selectLabelWhenHover` | Select's text on hover | With selection on |
| `selectIconWhenOff` | Select's icon when not selected (Disabled hides it) | With selection on |
| `selectIconWhenOn` | Select's icon when selected | With selection on |
| `selectIconWhenHover` | Select's icon on hover | With selection on |

### Layout

| Property | What it does | When to set it |
|---|---|---|
| `recordSpacing` | Space above each row: none to xx-large | As on the page section |
| `recordSpacingBottom` | Space below each row | Rarely |
| `recordSpacingHorizontal` | Space left and right of each row when rows sit side by side | With the size properties |
| `smallSize` | Each row's width out of 12 on small screens (rows side by side when below 12) | Cards side by side |
| `mediumSize` | The same on medium screens | Cards side by side |
| `largeSize` | The same on large screens | Cards side by side |
| `hideDivider` | Hides the line between rows | Short rows |
| `bottomMargin` | Space below the component | Rarely |
| `topMargin` | Space above the header | Rarely |
| `themeOverrideName` | A Form Theme for the rows | A screen styled apart from the org default |
| `themeHeaderName` | A Form Theme for the header only | Rarely |

### Header and accordion

| Property | What it does | When to set it |
|---|---|---|
| `showHeader` | Shows the header (default on) | Off when the screen already titles the rows |
| `title` | The header's title | Always when shown |
| `subtitle` | The line under the title | A short explanation |
| `iconName` | The header icon | As the screen's other headers |
| `helpText` | Help beside the title | Brief guidance |
| `richText` | Rich text inside the header | Longer guidance |
| `enableAccordion` | Each row in a collapsible panel | Long rows |
| `wrapInAccordion` | Wraps the whole repeater in a panel | A repeater that may be closed |
| `accordionTitle` | Each row's panel title; merge row fields into it | With the accordion |
| `subtitleTemplate` | Each row's panel subtitle, with merges | With the accordion |
| `iconNameTemplate` | Each row's panel icon, with merges | With the accordion |
| `dynamicHeaders` | Builds each row's header from the three templates above, merged with that row's answers | With the templates |
| `closedOnLoad` | Panels start closed | Many rows |
| `preventAccordionClose` | Panels cannot be closed | Rows that must stay visible |
| `disableAllHeaders` | Hides the row components' own section headers | Compact rows |

### Behaviour

| Property | What it does | When to set it |
|---|---|---|
| `requireAll` | Makes every question of every row required | Rarely: required questions belong in the component |
| `disableAll` | Shows every row read-only and hides the actions | A read-only summary |
| `review` | Shows the rows as a review | A review screen |
| `displayPrompts` | Shows the row questions' prompts | When the component uses prompts |
| `preventValidationBypass` | Always checks the rows, even for buttons that normally skip checks (Back, Save Progress) | Rows that must be valid before any move |
| `formRepeaterConfiguration` | One object from the **Configure Form (Repeater)** action holding the settings above. When it is set, it replaces every individual property, so never mix the two | A flow that sets many properties from one action or changes them at run time |

### Outputs (read them; never set them)

| Property | What it does | When to set it |
|---|---|---|
| `insertCollection` | Rows to insert | A flow that saves rows of its own object |
| `updateCollection` | Rows to update | The same |
| `deleteCollection` | Rows to delete | The same |
| `insertCollectionSize` | How many rows to insert | Decisions on the count |
| `updateCollectionSize` | How many rows to update | Decisions on the count |
| `deleteCollectionSize` | How many rows to delete | Decisions on the count |
| `prefillRecordsSize` | All rows, removed ones included | Rarely |
| `totalRecordsSize` | Rows still shown | "At least one" checks |
| `selectedRecords` | The selected rows (also an input: bind it to keep the selection on Back) | With selection |
| `firstSelectedRow` | The first selected row | Single choice |
| `selectedCollectionSize` | How many rows are selected | With selection |
| `selectedRecordsIds` | The selected rows' Ids | With selection |
| `selectedRecordsIdsString` | The same as one text value, for component visibility | With selection |
| `selectedRecordsValues` | The selected rows' `selectionReturnFieldValue` values | With selection |
| `selectedRecordsValuesString` | The same as one text value | With selection |
| `calculatedResult` | A record holding the sums, minimums, maximums and averages the row component's calculated fields ask for | Totals |
| `calculatedResultSelectedOnly` | The same over the selected rows | Totals of a selection |

### Set from the flow itself

| Property | What it does | When to set it |
|---|---|---|
| `interviewGuid` | The interview's Id, so the page's buttons reach this component | Always `{!$Flow.InterviewGuid}` (the script writes it) |
| `interviewStartDateTime` | The interview's start, with the Id | Always `{!$Flow.InterviewStartTime}` |
| `serverURL` | The server address, used to find the Experience Cloud path | Always `{!$Api.Enterprise_Server_URL_140}` |
| `elementApiName` | A key that tells two components on one screen apart | Two repeaters on one screen |
