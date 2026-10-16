# YOLO11n-DWCA-P2 论文项目交接文档

本文档用于把当前论文项目完整交接给新的 agent。新 agent 应先阅读本文档，再继续任何论文修改、审稿、格式转换或导出工作。

最后更新时间：2026-06-26
当前工作目录：`/Users/asus/ultralytics-paper-yolo11n-clean`

## 1. 工作区与分支

- 原始仓库目录：`/Users/asus/ultralytics`（历史实验输出、旧论文资产，工作区较乱，不要在此改论文）
- 干净论文 worktree：`/Users/asus/ultralytics-paper-yolo11n-clean`
- 干净论文分支：`codex/paper-yolo11n-dwca-p2-clean`
- Git 状态：`AGENT_HANDOFF.md`、`docs/paper_inputs/`、`docs/paper_outputs/` 均未跟踪。不要删除或回退这些文件；它们是当前论文工作的主要成果和输入。

新 agent 开始时建议执行：

```bash
cd /Users/asus/ultralytics-paper-yolo11n-clean
git branch --show-current
git status --short
```

## 2. 用户已经明确确认的硬性口径

这些要求优先级高于期刊模板中的泛化建议。

- 目标期刊：`哈尔滨理工大学学报 / Journal of Harbin University of Science and Technology`
- 作者单位：`东北林业大学 计算机与人工智能学院`
- 作者单位英文：`College of Computer and Artificial Intelligence, Northeast Forestry University`
- 最终方法名称：`YOLO11n-DWCA-P2`
- 论文对外展示模型名只使用：`baseline` 和 `DWCA-P2`
- 正文不要显式出现 `b32` 后缀；`baseline-b32` 和 `DWCA-P2-b32` 只能作为内部数据源口径写在报告或注释中，不应出现在论文正文展示名中。
- 主结果 baseline 行使用 Excel 中 `baseline-b32` 数据，对外显示为 `baseline`。
- 主结果最终模型行使用 Excel 中 `DWCA-P2-b32` 数据，对外显示为 `DWCA-P2`。
- 基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI、作者简介暂时不要写，用户需要和导师确认。
- AI 使用说明不要写。
- 不需要补做尺度分组 AP。
- 不要加入官方预训练 `.pt` 参考实验。
- 删除精度-速度权衡图，不要再恢复。
- 删除所有 Triplet / TDW / YOLOv11n-TDW 相关描述，全文围绕正增长模块路线描述。
- 不要伪造缺失数据。没有来源的小目标 AP、测试集 AP、逐图漏检数量、显著性检验、逐框预测统计等，一律不要声称。
- 不要把未发表论文全文上传到外部模型/API，除非用户明确授权。

## 3. 当前最新成果文件

最新论文输出目录：

```text
/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/
```

当前主要交付物：

- Markdown 论文：`docs/paper_outputs/yolo11n-dwca-p2-hljust.md`
- Word 论文：`docs/paper_outputs/yolo11n-dwca-p2-hljust.docx`
- 论文生成器：`docs/paper_outputs/build_yolo11n_dwca_p2_paper.py`
- 总体 QA 报告：`docs/paper_outputs/paper_generation_report.md`
- 哈理工格式转换报告：`docs/paper_outputs/hlg_format_report.md`
- 论文图目录：`docs/paper_outputs/figures/`
- 论文表目录：`docs/paper_outputs/tables/`
- Quick Look 首页预览：`docs/paper_outputs/quicklook_hlg/yolo11n-dwca-p2-hljust.docx.png`

最新格式转换已经完成，Word 文件已按《哈尔滨理工大学学报》写作规范和模板观察值做过格式调整。不要再从旧 DOCX 手工改；应优先修改生成器并重新生成 Markdown/DOCX/报告。

## 4. 当前论文内容状态（2026-06-26 实测核对）

当前论文题名（实测）：

```text
路侧交通小目标检测DWCA-P2方法
```

题名有效字符数约 18，满足期刊"20 字以内"要求。
（注意：旧版交接文档曾写作"路侧小目标检测DWCA-P2方法"，漏了"交通"二字，以本文件实测为准。）

当前论文结构（md 实测 h2 章节）：

