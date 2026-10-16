# 小论文写作全线路文档：基于 ARS 与当前 YOLOv11n 改进实验

> 作者：刘华硕  
> 项目：`/Users/asus/ultralytics`  
> 目标：利用 `academic-research-skills-codex` 与本项目实验结果，完成一篇可投稿/可用于学位阶段成果的小论文初稿、审稿式自检与修订闭环。  
> 当前建议入口：先走 `experiment-agent validate`，再走 `academic-paper plan`，随后分节写作、审稿、修订。

> 写作口径更新：按用户确认，以 `/Users/asus/ultralytics/刘华硕-实验记录表.xlsx` 为主数据源；实验记录表中的所有实验在论文中均按 `batch=32` 统一口径书写和解释。若历史 `args.yaml`、训练备注、早期交接记录或表格备注中出现 `AutoBatch`、`batch=0.85` 等旧表述，后续成稿时不作为论文训练口径引用；保留这些文件仅作为实验归档证据。

---

## 0. 这篇小论文最应讲什么

### 0.1 建议论文题目

优先题目：

> 面向路侧小目标检测的改进 YOLOv11n 方法：融合 P2 高分辨率检测头、DyHead 与 Wise-IoU

备选题目：

1. 面向车路协同路侧感知的小目标检测改进 YOLOv11n 方法
2. 融合高分辨率 P2 检测头与动态检测头的路侧目标检测方法
3. 面向 DAIR-V2X-I 路侧场景的轻量化 YOLOv11n 小目标检测改进

不建议把题目写成“Triplet Attention + DyHead + WIoU 改进 YOLOv11n”，因为当前实验结果显示 Triplet 系列收益不足，真正支撑论文贡献的是 `P2` 小目标检测头、`DyHead`、`WIoU`，以及可选的 `CoordAttention` 边际协同。

### 0.2 核心论点

建议主论点：

> DAIR-V2X-I 路侧图像具有小目标密集特征，单纯引入注意力模块并不能稳定提升 YOLOv11n 的检测性能；在 DyHead 与 WIoU 构成的强基线基础上，引入 P2/4 高分辨率检测分支能显著增强小目标召回与定位质量。CoordAttention 对最终方案有一定协同价值，但分解消融显示主要增益来自 P2 检测头。

这个论点的好处是：

- 和数据特征一致：标签统计显示小目标比例极高。
- 和实验结果一致：`DW-P2` 几乎复现 `DWCA-P2` 的 mAP50-95。
- 不夸大贡献：CA 不是主贡献，Triplet 是负面探索/路线收束证据。
- 能回答审稿人问题：为什么不是简单堆模块，而是根据失败路线逐步收束。

---

## 1. 当前证据资产

### 1.1 主要数据与结果文件

| 材料 | 路径 | 用途 |
|---|---|---|
| 实验总表 | `/Users/asus/ultralytics/刘华硕-实验记录表.xlsx` | 论文主结果表、消融表、对比表；后续写作以此表为准 |
| 历史导入表 | `/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx` | 早期导入/备份材料，不作为优先数据源 |
| 同名 CSV | `/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.csv` | 便于脚本统计和制图；若与主 Excel 不一致，以主 Excel 为准 |
| 数据集配置 | `/Users/asus/ultralytics/datasets/dair_v2x_i/dair_v2x_i.yaml` | 方法/实验设置中说明数据集类别 |
| 实验产物目录 | `/Users/asus/ultralytics/runs/detect/runs/ablation/` | 每组实验的曲线、混淆矩阵、结果 CSV、样例图 |
| 交接记录 | `/Users/asus/ultralytics/HANDOFF.md` | 实验历史、训练口径、结论演化 |
| 下一阶段实验需求 | `/Users/asus/ultralytics/docs/REQUIREMENTS-next-experiments.md` | 方法演进依据和设计动机 |

### 1.2 数据集事实

数据集：DAIR-V2X-I 路侧单目图像检测任务。当前配置类别为 8 类：

`Car`、`Truck`、`Van`、`Bus`、`Cyclist`、`Motorcyclist`、`Pedestrian`、`Trafficcone`。

本地标签统计：

| 划分 | 标注文件数 | 实例数 |
|---|---:|---:|
| train | 4940 | 227831 |
| val | 1411 | 65255 |
| test | 707 | 32628 |
| total | 7058 | 325714 |

全量类别分布：

| 类别 | 实例数 | 占比 |
|---|---:|---:|
| Car | 91443 | 28.07% |
| Truck | 3501 | 1.07% |
| Van | 6767 | 2.08% |
| Bus | 3379 | 1.04% |
| Cyclist | 17244 | 5.29% |
| Motorcyclist | 18256 | 5.60% |
| Pedestrian | 25194 | 7.74% |
| Trafficcone | 159930 | 49.10% |

