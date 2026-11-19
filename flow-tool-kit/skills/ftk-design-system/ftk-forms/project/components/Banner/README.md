# Banner

The title banner at the top of a form: a photo, the organization's logo, a title, a subtitle and tag pills. It is the **Banner section type**: added from **Add Section** in the Form Builder, beside Field Set, Image and Record Card, and most often placed in the **Form Template header** so the form opens with the client's brand.

**Maps to:** `Form_Component_Section__c.sectionType__c = bannerSection`, settings in `Banner__c` (JSON), drawn by `c-form-banner`.

## When to use which layout

Pick the layout from the form's shape:

| Form shape | Layout | Height | Why |
| --- | --- | --- | --- |
| Single page (no vertical page indicator) | **Compact** | Small | It blends into the card as the form's title |
| Multi-page without the vertical indicator (two pages with none, or three or more not-long pages with the `base` indicator above the page, C3) | **Overlay** | Small | Still `singleCardHeader`: square bottom corners, flush on the card. The page count never rounds the corners; only the vertical indicator does |
| Multi-page with the vertical page indicator, or stages mode | **Overlay** | Small | Short, so the first step sits right under it. Scrim in the main brand color, one or two tags at most |
| A very simple title | Split | Small | Offered, never the default |
| A form that features its photo | Overlay or Split | Medium or Large | Medium is 240px, Large 340px. Overlay and Split are the same height at every size |

Every converted form gets one banner, in the template header. Never repeat the form's title in a page header under it, and never add a "Page N of M" page header. The form-type rules table in the form-design skill's house preferences picks the row; see the design system README, Form-type rules.

## Where it goes

| `placement` | Where | What changes |
| --- | --- | --- |
| `singleCardHeader` | Form Template header, single-card template (no vertical page indicator, whatever the page count) | Square bottom corners, so it joins the form card; the page starts 12px below; text lines up with the fields (40px inset) |
| `header` | Form Template header, Stages Mode (the vertical indicator beside the card) | Rounded on all corners, inside the header card |
| `body` (default) | A section inside a form | Reaches 0.75rem past the fields on both sides so its text lines up with them |

The banner is not shown on the confirmation screen.

## How to set it up

| Prop | Package setting |
| --- | --- |
| `layout` | Layout: Overlay (default), Split, Compact |
| `height` | Height: Small (default, follows its text), Medium, Large |
| `tags` | Tags: semicolons ("2027 season; About 10 minutes"), or a multi-select picklist merge field |
| `title`, `subtitle` | Rich text with merge fields. Keep the title to one line at normal widths |
| `image`, `imageAlt` | Background Image (Asset Selector), with a record field override (a link, formula or rich text field). Optional |
| `backgroundColor` | Background Color: the Split panel, and the banner with no image. Empty is the brand |
| `scrimColor`, `scrimOpacity` | Scrim Color with opacity: the tint behind the text on the photo |
| `tagColor` | Tag Color: pill fill, text turns white on a dark color |
| `logo`, `logoAlt`, `logoShape` | Logo (Asset Selector, no field override), Square, Circle or None (no white card). Default: Overlay square, Split and Compact circle |
| `paddingTop`, `paddingBottom`, `paddingHorizontal` | The section's Style tab padding. It adds space **inside** the banner; Margin moves the whole banner |

## Notes
- Text sizes: title 1.5 to 2.25rem at line height 1.08, subtitle 0.875 to 1.0625rem at 1.25, no gap between them, 8px under the tags.
- Below 520px wide the logo moves to the top corner and Overlay's scrim rises from the bottom.
- Split with a logo is never shorter than the logo plus the banner's top and bottom padding, so the circle on the seam keeps clear space above and below it instead of touching the edges. Package gap: `formBanner.css` lets a short Split banner squeeze the logo against its edges.
- Guests see a rich text field's image only when the record is shared with the site guest user; otherwise the picked image shows.
