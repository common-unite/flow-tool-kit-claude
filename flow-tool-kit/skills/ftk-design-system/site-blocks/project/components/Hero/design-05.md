# Hero 05: Photo facts with parallax

**Use it when:** The same apply-for-help page as the navy facts panel, when you have a strong photo of the place or people.

**Why it works:** A tinted parallax photo sits behind the facts panel: the photo gives warmth, the tint keeps the text readable, the facts keep it practical.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; 2 buttons; 2 badges; a heading of about 10 words. If the client cannot supply it, pick another design.

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
| `entrance` | Motion: Entrance | `cascade` (Cascade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "badges": [{"title": "Accepting applications"}, {"title": "Court date? Call today", "style": "neutral"}], "badgePosition": "top", "sectionLabel": "Housing Stability Fund", "heading": "Up to three months of rent, paid to your landlord", "subheading": "One-time assistance for households behind on rent or facing eviction. Payments go directly to your landlord within ten days of a decision.", "buttons": [{"label": "Start an application", "url": "#", "style": "brand"}, {"label": "Apply with a case manager", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Covers", "value": "Up to 3 months back rent"}, {"title": "Income limit", "value": "80% of area median"}, {"title": "You will need", "value": "Lease, ID, notice if any"}, {"title": "Decision", "value": "10 days, paid to landlord"}], "entrance": "cascade", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Farmland_Aerial", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25"}
```
