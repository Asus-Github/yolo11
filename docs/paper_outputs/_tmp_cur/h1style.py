import re
with open("_tmp_cur/word/styles.xml","r",encoding="utf-8") as f:
    s = f.read()
# find Heading1 style
m = re.search(r'<w:style [^>]*w:styleId="Heading1".*?</w:style>', s, re.S)
if m:
    print("HEADING1:")
    print(m.group(0)[:1500])
# also check the heading style used - search pageBreakBefore
print("\n--- pageBreakBefore occurrences ---")
for mm in re.finditer(r'<w:style [^>]*w:styleId="([^"]*)"[^>]*>.*?pageBreakBefore', s, re.S):
    print(mm.group(1))
