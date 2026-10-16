from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


SOURCE = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版_图8空白修复.docx")
OUTPUT = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版_规范修订.docx")


def set_run_font(run, east=None, ascii_name=None, size=None, bold=None):
    run.font.name = ascii_name or east
    if east or ascii_name:
        rpr = run._r.get_or_add_rPr()
        rfonts = rpr.rFonts
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.insert(0, rfonts)
        if east:
            rfonts.set(qn("w:eastAsia"), east)
        if ascii_name:
            rfonts.set(qn("w:ascii"), ascii_name)
            rfonts.set(qn("w:hAnsi"), ascii_name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def set_para_spacing(para, line=1.15, before=0, after=0):
    fmt = para.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing = line
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)


def clear_fixed_page_number(paragraph):
    # Replace a literal footer number with a PAGE field so each page is numbered.
    if paragraph.text.strip() != "1":
        return
    for child in list(paragraph._p):
        paragraph._p.remove(child)
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_sep, text, fld_end])


document = Document(SOURCE)

# Match the journal's body spacing and avoid accidental direct-font overrides.
for para in document.paragraphs:
    set_para_spacing(para)
    for run in para.runs:
        if run.font.size is None and para.style.name not in {"Heading 1", "Heading 2"}:
            run.font.size = Pt(10.5)
        if run.text and para.style.name not in {"Heading 1", "Heading 2"}:
            # Set East Asian glyphs explicitly; keep Latin glyphs in Times New Roman.
            set_run_font(run, east="宋体", ascii_name="Times New Roman")

for table in document.tables:
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                set_para_spacing(para, line=1.15)
                for run in para.runs:
                    set_run_font(run, east="宋体", ascii_name="Times New Roman", size=9)

# Heading hierarchy: HeiTi, 12 pt, bold, with the journal's compact spacing.
for para in document.paragraphs:
    if para.style.name == "Heading 1":
        set_para_spacing(para, before=6, after=0)
        for run in para.runs:
            set_run_font(run, east="黑体", ascii_name="Times New Roman", size=12, bold=True)
    elif para.style.name == "Heading 2":
        set_para_spacing(para, before=3, after=0)
        for run in para.runs:
            set_run_font(run, east="黑体", ascii_name="Times New Roman", size=10.5, bold=True)

# Front matter follows the template's Chinese/English hierarchy.
front = {0: ("黑体", "Times New Roman", 18, True), 1: ("楷体", "Times New Roman", 15, True),
         2: ("宋体", "Times New Roman", 9, False), 3: ("楷体", "Times New Roman", 10, None),
         4: ("楷体", "Times New Roman", 10, None), 5: ("宋体", "Times New Roman", 9, None),
         6: ("Times New Roman", "Times New Roman", 16, True), 7: ("Times New Roman", "Times New Roman", 12, True),
         8: ("Times New Roman", "Times New Roman", 9, False), 9: ("Times New Roman", "Times New Roman", 10, None),
         10: ("Times New Roman", "Times New Roman", 10, None)}
for idx, spec in front.items():
    para = document.paragraphs[idx]
    set_para_spacing(para, line=1.15)
    for run in para.runs:
        set_run_font(run, east=spec[0], ascii_name=spec[1], size=spec[2], bold=spec[3])

# Figure/table captions: Chinese first, English second, centered, 9 pt bold.
for para in document.paragraphs:
    text = para.text.strip()
    if text.startswith(("图", "表")) and (text[1:2].isdigit()):
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            set_run_font(run, east="黑体", ascii_name="Times New Roman", size=9, bold=True)
    elif text.startswith(("Fig.", "Table ")):
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            set_run_font(run, east="Times New Roman", ascii_name="Times New Roman", size=9, bold=True)

# References: 9 pt, 1.25 spacing, hanging indent as already used by the manuscript.
for para in document.paragraphs:
    if para.text.strip().startswith("["):
        set_para_spacing(para, line=1.25)
        para.paragraph_format.left_indent = Pt(18)
        para.paragraph_format.first_line_indent = Pt(-18)
        for run in para.runs:
            set_run_font(run, east="宋体", ascii_name="Times New Roman", size=9)

for section in document.sections:
    for para in section.footer.paragraphs:
        clear_fixed_page_number(para)

document.save(OUTPUT)
print(OUTPUT.resolve())
