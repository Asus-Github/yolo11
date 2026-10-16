import docx
import sys

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    align = p.alignment
    style = p.style.name if p.style else "?"
    has_img = False
    for run in p.runs:
        if run.element.findall(f".//{NS}inline") or run.element.findall(f".//{NS}anchor"):
            has_img = True
    flag = "[IMG]" if has_img else ""
    print(f"{i:4d} | {style[:25]:25s} | align={align} | {flag} | {t[:90]}")
