# Cards 09: Inline icons, four across

**Use it when:** A long list of capabilities (eight) on a dark section, with one action after it.

**Why it works:** cardLayout inline puts the icon beside short text, so eight items fit on one screen in four columns.

**Content it needs:** 8 items; 1 buttons; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundTexture` | Background: Texture | `grid` (Grid) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardBackgroundColor` | Background: Card Background | `#FFFFFF` |
| `cardBackgroundOpacity` | Background: Card Background Opacity | `7` |
| `cardLayout` | Card Style: Card Layout | `inline` (Inline) |
| `cardStyle` | Bullets: Card Style | `clean` (Clean) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `iconStyle` | Items: Icon Style | `tile` (Tile) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Use Cases", "heading": "A full bowl of form needs.", "subheading": "Every form. One delightful Tool Kit.", "headingAlign": "left", "bodyAlign": "left", "buttons": [{"label": "Bring us your next form challenge", "url": "#", "style": "accent"}], "columns": "4", "cardStyle": "clean", "cardLayout": "inline", "iconStyle": "tile", "cardBackgroundColor": "#FFFFFF", "cardBackgroundOpacity": 7, "items": [{"title": "Grant applications", "iconType": "icon", "icon": "utility:page"}, {"title": "Event registrations", "iconType": "icon", "icon": "utility:clock"}, {"title": "Program intake", "iconType": "icon", "icon": "utility:database"}, {"title": "Volunteer signups", "iconType": "icon", "icon": "utility:user"}, {"title": "Surveys and feedback", "iconType": "icon", "icon": "utility:search"}, {"title": "Referrals and requests", "iconType": "icon", "icon": "utility:apps"}, {"title": "Renewals and reporting", "iconType": "icon", "icon": "utility:settings"}, {"title": "Interest and eligibility", "iconType": "icon", "icon": "utility:desktop_and_phone"}], "hoverStyle": "lift", "backgroundTexture": "grid"}
```
