# The render check

`scripts/render_check.cjs` loads each published page the way a visitor does and prints one table. It is the proof a page works; the Builder preview is not.

```bash
node <skill>/scripts/render_check.cjs <public page url> [more urls] [--expect 9,4] [--shots <folder>]
```

- **Public addresses only**, starting `https://`: the site's own domain and path prefix, as Setup, All Sites lists it (`https://<domain>/<prefix>/<page>`). Never the Builder or live-preview address.
- `--expect` gives, per page in order, the Flow Tool Kit component count the generator printed for it. Leave a place empty (`9,,4`) to skip a page.
- `--shots` saves a full-page screenshot per page and width (`1-<page>-1440.png`, `1-<page>-390.png`). Read them: a page can pass every number and still look wrong.

**Setup, once per computer or cloud session:** Node, and `npx -y playwright@1.47.2 install chromium`. The script finds Playwright from the project, the global install or the npx cache. In claude.ai chat the sandbox usually cannot reach the site. The check then needs Claude Code.

## How it loads a page

Each page and width gets a fresh browser context with no cookies, so it is a logged-out guest every time. Widths are 1440 by 900 (desktop) and 390 by 844 (phone). It waits for the page, scrolls to the bottom and back so entrance animations play, waits again, then measures through every shadow root, since LWR components render inside them.

## The columns

| Column | Fails when |
|---|---|
| width applied | The page's own `innerWidth` differs from the width asked: the measurement is not of a real phone layout |
| status | Not 200. "(login page)" means the visitor was sent to log in: the site is not public, not active, or the page is members-only |
| sideways scroll | The page is wider than the screen by more than 1 px: something does not fit at that width |
| broken images | An image that loaded with no pixels: a private file, a wrong asset name, or a file address a guest cannot reach |
| console errors | Any console error or uncaught page error. "(load failure)" marks LWR3008 or "could not be loaded": a component the publisher did not bundle |
| failed requests | Requests that failed or answered with an HTTP error (400 and up), each listed with its address. Never a FAIL on its own (analytics and fonts can fail harmlessly), but read every one: a 401 or 403 is usually missing guest access |
| FTK components | Top-level Flow Tool Kit components on the page, against `--expect`. Fewer means a block, form or repeater did not render for a guest |
| empty | A Flow Tool Kit component with no height: present but showing nothing, often missing guest access or an empty listing |
| LWR Support | Whether FlowToolKit LWR Support is on the page. A page with Flow Tool Kit components and no LWR Support fails |

Under the table, each error, broken image, failed request and empty component is listed with its width. Exit 0 when every row passes, 1 on any FAIL, 2 when the check could not run (no Playwright, a bad address).

## Reading a FAIL

- **An `HTTP 401` on `ui-api/object-info` and a repeater reading "Records are unavailable":** the guest has no access to the repeater's object. The component still renders (so the count matches), which is why failed requests and console errors are read too. Grant read on the object and its fields and add a guest sharing rule ([guest-access.md](guest-access.md)).
- **Component count short, LWR Support yes:** the guest cannot read what the block or repeater shows. Check field access and the guest sharing rule ([guest-access.md](guest-access.md)).
- **Load failure or LWR Support no:** add LWR Support (and your own support component) to the Theme Footer with `--entire-site`, deploy, publish, check again.
- **Component count off by what you just changed** (`3 of 2` after removing a section): the site was not published after the deploy. It still serves the last publish.
- **Sideways scroll at 390 only:** a fixed-width element or too many columns for a phone; look at the 390 screenshot.

A FAIL is fixed (then published and checked again) or reported as a deviation with its reason. "Checked as a guest" means this table, with every row read.
