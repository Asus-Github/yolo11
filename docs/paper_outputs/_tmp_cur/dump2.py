import docx
from docx.oxml.ns import qn
from lxml import etree
import re

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body
paras = body.findall(qn('w:p'))

def strip_ns(s):
    return re.sub(r'xmlns:[a-zA-Z0-9]+="[^"]*"\s*', '', s)

for i in range(121, 128):
    p = paras[i]
    s = etree.tostring(p).decode()
    s = strip_ns(s)
    # remove wp: namespace prefix for readability
    s = s.replace('xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"', '')
    print(f"========== para {i} ==========")
    print(s)
    print()
