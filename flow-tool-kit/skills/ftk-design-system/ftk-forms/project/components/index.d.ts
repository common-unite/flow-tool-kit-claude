/** Shared by every FlowToolKit field: the flowFormFieldLabel options. */
export interface FieldBaseProps {
  /** The field label. */
  label: string;
  /** Adds the outside asterisk; an empty answer shows "Complete this field." after blur. */
  required?: boolean;
  /** displayType__c = READONLY. */
  readOnly?: boolean;
  disabled?: boolean;
  /** Forces the error state with this message. */
  error?: string;
  helpText?: string;
  /** helpTextDisplay__c. Default "Hover Bubble". */
  helpTextDisplay?: 'Hover Bubble' | 'Below Label' | 'Below Field';
  /** labelSize__c. */
  labelSize?: 'slds-text-body_small' | 'slds-text-body_regular' | 'slds-text-title_bold' | 'slds-text-heading_small' | 'slds-text-heading_medium' | 'slds-text-heading_large';
  /** labelVariant__c = label-hidden: hides the label, keeps it for screen readers. */
  labelHidden?: boolean;
  /** Shows the focus state without interaction, for mockups. */
  focused?: boolean;
  /** labelVariant__c. label-inline puts the label in a column left of the control; label-hidden and none hide it (none also drops its space). Default "standard". */
  labelVariant?: 'standard' | 'label-stacked' | 'label-inline' | 'label-hidden' | 'none';
  /** inlineLabelWidth__c, with label-inline: the label column width, e.g. "40%" or "12rem". Default 33%. */
  inlineLabelWidth?: string;
  /** topMargin__c / bottomMargin__c: an SLDS margin class, e.g. "slds-m-top_small". */
  topMargin?: string;
  bottomMargin?: string;
  /** alignAbsoluteCenter__c / labelAlignAbsoluteCenter__c: centres the label and control. */
  alignCenter?: boolean;
  /** viewAsPlainText__c: draws the label over the value as text, no input box. */
  plainText?: boolean;
  /** disableHelpText__c: drops the help text however it is set to display. */
  disableHelpText?: boolean;
  /** customValidationMessage__c: shown when error is true. */
  customValidationMessage?: string;
  /** prepend__c / append__c: short text beside the input (TextInput, NumberInput standard, FormattedInput); choice fields show them under the options at either end, like a scale. */
  prepend?: string;
  append?: string;
  /** Label_Rich_Text__c: an HTML label (links, bold). Replaces the plain label text. */
  labelRichText?: string;
  className?: string;
  style?: React.CSSProperties;
}

/** flowFormField · stringType__c = standard · lightning-input */
export interface TextInputProps extends FieldBaseProps {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'email' | 'tel' | 'url' | 'number';
  maxLength?: number;
  /** Opens the Hover Bubble tooltip, for mockups. */
  helpOpen?: boolean;
}

/** flowFormField · stringType__c = textarea or Long Text Area · lightning-textarea + counter */
export interface TextAreaProps extends FieldBaseProps {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  /** Turns on the "typed / max" counter. */
  maxLength?: number;
  /** textAreaMinHeight__c */
  minHeight?: string;
  /** textAreaMaxHeight__c */
  maxHeight?: string;
}

export type PicklistOption = string | { label: string; value: string; /** visualpicker */ icon?: string; /** visualpicker */ image?: string };

/** picklistType__c · lightning-combobox or flowFormRadioCheckbox */
export interface PicklistProps extends FieldBaseProps {
  options: PicklistOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  /** picklistType__c. Default "standard". */
  variant?: 'standard' | 'radio' | 'separatedbuttons' | 'surveybuttons' | 'radiobuttons' | 'pathbuttons' | 'iconbuttons' | 'visualpicker';
  /** iconbuttons only: iconSelectorIconName__c. Default "utility:favorite". */
  icon?: string;
  /** iconbuttons only: iconSelectorColor__c. Default "#ffd602". */
  iconColor?: string;
  iconSize?: 'small' | 'medium' | 'large';
  /** visualpicker: true draws the phone layout (label under the box). Default false: icon only, label on hover. */
  captionAlways?: boolean;
  /** picklistColumnsSize__c for radio, separatedbuttons and visualpicker: "none" wraps at content width. */
  /** picklistColumnsSize__c: none or grow wrap at content width; a number sets columns. */
  columns?: 'none' | 'grow' | number | string;
  /** standard only. Default "Select an Option". */
  placeholder?: string;
  /** standard only: shows the dropdown open, for mockups. */
  open?: boolean;
}

/** flowFormCheckbox · booleanType__c */
export interface CheckboxProps extends FieldBaseProps {
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (checked: boolean) => void;
  /** booleanType__c: toggle = "default". Default "toggle". */
  variant?: 'toggle' | 'checkbox' | 'attestation' | 'picklist' | 'radio' | 'radiobuttons';
  /** booleanPicklistTypeOverride__c. The first label means checked. picklist, radio and radiobuttons option labels (blank = True/False); positioned toggle state text (blank = Enabled/Disabled). */
  booleanLabels?: 'True/False' | 'Yes/No' | 'Active/Inactive' | 'Enabled/Disabled' | 'Valid/Invalid' | 'On/Off';
  /** toggle only. labelVariant__c left / right. Default "top". */
  labelPosition?: 'top' | 'left' | 'right';
  /** positioned toggle only: replaces the booleanLabels state text (design only). */
  activeMessage?: string;
  inactiveMessage?: string;
  /** attestation only: bold first line. */
  attestationTitle?: string;
  /** attestation only: the consent statement. */
  attestationText?: string;
}

export declare function TextInput(props: TextInputProps): JSX.Element;
export declare function TextArea(props: TextAreaProps): JSX.Element;
export declare function Picklist(props: PicklistProps): JSX.Element;
export declare function Checkbox(props: CheckboxProps): JSX.Element;

/** flowFormField number / currency / percent · numberType__c (flowFormNumberInput) */
export interface NumberInputProps extends FieldBaseProps {
  value?: number | '';
  defaultValue?: number | '';
  onChange?: (value: number | '') => void;
  /** numberType__c. Default "standard". */
  variant?: 'standard' | 'stepper' | 'slider' | 'presetamounts';
  /** Default "number". Currency is USD. */
  format?: 'number' | 'currency' | 'percent';
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  /** presetamounts only. */
  presets?: number[];
  allowCustom?: boolean;
  customPlaceholder?: string;
}
export declare function NumberInput(props: NumberInputProps): JSX.Element;

/** lightning-input date / time / datetime · minDateType__c / maxDateType__c */
export interface DateInputProps extends FieldBaseProps {
  /** ISO: "2026-10-24", "14:00" or "2026-10-24T14:00". */
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  type?: 'date' | 'time' | 'datetime';
  /** ISO dates. */
  min?: string;
  max?: string;
  /** ISO date that the picker treats as today, for mockups. */
  today?: string;
  /** Shows the datepicker or time list open, for mockups. */
  open?: boolean;
}
export declare function DateInput(props: DateInputProps): JSX.Element;

