#!/usr/bin/env python3
"""Bring page.json level with a site review canvas: every edit made on the canvas itself goes back into the source.

A canvas can change without page.json: someone edits a block in the properties panel, or the Claude inside the canvas
answers a comment by editing the artboard. The next redraw from page.json would wipe those edits, and the site build would
ship something other than what was approved. Run this before applying a review round (references/review.md).

Usage:
  python3 -I pull_canvas_edits.py --site _site/<slug> --live <folder holding project/*.dc.html read from the canvas> [--dry-run]

Read the live files first with the Artifact tool: `read`, the canvas url, `paths` = every `project/*.dc.html`, `out_dir` = a
folder in the project. The desktop artboard of each page is the one read (phone and state artboards are drawn from
the same page.json). Each change is printed; nothing is written with --dry-run.

What it maps back:
- a block's props, key by key, with colours turned back into the palette's names
- section attributes and column widths; a wrapper holding more than one SB.Section becomes that many sections (-b, -c ids)
- dividers, rich text, HTML Editor markup and tabs (each tab's items); items gone from the canvas are dropped.
  Markup edited on the canvas is checked again when build_site_review.py redraws (htmlcheck.py)
- a repeater's drawn settings (card type, columns, colours) and its sample cards; a change made the same way on every
  sample card is a card setting, so it goes on the build's card template too
- the shared header and footer (site.json page.header / footerContent): patched, or emptied when no page draws them
- an artboard named <page>-<id>.dc.html that page.json does not draw becomes a `_design.states` entry on that page
Anything else (a new component type, a changed sample count) stops with the section named, for a hand edit.
"""
import argparse
import copy
import importlib.util
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_site_review", HERE / "build_site_review.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

PER_RECORD = {"imageAsset", "imageSource", "imageUrl", "image", "imageAlt", "title", "eyebrow", "subtitle", "badge", "description"}
KIND_OF = {"divider": "SB.Divider", "richText": "SB.RichContent", "htmlEditor": "SB.HtmlEditor", "repeater": "SB.Repeater",
           "tabs": "SB.Tabs", "formSlot": "SB.FormSlot", "search": "SB.Search", "languageSelector": "SB.LanguageSelector"}


class PullError(Exception):
    pass


# ---------- Reading an artboard back into a tree ----------

def render_vals(src):
    m = re.search(r"renderVals\(\)\s*\{\s*return (\{.*\});\s*\}\s*\}\s*</script>", src, re.S)
    if not m:
        raise PullError("no renderVals() in the artboard")
    return json.loads(m.group(1))


class _Markup(HTMLParser):
    """x-import and div elements inside <x-dc>; everything else (tags, labels, links) is ignored"""

    def __init__(self):
        super().__init__()
        self.root = {"c": "root", "k": []}
        self.stack = [self.root]
        self.inside = False

    def handle_starttag(self, tag, attrs):
        if tag == "x-dc":
            self.inside = True
            return
        if not self.inside or tag not in ("x-import", "div"):
            return
        a = dict(attrs)
        if tag == "x-import":
            node = {"c": a["component-from-global-scope"], "key": a["dc-props"].strip("{}"), "k": []}
        elif "data-section-id" in a:
            node = {"c": "section", "id": a["data-section-id"], "k": []}
        else:
            node = {"c": "plain", "k": []}
        self.stack[-1]["k"].append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        if tag == "x-dc":
            self.inside = False
        elif self.inside and tag in ("x-import", "div") and len(self.stack) > 1:
            self.stack.pop()


def artboard_sections(path):
    """[{"id", "k": [SB.Section nodes]}] in page order, each node {"c", "p", "k"}"""
    src = path.read_text()
    vals = render_vals(src)
    parser = _Markup()
    parser.feed(src)

    def build(node, parent=None):
        if node["c"] == "plain":
            kids = [x for k in node["k"] for x in build(k)]
            return [{"c": "div", "p": {}, "k": kids}] if parent == "SB.Tabs" else kids  # a tab's wrapper is the only plain div kept
        if node["c"] == "section":
            return [{"c": "wrapper", "id": node["id"], "k": [x for k in node["k"] for x in build(k)]}]
        return [{"c": node["c"], "p": vals[node["key"]], "k": [x for k in node["k"] for x in build(k, node["c"])]}]

    out = []

    def collect(nodes):
        for n in nodes:
            if n["c"] == "wrapper":
                out.append(n)
            else:
                collect(n["k"])

    collect([x for k in parser.root["k"] for x in build(k)])
    return out


