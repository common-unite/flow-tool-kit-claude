# Table properties

Every property a Table uses, read from the Flow Tool Kit package source: the Form Template Page Section fields, the form's section renderer that hands them to the table, the Page Section Preview on a record page, and the **Form (Table)** flow screen component's metadata and code. Names are written without the `FlowToolKit__` prefix; add it in an org (`FlowToolKit__Table_Row_Style__c`, extension `FlowToolKit:flowDataTable`). Before a build, read the org's own list once (a describe of `FlowToolKit__Form_Template_Page_Section__c` through the connector, or `sf sobject describe`) and compare: an org on an older Flow Tool Kit can lack a field, and a newer one can add one. `scripts/table.py` checks a spec against the lists below. The shared rules (minimum and maximum, labels, prefill, deleting rows, conversion) are in [_shared/standards/repeating-rows.md](../_shared/standards/repeating-rows.md).

**Two renderers read a Table section.** The form itself (Preview Form, every live form) and the **Page Section Preview** component on a Form Template Page or Page Section record page. In the package version these notes were read from they read different fields for the row form and for the display settings; the "Read by" column says which. Check every Table in Preview Form, not only on the record page.

## Page section fields

### The section, its table and its forms

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Component_Type__c` | What the section shows; `Table` draws the table component | Both | Always `Table` (the script writes it) |
| `Title__c` | The section's name in Form Builder; never shown on the form | Form Builder | Always |
| `FormQualifiedApiName__c` | The table component by name (a form component whose root type is `table`; its fields are the columns) | Both | A table component by name (build-template writes it from the plan) |
| `FormConfigJSON__c` | The section editor's wrapper: `component` mode names the table component, `custom` mode carries its JSON fixed to this section | Both | Written for you: by build-template, or by `section --format record` |
| `Form_Component__c` | A lookup to the table component's record, kept for reference; never read | Neither | With a record component, its Id |
| `Edit_FormQualifiedApiName__c` | The row form: the form component with every question of one row, opened by New, Edit and Clone. Loaded by name only | The form | Whenever New, Edit or Clone is on, unless the table component names its own default row form. The script writes the same value here and in the next field |
| `Alternate_FormQualifiedApiName__c` | The row form, as the Page Section Preview reads it. The package's own help calls this the current field; the form itself reads the one above | Page Section Preview | Always the same value as `Edit_FormQualifiedApiName__c` |
| `Bulk_FormQualifiedApiName__c` | The form for editing several selected rows at once | Both, but unused: a page section never turns on bulk edit | Leave blank on a page section; bulk edit is a flow screen setting |
| `Component_Section_Text__c` | Rich text shown above the table; merge fields resolve against the live submission | The form | An instruction above the table |

### Rows

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Min__c` | Passed to the table, which does not enforce it in this package version. Field default 1 | Both | Leave the default; limit the count with a Repeater or in the conversion |
| `Max__c` | The same: passed, not enforced. Field default 5 | Both | Leave the default |
| `Prefill_Template__c` | A Form Submission marked as a prefill template; its values seed every new row | The form | When new rows need defaults. Guests need read on that record |
| `Section_Tag__c` | The section's stable identifier; a prefill flow's Prefill From Mapped Record step (Related Records) puts rows in by it. A Data Conversion Tag(s) value, unique within the template | Prefill | Whenever a prefill flow will fill the rows |

