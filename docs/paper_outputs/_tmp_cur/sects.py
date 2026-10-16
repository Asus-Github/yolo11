import re
with open("word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()
sects = list(re.finditer(r'<w:sectPr[^>]*>.*?</w:sectPr>', xml, re.S))
print("num sectPr:", len(sects))
for i,m in enumerate(sects):
    block = m.group(0)
    cols = re.search(r'<w:cols[^/]*/>', block)
    typ = re.search(r'<w:type w:val="([^"]*)"', block)
    start = m.start()
    pre = xml[max(0,start-2000):start]
    texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', pre)
    ctx = "".join(texts)[-80:]
    print(f"--- sect {i} at {start} type={typ.group(1) if typ else None} cols={cols.group(0) if cols else None}")
    print(f"    ctx before: ...{ctx}")
