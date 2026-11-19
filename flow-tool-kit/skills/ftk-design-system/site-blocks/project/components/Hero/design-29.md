# Hero 29: Closing band, spotlight gold

**Use it when:** A closing band that must win attention (a deadline, a talk-to-us action).

**Why it works:** A spotlight gradient with a gold brand color is the most eye-catching band; the rise entrance makes it arrive as the reader reaches the end.

**Content it needs:** 1 buttons; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `spotlight` (Spotlight) |
| `brandColor` | Background: Brand Color | `#F4BE45` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroLayout` | Arrangement: Button Placement | `band` |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "heroLayout": "band", "background": "#032D60", "backgroundGradient": "spotlight", "brandColor": "#F4BE45", "heading": "Talk to a program officer.", "subheading": "Thirty minutes, no pitch deck, and an honest read on whether we are the right fit.", "buttons": [{"label": "Book a call", "url": "#", "style": "accent"}], "headingAlign": "left", "entrance": "rise"}
```
