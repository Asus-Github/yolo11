# Codex Recovery Summary

- 当前阶段：已完成 ARS 模拟审稿、根据审稿意见修订论文、生成逐点回复与人工核验清单；已完成结构 QA；正在做最终 DOCX 渲染确认。
- 已读取文件：AGENT_HANDOFF.md；academic-research-suite 的 SKILL.md、academic-paper-reviewer/WORKFLOW.md、academic-paper/WORKFLOW.md；documents SKILL.md 与 verify_render.md；pdf SKILL.md；两篇哈理工参考 PDF 的基本信息和摘要/关键词抽取结果；当前论文 Markdown/DOCX 与生成器。
- 已写入文件：docs/paper_outputs/review_report.md；docs/paper_outputs/yolo11n-dwca-p2-hljust-reviewed.md；docs/paper_outputs/yolo11n-dwca-p2-hljust-reviewed.docx；docs/paper_outputs/revision_response.md；docs/paper_outputs/remaining_human_checks.md；docs/paper_outputs/build_review_revision_outputs.py；docs/paper_outputs/build_yolo11n_dwca_p2_paper.py；docs/paper_outputs/rendered_reviewed/page-*.png 和 PDF。
- 主要审稿发现：评价集口径需前置；P2 是主增益、CoordAttention 只能辅助表述；RTX 4090 FPS 不等同端侧部署；类别级 AP 仅作辅助解释；训练曲线不能替代多 seed 或统计显著性；局限性需补充单数据集、固定种子、未报告独立测试集 AP。
- 已做修改决策：修订稿另存为 yolo11n-dwca-p2-hljust-reviewed.docx；正文仅显示 baseline 和 DWCA-P2；不新增数据/引用；不恢复 Triplet/TDW、官方 pt 参考实验、精度-速度权衡图；公式采用居中文本公式加右侧编号，避免图片裁切和裸 LaTeX。
- 当前 QA：Markdown 图 7、表 10、参考文献 29；DOCX 段落 205、表 15（含 5 个公式布局表）、inline_shapes 7（正文图）；正文 b32、Triplet/TDW、AI 使用说明、官方预训练、精度-速度权衡、尺度分组 AP、未确认元数据均为 0。
- 注意事项：基础 yolo11n-dwca-p2-hljust.docx 在同步生成器时被重新生成过，未找到旧副本；最终交付应强调新版文件为 yolo11n-dwca-p2-hljust-reviewed.docx。
- 剩余 checklist：完成最后一次 render_docx.py；检查 page-10 公式、page-1 首页、page-18/22 后部版式；确认 LibreOffice 临时 dylib 清理；最终汇报四个必需输出路径。
- 下一步准确动作：运行 render_docx.py 生成 rendered_reviewed/page-*.png 和 PDF；运行 find 检查 libreoffice Frameworks 中无 *.codex-render-backup 和临时 dylib 残留；最终回复。
