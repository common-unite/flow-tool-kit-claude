# Hero 21: Photo split with stats and crosshatch

**Use it when:** A demo or how-it-works section that pairs a claim with three proof numbers.

**Why it works:** A framed image on a crosshatched, side-scrimmed photo with counting stats beside it: busy enough to feel rich, ordered enough to read.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); one photo or screenshot; 3 stats; 2 buttons; a heading of about 11 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `side` (Side Scrim) |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#032D60` |
| `buttonAlign` | Buttons: Button Alignment | `right` (Right) |
| `countUp` | Items: countUp | `true` |
| `entrance` | Motion: Entrance | `wipe` (Wipe Reveal) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Lead Intake Flow in Salesforce Flow Builder` |
| `imageFit` | Media: Image Fit | `fit` (Fit) |
| `imageStyle` | Media: Image Style | `elevated` (Elevated) |
| `splitRatio` | Arrangement: Column Ratio | `left` (Wider Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#EEF1F4", "brandColor": "#032D60", "countUp": true, "sectionLabel": "Proof", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "right", "heading": "See two very different forms come together in under ten minutes.", "subheading": "Watch a long-form grant application and a simple event registration take shape, then see how Flow connects each submission to the right Salesforce context and manages what happens next.", "stats": [{"value": "10", "title": "minutes, two forms"}, {"value": "100%", "title": "Salesforce native"}, {"value": "0", "title": "lines of custom code"}], "buttons": [{"label": "Watch the under ten minute demo", "url": "#", "style": "brand"}, {"label": "Take the Goldilocks form check", "url": "#", "style": "outline"}], "reversed": true, "splitRatio": "left", "imageSource": "asset", "imageAlt": "Lead Intake Flow in Salesforce Flow Builder", "imageStyle": "elevated", "entrance": "wipe", "imageAsset": "FlowToolKit__Delightful_Bear_3", "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "backgroundOverlay": "side", "imageFit": "fit", "backgroundGradient": "off", "backgroundTexture": "crosshatch"}
```
