#!/usr/bin/env node
// The design review's browser checks, one file with three commands. Claude Code only.
//   node site_review.cjs check <site>/design                                  the self-contained review.html at both widths
//   node site_review.cjs site <site>/design <dc-runtime.js> <screenshot folder> [--kit DIR]   every artboard as the canvas plays it
//   node site_review.cjs measure <measure.json> <heights.json>                each artboard's tree with the kit bundle (build_site_review.py runs it)
// Required as a module it exports launch(), how it finds Playwright and a headless Chromium, and kitsRoot(), where the kits are.
const fs = require('fs');
const os = require('os');
const path = require('path');

// ---------- launch: find Playwright and a headless Chromium ----------
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


// ---------- check: the self-contained design/review.html ----------
function checkReviewPage() {
  // Headless check of the self-contained design/review.html at both widths: console errors, unknown components, broken images,
  // and a screenshot of every artboard. Works without the canvas runtime. Claude Code only.
  // Usage: node site_review.cjs check <site>/design

  (async () => {
    const design = path.resolve(process.argv[2] || 'design');
    const page = path.join(design, 'review.html');
    if (!fs.existsSync(page)) { console.error(`${page} not found: run build_site_review.py first`); process.exit(2); }
    const browser = await launch();
    const shots = path.join(design, 'render');
    fs.mkdirSync(shots, { recursive: true });
    let problems = 0;
    for (const width of [1280, 390]) {
      const tab = await browser.newPage({ viewport: { width: Math.max(width + 64, 900), height: 1000 } });
      const errors = [];
      tab.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
      tab.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text().slice(0, 200)); });
      await tab.goto('file://' + page + '#w=' + width, { waitUntil: 'load' });
      await tab.waitForTimeout(2500);
      const boards = await tab.evaluate(() => [...document.querySelectorAll('[data-board]')].map((sec) => ({
        name: sec.getAttribute('data-board'),
        unknown: [...sec.querySelectorAll('div')].filter((d) => /^Unknown component /.test(d.textContent)).length,
        broken: [...sec.querySelectorAll('img')].filter((i) => i.complete && i.naturalWidth === 0).map((i) => (i.getAttribute('src') || '').slice(0, 60)),
        height: Math.ceil(sec.getBoundingClientRect().height),
      })));
      const frames = await tab.$$('[data-board] .sr-frame');
      for (let i = 0; i < frames.length; i++) {
        await frames[i].screenshot({ path: path.join(shots, `${width}-${boards[i].name.replace(/\.dc\.html$/, '')}.png`) });
      }
      for (const b of boards) {
        const bad = b.unknown || b.broken.length;
        if (bad) problems++;
        console.log(`${bad ? 'FIX ' : 'ok  '}${width} ${b.name}: ${b.height}px${b.unknown ? `, ${b.unknown} unknown components` : ''}${b.broken.length ? `, broken images ${b.broken.join(' ')}` : ''}`);
      }
      errors.forEach((e) => console.log(`console error at ${width}: ${e}`));
      problems += errors.length;
      await tab.close();
    }
    await browser.close();
    console.log(`${problems} problem(s). Screenshots in ${shots}: look at each one.`);
    process.exit(problems ? 1 : 0);
  })().catch((e) => { console.error(e.stack || String(e)); process.exit(2); });
}

// ---------- site: the canvas as it will play ----------
// The kits ship in the plugin's ftk-design-system skill, beside this one as ftk-design-system/ or, where claude.ai mounts each
// skill alone, <plugin>:ftk-design-system/ (the same rule as _shared/lib/siblings.py). $FTK_DESIGN_SYSTEMS_DIR overrides it.
function kitsRoot() {
  if (process.env.FTK_DESIGN_SYSTEMS_DIR) return process.env.FTK_DESIGN_SYSTEMS_DIR;
  const skill = path.dirname(__dirname);
  const parent = path.dirname(skill);
  const own = path.basename(skill).includes(':') ? path.basename(skill).slice(0, path.basename(skill).lastIndexOf(':')) : null;
  const name = 'ftk-design-system';
  const found = (fs.existsSync(parent) ? fs.readdirSync(parent) : [])
    .filter((e) => e === name || (e.includes(':') && e.slice(e.lastIndexOf(':') + 1) === name))
    .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  function rank(e) { return own !== null && e.slice(0, e.lastIndexOf(':')) === own ? 0 : e === name ? 1 : 2; }
  return path.join(parent, found[0] || name);
}

