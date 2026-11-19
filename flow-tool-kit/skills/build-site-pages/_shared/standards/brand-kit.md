# Brand kit

Where a saved brand kit lives in the org and the keys of `brand-kit.json`, so every skill reads a saved brand the same way. The brand-kit skill writes it; org-catalog, ftk-start, form-design, build-template, build-email-templates and build-site-pages read it. A brand kit is optional: without one, forms use Flow Tool Kit's default style.

## Where a saved kit lives

A confirmed kit is saved to the org in one step, before any form is designed:

- **Style values** in the org's Form Style defaults (Form Builder's Global Styles tab, the protected Form Style Defaults setting, org row), one value per field: brand color in Color Primary (white text on it in Color On Primary), body and heading fonts as full CSS stacks in Font Family and Font Family Heading, heading weight, corner radius in Radius Medium and button corners in Button Radius, and the logo's asset name in Default Logo with its alt text. **Add-only**: a blank field takes the kit's value, the same value does nothing, a different value stays, and build-template puts the kit's value on that template's Style Overrides instead. Only the org's default brand writes here.
- **Logos and images** as public Asset Files (visible to guests) in the Asset Library, where the Flow Tool Kit image picker lists them; in a folder named for the brand when the library uses folders.
- **`brand-kit.json`**, a private file in the Asset Library, titled `brand-kit` for the org's default brand and `brand-kit-<slug>` for any other: everything the style fields cannot hold. A later save adds a version to the same file.

When the org refuses the API write to the setting, the values go into an import file for Global Styles, Import, with the org's current values first (Import replaces every saved org style); Default Logo is then set in the same tab with Select Image.

## brand-kit.json keys

| Key | What it holds |
|---|---|
| `brandName` | The organization's name as it appears on its site |
| `version`, `confirmedOn` | The kit's version number (1, then 2 for the first update) and the date the person confirmed it (YYYY-MM-DD) |
| `source` | The website the kit was read from |
| `slug`, `orgDefault` | The brand's folder name; `true` for the org's default brand, `false` for another brand in the same org |
| `programPage` | The program page whose words lead the form's copy, when one was given |
| `colors.primary` | The brand color (buttons, links, the banner fill), at least 4.5:1 against white |
| `colors.primaryOriginal` | The site's own brand color when it was darkened to reach 4.5:1 |
| `colors.heading` | The heading color, at least 4.5:1 against white |
| `colors.accent` | Optional second color; the original brand color when it was darkened and no accent was picked |
| `colors.background` | Optional light tint behind the form and around emails |
| `fonts.body`, `fonts.heading` | Font family names |
| `fonts.bodyStack`, `fonts.headingStack` | The full CSS stacks with a fallback, as written to the Form Style fields |
| `fonts.href` | The web font link a site's head markup loads |
| `style.cornerRadius`, `style.buttonRadius`, `style.headingWeight`, `style.buttonStyle` | Shape values (`8px`, `999px`, `700`, `filled` or `outline`) |
| `assets.logo` | The logo's Asset File name |
| `assets.logoAlt` | The logo's alt text (usually the brand name) |
| `assets.logoAlternate`, `assets.banner`, `assets.tile`, `assets.favicon` | Asset File names by role, when picked |
| `assets.bannerAlt` | The banner's alt text, when given |
| `assets.photos` | Asset File names of the other photos loaded |
| `voice.adjectives`, `voice.do`, `voice.avoid` | Short lists that describe the tone |
| `voice.sampleHeadings`, `voice.sampleButtons` | Wording taken from the site |

An Asset File name is letters, digits and single underscores (a packaged one carries its namespace, `FlowToolKit__Background_Forest_Sunbeams`), or an `https://` link. Unknown keys are ignored, so add rather than rename. Style values are recorded here as confirmed, but the Form Style defaults are what the forms use.

## Finding a saved kit

org-catalog counts a kit as saved when the org's Form Style defaults have Color Primary or Default Logo set, or a `brand-kit` file (JSON) is in the Asset Library. Style values alone are a partial kit with no tone. ftk-start then asks once: use it, update it, or ignore it.

## Several brands in one org

The org defaults hold one brand. Each other brand has its own `brand-kit-<slug>` file with `orgDefault` false, and is applied per template through that template's Style Overrides and Logo Override, never through a new Form Theme.

## What each reader takes

| Skill | Keys it reads |
|---|---|
| build-site-pages (`--brand-kit brand-kit.json`) | `colors.primary` (also the palette name `brand`), `colors.accent`, `colors.heading`, `colors.background` as palette names; `fonts.bodyStack` or else `fonts.body`, `fonts.headingStack` or else `fonts.heading` for the site's head tokens; `fonts.href` for the font link; `style.buttonRadius` for the site's button corners |
| build-email-templates | `colors.primary`, `colors.heading`, `colors.accent`, `colors.background`, `fonts.body`, `fonts.heading`, `assets.logo`, `assets.logoAlt`, `assets.banner` and `brandName`; the org's Form Style defaults fill what the file leaves out |
| build-template | The Form Style fields above, add-only, with the same token names |
| org-catalog | The file's title (`brand-kit` or `brand-kit-<slug>`, extension `json`) and the org's Color Primary and Default Logo, to report whether a kit is saved |
| form-design | `style`, `assets`, `images` and `brand_board`, in its own key names, from the brand-kit skill's `brandkit.py plan-style` output |
