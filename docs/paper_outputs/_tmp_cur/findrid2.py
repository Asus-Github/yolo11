import re
with open("_tmp_cur/word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()
for rid in ["rId14","rId15"]:
    for m in re.finditer(re.escape(rid), xml):
        i = m.start()
        print(f"=== {rid} at {i} ===")
        print(xml[max(0,i-400):i+200])
        print()
