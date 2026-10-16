import re
with open("word/document.xml","r",encoding="utf-8") as f:
    xml = f.read()

# Find positions of each 注 text
notes = ["注：现有记录", "注：各百分比", "注：AP 表示", "注：D、W"]
for n in notes:
    idx = xml.find(n)
    print(f"\n=== {n} at {idx} ===")
    if idx == -1:
        continue
    # show surrounding 600 chars
    print(xml[idx-200:idx+400])
    print("...")
