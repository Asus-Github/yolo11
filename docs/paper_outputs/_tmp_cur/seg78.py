import re
with open("_tmp_cur/word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()
seg = xml[260200:265600]
# strip namespace decls
seg = re.sub(r'xmlns:[a-zA-Z0-9]+="[^"]*"', '', seg)
seg = seg.replace('<w:', '<').replace('</w:', '</')
# add newlines for readability
seg = seg.replace('><', '>\n<')
print(seg)