按 640 输入尺度折算的小目标特征：

| 小目标定义 | 实例数 | 占比 |
|---|---:|---:|
| area < 32^2 px | 259421 | 79.65% |
| short side < 16 px | 223453 | 68.60% |
| short side < 32 px | 285172 | 87.55% |
| both sides < 32 px | 183595 | 56.37% |

类别级观察：

- `Pedestrian`：short side < 32 px 占 99.9%，中位短边约 8.9 px。
- `Trafficcone`：short side < 32 px 占 100.0%，中位短边约 4.2 px。
- `Cyclist`：short side < 32 px 占 93.4%，中位短边约 14.4 px。
- `Motorcyclist`：short side < 32 px 占 88.4%，中位短边约 15.5 px。

论文中可用的动机句：

> DAIR-V2X-I 路侧视角下远距离行人、骑行者和交通锥目标尺度较小。基于 YOLO 标注框的统计显示，在 640 输入尺度下，短边小于 32 像素的目标占 87.55%，其中 Pedestrian 与 Trafficcone 的中位短边分别仅约 8.9 像素和 4.2 像素。因此，原 YOLOv11n 的 P3/P4/P5 三尺度检测结构对极小目标存在特征分辨率不足的问题。

注意：该统计基于 YOLO 归一化标签和 640 输入尺度折算，不依赖原图实际像素尺寸。论文中应写清楚统计口径。

---

## 2. 实验结果的正确叙事

### 2.1 主结果

按用户确认，本文写作中所有实验均按 `batch=32` 的统一训练口径处理。`baseline-b32` 与 `DWCA-P2-b32` 保留为实验记录表中的组别名，但不再被解释为相对其他实验的“特殊复验口径”。建议将二者作为主结果对比：

注意：主 Excel 中第 25-26 行的实验类型仍显示为 `batch固定复验`，这是历史记录分类名。论文正文应将其表述为“统一 batch=32 训练口径下的最终主结果”，不要写成只有这两组才是 batch=32、其他实验不是 batch=32。

| 模型 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| baseline-b32 | 85.7 | 80.8 | 86.0 | 60.2 | 6.3 | 2.58 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |
| 提升 | +0.3 | +2.7 | +2.4 | +4.2 | +7.9 | +1.88 |

如果审稿或导师追问 `DWCA-P2` 与 `DWCA-P2-b32` 的关系，可解释为同一主方法在统一 batch=32 口径下的记录版本/重复实验结果：`DWCA-P2` 为 88.2/64.4，`DWCA-P2-b32` 为 88.4/64.4，mAP50-95 保持一致，说明主结论较稳定。论文主表建议采用 `DWCA-P2-b32` 作为最终记录值，消融分析中保留 `DWCA-P2` 用于和 `DW-P2`、`DWCA` 做分解比较。

建议写法：

> 在统一 batch=32、nbs=64 的训练口径下，DWCA-P2-b32 相比 YOLOv11n baseline-b32 的 mAP50 从 86.0% 提升至 88.4%，mAP50-95 从 60.2% 提升至 64.4%，Recall 从 80.8% 提升至 83.5%。这表明改进结构对目标召回和定位质量均有明显提升，尤其是更严格 IoU 阈值下的综合定位性能。

必须同时承认代价：

> 该提升伴随计算量增加，GFLOPs 从 6.3 增至 14.2，参数量从 2.58M 增至 4.46M。因此本文方法更适合路侧设备、边缘服务器或对精度优先的车路协同感知场景，而不是极端低算力端侧部署。

### 2.2 分解消融：P2 是主要增益来源

本节所有消融实验均按 `batch=32` 完成和解释，包括 `baseline`、`+T`、`+D`、`+W`、`+TD`、`+TW`、`+DW`、`TDW`、`TDW-CO`、`DWCA`、`DW-P2`、`DWCA-P2` 等实验组。也就是说，后续不再区分早期 AutoBatch 结果与固定 batch 结果，而是把实验记录表中的各组统一视为同一 batch 口径下的对比。

| 模型 | 结构含义 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M |
|---|---|---:|---:|---:|---:|---:|---:|
| +DW | DyHead + WIoU | 86.0 | 81.9 | 87.0 | 61.3 | 9.3 | 4.35 |
| DWCA | + CoordAttention，去 P2 | 86.8 | 81.4 | 86.8 | 61.3 | 9.3 | 4.36 |
| DW-P2 | + P2，去 CA | 85.6 | 83.5 | 88.1 | 64.4 | 14.2 | 4.45 |
| DWCA-P2 | + CoordAttention + P2 | 86.1 | 83.3 | 88.2 | 64.4 | 14.2 | 4.46 |

