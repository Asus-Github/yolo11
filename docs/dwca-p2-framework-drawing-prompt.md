# DWCA-P2-YOLO11 框架图绘制提示词

本文档用于指导画图大模型绘制 **DWCA-P2-YOLO11** 论文框架图。核心目标是让结构图清晰表达改进点，同时避免箭头交叉、箭头闭环、结构误连等问题。

## 可直接复制的完整提示词

请绘制一张用于硕士论文的高质量 YOLO11 改进框架图，模型名称为 **DWCA-P2-YOLO11**。请严格按照下面的结构和布局绘制，不要添加不存在的模块，不要画闭环箭头，不要让箭头交叉。

整体风格要求：

- 使用清晰的学术论文风格框架图，白色背景，模块为圆角矩形，线条简洁。
- 图从左到右表示数据流方向，所有主箭头必须从左向右，不允许出现反向箭头或闭环箭头。
- 按特征尺度分成 4 条水平泳道，从上到下分别是：
  - P2/4，160×160，小目标特征
  - P3/8，80×80，小尺度特征
  - P4/16，40×40，中尺度特征
  - P5/32，20×20，大尺度特征
- 不要画复杂的真实卷积细节，只画主要模块和特征融合关系。
- Concat 节点用小圆点或小矩形表示，标注 “Concat”。
- Upsample 箭头用向上连接，但仍保持从左到右推进。
- Downsample 箭头用向下连接，但仍保持从左到右推进。
- 所有跳连箭头使用浅灰色，主干箭头使用深色，检测输出箭头使用蓝色。
- 不要让跳连箭头穿过模块内部；如果需要连接不同尺度，请使用直角折线，并绕开模块。

请按以下结构绘制。

### 第一部分：Backbone

Backbone 放在图的左侧，按照从左到右、从上到下尺度递减的方式排列：

1. 输入图像 `Input 640×640`
2. `Conv` 得到 P1/2
3. `Conv + C3k2` 得到 `P2 feature, 160×160`
4. `Conv + C3k2` 得到 `P3 feature, 80×80`
5. 在 P3 feature 后面加入一个醒目的注意力模块：`CoordAttention`
6. `Conv + C3k2` 得到 `P4 feature, 40×40`
7. `Conv + C3k2 + SPPF + C2PSA` 得到 `P5 feature, 20×20`

请特别标注：`CoordAttention is inserted after P3 feature extraction`。

### 第二部分：Neck

Neck 放在图的中间，画成 FPN + PAN 结构。

Top-down FPN 路径：

1. 从 `P5 feature` 开始，经过 `Upsample ×2`
2. 与 `P4 feature` 进行 `Concat`
3. 经过 `C3k2` 得到 `FPN-P4`
4. `FPN-P4` 经过 `Upsample ×2`
5. 与 `P3 + CoordAttention` 进行 `Concat`
6. 经过 `C3k2` 得到 `FPN-P3`
7. `FPN-P3` 经过 `Upsample ×2`
8. 与 `P2 feature` 进行 `Concat`
9. 经过 `C3k2` 得到新增的 `P2 head, 160×160`

请用醒目颜色突出 `P2 head`，并标注：`New P2 small-object detection branch`。

Bottom-up PAN 路径：

1. `P2 head` 经过 `Downsample Conv, stride=2`
2. 与 `FPN-P3` 进行 `Concat`
3. 经过 `C3k2` 得到 `Refined P3 head, 80×80`
4. `Refined P3 head` 经过 `Downsample Conv, stride=2`
5. 与 `FPN-P4` 进行 `Concat`
6. 经过 `C3k2` 得到 `Refined P4 head, 40×40`
7. `Refined P4 head` 经过 `Downsample Conv, stride=2`
8. 与 `P5 feature` 进行 `Concat`
9. 经过 `C3k2` 得到 `Refined P5 head, 20×20`

### 第三部分：Detection Head

Detection Head 放在图的右侧。

将以下 4 个输出并行连接到同一个检测头：

- `P2 head, 160×160`
- `Refined P3 head, 80×80`
- `Refined P4 head, 40×40`
- `Refined P5 head, 20×20`

检测头模块名称为：

`DyHeadDetect`

请在检测头旁边标注：

`4-scale detection: P2, P3, P4, P5`

然后输出到：

`Prediction`

### 第四部分：Loss

Loss 放在 Prediction 右侧或右下角。

请单独画一个训练阶段的损失函数模块：

`WIoU v3 Loss`

连接方式为：

`Prediction + Ground Truth → WIoU v3 Loss`

注意：`WIoU v3 Loss` 是训练损失，不是网络结构中的特征提取模块，不要把它画在 Backbone 或 Neck 中。

### 需要突出的改进点

图中需要突出以下 4 个改进点：

1. `CoordAttention at P3`
2. `New P2/4 small-object detection branch`
3. `DyHeadDetect with four input scales`
4. `WIoU v3 Loss for bounding box regression`

请在图右上角添加一个简短标题：

`DWCA-P2-YOLO11 Framework`

### 禁止绘制内容

请不要绘制以下内容：

- 不要绘制循环箭头
- 不要绘制反向箭头
- 不要让任意箭头交叉
- 不要把 WIoU 画成 Backbone/Neck 中的网络层
- 不要把检测头画成三个尺度，必须是四个尺度 P2/P3/P4/P5
- 不要添加 Triplet Attention，因为本模型已经去掉 Triplet Attention

最终图应当是清晰的论文框架图，适合放入目标检测小论文中。

## 更稳的补充约束

如果画图模型仍然出现箭头交叉、闭环或结构混乱，可以在完整提示词后追加以下内容：

请优先保证结构清晰，而不是追求视觉复杂度。所有模块必须按照固定网格排列：Backbone 在左侧，Neck 在中间，DyHeadDetect 在右侧，Loss 在最右下角。不同尺度的特征图必须位于不同水平行，箭头只能连接相邻阶段，禁止跨越多个模块直接连线，除非是明确的 skip connection。所有 skip connection 必须使用浅灰色直角折线并贴着图的外侧走线。

## 极简结构骨架

如果画图模型支持“先给结构草图再渲染”，可以先给它下面的骨架：

```text
Input
  ↓
Backbone:
P2 source ───────────────────────────────┐
P3 source → CoordAttention ───────────┐  │
P4 source ────────────────────────┐   │  │
P5 source ── Upsample ─ Concat(P4) ─ C3k2 ─ Upsample ─ Concat(P3+CA) ─ C3k2 ─ Upsample ─ Concat(P2) ─ C3k2 → P2 head
                                                                                                      ↓
PAN:
P2 head ─ Downsample ─ Concat(FPN-P3) ─ C3k2 → P3 head
P3 head ─ Downsample ─ Concat(FPN-P4) ─ C3k2 → P4 head
P4 head ─ Downsample ─ Concat(P5)     ─ C3k2 → P5 head

Detect:
[P2 head, P3 head, P4 head, P5 head] → DyHeadDetect → Prediction
Prediction + Ground Truth → WIoU v3 Loss
```

正式绘图时建议优先使用完整提示词，极简骨架只作为结构约束辅助。