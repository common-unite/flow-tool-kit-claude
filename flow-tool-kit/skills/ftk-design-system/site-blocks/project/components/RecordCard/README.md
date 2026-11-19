# RecordCard

One record drawn as a card in one of eleven card types, its lines typed text or {{Field}} merge fields.

**Maps to:** a Form (Design Block) whose `sectionType` is `recordCard` (Record Card in the type picker). The preview is the package's own `siteDesignBlock`, compiled from `siteDesignBlock`, so what you see is what the site renders.

## Props

Every prop is a key of the block's JSON (the Configure Properties value). Write collections as arrays; they are stored as JSON strings. Enumerated props take only the package's values, and the props check fails on anything else. Full types: `index.d.ts`, `RecordCardProps`.

### Content

| Prop | Property Editor | Notes |
| --- | --- | --- |

### Detail Rows (`items`)

A list of rows, up to 6. Each takes:

| Key | Label | Values |
| --- | --- | --- |
| `title` | Label | richtext |
| `value` | Value | richtext |

With `heroMedia: "mediaTop"` each item takes `title`, `value`.

With `heroMedia: "iconLead"` each item takes `title`, `value`.

With `heroMedia: "fieldList"` each item takes `title`, `value`.

With `heroMedia: "valueSpotlight"` each item takes `title`, `value`.

With `heroMedia: "profile"` each item takes `title`, `value`.

### Card

`cardType`: `mediaTop`, `photoOverlay`, `dateTile`, `progress`, `headerBand`, `strip`, `countdown`, `iconLead`, `profile`, `fieldList`, `valueSpotlight`. Each card type draws its own slots; a slot the type does not draw is ignored. Card keys: `avatarType`, `backgroundColor`, `badge`, `badgeStyle`, `buttons`, `cardType`, `cornerTag`, `countdownDirection`, `countdownEnded`, `countdownUnits`, `date`, `description`, `endDate`, `eyebrow`, `flowApiName`, `formMode`, `formQualifiedApiName`, `icon`, `iconStyle`, `image`, `imageAlt`, `imageFrame`, `label`, `link`, `mediaHeight`, `meta`, `modalHeader`, `modalWidth`, `overlayStyle`, `progressCurrent`, `progressTotal`, `recordField`, `recordSource`, `rows`, `scrimColor`, `stripIcon`, `stripTone`, `style`, `subtitle`, `tags`, `target`, `textColor`, `title`, `type`, `url`, `value`, `valueSuffix`.

### Settings this type's designs use

| Prop | Property Editor | Values |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | color |
| `brandColor` | Background: Brand Color | color |

Buttons (`buttons`), badges (`badges`) and every Background, Border, Spacing, Motion, Visibility and Images setting are shared by all blocks: see the Block card and the shared parts.

## Rules

- A control steers only the part it sits under in the Property Editor. Set a color in the pane of the thing it paints.
- Labels are generic across types: the same key means the same thing on every block.
- Color props offer tokens: leave one empty and the block takes the site brand (layer 1) or the `--ftk-site-*` tokens (layer 2). Set a literal only where the design needs that exact color on this block (layer 3).
- Use SLDS: a look the block cannot give is a design question to raise, not something to hand-style.

## Designs

11 designs, all in this card's preview in the order below (each numbered in its corner; hover for its name), then the block in 1 of 2, 1 of 3, 1 of 4 and 8 and 4 columns and at phone width. Pick by the section's job and what the client can supply; how to choose across blocks: `Choosing blocks`.

| # | Design | Use it when |
| --- | --- | --- |
| 01 | Media on top | Listings with a photo (opportunities, programs). |
| 02 | Photo overlay | Photo-led records where the image sells it (events, places). |
| 03 | Date tile | Events and shifts, where the date matters most. |
| 04 | Countdown | Records with a deadline (applications, registration close). |
| 05 | Strip | Compact list rows (many records on one page). |
| 06 | Progress | Records with a goal (a campaign, a project). |
| 07 | Header band | Records with a category, shown in a colored band. |
| 08 | Small image lead | Compact records led by a small round image or icon (speakers, staff, resources). |
| 09 | Profile | People: staff, volunteers, mentors. |
| 10 | Field list | Records where several field values matter (an application summary). |
| 11 | Value spotlight | Records with one key number (an award amount, hours given). |

