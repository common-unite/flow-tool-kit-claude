# Cards 07: Split, two flat cards

**Use it when:** A section where the heading and intro need room beside the cards.

**Why it works:** arrangement split puts the heading on one side and a two-column grid of flat cards on the other: editorial, not a grid page.

**Content it needs:** 4 items; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `background` | Background: Background | `#EEF1F4` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardBackgroundColor` | Background: Card Background | `#FFFFFF` |
| `cardStyle` | Bullets: Card Style | `flat` (Flat Fill) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "background": "#EEF1F4", "brandColor": "#2E844A", "arrangement": "split", "sectionLabel": "The Goldilocks Framework", "heading": "Just right is not the finish line.", "subheading": "Built from the same circuit-node geometry as the Flow Tool Kit identity: navy structure, green action, and nothing you can't maintain yourselves.", "headingAlign": "left", "bodyAlign": "left", "columns": "2", "cardStyle": "flat", "cardBackgroundColor": "#FFFFFF", "items": [{"title": "Salesforce-Native", "description": "Built on Flow. Built for scale.", "iconType": "icon", "icon": "utility:desktop_and_phone"}, {"title": "No-Code Ready", "description": "Empower admins. Delight users.", "iconType": "icon", "icon": "utility:settings"}, {"title": "Built for Nonprofits", "description": "By nonprofit professionals.", "iconType": "icon", "icon": "utility:user"}, {"title": "Big Impact", "description": "Automate. Connect. Empower.", "iconType": "icon", "icon": "utility:trending"}], "hoverStyle": "lift"}
```
