import docx

NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"

def inspect(path, label):
    print(f"\n===== {label}: {path} =====")
    doc = docx.Document(path)
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
        # only print lines mentioning 图/表/注 or images
        if has_img or any(k in t for k in ["图", "表", "注", "Fig", "Table"]):
            print(f"{i:4d} | {style[:20]:20s} | align={align} | {flag} | {t[:100]}")

inspect("参考-层次差异特征与跨尺度增强的小目标检测算法 .docx", "REFERENCE")
