/** FlowToolKit Site Blocks. Every block component is the package's siteDesignBlock; its props are the block's JSON keys. */
export interface SiteTheme { brand?: string; accent?: string; font?: string; headingFont?: string; text?: string; }
/** Site type: "aura" (the base) or "lwr". Everything drawn follows it, and the stylesheet with it. */
export type SiteType = "aura" | "lwr";
/** Switches every component drawn, and the stylesheet, to one site type. The preview cards' Aura / LWR switch calls it. */
export declare function setSite(site: SiteType): void;
/** The page: the theme layout around a content region of Sections. site "aura" (default) or "lwr". On Aura, layout "buildYourOwn" (default, no visible header or footer) or "customerService" (logo, search, login, navigation bar and footer). On LWR, the Build Your Own (LWR) layout, whose header and footer regions each hold a Section: pass header and footer as Sections or as content for one. */
export declare function Page(props: { site?: SiteType; header?: any; theme?: SiteTheme; layout?: "buildYourOwn" | "customerService"; maxWidth?: string; logo?: string; siteName?: string; navItems?: Array<string | { label: string; href?: string }>; currentNav?: number; searchPlaceholder?: string; search?: boolean; loginLabel?: string; footer?: string | any; children?: any }): JSX.Element;
/** Lays a preview out at a desktop width and zooms it into its card, settling width media queries at that width. */
export declare function previewAt(width: number): void;
/** forceCommunity:section on Aura, community_layout:section on LWR. Columns are Column children whose widths add up to 12, one to four of them. background, backgroundOverlay, contentAreaWidth and sectionHeight are Aura only; sectionVerticalAlign is LWR only. */
export declare function Section(props: { background?: string; backgroundOverlay?: string; contentAreaWidth?: number; sectionHeight?: number; sectionVerticalAlign?: "flex-start" | "center" | "flex-end"; showGrid?: boolean; children?: any }): JSX.Element;
/** A section column. columnWidth 1 to 12; it stacks to full width below 1024px on both site types. */
export declare function Column(props: { columnWidth?: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12" | number; children?: any }): JSX.Element;
/** Form (Header) placed on a site with Display as Divider on. */
export declare function Divider(props: { dividerStyle?: "line" | "compact" | "centered" | "label" | "bookmark" | "ornament" | "pill" | "chevron" | "double" | "icon" | "fade" | "tag"; title?: string; subtitle?: string; iconName?: string; richText?: string; topMargin?: string; bottomMargin?: string }): JSX.Element;
/** A form or FlowToolKit component placed in a column, drawn by the FlowToolKit Forms design system's own bundle (Contact Us, Volunteer Application, Grant Application, or any FTK component with componentProps). Falls back to a labelled frame. */
export declare function FormSlot(props: { form: string; kind?: "Form Template" | "Flow" | "Record Card form" | "FlowToolKit component"; component?: string; componentProps?: Record<string, any>; formProps?: Record<string, any>; formStyle?: Record<string, any>; frame?: boolean; description?: string; href?: string; height?: number }): JSX.Element;
/** Rich Content Editor (forceCommunity:richTextInline; on LWR community_builder:richTextEditor). */
export declare function RichContent(props: { richTextValue: string }): JSX.Element;
/** HTML Editor (forceCommunity:htmlBlock; on LWR community_builder:htmlEditor). Scripts, frames and embeds are flagged and left out, as an Aura site strips them. */
export declare function HtmlEditor(props: { richTextValue: string; designTag?: boolean }): JSX.Element;
/** Tabs (forceCommunity:tabset; on LWR dxp_layout:tabs). One child per tab, in order. */
export declare function Tabs(props: { tabs: Array<{ tabName: string; tabKey?: string }>; activeTab?: string; useOverflowMenu?: boolean; children?: any }): JSX.Element;
/** Search (forceCommunity:searchBox; on LWR dxp_search:searchInput, which draws Builder's defaults and ignores placeholder and buttonLabel). */
export declare function Search(props: { placeholder?: string; buttonLabel?: string }): JSX.Element;
/** Language Selector (forceCommunity:languagePicker; on LWR dxp_base:languageSelector). Draws nothing with one language. */
export declare function LanguageSelector(props: { languages?: string[]; current?: string }): JSX.Element;
/** formDynamicRepeater drawn as its grid of record cards. Each record is a Record Card's JSON. */
export declare function Repeater(props: { cardType?: string; columns?: 1 | 2 | 3 | 4; records: Array<Record<string, any>> }): JSX.Element;
/** Any block by sectionType. */
export declare function Block(props: BlockProps & { sectionType: string }): JSX.Element;

/* Generated from the package's siteDesignBlockConfig and its property editor. */
export interface BlockProps {
    /** Background: Accent Color. The block's second brand color. It is the second stop of the Brand Gradient and Accent Top Bar card styles, the hero's glow washes and heading highlight, accent pills, timeline dots, non-featured pricing buttons, and the accent ink on a dark background. */
    accentColor?: string;
    /** Background: Accent Color Opacity */
    accentColorOpacity?: number;
    /** Arrangement: Arrangement */
    arrangement?: "stacked" | "split";
    /** Spacing */
    attachToPrevious?: string;
    /** Background: Background */
    background?: string;
    /** Background: Gradient End. The color the gradient finishes on, starting from the Background. Leave empty to fade into a darker shade of the background, or into the accent color when no background color is set. */
    backgroundAccentColor?: string;
    /** Background: Gradient End Opacity */
    backgroundAccentOpacity?: number;
    /** Images: Photo Motion. Movement applied to the background image. Both effects play in the builder and on the site, and stop for visitors who prefer reduced motion. */
    backgroundEffect?: "none" | "parallax" | "kenburns";
    /** Background: Gradient. Direction the background fades into the background accent. Works with or without a background color. */
    backgroundGradient?: "off" | "banner" | "diagonal" | "vertical" | "horizontal" | "radial" | "spotlight" | "corner";
    /** Background: Gradient Midpoint. Optional third color the gradient passes through at 55%. */
    backgroundMidColor?: string;
    /** Background: Gradient Midpoint Opacity */
    backgroundMidOpacity?: number;
    /** Background: Background Opacity */
    backgroundOpacity?: number;
    /** Images: Photo Overlay. Tint layered over the background image so headings and copy stay readable. Only paints when a background image is set. */
    backgroundOverlay?: "auto" | "none" | "bottom" | "side" | "tint" | "light" | "custom";
    /** Images: Overlay Color. Leave empty to tint with the block's own background, or a deep navy when that is light. The opacity applies to the Custom overlay; the other recipes carry their own. */
    backgroundOverlayColor?: string;
    /** Images: Drift Speed. How far the photo lags the page as the block scrolls past. */
    backgroundParallaxSpeed?: "0.15" | "0.25" | "0.4" | "0.6";
    /** Background: Texture. Faint pattern layered over the background, whatever the background is. */
    backgroundTexture?: "off" | "crosshatch" | "stripes" | "dots" | "grid";
    /** Badges: Badge Alignment */
    badgeAlign?: "left" | "center" | "right";
    /** Badges: Badge Position */
    badgePosition?: "bottom" | "top";
    /** Badges: Space Below Badges */
    badgesGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Images: Block Height. Minimum height for image-led blocks. Content taller than the preset grows the block rather than being cut off. */
    blockHeight?: "auto" | "band" | "standard" | "tall";
    /** Body: Block Title Color. Ink for the large title beside the image. Leave empty to follow the body text colour. */
    blockTitleColor?: string;
    /** Body: Block Title Color Opacity */
    blockTitleColorOpacity?: number;
    /** Body / Items / Card Style: Alignment */
    bodyAlign?: "left" | "center" | "right";
    /** Body: Space Below Body */
    bodyGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Border: Bottom */
    borderBottom?: string;
    /** Border: Border Color. Leave empty to use the brand color. */
    borderColor?: string;
    /** Border: Border Color Opacity */
    borderColorOpacity?: number;
    /** Border: Left */
    borderLeft?: string;
    /** Border: Right */
    borderRight?: string;
    /** Border: Top */
    borderTop?: string;
    /** Border: Border Width (px) */
    borderWidth?: string;
    /** Background: Brand Color. Overrides the site brand color for this block. */
    brandColor?: string;
    /** Background: Brand Color Opacity */
    brandColorOpacity?: number;
    /** Bullets: Check Color. Fill behind every bullet's tick. Leave empty to follow the block's accent color. */
    bulletCheckColor?: string;
    /** Bullets: Check Color Opacity */
    bulletCheckColorOpacity?: number;
    /** Bullets: Description Color. Ink for every bullet description. Leave empty to derive from the background. */
    bulletTextColor?: string;
    /** Bullets: Description Color Opacity */
    bulletTextColorOpacity?: number;
    /** Bullets: Title Color. Ink for every bullet title. Leave empty to derive from the background. */
    bulletTitleColor?: string;
    /** Bullets: Title Color Opacity */
    bulletTitleColorOpacity?: number;
    /** Bullets: Space Below Bullets */
    bulletsGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Buttons: Button Alignment */
    buttonAlign?: "left" | "center" | "right";
    /** Arrangement: Button Placement. With the heading keeps the buttons above the two columns. Under the copy ends the copy's column with them. */
    buttonPlacement?: "heading" | "copy";
    /** Buttons: Space Below Buttons */
    buttonsGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Background: Card Background */
    cardBackgroundColor?: string;
    /** Background: Card Background Opacity */
    cardBackgroundOpacity?: number;
    /** Card Style: Card Layout. Inline puts the icon beside the title for compact chips. */
    cardLayout?: "stacked" | "inline" | "banner";
    /** Card Style: Card Media. How an item's Icon Image URL renders. Cover ignores the icon backdrop. */
    cardMedia?: "icon" | "cover";
    /** Bullets / Card Style: Card Style */
    cardStyle?: "flat" | "outlined" | "elevated" | "deep" | "glow" | "topbar" | "siderule" | "gradient" | "ghost" | "inset" | "clean" | "joined";
    /** Items: Auto-advance. How long each slide holds. Auto-advance pauses on hover, stops while the block is off screen, and stops entirely for visitors who prefer reduced motion. Arrows, dots and swipe always work. */
    carouselInterval?: "0" | "4" | "5" | "8";
    /** Items / Card Style: Columns */
    columns?: "2" | "3" | "4" | "5";
    /** Images: Content Position. Where the copy sits in the block's vertical space. Only has an effect once a Block Height is set. */
    contentPosition?: "center" | "bottom" | "top";
    /** Arrangement: Copy Width */
    copyWidth?: "full" | "column";
    /** Items / Stats */
    countUp?: string;
    /** Motion: Entrance. Plays once as the block scrolls into view, never on revisit. Keep one entrance style per page. */
    entrance?: "" | "rise" | "cascade" | "wipe" | "zoom" | "blur";
    /** Items: Display. Rows is the At-a-glance card. Bars reads each value as a percentage. */
    factsDisplay?: "rows" | "bars" | "stacked" | "segmented";
    /** Footnote: Footnote Alignment */
    footnoteAlign?: "left" | "center" | "right";
    /** Footnote: Space Above Footnote */
    footnoteGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Items: Layout */
    galleryLayout?: "mosaic" | "grid" | "masonry" | "filmstrip";
    /** Heading: Space Below Heading. The gap between the heading and the content under it. None puts the content right under the heading. */
    headerGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Arrangement: Heading Position. Across the top runs the heading the full width, with the body and the media side by side under it. */
    headerPlacement?: "column" | "above";
    /** Heading: Heading Alignment */
    headingAlign?: "left" | "center" | "right";
    /** Heading: Heading Style */
    headingStyle?: "standard" | "statement";
    /** Arrangement: Button Placement */
    heroLayout?: "stacked" | "band";
    /** Media: Media. What sits beside the copy: the image, a Facts panel, a Timeline, Bullets, or nothing. */
    heroMedia?: "image" | "facts" | "timeline" | "bullets" | "none";
    /** Motion: Hover. Pointer feedback for the block's items. Use it only when they actually link somewhere. */
    hoverStyle?: "" | "lift" | "tilt" | "trace" | "ring" | "tint";
    /** Items: Icon Color. Ink for every item icon. Plain tints the glyph itself; Tile and Circle use it as the backdrop with a white glyph over it. An item with its own Icon Color overrides this. */
    iconColor?: string;
    /** Items: Icon Color Opacity */
    iconColorOpacity?: number;
    /** Items / Card Style: Icon Size. Small suits checklist rows; Large is the feature-icon default. */
    iconSize?: "xx-small" | "x-small" | "small" | "medium" | "large";
    /** Items / Card Style: Icon Style. Backdrop behind each item icon, tinted with the brand color. Circle renders solid brand with a white glyph. */
    iconStyle?: "plain" | "tile" | "circle";
    /** Media / Image / Images: Image Alt Text */
    imageAlt?: string;
    /** Media / Image / Images: Image Bleed. Lets artwork run past the section padding. */
    imageBleed?: "none" | "bottom" | "edge";
    /** Image: Caption Style. Where the image's title and description render, or whether they render at all. */
    imageCaption?: "below" | "overlay" | "none";
    /** Media / Image / Images: Image Fit. Fill crops the image to the space it sits in. Fit keeps the whole image and may leave room around it. */
    imageFit?: "fill" | "fit" | "natural";
    /** Media / Image / Images: Image Style */
    imageStyle?: "flat" | "outlined" | "elevated" | "deep" | "glow" | "topbar" | "siderule" | "gradient" | "ghost" | "inset" | "clean" | "joined" | "mascot";
    /** Items: Description Color. Ink for every point's description. Leave empty to derive from the background. */
    itemTextColor?: string;
    /** Items: Description Color Opacity */
    itemTextColorOpacity?: number;
    /** Items: Label Color. Ink for every label. An item with its own Label Color overrides this. Leave empty to derive from the background. */
    labelColor?: string;
    /** Items: Label Color Opacity */
    labelColorOpacity?: number;
    /** Items: Title Size. Scales every stat title relative to the block's body text. A stat with its own Title Size overrides this. */
    labelSize?: "" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Margin Bottom */
    marginBottom?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Margin Top */
    marginTop?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Bottom */
    overlapBottom?: string;
    /** Spacing: Overlap Amount (px) */
    overlapMargin?: string;
    /** Spacing: Top */
    overlapTop?: string;
    /** Spacing: Padding Bottom */
    paddingBottom?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Padding Left */
    paddingLeft?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Padding Right */
    paddingRight?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Spacing: Padding Top */
    paddingTop?: "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Items / Bullets: Item Display. Cards renders each item as its own small panel instead of a ticked bullet. */
    showcaseItems?: "list" | "cards";
    /** Arrangement: Column Ratio. Balance of the two columns in any side-by-side arrangement. */
    splitRatio?: "even" | "left" | "right";
    /** Stats: Label Color. Ink for every inline stat label. Leave empty to derive from the background. */
    statLabelColor?: string;
    /** Stats: Label Color Opacity */
    statLabelColorOpacity?: number;
    /** Stats: Value Color. Ink for every inline stat value. Leave empty to derive from the background. */
    statValueColor?: string;
    /** Stats: Value Color Opacity */
    statValueColorOpacity?: number;
    /** Stats: Space Below Stats */
    statsGap?: "default" | "none" | "xxx-small" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Items: Stats Treatment. One named layout for the row. Blocks saved with the old layout knobs open on the matching treatment and keep rendering until a new one is picked. */
    statsTreatment?: "row" | "tiles" | "spread";
    /** Items: Table Badge Fill. Used by any column set to the Badge display. */
    tableBadgeBackground?: string;
    /** Items: Table Badge Fill Opacity */
    tableBadgeBackgroundOpacity?: number;
    /** Items: Table Badge Text */
    tableBadgeColor?: string;
    /** Items: Table Badge Text Opacity */
    tableBadgeColorOpacity?: number;
    /** Items: Table Grid Lines */
    tableGridColor?: string;
    /** Items: Table Grid Lines Opacity */
    tableGridColorOpacity?: number;
    /** Columns: Table Header Fill */
    tableHeaderBackground?: string;
    /** Columns: Table Header Fill Opacity */
    tableHeaderBackgroundOpacity?: number;
    /** Columns: Table Header Text */
    tableHeaderColor?: string;
    /** Columns: Table Header Text Opacity */
    tableHeaderColorOpacity?: number;
    /** Items: Highlighted Row Fill */
    tableRowHighlight?: string;
    /** Items: Highlighted Row Fill Opacity */
    tableRowHighlightOpacity?: number;
    /** Body: Text Color. Overrides body and label ink. Leave empty to derive from the background. */
    textColor?: string;
    /** Body: Text Color Opacity */
    textColorOpacity?: number;
    /** Items: Marker Base. Fill behind each milestone marker. White by default so the markers read against any background. The ring around them follows the block's background on its own. */
    timelineBaseColor?: string;
    /** Items: Marker Base Opacity */
    timelineBaseColorOpacity?: number;
    /** Items: Marker Ink. The number or check inside each marker. Set this when a dark Marker Base needs a light symbol over it. */
    timelineMarkerInk?: string;
    /** Items: Marker Ink Opacity */
    timelineMarkerInkOpacity?: number;
    /** Items: Orientation. Horizontal is the cycle stepper; vertical is the process journey. */
    timelineOrientation?: "horizontal" | "vertical";
    /** Items: Value Color. Ink for every value. An item with its own Value Color overrides this. Leave empty to derive from the background. */
    valueColor?: string;
    /** Items: Value Color Opacity */
    valueColorOpacity?: number;
    /** Items: Value Size. Scales every stat value relative to the block's body text. Default follows the treatment: display scale in a row, body scale in tiles and inline. A stat with its own Value Size overrides this. */
    valueSize?: "" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large";
    /** Arrangement: Vertical Alignment. How the two columns align against each other: start, center, end, or stretch to fill the row. */
    verticalAlign?: "start" | "center" | "end" | "stretch";
    /** Spacing: Width. Blocks stay inside their container by default. Full Bleed and Inset Band break out to the viewport, so only use them in a full width region. */
    width?: "contained" | "full" | "inset";
    buttons?: Array<{ label?: string; description?: string; type?: "url" | "formTemplate" | "formSubmission" | "flow" | "recordForm"; url?: string; target?: "same" | "new"; templateId?: string; flowApiName?: string; recordSource?: string; formMode?: "edit" | "readOnly"; recordField?: string; formQualifiedApiName?: string; modalWidth?: "small" | "medium" | "large" | "full"; modalHeader?: string; modalSubheader?: string; style?: "brand" | "light" | "accent" | "outline" | "link" | "panel"; backgroundColor?: string; textColor?: string }> | string;
    badges?: Array<{ title?: string; style?: "neutral" | "brand" | "accent" | "outline"; pulse?: boolean }> | string;
    tableColumns?: Array<{ label?: string; width?: "auto" | "narrow" | "wide" | "widest" | "fit"; align?: "left" | "center" | "right"; display?: "text" | "richtext" | "badge" | "emphasis"; hideOnTablet?: boolean }> | string;
}

/** Hero block: sectionType "hero". */
export interface HeroProps extends BlockProps {
    /** Heading: Section Label. Small uppercase eyebrow above the heading. */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Body: Body Title. Optional title above the body copy. Most useful with Heading Position set to Across the top. */
    blockTitle?: string;
    /** Body: Body Copy. Optional paragraph under the body title. */
    description?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Facts, up to 6 */
    items?: Array<{ title?: string; value?: string }> | string;
    /** Bullets */
    bullets?: Array<{ title?: string; description?: string }> | string;
    /** Inline Stats, up to 5 */
    stats?: Array<{ title?: string; value?: string }> | string;
}
export declare function Hero(props: HeroProps): JSX.Element;

/** Stats block: sectionType "statsBar". */
export interface StatsBarProps extends BlockProps {
    /** Stats, up to 5 */
    items?: Array<{ title?: string; value?: string; titleColor?: string; valueColor?: string; titleSize?: "" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large"; valueSize?: "" | "xx-small" | "x-small" | "small" | "medium" | "large" | "x-large" | "xx-large"; iconType?: "icon" | "image"; icon?: string; iconColor?: string; iconImage?: string }> | string;
}
export declare function StatsBar(props: StatsBarProps): JSX.Element;

/** Facts block: sectionType "facts". */
export interface FactsProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Supporting Copy */
    subheading?: string;
    /** Footnote: Footnote */
    footnote?: string;
    /** Facts, up to 10 */
    items?: Array<{ title?: string; value?: string; labelColor?: string; valueColor?: string }> | string;
}
export declare function Facts(props: FactsProps): JSX.Element;

/** Timeline block: sectionType "timeline". */
export interface TimelineProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Footnote: Footnote */
    footnote?: string;
    /** Milestones, up to 8 */
    items?: Array<{ title?: string; meta?: string; state?: "upcoming" | "current" | "done" | "warning" }> | string;
}
export declare function Timeline(props: TimelineProps): JSX.Element;

/** Quote block: sectionType "quote". */
export interface QuoteProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Body: Quote */
    description?: string;
    /** Body: Attribution */
    attribution?: string;
    /** Body: Attribution Detail. Role or context line, such as "Executive Director, 2025 grantee". */
    attributionDetail?: string;
}
export declare function Quote(props: QuoteProps): JSX.Element;

