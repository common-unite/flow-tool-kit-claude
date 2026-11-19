#!/usr/bin/env node
// Plays every artboard of the review canvas the way the canvas will, and screenshots each one. Claude Code only.
// Usage: node check_site_review.cjs <site>/design <dc-runtime.js> <screenshot folder> [--kit <site-blocks kit>]
//   dc-runtime.js: the canvas's own runtime, read once from the canvas (Artifact read, path artifact-type/dc-runtime.js).
// Files come from design/project; the design system's code from design/project/ds/sb (chat mode) or the kit (code mode, where
// the canvas copies it server side); images only from uploads (/_blob/) recorded in site.json assets. Fails an artboard with
// console errors, missing files, broken images, an image that is not an upload, unresolved components or clipped content.
const path = require('path');
const fs = require('fs');
const { launch } = require('./playwright.cjs');

const args = process.argv.slice(2);
const kitAt = args.indexOf('--kit');
// The full kit is a release asset; ftk-start unpacks it at $FTK_DESIGN_SYSTEMS_DIR or ~/.flow-tool-kit/design-systems
const kitArg = kitAt >= 0 ? args.splice(kitAt, 2)[1]
  : path.join(process.env.FTK_DESIGN_SYSTEMS_DIR || path.join(require('os').homedir(), '.flow-tool-kit', 'design-systems'), 'site-blocks');
const [designArg, runtimeArg, shotsArg] = args;
if (!designArg || !runtimeArg || !shotsArg) { console.error('usage: node check_site_review.cjs <design folder> <dc-runtime.js> <screenshot folder> [--kit DIR]'); process.exit(2); }
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
