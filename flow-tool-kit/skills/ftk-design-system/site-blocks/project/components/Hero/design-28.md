# Hero 28: Closing band, green with dots

**Use it when:** A gentle closing nudge with one action, after a light section.

**Why it works:** A short green band with a fine dot texture and one button: present but not loud.

**Content it needs:** 1 buttons; a heading of about 4 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `dots` (Dots) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroLayout` | Arrangement: Button Placement | `band` |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "heroLayout": "band", "background": "#EEF1F4", "backgroundTexture": "dots", "brandColor": "#2E844A", "sectionLabel": "Volunteer", "heading": "Saturday shifts are open.", "subheading": "Four hours, lunch included, no experience needed.", "buttons": [{"label": "Pick a shift", "url": "#", "style": "brand"}], "headingAlign": "left"}
```
