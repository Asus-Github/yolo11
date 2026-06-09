# CHANGELOG — feat/dwca-p2

> 分支基于：`feat/dyhead-wiou`（含 DyHeadDetect + WIoU v3 基础设施）
> 创建日期：2026-06-09
> 实验编号：12（DWCA-P2）

---

## 改动摘要

四模块方案：DyHead + WIoU + CoordAttention + P2 小目标检测头。

**去掉 Triplet**（已实证无正收益），以 CoordAttention 替代并新增 P2/4 高分辨率检测分支。

## 设计动机与合理性分析

### 为什么去掉 Triplet？

| 实验 | mAP50 | mAP50-95 | 结论 |
|---|---|---|---|
| +T (Triplet only) | 85.9 | 60.2 | 无提升，甚至 mAP50-95 -0.7 |
| TDW (三模块) | 86.5 | 60.9 | 低于 +DW (87.0/61.3) |
| TDW-CO (channel-only) | 86.7 | 61.2 | 仍低于 +DW |

Triplet 的空间分支与 DyHead 冲突；即使 channel-only 也未超 +DW。**保留 Triplet 无意义。**

### 为什么选 CoordAttention？

1. CA 将位置信息（H/W 方向）编码进通道注意力，是"通道+位置"机制
2. **不做 2D 空间注意力**，与 DyHead 的 spatial-aware module 完全正交
3. CA 的 1D 水平/垂直池化 vs DyHead 的 2D deformable conv → 维度不同，冲突概率极低
4. 参数量极小（几 K），FPS 友好

### 为什么加 P2/4 小目标头？

1. DAIR-V2X-I 路侧远距离行人/骑行者在 P3/8 (80×80) 仍嫌粗
2. P2/4 (160×160) 提供 4 倍分辨率，是检测小目标公认有效手段
3. 与 DyHead 的多尺度 scale-aware module 互补（更多尺度输入）
4. 代价：GFLOPs 显著上升（9.3 → ~12-14），FPS 下降 30-40%

### 预测提升点数

| 指标 | +DW 基线 | DWCA-P2 预测 | 依据 |
|---|---|---|---|
| mAP50 | 87.0% | **87.5~88.0%** | CA(+0.2~0.4) + P2(+0.3~0.6) |
| mAP50-95 | 61.3% | **61.8~62.5%** | 小目标高 IoU 定位改善 |
| Recall | 81.9% | **82.5~83.5%** | P2 直接提升小目标检出率 |
| GFLOPs | 9.3 | ~12-14 | P2 分辨率高，计算量显著增加 |
| Params | 4.35M | ~4.7-5.0M | +CA(几K) + P2 branch(~0.3-0.6M) |

### 风险点

1. **P2 可能增加 FP**：若数据集小目标比例不够高，P2 检测头可能引入更多误检
2. **训练时间增加**：更多 anchors/loss term
3. **GFLOPs 代价大**：但路侧设备算力充裕，工程上可接受

## 文件改动

| 文件 | 操作 | 说明 |
|---|---|---|
| `ultralytics/nn/modules/conv.py` | 修改 | 末尾新增 `CoordAttention` 类 |
| `ultralytics/nn/modules/__init__.py` | 修改 | 导出 `CoordAttention` |
| `ultralytics/nn/tasks.py` | 修改 | import + parse_model 注册 CA |
| `ultralytics/cfg/models/11/yolo11-dwca-p2.yaml` | 新增 | 四模块 YAML |

## 代码改动详情

### CoordAttention（conv.py 末尾）

```python
class CoordAttention(nn.Module):
    """Coordinate Attention (Hou et al., CVPR 2021).
    Encodes positional info into channel attention via H/W pooling.
    """
    def __init__(self, c1, c2=None, reduction=32):
        mid = max(8, c1 // reduction)
        # pool_h: AdaptiveAvgPool2d((None, 1)) → (B,C,H,1)
        # pool_w: AdaptiveAvgPool2d((1, None)) → (B,C,1,W)
        # shared conv1 bottleneck → split → conv_h/conv_w → sigmoid
    def forward(self, x):
        # H/W separate pooling → concat → shared bottleneck → split → attention
        return x * a_h * a_w
```

### YAML 关键结构

```
Backbone: 标准 YOLO11 + CoordAttention at P3 end (layer 5)
Head:
  P5 → P4 → P3 → P2 (top-down)
  P2 → P3 → P4 → P5 (bottom-up)
  DyHeadDetect([P2, P3, P4, P5]) — 4 scale inputs
```

### parse_model 注册逻辑

```python
elif m is CoordAttention:
    c1 = ch[f]
    c2 = c1  # channel-preserving
    args = [c1, c2, *args]  # forward any yaml args (e.g. reduction)
```

## 训练命令（AutoDL）

```bash
# tmux: t_train_dwca_p2
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics && /root/miniconda3/bin/yolo train \
  model=ultralytics/cfg/models/11/yolo11-dwca-p2.yaml \
  data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
  epochs=300 batch=0.85 imgsz=640 optimizer=SGD seed=42 pretrained=false \
  project=runs/ablation name=DWCA-P2 2>&1 | tee runs/DWCA-P2_train.log
```

注意：需在训练脚本中设置 `BboxLoss.iou_type = "wiou"`。

## 通过判据

- mAP50 ≥ 87.5% **且** mAP50-95 ≥ 61.5% → 成功，可作为论文主方法
- 否则回退至 +DW 主线 + 数据/训练侧增强

## 消融子实验（条件触发）

| 编号 | 名称 | 说明 | 何时做 |
|---|---|---|---|
| 12b | DW-P2 | 去掉 CA，只加 P2 | DWCA-P2 成功后看 CA 单独贡献 |
| 12c | DWCA | 去掉 P2，只加 CA | DWCA-P2 成功后看 P2 单独贡献 |

## 复现步骤

1. `git checkout feat/dwca-p2`
2. AutoDL 上同步分支
3. 设置 WIoU：训练前 `BboxLoss.iou_type = "wiou"`
4. 执行上方训练命令
5. 训练完成后采集 best epoch 指标
