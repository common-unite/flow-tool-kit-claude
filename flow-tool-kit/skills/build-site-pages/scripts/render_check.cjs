#!/usr/bin/env node
// Logged-out render check at 1440 and 390 px (usage and columns: references/render-check.md); exit 1 on any FAIL.
const fs = require('fs');
const path = require('path');
const os = require('os');

// Find Playwright and a headless Chromium on any computer or cloud session (Linux, macOS, Windows).
// Install once: npx -y playwright@1.47.2 install chromium   (on Claude Code on the web, allow the npm registry first)

function loadPlaywright() {
  for (const name of ['playwright', 'playwright-core']) {
    try { return require(name); } catch (e) { /* next */ }
  }
  const cache = path.join(os.homedir(), '.npm', '_npx');
  for (const dir of fs.existsSync(cache) ? fs.readdirSync(cache) : []) {
    for (const name of ['playwright', 'playwright-core']) {
      const candidate = path.join(cache, dir, 'node_modules', name);
      if (fs.existsSync(path.join(candidate, 'package.json'))) return require(candidate);
    }
  }
  throw new Error('Playwright not found: run `npx -y playwright@1.47.2 install chromium` once');
}

function cachedShell() {
  const bases = [process.env.PLAYWRIGHT_BROWSERS_PATH, path.join(os.homedir(), '.cache', 'ms-playwright'),
    path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright'), path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright')].filter(Boolean);
  for (const base of bases) {
    for (const dir of (fs.existsSync(base) ? fs.readdirSync(base) : []).filter((d) => d.startsWith('chromium')).sort().reverse()) {
      for (const sub of fs.readdirSync(path.join(base, dir))) {
        for (const exe of ['chrome-headless-shell', 'chrome-headless-shell.exe', 'chrome', 'chrome.exe']) {
          const file = path.join(base, dir, sub, exe);
          if (fs.existsSync(file)) return file;
        }
      }
    }
  }
  throw new Error('No Chromium for Playwright: run `npx -y playwright@1.47.2 install chromium` once');
}

async function launch() {
  const { chromium } = loadPlaywright();
  return chromium.launch({ headless: true }).catch(() => chromium.launch({ headless: true, executablePath: cachedShell() }));
}


