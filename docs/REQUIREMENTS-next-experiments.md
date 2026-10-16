# 下一阶段实验需求文档

> 作者：刘华硕 / Date：2026-06-05
> 范围：在 YOLOv11n + DAIR-V2X-I（路侧 8 类）任务下，针对当前 TDW 主线偏弱的问题，规划三类增量实验。
> 当前最强：`+DW`（mAP50=87.0，mAP50-95=61.3，6.4→9.3 GFLOPs，2.6→4.35 M）。
> 当前 TDW 系：TDW 86.5 / TDW-CO 86.7，均未越过 +DW。

---

## 关键事实校准

- 现有 `DyHeadDetect.num_blocks = 2`（`ultralytics/nn/modules/head.py:1884`），**当前所有 +D/+TD/TDW/TDW-CO 已经在用 2 块级联**。所以本文档中"增加 DyHead block 数"= 2→3 或 2→4，并非 1→2。
- Triplet 当前位置：Backbone **P5 末端**（`yolo11-tdw-co.yaml:30`），位于 `C3k2(P5)` 之后、`SPPF` 之前。
- Triplet 形式：当前 TDW-CO 用 `no_spatial=True`（channel-only）。

---

## 需求 1：更改 Triplet 插入位置

### 1.1 合理性分析

当前 P5 末端方案的问题：
- **空间冗余**：原 TDW（含 H-W 空间分支）与 DyHead 的 spatial-aware module 都在最深、感受野最大的层做空间注意力，机制重叠（这一点 TDW-CO 已经部分回应）。
- **感受野错配**：P5/32 分辨率最低（如 640 输入下 20×20），路侧远距离小目标（行人/骑行者）在 P5 上几乎已被下采样消失，Triplet 在此层学到的跨维交互对小目标贡献小。
- **位置上的"晚到"**：P5 末端紧邻 SPPF + C2PSA，C2PSA 本身就是 PSA 注意力，再叠 Triplet 边际收益低。

候选位置（按推荐度排序）：

| 候选 | 位置 | 推理 | 风险 |
|---|---|---|---|
| **A. P3 source** | backbone 第 4 层之后（`C3k2 P3` 后） | DAIR-V2X-I 远距离小目标主要在 P3/8 层。Triplet 的跨维通道交互直接作用于小目标特征的高分辨率层，最有可能涨 Recall。DyHead 在 head 端处理空间，互不干扰。 | P3 通道少（128n=32），跨维操作 FLOPs 占比上升不多，但 P3 分辨率高（80×80），整体 GFLOPs 会涨。 |
| **B. P4 source** | backbone 第 6 层之后（`C3k2 P4` 后） | 中尺度目标（车辆主体）所在层，P4/16 是 mAP50 的主战场。性价比折中。 | 与 DyHead 在 P4 输出的 spatial 处理仍有一点距离，但比 P5 远。 |
| **C. Neck P3 输出后** | head 第 17 层之后（P3/8-small 输出后、进 DyHead 前） | 在 PAN 融合后注入跨维交互，让 Triplet 直接为 DyHead 提供"已增强"的小目标特征。 | 改动 head 索引，需要小心 Concat / Detect 引用的层号。 |
| D. P3+P4 双插 | A+B 同时 | 多尺度通道增强 | 参数 / FLOPs 双倍，可能过拟合 |

**推荐先做 A（P3 source 后）**。理由：
1. 直击 DAIR-V2X-I 小目标痛点。
2. DyHead 在 head 端处理空间，与 Backbone P3 端的通道注意力机制上正交。
3. 单点改动，与 TDW-CO 形成清晰对照（仅位置不同，Triplet 形式同为 channel-only）。

### 1.2 操作方案

**新建 YAML**：`ultralytics/cfg/models/11/yolo11-tdw-co-p3.yaml`

修改要点：
- 将 `TripletAttention[True]` 从 P5 末端（layer 9）移到 P3 source 之后（即 `C3k2 P3` 之后、`Conv P4/16` 之前）。
- 所有后续层索引 +1，Concat 和 Detect 引用同步更新。

具体改动（基于 `yolo11-tdw-co.yaml`）：

```yaml
backbone:
  - [-1, 1, Conv, [64, 3, 2]]              # 0  P1/2
  - [-1, 1, Conv, [128, 3, 2]]             # 1  P2/4
  - [-1, 2, C3k2, [256, False, 0.25]]      # 2
  - [-1, 1, Conv, [256, 3, 2]]             # 3  P3/8
  - [-1, 2, C3k2, [512, False, 0.25]]      # 4
  - [-1, 1, TripletAttention, [True]]      # 5  ★ Triplet at P3 end (channel-only)
  - [-1, 1, Conv, [512, 3, 2]]             # 6  P4/16
  - [-1, 2, C3k2, [512, True]]             # 7  (P4 source)
  - [-1, 1, Conv, [1024, 3, 2]]            # 8  P5/32
  - [-1, 2, C3k2, [1024, True]]            # 9
  - [-1, 1, SPPF, [1024, 5]]               # 10
  - [-1, 2, C2PSA, [1024]]                 # 11 (P5 source)
# head: P3 source 引用从 4 改为 5；其他层号不变
# 第二次 Upsample 后 Concat 引用 [-1, 5]（原为 [-1, 4]）
```

