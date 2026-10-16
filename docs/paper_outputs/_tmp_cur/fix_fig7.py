import docx
from docx.oxml.ns import qn
import shutil, os

SRC = "中文版北核_DWCA-P2-哈理工学报格式版.docx"
BAK = "中文版北核_DWCA-P2-哈理工学报格式版.pre-fig7fix.docx"
shutil.copy(SRC, BAK)

doc = docx.Document(SRC)
body = doc.element.body
paras = body.findall(qn('w:p'))

# find fig7 caption paragraph index
fig7_idx = None
for i, p in enumerate(paras):
    txt = "".join(t.text or "" for t in p.iter(qn('w:t')))
    if "图7" in txt and "模型训练与验证曲线" in txt:
        fig7_idx = i
        break
print("fig7 caption para idx:", fig7_idx)

def sect_cols(p):
    pPr = p.find(qn('w:pPr'))
    if pPr is None: return None
    s = pPr.find(qn('w:sectPr'))
    if s is None: return None
    c = s.find(qn('w:cols'))
    return c.get(qn('w:num')) if c is not None else None

def is_empty(p):
    return "".join(t.text or "" for t in p.iter(qn('w:t'))).strip() == ""

# the paragraph before fig7 caption should be empty with sectPr num=1
# the paragraph after  fig7 caption should be empty with sectPr num=2
prev_p = paras[fig7_idx-1]
next_p = paras[fig7_idx+1]
print("prev cols:", sect_cols(prev_p), "empty:", is_empty(prev_p))
print("next cols:", sect_cols(next_p), "empty:", is_empty(next_p))

assert sect_cols(prev_p) == "1" and is_empty(prev_p), "prev not as expected"
assert sect_cols(next_p) == "2" and is_empty(next_p), "next not as expected"

# remove the two stray section-break paragraphs
prev_p.getparent().remove(prev_p)
next_p.getparent().remove(next_p)

doc.save(SRC)
print("saved", SRC)
