"""Export a markdown document to PDF via headless Chrome.

Run:  python research/export_pdf.py docs/paper.md   (writes docs/paper.pdf)
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
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
"""


def main(src: str) -> None:
    md = Path(src).resolve()
    body = markdown.markdown(md.read_text(), extensions=["tables", "fenced_code"])
    html = (f'<!doctype html><html><head><meta charset="utf-8"><base href="{md.parent.as_uri()}/">'
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    out = md.with_suffix(".pdf")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", Path(f.name).as_uri()], check=True, capture_output=True)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