**消融对照**：
- 实验 10：`TDW-CO-P3`（Triplet 移至 P3 source 后，channel-only，DyHead，WIoU）
- 可选实验 10b：`TDW-CO-P4`（移至 P4 source 后）做位置消融

**风险与回退**：
- P3 层加注意力会让 GFLOPs 涨（粗估 9.3→9.6 左右），需在 batch=1 复测 FPS。
- 若 mAP 不涨反降，回退到 TDW-CO 原方案，记录"位置消融为负"。

---

## 需求 2：增加 DyHead block 数

### 2.1 合理性分析

**事实**：当前 `num_blocks=2`，所以"增加"= 2→3 或 2→4。

合理性：
- DyHead 原论文（CVPR 2021）建议 6 块级联，YOLO 改进类工作普遍降到 1–2 块以平衡 FPS。当前 2 块是常见折中。
- DyHead 是当前唯一被验证有效的模块（+D 单独贡献 mAP50 +0.7），加深它在理论上有继续提升空间。
- 但 DyHead 同时含 scale / spatial / task 三种注意力，块数增加会显著拉低 FPS（+D 已经是 435→109 FPS 的下降主因）。

**预期收益与代价**：
- 2→3：mAP 预计 +0.1~0.3，FPS 下降约 25~35%，Params 增长约 0.3M。
- 2→4：mAP 收益边际递减（+0.1 量级或停滞），FPS 下降约 50%。
- 路侧检测对 FPS 不敏感（路侧设备通常算力充裕、帧率要求 ≥25 即可），所以 3 块在工程上仍可接受。

**结论**：值得做，**优先 2→3**，2→4 仅在 3 块明显涨点时再补。

### 2.2 操作方案

**最简方案**（不动 YAML）：覆盖类属性。

新建一个轻量 wrapper 或在训练脚本中：

```python
from ultralytics.nn.modules.head import DyHeadDetect
DyHeadDetect.num_blocks = 3   # 训练前设置
```

**推荐方案**（更可控、可复现）：在 YAML 层面通过新增 module 变体实现。

由于 `num_blocks` 是 class attribute，建议在 `head.py` 增加 `DyHeadDetect3` / `DyHeadDetect4` 子类：

```python
class DyHeadDetect3(DyHeadDetect):
    num_blocks = 3

class DyHeadDetect4(DyHeadDetect):
    num_blocks = 4
```

并在 `nn/modules/__init__.py`、`nn/tasks.py` 的 `parse_model` 头检测分支同步注册。

**新建 YAML**：`yolo11-tdw-co-d3.yaml`（在最优 Triplet 位置基础上，把 `DyHeadDetect` 换成 `DyHeadDetect3`）。

**消融对照**：
- 实验 11：`TDW-CO-D3`（DyHead 块数 3，其他与当前最优相同）
- 实验 11b（条件触发）：`TDW-CO-D4`，仅在 D3 涨点 ≥ 0.2 mAP50 时再做

**注意**：
- 训练完务必 `model.fuse()` 后再测 FPS，DyHead 不可融合的部分会直接体现真实推理代价。
- 若 D3 与 +DW 仍打平，说明 DyHead 已饱和，该方向终止。

---

## 需求 3：四模块方案

### 3.1 合理性分析

四模块组合：**DyHead + WIoU + CA(Coordinate Attention) + P2 小目标层**

设计动机：
- **去掉 Triplet**：TDW / TDW-CO 已实证 Triplet 在本任务上**无正收益**，不应继续保留。
- **CA 替代 Triplet**：CA（Hou et al., CVPR 2021）将位置信息编码进通道注意力，机制上是"通道+位置"，**不做空间注意力**，与 DyHead 的 spatial-aware module 完全正交，避免 TDW 的冗余冲突。CA 参数量极小（约几 K），FPS 友好。
- **P2 小目标头**：DAIR-V2X-I 路侧远距离行人/骑行小目标多，P3/8（80×80）对极小目标仍嫌粗。新增 P2/4（160×160）检测层是检测小目标公认的有效手段，与 DyHead 的多尺度 scale-aware 互补。
- **WIoU**：保留 v3 focal-style bbox loss，已与 DyHead 形成验证有效的搭配（+DW 是当前最强）。

理论上限估计：
- baseline +DW 的 mAP50=87.0 → 加 CA 预计 +0.2~0.4 → 加 P2 预计再 +0.3~0.6（小目标 Recall 主导）。
- **合计目标 mAP50 ≥ 87.5，最好 ≥ 88.0**，否则相对 +DW 收益不足以支撑论文新颖性。

