# Hero 10: Eligibility quick check

**Use it when:** A grant or benefit page where the first question is whether to apply at all.

**Why it works:** A heading that promises a fast answer, a facts panel with the four tests, and one button. It sets expectations before the form.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 4 items; 1 buttons; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "headingAlign": "left", "bodyAlign": "left", "background": "#EEF1F4", "backgroundGradient": "off", "brandColor": "#53B95B", "sectionLabel": "Community Resilience Fund", "heading": "Sixty seconds tells you whether to apply.", "subheading": "Most funders make you read four pages of guidelines to learn you were never eligible. Answer three questions instead; if it is a fit, the full application starts prefilled with your answers.", "footnote": "$25k – $75k unrestricted · 2-year term · closes Sept 30", "buttons": [{"label": "✓ You are eligible to apply.", "url": "#", "style": "panel", "description": "Five questions, about three hours, saves as you go."}], "heroMedia": "facts", "items": [{"title": "501(c)(3) or fiscally sponsored?", "value": "Yes ✓"}, {"title": "Service area in Baker, Linn, or Marion county?", "value": "Yes ✓"}, {"title": "Operating budget under $2 million?", "value": "Yes ✓"}, {"title": "You are eligible to apply", "value": "✓"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "backgroundOverlay": "tint"}
```
