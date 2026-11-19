#!/usr/bin/env python3
"""Write and check a Flow Tool Kit Repeater: a page section's settings, or a Form (Repeater) flow screen component.

    python3 repeater.py check <spec.json> [--org-tags Default,Contacts,...]
    python3 repeater.py section <spec.json> [--format plan|record] [--namespace FlowToolKit] [--out <file>]
    python3 repeater.py flow-screen <spec.json> [--namespace FlowToolKit] [--out <file>]

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

# Page section fields a Repeater section reads, besides the ones every spec key writes (references/properties.md).
SECTION_FIELDS = {
    "Component_Type__c", "Title__c", "FormQualifiedApiName__c", "FormConfigJSON__c", "Form_Component__c",
    "Min__c", "Max__c", "Enable_New_Action__c", "New_Action_Button_Label__c", "Enable_Clone_Action__c",
    "Clone_Action_Button_Label__c", "Enable_Delete_Action__c", "Delete_Action_Button_Label__c",
    "Enable_Edit_Action__c", "Edit_Action_Button_Label__c", "Edit_Action_Modal_Title__c",
    "Edit_Action_Modal_Subtitle__c", "Repeater_Record_Spacing__c", "Repeater_Hide_Divider__c", "Bottom_Margin__c",
    "Prefill_Template__c", "Section_Tag__c", "Conversion_Rule__c", "Conversion_Map_Flow__c", "Add_to_Account__c",
    "Add_to_Campaign__c", "Contact_Matching_Rules__c", "Lead_Matching_Rules__c", "Contact_Record_Type__c",
    "Case_Record_Type__c", "Update_Most_Confident_Contact__c", "Update_Most_Confident_Lead__c",
    "Data_Conversion_Tag_s__c", "Show_Header__c", "Header_Display__c", "Header_Divider_Style__c", "Header_Style__c",
    "Header_Kicker__c", "Header_Lead__c", "Header_Tags__c", "Header_Tags_Position__c", "Header_Footer__c",
    "Header_Bottom_Margin__c", "Header_Title__c", "Header_Subtitle__c", "Header_Icon_Name__c",
    "Header_Top_Margin__c", "Header_Text__c", "Header_Text_Variant__c", "Section_Frame__c", "Top_Margin__c",
    "Component_Section_Text__c", "Conditional_Logic__c", "Do_Not_Print__c", "Field_Set_Show_Divider__c",
    "Divider_Style__c", "Divider_Position__c", "Divider_Title__c", "Divider_Subtitle__c", "Divider_Icon_Name__c",
    "Divider_Vertical_Margin__c",
}
READ_ONLY_SECTION_FIELDS = {"isRepeater__c", "FlowApiName_Related__c"}

# Form (Repeater) flow screen properties: name -> (type, role, label, default), from the component's metadata.
FLOW_PROPERTIES = {
    "formRepeaterConfiguration": ("apex://FlowToolKit.FormRepeaterConfiguration", "inputOnly", "Form (Repeater) Configuration", ""),
    "allowImport": ("Boolean", "inputOnly", "Show Import Button", ""),
    "importButtonLabel": ("String", "inputOnly", "Import Button Label", ""),
    "repositionFieldApiName": ("String", "inputOnly", "Reposition FieldApiName", ""),
    "allowReposition": ("Boolean", "inputOnly", "Show Reposition Buttons", ""),
    "navigateOnReposition": ("Boolean", "inputOnly", "Navigate On Reposition", ""),
    "allowNew": ("Boolean", "inputOnly", "Show New Button", ""),
    "newButtonLabel": ("String", "inputOnly", "New Button Label", ""),
    "allowDelete": ("Boolean", "inputOnly", "Show Delete Button", ""),
    "deleteButtonLabel": ("String", "inputOnly", "Delete Button Label", ""),
    "allowClone": ("Boolean", "inputOnly", "Show Clone Button", ""),
    "cloneButtonLabel": ("String", "inputOnly", "Clone Button Label", ""),
    "max": ("Integer", "inputOnly", "Maximum Number of Records", "5"),
    "min": ("Integer", "inputOnly", "Minimum Number of Records", "1"),
    "formQualifiedApiName": ("String", "inputOnly", "Form.QualifiedApiName", ""),
    "dynamicFormSelectorEnabled": ("Boolean", "inputOnly", "dynamicFormSelectorEnabled", "false"),
    "object": ("String", "inputOnly", "Object Name", ""),
    "recordTemplate": ("{T}", "inputOnly", "Record", ""),
    "formJSON": ("String", "inputOnly", "Form (JSON)", ""),
    "formJsonEnabled": ("Boolean", "inputOnly", "formJsonEnabled", "false"),
    "languageOverride": ("String", "", "Language Override", ""),
    "editFormQualifiedApiName": ("String", "inputOnly", "Edit FormQualifiedApiName", ""),
    "allowEdit": ("Boolean", "inputOnly", "Show Edit Button", ""),
    "editButtonLabel": ("String", "inputOnly", "Edit Button Label", ""),
    "editModalReturnOnSelect": ("Boolean", "inputOnly", "Edit Modal Return On Select", ""),
    "editReturnButtonLabel": ("String", "inputOnly", "Edit Return Button Label", ""),
    "editModalHeading": ("String", "inputOnly", "Edit Modal Heading", ""),
    "editModalSubheading": ("String", "inputOnly", "Edit Modal Subheading", ""),
    "prefillRecords": ("{T[]}", "", "Prefill Collection", ""),
    "updateCollection": ("{T[]}", "outputOnly", "Update Collection", ""),
    "deleteCollection": ("{T[]}", "outputOnly", "Delete Collection", ""),
    "insertCollection": ("{T[]}", "outputOnly", "Insert Collection", ""),
    "prefillRecordsSize": ("Integer", "outputOnly", "Prefill Collection Size", ""),
    "totalRecordsSize": ("Integer", "outputOnly", "Total Record(s)", ""),
    "updateCollectionSize": ("Integer", "outputOnly", "Update Collection Size", ""),
    "deleteCollectionSize": ("Integer", "outputOnly", "Delete Collection Size", ""),
    "insertCollectionSize": ("Integer", "outputOnly", "Insert Collection Size", ""),
    "displayRepeaterButtonsAbove": ("Boolean", "inputOnly", "displayRepeaterButtonsAbove", ""),
    "stampFormQualifiedApiName": ("Boolean", "inputOnly", "Stamp FormQualifiedApiName", ""),
    "hideDivider": ("Boolean", "inputOnly", "Hide Divider", ""),
    "selectionReturnFieldValue": ("String", "inputOnly", "Selection Return Field Value", ""),
    "maxSelection": ("Integer", "inputOnly", "Max Selection Size", ""),
    "allowViewDetails": ("Boolean", "inputOnly", "Allow View Details", ""),
    "viewDetailsNavigateOnSelect": ("Boolean", "inputOnly", "View Details Navigate on Select", ""),
    "viewDetailsButtonLabel": ("String", "inputOnly", "View Details Button Label", ""),
    "viewDetailsTarget": ("String", "inputOnly", "View Details Target", ""),
    "viewDetailsUrlField": ("String", "inputOnly", "View Details Url Field Value", ""),
    "allowSelect": ("Boolean", "inputOnly", "Allow Selection", ""),
    "hideSelectButton": ("Boolean", "inputOnly", "Rows control selection", ""),
    "navigateOnSelect": ("Boolean", "inputOnly", "navigateOnSelect", ""),
    "navigateToRecordOnSelect": ("Boolean", "inputOnly", "navigateToRecordOnSelect", ""),
    "showSelectedOnly": ("Boolean", "inputOnly", "Show Selected Only", ""),
    "selectLabelWhenOff": ("String", "inputOnly", "selectLabelWhenOff", ""),
    "selectLabelWhenOn": ("String", "inputOnly", "selectLabelWhenOn", ""),
    "selectLabelWhenHover": ("String", "inputOnly", "selectLabelWhenHover", ""),
    "selectIconWhenOff": ("String", "inputOnly", "selectIconWhenOff", ""),
    "selectIconWhenOn": ("String", "inputOnly", "selectIconWhenOn", ""),
    "selectIconWhenHover": ("String", "inputOnly", "selectIconWhenHover", ""),
    "firstSelectedRow": ("{T}", "outputOnly", "Selected Record (First Selected Row)", ""),
    "selectedRecords": ("{T[]}", "", "Selected Records", ""),
    "selectedCollectionSize": ("Integer", "outputOnly", "Selected Collection Size", ""),
    "selectedRecordsIds": ("String[]", "outputOnly", "Selected Id(s) Collection", ""),
    "selectedRecordsIdsString": ("String", "outputOnly", "Selected Id(s) (Text)", ""),
    "selectedRecordsValues": ("String[]", "outputOnly", "Selected Value(s) (Collection)", ""),
    "selectedRecordsValuesString": ("String", "outputOnly", "Selected Value(s) (Text)", ""),
    "bottomMargin": ("String", "inputOnly", "Bottom Margin", "slds-m-bottom_none"),
    "calculatedResult": ("{T}", "outputOnly", "Calculated Result", ""),
    "calculatedResultSelectedOnly": ("{T}", "outputOnly", "Calculated Result (Selected Only)", ""),
    "recordTypeOptions": ("@salesforce/schema/RecordType[]", "inputOnly", "Record Type Options", ""),
    "themeOverrideName": ("String", "inputOnly", "Theme Override", ""),
    "themeHeaderName": ("String", "inputOnly", "Theme Header", ""),
    "accordionTitle": ("String", "inputOnly", "Accordion Header", ""),
    "subtitleTemplate": ("String", "inputOnly", "Subtitle Template", ""),
    "iconNameTemplate": ("String", "inputOnly", "Icon Name Template", ""),
    "preventAccordionClose": ("Boolean", "inputOnly", "Prevent Accordion Close", "false"),
    "closedOnLoad": ("Boolean", "inputOnly", "Accordion Closed on Load", "false"),
    "displayPrompts": ("Boolean", "inputOnly", "Display Prompts", "false"),
    "preventValidationBypass": ("Boolean", "inputOnly", "Prevent Validation Bypass", "false"),
    "enableAccordion": ("Boolean", "inputOnly", "Enable Accordion", "false"),
    "wrapInAccordion": ("Boolean", "inputOnly", "Wrap In Accordion", "false"),
    "dynamicHeaders": ("Boolean", "inputOnly", "Enable Dynamic Headers", "false"),
    "smallSize": ("Integer", "inputOnly", "Small Size", ""),
    "mediumSize": ("Integer", "inputOnly", "Medium Size", ""),
    "largeSize": ("Integer", "inputOnly", "Large Size", ""),
    "recordSpacing": ("String", "inputOnly", "Record Top Margin", ""),
    "recordSpacingBottom": ("String", "inputOnly", "Record Bottom Margin", ""),
    "recordSpacingHorizontal": ("String", "inputOnly", "Record Horizontal Padding", ""),
    "review": ("Boolean", "inputOnly", "Review", "false"),
    "requireAll": ("Boolean", "inputOnly", "Require All", "false"),
    "disableAll": ("Boolean", "inputOnly", "Disable All", "false"),
    "disableAllHeaders": ("Boolean", "inputOnly", "Disable All Headers", "false"),
    "title": ("String", "inputOnly", "Title", ""),
    "subtitle": ("String", "inputOnly", "Subtitle", ""),
    "helpText": ("String", "inputOnly", "Help Text", ""),
    "topMargin": ("String", "inputOnly", "Margin Top", ""),
    "iconName": ("String", "inputOnly", "Icon Name", ""),
    "richText": ("String", "inputOnly", "Rich Text", ""),
    "showHeader": ("Boolean", "inputOnly", "Show Header", "true"),
    "interviewGuid": ("String", "inputOnly", "interviewGuid", ""),
    "interviewStartDateTime": ("DateTime", "inputOnly", "interviewStartDateTime", ""),
    "elementApiName": ("String", "inputOnly", "elementApiName", ""),
    "serverURL": ("String", "inputOnly", "serverURL", ""),
}
SPACING_PROPS = ("recordSpacing", "recordSpacingBottom", "recordSpacingHorizontal")


def check(spec, org_tags=None):
    out = rp.check_common(spec, org_tags)
    rep = spec.get("repeater") or {}
    edit_on = rp.action(spec, "edit")[0]
    if rep.get("record_spacing") is not None and rep["record_spacing"] not in rp.SPACING:
        out.append(rp.error("layout", "repeater.record_spacing is one of %s" % ", ".join(rp.SPACING)))
    if spec.get("table"):
        out.append(rp.error("kind", "table settings on a Repeater spec; a Table is built by build-table"))
    for name in rp.ACTIONS:
        _, settings = rp.action(spec, name)
        allowed = {"label", "modal_title", "modal_subtitle"} if name == "edit" else {"label"}
        for key in settings:
            if key not in allowed and key != "_bad":
                out.append(rp.error("actions", "actions.%s.%s is not a Repeater setting%s" % (
                    name, key, "; windows belong to a Table" if key.startswith("modal") else "")))
    if spec["where"] == "section":
        out += rp.check_extra(spec, SECTION_FIELDS, "Repeater page section")
        for name in (spec.get("extra") or {}):
            if name in READ_ONLY_SECTION_FIELDS:
                out.append(rp.error("extra", "%s is calculated by the package; never write it" % name))
        if edit_on:
            out.append(rp.warning("edit", "Edit on a Repeater page section has no effect: the section never hands "
                                  "the repeater an edit form, so no Edit button shows. Rows are edited in place; "
                                  "turn it off, or use a Table when rows need an Edit window"))
        if spec.get("flow"):
            out.append(rp.error("where", "flow settings on a page section spec; set where to flow-screen"))
    else:
        out += rp.check_flow_common(spec, FLOW_PROPERTIES)
        flow = spec.get("flow") or {}
        if edit_on and not flow.get("edit_form"):
            out.append(rp.error("edit", "Edit shows only with an edit form: set flow.edit_form, a record component "
                                "(<Name>_v0) or metadata component, loaded by name"))
        if flow.get("edit_form") and not edit_on:
            out.append(rp.warning("edit", "flow.edit_form is set but Edit is off"))
        props = flow.get("properties") or {}
        if "formRepeaterConfiguration" in props and (len(props) > 1 or spec.get("actions") or spec.get("rows")):
            out.append(rp.warning("configuration", "Form (Repeater) Configuration replaces every individual "
                                  "property when it is set; set the settings in the configuration action instead"))
        for prop in SPACING_PROPS:
            if prop in props and props[prop] not in rp.SPACING:
                out.append(rp.error("layout", "%s is one of %s" % (prop, ", ".join(rp.SPACING))))
    return out


def section(spec, record=False, namespace=rp.DEFAULT_NAMESPACE):
    fields = rp.section_fields(spec, record=record, namespace=namespace)
    rep = spec.get("repeater") or {}
    if rep.get("record_spacing"):
        fields["Repeater_Record_Spacing__c"] = rep["record_spacing"]
    if "hide_divider" in rep:
        fields["Repeater_Hide_Divider__c"] = bool(rep["hide_divider"])
    fields.update(spec.get("extra") or {})
    return fields


def flow_screen(spec, namespace=rp.DEFAULT_NAMESPACE):
    flow = spec.get("flow") or {}
    params = rp.flow_params_common(spec, namespace)
    rep = spec.get("repeater") or {}
    if rep.get("record_spacing"):
        params.append(("recordSpacing", "String", rep["record_spacing"]))
    if rep.get("hide_divider"):
        params.append(("hideDivider", "Boolean", True))
    edit_on, edit = rp.action(spec, "edit")
    if edit_on and flow.get("edit_form"):
        params.append(("editFormQualifiedApiName", "String", flow["edit_form"]))
        if edit.get("modal_title"):
            params.append(("editModalHeading", "String", edit["modal_title"]))
        if edit.get("modal_subtitle"):
            params.append(("editModalSubheading", "String", edit["modal_subtitle"]))
    params = rp.dedupe_params(params + rp.flow_params_extra(spec, FLOW_PROPERTIES))
    extension = "%s:flowFormRepeat" % namespace if namespace else "flowFormRepeat"
    return rp.flow_field_xml(flow.get("element_name", "Repeater"), extension,
                             rp.namespaced_object(flow.get("object"), namespace), params)


def main(argv=None):
    return rp.run_cli(argv, "repeater", check, section, flow_screen, __doc__)


if __name__ == "__main__":
    sys.exit(main())
