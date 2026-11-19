# Hero 15: Gradient split, framed photo right

**Use it when:** A values or approach statement with three supporting points and a good landscape photo.

**Why it works:** A brand gradient ground with the photo framed on the right and the points as white cards on the left: editorial and warm without the photo fighting the text.

**Content it needs:** one photo or screenshot; 3 bullets; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `entrance` | Motion: Entrance | `wipe` (Wipe Reveal) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `imageAlt` | Media: Image Alt Text | `Morning light through the forest canopy` |
| `imageFit` | Media: Image Fit | `fill` (Fill) |
| `imageStyle` | Media: Image Style | `clean` (Clean) |
| `showcaseItems` | Items: Item Display | `cards` (Cards) |
| `splitRatio` | Arrangement: Column Ratio | `right` (Wider Right) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "brandColor": "#53B95B", "sectionLabel": "Why This Fund Exists", "heading": "Unrestricted money, because you know your mission best.", "subheading": "Food security organizations spend too much time translating real work into fundable projects. This fund pays for the whole organization: the staff, the rent, the van that breaks down, and the program everyone already trusts you to run.", "footnote": "The work this fund pays for is already happening. Photo from a 2025 grantee site visit.", "headingAlign": "left", "bodyAlign": "left", "splitRatio": "right", "showcaseItems": "cards", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Wind_Farm_Mountains", "imageAlt": "Morning light through the forest canopy", "imageStyle": "clean", "bullets": [{"title": "What we fund", "description": "General operations, staff, direct food programs, distribution infrastructure, and capacity building."}, {"title": "What we do not fund", "description": "Individuals, capital campaigns over $50k, re-granting, political activity, or organizations outside the tri-county region."}, {"title": "Reporting that respects your time", "description": "One conversation and one two-page report per year. No custom metrics invented for us."}], "entrance": "wipe", "imageFit": "fill"}
```