# ---------- Mapping a live tree back onto page.json ----------

class Puller:
    def __init__(self, palette):
        self.palette = palette
        # brand and accent are aliases; a colour goes back under its own name
        self.names = {}
        for name, hexv in palette.items():
            if name not in ("brand", "accent"):
                self.names.setdefault(str(hexv).lower(), name)
        self.log = []

    def unpalette(self, live, old=None):
        if isinstance(live, str):
            if isinstance(old, str) and old.startswith("$") and str(self.palette.get(old[1:], "")).lower() == live.lower():
                return old
            return "$" + self.names[live.lower()] if live.lower() in self.names else live
        if isinstance(live, dict):
            return {k: self.unpalette(v, old.get(k) if isinstance(old, dict) else None) for k, v in live.items()}
        if isinstance(live, list):
            return [self.unpalette(v, old[i] if isinstance(old, list) and i < len(old) else None) for i, v in enumerate(live)]
        return live

    def patch(self, source, drawn, live, where):
        """source: the page.json props; drawn: what the generator drew from them; live: the canvas now"""
        new = copy.deepcopy(source)
        for k in sorted(set(drawn) | set(live)):
            if drawn.get(k) == live.get(k):
                continue
            if k not in live:
                new.pop(k, None)
                self.log.append(f"{where}: {k} removed")
            else:
                new[k] = self.unpalette(live[k], source.get(k))
                self.log.append(f"{where}: {k} = {json.dumps(live[k], ensure_ascii=False)[:100]}")
        return new

    @staticmethod
    def signature(item):
        if item.get("kind") == "block":
            p = item.get("props") or {}
            return ("SB.Block", p.get("sectionType"), p.get("heading") or p.get("title") or p.get("sectionLabel"))
        return (KIND_OF.get(item.get("kind"), item.get("kind")), None, None)

    @staticmethod
    def live_signature(node):
        p = node.get("p") or {}
        if node["c"] == "SB.Block":
            return ("SB.Block", p.get("sectionType"), p.get("heading") or p.get("title") or p.get("sectionLabel"))
        return (node["c"], None, None)

    def take(self, node, pool):
        """The page.json item this live node was drawn from: same type and heading, else same type and block kind, else same type"""
        s = self.live_signature(node)
        for depth in (3, 2, 1):
            for i, item in enumerate(pool):
                if self.signature(item)[:depth] == s[:depth]:
                    return pool.pop(i)
        return None

    def item(self, node, old, standin, where):
        c = node["c"]
        if old is None:
            if c == "SB.Block":
                self.log.append(f"{where}: new block {node['p'].get('sectionType')}")
                return {"kind": "block", "props": self.unpalette(node["p"])}
            raise PullError(f"{where}: a new {c} on the canvas; add it to page.json by hand")
        drawn = gen.item_node(old, self.palette, False, standin)
        if c == "SB.Block":
            return dict(old, props=self.patch(old.get("props") or {}, drawn["p"], node["p"], where))
        if c == "SB.Divider":
            return dict(old, attributes=self.patch(old.get("attributes") or {}, drawn["p"], node["p"], where))
        if c in ("SB.RichContent", "SB.HtmlEditor"):
            if drawn["p"] != node["p"]:
                self.log.append(f"{where}: rich text changed")
            return dict(old, richTextValue=node["p"].get("richTextValue", ""))
        if c == "SB.Repeater":
            return self.repeater(node, old, drawn, where)
        if c == "SB.Tabs":
            new = copy.deepcopy(old)
            for tab, div in zip(new.get("tabs") or [], node["k"]):
                pool = list(tab.get("items") or [])
                tab["items"] = [self.item(n, self.take(n, pool), standin, f"{where} tab {tab.get('tabKey')}") for n in div["k"]]
                for left in pool:
                    self.log.append(f"{where} tab {tab.get('tabKey')}: {self.signature(left)[0]} removed")
            return new
        if drawn["p"] != node["p"]:
            self.log.append(f"{where}: {c} differs on the canvas; page.json kept (hand edit): {json.dumps(node['p'])[:160]}")
        return old

    def repeater(self, node, old, drawn, where):
        new = copy.deepcopy(old)
        for k in gen.REPEATER_KEYS:
            if drawn["p"].get(k) != node["p"].get(k):
                if k in node["p"]:
                    new[k] = self.unpalette(node["p"][k], old.get(k))
                else:
                    new.pop(k, None)
                self.log.append(f"{where}: repeater {k} = {node['p'].get(k)}")
        drawn_cards, live_cards = drawn["p"].get("records") or [], node["p"].get("records") or []
        if len(drawn_cards) != len(live_cards):
            raise PullError(f"{where}: the canvas shows {len(live_cards)} sample cards, page.json {len(drawn_cards)}; edit by hand")
        samples = (new.setdefault("_design", {})).setdefault("sampleRecords", [])
        # a canvas drawn before sample cards took the card template lacks the template's keys on every card: not a removal
        template = {k for k, v in (old.get("card") or {}).items() if k != "link" and not any(gen.merge_token(x) for x in gen.strings(v))}
        unseen = {k for k in template if all(k not in l for l in live_cards)}
        drawn_cards = [{k: v for k, v in d.items() if k not in unseen} for d in drawn_cards]
        common = None
        for i, (d, l) in enumerate(zip(drawn_cards, live_cards)):
            samples[i] = self.patch(samples[i], d, l, f"{where} sample {i + 1}")
            changed = {k: l.get(k, None) for k in set(d) | set(l) if d.get(k) != l.get(k)}
            common = changed if common is None else {k: v for k, v in common.items() if k in changed and changed[k] == v}
        for k, v in (common or {}).items():
            if k in PER_RECORD:
                continue
            card = new.setdefault("card", {})
            if v is None:
                card.pop(k, None)
            else:
                card[k] = self.unpalette(v, card.get(k))
            self.log.append(f"{where}: card template {k} = {json.dumps(v)[:80]} (every sample card changed the same way)")
        return new

    def sections(self, wrapper, old):
        """One page.json section from a wrapper; a wrapper with several SB.Section becomes several sections"""
        standin = (old.get("_design") or {}).get("photoStandIn") or gen.PHOTO_STAND_IN
        pool = [it for col in old.get("columns") or [] for it in col.get("items") or []]
        out = []
        for n, sec in enumerate(wrapper["k"]):
            if sec["c"] != "SB.Section":
                raise PullError(f"{wrapper['id']}: {sec['c']} sits directly in the section wrapper")
            if n == 0:
                s = copy.deepcopy(old)
                attrs = {k: v for k, v in (old.get("attributes") or {}).items() if k != "sectionConfig"}
                s["attributes"] = self.patch(old.get("attributes") or {}, gen.swap_palette(attrs, self.palette), sec["p"], f"{wrapper['id']} section")
            else:
                sid = f"{wrapper['id']}-{'bcdefgh'[n - 1]}"
                s = {"attributes": self.unpalette(sec["p"]), "_design": {"id": sid, "job": "Split from " + wrapper["id"] + " on the canvas; name its job"}}
                self.log.append(f"{wrapper['id']}: new section {sid}")
            s["columns"] = [{"width": str(col["p"].get("columnWidth", "12")),
                             "items": [self.item(it, self.take(it, pool), standin, f"{wrapper['id']}/{n}/{ci}") for it in col["k"]]}
                            for ci, col in enumerate(sec["k"])]
            if n == 0:
                before = [str(c.get("width") or 12) for c in old.get("columns") or []]
                after = [c["width"] for c in s["columns"]]
                if before != after:
                    self.log.append(f"{wrapper['id']}: columns {before} -> {after}")
            out.append(s)
        for left in pool:
            self.log.append(f"{wrapper['id']}: {self.signature(left)[0]} removed")
        return out