分析：

- `DWCA` 相比 `+DW` 没有提升 mAP50-95，说明单独 CA 贡献有限。
- `DW-P2` 相比 `+DW` 的 mAP50 提升 +1.1，mAP50-95 提升 +3.1，Recall 提升 +1.6。
- `DWCA-P2` 相比 `DW-P2` 仅 mAP50 +0.1，mAP50-95 持平。
- 因此：P2 分支是主增益来源，CA 是边际协同或精度调节项。

建议写法：

> 分解消融表明，P2 高分辨率分支对性能提升起主要作用。去除 CA 后的 DW-P2 仍取得 88.1% mAP50 和 64.4% mAP50-95，几乎复现完整 DWCA-P2 的 88.2% 和 64.4%。相比之下，仅引入 CA 而不增加 P2 分支的 DWCA 与 +DW 基本持平。这说明在当前路侧小目标密集场景中，提升高分辨率检测尺度比单独引入轻量注意力更关键。

### 2.3 Triplet 路线应写成“探索失败后的方法收束”

本节 Triplet 路线相关实验同样按 `batch=32` 统一口径解释。它们的作用不是证明最终方法最优，而是说明 Triplet 插入、channel-only 变体、P3 位置调整和 DyHead 加深都未超过 `+DW` 强基线，从而支撑方法路线从注意力堆叠转向 P2 小目标分支。

实验记录表中另有一条 `参考实验（误跑）TDW-CO-P3`，其 IoU 损失为 `CIoU（误跑）`，备注说明原计划为 WIoU 但实际未设置 `BboxLoss.iou_type="wiou"`。该行只能作为实验过程说明，不纳入 WIoU 消融主结论；论文表格应采用正式 `下一阶段消融实验 TDW-CO-P3` 行。

| 模型 | 主要改动 | mAP50/% | mAP50-95/% |
|---|---|---:|---:|
| baseline | YOLOv11n | 85.9 | 60.9 |
| +T | Triplet | 85.9 | 60.2 |
| +D | DyHead | 86.6 | 61.3 |
| +W | WIoU | 86.0 | 60.2 |
| +DW | DyHead + WIoU | 87.0 | 61.3 |
| TDW | Triplet + DyHead + WIoU | 86.5 | 60.9 |
| TDW-CO | channel-only Triplet + DyHead + WIoU | 86.7 | 61.2 |
| TDW-CO-P3 | Triplet 移至 P3 | 86.7 | 61.1 |
| TDW-CO-D3 | DyHead blocks 2 -> 3 | 86.3 | 61.1 |

建议叙事：

> 初始实验尝试将 Triplet Attention、DyHead 与 WIoU 组合，但结果显示 Triplet 系列未能超过 DyHead + WIoU 的强基线。进一步将 Triplet 改为 channel-only、移动至 P3 层，或增加 DyHead 堆叠深度，均未带来稳定增益。这说明本任务中空间注意力与 DyHead 的空间建模可能存在功能重叠，继续堆叠注意力模块并非最优路径。基于这一结果，本文转向更符合路侧小目标特征的结构改进，即增加 P2/4 高分辨率检测分支，并以轻量 CoordAttention 替代 Triplet 作为边际增强模块。

这段非常重要：它把“失败实验”转化为方法设计依据。

### 2.4 对比实验必须分表

不要把 `.pt` 预训练模型、scratch/YAML 结构对比、消融实验混在同一个主表里。

建议三张表：

1. 主消融表：只比较同一 YOLOv11n 主线上的模块增删。
2. 同口径结构对比表：比较 `YOLOv5n-yaml`、`YOLOv8n-yaml`、`YOLOv10n-yaml`、`YOLOv11n baseline` 与本文方法。
3. 官方预训练参考表：比较 `.pt` 权重结果，只作为参考。

同口径结构对比建议：

本表中的结构对比实验也按 `batch=32` 统一口径解释。`yaml` 组用于比较不同 YOLO 结构在相同训练口径下的表现，重点是公平结构对比，而不是预训练权重能力比较。

| 模型 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv5n-yaml | 85.4 | 81.0 | 85.8 | 59.9 | 7.1 | 2.50 |
| YOLOv8n-yaml | 86.5 | 81.2 | 86.5 | 61.0 | 8.1 | 3.01 |
| YOLOv10n-yaml | 85.8 | 80.1 | 85.7 | 60.7 | 8.4 | 2.71 |
| YOLOv11n baseline | 85.9 | 80.8 | 85.9 | 60.9 | 6.4 | 2.60 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |

