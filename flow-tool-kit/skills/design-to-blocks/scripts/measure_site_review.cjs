#!/usr/bin/env node
// Renders each review artboard's component tree with the Site Blocks bundle at its width: height, console errors, broken images.
// Usage: node measure_site_review.cjs <measure.json> <heights.json>   (build_site_review.py writes measure.json and runs this)
// measure.json: {"roots": [kit project folders, searched in order], "boards": [{file, width, tree, fonts, assets: {name: file}}]}
const path = require('path');
const fs = require('fs');
const { launch } = require('./playwright.cjs');

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