### Actions and their windows

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Enable_New_Action__c` | Shows New, which opens the row form in a window to add a row | Both | People add rows |
| `New_Action_Button_Label__c` | New's text: New, Add, Create or Insert | Both | "Add" for people |
| `Table_New_Action_Modal_Title__c` | The add window's title | Both | Always with New: "Add a volunteer" |
| `Table_New_Action_Modal_Subtitle__c` | The add window's subtitle | Both | A line of guidance |
| `Enable_Edit_Action__c` | Shows Edit on each row, which opens the row form with that row's answers | Both | Almost always: the point of a Table |
| `Edit_Action_Button_Label__c` | Edit's text: Edit, Update or Change | Both | When "Edit" reads wrong |
| `Edit_Action_Modal_Title__c` | The edit window's title | Both | Always with Edit |
| `Edit_Action_Modal_Subtitle__c` | The edit window's subtitle | Both | A line of guidance |
| `Enable_Clone_Action__c` | Shows Clone on each row, which opens the row form with a copy | Both | Rows mostly alike |
| `Clone_Action_Button_Label__c` | Clone's text: Clone, Copy or Duplicate | Both | With Clone on |
| `Table_Clone_Action_Modal_Title__c` | The clone window's title | Both | With Clone on |
| `Table_Clone_Action_Modal_Subtitle__c` | The clone window's subtitle | Both | With Clone on |
| `Enable_Delete_Action__c` | Shows Delete on each row, after a confirmation. A removed saved row goes back flagged `IsDeleted` and is deleted when the form saves | Both | People remove rows |
| `Delete_Action_Button_Label__c` | Delete's text: Delete, Remove or Clear | Both | "Remove" for people |
| `Table_Delete_Action_Modal_Title__c` | The confirmation's title | Both | With Delete on |
| `Table_Delete_Action_Modal_Subtitle__c` | The confirmation's subtitle | Both | With Delete on |
| `Table_Delete_Action_Modal_Body__c` | The confirmation's message (rich text) | Both | Say what is lost |

### Table display

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Table_Display_Row_Numbers__c` | A numbered first column | Page Section Preview only | Set if wanted, then check Preview Form: the form does not apply it in this package version |
| `Table_Hide_Column_Headers__c` | Hides the column header row | Page Section Preview only | The same |
| `Table_Hide_Footer__c` | Hides the footer with the row count | Page Section Preview only | The same |
| `Table_Prevent_Column_Resize__c` | Stops people dragging column widths | Page Section Preview only | The same |
| `Table_Row_Style__c` | Row look: `hideBorders`, `slds-table_striped` or `slds-table_col-bordered` | Page Section Preview only | The same |
| `Table_Disable_Row_Action_Indicators__c` | Removed rows disappear instead of staying, marked, with a way to undo | Page Section Preview; the form always behaves as if it were on | The same |
| `Bottom_Margin__c` | Space below the whole section | Both | Only when the page's spacing needs it |