- 中文题名、作者、单位
- 中文摘要、中文关键词
- 英文题名、作者、单位
- 英文摘要、英文关键词
- `0 引言`
- `1 相关工作`
- `2 数据集与小目标特征分析`
- `3 改进 YOLO11n 检测方法`
- `4 实验设置`
- `5 实验结果与分析`
- `6 讨论`
- `7 结论`
- `参考文献`

当前图表与参考文献计数（md 实测）：

- Markdown 图数：6（fig1 ~ fig6）
- Markdown 表数：10（正文表，docx 中另有 5 个公式编号布局表，属公式排版结构）
- 参考文献数量：29
- DOCX 嵌入图片数：12
- DOCX table 对象数：16（10 正文表 + 5 公式编号布局表 + 1 其他）

当前禁用内容检查（md 实测，全部为 0）：

- 正文可见 `b32`：0
- Triplet / TDW：0
- AI 使用说明：0
- 官方预训练参考实验：0
- 精度-速度权衡图：0
- 未确认元数据（基金、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI）：0

## 5. 当前哈理工格式转换状态

格式依据：

- 写作规范：`/Users/asus/ultralytics/docs/about/哈理工学报论文写作规范.md`
- Word 模板：`/Users/asus/ultralytics/docs/about/论文模板.docx`

已经执行的格式调整：

- 中文题名压缩到 20 字以内。
- 中文摘要约 266 个汉字，按目的、过程、结果、结论组织，避免以"本文"作为摘要主语。
- 英文摘要与中文摘要对应。
- 英文关键词中 `Dynamic Head` 和 `Wise Intersection over Union` 已展开，避免只写缩写。
- DOCX 页面设置为 A4。
- 页边距按模板观察值设置：上约 3.2 cm，下约 2.5 cm，左右约 2.0 cm。
- 正文为五号宋体/Times New Roman，1.15 倍行距，首行缩进 2 字符。
- 图题和表题在 Word 中拆成中文、英文两行。
- 表格改为三线表样式。
- Markdown 公式在 DOCX 中转换为 Word 数学对象，采用居中公式、右侧编号 `(1)` 至 `(5)`。
- 实验环境与训练参数表已缩减，只保留硬件、框架、数据集划分、输入尺寸、训练参数、测速口径等主流论文常用项。

仍按用户要求留空：基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI、作者简介、AI 使用说明。

## 6. 权威实验数据与核心结果

权威实验结果文件：

```text
/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/刘华硕-飞书导入实验记录表.xlsx
```

Excel 工作表：

- `数据表`：26 行实验记录，包含实验类型、组别名、模型 YAML、IoU 损失、Triplet、DyHead、WIoU、Precision、Recall、mAP、FPS、GFLOPs、Params、备注等。
- `FPS测量记录`：统一 FPS 测量信息。

主结果内部数据源：

| 内部组别 | 对外展示名 | Precision/% | Recall/% | mAP@0.5/% | mAP@0.5:0.95/% | FPS | GFLOPs | Params/M |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline-b32 | baseline | 85.7 | 80.8 | 86.0 | 60.2 | 152.99 | 6.30 | 2.58 |
| DWCA-P2-b32 | DWCA-P2 | 86.0 | 83.5 | 88.4 | 64.4 | 100.54 | 14.20 | 4.46 |

主方法相对 baseline 的提升：

- Precision：`+0.3`
- Recall：`+2.7`
- mAP@0.5：`+2.4`
- mAP@0.5:0.95：`+4.2`
- GFLOPs：`+7.90`
- Params：`+1.88 M`
- FPS：约 `-52.45`

论文中应谨慎表述速度：

- 可写：在统一 RTX 4090 测速口径下，DWCA-P2 为约 100.5 FPS，baseline 为约 153.0 FPS。
- 不要写：某个实际路侧端硬件上已经达到实时部署，除非另有硬件测试数据。

## 7. 当前正文方法口径

最终方法围绕正增长模块路线：

- baseline
- `+D`：引入 DyHead
- `+DW`：DyHead + WIoU
- `DWCA`：DyHead + WIoU + CoordAttention，不含 P2
- `DW-P2`：DyHead + WIoU + P2，不含 CoordAttention
- `DWCA-P2`：完整结构

