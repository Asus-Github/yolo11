from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START


SOURCE = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版.docx")
OUTPUT = Path("docs/paper_outputs/中文版北核_DWCA-P2-哈理工学报格式版_图8空白修复.docx")


document = Document(SOURCE)
last_section = document.sections[-1]

if last_section.start_type != WD_SECTION_START.NEW_PAGE:
    raise RuntimeError(f"Expected final section to start on a new page, got {last_section.start_type!r}")

# The final two-column section begins with section 6. Making that section
# continuous lets it use the open space below Figure 8 without changing its
# column settings or any preceding figure layout.
last_section.start_type = WD_SECTION_START.CONTINUOUS

document.save(OUTPUT)
print(OUTPUT.resolve())
