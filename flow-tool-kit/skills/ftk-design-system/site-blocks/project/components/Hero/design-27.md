# Hero 27: Closing band, diagonal

**Use it when:** The last block on a page: one sentence and the two actions you most want taken.

**Why it works:** heroLayout band is a short, full-width strip (it replaces the retired Call to Action); the diagonal gradient makes it read as an ending.

**Content it needs:** 2 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroLayout` | Arrangement: Button Placement | `band` |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "heroLayout": "band", "background": "#032D60", "backgroundGradient": "diagonal", "brandColor": "#53B95B", "shineSweep": true, "heading": "Ready when you are.", "subheading": "Start an application today. It saves as you go, so you can finish any time before September 30.", "buttons": [{"label": "Start an application", "url": "#", "style": "brand"}, {"label": "Check eligibility", "url": "#", "style": "outline"}], "headingAlign": "left"}
```
