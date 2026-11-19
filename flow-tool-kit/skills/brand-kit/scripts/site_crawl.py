#!/usr/bin/env python3
"""Crawl every page an organization's site navigation links to, and list its images, headings, buttons and copy.

    python3 site_crawl.py https://www.example.org/ --program https://www.example.org/volunteer/ --out _brand/<slug>/site-crawl.json [--name "Riverside Community Garden"]

Standard library only, no browser. It fetches the start page (following its redirect first, so a bare host that redirects
to www is crawled as www), collects every same-site link on it (header and footer menus, every level, body links), fetches
those pages a few at a time and records for each: the title, h1 and h2 headings, body button labels, readable copy, and
every image: img src and the largest srcset entry, lazy data-* attributes, picture sources, noscript copies, gallery links
to image files, inline and <style> backgrounds, image URLs in page scripts and JSON, og:image and favicons. Images are
merged across pages (one entry, many pages; one media file served at many sizes is one image), measured from their file
headers, and given a group and a size fit for the picker.

Why the whole site: the photos people want are rarely all on the home page, and the picker is where the list narrows,
never the scan.

Exit code 3 means the site could not be reached at all (for example a code sandbox with no outside network): read the
pages with a web fetch tool instead (SKILL.md, "When the site cannot be crawled").
"""
import argparse
import base64
import concurrent.futures
import datetime
import html as htmllib
import json
import re
import struct
import sys
import urllib.parse
from html.parser import HTMLParser

from webfetch import POLITE, NetworkUnavailable

SKIP_LINK = re.compile(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|pptx?|mp4|mov)$|/wp-(content|admin|json|login)|/feed|/tag/|/author/|/page/\d|/category/|\?|#|mailto:|tel:", re.I)
SKIP_IMAGE = re.compile(r"/plugins/|/themes/[^/]+/(core|includes)/|fontawesome|emoji|gravatar|pixel|spacer|\.gif$|data:image|googleusercontent", re.I)
IMAGE_URL = re.compile(r"\.(jpe?g|png|webp|svg|avif)$", re.I)
IN_TEXT = re.compile(r"https?:\\?/\\?/[^\s\"'<>()]+?\.(?:jpe?g|png|webp|avif|svg)(?=[\"'\s?)<>]|$)", re.I)
SITE_BUILDER_URI = re.compile(r"\"uri\"\s*:\s*\"([0-9a-f]{6}_[0-9a-f]+~mv2\.(?:jpe?g|png|webp))\"", re.I)
SITE_BUILDER_MEDIA = re.compile(r"^https?://static\.wixstatic\.com/media/([^/]+?\.(?:jpe?g|png|webp|gif|svg))", re.I)
# A header built from divs: an id such as SITE_HEADER or masthead, or a class that is exactly a header word (a body class
# such as theme-builder-header-123 is not)
HEADER_ID = re.compile(r"header|masthead", re.I)
HEADER_CLASS = re.compile(r"^(site-?header|header|masthead|navbar|top-?bar|branding|site-branding)$", re.I)
SOCIAL = re.compile(r"facebook|instagram|linkedin|youtube|twitter|tiktok|pinterest|\bx icon\b|social", re.I)
LAZY_ATTRS = ("data-src", "data-lazy-src", "data-original", "data-bg", "data-background", "data-image", "data-pin-media", "data-full", "data-large-file")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
TITLE_SPLIT = re.compile(r"\s+[|:" + chr(0x2013) + chr(0x2014) + r"\-]\s+")  # "Program | Organization", any dash between
PERSON_ALT = re.compile(r"^[A-Z][a-zA-Z'\-]+( [A-Z][a-zA-Z'\-]+){1,2}$")
DOCUMENTS = re.compile(r"brochure|annual-report|impact-report|newsletter|flyer|digest|/en-espanol/|spanish-version", re.I)
SHOP = re.compile(r"/(shop|store|product|products|catalog|cart)[-/]", re.I)