const argv = process.argv.slice(2);
const urls = [];
let expect = [];
let shots = null;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--expect') expect = String(argv[++i] || '').split(',').map((n) => (n === '' ? null : Number(n)));
  else if (argv[i] === '--shots') shots = argv[++i];
  else urls.push(argv[i]);
}
if (!urls.length || urls.some((url) => !/^https:\/\//.test(url))) {
  console.error('Usage: node render_check.cjs <https page url> [...] [--expect 12,8] [--shots <folder>]');
  process.exit(2);
}
if (shots) fs.mkdirSync(shots, { recursive: true });
const WIDTHS = [[1440, 900], [390, 844]];
const LOAD_FAILURE = /LWR3008|could not be loaded|Something went wrong/i;

// Runs in the page: every element, through open shadow roots, since LWR components render inside them
function inspect() {
  const all = [];
  const walk = (root) => {
    for (const element of root.querySelectorAll('*')) {
      all.push(element);
      if (element.shadowRoot) walk(element.shadowRoot);
    }
  };
  walk(document);
  const ftk = all.filter((element) => element.tagName.toLowerCase().startsWith('flowtoolkit-'));
  const support = ftk.filter((element) => element.tagName.toLowerCase() === 'flowtoolkit-flow-tool-kit-lwr-support');
  const isFtk = (node) => node && node.tagName && node.tagName.toLowerCase().startsWith('flowtoolkit-');
  const parentOf = (node) => node.parentNode instanceof ShadowRoot ? node.parentNode.host : node.parentElement;
  // Top-level components only: a block's own inner Flow Tool Kit parts are not counted again
  const top = ftk.filter((element) => !support.includes(element) && (() => {
    for (let node = parentOf(element); node; node = parentOf(node)) if (isFtk(node)) return false;
    return true;
  })());
  const empty = top.filter((element) => element.getBoundingClientRect().height < 1).map((element) => element.tagName.toLowerCase());
  const text = all.filter((element) => !element.children.length).map((element) => element.textContent || '').join(' ');
  const images = all.filter((element) => element.tagName === 'IMG');
  return {
    inner: window.innerWidth,
    sideways: document.documentElement.scrollWidth - window.innerWidth,
    broken: images.filter((image) => image.complete && image.naturalWidth === 0 && image.currentSrc).map((image) => image.currentSrc.slice(0, 100)),
    login: /\/login(\/|$|\?)|\/s\/login/.test(location.pathname),
    loadFailure: /LWR3008|could not be loaded/i.test(text),
    components: top.length,
    empty,
    support: support.length > 0,
  };
}

(async () => {
  const browser = await launch();
  const rows = [];
  for (const [index, url] of urls.entries()) {
    for (const [width, height] of WIDTHS) {
      const context = await browser.newContext({ viewport: { width, height } });
      const page = await context.newPage();
      const errors = [];
      const failed = [];
      page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text().slice(0, 160)); });
      page.on('pageerror', (error) => errors.push(String(error.message || error).slice(0, 160)));
      page.on('requestfailed', (request) => failed.push(request.url().slice(0, 120)));
      page.on('response', (response) => { if (response.status() >= 400) failed.push(`HTTP ${response.status()} ${response.url().slice(0, 120)}`); });
      let status = 0;
      try { status = (await page.goto(url, { waitUntil: 'load', timeout: 60000 })).status(); } catch (error) { errors.push('goto: ' + error.message.slice(0, 120)); }
      await page.waitForTimeout(3000);
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 200)); }
        window.scrollTo(0, 0);
      }).catch(() => {});
      await page.waitForTimeout(2000);
      const measured = await page.evaluate(inspect).catch(() => ({ inner: 0, sideways: 0, broken: [], login: false, loadFailure: false, components: 0, empty: [], support: false }));
      if (shots) {
        const name = (new URL(url).pathname.replace(/\/+$/, '').split('/').pop() || 'home').replace(/[^\w-]/g, '_');
        await page.screenshot({ path: path.join(shots, `${index + 1}-${name}-${width}.png`), fullPage: true }).catch(() => {});
      }
      const loadFailure = measured.loadFailure || errors.some((text) => LOAD_FAILURE.test(text));
      rows.push({ url, width, status, ...measured, loadFailure, errors, failed, expected: expect[index] ?? null });
      await context.close();
    }
  }
  await browser.close();

  console.log('| page | width asked | width applied | status | sideways scroll (px) | broken images | console errors | failed requests | FTK components | empty | LWR Support | verdict |');
  console.log('|---|---|---|---|---|---|---|---|---|---|---|---|');
  let bad = 0;
  for (const row of rows) {
    const countOk = row.expected === null || row.components === row.expected;
    const ok = row.status === 200 && row.inner === row.width && row.sideways <= 1 && !row.broken.length && !row.errors.length
      && !row.login && !row.loadFailure && !row.empty.length && countOk && (row.components === 0 || row.support);
    if (!ok) bad++;
    const components = row.expected === null ? `${row.components}` : `${row.components} of ${row.expected}`;
    console.log(`| ${row.url} | ${row.width} | ${row.inner} | ${row.status}${row.login ? ' (login page)' : ''} | ${Math.max(0, row.sideways)} | ${row.broken.length} | ${row.errors.length}${row.loadFailure ? ' (load failure)' : ''} | ${row.failed.length} | ${components} | ${row.empty.length} | ${row.support ? 'yes' : 'no'} | ${ok ? 'pass' : 'FAIL'} |`);
  }
  for (const row of rows) {
    for (const text of row.errors) console.log(`- ${row.width}px console: ${text}`);
    for (const text of row.broken) console.log(`- ${row.width}px broken image: ${text}`);
    for (const text of row.failed) console.log(`- ${row.width}px failed request: ${text}`);
    for (const text of row.empty) console.log(`- ${row.width}px empty component: ${text}`);
    if (row.components && !row.support) console.log(`- ${row.width}px FlowToolKit LWR Support is not on the page: put it in the Theme Footer and publish`);
  }
  process.exit(bad ? 1 : 0);
})().catch((error) => { console.error(String(error.message || error)); process.exit(2); });