核心结论边界：

- P2 高分辨率检测分支是最终性能提升的主要来源。
- DyHead 与 WIoU 构成稳定正向基线。
- CoordAttention 只作为辅助增强模块，不要夸大为主要增益来源。
- 不要把结果简单归因于"模块越多越好"。
- 当前实验不支持声称 CoordAttention 单独显著提升 mAP@0.5:0.95。

## 8. 当前图表清单（2026-06-26 实测）

图目录：

```text
/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/figures/
```

figures 目录实际文件：

- `fig1_val_scale_distribution.png`：验证集各类别短边尺度分布
- `fig2_dwca_p2_architecture.png`：YOLO11n-DWCA-P2 网络结构示意图（原图，横向 Neck，保留备用，论文未引用）
- `fig2_dwca_p2_architecture_vertical.png`：YOLO11n-DWCA-P2 网络结构示意图（竖向 Neck 版，论文当前引用此图）
- `fig3_main_metrics.png`：baseline 与 DWCA-P2 主指标对比
- `fig4_class_map_gain.png`：类别级 mAP@0.5:0.95 增益
- `fig5_training_map50_95.png`：验证集 mAP@0.5:0.95 曲线
- `fig6_training_recall.png`：验证集 Recall 曲线

正文 6 图（md 引用）：

- 图 1 → `fig1_val_scale_distribution.png`
- 图 2 → `fig2_dwca_p2_architecture_vertical.png`（竖向 Neck 版）
- 图 3 → `fig3_main_metrics.png`
- 图 4 → `fig4_class_map_gain.png`
- 图 5 → `fig5_training_map50_95.png`
- 图 6 → `fig6_training_recall.png`

注意：

- 不要恢复精度-速度权衡图。
- 不要新增官方预训练参考实验图。
- 如果要修改图，应改 `build_yolo11n_dwca_p2_paper.py` 中的绘图函数并重新生成。

## 9. 图 2 结构示意图绘制说明（本次重点修改）

论文图 2 当前使用竖向 Neck 版（`fig2_dwca_p2_architecture_vertical.png`），由生成器中的 `draw_architecture_vertical(path)` 函数生成。

### 9.1 布局

四列竖向，主链路全程竖向直线：

- **Backbone**（左列）：Input → C2PSA，从上到下。tap 盒子（layer 2/5/7/11）通过 piecewise 线性锚定到 P-level 行中心。
- **Neck · FPN**（中左列）：top-down 路径，数据流向上（P4 底 → P2 顶）。每个 P-level 内 Upsample / Concat / C3k2 三盒竖排。
- **Neck · PAN**（中右列）：bottom-up 路径，数据流向下（P2 顶 → P5 底）。每个 P-level 内 Conv / Concat / C3k2 三盒竖排。
- **Head**（右列）：4 个 Detect 盒 + 下方 DyHeadDetect 结构说明块。

FPN 与 PAN 之间唯一的主链路横向转折在顶部（layer 20 → 21）。

### 9.2 DyHeadDetect 表达方式

- 4 个 Detect 盒用一个**红色虚线容器框**整体包裹，框顶标注「DyHeadDetect · 4 尺度共享检测头」。
- 容器框下方是 DyHeadDetect 结构说明块：三级注意力堆叠图示（Scale-aware → Spatial-aware → Task-aware，带层间连接箭头）+ WIoU v3 (train-only) 脚注。
- 容器框底部到说明块顶部之间一条短连接线，不穿过任何 Detect 盒。

### 9.3 关键几何参数（`draw_architecture_vertical` 内）

- `NW, NH = 176, 52`（neck 盒尺寸）
- `SUB = 104`（同一 P-level 内三节点竖向间距）
- `band_cy` P-level 行距 320，起始 `P2 = 420`（避免 Backbone 顶部 Input 盒溢出区域上边）
- FPN 主链路连接方向：`top_pt(a) → bot_pt(b)`（a 在下、b 在上，数据流向上，箭头走在两盒间隙，不贯穿盒子）
- PAN 主链路连接方向：`bot_pt(a) → top_pt(b)`（a 在上、b 在下，数据流向下）
- C2PSA(11) → Upsample(12)：正交折线，经 Backbone 与 FPN 列之间走廊，无斜线
- C2PSA(11) → Concat(28)：走底部 corridor + PAN 列**左侧**上升（避开 29 → Detect P5 feeder 的水平线）

