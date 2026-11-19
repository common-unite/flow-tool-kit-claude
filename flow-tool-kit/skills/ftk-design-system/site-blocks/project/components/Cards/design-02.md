# Cards 02: Four cards, two by two, on crosshatch

**Use it when:** Four short requirements or facts of equal weight (age, what to wear, accessibility).

**Why it works:** Four outlined cards in two columns on a crosshatched ground: each point gets equal weight and the band reads as one checklist.

**Content it needs:** 4 items. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#EEF1F4` |
| `backgroundTexture` | Background: Texture | `crosshatch` (Crosshatch) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `outlined` (Simple Border) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "bodyAlign": "left", "columns": "2", "cardStyle": "outlined", "items": [{"title": "Ages 14 and up", "description": "Volunteers under 16 need an adult on the same shift."}, {"title": "Closed-toe shoes", "description": "Required on the packing floor. Gloves and aprons provided."}, {"title": "Seated roles available", "description": "Tell us at signup and we will reserve one for you."}, {"title": "Hours are tracked for you", "description": "Your service hours post automatically. Request a signed letter any time."}], "hoverStyle": "lift", "backgroundTexture": "crosshatch", "background": "#EEF1F4"}
```
