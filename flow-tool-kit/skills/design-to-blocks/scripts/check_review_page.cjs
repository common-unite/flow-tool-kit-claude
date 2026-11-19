#!/usr/bin/env node
// Headless check of the self-contained design/review.html at both widths: console errors, unknown components, broken images,
// and a screenshot of every artboard. Works without the canvas runtime. Claude Code only.
// Usage: node check_review_page.cjs <site>/design
const path = require('path');
const fs = require('fs');
const { launch } = require('./playwright.cjs');

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
