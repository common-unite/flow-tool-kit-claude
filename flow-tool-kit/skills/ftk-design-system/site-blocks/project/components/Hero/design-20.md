# Hero 20: Framed illustration on a vertical gradient

**Use it when:** A product or feature page with a screenshot or illustration to show.

**Why it works:** The elevated image puts the visual on a white card with a shadow, the navy vertical gradient adds depth, and the blur entrance draws the eye to it.

**Content it needs:** one photo or screenshot; 1 buttons; a heading of about 10 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `vertical` (Vertical) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `entrance` | Motion: Entrance | `blur` (Blur In) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Lead Intake Flow in Salesforce Flow Builder` |
| `imageFit` | Media: Image Fit | `fit` (Fit) |
| `imageStyle` | Media: Image Style | `elevated` (Elevated) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "brandColor": "#2E844A", "sectionLabel": "See It Work", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "heading": "From blank flow to live form in under 10 minutes", "subheading": "Drag in the Flow Tool Kit building blocks, connect your records, and publish. No packages to babysit, no per-response fees, no exports.", "buttons": [{"label": "Watch the 3-minute demo", "url": "#", "style": "brand"}], "reversed": true, "imageSource": "asset", "imageAlt": "Lead Intake Flow in Salesforce Flow Builder", "imageStyle": "elevated", "entrance": "blur", "imageAsset": "FlowToolKit__Delightful_Bear_3", "backgroundGradient": "vertical", "background": "#032D60", "imageFit": "fit"}
```
