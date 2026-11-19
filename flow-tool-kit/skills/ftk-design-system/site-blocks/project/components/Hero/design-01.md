# Hero 01: Mascot over a navy gradient

**Use it when:** A volunteer or event landing page that should feel warm and human, with a clear sign-up action.

**Why it works:** The mascot bleeds off the bottom edge and floats beside the copy, so the page opens on a character instead of a stock photo; badges on top answer when and where before anyone reads the body.

**Content it needs:** a mascot or cut-out illustration; 2 buttons; 3 badges; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundAccentColor` | Background: Gradient End | `#155091` |
| `backgroundGradient` | Background: Gradient | `horizontal` (Horizontal) |
| `badgeAlign` | Badges: Badge Alignment | `left` (Left) |
| `badgePosition` | Badges: Badge Position | `top` |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `footnoteAlign` | Footnote: Footnote Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Volunteer mascot with a completed signup sheet` |
| `imageBleed` | Media: Image Bleed | `bottom` (Bleed Bottom) |
| `imageStyle` | Media: Image Style | `mascot` (Mascot) |
| `splitRatio` | Arrangement: Column Ratio | `left` (Wider Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "backgroundAccentColor": "#155091", "backgroundGradient": "horizontal", "brandColor": "#53B95B", "imageFloat": true, "badgePosition": "top", "badgeAlign": "left", "badges": [{"title": "Part of Summer of Service 2026", "style": "accent"}, {"title": "Saturday shift", "style": "neutral"}, {"title": "9 spots left", "style": "outline", "pulse": true}], "heading": "Saturday Food Distribution Crew", "subheading": "Help us pack and hand out fresh grocery boxes to about 400 neighbors. You will work alongside a small team, no experience needed, and every box you fill goes home with a family that afternoon.", "buttons": [{"label": "Sign up for this shift", "url": "#", "style": "accent"}, {"label": "Sign up a group", "url": "#", "style": "outline"}], "footnote": "Free · Ages 14 and up · Service hours letter provided on request", "footnoteAlign": "left", "imageSource": "asset", "imageAlt": "Volunteer mascot with a completed signup sheet", "imageStyle": "mascot", "imageBleed": "bottom", "splitRatio": "left", "entrance": "rise", "imageAsset": "FlowToolKit__Delightful_Bear_3"}
```
