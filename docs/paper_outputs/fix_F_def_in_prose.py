#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_F_def_in_prose.py — companion to Task #5: now that Eq.(5) introduces
F_h / F_w (branch 1x1 convs), the §3.5 prose after Eq.(5) must define them
so the equation is self-supporting.

Current run (body para after Eq.(5) table):
  ... fh、fw [run: '为变换后沿高度与宽度方向的分支。最终输出'] ...
Target:
  ... fh、fw 为 f 沿高度与宽度方向的拆分，Fh、Fw 为对应方向的 1×1 卷积。最终输出 ...
where fh/fw stay superscript and Fh/Fw are subscript (F_h / F_w), matching
Eq.(5) (F_{h} subscript, f^{h} superscript).
"""
import sys, shutil, zipfile, tempfile
from pathlib import Path
from copy import deepcopy
from lxml import etree

HERE = Path(__file__).resolve().parent
DOCX = HERE / "yolo11n-dwca-p2-hljust.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WNS = '{%s}' % W
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

OLD_RUN = '为变换后沿高度与宽度方向的分支。最终输出'


def ln(el):
    return etree.QName(el).localname


def make_run(rpr_template, vert, text):
    r = etree.Element(WNS + 'r')
    if rpr_template is not None:
        r.append(deepcopy(rpr_template))
    rPr = r.find(WNS + 'rPr')
    if vert is not None:
        if rPr is None:
            rPr = etree.Element(WNS + 'rPr')
            r.insert(0, rPr)
        va = etree.SubElement(rPr, WNS + 'vertAlign')
        va.set(WNS + 'val', 'subscript' if vert == 's' else 'superscript')
    t = etree.SubElement(r, WNS + 't')
    t.set(XML_SPACE, 'preserve')
    t.text = text
    return r


def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")
    work = Path(tempfile.mkdtemp(prefix="docx_Fdef_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        # find the §3.5 prose paragraph after Eq.(5)
        para = None
        target_run = None
        for p in body.findall(WNS + 'p'):
            if p.find('.//{%s}oMath' % M) is not None:
                continue
            for r in p.findall(WNS + 'r'):
                t_el = r.find(WNS + 't')
                if t_el is not None and t_el.text == OLD_RUN:
                    para = p
                    target_run = r
                    break
            if target_run is not None:
                break
        if target_run is None:
            sys.exit(f"fix_F_def: target run {OLD_RUN!r} not found")

        rpr = target_run.find(WNS + 'rPr')
        idx = list(para).index(target_run)
        para.remove(target_run)

        # new run sequence (F_h / F_w use subscript 'h'/'w')
        new_runs = [
            make_run(rpr, None, '为 f 沿高度与宽度方向的拆分，'),
            make_run(rpr, None, 'F'),
            make_run(rpr, 's', 'h'),
            make_run(rpr, None, '、'),
            make_run(rpr, None, 'F'),
            make_run(rpr, 's', 'w'),
            make_run(rpr, None, ' 为对应方向的 1×1 卷积。最终输出'),
        ]
        for j, nr in enumerate(new_runs):
            para.insert(idx + j, nr)

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8",
                   standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                fp = work / name
                if fp.is_file():
                    zout.writestr(name, fp.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))

        after = ''.join(t.text or '' for t in para.iter(WNS + 't'))
        print("[F-def] §3.5 prose after Eq.(5):")
        print("   ", after)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
