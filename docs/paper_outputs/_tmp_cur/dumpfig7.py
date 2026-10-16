import docx
from docx.oxml.ns import qn
from lxml import etree

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body
paras = body.findall(qn('w:p'))
for i in range(121, 128):
    p = paras[i]
    s = etree.tostring(p, pretty_print=True).decode()
    print(f"========== para {i} ==========")
    print(s[:2500])
    print()
