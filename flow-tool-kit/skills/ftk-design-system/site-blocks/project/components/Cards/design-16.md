# Cards 16: Five across, top bar

**Use it when:** Five small items in one row (five places a component can be used).

**Why it works:** Five columns with a brand top bar on each card keep five small cards distinct.

**Content it needs:** 5 items; a heading of about 6 words. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `bodyAlign` | Body: Alignment | `left` (Left) |
| `brandColor` | Background: Brand Color | `#2E844A` |
| `cardStyle` | Bullets: Card Style | `topbar` (Accent Top Bar) |
| `hoverStyle` | Motion: Hover | `lift` (Lift) |

JSON (the Configure Properties value):

```json
{"sectionType": "cards", "brandColor": "#2E844A", "sectionLabel": "One Swiss Army Form Component", "heading": "Build it once. Drop it everywhere.", "subheading": "Same component, same conditional logic, five places it can live. No rebuild, no divergence, no code.", "footnote": "One component. One place to change it. Don't repeat yourself.", "columns": "5", "cardStyle": "topbar", "bodyAlign": "left", "items": [{"title": "Record pages", "description": "Replaces Page Layouts and Dynamic Forms with one adaptive component.", "meta": "Same component", "iconType": "icon", "icon": "utility:desktop_and_phone"}, {"title": "New and Edit overrides", "description": "Override the standard buttons on any object. No code required.", "meta": "Same component", "iconType": "icon", "icon": "utility:settings"}, {"title": "Flow screens", "description": "Drop it into a screen and skip the tedious field mapping drudgery.", "meta": "Same component", "iconType": "icon", "icon": "utility:page"}, {"title": "Experience Cloud", "description": "Add it to any site page and improve the UX immediately.", "meta": "Same component", "iconType": "icon", "icon": "utility:user"}, {"title": "Any external site", "description": "Surface it anywhere with an embed code snippet.", "meta": "Same component", "iconType": "icon", "icon": "utility:apps"}], "hoverStyle": "lift"}
```
