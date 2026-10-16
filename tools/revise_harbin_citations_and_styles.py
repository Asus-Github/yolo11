from copy import deepcopy
from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


SOURCE = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版_最终格式修订.docx")
OUTPUT = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版_引用与格式修订.docx")
CITATION = re.compile(r"\[(\d+)(?:\s*[-－–—]\s*(\d+))?\]")


def set_fonts(run, east_asia, latin="Times New Roman", size=None, bold=None):
    run.font.name = latin
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), east_asia)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def replace_run_text(paragraph, replacements):
    """Replace text in-place so existing run-level formatting is retained."""
    for old, new in replacements:
        runs = list(paragraph.runs)
        joined = "".join(r.text for r in runs)
        start = joined.find(old)
        if start < 0:
            raise RuntimeError(
                f"Expected run text not found in paragraph {paragraph.text[:80]!r}: {old!r}"
            )
        end = start + len(old)
        pos = 0
        first = last = None
        for idx, run in enumerate(runs):
            next_pos = pos + len(run.text)
            if first is None and start < next_pos:
                first = idx
            if end <= next_pos:
                last = idx
                break
            pos = next_pos
        if first is None or last is None:
            raise RuntimeError(f"Could not map replacement span {old!r} to runs")
        if first == last:
            run = runs[first]
            local_start = start - sum(len(r.text) for r in runs[:first])
            run.text = run.text[:local_start] + new + run.text[local_start + len(old):]
            continue
        first_run, last_run = runs[first], runs[last]
        first_base = sum(len(r.text) for r in runs[:first])
        last_base = sum(len(r.text) for r in runs[:last])
        prefix = first_run.text[:start - first_base]
        suffix = last_run.text[end - last_base:]
        first_run.text = prefix + new
        last_run.text = suffix
        parent = first_run._r.getparent()
        for run in runs[first + 1:last]:
            parent.remove(run._r)


def split_and_superscript_citations(paragraph):
    for run in list(paragraph.runs):
        matches = list(CITATION.finditer(run.text))
        if not matches:
            continue
        parent = run._r.getparent()
        insert_at = parent.index(run._r)
        cursor = 0
        pieces = []
        for match in matches:
            if match.start() > cursor:
                pieces.append((run.text[cursor:match.start()], False))
            normalized = f"[{match.group(1)}"
            if match.group(2):
                # En dash sits on the visual midline; the full-width Chinese
                # hyphen used previously renders too high in superscript text.
                normalized += f"–{match.group(2)}"
            normalized += "]"
            pieces.append((normalized, True))
            cursor = match.end()
        if cursor < len(run.text):
            pieces.append((run.text[cursor:], False))
        for text, superscript in pieces:
            new_r = deepcopy(run._r)
            for child in list(new_r):
                if child.tag != qn("w:rPr"):
                    new_r.remove(child)
            t = OxmlElement("w:t")
            if text.startswith(" ") or text.endswith(" "):
                t.set(qn("xml:space"), "preserve")
            t.text = text
            new_r.append(t)
            rpr = new_r.get_or_add_rPr()
            old_va = rpr.find(qn("w:vertAlign"))
            if old_va is not None:
                rpr.remove(old_va)
            if superscript:
                va = OxmlElement("w:vertAlign")
                va.set(qn("w:val"), "superscript")
                rpr.append(va)
            parent.insert(insert_at, new_r)
            insert_at += 1
        parent.remove(run._r)


def scale_inline_drawing(paragraph, factor):
    """Scale an inline picture while keeping its OOXML extents consistent."""
    for extent in paragraph._p.xpath('.//wp:extent | .//a:xfrm/a:ext'):
        for attr in ('cx', 'cy'):
            value = extent.get(attr)
            if value:
                extent.set(attr, str(round(int(value) * factor)))


def set_section_columns(paragraph, count, space_twips=425):
    sect_pr = paragraph._p.pPr.find(qn('w:sectPr'))
    if sect_pr is None:
        raise RuntimeError(f"Expected section break at paragraph {paragraph.text!r}")
    cols = sect_pr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sect_pr.append(cols)
    cols.set(qn('w:num'), str(count))
    cols.set(qn('w:space'), str(space_twips))


