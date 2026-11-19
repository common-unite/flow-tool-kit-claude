#!/usr/bin/env python3
"""Download the picked images, ready to load into the org, and write review copies for a design canvas.

    python3 brand_assets.py _brand/<slug> [--file logo=path/to/logo.png ...] [--focal 0.5,0.4]

Reads brand-kit.json (the asset name of each role) and picked-files.json (each role's address on the site), both written
by brandkit.py confirm, and writes into the brand folder:

- assets/<role>.<ext>: the file to load into the org. A WebP or GIF becomes PNG or JPEG, because the Flow Tool Kit image
  picker lists only PNG, JPG and SVG files; anything wider than 2000px is scaled down to 2000px.
- canvas/<role>.<ext>: the copy a review canvas uploads. The banner is cropped to 3:1 around its focal point (--focal x,y
  from the top left, 0 to 1, else the kit's bannerFocal, else a little above the middle), so a cover crop never cuts
  through the subject. An SVG whose fills are CSS classes gets them written inline, because some viewers strip <style>
  and the logo would draw black.
- assets/manifest.json: per role the file, its source address, MD5 (the org's file checksum, used to find a copy already
  in the org), size, and the asset name.

--file role=path uses a file the person supplied (an upload in chat, a file from the organization) instead of downloading.
A site that refuses downloads (HTTP 403 from bot protection) needs this.

Pillow (pip install pillow) converts, scales and crops. Without it, PNG, JPEG and SVG files are kept as they are, the
banner is not cropped, and a WebP or GIF is reported for conversion before it is loaded.
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import sys

from webfetch import POLITE

MAX_WIDTH = 2000
EXT = {"image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
PICKER_TYPES = (".png", ".jpg", ".jpeg", ".svg")


def role_file(role):
    """logoAlternate -> logo-alternate, photos/Riverside_Photo_Harvest -> photos/Riverside_Photo_Harvest."""
    return role if role.startswith("photos/") else re.sub(r"(?<!^)([A-Z])", r"-\1", role).lower()


def kind_of(data, url="", content_type=""):
    head = data[:512].lstrip()
    if head.startswith(b"<svg") or head.startswith(b"<?xml") and b"<svg" in data[:2048]:
        return ".svg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return EXT.get(content_type) or pathlib.Path(url.split("?")[0]).suffix.lower() or ".bin"


def inline_svg_fills(svg):
    """CSS class fills and strokes (.cls-1{fill:#2f6b3a}) written onto each element; the <style> dropped."""
    rules = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", " ".join(re.findall(r"<style[^>]*>(.*?)</style>", svg, re.S))):
        props = dict((k.strip(), v.strip()) for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body))
        for sel in selectors.split(","):
            m = re.fullmatch(r"\s*\.([\w-]+)\s*", sel)
            if m:
                rules.setdefault(m.group(1), {}).update(props)
    svg = re.sub(r"<style[^>]*>.*?</style>", "", svg, flags=re.S)
    svg = re.sub(r"<defs>\s*</defs>", "", svg)

    def apply(m):
        attrs = "".join(f' {k}="{v}"' for cls in m.group(2).split() for k, v in rules.get(cls, {}).items()
                        if k in ("fill", "stroke", "stroke-width", "opacity", "fill-opacity", "fill-rule"))
        return f"{m.group(1)}{attrs}"
    return re.sub(r'(<[a-zA-Z]+[^>]*?)\sclass="([^"]+)"', apply, svg)


def crop_box(width, height, focal=None, ratio=3.0):
    """(left, top, right, bottom) of the ratio:1 crop around the focal point; None when the image is already that wide."""
    if not width or not height or width / height >= ratio:
        return None
    fx, fy = focal or (0.5, 0.4)
    crop_height = int(width / ratio)
    top = int(min(max(fy * height - crop_height / 2, 0), height - crop_height))
    return 0, top, width, top + crop_height


def prepare(data, ext, banner=False, focal=None):
    """(file bytes, ext, canvas bytes, canvas ext, notes) for one image."""
    notes = []
    if ext == ".svg":
        text = data.decode("utf-8", "replace")
        canvas = inline_svg_fills(text) if "<style" in text else text
        if canvas != text:
            notes.append("CSS fills written inline in the canvas copy")
        return data, ext, canvas.encode("utf-8"), ext, notes
    try:
        from PIL import Image
    except ImportError:
        if ext not in PICKER_TYPES:
            notes.append(f"{ext} is not listed by the image picker: install Pillow (pip install pillow) and run again, or convert it to PNG")
        if banner:
            notes.append("banner not cropped for the canvas (Pillow not installed)")
        return data, ext, data, ext, notes
    image = Image.open(io.BytesIO(data))
    transparent = image.mode in ("RGBA", "LA", "P") or "transparency" in image.info
    out_ext = ext if ext in PICKER_TYPES else (".png" if transparent else ".jpg")
    if out_ext != ext:
        notes.append(f"converted {ext} to {out_ext}: the image picker lists PNG, JPG and SVG only")
    if image.width > MAX_WIDTH:
        image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)))
        notes.append(f"scaled to {MAX_WIDTH}px wide")

    def save(img, extension):
        buffer = io.BytesIO()
        if extension == ".png":
            img.convert("RGBA" if transparent else "RGB").save(buffer, "PNG", optimize=True)
        else:
            img.convert("RGB").save(buffer, "JPEG", quality=85)
        return buffer.getvalue()

    unchanged = out_ext == ext and not any(n.startswith("scaled") for n in notes)
    file_bytes = data if unchanged else save(image, out_ext)
    canvas_bytes = file_bytes
    if banner:
        box = crop_box(image.width, image.height, focal)
        if box:
            canvas_bytes = save(image.crop(box), out_ext)
            notes.append(f"canvas copy cropped to 3:1 at y {box[1]} of {image.height}")
    return file_bytes, out_ext, canvas_bytes, out_ext, notes


