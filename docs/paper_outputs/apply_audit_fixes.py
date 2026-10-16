#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_audit_fixes.py — apply the equation-audit fixes (Tasks #5-9) to
yolo11n-dwca-p2-hljust.docx.  P2 (Eq.(2) order-mismatch footnote) is HELD
for the user and intentionally NOT touched here.

Surgical edits only — preserves native OMML equations, table layout, numbering,
fonts.  Backed up to .pre-audit-fix.docx before running (already done).

Changes:
  A. Eq.(5)  oMath  : g^h=σ(f^h) -> g^h=σ(F_h(f^h));  g^w=σ(f^w) -> g^w=σ(F_w(f^w))
                      (regenerate whole oMath from new LaTeX via latex_to_omath)
  B. Body (x2)      : "沿通道拼接" -> "沿空间维度拼接"
                      "沿通道维度拼接" -> "沿空间维度拼接"
  C. Eq.(8) after   : add ρ² / c² definitions, reorder ρ²-then-c², keep
                      "使梯度仅经 ρ² 流动" + stop-gradient note
  D. α/δ sentence   : "文献[21]给出的超参数" -> "文献[21]消融实验中最优的一组超参数"
  E. §3.5 self-eval : keep first sentence (...增强位置编码。), delete the
                      editorial self-assessment that follows it
