# Hero 09: Statement on a photo

**Use it when:** An about or mission page that opens with one strong sentence and a short paragraph, with nothing to click yet.

**Why it works:** A headline and one paragraph over a brand-tinted parallax photo, no buttons: the quietest hero, letting the copy carry the page.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); a heading of about 11 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.25` (Gentle) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `wipe` (Wipe Reveal) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "sectionLabel": "The Community Resilience Fund", "heading": "The van breaks down. The rent goes up. The mission stays.", "subheading": "Food security organizations spend too much time translating real work into fundable projects. This fund pays for the whole organization - the staff, the rent, the van, and the program everyone already trusts you to run. Unrestricted, because you know your mission best.", "entrance": "wipe", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Turbine_Blades_Blue", "backgroundOverlay": "tint", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25"}
```