/** Action Card block: sectionType "actionCard". */
export interface ActionCardProps extends BlockProps {
    /** Body: Label. The row label beside the big value, such as "Closes in" or "Seats remaining". */
    heading?: string;
    /** Body: Deadline (date). A date the card counts down to. Merge fields work, so {{Close_Date__c}} makes it record-driven. */
    deadline?: string;
    /** Body: Opens (date). Optional cycle start. With both dates the progress bar tracks the open window. */
    opensOn?: string;
    /** Body: Progress Current. Numeric alternative to the dates: the remaining count, such as seats left. */
    progressCurrent?: string;
    /** Body: Progress Total. The total the current value counts against. */
    progressTotal?: string;
    /** Footnote: Microcopy. The small line under the buttons, such as "Save and return any time". */
    footnote?: string;
}
export declare function ActionCard(props: ActionCardProps): JSX.Element;

/** Carousel block: sectionType "carousel". */
export interface CarouselProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Slides */
    items?: Array<{ iconImage?: string; imageAlt?: string; eyebrow?: string; title?: string; link?: string; target?: "same" | "new" }> | string;
}
export declare function Carousel(props: CarouselProps): JSX.Element;

/** Image block: sectionType "image". */
export interface ImageProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading. Doubles as the image caption when Caption Style puts a caption below or over the photo. */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
}
export declare function Image(props: ImageProps): JSX.Element;