"""
import sys, shutil, zipfile, tempfile
from pathlib import Path
from copy import deepcopy
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert_equations_to_omml import latex_to_omath

HERE = Path(__file__).resolve().parent
DOCX = HERE / "yolo11n-dwca-p2-hljust.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = '{%s}' % W
MNS = '{%s}' % M
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

NEW_EQ5 = (r'f=\delta(\mathrm{Conv}_{1\times1}([z^h,z^w])),\quad '
           r'g^h=\sigma(F_h(f^h)),\quad g^w=\sigma(F_w(f^w))')


def ln(el):
    return etree.QName(el).localname


def run_text(r):
    return ''.join(t.text or '' for t in r.findall(WNS + 't'))


def make_run(rpr_template, vert, text):
    """Build <w:r>: deepcopy rPr template, add vertAlign (sub/sup), then <w:t>."""
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


def fix_A_eq5(body):
    """Regenerate Eq.(5) oMath with F_h / F_w branch convs."""
    target = None
    for om in body.iter(MNS + 'oMath'):
        txt = ''.join(t.text or '' for t in om.iter(MNS + 't'))
        if 'Conv' in txt and 'z' in txt and 'σ' in txt:
            target = om
            break
    if target is None:
        sys.exit("fix_A: Eq.(5) oMath (Conv...) not found")
    before = ''.join(t.text or '' for t in target.iter(MNS + 't'))
    new_om = latex_to_omath(NEW_EQ5)
    parent = target.getparent()
    idx = list(parent).index(target)
    parent.remove(target)
    parent.insert(idx, new_om)
    after = ''.join(t.text or '' for t in new_om.iter(MNS + 't'))
    print(f"[A] Eq.(5) regenerated")
    print(f"    before: {before!r}")
    print(f"    after : {after!r}")
    # sanity: F_h / F_w must appear as sSub(base=F, sub=h/w)
    def mtxt(el):
        return ''.join(t.text or '' for t in el.iter(MNS + 't'))
    subs = [s for s in new_om.iter(MNS + 'sSub')]
    has_Fh = any(mtxt(s.find(MNS + 'e')) == 'F' and
                 mtxt(s.find(MNS + 'sub')) == 'h' for s in subs)
    has_Fw = any(mtxt(s.find(MNS + 'e')) == 'F' and
                 mtxt(s.find(MNS + 'sub')) == 'w' for s in subs)
    assert has_Fh and has_Fw, "fix_A: F_h/F_w subscripts missing after regen"


def fix_B_concat_direction(body):
    """沿通道拼接 / 沿通道维度拼接 -> 沿空间维度拼接 (2 places)."""
    changed = 0
    for p in body.findall(WNS + 'p'):
        if p.find('.//{%s}oMath' % M) is not None:
            continue
        for r in list(p.findall(WNS + 'r')):
            t_el = r.find(WNS + 't')
            if t_el is None or not t_el.text:
                continue
            orig = t_el.text
            # longer pattern first so '沿通道拼接' doesn't eat '维度'
            new = orig.replace('沿通道维度拼接', '沿空间维度拼接') \
                      .replace('沿通道拼接', '沿空间维度拼接')
            if new != orig:
                t_el.text = new
                t_el.set(XML_SPACE, 'preserve')
                changed += 1
                print(f"[B] {orig!r} -> {new!r}")
    assert changed == 2, f"fix_B: expected 2 concat-direction runs, changed {changed}"


def fix_C_rho_c_defs(body):
    """Rebuild the Eq.(8)-after sentence to define ρ² and c²."""
    para = None
    for p in body.findall(WNS + 'p'):
        ptext = ''.join(t.text or '' for t in p.iter(WNS + 't'))
        if '取停止梯度' in ptext and 'ρ' in ptext and '流动' in ptext:
            para = p
            break
    if para is None:
        sys.exit("fix_C: Eq.(8)-after paragraph (取停止梯度...流动) not found")

    children = list(para)
    # locate the run '其中' (start) and run '流动。记' (end-of-region)
    start_idx = end_idx = None
    for i, ch in enumerate(children):
        if ln(ch) == 'r' and run_text(ch) == '其中':
            start_idx = i
        if ln(ch) == 'r' and run_text(ch) == '流动。记':
            end_idx = i
            break
    if start_idx is None or end_idx is None or end_idx < start_idx:
        sys.exit(f"fix_C: region markers not found (start={start_idx}, end={end_idx})")
    region = children[start_idx:end_idx + 1]
    region_text = ''.join(run_text(r) for r in region if ln(r) == 'r')
    print(f"[C] region before: {region_text!r}")

    # rPr templates: vanilla from the '其中' run
    vanilla_rpr = children[start_idx].find(WNS + 'rPr')

    # verify the region really is c²-then-ρ² (so we rebuild it correctly)
    if ' c' not in region_text or 'ρ' not in region_text:
        sys.exit(f"fix_C: region unexpected (no c²/ρ²): {region_text!r}")

    # new run sequence: 其中 ρ² 为...中心距平方， c² 为...对角线平方（取停止梯度），
    # 使梯度仅经 ρ² 流动。记
    new_runs = [
        make_run(vanilla_rpr, None, '其中'),
        make_run(vanilla_rpr, None, ' ρ'),
        make_run(vanilla_rpr, 'p', '2'),
        make_run(vanilla_rpr, None, ' 为预测框与真实框中心距平方， c'),
        make_run(vanilla_rpr, 'p', '2'),
        make_run(vanilla_rpr, None,
                 ' 为二者最小外接矩形对角线平方（取停止梯度），使梯度仅经 ρ'),
        make_run(vanilla_rpr, 'p', '2'),
        make_run(vanilla_rpr, None, ' 流动。记'),
    ]
    # remove old region, insert new
    for ch in region:
        para.remove(ch)
    for j, nr in enumerate(new_runs):
        para.insert(start_idx + j, nr)
    after_text = ''.join(run_text(r) for r in para if ln(r) == 'r')
    # show the rebuilt head only (up to '流动。记')
    head = after_text[:after_text.index('流动。记') + len('流动。记')]
    print(f"[C] region after : {head!r}")


def fix_D_alpha_delta(body):
    """文献[21]给出的超参数 -> 文献[21]消融实验中最优的一组超参数."""
    changed = 0
    for p in body.findall(WNS + 'p'):
        for r in list(p.findall(WNS + 'r')):
            t_el = r.find(WNS + 't')
            if t_el is None or not t_el.text:
                continue
            if '给出的超参数' in t_el.text:
                orig = t_el.text
                t_el.text = t_el.text.replace('给出的超参数',
                                              '消融实验中最优的一组超参数')
                t_el.set(XML_SPACE, 'preserve')
                changed += 1
                print(f"[D] {orig!r} -> {t_el.text!r}")
    assert changed == 1, f"fix_D: expected 1 α/δ run, changed {changed}"


def fix_E_selfeval(body):
    """Keep first sentence of the §3.5 self-eval paragraph; drop the rest."""
    para = None
    for p in body.findall(WNS + 'p'):
        ptext = ''.join(t.text or '' for t in p.iter(WNS + 't'))
        if '需要强调的是' in ptext and '增强位置编码' in ptext:
            para = p
            break
    if para is None:
        sys.exit("fix_E: §3.5 self-eval paragraph (需要强调的是...增强位置编码) not found")

    # truncate the run that holds the first-sentence end + self-eval start
    trunc_run = None
    for r in para.findall(WNS + 'r'):
        t_el = r.find(WNS + 't')
        if t_el is None or not t_el.text:
            continue
        if '增强位置编码。' in t_el.text and '需要强调的是' in t_el.text:
            cut = t_el.text.index('增强位置编码。') + len('增强位置编码。')
            t_el.text = t_el.text[:cut]
            t_el.set(XML_SPACE, 'preserve')
            trunc_run = r
            break
    if trunc_run is None:
        sys.exit("fix_E: split run (增强位置编码。...需要强调的是) not found")

    # remove all <w:r> runs AFTER the truncated run
    trunc_idx = list(para).index(trunc_run)
    removed = 0
    for ch in list(para)[trunc_idx + 1:]:
        if ln(ch) == 'r':
            para.remove(ch)
            removed += 1
    after = ''.join(t.text or '' for t in para.iter(WNS + 't'))
    print(f"[E] §3.5 para after (removed {removed} runs):")
    print(f"    {after!r}")
    assert '需要强调的是' not in after, "fix_E: self-eval text still present"
    assert '过度强调' not in after, "fix_E: editorial tail still present"


def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")
    work = Path(tempfile.mkdtemp(prefix="docx_auditfix_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        fix_A_eq5(body)
        fix_B_concat_direction(body)
        fix_C_rho_c_defs(body)
        fix_D_alpha_delta(body)
        fix_E_selfeval(body)

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8",
                   standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                fp = work / name
                if fp.is_file():
                    zout.writestr(name, fp.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))
        print("\n=== all audit fixes applied & repacked ===")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
