# ThemeLayout

The Customer Service theme layout: the header (logo, search, login, navigation bar) over the page and the footer region under it. Draw it with `Page` and `layout: "customerService"`.

**Maps to:** the Customer Service theme's Default layout, `siteforce:serviceBody`, with Search (`forceCommunity:searchBox`), the profile menu (`selfService:userProfileMenu`) and Navigation Menu (`forceCommunity:multiLevelNavigation`) in its regions. Captured from the Testing CS site; checked against it side by side at desktop and phone width.

## Page props for this layout
- `logo`: an Asset File name (`FlowToolKit__FlowToolKit_Gray`) or an image address. The theme's Company Logo.
- `siteName`: the logo's title.
- `navItems`: the navigation menu's items, as labels or `{ label, href }`. `currentNav` marks the current page.
- `searchPlaceholder`; `search: false` leaves the header search out.
- `loginLabel`: the guest's login link. Default Login.
- `footer`: the footer region's content, as rich text or any element.
- `theme`: the Theme panel's brand, accent and fonts, as for any Page.

## Notes
- On a phone the navigation folds into the menu button and the search into an icon.
- The other layout, `buildYourOwn` (the default), is Testing Aura's: no visible header or footer, so a page's own first and last Sections carry them.

## On LWR

The Customer Service theme is an Aura theme. On LWR this card draws the Build Your Own (LWR) layout instead: header and footer regions that hold Sections. Design an LWR header from Sections and blocks (see Page).
