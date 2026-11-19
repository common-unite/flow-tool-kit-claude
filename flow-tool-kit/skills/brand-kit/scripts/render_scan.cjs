#!/usr/bin/env node
// Headless run of site-scan.js on one page (usage and setup: references/site-scan.md); it reads, never clicks or submits.
const fs = require("fs");
const os = require("os");
const path = require("path");

function loadPlaywright() {
  try { return require("playwright"); } catch (e) { /* fall through */ }
  const cache = path.join(os.homedir(), ".npm", "_npx");
  for (const dir of fs.existsSync(cache) ? fs.readdirSync(cache) : []) {
    const candidate = path.join(cache, dir, "node_modules", "playwright");
    if (fs.existsSync(path.join(candidate, "package.json"))) return require(candidate);
  }
  throw new Error("Playwright not found: run `npx -y playwright@1.47.2 install chromium-headless-shell` once");
}

function cachedShell() {
  for (const base of [path.join(os.homedir(), ".cache", "ms-playwright"), path.join(os.homedir(), "Library", "Caches", "ms-playwright")]) {
    for (const dir of (fs.existsSync(base) ? fs.readdirSync(base) : []).filter((d) => d.startsWith("chromium_headless_shell")).sort().reverse()) {
      for (const sub of fs.readdirSync(path.join(base, dir))) {
        const exe = path.join(base, dir, sub, "chrome-headless-shell");
        if (fs.existsSync(exe)) return exe;
      }
    }
  }
  return undefined;
}

(async () => {
  const [address, out] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  const widthAt = process.argv.indexOf("--width");
  const width = widthAt > 0 ? Number(process.argv[widthAt + 1]) : 1280;
  if (!address || !out) { console.error("usage: node render_scan.cjs <page address> <out.json> [--width 1280]"); process.exit(2); }
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true }).catch(() => chromium.launch({ headless: true, executablePath: cachedShell() }));
  try {
    const tab = await browser.newPage({ viewport: { width, height: 900 } });
    await tab.goto(address, { waitUntil: "load", timeout: 60000 });
    const script = fs.readFileSync(path.join(__dirname, "site-scan.js"), "utf8");
    await tab.evaluate(script);
    const scan = await tab.evaluate(() => window.__scan);
    scan.from = "rendered page";
    fs.writeFileSync(out, JSON.stringify(scan, null, 1));
    console.log(`${out}: ${scan.colors.length} colors, ${scan.images.length} images, fonts ${scan.fonts.body} / ${scan.fonts.heading}`);
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(String(error.message || error)); process.exit(1); });
