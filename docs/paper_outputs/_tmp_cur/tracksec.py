import docx
from docx.oxml.ns import qn

doc = docx.Document("中文版北核_DWCA-P2-哈理工学报格式版.docx")
body = doc.element.body

# Walk through paragraphs in order. Track current section column count.
# A sectPr in a paragraph's pPr ends a section. The LAST sectPr in body (sectPr child of body) applies to the final section.
# We'll assign each paragraph to the section whose ending sectPr comes at/after it.

# Collect paragraphs and sectPrs in document order.
paras = body.findall(qn('w:p'))
# Also the final body-level sectPr
final_sect = body.find(qn('w:sectPr'))

# For each paragraph, find if its pPr has a sectPr
sections = []  # list of (end_para_index, cols_num, type)
for i, p in enumerate(paras):
    pPr = p.find(qn('w:pPr'))
    if pPr is None:
        continue
    sectPr = pPr.find(qn('w:sectPr'))
    if sectPr is not None:
        cols = sectPr.find(qn('w:cols'))
        num = cols.get(qn('w:num')) if cols is not None else None
        typ = sectPr.find(qn('w:type'))
        typv = typ.get(qn('w:val')) if typ is not None else None
        sections.append((i, num, typv))

# final section
if final_sect is not None:
    cols = final_sect.find(qn('w:cols'))
    num = cols.get(qn('w:num')) if cols is not None else None
    sections.append((len(paras)-1, num, 'final'))

# Now for each paragraph, determine its section's col count:
# A paragraph belongs to the section that ends at the next sectPr at or after its index.
# Build a list: for each para index, the col count = the col count of the section whose end_para_index >= i (the smallest such).
import bisect
end_indices = [s[0] for s in sections]
col_for = {}
sec_idx = 0
for i in range(len(paras)):
    # find first section with end_para_index >= i
    while sec_idx < len(sections)-1 and sections[sec_idx][0] < i:
        sec_idx += 1
    # sections[sec_idx] applies
    col_for[i] = sections[sec_idx]

# Now print paragraphs that are 注 or 图/表 captions with their section col count
for i, p in enumerate(paras):
    txt = "".join(t.text or "" for t in p.iter(qn('w:t'))).strip()
    if not txt:
        continue
    if txt.startswith("注") or txt.startswith("图") or txt.startswith("表"):
        sec = col_for[i]
        print(f"para {i:4d} | cols={sec[1]} type={sec[2]} | {txt[:70]}")