def canonical(url):
    """One image, one URL: a site builder's media file at any size (w_444, w_79, fill or crop) is the media id's
    original, and an optimizer's resized copy is the file it was made from."""
    m = SITE_BUILDER_MEDIA.match(url)
    if m:
        return f"https://static.wixstatic.com/media/{m.group(1)}"
    return re.sub(r"\.bv_resized_\w+\.\w+(?=\.bv\.webp$)", "", url)


def squash(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def host_stem(host):
    """The site's own name in its address: riversidegarden for www.riversidegarden.example.org, gardenclub for gardenclub.example.co.uk."""
    return host.lower().removeprefix("www.").split(".")[0]


def org_name(title, host):
    """The organization's name from the home page title: the part that matches the domain or shares its words ("Riverside
    Community Garden - Growing food together" on www.riversidegarden.example.org), else the shortest part ("Home | Riverside Garden")."""
    parts = [p for p in TITLE_SPLIT.split(title or "") if p.strip()]
    stem = squash(host_stem(host))
    for part in parts:
        if squash(part) and (squash(part) in stem or stem in squash(part)):
            return part.strip()
    overlap = lambda part: sum(1 for w in re.findall(r"[a-z0-9]{3,}", part.lower()) if w in stem)
    best = max(parts, key=overlap, default="")
    if best and overlap(best):
        return best.strip()
    parts = [p for p in parts if squash(p) not in ("home", "welcome")] or parts
    return min(parts, key=len).strip() if parts else ""


def srcset_urls(srcset):
    """Candidates of a srcset as (url, width), read the way browsers do: a URL runs to whitespace, so commas inside a URL
    (w_444,h_200,al_c) are part of it, and only a comma after the URL's descriptor separates candidates."""
    out, text, i = [], srcset or "", 0
    while i < len(text):
        while i < len(text) and (text[i].isspace() or text[i] == ","):
            i += 1
        start = i
        while i < len(text) and not text[i].isspace():
            i += 1
        url = text[start:i]
        descriptor = ""
        if url.endswith(","):
            url = url.rstrip(",")
        else:
            start = i
            while i < len(text) and text[i] != ",":
                i += 1
            descriptor = text[start:i].strip()
        if url:
            m = re.match(r"(\d+(?:\.\d+)?)([wx])", descriptor)
            out.append((url, float(m.group(1)) * (1 if m.group(2) == "w" else 1000) if m else 0))
    return out


class Page(HTMLParser):
    def __init__(self, url, home):
        super().__init__(convert_charrefs=True)
        self.url, self.home = url, home
        self.title, self.site_name = "", ""
        self.headings, self.copy, self.buttons = [], [], []
        self.images, self.links = {}, set()
        self.stylesheets, self.styles, self.fonts_links, self.theme_color = [], [], [], ""
        self.open = []  # (tag, header-ish, home link) for every element still open
        self.text_target, self.buffer = None, []
        self.raw = {"script": 0, "style": 0}
        self.raw_text = []
        self.anchor_depth, self.anchor_buffer, self.anchor_class = 0, [], ""
        self.order = 0

    def absolute(self, value):
        if not value:
            return None
        value = htmllib.unescape(value.strip()).replace("\\/", "/")
        if value.startswith("data:"):
            return None
        try:
            joined = urllib.parse.urljoin(self.url, value)
        except ValueError:
            return None
        split = urllib.parse.urlsplit(joined)
        if split.scheme not in ("http", "https"):
            return None
        return urllib.parse.urlunsplit((split.scheme, split.netloc, split.path, "", ""))

    def where(self):
        if any(header for _, header, _ in self.open):
            return "header"
        if any(tag == "footer" for tag, _, _ in self.open):
            return "footer"
        return "body"

    def in_home_link(self):
        return any(home for _, _, home in self.open)

    def add_image(self, src, kind, alt="", width=0, height=0):
        if (src or "").startswith("data:image/svg+xml"):
            # A lazy loader's placeholder: an SVG that names the real image inside it
            body = src.split(",", 1)[-1]
            try:
                body = base64.b64decode(body).decode("utf-8", "replace") if ";base64" in src[:40] else urllib.parse.unquote(body)
            except ValueError:
                return
            for match in IN_TEXT.finditer(body):
                self.add_image(match.group(0), kind, alt, width, height)
            return
        url = self.absolute(src)
        if not url or SKIP_IMAGE.search(url):
            return
        url = canonical(url)
        if not IMAGE_URL.search(url):
            return
        if url in self.images:
            if alt and not self.images[url]["alt"]:
                self.images[url]["alt"] = alt.strip()
            return
        self.order += 1
        self.images[url] = {"url": url, "kind": kind, "alt": (alt or "").strip(), "width": width, "height": height,
                            "where": self.where(), "homeLink": self.in_home_link(), "order": self.order}

    @staticmethod
    def largest(srcset):
        candidates = srcset_urls(srcset)
        return max(candidates, key=lambda c: c[1])[0] if candidates else None

    @staticmethod
    def number(value):
        try:
            return int(float(re.sub(r"[^\d.]", "", value or "") or 0))
        except ValueError:
            return 0

    def handle_starttag(self, tag, attrs):
        attributes = {k: v or "" for k, v in attrs}
        if tag in self.raw:
            self.raw[tag] += 1
        header = tag in ("header", "nav") or attributes.get("role") == "banner" or (tag not in ("html", "body", "main") and (
            bool(HEADER_ID.search(attributes.get("id", ""))) or any(HEADER_CLASS.match(c) for c in attributes.get("class", "").split())))
        home = tag == "a" and self.absolute(attributes.get("href")) in (self.home, self.home.rstrip("/"))
        if tag not in VOID:
            self.open.append((tag, header, home))
        if tag == "a":
            self.anchor_depth += 1
            self.anchor_buffer = []
            self.anchor_class = attributes.get("class", "")
            href = attributes.get("href")
            if href:
                url = self.absolute(href)
                if url and IMAGE_URL.search(url):
                    self.add_image(href, "gallery link")
                elif url and not SKIP_LINK.search(href):
                    self.links.add(url.rstrip("/") + "/")
        if tag == "img":
            src = (self.largest(attributes.get("srcset") or attributes.get("data-srcset") or attributes.get("data-lazy-srcset"))
                   or next((attributes[a] for a in LAZY_ATTRS if attributes.get(a)), None) or attributes.get("src"))
            self.add_image(src, "image", attributes.get("alt", ""), self.number(attributes.get("width")), self.number(attributes.get("height")))
        elif tag != "a":
            for name in LAZY_ATTRS:  # lazy backgrounds and gallery items on any element
                if attributes.get(name):
                    self.add_image(attributes[name], "lazy image")
        if tag == "source" and (attributes.get("srcset") or attributes.get("data-srcset")):
            self.add_image(self.largest(attributes.get("srcset") or attributes.get("data-srcset")), "picture source")
        if tag == "meta" and attributes.get("property") == "og:image":
            self.add_image(attributes.get("content"), "share image")
        if tag == "meta" and attributes.get("property") == "og:site_name":
            self.site_name = attributes.get("content", "").strip()
        if tag == "meta" and attributes.get("name") == "theme-color":
            self.theme_color = attributes.get("content", "").strip()
        rel = (attributes.get("rel") or "").lower()
        if tag == "link" and "icon" in rel:
            self.add_image(attributes.get("href"), "favicon")
        if tag == "link" and "stylesheet" in rel and attributes.get("href"):
            href = htmllib.unescape(attributes["href"].strip())
            if "fonts.googleapis.com" in href:
                self.fonts_links.append(urllib.parse.urljoin(self.url, href))
            else:
                full = urllib.parse.urljoin(self.url, href)
                if full.startswith("http"):
                    self.stylesheets.append(full)
        for match in re.finditer(r"url\(['\"]?([^'\")]+)", attributes.get("style") or ""):
            self.add_image(match.group(1), "background")
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "title") and not any(self.raw.values()):
            self.text_target = tag
            self.buffer = []

    def handle_endtag(self, tag):
        if tag in self.raw and self.raw[tag]:
            self.raw[tag] -= 1
            text = "".join(self.raw_text)
            self.raw_text = []
            if tag == "style":
                self.styles.append(text)
                for match in re.finditer(r"url\(['\"]?([^'\")]+\.(?:jpe?g|png|webp|svg))", text, re.I):
                    self.add_image(match.group(1), "background")
            else:  # script-loaded galleries: image URLs in the page's scripts and JSON
                for match in IN_TEXT.finditer(text):
                    self.add_image(match.group(0), "script image")
                for match in SITE_BUILDER_URI.finditer(text):
                    self.add_image("https://static.wixstatic.com/media/" + match.group(1), "script image")
        if tag == "a" and self.anchor_depth:
            self.anchor_depth -= 1
            text = re.sub(r"\s+", " ", "".join(self.anchor_buffer)).strip()
            if (text and len(text) <= 40 and self.where() == "body" and re.search(r"button|btn|cta", self.anchor_class or "")
                    and text not in self.buttons):
                self.buttons.append(text)
        if tag == self.text_target:
            text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
            if tag == "title":
                self.title = self.title or text  # the page's, not an inline SVG's <title> further down
            elif text and self.where() == "body":
                if tag in ("h1", "h2") and len(self.headings) < 12:
                    self.headings.append(text)
                self.copy.append({"tag": tag, "text": text})
            self.text_target = None
        if tag not in VOID:
            for i in range(len(self.open) - 1, -1, -1):
                if self.open[i][0] == tag:
                    del self.open[i:]
                    break

    def handle_data(self, data):
        if any(self.raw.values()):
            self.raw_text.append(data)
        if self.anchor_depth:
            self.anchor_buffer.append(data)
        if self.text_target:
            self.buffer.append(data)


