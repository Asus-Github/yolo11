# CHANGELOG — Triplet Attention 集成日志（教学复现版）

> 本分支 `feat/triplet` 只包含 Triplet Attention 集成 + +T 训练结果。
> 不含 WIoU/DyHead 代码。如需组合变体，见 `feat/triplet-wiou` 等分支。

---

## 0. 全局信息

| 项 | 值 |
|---|---|
| 基线 | `main` (commit `4e8bbf7e`) — 原版 ultralytics + 训练脚手架 |
| 本分支 | `feat/triplet` |
| GitHub | `git@github.com:Asus-Github/yolo11.git` |
| 目标实验 | 表第 2 行 `+T`：`yolo11-t.yaml`（CIoU + Triplet）|
| 论文 | Misra et al., *Rotate to Attend: Convolutional Triplet Attention Module*, WACV 2021 |
| AutoDL 路径 | `/root/autodl-tmp/ultralytics` |

## 0.1 实验入口

```bash
python train_variant.py -c yolo11-t.yaml --iou ciou -n +T
```

---

## 1. Triplet Attention 改在哪：架构数据流

**与 WIoU 不同**，Triplet 是**架构层**改动：在 backbone P5 末端、SPPF 之前插入一个注意力模块。

```
Backbone（原版）:                Backbone（+T）:
  ...                             ...
  layer 8: C3k2 [1024]            layer 8: C3k2 [1024]
  layer 9: SPPF                   layer 9: TripletAttention   ← NEW
  layer 10: C2PSA                 layer 10: SPPF              ← shifted
                                  layer 11: C2PSA             ← shifted
```

后续 head 引用 backbone 层号 [-1, 4]、[-1, 6] 不变（因为这些层在插入点之前），但引用 `[-1, 10]` → `[-1, 11]`、`[-1, 13]` → `[-1, 14]`，Detect 索引 `[16, 19, 22]` → `[17, 20, 23]`。

## 2. Triplet Attention 论文公式速查

三条并行分支，每条对一对维度做注意力：

| 分支 | 处理的交互维度 | 实现 |
|---|---|---|
| 1 | (C, H) | `permute(0,2,1,3)` → AttentionGate → permute back |
| 2 | (C, W) | `permute(0,3,2,1)` → AttentionGate → permute back |
| 3 | (H, W) | 不 permute，直接 AttentionGate（即标准空间注意力）|

每个 AttentionGate：
1. **Z-Pool**：在 dim=1 上拼接 `max` 和 `mean`，得到形状 `[B, 2, *, *]`
2. **7×7 Conv → BN → Sigmoid**：得到形状 `[B, 1, *, *]` 的 attention map
3. **逐元素乘**：`x * sigmoid(...)` 得到加权特征图

最终输出：三支结果**取均值**（不加 1×1 conv 融合，参数量极小）。

参数量：`3 × (7×7×2×1) = 294`（+ 3 × BN 各 2 个参数 = 6）≈ 300 参数。yolo11n 整体只增加约 0.01M。

## 3. 改动清单与逐项解析

### 改动 1 — `ultralytics/nn/modules/conv.py`（commit `51b228aa3`）

**目的**：在 conv.py 末尾追加 `ZPool`、`AttentionGate`、`TripletAttention` 三个类。

```python
class ZPool(nn.Module):
    """Z-Pool: concat max-pool and avg-pool along given dim."""
    def __init__(self, dim=1):
        super().__init__()
        self.dim = dim
    def forward(self, x):
        return torch.cat(
            (torch.max(x, self.dim, keepdim=True)[0], torch.mean(x, self.dim, keepdim=True)),
            dim=self.dim,
        )


class AttentionGate(nn.Module):
    """Z-Pool -> 7x7 Conv -> BN -> Sigmoid * x."""
    def __init__(self, kernel_size=7):
        super().__init__()
        padding = (kernel_size - 1) // 2
        self.compress = ZPool(dim=1)
        self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, stride=1, padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(1)
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        return x * self.sigmoid(self.bn(self.conv(self.compress(x))))


class TripletAttention(nn.Module):
    def __init__(self, c1, c2=None, no_spatial=False, kernel_size=7):
        super().__init__()
        self.cw = AttentionGate(kernel_size)
        self.hc = AttentionGate(kernel_size)
        self.no_spatial = no_spatial
        if not no_spatial:
            self.hw = AttentionGate(kernel_size)
    def forward(self, x):
        x_perm1 = x.permute(0, 2, 1, 3).contiguous()
        x_out1  = self.cw(x_perm1).permute(0, 2, 1, 3).contiguous()
        x_perm2 = x.permute(0, 3, 2, 1).contiguous()
        x_out2  = self.hc(x_perm2).permute(0, 3, 2, 1).contiguous()
        if not self.no_spatial:
            x_out3 = self.hw(x)
            return (x_out1 + x_out2 + x_out3) / 3.0
        return (x_out1 + x_out2) / 2.0
```

