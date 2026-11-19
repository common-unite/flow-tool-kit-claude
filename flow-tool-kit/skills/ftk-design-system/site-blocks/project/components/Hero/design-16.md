# Hero 16: Tall photo, text at the bottom

**Use it when:** A mission or impact page that should open on a full-bleed photograph.

**Why it works:** The overlay darkens only the bottom where the text sits, so most of the photo stays clear; a tall block and rise entrance make it feel like a magazine cover.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 1 buttons; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundOverlay` | Images: Photo Overlay | `bottom` (Bottom Scrim) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.25` (Gentle) |
| `blockHeight` | Images: Block Height | `tall` (Tall) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `contentPosition` | Images: Content Position | `bottom` (Bottom) |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Our Mission", "heading": "A garden that feeds the people who tend it.", "subheading": "Plots, classes and fresh food, run by neighbors, for neighbors.", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "buttons": [{"label": "Learn more", "url": "#", "style": "accent"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Wind_Turbine_Sky", "backgroundOverlay": "bottom", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25", "blockHeight": "tall", "contentPosition": "bottom", "entrance": "rise"}
```
