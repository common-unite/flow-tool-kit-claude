# Cards 06: Centered icon cards

**Use it when:** Comparing three options side by side, each with a symbol and a short verdict.

**Why it works:** Centered icons, labels and titles in outlined cards read like product tiles; the icon carries the verdict at a glance.

**Content it needs:** 3 items; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `bodyAlign` | Body: Alignment | `center` (Center) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardMedia` | Card Style: Card Media | `cover` (Cover) |
| `cardStyle` | Bullets: Card Style | `outlined` (Simple Border) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#53B95B", "sectionLabel": "The Form Spectrum", "heading": "Every nonprofit form tool, tasted", "columns": "3", "cardStyle": "outlined", "cardMedia": "cover", "bodyAlign": "center", "items": [{"eyebrow": "Too Hot", "title": "OmniStudio · Custom Code", "description": "Overbuilt. Expensive. Hard to own.", "iconType": "icon", "icon": "utility:ban", "iconColor": "#CA0000"}, {"eyebrow": "Too Cold", "title": "Standard Flow · External Form Builders", "description": "Limited. Fragile. Disconnected.", "iconType": "icon", "icon": "utility:frozen"}, {"eyebrow": "Downright Delightful", "title": "Flow Tool Kit", "description": "Salesforce-native. Fast. Flexible. Delightful.", "iconType": "icon", "icon": "utility:like"}], "hoverStyle": "lift", "background": "#EEF1F4"}
```
