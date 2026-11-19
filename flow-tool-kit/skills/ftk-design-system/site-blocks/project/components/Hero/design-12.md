# Hero 12: Emergency fund facts

**Use it when:** An urgent or rapid-response fund where speed and limits must be clear immediately.

**Why it works:** Five facts on a tinted navy ground answer amount, speed and who qualifies; the headline names the urgency.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 5 items; 2 buttons; 2 badges; a heading of about 10 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |
| `splitRatio` | Arrangement: Column Ratio | `left` (Wider Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "headingAlign": "left", "bodyAlign": "left", "splitRatio": "left", "badges": [{"title": "Rolling · Always open", "style": "brand"}, {"title": "Decisions in 10 business days", "style": "outline"}], "badgePosition": "top", "sectionLabel": "Rapid Response Fund", "heading": "When the emergency will not wait for a grant cycle", "subheading": "One-time grants up to $10,000 for nonprofits facing an unexpected loss, urgent repair, or sudden spike in demand. A five-question application and a decision inside two weeks.", "buttons": [{"label": "Apply now", "url": "#", "style": "brand"}, {"label": "Call before you apply", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Deadline", "value": "Rolling, year-round"}, {"title": "Award cap", "value": "$10,000"}, {"title": "Decision time", "value": "10 business days"}, {"title": "Application", "value": "5 questions, ~30 min"}, {"title": "Limit", "value": "One award per org per year"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Solar_Panel_Install", "backgroundOverlay": "tint"}
```