function checkSiteReview() {
  // Plays every artboard of the review canvas the way the canvas will, and screenshots each one. Claude Code only.
  // Usage: node site_review.cjs site <site>/design <dc-runtime.js> <screenshot folder> [--kit <site-blocks kit>]
  //   dc-runtime.js: the canvas's own runtime, read once from the canvas (Artifact read, path artifact-type/dc-runtime.js).
  // Files come from design/project; the design system's code from design/project/ds/sb (chat mode) or the kit (code mode, where
  // the canvas copies it server side); images only from uploads (/_blob/) recorded in site.json assets. Fails an artboard with
  // console errors, missing files, broken images, an image that is not an upload, unresolved components or clipped content.

  const args = process.argv.slice(2);
  const kitAt = args.indexOf('--kit');
  const kitArg = kitAt >= 0 ? args.splice(kitAt, 2)[1] : path.join(kitsRoot(), 'site-blocks');
  const [designArg, runtimeArg, shotsArg] = args;
  if (!designArg || !runtimeArg || !shotsArg) { console.error('usage: node site_review.cjs site <design folder> <dc-runtime.js> <screenshot folder> [--kit DIR]'); process.exit(2); }
  const design = path.resolve(designArg);
  const project = path.join(design, 'project');
  const kitRoots = [path.join(path.resolve(kitArg), 'project'), path.join(path.resolve(kitArg), '..', 'ftk-forms', 'project')];
  const ORIGIN = 'http://canvas.local/';
  const batchesFile = path.join(design, 'publish-batches.json');
  const published = new Set();
  if (fs.existsSync(batchesFile)) for (const batch of JSON.parse(fs.readFileSync(batchesFile, 'utf8')).batches || []) for (const [k, v] of Object.entries(batch)) if (v !== null) published.add(k);
  const siteFile = path.join(design, '..', 'site.json');
  const blobs = {};
  if (fs.existsSync(siteFile)) {
    for (const [name, entry] of Object.entries(JSON.parse(fs.readFileSync(siteFile, 'utf8')).assets || {})) {
      if (!entry.blob) continue;
      const own = entry.file ? path.resolve(path.dirname(siteFile), entry.file) : null;
      blobs[entry.blob] = own && fs.existsSync(own) ? own : name;
    }
  }
  const ASSET_GROUPS = [[/^Background_/, 'Backgrounds', '.jpg'], [/^People_/, 'People', '.jpg'], [/_Bear_\d+$/, 'Bears', '.png']];
  const TYPES = { '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.json': 'application/json', '.html': 'text/html' };

  function inKit(rel) {
    for (const root of kitRoots) { const file = path.join(root, rel); if (file.startsWith(root) && fs.existsSync(file)) return file; }
    return null;
  }

  function blobFile(urlPath) {
    const target = blobs[urlPath];
    if (!target) return null;
    if (path.isAbsolute(target)) return target;
    if (target.startsWith('resource:')) return inKit('assets/resources/' + target.slice(9));
    for (const [rx, folder, ext] of ASSET_GROUPS) if (rx.test(target)) return inKit(`assets/${folder}/${target}${ext}`);
    return inKit(`assets/Logos/${target}.png`);
  }

  function resolve(urlPath) {
    if (urlPath === '/support.js') return path.resolve(runtimeArg);
    if (urlPath.startsWith('/_blob/')) return blobFile(urlPath);
    const local = path.join(project, urlPath);
    if (local.startsWith(project) && fs.existsSync(local)) return local;
    const ds = urlPath.match(/^\/ds\/sb\/(.+)$/);
    // Serve a design-system file only when the publish copies it to the canvas, so an image the canvas will not have shows here as missing
    if (ds && published.size && !published.has('project' + urlPath)) return null;
    return ds ? inKit(ds[1]) : null;
  }

  (async () => {
    const canvas = JSON.parse(fs.readFileSync(path.join(project, 'canvas.json'), 'utf8'));
    const heightsFile = path.join(design, 'heights.json');
    const kitRender = fs.existsSync(heightsFile) ? JSON.parse(fs.readFileSync(heightsFile, 'utf8')) : {};
    fs.mkdirSync(shotsArg, { recursive: true });
    const browser = await launch();
    let failed = 0;
    for (const file of canvas.order) {
      const frame = canvas.boards[file];
      const tab = await browser.newPage({ viewport: { width: frame.w, height: Math.min(frame.h, 4000) } });
      const errors = [];
      const missing = [];
      const notUploaded = new Set();
      tab.on('pageerror', (e) => errors.push(e.message.slice(0, 160)));
      tab.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text().slice(0, 160)); });
      await tab.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (url.origin + '/' !== ORIGIN) return route.continue();
        const urlPath = decodeURIComponent(url.pathname);
        // Served here from disk, but never on the live canvas: an image that is not an upload draws broken there
        if (route.request().resourceType() === 'image' && !urlPath.startsWith('/_blob/')) notUploaded.add(urlPath);
        const local = resolve(urlPath);
        if (!local) { missing.push(urlPath); return route.fulfill({ status: 404, body: '' }); }
        return route.fulfill({ contentType: TYPES[path.extname(local)] || 'application/octet-stream', body: fs.readFileSync(local) });
      });
      await tab.goto(ORIGIN + file, { waitUntil: 'load' });
      await tab.waitForTimeout(2000);
      const v = await tab.evaluate(() => ({
        height: Math.ceil(document.documentElement.scrollHeight),
        sections: document.querySelectorAll('[data-section-id]').length,
        sectionHeights: Object.fromEntries([...document.querySelectorAll('[data-section-id]')].map((s) => [s.getAttribute('data-section-id'), Math.ceil(s.getBoundingClientRect().height)])),
        blocks: document.querySelectorAll('[data-section-type]').length,
        placeholders: [...document.querySelectorAll('[data-dc-placeholder], .dc-placeholder')].length,
        broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')),
        notUploaded: [...document.images].map((i) => i.getAttribute('src') || '').filter((src) => {
          if (src.startsWith('data:')) return false;
          const url = new URL(src || 'about:blank', document.baseURI);
          return url.origin === location.origin ? !url.pathname.startsWith('/_blob/') : !/^https?:$/.test(url.protocol);
        }),
        text: (document.body.innerText || '').trim().length,
      }));
      await tab.screenshot({ path: path.join(shotsArg, file.replace(/\.dc\.html$/, '.png')), fullPage: true });
      const clipped = v.height > frame.h + 4;
      const expected = (kitRender[file] || {}).sections || {};
      const drift = Object.keys(expected).filter((id) => Math.abs((v.sectionHeights[id] || 0) - expected[id]) > 4).map((id) => `${id} ${v.sectionHeights[id] || 0} vs ${expected[id]}`);
      v.notUploaded.forEach((src) => notUploaded.add(src || '(empty src)'));
      const bad = errors.length || missing.length || v.broken.length || notUploaded.size || v.placeholders || clipped || !v.text || drift.length;
      if (bad) failed++;
      console.log(`${bad ? 'FIX ' : 'ok  '}${file} ${frame.w}x${frame.h}: content ${v.height}px${clipped ? ' (CLIPPED)' : ''}, sections ${v.sections}, blocks ${v.blocks}`
        + (Object.keys(expected).length ? (drift.length ? `, differs from the kit render: ${drift.join(', ')}` : ', matches the kit render') : '')
        + (errors.length ? `, errors: ${errors.slice(0, 3).join(' | ')}` : '') + (missing.length ? `, missing: ${missing.slice(0, 4).join(' ')}` : '')
        + (v.broken.length ? `, broken images: ${v.broken.slice(0, 3).join(' ')}` : '')
        + (notUploaded.size ? `, images not uploaded to the canvas (design/uploads.json): ${[...notUploaded].slice(0, 4).join(' ')}` : '') + (v.placeholders ? `, unresolved x-imports ${v.placeholders}` : ''));
      await tab.close();
    }
    await browser.close();
    console.log(`${canvas.order.length} artboards, ${failed} to fix. Screenshots in ${path.resolve(shotsArg)}: look at each one.`);
    process.exit(failed ? 1 : 0);
  })().catch((e) => { console.error(e.stack || String(e)); process.exit(2); });
}

