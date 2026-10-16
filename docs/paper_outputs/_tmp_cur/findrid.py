import re
with open("_tmp_cur/word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()
for rid in ["rId14","rId15","rId16","rId8","rId9","rId10","rId11","rId12","rId13"]:
    cnt = xml.count('r:embed="%s"' % rid)
    # find paragraph context
    idxs = [m.start() for m in re.finditer('r:embed="%s"' % rid, xml)]
    ctx = ""
    if idxs:
        i = idxs[0]
        pre = xml[max(0,i-3000):i]
        texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', pre)
        ctx = "".join(texts)[-50:]
    print(f"{rid}: count={cnt} ctx=...{ctx}")