/** Image Gallery block: sectionType "gallery". */
export interface GalleryProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the photos. */
    footnote?: string;
    /** Photos */
    items?: Array<{ image?: string; imageAlt?: string }> | string;
}
export declare function Gallery(props: GalleryProps): JSX.Element;

/** Cards block: sectionType "cards". */
export interface CardsProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Heading: Emphasis Line. Rendered larger, directly under the subheading. */
    description?: string;
    /** Cards */
    items?: Array<{ eyebrow?: string; title?: string; description?: string; meta?: string; labelColor?: string; valueColor?: string; link?: string; target?: "same" | "new"; linkLabel?: string; iconType?: "icon" | "image"; icon?: string; iconColor?: string; iconImage?: string }> | string;
}
export declare function Cards(props: CardsProps): JSX.Element;

/** Steps block: sectionType "steps". */
export interface StepsProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Footnote: Footnote */
    footnote?: string;
    /** Steps */
    items?: Array<{ title?: string; description?: string; link?: string; target?: "same" | "new"; linkLabel?: string }> | string;
}
export declare function Steps(props: StepsProps): JSX.Element;

/** Pricing block: sectionType "pricing". */
export interface PricingProps extends BlockProps {
    /** Heading: Section Label */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Subheading */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Pricing Tiers, up to 6 */
    items?: Array<{ title?: string; value?: string; description?: string; link?: string; target?: "same" | "new"; linkLabel?: string; features?: string; featured?: boolean }> | string;
}
export declare function Pricing(props: PricingProps): JSX.Element;