### 9.4 与 YAML 的一致性（已逐层核对）

全部 30 层的 C×H×W 与 `docs/paper_inputs/model_yamls/yolo11-dwca-p2.yaml` 完全一致，包括 6 个 Concat 的通道加法：

- 13: 256+128=384
- 16: 128+128=256
- 19: 64+64=128
- 22: 32+64=96
- 25: 64+128=192
- 28: 128+256=384

DyHeadDetect（layer 30）输入 `[20, 23, 26, 29]` 与图中四个 feeder 一致。CoordAttention 位于 layer 5（128×80×80）。WIoU v3 不是网络层，是训练时 bbox 回归损失，图中标注 `train-only`。

### 9.5 修改图 2 时的注意事项

- 不要覆盖 `fig2_dwca_p2_architecture.png`（原图保留备用）；竖向版输出文件名为 `fig2_dwca_p2_architecture_vertical.png`。
- `draw_architecture_vertical` 末尾有 `_crossings` 自检，任何连线穿过非端点盒子都会抛 AssertionError。修改布局后必须保持零交叉。
- 论文 md 引用（生成器内）当前指向 `fig2_dwca_p2_architecture_vertical.png`，不要改回原图。
- 标题已去掉「竖向 Neck」字样，中英文标题均为「YOLO11n-DWCA-P2 网络结构示意图 / Architecture diagram of YOLO11n-DWCA-P2 network」。

## 10. 当前表格清单

表目录：

```text
/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/tables/
```

关键 CSV：

- `experiment_records_clean.csv`：从 Excel 导出的规范化实验数据
- `main_results.csv`：主结果表
- `ablation.csv`：正增长消融实验表
- `structure_comparison.csv`：YOLO 轻量结构同口径对比表
- `speed_complexity.csv`：速度与复杂度表
- `training_params.csv`：已缩减的实验环境与训练参数表
- `dataset_split.csv`：数据集划分
- `class_distribution.csv`：类别分布
- `scale_statistics.csv`：总体尺度统计
- `val_scale_distribution_640.csv`：验证集类别尺度分布
- `class_ap_comparison.csv`：类别级 AP 对比
- `training_curves_baseline_vs_dwca_p2_b32.csv`：训练曲线数据源

当前正文 10 表：

- 表 1：DAIR-V2X-I 数据集划分与实例数
- 表 2：DAIR-V2X-I 类别实例分布
- 表 3：目标尺度统计结果
- 表 4：验证集各类别尺度分布
- 表 5：训练与测速参数设置
- 表 6：主结果对比
- 表 7：类别级 AP 对比
- 表 8：消融实验结果
- 表 9：同口径结构对比
- 表 10：速度与复杂度对比

## 11. 参考文献状态

当前参考文献数量：29 条。正文中已按顺序编码制引用，满足用户此前"至少 25 条"的要求。

注意事项：

- 当前参考文献已用于支撑 DAIR-V2X、YOLO、DyHead、CoordAttention、Wise-IoU、多尺度融合、小目标检测等背景。
- 正式投稿前仍建议人工核对期刊要求中的 GB/T 风格标点、外文作者大小写、页码、DOI、会议/期刊著录格式。
- 不要随意删除参考文献，避免正文引用断裂。

## 12. 论文生成器与复现命令

核心生成器：

```text
/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_outputs/build_yolo11n_dwca_p2_paper.py
```

生成器功能：

- 读取 Excel 实验数据。
- 导出规范化 CSV 表。
- 复制/读取旧资产中的尺度、类别 AP、训练曲线数据。
- 用 PIL 生成论文图（含 `draw_architecture` 原图与 `draw_architecture_vertical` 竖向版两个函数）。
- 生成 Markdown 论文。
- 用 python-docx 生成 DOCX。
- 生成 `paper_generation_report.md` 和 `hlg_format_report.md`。
- 生成 DOCX 时设置哈理工模板风格：A4、页边距、字体、行距、三线表、双语图表题、Word 数学公式对象。