def pixel_size(data, ext):
    if ext == ".svg":
        return 0, 0
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            return image.size
    except Exception:
        from site_crawl import image_size
        return image_size(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", help="the brand folder, _brand/<slug>")
    parser.add_argument("--file", action="append", default=[], help="role=path: use this file for the role instead of downloading")
    parser.add_argument("--focal", help="banner focal point x,y from the top left, 0 to 1")
    a = parser.parse_args(argv)
    folder = pathlib.Path(a.folder)
    kit = json.loads((folder / "brand-kit.json").read_text(encoding="utf-8"))
    picked_path = folder / "picked-files.json"
    picked = json.loads(picked_path.read_text(encoding="utf-8")) if picked_path.exists() else {}
    given = dict(item.split("=", 1) for item in a.file)
    focal = tuple(float(v) for v in a.focal.split(",")) if a.focal else (tuple(kit["bannerFocal"]) if kit.get("bannerFocal") else None)
    names = dict(kit.get("assets") or {})
    for name in names.pop("photos", []) or []:
        names["photos/" + name] = name
    roles = sorted(set(picked) | set(given))
    (folder / "assets").mkdir(exist_ok=True)
    (folder / "canvas").mkdir(exist_ok=True)
    manifest_path = folder / "assets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    failed = []
    for role in roles:
        source = given.get(role) or picked.get(role)
        try:
            if role in given:
                data = pathlib.Path(given[role]).read_bytes()
                ext = kind_of(data, given[role])
            else:
                data, content_type = POLITE.body(picked[role])
                ext = kind_of(data, picked[role], content_type)
        except Exception as error:
            failed.append(role)
            print(f"{role}: {source} could not be read ({error}). Save the image and pass --file {role}=<path>.")
            continue
        file_bytes, out_ext, canvas_bytes, canvas_ext, notes = prepare(data, ext, banner=role == "banner", focal=focal)
        stem = role_file(role)
        for directory in ("assets", "canvas"):
            parent = folder / directory / pathlib.Path(stem).parent
            parent.mkdir(parents=True, exist_ok=True)
            for old in parent.glob(pathlib.Path(stem).name + ".*"):
                old.unlink()
        (folder / "assets" / (stem + out_ext)).write_bytes(file_bytes)
        (folder / "canvas" / (stem + canvas_ext)).write_bytes(canvas_bytes)
        width, height = pixel_size(file_bytes, out_ext)
        manifest[role] = {"file": stem + out_ext, "canvas": "../canvas/" + stem + canvas_ext, "source": source,
                          "md5": hashlib.md5(file_bytes).hexdigest(), "width": width, "height": height,
                          "assetName": names.get(role), **({"notes": notes} if notes else {})}
        print(f"{role}: assets/{stem}{out_ext} ({width}x{height}){' (' + '; '.join(notes) + ')' if notes else ''}")
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"{manifest_path}: {len(manifest)} files" + (f"; {len(failed)} could not be read: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
