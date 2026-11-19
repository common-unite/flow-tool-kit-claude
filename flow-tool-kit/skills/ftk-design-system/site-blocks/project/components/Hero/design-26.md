# Hero 26: Radial gradient with bullets

**Use it when:** A capabilities section that lists six things on one screen.

**Why it works:** A radial navy gradient focuses the center, the elevated image anchors one side, and six bullets fit without feeling like a list page.

**Content it needs:** one photo or screenshot; 6 bullets; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `radial` (Radial) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageStyle` | Media: Image Style | `elevated` (Elevated) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "brandColor": "#53B95B", "sectionLabel": "Use Cases", "headingAlign": "left", "bodyAlign": "left", "heading": "A full bowl of form needs.", "bullets": [{"description": "Grant applications"}, {"description": "Event registrations"}, {"description": "Program intake"}, {"description": "Volunteer signups"}, {"description": "Surveys and feedback"}, {"description": "Referrals and requests"}], "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Mountain_Meadow_Sunset", "imageStyle": "elevated", "backgroundGradient": "radial", "background": "#032D60"}
```
