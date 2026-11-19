# Reading the website

How the brand kit reads an organization's site, where each item lands in a Flow Tool Kit form, and the checks. The scan informs the design; it is not a pixel copy of the site.

## What to collect, and where it goes

| Item | Where to look | Where it goes |
|---|---|---|
| Logo | The image in the header's home link, `og:image`, an SVG in the header, files whose name or alt text says logo and names the organization | Default Logo in the org's Form Style defaults: the banner of every template without its own logo. Keep the original file, and an SVG where one exists |
| Alternate logo | A white or one-color version, often in the footer | Dark or brand-colored backgrounds: a site footer, an email's brand bar |
| Brand color | Button backgrounds, links, the browser theme color, CSS variables named brand or primary | Form Style brand color (buttons, links, selected choices, the banner fill), at least 4.5:1 on white |
| Heading color, accent, background tint | Heading text, a second saturated color, light section backgrounds | Section titles, dividers and highlights, the area around emails |
| Fonts | Body and heading `font-family`, web font links, `@font-face` | Form Style body and heading fonts, with a fallback stack. A paid font the org cannot license for web use: pick a close Google Font and say which |
| Shape | Button and input corners, filled or outlined buttons, heading weight | Form Style corner radius, button corners, heading weight |
| Banner and tile | Wide photos on the program page first, then the home page hero | The template's banner image (wide, 1000px or more) and gallery tile (landscape, 400px or more) |
| Photos | Every page, tagged with its page | Public Asset Files for intros, confirmations and site pages. Never a photo of an identifiable person without the organization's permission |
| Tone of voice | The program page's headings and calls to action, the site's button labels | The kit's voice, then the wording of titles, help text and confirmation messages |

## Without a browser (the default)

`site_crawl.py` fetches pages with plain HTTP, politely: one request every `--delay` seconds (0.3 by default), four at a time, and a 429 or 503 waits for `Retry-After` and slows the rest of the crawl. It follows the start page's redirect first and treats `www` and the bare host as one site. It reads lazy-loaded images (`data-*` attributes, `<noscript>` copies, gallery links, image addresses in page scripts and JSON, a lazy loader's placeholder SVG that names the real file), takes the largest `srcset` entry, and counts one media file served at many sizes once.

It also keeps the home and program pages' stylesheet links and inline `<style>` blocks, which `site_styles.py` reads:

- every color with where it is used, scored by how much that place says "brand" (a button background counts far more than a border);
- a platform's untouched preset palette left out: block editor color presets at their default values, a page builder's starting kit colors, a CSS framework's default variables. A site that changed them keeps its own values. What was left out is listed in the review;
- grays, near black and near white kept apart as neutrals, offered for the heading and background picks;
- fonts by role, web font families, icon fonts left out; corner radius of buttons and of inputs and cards; heading weight; filled or outlined buttons.

Stylesheets give the colors a site declares. A site built mostly in a page builder's inline settings can hide its real brand from them; then offer the rendered-page scan.

## The rendered page (optional, ask first)

Ask: "Do you want exact colors and fonts from the rendered page? That needs a headless browser in Claude Code (or a browser tool you allow)." Only on a yes:

- **Claude Code**: `node scripts/render_scan.cjs <page address> _brand/<slug>/render-home.json`, once for the home page and once for the program page. It needs Playwright with Chromium once: `npx -y playwright@1.47.2 install chromium-headless-shell`. It loads the page, scrolls so lazy styles load, and reads computed colors (with where they are used), fonts, the button style and the main colors inside the logo. It never clicks or submits anything.
- **A browser tool the person allows**: paste `scripts/site-scan.js` into its JavaScript runner wrapped in `await`, on the home page and then the program page. Read the results in parts (`__scanPart('colors')`), since some tools hide long output. Do not load other pages in hidden frames from the runner: the tool can lose the tab.

Pass each result to `make_picker.py` with `--rendered`.

## In chat

A chat sandbox often cannot reach outside websites. `site_crawl.py` and `site_styles.py` then stop with exit code 3. Read the site with the **web fetch** tool instead:

1. Fetch the home page and the program page, then the pages their navigation links to. From what comes back, note each page's title, headings, button labels and readable text, and every image address with its alt text.
2. When a stylesheet address is visible (a `<link rel="stylesheet">`, or the theme's `style.css`), fetch it, save the text to a file in the sandbox, and run `python3 scripts/site_styles.py --css <file> --out _brand/<slug>/site-styles.json`. Pass any Google Fonts link with `--google-fonts`.
3. Write `site-crawl.json` by hand in the crawler's shape, so the rest of the steps run unchanged. The keys the later steps read:

```json
{
 "start": "https://www.example.org/", "organization": "Riverside Community Garden", "programPage": "https://www.example.org/volunteer/",
 "crawledOn": "2026-01-15",
 "pages": {"/": {"title": "Home", "headings": ["Growing food together"], "buttons": ["Volunteer with us"],
                 "copy": [{"tag": "p", "text": "Riverside Community Garden turns empty lots into shared gardens."}]}},
 "images": [{"url": "https://www.example.org/media/logo.png", "label": "Riverside Community Garden logo", "group": "logo",
             "fit": "logo", "size": "", "pages": ["/"], "page": "/", "program": false, "people": false}]
}
```

Groups: `logo`, `favicon`, `banners`, `site photos`, `people`, `partner logos`, `icons and badges`, `documents`, `shop and catalog`. Fit: `banner`, `banner (small)`, `wide block`, `tile`, `square`, `portrait`, `small`, `unknown size`, or the group for logos and icons.

Thumbnails need the image files, so in chat the review is usually the numbered list with each image's address; the person opens the ones they want to see. For the images picked, ask the person to upload the files (or save them from the site) and pass them to `brand_assets.py --file role=path`.

## Done when

- Every page in the site's navigation was read, or each one that failed is listed with its reason.
- Every color offered traces back to a place on the site, the logo, or a person's choice; nothing is added without saying so.
- The brand and heading colors reach 4.5:1 against white.
- A form drawn with the kit and the site, side by side, look like the same organization.
- Site unreachable even with web fetch: say so, ask the person for the logo file and the brand color, and build the kit from those.
