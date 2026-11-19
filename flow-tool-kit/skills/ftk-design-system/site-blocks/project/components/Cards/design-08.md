# Cards 08: Joined, three columns

**Use it when:** Three parts of one idea (a problem in three parts).

**Why it works:** cardStyle joined butts the cards together into one panel, so they read as one thought in three pieces.

**Content it needs:** 3 items; a heading of about 8 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `joined` (Joined) |
| `footnoteAlign` | Footnote: Footnote Alignment | `left` (Left) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "sectionLabel": "The Goldilocks Problem", "heading": "Nonprofit form building has become a Goldilocks problem.", "subheading": "Teams are left choosing which compromise they can tolerate.", "headingAlign": "left", "bodyAlign": "left", "columns": "3", "cardStyle": "joined", "footnote": "Just right is where we start. Delightful is the standard.", "footnoteAlign": "left", "items": [{"eyebrow": "Too hot", "title": "Custom code and heavyweight platforms", "description": "They can solve almost anything, but many nonprofits do not have the technical staff to own them."}, {"eyebrow": "Too cold", "title": "External form tools and tedious screen builds", "description": "Easy to design, until prefill, branching, data processing, and Salesforce automation get complex."}, {"eyebrow": "Downright delightful", "title": "Flow Tool Kit", "description": "An approachable front-end experience together with the data, logic, and automation of Salesforce Flow."}], "hoverStyle": "lift"}
```
