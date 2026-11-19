# Hero 18: Ken Burns banner

**Use it when:** A campaign or event page that wants motion without a video.

**Why it works:** The background photo slowly zooms and pans (Ken Burns) under a tint, with the title at the bottom. It reads like a video loop at the cost of one image.

**Content it needs:** a background photo (landscape, at least 1600px wide, subject away from the text side); 1 badges; a heading of about 3 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `background` | Background: Background | `#032D60` |
| `backgroundEffect` | Images: Photo Motion | `kenburns` (Ken Burns) |
| `backgroundOverlay` | Images: Photo Overlay | `tint` (Brand Tint) |
| `badgePosition` | Badges: Badge Position | `top` |
| `blockHeight` | Images: Block Height | `standard` (Standard) |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#53B95B` |
| `contentPosition` | Images: Content Position | `bottom` (Bottom) |
| `headingAlign` | Heading: Heading Alignment | `left` (Left) |

JSON (the Configure Properties value):

```json
{"sectionType": "hero", "background": "#032D60", "brandColor": "#53B95B", "heading": "Summer of Service", "subheading": "Five thousand neighbors reached between June and September.", "headingAlign": "left", "bodyAlign": "left", "badgePosition": "top", "badges": [{"title": "Summer of Service · 2026", "style": "accent"}], "backgroundImageSource": "asset", "backgroundImageAsset": "FlowToolKit__Background_Green_Leaves_Banner", "backgroundOverlay": "tint", "backgroundEffect": "kenburns", "blockHeight": "standard", "contentPosition": "bottom"}
```
