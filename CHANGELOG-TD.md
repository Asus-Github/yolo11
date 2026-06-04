# CHANGELOG — `+TD` (Triplet + DyHead)

> Branch: `feat/triplet-dyhead`
> Base: `feat/dyhead` (cherry-pick of `feat/triplet` integration commit `361fd0d`)
> Created: 2026-06-04

## 1. Goal

Combine the two structural improvements that already shipped:

- `+T` (Triplet Attention): inserted at the P5 end of the backbone (before SPPF).
- `+D` (DyHead / DyHeadDetect): replaces the final `Detect` with a head that runs
  cascaded spatial/scale/task-aware DyHead blocks per FPN level.

No loss change — IoU stays at CIoU (same as baseline / `+T` / `+D`).

## 2. Files added / changed

| File | Source | Notes |
|---|---|---|
| `ultralytics/nn/modules/conv.py` | from `feat/triplet` | adds `ZPool`, `AttentionGate`, `TripletAttention` |
| `ultralytics/nn/modules/__init__.py` | merged | exports both `TripletAttention` and `DyHead*` |
| `ultralytics/nn/tasks.py` | merged | imports + `parse_model` branches for both modules |
| `ultralytics/cfg/models/11/yolo11-t.yaml` | from `feat/triplet` | unchanged, kept for reference |
| `ultralytics/cfg/models/11/yolo11-d.yaml` | from `feat/dyhead` | unchanged |
| `ultralytics/cfg/models/11/yolo11-td.yaml` | NEW | yolo11-t backbone + DyHeadDetect head |

`yolo11-td.yaml` design:

- Backbone is byte-identical to `yolo11-t.yaml` (TripletAttention inserted as layer 9
  before SPPF; layers 10–11 are SPPF + C2PSA; head indices reference 4 / 6 / 11).
- Head is the standard YOLO11 PAN-FPN.
- Final detection layer:
  ```yaml
  - [[17, 20, 23], 1, DyHeadDetect, [nc]]
  ```
  — same indices as `yolo11-t.yaml` (since the +1 layer shift carries through),
  but `Detect` → `DyHeadDetect`.

`DyHeadDetect.num_blocks = 2` (class attribute, unchanged from `+D`).

## 3. Branch creation log

```bash
# Local
git checkout feat/dyhead          # 4390b1f (DyHead trained, results recorded)
git checkout -b feat/triplet-dyhead
git cherry-pick 361fd0dba         # Triplet integration from feat/triplet
# Auto-merge: __init__.py, tasks.py — clean.
# Conflict: HANDOFF.md (kept the newer one from feat/dyhead via .bak swap).
```

## 4. Training command

To run on autodl (RTX 4090, dataset `dair_v2x_i`, AutoBatch 0.85 = 85% mem):

```bash
yolo detect train \
  model=ultralytics/cfg/models/11/yolo11-td.yaml \
  data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
  epochs=300 imgsz=640 batch=0.85 \
  device=0 workers=8 \
  project=runs/ablation name=+TD \
  optimizer=SGD iou=0.7 lr0=0.01
```

tmux session: `t_train_td` (with `remain-on-exit on`).
Log: `/root/autodl-tmp/ultralytics/runs/+TD_train.log`.
Output dir: `/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+TD`.

## 5. Results

训练完成于 2026-06-04，autodl RTX 4090，300 epochs / 1.865h，AutoBatch=46。

`best.pt` validation（log 末尾 `Validating best.pt` 段）：

```
all   1411  65255   P=0.858  R=0.810  mAP50=0.862  mAP50-95=0.610
Speed: 0.0ms preprocess, 0.2ms inference, 0.0ms loss, 4.1ms postprocess per image
```

| Metric | +TD |
|---|---|
| Precision | 0.858 |
| Recall | 0.810 |
| mAP@0.5 | 0.862 |
| mAP@0.5:0.95 | 0.610 |
| FPS (`1000/(pre+inf+post)`) | 232.6 |
| GFLOPs | 9.29 |
| Params (M) | 4.36 |

xlsx row 6 (`+TD`) 已更新，列 I–O：85.8 / 81.0 / 86.2 / 61.0 / 232.6 / 9.29 / 4.36。

## 6. 与已完成实验对照

| 行 | 变体 | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | +T | 85.6 | 80.5 | 85.9 | 60.2 | 244 | 6.4 | 2.60 |
| 4 | +D | **86.3** | **81.1** | **86.6** | **61.3** | **435** | 9.3 | 4.35 |
| 5 | +W | 86.4 | 80.3 | 86.0 | 60.2 | 200 | 6.4 | 2.60 |
| 6 | +TD | 85.8 | 81.0 | 86.2 | 61.0 | 233 | 9.29 | 4.36 |

`+TD` 相对单 `+D`：mAP50 −0.4、mAP50-95 −0.3、P −0.5、R 持平、FPS 几乎腰斩。

## 7. 为什么 +TD 没比 +D 更好（论文层面分析）

1. **注意力机制功能重叠**。DyHead 自带 scale/spatial/task 三维度 attention（HSigmoid + offset DCN + 通道重标定），而 Triplet Attention 是 (C-H, C-W, H-W) 三分支 channel-spatial 交互。两者都覆盖 spatial+channel，串联后等效于两层冗余 attention，互相压制 → 注意力饱和。
2. **+T 自身贡献偏小**。row 3 看 +T 在 mAP50-95 = 60.2，与 +W 持平、明显低于 +D 61.3；它能补的短板正好是 head，而 head 已经被 DyHead 替换 → 可加性差。
3. **超参未针对组合重调**。`lr0=0.01 / SGD / 300ep / iou=0.7` 是单模块最优配方；+T 加入后特征分布变化使 DyHead 的 offset 学习更敏感，原 lr 偏大可能让后期收敛点劣化。
4. **小模型对 Triplet 的算子开销敏感**。三分支 permute+pool+conv1x1+sigmoid 在 nano scale latency 占比高，FPS 435→233（−47%），但 GFLOPs 几乎不增（pool/sigmoid 不计 FLOPs），即 **拿延迟换不到精度，是亏的**。
5. **数据集 ceiling**。DAIR-V2X-I baseline 86 附近接近上限，0.3–0.5 mAP 波动也可能落在训练随机性内。

论文价值：在消融表保留 "+TD 略低于 +D" 现象，可论证 "DyHead 已包含空间/通道注意力，再叠 Triplet 收益饱和"。
