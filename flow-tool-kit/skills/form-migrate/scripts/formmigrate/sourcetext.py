"""Text blocks from a captured source page, with their own formatting.

Legal and policy text (releases, waivers, conflict of interest policies) keeps the source's layout word for word:
centered headings, numbering, indented sub-items, underlines and blank lines. Re-flowing it into plain paragraphs
loses structure the organization's lawyer chose, so the rule is: match the source's formatting exactly.
Body text is set at 16px inside the rich text, so it is readable wherever it renders.

    from formmigrate import sourcetext
    html = sourcetext.block_html("sources/board-release/form.html", "tfa_236", start="Article I</div>")

FormAssembly puts each text block in `<div class="htmlSection" id="tfa_N"><div class="htmlContent" id="tfa_N-HTML">`;
`block_ids()` lists them in page order with the legend of the fieldset each sits in.
"""
import pathlib
import re

BODY_STYLE = "font-size: 16px; line-height: 1.5"


def _clean(body):
    """Office class names and inline font sizes out, so the 16px body sets the size; whitespace collapsed."""
    body = re.sub(r'\s*class="Mso\w+"', "", body)
    body = re.sub(r"font-size:\s*[^;\"]+;?\s*", "", body)
    body = re.sub(r'\s*style="\s*"', "", body)
    body = re.sub(r"<span>(.*?)</span>", r"\1", body, flags=re.S)
    body = re.sub(r"\s+", " ", body)
    # Drop the space only where a block tag meets another tag; between inline tags it is a word space
    # (`<i> </i>`, `</b> <i>`), and dropping it would glue two words together
    body = re.sub(r"(</?(?:%s)\b[^>]*>) (?=<)" % BLOCK_TAGS, r"\1", body)
    body = re.sub(r"> (?=</?(?:%s)\b)" % BLOCK_TAGS, ">", body).strip()
    return re.sub(r"<p[^>]*>\s*</p>", "", body)


BLOCK_TAGS = "p|div|ul|ol|li|br|table|thead|tbody|tr|td|th|h[1-6]|blockquote|hr"


def block_html(page, html_id, start=None, body_style=BODY_STYLE):
    """The block's markup with Office class names and empty paragraphs removed, whitespace collapsed, wrapped in a
    16px body. `start` trims everything before the first tag that contains it (a title the section header repeats)."""
    raw = pathlib.Path(page).read_text(errors="replace")
    at = raw.index(f'id="{html_id}-HTML"')
    body = raw[raw.index(">", at) + 1:raw.index("</div></div>\n", at)]
    body = _clean(body)
    if start:
        body = body[body.rindex("<", 0, body.index(start)):]
    return f'<div style="{body_style}">{body}</div>' if body_style else body


def label_html(page, field_id, body_style=BODY_STYLE):
    """A field's label in its own formatting (bold, italics), for a section's text when the label is the long question.
    Office class names, empty paragraphs and inline font sizes are removed, so the 16px body sets the size."""
    raw = pathlib.Path(page).read_text(errors="replace")
    body = re.search(rf'<label[^>]*for="{field_id}"[^>]*>(.*?)</label>', raw, re.S).group(1)
    body = _clean(body)
    if not body.startswith("<p"):
        body = f"<p>{body}</p>"
    return f'<div style="{body_style}">{body}</div>' if body_style else body


def block_ids(page):
    """[(html_id, legend)] for every FormAssembly text block, in page order."""
    raw = pathlib.Path(page).read_text(errors="replace")
    out, legend = [], ""
    for m in re.finditer(r'<legend[^>]*>(.*?)</legend>|<div class="htmlSection" id="(tfa_\d+)"', raw, re.S):
        if m.group(1) is not None:
            legend = re.sub(r"<[^>]+>|&nbsp;", " ", m.group(1)).strip()
        else:
            out.append((m.group(2), legend))
    return out