def image_size(data):
    """The pixel size from the first bytes of a PNG, JPEG, GIF or WebP file. SVG and anything unreadable give (0, 0)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        if data[12:16] == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3fff, h & 0x3fff
        if data[12:16] == b"VP8X":
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    if data[:2] == b"\xff\xd8":
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            length = struct.unpack(">H", data[index + 2:index + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[index + 5:index + 9])
                return width, height
            index += 2 + length
    return 0, 0


def measure(url):
    """Read the real pixel size from the first 64 KB of the file."""
    try:
        with POLITE.open(url, {"Range": "bytes=0-65535"}) as response:
            data = response.read(65536)
    except Exception:
        return 0, 0
    return image_size(data)


def fit_for(width, height, group):
    """Where a picture of this size can go in a form or on a site page. The scan measures; the picker shows the fit."""
    if group in ("logo", "favicon", "icons and badges", "partner logos"):
        return group
    if not width or not height:
        return "unknown size"
    aspect = width / height
    if width >= 1000 and aspect >= 1.5:
        return "banner"
    if width >= 700 and aspect >= 1.5:
        return "banner (small)"
    if width >= 400 and aspect >= 1.5:
        return "wide block"
    if width >= 400 and 1.1 <= aspect < 1.5:
        return "tile"
    if width >= 200 and 0.9 <= aspect < 1.1:
        return "square"
    if aspect < 0.9:
        return "portrait"
    return "small"


def humanize(url):
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    name = re.sub(r"\.(jpe?g|png|webp|svg|avif)$", "", name, flags=re.I)
    name = re.sub(r"~mv2$", "", name)
    name = re.sub(r"[-_]?\d{2,4}x\d{2,4}(-\d)?$", "", name)
    return re.sub(r"[-_]+", " ", name).strip()


def own_names(name, host, titles):
    """What the organization calls itself: its name, the domain's stem, its program names (the first part of a page title
    with two or more words, "Youth Garden Club | Riverside Community Garden"), and its initials, written "#rcg" because
    they must match a whole word of the alt text or file name ("RCG-02 Logo.png"), never letters inside another word."""
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    names = {squash(name), squash(host_stem(host))}
    for title in titles:
        first = TITLE_SPLIT.split(title or "")[0]
        if len(first.split()) >= 2 and squash(first) != squash(name):
            names.add(squash(first))
    names = {n for n in names if len(n) >= 3}
    if len(words) >= 2:
        names.add("#" + "".join(w[0] for w in words).lower())
    return names


def names_us(text, names):
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return any(n[1:] in tokens if n.startswith("#") else n in squash(text) for n in names)


def group_for(image, pages, names, total_pages=1):
    """The picker's group for one image. The organization's own logo is a logo: its alt text or file name says logo and names
    the organization or one of its programs, or it sits in the site's home link or header band on most pages, whatever the
    markup (some site builders make the header from divs). Another organization's logo stays a partner logo."""
    url, alt, where = image["url"].lower(), image["alt"], image["where"]
    width, height = image["width"], image["height"]
    page_paths = " ".join(pages).lower()
    text = f"{alt} {humanize(image['url'])}".lower()
    says_logo = bool(re.search(r"logo|wordmark|brandmark", text))
    if "favicon" in image["kind"] or re.search(r"favicon|site-icon|apple-touch-icon", url):
        return "favicon"
    if SOCIAL.search(text) or SOCIAL.search(url.rsplit("/", 1)[-1]):
        return "icons and badges"
    if says_logo and names_us(text, names):
        return "logo"
    # The top band: the image in the home link, or one of the first images in a header, on most pages of the site
    # (a post's own header image or a headshot sits on one page; the site's logo is on all of them)
    sitewide = len(pages) >= max(2, total_pages / 2) or total_pages <= 2
    top_band = sitewide and (image.get("homeLink") or (where == "header" and image.get("order", 99) <= 3))
    if top_band and image["kind"] in ("image", "picture source") and not PERSON_ALT.match(alt) and not (width >= 1000 and height >= 500):
        return "logo"
    if says_logo or "youtube" in url:
        return "partner logos"
    if PERSON_ALT.match(alt) or (re.search(r"/(staff|team|board)[-/]", page_paths) and width <= 500):
        return "people"
    if DOCUMENTS.search(url + " " + page_paths) or (height > width * 1.3 and width >= 400):
        return "documents"
    if re.search(r"badge|icon|graphic-only|transparent", url):
        return "icons and badges"
    if SHOP.search(url + " " + page_paths) and width <= 800 and image["kind"] != "background":
        return "shop and catalog"
    if image["kind"] == "background" or width >= 1000:
        return "banners"
    return "site photos"


