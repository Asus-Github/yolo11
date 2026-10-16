import docx
from docx.oxml.ns import qn
from lxml import etree

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body
paras = body.findall(qn('w:p'))

# Print paragraphs 118 to 128 (around fig7, fig8, and discussion)
for i in range(118, 130):
    if i >= len(paras):
        break
    p = paras[i]
    txt = "".join(t.text or "" for t in p.iter(qn('w:t'))).strip()
    pPr = p.find(qn('w:pPr'))
    has_sect = pPr is not None and pPr.find(qn('w:sectPr')) is not None
    jc = p.find(qn('w:pPr'))
    align = None
    if pPr is not None:
        jc_el = pPr.find(qn('w:jc'))
        if jc_el is not None:
            align = jc_el.get(qn('w:val'))
    # image?
    has_img = len(p.findall('.//' + qn('w:drawing'))) > 0
    print(f"--- para {i} | sect={has_sect} | align={align} | img={has_img} | {txt[:80]}")
    if has_sect:
        sectPr = pPr.find(qn('w:sectPr'))
        cols = sectPr.find(qn('w:cols'))
        cnum = cols.get(qn('w:num')) if cols is not None else None
        print(f"      sectPr cols num={cnum}")
