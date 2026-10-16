import docx
from docx.oxml.ns import qn

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body
paras = body.findall(qn('w:p'))
print("total paras:", len(paras))
for i, p in enumerate(paras):
    drawings = p.findall('.//' + qn('w:drawing'))
    if drawings:
        txt = "".join(t.text or "" for t in p.iter(qn('w:t'))).strip()
        # count inline vs anchor
        inline = p.findall('.//' + qn('wp:inline'))
        anchor = p.findall('.//' + qn('wp:anchor'))
        print(f"para {i:4d} | drawings={len(drawings)} inline={len(inline)} anchor={len(anchor)} | {txt[:60]}")
