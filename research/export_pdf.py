"""Export a markdown document to PDF via headless Chrome.

Run:  python research/export_pdf.py docs/paper.md   (writes docs/paper.pdf)
"""

import html as htmllib
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
# Math is written as GitHub renders it: $$...$$ blocks and $`...`$ inline. Typeset here with KaTeX.
MATH = re.compile(r"\$\$(.+?)\$\$|\$`(.+?)`\$", re.S)
RENDER_MATH = """document.querySelectorAll('.tex').forEach(e => katex.render(e.textContent, e,
  {displayMode: e.tagName === 'DIV', throwOnError: true}));"""
CSS = """  /* body font Charter, also used by the charts (research/figures.py) */
@page { size: Letter; margin: 0.9in 0.85in; }
body { font-family: "Charter", "Georgia", serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 4pt; }
h3:first-of-type { font-weight: normal; font-style: italic; color: #444; margin-top: 0; }
h2 { font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h2, h3 { page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 8pt 0; page-break-inside: avoid; }
th, td { border-bottom: 1px solid #ddd; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { border-bottom: 1.5px solid #888; }
img { width: 100%; page-break-inside: avoid; margin-top: 6pt; }
p:has(img) { page-break-inside: avoid; }
blockquote { margin: 6pt 18pt; color: #222; }
code, pre { font-family: "SF Mono", Menlo, monospace; font-size: 8.5pt; }
pre { background: #f6f6f4; padding: 6pt 8pt; white-space: pre-wrap; }
hr { border: none; border-top: 1px solid #ccc; margin: 10pt 0; }
em { color: #333; }
.keep { break-inside: avoid; page-break-inside: avoid; }
div.tex { margin: 6pt 0; font-size: 10pt; }
"""


def _text(el) -> str:
    return "".join(el.itertext()).strip()


def _is_lead(el) -> bool:
    """A heading, or a short line introducing what follows ("Results:", "... by year:")."""
    return el.tag in ("h1", "h2", "h3") or (el.tag == "p" and el.find("img") is None and _text(el).endswith(":"))


def keep_with_next(body: str) -> str:
    """Wrap each heading or lead-in line with the first table, list, figure or paragraph after it, and each
    figure with its caption, in a block Chrome will not split across pages (it ignores break-after: avoid)."""
    root = ET.fromstring(f"<div>{body}</div>")
    out, group = [], []
    for el in list(root):
        is_fig = el.tag == "p" and el.find("img") is not None
        if group and group[-1].tag == "p" and group[-1].find("img") is not None:  # figure waits for its caption
            if _text(el).startswith("Figure"):
                group.append(el)
                el = None
            out.append(group)
            group = []
            if el is None:
                continue
        short_intro = group and el.tag == "p" and not is_fig and len(_text(el)) < 220
        if _is_lead(el) or is_fig or short_intro:
            group.append(el)
            continue
        if group:
            group.append(el)
            out.append(group)
            group = []
        else:
            out.append([el])
    if group:
        out.append(group)
    html = []
    for g in out:
        inner = "".join(ET.tostring(e, encoding="unicode", method="html") for e in g)
        html.append(f'<div class="keep">{inner}</div>' if len(g) > 1 else inner)
    return "".join(html)


def with_math(text: str) -> tuple[str, list[str]]:
    """Swap math for placeholders so markdown leaves it alone; return the text and the HTML to put back."""
    found = []

    def stash(m):
        block, inline = m.group(1), m.group(2)
        tag = "div" if block is not None else "span"
        found.append(f'<{tag} class="tex">{htmllib.escape((block or inline).strip())}</{tag}>')
        return f"MATHSLOT{len(found) - 1}X"

    return MATH.sub(stash, text), found


def main(src: str) -> None:
    md = Path(src).resolve()
    text, math = with_math(md.read_text())
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    for i, frag in enumerate(math):
        body = body.replace(f"<p>MATHSLOT{i}X</p>", frag).replace(f"MATHSLOT{i}X", frag)
    body = keep_with_next(body)
    head = (f'<link rel="stylesheet" href="{KATEX}/katex.min.css"><script src="{KATEX}/katex.min.js"></script>'
            if math else "")
    script = f"<script>{RENDER_MATH}</script>" if math else ""
    html = (f'<!doctype html><html><head><meta charset="utf-8"><base href="{md.parent.as_uri()}/">'
            f"<style>{CSS}</style>{head}</head><body>{body}{script}</body></html>")
    out = md.with_suffix(".pdf")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=20000",
                    f"--print-to-pdf={out}", Path(f.name).as_uri()], check=True, capture_output=True)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