def same_site(a, b):
    strip = lambda host: host.lower().removeprefix("www.")
    return strip(urllib.parse.urlsplit(a).netloc) == strip(urllib.parse.urlsplit(b).netloc)


def parse(url, home):
    page = Page(url, home)
    try:
        text, _ = POLITE.text(url)
        page.feed(text)
    except NetworkUnavailable:
        raise
    except Exception as error:
        return url, None, str(error)
    return url, page, None


def crawl(start_url, program="", name="", workers=4):
    """The whole crawl as a dict (what --out writes)."""
    _, final = POLITE.text(start_url)
    start = final.split("?")[0].split("#")[0].rstrip("/") + "/"
    _, home, error = parse(start, start)
    if error:
        raise RuntimeError("start page failed: " + error)
    urls = sorted({start, *(link for link in home.links if same_site(link, start))})
    program_url = program.rstrip("/") + "/" if program else ""
    if program_url:
        urls = sorted({*urls, program_url})
    program_path = urllib.parse.urlsplit(program_url).path if program_url else ""
    program_copy, pages, errors, images, titles, styles = [], {}, {}, {}, [], {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for url, page, failure in pool.map(lambda u: parse(u, start), urls):
            if failure:
                errors[url] = failure
                continue
            path = urllib.parse.urlsplit(url).path
            titles.append(page.title)
            pages[path] = {"title": page.title, "headings": page.headings, "imageCount": len(page.images), "buttons": page.buttons,
                           "copy": [block for block in page.copy if len(block["text"]) > 2][:120]}
            if path in ("/", program_path):  # the two pages whose look the stylesheet scan reads
                styles[path] = {"url": url, "stylesheets": page.stylesheets, "inlineStyles": page.styles,
                                "googleFonts": page.fonts_links, "themeColor": page.theme_color}
            for url_image, image in page.images.items():
                entry = images.setdefault(url_image, {**image, "pages": []})
                if path not in entry["pages"]:
                    entry["pages"].append(path)
                if image["width"] > entry["width"]:
                    entry["width"], entry["height"] = image["width"], image["height"]
                if image["alt"] and not entry["alt"]:
                    entry["alt"] = image["alt"]
                entry["homeLink"] = entry.get("homeLink") or image["homeLink"]
                entry["order"] = min(entry["order"], image["order"])
                if image["where"] == "header":
                    entry["where"] = "header"
            if program_path and path == program_path:
                program_copy = page.copy
    host = urllib.parse.urlsplit(start).netloc
    org = name or home.site_name or org_name(home.title, host)
    names = own_names(org, host, titles)
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        measured = dict(zip(images.keys(), pool.map(measure, images.keys())))
    result = []
    for image in images.values():
        width, height = measured.get(image["url"], (0, 0))
        if not width:
            width, height = image["width"], image["height"]
        group = group_for({**image, "width": width, "height": height}, image["pages"], names, len(pages))
        result.append({"url": image["url"], "label": image["alt"] or humanize(image["url"]), "alt": image["alt"], "kind": image["kind"],
                       "group": group, "fit": fit_for(width, height, group), "width": width, "height": height,
                       "size": f"{width}x{height}" if width else "", "pages": image["pages"], "page": image["pages"][0],
                       "program": bool(program_path) and program_path in image["pages"], "people": group == "people",
                       "homeLink": bool(image.get("homeLink")), "where": image["where"]})
    result.sort(key=lambda image: (not image["program"], image["group"], -image["width"], image["label"]))
    return {"start": start, "requested": start_url, "organization": org, "ownNames": sorted(names), "programPage": program_url,
            "crawledOn": datetime.date.today().isoformat(), "pages": pages, "errors": errors, "images": result,
            "programCopy": program_copy, "styleSources": styles}


def main(argv=None):
    arguments = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    arguments.add_argument("start")
    arguments.add_argument("--program", default="", help="the program or campaign page the form serves; its copy is kept in full")
    arguments.add_argument("--out", required=True)
    arguments.add_argument("--name", default="", help="the organization's name, for telling its logo from partners' (default: the site's own)")
    arguments.add_argument("--workers", type=int, default=4)
    arguments.add_argument("--delay", type=float, default=0.3, help="seconds between requests to the site")
    options = arguments.parse_args(argv)
    POLITE.delay = options.delay
    try:
        output = crawl(options.start, options.program, options.name, options.workers)
    except NetworkUnavailable as error:
        print(f"site unreachable from here: {error}. Read the pages with a web fetch tool instead (SKILL.md).", file=sys.stderr)
        return 3
    except Exception as error:
        print(f"start page failed: {error}", file=sys.stderr)
        return 1
    with open(options.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=1, ensure_ascii=False)
    groups, fits = {}, {}
    for image in output["images"]:
        groups[image["group"]] = groups.get(image["group"], 0) + 1
        fits[image["fit"]] = fits.get(image["fit"], 0) + 1
    if output["start"] != options.start.rstrip("/") + "/":
        print(f"{options.start} redirects to {output['start']}; crawled {urllib.parse.urlsplit(output['start']).netloc}")
    print(f"{len(output['pages'])} pages, {len(output['errors'])} errors, {len(output['images'])} images -> {options.out} "
          f"(organization: {output['organization']})")
    for group, count in sorted(groups.items(), key=lambda item: -item[1]):
        print(f"  {count:4d}  {group}")
    print("fit:", ", ".join(f"{fit} {count}" for fit, count in sorted(fits.items(), key=lambda item: -item[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
