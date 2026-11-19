# Cards 13: Split, flat, two by two

**Use it when:** Four benefits beside a heading and intro.

**Why it works:** Split arrangement with a two by two grid of flat cards: balanced and easy to scan.

**Content it needs:** 4 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `arrangement` | Arrangement: Arrangement | `split` (Split) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `flat` (Flat Fill) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "arrangement": "split", "sectionLabel": "Plot Agreements", "heading": "Know your costs before the season starts.", "subheading": "Every plot fee is set in March. We choose the size together, you sign up, and the season begins. Nothing is added halfway through.<br><br><b>Fixed plot. Fixed fee. Fixed season. Agreed before anything is planted.</b><br><br>It works as a partnership. We count on members for watering shifts, workdays, weeding, and sharing the harvest to keep the garden growing.", "headingAlign": "left", "bodyAlign": "left", "columns": "2", "cardStyle": "flat", "items": [{"title": "Chosen together, up front", "description": "You choose the plot, its spot in the garden, and the season before anything is planted."}, {"title": "Ready on opening day", "description": "Signed up by March 7 means your bed is prepared and labeled on opening day."}, {"title": "No surprise fees", "description": "We will not come back mid-season asking for more money."}, {"title": "Repairs are ours", "description": "If a bed or a hose breaks, the garden fixes it at no cost to you."}], "hoverStyle": "lift"}
```
