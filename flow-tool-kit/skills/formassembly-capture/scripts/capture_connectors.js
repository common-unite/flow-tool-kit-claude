// Browser step, only after the person agreed and signed in: saves the Salesforce connector pages of the listed forms. Usage: ../references/getting-the-forms.md.
async (page) => {
  const config = await page.evaluate(() => {
    try { return JSON.parse(localStorage.getItem('faCaptureConfig') || '{}'); } catch (error) { return {}; }
  });
  if (!config.formIds || !config.formIds.length) return 'NO_FORMS: in the signed-in FormAssembly tab, set faCaptureConfig.formIds to the forms verify.py listed, then run again';
  const FORMS_URL = (config.host || 'https://app.formassembly.com').replace(/\/$/, '') + '/forms';
  await page.goto(FORMS_URL);
  if (!page.url().startsWith(FORMS_URL)) return 'SIGN_IN_REQUIRED: the person signs in at ' + page.url() + ' in this browser window, then run again';
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outPath = (config.outDir || '_formassembly/raw') + '/connectors-' + stamp + '.json';

  const pageCapture = async (config) => {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const problems = [];

    // FormAssembly's error page answers 200 and its scripts mention the error text, so only the title counts.
    const get = async (url) => {
      let last = { ok: false, status: 0, text: '' };
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const response = await fetch(url, { credentials: 'include' });
          const text = await response.text();
          last = { ok: response.ok && !/<title>[^<]*Something went wrong/i.test(text), status: response.status, text };
          if (last.ok) return last;
        } catch (error) { last = { ok: false, status: 0, text: String(error) }; }
        await sleep(1500 * (attempt + 1));
      }
      return last;
    };

    // Prefill setup pages print the secure-parameter secret key: blank it before saving.
    const blankSecrets = (html) => html.replace(/(Your Secret Key:?\s*(?:<[^>]*>\s*)*)[0-9a-f]{20,}/gi, '$1[REDACTED]');
    const snake = (name) => name.replace(/^Connector/, '').replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();

    // The connector list per form, from the JSON embedded in the connectors page.
    const forms = {};
    for (const formId of config.formIds.map(String)) {
      const index = await get('/connectors/index/' + formId);
      forms[formId] = [];
      if (!index.ok) { problems.push(`${formId}: connectors page failed (${index.status})`); continue; }
      for (const match of index.text.matchAll(/"Connector":\{"id":"(\d+)"(.*?)\}/g)) {
        const body = match[2];
        forms[formId].push({
          id: match[1],
          type: snake((body.match(/"name":"(\w+)"/) || [])[1] || ''),
          enabled: (body.match(/"status":"(\d)"/) || [])[1] === '1',
          event: (index.text.slice(match.index, match.index + 600).match(/"event":"(\w+)"/) || [])[1] || '',
          listed_by: 'browser',
        });
      }
    }

    // A setup page loads each object's mappings only when opened: render it in a frame and open every object.
    const renderConnector = (connector) => new Promise((resolve) => {
      const frame = document.createElement('iframe');
      frame.style.cssText = 'width:1400px;height:900px;position:fixed;left:-3000px;top:0';
      frame.src = `/connector_${connector.type}/setup/${connector.id}`;
      const finish = (html, stat) => { frame.remove(); resolve({ html, stat }); };
      const timer = setTimeout(() => finish('', { error: 'timeout' }), 180000);
      frame.onload = async () => {
        let doc; let form;
        for (let i = 0; i < 120; i++) {
          doc = frame.contentDocument;
          form = doc && doc.querySelector('#connectorSetupForm');
          if (form && (doc.querySelector('.collapsable-heading') || i > 20)) break;
          await sleep(500);
        }
        if (!form) { clearTimeout(timer); return finish('', { error: 'no setup form' }); }
        let passes = 0;
        for (; passes < 12; passes++) {
          const closed = [...doc.querySelectorAll('.collapsed .collapsable-heading')];
          if (!closed.length) break;
          closed.forEach((heading) => heading.click());
          await sleep(3000);
        }
        await sleep(1500);
        const stat = {
          objects: doc.querySelectorAll('.sobject').length,
          collapsed: doc.querySelectorAll('.sobject.collapsed').length,
          mappingTables: doc.querySelectorAll('.field-mapping-table').length,
          expandPasses: passes,
        };
        const clone = form.cloneNode(true);
        clone.querySelectorAll('select').forEach((select) => {
          const value = select.value;
          [...select.options].forEach((option) => { if (option.value !== value) option.remove(); });
        });
        clone.querySelectorAll('textarea').forEach((area) => { area.textContent = area.value; });
        clone.querySelectorAll('input').forEach((input) => { input.setAttribute('value', input.value); if (input.checked) input.setAttribute('checked', 'checked'); });
        clone.querySelectorAll('script,style,svg').forEach((element) => element.remove());
        clearTimeout(timer);
        finish(blankSecrets(clone.outerHTML), stat);
      };
      document.body.appendChild(frame);
    });

    const files = {};
    const stats = {};
    const queue = Object.keys(forms);
    await Promise.all([0, 1, 2].map(async () => {
      while (queue.length) {
        const formId = queue.shift();
        stats[formId] = { connectors: {} };
        for (const connector of forms[formId].filter((c) => /^salesforce/.test(c.type))) {
          const result = await renderConnector(connector);
          files[`${formId}/connector-${connector.type}-${connector.id}.html`] = result.html;
          stats[formId].connectors[connector.id] = { type: connector.type, bytes: result.html.length, ...result.stat };
        }
      }
    }));

    const bundle = { kind: 'connectors', capturedAt: new Date().toISOString(), account: location.host, forms, stats, files, problems };
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(new Blob([JSON.stringify(bundle)], { type: 'application/json' }));
    anchor.download = 'formassembly-connectors.json';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    return { forms: Object.keys(forms).length, connectors: Object.values(stats).reduce((n, s) => n + Object.keys(s.connectors).length, 0), problems };
  };

  const download = page.waitForEvent('download', { timeout: 0 });
  const summary = await page.evaluate(pageCapture, config);
  const file = await download;
  await file.saveAs(outPath);
  return JSON.stringify({ saved: outPath, ...summary });
}
