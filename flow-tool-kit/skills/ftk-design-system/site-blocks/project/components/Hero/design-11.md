# Hero 11: Fund name on a diagonal gradient

**Use it when:** A fund or program detail page that needs a clean title band before the details below it.

**Why it works:** A diagonal navy gradient with badges and two buttons: no image to source, still more designed than a flat color.

**Content it needs:** 2 buttons; 2 badges; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#F4BE45` |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `diagonal` (Diagonal) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#032D60", "backgroundGradient": "diagonal", "brandColor": "#53B95B", "accentColor": "#F4BE45", "badges": [{"title": "Open", "style": "brand"}, {"title": "Closes Sept 30", "style": "accent"}], "badgePosition": "top", "heading": "Community Resilience Fund", "subheading": "General operating · $25,000 – $75,000 · 2-year term", "buttons": [{"label": "Start application", "url": "#", "style": "brand"}, {"label": "Save for later", "url": "#", "style": "outline"}]}
```
