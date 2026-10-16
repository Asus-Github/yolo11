import re
with open("_tmp_cur/word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()
# find all <w:p ...> start positions and their matching </w:p> end
# Simple approach: find all paragraph start tags and end tags in order
starts = [m.start() for m in re.finditer(r'<w:p[ >]', xml)]
ends = [m.end() for m in re.finditer(r'</w:p>', xml)]
# pair them
# Build list of (start,end)
paras = list(zip(starts, ends))
print("num paras:", len(paras))
for target in [262623, 264122]:
    for idx,(s,e) in enumerate(paras):
        if s <= target < e:
            txt = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml[s:e])
            txt = "".join(txt).strip()
            print(f"pos {target} -> para idx {idx} span=({s},{e}) txt={txt[:60]!r}")
            break
