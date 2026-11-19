# Choosing blocks

How to decide, section by section, which block, which design and which settings a client page uses. Read this before designing any page. Each block card (Hero, Cards and the rest) shows every design for that block, numbered (Hero 01 to Hero 29), in narrower columns and at phone width, and its README says when to use each; this page says how to choose across blocks.

A page is designed in four decisions, in this order. Each one narrows the next.

1. **What is the page for?** Pick the page pattern.
2. **What is each section's job?** Pick the block.
3. **What does the client actually have?** Pick the design that fits the content.
4. **Where does it sit in the page's rhythm?** Pick background, motion and surface.

## 1. The page pattern

Start every page from the closest Page example card and change it, never from a blank page.

| The page is for | Start from | Recommended section order |
| --- | --- | --- |
| Getting people to apply (a grant, a benefit, a program) | `PageFundingOpportunity` | Hero, attached StatsBar, Cards of what it funds, eligibility Callout, Steps, Cards or Comparison Table, Quote, closing band |
| Listing many things (funds, programs, opportunities) | `ExampleListingPage`, `PageRecordCards` | Short hero, filter or intro Callout, Record Cards in a Repeater, closing band |
| Recruiting volunteers | `PageVolunteer` | Mascot or photo hero, Cards of roles, Steps to a first shift, Action Card for limited spots, Quote, closing band |
| Explaining a program | `PageProgramExamples` | Split hero with bullets, Stats, Timeline or Steps, Carousel or Gallery, Quote |
| Selling a service or product (marketing) | `PageProgramExamples` (there is no marketing Page example yet), with the product and problem heroes (`Hero` 19 to 23) | Problem hero, Cards of the solution, Stats proof, Pricing, Quote, closing band |
| Showing the work (impact, annual report) | `PageImageBlocks` | Ken Burns or tall photo hero, Stats, Facts as bars, Gallery, Quote |
| A record's own page (an application, a fund) | `ExampleParentRecordPage`, `ExampleChildRecordPage` | Banner hero, 8/4 Section with the record's form or Tabs and an Action Card |

## 2. The section's job

Every section has one job. Name it, then use the block that does that job.

| Job | Block | Not this |
| --- | --- | --- |
| Open the page, say what it is | `Hero` | A Callout or Cards as the first section |
| Answer "can I, when, how much" fast | `Hero` with `heroMedia: "facts"`, or `Facts` | Paragraphs of body copy |
| Prove it with numbers | `StatsBar` (attach it to the hero with `attachToPrevious`) | Numbers buried in Cards |
| Show proportions or a split | `Facts` with `factsDisplay: "bars"` or `"segmented"` | A table of percentages |
| Offer choices of equal weight | `Cards` | A Tag Cloud |
| Compare options on the same attributes | `ComparisonTable` | Cards with repeated fields |
| Sell tiers or levels | `Pricing` | Cards |
| Explain a process people follow | `Steps` | A Timeline |
| Show dates or stages over time | `Timeline` (horizontal for up to 5, vertical for more or for long text) | Steps |
| Ask for one thing, now | `ActionCard` (with a countdown or a limit) or `Callout` | A second Hero |
| Warn or remind | `Callout` with a border | A colored Hero band |
| Show many records | `RecordCard` in a `Repeater` | Hand-written Cards |
| Let people feel the work | `Quote`, `Carousel`, `ImageGallery`, `Image` | Stock photos in Cards |
| List topics, places or keywords | `TagCloud` | Bullets in a Callout |
| End the page with the next step | `Hero` with `heroLayout: "band"` | Nothing (a page never just stops) |

## 3. What the client has

A design is only right if the client can fill it. Before choosing a design, list what the client actually has for that section. Each variant card says what it needs.

| The client has | Use | Avoid |
| --- | --- | --- |
| Good photos of their own people and places | Photo heroes (`backgroundEffect`), `Quote` on a photo, `Carousel`, `ImageGallery`, `RecordCard` `photoOverlay` | Mascots and gradients that hide the photos |
| Only a logo and colors, no photos | Gradient and texture backgrounds, mascot heroes, `iconStyle: "tile"` Cards, `cardLayout: "banner"` Cards (a colored header band, no photo) | Photo heroes with a stock image that is not theirs |
| Hard numbers (served, raised, hours) | `StatsBar` with `countUp`, hero inline stats, `Facts` bars | Writing the numbers into body copy |
| Dates and deadlines | `RecordCard` `dateTile` or `countdown`, `ActionCard` countdown, horizontal `Timeline` | Dates hidden in paragraphs |
| Salesforce records (programs, shifts, funds, people) | `RecordCard` in a `Repeater`, matched card type: `dateTile` for events, `progress` for goals, `profile` for people, `valueSpotlight` for an amount, `fieldList` for detail | Static Cards that go out of date |
| Quotes from real people | `Quote` (one strong one per page, cinematic) | Inventing a quote |
| A long list (8 or more items) | `Cards` `cardLayout: "inline"` in 4 columns, `TagCloud` | 8 big cards |
| Two to three items | `Cards` with `arrangement: "split"` so the heading sits beside them | A 3-column grid with one item missing |

## 4. Rhythm: background, motion and surface

