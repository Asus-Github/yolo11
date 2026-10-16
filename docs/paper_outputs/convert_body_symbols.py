#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert inline math symbols in body text to real subscript/superscript runs.

Fixes the inconsistent body-text notation where some symbols used ASCII
underscores (y_c, B_gt, L_IoU) and others used Unicode supercripts (fʰ, c²).
After this, every inline symbol uses Word's real vertAlign subscript/
superscript runs, matching the equation notation.

Operates only on direct body <w:p> paragraphs that do NOT contain <m:oMath>
(i.e. real prose, not equations) and are not figure/table captions.
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
# ORDER MATTERS: longer/more-specific patterns first (L_IoU\* before L_IoU, etc.)
SYMBOLS = [
    (r'r_\{P2\}', [('n', 'r'), ('s', 'P2')]),
    (r'r_\{P3\}', [('n', 'r'), ('s', 'P3')]),
    (r'L_IoU\*',  [('n', 'L'), ('s', 'IoU'), ('p', '*')]),
    (r'L_IoU',    [('n', 'L'), ('s', 'IoU')]),
    (r'r_l',      [('n', 'r'), ('s', 'l')]),
    (r'y_c',      [('n', 'y'), ('s', 'c')]),
    (r'B_gt',     [('n', 'B'), ('s', 'gt')]),
    (r'F2',       [('n', 'F'), ('s', '2')]),
    (r'F3',       [('n', 'F'), ('s', '3')]),
    (r'F4',       [('n', 'F'), ('s', '4')]),
    (r'F5',       [('n', 'F'), ('s', '5')]),
    (r'zʰ',       [('n', 'z'), ('p', 'h')]),
    (r'zʷ',       [('n', 'z'), ('p', 'w')]),
    (r'gʰ',       [('n', 'g'), ('p', 'h')]),
    (r'gʷ',       [('n', 'g'), ('p', 'w')]),
    (r'fʰ',       [('n', 'f'), ('p', 'h')]),
    (r'fʷ',       [('n', 'f'), ('p', 'w')]),
    (r'c²',       [('n', 'c'), ('p', '2')]),
    (r'ρ²',       [('n', 'ρ'), ('p', '2')]),
]


def tokenize(text):
    """Split text into [('text', str) | ('tok', [tokens])] keeping symbols intact."""
    matches = []
    for pat, tokens in SYMBOLS:
        for m in re.finditer(pat, text):
            matches.append((m.start(), m.end(), tokens))
    # earliest start first; on tie, longest match first
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out, pos = [], 0
    for start, end, tokens in matches:
        if start < pos:
            continue  # overlap with an earlier (priority) match
        if start > pos:
            out.append(('text', text[pos:start]))
        out.append(('tok', tokens))
        pos = end
    if pos < len(text):
        out.append(('text', text[pos:]))
    return out


def make_run(rpr_template, vert, text):
    """Build <w:r>: copy rPr, add vertAlign if sub/sup, then <w:t>text</w:t>."""
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
    work = Path(tempfile.mkdtemp(prefix="docx_sym_"))
    try:
        with zipfile.ZipFile(DOCX) as z:
            names = z.namelist()
            z.extractall(work)
        doc_path = work / "word" / "document.xml"
        tree = etree.parse(str(doc_path))
        body = tree.getroot().find(WNS + 'body')

        changed_runs = 0
        changed_symbols = 0
        log = []
        for p in body.findall(WNS + 'p'):
            # skip equation paragraphs
            if p.find('.//{%s}oMath' % M) is not None:
                continue
            ptext = ''.join((t.text or '') for t in p.iter(WNS + 't'))
            stripped = ptext.strip()
            # skip figure/table captions
            if stripped.startswith(('图 ', 'Fig', '表 ', 'Tab')):
                continue
            for r in list(p.findall(WNS + 'r')):
                t_el = r.find(WNS + 't')
                if t_el is None or not t_el.text:
                    continue
                toks = tokenize(t_el.text)
                if not any(k == 'tok' for k, _ in toks):
                    continue
                rpr = r.find(WNS + 'rPr')
                idx = list(p).index(r)
                p.remove(r)
                at = idx
                sym_here = 0
                for kind, val in toks:
                    if kind == 'text':
                        p.insert(at, make_run(rpr, None, val)); at += 1
                    else:
                        for vk, vt in val:
                            vert = vk if vk in ('s', 'p') else None
                            p.insert(at, make_run(rpr, vert, vt)); at += 1
                            if vk in ('s', 'p'):
                                sym_here += 1
                changed_runs += 1
                changed_symbols += sym_here
                log.append((stripped[:50], sym_here))

        tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                p = work / name
                if p.is_file():
                    zout.writestr(name, p.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))

        print(f"Changed {changed_runs} runs, {changed_symbols} sub/sup symbols.")
        print("--- per-paragraph log ---")
        for ctx, n in log:
            print(f"  [{n} symbols] {ctx}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