document = Document(SOURCE)

# Keep the English keyword block within the two-column text width. The manual
# line break mirrors the journal's reference layout and prevents an overlong
# single line from stretching the first-page composition.
replace_run_text(document.paragraphs[10], [
    ("high-resolution feature; dynamic head", "high-resolution feature;\ndynamic head"),
])

# Figure 3 is tall enough to force section 4 onto a new page after the required
# first-use expansions. A modest proportional reduction keeps it readable and
# removes the resulting half-page void without separating it from its captions.
scale_inline_drawing(document.paragraphs[55], 0.82)
for idx, para in enumerate(document.paragraphs):
    if idx != 55 and para._p.xpath('.//w:drawing'):
        # Figure 2 is the core architecture diagram and must remain readable at
        # full-page width. Figure 1 can be slightly more compact to leave enough
        # vertical room for the following full-width figure block.
        factor = {35: 0.40, 48: 0.80, 97: 0.72, 141: 1.00}.get(idx, 1.00)
        scale_inline_drawing(para, factor)

# Tables 4/5 and Figures 4/5 are adjacent full-width blocks. The source placed
# an empty two-column section between each pair, forcing the figures onto new
# pages and leaving the preceding pages largely unused. Remove only those empty
# intervening sections; the full-width section boundaries around the actual
# table and figure blocks remain intact.
redundant_sections = [document.paragraphs[i] for i in (96, 108)]
for empty_section in redundant_sections:
    if empty_section.text or empty_section._p.pPr.find(qn("w:sectPr")) is None:
        raise RuntimeError("Expected an empty section break before a figure")
    empty_section._element.getparent().remove(empty_section._element)

# Headings in the source inherit an Office theme accent color. Pin both their
# direct formatting and OOXML color to black so Word cannot reapply blue.
for para in document.paragraphs:
    if para.style.name not in ("Heading 1", "Heading 2"):
        continue
    for run in para.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)
        color = run._r.get_or_add_rPr().find(qn("w:color"))
        if color is None:
            color = OxmlElement("w:color")
            run._r.get_or_add_rPr().append(color)
        color.attrib.pop(qn("w:themeColor"), None)
        color.attrib.pop(qn("w:themeTint"), None)
        color.attrib.pop(qn("w:themeShade"), None)
        color.set(qn("w:val"), "000000")

# English abstract: define only the necessary names; keep metrics concise.
replace_run_text(document.paragraphs[9], [
    ("A scale audit of DAIR-V2X-I shows", "A scale audit of the DAIR-V2X infrastructure-side dataset (DAIR-V2X-I) shows"),
    ("a scale-prior detector, YOLO11n-DWCA-P2, is proposed", "a scale-prior You Only Look Once version 11 nano detector (YOLO11n-DWCA-P2) is proposed"),
    ("uses DyHead", "uses Dynamic Head (DyHead)"),
    ("adopts Wise-IoU v3", "adopts Wise Intersection over Union version 3 (Wise-IoU v3)"),
])
# The Chinese abstract is independently read in production databases, so its
# first-use technical names are expanded as well.
replace_run_text(document.paragraphs[3], [
    ("YOLO11n-DWCA-P2", "You Only Look Once version 11 nano（YOLO11n）-DWCA-P2"),
    ("DyHead", "Dynamic Head（DyHead）"),
    ("CoordAttention", "Coordinate Attention（CoordAttention）"),
    ("Wise-IoU", "Wise Intersection over Union（Wise-IoU）"),
])

