# Page

An Aura site page: the theme layout around a content region of Sections, the way Experience Builder renders a Flexible Layout page.

**Maps to:** a Flexible Layout page (`siteforce:dynamicLayout`) in the theme's content area, inside one of two theme layouts:
- `layout: "buildYourOwn"` (default): the Testing Aura site's Build Your Own layout, `siteforceStarterBody` with the 1440px `cCenterPanel`. Its header and footer regions draw nothing, so a page carries its own in its first and last Sections.
- `layout: "customerService"`: the Testing CS site's Customer Service layout, `siteforce:serviceBody`: logo, search, login and navigation bar over the page, the footer region under it. See the ThemeLayout card for its props.

Each child of the content region sits in its own `ui-widget`.

## Props
- `theme`: the Theme panel values, the site's layer-1 branding. `brand` (Brand color), `accent`, `text`, `font` and `headingFont`. Leave it out to use the tokens (FlowToolKit green, DM Sans). Every block and SLDS component on the page reads these as the hooks an Aura site publishes (`--dxp-g-brand`, `--lwc-brandPrimary`, `--lwc-fontFamily`).
- `maxWidth`: the content area's width cap, 1440px as the theme sets it.
- `children`: `Section` elements, top to bottom.

## Designing a page
- Build the page from Sections. A Section holds one to four Columns whose widths add up to 12.
- Put content side by side whenever it reads side by side: text beside a form, facts beside an application, three cards in a 4/4/4 Section. Keep single-column Sections for content that really is full width: a Hero, a Carousel, a Table, long copy.
- Forms and FlowToolKit components go in a column as a `FormSlot`. The Forms design system owns how they look.
- The header, navigation menu and footer arrive in the next version.

## Preview at desktop width
Previews call `SB.previewAt(1280)`, which lays the page out 1280px wide and zooms it into the card. It hands the blocks their measurements in layout pixels and settles every width media query as it would be at 1280px, so blocks, Sections and the theme header all show their desktop layout. Without it a narrow card shows the tablet or phone layout, as the site does at that width.

## On LWR

`site: "lwr"` draws the Build Your Own (LWR) theme layout, `community_byo:scopedHeaderAndFooter`, as Testing LWR renders it: a header region, the content, a footer region. The conversion scripts place a design on an LWR site, so a design leaves `site` out unless it must show LWR-only markup.

| Prop | On LWR |
| --- | --- |
| `site` | `"lwr"`. Leave it out (Aura); the conversion scripts handle LWR. |
| `header`, `footer` | Each region holds Sections, as Builder's theme layout does. Pass Sections, or other content and it goes in a one-column Section. A string footer becomes Rich Content. Both empty draws the empty header and footer sections a new Build Your Own (LWR) site has. |
| `theme` | Sets the LWR branding set's `--dxp-g-brand`, `--dxp-g-brand-1` and font hooks. |
| `layout`, `logo`, `siteName`, `navItems`, `searchPlaceholder`, `loginLabel` | Aura only. LWR has no Customer Service theme; build an LWR header from Sections. |

The page fills the window height, so a short page ends with its footer at the bottom, as the site does.
