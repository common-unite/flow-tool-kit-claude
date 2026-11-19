# Hero 17: Framed photo on a brand gradient

**Use it when:** A team or organization section with a short headline, one action and a real photo.

**Why it works:** The photo sits in a clean frame on the brand gradient instead of filling the background, so any photo works without fighting the text.

**Content it needs:** one photo or screenshot; 1 buttons; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `entrance` | Motion: Entrance | `cascade` (Cascade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Volunteers planting saplings in an autumn woodland` |
| `imageStyle` | Media: Image Style | `clean` (Clean) |
| `splitRatio` | Arrangement: Column Ratio | `even` (Even) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Who We Serve", "heading": "Small teams doing outsized work.", "subheading": "Most of our clients run on two to ten staff. The org chart is short, the mission is not, and the technology has to hold.", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "buttons": [{"label": "Meet our clients", "url": "#", "style": "accent"}], "splitRatio": "even", "imageStyle": "clean", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "imageAlt": "Volunteers planting saplings in an autumn woodland", "entrance": "cascade"}
```
