#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert the 12 equation PNGs in yolo11n-dwca-p2-hljust.docx to native Word OMML.

Path C (surgical): unzip the docx, locate the 1x3 equation tables by the image
each center cell embeds, replace the image run with an <m:oMath> element, keep
the table structure / numbering / centering intact, repack.

Chain: LaTeX ->(latex2mathml)-> MathML ->(MS Word mathml2omml.xsl)-> OMML.

Re-runnable: if an equation image is already gone (already converted), it is
skipped with a note.
"""
import os, sys, shutil, zipfile, re, tempfile
from pathlib import Path
from lxml import etree
import latex2mathml.converter as l2m

# --------------------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent
DOCX = HERE / "yolo11n-dwca-p2-hljust.docx"
BAK  = HERE / "yolo11n-dwca-p2-hljust.bak.docx"
XSL  = "/Applications/Microsoft Word.app/Contents/Resources/mathml2omml.xsl"

# --------------------------------------------------------------------------- namespaces
W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M   = "http://schemas.openxmlformats.org/officeDocument/2006/math"
R   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A   = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS  = {"w": W, "m": M, "r": R, "a": A}
ETREE_NS = {f"xmlns:{p}": u for p, u in NS.items()}

# --------------------------------------------------------------------------- the 12 equations
# image number (word/media/imageN.png) -> equation number (1..12)
IMAGE_TO_EQ = {3:1, 5:2, 7:3, 8:4, 9:5, 10:6, 12:7, 13:8, 14:9, 15:10, 17:11, 18:12}
EQ_LATEX = {
 1:  r'd_l=\frac{d}{r_l}',
 2:  r"F'=L(S(\pi(F)))",
 3:  r'z_c^h(h)=\frac{1}{W}\sum_{0\leq i<W}x_c(h,i)',
 4:  r'z_c^w(w)=\frac{1}{H}\sum_{0\leq j<H}x_c(j,w)',
 5:  r'f=\delta(\mathrm{Conv}_{1\times1}([z^h,z^w])),\quad g^h=\sigma(f^h),\quad g^w=\sigma(f^w)',
 6:  r'y_c(h,w)=x_c(h,w)\cdot g_c^h(h)\cdot g_c^w(w)',
 7:  r'IoU=\frac{|B\cap B_{gt}|}{|B\cup B_{gt}|}',
 8:  r'R_{WIoU}=\exp(\frac{\rho^2}{c^2})',
 9:  r'\beta=\frac{L_{IoU}^{*}}{\bar{L}},\quad r=\frac{\beta}{\delta\,\alpha^{\beta-\delta}}',
 10: r'\mathcal{L}_{WIoUv3}=r\cdot R_{WIoU}\cdot L_{IoU}',
 11: r'P=\frac{TP}{TP+FP}',
 12: r'R=\frac{TP}{TP+FN}',
}

# --------------------------------------------------------------------------- latex -> oMath element
_xslt = etree.parse(XSL)
_transform = etree.XSLT(_xslt)
_omml_cache = {}

def latex_to_omath(latex: str):
    """Return a fresh <m:oMath> element for the given LaTeX."""
    if latex in _omml_cache:
        # return a deep copy so callers can insert independently
        return etree.fromstring(etree.tostring(_omml_cache[latex]))
    mml_str = l2m.convert(latex)
    mml_el = etree.fromstring(mml_str)
    result = _transform(mml_el)
    omath = result.getroot()
    # normalize to a standalone element string -> re-parse (clean ns declarations)
    el = etree.fromstring(etree.tostring(omath))
    fix_empty_nary(el)
    _omml_cache[latex] = el
    return etree.fromstring(etree.tostring(el))

def omml_text(el):
    return ''.join(t.text or '' for t in el.iter('{%s}t' % M))

def fix_empty_nary(omath):
    """Repair <m:nary> elements whose <m:e/> body is empty.

    latex2mathml emits \\sum_{...} as <msub><mo>∑</mo>...</msub> (a plain
    subscript), so the summation body (e.g. x_c(h,i)) ends up as a *sibling*
    of the nary, not inside it. The XSLT then promotes ∑ to <m:nary> with an
    empty <m:e/>, which Word renders as a dotted placeholder box. Fix: move
    the nary's following siblings into <m:e> so the summation has a body.
    """
    M_NS = '{%s}' % M
    for nary in list(omath.iter(M_NS + 'nary')):
        e = nary.find(M_NS + 'e')
        if e is None or len(e) > 0:
            continue  # e missing or already has a body
        parent = nary.getparent()
        if parent is None:
            continue
        idx = list(parent).index(nary)
        following = list(parent)[idx + 1:]
        if not following:
            continue
        for sib in following:
            parent.remove(sib)
            e.append(sib)

# --------------------------------------------------------------------------- helpers
def wval(el, attr="val"):
    return el.get("{%s}%s" % (W, attr)) if el is not None else None

def parse_rels(rels_xml_path):
    """rId -> target string (e.g. 'media/image3.png')."""
    rels = {}
    if not os.path.exists(rels_xml_path):
        return rels
    for rel in etree.parse(rels_xml_path).getroot():
        rels[rel.get("Id")] = rel.get("Target", "")
    return rels

def image_num_from_target(target: str):
    m = re.search(r"image(\d+)\.png", target or "")
    return int(m.group(1)) if m else None

# --------------------------------------------------------------------------- main
def main():
    if not DOCX.exists():
        sys.exit(f"docx not found: {DOCX}")
    if not os.path.exists(XSL):
        sys.exit(f"mathml2omml.xsl not found: {XSL}")

    work = Path(tempfile.mkdtemp(prefix="docx_omml_"))
    try:
        # 1. unzip
        with zipfile.ZipFile(DOCX) as zin:
            names = zin.namelist()
            zin.extractall(work)

        doc_xml_path = work / "word" / "document.xml"
        rels_path    = work / "word" / "_rels" / "document.xml.rels"
        rels = parse_rels(str(rels_path))

        # 2. parse document.xml; ensure m namespace declared on root
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(doc_xml_path), parser)
        root = tree.getroot()
        root_nsmap = root.nsmap
        if "m" not in root_nsmap:
            root.set("xmlns:m", M)

        # 3. locate every embedded image inside a table cell -> map to equation
        # iterate over all w:drawing elements; for each, find r:embed, resolve to
        # image number, and if it is one of our 12 equation images, replace the
        # enclosing w:r with an <m:oMath>.
        replaced = {}   # eq number -> omml text
        replaced_rids = {}  # eq number -> rId (for cleanup)
        skipped = []
        # collect drawings first (we will mutate the tree, so snapshot)
        drawings = list(root.iter("{%s}drawing" % W))
        for drawing in drawings:
            blip = drawing.find(".//{%s}blip" % A)
            if blip is None:
                continue
            rid = blip.get("{%s}embed" % R) or blip.get("{%s}link" % R)
            if not rid:
                continue
            target = rels.get(rid, "")
            img_num = image_num_from_target(target)
            if img_num not in IMAGE_TO_EQ:
                continue  # a figure image, not an equation — leave alone
            eq_num = IMAGE_TO_EQ[img_num]
            latex = EQ_LATEX[eq_num]

            # find enclosing w:r
            run = drawing.getparent()
            while run is not None and etree.QName(run).localname != "r":
                run = run.getparent()
            if run is None:
                skipped.append((eq_num, "no enclosing w:r"))
                continue
            para = run.getparent()
            if para is None or etree.QName(para).localname != "p":
                skipped.append((eq_num, "run parent not w:p"))
                continue

            # build oMath and insert at the run's position, then remove the run
            omath = latex_to_omath(latex)
            idx = list(para).index(run)
            para.remove(run)
            para.insert(idx, omath)
            replaced[eq_num] = omml_text(omath)
            replaced_rids[eq_num] = rid

        # 4. write document.xml back
        tree.write(str(doc_xml_path), xml_declaration=True, encoding="UTF-8",
                   standalone=True)

        # 4b. cleanup: remove now-unreferenced equation image files + their rels
        rels_tree = etree.parse(str(rels_path))
        rels_root = rels_tree.getroot()
        cleaned = []
        for eq_num, rid in replaced_rids.items():
            target = rels.get(rid, "")  # e.g. "media/image3.png"
            media_p = work / "word" / target
            if media_p.is_file():
                media_p.unlink()
            for rel in list(rels_root):
                if rel.get("Id") == rid:
                    rels_root.remove(rel)
            cleaned.append(os.path.basename(target))
        rels_tree.write(str(rels_path), xml_declaration=True, encoding="UTF-8",
                        standalone=True)
        if cleaned:
            print(f"Cleaned {len(cleaned)} orphaned equation images: {sorted(cleaned)}")

        # 5. repack docx preserving original member order
        tmp_out = work.parent / (work.name + "_out.docx")
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                p = work / name
                if p.is_file():
                    zout.writestr(name, p.read_bytes())
        shutil.move(str(tmp_out), str(DOCX))

        # 6. report
        print(f"Replaced {len(replaced)} equation images with native OMML.")
        for n in sorted(replaced):
            print(f"  ({n:2d}) text={replaced[n]!r}")
        if skipped:
            print("Skipped:")
            for n, why in skipped:
                print(f"  ({n}): {why}")
        missing = sorted(set(IMAGE_TO_EQ.values()) - set(replaced.keys()))
        if missing:
            print(f"WARNING: equations not found/replaced: {missing}")
            print("  (likely already converted — re-running on an OMML docx)")
        else:
            print("All 12 equations processed.")

    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
