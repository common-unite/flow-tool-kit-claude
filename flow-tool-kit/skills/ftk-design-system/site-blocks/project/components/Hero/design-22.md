# Hero 22: Problem statement with a mascot

**Use it when:** The opening of a page that names the reader's problem before the solution.

**Why it works:** A light gray ground and the hot bear mascot set an empathetic, slightly humorous tone for a pain point.

**Content it needs:** a mascot or cut-out illustration; 2 buttons; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `imageAlt` | Media: Image Alt Text | `Bear buried in printed grant applications, paper forms, and tangled cables` |
| `imageBleed` | Media: Image Bleed | `bottom` (Bleed Bottom) |
| `imageStyle` | Media: Image Style | `mascot` (Mascot) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#EEF1F4", "backgroundGradient": "off", "brandColor": "#53B95B", "imageFloat": true, "heading": "Every nonprofit has a form backlog.", "subheading": "Grant applications, event registrations, program intake, volunteer signups, surveys, referrals, and requests. The challenge is not knowing forms are needed. The challenge is building them quickly, changing them easily, and keeping the data connected to Salesforce.", "buttons": [{"label": "Bring your form backlog", "url": "#", "style": "accent"}, {"label": "Watch the under ten minute demo", "url": "#", "style": "outline"}], "imageSource": "asset", "imageAlt": "Bear buried in printed grant applications, paper forms, and tangled cables", "imageStyle": "mascot", "imageBleed": "bottom", "entrance": "rise", "imageAsset": "FlowToolKit__Hot_Bear_1"}
```