官方预训练参考表建议：

本表中的 `.pt` 实验同样按 `batch=32` 训练/验证口径写入论文，但由于 `.pt` 模型涉及官方预训练权重来源，与 scratch/YAML 结构对比仍需分表展示，不能作为严格同源公平比较。

| 模型 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv5n.pt | 87.3 | 81.4 | 87.0 | 62.3 | 7.8 | 2.65 |
| YOLOv8n.pt | 87.2 | 82.1 | 87.3 | 62.8 | 8.1 | 3.01 |
| YOLOv10n.pt | 85.2 | 81.3 | 86.9 | 63.5 | 6.5 | 2.27 |
| YOLOv11n.pt | 86.4 | 81.6 | 87.0 | 62.3 | 6.3 | 2.58 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |

说明句：

> 由于官方 `.pt` 模型引入了预训练权重和训练历史差异，本文将其作为参考实验而非严格同口径公平对比。公平结构对比以 YAML/scratch 或明确一致训练口径为主。

---

## 3. 方法结构怎么写

### 3.1 改进框架

本文方法可以命名为：

`YOLOv11n-DWCA-P2`

含义：

- `D`：DyHeadDetect，多尺度动态检测头。
- `W`：Wise-IoU，改进边界框回归损失。
- `CA`：CoordAttention，位置信息编码的轻量注意力。
- `P2`：P2/4 高分辨率小目标检测分支。

但写作中要强调：

- `D + W` 是强基线。
- `P2` 是主要贡献。
- `CA` 是辅助增强，不要写成决定性创新。

### 3.2 DWCA-P2 模型结构证据

模型 YAML 归档位置：

- `/Users/asus/ultralytics/.claude/worktrees/dw-p2/ultralytics/cfg/models/11/yolo11-dwca-p2.yaml`
- `/Users/asus/ultralytics/.claude/worktrees/dw-p2/ultralytics/cfg/models/11/yolo11-dw-p2.yaml`

注意：主仓当前分支未直接包含 `yolo11-dwca-p2.yaml`，论文复现性整理时需要确认最终源码分支是否已完整归档。建议后续把最终方法 YAML、模块代码、训练脚本和 WIoU 设置脚本统一复制或合并到论文归档分支。

DWCA-P2 结构要点：

- 在 backbone P3 末端加入 `CoordAttention`。
- 在 head 中从 P3 继续上采样到 P2/4，与 backbone layer 2 拼接。
- 新增 P2/4 tiny 输出层。
- `DyHeadDetect` 接收四尺度输入：P2、P3、P4、P5。

可写成：

> 相比原 YOLOv11n 的 P3/P4/P5 三尺度检测结构，本文在 neck-head 部分新增 P2/4 高分辨率检测分支，并将检测头输入扩展为 P2、P3、P4、P5 四尺度特征。该设计旨在保留更多浅层空间细节，缓解路侧远距离小目标在深层特征图中被过度下采样的问题。

### 3.3 WIoU 写法

当前实验记录说明 WIoU 必须通过 Python 入口设置并打印：

`BboxLoss.iou_type = "wiou"`

论文中不要展开太多 WIoU 内部公式，除非目标期刊要求。建议写：

> 为改善边界框回归阶段对不同质量样本的关注方式，本文将 YOLOv11n 默认 CIoU 损失替换为 Wise-IoU。训练时通过显式设置 `BboxLoss.iou_type="wiou"` 保证 WIoU 生效，并在所有 WIoU 相关实验中保持训练超参数一致。

---

## 4. 推荐论文结构

建议采用 IMRaD 结构，总字数 5000-7000 中文字。

### 摘要

需要包含四句话：

1. 研究背景：路侧感知中远距离小目标检测困难。
2. 方法：提出融合 P2 高分辨率分支、DyHead、WIoU 与 CoordAttention 的 YOLOv11n 改进模型。
3. 结果：在统一 batch=32 口径下，本文方法在 DAIR-V2X-I 上 mAP50 达到 88.4%，mAP50-95 达到 64.4%，较 baseline-b32 提升 2.4 和 4.2 个百分点。
4. 结论：P2 分支是主要增益来源，适合小目标密集路侧场景。

### 1 引言

写作任务：

- 说明车路协同/路侧感知的重要性。
- 说明 DAIR-V2X-I 路侧视角下目标小、密集、尺度差异大。
- 用标签统计支撑问题：short side < 32 px 的目标占 87.55%。
- 指出 YOLOv11n 默认 P3/P4/P5 检测结构对极小目标不够友好。
- 引出本文贡献。

建议贡献点：

