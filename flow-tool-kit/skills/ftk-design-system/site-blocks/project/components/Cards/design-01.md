# Cards 01: Three roles, outlined

**Use it when:** Choosing between options (roles, programs, ways to help).

**Why it works:** Three outlined cards with plain icons and a left-aligned heading: the clearest choice layout.

**Content it needs:** 3 items; a heading of about 10 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `outlined` (Simple Border) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |
| `iconStyle` | Items: Icon Style | `plain` (Plain) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "sectionLabel": "What You Will Be Doing", "heading": "Pick the role that fits how you like to work.", "subheading": "You will choose a role when you check in. Tell us your preference at signup and we will do our best to match it.", "headingAlign": "left", "bodyAlign": "left", "columns": "3", "cardStyle": "outlined", "iconStyle": "plain", "items": [{"title": "Box packing", "description": "Assemble grocery boxes on the line from a set list. Steady standing work, mostly indoors.", "meta": "12 volunteers needed", "iconType": "icon", "icon": "utility:page"}, {"title": "Load out and carry", "description": "Move boxes to the pickup lane and load them into cars. Outdoors, involves lifting up to 25 pounds.", "meta": "8 volunteers needed", "iconType": "icon", "icon": "utility:trending"}, {"title": "Greeting and check-in", "description": "Welcome neighbors, confirm names on the list, and answer questions. Seated work available.", "meta": "4 volunteers needed", "iconType": "icon", "icon": "utility:user"}], "hoverStyle": "lift"}
```
