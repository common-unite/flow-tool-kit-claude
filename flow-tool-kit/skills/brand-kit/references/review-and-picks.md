# The review and the picks

Images, colors and fonts are chosen by eye, so the review shows everything the scan found and the person picks. The scan never trims the list to "the best few"; the picker is where it narrows.

## The two forms of the review

`make_picker.py` writes both from the same `candidates.json`:

| File | Use it when | How the picks come back |
|---|---|---|
| `brand-picker.html` | The person can open a page: Claude Code on their computer (open the file in a browser), or a surface that publishes artifacts | **Copy my picks** puts the picks on the clipboard to paste into the conversation; **Download picks** saves `picks.json` |
| `brand-review.md` | Chat, voice, or no thumbnails | The person answers with numbers: "logo 10, banner 3, brand color 2, heading font 1, corner radius 8px". Write `picks.json` from the answer |

The page is self-contained: every image is a thumbnail embedded in the page, because an artifact viewer blocks images from other sites, and nothing is served from the computer. It keeps the person's picks in their browser until they clear them. It is about 15 KB plus the thumbnails (around 700 KB for 50 images); with `--no-thumbs` it lists addresses instead.

The starting picks are guesses: the logo in the header's home link, a white logo as the alternate, the largest favicon, a wide program-page photo as the banner, the most-used button color as the brand color, the heading text color, the most-used fonts. On an update (`--previous`), the saved kit's colors, fonts, style and voice are the starting picks; images are picked again from the fresh scan.

## What the person picks

| Pick | Notes |
|---|---|
| Logo | Logo-like images are shown first, with a switch to show all |
| Alternate logo, favicon | Optional |
| Banner | Banner-sized pictures first (1000px wide or more; 700 to 999px stretch and soften). None keeps the package photo |
| Tile | Landscape, 400px or more. Optional |
| More photos | Each becomes a public image in the org. Photos of identifiable people are marked and need the organization's permission |
| Brand color | Shows its contrast on white. Under 4.5:1 it is darkened when the kit is confirmed |
| Heading color, accent, background tint | Optional. The tint must keep dark text readable |
| Body and heading fonts | The fonts found, or a name typed in |
| Corner roundness, button corners | The values found on the site are marked |
| Tone of voice | A few adjectives. Claude adds the do and avoid lines and the sample wording from `site-copy.md` |

## picks.json

```json
{
 "brandName": "Riverside Community Garden",
 "logo": 10, "logoAlternate": 11, "favicon": 1, "banner": 3, "tile": 4, "photos": [20, 21],
 "primary": "#2f6b3a", "heading": "#1d2b22", "accent": "#f2c14e", "background": "#f7f5ef",
 "bodyFont": "Source Sans 3", "headingFont": "Merriweather",
 "cornerRadius": "6px", "buttonRadius": "pill", "headingWeight": "700",
 "voice": {"adjectives": ["warm", "plain", "neighborly"], "do": ["Say what happens next"], "avoid": ["Jargon"],
           "sampleHeadings": ["Volunteer at the garden"], "sampleButtons": ["Sign up for a shift"]},
 "logoAltText": "Riverside Community Garden",
 "orgDefault": true,
 "notes": {"banner": "Use the spring photo, not the winter one"}
}
```

- An image is its number in `candidates.json` (the number in the review) or its address.
- Leave a key out to keep the guess; set it to `null` to pick nothing.
- `orgDefault`: `true` for the org's main brand (it goes into the org's Form Style defaults), `false` for another brand in the same org.
- `logoAltText` defaults to the brand name; `bannerAltText` and `bannerFocal` (`[x, y]` from the top left, 0 to 1) are optional.
- `assetPrefix` overrides the first word of the Asset File names (`Riverside_Logo`); by default it is the brand's first distinctive word, or its initials.