1. 针对路侧小目标密集特征，在 YOLOv11n 中引入 P2/4 高分辨率检测分支，增强极小目标特征保留。
2. 将 DyHead 与 WIoU 结合，提升多尺度特征动态建模和边界框定位质量。
3. 通过完整消融实验验证各模块贡献，发现 P2 分支是主要增益来源，同时说明 Triplet 注意力路线在本任务中收益有限。

### 2 相关工作

建议分三节：

1. 路侧目标检测与 DAIR-V2X 感知任务。
2. YOLO 系列轻量目标检测方法。
3. 小目标检测增强方法：高分辨率检测头、多尺度特征融合、动态检测头、注意力机制与 IoU 损失。

需要文献：

- YOLOv5/YOLOv8/YOLOv10/YOLOv11 或 Ultralytics 相关文献/官方说明。
- DyHead 原论文。
- Wise-IoU 原论文。
- Coordinate Attention 原论文。
- DAIR-V2X 数据集论文。
- 小目标检测/P2 检测头相关论文。

### 3 方法

建议结构：

3.1 Baseline YOLOv11n  
说明原模型结构与 P3/P4/P5 检测。

3.2 P2 高分辨率检测分支  
说明新增 P2/4 分支的结构、输入输出与小目标动机。

3.3 DyHead 动态检测头  
说明其 scale-aware、spatial-aware、task-aware 动态建模能力。

3.4 WIoU 边界框回归损失  
说明替换 CIoU 的目的与训练实现。

3.5 CoordAttention 辅助增强  
说明其位置编码与通道注意力特征，但注意措辞为辅助模块。

### 4 实验设置

必须写清：

- 数据集：DAIR-V2X-I，8 类，train 4940、val 1411、test 707。
- 输入尺寸：640。
- 训练轮数：300 epochs。
- 优化器：SGD。
- seed：42。
- batch：统一按 batch=32 书写和解释。
- nbs：64。
- cos_lr：true。
- patience：50。
- close_mosaic：10。
- 指标：Precision、Recall、mAP50、mAP50-95、Params、GFLOPs。

可引用训练配置：

- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/args.yaml`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/args.yaml`

### 5 实验结果与分析

建议按这个顺序写：

1. 主结果：baseline-b32 vs DWCA-P2-b32。
2. 消融实验：+D、+W、+DW、DWCA、DW-P2、DWCA-P2。
3. Triplet 探索实验：说明为什么放弃 Triplet 主线。
4. 同口径结构对比。
5. 官方预训练参考。
6. 可视化结果：PR 曲线、混淆矩阵、检测样例。

### 6 讨论

必须讨论：

- 为什么 P2 对该数据集有效：小目标占比高。
- 为什么 CA 增益有限：分解消融显示主要由 P2 驱动。
- 为什么 Triplet 不作为最终方案：可能与 DyHead 空间建模重叠。
- 方法代价：GFLOPs 增加明显。
- 适用场景：路侧设备、边缘服务器、精度优先的感知节点。
- 局限：缺少更多数据集验证、类别级 AP 仍需补充、FPS 口径不完整。

### 7 结论

建议结论：

> 本文针对 DAIR-V2X-I 路侧场景小目标密集的问题，对 YOLOv11n 进行改进，提出融合 P2 高分辨率检测分支、DyHead、WIoU 与 CoordAttention 的 DWCA-P2 模型。实验结果表明，在统一 batch=32 训练设置下，本文方法相比 YOLOv11n baseline-b32 的 mAP50 提升 2.4 个百分点，mAP50-95 提升 4.2 个百分点。进一步分解消融显示，P2 高分辨率检测分支是性能提升的主要来源，说明针对路侧小目标保留浅层空间细节具有重要意义。

---

## 5. 图表规划

### 5.1 必做表格

| 编号 | 表名 | 数据来源 | 目的 |
|---|---|---|---|
| 表 1 | DAIR-V2X-I 类别与小目标分布统计 | YOLO label 统计 | 支撑 P2 动机 |
| 表 2 | 主消融实验结果 | Excel | 证明模块贡献 |
| 表 3 | 统一训练口径主结果对比 | Excel | 主结论 |
| 表 4 | 同口径结构对比 | Excel | 公平比较 |
| 表 5 | 官方预训练参考实验 | Excel | 补充参考 |

### 5.2 必做图片

| 编号 | 图名 | 推荐来源 |
|---|---|---|
| 图 1 | DWCA-P2 网络结构示意图 | 基于 YAML 手绘，或使用已有 `docs/tdw_backbone_neck_head.svg` 修改 |
| 图 2 | 不同方法 mAP50/mAP50-95 柱状图 | Excel/CSV 生成 |
| 图 3 | baseline-b32 与 DWCA-P2-b32 训练曲线对比 | `results.csv` |
| 图 4 | PR 曲线对比 | `BoxPR_curve.png` |
| 图 5 | 混淆矩阵 | `confusion_matrix.png` |
| 图 6 | 检测结果可视化 | `val_batch*_pred.jpg` |

