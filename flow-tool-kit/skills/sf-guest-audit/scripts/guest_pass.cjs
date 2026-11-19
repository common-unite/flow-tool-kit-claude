#!/usr/bin/env node
// Live guest pass, logged out: node guest_pass.cjs --plan guest-pass.json --out <folder> [--allow-submit] (references/live-pass.md).
const fs = require('fs');
const os = require('os');
const path = require('path');

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


const DATA_PATH = /\/aura|\/sfsites\/|\/webruntime\/|\/services\/data\/|\/ui-api\/|\/apexrest\/|graphql/i;
const SF_HOST = /(?:\.force\.com|\.salesforce\.com|\.site\.com|\.salesforce-sites\.com)$/i;
const BOT_FRAME = /recaptcha|hcaptcha|challenges\.cloudflare\.com|turnstile|arkoselabs|funcaptcha/i;
const LOGIN_PATH = /\/login(\/|$|\?)|\/secur\/|CommunitiesLogin/i;
const NEXT = /^(next|next page|continue|save (and|&) continue)$/i;
const SUBMIT = /submit|finish|done|pay|donate|register|sign ?up|send|complete|confirm|apply|enrol/i;
const PAYMENT = /card|cvv|cvc|expir|iban|routing|account.?number|cc-/i;
const MAX_BODY = 5 * 1024 * 1024;
const FAKE = {
  email: 'guest.check@example.com', tel: '555-0100', date: '2000-01-01', number: '1', url: 'https://example.com',
  text: 'Guest Check', textarea: 'Test entry from a guest exposure check. Please delete.',
};

function readPlan(argv) {
  const args = { forms: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--plan') args.plan = argv[++i];
    else if (argv[i] === '--out') args.out = argv[++i];
    else if (argv[i] === '--allow-submit') args.allowSubmit = true;
  }
  if (!args.plan || !args.out) throw new Error('Usage: node guest_pass.cjs --plan guest-pass.json --out <folder> [--allow-submit]');
  const plan = JSON.parse(fs.readFileSync(args.plan, 'utf8'));
  return { plan, out: args.out, allowSubmit: !!args.allowSubmit };
}

function expand(plan) {
  if (plan.authorized !== true) {
    throw new Error('the plan must say "authorized": true: run this only against a site you are authorized to test for your client');
  }
  const forms = [];
  for (const form of plan.forms || []) {
    forms.push(form);
    (form.prefill || []).forEach((url, i) => forms.push({ ...form, name: `${form.name} (prefill link ${i + 1})`, url, prefill: [] }));
  }
  for (const form of forms) {
    if (!/^https:\/\//.test(form.url || '')) throw new Error(`not an https address: ${form.url}`);
  }
  return forms;
}

// Runs in the page: visible text and input values, through open shadow roots (LWR components render inside them).
function readScreen() {
  const shown = [];
  const inputs = [];
  const visible = (el) => el && el.checkVisibility && el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
  const walk = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.TEXT_NODE) {
        const value = node.textContent.trim();
        if (value && visible(node.parentElement)) shown.push(value);
      } else {
        if (node.shadowRoot) walk(node.shadowRoot);
        if (/^(INPUT|TEXTAREA|SELECT)$/.test(node.tagName) && visible(node) && node.type !== 'password') {
          const value = node.tagName === 'SELECT' ? (node.selectedOptions[0] || {}).textContent : node.value;
          if (value) inputs.push(String(value).trim());
        }
      }
    }
  };
  walk(document);
  return { shown, inputs, title: document.title };
}

function actionLabels(post) {
  try {
    const message = JSON.parse(new URLSearchParams(post).get('message') || '{}');
    return (message.actions || []).map((action) => {
      const params = action.params || {};
      if (params.classname && params.method) return `Apex ${params.classname}.${params.method}`;
      if (params.flowDevName || params.flowName) return `Flow ${params.flowDevName || params.flowName}`;
      return String(action.descriptor || '').split('/').pop().replace('ACTION$', '');
    }).filter(Boolean);
  } catch (error) { return []; }
}

function fakeFor(type, name) {
  if (type === 'email' || /email/i.test(name)) return FAKE.email;
  if (type === 'tel' || /phone|mobile/i.test(name)) return FAKE.tel;
  if (type === 'date') return FAKE.date;
  if (type === 'number') return FAKE.number;
  if (type === 'url') return FAKE.url;
  return FAKE.text;
}

async function fill(page) {
  let filled = 0;
  for (const field of await page.locator('input, textarea, select').all()) {
    try {
      if (!(await field.isVisible()) || !(await field.isEditable())) continue;
      const info = await field.evaluate((el) => ({
        tag: el.tagName, type: (el.type || '').toLowerCase(), value: el.value,
        name: [el.name, el.id, el.autocomplete, el.getAttribute('aria-label'), el.placeholder].join(' '),
      }));
      if (info.value || PAYMENT.test(info.name)) continue;
      if (['password', 'file', 'hidden', 'checkbox', 'radio', 'submit', 'button', 'search', 'range', 'color'].includes(info.type)) continue;
      if (info.tag === 'SELECT') {
        const options = await field.locator('option').all();
        if (options.length > 1) await field.selectOption({ index: 1 });
      } else {
        await field.fill(info.tag === 'TEXTAREA' ? FAKE.textarea : fakeFor(info.type, info.name));
      }
      filled++;
    } catch (error) { /* a field that will not take a value is skipped */ }
  }
  return filled;
}