### Record Card 01: Media on top

**Use it when:** Listings with a photo (opportunities, programs).

**Why it works:** cardType mediaTop: photo, title, fields and a button, the most familiar card.

**Content it needs:** one photo or screenshot; 2 items; 1 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "mediaTop", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Tables", "badge": "Organizational Support", "eyebrow": "Animal Welfare", "title": "Clean Kennels at Shelter", "subtitle": "Riverside Animal Shelter", "items": [{"title": "Where", "value": "Riverside"}, {"title": "When", "value": "Oct 5 to Dec 25, 2026"}], "buttons": [{"label": "Sign up", "url": "#", "style": "link"}]}
```

### Record Card 02: Photo overlay

**Use it when:** Photo-led records where the image sells it (events, places).

**Why it works:** cardType photoOverlay puts the title and badge over the photo.

**Content it needs:** one photo or screenshot. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "photoOverlay", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Shoreline_Cleanup_Sunset", "badge": "Environment", "badgeStyle": "accent", "eyebrow": "Sat, Oct 17, 9 am to 12 pm", "title": "Riverside Shoreline Cleanup", "subtitle": "Riverside Shoreline Crew, north lot"}
```

### Record Card 03: Date tile

**Use it when:** Events and shifts, where the date matters most.

**Why it works:** cardType dateTile leads with a large date block, so a list of cards reads like a calendar.

**Content it needs:** one photo or screenshot; 2 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "dateTile", "date": "2026-10-24", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Tree_Planting_Autumn", "title": "Neighborhood Tree Planting", "subtitle": "10 am to 2 pm, Riverside Park", "meta": "32 going", "buttons": [{"label": "Add to calendar", "url": "#", "style": "outline"}, {"label": "Register", "url": "#", "style": "brand"}]}
```

### Record Card 04: Countdown

**Use it when:** Records with a deadline (applications, registration close).

**Why it works:** cardType countdown shows the time left as the main element, and switches to a closed message once the date passes.

**Content it needs:** 1 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "countdown", "date": "2026-10-19", "eyebrow": "Grant cycle", "title": "Applications close", "subtitle": "Submit before the deadline to be considered this cycle", "countdownEnded": "Applications are closed", "buttons": [{"label": "Start application", "url": "#", "style": "brand"}]}
```

### Record Card 05: Strip

**Use it when:** Compact list rows (many records on one page).

**Why it works:** cardType strip is a slim horizontal row, so many records fit.

**Content it needs:** 1 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "strip", "badge": "New", "badgeStyle": "brand", "title": "Clean energy training opens October 1", "subtitle": "Six sessions, stipend provided", "buttons": [{"label": "Learn more", "url": "#", "style": "link"}]}
```

### Record Card 06: Progress

**Use it when:** Records with a goal (a campaign, a project).

**Why it works:** cardType progress shows a progress bar toward the goal.

**Content it needs:** 1 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "progress", "eyebrow": "Food Security", "badge": "Filling fast", "title": "Pack Weekend Meal Kits", "subtitle": "Riverside Food Bank, Thu, Oct 8, 5:30 pm", "progressCurrent": "16", "progressTotal": "20", "meta": "4 spots left", "buttons": [{"label": "Claim a spot", "url": "#", "style": "accent"}]}
```

### Record Card 07: Header band

**Use it when:** Records with a category, shown in a colored band.

**Why it works:** cardType headerBand puts a brand band with badges above the content.

