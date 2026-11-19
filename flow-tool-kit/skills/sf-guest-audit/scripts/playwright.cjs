// Find Playwright and a headless Chromium on any computer or cloud session (Linux, macOS, Windows).
// Install once: npx -y playwright@1.47.2 install chromium   (on Claude Code on the web, allow the npm registry first)
const fs = require('fs');
const os = require('os');
const path = require('path');

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

module.exports = { launch };
