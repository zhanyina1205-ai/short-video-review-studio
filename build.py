"""Build an entirely static distribution with same-origin OCR and analysis assets."""
from pathlib import Path
import json
from shutil import copyfile
from analysis import FIELDS

dist = Path("dist")
vendor = dist / "vendor"
vendor.mkdir(parents=True, exist_ok=True)
for name in ("style.css", "app.js", "analysis.py", "browser.js"):
    copyfile(name, dist / name)
copyfile("skill/scripts/report.html", dist / "report.html")
(dist / "fields.json").write_text(json.dumps(list(FIELDS), ensure_ascii=False))
html = Path("index.html").read_text().replace('href="/style.css"', 'href="./style.css"')
html = html.replace('<script defer src="/app.js">','<script defer src="./browser.js"></script><script defer src="./app.js">')
html = html.replace("本地工作空间","当前浏览器工作空间").replace("在本机识别","在当前浏览器识别")
(dist / "index.html").write_text(html)
packages = Path("node_modules")
for name in ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"):
    copyfile(packages / "pyodide" / name, vendor / name)
for name in ("tesseract.min.js","worker.min.js","worker.min.js.LICENSE.txt","tesseract.min.js.LICENSE.txt"):
    copyfile(packages / "tesseract.js/dist" / name, vendor / name)
for name in ("tesseract-core-lstm.wasm.js","tesseract-core-simd-lstm.wasm.js","LICENSE"):
    copyfile(packages / "tesseract.js-core" / name, vendor / name)
for lang in ("chi_sim","eng"):
    name = lang + ".traineddata.gz"
    copyfile(packages / "@tesseract.js-data" / lang / "4.0.0_best_int" / name, vendor / name)