可直接使用的产物路径示例：

- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/results.csv`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/results.png`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/BoxPR_curve.png`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/confusion_matrix.png`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/val_batch0_pred.jpg`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/results.csv`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/BoxPR_curve.png`
- `/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/confusion_matrix.png`

---

## 6. 使用 ARS 完成小论文的全流程

项目地址：

`https://github.com/Imbad0202/academic-research-skills-codex`

Codex 版只有一个入口：

`$academic-research-suite`

内部会根据任务自动路由到：

- `experiment-agent`：实验计划、运行、验证、统计解释。
- `academic-paper`：论文规划、提纲、写作、摘要、修订、格式转换。
- `academic-paper-reviewer`：模拟审稿、方法审查、devil's advocate。
- `academic-pipeline`：端到端研究到论文流水线。
- `deep-research`：选题收束、文献综述、系统综述。

### Stage 0：建立论文材料包

目标：把所有材料放到一个清晰的上下文里。

建议准备：

- 实验结果 Excel。
- 训练产物路径。
- 关键 YAML。
- 数据集统计。
- 已有结论。
- 待确认问题。

提示词：

```text
Use $academic-research-suite.

Goal: prepare materials for a Chinese IMRaD-style computer vision paper.
Current project: /Users/asus/ultralytics
Main result table: /Users/asus/ultralytics/刘华硕-实验记录表.xlsx
Training artifacts: /Users/asus/ultralytics/runs/detect/runs/ablation/
Dataset: DAIR-V2X-I, 8 classes.

Please help me build a Material Passport and identify which materials are ready,
which are unverified, and which are missing before drafting.
```

### Stage 1：实验验证报告

使用 workflow：

`experiment-agent validate`

目标：

- 验证主结果是否能支撑论文。
- 区分主结论、辅助结论、不能写成强结论的部分。
- 生成可交给论文写作阶段的 Validation Report。

提示词：

```text
Use $academic-research-suite.
Workflow: experiment-agent validate.

请基于以下材料生成实验验证报告：
- /Users/asus/ultralytics/刘华硕-实验记录表.xlsx
- /Users/asus/ultralytics/HANDOFF.md
- /Users/asus/ultralytics/runs/detect/runs/ablation/

请重点验证：
1. baseline-b32 与 DWCA-P2-b32 在统一 batch=32 口径下是否可作为主结论；
2. DWCA-P2、DW-P2、DWCA 的分解消融如何解释 P2 与 CA 的贡献；
3. Triplet 系列实验是否应作为失败探索/路线收束证据；
4. 哪些对比实验属于公平同口径对比，哪些只能作为预训练参考；
5. 是否存在不能直接写进论文的风险结论。

口径约束：所有列出的实验均按 batch=32 完成和解释，不再区分 AutoBatch 与固定 batch 复验。

输出要求：
- Markdown；
- 包含 Material Passport；
- 给出 Overall Confidence；
- 给出可以写进论文的结论和必须谨慎措辞的结论。
```

### Stage 2：论文规划

使用 alias：

`ars-plan`

目标：

- 锁定研究问题。
- 生成 IMRaD 大纲。
- 明确每节要写什么证据。
- 做论证压力测试。

提示词：

```text
Use $academic-research-suite: ars-plan

我需要写一篇中文计算机视觉小论文。

主题：面向 DAIR-V2X-I 路侧小目标检测的改进 YOLOv11n。
核心方法：P2 高分辨率检测头 + DyHead + WIoU + CoordAttention。
核心结果：在统一 batch=32 口径下，DWCA-P2-b32 相比 baseline-b32，mAP50 从 86.0 提升到 88.4，mAP50-95 从 60.2 提升到 64.4。
关键限制：分解消融显示主要增益来自 P2，CA 贡献有限；Triplet 系列没有超过 +DW。
实验口径：所有实验均视为 batch=32 完成。

请输出：
1. 研究问题；
2. 中心论点；
3. 贡献点；
4. IMRaD 论文大纲；
5. 每节证据来源；
6. 图表计划；
7. 审稿风险和补救策略。
```

### Stage 3：文献与相关工作补齐

如果你还没有文献矩阵，使用：

`deep-research` 或 `ars-lit-review`

提示词：

