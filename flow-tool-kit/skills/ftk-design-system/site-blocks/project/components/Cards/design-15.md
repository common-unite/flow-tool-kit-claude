# Cards 15: Split outlined with a footnote

**Use it when:** Four points beside a heading, with a note below.

**Why it works:** Split arrangement, outlined cards aligned to the top and a centered footnote: room for qualifications.

**Content it needs:** 4 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `background` | Background: Background | `#EEF1F4` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `outlined` (Simple Border) |
| `footnoteAlign` | Footnote: Footnote Alignment | `center` (Center) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `verticalAlign` | Arrangement: Vertical Alignment | `start` (Start) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "arrangement": "split", "sectionLabel": "Your Plot, Recorded", "heading": "Every plot comes with a garden journal.", "subheading": "Your plot's planting dates, soil tests, harvest notes, and next season's plan live in a shared journal that belongs to you. A copy is kept at the shed, and so is the record of what worked and why.", "headingAlign": "left", "bodyAlign": "left", "footnote": "If you passed your plot on tomorrow, the next gardener would know exactly what grew there and why.", "footnoteAlign": "center", "columns": "2", "cardStyle": "outlined", "items": [{"title": "Seed library", "description": "Seeds saved every fall, so a bad season is always recoverable.", "iconType": "icon", "icon": "utility:database"}, {"title": "Planting history", "description": "Every crop, its spot in the bed, and how it did, kept in order.", "iconType": "icon", "icon": "utility:search"}, {"title": "Living journal", "description": "Written as you go each week, not as an afterthought at the end of the season.", "iconType": "icon", "icon": "utility:page"}, {"title": "Visible calendar", "description": "What is planted, what is next, and what is due for harvest, open to every member.", "iconType": "icon", "icon": "utility:trending"}], "hoverStyle": "lift", "background": "#EEF1F4", "verticalAlign": "start"}
```
