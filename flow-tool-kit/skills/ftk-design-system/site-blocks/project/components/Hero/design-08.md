# Hero 08: Light tinted photo facts

**Use it when:** A class or recurring program with simple logistics (days, times, cost, location).

**Why it works:** A tinted photo with a facts panel keeps the logistics prominent while the photo shows the setting; no entrance motion keeps it quiet.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; 2 buttons; 2 badges; a heading of about 9 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "badges": [{"title": "Join any week"}, {"title": "Free childcare during class"}], "badgePosition": "top", "sectionLabel": "<p>English for Everyday Life</p>", "heading": "Free English classes, mornings and evenings, join any week", "subheading": "Four levels from beginner to advanced. A 15-minute placement conversation puts you in the right level.", "buttons": [{"label": "Schedule your placement", "url": "#", "style": "brand"}, {"label": "See the class schedule", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Levels", "value": "4, placement decides"}, {"title": "Morning", "value": "Mon + Wed, 9:30 – 11:30"}, {"title": "Evening", "value": "Tue + Thu, 6 – 8 pm"}, {"title": "Childcare", "value": "Free, ages 2+, on site"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Forest_Sunbeams", "backgroundOverlay": "tint"}
```