推荐用 bundled Python 运行：

```bash
cd /Users/asus/ultralytics-paper-yolo11n-clean
/Users/asus/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/paper_outputs/build_yolo11n_dwca_p2_paper.py
```

不要用系统 Python，系统环境可能缺少 `python-docx`、`pandas` 或 Pillow。

生成器内 `make_figures` 会同时生成原图与竖向版图，但论文 md 只引用竖向版。若只改图 2，可单独调用：

```bash
python3 -c "import docs.paper_outputs.build_yolo11n_dwca_p2_paper as m; from pathlib import Path; m.draw_architecture_vertical(Path('docs/paper_outputs/figures/fig2_dwca_p2_architecture_vertical.png'))"
```

## 13. DOCX 渲染与已知环境问题

按 documents skill 要求，理想流程是用 `render_docx.py` 渲染 DOCX 为逐页 PNG，再逐页检查。

本机当前渲染失败原因：

```text
dyld: Library not loaded: /opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib
Referenced from: bundled LibreOffice libvcllo.dylib
```

已完成的可视化兜底：

- macOS Quick Look 可成功生成首页预览。
- 预览文件：`docs/paper_outputs/quicklook_hlg/yolo11n-dwca-p2-hljust.docx.png`
- 首页题名、作者、摘要、英文摘要、`0 引言` 开头可读，未见明显崩版。

注意：

- Quick Look 只验证首页，不等价于完整逐页 DOCX 渲染。
- 正式投稿前建议用户用 Word 或完整 LibreOffice 打开 DOCX 做人工版式检查。

## 14. 重要历史决策

用户曾提出并已执行的修改意见：

- 删除所有 `b32` 可见后缀，仅对外显示 baseline 和 DWCA-P2。
- 表 8 baseline 行使用 baseline-b32 数据并显示 FPS=153.0。
- 表 8 DWCA-P2 行使用 DWCA-P2-b32 数据但显示为 DWCA-P2。
- 删除精度-速度权衡图及正文引用。
- 删除官方预训练参考实验整节和表格。
- 缩减实验环境与训练参数表。
- 修复 DOCX 公式渲染：现在为 Word 数学对象，不是裸 LaTeX。
- 参考文献扩充到 25 条以上，当前为 29 条。
- 删除 AI 使用说明。
- 不补尺度分组 AP。
- 删除 Triplet/TDW 相关描述。
- 论文重点围绕正增长模块、P2 主增益、DyHead/WIoU 强基线、CoordAttention 辅助增强。

本次（2026-06-26）新增修改：

- 图 2 重绘为竖向 Neck 版（`draw_architecture_vertical` 函数），论文 md 与 docx 已切换到竖向版图。
- 竖向版采用四列竖向布局（Backbone / FPN / PAN / Head），主链路全程竖向直线，仅顶部 20→21 一处横向转折。
- DyHeadDetect 改用红色虚线容器框包裹 4 个 Detect + 下方三级注意力堆叠说明块的表达方式，不再用穿透虚线。
- 标题去掉「竖向 Neck」字样。
- Backbone 起始 y 下移（`band_cy["P2"] = 420`），修复 Input 盒溢出区域顶部的问题。
- 图例改为两行布局，修复 CoordAttention 图例项溢出画布右边界。
- 已逐层核对图中 30 层 C×H×W 与 YAML 完全一致。

## 15. 不要再做的事项

以下内容与用户后续要求冲突，新 agent 不要恢复：

- 不要恢复 `b32` 后缀到正文展示名。
- 不要恢复 Triplet、TDW、YOLOv11n-TDW 叙述。
- 不要恢复官方 `.pt` 预训练参考实验。
- 不要恢复精度-速度权衡图。
- 不要写 AI 使用声明。
- 不要补基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI、作者简介。
- 不要补做尺度分组 AP，除非用户后来明确改变决定并提供/允许重新计算所需预测数据。
- 不要声称逐图漏检数量、显著性检验或测试集 AP，除非本地能找到真实来源。
- 不要把图 2 改回横向 Neck 原图（`fig2_dwca_p2_architecture.png`）；论文当前用竖向版。
- 不要在 `draw_architecture_vertical` 中引入任何斜线连线或让箭头穿过模块盒子（自检会拦截）。