// ---------- measure: each artboard rendered with the kit bundle ----------
function measureSiteReview() {
  // Renders each review artboard's component tree with the Site Blocks bundle at its width: height, console errors, broken images.
  // Usage: node site_review.cjs measure <measure.json> <heights.json>   (build_site_review.py writes measure.json and runs this)
  // measure.json: {"roots": [kit project folders, searched in order], "boards": [{file, width, tree, fonts, assets: {name: file}}]}

  const [inFile, outFile] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(inFile, 'utf8'));
  const roots = job.roots.map((r) => path.resolve(r));
  const ORIGIN = 'http://site-review.local/';
  const TYPES = { '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.json': 'application/json' };

  function find(rel) {
    for (const root of roots) {
      const file = path.join(root, rel);
      if (file.startsWith(root) && fs.existsSync(file) && fs.statSync(file).isFile()) return file;
    }
    return null;
  }

  function tokensCss() {
    const tokens = JSON.parse(fs.readFileSync(find('tokens.json'), 'utf8'));
    const lines = ((tokens.color || {}).tokens || []).map((t) => `--${t.name}: ${typeof t.value === 'object' ? t.value.light : t.value};`);
    for (const family of ['spacing', 'radius', 'sizing', 'shadow']) for (const t of ((tokens[family] || {}).tokens || [])) lines.push(`--${t.name}: ${t.value};`);
    return (':root{' + lines.join('') + '}').replace(/\{([A-Za-z0-9_.-]+)\}/g, 'var(--$1)');
  }

  const LIBRARIES = ['components/lib/react.production.min.js', 'components/lib/react-dom.production.min.js', 'components/lib/slds-icons-2.30.7.js', 'components/lib/ftk-illustrations.js'];

  function page(board) {
    const client = Object.fromEntries(Object.keys(board.assets || {}).map((name) => [name, ORIGIN + 'client/' + encodeURIComponent(name)]));
    return `<!doctype html><html><head><meta charset="utf-8"><style>${tokensCss()} body{margin:0;background:#fff}</style>`
      + (board.fonts ? `<link rel="stylesheet" href="${board.fonts}">` : '')
      + `<link rel="stylesheet" href="${ORIGIN}components/bundle.css">`
      + LIBRARIES.map((l) => `<script src="${ORIGIN}${l}"></script>`).join('')
      + `<script>window.SB = { assetBase: ${JSON.stringify(ORIGIN)} };</script><script src="${ORIGIN}components/bundle.js"></script>`
      + `<script>(function(){var c=${JSON.stringify(client)},b=SB.assetUrl;SB.assetUrl=function(n){var k=String(n||'').replace(/^FlowToolKit__/,'');return c[k]||c[n]||b(n)};window.SiteBlocksAssetUrl=SB.assetUrl;})();SB.previewAt(${board.width});</script>`
      + `</head><body><div id="root"></div><script>
        var h = React.createElement;
        function el(n) {
          if (n.c === 'div') { return h.apply(null, ['div', Object.assign({}, n.p)].concat((n.k || []).map(el))); }
          var C = n.c.split('.').slice(1).reduce(function (o, k) { return o && o[k]; }, window.SB);
          if (!C) throw new Error('No component ' + n.c);
          return h.apply(null, [C, n.p].concat((n.k || []).map(el)));
        }
        ReactDOM.createRoot(document.getElementById('root')).render(el(${JSON.stringify(board.tree).replace(/</g, '\\u003c')}));
      </script></body></html>`;
  }

  (async () => {
    const browser = await launch();
    const out = {};
    for (const board of job.boards) {
      const tab = await browser.newPage({ viewport: { width: board.width, height: 900 } });
      const errors = [];
      const broken = [];
      tab.on('pageerror', (e) => errors.push(e.message));
      // a failed load is reported once, below, as a broken file; the console's own line for it is noise
      tab.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text().slice(0, 200)); });
      await tab.route('**/*', (route) => {
        const url = new URL(route.request().url());
        if (url.origin + '/' !== ORIGIN) return route.continue();  // web fonts; when the network is closed, the fallback font is measured
        if (url.pathname === '/board') return route.fulfill({ contentType: 'text/html', body: page(board) });
        const name = url.pathname.startsWith('/client/') ? decodeURIComponent(url.pathname.slice(8)) : null;
        const file = name ? (board.assets || {})[name] : find(decodeURIComponent(url.pathname).replace(/^\/+/, ''));
        if (!file || !fs.existsSync(file)) { broken.push(decodeURIComponent(url.pathname)); return route.fulfill({ status: 404, body: '' }); }
        return route.fulfill({ contentType: TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', body: fs.readFileSync(file) });
      });
      await tab.goto(ORIGIN + 'board', { waitUntil: 'load' });
      await tab.waitForTimeout(1500);
      const result = await tab.evaluate(() => {
        const root = document.getElementById('root');
        const sections = {};
        document.querySelectorAll('[data-section-id]').forEach((s) => { sections[s.getAttribute('data-section-id')] = Math.ceil(s.getBoundingClientRect().height); });
        const images = [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src'));
        return { height: Math.ceil(root.scrollHeight), sections, images };
      });
      out[board.file] = { height: result.height, sections: result.sections, errors, broken: [...new Set(broken.concat(result.images))] };
      await tab.close();
    }
    await browser.close();
    fs.writeFileSync(outFile, JSON.stringify(out, null, 1) + '\n');
    const bad = Object.values(out).some((b) => b.errors.length || b.broken.length);
    console.log(Object.entries(out).map(([f, b]) => `${f} ${b.height}px${b.errors.length ? ' errors ' + b.errors.length : ''}${b.broken.length ? ' broken ' + b.broken.length : ''}`).join('\n'));
    process.exit(bad ? 1 : 0);
  })().catch((e) => { console.error(e.stack || String(e)); process.exit(2); });
}

const COMMANDS = { check: checkReviewPage, site: checkSiteReview, measure: measureSiteReview };

if (require.main === module) {
  const command = COMMANDS[process.argv[2]];
  if (!command) {
    console.error('usage: node site_review.cjs check|site|measure ... (see the comment at the top of this file)');
    process.exit(2);
  }
  // each command reads its own arguments from process.argv, as when it was a script of its own
  process.argv.splice(2, 1);
  command();
}

module.exports = { launch, kitsRoot };