### Conversion (decided by new-mapping-flow)

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Conversion_Rule__c` | What each row converts into: Bypass (default), Contact1, Contact2 (each also with Set Mailing Address and Set Other Address), Lead1, Lead2, Case | Conversion | When the rows become records |
| `Conversion_Map_Flow__c` | The flow for this section's rows, dependent on the rule. Default runs the rule's packaged default flow, not the template's | Conversion | Default, or the flow's API name new-mapping-flow added and wired |
| `Add_to_Account__c` | Links each converted Contact to the Account the conversion produced | Conversion | Contacts who belong to the submitting organization |
| `Add_to_Campaign__c` | Adds each converted Contact or Lead to the submission's Campaign | Conversion | Event and campaign sign-ups |
| `Contact_Matching_Rules__c` | Matching rules used to find existing Contacts; blank checks every active rule | Conversion | A particular rule |
| `Lead_Matching_Rules__c` | The same for Leads | Conversion | Lead rows |
| `Update_Most_Confident_Contact__c` | With several Contact matches, update the most confident | Conversion | A best guess is acceptable |
| `Update_Most_Confident_Lead__c` | The same for Leads | Conversion | Lead rows |
| `Contact_Record_Type__c` | Record type for Contacts created from the rows | Conversion | Orgs with Contact record types |
| `Case_Record_Type__c` | Record type for Cases created from the rows | Conversion | Case rows |
| `Data_Conversion_Tag_s__c` | Tags stamped on each row for your own record-triggered flows | Your flows | Only when your automation branches on them |

### Header and frame (every section type has these; build-template sets them from the plan)

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `Show_Header__c` | Shows the header above the table; off by default | Both | Whenever the section has a title |
| `Header_Title__c` | The header's title (rich text) | Both | The title people read |
| `Header_Subtitle__c` | The line under the title | Both | A one-line explanation |
| `Header_Icon_Name__c` | An SLDS icon beside the title | Both | When other headers have icons |
| `Header_Text__c` | Rich text inside the header | The form | Longer guidance |
| `Header_Text_Variant__c` | The header text as plain text or a message card | The form | A note that must stand out |
| `Header_Display__c` | The header as the standard header or as a divider | Both | With the page's style |
| `Header_Divider_Style__c` | The divider style when the header is a divider | Both | With Divider |
| `Header_Style__c` | Classic (inside the frame) or outlined (on the border) | The form | With a framed section |
| `Header_Top_Margin__c` | Space above the header | Both | Rarely |
| `Header_Kicker__c` | Stacked style: a short line above the title | The form | Stacked headers only |
| `Header_Lead__c` | Stacked style: the body under the title | The form | Stacked headers only |
| `Header_Tags__c` | Stacked style: pills, separated by semicolons | The form | Stacked headers only |
| `Header_Tags_Position__c` | Stacked style: where the pills sit | The form | Stacked headers only |
| `Header_Footer__c` | Stacked style: the header's last line | The form | Stacked headers only |
| `Header_Bottom_Margin__c` | Stacked style: the gap under the header | The form | Stacked headers only |
| `Section_Frame__c` | The box round the section: clean, box or shadow | The form | As the plan's frame |
| `Top_Margin__c` | Space above the whole section | The form | As the plan's spacing |
| `Field_Set_Show_Divider__c` | Shows the section's own divider | The form | When the plan asks |
| `Divider_Style__c` | That divider's style | The form | With the divider on |
| `Divider_Position__c` | Above or below the section | The form | With the divider on |
| `Divider_Title__c` | Text on the divider | The form | With the divider on |
| `Divider_Subtitle__c` | Second line on the divider | The form | With the divider on |
| `Divider_Icon_Name__c` | Icon on the divider | The form | With the divider on |
| `Divider_Vertical_Margin__c` | Extra space round the divider | The form | With the divider on |
| `Conditional_Logic__c` | The rule that shows or hides the whole section | The form | A section only some people answer |
| `Do_Not_Print__c` | Leaves the section out of the answers PDF. An empty Table is already left out | PDF | Screen-only content |

### Never written

| Property | What it does | Read by | When to set it |
|---|---|---|---|
| `isTable__c` | A formula, checked when the type is Table | Both | Never |
| `FlowApiName_Related__c` | A formula: the flow the rows will run | Conversion | Never: read it to confirm the wiring |

## Flow screen properties

The **Form (Table)** component on a screen. `object` and `formQualifiedApiName` are required; every other input is optional. `scripts/table.py flow-screen` writes the common ones from the spec; any other goes in `flow.properties` by name.

### The table and its forms

| Property | What it does | When to set it |
|---|---|---|
| `object` | The rows' object API name (required) | Always (the script writes it) |
| `formQualifiedApiName` | The table component by name (required unless JSON) | A component by name |
| `formJSON` | The table component's JSON, fixed to this screen | JSON shape |
| `formJsonEnabled` | Reads the table from `formJSON` | With `formJSON` |
| `dynamicFormSelectorEnabled` | Lets a text variable choose the table at run time | Rarely |
| `overrideTableFormName` | The row form for New, Edit and Clone, by name; without it the table component's own default row form | Whenever New, Edit or Clone is on |
| `overrideTableFormBulkName` | The form for editing, resetting or deleting several selected rows at once | With a bulk action |
| `recordTemplate` | A record whose values seed every new row | New rows need defaults |
| `recordTypeOptions` | Record types offered for new rows | Objects with record types |
| `stampFormQualifiedApiName` | Writes the row form's name onto each new or cloned row | Rows that must remember their form |
| `languageOverride` | Shows the table in this language | A form in a fixed language |

### Rows

| Property | What it does | When to set it |
|---|---|---|
| `prefillRecords` | Rows in and out: the collection the table shows and hands back changed, removed saved rows flagged `IsDeleted` | Always bind it to a record collection variable |
| `bypassPrefillMaintain` | Replaces the rows with the collection whenever it changes, dropping rows added, selected or changed on screen | A screen action that reloads the rows |
| `min` | Passed, not enforced by the table in this package version | Leave blank |
| `max` | The same | Leave blank |
| `recordsToLoad` | How many rows load at a time as people scroll (default 20) | Long tables |
| `minRowHeight` | The table's height, counted in rows (default 5) | Short or tall tables |
| `tableHeight` | The table's height in pixels (default 300) | A fixed height |

### Actions

| Property | What it does | When to set it |
|---|---|---|
| `allowNew` | Shows New | People add rows |
| `newButtonLabel` | New's text | Wording such as "Add" |
| `allowEdit` | Shows Edit on each row | Almost always |
| `editButtonLabel` | Edit's text | When "Edit" reads wrong |
| `allowBulkEdit` | Shows Edit for several selected rows; only with a bulk form and Edit on | Rows changed in groups |
| `allowClone` | Shows Clone on each row | Rows mostly alike |
| `cloneButtonLabel` | Clone's text | With Clone on |
| `allowDelete` | Shows Delete on each row | People remove rows |
| `allowBulkDelete` | Shows Delete for several selected rows; only with a bulk form | Rows removed in groups |
| `deleteButtonLabel` | Delete's text | "Remove" for people |
| `allowReset` | Shows Reset on each row: puts a row back as it was when the screen opened (a new row is removed) | Screens where people experiment |
| `allowBulkReset` | Reset for several selected rows; only with a bulk form | The same, in groups |
| `resetButtonLabel` | Reset's text | With Reset on |
| `allowResetTable` | Shows Reset Table, which puts every row back | The same |
| `navigateOnNew` | Moves the flow forward after New | A flow that handles each action itself |
| `navigateOnEdit` | Moves forward after Edit | The same |
| `navigateOnClone` | Moves forward after Clone | The same |
| `navigateOnDelete` | Moves forward after Delete | The same |
| `navigateOnReset` | Moves forward after Reset | The same |
| `navigateOnSelect` | Moves forward on selection | One-click choices |

### Windows

| Property | What it does | When to set it |
|---|---|---|
| `newRecordModalHeading` | The add window's title | With New |
| `newRecordModalSubheading` | The add window's subtitle | With New |
| `editModalHeading` | The edit window's title | With Edit |
| `editModalSubheading` | The edit window's subtitle | With Edit |
| `cloneRecordModalHeading` | The clone window's title | With Clone |
| `cloneRecordModalSubheading` | The clone window's subtitle | With Clone |
| `deleteModalHeading` | The delete confirmation's title | With Delete |
| `deleteModalSubheading` | Its subtitle | With Delete |
| `deleteModalBody` | Its message | With Delete |
| `disableDeleteModalMessage` | Deletes without the confirmation | Rarely |
| `resetModalHeading` | The reset confirmation's title | With Reset |
| `resetModalSubheading` | Its subtitle | With Reset |
| `resetModalBody` | Its message | With Reset |
| `resetTableModalHeading` | The Reset Table confirmation's title | With Reset Table |
| `resetTableModalSubheading` | Its subtitle | With Reset Table |
| `resetTableBody` | Its message | With Reset Table |

### Display

| Property | What it does | When to set it |
|---|---|---|
| `showRowNumberColumn` | A numbered first column | Long lists people refer to by number |
| `showCheckBoxColumn` | A selection checkbox column | Bulk actions or picking rows |
| `hideTableHeader` | Hides the column headers | Self-explanatory columns |
| `hideTableFooter` | Hides the footer | A compact table |
| `disableColumnResize` | Stops people resizing columns | Fixed layouts |
| `minColumnWidth` | Narrowest column, in pixels | Many columns |
| `maxColumnWidth` | Widest column, in pixels (default 2000) | Long text columns |
| `tableRowClass` | Row look: `hideBorders`, `slds-table_striped`, `slds-table_col-bordered` | As the design shows |
| `disableRowActionIndicators` | Removed rows disappear instead of staying, marked, with a way to undo | A cleaner list |
| `urlTarget` | Where URL columns open (default a new tab, so the flow is not left) | Rarely |
| `displayAsDataTree` | Shows rows as a tree grouped by a parent field | Parent and child rows |
| `hierarchyFieldName` | The parent field for the tree | With the tree |
| `treeHideCollapseButtons` | The tree starts expanded with no collapse buttons | With the tree |
| `enableFilter` | Shows a search box that filters the rows. A text input: any value turns it on, so set it only to turn it on | Long tables |
| `minSearchString` | Characters typed before the filter applies (at least 2) | With the filter |
| `bottomMargin` | Space below the component | Rarely |
| `topMargin` | Space above the header | Rarely |
| `themeOverrideName` | A Form Theme for the row and bulk forms | A screen styled apart |
| `themeHeaderName` | A Form Theme for the table header | Rarely |

### Header

| Property | What it does | When to set it |
|---|---|---|
| `showHeader` | Shows the header | When the screen does not already title the table |
| `title` | The header's title | Always when shown |
| `subtitle` | The line under the title | A short explanation |
| `iconName` | The header icon | As the screen's other headers |
| `helpText` | Help beside the title | Brief guidance |

### The forms in the windows

| Property | What it does | When to set it |
|---|---|---|
| `enableAccordion` | The row form's sections as collapsible panels | Long row forms |
| `requireAll` | Every question in the row form required | Rarely |
| `disableAll` | The table read-only, actions hidden | A summary |
| `disableAllHeaders` | Hides the row form's section headers | Compact windows |
| `displayPrompts` | Shows the row form's prompts | When the component uses prompts |

### Selection

| Property | What it does | When to set it |
|---|---|---|
| `maxRowSelection` | The most rows that may be selected (default 50) | With selection |
| `minRowSelection` | The fewest rows that must be selected before the flow moves on | A choice that is required |
| `selectionReturnFieldValue` | The field whose values fill the Selected Value(s) outputs | With selection |
| `searchValue` | What the person typed in the filter (also an input to start with a filter) | Rarely |

### A second footer button

| Property | What it does | When to set it |
|---|---|---|
| `button2Enabled` | Adds a button of its own to the table's footer | A table action the flow handles |
| `type2` | What it does: NEXT and the other navigation types (default NEXT) | With the button |
| `label2` | Its text (default Continue) | With the button |
| `variant2` | Its style | With the button |
| `iconName2` | Its icon | With the button |
| `iconPosition2` | Icon left or right (default Right) | With the button |
| `triggerName2` | A name the flow can listen for | With the button |
| `enableModal2` | Asks for confirmation first | A button with consequences |
| `modalHeading2` | The confirmation's title | With the confirmation |
| `modalSubheading2` | Its subtitle | With the confirmation |
| `modalBody2` | Its message | With the confirmation |
| `modalTheme2` | Its colour theme | With the confirmation |
| `modalConfirmButtonLabel2` | Its confirm text | With the confirmation |
| `modalCancelButtonLabel2` | Its cancel text | With the confirmation |
| `bypassValidation2` | Moves on without checking the rows | Rarely |
| `reCAPTCHA_Enabled2` | Runs reCAPTCHA before the button acts | Public screens |
| `reCAPTCHA_Threshold2` | The reCAPTCHA score needed | With reCAPTCHA |
| `enable_AutoAction2` | Presses the button by itself after a timeout | Rarely |
| `autoActionTimeout2` | The timeout in milliseconds (default 10000) | With the auto action |
| `customButtons` | Apex-defined buttons that replace the default navigation | A flow with its own button set |

### Outputs (read them; never set them)

| Property | What it does | When to set it |
|---|---|---|
| `insertCollection` | Rows to insert | A flow that saves rows of its own object |
| `updateCollection` | Rows to update | The same |
| `deleteCollection` | Rows to delete | The same |
| `insertCollectionSize` | How many to insert | Decisions on the count |
| `updateCollectionSize` | How many to update | Decisions on the count |
| `deleteCollectionSize` | How many to delete | Decisions on the count |
| `prefillCollectionSize` | Rows shown, removed ones excluded | "At least one" checks |
| `recordsCollectionChangedTrigger` | A time stamp each time any row is added, cloned, changed or removed | Reactive screen components |
| `insertCollectionChangedTrigger` | The same, for added and cloned rows | Reactive screens |
| `updateCollectionChangedTrigger` | The same, for changed rows | Reactive screens |
| `deleteCollectionChangedTrigger` | The same, for removed rows | Reactive screens |
| `activeRow` | The row being added, edited or cloned | Reactive components beside the table |
| `calculationResultRecord` | A record with the column totals the table component asks for (over the selected rows when some are selected) | Totals |
| `action` | Which action was taken, when a Navigate On setting moved the flow | A flow that handles each action |
| `selectedRecords` | The selected rows (also an input: bind it to keep the selection on Back) | With selection |
| `firstSelectedRow` | The first selected row | Single choice |
| `selectedCollectionSize` | How many are selected | With selection |
| `selectedRecordsIds` | Their Ids | With selection |
| `selectedRecordsIdsString` | The same as one text value, for component visibility | With selection |
| `selectedRecordsValues` | Their `selectionReturnFieldValue` values | With selection |
| `selectedRecordsValuesString` | The same as one text value | With selection |
| `actionClickedDateTime` | When the second footer button was clicked | With the button |
| `buttonClicked` | The custom button clicked | With custom buttons |
| `buttonClickedLabel` | Its label | With custom buttons |
| `buttonClickedValue` | Its value | With custom buttons |
| `buttonClickedDateTime` | When it was clicked | With custom buttons |

### Set from the flow itself

| Property | What it does | When to set it |
|---|---|---|
| `interviewGuid` | The interview's Id, so the page's buttons reach this component | Always `{!$Flow.InterviewGuid}` (the script writes it) |
| `interviewStartDateTime` | The interview's start | Always `{!$Flow.InterviewStartTime}` |
| `serverURL` | The server address, for the Experience Cloud path | Always `{!$Api.Enterprise_Server_URL_140}` |
| `elementApiName` | A key that tells two components on one screen apart | Two tables on one screen |
