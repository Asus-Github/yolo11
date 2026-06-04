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

_Pending_ — fill in once training completes.

| Metric | +TD |
|---|---|
| Precision | TBD |
| Recall | TBD |
| mAP@0.5 | TBD |
| mAP@0.5:0.95 | TBD |
| FPS (`1000/(pre+inf+post)`) | TBD |
| GFLOPs | TBD |
| Params (M) | TBD |

xlsx target row: **row 6** (`+TD`) of `刘华硕-飞书导入实验记录表.xlsx` (`数据表`),
columns I–O.