## 16. 如果需要继续修改，建议流程

1. 先读本文件和最新两个报告：
   - `AGENT_HANDOFF.md`
   - `docs/paper_outputs/paper_generation_report.md`
   - `docs/paper_outputs/hlg_format_report.md`
2. 明确用户本轮指令属于格式、内容修改、审稿还是复现检查。
3. 优先修改 `docs/paper_outputs/build_yolo11n_dwca_p2_paper.py`。
4. 运行生成器重建 Markdown、DOCX、图、表和报告。
5. 做结构检查：
   - 标题长度
   - 摘要汉字数
   - 图/表/参考文献数量
   - 禁用词与禁用内容计数
   - DOCX 中是否有裸 LaTeX
   - DOCX 中是否有 Word 数学公式对象
6. 尝试 `render_docx.py`；若仍因 `little-cms2` 失败，用 Quick Look 预览兜底并明确记录限制。
7. 最终回复用户时给出最终文件路径和未完成/需人工确认事项。

## 17. 审查论文时的核对清单

重新审查论文时，建议逐项核对：

- 题名：`路侧交通小目标检测DWCA-P2方法`，≤20 字。
- 摘要：中文约 266 字，目的/过程/结果/结论四段式；英文与中文对应。
- 关键词：中英文对应，Dynamic Head / Wise IoU 已展开。
- 章节：0 引言 → 7 结论 → 参考文献，结构完整。
- 图：6 张，fig2 为竖向 Neck 版，引用文件名 `fig2_dwca_p2_architecture_vertical.png`。
- 表：10 张正文表，三线表样式。
- 参考文献：29 条，顺序编码。
- 禁用词：b32 / Triplet / TDW / AI 使用说明 / 官方预训练 / 精度速度权衡图，均为 0。
- 主结果数字：baseline（85.7/80.8/86.0/60.2/153.0/6.3/2.6M）、DWCA-P2（86.0/83.5/88.4/64.4/100.5/14.2/4.46M）。
- 消融路线：+D / +DW / DWCA / DW-P2 / DWCA-P2 五级，P2 为主增益结论。
- 元数据留空项：基金、收稿日期、中图分类号、文献标志码、文章编号、DOI、作者简介。
- DOCX 公式：5 个 Word 数学对象，编号 (1)~(5)。
- 图 2 与 YAML 一致性：30 层 C×H×W 全部核对通过。

## 18. 给新 agent 的起始提示词

可直接把下面这段发给新 agent：

```text
请在 /Users/asus/ultralytics-paper-yolo11n-clean 继续 YOLO11n-DWCA-P2 论文任务。先阅读 /Users/asus/ultralytics-paper-yolo11n-clean/AGENT_HANDOFF.md。

当前干净分支是 codex/paper-yolo11n-dwca-p2-clean。原始脏仓库在 /Users/asus/ultralytics，不要在原始脏分支直接改论文。当前最终输出为 docs/paper_outputs/yolo11n-dwca-p2-hljust.md 和 docs/paper_outputs/yolo11n-dwca-p2-hljust.docx，生成器是 docs/paper_outputs/build_yolo11n_dwca_p2_paper.py。

目标期刊是《哈尔滨理工大学学报》。作者单位为东北林业大学计算机与人工智能学院。基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI、作者简介先不要写，AI 使用说明也不要写。

论文对外模型名只用 baseline 和 DWCA-P2，不要在正文显示 b32。主结果内部数据源为 Excel 中 baseline-b32 与 DWCA-P2-b32 行。不要恢复 Triplet/TDW、官方 pt 预训练参考实验、精度-速度权衡图，也不要补尺度分组 AP。

图 2 当前使用竖向 Neck 版（fig2_dwca_p2_architecture_vertical.png），由 draw_architecture_vertical 函数生成，不要改回横向原图。修改图时保持零连线交叉、无斜线、箭头不穿过模块盒子。

如需修改，请优先改生成器并重新生成 Markdown/DOCX/图表/QA 报告。不要伪造 Excel 和本地材料中没有的数据。
```
