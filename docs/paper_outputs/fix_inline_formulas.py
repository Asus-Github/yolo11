#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_inline_formulas.py — convert textual pseudo-formulas in body prose to
real Word subscript/superscript runs (project "方案①+真上下标").

Scope: 中文版北核_DWCA-P2-图片优化版.docx
The 7 numbered display equations (式1-7) are already native OMML and are NOT
touched. Only inline body-text symbols that were written as plain characters
(πL, fh, LIoU, x∈R^(C×H×W)) and the duplicated β=LIoU*/L̄IoU definition are fixed:

  p87  πL/πS/πC  -> π_L / π_S / π_C   (subscript)
  p92  R^(C×H×W) -> R with superscript (C×H×W), caret removed
  p95  fh/fw/gh/gw -> f^h/f^w/g^h/g^w (superscript)
  p100 LIoU=     -> L_{IoU}=          (subscript on first LIoU only)
  p103 β=LIoU*/L̄IoU -> β（见式（6））  (drop duplicated textual formula)

Method: each target paragraph is a single vanilla <w:r>; we replace that run
with a token sequence [(vert, text), ...] where vert ∈ {None,'sub','sup'}.
Backup written to *.pre-formula-fix.docx. Idempotent: re-running on an already
fixed file will not find the original anchor substrings and will abort safely.
"""
import sys, re, shutil, zipfile, tempfile
from pathlib import Path
from copy import deepcopy
from lxml import etree

HERE = Path(__file__).resolve().parent
DOCX = HERE / "中文版北核_DWCA-P2-图片优化版.docx"
BAK  = HERE / "中文版北核_DWCA-P2-图片优化版.pre-formula-fix.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = '{%s}' % W
MNS = '{%s}' % M
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

# Each entry: (anchor_substring, [(vert, text), ...])  vert: None | 'sub' | 'sup'
# The anchor uniquely identifies the paragraph; the token list rebuilds its
# single body run. Concatenating all token texts must equal the desired new text.
EDITS = [
    ("尺度注意力 πL", [
        (None, "设多层输入特征为 F，DyHead 依次施加尺度注意力 π"),
        ('sub', "L"),
        (None, "、空间注意力 π"),
        ('sub', "S"),
        (None, "、任务注意力 π"),
        ('sub', "C"),
        (None, "，其总体映射表示为"),
    ]),
    ("一维全局平均池化", [
        (None, "对输入 x∈R"),
        ('sup', "(C×H×W)"),
        (None, "，分别沿宽度和高度方向进行一维全局平均池化："),
    ]),
    ("再生成方向注意力", [
        (None, "将两方向特征拼接并经1×1卷积、非线性变换后分解为 f"),
        ('sup', "h"),
        (None, " 与 f"),
        ('sup', "w"),
        (None, "，再生成方向注意力 g"),
        ('sup', "h"),
        (None, "、g"),
        ('sup', "w"),
        (None, "，输出为"),
    ]),
    ("WIoU 的距离注意项为", [
        (None, "令 L"),
        ('sub', "IoU"),
        (None, "=1−IoU，ρ 为预测框与真实框中心距离，c 为最小外接框对角线。WIoU 的距离注意项为"),
    ]),
    ("构造非单调聚焦系数", [
        (None, "以滑动平均归一化后的离群度 β（见式（6））构造非单调聚焦系数"),
    ]),
]


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
        va.set(WNS + 'val', 'subscript' if vert == 'sub' else 'superscript')
    t = etree.SubElement(r, WNS + 't')
    t.set(XML_SPACE, 'preserve')
    t.text = text
    return r


def run_text(el):
    return ''.join((tt.text or '') for tt in el.findall(WNS + 't'))


def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")

    # idempotency / freshness check: abort if anchor substrings already absent
    work = Path(tempfile.mkdtemp(prefix="docx_fixformula_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        done = []
        for anchor, tokens in EDITS:
            target = None
            for p in body.findall(WNS + 'p'):
                if p.find('.//{%s}oMath' % M) is not None:
                    continue  # never touch equation paragraphs
                if p.find('.//{%s}vertAlign' % W) is not None:
                    continue  # already has sub/sup -> idempotency guard
                if anchor in ''.join((t.text or '') for t in p.iter(WNS + 't')):
                    target = p
                    break
            if target is None:
                print(f"  SKIP (anchor not found, maybe already fixed): {anchor!r}")
                continue

            # find the single body run containing the anchor (skip pPr)
            body_runs = [c for c in target if etree.QName(c).localname == 'r']
            victim = None
            for r in body_runs:
                if anchor in run_text(r):
                    victim = r
                    break
            if victim is None:
                # anchor may be split across runs or the rebuild target uses a
                # substring not in the original (e.g. p103 new text). Fall back:
                # the paragraph has exactly one body run -> use it.
                if len(body_runs) == 1:
                    victim = body_runs[0]
                else:
                    print(f"  SKIP (anchor {anchor!r} not in any single run): {run_text(body_runs[0])[:60]!r}")
                    continue

            rpr = victim.find(WNS + 'rPr')
            idx = list(target).index(victim)
            target.remove(victim)
            for off, (vert, text) in enumerate(tokens):
                target.insert(idx + off, make_run(rpr, vert, text))
            done.append(anchor)

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                fp = work / name
                if fp.is_file():
                    zout.writestr(name, fp.read_bytes())

        # backup original, then replace
        if not BAK.exists():
            shutil.copy2(str(DOCX), str(BAK))
        shutil.move(str(tmp_out), str(DOCX))

        print(f"Backup: {BAK.name}")
        print(f"Edited {len(done)} paragraph(s):")
        for a in done:
            print(f"  ✓ {a}")
        if len(done) != len(EDITS):
            print(f"WARNING: {len(EDITS)-len(done)} anchor(s) not applied.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
