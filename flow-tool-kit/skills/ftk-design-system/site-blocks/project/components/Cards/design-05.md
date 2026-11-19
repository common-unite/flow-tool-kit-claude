# Cards 05: Ghost results with a button

**Use it when:** Results or outcomes on a dark section with one action after them.

**Why it works:** Ghost cards are see-through panels on a vertical gradient: the content feels part of the section, not boxes on it.

**Content it needs:** 3 items; 1 buttons; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `vertical` (Vertical) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardStyle` | Bullets: Card Style | `ghost` (Ghost Outline) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "background": "#032D60", "brandColor": "#53B95B", "columns": "3", "cardStyle": "ghost", "sectionLabel": "Past Awards", "heading": "Where the money went last cycle.", "subheading": "21 grants and $1.1 million awarded in 2025. The full award list is public.", "headingAlign": "left", "bodyAlign": "left", "buttons": [{"label": "See all past awards", "url": "#", "style": "outline"}], "items": [{"title": "Valley Harvest Pantry", "eyebrow": "$75,000", "description": "Doubled cold storage and added a second weekly distribution, reaching 300 more households."}, {"title": "Comida y Comunidad", "eyebrow": "$50,000", "description": "Hired its first full-time coordinator, moving the promotora food program off volunteer-only staffing."}, {"title": "Gleaners of Linn County", "eyebrow": "$25,000", "description": "Replaced the refrigerated van that moves recovered produce from twelve farms out to four rural sites."}], "hoverStyle": "lift", "backgroundGradient": "vertical"}
```