def region_index(wrappers, region):
    return [w for w in wrappers if w["id"].startswith(region + "-")]


def pull(site_dir, live_dir, dry_run=False):
    site_dir, live_dir = pathlib.Path(site_dir), pathlib.Path(live_dir)
    if (live_dir / "project").is_dir():
        live_dir = live_dir / "project"
    site, pages = gen.load_site(site_dir)
    p = Puller(site.get("palette") or {})
    site_raw = json.loads((site_dir / "site.json").read_text())
    shared = site_raw.get("page") or {}
    writes, header_seen, footer_seen = {}, False, False
    drawn = set()
    page_names = {e["urlName"] for e, _ in pages}

    for entry, page in pages:
        name = entry["urlName"]
        board = live_dir / f"{name}.dc.html"
        if not board.exists():
            raise PullError(f"{board.name} was not read from the canvas")
        src = site_dir / "pages" / f"{name}.json"
        raw = json.loads(src.read_text())
        wrappers = artboard_sections(board)
        old = {gen.section_id(s, i): s for i, s in enumerate(raw.get("sections") or [], 1)}
        body = [w for w in wrappers if not w["id"].startswith(("header-", "footer-"))]
        new_sections = []
        for w in body:
            if w["id"] not in old:
                raise PullError(f"{name}: canvas section {w['id']} is not in page.json")
            new_sections += p.sections(w, old[w["id"]])
        for sid in old:
            if sid not in {w["id"] for w in body}:
                p.log.append(f"{name}: section {sid} removed")
        raw["sections"] = new_sections

        # the shared header and footer are drawn on every page from site.json; the first page that draws one is read
        for region, key in (("header", "header"), ("footer", "footerContent")):
            live_region = region_index(wrappers, region)
            if live_region and key in shared and not (header_seen if region == "header" else footer_seen):
                shared[key] = [p.sections(w, s)[0] for w, s in zip(live_region, shared.get(key) or [])]
                if region == "header":
                    header_seen = True
                else:
                    footer_seen = True

        drawn.update({f"{name}.dc.html", f"{name}-phone.dc.html"} | {f"{name}-{gen.slug(s['id'])}.dc.html" for s in (raw.get("_design") or {}).get("states") or []})
        # an artboard drawn on the canvas for this page that page.json does not draw (an alternative someone added): keep it as a state
        for extra in sorted(live_dir.glob(f"{name}-*.dc.html")):
            stem = extra.name[:-len(".dc.html")]
            longer = [o for o in page_names if len(o) > len(name) and (stem == o or stem.startswith(o + "-"))]
            if extra.name in drawn or longer:
                continue
            sid = extra.name[len(name) + 1:-len(".dc.html")]
            states = raw.setdefault("_design", {}).setdefault("states", [])
            sections = []
            for w in artboard_sections(extra):
                if w["id"].startswith(("header-", "footer-")):
                    continue
                # a section the page already has is read against it; a new one starts empty
                base = old.get(w["id"]) or {"attributes": {}, "columns": [], "_design": {"id": w["id"], "job": f"From the canvas artboard {extra.name}; name its job"}}
                sections += p.sections(w, base)
            states.append({"id": sid, "title": sid.replace("-", " "), "sections": sections})
            drawn.add(extra.name)
            p.log.append(f"{name}: artboard {extra.name} kept as state {sid}")
        writes[src] = raw
        if p.log:
            print(f"--- {name}")
            for line in p.log:
                print("  " + line)
        p.log.clear()

    for key, seen in (("header", header_seen), ("footerContent", footer_seen)):
        if shared.get(key) and not seen:
            shared[key] = []
            print(f"--- site.json: page.{key} is drawn on no page of the canvas; emptied")
    site_raw["page"] = shared
    writes[site_dir / "site.json"] = site_raw
    if p.log:
        print("--- shared header and footer")
        for line in p.log:
            print("  " + line)
    if dry_run:
        print("dry run: nothing written")
        return
    for path, data in writes.items():
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"written: {len(writes)} files. Regenerate (build_site_review.py) and check that the redrawn artboards match the canvas.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", default=".", help="the site folder (_site/<slug>)")
    ap.add_argument("--live", required=True, help="the folder the canvas's project/*.dc.html files were read into")
    ap.add_argument("--dry-run", action="store_true", help="print the changes, write nothing")
    args = ap.parse_args()
    try:
        pull(args.site, args.live, args.dry_run)
    except PullError as e:
        sys.exit(f"pull_canvas_edits: {e}")
