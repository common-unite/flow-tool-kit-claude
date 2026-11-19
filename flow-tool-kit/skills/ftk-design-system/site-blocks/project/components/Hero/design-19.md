# Hero 19: Mascot on dots

**Use it when:** A playful marketing or product page, where personality matters more than facts.

**Why it works:** A bleeding mascot on a dotted navy ground with a punchy three-line headline: the most brand-forward hero in the set.

**Content it needs:** a mascot or cut-out illustration; 2 buttons; a heading of about 5 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundTexture` | Background: Texture | `dots` (Dots) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `footnoteAlign` | Footnote: Footnote Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Downright Delightful, the Flow Tool Kit bear holding a finished customer form` |
| `imageBleed` | Media: Image Bleed | `bottom` (Bleed Bottom) |
| `imageStyle` | Media: Image Style | `mascot` (Mascot) |
| `splitRatio` | Arrangement: Column Ratio | `left` (Wider Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "backgroundGradient": "off", "brandColor": "#53B95B", "imageFloat": true, "heading": "<font color=\"#F26B4A\">Too hot.</font> <font color=\"#5ABCE6\">Too cold.</font><br><font color=\"#53B95B\">Downright delightful.</font>", "subheading": "Flow Tool Kit helps nonprofits build polished Salesforce-connected forms in minutes, from long-form grant applications to simple event registrations, while Salesforce Flow handles the data, logic, automation, and record connections behind the scenes.", "buttons": [{"label": "Get the Flow Tool Kit", "url": "#", "style": "accent"}, {"label": "Book a Free Call", "url": "#", "style": "outline"}], "footnote": "Free to start · Grassroots $30/mo · Unlimited $150/mo", "footnoteAlign": "left", "imageSource": "asset", "imageAlt": "Downright Delightful, the Flow Tool Kit bear holding a finished customer form", "imageStyle": "mascot", "imageBleed": "bottom", "splitRatio": "left", "entrance": "rise", "imageAsset": "FlowToolKit__Delightful_Bear_4", "backgroundTexture": "dots"}
```
