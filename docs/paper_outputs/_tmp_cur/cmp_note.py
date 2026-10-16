import docx
from docx.oxml.ns import qn

def analyze(path, label):
    print(f"\n===== {label} =====")
    doc = docx.Document(path)
    body = doc.element.body
    paras = body.findall(qn('w:p'))
    sections = []
    for i, p in enumerate(paras):
        pPr = p.find(qn('w:pPr'))
        if pPr is None:
            continue
        sectPr = pPr.find(qn('w:sectPr'))
        if sectPr is not None:
            cols = sectPr.find(qn('w:cols'))
            num = cols.get(qn('w:num')) if cols is not None else None
            sections.append((i, num))
    final_sect = body.find(qn('w:sectPr'))
    if final_sect is not None:
        cols = final_sect.find(qn('w:cols'))
        num = cols.get(qn('w:num')) if cols is not None else None
        sections.append((len(paras)-1, num))
    end_indices = [s[0] for s in sections]
    sec_idx = 0
    for i in range(len(paras)):
        while sec_idx < len(sections)-1 and sections[sec_idx][0] < i:
            sec_idx += 1
        cur = sections[sec_idx]
        txt = "".join(t.text or "" for t in paras[i].iter(qn('w:t'))).strip()
        if txt.startswith("注"):
            print(f"  para {i:4d} | cols={cur[1]} | {txt[:60]}")

analyze("中文版北核_DWCA-P2-哈理工学报格式版.pre-notefix.docx", "PRE-NOTEFIX")
analyze("中文版北核_DWCA-P2-哈理工学报格式版.docx", "CURRENT")
