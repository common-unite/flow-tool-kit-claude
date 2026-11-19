// Rendered-page colors, fonts and images (usage: references/site-scan.md); URLs lose query strings because some browser tools hide them.
(async () => {
  const abs = u => { try { const x = new URL(u, location.href); return x.protocol.startsWith('http') ? x.origin + x.pathname : null } catch (e) { return null } };
  for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)) }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 600));
  const images = new Map();
  const addImage = (url, kind, extra = {}) => { const u = abs(url); if (!u) return; if (!images.has(u)) images.set(u, { url: u, kind, ...extra }) };
  document.querySelectorAll('img').forEach(i => {
    const best = (i.srcset || '').split(',').map(s => s.trim().split(/\s+/)).filter(p => p[0]).sort((a, b) => parseInt(b[1] || 0) - parseInt(a[1] || 0))[0];
    addImage(best ? best[0] : (i.currentSrc || i.src || i.dataset.src || i.dataset.lazySrc), i.closest('header,nav') ? 'header image' : i.closest('footer') ? 'footer image' : 'image', { alt: i.alt || '', w: i.naturalWidth, h: i.naturalHeight });
  });
  document.querySelectorAll('picture source').forEach(s => (s.srcset || '').split(',').forEach(p => addImage(p.trim().split(/\s+/)[0], 'picture source')));
  document.querySelectorAll('*').forEach(e => { const b = getComputedStyle(e).backgroundImage; (b.match(/url\(["']?([^"')]+)/g) || []).forEach(m => addImage(m.replace(/url\(["']?/, ''), 'background')) });
  document.querySelectorAll('link[rel*=icon]').forEach(l => addImage(l.href, 'favicon', { sizes: l.sizes + '' }));
  const og = document.querySelector('meta[property="og:image"]'); if (og) addImage(og.content, 'share image');
  const svgs = [...document.querySelectorAll('header svg, a[class*=logo] svg')].length;

  const hex = c => { const m = c && c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/); if (!m || (m[4] && +m[4] < 0.5)) return null; return '#' + [m[1], m[2], m[3]].map(v => (+v).toString(16).padStart(2, '0')).join('') };
  const colors = {};
  const addColor = (h, where) => { if (!h) return; (colors[h] = colors[h] || { hex: h, count: 0, where: new Set() }).count++; colors[h].where.add(where) };
  document.querySelectorAll('*').forEach(e => {
    const s = getComputedStyle(e), t = e.tagName.toLowerCase();
    const area = e.closest('header') ? 'header' : e.closest('footer') ? 'footer' : (t === 'a' || t === 'button' || /btn|button/.test(e.className)) ? 'button or link' : /^h\d$/.test(t) ? 'heading' : 'body';
    addColor(hex(s.backgroundColor), area + ' background'); addColor(hex(s.color), area + ' text');
    if (s.borderTopWidth !== '0px') addColor(hex(s.borderTopColor), area + ' border');
    (s.backgroundImage.match(/rgba?\([^)]+\)/g) || []).forEach(c => addColor(hex(c), area + ' gradient'));
    if (t === 'path' || t === 'svg' || t === 'circle') addColor(hex(s.fill), area + ' icon');
  });
  const variables = {};
  for (const sheet of document.styleSheets) { let rules; try { rules = sheet.cssRules } catch (e) { continue }
    for (const r of rules) if (r.style && /^(:root|body|html)/.test(r.selectorText || '')) for (const p of r.style) if (p.startsWith('--')) { const v = r.style.getPropertyValue(p).trim(); if (/^#[0-9a-f]{3,8}$|^rgb/i.test(v)) variables[p] = v } }

  const logoColors = [];
  const logo = document.querySelector('header img, a[class*=logo] img, img[class*=logo]');
  if (logo && logo.complete) { try {
    const c = document.createElement('canvas'), x = c.getContext('2d'); c.width = 64; c.height = 64 * logo.naturalHeight / logo.naturalWidth || 64;
    x.drawImage(logo, 0, 0, c.width, c.height); const d = x.getImageData(0, 0, c.width, c.height).data, bins = {};
    for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 200) continue; const [r, g, b] = [d[i], d[i + 1], d[i + 2]]; if (Math.max(r, g, b) - Math.min(r, g, b) < 30) continue;
      const k = [r, g, b].map(v => Math.round(v / 24) * 24).map(v => Math.min(v, 255).toString(16).padStart(2, '0')).join(''); bins[k] = (bins[k] || 0) + 1 }
    Object.entries(bins).sort((a, b) => b[1] - a[1]).slice(0, 5).forEach(([k, n]) => logoColors.push({ hex: '#' + k, pixels: n }));
  } catch (e) { logoColors.push({ error: 'logo is on another domain; sample it after download' }) } }

  const h = document.querySelector('h1,h2'), btn = document.querySelector('.wp-block-button__link,.wp-element-button,.elementor-button,a[class*=button],a[class*=btn],button[class],input[type=submit]');
  const bs = btn && getComputedStyle(btn);
  window.__scan = {
    page: abs(location.href), title: document.title,
    images: [...images.values()],
    colors: Object.values(colors).sort((a, b) => b.count - a.count).map(c => ({ hex: c.hex, count: c.count, where: [...c.where].slice(0, 4).join(', ') })),
    variables, logoColors, inlineSvgLogos: svgs,
    fonts: { heading: h && getComputedStyle(h).fontFamily, headingWeight: h && getComputedStyle(h).fontWeight, headingCase: h && getComputedStyle(h).textTransform, body: getComputedStyle(document.body).fontFamily,
      googleFonts: [...document.querySelectorAll('link[href*="fonts.googleapis"]')].map(l => l.href.split('?')[1] ? 'google fonts link' : l.href).length },
    button: bs && { text: btn.textContent.trim().slice(0, 30), radius: bs.borderRadius, background: hex(bs.backgroundColor), color: hex(bs.color), case: bs.textTransform, weight: bs.fontWeight, border: bs.borderTopWidth + ' ' + hex(bs.borderTopColor) },
    headings: [...document.querySelectorAll('h1,h2,h3')].slice(0, 12).map(e => e.textContent.trim().replace(/\s+/g, ' ').slice(0, 80)).filter(Boolean),
    links: [...new Set([...document.querySelectorAll('header a, nav a')].map(a => abs(a.href)).filter(u => u && u.startsWith(location.origin)))].slice(0, 40)
  };
  window.__scanPart = (k, from = 0, n = 25) => JSON.stringify(Array.isArray(window.__scan[k]) ? window.__scan[k].slice(from, from + n) : window.__scan[k]);
  return JSON.stringify({ page: window.__scan.page, images: window.__scan.images.length, colors: window.__scan.colors.length, variables: Object.keys(variables).length, logoColors: logoColors.length, links: window.__scan.links.length });
})()
