#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_body_symbols_v2.py — fix residual inline symbols missed by v1.

v1 (convert_body_symbols.py) converted the main ASCII-underscore symbols
(y_c, B_gt, L_IoU, F2-F5, zʰ ...) run-by-run. It missed two kinds:

  1. Symbols that SPAN two runs. In the 3.6 Wise-IoU paragraph the ρ of "ρ²"
     lives in its own run with rPr=None, while the "²" is in the next run — so
     no single run contains "ρ²" and v1's per-run tokenizer never matched it.
     Same for "像素"+"²" in the abstract.
  2. Unicode-² value/unit symbols (32², px², 像素², pixel²) that were never in
     v1's table.

It also left the stop-gradient star of "L_IoU*" as plain text in the 3.6
paragraph, while every other paragraph (and the equations) render it as a
superscript — an inconsistency.

This v2 fixes all three, font-safely:

  Step 1 — COALESCE: within each prose paragraph that contains '²' or '*',
     merge consecutive *vanilla* runs (no vertAlign/bold/italic) that share the
     SAME font signature (rFonts + sz; rPr=None counts as default). Same-font
     merging is font-safe; already-converted sub/sup runs carry vertAlign so
     they are not vanilla and are left intact (idempotent).
  Step 2 — TOKENIZE-SPLIT: split the coalesced text on the residual symbol
     patterns (ρ², c², 32², 像素², px², pixel²) into real superscript runs.
  Step 3 — STAR-FIX: a vanilla run starting with '*' whose preceding run
     (skipping proofErr/bookmarks) is a subscript-IoU run → make that leading
     '*' a superscript, so L_{IoU}^{*} matches the rest of the paper.

