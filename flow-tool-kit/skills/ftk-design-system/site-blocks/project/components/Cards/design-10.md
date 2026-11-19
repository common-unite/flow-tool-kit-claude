# Cards 10: Products with icons on navy

**Use it when:** Three products or tools, each with a short description and a link, on a dark section.

**Why it works:** Clean cards on navy with a large icon and a link each: every card has a strong marker without a photo.

**Content it needs:** 3 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardStyle` | Bullets: Card Style | `clean` (Clean) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `iconStyle` | Items: Icon Style | `tile` (Tile) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Our Products", "heading": "Programs our neighbors asked for.", "subheading": "Free to join, run by volunteers, and shaped by the people who use them.", "headingAlign": "left", "bodyAlign": "left", "columns": "3", "cardStyle": "clean", "iconStyle": "tile", "items": [{"eyebrow": "Flagship", "title": "Community Plots", "description": "Raised beds and full plots for any household in the neighborhood, with water, tools and compost on site.<br><br>Seedling: $20 per month<br>Grower: $40 per month<br>Harvest: $80 per month", "meta": "Take the two minute tour"}, {"title": "Youth Garden Club", "description": "After-school sessions where kids plant, harvest and cook what they grow. Snacks, gloves and aprons provided.", "meta": "See how it works", "iconType": "icon", "icon": "utility:apps"}, {"title": "Volunteer Workdays", "description": "Monthly workdays to build beds, turn compost and share the harvest with the neighborhood food pantry.", "meta": "See how it works", "iconType": "icon", "icon": "utility:trending"}], "hoverStyle": "lift"}
```
