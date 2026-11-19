# page.json and site.json

`page.json` is the design as data, one file per page at `_site/<slug>/pages/<urlName>.json`. It is the format build-site-pages reads to build the page, plus optional `_design` keys for the review canvas, which the build ignores. Add nothing else: a key the build does not know is a key the build drops.

## A page

| Key | What |
|---|---|
| `title`, `currentNav` | The page's title and its place in the navigation |
| `layout`, `logo`, `siteName`, `navItems`, `searchPlaceholder`, `loginLabel`, `footer`, `theme`, `maxWidth` | The `SB.Page` settings (the design system's Page card). Shared ones go in `site.json` `page` once. `layout` and the navigation props are Aura only; an LWR header is built from Sections |
| `header`, `footerContent` | Sections in the theme layout's header and footer regions. Shared ones go in `site.json` `page` |
| `sections[]` | `{attributes, columns[{width, items[]}], _design}`, top to bottom; one to four columns adding up to 12 |
| `_design` | `notes` (lines for the canvas's sticky note), `contentToCollect` (photos, copy, numbers still owed), `states` (extra artboards: `{id, title, emptyRepeaters}`, `{id, title, sections}`, or `{id, title, section, activeTab}` to draw one section with another tab open, one per tab after the first), `sampleRecord` (below) |

Each item has a `kind`:

| `kind` | Fields |
|---|---|
| `block` | `props`: the block's JSON (`sectionType` and the block's own keys; collections may be arrays or JSON strings; colours may be `"$name"` from the palette) |
| `divider` | `attributes` (a Flow Tool Kit header shown as a divider) |
| `richText` | `richTextValue`: formatted page copy in the Rich Content Editor |
| `htmlEditor` | `richTextValue`: markup in the standard HTML Editor, and `_design.reason` (why no block does it). Rules: [html-editor.md](html-editor.md) |
| `search`, `languageSelector` | `placeholder` |
| `tabs` | `tabs[{tabName, tabKey, items}]`, `activeTab` |
| `formSlot` | `form`, `formKind`, `formTemplate` once the Form Template exists |
| `repeater` | `object`, `card` (the fields each card shows, as `{{Field}}` merge fields in the card's slots: `title`, `eyebrow`, `subtitle`, `badge`, `value`, `imageSource` with `imageUrl`, `items`, `buttons`), `cardType`, `columns`, `pageSize`, `filter` (`{"conditionType": "AND", "conditions": [{"position": 1, "fieldApiName": "Status__c", "operator": "eq", "value": "Open"}]}`; `{!recordId}` as the value for a record page's children), `sortField`, `sortDirection`, `emptyMessage`, and `_design.sampleRecords` (the cards the canvas draws; the build queries the object instead). The generator refuses a repeater without `object` and `card`: build-site-pages cannot build a listing drawn only from samples |

A section's `_design`: `id` (stable; names the section on its tag and in comments; default `sNN-<job>`), `job` (what the section is for, in a few words), `designCard` (the design it was chosen from: "Hero 14", "Cards 08", or "HTML Editor"), `source` (where its copy came from; a web address shows as a link on the tag), `photoStandIn` (the package image drawn in place of a record-field photo in this section; default `FlowToolKit__Background_Volunteer_Build_Day`), `photoStandIns` (several, which a record carousel's slides take in turn).

A record page's `_design.sampleRecord`: field values the canvas fills into its blocks' `{{Field}}` text, such as `{"Name": "[SAMPLE] Community Resilience Fund"}`. The canvas has no record and the package blanks every token without one, so without it a heading reads "The story of" with the name missing. Mark text values `[SAMPLE]` so nobody reads them as live data, and leave photo fields out (they get stand-ins). Repeater cards use their own `sampleRecords`, never this. The build ignores it: the live page fills from the record.

Copy the organization has not yet confirmed is written in place as `[CONFIRM: ...]`; the canvas counts and lists every one.

## site.json

`start_site.py` writes the first version from the project config and the brand kit.

```json
{
  "slug": "riverside-fund", "title": "Riverside Community Fund", "canvasTitle": "Riverside Community Fund site review",
  "siteType": "lwr", "edition": "paid", "audiences": ["guest"],
  "pages": [{"urlName": "funding", "title": "Funding", "route": "/funding", "recordObject": null, "audience": ["guest"],
             "currentUrl": "https://www.example.org/grants"}],
  "palette": {"brand": "#2e844a", "accent": "#F4BE45", "deep": "#032D60", "tint": "#EEF1F4"},
  "brand": {"logo": "<asset name>", "theme": {"brand": "#2e844a", "accent": "#F4BE45", "font": "<stack>", "headingFont": "<stack>"},
            "colors": [{"name": "Brand", "hex": "#2e844a", "role": "buttons, links"}],
            "fonts": {"heading": "", "body": "", "heading_css": "", "body_css": "", "href": "<Google Fonts css2 link>"},
            "buttonRadius": "4px", "tone": "<tone paragraph>", "copy": ["<general copy>"], "images": [{"asset": "", "alt": "", "caption": ""}]},
  "page": {"siteName": "Riverside Community Fund", "logo": "<asset name>", "navItems": ["Home", "Funding"], "header": [], "footerContent": []},
  "canvasUrl": "<the canvas's link, once created>",
  "assets": {"<AssetName>": {"file": "<path from the site folder>", "blob": "/_blob/<id>"}}
}
```

| Key | What |
|---|---|
| `pages` | The artboard order, and what the build needs per page: `route`, `recordObject` (a record page's object), `audience` (guest, portal, internal: who sees it, which the HTML Editor check reads) and `currentUrl` (the page it replaces, linked on the artboard) |
| `siteType`, `edition`, `audiences` | The site's type, the org's Flow Tool Kit edition (paid or free) and the default audience, from `flow-tool-kit.json` |
| `palette` | Named colours; page.json refers to them as `"$name"`, and build-site-pages swaps them for the hex |
| `brand` | What the Brand artboard shows: only what was chosen, never every candidate a site scan found |
| `page` | Settings, header and footer every page shares |
| `canvasUrl` | The review canvas's link, written once the canvas exists |
| `assets` | Every image the canvas draws that is not in the design system or must be uploaded: the organization's own images with their local `file`, and, once uploaded, each image's `blob`. Packaged FlowToolKit images are found in the kit by name and keep only their `blob` |

Image names: a packaged photo is named as the org knows it, `FlowToolKit__Background_Farmland_Aerial`; the organization's own image by its Asset File name, `Riverside_Logo`; a design system resource as `resource:<path>`.
