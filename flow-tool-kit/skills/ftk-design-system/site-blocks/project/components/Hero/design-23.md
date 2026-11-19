# Hero 23: Brand gradient with key points and a mascot

**Use it when:** A capability section with three short labelled points (not numbers) and one action.

**Why it works:** The stats row holds three short words with captions, so key features read like stats; the mascot keeps it friendly on a green gradient.

**Content it needs:** a mascot or cut-out illustration; 3 stats; 1 buttons; a heading of about 13 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `entrance` | Motion: Entrance | `blur` (Blur In) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Flow Tool Kit bear presenting a completed grant application flowing into Salesforce` |
| `imageBleed` | Media: Image Bleed | `bottom` (Bleed Bottom) |
| `imageStyle` | Media: Image Style | `mascot` (Mascot) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Range", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "heading": "A long grant application and a simple registration, in the same ten minutes.", "subheading": "The point is not only speed. A simple form can stay simple. A complex form can stay powerful. Both connect to the Campaign, Funding Opportunity, or Program that matters.", "stats": [{"value": "Multi-step", "title": "with save and return"}, {"value": "Prefilled", "title": "from existing records"}, {"value": "Branching", "title": "handled in Flow"}], "buttons": [{"label": "Watch two forms come together", "url": "#", "style": "accent"}], "reversed": true, "imageSource": "asset", "imageAlt": "Flow Tool Kit bear presenting a completed grant application flowing into Salesforce", "imageStyle": "mascot", "imageBleed": "bottom", "entrance": "blur", "imageAsset": "FlowToolKit__Just_Right_Bear_2"}
```
