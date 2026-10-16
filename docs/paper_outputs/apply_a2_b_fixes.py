#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_a2_b_fixes.py — A2 (abbreviation expansion at first use) + B (numeric
consistency / table order). Surgical edits only.

A2 (规范15:英文缩写第一次出现给全称):
  - 中文摘要: mAP@0.5 -> 平均精度均值(mean Average Precision,mAP)@0.5  (first)
              100.5 FPS -> 100.5 frames per second(FPS)                (first)
  - 英文摘要: mAP@0.5 -> mean Average Precision (mAP)@0.5  (first)
              100.5 FPS -> 100.5 frames per second (FPS)   (first)
  - 正文 body#35: GFLOPs -> Giga floating-point operations(GFLOPs)      (first)
  - 正文 body#71: Params 2.6M -> 参数量(Parameters,Params) 2.6M         (first)
  - 正文 body#15: AP -> 平均精度(Average Precision,AP)                   (first, independent)
  (IoU already expanded via "Wise Intersection over Union"; SGD/RTX left as-is.)

B:
  B1 body#212: " 52.45" -> " 52.5"          (153.0-100.5=52.5, matches rounded FPS used elsewhere)
  B2 表20:     DWCA-P2 单张耗时 9.9 -> 9.95;  DW-P2 10.0 -> 9.95  (1000/100.5=9.95, matches body 9.95)
  B3 表20:     row order baseline,+DW,+D,DWCA,DWCA-P2,DW-P2
               -> baseline,+D,+DW,DWCA,DW-P2,DWCA-P2  (ablation route order, matches 表8)
"""
import sys, shutil, zipfile, tempfile
from pathlib import Path
from copy import deepcopy
from lxml import etree

HERE = Path(__file__).resolve().parent
DOCX = HERE / "yolo11n-dwca-p2-hljust.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WNS = '{%s}' % W
XML_SPACE = '{http://www.w3.org/XML/namespace}space'


def ln(e):
    return etree.QName(e).localname


def rt(r):
    t = r.find(WNS + 't')
    return t.text if t is not None and t.text else ''


def para_text(p):
    return ''.join(rt(r) for r in p.findall(WNS + 'r'))


def find_para(body, pred):
    for p in body.iter(WNS + 'p'):
        if pred(para_text(p)):
            return p
    return None


def repl_in_run(p, old, new, count=None):
    """In paragraph p, find first run whose <w:t> contains `old`, replace."""
    for r in p.findall(WNS + 'r'):
        t = r.find(WNS + 't')
        if t is not None and t.text and old in t.text:
            t.text = t.text.replace(old, new, count) if count else t.text.replace(old, new)
            t.set(XML_SPACE, 'preserve')
            return True
    return False


def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")
    # backup
    bak = HERE / "yolo11n-dwca-p2-hljust.pre-a2b-fix.docx"
    if not bak.exists():
        shutil.copy2(DOCX, bak)
        print(f"backup -> {bak.name}")

    work = Path(tempfile.mkdtemp(prefix="docx_a2b_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        log = []

        # ---- A2: abbreviation expansion ----
        zh = find_para(body, lambda t: t.startswith('摘要'))
        en = find_para(body, lambda t: t.startswith('Abstract'))
        p35 = find_para(body, lambda t: 'P2 路线将 GFLOPs' in t)
        p71 = find_para(body, lambda t: 'baseline 在固定 batch=32 复验' in t)
        p15 = find_para(body, lambda t: '高 IoU 阈值下 AP 下降' in t)
        assert all([zh, en, p35, p71, p15]), "A2: a target paragraph not found"

        ok = repl_in_run(zh, 'mAP@0.5 ', '平均精度均值(mean Average Precision,mAP)@0.5 ')
        log.append(("A2 zh mAP", ok))
        ok = repl_in_run(zh, '100.5 FPS', '100.5 frames per second(FPS)')
        log.append(("A2 zh FPS", ok))
        ok = repl_in_run(en, 'mAP@0.5', 'mean Average Precision (mAP)@0.5', count=1)
        log.append(("A2 en mAP", ok))
        ok = repl_in_run(en, '100.5 FPS', '100.5 frames per second (FPS)', count=1)
        log.append(("A2 en FPS", ok))
        ok = repl_in_run(p35, ' GFLOPs ', ' Giga floating-point operations(GFLOPs) ')
        log.append(("A2 GFLOPs", ok))
        ok = repl_in_run(p71, 'Params 2.6M', '参数量(Parameters,Params) 2.6M')
        log.append(("A2 Params", ok))
        ok = repl_in_run(p15, ' AP ', ' 平均精度(Average Precision,AP) ')
        log.append(("A2 AP", ok))

        # ---- B1: FPS drop 52.45 -> 52.5 ----
        p212 = find_para(body, lambda t: 'FPS 下降约' in t)
        assert p212 is not None, "B1: paragraph not found"
        ok = repl_in_run(p212, ' 52.45', ' 52.5')
        log.append(("B1 52.45->52.5", ok))

        # ---- B2 + B3: table 20 (speed/complexity) ----
        tbl20 = None
        for tbl in body.iter(WNS + 'tbl'):
            hdr = ' '.join(para_text(p) for p in tbl.iter(WNS + 'p'))
            if '单张耗时' in hdr and '相对baseline' in hdr:
                tbl20 = tbl
                break
        assert tbl20 is not None, "B2/B3: table 20 not found"

        # B2: fix 单张耗时 for DWCA-P2 (9.9) and DW-P2 (10.0) -> 9.95
        for tr in tbl20.findall(WNS + 'tr'):
            cells = [''.join(rt(r) for r in tc.iter(WNS + 'r'))
                     for tc in tr.findall(WNS + 'tc')]
            if len(cells) >= 3 and cells[0] in ('DWCA-P2', 'DW-P2'):
                tc = tr.findall(WNS + 'tc')[2]  # 单张耗时/ms column
                for t in tc.iter(WNS + 't'):
                    if t.text in ('9.9', '10.0'):
                        old = t.text
                        t.text = '9.95'
                        log.append((f"B2 {cells[0]} {old}->9.95", True))
        # B3: reorder rows to ablation route
        trs = tbl20.findall(WNS + 'tr')
        # current: [header, baseline, +DW, +D, DWCA, DWCA-P2, DW-P2]
        # desired: [header, baseline, +D, +DW, DWCA, DW-P2, DWCA-P2]
        desired = [trs[0], trs[1], trs[3], trs[2], trs[4], trs[6], trs[5]]
        for tr in trs:
            tbl20.remove(tr)
        for tr in desired:
            tbl20.append(tr)
        log.append(("B3 row reorder", True))

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8",
                   standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                fp = work / name
                if fp.is_file():
                    zout.writestr(name, fp.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))

        print("=== applied ===")
        for k, v in log:
            print(f"  [{'OK' if v else 'MISS'}] {k}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