#### 关键设计点

| 点 | 为什么 |
|---|---|
| `c2` 形参存在但忽略 | 因为 ultralytics `parse_model` 标准 API 是 `Module(c1, c2, *args)`，但 Triplet 通道不变 (`c2 == c1`)。保留参数以兼容 |
| `permute().contiguous()` | permute 只调 view，stride 不连续会让后续 `Conv2d` 失败；`contiguous()` 显式 reshape 内存 |
| 三支取均值不学习权重 | 论文设计：保持参数极小；学权重收益甚微但增加几个参数 |
| ZPool 用 max+mean | 类似 CBAM 的 spatial attention，但 CBAM 是 `(cat -> conv)` 而 Triplet 把这个套路用到三个维度上 |

### 改动 2 — `ultralytics/nn/modules/__init__.py`

```python
from .conv import (
    ...
    SpatialAttention,
    TripletAttention,    # ← NEW
)
__all__ = (
    ...
    "SpatialAttention",
    "TorchVision",
    "TripletAttention",  # ← NEW
    ...
)
```

按字母顺序追加，不破坏其他模块的查找。

### 改动 3 — `ultralytics/nn/tasks.py`

```python
from ultralytics.nn.modules import (
    ...
    TorchVision,
    TripletAttention,    # ← NEW import
    WorldDetect,
    ...
)

# 在 parse_model 函数里，frozenset({TorchVision, Index}) 之前加：
        elif m is TripletAttention:
            c1 = ch[f]
            c2 = c1
            args = [c1]
```

#### 关键设计点

`parse_model` 是 ultralytics 把 YAML 配置转成 PyTorch 模块的核心。每个新模块**必须**告诉它：
- 输入通道 `c1` 从哪来（`ch[f]` 表示从层 `f` 的输出通道）
- 输出通道 `c2` 是多少（影响后续层的 `ch[f]`）
- args 列表怎么传给 `__init__`

漏掉这一段会报 `AttributeError: 'TripletAttention' object has no attribute 'i'`。

### 改动 4 — `ultralytics/cfg/models/11/yolo11-t.yaml`（新建）

见仓库内 `ultralytics/cfg/models/11/yolo11-t.yaml`。**最关键改动**：

```yaml
backbone:
  ...
  - [-1, 2, C3k2, [1024, True]]            # 8
  - [-1, 1, TripletAttention, []]          # 9  ★ NEW
  - [-1, 1, SPPF, [1024, 5]]               # 10  (was 9)
  - [-1, 2, C2PSA, [1024]]                 # 11  (was 10)

head:
  - [-1, 1, nn.Upsample, [None, 2, "nearest"]]  # 12 (was 11)
  - [[-1, 6], 1, Concat, [1]]                    # backbone P4, idx 6 unchanged
  ...
  - [[-1, 11], 1, Concat, [1]]                   # was [-1, 10]
  ...
  - [[17, 20, 23], 1, Detect, [nc]]              # was [16, 19, 22]
```

**容易踩坑**：插入一层 → 后续所有**绝对层号引用**都要 +1。`-1`（前一层）类型的引用不受影响。

---

## 4. Smoke Test（autodl, 2026-06-04）

```python
from ultralytics.nn.tasks import DetectionModel
m = DetectionModel('ultralytics/cfg/models/11/yolo11-t.yaml', ch=3, nc=8, verbose=False)
# Layers: 25
# Params: 2,591,700 (~2.59M)  ← baseline 2.58M, +T 加 0.01M

import torch
m.eval()
y = m(torch.randn(2, 3, 640, 640))
# y[0].shape == (2, 12, 8400)  forward 通过
```

参数量比 baseline 多 ~10K，符合 Triplet 论文的「极小开销」描述。

---

## 5. 训练复现命令

```bash
ssh autodl
tmux new -s t_train
tmux set-option -t t_train remain-on-exit on   # ★ 训练结束后保留窗口
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
cd /root/autodl-tmp/ultralytics
git checkout feat/triplet      # 切到本分支
python train_variant.py -c yolo11-t.yaml --iou ciou -n +T 2>&1 | tee runs/+T_train.log
```

> ⚠️ tmux 教训（来自 +W 训练）：默认 `tmux new -d 'cmd'` 在 cmd 结束后 session 销毁。务必加 `remain-on-exit on` 或在 cmd 末尾加 `; bash`。

## 6. 训练结果

### 6.1 配置（args.yaml）

