# Worked example: Riverside Community Fund

An invented community fund's two pages, drawn to every site house rule. Copy its shape when you start a site; never its words.

| File | What it shows |
|---|---|
| `site.json` | Palette by name, the brand board, the shared navigation and footer, a guest audience, the paid edition |
| `pages/funding.json` | A listing: photo hero with the full range, the open funds as a Repeater of photo-overlay record cards beside an Action Card and Facts, a tag cloud, the page's one HTML Editor section (`s03b-split`, a stacked bar of the whole budget), a comparison table, a parallax quote band, steps and a closing band. An `empty` state draws the page with no open funds |
| `pages/fund.json` | A record page on a custom object: the hero, stats, tabs with rich content in every tab (each tab after the first has its own state artboard), a carousel and the closing ask, with `_design.sampleRecord` filling the `{{Field}}` text on the canvas |

Draw it (with the Site Blocks kit the plugin ships in its ftk-design-system skill):

```bash
cp -r examples/riverside-sample _site/riverside-sample
python3 -I scripts/build_site_review.py --site _site/riverside-sample
```

It passes every handoff and house check; the run lists only the images still to upload to a canvas.