Skips: paragraphs containing <m:oMath> (equations), figure/table captions.
`close_mosaic` (a YOLO hyperparameter name) is not matched by any pattern, so
its underscore is left alone — it is a parameter name, not a math subscript.
"""
import os, sys, re, shutil, zipfile, tempfile
from pathlib import Path
from copy import deepcopy
from lxml import etree

HERE = Path(__file__).resolve().parent
DOCX = HERE / "yolo11n-dwca-p2-hljust.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = '{%s}' % W
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

# pattern -> run tokens: ('n',txt)=normal, ('s',txt)=subscript, ('p',txt)=superscript
SYMBOLS = [
    (r'32²',     [('n', '32'), ('p', '2')]),
    (r'像素²',   [('n', '像素'), ('p', '2')]),
    (r'pixel²',  [('n', 'pixel'), ('p', '2')]),
    (r'px²',     [('n', 'px'), ('p', '2')]),
    (r'ρ²',      [('n', 'ρ'), ('p', '2')]),
    (r'c²',      [('n', 'c'), ('p', '2')]),
]


def tokenize(text):
    matches = []
    for pat, tokens in SYMBOLS:
        for m in re.finditer(pat, text):
            matches.append((m.start(), m.end(), tokens))
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out, pos = [], 0
    for start, end, tokens in matches:
        if start < pos:
            continue
        if start > pos:
            out.append(('text', text[pos:start]))
        out.append(('tok', tokens))
        pos = end
    if pos < len(text):
        out.append(('text', text[pos:]))
    return out


def is_vanilla(rpr):
    """Plain-text run: no vertAlign, no bold, no italic. rPr None => vanilla."""
    if rpr is None:
        return True
    if rpr.find(WNS + 'vertAlign') is not None:
        return False
    if rpr.find(WNS + 'b') is not None:
        return False
    if rpr.find(WNS + 'i') is not None:
        return False
    return True


def font_sig(rpr):
    """Font signature = (rFonts serialized w/o ns decls, sz val). None => (None,None)."""
    if rpr is None:
        return (None, None)
    rf = rpr.find(WNS + 'rFonts')
    rf_s = None
    if rf is not None:
        rf_s = etree.tostring(rf, encoding='unicode')
        rf_s = re.sub(r'\sxmlns(?::[a-zA-Z0-9]+)?="[^"]*"', '', rf_s)
    sz = rpr.find(WNS + 'sz')
    sz_v = sz.get(WNS + 'val') if sz is not None else None
    return (rf_s, sz_v)


def vert_of_rpr(rpr):
    if rpr is None:
        return None
    va = rpr.find(WNS + 'vertAlign')
    return va.get(WNS + 'val') if va is not None else None


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


def run_text(el):
    return ''.join(t.text or '' for t in el.findall(WNS + 't'))


def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")
    work = Path(tempfile.mkdtemp(prefix="docx_symv2_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        n_coalesced = 0
        n_symbols = 0
        n_stars = 0
        log = []

        for p in body.findall(WNS + 'p'):
            if p.find('.//{%s}oMath' % M) is not None:
                continue
            ptext = ''.join((t.text or '') for t in p.iter(WNS + 't'))
            if ptext.strip().startswith(('图 ', 'Fig', '表 ', 'Tab')):
                continue
            if '²' not in ptext and '*' not in ptext:
                continue

            # ---- build item list: ['run', rpr, text] | ['elem', element] ----
            items = []
            for ch in list(p):
                if etree.QName(ch).localname == 'r':
                    rpr = ch.find(WNS + 'rPr')
                    txt = run_text(ch)
                    if is_vanilla(rpr) and txt != '':
                        items.append(['run', rpr, txt])
                    else:
                        items.append(['elem', ch])
                else:
                    items.append(['elem', ch])

            # ---- step 1: coalesce consecutive vanilla runs w/ same font_sig ----
            merged = []
            i = 0
            while i < len(items):
                it = items[i]
                if it[0] == 'run':
                    sig = font_sig(it[1])
                    parts = [it[2]]
                    rpr_choices = [it[1]]
                    j = i + 1
                    while j < len(items) and items[j][0] == 'run' and font_sig(items[j][1]) == sig:
                        parts.append(items[j][2])
                        rpr_choices.append(items[j][1])
                        j += 1
                    if j > i + 1:
                        n_coalesced += (j - i - 1)
                    # prefer a non-None rPr so lang/rFonts are preserved
                    rpr0 = next((r for r in rpr_choices if r is not None), None)
                    merged.append(['run', rpr0, ''.join(parts)])
                    i = j
                else:
                    merged.append(it)
                    i += 1
            items = merged

            # ---- step 2: tokenize-split each run item ----
            split = []
            for it in items:
                if it[0] != 'run':
                    split.append(it)
                    continue
                rpr, txt = it[1], it[2]
                toks = tokenize(txt)
                if not any(k == 'tok' for k, _ in toks):
                    split.append(it)
                    continue
                for kind, val in toks:
                    if kind == 'text':
                        if val:
                            split.append(['run', rpr, val])
                    else:
                        for vk, vt in val:
                            if vk == 'n':
                                if vt:
                                    split.append(['run', rpr, vt])
                            elif vk == 'p':
                                split.append(['sup', rpr, vt])
                                n_symbols += 1
                            elif vk == 's':
                                split.append(['sub', rpr, vt])
                                n_symbols += 1
            items = split

            # ---- step 3: star-fix ----
            def prev_run_vert_text(idx):
                k = idx - 1
                while k >= 0:
                    it = items[k]
                    if it[0] == 'run':
                        return (None, it[2])
                    if it[0] == 'sup':
                        return ('superscript', it[2])
                    if it[0] == 'sub':
                        return ('subscript', it[2])
                    if it[0] == 'elem' and etree.QName(it[1]).localname == 'r':
                        return (vert_of_rpr(it[1].find(WNS + 'rPr')), run_text(it[1]))
                    k -= 1
                return (None, None)

            fixed = []
            for i, it in enumerate(items):
                if it[0] == 'run' and it[2].startswith('*'):
                    pv, ptxt = prev_run_vert_text(i)
                    if pv == 'subscript' and 'IoU' in ptxt:
                        n_stars += 1
                        log.append(f"  star->sup in: {ptext[:50]!r}")
                        fixed.append(['sup', it[1], '*'])
                        rest = it[2][1:]
                        if rest:
                            fixed.append(['run', it[1], rest])
                        continue
                fixed.append(it)
            items = fixed

            if any(it[0] in ('sup', 'sub') for it in items):
                pass  # changes happened

            # ---- rebuild paragraph children ----
            for ch in list(p):
                p.remove(ch)
            for it in items:
                if it[0] == 'elem':
                    p.append(it[1])
                elif it[0] == 'run':
                    p.append(make_run(it[1], None, it[2]))
                elif it[0] == 'sub':
                    p.append(make_run(it[1], 's', it[2]))
                elif it[0] == 'sup':
                    p.append(make_run(it[1], 'p', it[2]))

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                fp = work / name
                if fp.is_file():
                    zout.writestr(name, fp.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))

        print(f"Coalesced {n_coalesced} adjacent vanilla runs.")
        print(f"Converted {n_symbols} residual superscript symbols (² -> real sup).")
        print(f"Fixed {n_stars} L_IoU* stars (plain -> superscript).")
        for line in log:
            print(line)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
