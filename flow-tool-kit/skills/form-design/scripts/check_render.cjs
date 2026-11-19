#!/usr/bin/env node
// Headless render check of design/review.html: node check_render.cjs <design folder> [--write-heights] (usage: references/drawing.md, Publishing the canvas).
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
  throw new Error("Playwright not found: run `npx -y playwright@1.47.2 install chromium` once");
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
  throw new Error("No Chromium for Playwright: run `npx -y playwright@1.47.2 install chromium-headless-shell` once");
}

(async () => {
  const design = path.resolve(process.argv[2] || "design");
  const writeHeights = process.argv.includes("--write-heights");
  const page = path.join(design, "review.html");
  if (!fs.existsSync(page)) { console.error(`${page} not found: run draw_plan.py first`); process.exit(2); }
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true }).catch(() => chromium.launch({ headless: true, executablePath: cachedShell() }));
  const tab = await browser.newPage({ viewport: { width: 2300, height: 1200 }, deviceScaleFactor: 1 });
  const errors = [];
  tab.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  tab.on("pageerror", (e) => errors.push(String(e)));
  await tab.goto("file://" + page, { waitUntil: "load" });
  await tab.waitForTimeout(1500);
  const boards = await tab.evaluate(() => Array.from(document.querySelectorAll("[data-board]")).map((sec) => {
    const root = sec.querySelector(".fd-root > *");
    const declared = parseInt((sec.querySelector("h2").textContent.match(/x (\d+)\)$/) || [])[1] || "0", 10);
    let frame = root;
    while (frame && !(frame.style && frame.style.minHeight)) frame = frame.firstElementChild;
    if (frame) frame.style.minHeight = "0px";
    const measured = root ? Math.ceil(root.getBoundingClientRect().height) : 0;
    if (frame) frame.style.minHeight = declared + "px";
    const unknown = Array.from(sec.querySelectorAll("div")).filter((d) => /^Unknown component /.test(d.textContent)).map((d) => d.textContent);
    return { name: sec.getAttribute("data-board"), declared, measured, unknown };
  }));
  fs.mkdirSync(path.join(design, "render"), { recursive: true });
  const sections = await tab.$$("[data-board]");
  for (let i = 0; i < sections.length; i++) {
    const root = await sections[i].$(".fd-root");
    await root.screenshot({ path: path.join(design, "render", boards[i].name.replace(/\.dc\.html$/, ".png")) });
  }
  await browser.close();
  const heightsPath = path.join(design, "measured-heights.json");
  const heights = fs.existsSync(heightsPath) ? JSON.parse(fs.readFileSync(heightsPath, "utf8")) : {};
  let problems = errors.length;
  for (const b of boards) {
    const want = Math.ceil((b.measured + 40) / 20) * 20;
    b.status = b.unknown.length ? "unknown component" : b.measured > b.declared ? "content taller than its frame" : b.measured < b.declared * 0.6 ? "loose: frame much taller than its content" : "ok";
    if (b.status !== "ok" && !b.status.startsWith("loose")) problems += 1;
    if (writeHeights && (b.measured > b.declared || b.measured < b.declared * 0.6)) heights[b.name] = Math.min(8000, want);
    console.log(`${b.status === "ok" ? "ok  " : b.status.startsWith("loose") ? "note" : "FIX "} ${b.name}: frame ${b.declared}px, content ${b.measured}px${b.status === "ok" ? "" : " (" + b.status + ")"}`);
  }
  if (writeHeights) fs.writeFileSync(heightsPath, JSON.stringify(heights, null, 1) + "\n");
  fs.writeFileSync(path.join(design, "render-check.json"), JSON.stringify({ boards, errors }, null, 1) + "\n");
  errors.forEach((e) => console.log(`console error: ${e}`));
  console.log(`${boards.length} boards, ${problems} problem(s). Screenshots in ${path.join(design, "render")}: look at each one.`);
  process.exit(problems ? 1 : 0);
})();
