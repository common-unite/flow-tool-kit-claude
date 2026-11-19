# The header, the logo and the brand styles

## The header

Every form gets a Banner in the Form Template header: the title, a one-line subtitle, up to three tags, a photo and the logo. Never a logo row, and never a page header repeating the title.

Flow Tool Kit ships one Banner header, **Header (Banner)** (`Form_Header_Banner`, Overlay layout), and puts it on every new template. Its Banner section merges everything from the template it heads:

| Banner setting | Merges | Set on the Form Template from |
|---|---|---|
| Title | `{{Name}}` | `template.Name` |
| Subtitle | `{{FlowToolKit__Form_Template_Subtitle__c}}` | `template.banner.subtitle` |
| Tags | `{{FlowToolKit__Header_Tags__c}}`, one pill per `;` | `template.banner.tags` |
| Image | `{{FlowToolKit__Form_Banner_Image__c}}` | `assets.banner`, else the package's banner photo |
| Logo Override Field | `{{FlowToolKit__Logo__c}}`: the template's Logo Override, else the org Default Logo | `assets.logo` (below) |
| Logo Alt Text Override Field | `{{FlowToolKit__Logo_Alt_Text__c}}` | `assets.logo_alt` |
| Fill | the brand color, `--ftk-color-primary` | the brand styles (below) |

So one header serves every template, and nothing in a header belongs to one form.

| The form | Header | How the build gets it |
|---|---|---|
| Two or more pages (`banner.layout` overlay) | Header (Banner), Overlay | Sets `FormQualifiedApiName_Header__c` to the packaged header |
| One page (compact) | A Compact Banner | Creates `HDR_Banner_Compact` once per org, then reuses it |
| Named Split | A Split Banner | Creates `HDR_Banner_Split` once per org, then reuses it |
| `header: "metadata"` | Your own header form | Uses the name in `template.FormQualifiedApiName_Header__c` after checking it is built on Form Template |

The created headers are record components on Form Template with exactly the packaged Banner settings and only the layout changed, filed in the Headers folder. `--refresh-headers` rewrites them (after a Flow Tool Kit upgrade adds the logo fields, for example). On a site, guests read record components only through a guest sharing rule on Form Component (after-the-build.md). An org on a Flow Tool Kit release without the packaged Banner header gets an Overlay one created the same way.

A header form must be built on Form Template, never Form Submission: the template's Header/Footer tab lists only Form Template forms and clears any other the first time someone opens it.

## The logo

The Logo and Logo Alt Text fields on Form Template are formulas: the template's **Logo Override** when it is set, otherwise the org's **Default Logo** from Form Builder's Global Styles tab. Both hold an Asset File name or an `https://` link.

| The org's Default Logo | Brand kit saved for the org | The build |
|---|---|---|
| Blank | Yes | Sets the Default Logo (and alt text): every template on the Banner shows it |
| The same logo | Yes | Nothing |
| Another logo | Yes | Sets this template's Logo Override |
| Any | No | Sets this template's Logo Override |

The Logo fields (`Logo_Override__c`, `Logo_Alt_Text_Override__c` and the `Logo__c` and `Logo_Alt_Text__c` formulas) came with Flow Tool Kit 5.4. On a 5.3 org the build puts the logo on the banner itself: the Banner's own logo image setting (`logoAsset`, with `logoAlt` for the alt text) in a header record component named after the logo, `HDR_Banner_<Layout>_<logo Asset File name>` (at most 40 characters), shared by every template with that logo. The packaged Overlay header cannot carry a logo there, so an Overlay form on 5.3 gets its own Overlay header the same way. After the upgrade a rebuild uses the Logo fields and the usual header. An org before 5.3 cannot create record components: the build sets no logo there and says to upgrade.

## Colors

The Banner fills with the brand color, `--ftk-color-primary`, from the template's Style Overrides or the org's defaults, so a template's brand color needs no extra field. An org that serves several brands and wants the banner's own color set per template can add a Text field `Brand_Color__c` on Form Template (a description, and Read for guests): the Compact and Split headers then merge it into Background Color, and the build fills it from the plan's brand color. An empty value, or text that is not a color, is ignored and the brand color shows. The packaged Overlay header keeps the brand color fill.

## Brand styles: add-only

The org's Form Style defaults (Global Styles tab, the Form Style Defaults custom setting) are what every template inherits. For each brand value in `styleTokens`:

| The org's value | The build |
|---|---|
| Blank | Adds the brand value to the org defaults |
| The same | Nothing |
| Different | Keeps the org's value; the brand value goes on this template's Style Overrides |

Only brand values go org-wide: the brand color with its hover, active and text-on colors, the fonts and heading weight, and the corner radii. Only when the project config says the brand kit is the org's own (`brand_kit.choice` use, update or new). Layout values from the house rules (text, input and border size, spacing, label and border colors, section frame colors) and every value of a form without a brand kit go on the template only, so building one form never restyles the others.

**Writing the setting.** It is a protected custom setting. Writing it through the REST API was tested in a subscriber org (Flow Tool Kit 5.2, a System Administrator): insert, update, read and delete all worked. If an org refuses the write or the read:

- the brand values go on the template, so the form looks right now;
- with the org's current values readable, the build writes `global-styles-import.json`: the current values plus the brand, because **Import replaces every saved org style**. Paste it in Form Builder, Global Styles, Import, then Preview import and Save org defaults;
- with nothing readable, it writes `global-styles-additions.json`. Export the Global Styles first, save the JSON, then `python3 scripts/brandstyles.py merge --export exported.json --additions global-styles-additions.json` writes the import file;
- set the Default Logo in the same tab's Logo group with Select Image.

The template keeps the packaged default theme. A brand never becomes a new Form Theme: only the default theme yields to the Style Editor, so a theme of its own would freeze frames, radius and colors.