代价估计：
- P2 层使 GFLOPs 显著上升（9.3 → 约 12~14），Params +0.3~0.5M。
- FPS 下降约 30~40%。
- 训练时间也会增加（更多 anchors / loss term）。

**风险点**：
1. P2 层若数据集真实小目标比例不够高，会反而增加 FP。需先统计 DAIR-V2X-I 中 bbox 短边 < 16px 的占比。
2. CA 与 DyHead 同时引入"位置编码"，需关注是否再次出现 TDW 式重叠（CA 的位置编码是 1D 的水平/垂直池化，与 DyHead 的 2D spatial 卷积不同维度，理论冲突小）。

### 3.2 操作方案

**Step 1：CA 模块实现**
- 新文件：`ultralytics/nn/modules/attention.py` 中新增 `CoordAttention` 类（若未实现）。
- 在 `__init__.py` 与 `parse_model` 注册。
- 插入位置：与最优 Triplet 位置一致（建议 P3 source 后，与需求 1 复用结论）。

**Step 2：新建 YAML — `yolo11-dwca-p2.yaml`**
- backbone：在 P3 source 后插入 `CoordAttention`。
- head：新增 P2 检测分支：
  - 在现有 P3 上采样后再 Upsample 到 P2/4，与 backbone 第 2 层（P2 source `C3k2 [256]`）Concat。
  - 新增一个 P2/4-tiny 输出 head。
  - DyHeadDetect 改为 4 输入：`[P2, P3, P4, P5]`。
- 损失：保留 WIoU v3。

**Step 3：训练配置**
- imgsz=640 起跑；若小目标 Recall 不达预期，第二轮跑 imgsz=768。
- epochs=300，与 TDW 系一致，确保可比。
- 关闭 mosaic 最后 10 epochs（小目标更适合）。

**Step 4：实验编号**
- 实验 12：`DWCA-P2`（DyHead + WIoU + CA + P2，最终四模块方案）
- 实验 12b（消融）：`DW-P2`（去掉 CA 看 P2 单独贡献）
- 实验 12c（消融）：`DWCA`（去掉 P2 看 CA 单独贡献）

**Step 5：论文叙事**
- 主线："面向路侧小目标的 YOLOv11n 改进：DyHead + WIoU 双模块基线 + CA 跨维通道注意力 + P2 高分辨率检测头"。
- 卖点：场景驱动（车路协同/路侧视角）、小目标痛点明确、四模块各自机制正交无冗余。
- 与 TDW 系列的关系：TDW / TDW-CO 作为前期探索写入消融，**论证"Triplet 空间分支与 DyHead 冲突"是改用 CA 的依据**，让方法演进有故事性，而非单纯堆模块。

---

## 实验执行优先级与建议顺序

| 优先级 | 实验 | 预期工时 | 是否阻塞下一步 |
|---|---|---|---|
| P0 | 实验 10：TDW-CO-P3（Triplet 移到 P3） | 1 轮 300 ep | 是。结果决定 CA 是否也放 P3 |
| P0 | 实验 11：TDW-CO-D3（DyHead 2→3） | 1 轮 300 ep | 否，可与 P0 并行 |
| P1 | 实验 12：DWCA-P2（四模块方案） | 1 轮 300 ep + 可能 imgsz=768 复跑 | 是，作为最终方案 |
| P2 | 实验 10b/11b/12b/12c | 视 P0/P1 结果决定 | 仅在主实验收益显著时做 |

**建议**：P0 两组实验先并行启动（AutoDL 单卡可串行，两块卡可并行），结果出来后用最优 Triplet 位置再启动 P1 四模块。

---

## 通过/终止判据

- 需求 1（位置）：mAP50 ≥ 86.9（即 ≥ TDW-CO + 0.2）才视为有效，否则保留 TDW-CO 作为最佳 Triplet 方案。
- 需求 2（D3）：mAP50 ≥ 87.2（即 ≥ +DW + 0.2）才继续做 D4，否则停止 DyHead 加深方向。
- 需求 3（四模块）：mAP50 ≥ 87.5 且 mAP50-95 ≥ 61.5 才视为成功，可作为论文主方法；否则回退至 +DW 主线 + 数据/训练侧增强。

---

## 涉及文件改动清单

新增：
- `ultralytics/cfg/models/11/yolo11-tdw-co-p3.yaml`
- `ultralytics/cfg/models/11/yolo11-tdw-co-d3.yaml`
- `ultralytics/cfg/models/11/yolo11-dwca-p2.yaml`
- （视情况）`ultralytics/nn/modules/attention.py` 中 `CoordAttention`

修改：
- `ultralytics/nn/modules/head.py`：新增 `DyHeadDetect3`（可选 `DyHeadDetect4`）
- `ultralytics/nn/modules/__init__.py`：导出新模块
- `ultralytics/nn/tasks.py`：`parse_model` Detect 分支注册新 head 类（与现有 DyHeadDetect 同分支）

不动：
- 训练数据集、损失实现、其他已稳定模块。
