# 哈理工学报格式转换报告

- 论文 Markdown：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/yolo11n-dwca-p2-hljust.md`
- 论文 DOCX：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/yolo11n-dwca-p2-hljust.docx`
- 写作规范：`/Users/asus/ultralytics/docs/about/哈理工学报论文写作规范.md`
- 参考模板：`/Users/asus/ultralytics/docs/about/论文模板.docx`

## 已执行格式调整

- 中文题名改为 `路侧交通小目标检测DWCA-P2方法`，有效字符数为 18，满足 20 字以内要求。
- 中文摘要约 267 个汉字，按目的、过程、结果和结论组织，避免使用“本文”作为主语。
- 英文摘要与中文摘要内容对应，英文关键词中 `Dynamic Head` 和 `Wise Intersection over Union` 已展开。
- DOCX 按模板观察值设置 A4 页面、上 3.2 cm、下 2.5 cm、左右 2.0 cm 页边距；正文采用五号宋体/Times New Roman、1.15 倍行距、首行缩进 2 字符。
- 图题、表题均采用中文题名与英文题名分行显示；表格改为三线表。
- Markdown 公式在 DOCX 中转换为居中文本公式，并采用右侧编号 `(1)` 至 `(12)`。
- 实验环境与训练参数表已缩减为硬件、框架、数据集划分、输入尺寸、训练参数和测速口径等主流论文常用项。

## 按用户要求保留为空

- 基金项目、收稿日期、中图分类号、文献标志码、文章编号和稿件 DOI 未写入。
- 作者简介未补写，等待作者与导师确认。
- AI 使用说明未写入。

## 计数检查

- Markdown 图数：11
- Markdown 表数：11
- 参考文献数量：30
- 可见 b32 后缀：0
- DOCX 结构检查：11 张正文表 + 12 个公式编号布局表，11 张正文图。

## 渲染说明

- 本机 bundled LibreOffice 仍因缺少 `/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib` 无法完成逐页 PNG 渲染。
- 已完成 DOCX 结构检查和 macOS Quick Look 首页预览检查；正式投稿前建议在 Word 或完整 LibreOffice 环境中做最终人工版式确认。
