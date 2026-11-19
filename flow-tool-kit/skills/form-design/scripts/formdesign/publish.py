"""Write the canvas: one .dc.html per artboard, canvas.json, the publish batches, the image uploads and the fallback page.

The Design canvas loads the FlowToolKit Forms design system from `project/ds/ftk/` inside the canvas. Those five files come
from the person's own copy of the design system (its link is in flow-tool-kit.json, written by ftk-start):

- Claude Code copies them server side from that artifact ({"artifact": <link>, "path": ...} in the files map), up to 255
  files a call;
- chat cannot copy server side, so the files are written from the full kit (the release zip ftk-start unpacks), at most 16
  files a call.

When the account has no Design type, review.html is one self-contained page with the same components, built from the
full kit (React, bundle.js, bundle.css and only the icons the boards use).
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import pathlib
import re
import shutil
from datetime import datetime, timezone

from . import boards, nodes

DS_NAMESPACE = "ftk"
# Canvas path -> path inside the design system (the full kit's project/ tree, as ftk-start installs it)
DS_FILES = {
    "project/ds/ftk/components/bundle.css": "project/components/bundle.css",
    "project/ds/ftk/components/bundle.js": "project/components/bundle.js",
    "project/ds/ftk/components/lib/slds-icons-2.30.7.js": "project/components/lib/slds-icons-2.30.7.js",
    "project/ds/ftk/components/lib/ftk-illustrations.js": "project/components/lib/ftk-illustrations.js",
    "project/ds/ftk/tokens.json": "project/tokens.json",
}
REACT_FILES = ("project/components/lib/react.production.min.js", "project/components/lib/react-dom.production.min.js")
PACKAGE_BANNER = {"asset": "FlowToolKit__Background_Forest_Sunbeams", "path": "project/assets/Backgrounds/Background_Forest_Sunbeams.jpg"}
BATCH = {"code": 255, "chat": 16}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
<link rel="stylesheet" href="ds/ftk/components/bundle.css">
<script src="ds/ftk/components/lib/slds-icons-2.30.7.js"></script>
<script src="ds/ftk/components/lib/ftk-illustrations.js"></script>
<script src="ds/ftk/components/bundle.js"></script>
</head>
<body>
<x-dc>
<helmet>
{fonts}<style>{css}</style>
</helmet>
"""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha1(path: pathlib.Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def pixel_size(path: pathlib.Path) -> tuple:
    """(width, height) of a PNG or JPEG from its header; (0, 0) when unknown."""
    data = path.read_bytes()[:262144]
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    i = 2
    while data[:2] == b"\xff\xd8" and i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + (0 if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 else length)
    return 0, 0


# ---------------------------------------------------------------- images
def local_images(plans: list, kit: pathlib.Path | None) -> dict:
    """Every image the canvas draws, as local files: the plan's logo and banner (images.*, relative to the plan), each form's
    source screenshot (source.screenshot) keyed source-<slug>, and the package banner photo when no plan has a banner."""
    files = {}
    for slug, plan, base in plans:
        for key, rel in (plan.get("images") or {}).items():
            path = (base / rel) if rel else None
            if path and path.exists() and path.suffix.lower() in IMAGE_EXT:
                files.setdefault(key, path)
        shot = (plan.get("source") or {}).get("screenshot")
        if shot and (base / shot).exists():
            files[f"source-{slug}"] = base / shot
    if "banner" not in files and kit and (kit / PACKAGE_BANNER["path"]).exists():
        files["banner"] = kit / PACKAGE_BANNER["path"]
    return files


def canvas_urls(design: pathlib.Path, files: dict) -> tuple[dict, list]:
    """(urls, pending): each image's canvas upload url from design/blobs.json, and the images still to upload (new, or
    changed since their upload). A pending image is drawn as a labelled placeholder or left off, never with an empty src."""
    path = design / "blobs.json"
    recorded = json.loads(path.read_text()) if path.exists() else {}
    urls, pending = {}, []
    for key, file in files.items():
        entry = recorded.get(key) or {}
        url, digest = (entry.get("url"), entry.get("sha1")) if isinstance(entry, dict) else (entry, None)
        if url and (digest is None or digest == sha1(file)):
            urls[key] = url
        else:
            pending.append({"name": key, "file": str(file.resolve()), "sha1": sha1(file)})
    return urls, pending


IMAGE_REF = "fdimg:"


def data_urls(files: dict) -> dict:
    """The same images inlined once, for the self-contained page: {key: data url}. The boards refer to each as fdimg:<key>."""
    out = {}
    for key, file in files.items():
        kind = mimetypes.guess_type(str(file))[0] or "image/png"
        out[key] = f"data:{kind};base64," + base64.b64encode(file.read_bytes()).decode()
    return out


def image_refs(files: dict) -> dict:
    return {key: IMAGE_REF + key for key in files}


# ---------------------------------------------------------------- canvas files
def dc_html(board: dict, style: dict, fonts_href: str | None) -> str:
    vals = nodes.Vals()
    markup = nodes.to_dc(board["tree"], vals)
    fonts = f'<link rel="stylesheet" href="{nodes.esc(fonts_href)}">\n' if fonts_href else ""
    props = {"brand": {"editor": "color", "default": style["brand"], "options": [style["brand"], style["heading_color"], style["accent"]], "section": "Brand"},
             "$preview": {"width": board["w"], "height": board["h"]}}
    data_props = json.dumps(props).replace("&", "&amp;").replace("'", "&#39;")
    script = (f"<script type=\"text/x-dc\" data-dc-script data-props='{data_props}'>\n"
              "class Component extends DCLogic {\n  renderVals() {\n"
              f"    const brand = this.props.brand ?? {json.dumps(style['brand'])};\n"
              f"    return {{ ...{json.dumps(vals.values, ensure_ascii=False)}, brand }};\n  }}\n}}\n</script>\n</body>\n</html>\n")
    return HEAD.format(title=nodes.esc(board["title"]), fonts=fonts, css=boards.page_css(style)) + markup + "\n</x-dc>\n" + script


def layout(groups: list) -> tuple[dict, list, dict]:
    """Canvas positions. Single-page forms side by side in the first row; each multi-page form its own row (source, stages,
    pages, review); then confirmations, emails and the field audit. The brand board sits left of everything."""
    frames, order, notes = {}, [], {}

    def put(board, x, y):
        frames[board["name"]] = {"x": x, "y": y, "w": board["w"], "h": board["h"], "title": board["title"],
                                 **({"is_interactive": True} if board.get("interactive") else {})}
        order.append(board["name"])
        return x + board["w"] + 80

    singles = [g for g in groups if g["kind"] == "single"]
    multis = [g for g in groups if g["kind"] == "multi"]
    brand = next((g for g in groups if g["kind"] == "brand"), None)
    tail = next((g for g in groups if g["kind"] == "tail"), None)
    if brand:
        put(brand["boards"][0], -1720, 0)
    x, row_h = 0, 0
    for g in singles:
        x0 = x
        for b in g["boards"]:
            x = put(b, x, 0)
        h = max(b["h"] for b in g["boards"])
        if g.get("notes"):
            notes[f"n_{g['slug'].replace('-', '_')}"] = {"x": x0, "y": h + 40, "text": g["notes"], "w": 1100, "fill": "orange"}
        row_h = max(row_h, h + (520 if g.get("notes") else 0))
        x += 100
    if singles:
        notes["t_single"] = {"x": 0, "y": -420, "text": "Single-page forms", "kind": "title1", "maxW": max(x - 80, 400)}
    y = (row_h + 520) if singles else 0
    for g in multis:
        notes[f"t_{g['slug'].replace('-', '_')}"] = {"x": 0, "y": y - 420, "text": g["title"], "kind": "title1", "maxW": 5800}
        x = 0
        for b in g["boards"]:
            x = put(b, x, y)
        if g.get("notes"):
            notes[f"n_{g['slug'].replace('-', '_')}"] = {"x": x, "y": y, "text": g["notes"], "w": 900, "fill": "orange"}
        y += max(max(b["h"] for b in g["boards"]), 1300) + 520
    if tail:
        notes["t_end"] = {"x": 0, "y": y - 420, "text": "Confirmations, emails and field audit", "kind": "title1", "maxW": 3900}
        conf = [b for b in tail["boards"] if b["name"] == "Confirmations.dc.html"]
        emails = [b for b in tail["boards"] if b["name"].startswith("Emails")]
        audit = [b for b in tail["boards"] if b["name"].startswith("FieldAudit")]
        ey = y
        for b in conf + emails:
            put(b, 0, ey)
            ey += b["h"] + 120
        ax = 2280
        for b in audit:
            ax = put(b, ax, y)
    return frames, order, notes


def write_canvas(design: pathlib.Path, all_boards: list, groups: list, style: dict, fonts_href: str | None,
                 ds: dict, measured: dict, title: str) -> dict:
    project = design / "project"
    project.mkdir(parents=True, exist_ok=True)
    for board in all_boards:
        h = min(boards.CAP, int(measured.get(board["name"]) or board["h"]))
        if h != board["h"]:
            board["h"] = h
            board["tree"]["p"]["style"] = re.sub(r"min-height: \d+px", f"min-height: {h}px", board["tree"]["p"].get("style", ""))
    over = {b["name"]: b["h"] for b in all_boards if b["h"] > boards.CAP or b["w"] > boards.CAP}
    if over:
        raise SystemExit(f"artboards over the canvas cap of {boards.CAP}px: {over}")
    written = set()
    for board in all_boards:
        (project / board["name"]).write_text(dc_html(board, style, fonts_href))
        written.add(board["name"])
    stale = sorted(p.name for p in project.glob("*.dc.html") if p.name not in written)
    for name in stale:
        (project / name).unlink()
    frames, order, notes = layout(groups)
    canvas_path = project / "canvas.json"
    previous = json.loads(canvas_path.read_text()) if canvas_path.exists() else {}
    created = previous.get("createdOnFiles") or {"v": 1, "at": now()}
    kept_notes = {k: v for k, v in (previous.get("notes") or {}).items() if not re.match(r"^(t|n)_", k)}  # notes people drew stay
    systems = [s for s in previous.get("designSystems") or [] if s.get("namespace") != DS_NAMESPACE]
    old = next((s for s in previous.get("designSystems") or [] if s.get("namespace") == DS_NAMESPACE), {})
    systems.append({"title": ds.get("title") or "FlowToolKit Forms", "namespace": DS_NAMESPACE, "artifact": ds.get("url"),
                    "version": ds.get("kit_version") or old.get("version"), "copiedAt": old.get("copiedAt") or created["at"]})
    canvas = {**previous, "v": 3, "createdOnFiles": created, "title": previous.get("title") or title,
              "launch": previous.get("launch") or {"view": "canvas"}, "pages": previous.get("pages") or [], "boards": frames,
              "order": order, "notes": {**kept_notes, **notes}, "designSystems": systems}
    canvas_path.write_text(json.dumps(canvas, indent=1) + "\n")
    return {"written": sorted(written), "stale": stale}


def publish_batches(design: pathlib.Path, written: list, stale: list, mode: str, ds: dict, kit: pathlib.Path | None) -> dict:
    """design/publish-batches.json: the publish as `files` maps (root design/), in order, each within the mode's per-call limit.

    code: the design system copied server side from the person's own artifact. chat: its files written from the full kit,
    copied first into design/project/ds/ftk/. canvas.json goes in the last batch, so the canvas opens on a complete set."""
    entries = [(f"project/{name}", f"project/{name}") for name in written]
    if mode == "code":
        if not ds.get("url"):
            raise SystemExit("no FlowToolKit Forms design system link: run ftk-start's design system step, which installs your own copy "
                             "and saves its link in flow-tool-kit.json (design_systems.forms.url)")
        entries += [(path, {"artifact": ds["url"], "path": src}) for path, src in DS_FILES.items()]
    else:
        if not kit:
            raise SystemExit("chat publishing writes the design system files from the full kit, and it was not found; get it with ftk-start's design system step (`ds_install.py fetch` in Claude Code, or `ds_install.py unpack --zip` on the attached release zip in chat), or pass --kit")
        for path, src in DS_FILES.items():
            target = design / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kit / src, target)
            entries.append((path, path))
    entries += [(f"project/{name}", None) for name in stale]
    size = BATCH[mode] - 1
    batches = [dict(entries[i:i + size]) for i in range(0, len(entries), size)] or [{}]
    batches[-1]["project/canvas.json"] = "project/canvas.json"
    out = {"mode": mode, "root": str(design), "per_call": BATCH[mode], "design_system": ds.get("url"), "batches": batches}
    (design / "publish-batches.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def write_uploads(design: pathlib.Path, pending: list, canvas_url: str | None) -> list:
    paths = [p["file"] for p in pending]
    (design / "uploads.json").write_text(json.dumps({"canvas": canvas_url, "files": pending,
                                                     "file_paths": [paths[i:i + 25] for i in range(0, len(paths), 25)]}, indent=1) + "\n")
    return pending


# ---------------------------------------------------------------- the fallback page
STANDALONE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{fonts}<style>{tokens}</style>
<style>{bundle_css}</style>
<style>{css}
.fd-board{{margin:0 0 48px}}.fd-board>h2{{font:600 16px/1.4 Arial,sans-serif;color:#353535;margin:0 16px 8px}}
.fd-scroll{{overflow-x:auto;padding:0 16px}}.fd-root{{display:inline-block}}
.fd-banner{{font:14px/1.5 Arial,sans-serif;background:#fff8c4;padding:10px 16px;margin:0 0 24px}}</style>
<script>{react}</script>
<script>{react_dom}</script>
<script>window.SLDSIcons={icons};var IMAGES={images};</script>
<script>{bundle_js}</script>
</head>
<body>
<p class="fd-banner">Review page for {title_text}. The same FlowToolKit Forms components as the design canvas, in one self-contained file:
every branch is drawn and marked, nothing here is the live form.</p>
<div id="boards"></div>
<script>
var BOARDS = {boards};
var F = window.FTK, h = React.createElement;
function styleObj(s) {{ var o = {{}}; (s || '').split(';').forEach(function (d) {{ var i = d.indexOf(':'); if (i < 0) return;
  var k = d.slice(0, i).trim(), v = d.slice(i + 1).trim(); if (!k) return;
  o[k.indexOf('--') === 0 ? k : k.replace(/-([a-z])/g, function (_, c) {{ return c.toUpperCase(); }})] = v; }}); return o; }}
function img(s) {{ return typeof s === 'string' ? s.replace(/fdimg:([A-Za-z0-9_-]+)/g, function (m, k) {{ return IMAGES[k] || ''; }}) : s; }}
function build(n, key) {{
  if (typeof n === 'string') return n;
  if (n.raw !== undefined) return h('div', {{ key: key, style: {{ display: 'contents' }}, dangerouslySetInnerHTML: {{ __html: img(n.raw) }} }});
  var p = Object.assign({{ key: key }}, n.p), kids = (n.c || []).map(build);
  Object.keys(p).forEach(function (k) {{ p[k] = img(p[k]); }});
  if (n.t.indexOf('FTK.') === 0) {{ var C = F[n.t.slice(4)]; if (!C) return h('div', {{ key: key, style: {{ color: '#b3261e' }} }}, 'Unknown component ' + n.t);
    return h.apply(null, [C, p].concat(kids)); }}
  if (p.style) p.style = styleObj(p.style); if (p['class']) {{ p.className = p['class']; delete p['class']; }}
  return h.apply(null, [n.t, p].concat(kids));
}}
var root = document.getElementById('boards');
BOARDS.forEach(function (b, i) {{
  var sec = document.createElement('section'); sec.className = 'fd-board'; sec.setAttribute('data-board', b.name);
  sec.innerHTML = '<h2></h2><div class="fd-scroll"><div class="fd-root"></div></div>';
  sec.querySelector('h2').textContent = b.title + ' (' + b.w + ' x ' + b.h + ')';
  root.appendChild(sec);
  ReactDOM.createRoot(sec.querySelector('.fd-root')).render(build(b.tree, 'b' + i));
}});
</script>
</body>
</html>
"""


def icon_subset(kit: pathlib.Path, wanted: set) -> str:
    """Only the icons the boards use, plus every utility icon the components draw on their own."""
    text = (kit / "project/components/lib/slds-icons-2.30.7.js").read_text()
    lib = json.loads(text[text.index("window.SLDSIcons=") + len("window.SLDSIcons="):].rstrip().rstrip(";"))
    bundle = (kit / "project/components/bundle.js").read_text()
    wanted = set(wanted) | set(re.findall(r"utility:[a-z0-9_]+", bundle))
    return json.dumps({k: v for k, v in lib.items() if k in wanted}, separators=(",", ":"))


def tokens_css(kit: pathlib.Path) -> str:
    """The design system's base tokens as CSS variables (on the canvas the Design runtime defines them from tokens.json)."""
    data = json.loads((kit / "project/tokens.json").read_text())
    decls = []
    for group in ("color", "spacing", "radius", "sizing", "shadow"):
        for token in (data.get(group) or {}).get("tokens") or []:
            if token.get("name") and token.get("value") is not None:
                decls.append(f"--{token['name']}:{token['value']}")
    for name, family in ((data.get("type") or {}).get("families") or {}).items():
        decls.append(f"--font-{name}:{family}")
    return ":root{" + ";".join(decls) + "}"


def write_standalone(path: pathlib.Path, all_boards: list, style: dict, fonts_href: str | None, kit: pathlib.Path, title: str,
                     images: dict | None = None) -> int:
    trees = [{"name": b["name"], "title": b["title"], "w": b["w"], "h": b["h"], "tree": nodes.to_react(b["tree"], style["brand"])} for b in all_boards]
    icons = set()
    for b in all_boards:
        icons |= nodes.icons_used(b["tree"])
    script_safe = lambda s: s.replace("</script", "<\\/script")
    page = STANDALONE.format(
        title=nodes.esc(title), title_text=nodes.esc(title),
        fonts=f'<link rel="stylesheet" href="{nodes.esc(fonts_href)}">\n' if fonts_href else "",
        bundle_css=(kit / "project/components/bundle.css").read_text().replace("</style", "<\\/style"),
        css=boards.page_css(style), tokens=tokens_css(kit),
        react=script_safe((kit / REACT_FILES[0]).read_text()), react_dom=script_safe((kit / REACT_FILES[1]).read_text()),
        icons=script_safe(icon_subset(kit, icons)), bundle_js=script_safe((kit / "project/components/bundle.js").read_text()),
        images=script_safe(json.dumps(images or {})), boards=script_safe(json.dumps(trees, ensure_ascii=False)))
    path.write_text(page)
    return len(page.encode())