```text
Use $academic-research-suite: ars-lit-review

请为这篇小论文生成相关工作文献框架。
主题：YOLOv11n 路侧小目标检测，P2 高分辨率检测头，DyHead，Wise-IoU，CoordAttention，DAIR-V2X-I。

请输出：
1. 必读文献类别；
2. 每类应引用的代表性论文；
3. 相关工作三段式结构；
4. 哪些文献支撑方法，哪些文献支撑数据集和实验设置；
5. IEEE 或 GB/T 可转换的引用信息。
```

注意：文献需要联网核验，不能让模型凭记忆给虚假 DOI。后续写正文前，应做一次 citation-check。

### Stage 4：分节写作

不建议一口气写全文。建议按顺序写：

1. 方法。
2. 实验设置。
3. 实验结果。
4. 引言。
5. 相关工作。
6. 摘要和结论。

方法与实验优先，因为它们最依赖已有真实数据。

提示词：

```text
Use $academic-research-suite.
Workflow: academic-paper full.

请先起草这篇中文小论文的“方法”和“实验设置”两节。

要求：
1. 方法以 YOLOv11n-DWCA-P2 为主；
2. 明确 P2 高分辨率检测头是关键改进；
3. DyHead 与 WIoU 作为有效基础模块；
4. CoordAttention 写成辅助增强，不夸大；
5. 训练设置必须引用 args.yaml 中的实际配置；
6. 不要虚构类别级 AP、FPS 或外部数据集结果。
```

实验结果写作提示词：

```text
Use $academic-research-suite.
Workflow: academic-paper full.

请基于以下实验结果起草“实验结果与分析”一节：
- 主结果：baseline-b32 vs DWCA-P2-b32；
- 分解消融：+DW、DWCA、DW-P2、DWCA-P2；
- Triplet 探索：+T、TDW、TDW-CO、TDW-CO-P3、TDW-CO-D3；
- 同口径结构对比；
- 官方预训练参考。

统一口径：上述所有实验均按 batch=32 完成和解释。

请特别注意：
1. 不要把预训练 .pt 结果和 YAML/scratch 结果混成公平对比；
2. 明确 P2 是主要增益来源；
3. 承认计算量增加；
4. 对 CA 和 Triplet 使用谨慎措辞。
```

### Stage 5：图表生成

可使用 ARS 的 `visualization_agent` 思路，也可以直接让我基于 Excel 和 results.csv 生成图。

提示词：

```text
Use $academic-research-suite.

请基于以下文件规划并生成论文图表代码：
- /Users/asus/ultralytics/刘华硕-实验记录表.xlsx
- /Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/results.csv
- /Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/results.csv

需要：
1. mAP50 和 mAP50-95 对比柱状图；
2. baseline-b32 vs DWCA-P2-b32 训练曲线；
3. 消融实验性能-计算量散点图；
4. 图注和正文引用句。
```

### Stage 6：审稿式自检

使用：

`ars-reviewer`

提示词：

```text
Use $academic-research-suite: ars-reviewer

请以计算机视觉小论文审稿人的角度审查这篇稿件。

重点审查：
1. 创新性是否足以支撑小论文；
2. P2、CA、DyHead、WIoU 的贡献是否被过度声称；
3. 消融实验是否支持主结论；
4. 预训练对比和同口径对比是否混淆；
5. 是否需要补充类别级 AP、FPS、小目标统计或更多可视化；
6. 方法复现性是否充分。

输出：
- 5 个角度的审稿意见；
- 总体决定；
- 必改问题；
- 可选增强问题；
- 修订路线图。
```

### Stage 7：修订

使用：

`ars-revision`

提示词：

```text
Use $academic-research-suite: ars-revision

请根据审稿意见修订论文。

修订原则：
1. 保留真实实验边界；
2. 不夸大 CA 和 Triplet；
3. 强化 P2 小目标分支的动机；
4. 明确计算量增加的局限；
5. 将预训练参考与公平对比分开；
6. 增加复现性说明。
```

### Stage 8：引用检查与格式整理

使用：

`ars-citation-check` 与 `ars-format-convert`

提示词：

```text
Use $academic-research-suite: ars-citation-check

请检查论文中的引用：
1. 是否存在虚假引用；
2. 是否每个方法都有对应来源；
3. 是否缺少 DAIR-V2X、DyHead、WIoU、CoordAttention、YOLO 系列相关引用；
4. 是否正文引用和参考文献列表一致。
```

格式转换：

```text
Use $academic-research-suite: ars-format-convert

请将最终 Markdown 论文整理成目标格式。
暂定：
- 中文正文；
- IEEE 或学校模板；
- 保留图表编号；
- 输出 DOCX/LaTeX/PDF 所需结构。
```

---

## 7. 审稿风险与应对

### 风险 1：创新性被认为是模块堆叠