These settings make a page look designed instead of assembled. Decide them across the whole page, not block by block.

### Backgrounds

Alternate three grounds down the page: a deep brand color, white, and a light tint (`#EEF1F4` or the client's light tint). Never put two sections with the same ground next to each other unless the second is attached to the first.

| Background | Use it for | Why |
| --- | --- | --- |
| Photo (`backgroundImageAsset`) with `backgroundOverlay` | The opening hero, one mid-page band, the strongest quote | A photo is the most emotional ground; more than three per page and nothing stands out |
| `backgroundOverlay: "tint"` | Text centered over a photo | Brand-colored wash keeps text readable anywhere on the photo |
| `"side"` | Text on one side, subject on the other | Keeps the photo's subject clear |
| `"bottom"` | Tall photo with text at the bottom | Darkens only where the text sits |
| `backgroundGradient` `diagonal`, `vertical`, `horizontal` | Deep-color sections that need depth without a photo | Reads designed, costs nothing to source |
| `radial`, `spotlight`, `corner` | One section that must draw the eye (a feature, a closing band) | A focused light pulls attention; use one per page |
| `backgroundTexture` `crosshatch`, `dots`, `grid`, `stripes` | Light or deep sections that sit between two similar ones | Separates sections without a new color; `grid` suits schedules and maps, `dots` suits friendly copy, `crosshatch` suits statements |

### Motion

Motion is a budget, not a default. A page gets one motion moment above the fold and at most two below it.

| Setting | Use it | Do not |
| --- | --- | --- |
| `backgroundEffect: "kenburns"` | The opening hero or the closing quote, when the client has one great photo | Use it on two blocks on one page |
| `backgroundEffect: "parallax"` | One mid-page photo band | Use it under dense text |
| `entrance` `rise` | The default for the opening block | Put an entrance on every block |
| `cascade` | Lists that should arrive in order (bullets, steps, tags) | Use it on a single item |
| `wipe`, `blur`, `zoom` | A statement hero, a product shot, a quote | Use them on forms or tables |
| `countUp` | Stats that are achievements | Use it on prices or dates |
| `hoverStyle` `lift` | Anything clickable in a grid | Use `tilt` outside playful marketing pages |

### Surfaces (`cardStyle`, `imageStyle`)

| Surface | Means | Use it for |
| --- | --- | --- |
| `clean`, `flat` | Quiet | Cards inside a busy or dark section |
| `outlined` | Plain and honest | Choices, reassurance, lists of equal options |
| `elevated` | Pick me | Options to click, product shots |
| `deep` | Dramatic | One feature or urgent card |
| `glow` | Special | An event or opening date on a dark section |
| `topbar`, `siderule` | Status or category | Goals, notices, five small items in a row |
| `ghost` | Part of the section | Results on a gradient |
| `joined` | One idea in parts | Three parts of a problem, four ingredients |
| `mascot` (image only) | Personality | Marketing and volunteer heroes with a bear |

### Layout

- **Columns:** mix widths. A page of all 12-column sections looks like a document. Use 7/5 or 8/4 for copy beside a form or an Action Card, 6/6 for paired content.
- **`arrangement: "split"`:** put the heading beside the content when the content is short (two to four items) or the heading needs an intro paragraph.
- **`blockHeight`:** `tall` for one cinematic opening, `band` for thin strips (stats, closing band), `auto` for everything else.
- **`width`:** `full` for photo and color bands, `contained` for text-heavy sections, `inset` for a band that should read as a panel on the page.
- **`attachToPrevious`:** a StatsBar or Facts under a hero joins it, so the proof belongs to the promise.

### Column limits

A 1 of 4 column is about 300px; some designs fall apart there. Each block README's **Column limits** section lists them with the reason. At a glance, never put these in a 1 of 4 column (1 of 3 or wider only):

| Block | Designs that need 1 of 3 or wider | Also weak at phone width |
| --- | --- | --- |
| Pricing | every design (prefer full width or 1 of 2) | Pricing 06 |
| Hero | 03, 05, 07, 08, 10, 12, 13, 14, 21, 23 | |
| Callout | 02, 04, 05 | |
| Cards | 04, 06 | |
| Carousel | 06 | Carousel 06 |
| Facts | 04 | |
| Tag Cloud | 06 | Tag Cloud 06 |
| Comparison Table | 05 | |

Action Card, Quote, Stats, Timeline, Steps, Image, Image Gallery and Record Card designs hold up at every width. The usual cause is a large centered heading that breaks inside a word: on a phone-first page, shorten the heading or pick another design.

## Before you hand a design over

A page passes when all of these are true:

- [ ] It started from a Page example card, and each section names its job.
- [ ] Every block was chosen from the designs in its block card, not left at the block's defaults.
- [ ] The grounds alternate; no two neighbors share a background unless attached.
- [ ] At most one photo motion and one entrance above the fold.
- [ ] Every photo, number, date and quote is something the client has (or is listed as content to collect).
- [ ] Records come from Record Cards, not hand-written cards.
- [ ] The page ends with a closing band or Action Card.
- [ ] Column widths vary somewhere on the page.
- [ ] No design sits in a column narrower than its block README's Column limits allow.
- [ ] Every value passes the props check (the preview shows no props error).
