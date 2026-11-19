# Hero 03: Campaign with counting stats

**Use it when:** A campaign or season launch where the numbers are the story (shifts filled, meals served, volunteers).

**Why it works:** Inline stats count up as the hero appears, giving proof in the first screen; the wipe entrance and mascot keep it from reading like a report.

**Content it needs:** a mascot or cut-out illustration; 3 stats; 2 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundAccentColor` | Background: Gradient End | `#155091` |
| `backgroundGradient` | Background: Gradient | `horizontal` (Horizontal) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `countUp` | Items: countUp | `true` |
| `entrance` | Motion: Entrance | `wipe` (Wipe Reveal) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Mascot presenting the Summer of Service campaign roadmap` |
| `imageBleed` | Media: Image Bleed | `bottom` (Bleed Bottom) |
| `imageStyle` | Media: Image Style | `mascot` (Mascot) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "backgroundAccentColor": "#155091", "backgroundGradient": "horizontal", "brandColor": "#53B95B", "countUp": true, "sectionLabel": "This Shift Is Part Of", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "heading": "Summer of Service 2026", "subheading": "Eleven weekends, nine partner organizations, one goal of 5,000 neighbors served. Sign up for one shift or follow the whole series. Your hours count toward the campaign total either way.", "stats": [{"value": "3,180", "title": "neighbors served so far"}, {"value": "742", "title": "volunteers this summer"}, {"value": "6", "title": "weekends remaining"}], "buttons": [{"label": "See all Summer of Service shifts", "url": "#", "style": "accent"}, {"label": "Follow the campaign", "url": "#", "style": "outline"}], "reversed": true, "imageSource": "asset", "imageAlt": "Mascot presenting the Summer of Service campaign roadmap", "imageStyle": "mascot", "imageBleed": "bottom", "entrance": "wipe", "imageAsset": "FlowToolKit__Just_Right_Bear_1"}
```
