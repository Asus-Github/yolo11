import docx
from docx.oxml.ns import qn

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body
paras = body.findall(qn('w:p'))
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
for i, p in enumerate(paras):
    blips = p.findall('.//' + A + 'blip')
    if blips:
        txt = "".join(t.text or "" for t in p.iter(qn('w:t'))).strip()
        ids = [b.get(R + 'embed') for b in blips]
        pPr = p.find(qn('w:pPr'))
        has_sect = pPr is not None and pPr.find(qn('w:sectPr')) is not None
        cnum = None
        if has_sect:
            cols = pPr.find(qn('w:sectPr')).find(qn('w:cols'))
            cnum = cols.get(qn('w:num')) if cols is not None else None
        print(f"para {i:4d} | imgs={ids} | sectEnd cols={cnum} | {txt[:50]}")
