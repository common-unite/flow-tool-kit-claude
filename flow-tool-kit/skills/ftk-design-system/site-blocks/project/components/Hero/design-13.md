# Hero 13: Capital grant facts, light

**Use it when:** A capital or equipment grant page with several eligibility facts and a long description below.

**Why it works:** A white ground with five facts and three badges reads as practical and trustworthy, suited to a funder audience.

**Content it needs:** 5 items; 2 buttons; 3 badges; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#F4BE45` |
| `background` | Background: Background | `#FFFFFF` |
| `backgroundGradient` | Background: Gradient | `off` (Off) |
| `badgePosition` | Badges: Badge Position | `top` |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `cardBackgroundColor` | Background: Card Background | `#EEF1F4` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |
| `splitRatio` | Arrangement: Column Ratio | `left` (Wider Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#FFFFFF", "backgroundGradient": "off", "brandColor": "#53B95B", "accentColor": "#F4BE45", "headingAlign": "left", "bodyAlign": "left", "splitRatio": "left", "cardBackgroundColor": "#EEF1F4", "badges": [{"title": "2026 cycle open", "style": "brand"}, {"title": "1:1 match required", "style": "neutral"}, {"title": "Closes October 15", "style": "accent", "pulse": true}], "badgePosition": "top", "sectionLabel": "Infrastructure Grant Program", "heading": "Buildings, vehicles, and equipment that outlast the grant", "subheading": "Grants of $10,000 to $100,000 toward physical assets: kitchen equipment, vehicles, accessibility retrofits, and facility repairs. Requires a dollar-for-dollar match and two vendor quotes.", "buttons": [{"label": "Start an application", "url": "#", "style": "brand"}, {"label": "Read the match rules", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Award range", "value": "$10k – $100k"}, {"title": "Match", "value": "1:1, cash or pledged"}, {"title": "Eligible costs", "value": "Assets over $5k, 3+ yr life"}, {"title": "Required docs", "value": "2 quotes + board resolution"}, {"title": "Payout", "value": "On invoice, reimbursed"}]}
```
