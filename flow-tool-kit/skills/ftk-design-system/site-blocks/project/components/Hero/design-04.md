# Hero 04: Navy facts panel

**Use it when:** A service people apply for, where eligibility, schedule and cost decide whether they keep reading.

**Why it works:** heroMedia facts swaps the image for a four-line facts panel, so the hero answers the applicant's first questions without a click.

**Content it needs:** 4 items; 2 buttons; 2 badges; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "badges": [{"title": "Open today until 6 pm"}, {"title": "No appointment needed"}], "badgePosition": "top", "sectionLabel": "Eastside Community Pantry", "heading": "Groceries for your household, twice a month, free", "subheading": "Walk in during open hours and shop the shelves like a store. You do not need ID, proof of income, or an address to receive food.", "buttons": [{"label": "Get directions", "url": "#", "style": "brand"}, {"label": "See this week's hours", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Tue + Thu", "value": "2 pm – 6 pm"}, {"title": "Saturday", "value": "9 am – 12 pm"}, {"title": "Visits", "value": "2 per month per household"}, {"title": "Home delivery", "value": "Available 65+ or disabled"}], "entrance": "rise"}
```