**Content it needs:** 1 buttons; 3 badges. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "headerBand", "eyebrow": "Virtual, live", "cornerTag": "90 min", "title": "Grant Writing for First-Time Applicants", "description": "Build a letter of interest from a template, with live feedback on your draft.", "badges": [{"title": "Beginner"}, {"title": "Free"}, {"title": "Certificate"}], "meta": "Dana Morales, Wed, Oct 14, 12 pm PT", "buttons": [{"label": "Enroll", "url": "#", "style": "link"}]}
```

### Record Card 08: Small image lead

**Use it when:** Compact records led by a small round image or icon (speakers, staff, resources).

**Why it works:** cardType iconLead puts a small round image beside the title, so many records stay compact but still have a face.

**Content it needs:** one photo or screenshot; 2 badges. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "iconLead", "avatarType": "image", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Volunteer_Team_Talking", "eyebrow": "Keynote, day 1", "title": "Tasha Nguyen", "subtitle": "Executive Director, Riverside Housing Partners", "description": "Keeping neighbors in place as values rise.", "badges": [{"title": "Housing"}, {"title": "9 am"}]}
```

### Record Card 09: Profile

**Use it when:** People: staff, volunteers, mentors.

**Why it works:** cardType profile centers a round photo with name, role and badges.

**Content it needs:** one photo or screenshot; 2 buttons; 3 badges. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "profile", "avatarType": "image", "imageSource": "asset", "imageAsset": "FlowToolKit__Background_Bamboo_Forest_Joy", "title": "Jordan Reyes", "subtitle": "Volunteer Coordinator, Riverside East", "badges": [{"title": "Bilingual"}, {"title": "Youth"}, {"title": "5 yrs"}], "buttons": [{"label": "Email", "url": "#", "style": "brand"}, {"label": "Book time", "url": "#", "style": "outline"}]}
```

### Record Card 10: Field list

**Use it when:** Records where several field values matter (an application summary).

**Why it works:** cardType fieldList lists label and value pairs, like a mini record page.

**Content it needs:** 4 items; 2 buttons; 3 badges. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "fieldList", "title": "Front Desk Greeter", "items": [{"title": "Organization", "value": "Riverside Neighborhood Center"}, {"title": "Location", "value": "100 Riverside Plaza"}, {"title": "Schedule", "value": "Weekdays, 2-hr blocks"}, {"title": "Commitment", "value": "3 months"}], "badges": [{"title": "Spanish"}, {"title": "Customer service"}, {"title": "Ages 16+"}], "buttons": [{"label": "Apply", "url": "#", "style": "brand"}, {"label": "Save", "url": "#", "style": "outline"}]}
```

### Record Card 11: Value spotlight

**Use it when:** Records with one key number (an award amount, hours given).

**Why it works:** cardType valueSpotlight puts one value large, with the rest as supporting text.

**Content it needs:** 1 buttons. If the client cannot supply it, pick another design.

| Prop | Property Editor | Value |
| --- | --- | --- |
| `accentColor` | Background: Accent Color | `#53B95B` |
| `brandColor` | Background: Brand Color | `#032D60` |

JSON (the Configure Properties value):

```json
{"sectionType": "recordCard", "brandColor": "#032D60", "accentColor": "#53B95B", "cardType": "valueSpotlight", "eyebrow": "Scholarship", "badge": "Closes Nov 1", "title": "First-Gen College Fund", "value": "$5,000", "subtitle": "10 awards for county seniors", "buttons": [{"label": "Apply", "url": "#", "style": "accent"}]}
```

## Column limits

Checked by rendering every design in a 1 of 2 (6), 1 of 3 (4) and 1 of 4 (3) Section column on a 1280px page, and at phone width (390px). A 1 of 4 column is about 300px wide. Designs not listed here hold up at every width. The narrower-columns and phone rows of this card only show designs that are allowed there.

Every Record Card design holds up in 1 of 4 and at phone width.

## On LWR

The same component (`FlowToolKit:siteDesignBlock`) with the same JSON; the conversion scripts place it on an LWR site. Checked side by side on the Testing LWR site.

- **Placement:** in a column of an LWR section (`community_layout:section`), not an Aura Flexible Layout section. Every component in a column but the last is spaced by the site's component spacer (1.5rem at Builder's default).
- **Theme:** brand and fonts come from the LWR branding set's `--dxp-g-*` hooks instead of the Aura Theme panel. `Page`'s `theme` sets both.
- **Asset Files:** served from `<site basePath>/sfsites/c/file-asset/<name>`; the block resolves either site's path from the same Asset File name.
- **Publish:** an LWR site serves what it had at its last publish, so publish after placing or changing a block.