/** Callout block: sectionType "callout". */
export interface CalloutProps extends BlockProps {
    /** Heading: Eyebrow */
    sectionLabel?: string;
    /** Heading: Statement */
    heading?: string;
    /** Heading: Supporting Copy */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Heading: Emphasis Line. Rendered larger, directly under the supporting copy. */
    description?: string;
}
export declare function Callout(props: CalloutProps): JSX.Element;

/** Comparison Table block: sectionType "table". */
export interface TableProps extends BlockProps {
    /** Heading: Eyebrow */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Supporting Copy */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Rows */
    items?: Array<{ featured?: boolean }> | string;
    /** Columns, up to 6 */
    columns?: Array<{ label?: string; width?: "auto" | "narrow" | "wide" | "widest" | "fit"; align?: "left" | "center" | "right"; display?: "text" | "richtext" | "badge" | "emphasis"; hideOnTablet?: boolean }> | string;
}
export declare function Table(props: TableProps): JSX.Element;

/** Tag Cloud block: sectionType "pills". */
export interface PillsProps extends BlockProps {
    /** Heading: Eyebrow */
    sectionLabel?: string;
    /** Heading: Heading */
    heading?: string;
    /** Heading: Supporting Copy */
    subheading?: string;
    /** Footnote: Footnote. Small line rendered below the section content. */
    footnote?: string;
    /** Pills */
    items?: Array<{ title?: string; style?: "neutral" | "brand" | "accent" | "outline"; link?: string; target?: "same" | "new"; iconImage?: string }> | string;
}
export declare function Pills(props: PillsProps): JSX.Element;

/** Record Card block: sectionType "recordCard". */
export interface RecordCardProps extends BlockProps {
    /** Detail Rows, up to 6 */
    items?: Array<{ title?: string; value?: string }> | string;
}
export declare function RecordCard(props: RecordCardProps): JSX.Element;
