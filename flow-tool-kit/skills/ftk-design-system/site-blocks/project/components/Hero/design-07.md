# Hero 07: Static photo facts

**Use it when:** An apply-for-help page where motion would feel out of place (legal, medical, crisis services).

**Why it works:** Same facts layout as the parallax version with the motion off: calm, steady, and still warm from the tinted photo.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; 2 buttons; 2 badges; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.25` (Gentle) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "badges": [{"title": "Next clinic: August 6"}, {"title": "First come, first served"}], "badgePosition": "top", "sectionLabel": "First Thursday Legal Clinic", "heading": "Thirty minutes with a volunteer attorney, free", "subheading": "Housing, family, immigration, and benefits questions. Spanish and Vietnamese interpretation on site.", "buttons": [{"label": "See upcoming dates", "url": "#", "style": "brand"}, {"label": "What to bring", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "When", "value": "1st Thursday, 5 – 8 pm"}, {"title": "Doors open", "value": "4:30 pm sign-in"}, {"title": "Capacity", "value": "~30 consultations"}, {"title": "Languages", "value": "EN · ES · VI on site"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Volunteer_Build_Day", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25"}
```
