# Hero 14: Tall photo, side overlay

**Use it when:** The top of a funder's main grant page, where you want one cinematic moment before the details.

**Why it works:** A tall parallax photo with a side overlay holds the text in a dark band on one side, so the photo stays visible on the other; the facts panel keeps it useful.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 5 items; 2 buttons; 3 badges; a heading of about 7 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `parallax` (Parallax) |
| `backgroundOverlay` | Images: Photo Overlay | `side` (Side Scrim) |
| `backgroundParallaxSpeed` | Images: Drift Speed | `0.25` (Gentle) |
| `badgePosition` | Badges: Badge Position | `top` |
| `blockHeight` | Images: Block Height | `tall` (Tall) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `buttonAlign` | Buttons: Button Alignment | `left` (Left) |
| `contentPosition` | Images: Content Position | `center` (Centered) |
| `entrance` | Motion: Entrance | `rise` (Rise and Fade) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |
| `heroMedia` | Media: Media | `facts` (Facts) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "brandColor": "#53B95B", "sectionLabel": "Community Resilience Fund", "heading": "General operating grants for food security organizations", "subheading": "Two-year, unrestricted grants of $25,000 to $75,000 for organizations reducing food insecurity in the tri-county region. We fund the mission, not a line item, and we do not ask you to invent a new program to fit our guidelines.", "footnote": "Save and return any time · Two-stage review · Decisions within 60 days of close", "headingAlign": "left", "bodyAlign": "left", "buttonAlign": "left", "badgePosition": "top", "badges": [{"title": "Accepting applications", "style": "accent"}, {"title": "2026 cycle", "style": "outline"}, {"title": "Closes September 30", "style": "neutral"}], "buttons": [{"label": "Start an application", "url": "#", "style": "accent"}, {"label": "Check your eligibility", "url": "#", "style": "outline"}], "heroMedia": "facts", "items": [{"title": "Total available", "value": "$1,200,000"}, {"title": "Award range", "value": "$25,000 - $75,000"}, {"title": "Grant term", "value": "2 years, unrestricted"}, {"title": "Expected awards", "value": "18 - 24"}, {"title": "Application time", "value": "About 3 hours"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "backgroundOverlay": "side", "backgroundEffect": "parallax", "backgroundParallaxSpeed": "0.25", "blockHeight": "tall", "contentPosition": "center", "entrance": "rise"}
```