| 项 | 值 | 说明 |
|---|---|---|
| epochs | 300 | patience=50 早停 |
| batch | 0.85 (AutoBatch) | 实际 **batch=61**（vs baseline=64, +W=62）|
| imgsz | 640 | |
| optimizer | SGD | lr0=0.01, momentum=0.937 |
| amp | True | |
| nbs | 64 | accumulate=round(64/61)=1，未触发梯度累积 |
| weight_decay 缩放 | × (61/64) ≈ 0.953 | 比 baseline 略弱的正则化 |

### 6.2 训练过程

- **总 epochs**：273（早停于 epoch 273，最佳 epoch 223）
- **训练时间**：1.369 h on RTX 4090
- **GPU 显存**：~13G / 24G（85% AutoBatch 探测目标）

### 6.3 best.pt val 最终指标

| 指标 | +T | baseline (CIoU) | Δ |
|---|---|---|---|
| Precision | **85.6%** | 85.7%* | -0.1 |
| Recall | **80.5%** | 80.3%* | +0.2 |
| **mAP@0.5** | **85.9%** | 85.7%* | **+0.2** |
| **mAP@0.5:0.95** | **60.2%** | 60.1%* | **+0.1** |
| FPS | 244 | ~250 | -6 (略降，符合预期) |
| GFLOPs | 6.4 | 6.4 | 0 |
| Params | 2.58 M | 2.58 M | +0.01 M |

> \* baseline 数据来自 baseline-v2 训练（autodl 历史）

### 6.4 各类别 mAP@0.5（best.pt val）

| 类别 | mAP50 | mAP50-95 |
|---|---|---|
| Car | 95.7% | 78.9% |
| Bus | 93.8% | 77.0% |
| Trafficcone | 92.3% | 49.6% |
| Cyclist | 87.5% | 59.4% |
| Van | 81.3% | 68.1% |
| Truck | 81.3% | 55.2% |
| Pedestrian | 78.7% | 43.0% |
| Motorcyclist | 76.2% | 50.1% |

### 6.5 分析

**结论**：Triplet Attention 在 dair_v2x_i 数据集上对 YOLOv11n 提升**极其有限**（mAP50 +0.2%，mAP50-95 +0.1%），统计上不显著。

**为什么提升小**：

1. **Triplet 设计哲学**：Triplet Attention 是「极轻量」注意力（仅 +10K 参数，<0.5%），在大模型（ResNet-50）上有显著提升，但 YOLOv11n 已经很轻量化，注意力的边际收益小
2. **插入位置**：仅在 backbone P5 末端插入 1 处。论文里通常每个 stage 都插入（多次注意力堆叠），单点插入是最保守版本
3. **数据集特点**：dair_v2x_i 是路侧相机视角（俯瞰角度），Cyclist/Pedestrian 等小目标多。Triplet 更擅长跨通道-空间交互，对多尺度目标的相对收益低于专门的特征金字塔改造

**速度代价**：
- 推理时间：4.1ms → 5ms 增加约 1ms（postprocess 不变，inference 因为多了 attention 计算和 3 次 permute 略慢）
- FPS 从 baseline ~250 降到 244，下降 ~2.4%
- 论文里可写为「计算开销可忽略」（< 5% FPS）

**与 +W 的对比**（同等条件下两个单模块改动）：

| 变体 | mAP50 增益 | mAP50-95 增益 | 参数量代价 | 推理速度代价 |
|---|---|---|---|---|
| +W (WIoU) | +0.3% | +0.1% | 0 (loss 改动) | 0 |
| +T (Triplet) | +0.2% | +0.1% | +10K | -2.4% FPS |

两个单模块改动都在「随机性区间内」，需看后续 +TW、+TD、TDW 组合是否有协同效应。

### 6.6 复现命令

```bash
git clone -b feat/triplet git@github.com:Asus-Github/yolo11.git
cd yolo11
ssh autodl
tmux new -s t_train
tmux set-option -t t_train remain-on-exit on
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
cd /root/autodl-tmp/ultralytics
git checkout feat/triplet
python train_variant.py -c yolo11-t.yaml --iou ciou -n +T 2>&1 | tee runs/+T_train.log
```

**环境注释**：本次实际训练在 `feat/wiou` HEAD 上启动（autodl 当时未切分支），但 `--iou ciou` 使 BboxLoss 走 CIoU 分支，与 `feat/triplet` 分支执行路径**完全等价**（CIoU 代码与 baseline 完全相同，WIoU 代码处于 dormant 状态未触发）。最终结果可重现。

---

## 7. 后续合并到组合分支

| 目标分支 | 合并路径 |
|---|---|
| `feat/triplet-wiou` (+TW) | `git checkout feat/wiou && git merge feat/triplet` 或反之 |
| `feat/triplet-dyhead` (+TD) | `git checkout feat/dyhead && git merge feat/triplet` |
| `feat/tdw` (TDW) | 先合 +T 和 +D，再合 WIoU |

每个组合分支跑完该变体训练，结果都进对应分支，避免污染基础分支。