async function buttons(page) {
  const found = [];
  for (const button of await page.getByRole('button').all()) {
    try {
      if (!(await button.isVisible())) continue;
      found.push({ button, name: ((await button.textContent()) || (await button.getAttribute('aria-label')) || '').trim() });
    } catch (error) { /* detached */ }
  }
  return found;
}

async function settle(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
}

async function blocked(page) {
  if (LOGIN_PATH.test(new URL(page.url()).pathname)) return 'the page asks for a sign-in; the pass never signs in or works around it';
  if (page.frames().some((frame) => BOT_FRAME.test(frame.url()))) return 'the page has bot protection (a CAPTCHA); the pass never bypasses it';
  return null;
}

async function runForm(browser, form, options) {
  const context = await browser.newContext({ serviceWorkers: 'block', viewport: { width: 1280, height: 900 } });
  if (options.route) await options.route(context);
  const page = await context.newPage();
  const host = new URL(form.url).host;
  const result = { name: form.name, url: form.url, query: Object.fromEntries(new URL(form.url).searchParams),
    steps: [], responses: [], console: [], notes: [], stopped: null };
  const actions = new Map();
  page.on('request', (request) => {
    if (request.method() === 'POST' && DATA_PATH.test(request.url())) actions.set(request, actionLabels(request.postData() || ''));
  });
  page.on('response', async (response) => {
    const url = new URL(response.url());
    const type = (response.headers()['content-type'] || '').toLowerCase();
    const kind = response.request().resourceType();
    if (!(url.host === host || SF_HOST.test(url.host))) return;
    if (!(kind === 'document' || kind === 'xhr' || kind === 'fetch')) return;
    if (!(DATA_PATH.test(url.pathname) || /json/.test(type) || kind === 'document')) return;
    let body = '';
    try { body = await response.text(); } catch (error) { return; }
    result.responses.push({ url: response.url(), status: response.status(), contentType: type, kind,
      actions: actions.get(response.request()) || [], body: body.slice(0, MAX_BODY), truncated: body.length > MAX_BODY });
  });
  page.on('console', (message) => { if (result.console.length < 200) result.console.push({ type: message.type(), text: message.text().slice(0, 300) }); });
  page.on('pageerror', (error) => result.console.push({ type: 'error', text: String(error.message || error).slice(0, 300) }));

  const step = async (label) => result.steps.push({ label, url: page.url(), ...(await page.evaluate(readScreen).catch(() => ({ shown: [], inputs: [] }))) });
  try {
    await page.goto(form.url, { waitUntil: 'load', timeout: 60000 });
  } catch (error) {
    result.stopped = `could not open the page: ${String(error.message).slice(0, 120)}`;
  }
  if (!result.stopped) {
    await settle(page);
    result.stopped = await blocked(page);
    await step('opened');
  }
  const pages = Number.isInteger(form.advance) ? form.advance : 0;
  for (let i = 0; !result.stopped && i <= pages; i++) {
    if (form.fill) {
      const count = await fill(page);
      if (count) await step(`filled ${count} field(s) with fake data`);
    }
    const found = await buttons(page);
    const next = found.find((b) => NEXT.test(b.name));
    const submit = found.find((b) => SUBMIT.test(b.name));
    if (next && i < pages) {
      await next.button.click().catch(() => {});
      await settle(page);
      result.stopped = await blocked(page);
      await step(`after ${next.name}`);
      continue;
    }
    if (submit && !next) {
      if (form.submit === true && options.allowSubmit) {
        await submit.button.click().catch(() => {});
        await settle(page);
        await step(`after ${submit.name}`);
        result.notes.push(`submitted with fake data (${submit.name}), as the plan and --allow-submit asked`);
      } else {
        result.stopped = `stopped at the last page without pressing ${submit.name}`;
      }
    }
    break;
  }
  if (!result.stopped && !result.notes.length) result.notes.push('pass finished');
  await context.close();
  return result;
}

async function runPass(plan, options = {}) {
  const forms = expand(plan);
  const browser = await (options.launch || launch)();
  const capture = { tool: 'guest_pass', version: 1, started: new Date().toISOString(), sandbox: plan.sandbox === true, forms: [] };
  try {
    for (const form of forms) capture.forms.push(await runForm(browser, form, options));
  } finally {
    await browser.close();
  }
  return capture;
}

if (require.main === module) {
  (async () => {
    let args;
    try { args = readPlan(process.argv.slice(2)); expand(args.plan); } catch (error) { console.error(String(error.message)); process.exit(2); }
    const capture = await runPass(args.plan, { allowSubmit: args.allowSubmit });
    fs.mkdirSync(args.out, { recursive: true });
    const file = path.join(args.out, 'capture.json');
    fs.writeFileSync(file, JSON.stringify(capture, null, 1));
    console.log(`capture: ${file}`);
    for (const form of capture.forms) {
      console.log(`  ${form.name}: ${form.steps.length} step(s), ${form.responses.length} response(s) kept${form.stopped ? `; ${form.stopped}` : ''}`);
    }
    console.log('Next: python3 scripts/exposure.py analyze ' + file + ' --out ' + args.out);
  })().catch((error) => { console.error(error); process.exit(1); });
}

module.exports = { runPass, expand, launch };
