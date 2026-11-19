# Hero 02: Location with detail cards, mascot left

**Use it when:** A where-to-go or visit-us section: address, parking, transit, accessibility.

**Why it works:** The mascot sits left on a quiet gray ground and the details stack as small cards on the right, so practical information reads as friendly rather than as a list; cascade brings the cards in one by one.

**Content it needs:** one photo or screenshot; 3 bullets; 2 buttons; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#032D60` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `entrance` | Motion: Entrance | `cascade` (Cascade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Map of the Riverside Community Kitchen entrance` |
| `imageFit` | Media: Image Fit | `fit` (Fit) |
| `imageStyle` | Media: Image Style | `clean` (Clean) |
| `showcaseItems` | Items: Item Display | `cards` (Cards) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#EEF1F4", "backgroundGradient": "off", "brandColor": "#032D60", "sectionLabel": "Where To Go", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "heading": "Riverside Community Kitchen", "subheading": "1420 Riverside Avenue<br>Loading dock entrance, rear of the building<br>Riverside", "showcaseItems": "cards", "bullets": [{"title": "Parking", "description": "Free lot on the north side. Overflow street parking on Ash."}, {"title": "Transit", "description": "Bus 14 to Riverside and Ash, two minute walk."}, {"title": "Accessibility", "description": "Step-free entry at the dock. Accessible restrooms on the main floor."}], "buttons": [{"label": "Get directions", "url": "#", "style": "brand"}, {"label": "Add to calendar", "url": "#", "style": "outline"}], "reversed": true, "imageSource": "asset", "imageAlt": "Map of the Riverside Community Kitchen entrance", "imageStyle": "clean", "entrance": "cascade", "imageAsset": "FlowToolKit__Delightful_Bear_3", "imageFit": "fit"}
```
