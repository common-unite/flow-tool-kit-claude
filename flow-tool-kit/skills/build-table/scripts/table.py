#!/usr/bin/env python3
"""Write and check a Flow Tool Kit Table: a page section's settings, or a Form (Table) flow screen component.

    python3 table.py check <spec.json> [--org-tags Default,Contacts,...]
    python3 table.py section <spec.json> [--format plan|record] [--namespace FlowToolKit] [--out <file>]
    python3 table.py flow-screen <spec.json> [--namespace FlowToolKit] [--out <file>]

check prints every finding and exits 1 on any error. section writes the page section fields: plan keys to put on the
section in plan.json (build-template keeps them on every rebuild), or namespaced fields to update an existing
section record. flow-screen writes the <fields> element for a screen. Both refuse a spec with errors.

Exit codes: 0 clean (warnings allowed), 1 errors found, 2 a malformed spec or argument.
Python 3 standard library only. Works the same in claude.ai chat (code execution) and Claude Code.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # keep _shared/ exactly as the sync script wrote it
sys.path.insert(0, str(HERE.parent / "_shared" / "lib"))
import repeating as rp  # noqa: E402

ROW_STYLES = ("hideBorders", "slds-table_striped", "slds-table_col-bordered")

# Table display settings: spec key -> (page section field, flow screen property)
DISPLAY = {
    "row_numbers": ("Table_Display_Row_Numbers__c", "showRowNumberColumn"),
    "hide_column_headers": ("Table_Hide_Column_Headers__c", "hideTableHeader"),
    "hide_footer": ("Table_Hide_Footer__c", "hideTableFooter"),
    "prevent_column_resize": ("Table_Prevent_Column_Resize__c", "disableColumnResize"),
    "disable_row_action_indicators": ("Table_Disable_Row_Action_Indicators__c", "disableRowActionIndicators"),
    "row_style": ("Table_Row_Style__c", "tableRowClass"),
}
# Window wording: (action, spec key) -> (page section field, flow screen property)
MODALS = {
    ("new", "modal_title"): ("Table_New_Action_Modal_Title__c", "newRecordModalHeading"),
    ("new", "modal_subtitle"): ("Table_New_Action_Modal_Subtitle__c", "newRecordModalSubheading"),
    ("edit", "modal_title"): ("Edit_Action_Modal_Title__c", "editModalHeading"),
    ("edit", "modal_subtitle"): ("Edit_Action_Modal_Subtitle__c", "editModalSubheading"),
    ("clone", "modal_title"): ("Table_Clone_Action_Modal_Title__c", "cloneRecordModalHeading"),
    ("clone", "modal_subtitle"): ("Table_Clone_Action_Modal_Subtitle__c", "cloneRecordModalSubheading"),
    ("delete", "modal_title"): ("Table_Delete_Action_Modal_Title__c", "deleteModalHeading"),
    ("delete", "modal_subtitle"): ("Table_Delete_Action_Modal_Subtitle__c", "deleteModalSubheading"),
    ("delete", "modal_body"): ("Table_Delete_Action_Modal_Body__c", "deleteModalBody"),
}

# Page section fields a Table section reads (references/properties.md).
SECTION_FIELDS = {
    "Component_Type__c", "Title__c", "FormQualifiedApiName__c", "FormConfigJSON__c", "Form_Component__c",
    "Alternate_FormQualifiedApiName__c", "Edit_FormQualifiedApiName__c", "Bulk_FormQualifiedApiName__c",
    "Min__c", "Max__c", "Enable_New_Action__c", "New_Action_Button_Label__c", "Enable_Edit_Action__c",
    "Edit_Action_Button_Label__c", "Enable_Clone_Action__c", "Clone_Action_Button_Label__c",
    "Enable_Delete_Action__c", "Delete_Action_Button_Label__c", "Bottom_Margin__c", "Prefill_Template__c",
    "Section_Tag__c", "Conversion_Rule__c", "Conversion_Map_Flow__c", "Add_to_Account__c", "Add_to_Campaign__c",
    "Contact_Matching_Rules__c", "Lead_Matching_Rules__c", "Contact_Record_Type__c", "Case_Record_Type__c",
    "Update_Most_Confident_Contact__c", "Update_Most_Confident_Lead__c", "Data_Conversion_Tag_s__c",
    "Show_Header__c", "Header_Display__c", "Header_Divider_Style__c", "Header_Style__c", "Header_Kicker__c",
    "Header_Lead__c", "Header_Tags__c", "Header_Tags_Position__c", "Header_Footer__c", "Header_Bottom_Margin__c",
    "Header_Title__c", "Header_Subtitle__c", "Header_Icon_Name__c", "Header_Top_Margin__c", "Header_Text__c",
    "Header_Text_Variant__c", "Section_Frame__c", "Top_Margin__c", "Component_Section_Text__c",
    "Conditional_Logic__c", "Do_Not_Print__c", "Field_Set_Show_Divider__c", "Divider_Style__c",
    "Divider_Position__c", "Divider_Title__c", "Divider_Subtitle__c", "Divider_Icon_Name__c",
    "Divider_Vertical_Margin__c",
} | {field for field, _ in DISPLAY.values()} | {field for field, _ in MODALS.values()}
READ_ONLY_SECTION_FIELDS = {"isTable__c", "FlowApiName_Related__c"}

# Form (Table) flow screen properties: name -> (type, role, label, default), from the component's metadata.
FLOW_PROPERTIES = {
    "object": ("String", "inputOnly", "Object Name", ""),
    "formQualifiedApiName": ("String", "inputOnly", "Form.QualifiedApiName", ""),
    "dynamicFormSelectorEnabled": ("Boolean", "inputOnly", "dynamicFormSelectorEnabled", "false"),
    "recordTemplate": ("{T}", "inputOnly", "Record", ""),
    "recordTypeOptions": ("@salesforce/schema/RecordType[]", "inputOnly", "Record Type Options", ""),
    "overrideTableFormName": ("String", "inputOnly", "Override Table Record Edit Form", ""),
    "overrideTableFormBulkName": ("String", "inputOnly", "Override Table Record Bulk Edit Form", ""),
    "prefillRecords": ("{T[]}", "", "Prefill Collection", ""),
    "updateCollection": ("{T[]}", "outputOnly", "Update Collection", ""),
    "deleteCollection": ("{T[]}", "outputOnly", "Delete Collection", ""),
    "insertCollection": ("{T[]}", "outputOnly", "Insert Collection", ""),
    "prefillCollectionSize": ("Integer", "outputOnly", "Prefill Collection Size", ""),
    "updateCollectionSize": ("Integer", "outputOnly", "Update Collection Size", ""),
    "deleteCollectionSize": ("Integer", "outputOnly", "Delete Collection Size", ""),
    "insertCollectionSize": ("Integer", "outputOnly", "Insert Collection Size", ""),
    "recordsCollectionChangedTrigger": ("DateTime", "outputOnly", "Prefill Records Changed Trigger", ""),
    "updateCollectionChangedTrigger": ("DateTime", "outputOnly", "Update Records Changed Trigger", ""),
    "insertCollectionChangedTrigger": ("DateTime", "outputOnly", "Insert Records Changed Trigger", ""),
    "deleteCollectionChangedTrigger": ("DateTime", "outputOnly", "Delete Records Changed Trigger", ""),
    "calculationResultRecord": ("{T}", "outputOnly", "Calculation Result(s)", ""),
    "activeRow": ("{T}", "outputOnly", "Active Row", ""),
    "selectionReturnFieldValue": ("String", "inputOnly", "Selection Return Field Value", ""),
    "firstSelectedRow": ("{T}", "outputOnly", "Selected Record (First Selected Row)", ""),
    "selectedRecords": ("{T[]}", "", "Selected Records", ""),
    "selectedCollectionSize": ("Integer", "outputOnly", "Selected Collection Size", ""),
    "selectedRecordsIds": ("String[]", "outputOnly", "Selected Id(s) Collection", ""),
    "selectedRecordsIdsString": ("String", "outputOnly", "Selected Id(s) (Text)", ""),
    "selectedRecordsValues": ("String[]", "outputOnly", "Selected Value(s) (Collection)", ""),
    "selectedRecordsValuesString": ("String", "outputOnly", "Selected Value(s) (Text)", ""),
    "max": ("Integer", "inputOnly", "Maximum Number of Records", ""),
    "min": ("Integer", "inputOnly", "Minimum Number of Records", ""),
    "urlTarget": ("String", "inputOnly", "urlTarget", ""),
    "minRowHeight": ("Integer", "inputOnly", "Minimum Row Height", "5"),
    "recordsToLoad": ("Integer", "inputOnly", "Records to Load", ""),
    "displayAsDataTree": ("Boolean", "inputOnly", "Display as Hierarchy Tree", ""),
    "hierarchyFieldName": ("String", "inputOnly", "Hierarchy Field Name", ""),
    "treeHideCollapseButtons": ("Boolean", "inputOnly", "Data Tree Hide Collapse Buttons", ""),
    "disableColumnResize": ("Boolean", "inputOnly", "Disable Column Resize", ""),
    "minColumnWidth": ("Integer", "inputOnly", "Min Column Width", ""),
    "maxColumnWidth": ("Integer", "inputOnly", "Max Column Width", ""),
    "maxRowSelection": ("Integer", "inputOnly", "Max Row Selection", ""),
    "minRowSelection": ("Integer", "inputOnly", "Min Row Selection", ""),
    "showRowNumberColumn": ("Boolean", "inputOnly", "Show Row Number Column", ""),
    "showCheckBoxColumn": ("Boolean", "inputOnly", "Show Checkbox Column", ""),
    "hideTableHeader": ("Boolean", "inputOnly", "Hide Tables Column Headers", ""),
    "hideTableFooter": ("Boolean", "inputOnly", "Hide Table Footer", ""),
    "tableRowClass": ("String", "inputOnly", "Table Row Class", ""),
    "disableRowActionIndicators": ("Boolean", "inputOnly", "disableRowActionIndicators", "false"),
    "stampFormQualifiedApiName": ("Boolean", "inputOnly", "Stamp FormQualifiedApiName", ""),
    "bypassPrefillMaintain": ("Boolean", "inputOnly", "bypassPrefillMaintain", "false"),
    "formJSON": ("String", "inputOnly", "Form (JSON)", ""),
    "formJsonEnabled": ("Boolean", "inputOnly", "formJsonEnabled", "false"),
    "languageOverride": ("String", "", "Language Override", ""),
    "tableHeight": ("Integer", "inputOnly", "tableHeight", ""),
    "button2Enabled": ("Boolean", "inputOnly", "button2Enabled", "false"),
    "type2": ("String", "inputOnly", "type", "NEXT"),
    "triggerName2": ("String", "inputOnly", "triggerName", ""),
    "label2": ("String", "inputOnly", "label", "Continue"),
    "variant2": ("String", "inputOnly", "variant", "variant"),
    "iconName2": ("String", "inputOnly", "iconName", ""),
    "iconPosition2": ("String", "inputOnly", "iconPosition", "Right"),
    "enableModal2": ("Boolean", "inputOnly", "enableModal", "false"),
    "modalHeading2": ("String", "inputOnly", "modalHeading", ""),
    "modalSubheading2": ("String", "inputOnly", "modalSubheading", ""),
    "modalTheme2": ("String", "inputOnly", "modalTheme", "slds-theme_default"),
    "modalBody2": ("String", "inputOnly", "modalBody", ""),
    "modalConfirmButtonLabel2": ("String", "inputOnly", "modalConfirmButtonLabel", "Confirm"),
    "modalCancelButtonLabel2": ("String", "inputOnly", "modalCancelButtonLabel", "Confirm"),
    "bypassValidation2": ("Boolean", "inputOnly", "bypassValidation", "false"),
    "reCAPTCHA_Threshold2": ("Integer", "inputOnly", "reCAPTCHA_Threshold", ""),
    "reCAPTCHA_Enabled2": ("Boolean", "inputOnly", "reCAPTCHA_Enabled", "false"),
    "actionClickedDateTime": ("DateTime", "outputOnly", "Action Clicked (Trigger)", ""),
    "enable_AutoAction2": ("Boolean", "inputOnly", "enable_AutoAction", "false"),
    "autoActionTimeout2": ("String", "inputOnly", "autoActionTimeout", "10000"),
    "editModalHeading": ("String", "inputOnly", "Edit Modal Heading", ""),
    "editModalSubheading": ("String", "inputOnly", "Edit Modal Subheading", ""),
    "newRecordModalHeading": ("String", "inputOnly", "New Modal Heading", ""),
    "newRecordModalSubheading": ("String", "inputOnly", "New Modal Subheading", ""),
    "cloneRecordModalHeading": ("String", "inputOnly", "Clone Modal Heading", ""),
    "cloneRecordModalSubheading": ("String", "inputOnly", "Clone Modal Subheading", ""),
    "deleteModalHeading": ("String", "inputOnly", "Delete Modal Heading", ""),
    "deleteModalSubheading": ("String", "inputOnly", "Delete Modal Subheading", ""),
    "deleteModalBody": ("String", "inputOnly", "Delete Modal Body", ""),
    "disableDeleteModalMessage": ("Boolean", "inputOnly", "disableDeleteModalMessage", ""),
    "resetModalHeading": ("String", "inputOnly", "Reset Modal Heading", ""),
    "resetModalSubheading": ("String", "inputOnly", "Reset Modal Subheading", ""),
    "resetModalBody": ("String", "inputOnly", "Reset Modal Body", ""),
    "resetTableModalHeading": ("String", "inputOnly", "Reset Table Modal Heading", ""),
    "resetTableModalSubheading": ("String", "inputOnly", "Reset Table Modal Subheading", ""),
    "resetTableBody": ("String", "inputOnly", "Reset Table Modal Body", ""),
    "allowClone": ("Boolean", "inputOnly", "Show Clone Button", ""),
    "cloneButtonLabel": ("String", "inputOnly", "Clone Button Label", ""),
    "allowDelete": ("Boolean", "inputOnly", "Show Delete Button", ""),
    "allowBulkDelete": ("Boolean", "inputOnly", "Show Bulk Delete Button", ""),
    "deleteButtonLabel": ("String", "inputOnly", "Delete Button Label", ""),
    "allowNew": ("Boolean", "inputOnly", "Show New Button", ""),
    "newButtonLabel": ("String", "inputOnly", "New Button Label", ""),
    "allowEdit": ("Boolean", "inputOnly", "Show Edit Button", ""),
    "allowBulkEdit": ("Boolean", "inputOnly", "Show Bulk Edit Button", ""),
    "editButtonLabel": ("String", "inputOnly", "Edit Button Label", ""),
    "allowReset": ("Boolean", "inputOnly", "Show Reset Button", ""),
    "allowBulkReset": ("Boolean", "inputOnly", "Show Bulk Reset Button", ""),
    "resetButtonLabel": ("String", "inputOnly", "Reset Button Label", ""),
    "allowResetTable": ("Boolean", "inputOnly", "Show Reset Table Button", ""),
    "navigateOnSelect": ("Boolean", "inputOnly", "Navigate on Select", ""),
    "navigateOnNew": ("Boolean", "inputOnly", "Navigate on New", ""),
    "navigateOnEdit": ("Boolean", "inputOnly", "Navigate on Edit", ""),
    "navigateOnDelete": ("Boolean", "inputOnly", "Navigate on Delete", ""),
    "navigateOnClone": ("Boolean", "inputOnly", "Navigate on Clone", ""),
    "navigateOnReset": ("Boolean", "inputOnly", "Navigate on Reset", ""),
    "action": ("String", "outputOnly", "action", ""),
    "minSearchString": ("Integer", "inputOnly", "Minimum Search String", ""),
    "searchValue": ("String", "", "Search/Filter Value", ""),
    "enableFilter": ("String", "inputOnly", "Enable Filter", ""),
    "bottomMargin": ("String", "inputOnly", "Bottom Margin", "slds-m-bottom_none"),
    "themeOverrideName": ("String", "inputOnly", "Theme Override", ""),
    "themeHeaderName": ("String", "inputOnly", "Theme Header", ""),
    "enableAccordion": ("Boolean", "inputOnly", "Enable Accordion", "false"),
    "requireAll": ("Boolean", "inputOnly", "Require All", "false"),
    "disableAll": ("Boolean", "inputOnly", "Disable All", "false"),
    "disableAllHeaders": ("Boolean", "inputOnly", "Disable All Headers", "false"),
    "displayPrompts": ("Boolean", "inputOnly", "Display Prompts", "false"),
    "title": ("String", "inputOnly", "Title", ""),
    "subtitle": ("String", "inputOnly", "Subtitle", ""),
    "helpText": ("String", "inputOnly", "Help Text", ""),
    "topMargin": ("String", "inputOnly", "Margin-Top", ""),
    "iconName": ("String", "inputOnly", "Icon Name", ""),
    "showHeader": ("Boolean", "inputOnly", "Show Header", ""),
    "customButtons": ("apex://FlowToolKit.Button[]", "inputOnly", "1) Custom Buttons (Optional)", ""),
    "buttonClicked": ("apex://FlowToolKit.Button", "outputOnly", "Button Clicked", ""),
    "buttonClickedLabel": ("String", "outputOnly", "Button Clicked (Label)", ""),
    "buttonClickedValue": ("String", "outputOnly", "Button Clicked (Value)", ""),
    "buttonClickedDateTime": ("DateTime", "outputOnly", "Button Clicked (DateTime)", ""),
    "interviewGuid": ("String", "inputOnly", "interviewGuid", ""),
    "interviewStartDateTime": ("DateTime", "inputOnly", "interviewStartDateTime", ""),
    "elementApiName": ("String", "inputOnly", "elementApiName", ""),
    "serverURL": ("String", "inputOnly", "serverURL", ""),
}


def check(spec, org_tags=None):
    out = rp.check_common(spec, org_tags)
    table = spec.get("table") or {}
    section = spec["where"] == "section"
    if spec.get("repeater"):
        out.append(rp.error("kind", "repeater settings on a Table spec; a Repeater is built by build-repeater"))
    row_form, bulk_form = table.get("row_form"), table.get("bulk_form")
    opens_window = [name for name in ("new", "edit", "clone") if rp.action(spec, name)[0]]
    if opens_window and not row_form and not table.get("component_has_row_form"):
        out.append(rp.error("row_form", "%s open%s a window with the row's questions: set table.row_form (the "
                            "form component with every question of one row), or component_has_row_form when the "
                            "table component names its own" % (", ".join(opens_window).capitalize(),
                                                             "s" if len(opens_window) == 1 else "")))
    for key, value in (("row_form", row_form), ("bulk_form", bulk_form)):
        if value is None:
            continue
        if not isinstance(value, str) or not rp.API_NAME.match(value):
            out.append(rp.error(key, "table.%s is a component's API name (a record component as <Name>_v0, or a "
                                "metadata component): the window loads its form by name, never JSON" % key))
        elif value == spec.get("component"):
            out.append(rp.error(key, "table.%s is the table component itself; the window needs a form component "
                                "with every question of one row" % key))
    if table.get("row_style") is not None and table["row_style"] not in ROW_STYLES:
        out.append(rp.error("layout", "table.row_style is one of %s" % ", ".join(ROW_STYLES)))
    for key in table:
        if key not in DISPLAY and key not in ("row_form", "bulk_form", "component_has_row_form", "bulk_edit"):
            out.append(rp.error("table", "table.%s is not a Table setting" % key))
    for (name, key), _ in MODALS.items():
        on, settings = rp.action(spec, name)
        if settings.get(key) and not on:
            out.append(rp.warning("modals", "actions.%s.%s is set but %s is off" % (name, key, name.capitalize())))
    for name in rp.ACTIONS:
        _, settings = rp.action(spec, name)
        for key in settings:
            if key not in ("label",) and (name, key) not in MODALS:
                out.append(rp.error("modals", "actions.%s.%s is not a Table window setting" % (name, key)))
    if section:
        out += rp.check_extra(spec, SECTION_FIELDS, "Table page section")
        for name in (spec.get("extra") or {}):
            if name in READ_ONLY_SECTION_FIELDS:
                out.append(rp.error("extra", "%s is calculated by the package; never write it" % name))
        shown = [key for key in DISPLAY if key in table]
        if shown:
            out.append(rp.warning("display", "the form itself does not apply %s in the package version these notes "
                                  "were read from (only the Page Section Preview on a record page does): set them, "
                                  "then check Preview Form before promising them" % ", ".join(shown)))
        if bulk_form or table.get("bulk_edit"):
            out.append(rp.warning("bulk", "a page section never turns on bulk edit, so the bulk form is not used "
                                  "there; bulk edit works on a flow screen"))
        if spec.get("flow"):
            out.append(rp.error("where", "flow settings on a page section spec; set where to flow-screen"))
    else:
        out += rp.check_flow_common(spec, FLOW_PROPERTIES)
        if table.get("bulk_edit") and not bulk_form:
            out.append(rp.error("bulk", "bulk edit shows only with a bulk form: set table.bulk_form"))
        if table.get("bulk_edit") and not rp.action(spec, "edit")[0]:
            out.append(rp.error("bulk", "bulk edit needs Edit on"))
    return out


def section(spec, record=False, namespace=rp.DEFAULT_NAMESPACE):
    fields = rp.section_fields(spec, record=record, namespace=namespace)
    table = spec.get("table") or {}
    if table.get("row_form"):
        # The form reads Edit_FormQualifiedApiName__c; the Page Section Preview reads Alternate. Write both.
        fields["Edit_FormQualifiedApiName__c"] = table["row_form"]
        fields["Alternate_FormQualifiedApiName__c"] = table["row_form"]
    if table.get("bulk_form"):
        fields["Bulk_FormQualifiedApiName__c"] = table["bulk_form"]
    for key, (field, _) in DISPLAY.items():
        if key in table:
            fields[field] = table[key]
    for (name, key), (field, _) in MODALS.items():
        on, settings = rp.action(spec, name)
        if on and settings.get(key):
            fields[field] = settings[key]
    fields.update(spec.get("extra") or {})
    return fields


def flow_screen(spec, namespace=rp.DEFAULT_NAMESPACE):
    flow = spec.get("flow") or {}
    table = spec.get("table") or {}
    params = rp.flow_params_common(spec, namespace)
    if table.get("row_form"):
        params.append(("overrideTableFormName", "String", table["row_form"]))
    if table.get("bulk_form"):
        params.append(("overrideTableFormBulkName", "String", table["bulk_form"]))
    if table.get("bulk_edit"):
        params.append(("allowBulkEdit", "Boolean", True))
    for key, (_, prop) in DISPLAY.items():
        if key in table:
            params.append((prop, "String" if key == "row_style" else "Boolean", table[key]))
    for (name, key), (_, prop) in MODALS.items():
        on, settings = rp.action(spec, name)
        if on and settings.get(key):
            params.append((prop, "String", settings[key]))
    params = rp.dedupe_params(params + rp.flow_params_extra(spec, FLOW_PROPERTIES))
    extension = "%s:flowDataTable" % namespace if namespace else "flowDataTable"
    return rp.flow_field_xml(flow.get("element_name", "Table"), extension,
                             rp.namespaced_object(flow.get("object"), namespace), params)


def main(argv=None):
    return rp.run_cli(argv, "table", check, section, flow_screen, __doc__)


if __name__ == "__main__":
    sys.exit(main())