/** Multi-Select Picklist · picklistType__c (flowFormMultiselectCheckbox, comboBox, lightning-dual-listbox) */
export interface MultiPicklistProps extends FieldBaseProps {
  options: PicklistOption[];
  value?: string[];
  defaultValue?: string[];
  onChange?: (values: string[]) => void;
  /** Default "multiselectcheckbox". standard = dual listbox. Exclusive values clear and lock the rest; All of the above selects every non-exclusive option. */
  variant?: 'multiselectcheckbox' | 'selectallmultiselectcheckbox' | 'separatedbuttons' | 'multiselectbadge' | 'combobox' | 'visualpicker' | 'standard';
  /** picklistColumnsSize__c: none or grow wrap at content width; a number sets columns. */
  columns?: 'none' | 'grow' | number | string;
  /** The most answers allowed. */
  max?: number;
  /** combobox only. */
  open?: boolean;
  placeholder?: string;
  captionAlways?: boolean;
}
export declare function MultiPicklist(props: MultiPicklistProps): JSX.Element;

/** formSectionTheme + sectionFrame + header */
export interface SectionProps {
  title?: string;
  subtitle?: string;
  /** An SLDS icon name, e.g. "standard:account". */
  icon?: string;
  /** Header_Display__c. Default "Header". */
  headerDisplay?: 'Header' | 'Divider';
  /** Divider_Style__c, when headerDisplay is "Divider". */
  dividerStyle?: DividerProps['variant'];
  /** borderSize__c for a divider header's rules, px. */
  ruleSize?: number;
  brandColor?: string;
  helpText?: string;
  /** sectionTheme__c. Default "clean" (None). */
  frame?: 'clean' | 'box' | 'shadow';
  /** Header style. card and outlined need a box or shadow frame. Default "classic". */
  headerStyle?: 'classic' | 'classicSpread' | 'card' | 'outlined' | 'hero';
  showHeader?: boolean;
  /** Stacked (hero) only: Header_Kicker__c, Header_Lead__c, Header_Footer__c, Header_Tags__c. */
  kicker?: string;
  lead?: string;
  footer?: string;
  tags?: string[];
  /** Header_Tags_Position__c. Default "belowLead". */
  tagsPosition?: 'belowLead' | 'aboveEyebrow' | 'aboveKicker' | 'aboveTitle';
  /** Header_Bottom_Margin__c: an SLDS class, e.g. "slds-m-bottom_small". */
  headerBottomMargin?: string;
  /** Section widthLarge__c / widthMedium__c / widthSmall__c, 1 to 12. Put sections in a SectionGrid to sit side by side. */
  large?: number;
  medium?: number;
  small?: number;
  /** marginTop__c / marginBottom__c (slds-m-*), paddingTop/Bottom/Left/Right__c and horizontalPadding__c (slds-p-*). Package default: none. */
  marginTop?: string;
  marginBottom?: string;
  paddingTop?: string;
  paddingBottom?: string;
  paddingLeft?: string;
  paddingRight?: string;
  horizontalPadding?: string;
  /** horizontalAlign__c: how fields that do not fill a row line up. */
  horizontalAlign?: 'start' | 'center' | 'space' | 'spread' | 'end';
  /** hideAccordionBorder__c */
  hideAccordionBorder?: boolean;
  /** richText__c: the section's rich text, drawn above the fields. */
  richText?: string;
  /** Flow Action (flowApiName__c): flowButtonLabel__c, default "Run Flow" (true). Always a brand button; a click opens the flow in a modal (modalSize__c, default large). */
  flowButtonLabel?: string | true;
  /** flowButtonStyle__c: CSS that places the button over the rich text, default "z-index:3; right:0; bottom:20%". Ignored with no rich text (the button sits right-aligned). */
  flowButtonStyle?: string;
  /** headingBackgroundColor__c, a hex value. */
  headerBackground?: string;
  /** headingBackgroundGradient__c. */
  headerGradient?: boolean;
  /** headingFontColor__c */
  titleColor?: string;
  /** headingSubtitleFontColor__c */
  subtitleColor?: string;
  /** headingIconColor__c */
  iconColor?: string;
  /** borderColor__c: frame edge and header rule. */
  borderColor?: string;
  /** borderSize__c (px): frame edge width and the rule beside an outlined title. */
  borderSize?: number;
  /** sectionBackgroundColor__c */
  sectionBackground?: string;
  /** sectionType__c = accordionSection */
  accordion?: boolean;
  open?: boolean;
  /** accordionBackgroundColor__c */
  accordionBackground?: string;
  /** accordionFontColor__c */
  accordionFontColor?: string;
  /** Optional header actions, drawn at the right of a Classic header. */
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

/** widthLarge__c / widthMedium__c / widthSmall__c */
export interface ColumnProps {
  /** A number of columns, or "shrink" (content width; the next field follows on the same row). */
  large?: number | 'shrink';
  /** Under 800px of container width. */
  medium?: number;
  /** Under 500px of container width. */
  small?: number;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export declare function Section(props: SectionProps): JSX.Element;
export declare function Column(props: ColumnProps): JSX.Element;
/** The form body as a 12-column grid, so sections with large / medium / small widths sit side by side. */
export declare function SectionGrid(props: { children?: React.ReactNode; className?: string; style?: React.CSSProperties }): JSX.Element;
/** Design-only note that a field or section appears when a rule is met (conditionalLogic__c). */

/** formSectionDivider · Divider_Style__c */
export interface DividerProps {
  variant?: 'line' | 'compact' | 'centered' | 'label' | 'bookmark' | 'ornament' | 'pill' | 'chevron' | 'double' | 'icon' | 'fade' | 'tag';
  label?: string;
  subtitle?: string;
  /** An SLDS icon name. */
  icon?: string;
  brandColor?: string;
  borderColor?: string;
  labelColor?: string;
  iconColor?: string;
  subtitleColor?: string;
  /** Rule thickness in px. Default 2. */
  ruleSize?: number;
  className?: string;
  style?: React.CSSProperties;
}

/** lightning-icon · SLDS 2.30.7 */
export interface IconProps {
  /** category:name, e.g. "utility:location". */
  name: string;
  size?: 'xx-small' | 'x-small' | 'small' | 'medium' | 'large' | number;
  variant?: 'glyph' | 'tile';
  color?: string;
  title?: string;
  className?: string;
  style?: React.CSSProperties;
}

export declare function Divider(props: DividerProps): JSX.Element;
export declare function Icon(props: IconProps): JSX.Element;

/** The Basic overrides of the FlowToolKit Style Editor (Form Style). Leave a prop out to keep the package default. */
export interface FormStyleValues {
  /** Brand · --ftk-color-primary */
  brand?: string;
  /** Brand text · --ftk-color-on-primary */
  brandText?: string;
  /** Input text · --ftk-color-text */
  inputText?: string;
  /** Field labels · --ftk-color-label */
  fieldLabels?: string;
  /** Choice text · --ftk-color-option */
  choiceText?: string;
  /** Form background · --ftk-color-background */
  formBackground?: string;
  /** Card background · --ftk-color-surface */
  cardBackground?: string;
  /** Input background · --ftk-color-control-surface */
  inputBackground?: string;
  /** Borders · --ftk-color-border */
  borders?: string;
  /** Border thickness, percent (100 = default) · --ftk-border-scale */
  borderThickness?: number;
  /** Corner radius, px · --ftk-radius-medium */
  cornerRadius?: number;
  /** Input size, percent · --ftk-control-scale */
  inputSize?: number;
  /** Text size, percent · --ftk-font-scale */
  textSize?: number;
  /** Field spacing, percent · --ftk-spacing-scale */
  fieldSpacing?: number;
  /** Label weight, 100 to 900 · --ftk-font-weight-label */
  labelWeight?: number;
  /** Horizontal padding, px · --ftk-section-padding-inline. Unframed sections only; framed sections keep 20px */
  paddingInline?: number;
  /** Vertical padding, px · --ftk-section-padding-block */
  paddingBlock?: number;
  /** Font, a CSS font stack · --ftk-font-family */
  font?: string;
  /** Opacity % for any color, e.g. brandOpacity: 80 */
  [opacity: `${string}Opacity`]: number | undefined;
  /** Style Editor Advanced tab: token name without --ftk- (or with it) to a CSS value, e.g. { 'font-family-heading': 'Georgia, serif', 'table-shade': '#eef4ff' }. See FORM_STYLE_ADVANCED. */
  advanced?: Record<string, string>;
}

/** One Advanced token, generated from the package's formStyleConfig.js. */
export interface FormStyleAdvancedToken {
  key: string;
  token: string;
  label: string;
  category: string;
  type: string;
  defaultValue: string;
  units: string[];
  description: string;
}

export interface FormStyleProps extends FormStyleValues {
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

/** The CSS custom properties a set of Basic values produces. */
export declare function formStyleVars(values: FormStyleValues): Record<string, string>;
/** Apply Basic values to an element (and everything inside it). */
export declare function applyFormStyle(el: HTMLElement, values: FormStyleValues): void;
/** Follow the Form Style card's saved values on this page. */
export declare function syncPreviewStyle(el?: HTMLElement): void;


// ---- Batch 4 group A ----
/** flowFormField reference · referenceFieldOverrideType__c, enableCustomLookup__c */
export interface LookupOption { label: string; value: string; sublabel?: string; icon?: string }
export interface LookupProps extends FieldBaseProps {
  options?: LookupOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  /** standard = lightning-input-field lookup; customSearch = enableCustomLookup__c; recordpicker = Record Picker override. */
  variant?: 'standard' | 'customSearch' | 'recordpicker';
  /** Singular object label. Default "Account". */
  objectLabel?: string;
  /** Default "standard:account". */
  objectIcon?: string;
  allowNew?: boolean;
  newButtonLabel?: string;
  placeholder?: string;
  open?: boolean;
  searchValue?: string;
}
export declare function Lookup(props: LookupProps): JSX.Element;

export interface AddressValue { street?: string; city?: string; province?: string; postalCode?: string; country?: string }
export type AddressPartFlags = { street?: boolean; city?: boolean; province?: boolean; postalCode?: boolean; country?: boolean };
/** flowFormFieldAddress · lightning-input-address */
export interface AddressProps {
  label?: string;
  value?: AddressValue;
  defaultValue?: AddressValue;
  onChange?: (value: AddressValue) => void;
  /** Address search box. Default true. */
  showLookup?: boolean;
  lookupPlaceholder?: string;
  suggestions?: { label: string; sublabel?: string; address: AddressValue }[];
  open?: boolean;
  searchValue?: string;
  /** State and Country picklists. One country hides the Country part. */
  countries?: PicklistOption[];
  provinces?: PicklistOption[] | Record<string, PicklistOption[]>;
  hideProvince?: boolean;
  labels?: { street?: string; city?: string; province?: string; postalCode?: string; country?: string };
  placeholders?: { street?: string; city?: string; province?: string; postalCode?: string; country?: string };
  required?: boolean | AddressPartFlags;
  readOnly?: boolean;
  showStaticMap?: boolean;
  disabled?: boolean;
  error?: string;
  helpText?: string;
  helpTextDisplay?: 'Hover Bubble' | 'Below Label' | 'Below Field';
  labelSize?: string;
  labelHidden?: boolean;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Address(props: AddressProps): JSX.Element;

/** flowFormField tel / email / url · phoneMask__c */
export interface FormattedInputProps extends FieldBaseProps {
  type?: 'phone' | 'email' | 'url';
  /** phoneMask__c. Default "(xxx) xxx-xxxx". */
  phoneMask?: '(xxx) xxx-xxxx' | 'xxx-xxx-xxxx' | 'xx xxxx xxxx' | 'xxxx xxx xxx' | 'none';
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
}
export declare function FormattedInput(props: FormattedInputProps): JSX.Element;

/** flowFormRichTextInput · RichTextFormats__c, enableRichPlainTextToggle__c */
export interface RichTextInputProps extends FieldBaseProps {
  value?: string;
  defaultValue?: string;
  onChange?: (html: string) => void;
  placeholder?: string;
  formats?: Array<'font' | 'size' | 'color' | 'bold' | 'italic' | 'underline' | 'list' | 'indent' | 'align' | 'link' | 'image' | 'clean'>;
  plainTextToggle?: boolean;
  toolbarPosition?: 'top' | 'bottom';
  /** textAreaMinHeight__c, a CSS length such as '240px'. Taller boxes for essay answers. */
  minHeight?: string;
  /** textAreaMaxHeight__c. Defaults to 15rem, or no cap when minHeight is set. */
  maxHeight?: string;
  font?: string;
  fontSize?: string;
}
export declare function RichTextInput(props: RichTextInputProps): JSX.Element;

/** flowFormRichText · Header_Text_Variant__c */
export interface RichTextProps {
  html?: string;
  children?: React.ReactNode;
  variant?: 'default' | 'highlight' | 'info' | 'warning' | 'error' | 'success';
  className?: string;
  style?: React.CSSProperties;
}
export declare function RichText(props: RichTextProps): JSX.Element;

/** flowFormPrompt · fieldPrompt__c, promptDisplayType__c, promptColor__c, promptFontColor__c */
export interface FieldPromptProps {
  message?: React.ReactNode;
  html?: string;
  children?: React.ReactNode;
  displayType?: 'prompt' | 'richtext';
  color?: string;
  fontColor?: string;
  /** The field the prompt sits above. */
  field?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function FieldPrompt(props: FieldPromptProps): JSX.Element;

// ---- Batch 4 group B ----
/** formFieldFileUpload · longTextType__c = fileUpload */
export interface UploadedFile { name: string; mimeType?: string; }
export interface FileUploadProps extends FieldBaseProps {
  value?: UploadedFile[];
  defaultValue?: UploadedFile[];
  onChange?: (files: UploadedFile[]) => void;
  /** uploadMultipleFiles__c */
  multiple?: boolean;
  /** Most files allowed with multiple. */
  max?: number;
  /** acceptedFormats__c, semicolon separated: ".pdf;.png" */
  acceptedFormats?: string;
  /** fileNameFormat__c with {{label}} and {{filename}} */
  fileNameFormat?: string;
  /** preventFileDeletion__c */
  preventFileDeletion?: boolean;
  /** disablePreviewLink__c */
  disablePreviewLink?: boolean;
}
export declare function FileUpload(props: FileUploadProps): JSX.Element;

/** imgUpload · richTextType__c = imageUpload */
export interface ImageUploadProps extends FieldBaseProps {
  /** Image URL or data URL. */
  value?: string;
  defaultValue?: string;
  fileName?: string;
  onChange?: (src: string) => void;
  /** Shows the preview modal open, in place, for mockups. */
  open?: boolean;
}
export declare function ImageUpload(props: ImageUploadProps): JSX.Element;

/** signaturePad · richTextType__c = signaturePad */
export interface SignaturePadProps extends FieldBaseProps {
  /** PNG data URL of the signature. */
  value?: string;
  defaultValue?: string;
  onChange?: (dataUrl: string) => void;
  /** Default 3. */
  strokeThickness?: number;
  /** Default "black". */
  penColor?: string;
  minHeight?: number | string;
  /** Draws an example signature, for mockups. */
  sample?: boolean;
}
export declare function SignaturePad(props: SignaturePadProps): JSX.Element;

type SldsMargin = string;
/** displayImage */
export interface DisplayImageProps {
  /** contentAssetName / customImageLink */
  src: string;
  alt?: string;
  /** CSS for the image, e.g. "height:220px; object-position:center bottom" */
  imageStyle?: string;
  overlayHexColor?: string;
  /** 0 to 1. With no overlayHexColor the tint is the brand. */
  overlayOpacity?: number;
  /** The section's rich text laid over the image (richText__c). */
  customRichText?: string;
  /** viewAsPlainText__c: 'richtext' (View as Rich Text, default) sits centred with 1rem padding; 'html' (View as Plain Text) fills the whole image and lays itself out. */
  overlayMode?: 'richtext' | 'html';
  parallax?: boolean;
  /** e.g. "slds-m-top_medium" */
  topMargin?: SldsMargin;
  bottomMargin?: SldsMargin;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function DisplayImage(props: DisplayImageProps): JSX.Element | null;

/** displayIllustration · displayIllustrationArt */
export type IllustrationType = 'Base' | 'Camping' | 'Maintenance' | 'Desert' | 'Road' | 'No Access' | 'Balloon' | 'Lightning' | 'Axe' | 'Not Available' | 'Fishing' | 'Mountain' | 'No Events' | 'No Tasks' | 'Setup' | 'Gone Fishing' | 'No Access #2' | 'No Content' | 'No Preview' | 'Preview' | 'Research' | 'Approval' | 'Spinner'; // partner-clean: allow R4
export interface IllustrationProps {
  /** Default "Base". */
  type?: IllustrationType;
  /** Default "small". */
  size?: 'small' | 'large';
  title?: string;
  /** Rich text (HTML). */
  subtitle?: string;
  topMargin?: SldsMargin;
  bottomMargin?: SldsMargin;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Illustration(props: IllustrationProps): JSX.Element;
export declare const ILLUSTRATION_TYPES: IllustrationType[];


// ---- Batch 4 group C ----
/** flowFormLikertMatrix · Likert Matrix section */
export interface LikertScaleOption { label: string; value: string | number; help?: string }
export interface LikertRow { id?: string; label: string; required?: boolean; helpText?: string; helpTextDisplay?: 'Hover Bubble' | 'Below Label' | 'Below Field'; readOnly?: boolean }
export interface LikertMatrixProps {
  /** Likert_Mode__c. Default "Picklist". */
  mode?: 'Picklist' | 'Number';
  scale: (string | LikertScaleOption)[];
  rows: (string | LikertRow)[];
  values?: Record<string, string | number>;
  defaultValues?: Record<string, string | number>;
  onChange?: (values: Record<string, string | number>, rowId: string) => void;
  /** Default "auto": grid at 480px and wider, stacked survey buttons below. */
  layout?: 'auto' | 'grid' | 'stacked';
  /** Show_Total_Score__c */
  showTotal?: boolean;
  /** Total_Score_Label__c. Default "Total Score". */
  totalLabel?: string;
  showErrors?: boolean;
  readOnly?: boolean;
  review?: boolean;
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}
export declare function LikertMatrix(props: LikertMatrixProps): JSX.Element;

/** flowFormRepeat (card) · flowDataTable (table) */
export type RecordSpacing = 'none' | 'xxx-small' | 'xx-small' | 'x-small' | 'small' | 'medium' | 'large' | 'x-large' | 'xx-large';
export interface RepeaterColumn {
  field: string;
  label: string;
  type?: 'text' | 'email' | 'url' | 'textarea' | 'number' | 'currency' | 'percent' | 'picklist';
  options?: PicklistOption[];
  required?: boolean;
  editable?: boolean;
  /** Read-only calculated column over other fields, e.g. "rate * hours * weeks + benefits". */
  formula?: string | ((row: Record<string, unknown>) => number);
  /** Grand Totals row. */
  calculationType?: 'Sum' | 'Min' | 'Max' | 'Average';
  /** Card layout spans [large, medium, small]. Default [6, 6, 12]. */
  widths?: [number, number, number];
  width?: string | number;
  placeholder?: string;
  helpText?: string;
  defaultValue?: unknown;
  min?: number;
  max?: number;
  /** columnAlignment__c. Default left, right for numbers. */
  alignment?: 'left' | 'center' | 'right';
  /** columnIconName__c and columnIconPosition__c (default left). */
  iconName?: string;
  iconPosition?: 'left' | 'right';
  /** columnWrapText__c. */
  wrapText?: boolean;
  /** columnVisibility__c. Hidden columns stay in the edit modal. */
  visibility?: 'visible' | 'hidden';
  /** columnDisplayType__c. url draws a link. */
  displayType?: 'text' | 'url';
  /** columnInitialWidth__c / columnFixedWidth__c. */
  initialWidth?: string | number;
  fixedWidth?: string | number;
  /** Table number formatting: minimumIntegerDigits__c, minimum/maximumFractionDigits__c, minimum/maximumSignificantDigits__c. */
  minimumIntegerDigits?: number;
  minimumFractionDigits?: number;
  maximumFractionDigits?: number;
  minimumSignificantDigits?: number;
  maximumSignificantDigits?: number;
  /** currencyCode__c for a currency column. Default USD. */
  currencyCode?: string;
}
export interface RepeaterProps {
  /** The repeater's own header (showHeader). With it on, Import and New sit in the header; with it off they sit on every record beside Clone (flowFormRepeat showImportAndNewOnRows). */
  showHeader?: boolean;
  /** Draws each record's content in place of the columns grid, for a repeated form component that is not plain fields, such as a RecordCard. */
  renderRecord?: (row: Record<string, unknown>, index: number) => React.ReactNode;
  /** With more records than max (and showSelectedOnly off) the records page max at a time; the page to start on. */
  defaultPage?: number;
  title?: string;
  subtitle?: string;
  /** An SLDS utility: icon. */
  icon?: string;
  headerHelpText?: string;
  /** Default "card". */
  layout?: 'card' | 'table';
  columns: RepeaterColumn[];
  rows?: Record<string, unknown>[];
  defaultRows?: Record<string, unknown>[];
  onChange?: (rows: Record<string, unknown>[]) => void;
  /** Default 1. */
  min?: number;
  /** Default 5. */
  max?: number;
  allowNew?: boolean;
  allowDelete?: boolean;
  allowClone?: boolean;
  allowReposition?: boolean;
  allowEdit?: boolean;
  newButtonLabel?: string;
  deleteButtonLabel?: string;
  cloneButtonLabel?: string;
  editButtonLabel?: string;
  /** Default "Reset". */
  resetButtonLabel?: string;
  /** Card layout: allowImport__c with importButtonLabel (default "Import"). */
  allowImport?: boolean;
  importButtonLabel?: string;
  /** Edit modal: editModalHeading, editModalSubheading, editReturnButtonLabel (default "Return"). */
  editModalHeading?: string;
  editModalSubheading?: string;
  editReturnButtonLabel?: string;
  /** Opens the edit modal on this row index, for mockups. */
  editOpen?: number;
  /** false draws the modal over the page (position fixed). Default true keeps it inside the card. */
  /** Where a preview draws the edit modal: 'cover' (default for cards) lays it over the repeater the way c-modal covers the page; false draws it over the whole page; true puts it in the flow. */
  modalInline?: boolean | 'cover';
  /** Card layout: records span the full width (featured). */
  featured?: boolean;
  /** Card layout: record spans [large, medium, small] so records sit side by side. Default [12, 12, 12]. */
  recordWidths?: [number, number, number];
  /** Card layout: only rows with selected: true show (showSelectedOnly). */
  showSelectedOnly?: boolean;
  /** Repeater_Record_Spacing__c: above, below and between side-by-side records. */
  recordSpacing?: RecordSpacing;
  recordSpacingBottom?: RecordSpacing;
  recordSpacingHorizontal?: RecordSpacing;
  /** Table: showCheckBoxColumn with min/maxRowSelection; maxRowSelection 1 draws radios. Indexes in selected start checked. */
  showCheckBoxColumn?: boolean;
  minRowSelection?: number;
  maxRowSelection?: number;
  selected?: number[];
  onSelect?: (rows: Record<string, unknown>[], indexes: number[]) => void;
  /** Table row actions menu: Edit, Clone, Delete, Reset. "buttons" keeps the older icon buttons. */
  allowReset?: boolean;
  rowActionStyle?: 'menu' | 'buttons';
  /** Bulk actions menu, shown once rows are selected. */
  allowBulkEdit?: boolean;
  allowBulkDelete?: boolean;
  allowBulkReset?: boolean;
  /** Reset Table icon button. */
  allowResetTable?: boolean;
  /** Header buttons beside New (buttonsCustom in the table header). */
  customButtons?: { label: string; iconName?: string; variant?: string }[];
  /** Table_Disable_Row_Action_Indicators__c. Off: new, changed and deleted rows tint green, yellow and red with a change column. */
  disableRowActionIndicators?: boolean;
  /** Table_Row_Style__c. */
  tableRowStyle?: 'hideBorders' | 'slds-table_striped' | 'slds-table_col-bordered';
  /** Table_Hide_Column_Headers__c. */
  hideColumnHeaders?: boolean;
  /** Table_Prevent_Column_Resize__c. */
  preventColumnResize?: boolean;
  /** Tree view: displayAsDataTree with hierarchyFieldName (rows carry Id and the parent Id); treeHideCollapseButtons expands every row. */
  displayAsDataTree?: boolean;
  hierarchyFieldName?: string;
  treeHideCollapseButtons?: boolean;
  /** Draws the table shadow (--ftk-table-shadow). */
  tableShadow?: boolean;
  /** Hides the "n of max records" line under a table. */
  hideLimit?: boolean;
  /** Mockups: open a row's action menu, or the bulk menu. */
  rowMenuOpen?: number;
  bulkMenuOpen?: boolean;
  /** Card layout heading per record; {n} is the record number. */
  recordTitle?: string;
  displayRepeaterButtonsAbove?: boolean;
  hideDivider?: boolean;
  showRowNumberColumn?: boolean;
  showFilter?: boolean;
  hideTableFooter?: boolean;
  /** Default "Grand Totals"; tables switch to "Selected Totals" or "Filtered Totals". */
  totalsLabel?: string;
  total?: { column: string; mustEqual?: number; message?: string; matchedMessage?: string };
  label?: string;
  helpText?: string;
  helpTextDisplay?: 'Hover Bubble' | 'Below Label' | 'Below Field';
  required?: boolean;
  readOnly?: boolean;
  review?: boolean;
  disableAll?: boolean;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Repeater(props: RepeaterProps): JSX.Element;

/** recordCard · recordCardConfig */
export type RecordCardType = 'mediaTop' | 'photoOverlay' | 'dateTile' | 'progress' | 'headerBand' | 'strip' | 'countdown' | 'iconLead' | 'profile' | 'fieldList' | 'valueSpotlight';
export interface RecordCardButton { label: string; url?: string; style?: 'brand' | 'light' | 'accent' | 'outline' | 'link' }
export interface RecordCardProps {
  /** Default "mediaTop". */
  cardType?: RecordCardType;
  /** Default "elevated". */
  cardStyle?: 'elevated' | 'outlined' | 'flat';
  sample?: boolean;
  image?: string;
  imageAlt?: string;
  badge?: string;
  badgeStyle?: 'neutral' | 'brand' | 'accent' | 'outline';
  cornerTag?: string;
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  description?: string;
  rows?: { label: string; value: string }[];
  tags?: (string | { label: string; style?: 'neutral' | 'brand' | 'accent' | 'outline' })[];
  value?: string;
  valueSuffix?: string;
  meta?: string;
  buttons?: (string | RecordCardButton)[];
  /** ISO date, for dateTile and countdown. */
  date?: string;
  progressCurrent?: string;
  progressTotal?: string;
  link?: string;
  mediaHeight?: 'short' | 'medium' | 'tall';
  imageFrame?: boolean;
  overlayStyle?: 'bottom' | 'side' | 'tint' | 'light' | 'none';
  scrimColor?: string;
  avatarType?: 'initials' | 'image' | 'icon';
  icon?: string;
  iconStyle?: 'circle' | 'tile';
  stripTone?: 'info' | 'warning' | 'success' | 'error';
  stripIcon?: string;
  countdownUnits?: 'dhm' | 'dhms' | 'd';
  countdownDirection?: 'down' | 'up';
  countdownEnded?: string;
  /** Pins the countdown clock for a mockup (ISO). */
  now?: string;
  /** the card sits in a repeater whose rows control selection. Button mode adds a Select button first in `buttons`. */
  allowSelect?: boolean;
  /** a visual picker section wraps the card: the whole card selects and the card link is dropped. */
  picker?: boolean;
  isSelected?: boolean;
  /** The repeater is at its Max Selection Size: an unselected card's Select is disabled. */
  preventNewSelection?: boolean;
  /** The repeater's Select label overrides; defaults Select, Selected, Unselect. */
  selectLabels?: { off?: string; on?: string; hover?: string };
  onSelect?: () => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function RecordCard(props: RecordCardProps): JSX.Element;
export declare const RECORD_CARD_SAMPLES: Record<RecordCardType, Partial<RecordCardProps>>;



// ---- Group F ----
/** The Style Editor Advanced tab, in the package's order (139 tokens). */
export declare const FORM_STYLE_ADVANCED: FormStyleAdvancedToken[];

/** flowFormLookup custom search (enableCustomLookup__c): customLookupHeader__c, customLookupSubheader__c, a single-select flowDataTable */
export interface LookupSearchTableProps {
  /** customLookupHeader__c */
  header?: string;
  /** customLookupSubheader__c */
  subheader?: string;
  /** The lookup's table form columns; cells are read only. */
  columns: RepeaterColumn[];
  rows: Record<string, unknown>[];
  /** Row index that starts selected. Save shows once a row is selected. */
  selectedIndex?: number;
  /** Default true. */
  enableFilter?: boolean;
  allowNew?: boolean;
  newButtonLabel?: string;
  showRowNumberColumn?: boolean;
  tableRowStyle?: 'hideBorders' | 'slds-table_striped' | 'slds-table_col-bordered';
  hideTableHeader?: boolean;
  hideTableFooter?: boolean;
  displayAsDataTree?: boolean;
  hierarchyFieldName?: string;
  /** Default true. false draws the modal over the page. */
  inline?: boolean;
  /** Default true. */
  open?: boolean;
  onSave?: (row: Record<string, unknown>) => void;
  onCancel?: () => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function LookupSearchTable(props: LookupSearchTableProps): JSX.Element;

// ---- Batch 4 group D ----
/** lightning-button with the FTK brand (buttonHoverStyles) */
export interface FormButtonProps {
  label: string;
  variant?: 'neutral' | 'brand' | 'brand-outline' | 'destructive' | 'base';
  /** Any SLDS utility icon, e.g. "utility:forward". */
  iconName?: string;
  iconPosition?: 'left' | 'right';
  disabled?: boolean;
  /** Full width. */
  stretch?: boolean;
  onClick?: (event: unknown) => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function FormButton(props: FormButtonProps): JSX.Element;

/** One form section as a tab. */
export interface TabProps {
  label: string;
  value?: string;
  /** Section FlowToolKit__iconName__c, any SLDS icon name. */
  icon?: string;
  /** Shows the tab error indicator. */
  invalid?: boolean;
  children?: React.ReactNode;
}
export declare function Tab(props: TabProps): JSX.Element;

/** flowForm FlowToolKit__type__c tabset and carousel */
export interface TabsetProps {
  /** FlowToolKit__type__c. Default "default". For carousel use the Carousel component. */
  variant?: 'default' | 'scoped' | 'vertical' | 'carousel';
  tabs?: Array<{ label: string; value?: string; icon?: string; invalid?: boolean; content?: React.ReactNode }>;
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  /** carousel only. */
  backLabel?: string;
  nextLabel?: string;
  finishLabel?: string;
  onFinish?: () => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Tabset(props: TabsetProps): JSX.Element;

/** A Flow Form shown as a carousel (FlowToolKit__type__c = carousel): one section at a time, progress indicator, Back / Continue, Finish on the last. */
export interface CarouselProps extends Omit<TabsetProps, 'variant'> {}
export declare function Carousel(props: CarouselProps): JSX.Element;

/** formStageIndicator · Stage_Indicator_Type__c */
export interface StageIndicatorProps {
  /** Hide_Stage_Indicator__c: draws nothing. */
  hidden?: boolean;
  stages: Array<string | { label: string }>;
  current?: string;
  /** Labels of completed pages. Default: every page before current. */
  complete?: string[];
  hasError?: boolean;
  type?: 'base' | 'path' | 'vertical' | 'footer base' | 'footer path';
  variant?: 'base' | 'shaded';
  /** Stages Mode markers (vertical). */
  stageSteps?: Array<{ label: string; status?: 'done' | 'in-progress' | 'requires-correction' | 'locked' | 'todo'; clickable?: boolean }>;
  /** base: keep the current page's label tooltip open, for mockups. */
  showLabels?: 'current';
  onSelect?: (label: string) => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function StageIndicator(props: StageIndicatorProps): JSX.Element;

export interface StagesOverviewStage {
  title: string;
  description?: string;
  status?: 'done' | 'requires-correction' | 'in-progress' | 'todo' | 'optional' | 'locked';
  /** Is_Optional__c, shown as an Optional badge whatever the status. */
  optional?: boolean;
  /** Visibility__c. Internal Only and External Only draw a badge (a design note: the package just leaves the page out for the other audience). */
  visibility?: 'Both' | 'Internal Only' | 'External Only';
  hasStarted?: boolean;
  /** 0 to 1, drawn as the progress ring. */
  progress?: number;
  /** Estimated_Time__c in minutes, or a label. */
  time?: number | string;
  meta?: { fields?: number; completedFields?: number; errors?: number };
  substeps?: Array<string | { title: string; description?: string }>;
  correctionDetails?: string;
  conditional?: boolean;
  /** null hides the button. Default follows status. */
  action?: { kind: 'primary' | 'resume' | 'start' | 'fix' | 'review' | 'secondary'; label: string; disabled?: boolean } | null;
  /** Page Button_Label__c for Start. Default "Start Step". */
  startLabel?: string;
  open?: boolean;
  current?: boolean;
}
/** formTemplateStages · Stages_Mode__c */
export interface StagesOverviewProps {
  title: string;
  subtitle?: string;
  lastSaved?: string;
  current?: string;
  stages: StagesOverviewStage[];
  /** Stage_Mode_Layout__c values. */
  layout?: Array<'Hide Progress Banner' | 'Hide Completed Fields' | 'Display Template Header'>;
  hideProgressBanner?: boolean;
  hideCompletedFields?: boolean;
  /** Display Template Header: the template's header form, usually a Banner (Overlay, Small, placement 'header'). Shown in place of title and subtitle when the layout includes Display Template Header (or displayTemplateHeader is true). */
  templateHeader?: React.ReactNode;
  displayTemplateHeader?: boolean;
  onSelect?: (stage: StagesOverviewStage) => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function StagesOverview(props: StagesOverviewProps): JSX.Element;

/** buttonsCustom · Buttons_Position__c · Button_Alignment__c */
export interface NavigationProps {
  /** Buttons_Position__c. Default "Docked". */
  position?: 'Docked' | 'Footer' | 'Standard';
  /** Button_Alignment__c. Default "center". */
  alignment?: 'start' | 'center' | 'end' | 'spread' | 'space';
  /** The previous page's label; shows Back. */
  backLabel?: string;
  back?: boolean;
  saveProgress?: boolean;
  saveProgressLabel?: string;
  /** Page Button_Label__c. Default "Continue". */
  nextLabel?: string;
  lastPage?: boolean;
  /** Submit_Button_Label__c. Default "Submit". */
  submitLabel?: string;
  /** Last page opens the review screen (utility:forward). */
  reviewNext?: boolean;
  /** Review_Page_Button_Label__c: labels the button that opens review. Default "Continue to Review"; picklist also has "Continue to Final Review", "Review & Submit", "Review Answers". */
  reviewLabel?: string;
  /** buttonsCustom showAsPath: the buttons draw as a path (lightning-progress-indicator type path). */
  showAsPath?: boolean;
  /** Path only: the label of the current step. */
  currentStage?: string;
  /** buttonsCustom groupButtons: every shown button in one lightning-button-group. */
  groupButtons?: boolean;
  /** buttonsCustom numberOfButtonsToShow (a form template passes 4). The rest go in the "Additional Actions" menu; 0 = menu only. */
  numberOfButtonsToShow?: number;
  /** buttonsCustom enableModal on the submit button: confirm before it runs. true uses the defaults. A button can also carry its own confirmModal. */
  confirmModal?: boolean | ConfirmModalProps;
  submitted?: boolean;
  readOnly?: boolean;
  buttons?: FormButtonProps[];
  infoText?: string;
  onClick?: (button: FormButtonProps) => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Navigation(props: NavigationProps): JSX.Element;
/** buttonsCustom: the form's button bar, navigation (Back, Save Progress, Continue, Submit) plus action buttons. Same component as Navigation. */
export declare function Buttons(props: NavigationProps): JSX.Element;

/** flowPagination: only the Form Repeater uses it (flowFormRepeat displayPagination), so it has no card of its own; see Repeater. */
export interface PaginationProps {
  total: number;
  pageSize?: number;
  page?: number;
  defaultPage?: number;
  onChange?: (page: number) => void;
  className?: string;
  style?: React.CSSProperties;
}
export declare function Pagination(props: PaginationProps): JSX.Element;

/** flowFormFieldReview */
export interface ReviewFieldProps {
  label: string;
  value?: unknown;
  type?: 'string' | 'boolean' | 'multipicklist' | 'currency' | 'percent' | 'double' | 'date' | 'datetime' | 'time' | 'email' | 'tel' | 'url' | 'richtext' | 'reference' | 'fileupload';
  /** reference: the related record's name. */
  relatedName?: string;
  /** reference: hide a raw Id from guests. */
  guest?: boolean;
  className?: string;
  style?: React.CSSProperties;
}
export declare function ReviewField(props: ReviewFieldProps): JSX.Element | null;

/** flowFormReview section block */
export interface ReviewSectionProps {
  title?: string;
  showHeader?: boolean;
  fields?: ReviewFieldProps[];
  /** Read Only: the link reads View. */
  readOnly?: boolean;
  editLabel?: string;
  /** Failed validation on submit. */
  invalid?: boolean;
  repeaterIndex?: number;
  repeaterTotal?: number;
  level?: 'form' | 'section';
  onEdit?: () => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function ReviewSection(props: ReviewSectionProps): JSX.Element;

/** formTemplate review screen · Enable_Review_Screen__c */
export interface ReviewPageProps {
  /** Review_Page_Label__c. Default "Review". */
  title?: string;
  /** Review_Page_Subtitle__c */
  subtitle?: string;
  pages?: Array<{ label?: string; sections: ReviewSectionProps[] }>;
  readOnly?: boolean;
  onEdit?: (page: unknown, section: unknown) => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function ReviewPage(props: ReviewPageProps): JSX.Element;


// ---- Group E: the form template around the pages ----
/** lightning-spinner size large, variant brand (formTemplate showBlockingSpinner). */
export interface SpinnerProps { size?: 'small' | 'medium' | 'large'; alternativeText?: string; /** Sit in the flow instead of covering the parent. */ inline?: boolean; className?: string; style?: React.CSSProperties }
export declare function Spinner(props: SpinnerProps): JSX.Element;

/** formLoadingStencil: shown while the template's prefill flow runs. */
export declare function LoadingStencil(props: { className?: string; style?: React.CSSProperties }): JSX.Element;

/** c-modal opened by a buttonsCustom button with enableModal. */
export interface ConfirmModalProps {
  /** modalHeading */
  heading?: string;
  /** modalSubheading */
  subheading?: string;
  /** modalBody (rich text) */
  body?: string;
  /** modalConfirmButtonLabel. Default "Confirm". */
  confirmLabel?: string;
  /** modalCancelButtonLabel. Default "Cancel". */
  cancelLabel?: string;
  /** modalTheme: the header band. Default slds-theme_default. */
  theme?: 'slds-theme_default' | 'slds-theme_shade' | 'slds-theme_inverse' | 'slds-theme_alt-inverse' | 'slds-theme_success' | 'slds-theme_info' | 'slds-theme_warning' | 'slds-theme_error' | 'slds-theme_offline';
  /** Draw in place instead of over the page, for previews. */
  inline?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function ConfirmModal(props: ConfirmModalProps): JSX.Element;

/** formTemplate message and state panels. */
export interface TemplateStateProps {
  /** inactive: IsActive__c off or outside Start_Date__c / Close_Date__c. The rest are error states. */
  state?: 'inactive' | 'prefillError' | 'paymentError' | 'loadError' | 'noForm' | 'missingRecord' | 'prefillTemplate';
  /** inactive: the title is "<Form Template Name> | Not Available". */
  templateName?: string;
  title?: string;
  /** Offline_Message__c for inactive; the error text otherwise. */
  message?: string;
  className?: string;
  style?: React.CSSProperties;
}
export declare function TemplateState(props: TemplateStateProps): JSX.Element;

/** formTemplate confirmation (after submit, unless Skip_Confirmation_Page__c). */
export interface ConfirmationPageProps {
  /** Confirmation_Page_Message__c (rich text). Default "Your response has been submitted." Confirmation_Page_Label__c is stored but not drawn. */
  message?: string;
  /** a Stripe receipt adds a brand "View Receipt" button (utility:new_window). */
  receiptUrl?: string;
  receiptLabel?: string;
  onViewReceipt?: (url: string) => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function ConfirmationPage(props: ConfirmationPageProps): JSX.Element;

/** Form_Template_Page__c header, drawn by c-header like a section header. */
export interface PageHeaderProps {
  /** Show_Header__c. Default true here. */
  showHeader?: boolean;
  /** Header_Style__c. Default "classic". */
  headerStyle?: 'classic' | 'classicSpread' | 'hero';
  /** Header_Title__c */
  title: string;
  /** Header_Subtitle__c */
  subtitle?: string;
  /** Header_Icon_Name__c */
  icon?: string;
  /** Header_Kicker__c (hero) */
  kicker?: string;
  /** Header_Lead__c (hero) */
  lead?: string;
  /** Header_Tags__c (hero), a list or a semicolon string. */
  tags?: string[] | string;
  /** Header_Tags_Position__c. Default "belowLead". */
  tagsPosition?: 'belowLead' | 'aboveEyebrow' | 'aboveKicker' | 'aboveTitle';
  /** Header_Footer__c (HTML) */
  footer?: string;
  /** Header_Text__c with Header_Text_Variant__c */
  text?: string;
  textVariant?: 'default' | 'highlight' | 'info' | 'warning' | 'error' | 'success';
  /** Header_Top_Margin__c. Default slds-m-top_none. */
  topMargin?: string;
  /** Header_Bottom_Margin__c. Default slds-m-bottom_none. */
  bottomMargin?: string;
  /** Form_Banner_Image__c / Form_Banner_Image_URL__c. NEEDS A BUILD CHANGE: the package stores it but no component draws it yet. */
  bannerImage?: string;
  bannerAlt?: string;
  titleColor?: string;
  subtitleColor?: string;
  iconColor?: string;
  className?: string;
  style?: React.CSSProperties;
}
export declare function PageHeader(props: PageHeaderProps): JSX.Element | null;

/** formSurveyQuestion: one question card in survey mode (Survey_Section__c). Wrap a field. */
export interface SurveyQuestionProps {
  /** The question in focus: brand border, lifted. Others sit under a white veil at 90%. */
  active?: boolean;
  /** "Question {position} of {total}", shown when total is over 1. */
  position?: number;
  total?: number;
  /** Required pill (from the wrapped field). */
  required?: boolean;
  /** Answered pill with a check. */
  answered?: boolean;
  /** Next button (Survey_Next, "Next"), brand on the active card. Default shown. */
  showNext?: boolean;
  nextLabel?: string;
  /** The question wraps a whole section (Likert): takes the 0.5rem inset. */
  section?: boolean;
  /** The active card grows toward the respondent; 1 to about 1.04. */
  scale?: number;
  onNext?: () => void;
  onActivate?: () => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function SurveyQuestion(props: SurveyQuestionProps): JSX.Element;
/** formSurveyScope: the run of survey questions. */
export declare function SurveyScope(props: { children?: React.ReactNode; className?: string; style?: React.CSSProperties }): JSX.Element;

/** The payment page. The Stripe form comes from the Stripe Connector, so this is a labelled stand-in. */
export interface PaymentStepProps { /** payment (Pay Now), subscription (Confirm Subscription), setup (Save Card) */ mode?: 'payment' | 'subscription' | 'setup'; buttonLabel?: string; /** Settings | Hide Header */ hideHeader?: boolean; /** Billing info, Stripe Address Element */ enableAddress?: boolean; /** Contact info, Link Authentication Element */ enableLink?: boolean; /** Settings | Display Express Checkout */ expressCheckout?: boolean; expressCheckoutButtonType?: 'donate' | 'book' | 'order' | 'plain' | 'subscribe' | 'buy' | 'checkout' | 'pay'; /** Payment method types shown as tabs */ tabs?: string[]; selectedTab?: string; /** Stripe's error message above the form */ paymentMessage?: string; /** Shows the Payment Unavailable state. */ error?: boolean | string; children?: React.ReactNode; className?: string; style?: React.CSSProperties }
export interface StripePaymentElementProps { tabs?: string[]; selected?: string }
export declare function StripePaymentElement(props: StripePaymentElementProps): JSX.Element;
export declare function PaymentStep(props: PaymentStepProps): JSX.Element;


/** flowToolKitBrandFooter: the support band under builder setting editors. Logo not included. */
export declare function BrandFooter(props: { promptText?: string; className?: string; style?: React.CSSProperties }): JSX.Element;

/** formTemplate: the shell around pages. Props follow Form_Template__c. */
export interface FormTemplateProps {
  /** Stages_Mode__c: overview of the pages, or inside one step (Return / Save Progress / Mark Complete). */
  stagesMode?: boolean;
  view?: 'overview' | 'step';
  /** StagesOverview rows for the overview view. */
  stageRows?: Array<Record<string, unknown>>;
  /** Extra StagesOverview props for the overview view. */
  overview?: Record<string, unknown>;
  /** Pages already complete in a step view (Stages Mode marks none by default). */
  completeStages?: string[];
  /** false hides Save Progress in the Stages buttons. */
  saveProgress?: boolean;
  /** active (default), loading (prefill flow running), inactive, confirmation, error. */
  state?: 'active' | 'loading' | 'inactive' | 'confirmation' | 'error';
  errorType?: 'loadError' | 'noForm' | 'missingRecord' | 'prefillError' | 'paymentError' | 'prefillTemplate';
  errorMessage?: string;
  /** Form Template Name (the inactive title). */
  name?: string;
  /** Offline_Message__c */
  offlineMessage?: string;
  /** Confirmation_Page_Message__c */
  confirmationMessage?: string;
  receiptUrl?: string;
  onViewReceipt?: (url: string) => void;
  /** FormQualifiedApiName_Header__c / Template_Header_Text__c: draw the header form here. */
  header?: React.ReactNode;
  /** FormQualifiedApiName_Footer__c / Template_Footer_Text__c: drawn read only (disable-all). */
  footer?: React.ReactNode;
  /** Page labels in order. */
  stages?: string[];
  currentStage?: string;
  /** Hide_Stage_Indicator__c */
  hideStageIndicator?: boolean;
  /** Stage_Indicator_Type__c and any StageIndicator props. */
  stageIndicator?: Partial<StageIndicatorProps>;
  /** The current page's header (Show_Header__c and the Header_* fields). */
  pageHeader?: PageHeaderProps;
  /** Buttons_Position__c. Default "Standard" here. */
  buttonsPosition?: 'Docked' | 'Footer' | 'Standard';
  buttonAlignment?: 'start' | 'center' | 'end' | 'spread' | 'space';
  /** Navigation props for the page's buttons; false hides them. */
  navigation?: Partial<NavigationProps>;
  buttons?: false;
  /** Whole form read only (disable-all), as on a submitted form. */
  readOnly?: boolean;
  /** The blocking brand spinner over the template. */
  blockingSpinner?: boolean;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}
export declare function FormTemplate(props: FormTemplateProps): JSX.Element;

/** formBanner: the Banner section type (sectionType bannerSection). Settings are the section's Banner__c JSON. */
export interface BannerProps {
  /** Default "overlay". Compact for a single-page form; Overlay at Small for a multi-page form with the vertical page indicator or stages mode; Split for a very simple title. */
  layout?: 'overlay' | 'split' | 'compact';
  /** Default "small", which follows its text. Medium 240px and Large 340px minimum. Overlay and Split match at every size. */
  height?: 'small' | 'medium' | 'large';
  /** Pills above the title: a list, or one semicolon string (also how a multi-select picklist merge field arrives). */
  tags?: string[] | string;
  /** Rich text (HTML) or plain text. Merge fields work in the package. */
  title?: string;
  subtitle?: string;
  /** imageAsset, or the record field override. Optional: without it the banner shows backgroundColor. */
  image?: string;
  /** Empty marks the photo as decoration. */
  imageAlt?: string;
  /** logoAsset. No field override. */
  logo?: string;
  logoAlt?: string;
  /** Default follows the layout: Overlay square, Split and Compact circle. None keeps the logo and drops its white card. */
  logoShape?: 'square' | 'circle' | 'none';
  /** Fills the Split panel, and the banner with no image. Empty is the brand color. */
  backgroundColor?: string;
  /** Tint behind the text on the photo. */
  scrimColor?: string;
  /** Percent, default 72. */
  scrimOpacity?: number;
  /** Pill fill; text turns white on a dark color. */
  tagColor?: string;
  /** Where it renders: "body" (default, bleeds 0.75rem past the fields), "header" (the Form Template header), "singleCardHeader" (header of a template with no vertical page indicator: square bottom corners). */
  placement?: 'body' | 'header' | 'singleCardHeader';
  /** The section's Padding Top, Bottom and Horizontal (SLDS class names such as slds-p-top_large), applied inside the banner. */
  paddingTop?: string;
  paddingBottom?: string;
  paddingHorizontal?: string;
  className?: string;
  style?: object;
}
export declare function Banner(props: BannerProps): JSX.Element;
