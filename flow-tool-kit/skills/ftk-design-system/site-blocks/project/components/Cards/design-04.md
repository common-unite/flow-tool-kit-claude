# Cards 04: Category header cards

**Use it when:** Programs or funds, each with a category, title, short description and link.

**Why it works:** cardLayout banner puts a brand-colored header band with the category and title on top of each card, so the cards read like listings without needing photos.

**Content it needs:** 3 items; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardLayout` | Card Style: Card Layout | `banner` (Banner Header) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "columns": "3", "cardLayout": "banner", "brandColor": "#53B95B", "background": "#FFFFFF", "backgroundGradient": "off", "sectionLabel": "All programs", "heading": "Find the right program", "items": [{"eyebrow": "Food", "title": "Eastside Community Pantry", "description": "Groceries for your household, twice a month, free. No ID or appointment needed.", "link": "#", "linkLabel": "Visit the pantry →"}, {"eyebrow": "Housing", "title": "Housing Stability Fund", "description": "Up to three months of back rent, paid directly to your landlord.", "link": "#", "linkLabel": "Check your eligibility →"}, {"eyebrow": "Legal", "title": "First Thursday Legal Clinic", "description": "Thirty minutes with a volunteer attorney, first come first served.", "link": "#", "linkLabel": "See upcoming dates →"}], "hoverStyle": "lift"}
```