应对：

- 不把贡献写成“同时用了四个模块”。
- 写成“由失败探索收束到小目标结构增强”。
- 强调标签统计与 P2 分支之间的因果动机。

推荐句：

> 本文并非简单叠加注意力模块，而是通过前期 Triplet 与 DyHead 组合消融发现注意力堆叠收益有限，进而转向与路侧小目标尺度分布更匹配的高分辨率 P2 检测分支。

### 风险 2：CA 贡献不足

应对：

- 主动承认。
- 把 CA 写成辅助模块。
- 将主贡献给 P2。

推荐句：

> 分解消融显示 CA 单独贡献有限，因此本文不将其作为主要性能来源，而将其定位为位置编码辅助增强模块。

### 风险 3：计算量增加明显

应对：

- 给出 Params/GFLOPs。
- 明确场景适配：路侧设备/边缘服务器。
- 若能补 FPS，优先补固定硬件下 FPS。

推荐句：

> 尽管 P2 分支显著提高了小目标检测性能，但也带来了计算量增加。考虑到路侧感知节点通常具备相对稳定的边缘计算条件，本文方法更适用于精度优先的路侧协同感知部署。

### 风险 4：缺少类别级 AP

应对：

- 最好补充 `val` 的 per-class AP。
- 如果来不及补，至少用标签统计和混淆矩阵做辅助说明。

建议后续任务：

```text
请基于 best.pt 对 DAIR-V2X-I val 集重新验证，导出 per-class Precision、Recall、AP50、AP50-95。
```

### 风险 5：复现性不足

应对：

- 整理最终源码分支。
- 把 `yolo11-dwca-p2.yaml` 放回主项目可追踪路径。
- 明确 WIoU 设置入口。
- 记录 commit、args.yaml、训练日志、best.pt 存放方式。

---

## 8. 需要优先补齐的材料

### P0：强烈建议补

1. 类别级 AP 表：尤其 Pedestrian、Cyclist、Motorcyclist、Trafficcone。
2. baseline-b32 与 DWCA-P2-b32 的同一硬件 FPS 测试。
3. 最终方法源码归档：`yolo11-dwca-p2.yaml`、`CoordAttention`、`DyHeadDetect`、WIoU 设置脚本。
4. 主方法结构图。

### P1：有时间再补

1. 更多可视化样例：小目标漏检/误检对比。
2. 不同 IoU 阈值或不同尺度目标的 AP 分析。
3. test 集最终结果。
4. 与 RT-DETR、YOLOv9 等更多模型比较。

### P2：论文增强项

1. 消融结果显著性/多次训练均值方差。
2. 不同输入尺寸 640/768 对比。
3. 模型部署推理延迟、显存占用。

---

## 9. 下一轮和我交互时建议确认的问题

请优先确认这些问题，我可以据此直接进入“论文规划/初稿写作”：

1. 小论文目标是中文期刊、会议、学报、课程论文，还是硕士论文中的一章？
2. 目标字数大约是多少：3000、5000、7000 还是 8000+？
3. 参考文献格式用 IEEE、GB/T 7714，还是学校模板？
4. 是否要把最终方法命名为 `DWCA-P2`，还是更强调 `DW-P2`？
5. 是否允许我继续补做类别级 AP、FPS 和图表生成？
6. 最终正文语言是中文，摘要是否需要中英双语？
7. 你希望我先写“完整论文初稿”，还是先写“详细大纲 + 方法/实验两节”？

我的建议默认值：

- 论文类型：中文 IMRaD 小论文。
- 字数：6000 中文字左右。
- 引用格式：IEEE 或 GB/T 7714，按你的学校/期刊要求调整。
- 主方法名：`YOLOv11n-DWCA-P2`，但结论强调 P2 是主要增益来源。
- 下一步：先生成 `实验验证报告 + 详细论文大纲`，再写方法和实验两节。

---

## 10. 最短可执行路线

如果想最快进入成稿，可以按下面 5 步：

1. 用 `experiment-agent validate` 生成实验验证报告。
2. 用 `ars-plan` 生成论文大纲和图表计划。
3. 让我补类别级 AP/FPS/图表，如果你同意。
4. 用 `academic-paper full` 先写方法和实验结果。
5. 用 `ars-reviewer` 审稿，再用 `ars-revision` 修订。

建议当前马上执行的提示词：

```text
Use $academic-research-suite.
请基于 docs/small-paper-writing-route-ars.md、刘华硕-实验记录表.xlsx 和 runs/detect/runs/ablation/，先生成这篇小论文的实验验证报告与详细论文大纲。默认中文 IMRaD、6000 字、IEEE/GB/T 可转换引用格式。
```
