# YOLO11n-DWCA-P2 论文生成报告

- 输入 Excel：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/刘华硕-飞书导入实验记录表.xlsx`
- 目标期刊模板：`/Users/asus/ultralytics/docs/about/论文模板.docx`
- Markdown：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/yolo11n-dwca-p2-hljust.md`
- Word：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/yolo11n-dwca-p2-hljust.docx`
- 表格目录：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/tables`
- 图片目录：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/figures`

## 数据完整性

- Excel 数据表行数：26
- 主结果数据源：内部读取 Excel 的 `baseline-b32` 与 `DWCA-P2-b32` 行；正文展示名统一为 baseline 与 DWCA-P2。
- Markdown 图数：11
- Markdown 表数：11
- 参考文献数量：30
- 正文可见 b32 后缀：0
- 禁用内容计数：Triplet/TDW=0, 外部权重参考=0, 精度-速度权衡图=0, AI 使用说明=0, 未确认元数据=0
- 哈理工格式检查：中文题名 18 个有效字符；中文摘要约 266 个汉字；关键词、图题、表题均保留中英文。

## 关键结论口径

- 最终方法名：YOLO11n-DWCA-P2。
- 正文最终模型展示名：DWCA-P2；baseline 展示名：baseline。
- 表 8 baseline 行使用固定 batch 复验数据，FPS=153.0；DWCA-P2 行使用最终固定 batch 复验数据，FPS=100.5。
- 正文消融实验已收敛到 DyHead、WIoU、CoordAttention 与 P2 分支的正增长路线。
- 已删除精度-速度权衡图及外部权重参考实验；速度信息仅保留在速度与复杂度表。
- 不同目标尺度下的细分指标、显著性检验和逐图漏检数量未在本地材料中发现，正文未声称；按用户确认，本轮不补做额外尺度细分实验。
- FPS 已按 Excel 中统一 RTX 4090 测量口径写入速度与复杂度分析。

## 待作者确认信息

- 基金项目、收稿日期、中图分类号、文献标志码、文章编号和稿件 DOI 暂不写入正文，待作者与导师确认后再补。
- 作者单位已按用户确认更新为东北林业大学计算机与人工智能学院。
- 参考文献已补充至 25 条以上，并已在引言、相关工作、方法依据和数据分析中真实引用；正式投稿前仍建议按期刊模板逐条核对标点、大小写和页码。

## Word 渲染 QA

- DOCX 已按模板观察结果设置 A4、页边距约上 3.2 cm、下 2.5 cm、左右 2.0 cm，正文五号宋体/Times New Roman，1.15 倍行距。
- 图题与表题均在 Word 中拆成中文、英文两行；正文表格已改为三线表样式。
- DOCX 生成器已将 Markdown 公式转换为居中文本公式，并采用右侧编号的版式，避免 Word 中显示裸 LaTeX 公式文本。
- DOCX 正文结构预期：11 张正文表、11 张正文图；程序结构统计中还会额外出现 12 个公式编号布局表。
- macOS Quick Look 已能解析 DOCX 并生成首页缩略图，首页题名、作者、摘要和引言开头未见明显崩版；作者单位编号已在 Word 中按上标处理。
- 本机 LibreOffice 渲染未完成，原因是 bundled LibreOffice 依赖 `/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib`，当前环境无权限创建该路径；`DYLD_LIBRARY_PATH` 也未能覆盖该硬编码依赖。
- 因此本次按 documents skill fallback 做了结构与资源检查和首页缩略图检查，未能提供完整逐页 PNG 视觉验收。建议在装有完整 LibreOffice/Word 的机器上最终打开 DOCX 做一次人工版式确认。