# Main text: expand technical abbreviations at their first substantive use.
replace_run_text(document.paragraphs[13], [
    ("Faster R-CNN", "Faster Region-based Convolutional Neural Network（Faster R-CNN）"),
    ("YOLO 系列", "You Only Look Once（YOLO）系列"),
    ("RT-DETR", "Real-Time Detection Transformer（RT-DETR）"),
])
replace_run_text(document.paragraphs[13], [("） 为", "）为"), ("） 等", "）等")])
replace_run_text(document.paragraphs[20], [
    ("FPN 通过", "特征金字塔网络（Feature Pyramid Network，FPN）通过"),
    ("PANet 进一步", "路径聚合网络（Path Aggregation Network，PANet）进一步"),
    ("SNIP 从", "图像金字塔尺度归一化（Scale Normalization for Image Pyramids，SNIP）从"),
    ("SAHI 则", "切片辅助超推理（Slicing Aided Hyper Inference，SAHI）则"),
    ("BiFPN", "双向特征金字塔网络（Bidirectional Feature Pyramid Network，BiFPN）"),
])
replace_run_text(document.paragraphs[20], [("通过 双向", "通过双向"), ("） 进行", "）进行")])
replace_run_text(document.paragraphs[22], [
    ("SENet 首先", "压缩激励网络（Squeeze-and-Excitation Network，SENet）首先"),
    ("CBAM 进一步", "卷积块注意力模块（Convolutional Block Attention Module，CBAM）进一步"),
    ("ECA-Net 则", "高效通道注意力网络（Efficient Channel Attention Network，ECA-Net）则"),
])
replace_run_text(document.paragraphs[31], [
    ("COCO 中", "通用目标检测数据集 Common Objects in Context（COCO）中"),
])
replace_run_text(document.paragraphs[31], [("参照 通用", "参照通用")])
replace_run_text(document.paragraphs[73], [
    ("令 LIoU=1−IoU", "令 LIoU=1−IoU，其中 IoU 表示交并比（Intersection over Union）"),
])
replace_run_text(document.paragraphs[79], [
    ("GIoU[28]", "广义交并比（Generalized Intersection over Union，GIoU）[28]"),
    ("DIoU[29]", "距离交并比（Distance Intersection over Union，DIoU）[29]"),
])
replace_run_text(document.paragraphs[82], [
    ("优化器为 SGD", "优化器为随机梯度下降（Stochastic Gradient Descent，SGD）"),
])
replace_run_text(document.paragraphs[88], [
    ("mAP@0.5、mAP@0.5:0.95", "平均精度均值（mean Average Precision，mAP）@0.5、mAP@0.5:0.95"),
    ("每秒帧数（FPS）", "每秒帧数（frames per second，FPS）"),
    ("GFLOPs", "十亿次浮点运算量（giga floating-point operations，GFLOPs）"),
])

# Chinese and English figure/table captions are 9 pt, bold, centered.
for para in document.paragraphs:
    text = para.text.strip()
    if re.match(r"^[图表]\d+", text):
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            set_fonts(run, "黑体", size=9, bold=True)
    elif text.startswith(("Fig.", "Table ")):
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            set_fonts(run, "Times New Roman", size=9, bold=True)

# Keep each embedded figure with both caption lines. The original manuscript
# already chains the Chinese caption to the English caption; the drawing must
# remain chained to them so a figure title cannot be stranded on the next page.
for para in document.paragraphs:
    if para._p.xpath('.//w:drawing'):
        ppr = para._p.get_or_add_pPr()
        for tag in ('keepNext', 'keepLines'):
            if ppr.find(qn('w:' + tag)) is None:
                ppr.append(OxmlElement('w:' + tag))

# In-text references use bracketed superscripts; the reference list stays baseline.
reference_heading_index = next(i for i, p in enumerate(document.paragraphs) if p.text.strip() == "参考文献")
for para in document.paragraphs[:reference_heading_index]:
    split_and_superscript_citations(para)

# Reference heading and entries follow the journal template.
ref_heading = document.paragraphs[reference_heading_index]
ref_heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
ref_heading.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
ref_heading.paragraph_format.line_spacing = 1.5
ref_heading.paragraph_format.space_before = Pt(10.5)
ref_heading.paragraph_format.space_after = Pt(0)
for run in ref_heading.runs:
    set_fonts(run, "黑体", size=9, bold=True)

for para in document.paragraphs[reference_heading_index + 1:]:
    if not para.text.strip().startswith("["):
        continue
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    para.paragraph_format.line_spacing = 1.25
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(0)
    para.paragraph_format.left_indent = Pt(18)
    para.paragraph_format.first_line_indent = Pt(-18)
    for run in para.runs:
        set_fonts(run, "宋体", size=9, bold=False)

document.save(OUTPUT)
print(OUTPUT.resolve())
